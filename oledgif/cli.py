"""CLI : python -m oledgif "TEXTE" [options]"""

import argparse
import os
import random
import string
import sys

from . import __version__
from .describe import parse as parse_description
from .effects import ALNUM, DESCRIPTIONS, EFFECTS, Ctx
from .export import EXT, FORMATS, save_export
from .fonts import load_font
from .patterns import PATTERNS
from .presets import DEFAULT_PRESET, PRESETS, resolve_size
from .render import convert_animation, load_source, save_gif

from PIL import Image

CHARSETS = {
    "alnum": ALNUM,
    "digits": string.digits,
    "upper": string.digits + string.ascii_uppercase,
    "letters": string.ascii_letters,
    "ascii": "".join(c for c in string.printable if c.isprintable() and c != " "),
}


def build_parser():
    p = argparse.ArgumentParser(
        prog="oledgif",
        description="Génère des GIFs animés 1 bit pour écrans OLED (SteelSeries, SSD1306...).",
    )
    p.add_argument("text", nargs="?", help="texte à animer (optionnel avec --image ou un motif)")
    p.add_argument("-d", "--describe", metavar="PHRASE",
                   help="décrire l'animation en langage naturel, ex: 'GG qui clignote vite'")
    p.add_argument("-i", "--image", metavar="FICHIER",
                   help="image source (PNG/JPG/GIF...) : convertie en 1 bit avec tramage ; "
                        "un GIF animé est converti tel quel si --effect vaut auto/convert")
    p.add_argument("--style", default="photo", choices=["photo", "solid", "comic", "edges"],
                   help="rendu de --image : photo = contraste+netteté+tramage (défaut), "
                        "solid = seuillage net (logos), comic = solid + contours blancs "
                        "des formes perdues dans le noir (illustrations), "
                        "edges = contours blancs sur noir")
    p.add_argument("--fit", default="contain", choices=["contain", "cover"],
                   help="contain = image entière (défaut), cover = remplit l'écran en "
                        "recadrant — recommandé pour les photos paysage")
    p.add_argument("--no-dither", action="store_true",
                   help="alias de --style solid")
    p.add_argument("--no-denoise", action="store_true",
                   help="garde le bruit : désactive le filtre médian et la suppression "
                        "des pixels isolés (reflets, sources de lumière ponctuelles)")
    p.add_argument("-o", "--out", default=None, help="fichier de sortie (.gif/.h/.xbm)")
    p.add_argument("-f", "--format", default="gif", choices=sorted(FORMATS),
                   help="gif (défaut) ; c-array = header C uint8_t[] PROGMEM pour "
                        "Arduino/QMK (drawBitmap) ; xbm = X BitMap (1 frame)")
    p.add_argument("-p", "--preset", default=None,
                   help=f"écran cible (défaut: {DEFAULT_PRESET}) — voir --list-presets")
    p.add_argument("--size", default=None, metavar="WxH", help="taille custom, ex: 128x40")
    p.add_argument("-e", "--effect", default="auto",
                   help="effet (défaut: auto) — voir --list-effects")
    p.add_argument("--fps", type=int, default=15)
    p.add_argument("--seconds", type=float, default=4.0, help="durée cible (certains effets la déduisent)")
    p.add_argument("--speed", type=float, default=None, help="vitesse de défilement en px/s (scroll)")
    p.add_argument("--font", default=None, help="chemin d'une police .ttf")
    p.add_argument("--font-size", type=int, default=None)
    p.add_argument("--charset", default="alnum",
                   help="alnum|digits|upper|letters|ascii ou chaîne littérale (matrix/slot)")
    p.add_argument("--invert", action="store_true", help="noir sur blanc")
    p.add_argument("--scale", type=int, default=1, help="agrandit le GIF xN (aperçu)")
    p.add_argument("--seed", type=int, default=None, help="graine aléatoire (rendu reproductible)")
    p.add_argument("--push", action="store_true",
                   help="envoie l'animation directement à l'écran OLED SteelSeries "
                        "(GameSense) au lieu d'écrire un fichier ; Ctrl-C pour arrêter")
    p.add_argument("--loops", type=int, default=0,
                   help="nombre de boucles pour --push (0 = infini, défaut)")
    p.add_argument("--demo", action="store_true", help="génère un exemple de chaque effet dans ./samples")
    p.add_argument("--list-effects", action="store_true")
    p.add_argument("--list-presets", action="store_true")
    p.add_argument("--version", action="version", version=f"oledgif {__version__}")
    return p


def build_frames(text, *, preset=None, size=None, effect="auto", fps=15, seconds=4.0,
                 speed=None, font_path=None, font_size=None, charset=ALNUM,
                 seed=None, image=None, style="photo", fit="contain", denoise=True):
    """Construit les frames sans écrire : retourne (frames, durations, effect, W, H).

    `durations` vaut None sauf pour la conversion d'un GIF animé source.
    """
    W, H = resolve_size(preset, size)
    font = load_font(font_path, font_size, screen_h=H)

    frames, durations = None, None
    src = None
    if image:
        im = Image.open(image)
        if getattr(im, "is_animated", False) and effect in ("auto", "convert"):
            # GIF animé -> conversion frame par frame, durées d'origine conservées
            frames, durations = convert_animation(image, W, H, style, fit, denoise)
            effect = "convert"
        else:
            im.close()
            src = load_source(image, W, H, style, fit, denoise)
            if effect in ("auto", "convert"):
                effect = "vhs"

    if frames is None:
        if effect == "auto":
            try:
                wide = font.getlength(text) > W - 4
            except AttributeError:
                wide = len(text) * 7 > W - 4
            effect = "scroll" if wide else "wave"
        if effect not in EFFECTS:
            raise SystemExit(f"Effet inconnu: {effect!r}. Effets: {', '.join(EFFECTS)}")
        ctx = Ctx(text=text or "", W=W, H=H, fps=fps, seconds=seconds, font=font,
                  font_path=font_path, font_size=font_size, charset=charset,
                  speed=speed, src=src, rng=random.Random(seed))
        frames = EFFECTS[effect](ctx)
    return frames, durations, effect, W, H


def make_gif(text, out, *, preset=None, size=None, effect="auto", fps=15, seconds=4.0,
             speed=None, font_path=None, font_size=None, charset=ALNUM,
             invert=False, scale=1, seed=None, image=None, style="photo", fit="contain",
             denoise=True, fmt="gif"):
    frames, durations, effect, W, H = build_frames(
        text, preset=preset, size=size, effect=effect, fps=fps, seconds=seconds,
        speed=speed, font_path=font_path, font_size=font_size, charset=charset,
        seed=seed, image=image, style=style, fit=fit, denoise=denoise)

    if fmt == "gif":
        n, duration = save_gif(frames, out, fps=fps, invert=invert,
                               scale=scale, durations=durations)
        return out, effect, W, H, n, duration

    dur = durations if durations else max(20, int(round(1000 / fps)))
    _, n = save_export(frames, out, fmt, W, H, dur, invert=invert)
    return out, effect, W, H, n, (dur[0] if isinstance(dur, list) else dur)


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.list_effects:
        for name, desc in DESCRIPTIONS.items():
            print(f"  {name:<11} {desc}")
        return 0
    if args.list_presets:
        for name, (w, h, desc) in PRESETS.items():
            print(f"  {name:<12} {w}x{h:<4} {desc}")
        return 0

    charset = CHARSETS.get(args.charset, args.charset)

    if args.demo:
        outdir = "samples"
        os.makedirs(outdir, exist_ok=True)
        text = args.text or "GG WP 42"
        for name in EFFECTS:
            out = os.path.join(outdir, f"{name}.gif")
            make_gif(text, out, preset=args.preset, size=args.size, effect=name,
                     fps=args.fps, seconds=args.seconds, speed=args.speed,
                     font_path=args.font, font_size=args.font_size, charset=charset,
                     invert=args.invert, scale=args.scale, seed=args.seed or 42)
            print(f"  {out}")
        return 0

    text, effect, fps, seconds = args.text, args.effect, args.fps, args.seconds
    if args.describe:
        parsed = parse_description(args.describe)
        text = parsed.get("text", text)
        if effect == "auto":
            effect = parsed.get("effect", "auto")
        fps = parsed.get("fps", fps)
        seconds = parsed.get("seconds", seconds)

    textless_ok = args.image or effect in PATTERNS or effect == "matrix"
    if not text and not textless_ok:
        print("Erreur: aucun texte. Passe-le en argument, entre guillemets dans --describe, "
              "ou utilise --image / un motif (starfield, plasma, life, eq, scope, radar).",
              file=sys.stderr)
        return 2

    if args.push:
        from .push import PushError, push_animation
        frames, durations, effect, W, H = build_frames(
            text, preset=args.preset, size=args.size, effect=effect, fps=fps,
            seconds=seconds, speed=args.speed, font_path=args.font,
            font_size=args.font_size, charset=charset, seed=args.seed,
            image=args.image, style="solid" if args.no_dither else args.style,
            fit=args.fit, denoise=not args.no_denoise)
        print(f"-> push {W}x{H}, effet {effect}, {len(frames)} frames vers SteelSeries "
              f"({'inf' if args.loops == 0 else args.loops} boucle(s), Ctrl-C pour arreter)")
        try:
            sent = push_animation(frames, W, H, fps=fps, loops=args.loops,
                                  invert=args.invert, durations=durations)
        except PushError as exc:
            print(f"Erreur push: {exc}", file=sys.stderr)
            return 3
        except KeyboardInterrupt:
            print("\ninterrompu.")
            return 0
        print(f"{sent} frames envoyées.")
        return 0

    ext = EXT[args.format]
    if args.out:
        out = args.out
    elif text:
        out = "".join(c if c.isalnum() else "_" for c in text)[:24] + ext
    elif args.image:
        out = os.path.splitext(os.path.basename(args.image))[0] + "_oled" + ext
    else:
        out = f"{effect}{ext}"
    out, effect, W, H, n, duration = make_gif(
        text, out, preset=args.preset, size=args.size, effect=effect, fps=fps,
        seconds=seconds, speed=args.speed, font_path=args.font,
        font_size=args.font_size, charset=charset, invert=args.invert,
        scale=args.scale, seed=args.seed, image=args.image,
        style="solid" if args.no_dither else args.style, fit=args.fit,
        denoise=not args.no_denoise, fmt=args.format)
    unit = "frames" if args.format == "gif" else f"frame(s) -> {args.format}"
    print(f"{out}  —  {W}x{H}, effet {effect}, {n} {unit} @ {duration} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
