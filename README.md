# oled-gif-studio

*[Lire en français](https://github.com/MaticeMrll/oled-gif-studio/blob/main/README.fr.md)*

<p align="center">
  <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/hero.gif" width="384" alt="OLED GIF STUDIO scrolling on a 128x40 screen">
</p>

**1-bit** animated GIF generator for small OLED screens: SteelSeries
keyboards/mice, SSD1306/SH1106 modules (Arduino, Raspberry Pi, QMK
macropads)...

No AI model, no paid API: everything is **procedural** (Python + Pillow), so
it's instant, free, and pixel-perfect. A "natural language description" mode
(French or English) picks the effect and parameters for you.

> All previews in this README are scaled ×3 — the actual GIF size is that of
> the target screen (128×40 by default).

## Installation

None needed if Python (≥ 3.10) + Pillow are already installed. Otherwise:

```
pip install Pillow
```

Optional, to get the `oledgif` command available everywhere:

```
pip install -e .
```

## Quick usage

```powershell
# From the project folder:
python -m oledgif "HELLO WORLD"                          # auto effect → hello.gif
python -m oledgif "GG" -e slot -o gg.gif                 # slot machine
python -m oledgif "PWNED" -e glitch -p rival             # for a mouse's OLED
python -m oledgif "42" -e matrix --size 128x64 --fps 20  # custom size

# In natural language:
python -m oledgif -d "the text 'HELLO' scrolling slowly"
python -m oledgif -d "'GAME OVER' blinking fast for 3s"
python -m oledgif -d "a radar sweeping the screen"

# From an image:
python -m oledgif -i photo.jpg --fit cover               # full-screen photo, vhs effect
python -m oledgif -i comic.jpg --fit cover --style comic # illustration/comic
python -m oledgif -i logo.png -e bounce                  # the logo bounces
python -m oledgif -i meme.gif                            # animated GIF converted as-is

# Text-free patterns (screensavers):
python -m oledgif -e starfield
python -m oledgif -e plasma --seconds 6

# One example of every effect in ./samples:
python -m oledgif --demo
```

## Text / image effects (`--list-effects`)

<table>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/scroll.gif" alt="scroll"><br><code>scroll</code> — perfectly looping scroll</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/typewriter.gif" alt="typewriter"><br><code>typewriter</code> — typewriter with cursor</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/wave.gif" alt="wave"><br><code>wave</code> — letters waving</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/blink.gif" alt="blink"><br><code>blink</code> — blinking</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/bounce.gif" alt="bounce"><br><code>bounce</code> — DVD-logo-style bounce</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/matrix.gif" alt="matrix"><br><code>matrix</code> — character rain revealing the text</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/slot.gif" alt="slot"><br><code>slot</code> — each letter cycles then locks in</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/glitch.gif" alt="glitch"><br><code>glitch</code> — shifted bands + noise</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/pulse.gif" alt="pulse"><br><code>pulse</code> — heartbeat</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/vhs.gif" alt="vhs"><br><code>vhs</code> — VHS tape tracking look</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/slide.gif" alt="slide"><br><code>slide</code> — bottom-to-top credits crawl</td>
<td></td>
</tr>
</table>

`typewriter`, `wave`, `matrix`, and `slot` are text-only; the others also
accept an image (`--image`).

`--effect auto` (default): `scroll` if the text is too wide for the screen,
otherwise `wave`; `vhs` for an image; direct conversion for an animated GIF.

## Text-free patterns (screensavers)

<table>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/starfield.gif" alt="starfield"><br><code>starfield</code> — hyperspace</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/plasma.gif" alt="plasma"><br><code>plasma</code> — retro dithered plasma</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/life.gif" alt="life"><br><code>life</code> — Conway's Game of Life</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/eq.gif" alt="eq"><br><code>eq</code> — audio equalizer</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/scope.gif" alt="scope"><br><code>scope</code> — oscilloscope</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/radar.gif" alt="radar"><br><code>radar</code> — sweep with echoes</td>
</tr>
</table>

## Images: the 4 rendering styles

Converting a color image to 1 bit over 5120 pixels is an exercise in
sacrifice — the right `--style` depends on the source. Demonstrated on the
same scene (moon, silhouettes against a gradient sky, city lights):

| Render | Style |
|---|---|
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_source.png" alt="source" width="288"> | **Source** (grayscale) |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_photo.png" alt="photo" width="288"> | `--style photo` (default) — auto-contrast + sharpening + Floyd-Steinberg dithering. The right choice for **real photos**: the dithering simulates grayscale levels. On an illustration it turns into noise. |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_solid.png" alt="solid" width="288"> | `--style solid` — hard thresholding (alias `--no-dither`). Great for **logos** and line art… but anything dark-on-dark disappears into black. |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_comic.png" alt="comic" width="288"> | `--style comic` — like `solid`, but an automatic 2nd threshold (Otsu) separates dark tones and outlines shapes drowned in black with a **white contour**. Ideal for **illustrations/comics**. |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_edges.png" alt="edges" width="288"> | `--style edges` — edge detection, white lines on black background. Neon/wireframe look, often the most readable for a **landscape or a face**. |

Other image options:

- `--fit cover` — the image fills the whole screen (cropped) instead of being
  shrunk to a stamp in the middle. Recommended for landscape photos.
- **Denoising** (on by default): a median filter plus isolated-pixel removal
  eliminate "salt and pepper" noise (reflections, streetlights, stars).
  `--no-denoise` disables it if you actually want to keep those specks.
- An **animated GIF** input is converted frame by frame, keeping the
  original durations (with `--effect auto`).

## Natural language (`--describe`)

```powershell
python -m oledgif -d "the text 'BRB' bouncing for 5 seconds"
python -m oledgif -d "'REC' in vintage vhs mode"
python -m oledgif -d "un radar qui balaie l'écran"
```

The parser (FR/EN, accent-insensitive) recognizes the effect by keywords
("scrolls", "blinks", "types", "radar", "vintage"...), the text in quotes,
the duration ("for 3s"), and the speed ("slowly", "fast").

## Preconfigured screens (`--list-presets`)

| Preset        | Size    | Hardware |
|---------------|---------|----------|
| `apex` (default) | 128×40 | SteelSeries Apex 5 / 7 / Pro (keyboard OLED) |
| `rival`       | 128×36  | SteelSeries Rival 700 / 710 (mouse OLED) |
| `oled-128x64` | 128×64  | SSD1306 / SH1106 / SSD1309 |
| `oled-128x32` | 128×32  | SSD1306 |
| `oled-96x16`  | 96×16   | SSD1306 |
| `oled-256x64` | 256×64  | SSD1322 |

Any other size: `--size WIDTHxHEIGHT`.

## Useful options

- `--charset alnum|digits|upper|letters|ascii` or a literal string — the
  character set used by `matrix` and `slot` (default: the 62 alphanumeric
  characters `0-9A-Za-z`).
- `--font path.ttf --font-size N` — custom font (default: Consolas, size
  adjusted to the screen).
- `--invert` — black on white.
- `--scale 4` — GIF enlarged ×4 (for comfortable previewing).
- `--seed 42` — reproducible rendering for random effects.
- `--fps`, `--seconds`, `--speed` (px/s for scroll).

## Sending the GIF to a SteelSeries screen

Two options:

1. **SteelSeries GG**: in your keyboard's settings (OLED section), you can
   import a 128×40 image/GIF — the GIFs generated here are already in the
   right format (1 bit, exact size).
2. **GameSense API** (programmatic): like
   [SteelseriesAnimGif](https://github.com/bolner/SteelseriesAnimGif) does,
   you can stream frames to the screen via SteelSeries GG's local API. The
   GIFs produced here are directly usable frame by frame.

## Project structure

```
oledgif/
  cli.py        # command line + make_gif()
  effects.py    # the 11 text/image effects (@effect registry)
  patterns.py   # the 6 text-free patterns
  render.py     # image prep, binarization, GIF writing
  describe.py   # FR/EN natural language parser
  presets.py    # market screen sizes
  fonts.py      # font loading
samples/        # one example GIF per effect (actual size, --demo)
docs/           # README illustrations (scaled ×3)
```
--- 
## My pick

<img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/keyboard.jpg" alt="source" width="288">

Ninja Turtles!
