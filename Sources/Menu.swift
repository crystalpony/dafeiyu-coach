import AppKit
import Foundation

// 菜单栏与右键菜单。放在扩展里，避免主控制器过长。
extension AppController {
    // MARK: 菜单

    func buildMenu() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let b = statusItem.button {
            let img = NSImage(systemSymbolName: "fish.fill", accessibilityDescription: "大肥鱼 Coach")
                ?? NSImage(systemSymbolName: "fish", accessibilityDescription: "大肥鱼 Coach")
            img?.isTemplate = true
            b.image = img
            b.imagePosition = .imageLeading
            b.title = "大肥鱼"
            b.font = NSFont.systemFont(ofSize: 11.5, weight: .medium)
            b.toolTip = "桌面大肥鱼 Coach"
        }
        statusMenu = NSMenu()
        statusMenu.delegate = self
        statusItem.menu = statusMenu
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        if menu === statusMenu { populate(menu) }
    }

    func populate(_ menu: NSMenu) {
        menu.removeAllItems()
        func item(_ title: String, _ action: Selector?, _ key: String = "") -> NSMenuItem {
            let it = NSMenuItem(title: title, action: action, keyEquivalent: key)
            it.target = self
            return it
        }
        menu.addItem(item(bubbleVisible ? "收起气泡" : "显示气泡", #selector(menuToggleBubble)))
        menu.addItem(item(settings.petOn ? "隐藏桌宠" : "显示桌宠", #selector(menuTogglePet)))
        menu.addItem(.separator())
        let quiet = item("安静模式（不主动搭话）", #selector(menuToggleQuiet))
        quiet.state = settings.quiet ? .on : .off
        menu.addItem(quiet)
        let playful = item("互动陪伴（靠近鼠标 / 应用反应）", #selector(menuTogglePlayful))
        playful.state = settings.playful ? .on : .off
        menu.addItem(playful)
        let sing = item("放歌时跟着唱", #selector(menuToggleSing))
        sing.state = (settings.sing ?? true) ? .on : .off
        menu.addItem(sing)
        menu.addItem(item("会议模式 60 分钟", #selector(menuMeeting)))
        let reduced = item("减少动态（关闭摇摆/音符）", #selector(menuToggleReduced))
        reduced.state = (settings.reducedMotion ?? false) ? .on : .off
        menu.addItem(reduced)
        menu.addItem(.separator())
        menu.addItem(item("摸摸头", #selector(menuPat)))
        menu.addItem(item("添一碗米饭", #selector(menuFeed)))
        menu.addItem(item("专注 25 分钟", #selector(menuFocus)))
        menu.addItem(item("取消专注", #selector(menuCancelFocus)))
        menu.addItem(item("跳个舞", #selector(menuDance)))
        menu.addItem(item("游到鼠标边", #selector(menuCome)))
        menu.addItem(.separator())
        let sizeMenu = NSMenuItem(title: "桌宠大小", action: nil, keyEquivalent: "")
        let sizeSub = NSMenu()
        for v in [0.8, 1.0, 1.25, 1.5] {
            let it = NSMenuItem(title: "\(Int(v * 100))%", action: #selector(menuSetPetScale(_:)), keyEquivalent: "")
            it.target = self
            it.representedObject = v
            it.state = abs(settings.petScale - v) < 0.01 ? .on : .off
            sizeSub.addItem(it)
        }
        sizeMenu.submenu = sizeSub
        menu.addItem(sizeMenu)
        let bMenu = NSMenuItem(title: "气泡大小", action: nil, keyEquivalent: "")
        let bSub = NSMenu()
        for v in [0.9, 1.0, 1.2] {
            let it = NSMenuItem(title: "\(Int(v * 100))%", action: #selector(menuSetBubbleScale(_:)), keyEquivalent: "")
            it.target = self
            it.representedObject = v
            it.state = abs(settings.bubbleScale - v) < 0.01 ? .on : .off
            bSub.addItem(it)
        }
        bMenu.submenu = bSub
        menu.addItem(bMenu)
        menu.addItem(item("重置位置", #selector(menuReset)))
        menu.addItem(.separator())
        menu.addItem(item("三步演示", #selector(menuDemo)))
        menu.addItem(item("关于大肥鱼 Coach", #selector(menuAbout)))
        menu.addItem(item("退出", #selector(menuQuit), "q"))
    }

    func showContextMenu(at point: NSPoint) {
        let menu = NSMenu()
        populate(menu)
        menu.popUp(positioning: nil, at: point, in: nil)
    }

    @objc func menuToggleBubble() {
        if bubbleVisible { hideBubbleByUser() } else { showBubbleByUser() }
    }
    @objc func menuTogglePet() {
        if settings.petOn { hidePetByUser() } else { showPetByUser() }
    }
    @objc func menuToggleQuiet() {
        settings.quiet.toggle(); saveSettings(settings)
        if settings.quiet { session = nil; saveSession(nil); clearPointer() }
    }
    @objc func menuTogglePlayful() { settings.playful.toggle(); saveSettings(settings) }
    @objc func menuToggleReduced() {
        settings.reducedMotion = !(settings.reducedMotion ?? false)
        saveSettings(settings)
        petView.reducedMotion = settings.reducedMotion ?? false
        petView.needsDisplay = true
    }

    @objc func menuMeeting() {
        settings.quiet = true
        quietUntil = Date().addingTimeInterval(3600)
        saveSettings(settings)
        session = nil; saveSession(nil); clearPointer(); stopMusicDisplay()
        showBubble(title: "", text: "会议模式：1 小时内我不主动说话，也不唱歌。", badge: "安静", tone: .thinking, hold: 5)
    }

    @objc func menuToggleSing() {
        settings.sing = !(settings.sing ?? true)
        saveSettings(settings)
        if settings.sing == false { stopMusicDisplay() }
    }
    @objc func menuPat() { handlePetClick(.head) }
    @objc func menuFeed() { feed() }
    @objc func menuFocus() { startFocus(minutes: 25) }
    @objc func menuCancelFocus() { cancelFocus() }
    @objc func menuDance() { petDance() }
    @objc func menuCome() { comeHere() }
    @objc func menuSetPetScale(_ sender: NSMenuItem) {
        if let v = sender.representedObject as? Double { setPetScale(v) }
    }
    @objc func menuSetBubbleScale(_ sender: NSMenuItem) {
        if let v = sender.representedObject as? Double { setBubbleScale(v) }
    }
    @objc func menuReset() { resetPosition() }
    @objc func menuDemo() { runDemo() }
    @objc func menuQuit() { NSApp.terminate(nil) }
    @objc func menuAbout() {
        let assets = Paths.assets
        var size = 0
        if let e = FileManager.default.enumerator(at: assets, includingPropertiesForKeys: [.fileSizeKey]) {
            for case let u as URL in e {
                if let n = try? u.resourceValues(forKeys: [.fileSizeKey]).fileSize { size += n }
            }
        }
        let alert = NSAlert()
        alert.messageText = "桌面大肥鱼 Coach \(kVersion)"
        alert.informativeText = """
        独立版桌宠：agent 通过 skills / CLI / MCP 调用，指针 + 气泡 + 15 段动画。
        动画素材 \(manifest.clips.count) 组，\(String(format: "%.1f", Double(size) / 1048576)) MB。
        Socket: \(Paths.socket.path)
        配置: \(Paths.home.path)
        """
        alert.addButton(withTitle: "好")
        NSApp.activate(ignoringOtherApps: true)
        alert.runModal()
    }
}
