"""Motifs animés sans texte : écrans de veille pour OLED.

Importé pour ses effets de bord (enregistrement dans EFFECTS).
"""

import math
import time

from PIL import Image, ImageDraw

from .effects import Ctx, effect
from .fonts import fit_font
from .render import canvas, text_image

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

# Effets utilisables sans texte ni image
PATTERNS = {"starfield", "plasma", "life", "eq", "scope", "radar",
            "fire", "snow", "fireworks", "spiral", "tunnel", "clock"}

_BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


@effect("starfield", "champ d'étoiles en hyperespace (sans texte)")
def starfield(ctx: Ctx):
    rng = ctx.rng
    n = max(24, ctx.W * ctx.H // 140)
    stars = [[rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.08, 1.0)]
             for _ in range(n)]
    cx, cy = ctx.W / 2, ctx.H / 2
    frames = []
    for _ in range(ctx.nframes):
        f = canvas(ctx.W, ctx.H)
        px = f.load()
        for s in stars:
            s[2] -= 0.022
            if s[2] <= 0.06:
                s[0], s[1], s[2] = rng.uniform(-1, 1), rng.uniform(-1, 1), 1.0
            x, y = cx + s[0] / s[2] * cx, cy + s[1] / s[2] * cy
            if 0 <= x < ctx.W and 0 <= y < ctx.H:
                px[int(x), int(y)] = 255
                if s[2] < 0.3:  # étoiles proches plus grosses
                    if x + 1 < ctx.W:
                        px[int(x) + 1, int(y)] = 255
                    if y + 1 < ctx.H:
                        px[int(x), int(y) + 1] = 255
        frames.append(f)
    return frames


@effect("plasma", "plasma rétro tramé Bayer, boucle parfaite (sans texte)")
def plasma(ctx: Ctx):
    W, H = ctx.W, ctx.H
    if np is not None:
        return _plasma_np(ctx)
    frames = []
    for t in range(ctx.nframes):
        ph = 2 * math.pi * t / ctx.nframes
        f = canvas(W, H)
        px = f.load()
        for y in range(H):
            for x in range(W):
                v = (math.sin(x / 9 + 2 * ph)
                     + math.sin(y / 5 - 2 * ph)
                     + math.sin((x + y) / 11 + 4 * ph)
                     + math.sin(math.hypot(x - W / 2, y - H / 2) / 6 - 2 * ph)) / 4
                if (v + 1) * 8 > _BAYER4[y % 4][x % 4]:
                    px[x, y] = 255
        frames.append(f)
    return frames


def _plasma_np(ctx: Ctx):
    """Plasma vectorisé numpy (identique au fallback, ~100x plus rapide)."""
    W, H = ctx.W, ctx.H
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
    dist = np.hypot(xs - W / 2, ys - H / 2)
    bayer = np.tile(np.array(_BAYER4, dtype=np.float64),
                    (H // 4 + 1, W // 4 + 1))[:H, :W]
    frames = []
    for t in range(ctx.nframes):
        ph = 2 * math.pi * t / ctx.nframes
        v = (np.sin(xs / 9 + 2 * ph)
             + np.sin(ys / 5 - 2 * ph)
             + np.sin((xs + ys) / 11 + 4 * ph)
             + np.sin(dist / 6 - 2 * ph)) / 4
        arr = np.where((v + 1) * 8 > bayer, 255, 0).astype(np.uint8)
        frames.append(Image.fromarray(arr, "L"))
    return frames


@effect("life", "jeu de la vie de Conway, soupe aléatoire (sans texte)")
def life(ctx: Ctx):
    cell = 2
    gw, gh = max(4, ctx.W // cell), max(4, ctx.H // cell)
    rng = ctx.rng
    grid = [[1 if rng.random() < 0.35 else 0 for _ in range(gw)] for _ in range(gh)]
    frames = []
    for _ in range(ctx.nframes):
        f = canvas(ctx.W, ctx.H)
        d = ImageDraw.Draw(f)
        for r in range(gh):
            for c in range(gw):
                if grid[r][c]:
                    d.rectangle([c * cell, r * cell, c * cell + cell - 1,
                                 r * cell + cell - 1], fill=255)
        frames.append(f)
        nxt = [[0] * gw for _ in range(gh)]
        alive = 0
        for r in range(gh):
            for c in range(gw):
                nb = sum(grid[(r + dr) % gh][(c + dc) % gw]
                         for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                         if (dr, dc) != (0, 0))
                nxt[r][c] = 1 if (nb == 3 or (grid[r][c] and nb == 2)) else 0
                alive += nxt[r][c]
        grid = nxt
        if alive < gw * gh * 0.03:  # la soupe est morte : on ressème
            grid = [[1 if rng.random() < 0.35 else 0 for _ in range(gw)]
                    for _ in range(gh)]
    return frames


@effect("eq", "égaliseur audio : barres et pics qui retombent (sans texte)")
def eq(ctx: Ctx):
    bar_w, gap = 4, 2
    nb = max(3, (ctx.W + gap) // (bar_w + gap))
    rng = ctx.rng
    freqs = [(rng.randint(1, 3), rng.randint(2, 5), rng.uniform(0, math.tau))
             for _ in range(nb)]
    peaks = [0.0] * nb
    frames = []
    for t in range(ctx.nframes):
        ph = 2 * math.pi * t / ctx.nframes
        f = canvas(ctx.W, ctx.H)
        d = ImageDraw.Draw(f)
        for i, (f1, f2, p0) in enumerate(freqs):
            v = abs(0.65 * math.sin(f1 * ph + p0) + 0.35 * math.sin(f2 * ph + 2 * p0))
            h = max(1, int(v * (ctx.H - 3)))
            peaks[i] = max(peaks[i] - ctx.H / (ctx.fps * 1.2), h + 2)
            x = i * (bar_w + gap)
            d.rectangle([x, ctx.H - h, x + bar_w - 1, ctx.H - 1], fill=255)
            py = ctx.H - 1 - int(min(peaks[i], ctx.H - 1))
            d.line([x, py, x + bar_w - 1, py], fill=255)
        frames.append(f)
    return frames


@effect("scope", "oscilloscope : onde sinusoïdale modulée (sans texte)")
def scope(ctx: Ctx):
    cy = ctx.H / 2
    amp = ctx.H * 0.42
    frames = []
    for t in range(ctx.nframes):
        ph = 2 * math.pi * t / ctx.nframes
        f = canvas(ctx.W, ctx.H)
        d = ImageDraw.Draw(f)
        for gx in range(0, ctx.W, 8):  # graduations discrètes
            f.putpixel((gx, int(cy)), 255)
        pts = []
        for x in range(ctx.W):
            env = 0.5 + 0.5 * math.sin(2 * math.pi * x / ctx.W - 2 * ph)
            y = cy + amp * env * math.sin(2 * math.pi * 3 * x / ctx.W + 4 * ph)
            pts.append((x, y))
        d.line(pts, fill=255)
        frames.append(f)
    return frames


@effect("radar", "balayage radar avec échos qui s'effacent (sans texte)")
def radar(ctx: Ctx):
    cx, cy = ctx.W // 2, ctx.H // 2
    R = min(cx, cy) - 1
    rng = ctx.rng
    blips = [(rng.uniform(0, math.tau), rng.uniform(0.3, 0.95)) for _ in range(6)]
    rotations = max(1, round(ctx.seconds / 2))
    frames = []
    for t in range(ctx.nframes):
        sweep = (2 * math.pi * rotations * t / ctx.nframes) % math.tau
        f = canvas(ctx.W, ctx.H)
        d = ImageDraw.Draw(f)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=255)
        d.line([cx, cy,
                cx + R * math.cos(sweep), cy + R * math.sin(sweep)], fill=255)
        for ang, dist in blips:
            age = (sweep - ang) % math.tau
            if age < 1.4:  # l'écho reste visible ~1/4 de tour
                bx, by = cx + R * dist * math.cos(ang), cy + R * dist * math.sin(ang)
                d.rectangle([bx - 1, by - 1, bx + 1, by + 1], fill=255)
        frames.append(f)
    return frames


@effect("fire", "flammes tramées qui montent du bas (sans texte)")
def fire(ctx: Ctx):
    W, H, rng = ctx.W, ctx.H, ctx.rng
    heat = [[0.0] * W for _ in range(H)]
    frames = []
    for _ in range(ctx.nframes):
        for x in range(W):  # braises : rangée du bas ré-allumée
            heat[H - 1][x] = rng.uniform(0.55, 1.0) if rng.random() < 0.9 else 0.15
        for y in range(H - 2, -1, -1):  # propagation vers le haut + dérive + refroidissement
            row, below = heat[y], heat[y + 1]
            for x in range(W):
                sx = min(W - 1, max(0, x + rng.randint(-1, 1)))
                row[x] = max(0.0, below[sx] - rng.uniform(0.02, 0.16))
        f = canvas(W, H)
        px = f.load()
        for y in range(H):
            hy, by = heat[y], _BAYER4[y % 4]
            for x in range(W):
                if hy[x] * 16 > by[x % 4]:
                    px[x, y] = 255
        frames.append(f)
    return frames


@effect("snow", "neige qui tombe et s'accumule (sans texte)")
def snow(ctx: Ctx):
    W, H, rng = ctx.W, ctx.H, ctx.rng
    n = max(12, W * H // 90)
    flakes = [[rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.3, 1.0)]
              for _ in range(n)]
    pile = [0] * W  # hauteur de neige accumulée par colonne
    frames = []
    for _ in range(ctx.nframes):
        f = canvas(W, H)
        px = f.load()
        for fl in flakes:
            fl[1] += fl[2]
            fl[0] += math.sin(fl[1] / 6.0) * 0.35  # dérive latérale
            xi = int(fl[0]) % W
            floor = H - 1 - pile[xi]
            if fl[1] >= floor:  # touche le sol : s'accumule et renaît en haut
                if pile[xi] < H - 2 and rng.random() < 0.6:
                    pile[xi] += 1
                fl[0], fl[1], fl[2] = rng.uniform(0, W), 0.0, rng.uniform(0.3, 1.0)
            else:
                px[xi, int(fl[1])] = 255
        for x in range(W):  # le tas de neige
            for y in range(H - pile[x], H):
                px[x, y] = 255
        if sum(pile) > W * H * 0.55:  # écran plein : on repart propre (boucle)
            pile = [0] * W
        frames.append(f)
    return frames


@effect("fireworks", "feux d'artifice : fusées qui explosent en gerbes (sans texte)")
def fireworks(ctx: Ctx):
    W, H, rng = ctx.W, ctx.H, ctx.rng
    g = H / 900.0  # gravité
    # fusées déjà en vol au départ : évite un début (et un aperçu) vide
    rockets = [[rng.uniform(W * 0.25, W * 0.75), H * f,
                -rng.uniform(0.9, 1.5) * H / 30.0,
                rng.uniform(H * 0.12, H * 0.4)] for f in (0.55, 0.8)]
    sparks = []
    frames = []
    for _ in range(ctx.nframes):
        if rng.random() < 0.14 and len(rockets) < 3:
            rockets.append([rng.uniform(W * 0.2, W * 0.8), float(H),
                            -rng.uniform(0.9, 1.5) * H / 30.0,
                            rng.uniform(H * 0.12, H * 0.45)])
        f = canvas(W, H)
        px = f.load()
        for r in rockets[:]:
            r[1] += r[2]
            if r[1] <= r[3] or r[2] >= 0:  # apogée : explosion
                rockets.remove(r)
                for _ in range(rng.randint(14, 24)):
                    a = rng.uniform(0, math.tau)
                    sp = rng.uniform(0.4, 1.4) * W / 60.0
                    sparks.append([r[0], r[1], math.cos(a) * sp,
                                   math.sin(a) * sp, rng.uniform(6, 14)])
            elif 0 <= int(r[0]) < W and 0 <= int(r[1]) < H:
                px[int(r[0]), int(r[1])] = 255
        for s in sparks[:]:
            s[0] += s[2]
            s[1] += s[3]
            s[3] += g
            s[4] -= 1
            if s[4] <= 0:
                sparks.remove(s)
            elif 0 <= int(s[0]) < W and 0 <= int(s[1]) < H:
                px[int(s[0]), int(s[1])] = 255
        frames.append(f)
    return frames


@effect("spiral", "spirale hypnotique en rotation, boucle parfaite (sans texte)")
def spiral(ctx: Ctx):
    W, H = ctx.W, ctx.H
    cx, cy = W / 2, H / 2
    maxr = math.hypot(cx, cy)
    frames = []
    for t in range(ctx.nframes):
        ph = 2 * math.pi * t / ctx.nframes  # un tour complet = boucle
        f = canvas(W, H)
        d = ImageDraw.Draw(f)
        for arm in (0, math.pi):  # deux bras
            pts, theta = [], 0.0
            while True:
                r = 1.3 * theta
                if r > maxr:
                    break
                a = theta + ph + arm
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                theta += 0.28
            if len(pts) > 1:
                d.line(pts, fill=255)
        frames.append(f)
    return frames


@effect("tunnel", "tunnel damier en profondeur, boucle parfaite (sans texte)")
def tunnel(ctx: Ctx):
    W, H = ctx.W, ctx.H
    cx, cy = W / 2, H / 2
    sectors, cycles = 8, 3  # damier angulaire ; cycles entiers => boucle
    if np is not None:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float64)
        dist = np.hypot(xs - cx, ys - cy) + 1e-6
        ang = np.arctan2(ys - cy, xs - cx)
        depth = min(cx, cy) * 6.0 / dist
        a_idx = np.floor(ang / (2 * math.pi) * sectors)
        frames = []
        for t in range(ctx.nframes):
            d_idx = np.floor(depth + t / ctx.nframes * cycles * 2)
            arr = np.where(((a_idx + d_idx).astype(np.int64) & 1) == 0, 255, 0)
            frames.append(Image.fromarray(arr.astype(np.uint8), "L"))
        return frames
    frames = []
    for t in range(ctx.nframes):
        f = canvas(W, H)
        px = f.load()
        for y in range(H):
            for x in range(W):
                dist = math.hypot(x - cx, y - cy) + 1e-6
                ang = math.atan2(y - cy, x - cx)
                depth = min(cx, cy) * 6.0 / dist
                a_idx = math.floor(ang / (2 * math.pi) * sectors)
                d_idx = math.floor(depth + t / ctx.nframes * cycles * 2)
                if (int(a_idx + d_idx) & 1) == 0:
                    px[x, y] = 255
        frames.append(f)
    return frames


@effect("clock", "horloge numérique HH:MM:SS qui égrène les secondes (sans texte)")
def clock(ctx: Ctx):
    W, H = ctx.W, ctx.H
    base = time.localtime()
    start = base.tm_hour * 3600 + base.tm_min * 60 + base.tm_sec
    font = fit_font("00:00:00", W - 4, ctx.font_path, ctx.font_size or int(H * 0.55), H)
    frames = []
    for t in range(ctx.nframes):
        secs = (start + t // max(1, ctx.fps)) % 86400
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        sep = ":" if (t // max(1, ctx.fps // 2)) % 2 == 0 else " "  # deux-points clignotant
        txt = f"{h:02d}{sep}{m:02d}{sep}{s:02d}"
        img = text_image(txt, font)
        f = canvas(W, H)
        f.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
        frames.append(f)
    return frames
