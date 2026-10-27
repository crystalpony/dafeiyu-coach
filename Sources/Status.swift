import AppKit
import Foundation

// 状态序列化与小型解析工具。放在扩展里，控制单文件行数。
extension AppController {
    func bubbleTone(_ s: String?) -> BubbleTone {
        switch s {
        case "success": return .success
        case "error": return .error
        case "thinking": return .thinking
        case "music": return .music
        default: return .coach
        }
    }

    func num(_ v: Any?) -> Double? {
        if let d = v as? Double { return d }
        if let i = v as? Int { return Double(i) }
        if let n = v as? NSNumber { return n.doubleValue }
        if let s = v as? String { return Double(s) }
        return nil
    }

    func bool(_ v: Any?, default d: Bool) -> Bool {
        if let b = v as? Bool { return b }
        if let n = v as? NSNumber { return n.boolValue }
        if let s = v as? String { return ["1", "true", "on", "yes"].contains(s.lowercased()) }
        return d
    }

    func isMeetingFrontmost() -> Bool {
        Quips.isMeetingApp(NSWorkspace.shared.frontmostApplication?.localizedName ?? "")
    }

    func statusPayload() -> [String: Any] {
        var r: [String: Any] = [
            "ok": true,
            "version": kVersion,
            "protocol": kProtocol,
            "pid": ProcessInfo.processInfo.processIdentifier,
            "uptime": Int(Date().timeIntervalSince(startedAt)),
            "agent": settings.lastAgent,
            "quiet": settings.quiet,
            "playful": settings.playful,
            "petVisible": petVisible,
            "bubbleVisible": bubbleVisible,
            "petScale": settings.petScale,
            "bubbleScale": settings.bubbleScale,
            "sleeping": sleeping,
            "singing": singing,
            "sing": settings.sing ?? true,
            "reducedMotion": settings.reducedMotion ?? false,
            "songTitle": songTitle,
            "songArtist": songArtist,
            "lyric": lyricLine,
            "blend": Double(player.blend),
            "rice": settings.riceCount ?? 0,
            "focusRemaining": focusUntil.map { max(0, Int($0.timeIntervalSinceNow)) } ?? 0,
            "quietRemaining": quietUntil.map { max(0, Int($0.timeIntervalSinceNow)) } ?? 0,
            "pointer": pointerGlobal != nil,
            "clip": player.currentName,
            "frame": player.frameIndex,
            "mainScale": Double(ScreenSpace.mainScreen.backingScaleFactor),
            "screens": ScreenSpace.describeScreens(),
            "clips": manifest.clips.keys.sorted(),
            "assets": Paths.assets.path,
            "socket": Paths.socket.path,
        ]
        if let pet = petWindow?.frame {
            r["pet"] = ["x": pet.origin.x, "y": pet.origin.y, "w": pet.width, "h": pet.height,
                        "topLeftY": ScreenSpace.anchorMaxY - pet.maxY]
        }
        if let b = bubbleWindow?.frame {
            r["bubble"] = ["x": b.origin.x, "y": b.origin.y, "w": b.width, "h": b.height,
                           "topLeftY": ScreenSpace.anchorMaxY - b.maxY]
        }
        if let s = session {
            var js: [String: Any] = [
                "id": s.id, "title": s.title, "total": s.total,
                "index": s.index, "done": StepLogic.completedCount(s),
                "finished": s.finished, "agent": s.agent,
            ]
            if let cur = s.current {
                js["text"] = cur.text
                js["hint"] = cur.hint ?? ""
                js["label"] = cur.label ?? ""
                js["x"] = cur.x ?? NSNull()
                js["y"] = cur.y ?? NSNull()
            }
            r["session"] = js
        } else {
            r["session"] = NSNull()
        }
        return r
    }

}
