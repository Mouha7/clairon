// Fabrique les images de Clairon : l'icône de l'application et les vignettes
// d'état. Lancé à l'installation ; rien ne dépend de lui ensuite.
//
//   swift outils/fabrique.swift <dossier-de-sortie>
//
// L'icône est ORIGINALE (un clairon qui sonne, sur une tuile ambre-corail) :
// aucun logo de tiers. Les vignettes utilisent des symboles système, qui ne
// servent qu'à l'intérieur de l'interface, jamais comme icône d'application.
import AppKit

let arguments = CommandLine.arguments
guard arguments.count == 2 else { print("usage : fabrique <sortie>"); exit(2) }
let sortie = URL(fileURLWithPath: arguments[1])
try? FileManager.default.createDirectory(at: sortie, withIntermediateDirectories: true)

func couleur(_ hex: UInt32, _ alpha: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
            blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
}

func enregistrer(_ taille: Int, _ nom: String, _ dessin: (CGRect) -> Void) {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: taille, pixelsHigh: taille,
                               bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                               colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    dessin(CGRect(x: 0, y: 0, width: taille, height: taille))
    NSGraphicsContext.restoreGraphicsState()
    try! rep.representation(using: .png, properties: [:])!.write(to: sortie.appendingPathComponent(nom))
}

// ── L'icône : le gabarit des icônes macOS (tuile de 824 px sur 1 024, rayon
// ≈ 22,4 %, ombre portée douce), un clairon blanc et deux ondes.
enregistrer(1024, "icone-1024.png") { cadre in
    let tuile = cadre.insetBy(dx: 100, dy: 100)
    let forme = NSBezierPath(roundedRect: tuile, xRadius: 185, yRadius: 185)
    NSGraphicsContext.saveGraphicsState()
    let ombre = NSShadow()
    ombre.shadowColor = couleur(0x000000, 0.30)
    ombre.shadowOffset = NSSize(width: 0, height: -12)
    ombre.shadowBlurRadius = 28
    ombre.set()
    couleur(0xEE6B3A).setFill()
    forme.fill()
    NSGraphicsContext.restoreGraphicsState()
    NSGradient(starting: couleur(0xFFA65A), ending: couleur(0xE0482C))!.draw(in: forme, angle: -90)
    // Un reflet discret sur le haut de la tuile.
    NSGraphicsContext.saveGraphicsState()
    forme.addClip()
    NSGradient(starting: couleur(0xFFFFFF, 0.22), ending: couleur(0xFFFFFF, 0))!
        .draw(in: CGRect(x: tuile.minX, y: tuile.midY, width: tuile.width, height: tuile.height / 2), angle: -90)
    NSGraphicsContext.restoreGraphicsState()

    // Le clairon, décalé vers la gauche pour que l'ensemble (avec les ondes)
    // soit centré sur la tuile.
    // Incliné vers le haut, comme un clairon qu'on embouche : un geste, pas un pictogramme.
    let decalage = NSAffineTransform()
    decalage.translateX(by: 512, yBy: 512)
    decalage.rotate(byDegrees: 12)
    decalage.translateX(by: -512 - 50, yBy: -512 - 10)
    NSGraphicsContext.saveGraphicsState()
    decalage.concat()
    let relief = NSShadow()
    relief.shadowColor = couleur(0x7A1F0A, 0.35)
    relief.shadowOffset = NSSize(width: 0, height: -8)
    relief.shadowBlurRadius = 16
    relief.set()
    let corps = NSBezierPath()
    corps.move(to: NSPoint(x: 290, y: 470))
    corps.line(to: NSPoint(x: 530, y: 470))
    corps.curve(to: NSPoint(x: 764, y: 300), controlPoint1: NSPoint(x: 645, y: 470), controlPoint2: NSPoint(x: 724, y: 388))
    corps.line(to: NSPoint(x: 764, y: 724))
    corps.curve(to: NSPoint(x: 530, y: 554), controlPoint1: NSPoint(x: 724, y: 636), controlPoint2: NSPoint(x: 645, y: 554))
    corps.line(to: NSPoint(x: 290, y: 554))
    corps.close()
    corps.append(NSBezierPath(roundedRect: CGRect(x: 222, y: 450, width: 84, height: 124), xRadius: 26, yRadius: 26))
    NSColor.white.setFill()
    corps.fill()
    NSGraphicsContext.restoreGraphicsState()
    NSGraphicsContext.saveGraphicsState()
    decalage.concat()
    // Le pavillon, vu de trois quarts : une ellipse un peu plus chaude.
    couleur(0xFFE3D2).setFill()
    NSBezierPath(ovalIn: CGRect(x: 740, y: 300, width: 50, height: 424)).fill()
    // Deux ondes : le clairon SONNE.
    for (rayon, alpha) in [(CGFloat(80), CGFloat(0.95)), (CGFloat(134), CGFloat(0.6))] {
        let onde = NSBezierPath()
        onde.appendArc(withCenter: NSPoint(x: 796, y: 512), radius: rayon, startAngle: -40, endAngle: 40)
        onde.lineWidth = 30
        onde.lineCapStyle = .round
        couleur(0xFFFFFF, alpha).setStroke()
        onde.stroke()
    }
    NSGraphicsContext.restoreGraphicsState()
}

// ── Les vignettes d'état : une tuile de couleur et un symbole blanc, lisibles
// en 40 px dans la bannière. Symboles d'UNE seule couche : en blanc uni, un
// symbole à plusieurs couches (une bulle ET ses points) se fond en une tache.
let etats: [(String, String, UInt32)] = [
    ("termine", "checkmark", 0x34C759),
    ("autorisation", "hand.raised.fill", 0xFF9500),
    ("attente", "ellipsis", 0x0A84FF),
    ("question", "questionmark", 0xAF52DE),
    ("connexion", "key.fill", 0x30B0C7),
    ("erreur", "exclamationmark", 0xFF3B30),
]
for (nom, symbole, teinte) in etats {
    enregistrer(256, "etat-\(nom).png") { cadre in
        let forme = NSBezierPath(roundedRect: cadre.insetBy(dx: 8, dy: 8), xRadius: 58, yRadius: 58)
        NSGradient(starting: couleur(teinte).blended(withFraction: 0.18, of: .white)!,
                   ending: couleur(teinte))!.draw(in: forme, angle: -90)
        let reglage = NSImage.SymbolConfiguration(pointSize: 118, weight: .bold)
            .applying(NSImage.SymbolConfiguration(paletteColors: [.white]))
        guard let image = NSImage(systemSymbolName: symbole, accessibilityDescription: nil)?
            .withSymbolConfiguration(reglage) else { print("symbole absent : \(symbole)"); return }
        let taille = image.size
        image.draw(in: CGRect(x: cadre.midX - taille.width / 2, y: cadre.midY - taille.height / 2,
                              width: taille.width, height: taille.height))
    }
}
print("images : \(sortie.path)")
