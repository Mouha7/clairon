"""Les adaptateurs : l'événement d'un agent → une `Alerte` commune.

Un adaptateur par agent, et rien d'autre ne connaît la forme de ses
événements. Ajouter un agent, c'est écrire une fonction ici et l'inscrire dans
`ADAPTATEURS` — le reste de Clairon ne change pas.

Version 0.1 : Claude Code seulement (hooks `Notification`, `Stop`,
`StopFailure`, https://code.claude.com/docs/en/hooks).
"""
from __future__ import annotations

import json
import os
import re
from typing import Callable, Optional

from .etats import Alerte

#: `TERM_PROGRAM` (ou l'éditeur détecté) → l'application à ramener au clic.
APPLICATIONS = {
    "vscode": "com.microsoft.VSCode",
    "cursor": "com.todesktop.230313mt0l1oxb",
    "iTerm.app": "com.googlecode.iterm2",
    "Apple_Terminal": "com.apple.Terminal",
    "ghostty": "com.mitchellh.ghostty",
    "WarpTerminal": "dev.warp.Warp-Stable",
}


def application_de_travail(environnement: dict) -> str:
    """L'application où tourne l'agent, d'après son environnement.

    `CLAIRON_APP` l'impose ; sinon `TERM_PROGRAM`, que posent les terminaux
    et les éditeurs. Vide quand on ne sait pas : le clic ne fera rien plutôt
    que d'ouvrir la mauvaise application.
    """
    imposee = environnement.get("CLAIRON_APP", "")
    if imposee:
        return imposee
    programme = environnement.get("TERM_PROGRAM", "")
    if programme == "vscode" and "CURSOR_TRACE_ID" in environnement:
        return APPLICATIONS["cursor"]
    return APPLICATIONS.get(programme, "")


# ─── Claude Code ─────────────────────────────────────────────────────────────

#: `notification_type` de Claude Code → état commun
TYPES_CLAUDE = {
    "permission_prompt": "autorisation",
    "idle_prompt": "attente",
    "elicitation_dialog": "question",
    "auth_success": "connexion",
}


def derniere_reponse(evenement: dict) -> str:
    """Le dernier texte de Claude : fourni par l'événement, sinon lu à la fin du transcript.

    La fin d'un transcript peut n'être faite que de captures d'écran (des
    centaines de Ko chacune) : on élargit la fenêtre tant qu'on n'a rien trouvé.
    """
    direct = evenement.get("last_assistant_message")
    if isinstance(direct, str) and direct.strip():
        return direct
    chemin = evenement.get("transcript_path") or ""
    for fenetre in (512_000, 4_000_000, 16_000_000):
        try:
            with open(chemin, "rb") as f:
                f.seek(0, os.SEEK_END)
                taille = f.tell()
                f.seek(max(0, taille - fenetre))
                lignes = f.read().decode("utf-8", "ignore").splitlines()
        except OSError:
            return ""
        for ligne in reversed(lignes):
            try:
                entree = json.loads(ligne)
            except ValueError:
                continue  # la première ligne lue peut être tronquée
            if entree.get("type") != "assistant":
                continue
            contenu = (entree.get("message") or {}).get("content") or []
            textes = [b.get("text", "") for b in contenu if isinstance(b, dict) and b.get("type") == "text"]
            if any(t.strip() for t in textes):
                return "\n".join(textes)
        if fenetre >= taille:
            break
    return ""


def outil_demande(message: str) -> str:
    """« Claude needs your permission to use Bash » → « Bash »."""
    trouve = re.search(r"permission to use (.+?)\.?$", message or "")
    return trouve.group(1) if trouve else ""


def claude_code(evenement: dict, environnement: dict) -> Optional[Alerte]:
    from .resume import resumer

    nom = evenement.get("hook_event_name", "")
    message = (evenement.get("message") or "").strip()
    commun = {
        "agent": "Claude",
        "dossier": evenement.get("cwd") or "",
        "session": evenement.get("session_id") or "",
        "application": application_de_travail(environnement),
    }
    if nom == "Stop":
        return Alerte(etat="termine", texte=resumer(derniere_reponse(evenement)), **commun)
    if nom == "StopFailure":
        erreur = evenement.get("error")
        if isinstance(erreur, dict):
            erreur = erreur.get("message") or erreur.get("type")
        return Alerte(etat="erreur", texte=resumer(str(erreur or message or "")), **commun)
    if nom == "Notification":
        etat = TYPES_CLAUDE.get(evenement.get("notification_type", ""), "")
        if etat == "autorisation":
            # Seul le NOM de l'outil passe : la phrase (« Pour utiliser : Bash »)
            # se rédige dans la langue choisie (`etats.rediger`).
            return Alerte(etat=etat, texte="", outil=outil_demande(message), **commun)
        if etat == "attente":
            return Alerte(etat=etat, texte="", **commun)
        if etat:
            return Alerte(etat=etat, texte=resumer(message), **commun)
        # Un type que Clairon ne connaît pas encore : montré tel quel.
        return Alerte(etat="attente", texte=resumer(message), **commun)
    return None


#: agent → adaptateur
ADAPTATEURS: dict[str, Callable[[dict, dict], Optional[Alerte]]] = {
    "claude-code": claude_code,
}
