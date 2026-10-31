"""Le cœur de Clairon : événement → état → texte, et les réglages fusionnés sans perte.

    python3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest
from unittest import mock

from clairon import installation
from clairon.adaptateurs import application_de_travail, claude_code, derniere_reponse, outil_demande
from clairon.etats import Alerte, rediger
from clairon.resume import resumer

ENV_VSCODE = {"TERM_PROGRAM": "vscode"}


def evenement(**champs):
    base = {"cwd": "/tmp/mon-projet", "session_id": "s-1"}
    base.update(champs)
    return base


class LesEtats(unittest.TestCase):
    def test_chaque_evenement_de_claude_code_donne_son_etat(self):
        cas = [
            (evenement(hook_event_name="Stop", last_assistant_message="Fini."), "termine"),
            (evenement(hook_event_name="StopFailure", error={"message": "Limite atteinte"}), "erreur"),
            (evenement(hook_event_name="Notification", notification_type="permission_prompt",
                       message="Claude needs your permission to use Bash"), "autorisation"),
            (evenement(hook_event_name="Notification", notification_type="idle_prompt"), "attente"),
            (evenement(hook_event_name="Notification", notification_type="elicitation_dialog",
                       message="Quel port ?"), "question"),
            (evenement(hook_event_name="Notification", notification_type="auth_success"), "connexion"),
        ]
        for donnee, attendu in cas:
            with self.subTest(attendu):
                self.assertEqual(claude_code(donnee, ENV_VSCODE).etat, attendu)

    def test_un_type_inconnu_reste_visible_et_un_evenement_etranger_est_ignore(self):
        alerte = claude_code(evenement(hook_event_name="Notification", notification_type="nouveau",
                                       message="Quelque chose de neuf"), {})
        self.assertEqual((alerte.etat, alerte.texte), ("attente", "Quelque chose de neuf"))
        self.assertIsNone(claude_code(evenement(hook_event_name="PreToolUse"), {}))

    def test_la_session_regroupe_et_le_dossier_suit(self):
        alerte = claude_code(evenement(hook_event_name="Stop", last_assistant_message="Ok."), ENV_VSCODE)
        self.assertEqual((alerte.session, alerte.dossier), ("s-1", "/tmp/mon-projet"))


class LesTextes(unittest.TestCase):
    def test_francais_et_anglais(self):
        alerte = Alerte(etat="autorisation", agent="Claude", texte="", dossier="", session="",
                        outil=outil_demande("Claude needs your permission to use Bash"))
        self.assertEqual(rediger(alerte, "fr"), ("Claude attend ton autorisation", "Pour utiliser : Bash"))
        self.assertEqual(rediger(alerte, "en"), ("Claude needs your permission", "To use: Bash"))

    def test_un_texte_vide_prend_le_texte_par_defaut_de_l_etat(self):
        alerte = Alerte(etat="erreur", agent="Claude", texte="", dossier="", session="")
        self.assertIn("limite d'usage", rediger(alerte, "fr")[1])


class LeResume(unittest.TestCase):
    def test_la_premiere_phrase_utile_sans_balisage(self):
        texte = "## Bilan\n\n```bash\nls\n```\n**V1.56.0 est en production** : voir [le cahier](docs/x.md)."
        # Une vraie phrase passe avant un titre ; le titre seul ne sert qu'à défaut.
        self.assertEqual(resumer(texte), "V1.56.0 est en production : voir le cahier.")
        self.assertEqual(resumer("## Bilan\n\n```\nx\n```"), "Bilan")
        self.assertEqual(resumer("| --- | --- |\n- **Fait** : tout"), "Fait : tout")

    def test_borne_a_un_espace_avec_une_ellipse(self):
        resume = resumer("mot " * 100, limite=30)
        self.assertTrue(resume.endswith("…"))
        self.assertLessEqual(len(resume), 31)

    def test_rien_d_utile(self):
        self.assertEqual(resumer("```\ncode\n```"), "")


class LeTranscript(unittest.TestCase):
    def test_le_dernier_texte_de_l_assistant_meme_derriere_une_ligne_tronquee(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            f.write('{"type": "assistant", "mes')  # une ligne tronquée en tête
            f.write("\n")
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Premier."}]}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use"}]}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Dernier."}]}}) + "\n")
            f.write(json.dumps({"type": "user", "message": {"content": "merci"}}) + "\n")
        try:
            self.assertEqual(derniere_reponse({"transcript_path": f.name}), "Dernier.")
        finally:
            os.unlink(f.name)

    def test_le_champ_direct_passe_avant_le_transcript(self):
        self.assertEqual(derniere_reponse({"last_assistant_message": "Direct.", "transcript_path": "/x"}), "Direct.")


class LApplicationDeTravail(unittest.TestCase):
    def test_editeurs_et_terminaux(self):
        self.assertEqual(application_de_travail({"TERM_PROGRAM": "vscode"}), "com.microsoft.VSCode")
        self.assertEqual(application_de_travail({"TERM_PROGRAM": "vscode", "CURSOR_TRACE_ID": "x"}),
                         "com.todesktop.230313mt0l1oxb")
        self.assertEqual(application_de_travail({"TERM_PROGRAM": "iTerm.app"}), "com.googlecode.iterm2")
        self.assertEqual(application_de_travail({"CLAIRON_APP": "com.exemple"}), "com.exemple")

    def test_inconnue_rien_plutot_que_la_mauvaise(self):
        self.assertEqual(application_de_travail({}), "")


class LesReglages(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.fichier = os.path.join(self.dossier, "settings.json")
        self.patch = mock.patch.object(installation, "REGLAGES_CLAUDE", self.fichier)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def ecrire(self, contenu):
        with open(self.fichier, "w", encoding="utf-8") as f:
            json.dump(contenu, f)

    def lire(self):
        with open(self.fichier, encoding="utf-8") as f:
            return json.load(f)

    def test_brancher_garde_tout_le_reste_et_fait_une_copie(self):
        autre_hook = {"type": "command", "command": "prettier --write"}
        self.ecrire({"theme": "dark", "hooks": {"PostToolUse": [{"matcher": "Edit", "hooks": [autre_hook]}],
                                                "Stop": [{"hooks": [autre_hook]}]}})
        copie = installation.brancher_claude_code()
        reglages = self.lire()
        self.assertTrue(os.path.exists(copie))
        self.assertEqual(reglages["theme"], "dark")
        self.assertEqual(reglages["hooks"]["PostToolUse"][0]["hooks"], [autre_hook])
        # Le hook étranger sur Stop reste, le nôtre s'ajoute à côté.
        commandes = [h["command"] for bloc in reglages["hooks"]["Stop"] for h in bloc["hooks"]]
        self.assertIn("prettier --write", commandes)
        self.assertTrue(any("bin/clairon" in c for c in commandes))
        for evenement in installation.EVENEMENTS_CLAUDE:
            self.assertIn(evenement, reglages["hooks"])

    def test_brancher_deux_fois_ne_double_rien_et_remplace_une_ancienne_installation(self):
        self.ecrire({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/x/.claude/clairon/clairon.py"}]}]}})
        installation.brancher_claude_code()
        installation.brancher_claude_code()
        commandes = [h["command"] for bloc in self.lire()["hooks"]["Stop"] for h in bloc["hooks"]]
        self.assertEqual(len(commandes), 1)
        self.assertIn("bin/clairon", commandes[0])

    def test_installe_par_homebrew_le_hook_survit_aux_mises_a_jour(self):
        self.assertEqual(installation.racine_stable("/opt/homebrew/Cellar/clairon/0.1.0/libexec"),
                         "/opt/homebrew/opt/clairon/libexec")
        self.assertEqual(installation.racine_stable("/Users/x/.clairon"), "/Users/x/.clairon")

    def test_debrancher_ne_retire_que_les_notres(self):
        autre = {"type": "command", "command": "prettier --write"}
        self.ecrire({"hooks": {"Stop": [{"hooks": [autre]}]}})
        installation.brancher_claude_code()
        installation.debrancher_claude_code()
        self.assertEqual(self.lire()["hooks"], {"Stop": [{"hooks": [autre]}]})


if __name__ == "__main__":
    unittest.main()
