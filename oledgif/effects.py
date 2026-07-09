"""Effets d'animation. Chaque effet reçoit un Ctx et retourne une liste de frames "L"."""

import math
import random
import string
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from .fonts import fit_font, load_font
from .render import canvas, char_images, text_image

ALNUM = string.digits + string.ascii_uppercase + string.ascii_lowercase

EFFECTS: dict[str, callable] = {}
DESCRIPTIONS: dict[str, str] = {}


def effect(name: str, desc: str):
    def deco(fn):
        EFFECTS[name] = fn
        DESCRIPTIONS[name] = desc
        return fn
    return deco


@dataclass
class Ctx:
    text: str
    W: int
    H: int
    fps: int = 15
    seconds: float = 4.0
    font: object = None
    font_path: str | None = None
    font_size: int | None = None
    charset: str = ALNUM
    speed: float | None = None  # px/s pour scroll
    src: object = None  # image source (--image) ; sinon le texte est rendu
    rng: random.Random = field(default_factory=random.Random)

    @property
    def nframes(self) -> int:
        return max(2, int(round(self.fps * self.seconds)))

    def center(self, img) -> tuple[int, int]:
        return (self.W - img.width) // 2, (self.H - img.height) // 2

    def sprite(self):
        """Ce que l'effet anime : l'image fournie, sinon le texte rendu."""
        return self.src if self.src is not None else text_image(self.text, self.font)


# ---------------------------------------------------------------- scroll

@effect("scroll", "le texte/l'image défile de droite à gauche (boucle parfaite)")
def scroll(ctx: Ctx):
    timg = ctx.sprite()
    speed = ctx.speed or max(20.0, ctx.W / 3)  # px/s
    travel = ctx.W + timg.width
    n = max(2, int(round(travel / speed * ctx.fps)))
    y = (ctx.H - timg.height) // 2
    frames = []
    for i in range(n):
        f = canvas(ctx.W, ctx.H)
        x = ctx.W - int(round(travel * i / n))
        f.paste(timg, (x, y))
        frames.append(f)
    return frames


# ---------------------------------------------------------------- typewriter

@effect("typewriter", "machine à écrire : les lettres apparaissent une à une, curseur clignotant")
def typewriter(ctx: Ctx):
    cps = 8  # caractères/seconde
    fpc = max(1, round(ctx.fps / cps))
    blink = max(1, ctx.fps // 2)
    hold = int(ctx.fps * 1.5)
    frames = []
    total = len(ctx.text) * fpc + hold
    for t in range(total):
        k = min(len(ctx.text), t // fpc + 1) if t < len(ctx.text) * fpc else len(ctx.text)
        part = ctx.text[:k]
        timg = text_image(part, ctx.font) if part.strip() else None
        f = canvas(ctx.W, ctx.H)
        w = timg.width if timg else int(ctx.font.getlength(part)) if part else 0
        x = min(2, ctx.W - 6 - w)  # reste lisible si le texte déborde
        y = (ctx.H - (timg.height if timg else ctx.H // 2)) // 2
        if timg:
            f.paste(timg, (x, y))
        if (t // blink) % 2 == 0:  # curseur bloc
            ch = timg.height if timg else max(8, ctx.H // 2)
            cx = x + w + 2
            ImageDraw.Draw(f).rectangle([cx, y, cx + max(3, ch // 2), y + ch], fill=255)
        frames.append(f)
    return frames


# ---------------------------------------------------------------- wave

@effect("wave", "les lettres ondulent verticalement en vague")
def wave(ctx: Ctx):
    chars = char_images(ctx.text, ctx.font)
    total_w = sum(adv for _, adv in chars)
    x0 = (ctx.W - total_w) // 2
    max_h = max((im.height for im, _ in chars if im), default=ctx.H // 2)
    mid = (ctx.H - max_h) // 2
    amp = max(1, min(mid, int(ctx.H * 0.18)))
    frames = []
    for t in range(ctx.nframes):
        f = canvas(ctx.W, ctx.H)
        phase = 2 * math.pi * t / ctx.nframes * max(1, round(ctx.seconds))
        x = x0
        for i, (im, adv) in enumerate(chars):
            if im:
                y = mid + int(round(amp * math.sin(phase + i * 0.7)))
                f.paste(im, (x, y))
            x += adv
        frames.append(f)
    return frames


# ---------------------------------------------------------------- blink

@effect("blink", "le texte/l'image clignote")
def blink(ctx: Ctx):
    timg = ctx.sprite()
    pos = ctx.center(timg)
    period = max(2, ctx.fps // 2)
    frames = []
    for t in range(ctx.nframes):
        f = canvas(ctx.W, ctx.H)
        if (t // period) % 2 == 0:
            f.paste(timg, pos)
        frames.append(f)
    return frames


# ---------------------------------------------------------------- bounce

@effect("bounce", "le texte/l'image rebondit sur les bords (façon logo DVD)")
def bounce(ctx: Ctx):
    timg = ctx.sprite()
    free_x, free_y = max(0, ctx.W - timg.width), max(0, ctx.H - timg.height)
    vx = free_x / (ctx.fps * 1.6) if free_x else 0.0
    vy = free_y / (ctx.fps * 0.9) if free_y else 0.0
    vx, vy = max(vx, 0.4) if free_x else 0, max(vy, 0.4) if free_y else 0
    x, y = free_x * 0.3, free_y * 0.7
    frames = []
    for _ in range(ctx.nframes):
        f = canvas(ctx.W, ctx.H)
        f.paste(timg, (int(round(x)), int(round(y))))
        frames.append(f)
        x += vx
        y += vy
        if free_x and (x < 0 or x > free_x):
            vx = -vx
            x = max(0.0, min(x, float(free_x)))
        if free_y and (y < 0 or y > free_y):
            vy = -vy
            y = max(0.0, min(y, float(free_y)))
    return frames


# ---------------------------------------------------------------- matrix

@effect("matrix", "pluie de caractères alphanumériques ; le texte se révèle au centre (texte optionnel)")
def matrix(ctx: Ctx):
    fm = load_font(ctx.font_path, size=max(8, ctx.H // 4), screen_h=ctx.H)
    cell_w = max(4, int(round(fm.getlength("0")))) if hasattr(fm, "getlength") else 6
    cell_h = max(6, text_image("0", fm).height + 1)
    ncols, nrows = max(1, ctx.W // cell_w), max(1, ctx.H // cell_h) + 1
    rng = ctx.rng
    grid = [[rng.choice(ctx.charset) for _ in range(nrows)] for _ in range(ncols)]
    heads = [rng.uniform(0, nrows) for _ in range(ncols)]
    speeds = [rng.uniform(0.15, 0.55) for _ in range(ncols)]
    trails = [rng.randint(2, max(3, nrows)) for _ in range(ncols)]
    reveal_at = int(ctx.nframes * 0.55)
    timg = ctx.sprite() if (ctx.text.strip() or ctx.src is not None) else None
    frames = []
    for t in range(ctx.nframes):
        f = canvas(ctx.W, ctx.H)
        d = ImageDraw.Draw(f)
        for c in range(ncols):
            heads[c] = (heads[c] + speeds[c]) % (nrows + trails[c])
            if rng.random() < 0.15:
                grid[c][rng.randrange(nrows)] = rng.choice(ctx.charset)
            for k in range(trails[c]):
                r = int(heads[c]) - k
                if 0 <= r < nrows:
                    d.text((c * cell_w, r * cell_h), grid[c][r], font=fm, fill=255)
        if timg and t >= reveal_at:
            x, y = ctx.center(timg)
            d.rectangle([x - 3, y - 2, x + timg.width + 2, y + timg.height + 1], fill=0)
            f.paste(timg, (x, y))
        frames.append(f)
    return frames


# ---------------------------------------------------------------- slot

@effect("slot", "machine à sous : chaque position cycle sur tout l'alphabet puis se fige")
def slot(ctx: Ctx):
    cells = len(ctx.text)
    size = ctx.font_size or max(8, int(ctx.H * 0.62))
    font = fit_font("0" * max(1, cells), ctx.W - 4, ctx.font_path, size, ctx.H)
    cell_w = int(round(font.getlength("0"))) + 1 if hasattr(font, "getlength") else 7
    x0 = (ctx.W - cell_w * cells) // 2
    lock = [int(ctx.nframes * 0.7 * (i + 1) / (cells + 1)) for i in range(cells)]
    rng = ctx.rng
    frames = []
    for t in range(ctx.nframes):
        f = canvas(ctx.W, ctx.H)
        d = ImageDraw.Draw(f)
        for i, target in enumerate(ctx.text):
            ch = target if (t >= lock[i] or target == " ") else rng.choice(ctx.charset)
            im = text_image(ch, font) if ch != " " else None
            if im:
                f.paste(im, (x0 + i * cell_w + (cell_w - im.width) // 2,
                             (ctx.H - im.height) // 2))
        frames.append(f)
    return frames


# ---------------------------------------------------------------- glitch

@effect("glitch", "texte/image corrompu : bandes décalées et bruit aléatoire")
def glitch(ctx: Ctx):
    base = canvas(ctx.W, ctx.H)
    timg = ctx.sprite()
    base.paste(timg, ctx.center(timg))
    rng = ctx.rng
    frames = []
    for t in range(ctx.nframes):
        f = base.copy()
        if t % 7 != 0:  # frame propre régulière, ça respire
            for _ in range(rng.randint(1, 3)):
                y0 = rng.randrange(0, ctx.H - 2)
                h = rng.randint(2, max(3, ctx.H // 5))
                dx = rng.randint(-ctx.W // 8, ctx.W // 8)
                band = f.crop((0, y0, ctx.W, min(ctx.H, y0 + h)))
                ImageDraw.Draw(f).rectangle([0, y0, ctx.W, y0 + h], fill=0)
                f.paste(band, (dx, y0))
            px = f.load()
            for _ in range(int(ctx.W * ctx.H * 0.006)):
                px[rng.randrange(ctx.W), rng.randrange(ctx.H)] = 255
        frames.append(f)
    return frames


# ---------------------------------------------------------------- pulse

@effect("pulse", "le texte/l'image bat comme un cœur (zoom avant/arrière)")
def pulse(ctx: Ctx):
    timg = ctx.sprite()
    frames = []
    for t in range(ctx.nframes):
        s = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(2 * math.pi * t / ctx.fps))
        im = timg.resize((max(1, int(timg.width * s)), max(1, int(timg.height * s))),
                         Image.NEAREST)
        f = canvas(ctx.W, ctx.H)
        f.paste(im, ctx.center(im))
        frames.append(f)
    return frames


# ---------------------------------------------------------------- vhs

@effect("vhs", "tremblement horizontal façon cassette vidéo (défaut pour les images)")
def vhs(ctx: Ctx):
    base = canvas(ctx.W, ctx.H)
    timg = ctx.sprite()
    base.paste(timg, ctx.center(timg))
    rng = ctx.rng
    n = ctx.nframes
    tau = 2 * math.pi
    cycles = max(1, round(ctx.seconds / 2))  # ondulations complètes par boucle
    frames = []
    for t in range(n):
        ph = tau * t / n
        f = canvas(ctx.W, ctx.H)
        band_y = int(ctx.H * t / n)  # bande de tracking, 1 passage par boucle
        jerk = rng.choice((-2, 2)) if rng.random() < 0.12 else 0  # à-coup
        for y in range(ctx.H):
            off = round(1.6 * math.sin(ph * cycles + y / 6.5)
                        + 0.9 * math.sin(ph * 2 * cycles + y / 2.8)) + jerk
            if abs(y - band_y) < 2:
                off += 4 + rng.randint(0, 3)
            row = base.crop((0, y, ctx.W, y + 1))
            f.paste(row, (off % ctx.W, y))
            f.paste(row, (off % ctx.W - ctx.W, y))  # bouclage horizontal
        d = ImageDraw.Draw(f)
        for _ in range(rng.randint(2, 6)):  # poussière sur la bande
            x = rng.randrange(ctx.W)
            d.line([x, band_y, min(ctx.W - 1, x + rng.randint(1, 4)), band_y], fill=255)
        frames.append(f)
    return frames


# ---------------------------------------------------------------- slide

@effect("slide", "le texte/l'image entre par le bas, pause, sort par le haut")
def slide(ctx: Ctx):
    timg = ctx.sprite()
    x, yc = ctx.center(timg)
    n = ctx.nframes
    n_in, n_out = int(n * 0.25), int(n * 0.25)
    frames = []
    for t in range(n):
        f = canvas(ctx.W, ctx.H)
        if t < n_in:
            y = ctx.H - int((ctx.H - yc) * (t + 1) / n_in)
        elif t >= n - n_out:
            k = t - (n - n_out)
            y = yc - int((yc + timg.height) * (k + 1) / n_out)
        else:
            y = yc
        f.paste(timg, (x, y))
        frames.append(f)
    return frames
