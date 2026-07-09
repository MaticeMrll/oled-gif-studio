"""Export des frames binaires vers des formats exploitables sur microcontrôleur.

- ``c-array`` : header C ``const uint8_t[N][bytes] PROGMEM`` compatible
  ``display.drawBitmap()`` (Adafruit_GFX / U8g2), packing horizontal MSB en tête,
  lignes alignées sur l'octet. Idéal SSD1306 / SH1106 sur Arduino, ESP32, QMK.
- ``xbm``    : X BitMap standard (packing horizontal LSB en tête), une frame.

`invert` inverse les bits (pixel allumé <-> éteint) selon la polarité de l'écran.
"""

import os

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

from .render import binarize

FORMATS = {"gif", "c-array", "xbm"}
EXT = {"gif": ".gif", "c-array": ".h", "xbm": ".xbm"}


def _bits(frame, invert=False):
    """Frame -> tableau H x W de 0/1 (1 = pixel allumé)."""
    b = binarize(frame, invert)  # mode "1", 0/255
    if np is not None:
        return (np.asarray(b, dtype=np.uint8) > 0).astype(np.uint8)
    w, h = b.size
    px = b.load()
    return [[1 if px[x, y] else 0 for x in range(w)] for y in range(h)]


def _pack_row_major(bits, w, h, bitorder="big"):
    """Empaquète les bits en octets, ligne par ligne, alignés sur l'octet."""
    if np is not None:
        packed = np.packbits(np.asarray(bits, dtype=np.uint8), axis=1,
                             bitorder="little" if bitorder == "little" else "big")
        return [bytes(row) for row in packed]
    row_bytes = (w + 7) // 8
    rows = []
    for y in range(h):
        buf = bytearray(row_bytes)
        for x in range(w):
            if bits[y][x]:
                if bitorder == "little":
                    buf[x >> 3] |= 1 << (x & 7)
                else:
                    buf[x >> 3] |= 0x80 >> (x & 7)
        rows.append(bytes(buf))
    return rows


def _hex_bytes(data, per_line=16, indent="  "):
    out, line = [], []
    for i, byte in enumerate(data):
        line.append(f"0x{byte:02X}")
        if len(line) == per_line or i == len(data) - 1:
            out.append(indent + ", ".join(line) + ",")
            line = []
    return "\n".join(out)


def to_c_array(frames, w, h, durations, var="oledgif", invert=False):
    """Retourne le texte d'un header C animé (voir docstring module)."""
    row_bytes = (w + 7) // 8
    frame_bytes = row_bytes * h
    n = len(frames)
    packed = []
    for f in frames:
        rows = _pack_row_major(_bits(f, invert), w, h, "big")
        packed.append(b"".join(rows))

    lines = [
        "// Généré par oled-gif-studio — https://github.com/MaticeMrll/oled-gif-studio",
        f"// {w}x{h}, {n} frame(s). Usage Adafruit_GFX / U8g2 :",
        f"//   display.drawBitmap(0, 0, {var}_frames[i], "
        f"{var.upper()}_WIDTH, {var.upper()}_HEIGHT, 1);",
        "#pragma once",
        "#include <stdint.h>",
        "#ifdef __AVR__",
        "  #include <avr/pgmspace.h>",
        "#elif !defined(PROGMEM)",
        "  #define PROGMEM",
        "#endif",
        "",
        f"#define {var.upper()}_WIDTH  {w}",
        f"#define {var.upper()}_HEIGHT {h}",
        f"#define {var.upper()}_FRAMES {n}",
        f"#define {var.upper()}_FRAME_BYTES {frame_bytes}",
        "",
        f"const uint8_t {var}_frames[{n}][{frame_bytes}] PROGMEM = {{",
    ]
    for i, data in enumerate(packed):
        lines.append("  {")
        lines.append(_hex_bytes(data, indent="    "))
        lines.append("  }," if i < n - 1 else "  }")
    lines.append("};")
    lines.append("")

    durs = durations if isinstance(durations, list) else [durations] * n
    lines.append(f"const uint16_t {var}_durations[{n}] PROGMEM = {{")
    lines.append(_hex_int(durs))
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def _hex_int(values, per_line=12, indent="  "):
    out, line = [], []
    for i, v in enumerate(values):
        line.append(str(int(v)))
        if len(line) == per_line or i == len(values) - 1:
            out.append(indent + ", ".join(line) + ",")
            line = []
    return "\n".join(out)


def to_xbm(frame, w, h, name="oledgif", invert=False):
    """Retourne le texte d'un fichier XBM (une frame, packing LSB horizontal)."""
    rows = _pack_row_major(_bits(frame, invert), w, h, "little")
    data = b"".join(rows)
    lines = [
        f"#define {name}_width {w}",
        f"#define {name}_height {h}",
        f"static unsigned char {name}_bits[] = {{",
        _hex_bytes(data),
        "};",
        "",
    ]
    return "\n".join(lines)


def save_export(frames, path, fmt, w, h, durations, invert=False):
    """Écrit `frames` (images "L") vers `path` selon `fmt` (c-array|xbm).

    Retourne (path, n_frames). Le format `gif` est géré par render.save_gif.
    """
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    var = "".join(c if c.isalnum() else "_"
                  for c in os.path.splitext(os.path.basename(path))[0]).strip("_")
    var = var or "oledgif"
    if var[0].isdigit():
        var = "img_" + var
    if fmt == "c-array":
        text = to_c_array(frames, w, h, durations, var=var, invert=invert)
    elif fmt == "xbm":
        # XBM ne gère qu'une image : la première frame
        text = to_xbm(frames[0], w, h, name=var, invert=invert)
    else:
        raise ValueError(f"format d'export inconnu: {fmt!r}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path, len(frames)
