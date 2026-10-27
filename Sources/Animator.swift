import AppKit
import Foundation

/// 逐帧播放器：按需从磁盘解码，NSCache 限制常驻帧数，避免 820 帧同时进内存。
final class ClipPlayer {
    private let manifest: ClipManifest
    private let cache = NSCache<NSString, NSImage>()
    private(set) var currentName: String = "idle"
    private(set) var current: ClipInfo
    private(set) var frameIndex: Int = 0
    private var accumulator: Double = 0
    private var finishedFired = false
    private var lastTick: CFTimeInterval = CACurrentMediaTime()

    var autoReturnToIdle = true
    var onClipFinished: ((String) -> Void)?

    // 过渡：上一帧 + 新剪辑叠加，避免 0ms 硬切
    private(set) var previousImage: NSImage?
    private(set) var blend: CGFloat = 1
    private var transitionDuration: Double = 0.14
    private(set) var currentPriority = 0
    private(set) var busy = false

    init(manifest: ClipManifest) {
        self.manifest = manifest
        self.current = manifest.clips["idle"] ?? ClipInfo(fps: 12, loop: true, frameCount: 1, durationMs: 1000, frames: [])
        cache.countLimit = 28
    }

    func resolve(_ name: String) -> String {
        switch name {
        case "talk": return "idle"
        case "point": return "working"
        case "celebrate", "dance", "cheer": return "success"
        case "greet", "wave", "happy": return "pat"
        case "snack", "rice": return "eat"
        case "sleepy": return "yawn"
        default: return name
        }
    }

    var resolvedName: String { resolve(currentName) }

    var isLooping: Bool { current.loop }

    func play(_ name: String, loop: Bool? = nil, autoIdle: Bool? = nil,
              transition: Double = 0.14, priority: Int = 50, force: Bool = false,
              onFinish: ((String) -> Void)? = nil) {
        let key = resolve(name)
        guard var clip = manifest.clips[key] ?? manifest.clips["idle"] else { return }
        if let l = loop { clip.loop = l }

        // 同一剪辑不从头重播；低优先级不打断正在播放的一次性动作。
        if !force {
            if key == resolve(currentName) && !finishedFired { return }
            if busy && priority < currentPriority { return }
        }

        let outgoing = image()
        currentName = name
        current = clip
        frameIndex = 0
        accumulator = 0
        finishedFired = false
        lastTick = CACurrentMediaTime()
        currentPriority = priority
        busy = !clip.loop && clip.frameCount > 1
        if let a = autoIdle { autoReturnToIdle = a }
        onClipFinished = onFinish
        if transition > 0, let outgoing {
            previousImage = outgoing
            blend = 0
            transitionDuration = transition
        } else {
            previousImage = nil
            blend = 1
        }
        prefetchEarlyFrames(2)
    }

    /// 返回是否有新帧需要重绘。
    func tick() -> Bool {
        let now = CACurrentMediaTime()
        let dt = min(0.2, max(0, now - lastTick))
        lastTick = now
        var changed = false
        if blend < 1 {
            blend = min(1, blend + CGFloat(dt / max(0.02, transitionDuration)))
            if blend >= 1 { previousImage = nil }
            changed = true
        }
        guard current.frameCount > 1, !current.frames.isEmpty else { return changed }
        accumulator += dt
        let step = 1.0 / max(current.fps, 1)
        guard accumulator >= step else { return false }
        let advance = min(6, Int(accumulator / step))
        accumulator -= Double(advance) * step
        if current.loop {
            frameIndex = (frameIndex + advance) % current.frameCount
            return true
        }
        let next = frameIndex + advance
        if next >= current.frameCount - 1 {
            frameIndex = current.frameCount - 1
            if !finishedFired {
                finishedFired = true
                busy = false
                let name = currentName
                DispatchQueue.main.async { [weak self] in
                    guard let self else { return }
                    self.onClipFinished?(name)
                    if self.autoReturnToIdle && !self.current.loop {
                        self.play("idle", loop: true, autoIdle: true,
                                  transition: 0.18, priority: 10, force: true, onFinish: nil)
                    }
                }
            }
            return true
        }
        frameIndex = next
        return true
    }

    func image() -> NSImage? {
        guard !current.frames.isEmpty else { return nil }
        let idx = max(0, min(frameIndex, current.frames.count - 1))
        let rel = current.frames[idx]
        let key = rel as NSString
        if let hit = cache.object(forKey: key) { return hit }
        let url = Paths.assets.appendingPathComponent(rel)
        guard let img = NSImage(contentsOf: url) else { return nil }
        cache.setObject(img, forKey: key)
        return img
    }

    func prefetchEarlyFrames(_ count: Int = 2) {
        for i in 0..<min(count, current.frames.count) {
            _ = imageAt(i)
        }
    }

    private func imageAt(_ i: Int) -> NSImage? {
        guard i < current.frames.count else { return nil }
        let rel = current.frames[i]
        let key = rel as NSString
        if let hit = cache.object(forKey: key) { return hit }
        guard let img = NSImage(contentsOf: Paths.assets.appendingPathComponent(rel)) else { return nil }
        cache.setObject(img, forKey: key)
        return img
    }

    /// 让当前剪辑暂停/继续时不出现“跳一大步”。
    func touchClock() { lastTick = CACurrentMediaTime(); accumulator = 0 }
}
