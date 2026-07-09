"""Mode langage naturel (FR/EN) : une phrase -> effet + paramètres.

Pas de modèle IA : simple correspondance de mots-clés, instantané et gratuit.
"""

import re
import unicodedata

KEYWORDS = {
    "scroll":     ["defile", "defilant", "scroll", "marquee", "bandeau", "glisse a gauche"],
    "typewriter": ["machine a ecrire", "typewriter", "tape", "frappe", "ecrit lettre"],
    "wave":       ["vague", "wave", "ondule", "ondulation", "flotte"],
    "blink":      ["clignote", "clignotant", "blink", "flash", "flashe"],
    "bounce":     ["rebond", "rebondit", "bounce", "dvd"],
    "matrix":     ["matrix", "pluie", "rain", "code qui tombe", "hacker"],
    "slot":       ["slot", "machine a sous", "roulette", "casino", "tirage", "jackpot"],
    "glitch":     ["glitch", "bug", "corrompu", "casse", "parasite"],
    "pulse":      ["pulse", "bat", "battement", "coeur", "respire", "zoom"],
    "slide":      ["slide", "monte", "remonte", "entre par le bas", "générique", "credits"],
    "vhs":        ["vhs", "vintage", "retro", "cassette", "tracking", "analogique", "crt"],
    # motifs sans texte
    "starfield":  ["etoile", "star", "warp", "espace", "hyperespace", "galaxie"],
    "plasma":     ["plasma", "lave", "psychedelique"],
    "life":       ["jeu de la vie", "conway", "cellule", "automate"],
    "eq":         ["egaliseur", "equalizer", "musique", "spectre", "barres audio", "visualiseur"],
    "scope":      ["oscilloscope", "oscillo", "onde", "signal", "sinusoide"],
    "radar":      ["radar", "sonar", "balayage", "echo"],
}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def parse(description: str) -> dict:
    """Retourne {effect, text?, fps?, seconds?} déduits de la phrase."""
    folded = _fold(description)
    out: dict = {}

    # texte entre guillemets : "..." '...' «...» “...”
    m = re.search(r'["\'«“](.+?)["\'»”]', description)
    if m:
        out["text"] = m.group(1)

    for effect, words in KEYWORDS.items():
        if any(w in folded for w in words):
            out["effect"] = effect
            break

    if any(w in folded for w in ("rapide", "vite", "fast", "quick")):
        out["fps"] = 25
    elif any(w in folded for w in ("lent", "lentement", "slow", "doucement")):
        out["fps"] = 10

    m = re.search(r"(\d+(?:[.,]\d+)?)\s*s(?:ec|econdes?)?\b", folded)
    if m:
        out["seconds"] = float(m.group(1).replace(",", "."))

    return out
