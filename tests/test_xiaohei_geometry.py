"""Pixel/geometry regressions against the five source poses, without Runtime frames.

Run with: python3 -B -m unittest discover -s tests -p test_xiaohei_geometry.py -v
Coordinates in fixtures are authored at 300x250 and inspected at native 3x scale.
"""
from __future__ import annotations

import ast
import importlib.util
import itertools
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "build_xiaohei.py"
SPEC = importlib.util.spec_from_file_location("xiaohei_geometry_generator", GENERATOR)
g = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = g  # dataclasses resolves annotations through sys.modules.
SPEC.loader.exec_module(g)

SCALE = 3
SIZE = (900, 750)
SOURCES = {"newfront": "front", "side": "side", "lie": "lie",
           "sleep": "sleep", "angry": "angry"}
# Independent, fixed ROIs: do not borrow the implementation's editable eye masks.
FRONT_EYES = ((70, 53, 149, 156), (156, 55, 230, 156))
FRONT_MOUTH = (138, 156, 174, 173)
SLEEP_MAIN_EYE = (148, 126, 221, 200)


def crop_pixels(image, box):
    return np.asarray(image.crop(tuple(v * SCALE for v in box)))


def bright_pixels(pixels):
    return (pixels[..., :3].mean(axis=2) > 165) & (pixels[..., 3] > 200)


def clip_poses():
    for name, (frames, _, fn) in g.CLIPS.items():
        for index in range(frames):
            yield name, index, fn(index / g.FPS)


def runs(mask):
    """Half-open contiguous runs; opposite silhouette edges are separate runs."""
    changes = np.diff(np.pad(np.asarray(mask, dtype=np.int8), (1, 1)))
    return list(zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)))


def tail_rectangle():
    pixels = np.zeros((SIZE[1], SIZE[0], 4), dtype=np.uint8)
    pixels[170 * SCALE:225 * SCALE, 220 * SCALE:238 * SCALE] = (25, 65, 105, 255)
    return Image.fromarray(pixels, "RGBA")


def legacy_blended_tail(image, amplitude):
    """Negative control: the old arr*(1-mask)+warped*mask ghosting operation.

    Deliberately independent of wag_tail_side, so a regression in that function
    cannot change the bad fixture or silently weaken the contour assertion.
    """
    pixels = np.asarray(image, dtype=np.float64)
    yy, xx = np.indices(pixels.shape[:2])
    x, y = xx / SCALE, yy / SCALE
    mask = (np.clip((x - 196) / 58, 0, 1) ** 2
            * np.clip((y - 138) / 22, 0, 1)
            * np.clip((248 - y) / 18, 0, 1))
    source_x = np.clip(xx - amplitude * SCALE * mask, 0, image.width - 1)
    left = np.floor(source_x).astype(int)
    right = np.minimum(left + 1, image.width - 1)
    fraction = (source_x - left)[..., None]
    warped = pixels[yy, left] * (1 - fraction) + pixels[yy, right] * fraction
    blended = pixels * (1 - mask[..., None]) + warped * mask[..., None]
    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), "RGBA")


def nose_mask(image):
    """Find actual blue nose pixels, not an implementation-provided landmark."""
    pixels = np.asarray(image).astype(np.int16)
    r, green, blue, alpha = np.moveaxis(pixels, -1, 0)
    return ((alpha >= 200) & (r >= 90) & (r <= 190)
            & (green >= 150) & (blue >= 200)
            & (green - r > 25) & (blue - green > 15))


def centroid(mask):
    y, x = np.nonzero(mask)
    if not x.size:
        raise AssertionError("actual blue nose pixels are missing")
    return np.array([x.mean(), y.mean()])


def affine_nose_prediction(image, pose):
    """Independent NumPy forward geometry + bilinear-alpha grounding oracle.

    No calls to transform_character, Pillow affine, or any generator geometry
    helper. Pixel centers, not pixel corners, are transformed. Bilinear alpha
    predicts the >=128 ground row; the 1.25 native-pixel budget allows the
    generator's bicubic boundary rounding, not a separately anchored face.
    """
    theta = np.deg2rad(pose.rot)
    rotation = np.array([[np.cos(theta), -np.sin(theta)],
                         [np.sin(theta), np.cos(theta)]])
    forward = rotation @ np.diag([pose.body_sx, pose.body_sy])
    anchor = np.array([150 * SCALE, g.GROUND * SCALE], dtype=float)
    translation = np.array([pose.body_dx * SCALE, 0.0])
    predicted = forward @ (centroid(nose_mask(image)) + .5 - anchor)
    predicted += anchor + translation - .5

    alpha = np.asarray(image)[..., 3].astype(float)
    yy, xx = np.indices(alpha.shape, dtype=float)
    destinations = np.stack((xx + .5, yy + .5), axis=-1)
    source = ((destinations - anchor - translation) @ np.linalg.inv(forward).T
              + anchor - .5)
    x0 = np.floor(source[..., 0]).astype(int)
    y0 = np.floor(source[..., 1]).astype(int)
    fx, fy = source[..., 0] - x0, source[..., 1] - y0
    sampled_alpha = np.zeros_like(alpha)
    for dx, dy in itertools.product((0, 1), repeat=2):
        x, y = x0 + dx, y0 + dy
        inside = (x >= 0) & (x < image.width) & (y >= 0) & (y < image.height)
        weight = (fx if dx else 1 - fx) * (fy if dy else 1 - fy)
        sampled_alpha[inside] += alpha[y[inside], x[inside]] * weight[inside]
    occupied_rows = np.flatnonzero(np.any(sampled_alpha >= 128, axis=1))
    if not occupied_rows.size:
        raise AssertionError("independent affine oracle lost the character")
    predicted[1] += round((g.GROUND + pose.jump) * SCALE) - (occupied_rows[-1] + 1)
    return predicted


class XiaoheiGeometryTests(unittest.TestCase):
    def assert_pixels_equal(self, actual, expected, context):
        actual, expected = np.asarray(actual), np.asarray(expected)
        self.assertEqual(actual.shape, expected.shape, context)
        changed = np.any(actual != expected, axis=-1)
        count = int(np.count_nonzero(changed))
        delta = int(np.abs(actual.astype(np.int16) - expected.astype(np.int16)).max())
        self.assertEqual(count, 0, f"{context}: {count} changed RGBA pixels; max channel delta={delta}")

    def assert_single_tail_contour(self, image):
        alpha = np.asarray(image)[..., 3]
        occupied = np.flatnonzero(np.any(alpha > 0, axis=1))
        self.assertGreater(occupied.size, 0, "tail disappeared")
        for y in occupied:
            row = alpha[y]
            fractional = runs((row > 0) & (row < 255))
            for start, end in fractional:
                self.assertLessEqual(
                    end - start, 2,
                    f"semi-transparent tail edge spans {end - start}px at y={y}, "
                    f"x=[{start},{end}) in native 900px space (maximum 2px)")
            self.assertLessEqual(len(fractional), 2, f"multiple tail edges at y={y}")
            self.assertEqual(len(runs(row > 0)), 1, f"split tail silhouette at y={y}")
            self.assertEqual(len(runs(row == 255)), 1, f"tail lost its single opaque core at y={y}")

    def test_ast_has_25_unique_clip_declarations_and_1992_frames(self):
        declarations = []
        tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if (isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Name)
                        and decorator.func.id == "clip"):
                    self.assertEqual(len(decorator.args), 3, f"@clip on {node.name}")
                    name, frames, loop = map(ast.literal_eval, decorator.args)
                    declarations.append((name, frames, loop, node.name))
        self.assertEqual(len(declarations), 25)
        self.assertEqual(len({item[0] for item in declarations}), 25,
                         "duplicate @clip names must not be hidden by a dict overwrite")
        self.assertEqual(sum(item[1] for item in declarations), 1992)
        self.assertEqual(len(g.CLIPS), 25)
        self.assertEqual(sum(item[0] for item in g.CLIPS.values()), 1992)
        self.assertEqual({name for name, *_ in declarations}, set(g.CLIPS))
        for name, frames, loop, function_name in declarations:
            with self.subTest(clip=name):
                actual_frames, actual_loop, fn = g.CLIPS[name]
                self.assertEqual((actual_frames, actual_loop, fn.__name__),
                                 (frames, loop, function_name))

    def test_duplicate_clip_raises_without_overwriting_original_function(self):
        registry = dict(g.CLIPS)
        before = dict(registry)
        original = registry["idle"]

        def replacement(t):
            return g.Pose(pose="angry")

        with patch.object(g, "CLIPS", registry):
            with self.assertRaises(ValueError):
                g.clip("idle", 1, False)(replacement)
            self.assertEqual(registry, before)
            self.assertIs(registry["idle"], original)
            self.assertIs(registry["idle"][2], original[2])

    def test_load_pose_opens_only_the_five_sources_never_legacy_base(self):
        self.assertEqual(g.POSE_FILES, SOURCES)
        expected = {(ROOT / "scripts" / "poses" / f"{stem}.png").resolve()
                    for stem in SOURCES.values()}
        opened = []
        original_open = Image.open

        def checked_open(path, *args, **kwargs):
            resolved = Path(path).resolve()
            self.assertNotIn("xiaohei_base_hi", str(resolved))
            self.assertIn(resolved, expected, f"non-five-pose source read: {resolved}")
            opened.append(resolved)
            return original_open(path, *args, **kwargs)

        with patch.object(g, "_POSE_CACHE", {}), patch.object(g.Image, "open", side_effect=checked_open):
            for name in SOURCES:
                with self.subTest(pose=name):
                    image = g.load_pose(name)
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.size, SIZE)
                    self.assertIsNotNone(image.getchannel("A").getbbox())
        self.assertCountEqual(opened, expected)
        for name, index, pose in clip_poses():
            with self.subTest(clip=name, frame=index):
                self.assertIn(pose.pose, SOURCES)

    def test_load_pose_rejects_front_and_other_noncanonical_names_before_io(self):
        invalid = ("front", "xiaohei_base_hi", "xiaohei_base_hi.png",
                   "../xiaohei_base_hi", "poses/front.png", "unknown", "")
        # A stale cache must not make a forbidden alias valid either.
        for cached in (False, True):
            cache = {name: Image.new("RGBA", SIZE) for name in invalid} if cached else {}
            with patch.object(g, "_POSE_CACHE", cache), patch.object(g.Image, "open") as opener:
                for name in invalid:
                    with self.subTest(name=name, stale_cache=cached):
                        with self.assertRaises(ValueError):
                            g.load_pose(name)
                        opener.assert_not_called()

    def test_neutral_front_eye_rois_are_exact_source_pixels(self):
        source = g.load_pose("newfront")
        for box in FRONT_EYES:
            self.assertGreater(int(bright_pixels(crop_pixels(source, box)).sum()), 100,
                               f"empty or misplaced original eye ROI: {box}")
        neutral_poses = [("Pose()", g.Pose()), ("idle(0)", g.CLIPS["idle"][2](0))]
        neutral_poses.extend((f"{name}(0)", fn(0)) for name, (_, _, fn) in g.CLIPS.items()
                             if fn(0).pose == "newfront" and fn(0).eye_open == 1)
        for label, pose in neutral_poses:
            local = g.local_character(pose)
            for box in FRONT_EYES:
                with self.subTest(pose=label, roi=box):
                    self.assert_pixels_equal(crop_pixels(local, box), crop_pixels(source, box),
                                             f"{label}: original front eye ROI {box}")

    def test_every_front_action_frame_preserves_original_mouth_roi(self):
        original = crop_pixels(g.load_pose("newfront"), FRONT_MOUTH)
        self.assertGreater(np.unique(original[..., :3].reshape(-1, 3), axis=0).shape[0], 1,
                           "original mouth ROI must not be an empty uniform fixture")
        covered = set()
        for name, index, pose in clip_poses():
            if pose.pose != "newfront":
                continue
            covered.add(name)
            with self.subTest(clip=name, frame=index):
                self.assert_pixels_equal(crop_pixels(g.local_character(pose), FRONT_MOUTH),
                                         original, f"{name}[{index}] repainted the original mouth")
        self.assertTrue({"idle", "thinking", "working", "success", "pat", "meow", "heixiu"} <= covered)
        for openness, expression in itertools.product((0.0, 0.5, 1.0), ("open", "happy")):
            with self.subTest(eye_open=openness, expression=expression):
                pose = g.Pose(eye_open=openness, eye=expression)
                self.assert_pixels_equal(crop_pixels(g.local_character(pose), FRONT_MOUTH),
                                         original, "front expression repainted the original mouth")

    def test_actual_front_and_side_noses_follow_maximum_whole_character_affine(self):
        # All scale limits, both rotation signs, and translation: a screen-fixed
        # or separately scaled face cannot accidentally pass at an identity pose.
        extremes = ((-2.8, .85, 1.12, -8), (2.8, 1.12, .85, 8),
                    (-2.8, 1.12, 1.12, -8), (2.8, .85, .85, 8))
        for name in ("newfront", "side"):
            local = g.local_character(g.Pose(pose=name, shadow=0))
            mask = nose_mask(local)
            self.assertGreater(int(mask.sum()), 20, f"{name}: no measurable actual nose")
            original_center = centroid(mask)
            for rot, sx, sy, dx in extremes:
                pose = g.Pose(pose=name, rot=rot, body_sx=sx, body_sy=sy, body_dx=dx, shadow=0)
                with self.subTest(pose=name, rot=rot, sx=sx, sy=sy, dx=dx):
                    predicted = affine_nose_prediction(local, pose)
                    self.assertGreater(np.linalg.norm(predicted - original_center), 6,
                                       "affine fixture is too small to detect a fixed nose")
                    transformed = g.transform_character(local.copy(), pose)
                    actual = centroid(nose_mask(transformed))
                    error = float(np.linalg.norm(actual - predicted))
                    self.assertLessEqual(error, 1.25,
                                         f"{name}: nose={actual}, affine prediction={predicted}, "
                                         f"error={error:.3f} native pixels")
                    # Feed exactly the same local raster into the complete render
                    # path: facial features must not be redrawn after the affine.
                    with patch.object(g, "local_character", return_value=local.copy()):
                        rendered = g.render(pose)
                    expected_render = transformed.resize((300, 250), Image.Resampling.LANCZOS)
                    self.assert_pixels_equal(rendered, expected_render,
                                             f"{name}: render changed the transformed local raster")
                    rendered_center = (centroid(nose_mask(rendered)) + .5) * SCALE - .5
                    self.assertLessEqual(float(np.linalg.norm(rendered_center - predicted)), 2.25,
                                         f"{name}: rendered nose drifted from its body")

    def test_side_tail_has_one_contour_and_at_most_two_pixel_soft_edges(self):
        original = tail_rectangle()
        self.assertEqual(set(np.unique(np.asarray(original)[..., 3])), {0, 255})
        self.assert_single_tail_contour(original)
        old_center = centroid(np.asarray(original)[..., 3] >= 128)
        for amplitude in (-6, 6):
            with self.subTest(amplitude=amplitude):
                result = g.wag_tail_side(original, amplitude)
                self.assertEqual(result.size, SIZE)
                self.assert_single_tail_contour(result)
                new_center = centroid(np.asarray(result)[..., 3] >= 128)
                self.assertGreater((new_center[0] - old_center[0]) * np.sign(amplitude), .5,
                                   "a no-op tail must not pass the single-contour check")

    def test_tail_contour_assertion_rejects_old_mask_blend_ghosts(self):
        for amplitude in (-6, 6):
            with self.subTest(amplitude=amplitude):
                ghost = legacy_blended_tail(tail_rectangle(), amplitude)
                with self.assertRaisesRegex(AssertionError, "semi-transparent tail edge spans"):
                    self.assert_single_tail_contour(ghost)

    def test_tail_wag_preserves_the_entire_left_half_exactly(self):
        sentinel = np.asarray(tail_rectangle()).copy()
        rng = np.random.default_rng(2026)
        sentinel[:, :SIZE[0] // 2, :3] = rng.integers(
            0, 256, size=(SIZE[1], SIZE[0] // 2, 3), dtype=np.uint8)
        # Nonzero varied alpha catches lossy premultiply/unpremultiply even in
        # regions where the displacement is exactly zero; RGB is not disposable.
        sentinel[:, :SIZE[0] // 2, 3] = rng.integers(
            1, 256, size=(SIZE[1], SIZE[0] // 2), dtype=np.uint8)
        fixtures = (("source side", g.load_pose("side")),
                    ("independent RGBA sentinel", Image.fromarray(sentinel, "RGBA")))
        for label, original in fixtures:
            before = np.asarray(original).copy()
            for amplitude in (-6, 0, 6):
                with self.subTest(fixture=label, amplitude=amplitude):
                    result = g.wag_tail_side(original, amplitude)
                    self.assert_pixels_equal(np.asarray(result)[:, :SIZE[0] // 2],
                                             before[:, :SIZE[0] // 2],
                                             f"{label}: tail wag {amplitude} changed the left half")
                    self.assert_pixels_equal(original, before, "tail wag mutated its input")

    def test_nonjumping_pose_ground_does_not_drift_with_rotation_or_scale(self):
        transforms = ((0, 1, 1), (-2.8, 1, 1), (2.8, 1, 1),
                      (0, .85, 1), (0, 1.12, 1), (0, 1, .85), (0, 1, 1.12),
                      (-2.8, .85, 1.12), (2.8, 1.12, .85))
        self.assertEqual((g.W, g.H, g.S), (300, 250, SCALE))
        for name in SOURCES:
            ordinary = g.Pose(pose=name)
            local = g.local_character(ordinary)
            for rot, sx, sy in transforms:
                with self.subTest(pose=name, rot=rot, sx=sx, sy=sy):
                    pose = replace(ordinary, rot=rot, body_sx=sx, body_sy=sy)
                    self.assertEqual(pose.jump, 0)
                    alpha = np.asarray(g.transform_character(local.copy(), pose))[..., 3]
                    rows = np.flatnonzero(np.any(alpha >= 128, axis=1))
                    self.assertGreater(rows.size, 0, "ground test lost the character")
                    # Exclusive bottom, matching an alpha>=128 bounding box.
                    self.assertEqual(int(rows[-1]) + 1, g.GROUND * SCALE,
                                     f"{name}: nonjumping feet drifted off the ground")

    def test_meow_first_last_and_duration_endpoint_equal_idle_zero(self):
        frames, _, fn = g.CLIPS["meow"]
        idle = g.CLIPS["idle"][2](0)
        expected_local = g.local_character(idle)
        expected_frame = g.render(idle)
        for t in (0, (frames - 1) / g.FPS, frames / g.FPS):
            with self.subTest(time=t):
                self.assert_pixels_equal(g.local_character(fn(t)), expected_local,
                                         f"meow({t}) local pose does not return to idle(0)")
                self.assert_pixels_equal(g.render(fn(t)), expected_frame,
                                         f"meow({t}) rendered frame does not return to idle(0)")

    def test_meow_interior_frames_are_not_static(self):
        frames, _, fn = g.CLIPS["meow"]
        idle = np.asarray(g.render(g.CLIPS["idle"][2](0)))
        changes = []
        for index in range(1, frames - 1):
            frame = np.asarray(g.render(fn(index / g.FPS)))
            changes.append(int(np.count_nonzero(np.any(frame != idle, axis=2))))
        self.assertGreater(max(changes), 0, "all interior meow frames are identical to idle(0)")
        self.assertGreater(sum(count > 0 for count in changes), 1,
                           "meow is static except for a single-frame glitch")

    def test_sleep_main_eye_brightness_drops_by_more_than_ninety_percent(self):
        source = crop_pixels(g.load_pose("sleep"), SLEEP_MAIN_EYE)
        before = int(bright_pixels(source).sum())
        self.assertGreater(before, 100, "fixed main-eye ROI does not contain the original eye white")
        # Only the main eye, excluding the bright ear and the separate upper eye.
        for label, pose in (("Pose(sleep)", g.Pose(pose="sleep")),
                            ("sleep(0)", g.CLIPS["sleep"][2](0)),
                            ("sleep(1)", g.CLIPS["sleep"][2](1))):
            with self.subTest(pose=label):
                after = int(bright_pixels(crop_pixels(g.local_character(pose), SLEEP_MAIN_EYE)).sum())
                self.assertLess(after / before, .1,
                                f"{label}: main-eye bright pixels {before} -> {after}; "
                                f"reduction={1 - after / before:.2%}, required >90%")


if __name__ == "__main__":
    unittest.main()
