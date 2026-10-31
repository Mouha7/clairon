"""Les états communs à tous les agents, et leurs textes.

Un adaptateur (voir `adaptateurs.py`) traduit l'événement propre à un agent en
l'un de ces six états ; la suite — titre, son, vignette — ne dépend plus de
l'agent. Les textes existent en français et en anglais ; la langue suit celle
du système, ou `CLAIRON_LANG` (`fr` ou `en`).
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

#: état → son (fichier `.aiff` livré dans l'application)
SONS = {
    "termine": "Glass",
    "autorisation": "Ping",
    "attente": "Pop",
    "question": "Purr",
    "connexion": "Hero",
    "erreur": "Basso",
}

TEXTES = {
    "fr": {
        "termine": ("{agent} a terminé", "La réponse est prête."),
        "autorisation": ("{agent} attend ton autorisation", "Une autorisation est demandée."),
        "attente": ("{agent} attend ta réponse", "Il t'a répondu ; la suite dépend de toi."),
        "question": ("{agent} te pose une question", "Une question t'attend."),
        "connexion": ("Connexion réussie", "{agent} est connecté."),
        "erreur": ("{agent} s'est arrêté sur une erreur",
                   "Le tour s'est interrompu : limite d'usage, réseau ou serveur."),
        "outil": "Pour utiliser : {outil}",
    },
    "en": {
        "termine": ("{agent} is done", "The answer is ready."),
        "autorisation": ("{agent} needs your permission", "A permission is requested."),
        "attente": ("{agent} is waiting for you", "It replied; the next step is yours."),
        "question": ("{agent} has a question for you", "A question is waiting."),
        "connexion": ("Signed in", "{agent} is signed in."),
        "erreur": ("{agent} stopped on an error",
                   "The turn was interrupted: usage limit, network or server."),
        "outil": "To use: {outil}",
    },
}


@dataclass(frozen=True)
class Alerte:
    """Ce qu'un adaptateur rend : de quoi rédiger UNE notification."""

    etat: str
    agent: str
    #: Le détail ; vide → le texte par défaut de l'état.
    texte: str
    #: Le dossier de travail (le projet).
    dossier: str
    #: Une alerte par session : la nouvelle remplace l'ancienne.
    session: str
    #: L'application à ramener au clic (identifiant de bundle), vide sinon.
    application: str = ""
    #: L'outil pour lequel une autorisation est demandée (« Bash »), vide sinon.
    outil: str = ""


def langue() -> str:
    """`fr` ou `en` : `CLAIRON_LANG`, sinon la première langue du système."""
    choisie = os.environ.get("CLAIRON_LANG", "").lower()[:2]
    if choisie in TEXTES:
        return choisie
    try:
        sortie = subprocess.run(
            ["/usr/bin/defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True, timeout=2,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "en"
    for ligne in sortie.splitlines():
        ligne = ligne.strip().strip('",()').lower()
        if ligne:
            return "fr" if ligne.startswith("fr") else "en"
    return "en"


def rediger(alerte: Alerte, code_langue: str) -> tuple[str, str]:
    """(titre, texte) de l'alerte dans cette langue."""
    catalogue = TEXTES.get(code_langue, TEXTES["en"])
    titre, defaut = catalogue[alerte.etat]
    if alerte.outil:
        texte = catalogue["outil"].format(outil=alerte.outil)
    else:
        texte = alerte.texte or defaut.format(agent=alerte.agent)
    return titre.format(agent=alerte.agent), texte
