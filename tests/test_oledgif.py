"""Suite de tests oled-gif-studio.

Couvre : rendu des effets, équivalence numpy/pur-Python, export C-array/XBM
(round-trip), parsing langage naturel, presets et garde-fous.
"""

import os

import pytest
from PIL import Image

from oledgif import export, patterns, render
from oledgif.cli import build_frames, make_gif
from oledgif.describe import parse
from oledgif.effects import EFFECTS
from oledgif.presets import resolve_size

W, H = 64, 32


# ------------------------------------------------------------------ effets

@pytest.mark.parametrize("name", sorted(EFFECTS))
def test_effect_produit_frames_valides(name):
    frames, _, effect, w, h = build_frames(
        "GG42", effect=name, size=f"{W}x{H}", fps=6, seconds=1, seed=1)
    assert effect == name
    assert len(frames) >= 2
    for f in frames:
        assert f.size == (W, H)
        assert f.mode == "L"


def test_auto_choisit_scroll_si_large():
    _, _, effect, *_ = build_frames("texte vraiment tres large" * 2,
                                    effect="auto", size="64x16", fps=6, seconds=1)
    assert effect == "scroll"


# ------------------------------------------------- équivalence numpy / python

@pytest.mark.skipif(render.np is None, reason="numpy absent")
def test_despeckle_numpy_egal_python():
    img = Image.new("L", (40, 20), 0)
    px = img.load()
    import random
    r = random.Random(1)
    for _ in range(120):
        px[r.randrange(40), r.randrange(20)] = 255
    a = render._despeckle_np(img)
    np_bak = render.np
    render.np = None
    try:
        b = render._despeckle(img)
    finally:
        render.np = np_bak
    assert list(a.getdata()) == list(b.getdata())


@pytest.mark.skipif(patterns.np is None, reason="numpy absent")
def test_plasma_numpy_egal_python():
    from oledgif.effects import Ctx
    ctx = Ctx(text="", W=32, H=16, fps=5, seconds=1)
    a = patterns._plasma_np(ctx)
    np_bak = patterns.np
    patterns.np = None
    try:
        b = patterns.plasma(ctx)
    finally:
        patterns.np = np_bak
    assert all(list(x.getdata()) == list(y.getdata()) for x, y in zip(a, b))


# ------------------------------------------------------------------ export

def _decode_c_array(text):
    """Extrait (w, h, nframes, frames_bytes) d'un header généré."""
    import re
    w = int(re.search(r"_WIDTH\s+(\d+)", text).group(1))
    h = int(re.search(r"_HEIGHT\s+(\d+)", text).group(1))
    n = int(re.search(r"_FRAMES\s+(\d+)", text).group(1))
    body = text.split("_frames", 1)[1].split("{", 1)[1]
    body = body.rsplit("};", 1)[0]
    hexes = re.findall(r"0x[0-9A-Fa-f]{2}", body)
    data = bytes(int(x, 16) for x in hexes)
    return w, h, n, data


def test_c_array_round_trip():
    frame = Image.new("L", (16, 8), 0)
    frame.paste(255, (0, 0, 4, 4))  # coin haut-gauche allumé
    text = export.to_c_array([frame], 16, 8, 100, var="t")
    w, h, n, data = _decode_c_array(text)
    assert (w, h, n) == (16, 8, 1)
    assert len(data) == (16 // 8) * 8  # 2 octets/ligne * 8 lignes
    # ligne 0 : 4 pixels allumés en tête => 0xF0 0x00
    assert data[0] == 0xF0 and data[1] == 0x00
    # ligne 5 (hors du carré) => éteinte
    assert data[10] == 0x00 and data[11] == 0x00


def test_xbm_lisible_par_pillow(tmp_path):
    frame = Image.new("L", (16, 8), 0)
    frame.paste(255, (2, 2, 10, 6))
    path = tmp_path / "t.xbm"
    export.save_export([frame], str(path), "xbm", 16, 8, 100)
    reloaded = Image.open(path).convert("1")
    assert reloaded.size == (16, 8)
    expected = render.binarize(frame)
    assert list(reloaded.getdata()) == list(expected.getdata())


def test_make_gif_ecrit_fichier(tmp_path):
    out = tmp_path / "x.gif"
    path, effect, w, h, n, dur = make_gif("HI", str(out), size="64x16",
                                          effect="wave", fps=6, seconds=1)
    assert os.path.isfile(path)
    assert n >= 2 and (w, h) == (64, 16)


def test_make_gif_cree_dossier_manquant(tmp_path):
    out = tmp_path / "sub" / "dir" / "x.gif"
    make_gif("HI", str(out), size="64x16", effect="blink", fps=4, seconds=1)
    assert out.is_file()


def test_save_gif_vide_leve():
    with pytest.raises(ValueError):
        render.save_gif([], "x.gif", fps=10)


# ------------------------------------------------------------------ describe

@pytest.mark.parametrize("phrase,attendu", [
    ("un feu qui monte", "fire"),
    ("feux d artifice", "fireworks"),
    ("de la neige qui tombe", "snow"),
    ("une spirale hypnotique", "spiral"),
    ("affiche l heure", "clock"),
    ("GG qui defile vite", "scroll"),
    ("texte qui clignote", "blink"),
])
def test_describe_effet(phrase, attendu):
    assert parse(phrase).get("effect") == attendu


def test_describe_texte_et_vitesse():
    out = parse('affiche "GG WP" rapidement pendant 3 secondes')
    assert out["text"] == "GG WP"
    assert out["fps"] == 25
    assert out["seconds"] == 3.0


# ------------------------------------------------------------------ presets

def test_resolve_size():
    assert resolve_size("apex", None) == (128, 40)
    assert resolve_size(None, "200x50") == (200, 50)


def test_resolve_size_invalide():
    with pytest.raises(SystemExit):
        resolve_size(None, "pas-une-taille")
