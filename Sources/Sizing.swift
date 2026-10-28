import AppKit
import Foundation

// 尺寸与安全边界。单独成文件：Controller 已接近 1100 行的审计上限。
extension AppController {
    /// 桌宠安全范围：最小保证 73×61 pt 左右仍然点得到；最大不超过屏幕一半。
    func petScaleLimits() -> (min: Double, max: Double) {
        let vf = (petWindow?.screen ?? ScreenSpace.mainScreen).visibleFrame
        let minScale = max(0.35, 44.0 / min(petBase.width, petBase.height))
        let maxScale = min((vf.width * 0.5 - 8) / petBase.width,
                           (vf.height * 0.5 - 8) / petBase.height)
        return (minScale, max(minScale, maxScale))
    }

    /// 气泡安全范围：最小 40%（文字仍可辨认）；最大宽/高都不超过半屏。
    func bubbleScaleLimits(for base: NSSize) -> (min: Double, max: Double) {
        let vf = (petWindow?.screen ?? ScreenSpace.mainScreen).visibleFrame
        let minScale = 0.40
        let maxScale = min((vf.width * 0.5 - 8) / max(base.width, 1),
                           (vf.height * 0.5 - 8) / max(base.height, 1))
        return (minScale, max(minScale, maxScale))
    }

    /// 手动宽高的硬边界（pt）。
    func bubbleManualLimits() -> (minW: CGFloat, minH: CGFloat, maxW: CGFloat, maxH: CGFloat) {
        let vf = (petWindow?.screen ?? ScreenSpace.mainScreen).visibleFrame
        return (180, 40, max(180, floor(vf.width * 0.5 - 8)), max(40, floor(vf.height * 0.5 - 8)))
    }

    func currentBubbleBase() -> NSSize {
        BubbleView.measure(title: bubbleView.title, text: bubbleView.text,
                           subtext: bubbleView.subtext, badge: bubbleView.badge,
                           total: bubbleView.total, music: bubbleKind == .music)
    }

    func layoutBubble() {
        let isMusic = bubbleKind == .music
        var target = NSSize.zero
        let manualW = settings.bubbleW
        let manualH = settings.bubbleH

        if let mw = manualW, let mh = manualH {
            // 手动宽高：直接按 pt 画，文字布局随宽高自适应；不再乘百分比。
            let m = bubbleManualLimits()
            let wantedW = clamp(CGFloat(mw), m.minW, m.maxW)
            if isMusic {
                let wantedH = clamp(CGFloat(mh), m.minH, m.maxH)
                target = NSSize(width: wantedW, height: wantedH)
                bubbleView.baseSize = target
            } else {
                let measured = BubbleView.measure(title: bubbleView.title, text: bubbleView.text,
                                                  subtext: bubbleView.subtext,
                                                  badge: bubbleView.badge, total: bubbleView.total,
                                                  music: false, width: wantedW)
                // 高度不足以放下正文时自动抬高，避免裁掉字；上限仍是半屏。
                let wantedH = min(max(CGFloat(mh), measured.height), m.maxH)
                target = NSSize(width: wantedW, height: wantedH)
                bubbleView.baseSize = target
            }
            bubbleView.contentScale = 1
            bubbleDrawScale = 1
        } else {
            let base = BubbleView.measure(title: bubbleView.title, text: bubbleView.text,
                                          subtext: bubbleView.subtext,
                                          badge: bubbleView.badge, total: bubbleView.total,
                                          music: isMusic)
            let limits = bubbleScaleLimits(for: base)
            let s = CGFloat(clamp(CGFloat(settings.bubbleScale),
                                  CGFloat(limits.min), CGFloat(limits.max)))
            bubbleView.baseSize = base
            bubbleView.contentScale = s
            bubbleDrawScale = s
            target = NSSize(width: ceil(base.width * s), height: ceil(base.height * s))
        }

        bubbleWindow.setContentSize(target)
        bubbleView.frame = NSRect(origin: .zero, size: bubbleWindow.contentView!.bounds.size)
        bubbleView.needsDisplay = true
        repositionBubble()
    }

    func setPetScale(_ v: Double) {
        let limits = petScaleLimits()
        settings.petScale = Double(clamp(CGFloat(v), CGFloat(limits.min), CGFloat(limits.max)))
        let size = petSize()
        var f = petWindow.frame
        let center = NSPoint(x: f.midX, y: f.midY)
        f.size = size
        f.origin = NSPoint(x: center.x - size.width / 2, y: center.y - size.height / 2)
        let screen = petWindow.screen ?? ScreenSpace.mainScreen
        f.origin.x = clamp(f.origin.x, screen.visibleFrame.minX, screen.visibleFrame.maxX - size.width)
        f.origin.y = clamp(f.origin.y, screen.visibleFrame.minY, screen.visibleFrame.maxY - size.height)
        petWindow.setFrame(f, display: true)
        petView.frame = NSRect(origin: .zero, size: size)
        petView.needsDisplay = true
        saveSettings(settings)
        savePosition()
        repositionBubble()
        refreshPetPoint()
    }

    func setBubbleScale(_ v: Double) {
        // 比例模式会退出“手动宽高”，两方面只留一个生效。
        settings.bubbleW = nil
        settings.bubbleH = nil
        let base = currentBubbleBase()
        let limits = bubbleScaleLimits(for: base)
        settings.bubbleScale = Double(clamp(CGFloat(v), CGFloat(limits.min), CGFloat(limits.max)))
        saveSettings(settings)
        layoutBubble()
    }

    func setBubbleSize(width: Double, height: Double) {
        let m = bubbleManualLimits()
        settings.bubbleW = Double(clamp(CGFloat(width), m.minW, m.maxW))
        settings.bubbleH = Double(clamp(CGFloat(height), m.minH, m.maxH))
        saveSettings(settings)
        layoutBubble()
    }

    func resetBubbleSize() {
        settings.bubbleW = nil
        settings.bubbleH = nil
        settings.bubbleScale = 1.0
        saveSettings(settings)
        layoutBubble()
    }

    func repositionBubble() {
        guard petWindow != nil, bubbleWindow != nil else { return }
        let pf = petWindow.frame
        let bsize = bubbleWindow.frame.size
        let screen = petWindow.screen ?? ScreenSpace.mainScreen
        let vf = screen.visibleFrame
        let gap: CGFloat = 8

        if bubbleKind == .music {
            // 歌词贴在头顶，居中，不挡住桌面
            var ox = clamp(pf.midX - bsize.width / 2, vf.minX + 4, vf.maxX - bsize.width - 4)
            var oy = pf.maxY + 6
            if oy + bsize.height > vf.maxY - 4 {
                oy = pf.minY - bsize.height - 6
            }
            ox = clamp(ox, vf.minX + 4, vf.maxX - bsize.width - 4)
            oy = clamp(oy, vf.minY + 4, vf.maxY - bsize.height - 4)
            bubbleWindow.setFrameOrigin(NSPoint(x: ox, y: oy))
            bubbleView.tailOnRight = false
            bubbleView.tailAtBottom = true
            bubbleView.needsDisplay = true
            closeWindow.orderOut(nil)
            return
        }

        var originX: CGFloat
        var tailOnRight: Bool
        if pf.maxX + gap + bsize.width <= vf.maxX - 4 {
            originX = pf.maxX + gap
            tailOnRight = false
        } else if pf.minX - gap - bsize.width >= vf.minX + 4 {
            originX = pf.minX - gap - bsize.width
            tailOnRight = true
        } else {
            originX = clamp(pf.maxX + gap, vf.minX + 4, vf.maxX - bsize.width - 4)
            tailOnRight = false
        }
        var originY = pf.maxY - bsize.height - 4
        originY = clamp(originY, vf.minY + 4, vf.maxY - bsize.height - 4)
        bubbleWindow.setFrameOrigin(NSPoint(x: originX, y: originY))
        bubbleView.tailOnRight = tailOnRight
        bubbleView.needsDisplay = true

        let bodyRight = originX + bsize.width - (tailOnRight ? 11 * bubbleDrawScale : 0)
        let closeSize: CGFloat = 24
        closeWindow.setFrame(NSRect(x: bodyRight - closeSize - 5,
                                    y: originY + bsize.height - closeSize - 5,
                                    width: closeSize, height: closeSize), display: false)
    }
}
