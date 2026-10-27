import AppKit
import Foundation

// MARK: - 可成为 key 的无边框小窗（右键菜单 / 关闭按钮需要）
final class CoachWindow: NSWindow {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

// MARK: - 大肥鱼

enum PetRegion { case head, body, tail }

struct HeartParticle {
    var x: CGFloat; var y: CGFloat; var vy: CGFloat
    var alpha: CGFloat; var size: CGFloat; var drift: CGFloat
}

struct Confetto {
    var x: CGFloat; var y: CGFloat; var vx: CGFloat; var vy: CGFloat
    var rot: CGFloat; var spin: CGFloat; var color: NSColor; var life: CGFloat
}

final class PetView: NSView {
    var player: ClipPlayer?
    var bubbleHidden = false { didSet { needsDisplay = true } }
    var sleeping = false { didSet { needsDisplay = true } }
    var singing = false { didSet { needsDisplay = true } }
    var reducedMotion = false
    var notes: [HeartParticle] = []
    var phase: CGFloat = 0
    var pulse: CGFloat = 0
    var isDragging = false
    var interactive = true

    var hearts: [HeartParticle] = []
    var confetti: [Confetto] = []
    private var clickWork: DispatchWorkItem?
    private var dragStart = NSPoint.zero
    private var originStart = NSPoint.zero
    private var moved = false

    var onRegionClick: ((PetRegion) -> Void)?
    var onDoubleClick: (() -> Void)?
    var onDragBegin: (() -> Void)?
    var onDragEnd: (() -> Void)?
    var onContextMenu: ((NSPoint) -> Void)?

    override var isFlipped: Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    private var accent: NSColor { NSColor(calibratedRed: 0.30, green: 0.45, blue: 0.82, alpha: 1) }

    override func draw(_ dirtyRect: NSRect) {
        let w = bounds.width, h = bounds.height
        let hop: CGFloat = pulse > 0 ? -7 * sin(pulse * .pi) : 0
        let singBob: CGFloat = (singing && !reducedMotion) ? -2.2 * abs(sin(phase * 2.2)) : 0
        let breathe: CGFloat = (player?.resolvedName == "idle") ? 1.5 * sin(phase) : 0

        if let p = player, p.image() != nil {
            let pad: CGFloat = 6
            let blend = p.blend
            let outgoing = p.previousImage
            let incoming = p.image()
            if let ctx = NSGraphicsContext.current?.cgContext {
                ctx.saveGState()
                if isDragging {
                    ctx.translateBy(x: w / 2, y: h / 2)
                    ctx.rotate(by: 0.045 * sin(phase * 1.4))
                    ctx.translateBy(x: -w / 2, y: -h / 2)
                } else if singing && !reducedMotion {
                    ctx.translateBy(x: w / 2, y: h / 2)
                    ctx.rotate(by: 0.018 * sin(phase * 2.6))
                    ctx.translateBy(x: -w / 2, y: -h / 2)
                }
                func draw(_ img: NSImage, alpha: CGFloat) {
                    guard alpha > 0.01 else { return }
                    let scale = min((w - pad * 2) / max(img.size.width, 1), (h - pad * 2) / max(img.size.height, 1))
                    let dw = img.size.width * scale
                    let dh = img.size.height * scale
                    let rect = NSRect(x: (w - dw) / 2, y: (h - dh) / 2 + hop + singBob + breathe, width: dw, height: dh)
                    img.draw(in: rect, from: .zero, operation: .sourceOver, fraction: alpha,
                             respectFlipped: true, hints: [.interpolation: NSImageInterpolation.high])
                }
                if let outgoing, blend < 0.99 { draw(outgoing, alpha: 1 - blend) }
                if let incoming { draw(incoming, alpha: max(0.01, blend)) }
                ctx.restoreGState()
            }
        } else {
            drawFallbackFish(w: w, h: h, hop: hop + breathe)
        }

        drawConfetti()
        drawHearts()
        drawNotes()

        if bubbleHidden && !isDragging {
            drawSpeechBadge(w: w, h: h)
        }
        if sleeping {
            drawSleepMarks(w: w, h: h)
        }
    }

    private func drawFallbackFish(w: CGFloat, h: CGFloat, hop: CGFloat) {
        let bob = 2.5 * sin(phase * 1.2) + hop
        let bodyRect = NSRect(x: w * 0.10, y: h * 0.36 + bob, width: w * 0.72, height: h * 0.42)
        let tail = NSBezierPath()
        let tx = bodyRect.maxX - 4
        tail.move(to: NSPoint(x: tx, y: bodyRect.midY))
        tail.curve(to: NSPoint(x: tx + 26, y: bodyRect.midY - 20),
                   controlPoint1: NSPoint(x: tx + 14, y: bodyRect.midY - 4),
                   controlPoint2: NSPoint(x: tx + 24, y: bodyRect.midY - 12))
        tail.curve(to: NSPoint(x: tx + 26, y: bodyRect.midY + 20),
                   controlPoint1: NSPoint(x: tx + 24, y: bodyRect.midY + 12),
                   controlPoint2: NSPoint(x: tx + 14, y: bodyRect.midY + 4))
        tail.close()
        NSColor(calibratedRed: 0.98, green: 0.62, blue: 0.28, alpha: 1).setFill()
        tail.fill()
        let grad = NSGradient(starting: NSColor(calibratedRed: 1.0, green: 0.80, blue: 0.45, alpha: 1),
                              ending: NSColor(calibratedRed: 0.97, green: 0.55, blue: 0.20, alpha: 1))!
        grad.draw(in: NSBezierPath(ovalIn: bodyRect), angle: -70)
        NSColor.white.setFill()
        NSBezierPath(ovalIn: NSRect(x: bodyRect.minX + 18, y: bodyRect.midY - 8, width: 11, height: 11)).fill()
        NSColor.black.setFill()
        NSBezierPath(ovalIn: NSRect(x: bodyRect.minX + 21, y: bodyRect.midY - 5, width: 5, height: 5)).fill()
    }

    private func drawSpeechBadge(w: CGFloat, h: CGFloat) {
        let sc = max(w / 210, 0.6)
        let bs = max(19, 25 * sc)
        let badge = NSRect(x: w * 0.66, y: h * 0.13, width: bs, height: bs)
        accent.withAlphaComponent(0.95).setFill()
        NSBezierPath(ovalIn: badge).fill()
        NSColor.white.withAlphaComponent(0.96).setStroke()
        let ring = NSBezierPath(ovalIn: badge.insetBy(dx: 0.8, dy: 0.8))
        ring.lineWidth = 1.5
        ring.stroke()
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 13 * sc, weight: .heavy),
            .foregroundColor: NSColor.white
        ]
        let label = NSAttributedString(string: "…", attributes: attrs)
        let sz = label.size()
        label.draw(at: NSPoint(x: badge.midX - sz.width / 2, y: badge.midY - sz.height / 2))
    }

    private func drawSleepMarks(w: CGFloat, h: CGFloat) {
        let base = NSPoint(x: w * 0.68, y: h * 0.16)
        for i in 0..<3 {
            let t = CGFloat(i) / 3
            let alpha = 0.35 + 0.45 * (0.5 + 0.5 * sin(phase * 1.2 - t * 2))
            let size = (11 + CGFloat(i) * 3) * max(w / 210, 0.6)
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: size, weight: .bold),
                .foregroundColor: accent.withAlphaComponent(alpha)
            ]
            NSAttributedString(string: "z", attributes: attrs)
                .draw(at: NSPoint(x: base.x + CGFloat(i) * 9, y: base.y - CGFloat(i) * 13))
        }
    }

    private func drawHearts() {
        for p in hearts where p.alpha > 0.01 {
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: p.size, weight: .bold),
                .foregroundColor: NSColor(calibratedRed: 1.0, green: 0.42, blue: 0.55, alpha: p.alpha)
            ]
            NSAttributedString(string: "♥", attributes: attrs).draw(at: NSPoint(x: p.x, y: p.y))
        }
    }

    private func drawNotes() {
        for p in notes where p.alpha > 0.02 {
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: p.size, weight: .semibold),
                .foregroundColor: NSColor(calibratedRed: 0.62, green: 0.44, blue: 0.95, alpha: p.alpha)
            ]
            let glyph = Int(p.size * 10) % 2 == 0 ? "♪" : "♫"
            NSAttributedString(string: glyph, attributes: attrs).draw(at: NSPoint(x: p.x, y: p.y))
        }
    }

    func spawnNote() {
        guard !reducedMotion else { return }
        let w = bounds.width
        notes.append(HeartParticle(x: w * 0.5 + CGFloat.random(in: -w * 0.28 ... w * 0.28),
                                   y: bounds.height * 0.30,
                                   vy: CGFloat.random(in: -0.9 ... -0.55),
                                   alpha: 1,
                                   size: CGFloat.random(in: 13...19),
                                   drift: CGFloat.random(in: -0.25...0.25)))
        needsDisplay = true
    }

    private func drawConfetti() {
        for c in confetti where c.life > 0.02 {
            c.color.withAlphaComponent(min(1, c.life)).setFill()
            let rect = NSRect(x: c.x, y: c.y, width: 6, height: 3.4)
            let ctx = NSGraphicsContext.current?.cgContext
            ctx?.saveGState()
            ctx?.translateBy(x: rect.midX, y: rect.midY)
            ctx?.rotate(by: c.rot)
            NSBezierPath(rect: NSRect(x: -3, y: -1.7, width: 6, height: 3.4)).fill()
            ctx?.restoreGState()
        }
    }

    func burstHearts(count: Int = 5) {
        let w = bounds.width
        for i in 0..<count {
            hearts.append(HeartParticle(
                x: w * 0.5 + CGFloat(i - count / 2) * 12 + CGFloat.random(in: -4...4),
                y: bounds.height * 0.34,
                vy: CGFloat.random(in: -1.4 ... -0.9),
                alpha: 1,
                size: CGFloat.random(in: 12...18),
                drift: CGFloat.random(in: -0.35...0.35)))
        }
        needsDisplay = true
    }

    func burstConfetti(count: Int = 26) {
        let palette: [NSColor] = [
            NSColor(calibratedRed: 1.0, green: 0.55, blue: 0.25, alpha: 1),
            NSColor(calibratedRed: 0.35, green: 0.55, blue: 0.95, alpha: 1),
            NSColor(calibratedRed: 0.30, green: 0.80, blue: 0.55, alpha: 1),
            NSColor(calibratedRed: 1.0, green: 0.80, blue: 0.30, alpha: 1),
            NSColor(calibratedRed: 0.85, green: 0.45, blue: 0.85, alpha: 1)
        ]
        for _ in 0..<count {
            confetti.append(Confetto(
                x: CGFloat.random(in: 0.15...0.85) * bounds.width,
                y: bounds.height * 0.35,
                vx: CGFloat.random(in: -2.2...2.2),
                vy: CGFloat.random(in: -3.4 ... -1.4),
                rot: CGFloat.random(in: 0...3.14),
                spin: CGFloat.random(in: -0.2...0.2),
                color: palette.randomElement()!,
                life: 1))
        }
        needsDisplay = true
    }

    func tickEffects(_ dt: CGFloat) {
        var needs = false
        if !notes.isEmpty {
            needs = true
            for i in notes.indices {
                notes[i].y += notes[i].vy * dt * 60
                notes[i].x += notes[i].drift * dt * 60
                notes[i].alpha -= dt * 0.32
            }
            notes.removeAll { $0.alpha <= 0.02 }
        }
        if !hearts.isEmpty {
            needs = true
            for i in hearts.indices {
                hearts[i].y += hearts[i].vy * dt * 60
                hearts[i].x += hearts[i].drift * dt * 60
                hearts[i].alpha -= dt * 0.55
            }
            hearts.removeAll { $0.alpha <= 0.01 }
        }
        if !confetti.isEmpty {
            needs = true
            for i in confetti.indices {
                confetti[i].vy += 0.09 * dt * 60
                confetti[i].x += confetti[i].vx * dt * 60
                confetti[i].y += confetti[i].vy * dt * 60
                confetti[i].rot += confetti[i].spin * dt * 60
                confetti[i].life -= dt * 0.22
            }
            confetti.removeAll { $0.life <= 0.02 || $0.y > bounds.height + 20 }
        }
        if needs { needsDisplay = true }
    }

    // MARK: 鼠标

    override func resetCursorRects() {
        addCursorRect(bounds, cursor: isDragging ? .closedHand : .openHand)
    }

    override func mouseDown(with event: NSEvent) {
        guard interactive else { return }
        isDragging = true
        moved = false
        dragStart = NSEvent.mouseLocation
        originStart = window?.frame.origin ?? .zero
        NSCursor.closedHand.push()
    }

    override func mouseDragged(with event: NSEvent) {
        guard isDragging, let win = window else { return }
        let now = NSEvent.mouseLocation
        let dx = now.x - dragStart.x
        let dy = now.y - dragStart.y
        if !moved && (abs(dx) > 3 || abs(dy) > 3) {
            moved = true
            clickWork?.cancel()
            onDragBegin?()
        }
        guard moved else { return }
        let screen = win.screen ?? NSScreen.main ?? NSScreen.screens[0]
        var o = NSPoint(x: originStart.x + dx, y: originStart.y + dy)
        o.x = clamp(o.x, screen.visibleFrame.minX, screen.visibleFrame.maxX - win.frame.width)
        o.y = clamp(o.y, screen.visibleFrame.minY, screen.visibleFrame.maxY - win.frame.height)
        win.setFrameOrigin(o)
    }

    override func mouseUp(with event: NSEvent) {
        guard isDragging else { return }
        isDragging = false
        NSCursor.pop()
        window?.invalidateCursorRects(for: self)
        if moved {
            onDragEnd?()
            return
        }
        if event.clickCount >= 2 {
            clickWork?.cancel()
            onDoubleClick?()
            return
        }
        let local = convert(event.locationInWindow, from: nil)
        let region: PetRegion
        if local.y < bounds.height * 0.42 && local.x > bounds.width * 0.18 && local.x < bounds.width * 0.82 {
            region = .head
        } else if local.x > bounds.width * 0.70 && local.y > bounds.height * 0.52 {
            region = .tail
        } else {
            region = .body
        }
        clickWork?.cancel()
        let work = DispatchWorkItem { [weak self] in self?.onRegionClick?(region) }
        clickWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.20, execute: work)
    }

    override func rightMouseDown(with event: NSEvent) {
        onContextMenu?(NSEvent.mouseLocation)
    }
}

// MARK: - 气泡

enum BubbleTone {
    case coach, success, error, thinking, music
    var accent: NSColor {
        switch self {
        case .coach: return NSColor(calibratedRed: 0.97, green: 0.53, blue: 0.24, alpha: 1)
        case .success: return NSColor(calibratedRed: 0.20, green: 0.68, blue: 0.46, alpha: 1)
        case .error: return NSColor(calibratedRed: 0.90, green: 0.28, blue: 0.32, alpha: 1)
        case .thinking: return NSColor(calibratedRed: 0.35, green: 0.50, blue: 0.88, alpha: 1)
        case .music: return NSColor(calibratedRed: 0.55, green: 0.38, blue: 0.90, alpha: 1)
        }
    }
    var ink: NSColor {
        switch self {
        case .error: return NSColor(calibratedRed: 0.55, green: 0.10, blue: 0.14, alpha: 1)
        default: return NSColor(calibratedRed: 0.14, green: 0.17, blue: 0.26, alpha: 1)
        }
    }
}

final class BubbleView: NSView {
    var title: String = ""
    var text: String = ""
    var subtext: String = ""
    var badge: String = ""
    var tone: BubbleTone = .coach
    var doneCount: Int = 0
    var total: Int = 0
    var currentIndex: Int = 0
    var contentScale: CGFloat = 1
    var tailOnRight = false
    var compactMusic = false
    var tailAtBottom = false
    var baseSize = NSSize(width: 330, height: 96)

    override var isFlipped: Bool { true }

    override func draw(_ dirtyRect: NSRect) {
        guard let ctx = NSGraphicsContext.current else { return }
        ctx.saveGraphicsState()
        ctx.cgContext.scaleBy(x: contentScale, y: contentScale)

        if compactMusic {
            drawMusicBar()
            ctx.restoreGraphicsState()
            return
        }

        let W = baseSize.width, H = baseSize.height
        let tailW: CGFloat = 11
        let bodyX: CGFloat = tailOnRight ? 0 : tailW
        let bodyW = W - tailW
        let bodyRect = NSRect(x: bodyX, y: 3, width: bodyW, height: H - 6)
        let path = NSBezierPath(roundedRect: bodyRect, xRadius: 15, yRadius: 15)

        NSColor(calibratedWhite: 1.0, alpha: 0.975).setFill()
        path.fill()
        tone.accent.withAlphaComponent(0.85).setStroke()
        path.lineWidth = 1.8
        path.stroke()

        let ty = H - 46
        let tail = NSBezierPath()
        if tailOnRight {
            tail.move(to: NSPoint(x: bodyRect.maxX - 1, y: ty))
            tail.line(to: NSPoint(x: bodyRect.maxX + tailW, y: ty + 12))
            tail.line(to: NSPoint(x: bodyRect.maxX - 1, y: ty + 24))
        } else {
            tail.move(to: NSPoint(x: bodyRect.minX + 1, y: ty))
            tail.line(to: NSPoint(x: bodyRect.minX - tailW, y: ty + 12))
            tail.line(to: NSPoint(x: bodyRect.minX + 1, y: ty + 24))
        }
        tail.close()
        NSColor(calibratedWhite: 1.0, alpha: 0.975).setFill()
        tail.fill()
        tone.accent.withAlphaComponent(0.85).setStroke()
        tail.lineWidth = 1.8
        tail.stroke()

        var y: CGFloat = 15
        let textX = bodyRect.minX + 16
        let textW = bodyRect.width - 30

        if !badge.isEmpty {
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: 10.5, weight: .bold),
                .foregroundColor: tone.accent
            ]
            let b = NSAttributedString(string: badge, attributes: attrs)
            b.draw(with: NSRect(x: textX, y: y, width: textW, height: 15),
                   options: [.usesLineFragmentOrigin, .usesFontLeading])
            y += 16
        }
        if !title.isEmpty {
            let para = NSMutableParagraphStyle(); para.lineSpacing = 1
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: 13, weight: .bold),
                .foregroundColor: tone.ink,
                .paragraphStyle: para
            ]
            let t = NSAttributedString(string: title, attributes: attrs)
            let h = ceil(t.boundingRect(with: NSSize(width: textW, height: 200),
                                        options: [.usesLineFragmentOrigin, .usesFontLeading]).height)
            t.draw(with: NSRect(x: textX, y: y, width: textW, height: h + 2),
                   options: [.usesLineFragmentOrigin, .usesFontLeading])
            y += h + 5
        }

        let para = NSMutableParagraphStyle()
        para.lineSpacing = 3.2
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 14.5, weight: .medium),
            .foregroundColor: tone.ink,
            .paragraphStyle: para
        ]
        let body = NSAttributedString(string: text, attributes: attrs)
        let bodyH = body.boundingRect(with: NSSize(width: textW, height: 2000),
                                      options: [.usesLineFragmentOrigin, .usesFontLeading]).height
        body.draw(with: NSRect(x: textX, y: y, width: textW, height: bodyH + 4),
                  options: [.usesLineFragmentOrigin, .usesFontLeading])
        y += ceil(bodyH) + 5

        if !subtext.isEmpty {
            let subPara = NSMutableParagraphStyle(); subPara.lineSpacing = 2
            let subAttrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: 12.5, weight: .regular),
                .foregroundColor: NSColor(calibratedWhite: 0.45, alpha: 1),
                .paragraphStyle: subPara
            ]
            let sub = NSAttributedString(string: subtext, attributes: subAttrs)
            let subH = sub.boundingRect(with: NSSize(width: textW, height: 300),
                                        options: [.usesLineFragmentOrigin, .usesFontLeading]).height
            sub.draw(with: NSRect(x: textX, y: y, width: textW, height: subH + 3),
                     options: [.usesLineFragmentOrigin, .usesFontLeading])
        }

        if total > 0 {
            let dotsY = H - 16
            let dotR: CGFloat = 3.2
            let gap: CGFloat = 7
            let startX = textX
            let limit = min(total, 14)
            for i in 0..<limit {
                let r = NSRect(x: startX + CGFloat(i) * (dotR * 2 + gap), y: dotsY, width: dotR * 2, height: dotR * 2)
                if i < doneCount {
                    tone.accent.setFill()
                } else if i == currentIndex {
                    tone.accent.withAlphaComponent(0.95).setFill()
                } else {
                    tone.accent.withAlphaComponent(0.22).setFill()
                }
                NSBezierPath(ovalIn: r).fill()
                if i == currentIndex {
                    tone.accent.withAlphaComponent(0.35).setStroke()
                    let ring = NSBezierPath(ovalIn: r.insetBy(dx: -2, dy: -2))
                    ring.lineWidth = 1
                    ring.stroke()
                }
            }
        }

        ctx.restoreGraphicsState()
    }

    /// 唱歌时贴在头顶的窄歌词条：最多两行，一句歌词一行，不占桌面。
    private func drawMusicBar() {
        let W = baseSize.width, H = baseSize.height
        let bodyRect = NSRect(x: 2, y: 2, width: W - 4, height: H - 12)
        let path = NSBezierPath(roundedRect: bodyRect, xRadius: 14, yRadius: 14)
        NSColor(calibratedWhite: 1.0, alpha: 0.97).setFill()
        path.fill()
        tone.accent.withAlphaComponent(0.78).setStroke()
        path.lineWidth = 1.5
        path.stroke()

        // 指向头顶的小尾巴
        if tailAtBottom {
            let tail = NSBezierPath()
            tail.move(to: NSPoint(x: W / 2 - 7, y: bodyRect.maxY - 1))
            tail.line(to: NSPoint(x: W / 2, y: H - 1))
            tail.line(to: NSPoint(x: W / 2 + 7, y: bodyRect.maxY - 1))
            tail.close()
            NSColor(calibratedWhite: 1.0, alpha: 0.97).setFill()
            tail.fill()
            tone.accent.withAlphaComponent(0.78).setStroke()
            tail.lineWidth = 1.5
            tail.stroke()
        }

        // ♪ 徽标
        let badgeRect = NSRect(x: 12, y: 13, width: 24, height: 24)
        tone.accent.withAlphaComponent(0.14).setFill()
        NSBezierPath(ovalIn: badgeRect).fill()
        let noteAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 14, weight: .bold),
            .foregroundColor: tone.accent
        ]
        let note = NSAttributedString(string: "♪", attributes: noteAttrs)
        let ns = note.size()
        note.draw(at: NSPoint(x: badgeRect.midX - ns.width / 2, y: badgeRect.midY - ns.height / 2))

        let textX: CGFloat = 44
        let rightPad: CGFloat = 12
        let titleW = W - textX - rightPad

        // 歌曲名（小字、单行截断）
        if !title.isEmpty {
            let p = NSMutableParagraphStyle()
            p.lineBreakMode = .byTruncatingTail
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: 10.5, weight: .medium),
                .foregroundColor: NSColor(calibratedWhite: 0.48, alpha: 1),
                .paragraphStyle: p
            ]
            NSAttributedString(string: title, attributes: attrs)
                .draw(in: NSRect(x: textX, y: 9, width: titleW, height: 14))
        }

        // 当前歌词（单行，超长自动省略）
        let p = NSMutableParagraphStyle()
        p.lineBreakMode = .byTruncatingTail
        let lyricAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 14, weight: .semibold),
            .foregroundColor: tone.ink,
            .paragraphStyle: p
        ]
        let line = text.isEmpty ? "♪ 跟着哼" : text
        NSAttributedString(string: line, attributes: lyricAttrs)
            .draw(in: NSRect(x: textX, y: 25, width: titleW, height: 20))
    }

    static func measure(title: String, text: String, subtext: String = "", badge: String, total: Int,
                        music: Bool = false) -> NSSize {
        if music { return NSSize(width: 316, height: 62) }
        let width: CGFloat = 336
        let textW = width - 11 - 30
        var h: CGFloat = 15
        if !badge.isEmpty { h += 16 }
        if !title.isEmpty {
            let para = NSMutableParagraphStyle(); para.lineSpacing = 1
            let attrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: 13, weight: .bold), .paragraphStyle: para
            ]
            let t = NSAttributedString(string: title, attributes: attrs)
            h += ceil(t.boundingRect(with: NSSize(width: textW, height: 200),
                                     options: [.usesLineFragmentOrigin, .usesFontLeading]).height) + 5
        }
        let para = NSMutableParagraphStyle(); para.lineSpacing = 3.2
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 14.5, weight: .medium), .paragraphStyle: para
        ]
        let body = NSAttributedString(string: text, attributes: attrs)
        h += ceil(body.boundingRect(with: NSSize(width: textW, height: 2000),
                                    options: [.usesLineFragmentOrigin, .usesFontLeading]).height)
        if !subtext.isEmpty {
            let subAttrs: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: 12.5)]
            let sub = NSAttributedString(string: subtext, attributes: subAttrs)
            h += ceil(sub.boundingRect(with: NSSize(width: textW, height: 300),
                                       options: [.usesLineFragmentOrigin, .usesFontLeading]).height) + 4
        }
        h += 22
        if total > 0 { h += 10 }
        h += 8
        return NSSize(width: width, height: max(64, h))
    }
}

// MARK: - 气泡关闭按钮

final class BubbleCloseView: NSView {
    var hovering = false { didSet { needsDisplay = true } }
    var onClick: (() -> Void)?
    private var tracking: NSTrackingArea?

    override var isFlipped: Bool { true }

    override func draw(_ dirtyRect: NSRect) {
        let c = NSRect(x: 1.5, y: 1.5, width: bounds.width - 3, height: bounds.height - 3)
        NSColor(calibratedWhite: hovering ? 0.34 : 0.56, alpha: 0.94).setFill()
        NSBezierPath(ovalIn: c).fill()
        NSColor.white.withAlphaComponent(0.9).setStroke()
        let ring = NSBezierPath(ovalIn: c.insetBy(dx: 0.5, dy: 0.5))
        ring.lineWidth = 1.2
        ring.stroke()
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 11, weight: .bold),
            .foregroundColor: NSColor.white
        ]
        let xs = NSAttributedString(string: "✕", attributes: attrs)
        let sz = xs.size()
        xs.draw(at: NSPoint(x: c.midX - sz.width / 2, y: c.midY - sz.height / 2))
    }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let tracking { removeTrackingArea(tracking) }
        let t = NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect],
                               owner: self, userInfo: nil)
        addTrackingArea(t)
        tracking = t
    }
    override func mouseEntered(with event: NSEvent) { hovering = true }
    override func mouseExited(with event: NSEvent) { hovering = false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .pointingHand) }
    override func mouseDown(with event: NSEvent) { onClick?() }
}

// MARK: - 收起后的找回小圆点

final class RestoreView: NSView {
    var onClick: (() -> Void)?
    var hovering = false { didSet { needsDisplay = true } }
    private var tracking: NSTrackingArea?

    override func draw(_ dirtyRect: NSRect) {
        let c = bounds.insetBy(dx: 2, dy: 2)
        NSColor(calibratedRed: 0.30, green: 0.45, blue: 0.82, alpha: 0.96).setFill()
        NSBezierPath(ovalIn: c).fill()
        NSColor.white.withAlphaComponent(0.94).setStroke()
        let ring = NSBezierPath(ovalIn: c.insetBy(dx: 1, dy: 1))
        ring.lineWidth = 1.4
        ring.stroke()
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 12, weight: .bold),
            .foregroundColor: NSColor.white
        ]
        let s = NSAttributedString(string: "鱼", attributes: attrs)
        let sz = s.size()
        s.draw(at: NSPoint(x: c.midX - sz.width / 2, y: c.midY - sz.height / 2))
    }
    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let tracking { removeTrackingArea(tracking) }
        let t = NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect],
                               owner: self, userInfo: nil)
        addTrackingArea(t); tracking = t
    }
    override func mouseEntered(with event: NSEvent) { hovering = true }
    override func mouseExited(with event: NSEvent) { hovering = false }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func resetCursorRects() { addCursorRect(bounds, cursor: .pointingHand) }
    override func mouseDown(with event: NSEvent) { onClick?() }
}

// MARK: - 演示舞台（盖住其它应用，抬高桌宠层，供截图/录屏）
final class StageView: NSView {
    override var isFlipped: Bool { true }
    override func draw(_ dirtyRect: NSRect) {
        let w = bounds.width, h = bounds.height
        let grad = NSGradient(starting: NSColor(calibratedRed: 0.985, green: 0.965, blue: 0.930, alpha: 1),
                              ending: NSColor(calibratedRed: 0.905, green: 0.940, blue: 0.985, alpha: 1))!
        grad.draw(in: bounds, angle: -55)
        for (i, c) in [NSColor(calibratedRed: 0.98, green: 0.62, blue: 0.32, alpha: 0.10),
                       NSColor(calibratedRed: 0.36, green: 0.50, blue: 0.92, alpha: 0.09)].enumerated() {
            let r = min(w, h) * (i == 0 ? 0.42 : 0.52)
            let cx = i == 0 ? w * 0.82 : w * 0.16
            let cy = i == 0 ? h * 0.22 : h * 0.80
            c.setFill()
            NSBezierPath(ovalIn: NSRect(x: cx - r / 2, y: cy - r / 2, width: r, height: r)).fill()
        }
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 12, weight: .medium),
            .foregroundColor: NSColor(calibratedWhite: 0.25, alpha: 0.28)
        ]
        NSAttributedString(string: "桌面大肥鱼 Coach", attributes: attrs)
            .draw(at: NSPoint(x: 26, y: h - 34))
    }
}

// MARK: - 指针层（每块屏一个，鼠标穿透）

final class PointerView: NSView {
    var targetGlobal: CGPoint?      // AppKit 全局坐标
    var petGlobal: CGPoint?         // AppKit 全局坐标
    var label: String = ""
    var tone: BubbleTone = .coach
    var phase: CGFloat = 0
    var screenFrame: NSRect = .zero

    override var isFlipped: Bool { true }

    private func local(_ p: CGPoint) -> CGPoint {
        CGPoint(x: p.x - screenFrame.minX, y: screenFrame.maxY - p.y)
    }

    override func draw(_ dirtyRect: NSRect) {
        guard let t = targetGlobal else { return }
        let center = local(t)
        guard bounds.contains(center) else { return }
        let accent = tone.accent
        let pulse = 26 + 6 * sin(phase * 1.9)

        if let pet = petGlobal {
            let p = local(pet)
            if bounds.contains(p) {
                let line = NSBezierPath()
                line.move(to: NSPoint(x: p.x, y: p.y - 26))
                let mid = NSPoint(x: (p.x + center.x) / 2, y: (p.y + center.y) / 2 - 34)
                line.curve(to: NSPoint(x: center.x, y: center.y - 8),
                           controlPoint1: NSPoint(x: p.x, y: mid.y),
                           controlPoint2: NSPoint(x: center.x, y: mid.y))
                accent.withAlphaComponent(0.35).setStroke()
                line.lineWidth = 1.6
                line.setLineDash([4, 5], count: 2, phase: 0)
                line.stroke()
            }
        }

        // 柔光
        accent.withAlphaComponent(0.10).setFill()
        NSBezierPath(ovalIn: NSRect(x: center.x - pulse - 16, y: center.y - pulse - 16,
                                    width: (pulse + 16) * 2, height: (pulse + 16) * 2)).fill()

        NSColor.white.withAlphaComponent(0.96).setStroke()
        let outer = NSBezierPath(ovalIn: NSRect(x: center.x - pulse - 3, y: center.y - pulse - 3,
                                                width: (pulse + 3) * 2, height: (pulse + 3) * 2))
        outer.lineWidth = 6.5
        outer.stroke()

        accent.setStroke()
        let ring = NSBezierPath(ovalIn: NSRect(x: center.x - pulse, y: center.y - pulse,
                                               width: pulse * 2, height: pulse * 2))
        ring.lineWidth = 3.2
        ring.stroke()

        accent.setFill()
        NSBezierPath(ovalIn: NSRect(x: center.x - 3.4, y: center.y - 3.4, width: 6.8, height: 6.8)).fill()

        // 上方指示箭头
        let bob = 3 * sin(phase * 2.4)
        let ax = center.x
        let ay = center.y - pulse - 20 + bob
        let arrow = NSBezierPath()
        arrow.move(to: NSPoint(x: ax, y: ay + 16))
        arrow.line(to: NSPoint(x: ax - 9, y: ay))
        arrow.line(to: NSPoint(x: ax + 9, y: ay))
        arrow.close()
        NSColor.white.setStroke()
        arrow.lineWidth = 5
        arrow.stroke()
        accent.setFill()
        arrow.fill()

        drawLabel(near: center, accent: accent)
    }

    private func drawLabel(near center: CGPoint, accent: NSColor) {
        guard !label.isEmpty else { return }
        let para = NSMutableParagraphStyle(); para.alignment = .center
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 13, weight: .semibold),
            .foregroundColor: NSColor(calibratedWhite: 0.12, alpha: 1),
            .paragraphStyle: para
        ]
        let maxW: CGFloat = 300
        let s = NSAttributedString(string: label, attributes: attrs)
        let bound = s.boundingRect(with: NSSize(width: maxW, height: 200),
                                   options: [.usesLineFragmentOrigin, .usesFontLeading])
        let w = min(maxW, ceil(bound.width)) + 22
        let h = ceil(bound.height) + 12
        var x = center.x - w / 2
        var y = center.y + 26 + 30
        if y + h > bounds.height - 8 { y = center.y - 26 - 30 - h }
        x = clamp(x, 8, bounds.width - w - 8)
        let rect = NSRect(x: x, y: y, width: w, height: h)
        let pill = NSBezierPath(roundedRect: rect, xRadius: h / 2, yRadius: h / 2)
        NSColor(calibratedWhite: 1.0, alpha: 0.97).setFill()
        pill.fill()
        accent.withAlphaComponent(0.9).setStroke()
        pill.lineWidth = 1.5
        pill.stroke()
        s.draw(with: NSRect(x: rect.minX + 11, y: rect.minY + 5, width: rect.width - 22, height: h),
               options: [.usesLineFragmentOrigin, .usesFontLeading])
    }
}
