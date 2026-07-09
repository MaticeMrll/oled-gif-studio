"""Presets d'écrans OLED répandus sur le marché."""

PRESETS = {
    # SteelSeries (GameSense / SteelSeries GG)
    "apex":         (128, 40, "SteelSeries Apex 5 / 7 / Pro — OLED clavier"),
    "rival":        (128, 36, "SteelSeries Rival 700 / 710 — OLED souris"),
    # Modules OLED I2C/SPI courants (Arduino, Raspberry Pi, macropads QMK...)
    "oled-128x64":  (128, 64, "SSD1306 / SH1106 / SSD1309 128x64"),
    "oled-128x32":  (128, 32, "SSD1306 128x32"),
    "oled-96x16":   (96, 16, "SSD1306 96x16"),
    "oled-256x64":  (256, 64, "SSD1322 256x64"),
}

DEFAULT_PRESET = "apex"


def resolve_size(preset: str | None, size: str | None) -> tuple[int, int]:
    """--size WxH prime sur --preset ; sinon preset (défaut: apex)."""
    if size:
        try:
            w, h = size.lower().split("x")
            return int(w), int(h)
        except ValueError:
            raise SystemExit(f"--size invalide: {size!r} (attendu: LARGEURxHAUTEUR, ex. 128x40)")
    name = preset or DEFAULT_PRESET
    if name not in PRESETS:
        raise SystemExit(f"Preset inconnu: {name!r}. Presets: {', '.join(PRESETS)}")
    w, h, _ = PRESETS[name]
    return w, h
