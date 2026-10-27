import AppKit
import Foundation

// MARK: - 版本与路径

let kAppName = "桌面大肥鱼 Coach"
let kVersion = "1.1.0"
let kProtocol = 1

struct Paths {
    static var home: URL {
        if let p = ProcessInfo.processInfo.environment["DAFEIYU_HOME"], !p.isEmpty {
            return URL(fileURLWithPath: p, isDirectory: true)
        }
        return FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".dafeiyu", isDirectory: true)
    }
    static var socket: URL { home.appendingPathComponent("coach.sock") }
    static var settings: URL { home.appendingPathComponent("settings.json") }
    static var session: URL { home.appendingPathComponent("session.json") }
    static var log: URL { home.appendingPathComponent("coach.log") }
    static var pid: URL { home.appendingPathComponent("coach.pid") }
    static var assets: URL {
        if let p = ProcessInfo.processInfo.environment["DAFEIYU_ASSETS"], !p.isEmpty {
            return URL(fileURLWithPath: p, isDirectory: true)
        }
        let exe = URL(fileURLWithPath: CommandLine.arguments[0]).resolvingSymlinksInPath()
        let beside = exe.deletingLastPathComponent().appendingPathComponent("clips", isDirectory: true)
        if FileManager.default.fileExists(atPath: beside.appendingPathComponent("manifest.json").path) {
            return beside
        }
        // 开发期：<project>/.build/dafeiyu-daemon -> <project>/Runtime/clips
        let project = exe.deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Runtime/clips", isDirectory: true)
        if FileManager.default.fileExists(atPath: project.appendingPathComponent("manifest.json").path) {
            return project
        }
        return home.appendingPathComponent("clips", isDirectory: true)
    }
    static func ensureHome() {
        try? FileManager.default.createDirectory(at: home, withIntermediateDirectories: true)
    }
}

func clamp(_ v: CGFloat, _ lo: CGFloat, _ hi: CGFloat) -> CGFloat { min(max(v, lo), hi) }

func logLine(_ message: String) {
    let f = DateFormatter()
    f.dateFormat = "HH:mm:ss"
    let line = "[\(f.string(from: Date()))] \(message)\n"
    if let data = line.data(using: .utf8) {
        if let h = try? FileHandle(forWritingTo: Paths.log) {
            h.seekToEndOfFile(); h.write(data); try? h.close()
        } else {
            try? data.write(to: Paths.log)
        }
    }
    if ProcessInfo.processInfo.environment["DAFEIYU_DEBUG"] != nil {
        FileHandle.standardError.write(Data(line.utf8))
    }
}

// MARK: - 坐标
//
// 对外（CLI / Agent / 技能）统一使用「主屏左上角为原点、x 向右、y 向下」的屏幕点。
// AppKit 使用左下角原点；两者通过主屏 maxY 互换。多屏时以主屏左上角为基准。

enum ScreenSpace {
    static var mainScreen: NSScreen { NSScreen.main ?? NSScreen.screens.first! }
    static var anchorMaxY: CGFloat { mainScreen.frame.maxY }

    static func toAppKit(_ p: CGPoint) -> CGPoint {
        CGPoint(x: p.x, y: anchorMaxY - p.y)
    }
    static func toTopLeft(_ p: CGPoint) -> CGPoint {
        CGPoint(x: p.x, y: anchorMaxY - p.y)
    }
    static func screen(containing appKitPoint: CGPoint) -> NSScreen {
        NSScreen.screens.first { NSMouseInRect(appKitPoint, $0.frame, false) } ?? mainScreen
    }
    static func normalized(_ nx: Double, _ ny: Double) -> CGPoint {
        let f = mainScreen.frame
        return CGPoint(x: f.minX + CGFloat(clamp(CGFloat(nx), 0, 1)) * f.width,
                       y: CGFloat(clamp(CGFloat(ny), 0, 1)) * f.height)
    }
    static func clampTopLeft(_ p: CGPoint, screen: NSScreen) -> CGPoint {
        let f = screen.frame
        return CGPoint(x: min(max(p.x, f.minX), f.maxX), y: min(max(p.y, 0), f.height))
    }
    static func describeScreens() -> [[String: Any]] {
        NSScreen.screens.map { s in
            [
                "frame": ["x": s.frame.minX, "y": s.frame.minY, "w": s.frame.width, "h": s.frame.height],
                "topLeftY": anchorMaxY - s.frame.maxY,
                "scale": s.backingScaleFactor,
                "main": s == mainScreen,
            ]
        }
    }
}

// MARK: - 偏好 / 会话

struct CoachSettings: Codable {
    var petScale: Double = 1.0
    var bubbleScale: Double = 1.0
    var petX: Double? = nil
    var petY: Double? = nil
    var quiet: Bool = false
    var playful: Bool = true
    var bubbleOn: Bool = true
    var petOn: Bool = true
    var lastAgent: String = ""
    var sing: Bool? = true
    var riceCount: Int? = 0
    var reducedMotion: Bool? = false
}

func loadSettings() -> CoachSettings {
    guard let data = try? Data(contentsOf: Paths.settings),
          let s = try? JSONDecoder().decode(CoachSettings.self, from: data) else { return CoachSettings() }
    return s
}

func saveSettings(_ s: CoachSettings) {
    let enc = JSONEncoder()
    enc.outputFormatting = [.prettyPrinted, .sortedKeys]
    if let d = try? enc.encode(s) { try? d.write(to: Paths.settings, options: .atomic) }
}

struct CoachStep: Codable {
    var text: String
    var hint: String? = nil
    var x: Double? = nil
    var y: Double? = nil
    var label: String? = nil
}

struct CoachSession: Codable {
    var id: String = UUID().uuidString
    var title: String = ""
    var steps: [CoachStep] = []
    var index: Int = 0
    var done: [Bool] = []
    var agent: String = ""
    var finished: Bool = false
    var updatedAt: Double = Date().timeIntervalSince1970

    var total: Int { steps.count }
    var current: CoachStep? { (index >= 0 && index < steps.count) ? steps[index] : nil }
    var progressText: String { total > 0 ? "\(min(index + 1, total))/\(total)" : "" }

    mutating func normalize() {
        if done.count < steps.count { done.append(contentsOf: Array(repeating: false, count: steps.count - done.count)) }
        if done.count > steps.count { done = Array(done.prefix(steps.count)) }
        index = max(0, min(index, max(0, steps.count - 1)))
    }
}

func loadSession() -> CoachSession? {
    guard let d = try? Data(contentsOf: Paths.session),
          let s = try? JSONDecoder().decode(CoachSession.self, from: d) else { return nil }
    return s
}

func saveSession(_ s: CoachSession?) {
    guard let s = s else { try? FileManager.default.removeItem(at: Paths.session); return }
    let enc = JSONEncoder()
    enc.outputFormatting = [.prettyPrinted, .sortedKeys]
    if let d = try? enc.encode(s) { try? d.write(to: Paths.session, options: .atomic) }
}

// MARK: - 动画清单

struct ClipInfo: Codable {
    var fps: Double
    var loop: Bool
    var frameCount: Int
    var durationMs: Int
    var frames: [String]
}

struct ClipManifest: Codable {
    var formatVersion: Int
    var character: String
    var displayName: String
    var frameSize: [Double]
    var license: String
    var clips: [String: ClipInfo]

    static func load() -> ClipManifest? {
        let url = Paths.assets.appendingPathComponent("manifest.json")
        guard let data = try? Data(contentsOf: url),
              let m = try? JSONDecoder().decode(ClipManifest.self, from: data) else { return nil }
        return m
    }
}

// 气泡与步骤的纯逻辑，`--selftest` 会直接验证这些函数。
enum StepLogic {
    static func advance(_ s: inout CoachSession) -> Bool {
        s.normalize()
        guard !s.steps.isEmpty else { return true }
        s.done[s.index] = true
        if s.index + 1 >= s.steps.count {
            s.finished = true
            s.index = s.steps.count
            return true
        }
        s.index += 1
        s.updatedAt = Date().timeIntervalSince1970
        return false
    }

    static func rewind(_ s: inout CoachSession) {
        s.normalize()
        guard !s.steps.isEmpty else { return }
        if s.finished { s.finished = false; s.index = s.steps.count - 1 }
        else if s.index > 0 { s.index -= 1 }
        s.done[s.index] = false
        s.updatedAt = Date().timeIntervalSince1970
    }

    static func completedCount(_ s: CoachSession) -> Int {
        s.done.filter { $0 }.count
    }
}

// MARK: - 自测

func runSelfTest(manifest: ClipManifest?) -> Int32 {
    var failures: [String] = []
    func expect(_ cond: Bool, _ name: String) {
        if !cond { failures.append(name) }
    }
    let mainH = ScreenSpace.anchorMaxY
    let p = CGPoint(x: 100, y: 50)
    let back = ScreenSpace.toTopLeft(ScreenSpace.toAppKit(p))
    expect(abs(back.x - p.x) < 0.001 && abs(back.y - p.y) < 0.001, "topLeft<->appKit roundtrip")
    expect(ScreenSpace.toAppKit(p).y == mainH - 50, "topLeft conversion")
    let n = ScreenSpace.normalized(0.5, 0.5)
    expect(n.x > 0 && n.y > 0, "normalized point")

    var s = CoachSession(title: "t", steps: [CoachStep(text: "a"), CoachStep(text: "b"), CoachStep(text: "c")], index: 0, done: [false, false, false])
    expect(s.progressText == "1/3", "progress text")
    expect(StepLogic.advance(&s) == false && s.index == 1, "advance middle")
    expect(StepLogic.advance(&s) == false && s.index == 2, "advance second")
    expect(StepLogic.advance(&s) == true && s.finished, "advance finish")
    var s2 = CoachSession(title: "t", steps: [CoachStep(text: "a")], index: 0, done: [false])
    expect(StepLogic.advance(&s2) == true && s2.finished, "single step finish")
    var s3 = CoachSession(title: "t", steps: [CoachStep(text: "a"), CoachStep(text: "b")], index: 1, done: [true, false])
    StepLogic.rewind(&s3)
    expect(s3.index == 0 && s3.done[0] == false, "rewind")
    expect(StepLogic.completedCount(s3) == 0, "completed count")

    expect(Quips.isMeetingApp("Zoom"), "meeting app zoom")
    expect(Quips.isMeetingApp("腾讯会议"), "meeting app tencent")
    expect(!Quips.isMeetingApp("Xcode"), "meeting app negative")
    if let m = manifest {
        expect(m.clips.count >= 12, "clip count >= 12")
        for (name, clip) in m.clips {
            expect(clip.frameCount == clip.frames.count, "frame count \(name)")
            expect(!clip.frames.isEmpty, "frames \(name)")
            expect(FileManager.default.fileExists(atPath: Paths.assets.appendingPathComponent(clip.frames[0]).path),
                   "frame exists \(name)")
        }
    } else {
        failures.append("manifest missing at \(Paths.assets.path)")
    }

    if failures.isEmpty {
        print("{\"ok\":true,\"tests\":\"passed\",\"clips\":\(manifest?.clips.count ?? 0)}")
        return 0
    }
    print("{\"ok\":false,\"failures\":\(failures)}")
    return 1
}
