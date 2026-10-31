"""La commande `clairon`.

    clairon install      construit Clairon.app et branche les hooks de Claude Code
    clairon uninstall    débranche les hooks et retire Clairon.app
    clairon test         envoie une notification de chaque état
    clairon effacer      retire du centre toutes les notifications de Clairon
    clairon hook <agent> lit un événement JSON sur l'entrée standard (appelé par l'agent)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

from . import __version__
from .adaptateurs import ADAPTATEURS, application_de_travail
from .etats import SONS, Alerte
from .installation import brancher_claude_code, construire, debrancher_claude_code
from .notifier import APPLICATION, effacer, envoyer


def hook(agent: str) -> int:
    adaptateur = ADAPTATEURS.get(agent)
    if adaptateur is None:
        return 0  # un agent inconnu ne doit jamais faire échouer l'agent
    try:
        evenement = json.load(sys.stdin)
    except ValueError:
        return 0
    alerte = adaptateur(evenement, dict(os.environ))
    if alerte is not None:
        envoyer(alerte)
    return 0


def tester() -> int:
    dossier = os.getcwd()
    application = application_de_travail(dict(os.environ))
    exemples = {
        "termine": "Les tests passent : 42 réussis, aucun échec.",
        "autorisation": "",
        "attente": "",
        "question": "Quelle base de données faut-il utiliser pour ce service ?",
        "connexion": "",
        "erreur": "Limite d'usage atteinte, reprise dans 12 minutes.",
    }
    for etat in SONS:
        envoyer(Alerte(etat=etat, agent="Claude", texte=exemples[etat], dossier=dossier,
                       session=f"clairon-test-{etat}", application=application,
                       outil="Bash" if etat == "autorisation" else ""), attendre=True)
        time.sleep(0.6)
    return 0


def installer() -> int:
    print("Clairon", __version__)
    print("→ construction de l'application…")
    print("  ", construire(__version__))
    copie = brancher_claude_code()
    print("→ hooks de Claude Code branchés : Notification, Stop, StopFailure")
    if copie:
        print("   copie de tes réglages :", copie)
    print("→ notification de bienvenue (à la première, macOS demande l'autorisation)")
    envoyer(Alerte(etat="termine", agent="Claude", texte="Clairon est prêt.",
                   dossier=os.getcwd(), session="clairon-bienvenue",
                   application=application_de_travail(dict(os.environ))), attendre=True)
    return 0


def desinstaller() -> int:
    copie = debrancher_claude_code()
    shutil.rmtree(APPLICATION, ignore_errors=True)
    print("Clairon retiré.", f"Copie de tes réglages : {copie}" if copie else "")
    return 0


def main(arguments: list[str]) -> int:
    if not arguments or arguments[0] in ("-h", "--help", "aide"):
        print(__doc__)
        return 0
    commande = arguments[0]
    if commande == "hook":
        return hook(arguments[1] if len(arguments) > 1 else "claude-code")
    if commande == "install":
        return installer()
    if commande == "uninstall":
        return desinstaller()
    if commande == "test":
        return tester()
    if commande in ("effacer", "clear"):
        effacer()
        return 0
    if commande in ("--version", "version"):
        print(__version__)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
