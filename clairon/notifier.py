"""Confier une `Alerte` à Clairon.app — sans l'attendre : l'agent n'est jamais ralenti."""
from __future__ import annotations

import os
import subprocess

from .etats import SONS, Alerte, langue, rediger

APPLICATION = os.path.expanduser("~/Applications/Clairon.app")
BINAIRE = os.path.join(APPLICATION, "Contents/MacOS/Clairon")
RESSOURCES = os.path.join(APPLICATION, "Contents/Resources")
REGLAGES = os.path.expanduser("~/.config/clairon")

#: Les applications qui savent recevoir un DOSSIER (elles ramènent la fenêtre
#: du projet) ; un terminal, lui, est seulement ramené au premier plan.
EDITEURS = {"com.microsoft.VSCode", "com.todesktop.230313mt0l1oxb"}


def interrupteur(nom: str) -> bool:
    """`pause` coupe tout, `sans-son` rend muet : un simple fichier dans ~/.config/clairon."""
    return os.path.exists(os.path.join(REGLAGES, nom))


def effacer() -> None:
    """Retire du centre de notifications toutes celles de Clairon."""
    if os.access(BINAIRE, os.X_OK):
        subprocess.run([BINAIRE, "--effacer", "tout"], check=False)


def envoyer(alerte: Alerte, attendre: bool = False) -> bool:
    """Publie l'alerte. Faux si Clairon est en pause ou n'est pas installé."""
    if interrupteur("pause") or not os.access(BINAIRE, os.X_OK):
        return False
    titre, texte = rediger(alerte, langue())
    projet = os.path.basename(alerte.dossier.rstrip("/")) or alerte.agent
    son = "aucun" if interrupteur("sans-son") else SONS[alerte.etat] + ".aiff"
    commande = [
        BINAIRE,
        "--titre", titre,
        "--sous-titre", projet,
        "--texte", texte,
        "--son", son,
        "--fil", projet,
        "--id", alerte.session or projet,
        "--vignette", os.path.join(RESSOURCES, f"etat-{alerte.etat}.png"),
        "--ouvrir", alerte.application,
        "--dossier", alerte.dossier if alerte.application in EDITEURS else "",
    ]
    processus = subprocess.Popen(
        commande, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=None if attendre else subprocess.DEVNULL, start_new_session=not attendre,
    )
    if attendre:
        processus.wait(timeout=120)
    return True
