"""Une phrase lisible tirée d'une réponse en Markdown — l'aperçu de « terminé »."""
from __future__ import annotations

import re


def _nettoyer(ligne: str) -> str:
    ligne = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ligne)  # [lien](cible) → lien
    ligne = re.sub(r"[*_`#>|]+", "", ligne)
    ligne = re.sub(r"^\s*(?:[-•]|\d+[.)])\s+", "", ligne)
    return re.sub(r"\s+", " ", ligne).strip()


def _utile(ligne: str) -> bool:
    return len(ligne) >= 3 and not re.fullmatch(r"[-:\s]+", ligne)


def resumer(texte: str, limite: int = 170) -> str:
    """La première phrase utile d'un texte Markdown, sans balisage, bornée.

    Les blocs de code sont sautés, les liens gardent leur libellé, les puces
    perdent leurs marques, et une ligne de tableau vide (`|---|`) ne compte pas.
    Une vraie phrase passe avant un TITRE (« ## Bilan » n'apprend rien) ; le
    titre ne sert que s'il n'y a rien d'autre. Au-delà de `limite`, on coupe à
    un espace et on termine par « … ».
    """
    texte = re.sub(r"```.*?```", " ", texte or "", flags=re.S)
    titre = ""
    choisie = ""
    for brute in texte.splitlines():
        ligne = _nettoyer(brute)
        if not _utile(ligne):
            continue
        if brute.lstrip().startswith("#"):
            titre = titre or ligne
            continue
        choisie = ligne
        break
    choisie = choisie or titre
    if len(choisie) <= limite:
        return choisie
    coupe = choisie[:limite].rsplit(" ", 1)[0].rstrip(",;:")
    return coupe + "…"
