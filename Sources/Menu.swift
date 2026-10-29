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
        refreshStatusItem()
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
        // 互动与专注
        let interactMenu = NSMenuItem(title: "互动与专注", action: nil, keyEquivalent: "")
        let interactSub = NSMenu()
        interactSub.addItem(item("摸摸头", #selector(menuPat)))
        interactSub.addItem(item("添一碗米饭", #selector(menuFeed)))
        interactSub.addItem(item("专注 25 分钟", #selector(menuFocus)))
        interactSub.addItem(item("取消专注", #selector(menuCancelFocus)))
        interactSub.addItem(item("跳个舞", #selector(menuDance)))
        interactSub.addItem(item(manifest.character == "xiaohei" ? "跑到鼠标边" : "游到鼠标边", #selector(menuCome)))
        if currentCharacter == "xiaohei" {
            interactSub.addItem(.separator())
            let petMenu = NSMenuItem(title: "小黑互动", action: nil, keyEquivalent: "")
            let petSub = NSMenu()
            for (title, clip) in [("眯眼摇头", "wash"), ("躺着晃晃", "roll"), ("蓄势一下", "pounce"),
                                  ("受惊停顿", "fluff"), ("和黑咻玩", "heixiu"), ("喵一声", "meow"),
                                  ("喵两声", "meow2"), ("喂条小鱼", "fish")] {
                let it = item(title, #selector(menuXiaoheiAction(_:)))
                it.representedObject = clip
                petSub.addItem(it)
            }
            petSub.addItem(.separator())
            let sleepItem = item(sleeping ? "叫醒小黑" : "睡觉",
                                 sleeping ? #selector(menuWake) : #selector(menuXiaoheiAction(_:)))
            sleepItem.representedObject = "sleep"
            petSub.addItem(sleepItem)
            petMenu.submenu = petSub
            interactSub.addItem(petMenu)
        }
        interactMenu.submenu = interactSub
        menu.addItem(interactMenu)

        // 小黑日常：小动作 / 玩耍 / 吃什么 / 时节 / 移动 / 碎碎念 / 工作状态
        if currentCharacter == "xiaohei" {
            let dailyMenu = NSMenuItem(title: "小黑日常", action: nil, keyEquivalent: "")
            let dailySub = NSMenu()

            let smallMenu = NSMenuItem(title: "小动作", action: nil, keyEquivalent: "")
            let smallSub = NSMenu()
            for (title, clip) in [("伸懒腰", "stretch"), ("困倦眯眼", "yawn"), ("摇尾巴", "tail")] {
                let it = item(title, #selector(menuDailyAction(_:)))
                it.representedObject = clip
                smallSub.addItem(it)
            }
            smallMenu.submenu = smallSub
            dailySub.addItem(smallMenu)

            let playMenu = NSMenuItem(title: "玩耍", action: nil, keyEquivalent: "")
            let playSub = NSMenu()
            for (title, clip) in [("蓄势一下", "pounce"), ("受惊停顿", "fluff"), ("和黑咻玩", "heixiu")] {
                let it = item(title, #selector(menuDailyAction(_:)))
                it.representedObject = clip
                playSub.addItem(it)
            }
            playMenu.submenu = playSub
            dailySub.addItem(playMenu)

            let eatMenu = NSMenuItem(title: "吃什么", action: nil, keyEquivalent: "")
            let eatSub = NSMenu()
            let fish = item("小鱼干", #selector(menuXiaoheiAction(_:)))
            fish.representedObject = "fish"
            eatSub.addItem(fish)
            eatSub.addItem(item("米饭", #selector(menuFeed)))
            let cake = item("月饼", #selector(menuFestival(_:)))
            cake.representedObject = "midautumn"
            eatSub.addItem(cake)
            let zongzi = item("粽子", #selector(menuFestival(_:)))
            zongzi.representedObject = "duanwu"
            eatSub.addItem(zongzi)
            eatMenu.submenu = eatSub
            dailySub.addItem(eatMenu)

            let seasonMenu = NSMenuItem(title: "时节", action: nil, keyEquivalent: "")
            let seasonSub = NSMenu()
            for (title, key) in [("春节 · 拜年", "spring"), ("元宵 · 看灯", "yuanxiao"),
                                 ("端午 · 粽子", "duanwu"), ("中秋 · 月饼", "midautumn"),
                                 ("重阳 · 登高", "chongyang"), ("万圣 · 南瓜", "halloween"),
                                 ("圣诞 · 礼物", "christmas"), ("新年 · 福气", "newyear"),
                                 ("秋 · 落叶", "leaves"), ("冬 · 雪人", "snowman"),
                                 ("冬 · 烟花", "fireworks"), ("腊八 · 粥", "porridge"),
                                 ("春节 · 年糕", "ricecake"), ("清明 · 青团", "qingtuan"),
                                 ("新春 · 福字", "fu")] {
                let it = item(title, #selector(menuFestival(_:)))
                it.representedObject = key
                seasonSub.addItem(it)
            }
            seasonMenu.submenu = seasonSub
            dailySub.addItem(seasonMenu)

            let moveMenu = NSMenuItem(title: "移动", action: nil, keyEquivalent: "")
            let moveSub = NSMenu()
            for (title, key) in [("屏幕中央", "center"), ("左上角", "leftTop"),
                                 ("右下角", "rightBottom"), ("鼠标旁", "cursor")] {
                let it = item(title, #selector(menuMovePreset(_:)))
                it.representedObject = key
                moveSub.addItem(it)
            }
            moveMenu.submenu = moveSub
            dailySub.addItem(moveMenu)

            dailySub.addItem(.separator())
            dailySub.addItem(item("说句话…", #selector(menuCustomSay)))
            dailySub.addItem(item("碎碎念", #selector(menuDailyChatter)))
            dailySub.addItem(item("工作状态", #selector(menuDailyStatus)))
            dailyMenu.submenu = dailySub
            menu.addItem(dailyMenu)
        }

        // 唱歌
        let singMenu = NSMenuItem(title: "唱歌", action: nil, keyEquivalent: "")
        let singSub = NSMenu()
        let sing = item("放歌时跟着唱", #selector(menuToggleSing))
        sing.state = (settings.sing ?? true) ? .on : .off
        singSub.addItem(sing)
        let preview = item("试唱一段（20 秒）", #selector(menuPreviewSing))
        preview.isEnabled = manifest.character == "xiaohei" && (settings.sing ?? true)
        singSub.addItem(preview)
        if currentCharacter == "xiaohei" {
            let styleMenu = NSMenuItem(title: "唱歌花样", action: nil, keyEquivalent: "")
            let styleSub = NSMenu()
            let nowStyle = settings.singStyle ?? "auto"
            for (id, title) in [("auto", "自动换着来（推荐）"), ("sway", "只律动摇摆"),
                                ("mic", "尾巴拿麦克风"), ("hat", "街舞帽开跳"),
                                ("tail", "坐直摇尾巴")] {
                let it = item(title, #selector(menuSetSingStyle(_:)))
                it.representedObject = id
                it.state = id == nowStyle ? .on : .off
                styleSub.addItem(it)
            }
            styleMenu.submenu = styleSub
            singSub.addItem(styleMenu)
        }
        singMenu.submenu = singSub
        menu.addItem(singMenu)

        // 陪伴与指导
        let companyMenu = NSMenuItem(title: "陪伴与指导", action: nil, keyEquivalent: "")
        let companySub = NSMenu()
        let quiet = item("安静模式（不主动搭话）", #selector(menuToggleQuiet))
        quiet.state = settings.quiet ? .on : .off
        companySub.addItem(quiet)
        let playful = item("互动陪伴（靠近鼠标 / 应用反应）", #selector(menuTogglePlayful))
        playful.state = settings.playful ? .on : .off
        companySub.addItem(playful)
        let guide = item(GuideGate.menuTitle, #selector(menuToggleGuide))
        guide.state = guideEnabled ? .on : .off
        companySub.addItem(guide)
        if session != nil {
            companySub.addItem(item("结束当前指引", #selector(menuEndGuide)))
        }
        companySub.addItem(item("会议模式 60 分钟", #selector(menuMeeting)))
        let reduced = item("减少动态（关闭摇摆/音符）", #selector(menuToggleReduced))
        reduced.state = (settings.reducedMotion ?? false) ? .on : .off
        companySub.addItem(reduced)
        companyMenu.submenu = companySub
        menu.addItem(companyMenu)

        let charMenu = NSMenuItem(title: "形象", action: nil, keyEquivalent: "")
        let charSub = NSMenu()
        for option in CharacterOption.all() {
            let it = item(option.name, #selector(menuSetCharacter(_:)))
            it.representedObject = option.id
            it.state = option.id == currentCharacter ? .on : .off
            charSub.addItem(it)
        }
        if charSub.items.count < 2 {
            let hint = item("把素材放到 characters/ 即可添加", nil)
            hint.isEnabled = false
            charSub.addItem(.separator())
            charSub.addItem(hint)
        }
        charMenu.submenu = charSub
        menu.addItem(charMenu)

        if currentCharacter == "xiaohei" {
            let xhMenu = NSMenuItem(title: "小黑设置", action: nil, keyEquivalent: "")
            let xhSub = NSMenu()
            let meow = item("待机随机喵喵叫", #selector(menuToggleMeow))
            meow.state = (settings.meowEnabled ?? true) ? .on : .off
            xhSub.addItem(meow)
            let meowSound = item("喵叫音效", #selector(menuToggleMeowSound))
            meowSound.state = (settings.meowSound ?? true) ? .on : .off
            xhSub.addItem(meowSound)
            let hint = item("随机开关只停待机喵；音效可单独静音", nil)
            hint.isEnabled = false
            xhSub.addItem(hint)
            xhMenu.submenu = xhSub
            menu.addItem(xhMenu)
        }

        let sizeMenu = NSMenuItem(title: "桌宠大小", action: nil, keyEquivalent: "")
        let sizeSub = NSMenu()
        let petLimits = petScaleLimits()
        let petNow = item("当前：\(Int(round(settings.petScale * 100)))%", nil)
        petNow.isEnabled = false
        sizeSub.addItem(petNow)
        sizeSub.addItem(item("输入百分比…", #selector(menuCustomPetScale)))
        sizeSub.addItem(.separator())
        for v in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0] where v >= petLimits.min && v <= petLimits.max {
            let it = NSMenuItem(title: "\(Int(v * 100))%", action: #selector(menuSetPetScale(_:)), keyEquivalent: "")
            it.target = self
            it.representedObject = v
            it.state = abs(settings.petScale - v) < 0.01 ? .on : .off
            sizeSub.addItem(it)
        }
        sizeMenu.submenu = sizeSub

        let bMenu = NSMenuItem(title: "气泡大小", action: nil, keyEquivalent: "")
        let bSub = NSMenu()
        let manual = settings.bubbleW != nil && settings.bubbleH != nil
        var nowText: String
        if manual, let w = settings.bubbleW, let h = settings.bubbleH {
            nowText = "当前：手动 \(Int(w))×\(Int(h)) pt"
            if bubbleVisible {
                let f = bubbleWindow.frame.size
                if abs(f.width - w) > 1 || abs(f.height - h) > 1 {
                    nowText += "（实际 \(Int(f.width))×\(Int(f.height))）"
                }
            }
        } else {
            nowText = "当前：\(Int(round(settings.bubbleScale * 100)))%"
            if bubbleVisible {
                nowText += "（\(Int(bubbleWindow.frame.width))×\(Int(bubbleWindow.frame.height))）"
            }
        }
        let bNow = item(nowText, nil)
        bNow.isEnabled = false
        bSub.addItem(bNow)
        bSub.addItem(item("输入百分比…", #selector(menuCustomBubbleScale)))
        bSub.addItem(item("手动宽×高（pt）…", #selector(menuCustomBubbleSize)))
        bSub.addItem(item("恢复默认（100%）", #selector(menuResetBubbleSize)))
        bSub.addItem(.separator())
        let bLimits = bubbleScaleLimits(for: NSSize(width: 336, height: 64))
        for v in [0.6, 0.8, 1.0, 1.2, 1.6, 2.0] where v >= bLimits.min && v <= bLimits.max {
            let it = NSMenuItem(title: "\(Int(v * 100))%", action: #selector(menuSetBubbleScale(_:)), keyEquivalent: "")
            it.target = self
            it.representedObject = v
            it.state = (!manual && abs(settings.bubbleScale - v) < 0.01) ? .on : .off
            bSub.addItem(it)
        }
        bMenu.submenu = bSub

        let displayMenu = NSMenuItem(title: "显示与尺寸", action: nil, keyEquivalent: "")
        let displaySub = NSMenu()
        displaySub.addItem(sizeMenu)
        displaySub.addItem(bMenu)
        displaySub.addItem(item("重置位置", #selector(menuReset)))
        displayMenu.submenu = displaySub
        menu.addItem(displayMenu)
        menu.addItem(.separator())
        let demo = item("三步演示", #selector(menuDemo))
        demo.isEnabled = guideEnabled
        menu.addItem(demo)
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
    @objc func menuToggleGuide() { setGuideEnabled(!guideEnabled) }
    @objc func menuEndGuide() { cancelGuide(text: "好，这个任务先收起。我先安静待着。") }
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
    @objc func menuToggleMeow() {
        settings.meowEnabled = !(settings.meowEnabled ?? true)
        saveSettings(settings)
        showBubble(title: "", text: (settings.meowEnabled ?? true) ? "喵喵叫：开。待机时会随机喵一声。" : "喵喵叫：关。想听就点「喵一声」。",
                   badge: "小黑设置", tone: .coach, hold: 3.5)
    }
    @objc func menuToggleMeowSound() {
        settings.meowSound = !(settings.meowSound ?? true)
        saveSettings(settings)
        if settings.meowSound ?? true {
            MeowAudio.shared.playSequence(twice: false, enabled: true)
        } else {
            MeowAudio.shared.cancel()
        }
        showBubble(title: "", text: (settings.meowSound ?? true) ? "喵叫音效：开。" : "喵叫音效：关，只保留动作和气泡。",
                   badge: "小黑设置", tone: .coach, hold: 3)
    }
    @objc func menuSetSingStyle(_ sender: NSMenuItem) {
        guard let style = sender.representedObject as? String else { return }
        setSingStyle(style)
    }
    @objc func menuPreviewSing() { previewSinging() }
    @objc func menuCustomSay() {
        guard let text = inputAlert(title: "让小黑说句话", info: "输入一句想让小黑说的话。",
                                    value: "", placeholder: "例如：今天也辛苦啦") else { return }
        guard !text.isEmpty else { return }
        wake()
        player.play("pat", loop: false, autoIdle: true, transition: 0.18, priority: 70)
        petView.burstHearts(count: 1)
        showBubble(title: "小黑说", text: text, badge: "文字", tone: .coach, hold: 6)
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

    // MARK: 自定义大小

    private func inputAlert(title: String, info: String, value: String, placeholder: String) -> String? {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = info
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 240, height: 24))
        field.stringValue = value
        field.placeholderString = placeholder
        alert.accessoryView = field
        alert.addButton(withTitle: "应用")
        alert.addButton(withTitle: "取消")
        NSApp.activate(ignoringOtherApps: true)
        alert.window.initialFirstResponder = field
        guard alert.runModal() == .alertFirstButtonReturn else { return nil }
        return field.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func percentValue(_ text: String) -> Double? {
        let cleaned = text
            .replacingOccurrences(of: "%", with: "")
            .replacingOccurrences(of: "％", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard let v = Double(cleaned), v.isFinite, v > 0 else { return nil }
        return v / 100.0
    }

    private func notice(_ title: String, _ info: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = info
        alert.addButton(withTitle: "好")
        NSApp.activate(ignoringOtherApps: true)
        alert.runModal()
    }

    @objc func menuCustomPetScale() {
        let limits = petScaleLimits()
        let lo = Int(round(limits.min * 100)), hi = Int(round(limits.max * 100))
        guard let text = inputAlert(
            title: "桌宠大小",
            info: "直接输入百分值，例如 80。\n安全范围 \(lo)%–\(hi)%：再小会点不到，再大会超过屏幕一半。",
            value: "\(Int(round(settings.petScale * 100)))",
            placeholder: "例如 120") else { return }
        guard let v = percentValue(text) else {
            notice("输入无效", "请输入百分值，例如 80 或 125%。")
            return
        }
        let clamped = min(max(v, limits.min), limits.max)
        setPetScale(clamped)
        if abs(clamped - v) > 0.001 {
            notice("已按安全范围调整", "桌宠大小限制在 \(lo)%–\(hi)%，已设为 \(Int(round(clamped * 100)))%。")
        }
    }

    @objc func menuCustomBubbleScale() {
        let base = currentBubbleBase()
        let limits = bubbleScaleLimits(for: base)
        let lo = Int(round(limits.min * 100)), hi = Int(round(limits.max * 100))
        let current = settings.bubbleW != nil ? 1.0 : settings.bubbleScale
        guard let text = inputAlert(
            title: "气泡大小（百分比）",
            info: "直接输入百分值，例如 75。\n安全范围 \(lo)%–\(hi)%；手动宽高会切换回比例模式。",
            value: "\(Int(round(current * 100)))",
            placeholder: "例如 80") else { return }
        guard let v = percentValue(text) else {
            notice("输入无效", "请输入百分值，例如 80 或 125%。")
            return
        }
        let clamped = min(max(v, limits.min), limits.max)
        setBubbleScale(clamped)
        if abs(clamped - v) > 0.001 {
            notice("已按安全范围调整", "气泡大小限制在 \(lo)%–\(hi)%，已设为 \(Int(round(clamped * 100)))%。")
        }
    }

    @objc func menuCustomBubbleSize() {
        let m = bubbleManualLimits()
        let current = bubbleWindow != nil ? bubbleWindow.frame.size : NSSize(width: 280, height: 50)
        let w0 = settings.bubbleW ?? Double(max(m.minW, current.width))
        let h0 = settings.bubbleH ?? Double(max(m.minH, current.height))
        let alert = NSAlert()
        alert.messageText = "气泡大小（宽 × 高）"
        alert.informativeText = "单位是 pt。宽 \(Int(m.minW))–\(Int(m.maxW))，高 \(Int(m.minH))–\(Int(m.maxH))，都不会超过屏幕一半；对话气泡正文放不下时会自动抬高。"
        let box = NSView(frame: NSRect(x: 0, y: 0, width: 250, height: 60))
        let wLabel = NSTextField(labelWithString: "宽（pt）")
        wLabel.frame = NSRect(x: 0, y: 34, width: 64, height: 20)
        let wField = NSTextField(frame: NSRect(x: 68, y: 31, width: 150, height: 24))
        wField.stringValue = "\(Int(w0.rounded()))"
        let hLabel = NSTextField(labelWithString: "高（pt）")
        hLabel.frame = NSRect(x: 0, y: 6, width: 64, height: 20)
        let hField = NSTextField(frame: NSRect(x: 68, y: 3, width: 150, height: 24))
        hField.stringValue = "\(Int(h0.rounded()))"
        box.addSubview(wLabel); box.addSubview(wField)
        box.addSubview(hLabel); box.addSubview(hField)
        alert.accessoryView = box
        alert.addButton(withTitle: "应用")
        alert.addButton(withTitle: "取消")
        NSApp.activate(ignoringOtherApps: true)
        alert.window.initialFirstResponder = wField
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        guard let w = Double(wField.stringValue.trimmingCharacters(in: .whitespaces)),
              let h = Double(hField.stringValue.trimmingCharacters(in: .whitespaces)),
              w.isFinite, h.isFinite, w > 0, h > 0 else {
            notice("输入无效", "宽和高都要填正数，单位 pt。")
            return
        }
        let cw = min(max(w, m.minW), m.maxW)
        let ch = min(max(h, m.minH), m.maxH)
        setBubbleSize(width: cw, height: ch)
        if abs(cw - w) > 0.5 || abs(ch - h) > 0.5 {
            notice("已按安全范围调整", "宽限制在 \(Int(m.minW))–\(Int(m.maxW)) pt，高限制在 \(Int(m.minH))–\(Int(m.maxH)) pt；已设为 \(Int(cw))×\(Int(ch))。")
        }
    }

    @objc func menuResetBubbleSize() {
        resetBubbleSize()
    }

    @objc func menuReset() { resetPosition() }
    @objc func menuDemo() { runDemo() }
    @objc func menuQuit() { NSApp.terminate(nil) }
    @objc func menuAbout() {
        let assets = assetsRoot
        var size = 0
        if let e = FileManager.default.enumerator(at: assets, includingPropertiesForKeys: [.fileSizeKey]) {
            for case let u as URL in e {
                if let n = try? u.resourceValues(forKeys: [.fileSizeKey]).fileSize { size += n }
            }
        }
        let alert = NSAlert()
        alert.messageText = "桌面大肥鱼 Coach \(kVersion)"
        alert.informativeText = """
        独立版桌宠：agent 通过 skills / CLI / MCP 调用，指针 + 气泡 + 15/25 段动画。
        当前形象：\(manifest.displayName)（\(manifest.clips.count) 组，\(String(format: "%.1f", Double(size) / 1048576)) MB）。
        唱歌：4 种花样（律动 / 立麦伴唱 / 街舞帽 / 坐直摇尾），自动或固定。
        喵叫：动作、连叫与 CC0 音效，可分别关闭。
        形象菜单可随时切换；也可用 dafeiyu character xiaohei。
        Socket: \(Paths.socket.path)
        配置: \(Paths.home.path)
        """
        alert.addButton(withTitle: "好")
        NSApp.activate(ignoringOtherApps: true)
        alert.runModal()
    }
}
