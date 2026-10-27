import AppKit
import Foundation

// 演示舞台：盖住其它应用、抬高桌宠/气泡层，专门用于截图、录屏和验收。
extension AppController {
    func showStage() {
        guard stageWindow == nil else { return }
        let screen = ScreenSpace.mainScreen
        let w = NSWindow(contentRect: screen.frame, styleMask: .borderless, backing: .buffered, defer: false)
        w.isOpaque = true
        w.backgroundColor = NSColor(calibratedRed: 0.96, green: 0.95, blue: 0.93, alpha: 1)
        w.hasShadow = false
        w.ignoresMouseEvents = true
        w.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 2)
        w.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
        w.isReleasedWhenClosed = false
        w.contentView = StageView(frame: NSRect(origin: .zero, size: screen.frame.size))
        w.orderFrontRegardless()
        stageWindow = w
        petWindow.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 3)
        bubbleWindow.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 3)
        closeWindow.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 4)
        logLine("stage on")
    }

    func hideStage() {
        guard let w = stageWindow else { return }
        w.orderOut(nil)
        stageWindow = nil
        petWindow.level = .floating
        bubbleWindow.level = .floating
        closeWindow.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 1)
        logLine("stage off")
    }

}
