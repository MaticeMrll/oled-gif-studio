"""Chargement de police. Priorité aux monospaces (rendu stable sur petit écran)."""

from PIL import ImageFont

# ImageFont.truetype cherche automatiquement dans C:\Windows\Fonts sous Windows.
CANDIDATES = ["consola.ttf", "lucon.ttf", "cour.ttf", "DejaVuSansMono.ttf", "arial.ttf"]


def load_font(path: str | None = None, size: int | None = None, screen_h: int = 40):
    if size is None:
        size = max(8, int(screen_h * 0.62))
    if path:
        return ImageFont.truetype(path, size)
    for name in CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_font(text: str, max_w: int, path: str | None, size: int, screen_h: int):
    """Réduit la taille jusqu'à ce que `text` tienne dans max_w pixels."""
    font = load_font(path, size, screen_h)
    while size > 7:
        try:
            width = font.getlength(text)
        except AttributeError:  # bitmap fallback sans getlength
            break
        if width <= max_w:
            break
        size -= 1
        font = load_font(path, size, screen_h)
    return font
