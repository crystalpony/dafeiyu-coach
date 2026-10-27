import AppKit
import Foundation

// 陪伴、前台应用反应、待机小动作、游到鼠标边。与主控制器分开，便于单独维护。
extension AppController {
    // MARK: 陪伴

    func observeWorkspace() {
        appObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification, object: nil, queue: .main
        ) { [weak self] note in
            guard let self else { return }
            guard let app = note.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else { return }
            self.reactToApp(app)
        }
        wakeObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.screensDidWakeNotification, object: nil, queue: .main
        ) { [weak self] _ in
            guard let self else { return }
            self.buildPointerLayers()
            self.player.touchClock()
        }
        NotificationCenter.default.addObserver(forName: NSApplication.didChangeScreenParametersNotification,
                                               object: nil, queue: .main) { [weak self] _ in
            guard let self else { return }
            self.buildPointerLayers()
        }
    }

    func reactToApp(_ app: NSRunningApplication) {
        guard settings.playful, !settings.quiet, session == nil, !sleeping else { return }
        if Quips.isMeetingApp(app.localizedName ?? "") {
            if bubbleKind == .music { stopMusicDisplay() }
            return
        }
        guard app.processIdentifier != ProcessInfo.processInfo.processIdentifier else { return }
        guard Date().timeIntervalSince(lastQuipAt) > 150 else { return }
        guard !bubbleVisible else { return }
        let name = app.localizedName ?? ""
        guard !name.isEmpty else { return }
        if name == "Finder" && !Bool.random() { return }
        let line = Quips.forApp(name)
        guard !line.isEmpty else { return }
        lastQuipAt = Date()
        player.play("pat", loop: false, autoIdle: true)
        showBubble(title: "", text: line, badge: name, tone: .thinking, hold: 6.5)
        logLine("app quip \(name): \(line)")
    }

    func idleTick() {
        guard settings.petOn else { return }
        if let t = musicLastUpdate, singing, Date().timeIntervalSince(t) > 30 {
            stopMusicDisplay()
        }
        if let until = focusUntil, Date() >= until {
            finishFocus()
        }
        if let until = quietUntil, Date() >= until {
            quietUntil = nil
            settings.quiet = false
            saveSettings(settings)
            showBubble(title: "", text: "会议模式结束，我回来啦。", badge: "", tone: .coach, hold: 4)
        }
        let idleFor = Date().timeIntervalSince(lastCommandAt)
        if !settings.quiet, !sleeping, session == nil, idleFor > 600 {
            sleeping = true
            player.play("yawn", loop: false, autoIdle: false)
            petView.sleeping = true
            logLine("sleep")
            return
        }
        guard !settings.quiet, !sleeping, session == nil, !bubbleVisible, pointerGlobal == nil else { return }
        if isMeetingFrontmost() { return }
        guard Date() >= nextIdleActionAt else { return }
        nextIdleActionAt = Date().addingTimeInterval(Double.random(in: 70...150))
        let roll = Int.random(in: 0..<10)
        if roll < 4 {
            player.play("pat", loop: false, autoIdle: true)
            petView.burstHearts(count: 2)
            showBubble(title: "", text: Quips.idleRandom(), badge: "", tone: .coach, hold: 6)
        } else if roll < 7 {
            player.play(Bool.random() ? "stretch" : "yawn", loop: false, autoIdle: true)
        } else if settings.playful, glide == nil {
            glideToCursorAndBack()
        }
    }

    func glideToCursorAndBack() {
        let mouse = NSEvent.mouseLocation
        let screen = ScreenSpace.screen(containing: mouse)
        let size = petWindow.frame.size
        let vf = screen.visibleFrame
        var to = NSPoint(x: mouse.x + 46, y: mouse.y - size.height * 0.55)
        to.x = clamp(to.x, vf.minX, vf.maxX - size.width)
        to.y = clamp(to.y, vf.minY, vf.maxY - size.height)
        let origin = petWindow.frame.origin
        if abs(to.x - origin.x) < 40 && abs(to.y - origin.y) < 40 { return }
        glide = (origin, to, CACurrentMediaTime(), 0.9, origin)
        player.play("working", loop: true, autoIdle: false)
        DispatchQueue.main.asyncAfter(deadline: .now() + 8) { [weak self] in
            guard let self, self.glide == nil, Date().timeIntervalSince(self.lastCommandAt) > 6 else { return }
            self.player.play("idle", loop: true, autoIdle: true)
        }
    }

    func comeHere() {
        guard petWindow != nil else { return }
        wake()
        let mouse = NSEvent.mouseLocation
        let screen = ScreenSpace.screen(containing: mouse)
        let size = petWindow.frame.size
        let vf = screen.visibleFrame
        var to = NSPoint(x: mouse.x + 40, y: mouse.y + 30)
        to.x = clamp(to.x, vf.minX, vf.maxX - size.width)
        to.y = clamp(to.y, vf.minY, vf.maxY - size.height)
        glide = (petWindow.frame.origin, to, CACurrentMediaTime(), 0.75, nil)
        player.play("working", loop: true, autoIdle: true)
    }


    /// 明确让大肥鱼随便说一句（测试/互动都可用）。
    func quipNow() {
        wake()
        let app = NSWorkspace.shared.frontmostApplication?.localizedName ?? ""
        let line = Quips.forApp(app)
        lastQuipAt = Date()
        player.play("pat", loop: false, autoIdle: true)
        petView.burstHearts(count: 2)
        showBubble(title: "", text: line, badge: app, tone: .thinking, hold: 6.5)
    }
}

// MARK: - 陪伴台词

enum Quips {
    static var idleIndex = 0
    static let idle = [
        "我在呢。需要我指给你看，就喊我一声。",
        "坐久了，伸个懒腰吧。",
        "慢慢来，一步一步就好。",
        "今天也辛苦啦，喝口水吧。",
        "不着急，我陪你。",
        "要不要我帮你盯着下一步？",
    ]

    static func idleRandom() -> String {
        idleIndex = (idleIndex + 1) % idle.count
        return idle[idleIndex]
    }

    static func isMeetingApp(_ name: String) -> Bool {
        let n = name.lowercased()
        return ["zoom", "teams", "webex", "meet", "腾讯会议", "飞书会议", "钉钉会议",
                "facetime", "google meet", "tencent meeting", "voov"].contains { n.contains($0) }
    }

    static func forApp(_ name: String) -> String {
        let n = name.lowercased()
        if n.contains("xcode") || n.contains("visual studio") || n.contains("cursor") || n.contains("terminal") || n.contains("iterm") || n.contains("warp") || n.contains("qoder") || n.contains("codex") || n.contains("deepseek") || n.contains("claude") {
            return ["写代码呀？我先安静待着，需要时喊我。", "编译的事我不催，慢慢来。", "要不要我帮你看看下一步？"].randomElement()!
        }
        if n.contains("safari") || n.contains("chrome") || n.contains("edge") || n.contains("firefox") || n.contains("arc") {
            return ["查资料吗？找到重点可以让我记着。", "网页看久了，眼睛也歇一会儿。"].randomElement()!
        }
        if n.contains("garageband") || n.contains("logic") || n.contains("music") || n.contains("ableton") {
            return "要不要一起打拍子？我可以帮你数拍。"
        }
        if n.contains("finder") {
            return "找文件吗？我可以帮你指路。"
        }
        if n.contains("feishu") || n.contains("lark") || n.contains("wechat") || n.contains("qq") || n.contains("mail") || n.contains("slack") {
            return "回消息别忘了喝水，我在这儿等你。"
        }
        if n.contains("keynote") || n.contains("powerpoint") || n.contains("pages") || n.contains("word") || n.contains("wps") {
            return "做文档辛苦啦，要不要我帮你理一理结构？"
        }
        return ["我在呢，随时可以叫我。", "需要一步一步带你看，就告诉我。", "今天想先做哪件事？"].randomElement()!
    }
}
