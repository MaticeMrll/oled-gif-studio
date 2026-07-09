"""Push d'une animation directement sur l'OLED d'un périphérique SteelSeries.

Utilise l'API locale GameSense (SteelSeries GG / Engine). Le serveur HTTP local
publie son adresse dans ``coreProps.json`` ; on enregistre un « jeu », on lie un
événement d'écran, puis on réémet l'image frame par frame (l'image d'un handler
d'écran est statique — pour animer, on ré-lie l'événement à chaque frame, ce que
font les projets de streaming vidéo sur ces écrans).

Nécessite ``requests`` (``pip install oledgifstudio[push]``) et SteelSeries GG
lancé. Le format d'image attendu est identique à l'export C-array : 1 bit/pixel,
row-major, MSB en tête — on réutilise donc le packing de ``export``.
"""

import json
import os
import time

from .export import _bits, _pack_row_major

GAME_ID = "OLEDGIFSTUDIO"
GAME_NAME = "OLED GIF Studio"
DEVELOPER = "MaticeMrll"

# Emplacements connus du fichier de découverte de l'adresse du serveur local.
_COREPROPS = [
    os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                 "SteelSeries", "SteelSeries Engine 3", "coreProps.json"),
    os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                 "SteelSeries", "GG", "coreProps.json"),
    "/Library/Application Support/SteelSeries Engine 3/coreProps.json",  # macOS
]


class PushError(RuntimeError):
    pass


def find_address():
    """Adresse `host:port` du serveur GameSense, ou lève PushError."""
    override = os.environ.get("OLEDGIF_GAMESENSE_ADDRESS")
    if override:
        return override
    for path in _COREPROPS:
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                continue
            addr = data.get("address")
            if addr:
                return addr
    raise PushError(
        "SteelSeries GameSense introuvable (coreProps.json absent). "
        "Vérifie que SteelSeries GG est lancé, ou force l'adresse via la "
        "variable d'environnement OLEDGIF_GAMESENSE_ADDRESS (ex. 127.0.0.1:49721)."
    )


def _pack(frame, w, h, invert):
    rows = _pack_row_major(_bits(frame, invert), w, h, "big")
    return list(b"".join(rows))


def _screen_handler(w, h, image_data):
    return {
        "device-type": f"screened-{w}x{h}",
        "mode": "screen",
        "zone": "one",
        "datas": [{"has-text": False, "image-data": image_data}],
    }


def push_animation(frames, w, h, fps=15, loops=0, invert=False,
                   durations=None, address=None):
    """Joue l'animation sur l'écran du périphérique.

    loops=0 => boucle jusqu'à Ctrl-C. Retourne le nombre de frames envoyées.
    """
    try:
        import requests
    except ImportError as exc:  # pragma: no cover
        raise PushError(
            "le push nécessite `requests` : pip install oledgifstudio[push]"
        ) from exc

    address = address or find_address()
    base = f"http://{address}"
    sess = requests.Session()

    def post(route, payload):
        r = sess.post(base + route, json=payload, timeout=3)
        if r.status_code >= 400:
            raise PushError(f"{route} -> {r.status_code}: {r.text[:200]}")
        return r

    post("/game_metadata", {
        "game": GAME_ID, "game_display_name": GAME_NAME, "developer": DEVELOPER,
    })

    packed = [_pack(f, w, h, invert) for f in frames]
    if durations and isinstance(durations, list):
        delays = [max(0.0, d / 1000.0) for d in durations]
    else:
        delays = [1.0 / max(1, fps)] * len(frames)

    sent = 0
    try:
        loop = 0
        while loops == 0 or loop < loops:
            for i, data in enumerate(packed):
                post("/bind_game_event", {
                    "game": GAME_ID, "event": "FRAME",
                    "min_value": 0, "max_value": 100, "icon_id": 0,
                    "handlers": [_screen_handler(w, h, data)],
                })
                post("/game_event", {
                    "game": GAME_ID, "event": "FRAME",
                    "data": {"value": (sent % 100) + 1},
                })
                sent += 1
                time.sleep(delays[i])
            loop += 1
    finally:
        try:
            post("/remove_game", {"game": GAME_ID})
        except Exception:  # nettoyage best-effort
            pass
    return sent
