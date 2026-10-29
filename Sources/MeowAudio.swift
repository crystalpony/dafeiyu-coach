import AppKit
import Foundation

/// 喵叫音效：CC0 样本 Runtime/sounds/xiaohei_meow.wav。
/// 单独放一个单例，避免 AppController 继续膨胀，并保证 NSSound 在播放期间被持有。
final class MeowAudio {
    static let shared = MeowAudio()
    private var player: NSSound?
    private var generation = 0

    func playSequence(twice: Bool, enabled: Bool) {
        generation &+= 1
        let gen = generation
        guard enabled else { return }
        playOnce()
        guard twice else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.45) { [weak self] in
            guard let self, self.generation == gen else { return }
            self.playOnce()
        }
    }

    func cancel() {
        generation &+= 1
        player?.stop()
    }

    private func playOnce() {
        let url = Paths.sounds.appendingPathComponent("xiaohei_meow.wav")
        guard let sound = NSSound(contentsOf: url, byReference: true) else { return }
        player?.stop()
        sound.volume = 0.9
        player = sound
        logLine("meow sound play=\(sound.play())")
    }
}
