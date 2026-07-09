"""Serveur HTTP local (stdlib uniquement) exposant l'API JSON d'oledgif.

Aucune dépendance web (pas de Flask) : http.server + threading + json.
Écoute uniquement sur 127.0.0.1 (jamais 0.0.0.0).
"""

import base64
import binascii
import json
import os
import re
import socket
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler

from .. import __version__
from ..cli import CHARSETS, build_frames
from ..describe import parse as parse_description
from ..effects import DESCRIPTIONS
from ..export import EXT, to_c_array, to_xbm
from ..patterns import PATTERNS
from ..presets import DEFAULT_PRESET, PRESETS
from ..push import PushError, find_address, push_animation
from ..render import save_gif

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}

_EXT_FROM_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}

_PLACEHOLDER_HTML = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>oledgif</title></head>
<body style="font-family: sans-serif; background:#111; color:#eee; padding:2rem">
<h1>oledgif — Frontend en cours de generation</h1>
<p>Le serveur backend tourne. Les fichiers statiques
(<code>oledgif/web/static/index.html</code>) ne sont pas encore presents.</p>
<p>L'API JSON est disponible sous <code>/api/*</code>
(voir <a href="/api/meta" style="color:#8cf">/api/meta</a>).</p>
</body></html>
"""

# ---------------------------------------------------------------- push state

_push_lock = threading.Lock()
_push_state = {
    "thread": None,
    "stop_event": None,
    "sent": 0,
    "error": None,
    "running": False,
    "address": None,
}


def _push_status_snapshot():
    with _push_lock:
        return {
            "ok": True,
            "running": _push_state["running"],
            "sent": _push_state["sent"],
            "error": _push_state["error"],
            "address": _push_state["address"],
        }


# ---------------------------------------------------------------- helpers

def find_free_port(start=8100, attempts=50):
    """Renvoie le premier port TCP libre sur 127.0.0.1 à partir de `start`."""
    port = start
    for _ in range(attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                port += 1
                continue
            return port
    raise RuntimeError("aucun port TCP libre trouve sur 127.0.0.1")


def _content_type(path):
    ext = os.path.splitext(path)[1].lower()
    return _MIME.get(ext, "application/octet-stream")


def _meta():
    return {
        "ok": True,
        "version": __version__,
        "default_preset": DEFAULT_PRESET,
        "presets": [{"name": name, "w": w, "h": h, "desc": desc}
                    for name, (w, h, desc) in PRESETS.items()],
        "effects": [{"name": name, "desc": desc,
                     "textless": (name in PATTERNS) or (name == "matrix")}
                    for name, desc in DESCRIPTIONS.items()],
        "charsets": ["alnum", "digits", "upper", "letters", "ascii"],
        "styles": ["photo", "solid", "comic", "edges"],
        "fits": ["contain", "cover"],
    }


def _var_name(text):
    var = "".join(c if c.isalnum() else "_" for c in (text or "")).strip("_")
    var = var or "oledgif"
    if var[0].isdigit():
        var = "img_" + var
    return var


def _decode_data_url_to_temp(data_url):
    """Décode une dataURL base64 (data:image/...;base64,XXXX) vers un fichier temp."""
    if not isinstance(data_url, str) or not data_url.startswith("data:"):
        raise ValueError("image: dataURL attendue (data:image/...;base64,...)")
    header, _, b64data = data_url.partition(",")
    if not b64data:
        raise ValueError("image: dataURL vide")
    mime = "image/png"
    m = re.match(r"data:([^;,]+)", header)
    if m:
        mime = m.group(1)
    ext = _EXT_FROM_MIME.get(mime, ".png")
    try:
        raw = base64.b64decode(b64data)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"image: base64 invalide ({exc})")
    if not raw:
        raise ValueError("image: contenu decode vide")
    fd, path = tempfile.mkstemp(suffix=ext, prefix="oledgif_web_")
    with os.fdopen(fd, "wb") as fh:
        fh.write(raw)
    return path


def _build(body):
    """Résout les paramètres communs generate/export/push et construit les frames.

    Retourne un dict {frames, durations, effect, w, h, fps, text}.
    Lève ValueError/SystemExit (message clair) en cas d'entrée invalide.
    """
    text = body.get("text")
    describe = body.get("describe")
    effect = body.get("effect") or "auto"
    fps = int(body.get("fps") or 15)
    seconds = float(body.get("seconds") or 4.0)

    if describe and effect == "auto":
        parsed = parse_description(describe)
        if "text" in parsed:
            text = parsed["text"]
        if "effect" in parsed:
            effect = parsed["effect"]
        if "fps" in parsed:
            fps = parsed["fps"]
        if "seconds" in parsed:
            seconds = parsed["seconds"]

    image = body.get("image")
    textless_ok = bool(image) or effect in PATTERNS or effect == "matrix"
    if not text and not textless_ok:
        raise ValueError(
            "Aucun texte : passe `text`, une `describe` avec du texte entre "
            "guillemets, une `image`, ou choisis un effet motif (starfield, "
            "plasma, life, eq, scope, radar, fire, snow, fireworks, spiral, "
            "tunnel, clock, matrix)."
        )

    charset_key = body.get("charset", "alnum")
    charset = CHARSETS.get(charset_key, charset_key)

    speed = body.get("speed")
    speed = float(speed) if speed is not None else None
    font_size = body.get("font_size")
    font_size = int(font_size) if font_size is not None else None
    seed = body.get("seed")
    seed = int(seed) if seed is not None else None

    tmp_image_path = None
    try:
        if image:
            tmp_image_path = _decode_data_url_to_temp(image)
        frames, durations, effect, W, H = build_frames(
            text,
            preset=body.get("preset"),
            size=body.get("size"),
            effect=effect,
            fps=fps,
            seconds=seconds,
            speed=speed,
            font_path=body.get("font_path"),
            font_size=font_size,
            charset=charset,
            seed=seed,
            image=tmp_image_path,
            style=body.get("style", "photo"),
            fit=body.get("fit", "contain"),
            denoise=bool(body.get("denoise", True)),
        )
    finally:
        if tmp_image_path:
            try:
                os.unlink(tmp_image_path)
            except OSError:
                pass

    return {
        "frames": frames, "durations": durations, "effect": effect,
        "w": W, "h": H, "fps": fps, "text": text,
    }


# ---------------------------------------------------------------- HTTP handler

class Handler(BaseHTTPRequestHandler):
    server_version = f"oledgif-web/{__version__}"
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002 - signature imposée par la stdlib
        pass  # silencieux : évite de polluer la console pendant l'usage normal

    # -- réponses -----------------------------------------------------

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _html(self, status, html_text):
        body = html_text.encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _bytes(self, status, data, content_type):
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"JSON invalide: {exc}")
        if not isinstance(data, dict):
            raise ValueError("le corps JSON doit être un objet")
        return data

    # -- routage --------------------------------------------------------

    def do_GET(self):
        try:
            path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            if path == "/":
                self._serve_index()
            elif path == "/api/meta":
                self._json(200, _meta())
            elif path == "/api/push/status":
                self._json(200, _push_status_snapshot())
            elif path.startswith("/static/"):
                self._serve_static(path[len("/static/"):])
            else:
                self._json(404, {"ok": False, "error": f"route inconnue: {path}"})
        except Exception as exc:  # ceinture et bretelles : jamais de 500 nue
            self._json(500, {"ok": False, "error": str(exc)})

    def do_POST(self):
        try:
            path = urllib.parse.urlsplit(self.path).path
            if path == "/api/generate":
                self._handle_generate(self._read_json())
            elif path == "/api/export":
                self._handle_export(self._read_json())
            elif path == "/api/push":
                self._handle_push(self._read_json())
            elif path == "/api/push/stop":
                self._handle_push_stop()
            else:
                self._json(404, {"ok": False, "error": f"route inconnue: {path}"})
        except Exception as exc:
            self._json(500, {"ok": False, "error": str(exc)})

    # -- statique ---------------------------------------------------------

    def _serve_index(self):
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            with open(index_path, "rb") as fh:
                self._bytes(200, fh.read(), "text/html; charset=utf-8")
        else:
            self._html(200, _PLACEHOLDER_HTML)

    def _serve_static(self, rel_path):
        rel_path = rel_path.lstrip("/")
        if not rel_path or ".." in rel_path.replace("\\", "/").split("/"):
            self._json(400, {"ok": False, "error": "chemin invalide"})
            return
        static_root = os.path.normpath(STATIC_DIR)
        full = os.path.normpath(os.path.join(static_root, rel_path))
        if full != static_root and not full.startswith(static_root + os.sep):
            self._json(403, {"ok": False, "error": "accès refusé"})
            return
        if not os.path.isfile(full):
            self._json(404, {"ok": False, "error": "fichier introuvable"})
            return
        with open(full, "rb") as fh:
            data = fh.read()
        self._bytes(200, data, _content_type(full))

    # -- API : génération / export ---------------------------------------

    def _handle_generate(self, body):
        try:
            built = _build(body)
        except (SystemExit, Exception) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return

        fd, tmp_path = tempfile.mkstemp(suffix=".gif", prefix="oledgif_web_")
        os.close(fd)
        try:
            n, duration = save_gif(
                built["frames"], tmp_path, fps=built["fps"],
                invert=bool(body.get("invert", False)),
                scale=int(body.get("scale") or 1),
                durations=built["durations"],
            )
            with open(tmp_path, "rb") as fh:
                data = fh.read()
        except (SystemExit, Exception) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        gif_b64 = base64.b64encode(data).decode("ascii")
        self._json(200, {
            "ok": True,
            "gif": f"data:image/gif;base64,{gif_b64}",
            "effect": built["effect"],
            "w": built["w"],
            "h": built["h"],
            "frames": n,
            "duration": duration,
        })

    def _handle_export(self, body):
        fmt = body.get("format")
        if fmt not in ("c-array", "xbm"):
            self._json(400, {"ok": False,
                              "error": f"format d'export invalide: {fmt!r} "
                                       "(attendu c-array|xbm)"})
            return
        try:
            built = _build(body)
        except (SystemExit, Exception) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return

        invert = bool(body.get("invert", False))
        var = _var_name(built["text"])
        try:
            if fmt == "c-array":
                durs = built["durations"] if isinstance(built["durations"], list) \
                    else max(20, round(1000 / built["fps"]))
                content = to_c_array(built["frames"], built["w"], built["h"], durs,
                                     var=var, invert=invert)
            else:
                content = to_xbm(built["frames"][0], built["w"], built["h"],
                                 name=var, invert=invert)
        except (SystemExit, Exception) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return

        self._json(200, {
            "ok": True,
            "filename": var + EXT[fmt],
            "content": content,
            "mime": "text/plain",
        })

    # -- API : push ---------------------------------------------------------

    def _handle_push(self, body):
        try:
            built = _build(body)
        except (SystemExit, Exception) as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return

        loops = int(body.get("loops") or 0)
        invert = bool(body.get("invert", False))

        # arrête un push déjà en cours, s'il y en a un
        with _push_lock:
            old_thread = _push_state["thread"]
            old_stop = _push_state["stop_event"]
            was_running = _push_state["running"]
        if was_running and old_stop is not None:
            old_stop.set()
            if old_thread is not None:
                old_thread.join(timeout=5)

        try:
            address = find_address()
        except PushError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return

        stop_event = threading.Event()
        frames, durations, w, h, fps = (
            built["frames"], built["durations"], built["w"], built["h"], built["fps"])

        def _run():
            sent, error = 0, None
            try:
                sent = push_animation(
                    frames, w, h, fps=fps, loops=loops, invert=invert,
                    durations=durations, address=address,
                    should_stop=stop_event.is_set,
                )
            except PushError as exc:
                error = str(exc)
            except Exception as exc:  # ne doit jamais faire planter le thread silencieusement
                error = str(exc)
            with _push_lock:
                _push_state["sent"] = sent
                _push_state["error"] = error
                _push_state["running"] = False

        thread = threading.Thread(target=_run, daemon=True)
        with _push_lock:
            _push_state.update({
                "thread": thread, "stop_event": stop_event,
                "sent": 0, "error": None, "running": True, "address": address,
            })
        thread.start()

        self._json(200, {"ok": True, "running": True, "address": address})

    def _handle_push_stop(self):
        with _push_lock:
            stop_event = _push_state["stop_event"]
            if stop_event is not None:
                stop_event.set()
        self._json(200, {"ok": True, "stopped": True})
