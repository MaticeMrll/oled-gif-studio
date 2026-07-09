"""Rendu bas niveau : texte/image -> bitmap, binarisation 1 bit, écriture GIF."""

import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageSequence

try:  # numpy accélère nettement despeckle/plasma ; fallback pur Python sinon
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

THRESHOLD = 128


def canvas(w: int, h: int) -> Image.Image:
    return Image.new("L", (w, h), 0)


def text_image(text: str, font) -> Image.Image:
    """Rend `text` (blanc sur noir) dans une image ajustée au plus près."""
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    bbox = probe.textbbox((0, 0), text, font=font)
    w = max(1, bbox[2] - bbox[0])
    h = max(1, bbox[3] - bbox[1])
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text((-bbox[0], -bbox[1]), text, font=font, fill=255)
    return img


def char_images(text: str, font):
    """Liste (image, avance_x) par caractère — pour les effets par lettre."""
    out = []
    for ch in text:
        try:
            adv = font.getlength(ch)
        except AttributeError:
            adv = text_image(ch, font).width + 1
        out.append((None if ch == " " else text_image(ch, font), int(round(adv))))
    return out


def _fit(im: Image.Image, max_w: int, max_h: int, fit: str) -> Image.Image:
    if fit == "cover":
        return ImageOps.fit(im, (max_w, max_h), Image.LANCZOS)
    scale = min(max_w / im.width, max_h / im.height)
    return im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))),
                     Image.LANCZOS)


def _despeckle(im: Image.Image) -> Image.Image:
    """Éteint tout pixel 0/255 dont aucun des 8 voisins n'a sa couleur.

    Élimine le « poivre et sel » (reflets, sources de lumière ponctuelles)
    sans toucher à la trame Floyd-Steinberg, dont les pixels ont toujours
    des voisins diagonaux de même couleur.
    """
    if np is not None:
        return _despeckle_np(im)
    w, h = im.size
    px = im.load()
    out = im.copy()
    po = out.load()
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            alone = True
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and px[nx, ny] == v:
                        alone = False
                        break
                if not alone:
                    break
            if alone:
                po[x, y] = 255 - v
    return out


def _despeckle_np(im: Image.Image) -> Image.Image:
    """Équivalent vectorisé de `_despeckle` (voir docstring). ~50x plus rapide."""
    a = np.asarray(im, dtype=np.int16)
    # bord rembourré avec un sentinelle (-1) qui n'égale jamais 0/255
    p = np.pad(a, 1, constant_values=-1)
    h, w = a.shape
    same = np.zeros((h, w), dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            same |= p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w] == a
    out = a.copy()
    alone = ~same
    out[alone] = 255 - out[alone]
    return Image.fromarray(out.astype("uint8"), "L")


def _otsu(hist) -> int | None:
    """Seuil d'Otsu (variance inter-classes maximale) sur un histogramme 256 bins."""
    total = sum(hist)
    if total == 0:
        return None
    s_all = sum(i * h for i, h in enumerate(hist))
    w0 = s0 = 0
    best, thr = 0.0, None
    for t in range(256):
        w0 += hist[t]
        if w0 == 0:
            continue
        w1 = total - w0
        if w1 == 0:
            break
        s0 += t * hist[t]
        m0, m1 = s0 / w0, (s_all - s0) / w1
        var = w0 * w1 * (m0 - m1) ** 2
        if var > best:
            best, thr = var, t
    return thr


def _prepare(im: Image.Image, max_w: int, max_h: int,
             style: str = "photo", fit: str = "contain",
             denoise: bool = True) -> Image.Image:
    """Niveaux de gris + redimensionnement, puis conversion 1 bit selon `style`.

    photo  : auto-contraste + netteté + trame Floyd-Steinberg (photos)
    solid  : seuillage net à l'écriture (logos, dessins au trait)
    comic  : solid + les formes noyées dans le noir retracées en contour blanc
    edges  : détection de contours -> traits blancs sur noir (photos très petites)
    denoise: filtre médian avant conversion + suppression des pixels isolés après
    """
    im = ImageOps.exif_transpose(im).convert("L")
    if style == "edges":
        # contours calculés en 2x puis épaissis, sinon ils disparaissent à la réduction
        big = _fit(im, max_w * 2, max_h * 2, fit)
        big = ImageOps.autocontrast(big, cutoff=1)
        if denoise:
            big = big.filter(ImageFilter.MedianFilter(3))
        big = big.filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.FIND_EDGES)
        ImageDraw.Draw(big).rectangle([0, 0, big.width - 1, big.height - 1],
                                      outline=0, width=2)  # cadre = artefact du bord
        big = ImageOps.autocontrast(big).filter(ImageFilter.MaxFilter(3))
        small = big.resize((max(1, big.width // 2), max(1, big.height // 2)), Image.LANCZOS)
        # seuil adaptatif : on garde ~10 % des pixels (les contours les plus forts)
        hist, acc, thr = small.histogram(), 0, 255
        budget = small.width * small.height * 0.10
        for lvl in range(255, -1, -1):
            acc += hist[lvl]
            if acc >= budget:
                thr = lvl
                break
        thr = max(24, thr)
        small = small.point(lambda p: 255 if p >= thr else 0)
        return _despeckle(small) if denoise else small
    im = _fit(im, max_w, max_h, fit)
    im = ImageOps.autocontrast(im, cutoff=1)
    if style == "comic":
        if denoise:
            im = im.filter(ImageFilter.MedianFilter(3))
        solid = im.point(lambda p: 255 if p >= THRESHOLD else 0)
        dark = ImageChops.invert(solid)  # blanc = zones noires du seuillage
        hist = im.histogram(dark.convert("1"))
        thr = _otsu(hist)
        total = sum(hist)
        if thr is None or total == 0:
            return solid
        lo = sum(hist[:thr + 1])
        if min(lo, total - lo) / total < 0.05:  # zone noire quasi unie : rien à tracer
            return solid
        # frontière entre les deux populations sombres (ex. ciel / silhouette),
        # tenue à 1 px des zones blanches pour ne pas doubler leurs bords
        mid = ImageChops.multiply(im.point(lambda p, t=thr: 255 if p > t else 0), dark)
        contour = ImageChops.difference(mid, mid.filter(ImageFilter.MinFilter(3)))
        contour = ImageChops.multiply(contour, dark.filter(ImageFilter.MinFilter(3)))
        out = ImageChops.lighter(solid, contour)
        return _despeckle(out) if denoise else out
    if style == "photo":
        if denoise:  # pas en solid : le médian arrondirait les logos nets
            im = im.filter(ImageFilter.MedianFilter(3))
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=160, threshold=2))
        im = im.convert("1", dither=Image.FLOYDSTEINBERG).convert("L")
        if denoise:
            im = _despeckle(im)
    return im


def load_source(path: str, max_w: int, max_h: int, style: str = "photo",
                fit: str = "contain", denoise: bool = True) -> Image.Image:
    """Charge une image et la prépare comme 'sprite' 1 bit pour les effets."""
    return _prepare(Image.open(path), max_w, max_h, style, fit, denoise)


def convert_animation(path: str, w: int, h: int, style: str = "photo",
                      fit: str = "contain", denoise: bool = True):
    """Convertit un GIF animé existant : frames centrées + durées d'origine."""
    im = Image.open(path)
    frames, durations = [], []
    for raw in ImageSequence.Iterator(im):
        sprite = _prepare(raw.convert("L"), w, h, style, fit, denoise)
        f = canvas(w, h)
        f.paste(sprite, ((w - sprite.width) // 2, (h - sprite.height) // 2))
        frames.append(f)
        durations.append(max(20, int(raw.info.get("duration", 100))))
    return frames, durations


def binarize(frame: Image.Image, invert: bool = False) -> Image.Image:
    if invert:
        return frame.point(lambda p: 0 if p >= THRESHOLD else 255).convert("1")
    return frame.point(lambda p: 255 if p >= THRESHOLD else 0).convert("1")


def save_gif(frames, path: str, fps: int, invert: bool = False, scale: int = 1,
             loop: int = 0, durations=None):
    """Binarise, agrandit (nearest) si demandé, et écrit le GIF bouclé.

    `durations` (liste de ms par frame) prime sur `fps` — utile en conversion.
    """
    if not frames:
        raise ValueError("aucune frame à écrire (l'effet n'a rien produit)")
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    out = []
    for f in frames:
        b = binarize(f, invert)
        if scale > 1:
            b = b.resize((b.width * scale, b.height * scale), Image.NEAREST)
        out.append(b.convert("P"))
    duration = durations if durations else max(20, int(round(1000 / fps)))
    out[0].save(
        path,
        save_all=True,
        append_images=out[1:],
        duration=duration,
        loop=loop,
        optimize=True,
    )
    return len(out), (duration if isinstance(duration, int) else duration[0])
