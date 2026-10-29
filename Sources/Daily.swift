import AppKit
import Foundation

// 小黑日常：时节小道具、碎碎念、工作状态、移动。保持底图与动画不变，
// 节日道具画在桌宠窗口的独立图层里，不烘焙进角色帧。
extension AppController {
    @objc func menuFestival(_ sender: NSMenuItem) {
        guard let key = sender.representedObject as? String else { return }
        showFestival(key)
    }

    @objc func menuDailyChatter() { dailyChatter() }
    @objc func menuDailyStatus() { dailyStatus() }
    @objc func menuDailyAction(_ sender: NSMenuItem) {
        guard let clip = sender.representedObject as? String else { return }
        dailyAction(clip)
    }
    @objc func menuMovePreset(_ sender: NSMenuItem) {
        guard let preset = sender.representedObject as? String else { return }
        moveToPreset(preset)
    }

    func showFestival(_ key: String) {
        let specs: [String: (prop: String, text: String, badge: String)] = [
            "spring": ("lantern", "春节好，给你拜个年。", "春节"),
            "yuanxiao": ("lantern", "元宵节，一起看灯。", "元宵"),
            "duanwu": ("zongzi", "端午安康，吃个粽子。", "端午"),
            "midautumn": ("mooncake", "中秋快乐，分你一半月饼。", "中秋"),
            "chongyang": ("flower", "重阳登高，慢慢走。", "重阳"),
            "halloween": ("pumpkin", "不给糖就捣蛋。", "万圣"),
            "christmas": ("gift", "圣诞快乐，礼物收好。", "圣诞"),
            "newyear": ("envelope", "新年好，福气到。", "新年"),
            "leaves": ("leaves", "秋天到，叶子落在你桌上了。", "秋"),
            "snowman": ("snowman", "下雪啦，堆个雪人。", "冬"),
            "fireworks": ("fireworks", "放个烟花，庆祝一下。", "烟花"),
            "porridge": ("porridge", "腊八喝粥，暖暖的。", "腊八"),
            "ricecake": ("ricecake", "年年高，吃块年糕。", "年糕"),
            "qingtuan": ("qingtuan", "清明一口青团。", "清明"),
            "fu": ("fu", "福字到，新年好。", "福字"),
        ]
        guard let spec = specs[key] else { return }
        wake()
        petView.startFestival(spec.prop)
        player.play(key == "spring" || key == "newyear" ? "success" : "pat",
                    loop: false, autoIdle: true, transition: 0.18, priority: 75)
        if key == "spring" || key == "newyear" {
            petView.burstConfetti(count: 12)
        }
        showBubble(title: "", text: spec.text, badge: spec.badge, tone: .success, hold: 5)
    }

    func dailyChatter() {
        wake()
        player.play("pat", loop: false, autoIdle: true, transition: 0.18, priority: 70)
        petView.burstHearts(count: 2)
        showBubble(title: "", text: Quips.idleRandom(), badge: "碎碎念", tone: .coach, hold: 5)
    }

    func dailyStatus() {
        var bits: [String] = []
        let app = NSWorkspace.shared.frontmostApplication?.localizedName ?? "桌面"
        bits.append("在陪你：\(app)")
        if let until = focusUntil {
            let remain = max(0, Int(until.timeIntervalSinceNow))
            bits.append(remain > 60 ? "专注 \(remain / 60) 分钟" : "专注 \(remain) 秒")
        }
        if sleeping { bits.append("睡着") }
        if singing { bits.append("唱歌 · \(singStyleName(settings.singStyle ?? "auto"))") }
        if settings.quiet { bits.append("安静模式") }
        bits.append("米饭 \(settings.riceCount ?? 0) 碗")
        bits.append((settings.meowSound ?? true) ? "喵音效开" : "喵音效关")
        showBubble(title: "小黑现在", text: bits.joined(separator: " · "),
                   badge: "工作状态", tone: .thinking, hold: 6)
    }

    func dailyAction(_ clip: String) {
        guard manifest.clips[clip] != nil else { return }
        wake()
        player.play(clip, loop: false, autoIdle: true, transition: 0.18, priority: 75)
        petView.needsDisplay = true
    }

    func moveToPreset(_ preset: String) {
        guard let win = petWindow else { return }
        if preset == "cursor" {
            comeHere()
            return
        }
        let vf = ScreenSpace.mainScreen.visibleFrame
        let size = win.frame.size
        var origin = win.frame.origin
        switch preset {
        case "center":
            origin = NSPoint(x: vf.midX - size.width / 2, y: vf.midY - size.height / 2)
        case "leftTop":
            origin = NSPoint(x: vf.minX + 30, y: vf.maxY - size.height - 30)
        case "rightBottom":
            origin = NSPoint(x: vf.maxX - size.width - 30, y: vf.minY + 30)
        default:
            return
        }
        win.setFrameOrigin(origin)
        savePosition()
        repositionBubble()
        refreshPetPoint()
        wake()
        showBubble(title: "", text: "挪好了。", badge: "移动", tone: .coach, hold: 2)
    }
}
