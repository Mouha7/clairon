# Journal des versions

## 0.1.0 — 2026-10-31

Première version.

- **Une application macOS native** (`UserNotifications`) : icône originale, une vignette et un son pour chacun des six états (terminé, autorisation, attente, question, connexion, erreur).
- **L'adaptateur Claude Code** : hooks `Notification`, `Stop` et `StopFailure`, en arrière-plan. Pour « terminé », l'aperçu reprend la première phrase de la réponse.
- **Le rangement** : un groupe par projet, et une notification par session, la nouvelle remplaçant l'ancienne.
- **Le clic** ramène l'outil de travail : VS Code ou Cursor sur le dossier du projet, ou le terminal (iTerm2, Terminal, Ghostty, Warp).
- **Les textes**, en français et en anglais.
- **Les commandes** : `clairon install`, qui fusionne les réglages de Claude Code après les avoir sauvegardés, `clairon uninstall`, `clairon test` et `clairon effacer`.
- **L'installation par Homebrew** : `brew install mouha7/tap/clairon`, puis `clairon install`, qui construit l'application sur la machine.
