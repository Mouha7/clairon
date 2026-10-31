"""Construire Clairon.app, et (dé)brancher les hooks de Claude Code.

Les réglages de Claude Code (`~/.claude/settings.json`) sont FUSIONNÉS, jamais
remplacés : on ajoute nos hooks à côté de ceux qui existent, on ne retire que
les nôtres, et une copie datée du fichier est gardée avant toute écriture.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from .notifier import APPLICATION

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGLAGES_CLAUDE = os.path.expanduser("~/.claude/settings.json")
EVENEMENTS_CLAUDE = ("Notification", "Stop", "StopFailure")
SONS = ("Glass", "Ping", "Pop", "Purr", "Hero", "Basso")
LSREGISTER = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/"
              "LaunchServices.framework/Support/lsregister")

INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key><string>io.github.mouha7.clairon</string>
  <key>CFBundleName</key><string>Clairon</string>
  <key>CFBundleDisplayName</key><string>Clairon</string>
  <key>CFBundleExecutable</key><string>Clairon</string>
  <key>CFBundleIconFile</key><string>Clairon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>{version}</string>
  <key>CFBundleVersion</key><string>{version}</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>LSUIElement</key><true/>
  <key>NSHumanReadableCopyright</key><string>MIT</string>
</dict>
</plist>
"""


def _lancer(*commande: str) -> None:
    subprocess.run(list(commande), check=True, stdout=subprocess.DEVNULL)


def construire(version: str) -> str:
    """Construit Clairon.app dans ~/Applications ; rend son chemin."""
    with tempfile.TemporaryDirectory() as travail:
        images = os.path.join(travail, "images")
        _lancer("/usr/bin/swift", os.path.join(RACINE, "outils/fabrique.swift"), images)
        jeu = os.path.join(travail, "Clairon.iconset")
        os.mkdir(jeu)
        source = os.path.join(images, "icone-1024.png")
        for t in (16, 32, 128, 256, 512):
            _lancer("/usr/bin/sips", "-z", str(t), str(t), source, "--out", f"{jeu}/icon_{t}x{t}.png")
            _lancer("/usr/bin/sips", "-z", str(2 * t), str(2 * t), source, "--out", f"{jeu}/icon_{t}x{t}@2x.png")
        icone = os.path.join(travail, "Clairon.icns")
        _lancer("/usr/bin/iconutil", "-c", "icns", jeu, "-o", icone)
        binaire = os.path.join(travail, "Clairon")
        _lancer("/usr/bin/swiftc", "-O", "-swift-version", "5", "-o", binaire,
                os.path.join(RACINE, "app/Clairon.swift"))

        shutil.rmtree(APPLICATION, ignore_errors=True)
        ressources = os.path.join(APPLICATION, "Contents/Resources")
        os.makedirs(os.path.join(APPLICATION, "Contents/MacOS"))
        os.makedirs(ressources)
        shutil.copy(binaire, os.path.join(APPLICATION, "Contents/MacOS/Clairon"))
        shutil.copy(icone, ressources)
        for nom in os.listdir(images):
            if nom.startswith("etat-"):
                shutil.copy(os.path.join(images, nom), ressources)
        # Les sons voyagent DANS l'application : c'est là que le centre de
        # notifications les cherche.
        for son in SONS:
            shutil.copy(f"/System/Library/Sounds/{son}.aiff", ressources)
        with open(os.path.join(APPLICATION, "Contents/Info.plist"), "w", encoding="utf-8") as f:
            f.write(INFO_PLIST.format(version=version))
    _lancer("/usr/bin/codesign", "--force", "--deep", "--sign", "-", APPLICATION)
    _lancer(LSREGISTER, "-f", APPLICATION)
    return APPLICATION


def racine_stable(racine: str = RACINE) -> str:
    """Le dossier à écrire dans les hooks : il doit survivre aux mises à jour.

    Installé par Homebrew, le code vit dans `…/Cellar/clairon/<version>/`, qui
    disparaît à la version suivante ; `…/opt/clairon/` suit toujours la
    version courante.
    """
    return re.sub(r"/Cellar/clairon/[^/]+/", "/opt/clairon/", racine + "/").rstrip("/")


def commande_du_hook() -> str:
    return f'"{os.path.join(racine_stable(), "bin/clairon")}" hook claude-code'


def _est_a_nous(hook: dict) -> bool:
    """Nos hooks, y compris ceux d'une installation antérieure."""
    commande = hook.get("command", "")
    return "clairon" in commande.lower()


def _lire_reglages() -> dict:
    try:
        with open(REGLAGES_CLAUDE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _ecrire_reglages(reglages: dict) -> str:
    """Écrit les réglages après en avoir gardé une copie datée ; rend le chemin de la copie."""
    copie = ""
    if os.path.exists(REGLAGES_CLAUDE):
        copie = f"{REGLAGES_CLAUDE}.avant-clairon-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(REGLAGES_CLAUDE, copie)
    os.makedirs(os.path.dirname(REGLAGES_CLAUDE), exist_ok=True)
    with open(REGLAGES_CLAUDE, "w", encoding="utf-8") as f:
        f.write(json.dumps(reglages, ensure_ascii=False, indent=2) + "\n")
    return copie


def retirer_nos_hooks(reglages: dict) -> dict:
    hooks = reglages.get("hooks") or {}
    for evenement in list(hooks):
        blocs = []
        for bloc in hooks[evenement]:
            bloc = dict(bloc, hooks=[h for h in bloc.get("hooks", []) if not _est_a_nous(h)])
            if bloc["hooks"]:
                blocs.append(bloc)
        if blocs:
            hooks[evenement] = blocs
        else:
            del hooks[evenement]
    if hooks:
        reglages["hooks"] = hooks
    else:
        reglages.pop("hooks", None)
    return reglages


def brancher_claude_code() -> str:
    """Ajoute les trois hooks de Clairon (en arrière-plan) ; rend le chemin de la copie."""
    reglages = retirer_nos_hooks(_lire_reglages())
    hooks = reglages.setdefault("hooks", {})
    notre = {"type": "command", "command": commande_du_hook(), "timeout": 10, "async": True}
    for evenement in EVENEMENTS_CLAUDE:
        bloc = {"hooks": [dict(notre)]}
        if evenement == "Notification":
            bloc = {"matcher": "", **bloc}
        hooks.setdefault(evenement, []).append(bloc)
    return _ecrire_reglages(reglages)


def debrancher_claude_code() -> str:
    return _ecrire_reglages(retirer_nos_hooks(_lire_reglages()))
