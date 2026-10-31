// Clairon — les notifications natives des agents de code sur le Mac.
//
//   Clairon --titre "Claude a terminé" --sous-titre "mon-projet" --texte "…" \
//           --son Glass.aiff --fil mon-projet --id <session> \
//           --vignette …/etat-termine.png \
//           --ouvrir com.microsoft.VSCode --dossier /chemin/du/projet
//   Clairon --effacer tout      retire du centre toutes ses notifications
//
// Sans `--titre`, Clairon a été lancé par un CLIC sur une de ses notifications :
// il ramène l'application de travail (l'éditeur sur le dossier du projet, ou
// le terminal), puis se ferme. Il ne reste jamais en mémoire, n'a pas d'icône
// dans le Dock et ne lit rien d'autre que ses arguments.
import AppKit
import UserNotifications

final class Clairon: NSObject, NSApplicationDelegate, UNUserNotificationCenterDelegate {
    private var options: [String: String] = [:]

    func applicationDidFinishLaunching(_ note: Notification) {
        options = Self.lire(CommandLine.arguments)
        let centre = UNUserNotificationCenter.current()
        centre.delegate = self
        if options["effacer"] != nil {
            centre.removeAllDeliveredNotifications()
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { NSApp.terminate(nil) }
            return
        }
        guard options["titre"] != nil else {
            // Lancé par un clic : le centre appelle `didReceive` ; sinon, on part.
            DispatchQueue.main.asyncAfter(deadline: .now() + 8) { NSApp.terminate(nil) }
            return
        }
        centre.requestAuthorization(options: [.alert, .sound]) { autorise, erreur in
            guard autorise else {
                // Visible quand on lance Clairon à la main : la raison d'un refus.
                Self.signaler("notifications refusées (\(erreur.map { "\($0)" } ?? "réglage macOS"))")
                DispatchQueue.main.async { NSApp.terminate(nil) }
                return
            }
            self.publier(dans: centre)
        }
    }

    private func publier(dans centre: UNUserNotificationCenter) {
        let contenu = UNMutableNotificationContent()
        contenu.title = options["titre"] ?? "Clairon"
        if let s = options["sous-titre"], !s.isEmpty { contenu.subtitle = s }
        if let t = options["texte"], !t.isEmpty { contenu.body = t }
        if let son = options["son"], !son.isEmpty, son != "aucun" {
            // Les sons sont DANS l'application (Contents/Resources) : c'est là
            // que le centre de notifications les cherche.
            contenu.sound = UNNotificationSound(named: UNNotificationSoundName(son))
        }
        // Le fil regroupe les notifications d'un même projet dans le centre.
        contenu.threadIdentifier = options["fil"] ?? "clairon"
        contenu.userInfo = ["ouvrir": options["ouvrir"] ?? "", "dossier": options["dossier"] ?? ""]
        contenu.interruptionLevel = .active
        if let chemin = options["vignette"], let piece = Self.piece(chemin) {
            contenu.attachments = [piece]
        }
        // Même identifiant pour une même session : la nouvelle notification
        // REMPLACE la précédente au lieu de s'empiler.
        let requete = UNNotificationRequest(
            identifier: options["id"] ?? UUID().uuidString, content: contenu, trigger: nil)
        centre.add(requete) { erreur in
            if let erreur { Self.signaler("\(erreur)") }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { NSApp.terminate(nil) }
        }
    }

    /// La vignette est COPIÉE : le centre de notifications DÉPLACE le fichier reçu.
    private static func piece(_ chemin: String) -> UNNotificationAttachment? {
        let source = URL(fileURLWithPath: chemin)
        let copie = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString + "-" + source.lastPathComponent)
        guard (try? FileManager.default.copyItem(at: source, to: copie)) != nil else { return nil }
        return try? UNNotificationAttachment(identifier: "etat", url: copie)
    }

    /// Un clic : l'application de travail. Un éditeur reçoit le dossier du
    /// projet (il ramène la fenêtre déjà ouverte dessus) ; un terminal est
    /// simplement ramené au premier plan.
    func userNotificationCenter(
        _ c: UNUserNotificationCenter, didReceive r: UNNotificationResponse,
        withCompletionHandler fin: @escaping () -> Void
    ) {
        let infos = r.notification.request.content.userInfo
        let appli = infos["ouvrir"] as? String ?? ""
        let dossier = infos["dossier"] as? String ?? ""
        let finir = { DispatchQueue.main.async { fin(); NSApp.terminate(nil) } }
        guard !appli.isEmpty, let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: appli) else {
            finir()
            return
        }
        let reglages = NSWorkspace.OpenConfiguration()
        reglages.activates = true
        if !dossier.isEmpty, FileManager.default.fileExists(atPath: dossier) {
            NSWorkspace.shared.open([URL(fileURLWithPath: dossier)], withApplicationAt: url, configuration: reglages) { _, _ in finir() }
        } else {
            NSWorkspace.shared.openApplication(at: url, configuration: reglages) { _, _ in finir() }
        }
    }

    func userNotificationCenter(
        _ c: UNUserNotificationCenter, willPresent n: UNNotification,
        withCompletionHandler fin: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        fin([.banner, .list, .sound])
    }

    private static func signaler(_ texte: String) {
        FileHandle.standardError.write(Data("Clairon : \(texte)\n".utf8))
    }

    private static func lire(_ args: [String]) -> [String: String] {
        var resultat: [String: String] = [:]
        var i = 1
        while i < args.count {
            let a = args[i]
            if a.hasPrefix("--"), i + 1 < args.count {
                resultat[String(a.dropFirst(2))] = args[i + 1]
                i += 2
            } else {
                i += 1
            }
        }
        return resultat
    }
}

let application = NSApplication.shared
let clairon = Clairon()
application.delegate = clairon
application.setActivationPolicy(.accessory)
application.run()
