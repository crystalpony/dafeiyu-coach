import AppKit
import Foundation

// 唱歌花样：固定风格或自动偶发切换。所有变体共用同一条唱歌状态，
// 小黑使用单帧姿态切换；大肥鱼保留既有淡化。不伪造转身。
extension AppController {
    static let singStyles = ["auto", "sway", "mic", "hat", "tail"]

    func preferredSingClip() -> String {
        guard manifest.character == "xiaohei" else { return "sing" }
        switch settings.singStyle ?? "auto" {
        case "mic": return manifest.clips["sing_mic"] != nil ? "sing_mic" : "sing"
        case "hat": return manifest.clips["sing_hat"] != nil ? "sing_hat" : "sing"
        case "tail": return manifest.clips["sing_tail"] != nil ? "sing_tail" : "sing"
        default: return "sing"
        }
    }

    func startSinging() {
        wake()
        singing = true
        petView.singing = true
        singVariant = preferredSingClip()
        playSing(force: true, transition: 0.30)
        nextSingSwitchAt = (settings.singStyle ?? "auto") == "auto"
            ? Date().addingTimeInterval(Double.random(in: 10...16)) : nil
    }

    func playSing(force: Bool = false, transition: Double = 0.32) {
        guard singing, manifest.clips[singVariant] != nil else { return }
        player.play(singVariant, loop: true, autoIdle: true,
                    transition: transition, priority: 85, force: force)
    }

    /// 由 24Hz tick 调用；只在 auto 模式下偶发切到麦克风/街舞帽/坐直摇尾。
    func updateSingRotation() {
        guard singing, (settings.singStyle ?? "auto") == "auto" else { return }
        guard let next = nextSingSwitchAt, Date() >= next else { return }
        let special = ["sing_mic", "sing_hat", "sing_tail"].filter { manifest.clips[$0] != nil }
        guard !special.isEmpty else { return }
        if singVariant == "sing" {
            if Bool.random() {
                singVariant = special.randomElement() ?? "sing"
            }
        } else if Double.random(in: 0..<1) < 0.42 {
            singVariant = "sing"
        } else {
            let others = special.filter { $0 != singVariant }
            if let pick = others.randomElement() { singVariant = pick }
        }
        playSing(force: true, transition: 0.36)
        let hold = singVariant == "sing" ? Double.random(in: 8...14) : Double.random(in: 9...15)
        nextSingSwitchAt = Date().addingTimeInterval(hold)
        logLine("sing variant \(singVariant)")
    }

    func setSingStyle(_ style: String, announce: Bool = true) {
        let value = Self.singStyles.contains(style) ? style : "auto"
        settings.singStyle = value
        saveSettings(settings)
        if singing {
            singVariant = preferredSingClip()
            playSing(force: true, transition: 0.34)
            nextSingSwitchAt = value == "auto"
                ? Date().addingTimeInterval(Double.random(in: 10...16)) : nil
        }
        if announce {
            showBubble(title: "", text: singStyleName(value), badge: "唱歌", tone: .music, hold: 3)
        }
    }

    /// 不依赖音乐监听，直接试唱 20 秒，方便用户预览花样。
    func previewSinging() {
        guard session == nil, !settings.quiet, settings.petOn else { return }
        wake()
        startSinging()
        musicLastUpdate = Date()
        showBubble(title: "唱歌舞台", text: "试唱一段。菜单「唱歌花样」可以换麦克风、街舞帽或摇尾巴。",
                   badge: "♪ 预览", tone: .music, hold: 4)
        logLine("sing preview")
    }

    func singStyleName(_ style: String) -> String {
        switch style {
        case "sway": return "唱歌花样：只律动摇摆"
        case "mic": return "唱歌花样：立麦伴唱"
        case "hat": return "唱歌花样：街舞帽开跳"
        case "tail": return "唱歌花样：坐直摇尾巴"
        default: return "唱歌花样：自动换着来"
        }
    }
}
