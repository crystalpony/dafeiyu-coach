"""Real frame/manifest regressions; no Tk window, server, or installed assets needed."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dafeiyu_gui", ROOT / "bin" / "dafeiyu_gui.py")
gui = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gui)


def make_assets(root: Path, character: str) -> Path:
    assets = root / character
    assets.mkdir()
    frames = []
    for i in range(24):
        name = f"frame-{i}.png"
        im = Image.new("RGBA", (48, 40))
        draw = ImageDraw.Draw(im)
        draw.rectangle((3 + i, 5, 20 + i, 28), fill=(20 + i * 9, 60, 90, 255))
        draw.rectangle((8, 33, 39, 35), fill=(35, 35, 35, 255))
        im.save(assets / name)
        frames.append(name)

    def clip(selected, loop=True, fps=24):
        return dict(fps=fps, loop=loop, frameCount=len(selected),
                    durationMs=round(len(selected) * 1000 / fps), frames=selected)

    clips = {
        "idle": clip(frames),
        "sing": clip(frames[8:] + frames[:8]),
        "working": clip(frames[16:] + frames[:16]),
        "drag": clip(frames[12:] + frames[:12]),
        "pat": clip(frames[3:6], False),
        "poke": clip(frames[6:9], False),
        "drop": clip(frames[9:12], False),
        "rice": clip(frames[12:15], False),
        "still": clip(frames[20:21]),
        "slow": clip(frames[21:23], fps=1),
        "once": clip(frames[22:24], False, fps=1000),
    }
    manifest = dict(formatVersion=1, character=character, displayName=character,
                    frameSize=[48, 40], license="test fixture", clips=clips)
    (assets / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return assets


class FakeClock:
    ms = 0

    def __call__(self):
        return self.ms / 1000


class PlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="xiaohei-player-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.assets = {c: make_assets(Path(cls.temp.name), c) for c in ("xiaohei", "dafeiyu")}

    def setUp(self):
        if gui.GUI_ERR is not None:
            self.skipTest(str(gui.GUI_ERR))
        self.clock = FakeClock()
        clock_patch = patch.object(gui.time, "monotonic", self.clock)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)

    def assert_single_frame(self, anim):
        self.assertIsNone(anim.prev)
        self.assertEqual(anim.blend, 1)
        expected = anim._load(anim.frames[anim.idx])
        self.assertIsNotNone(expected)
        self.assertEqual(anim.image().tobytes(), expected.tobytes())

    def test_xiaohei_nonidle_and_rapid_forced_switches(self):
        anim = gui.Animator(self.assets["xiaohei"])
        with patch.object(gui.Image, "blend", side_effect=AssertionError("crossfade forbidden")):
            for force in (False, True, False, True):
                for name in ("sing", "working", "pat", "poke", "drag", "drop", "rice", "still", "idle"):
                    with self.subTest(force=force, clip=name):
                        anim.set_clip(name, force=force)
                        self.assert_single_frame(anim)
                        self.clock.ms += 16
                        anim.tick()
                        self.assert_single_frame(anim)
            anim.set_clip("sing", force=True)
            self.clock.ms += 80
            anim.tick()
            self.assertGreater(anim.idx, 0)
            anim.set_clip("sing", force=True)
            self.assertEqual(anim.idx, 0)
            self.assert_single_frame(anim)

    def test_switch_resets_clock_and_preserves_first_frame(self):
        anim = gui.Animator(self.assets["xiaohei"])
        for name, force in (("sing", False), ("working", True), ("working", True)):
            self.clock.ms += 150
            anim.set_clip(name, force=force)
            self.assertEqual(anim.last, self.clock())
            self.clock.ms += 16
            anim.tick()
            self.assertEqual(anim.idx, 0)
            self.clock.ms += 32
            anim.tick()
            self.assertEqual(anim.idx, 1)
            self.assert_single_frame(anim)

    def test_same_clip_without_force_keeps_clock_and_progress(self):
        anim = gui.Animator(self.assets["xiaohei"])
        anim.set_clip("sing")
        self.clock.ms = 50
        anim.tick()
        last, acc, idx = anim.last, anim.acc, anim.idx
        self.clock.ms += 16
        anim.set_clip("sing")
        self.assertEqual((anim.last, anim.acc, anim.idx), (last, acc, idx))
        self.assert_single_frame(anim)

    def test_fish_keeps_crossfade_and_forced_switch_behavior(self):
        anim = gui.Animator(self.assets["dafeiyu"])
        old = anim.image().copy()
        anim.set_clip("sing")
        self.assertIsNotNone(anim.prev)
        self.assertEqual(anim.blend, 0)
        self.assertEqual(anim.image().tobytes(), old.tobytes())
        self.clock.ms = 16
        image = anim.tick()
        self.assertGreater(anim.blend, 0)
        self.assertLess(anim.blend, 1)
        expected = Image.blend(old, anim._load(anim.frames[anim.idx]), anim.blend)
        self.assertEqual(image.tobytes(), expected.tobytes())
        self.clock.ms = 200
        anim.tick()
        self.assertIsNone(anim.prev)
        self.assertEqual(anim.blend, 1)
        anim.set_clip("pat", force=True)
        self.assert_single_frame(anim)

    def run_gui_second(self, character):
        """Execute the real GuiApp.tick/after chain on a virtual Tk scheduler."""
        app = gui.GuiApp.__new__(gui.GuiApp)
        app.anim = gui.Animator(self.assets[character])
        app.anim.set_clip("sing", force=True)
        app.core = SimpleNamespace(stop=False)
        app.state = lambda: {"clip": "sing", "rice": 0}
        app.last_clip, app.last_rice, app.phase = "sing", 0, 0.0
        app.update_bubble = Mock()
        app.update_pointer = Mock()
        app.update_notes = Mock()
        app.pet_item = 1
        rendered, delays = [], []
        pending = []

        def render(item, image):
            self.assertEqual(item, app.pet_item)
            pixels = image.tobytes()
            if not rendered or rendered[-1] != pixels:
                rendered.append(pixels)
            if character == "xiaohei":
                self.assert_single_frame(app.anim)

        def after(delay, callback):
            delays.append(delay)
            pending[:] = [(self.clock.ms + delay, callback)]

        app.pet_canvas = SimpleNamespace(itemconfigure=render)
        app.root = SimpleNamespace(after=after)
        with patch.object(gui.ImageTk, "PhotoImage", side_effect=lambda im: im.copy()):
            app.tick()
            while pending[0][0] < 1000:
                self.clock.ms, callback = pending.pop()
                callback()
        return app, rendered, delays

    def test_gui_shows_all_24_frames_in_one_second(self):
        app, rendered, delays = self.run_gui_second("xiaohei")
        expected = [app.anim._load(f).tobytes() for f in app.anim.frames]
        self.assertEqual(len(rendered), 24, "70ms scheduling skips baked 24fps frames")
        self.assertEqual(rendered, expected)
        self.assertEqual(set(delays), {16})

    def test_fish_keeps_existing_gui_cadence(self):
        _, _, delays = self.run_gui_second("dafeiyu")
        self.assertEqual(set(delays), {70})

    def test_gui_auto_state_changes_are_single_frame(self):
        # Core owns auto-idle on Windows: exercise the real GUI state->set_clip path.
        app, _, _ = self.run_gui_second("xiaohei")
        with patch.object(gui.ImageTk, "PhotoImage", side_effect=lambda im: im.copy()):
            for name in ("pat", "idle", "poke", "idle", "drag", "drop", "idle", "sing") * 3:
                app.state = lambda name=name: {"clip": name, "rice": 0}
                self.clock.ms += 16
                app.tick()
                self.assertEqual(app.anim.current, name)
                self.assert_single_frame(app.anim)

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("swiftc"), "requires macOS Swift/AppKit")
    def test_swift_player_and_baked_view(self):
        harness = Path(self.temp.name) / "PlayerRegression.swift"
        harness.write_text(SWIFT_HARNESS, encoding="utf-8")
        binary = Path(self.temp.name) / "player-regression"
        sources = sorted(p for p in (ROOT / "Sources").glob("*.swift") if p.name != "main.swift")
        build = subprocess.run(
            ["swiftc", "-swift-version", "5", *map(str, sources), str(harness),
             "-framework", "AppKit", "-framework", "QuartzCore", "-o", str(binary)],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        run = subprocess.run([str(binary), str(self.assets["xiaohei"]), str(self.assets["dafeiyu"])],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("Swift player/view regressions passed", run.stdout)


SWIFT_HARNESS = r'''
import AppKit
import Foundation

@main
struct PlayerRegression {
    static func main() throws {
        var failures: [String] = []
        func expect(_ condition: Bool, _ message: String) {
            if !condition { failures.append(message) }
        }
        func load(_ argument: Int) throws -> ClipPlayer {
            let root = URL(fileURLWithPath: CommandLine.arguments[argument])
            let data = try Data(contentsOf: root.appendingPathComponent("manifest.json"))
            let manifest = try JSONDecoder().decode(ClipManifest.self, from: data)
            return ClipPlayer(manifest: manifest, assets: root)
        }
        func single(_ p: ClipPlayer, _ context: String) {
            expect(p.previousImage == nil, "previousImage retained: \(context)")
            expect(p.blend == 1, "partial alpha: \(context)")
            expect(p.image() != nil, "missing fixture image: \(context)")
        }
        func pumpUntil(_ condition: () -> Bool, player: ClipPlayer) {
            let deadline = Date().addingTimeInterval(1)
            while !condition() && Date() < deadline {
                _ = player.tick()
                single(player, "auto tick")
                RunLoop.main.run(until: Date().addingTimeInterval(0.002))
            }
            expect(condition(), "auto completion deadline")
        }
        let cat = try load(1)
        single(cat, "initial")
        for force in [false, true, false, true] {
            for name in ["sing", "working", "pat", "poke", "drag", "drop", "rice", "still", "idle"] {
                cat.play(name, priority: 100, force: force)
                expect(cat.currentName == name, "switch rejected: \(name)")
                expect(cat.frameIndex == 0, "first frame skipped: \(name)")
                single(cat, "\(name) force=\(force)")
                _ = cat.tick()
                single(cat, "after tick \(name)")
            }
        }
        // A real non-looping clip must auto-return without retaining its last image.
        for _ in 0..<4 {
            cat.play("once", force: true)
            single(cat, "before auto-idle")
            pumpUntil({ cat.currentName == "idle" }, player: cat)
            single(cat, "auto-idle")
        }
        // Complete then force a different non-looping clip before the queued return runs.
        for _ in 0..<4 {
            cat.play("once", force: true)
            let deadline = Date().addingTimeInterval(1)
            while cat.busy && Date() < deadline { _ = cat.tick() }
            expect(!cat.busy, "once finished")
            cat.play("slow", loop: false, force: true)
            RunLoop.main.run(until: Date().addingTimeInterval(0.002))
            expect(cat.currentName == "slow", "stale auto-idle overrode forced clip")
            single(cat, "forced before queued auto-idle")
        }
        let fish = try load(2)
        fish.play("slow", transition: 10, force: true)
        expect(fish.previousImage != nil && fish.blend == 0, "fish lost crossfade")
        // Below the 1fps step, transition-only progress must still request a redraw.
        let changed = fish.tick()
        expect(fish.frameIndex == 0, "slow fixture advanced too soon")
        expect(fish.blend > 0 && fish.blend < 1, "fish transition did not progress")
        expect(changed, "transition-only tick swallowed redraw")
        fish.play("sing", transition: 0, force: true)
        single(fish, "explicit fish hard cut")

        func render(_ view: PetView) -> Data {
            let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 210, pixelsHigh: 175,
                bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
            NSGraphicsContext.saveGraphicsState()
            NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)!
            NSGraphicsContext.current!.cgContext.clear(view.bounds)
            view.draw(view.bounds)
            NSGraphicsContext.restoreGraphicsState()
            return rep.representation(using: .png, properties: [:])!
        }
        let view = PetView(frame: NSRect(x: 0, y: 0, width: 210, height: 175))
        view.player = cat
        for name in ["idle", "sing", "drag"] {
            cat.play(name, force: true)
            view.phase = 0; view.pulse = 0; view.singing = false; view.isDragging = false
            let baseline = render(view)
            for phase: CGFloat in [0.65, 1.45] {
                view.phase = phase
                expect(render(view) == baseline, "baked breathe shifted image/shadow")
                view.pulse = 0.5
                expect(render(view) == baseline, "baked hop shifted image/shadow")
                view.singing = true
                expect(render(view) == baseline, "baked singing transformed image/shadow")
                view.isDragging = true
                expect(render(view) == baseline, "baked dragging rotated image/shadow")
                view.pulse = 0; view.singing = false; view.isDragging = false
            }
        }
        view.player = fish
        fish.play("idle", transition: 0, force: true)
        view.phase = 0
        let fishBaseline = render(view)
        view.phase = 1.45
        expect(render(view) != fishBaseline, "fish lost breathe motion")
        if !failures.isEmpty {
            for failure in failures { print("FAIL: \(failure)") }
            exit(1)
        }
        print("Swift player/view regressions passed")
    }
}
'''


if __name__ == "__main__":
    unittest.main()
