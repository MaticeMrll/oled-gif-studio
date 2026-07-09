# oled-gif-studio

*[Read in English](README.md)*

<p align="center">
  <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/hero.gif" width="384" alt="OLED GIF STUDIO qui défile sur un écran 128x40">
</p>

Générateur de GIFs animés **1 bit** pour les écrans OLED **de toutes tailles** :
claviers/souris SteelSeries, modules SSD1306/SH1106 (Arduino, Raspberry Pi,
macropads QMK), ou n'importe quelle résolution custom. Choisis un preset ou fixe
ta propre taille `LARGEURxHAUTEUR` — tout le pipeline est indépendant de la
résolution, d'une barrette 96×16 à un panneau 256×64.

Pas de modèle IA, pas d'API payante : tout est **procédural** (Python + Pillow),
donc instantané, gratuit et pixel-perfect. Un mode « description en langage
naturel » (français ou anglais) choisit l'effet et les paramètres pour toi.

Tu peux aussi **exporter les frames en tableau C** (`--format c-array`) pour les
flasher sur un SSD1306 Arduino/QMK, ou les **envoyer en direct** sur un écran
OLED SteelSeries (`--push`). `pip install oledgifstudio[fast]` ajoute NumPy pour
accélérer nettement les effets lourds (optionnel — fallback pur Python sinon).

> Tous les aperçus de ce README sont agrandis ×3 — la taille réelle des GIFs
> est celle de l'écran cible (128×40 par défaut).

## Installation

Aucune, si Python (≥ 3.10) + Pillow sont déjà installés. Sinon :

```
pip install Pillow
```

Optionnel, pour avoir la commande `oledgif` partout :

```
pip install -e .
```

Extras optionnels : `pip install -e .[fast]` (NumPy — accélère `plasma`,
`tunnel`, le tramage d'images) et `pip install -e .[push]` (`requests` — requis
pour `--push`). `.[dev]` installe tout, plus `pytest`.

## Usage rapide

```powershell
# Depuis le dossier du projet :
python -m oledgif "HELLO WORLD"                          # effet auto → hello.gif
python -m oledgif "GG" -e slot -o gg.gif                 # machine à sous
python -m oledgif "PWNED" -e glitch -p rival             # pour l'OLED d'une souris
python -m oledgif "42" -e matrix --size 128x64 --fps 20  # taille custom

# En langage naturel :
python -m oledgif -d "le texte 'BONJOUR' défile lentement"
python -m oledgif -d "'GAME OVER' qui clignote vite pendant 3s"
python -m oledgif -d "un radar qui balaie l'écran"

# À partir d'une image :
python -m oledgif -i photo.jpg --fit cover               # photo plein écran, effet vhs
python -m oledgif -i comic.jpg --fit cover --style comic # illustration/BD
python -m oledgif -i logo.png -e bounce                  # le logo rebondit
python -m oledgif -i meme.gif                            # GIF animé converti tel quel

# Motifs sans texte (écrans de veille) :
python -m oledgif -e starfield
python -m oledgif -e plasma --seconds 6
python -m oledgif -e fire                                # flammes qui montent
python -m oledgif -e tunnel                              # tunnel en damier
python -m oledgif -e clock                               # horloge numérique

# N'importe quelle résolution — pas seulement les presets :
python -m oledgif "HELLO" --size 200x64
python -m oledgif "HI" -e wave --size 100x24

# Export pour microcontrôleur (Arduino / QMK / SSD1306) :
python -m oledgif "GG" -e blink -f c-array -o logo.h     # header C, drawBitmap()
python -m oledgif -i logo.png -f xbm -o logo.xbm         # X BitMap

# Push direct sur un OLED SteelSeries (GameSense, en live) :
python -m oledgif -e clock --push                        # boucle jusqu'à Ctrl-C
python -m oledgif "GG WP" -e slot --push --loops 3

# Un exemple de chaque effet dans ./samples :
python -m oledgif --demo
```

## Interface web

Tu préfères cliquer plutôt que taper ? Une interface web locale expose **tout** ce
que fait la CLI — chaque effet et motif, la description en langage naturel,
l'import d'image, n'importe quelle taille d'écran, l'export C-array/XBM et le push
live sur un OLED SteelSeries — avec un aperçu OLED réaliste qui se met à jour au
fil des réglages.

```powershell
python -m oledgif.web        # lance un serveur local et ouvre le navigateur
# ou, une fois installé :  oledgif-web
```

Elle tourne **100 % en local** avec **zéro dépendance supplémentaire** (uniquement
la bibliothèque standard de Python — pas de Flask, pas de CDN, rien ne sort de ta
machine). Ajoute `--no-browser` pour ne pas ouvrir le navigateur, ou `--port 9000`
pour choisir un port. Le push live nécessite toujours SteelSeries GG lancé et
`requests` (`pip install oledgifstudio[push]`).

## Effets texte / image (`--list-effects`)

<table>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/scroll.gif" alt="scroll"><br><code>scroll</code> — défilement en boucle parfaite</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/typewriter.gif" alt="typewriter"><br><code>typewriter</code> — machine à écrire avec curseur</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/wave.gif" alt="wave"><br><code>wave</code> — lettres en vague</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/blink.gif" alt="blink"><br><code>blink</code> — clignotement</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/bounce.gif" alt="bounce"><br><code>bounce</code> — rebond façon logo DVD</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/matrix.gif" alt="matrix"><br><code>matrix</code> — pluie de caractères qui révèle le texte</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/slot.gif" alt="slot"><br><code>slot</code> — chaque lettre cycle puis se fige</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/glitch.gif" alt="glitch"><br><code>glitch</code> — bandes décalées + bruit</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/pulse.gif" alt="pulse"><br><code>pulse</code> — battement de cœur</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/vhs.gif" alt="vhs"><br><code>vhs</code> — tracking façon cassette vidéo</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/slide.gif" alt="slide"><br><code>slide</code> — générique bas → haut</td>
<td></td>
</tr>
</table>

`typewriter`, `wave`, `matrix` et `slot` sont réservés au texte ; les autres
acceptent aussi une image (`--image`).

`--effect auto` (défaut) : `scroll` si le texte est trop large pour l'écran,
sinon `wave` ; `vhs` pour une image ; conversion directe pour un GIF animé.

## Motifs sans texte (écrans de veille)

<table>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/starfield.gif" alt="starfield"><br><code>starfield</code> — hyperespace</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/plasma.gif" alt="plasma"><br><code>plasma</code> — plasma rétro tramé</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/life.gif" alt="life"><br><code>life</code> — jeu de la vie de Conway</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/eq.gif" alt="eq"><br><code>eq</code> — égaliseur audio</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/scope.gif" alt="scope"><br><code>scope</code> — oscilloscope</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/radar.gif" alt="radar"><br><code>radar</code> — balayage avec échos</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/fire.gif" alt="fire"><br><code>fire</code> — flammes tramées qui montent</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/snow.gif" alt="snow"><br><code>snow</code> — neige qui tombe et s'accumule</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/fireworks.gif" alt="fireworks"><br><code>fireworks</code> — fusées qui explosent en gerbes</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/spiral.gif" alt="spiral"><br><code>spiral</code> — spirale hypnotique en rotation</td>
</tr>
<tr>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/tunnel.gif" alt="tunnel"><br><code>tunnel</code> — tunnel damier en profondeur</td>
<td align="center"><img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/clock.gif" alt="clock"><br><code>clock</code> — horloge numérique qui égrène</td>
</tr>
</table>

## Images : les 4 styles de rendu

Convertir une image couleur en 1 bit sur 5120 pixels est un exercice de
sacrifice — le bon `--style` dépend de la source. Démonstration sur la même
scène (lune, silhouettes sur ciel en dégradé, lumières de ville) :

| Rendu | Style |
|---|---|
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_source.png" alt="source" width="288"> | **Source** (niveaux de gris) |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_photo.png" alt="photo" width="288"> | `--style photo` (défaut) — auto-contraste + netteté + trame Floyd-Steinberg. Le bon choix pour les **photos réelles** : la trame simule les niveaux de gris. Sur une illustration, elle devient du bruit. |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_solid.png" alt="solid" width="288"> | `--style solid` — seuillage net (alias `--no-dither`). Parfait pour les **logos** et dessins au trait… mais tout ce qui est sombre-sur-sombre disparaît dans le noir. |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_comic.png" alt="comic" width="288"> | `--style comic` — comme `solid`, mais un 2ᵉ seuil automatique (Otsu) sépare les tons sombres et retrace en **contour blanc** les formes noyées dans le noir. Idéal pour les **illustrations/BD**. |
| <img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/style_edges.png" alt="edges" width="288"> | `--style edges` — détection de contours, traits blancs sur fond noir. Look néon/filaire, souvent le plus lisible pour un **paysage ou un visage**. |

Autres options d'image :

- `--fit cover` — l'image remplit tout l'écran (recadrée) au lieu d'être
  réduite à un timbre-poste au milieu. Recommandé pour les photos paysage.
- **Dé-bruitage** (actif par défaut) : un filtre médian + une suppression des
  pixels isolés éliminent le « poivre et sel » (reflets, lampadaires, étoiles).
  `--no-denoise` le désactive si tu veux justement garder ces points.
- Un **GIF animé** en entrée est converti frame par frame en conservant les
  durées d'origine (avec `--effect auto`).

## Langage naturel (`--describe`)

```powershell
python -m oledgif -d "le texte 'BRB' qui rebondit pendant 5 secondes"
python -m oledgif -d "'REC' en mode vhs vintage"
python -m oledgif -d "a fast blinking 'GO' for 3 seconds"
```

Le parseur (FR/EN, insensible aux accents) reconnaît l'effet par mots-clés
(« défile », « clignote », « tape », « radar », « vintage »…), le texte entre
guillemets, la durée (« pendant 3s ») et la vitesse (« lentement », « vite »).

## Écrans préconfigurés (`--list-presets`)

| Preset        | Taille  | Matériel |
|---------------|---------|----------|
| `apex` (défaut) | 128×40 | SteelSeries Apex 5 / 7 / Pro (OLED clavier) |
| `rival`       | 128×36  | SteelSeries Rival 700 / 710 (OLED souris) |
| `oled-128x64` | 128×64  | SSD1306 / SH1106 / SSD1309 |
| `oled-128x32` | 128×32  | SSD1306 |
| `oled-96x16`  | 96×16   | SSD1306 |
| `oled-256x64` | 256×64  | SSD1322 |

N'importe quelle autre taille : `--size LARGEURxHAUTEUR`.

## Options utiles

- `--charset alnum|digits|upper|letters|ascii` ou une chaîne littérale — le
  jeu de caractères utilisé par `matrix` et `slot` (défaut : les 62
  alphanumériques `0-9A-Za-z`).
- `--font chemin.ttf --font-size N` — police custom (défaut : Consolas,
  taille ajustée à l'écran).
- `--invert` — noir sur blanc.
- `--scale 4` — GIF agrandi ×4 (pour prévisualiser confortablement).
- `--seed 42` — rendu reproductible pour les effets aléatoires.
- `--fps`, `--seconds`, `--speed` (px/s pour scroll).
- `--format gif|c-array|xbm` — type de sortie (voir la section export).
- `--push [--loops N]` — envoi en direct sur un OLED SteelSeries au lieu d'un fichier.

## Export pour microcontrôleur (`--format c-array` / `xbm`)

Au-delà du GIF, tu peux exporter les frames en code source pour les afficher sur
un OLED nu (SSD1306/SH1106) piloté par un Arduino, un ESP32 ou un clavier QMK :

```powershell
python -m oledgif "GG" -e blink -p oled-128x32 -f c-array -o logo.h
python -m oledgif -i logo.png -f xbm -o logo.xbm
```

- **`c-array`** → un header C avec `const uint8_t frames[N][octets] PROGMEM`
  (1 bit/pixel, packing horizontal, MSB en tête — la convention Adafruit_GFX /
  U8g2). Il émet aussi `_WIDTH`, `_HEIGHT`, `_FRAMES` et une table
  `_durations[]`. Il suffit de l'inclure et d'animer :

  ```cpp
  #include "logo.h"
  for (uint8_t i = 0; i < GG_FRAMES; i++) {
      display.clearDisplay();
      display.drawBitmap(0, 0, gg_frames[i], GG_WIDTH, GG_HEIGHT, 1);
      display.display();
      delay(gg_durations[i]);
  }
  ```

- **`xbm`** → un X BitMap standard (1re frame), lisible par la plupart des outils.

## Envoyer l'animation sur un écran SteelSeries

Trois options, de la plus simple à la plus manuelle :

1. **Push en direct (`--push`)** — envoie l'animation directement sur l'OLED du
   clavier/souris via l'API GameSense locale de SteelSeries GG, sans fichier :

   ```powershell
   python -m oledgif -e clock --push            # boucle jusqu'à Ctrl-C
   python -m oledgif "GG WP" -e slot --push --loops 3
   ```

   SteelSeries GG doit tourner. L'adresse du serveur est auto-détectée depuis
   `coreProps.json` ; force-la via la variable d'environnement
   `OLEDGIF_GAMESENSE_ADDRESS` au besoin. Nécessite `requests`
   (`pip install oledgifstudio[push]`).
2. **Import SteelSeries GG** : dans les réglages OLED de ton périphérique,
   importe le GIF généré — il est déjà en 1 bit à la taille exacte de l'écran.
3. **GameSense API** (ton propre code) : les frames sont directement
   exploitables octet par octet, comme
   [SteelseriesAnimGif](https://github.com/bolner/SteelseriesAnimGif).

## Structure du projet

```
oledgif/
  cli.py        # ligne de commande + build_frames() / make_gif()
  effects.py    # les 11 effets texte/image (registre @effect)
  patterns.py   # les 12 motifs/écrans de veille sans texte
  render.py     # préparation d'images, binarisation, écriture GIF (chemins NumPy)
  export.py     # export C-array / XBM pour microcontrôleur
  push.py       # push en direct sur un OLED SteelSeries (API GameSense)
  describe.py   # parseur langage naturel FR/EN
  presets.py    # tailles d'écrans du marché
  fonts.py      # chargement de police
  web/          # interface web locale (http.server stdlib + SPA JS vanilla)
tests/          # suite pytest
samples/        # un GIF d'exemple par effet (taille réelle, --demo)
docs/           # illustrations du README (agrandies ×3)
```
--- 
## Mon choix

<img src="https://raw.githubusercontent.com/MaticeMrll/oled-gif-studio/main/docs/keyboard.jpg" alt="source" width="288">

Ninja Turtles !
