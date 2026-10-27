import AppKit
import Foundation

// 入口：
//   dafeiyu-daemon                 启动桌宠（由 CLI 自动拉起）
//   dafeiyu-daemon --selftest      纯逻辑 + 素材自测
//   dafeiyu-daemon --version
//   dafeiyu-daemon --check         校验动画清单
// 环境变量：DAFEIYU_HOME / DAFEIYU_ASSETS / DAFEIYU_DEBUG

let args = CommandLine.arguments

if args.contains("--version") {
    print("\(kAppName) \(kVersion) (macOS, AppKit)")
    exit(0)
}

let manifest = ClipManifest.load()

if args.contains("--selftest") {
    exit(runSelfTest(manifest: manifest))
}

if args.contains("--check") {
    guard let m = manifest else {
        print("{\"ok\":false,\"error\":\"manifest missing at \(Paths.assets.path)\"}")
        exit(2)
    }
    var result: [String: Any] = [
        "ok": true, "clips": m.clips.count, "frames": m.clips.values.reduce(0) { $0 + $1.frameCount },
        "assets": Paths.assets.path,
    ]
    var missing: [String] = []
    for (_, c) in m.clips {
        for f in c.frames where !FileManager.default.fileExists(atPath: Paths.assets.appendingPathComponent(f).path) {
            missing.append(f)
        }
    }
    result["missing"] = missing
    let data = try! JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print(String(data: data, encoding: .utf8) ?? "{}")
    exit(missing.isEmpty ? 0 : 1)
}

guard let manifest else {
    let msg = "动画素材缺失：\(Paths.assets.appendingPathComponent("manifest.json").path)\n请先运行 scripts/build_assets.py 或源码安装。\n"
    FileHandle.standardError.write(Data(msg.utf8))
    logLine(msg)
    exit(2)
}

let app = NSApplication.shared
let controller = AppController(manifest: manifest)
let server = CoachServer()
server.handler = { controller.handle($0) }
controller.server = server
app.delegate = controller
app.setActivationPolicy(.accessory)

// 让 Ctrl-C / kill 能干净退出并删掉 socket
signal(SIGINT, SIG_IGN)
signal(SIGTERM, SIG_IGN)
let sigint = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
sigint.setEventHandler { NSApp.terminate(nil) }
sigint.resume()
let sigterm = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
sigterm.setEventHandler { NSApp.terminate(nil) }
sigterm.resume()

app.run()
