import AppKit
import Foundation

// 多形象切换：菜单、CLI、状态共用。单独成文件，Controller 已接近审计行数上限。
extension AppController {
    var currentCharacter: String { settings.character ?? "dafeiyu" }

    func refreshStatusItem() {
        guard let b = statusItem?.button else { return }
        let xiaohei = manifest.character == "xiaohei"
        let symbol = xiaohei ? "pawprint.fill" : "fish.fill"
        let fallback = xiaohei ? "pawprint" : "fish"
        let img = NSImage(systemSymbolName: symbol, accessibilityDescription: manifest.displayName)
            ?? NSImage(systemSymbolName: fallback, accessibilityDescription: manifest.displayName)
        img?.isTemplate = true
        b.image = img
        b.title = manifest.displayName
        b.font = NSFont.systemFont(ofSize: 11.5, weight: .medium)
        b.toolTip = "\(kAppName) · \(manifest.displayName)"
    }

    @discardableResult
    func switchCharacter(_ id: String, announce: Bool = true) -> Bool {
        guard let root = Paths.characterAssets(id),
              let m = ClipManifest.load(from: root) else { return false }
        if id == currentCharacter && m.character == manifest.character { return true }

        settings.character = id
        saveSettings(settings)
        manifest = m
        assetsRoot = root
        player = ClipPlayer(manifest: m, assets: root)
        petView?.player = player
        player.prefetchEarlyFrames(3)
        if singing, session == nil {
            singVariant = preferredSingClip()
            playSing(force: true, transition: 0.25)
            nextSingSwitchAt = (settings.singStyle ?? "auto") == "auto"
                ? Date().addingTimeInterval(Double.random(in: 10...16)) : nil
        } else {
            player.play("idle", loop: true, autoIdle: true, transition: 0.2, priority: 10, force: true)
        }
        petView?.needsDisplay = true
        refreshStatusItem()
        logLine("character switched id=\(id) assets=\(root.path) clips=\(m.clips.count)")

        if announce {
            let intro = m.character == "xiaohei"
                ? "我是小黑。以后我陪着你；要我指哪里，我就跳过去。"
                : "我是大肥鱼。以后我陪着你；要我指哪里，我就游过去。"
            showBubble(title: "\(m.displayName)来了", text: intro,
                       badge: "形象已切换", tone: .coach, hold: 5)
        }
        return true
    }

    @objc func menuSetCharacter(_ sender: NSMenuItem) {
        guard let id = sender.representedObject as? String else { return }
        _ = switchCharacter(id)
    }

    // MARK: 小黑经典互动（仅小黑菜单出现）

    func doubleClickAction() {
        if currentCharacter == "xiaohei" {
            xiaoheiAction("roll")
        } else {
            petDance()
        }
    }

    @objc func menuXiaoheiAction(_ sender: NSMenuItem) {
        guard let clip = sender.representedObject as? String else { return }
        xiaoheiAction(clip)
    }

    @objc func menuWake() {
        wake()
        showBubble(title: "", text: "醒啦。我还在这里。", badge: "", tone: .coach, hold: 3)
    }

    func handleXiaoheiAction(_ cmd: [String: Any]) -> [String: Any] {
        guard manifest.character == "xiaohei" else {
            return ["ok": false, "error": "当前不是小黑"]
        }
        guard let name = cmd["name"] as? String, !name.isEmpty else {
            return ["ok": false, "error": "xiaohei_action 需要 name"]
        }
        xiaoheiAction(name)
        return ["ok": true, "clip": player.currentName, "sleeping": sleeping,
                "character": manifest.character]
    }

    func xiaoheiAction(_ clip: String) {
        wake()
        if clip == "fish" {
            player.play("eat", loop: false, autoIdle: true, transition: 0.16, priority: 90, force: true)
            petView.burstHearts(count: 3)
            showBubble(title: "", text: "小鱼！", badge: "", tone: .success, hold: 4)
            return
        }
        if clip == "sleep" {
            sleeping = true
            player.play("sleep", loop: true, autoIdle: false, transition: 0.20, priority: 90, force: true)
            petView.sleeping = true
            showBubble(title: "", text: "眯一会儿…", badge: "", tone: .coach, hold: 3)
            return
        }
        if clip == "meow" || clip == "meow2" {
            meowAction(twice: clip == "meow2")
            return
        }
        let lines = [
            "wash": "眯眼，晃晃脑袋。",
            "roll": "躺着晃一晃。",
            "pounce": "准备好了。",
            "fluff": "吓了一跳。",
            "heixiu": "黑咻，陪我待一会儿。",
            "meow": "喵～",
        ]
        player.play(clip, loop: false, autoIdle: true, transition: 0.16, priority: 90, force: true)
        if clip == "heixiu" || clip == "roll" {
            petView.burstHearts(count: 2)
        }
        showBubble(title: "", text: lines[clip] ?? "", badge: "", tone: .coach, hold: 4)
    }

    /// 单喵或连续两声喵；第二声复用同一段 36 帧动作，不新增素材。
    func meowAction(twice: Bool) {
        wake()
        MeowAudio.shared.playSequence(twice: twice, enabled: settings.meowSound ?? true)
        if twice {
            player.play("meow", loop: false, autoIdle: false, transition: 0.14,
                        priority: 90, force: true) { [weak self] _ in
                guard let self else { return }
                self.player.play("meow", loop: false, autoIdle: true,
                                 transition: 0.12, priority: 90, force: true)
            }
        } else {
            player.play("meow", loop: false, autoIdle: true, transition: 0.14,
                        priority: 90, force: true)
        }
        showBubble(title: "", text: twice ? "喵喵～" : "喵～", badge: "", tone: .coach, hold: twice ? 4.5 : 4)
    }
}
