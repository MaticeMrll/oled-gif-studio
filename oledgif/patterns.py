"""Motifs animés sans texte : écrans de veille pour OLED.

Importé pour ses effets de bord (enregistrement dans EFFECTS).
"""

import math

from PIL import ImageDraw

from .effects import Ctx, effect
from .render import canvas

# Effets utilisables sans texte ni image
PATTERNS = {"starfield", "plasma", "life", "eq", "scope", "radar"}

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
