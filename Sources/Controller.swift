import AppKit
import Foundation

enum BubbleKind { case none, coach, success, error, thinking, music }

final class AppController: NSObject, NSApplicationDelegate, NSMenuDelegate {
    // 模型
    let manifest: ClipManifest
    let player: ClipPlayer
    var settings: CoachSettings
    var session: CoachSession?
    var startedAt = Date()

    // 窗口
    var petWindow: CoachWindow!
    var petView: PetView!
    var bubbleWindow: NSWindow!
    var bubbleView: BubbleView!
    var closeWindow: CoachWindow!
    var closeView: BubbleCloseView!
    var restoreWindow: CoachWindow!
    var restoreView: RestoreView!
    var pointerLayers: [(screen: NSScreen, window: CoachWindow, view: PointerView)] = []
    var statusItem: NSStatusItem!
    var statusMenu: NSMenu!
    var server: CoachServer?
    var stageWindow: NSWindow?

    // 气泡状态
    var bubbleContent = false
    var bubbleUserHidden = false
    var bubbleAutoHidden = false
    var bubbleHideWork: DispatchWorkItem?
    var bubbleKind: BubbleKind = .none

    // 唱歌
    var singing = false
    var songTitle = ""
    var songArtist = ""
    var lyricLine = ""
    var nextLyric = ""
    var musicLastUpdate: Date?
    var focusUntil: Date?
    var quietUntil: Date?
    var lastNoteAt = Date.distantPast

    // 指针状态
    var pointerGlobal: CGPoint?
    var pointerLabel = ""
    var pointerTone: BubbleTone = .coach
    var pointerUntil: Date?
    var pointerPhase: CGFloat = 0

    // 交互 / 陪伴
    var lastCommandAt = Date()
    var lastQuipAt = Date.distantPast
    var nextIdleActionAt = Date().addingTimeInterval(50)
    var sleeping = false
    var glide: (from: NSPoint, to: NSPoint, start: CFTimeInterval, duration: Double, returnTo: NSPoint?)?

    // 计时器
    var tickTimer: Timer?
    var idleTimer: Timer?
    var lastTick = CACurrentMediaTime()
    var appObserver: NSObjectProtocol?
    var wakeObserver: NSObjectProtocol?

    let petBase = NSSize(width: 210, height: 175)
    var bubbleDrawScale: CGFloat = 1.0

    // MARK: 初始化

    init(manifest: ClipManifest) {
        self.manifest = manifest
        self.player = ClipPlayer(manifest: manifest)
        self.settings = loadSettings()
        self.session = loadSession()
        super.init()
        clampSettings()
    }

    func clampSettings() {
        let petLimits = petScaleLimits()
        settings.petScale = Double(clamp(CGFloat(settings.petScale),
                                         CGFloat(petLimits.min), CGFloat(petLimits.max)))
        let bubbleBase = NSSize(width: 336, height: 64)
        let bLimits = bubbleScaleLimits(for: bubbleBase)
        settings.bubbleScale = Double(clamp(CGFloat(settings.bubbleScale),
                                            CGFloat(bLimits.min), CGFloat(bLimits.max)))
        // 手动宽高可能是旧机器/旧屏幕留下的，按当前屏幕收进安全范围。
        let m = bubbleManualLimits()
        if let w = settings.bubbleW {
            settings.bubbleW = Double(clamp(CGFloat(w), m.minW, m.maxW))
        }
        if let h = settings.bubbleH {
            settings.bubbleH = Double(clamp(CGFloat(h), m.minH, m.maxH))
        }
        if settings.bubbleW == nil || settings.bubbleH == nil {
            settings.bubbleW = nil
            settings.bubbleH = nil
        }
    }

    // MARK: 生命周期

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        buildPet()
        buildBubble()
        buildRestoreDot()
        buildPointerLayers()
        buildMenu()
        startTimers()
        observeWorkspace()

        petWindow.orderFrontRegardless()
        if guideEnabled, let s = session, !s.steps.isEmpty, !s.finished {
            session = s
            showCurrentStep(playAnim: false)
        } else {
            session = nil
            saveSession(nil)
            hideBubble(auto: false)
            player.play("idle", loop: true, autoIdle: true)
        }
        applyVisibility()
        startServer()
        logLine("started pid=\(ProcessInfo.processInfo.processIdentifier) assets=\(Paths.assets.path) clips=\(manifest.clips.count)")
    }

    func startServer() {
        guard let server else { return }
        do {
            try server.start()
            try? "\(ProcessInfo.processInfo.processIdentifier)\n".write(to: Paths.pid, atomically: true, encoding: .utf8)
        } catch {
            let msg = "启动失败：\(error)"
            logLine(msg)
            FileHandle.standardError.write(Data((msg + "\n").utf8))
            NSApp.terminate(nil)
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        server?.stop()
        savePosition()
        saveSession(session)
        saveSettings(settings)
        try? FileManager.default.removeItem(at: Paths.pid)
        logLine("terminated")
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }

    // MARK: 构建界面

    func petSize() -> NSSize {
        NSSize(width: round(petBase.width * CGFloat(settings.petScale)),
               height: round(petBase.height * CGFloat(settings.petScale)))
    }

    func buildPet() {
        let screen = ScreenSpace.mainScreen
        let size = petSize()
        var origin = NSPoint(x: screen.visibleFrame.minX + 40, y: screen.visibleFrame.minY + 110)
        if let x = settings.petX, let y = settings.petY { origin = NSPoint(x: x, y: y) }
        origin.x = clamp(origin.x, screen.visibleFrame.minX, screen.visibleFrame.maxX - size.width)
        origin.y = clamp(origin.y, screen.visibleFrame.minY, screen.visibleFrame.maxY - size.height)

        let w = CoachWindow(contentRect: NSRect(origin: origin, size: size),
                            styleMask: .borderless, backing: .buffered, defer: false)
        w.isOpaque = false
        w.backgroundColor = .clear
        w.hasShadow = false
        w.level = .floating
        w.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        w.isReleasedWhenClosed = false
        w.isMovableByWindowBackground = false

        let v = PetView(frame: NSRect(origin: .zero, size: size))
        v.player = player
        v.onRegionClick = { [weak self] region in self?.handlePetClick(region) }
        v.onDoubleClick = { [weak self] in self?.petDance() }
        v.onDragBegin = { [weak self] in
            guard let self else { return }
            self.wake()
            self.player.play("drag", loop: true, autoIdle: false, transition: 0.12, priority: 100)
            self.petView.isDragging = true
        }
        v.onDragEnd = { [weak self] in
            guard let self else { return }
            self.petView.isDragging = false
            self.player.play("drop", loop: false, autoIdle: true, transition: 0.10, priority: 100)
            self.savePosition()
            self.repositionBubble()
            self.refreshPetPoint()
        }
        v.onContextMenu = { [weak self] p in self?.showContextMenu(at: p) }
        w.contentView = v
        petWindow = w
        petView = v
        player.prefetchEarlyFrames(3)
    }

    func buildBubble() {
        let bw = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 336, height: 100),
                          styleMask: .borderless, backing: .buffered, defer: false)
        bw.isOpaque = false
        bw.backgroundColor = .clear
        bw.hasShadow = true
        bw.ignoresMouseEvents = true
        bw.level = .floating
        bw.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        bw.isReleasedWhenClosed = false
        let bv = BubbleView(frame: NSRect(x: 0, y: 0, width: 336, height: 100))
        bw.contentView = bv
        bubbleWindow = bw
        bubbleView = bv

        let cw = CoachWindow(contentRect: NSRect(x: 0, y: 0, width: 24, height: 24),
                             styleMask: .borderless, backing: .buffered, defer: false)
        cw.isOpaque = false
        cw.backgroundColor = .clear
        cw.hasShadow = false
        cw.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 1)
        cw.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        cw.isReleasedWhenClosed = false
        let cv = BubbleCloseView(frame: NSRect(x: 0, y: 0, width: 24, height: 24))
        cv.onClick = { [weak self] in self?.hideBubbleByUser() }
        cw.contentView = cv
        closeWindow = cw
        closeView = cv
        bw.orderOut(nil)
        cw.orderOut(nil)
    }

    func buildRestoreDot() {
        let rw = CoachWindow(contentRect: NSRect(x: 0, y: 0, width: 36, height: 36),
                             styleMask: .borderless, backing: .buffered, defer: false)
        rw.isOpaque = false
        rw.backgroundColor = .clear
        rw.hasShadow = false
        rw.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 1)
        rw.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        rw.isReleasedWhenClosed = false
        let rv = RestoreView(frame: NSRect(x: 0, y: 0, width: 36, height: 36))
        rv.onClick = { [weak self] in self?.showPetByUser() }
        rw.contentView = rv
        restoreWindow = rw
        restoreView = rv
        rw.orderOut(nil)
    }

    func buildPointerLayers() {
        for layer in pointerLayers { layer.window.orderOut(nil) }
        pointerLayers.removeAll()
        for screen in NSScreen.screens {
            let w = CoachWindow(contentRect: screen.frame, styleMask: .borderless,
                                backing: .buffered, defer: false)
            w.isOpaque = false
            w.backgroundColor = .clear
            w.hasShadow = false
            w.ignoresMouseEvents = true
            w.level = .screenSaver
            w.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]
            w.isReleasedWhenClosed = false
            let v = PointerView(frame: NSRect(origin: .zero, size: screen.frame.size))
            v.screenFrame = screen.frame
            w.contentView = v
            pointerLayers.append((screen, w, v))
            w.orderFrontRegardless()
        }
        refreshPointerLayers()
        logLine("pointer layers=\(pointerLayers.count) screens=\(NSScreen.screens.count)")
    }

    // MARK: 气泡

    var petVisible: Bool { settings.petOn }
    var guideEnabled: Bool { GuideGate.allows(settings) }
    var bubbleVisible: Bool {
        settings.bubbleOn && bubbleContent && !bubbleUserHidden && !bubbleAutoHidden && settings.petOn
    }

    func showBubble(title: String, text: String, badge: String, tone: BubbleTone,
                    subtext: String = "", kind: BubbleKind = .coach,
                    total: Int = 0, done: Int = 0, index: Int = 0, hold: Double = 0,
                    force: Bool = true) {
        bubbleHideWork?.cancel()
        bubbleKind = kind
        bubbleView.compactMusic = (kind == .music)
        bubbleView.tailAtBottom = (kind == .music)
        bubbleView.alphaValue = 1.0
        bubbleView.title = title
        bubbleView.text = text
        bubbleView.subtext = subtext
        bubbleView.badge = badge
        bubbleView.tone = tone
        bubbleView.total = total
        bubbleView.doneCount = done
        bubbleView.currentIndex = index
        bubbleContent = !(text.isEmpty && title.isEmpty)
        if force && bubbleContent {
            bubbleUserHidden = false
            bubbleAutoHidden = false
        }
        layoutBubble()
        applyVisibility()
        if force && bubbleContent && kind != .music {
            bubbleView.alphaValue = 0.0
            NSAnimationContext.runAnimationGroup { ctx in
                ctx.duration = 0.12
                self.bubbleView.animator().alphaValue = 1.0
            }
        }
        if hold > 0 && bubbleContent {
            let work = DispatchWorkItem { [weak self] in
                guard let self else { return }
                self.bubbleAutoHidden = true
                self.applyVisibility()
            }
            bubbleHideWork = work
            DispatchQueue.main.asyncAfter(deadline: .now() + min(hold, 600), execute: work)
        }
    }

    func hideBubbleByUser() {
        bubbleUserHidden = true
        applyVisibility()
    }

    func showBubbleByUser() {
        bubbleUserHidden = false
        bubbleAutoHidden = false
        applyVisibility()
    }

    func hideBubble(auto: Bool) {
        bubbleContent = false
        if auto { bubbleAutoHidden = true }
        applyVisibility()
    }

    func applyVisibility() {
        let petOn = petVisible
        if petOn {
            petWindow.orderFrontRegardless()
            restoreWindow.orderOut(nil)
        } else {
            petWindow.orderOut(nil)
            let f = petWindow.frame
            restoreWindow.setFrameOrigin(NSPoint(x: f.midX - 18, y: f.midY - 18))
            restoreWindow.orderFrontRegardless()
        }
        if bubbleVisible {
            bubbleWindow.orderFrontRegardless()
            if bubbleKind == .music {
                closeWindow.orderOut(nil)
            } else {
                closeWindow.orderFrontRegardless()
            }
        } else {
            bubbleWindow.orderOut(nil)
            closeWindow.orderOut(nil)
        }
        petView.bubbleHidden = bubbleContent && !bubbleVisible
        petView.sleeping = sleeping
        petView.singing = singing
        petView.reducedMotion = settings.reducedMotion ?? false
        if !petOn {
            clearPointer(orderOut: true)
            bubbleWindow.orderOut(nil)
            closeWindow.orderOut(nil)
        }
    }

    func stopMusicDisplay() {
        singing = false
        musicLastUpdate = nil
        songTitle = ""
        songArtist = ""
        lyricLine = ""
        nextLyric = ""
        petView.singing = false
        if bubbleKind == .music {
            bubbleContent = false
            bubbleKind = .none
            applyVisibility()
        }
    }

    // MARK: 指针

    func showPointer(topLeft: CGPoint, label: String, hold: Double, tone: BubbleTone) {
        guard guideEnabled else {
            logLine("pointer blocked: guide mode off")
            return
        }
        let appKit = ScreenSpace.toAppKit(topLeft)
        pointerGlobal = appKit
        pointerLabel = label
        pointerTone = tone
        pointerUntil = hold > 0 ? Date().addingTimeInterval(hold) : nil
        refreshPointerLayers()
        for layer in pointerLayers { layer.window.orderFrontRegardless() }
        logLine("pointer \(Int(topLeft.x)),\(Int(topLeft.y)) label=\(label)")
    }

    func clearPointer(orderOut: Bool = true) {
        pointerGlobal = nil
        pointerUntil = nil
        pointerLabel = ""
        for layer in pointerLayers {
            layer.view.targetGlobal = nil
            layer.view.needsDisplay = true
            if orderOut { layer.window.orderOut(nil) }
        }
    }

    func refreshPointerLayers() {
        let pet = petWindow?.frame
        let petPoint = pet.map { NSPoint(x: $0.midX, y: $0.maxY - 10) }
        for layer in pointerLayers {
            layer.view.targetGlobal = pointerGlobal
            layer.view.petGlobal = petPoint
            layer.view.label = pointerLabel
            layer.view.tone = pointerTone
            layer.view.phase = pointerPhase
            layer.view.needsDisplay = true
            if pointerGlobal == nil { layer.window.orderOut(nil) }
            else { layer.window.orderFrontRegardless() }
        }
    }

    func refreshPetPoint() {
        let pet = petWindow?.frame
        let petPoint = pet.map { NSPoint(x: $0.midX, y: $0.maxY - 10) }
        for layer in pointerLayers { layer.view.petGlobal = petPoint; layer.view.needsDisplay = true }
    }

    // MARK: 步骤 / 指导

    /// 指引模式总开关。关闭时立刻清空任务、指针与任务气泡，回到空闲。
    func setGuideEnabled(_ on: Bool, announce: Bool = true) {
        wake()
        settings.guideEnabled = on
        saveSettings(settings)
        if on {
            logLine("guide mode on")
            if announce, bubbleKind != .music {
                showBubble(title: "任务指导", text: "指引模式已开启。需要时我会一步一步带你做。",
                           badge: "已开启", tone: .success, hold: 4)
            }
            return
        }
        let hadTask = session != nil
        session = nil
        saveSession(nil)
        clearPointer()
        if !singing {
            player.play("idle", loop: true, autoIdle: true, transition: 0.18, priority: 90, force: true)
        }
        logLine("guide mode off clearedTask=\(hadTask)")
        if announce, bubbleKind != .music {
            showBubble(title: "任务指导",
                       text: hadTask ? "指引模式已关闭，当前任务已清空，我先安静待着。" : "指引模式已关闭，我先安静待着。要再开启就在菜单里勾上。",
                       badge: "已关闭", tone: .coach, hold: 4)
        } else if !announce, bubbleKind == .coach {
            bubbleKind = .none
            hideBubble(auto: false)
        }
    }

    @discardableResult
    func startGuide(title: String, steps: [CoachStep], start: Int, agent: String) -> Bool {
        guard guideEnabled, !steps.isEmpty else { return false }
        singing = false
        petView.singing = false
        var s = CoachSession(title: title, steps: steps, index: start,
                             done: Array(repeating: false, count: steps.count),
                             agent: agent)
        s.normalize()
        session = s
        saveSession(s)
        showCurrentStep(playAnim: true)
        logLine("guide start title=\(title) steps=\(steps.count)")
        return true
    }

    func showCurrentStep(playAnim: Bool) {
        guard let s = session, let step = s.current else { return }
        let hint = (step.hint?.isEmpty == false) ? "\n提示：\(step.hint!)" : ""
        showBubble(title: s.title,
                   text: step.text + hint,
                   badge: "第 \(s.progressText) 步",
                   tone: .coach,
                   total: s.total,
                   done: StepLogic.completedCount(s),
                   index: s.index,
                   hold: 0)
        if let x = step.x, let y = step.y {
            showPointer(topLeft: CGPoint(x: x, y: y), label: step.label ?? "点这里", hold: 0, tone: .coach)
            player.play("point", loop: true, autoIdle: false, transition: 0.16, priority: 70)
        } else {
            clearPointer()
            if playAnim {
                player.play("pat", loop: false, autoIdle: true, transition: 0.16, priority: 60)
                petView.burstHearts(count: 3)
            } else {
                player.play("talk", loop: true, autoIdle: true, transition: 0.16, priority: 50)
            }
        }
    }

    func advanceStep(say: String?) {
        guard var s = session, !s.steps.isEmpty else { return }
        if s.finished {
            showBubble(title: "已经完成啦", text: "这个任务的所有步骤都完成了。要开始新的任务就再叫我。",
                       badge: "完成", tone: .success, total: s.total, done: s.total, index: s.total, hold: 8)
            return
        }
        let finishedNow = StepLogic.advance(&s)
        session = s
        saveSession(s)
        if finishedNow {
            finishGuide()
            return
        }
        wake()
        if let say, !say.isEmpty {
            guard let step = s.current else { return }
            player.play("pat", loop: false, autoIdle: true, transition: 0.16, priority: 60)
            petView.burstHearts(count: 4)
            showBubble(title: s.title, text: say, badge: "第 \(s.progressText) 步", tone: .coach,
                       total: s.total, done: StepLogic.completedCount(s), index: s.index, hold: 0)
            if let x = step.x, let y = step.y {
                showPointer(topLeft: CGPoint(x: x, y: y), label: step.label ?? "点这里", hold: 0, tone: .coach)
            } else { clearPointer() }
        } else {
            showCurrentStep(playAnim: true)
        }
    }

    func rewindStep() {
        guard var s = session, !s.steps.isEmpty else { return }
        StepLogic.rewind(&s)
        session = s
        saveSession(s)
        wake()
        showCurrentStep(playAnim: true)
    }

    func finishGuide() {
        guard var s = session else { return }
        let title = s.title.isEmpty ? "这个任务" : "「\(s.title)」"
        let total = s.total
        s.finished = true
        s.index = total
        s.done = Array(repeating: true, count: total)
        s.updatedAt = Date().timeIntervalSince1970
        session = s
        saveSession(s)
        singing = false
        petView.singing = false
        clearPointer()
        player.play("success", loop: false, autoIdle: true, transition: 0.18, priority: 80)
        petView.burstConfetti(count: 30)
        petView.burstHearts(count: 6)
        showBubble(title: "完成！",
                   text: "\(title)全部 \(total) 步都完成了，辛苦啦。需要我继续时再叫我。",
                   badge: "完成 \(total)/\(total)",
                   tone: .success, kind: .success, total: total, done: total, index: total, hold: 12)
    }

    func cancelGuide(text: String? = nil) {
        session = nil
        saveSession(nil)
        clearPointer()
        player.play("talk", loop: true, autoIdle: true)
        showBubble(title: "", text: text ?? "好，先做到这里。我不催你，歇一会儿也行。",
                   badge: "", tone: .coach, hold: 6)
    }

    // MARK: 互动

    func handlePetClick(_ region: PetRegion) {
        wake()
        if !bubbleVisible && bubbleContent {
            showBubbleByUser()
            player.play("talk", loop: true, autoIdle: true)
            return
        }
        switch region {
        case .head:
            player.play("pat", loop: false, autoIdle: true, transition: 0.16, priority: 60)
            petView.burstHearts(count: 5)
            if session == nil && bubbleKind != .music { showBubble(title: "", text: "嘿嘿，摸头最舒服了。", badge: "", tone: .coach, hold: 4) }
        case .body:
            player.play("poke", loop: false, autoIdle: true, transition: 0.14, priority: 60)
            if session == nil && bubbleKind != .music { showBubble(title: "", text: "呀！被戳到了。要帮忙就叫我一声。", badge: "", tone: .coach, hold: 4) }
        case .tail:
            player.play("tail", loop: false, autoIdle: true, transition: 0.14, priority: 60)
            if session == nil && bubbleKind != .music { showBubble(title: "", text: "尾巴不能乱碰啦～", badge: "", tone: .coach, hold: 3.5) }
        }
    }

    func wake() {
        lastCommandAt = Date()
        if sleeping {
            sleeping = false
            player.play("idle", loop: true, autoIdle: true)
            petView.sleeping = false
        }
        nextIdleActionAt = Date().addingTimeInterval(Double.random(in: 55...120))
    }

    // MARK: 移动 / 缩放

    func savePosition() {
        guard let w = petWindow else { return }
        settings.petX = Double(w.frame.origin.x)
        settings.petY = Double(w.frame.origin.y)
        saveSettings(settings)
    }

    func resetPosition() {
        let screen = ScreenSpace.mainScreen
        let size = petSize()
        let origin = NSPoint(x: screen.visibleFrame.minX + 40,
                             y: screen.visibleFrame.minY + 110)
        petWindow.setFrame(NSRect(origin: origin, size: size), display: true)
        savePosition()
        repositionBubble()
        refreshPetPoint()
    }

    func showPetByUser() {
        settings.petOn = true
        bubbleUserHidden = false
        bubbleAutoHidden = false
        saveSettings(settings)
        applyVisibility()
    }

    func hidePetByUser() {
        settings.petOn = false
        saveSettings(settings)
        applyVisibility()
    }

    // MARK: 计时器

    func startTimers() {
        let t = Timer(timeInterval: 1.0 / 24.0, repeats: true) { [weak self] _ in self?.tick() }
        RunLoop.main.add(t, forMode: .common)
        tickTimer = t
        let i = Timer(timeInterval: 1.0, repeats: true) { [weak self] _ in self?.idleTick() }
        RunLoop.main.add(i, forMode: .common)
        idleTimer = i
    }

    func tick() {
        let now = CACurrentMediaTime()
        let dt = min(0.2, max(0, now - lastTick))
        lastTick = now
        pointerPhase += CGFloat(dt) * 2.1
        petView.phase += CGFloat(dt) * 1.1
        if petView.pulse > 0 { petView.pulse = max(0, petView.pulse - CGFloat(dt) * 2.4) }
        petView.tickEffects(CGFloat(dt))
        if singing, Date().timeIntervalSince(lastNoteAt) > 0.55 {
            lastNoteAt = Date()
            petView.spawnNote()
        }
        // 被拖拽/一次性动作压住后，音乐还在就恢复唱歌（不抢正在播的高优先级动作）
        if singing, !petView.isDragging, pointerGlobal == nil, !player.busy,
           player.currentPriority <= 85, player.resolvedName != "sing" {
            player.play("sing", loop: true, autoIdle: true, transition: 0.20, priority: 85)
        }

        if let g = glide {
            let t = min(1, (now - g.start) / g.duration)
            let e = 1 - pow(1 - t, 3)
            let origin = NSPoint(x: g.from.x + (g.to.x - g.from.x) * e,
                                 y: g.from.y + (g.to.y - g.from.y) * e)
            petWindow.setFrameOrigin(origin)
            repositionBubble()
            refreshPetPoint()
            if t >= 1 {
                glide = nil
                player.play("pat", loop: false, autoIdle: true)
                petView.burstHearts(count: 3)
                if let back = g.returnTo {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 6.5) { [weak self] in
                        guard let self, self.glide == nil, Date().timeIntervalSince(self.lastCommandAt) > 5 else { return }
                        self.glide = (self.petWindow.frame.origin, back, CACurrentMediaTime(), 1.0, nil)
                        self.player.play("working", loop: true, autoIdle: true)
                    }
                }
            }
        }

        if petVisible && petWindow.occlusionState.contains(.visible) {
            if player.tick() { petView.needsDisplay = true }
        }
        if pointerGlobal != nil {
            for layer in pointerLayers {
                layer.view.phase = pointerPhase
                layer.view.needsDisplay = true
            }
            if let until = pointerUntil, Date() >= until { clearPointer() }
        }
    }

    // MARK: 命令

    func handle(_ cmd: [String: Any]) -> [String: Any] {
        wake()
        let name = (cmd["cmd"] as? String) ?? ""
        switch name {
        case "ping":
            return ["ok": true, "pong": true, "version": kVersion, "pid": ProcessInfo.processInfo.processIdentifier]

        case "status", "info":
            return statusPayload()

        case "hello":
            let agent = (cmd["agent"] as? String) ?? "agent"
            settings.lastAgent = agent
            saveSettings(settings)
            session = nil
            saveSession(nil)
            clearPointer()
            player.play("pat", loop: false, autoIdle: true)
            petView.burstHearts(count: 4)
            if guideEnabled {
                showBubble(title: "大肥鱼在听", text: "我是大肥鱼。接下来我会一步一步说给你听；需要指哪里，我就游过去。",
                           badge: "\(agent) 已连接", tone: .coach, hold: 8)
            } else {
                showBubble(title: "大肥鱼在听", text: "我在。不过指引模式关着，需要任务指导请先在菜单里打开。",
                           badge: "\(agent) 已连接 · 指引已关", tone: .coach, hold: 6)
            }
            logLine("hello agent=\(agent) guideEnabled=\(guideEnabled)")
            return ["ok": true, "agent": agent, "message": "connected", "guideEnabled": guideEnabled]

        case "bye", "end":
            session = nil
            saveSession(nil)
            clearPointer()
            showBubble(title: "", text: "那我先安静陪你。想继续的时候再叫我。", badge: "", tone: .coach, hold: 5)
            player.play("idle", loop: true, autoIdle: true)
            return ["ok": true]

        case "say":
            guard let text = cmd["text"] as? String, !text.isEmpty else {
                return ["ok": false, "error": "say 需要 text"]
            }
            let title = (cmd["title"] as? String) ?? ""
            let badge = (cmd["step"] as? String) ?? ""
            let hold = (cmd["hold"] as? Double) ?? 0
            let tone = bubbleTone(cmd["tone"] as? String)
            showBubble(title: title, text: text, badge: badge, tone: tone, hold: hold)
            if let anim = cmd["anim"] as? String, !anim.isEmpty {
                player.play(anim, loop: false, autoIdle: true)
            } else {
                player.play("talk", loop: false, autoIdle: true)
            }
            return ["ok": true]

        case "point":
            guard guideEnabled else {
                return ["ok": false, "error": GuideGate.disabledMessage, "guideEnabled": false]
            }
            guard let x = num(cmd["x"]), let y = num(cmd["y"]) else {
                return ["ok": false, "error": "point 需要 x / y"]
            }
            let unit = (cmd["unit"] as? String) ?? "pt"
            var p = CGPoint(x: x, y: y)
            var scaleNote: Double? = nil
            if unit == "norm" {
                p = ScreenSpace.normalized(Double(x), Double(y))
            } else if unit == "px" {
                let s = (cmd["scale"] as? Double) ?? Double(ScreenSpace.mainScreen.backingScaleFactor)
                p = CGPoint(x: x / s, y: y / s)
                scaleNote = s
            }
            let label = (cmd["label"] as? String) ?? ""
            let hold = (cmd["hold"] as? Double) ?? 10
            showPointer(topLeft: p, label: label, hold: hold, tone: bubbleTone(cmd["tone"] as? String))
            if (cmd["anim"] as? String) == nil {
                player.play("point", loop: true, autoIdle: false, transition: 0.16, priority: 70)
            } else if let a = cmd["anim"] as? String { player.play(a, loop: false, autoIdle: true) }
            var r: [String: Any] = ["ok": true, "x": p.x, "y": p.y]
            if let s = scaleNote { r["scale"] = s }
            return r

        case "clear_point":
            clearPointer()
            return ["ok": true]

        case "guide":
            guard guideEnabled else {
                return ["ok": false, "error": GuideGate.disabledMessage, "guideEnabled": false]
            }
            let title = (cmd["title"] as? String) ?? ""
            let raw = (cmd["steps"] as? [[String: Any]]) ?? []
            var steps: [CoachStep] = []
            for item in raw {
                if let t = item["text"] as? String {
                    steps.append(CoachStep(text: t,
                                           hint: item["hint"] as? String,
                                           x: num(item["x"]), y: num(item["y"]),
                                           label: item["label"] as? String))
                }
            }
            guard !steps.isEmpty else { return ["ok": false, "error": "guide 需要至少一个 steps[].text"] }
            let start = Int((cmd["start"] as? Double) ?? 0)
            startGuide(title: title, steps: steps, start: max(0, start), agent: (cmd["agent"] as? String) ?? settings.lastAgent)
            var r = statusPayload()
            r["ok"] = true
            r["guide"] = title
            return r

        case "next":
            guard session != nil else { return ["ok": false, "error": "当前没有进行中的 guide"] }
            advanceStep(say: cmd["say"] as? String)
            var r = statusPayload(); r["ok"] = true; return r

        case "prev":
            guard session != nil else { return ["ok": false, "error": "当前没有进行中的 guide"] }
            rewindStep()
            var r = statusPayload(); r["ok"] = true; return r

        case "finish":
            guard session != nil else { return ["ok": false, "error": "当前没有进行中的 guide"] }
            finishGuide()
            var r = statusPayload(); r["ok"] = true; return r

        case "cancel":
            cancelGuide(text: cmd["text"] as? String)
            return ["ok": true]

        case "music_start":
            songTitle = (cmd["title"] as? String) ?? ""
            songArtist = (cmd["artist"] as? String) ?? ""
            guard session == nil, !settings.quiet, settings.petOn, (settings.sing ?? true),
                  !isMeetingFrontmost() else {
                return ["ok": true, "suppressed": true]
            }
            wake()
            singing = true
            musicLastUpdate = Date()
            petView.singing = true
            player.play("sing", loop: true, autoIdle: true, transition: 0.22, priority: 85)
            showBubble(title: songArtist.isEmpty ? songTitle : "\(songTitle) · \(songArtist)",
                       text: "准备开唱…", badge: "♪", tone: .music, kind: .music, hold: 0)
            return ["ok": true, "singing": true]

        case "lyric":
            let title = (cmd["title"] as? String) ?? songTitle
            let artist = (cmd["artist"] as? String) ?? songArtist
            let line = (cmd["line"] as? String) ?? ""
            let next = (cmd["next"] as? String) ?? ""
            songTitle = title
            songArtist = artist
            lyricLine = line
            nextLyric = next
            guard session == nil, !settings.quiet, settings.petOn, (settings.sing ?? true),
                  !isMeetingFrontmost() else {
                return ["ok": true, "suppressed": true]
            }
            if !singing {
                wake()
                singing = true
                petView.singing = true
                player.play("sing", loop: true, autoIdle: true, transition: 0.22, priority: 85)
            }
            musicLastUpdate = Date()
            let total = (cmd["total"] as? Double).map { Int($0) } ?? 0
            let index = (cmd["index"] as? Double).map { Int($0) } ?? 0
            let badge = total > 0 ? "♪ \(min(index + 1, total))/\(total)" : "♪"
            showBubble(title: artist.isEmpty ? title : "\(title) · \(artist)",
                       text: line.isEmpty ? "♪ 跟着哼" : line,
                       badge: badge, tone: .music, subtext: "", kind: .music, hold: 0)
            petView.spawnNote()
            return ["ok": true, "singing": true]

        case "music_stop":
            stopMusicDisplay()
            player.play("idle", loop: true, autoIdle: true)
            return ["ok": true]

        case "music_status":
            var r = statusPayload()
            r["ok"] = true
            return r

        case "play":
            guard let clip = cmd["clip"] as? String, !clip.isEmpty else {
                return ["ok": false, "error": "play 需要 clip"]
            }
            player.play(clip, loop: false, autoIdle: true, transition: 0.16, priority: 90, force: true)
            let actual = player.currentName
            let actualResolved: String
            switch actual {
            case "talk": actualResolved = "idle"
            case "point": actualResolved = "working"
            case "celebrate", "dance", "cheer": actualResolved = "success"
            case "greet", "wave", "happy": actualResolved = "pat"
            case "snack": actualResolved = "eat"
            case "sleepy": actualResolved = "yawn"
            default: actualResolved = actual
            }
            if actualResolved == "success" { petView.burstConfetti(count: 24); petView.burstHearts(count: 4) }
            if let text = cmd["text"] as? String, !text.isEmpty {
                showBubble(title: (cmd["title"] as? String) ?? "", text: text,
                           badge: (cmd["step"] as? String) ?? "", tone: bubbleTone(cmd["tone"] as? String), hold: (cmd["hold"] as? Double) ?? 0)
            }
            return ["ok": true, "clip": clip, "resolved": manifest.clips[actualResolved] != nil ? actualResolved : "idle"]

        case "mood":
            let mood = (cmd["value"] as? String) ?? "idle"
            let clip: String
            switch mood {
            case "happy": clip = "pat"
            case "think", "thinking": clip = "thinking"
            case "focus", "working": clip = "working"
            case "sleepy": clip = "yawn"
            case "error": clip = "error"
            default: clip = "idle"
            }
            player.play(clip, loop: ["idle", "thinking", "working"].contains(clip), autoIdle: true)
            return ["ok": true, "mood": mood, "clip": clip]

        case "stage":
            if bool(cmd["on"], default: true) { showStage() } else { hideStage() }
            return ["ok": true, "stage": stageWindow != nil]

        case "hide":
            hidePetByUser()
            return ["ok": true]

        case "show":
            showPetByUser()
            return ["ok": true]

        case "quiet":
            settings.quiet = bool(cmd["on"], default: true)
            let minutes = num(cmd["minutes"]) ?? 0
            quietUntil = (settings.quiet && minutes > 0) ? Date().addingTimeInterval(minutes * 60) : nil
            saveSettings(settings)
            if settings.quiet { session = nil; saveSession(nil); clearPointer(); stopMusicDisplay() }
            applyVisibility()
            return ["ok": true, "quiet": settings.quiet,
                    "quietRemaining": quietUntil.map { max(0, Int($0.timeIntervalSinceNow)) } ?? 0]

        case "config":
            if let v = num(cmd["petScale"]) { setPetScale(v) }
            if let v = num(cmd["bubbleScale"]) { setBubbleScale(v) }
            if let w = num(cmd["bubbleW"]), let h = num(cmd["bubbleH"]) { setBubbleSize(width: w, height: h) }
            if bool(cmd["bubbleAuto"], default: false) { resetBubbleSize() }
            if let g = cmd["guideEnabled"] as? Bool { setGuideEnabled(g) }
            if let v = cmd["quiet"] as? Bool { settings.quiet = v }
            if let v = cmd["playful"] as? Bool { settings.playful = v }
            if let v = cmd["bubbleOn"] as? Bool { settings.bubbleOn = v }
            if let v = cmd["petOn"] as? Bool { settings.petOn = v }
            if let v = cmd["sing"] as? Bool { settings.sing = v }
            if let v = cmd["reducedMotion"] as? Bool { settings.reducedMotion = v }
            saveSettings(settings)
            applyVisibility()
            return statusPayload()

        case "feed":
            feed()
            return ["ok": true]

        case "focus":
            if (cmd["cancel"] as? Bool) == true {
                cancelFocus()
            } else {
                startFocus(minutes: num(cmd["minutes"]) ?? 25)
            }
            return ["ok": true, "focusRemaining": focusUntil.map { max(0, Int($0.timeIntervalSinceNow)) } ?? 0]

        case "focus_cancel":
            cancelFocus()
            return ["ok": true]

        case "dance":
            petDance()
            return ["ok": true]

        case "quip":
            quipNow()
            return ["ok": true]

        case "come":
            comeHere()
            return ["ok": true]

        case "move":
            guard let x = num(cmd["x"]), let y = num(cmd["y"]) else { return ["ok": false, "error": "move 需要 x/y"] }
            let p = ScreenSpace.toAppKit(CGPoint(x: x, y: y))
            let screen = ScreenSpace.screen(containing: p)
            let size = petWindow.frame.size
            var o = NSPoint(x: p.x - size.width / 2, y: p.y - size.height / 2)
            o.x = clamp(o.x, screen.visibleFrame.minX, screen.visibleFrame.maxX - size.width)
            o.y = clamp(o.y, screen.visibleFrame.minY, screen.visibleFrame.maxY - size.height)
            petWindow.setFrameOrigin(o)
            savePosition()
            repositionBubble()
            refreshPetPoint()
            return ["ok": true]

        case "demo":
            guard runDemo() else {
                return ["ok": false, "error": GuideGate.disabledMessage, "guideEnabled": false]
            }
            return ["ok": true, "demo": true]

        case "quit":
            saveSession(session)
            saveSettings(settings)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) { NSApp.terminate(nil) }
            return ["ok": true, "quitting": true]

        default:
            return ["ok": false, "error": "未知命令: \(name)"]
        }
    }

    @discardableResult
    func runDemo() -> Bool {
        guard guideEnabled else {
            showBubble(title: "任务指导", text: "指引模式关着。先在菜单里打开「任务指导（指引模式）」，我就能演示了。",
                       badge: "已关闭", tone: .coach, hold: 5)
            return false
        }
        let oldQuiet = settings.quiet
        let oldPlayful = settings.playful
        settings.quiet = false
        settings.playful = false
        session = nil
        player.play("pat", loop: false, autoIdle: true)
        showBubble(title: "大肥鱼 Coach", text: "演示开始：我会先打个招呼，然后一步一步带你做。",
                   badge: "demo", tone: .coach, hold: 3)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.6) { [weak self] in
            guard let self, self.guideEnabled else { return }
            let screen = ScreenSpace.mainScreen.frame
            let steps = [
                CoachStep(text: "先看这个红色圆环。它指着屏幕上要点的位置，气泡里写的是这一步要做什么。",
                          x: Double(screen.minX + screen.width * 0.62),
                          y: Double(screen.height * 0.30),
                          label: "点这里试试"),
                CoachStep(text: "做完一步，Agent 会让我跳到下一步（点右下角的圆点可以看到进度）。",
                          x: Double(screen.minX + screen.width * 0.38),
                          y: Double(screen.height * 0.52),
                          label: "第二步"),
                CoachStep(text: "最后我会撒花庆祝，然后安静地陪你待着。"),
            ]
            self.startGuide(title: "桌面大肥鱼 · 三步演示", steps: steps, start: 0, agent: "demo")
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 9.0) { [weak self] in self?.advanceStep(say: nil) }
        DispatchQueue.main.asyncAfter(deadline: .now() + 15.0) { [weak self] in self?.advanceStep(say: nil) }
        DispatchQueue.main.asyncAfter(deadline: .now() + 20.0) { [weak self] in self?.finishGuide() }
        DispatchQueue.main.asyncAfter(deadline: .now() + 22.0) { [weak self] in
            guard let self else { return }
            self.settings.quiet = oldQuiet
            self.settings.playful = oldPlayful
        }
        return true
    }

}
