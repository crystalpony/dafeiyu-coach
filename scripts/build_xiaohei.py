#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""五稿驱动：原像素 → 局部表情 → 同坐标变换 → 接地 → 独立道具。
只读 poses/{front,side,lie,sleep,angry}.png；300×250、3×超采样、24fps。
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Runtime/characters/xiaohei"
POSE_DIR = Path(__file__).parent / "poses"
W, H, S, FPS, GROUND = 300, 250, 3, 24, 241
BODY_INK, LINE_INK = (13, 11, 15), (52, 38, 30)
GOLD, MINT = (234, 192, 96), (156, 203, 72)
POSE_FILES = {"newfront": "front", "side": "side", "lie": "lie", "sleep": "sleep", "angry": "angry"}
POSE_TARGET_H = {"newfront": 690, "side": 675, "lie": 435, "sleep": 435, "angry": 575}
_POSE_CACHE, _EYE_CACHE = {}, {}


def pt(p):
    return p[0] * S, p[1] * S


def ellipse_pts(cx, cy, rx, ry, rot=0, n=48):
    r = math.radians(rot)
    return [(cx + rx*math.cos(i*math.tau/n)*math.cos(r) - ry*math.sin(i*math.tau/n)*math.sin(r),
             cy + rx*math.cos(i*math.tau/n)*math.sin(r) + ry*math.sin(i*math.tau/n)*math.cos(r)) for i in range(n)]


def fill(d, points, color):
    d.polygon([pt(p) for p in points], fill=color)


def stroke(d, points, color=LINE_INK, width=2, closed=False):
    points = [pt(p) for p in points]
    if closed:
        points.append(points[0])
    d.line(points, fill=color, width=max(1, round(width*S)), joint="curve")


def wave(t, period, phase=0):
    return math.sin(t * math.tau / period + phase)


def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)


def seg(t, start, end):
    return max(0., min(1., (t-start)/(end-start)))


def envelope(t, start, attack, release, end):
    return smooth(seg(t, start, attack)) * (1-smooth(seg(t, release, end)))


def blink(t, events):
    value = 1.
    for center, duration in events:
        phase = abs(t-center)/(duration/2)
        if phase < 1:
            value = min(value, smooth(phase))
    return value


@dataclass
class Pose:
    pose: str = "newfront"
    body_dx: float = 0.
    body_sx: float = 1.
    body_sy: float = 1.
    rot: float = 0.
    jump: float = 0.
    eye_open: float = 1.
    eye: str = "open"
    tail_wag: float = 0.
    wear_cap: bool = False
    prop: str | None = None
    prop_t: float = 0.
    shadow: float = 1.


def sanitize_pose(im):
    """沿用基线暗部归一；亮部与alpha不重新设计。"""
    arr = np.asarray(im).astype(np.int16)
    rgb, alpha = arr[..., :3], arr[..., 3]
    luma = rgb.mean(axis=2)
    bright = ((luma > 150).astype(np.uint8)*255)
    near = np.asarray(Image.fromarray(bright, "L").filter(ImageFilter.MaxFilter(9))) > 0
    rgb[(alpha > 0) & (luma <= 34)] = BODY_INK
    rgb[(alpha > 0) & (luma > 34) & (luma <= 96) & ~near] = LINE_INK
    return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")


def load_pose(name):
    if name not in POSE_FILES:
        raise ValueError(f"unknown source pose: {name}")
    if name not in _POSE_CACHE:
        with Image.open(POSE_DIR / (POSE_FILES[name]+".png")) as source:
            im = sanitize_pose(source.convert("RGBA"))
        im = im.crop(im.getbbox())
        target = POSE_TARGET_H[name]
        im = im.resize((round(im.width*target/im.height), target), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (W*S, H*S))
        canvas.alpha_composite(im, ((W*S-im.width)//2, GROUND*S-target))
        _POSE_CACHE[name] = canvas
    return _POSE_CACHE[name].copy()


# 选择原画连通眼白，不是重新设计的眼形。front/side等比小缩放留画布余量。
EYE_BOXES = {
    "newfront": [(70, 53, 149, 156), (156, 55, 230, 156)],
    "side": [(60, 53, 112, 143), (113, 72, 188, 158)],
    "sleep": [(145, 126, 221, 200), (144, 109, 171, 143)],
}


def largest_component(mask):
    pending = mask.copy(); largest = []
    for y, x in zip(*np.where(mask)):
        if not pending[y, x]:
            continue
        queue = deque([(int(y), int(x))]); pending[y, x] = False; points = []
        while queue:
            yy, xx = queue.popleft(); points.append((yy, xx))
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                ny, nx = yy+dy, xx+dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and pending[ny, nx]:
                    pending[ny, nx] = False; queue.append((ny, nx))
        if len(points) > len(largest):
            largest = points
    result = np.zeros(mask.shape, np.uint8)
    if largest:
        coords = np.array(largest); result[coords[:, 0], coords[:, 1]] = 255
    return Image.fromarray(result, "L")


def eye_regions(name):
    if name in _EYE_CACHE:
        return _EYE_CACHE[name]
    im = load_pose(name); regions = []
    for box in EYE_BOXES.get(name, []):
        box = tuple(round(v*S) for v in box)
        a = np.asarray(im.crop(box))
        mask = largest_component((a[..., :3].mean(2) > 165) & (a[..., 3] > 200))
        padded = Image.new("L", (mask.width+2, mask.height+2)); padded.paste(mask, (1, 1))
        flooded = padded.copy(); ImageDraw.floodfill(flooded, (0, 0), 255)
        padded = ImageChops.lighter(padded, ImageChops.invert(flooded))
        mask = padded.crop((1, 1, mask.width+1, mask.height+1))
        if name == "sleep" and not regions:
            # 主眼白是开口月牙，普通填孔算法不能包含左侧瞳孔；眼睑覆盖整只原眼。
            ImageDraw.Draw(mask).ellipse((0, 0, mask.width-1, mask.height-1), fill=255)
        if not mask.getbbox():
            raise ValueError(f"empty eye region: {name} {box}")
        regions.append((box, mask))
    _EYE_CACHE[name] = regions
    return regions


def apply_eyelids(layer, name, openness, happy=False):
    """使用原画整块眼像素闭合，不重画瞳孔/眼色。"""
    openness = max(0., min(1., openness))
    if openness >= .999:
        return
    for box, mask in eye_regions(name):
        original = layer.crop(box); cleared = original.copy()
        pixels = np.asarray(original)
        light = (pixels[..., :3].mean(2) > 165) & (np.asarray(mask) > 0)
        cream = BODY_INK if name == "sleep" else tuple(int(v) for v in np.median(pixels[..., :3][light], axis=0))
        cleared.paste(cream+(255,), (0, 0, original.width, original.height), mask)
        if openness > .12:
            eye = original.copy(); eye.putalpha(mask)
            height = max(1, round(eye.height*openness))
            eye = eye.resize((eye.width, height), Image.Resampling.LANCZOS)
            cleared.alpha_composite(eye, (0, (original.height-height)//2))
        else:
            bounds = mask.getbbox(); cx = (bounds[0]+bounds[2])/2; cy = (bounds[1]+bounds[3])/2
            rx = (bounds[2]-bounds[0])*.32
            points = [(cx+rx*u, cy+(1 if not happy else -1)*3*S*(1-u*u)) for u in np.linspace(-1, 1, 24)]
            ImageDraw.Draw(cleared).line(points, fill=LINE_INK+(255,), width=3*S, joint="curve")
        layer.paste(cleared, box[:2])


def wag_tail_side(im, amp):
    """单次逆映射，根部位移为0；不把形变混回原尾巴。"""
    if abs(amp) < .001:
        return im.copy()
    arr = np.asarray(im, dtype=np.float32); h, w = arr.shape[:2]
    yy, xx = np.mgrid[:h, :w]; x, y = xx/S, yy/S
    weight = np.clip((x-196)/58, 0, 1)**2
    band = np.clip((y-138)/22, 0, 1)*np.clip((248-y)/18, 0, 1)
    src = np.clip(xx-amp*weight*band*S, 0, w-1)
    x0 = src.astype(np.int32); x1 = np.minimum(x0+1, w-1); fraction = (src-x0)[..., None]
    arr[..., :3] *= arr[..., 3:]/255
    result = arr[yy, x0]*(1-fraction)+arr[yy, x1]*fraction
    result[..., :3] = np.divide(result[..., :3]*255, result[..., 3:], out=np.zeros_like(result[..., :3]), where=result[..., 3:] > 0)
    output = np.rint(np.clip(result, 0, 255)).astype(np.uint8)
    # 逆映射位移为零的区域必须保留原始RGBA，包括不可见像素的RGB。
    stationary = weight * band == 0
    output[stationary] = np.asarray(im)[stationary]
    return Image.fromarray(output, "RGBA")


def draw_cap(layer):
    d = ImageDraw.Draw(layer)
    crown = [(105, 47), (112, 32), (128, 25), (153, 25), (176, 34), (184, 48)]
    fill(d, crown, MINT); stroke(d, crown, width=3, closed=True)
    band = [(107, 43), (184, 46), (184, 53), (105, 50)]
    fill(d, band, (240, 233, 210)); stroke(d, band, closed=True)
    brim = [(178, 49), (211, 57), (221, 64), (188, 60)]
    fill(d, brim, (40, 58, 34)); stroke(d, brim, width=3, closed=True)
    for x in (124, 143, 162):
        stroke(d, [(x, 31), (145+(x-145)*.7, 44)], (108, 154, 58), 1.2)


def local_character(p):
    char = load_pose(p.pose)
    if p.pose == "newfront":
        draw_front_face(char, p)
    elif p.pose == "side":
        draw_side_face(char, p)
    elif p.pose == "sleep":
        apply_eyelids(char, "sleep", 0)
    if p.wear_cap:
        draw_cap(char)
    if p.pose == "side" and abs(p.tail_wag) > .001:
        char = wag_tail_side(char, p.tail_wag)
    return char


def transform_character(char, p):
    sx, sy = p.body_sx, p.body_sy
    if not (.85 <= sx <= 1.12 and .85 <= sy <= 1.12):
        raise ValueError("body transform outside authored range")
    theta = math.radians(p.rot); c, s = math.cos(theta), math.sin(theta)
    a, b, d, e = c/sx, s/sx, -s/sy, c/sy
    cx, cy = 150*S, GROUND*S
    tx, ty = cx-a*(cx+p.body_dx*S)-b*cy, cy-d*(cx+p.body_dx*S)-e*cy
    transformed = char.transform(char.size, Image.Transform.AFFINE, (a, b, tx, d, e, ty), Image.Resampling.BICUBIC)
    box = transformed.getchannel("A").point(lambda v: 255 if v >= 128 else 0).getbbox()
    if not box:
        raise ValueError("empty transformed character")
    offset = round((GROUND+p.jump)*S)-box[3]
    grounded = Image.new("RGBA", char.size); grounded.alpha_composite(transformed, (0, offset))
    return grounded


def draw_props(canvas, p):
    d = ImageDraw.Draw(canvas)
    if p.prop in ("notes", "mic"):
        for i, (x, y) in enumerate([(253, 83), (273, 63), (267, 108)]):
            y += 2*wave(p.prop_t, 2, i*1.3)
            fill(d, ellipse_pts(x, y, 3.3, 2.6, -20), GOLD)
            stroke(d, [(x+3, y), (x+3, y-12), (x+8, y-9)], GOLD, 1.8)
    if p.prop == "mic":
        # 原稿尾巴无法卷握：用独立落地立麦，不补分叉。
        stroke(d, [(267, 164), (267, 237)], width=3)
        stroke(d, [(252, 241), (267, 237), (282, 241)], width=3)
        stroke(d, [(267, 169), (254, 143)], width=5)
        fill(d, ellipse_pts(251, 137, 8, 10, -22), (238, 231, 214))
        stroke(d, ellipse_pts(251, 137, 8, 10, -22), closed=True)
        for y in (132, 136, 140):
            stroke(d, [(246, y), (256, y)], (126, 112, 88), 1)
    if p.prop in ("fish", "bowl"):
        x, y = 242, 229
        bowl = [(x-20, y), (x-15, y+12), (x+15, y+12), (x+20, y)]
        fill(d, bowl, (238, 230, 212)); stroke(d, bowl, closed=True)
        fill(d, ellipse_pts(x, y, 20, 4), (250, 245, 230)); stroke(d, ellipse_pts(x, y, 20, 4), closed=True)
        if p.prop == "fish":
            fill(d, ellipse_pts(x-2, y-3, 10, 5), (126, 174, 192))
            fill(d, [(x+6, y-3), (x+14, y-8), (x+14, y+1)], (126, 174, 192))
            fill(d, ellipse_pts(x-7, y-4, 1, 1), LINE_INK)
        else:
            for dx in (-9, 0, 9):
                fill(d, ellipse_pts(x+dx, y-4, 6, 5), (255, 253, 242))
    if p.prop == "exclaim":
        stroke(d, [(269, 74), (269, 91)], GOLD, 3); fill(d, ellipse_pts(269, 98, 2, 2), GOLD)
    if p.prop == "thinking":
        for x, y, r in [(249, 115, 2), (257, 104, 3), (268, 87, 5)]:
            fill(d, ellipse_pts(x, y+wave(p.prop_t, 4), r, r), GOLD)
    if p.prop == "working":
        for i in range(3):
            fill(d, ellipse_pts(249+i*12, 125-3*wave(p.prop_t, 3, i), 2.5, 2.5), GOLD)
    if p.prop == "zzz":
        for x, y, r in [(229, 116, 4), (248, 93, 5), (270, 71, 6)]:
            stroke(d, [(x-r, y), (x+r, y), (x-r, y+r), (x+r, y+r)], GOLD, 2)


def draw_front_face(layer, p):
    apply_eyelids(layer, "newfront", p.eye_open, happy=p.eye == "happy")
    d = ImageDraw.Draw(layer); nose = [(149.5, 140), (154.5, 140), (152, 150)]
    fill(d, nose, (151, 203, 233)); stroke(d, nose, width=.75, closed=True)


def draw_side_face(layer, p):
    apply_eyelids(layer, "side", p.eye_open, happy=p.eye == "happy")
    d = ImageDraw.Draw(layer); nose = [(120, 143), (135, 143), (128, 154)]
    fill(d, nose, (151, 203, 233)); stroke(d, nose, width=1.5, closed=True)


def render_pose(p, rig=False):
    char = transform_character(local_character(p), p)
    canvas = Image.new("RGBA", (W*S, H*S))
    if p.shadow > 0 and p.pose not in ("lie", "sleep"):
        shadow = Image.new("RGBA", canvas.size); width = 48*max(.4, 1+p.jump/70)
        ImageDraw.Draw(shadow).ellipse([pt((150+p.body_dx-width, GROUND-2)), pt((150+p.body_dx+width, GROUND+1))], fill=(13, 11, 15, round(55*p.shadow)))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(1.3*S)))
    canvas.alpha_composite(char); draw_props(canvas, p)
    if rig:
        stroke(ImageDraw.Draw(canvas), [(140, GROUND), (160, GROUND)], (20, 140, 120), 1)
    return canvas.resize((W, H), Image.Resampling.LANCZOS)


def render(p, rig=False):
    return render_pose(p, rig=rig)


CLIPS = {}


def clip(name, frames, loop):
    def register(fn):
        if name in CLIPS:
            raise ValueError(f"duplicate clip registration: {name}")
        CLIPS[name] = (frames, loop, fn)
        return fn
    return register


@clip("idle", 144, True)
def idle(t):
    return Pose(body_sy=1+.008*wave(t, 3), eye_open=blink(t, [(1.9, .25), (4.6, .24), (4.95, .20)]))


@clip("thinking", 96, True)
def thinking(t):
    return Pose(rot=.8*wave(t, 4), eye_open=blink(t, [(2.2, .26)]), prop="thinking", prop_t=t)


@clip("working", 72, True)
def working(t):
    return Pose(body_sy=1+.005*wave(t, 3), eye_open=blink(t, [(1.4, .23)]), prop="working", prop_t=t)


@clip("success", 60, False)
def success(t):
    k = envelope(t, .05, .4, 1.9, 2.45)
    return Pose(body_sy=1+.012*k, eye_open=1-k, eye="happy")


@clip("pat", 72, False)
def pat(t):
    k = envelope(t, 0, .4, 2.3, 2.95)
    return Pose(body_sy=1-.012*k, rot=.8*k, eye_open=1-k, eye="happy")


@clip("error", 72, False)
def error(t):
    return Pose(pose="angry", rot=.8*envelope(t, 0, .35, 2.4, 2.95), prop="exclaim")


@clip("poke", 48, False)
def poke(t):
    k = envelope(t, .05, .25, .5, 1.95)
    return Pose(pose="angry", body_sy=1-.015*k, rot=-1.2*k, prop="exclaim")


@clip("tail", 96, True)
def tail(t):
    return Pose(pose="side", tail_wag=6*wave(t, 2), eye_open=blink(t, [(2.7, .26)]))


@clip("drag", 48, True)
def drag(t):
    return Pose(pose="side", rot=2+.8*wave(t, 2), shadow=0)


@clip("drop", 48, False)
def drop(t):
    k = envelope(t, 0, .2, .35, .9)
    return Pose(pose="side", body_sy=1-.028*k, body_sx=1+.012*k)


@clip("roll", 72, False)
def roll(t):
    k = envelope(t, .05, .3, 2.6, 2.95)
    return Pose(pose="lie", rot=2*wave(t, 1.5)*k, shadow=0)


@clip("sleep", 96, True)
def sleep(t):
    return Pose(pose="sleep", body_sy=1+.009*wave(t, 4), shadow=0, prop="zzz")


@clip("wash", 72, False)
def wash(t):
    k = envelope(t, .05, .4, 2.4, 2.95)
    return Pose(pose="side", rot=1.4*wave(t, 1.5)*k, eye_open=1-k, eye="happy")


@clip("meow", 36, False)
def meow(t):
    k = envelope(t, .08, .3, .65, 1.2)
    return Pose(body_sy=1+.012*k, eye_open=blink(t, [(.75, .22)]))


@clip("heixiu", 96, False)
def heixiu(t):
    # 只保留正面稿自带黑咻，不另画新造型分身。
    k = envelope(t, .1, .5, 3.1, 3.95)
    return Pose(rot=.7*wave(t, 2)*k, eye_open=blink(t, [(1.3, .25), (2.8, .25)]))


@clip("yawn", 72, False)
def yawn(t):
    k = envelope(t, .1, .6, 2.1, 2.95)
    return Pose(pose="side", body_sy=1+.014*k, eye_open=1-k)


@clip("eat", 96, False)
def eat(t):
    k = envelope(t, .1, .5, 3.2, 3.95)
    return Pose(pose="side", rot=.5*wave(t, 1)*k, prop="fish", prop_t=t, eye_open=blink(t, [(1.8, .24)]))


@clip("rice", 120, False)
def rice(t):
    k = envelope(t, .1, .5, 4.2, 4.95)
    return Pose(pose="side", rot=.5*wave(t, 1)*k, prop="bowl", prop_t=t, eye_open=blink(t, [(2.5, .24)]))


@clip("pounce", 60, False)
def pounce(t):
    k = envelope(t, .05, .4, .7, 2.45)
    return Pose(pose="side", body_sy=1-.025*k, rot=-1.2*k)


@clip("fluff", 48, False)
def fluff(t):
    # 无游离毛刺；使用完整生气稿表达受惊停顿。
    k = envelope(t, .05, .2, 1.3, 1.95)
    return Pose(pose="angry", body_sy=1+.012*k, prop="exclaim")


@clip("stretch", 84, False)
def stretch(t):
    k = envelope(t, .05, 1.1, 2.4, 3.45)
    return Pose(pose="side", body_sy=1+.02*k, eye_open=1-k)


def singing(t):
    return Pose(pose="side", rot=.7*wave(t, 2), body_sy=1+.006*wave(t, 1), eye_open=0, eye="happy")


@clip("sing", 96, True)
def sing(t):
    return singing(t)


@clip("sing_mic", 96, True)
def sing_mic(t):
    p = singing(t); p.prop = "mic"; p.prop_t = t
    return p


@clip("sing_hat", 96, True)
def sing_hat(t):
    p = singing(t); p.wear_cap = True; p.prop = "notes"; p.prop_t = t; p.body_sy = 1+.008*wave(t, .5)
    return p


@clip("sing_tail", 96, True)
def sing_tail(t):
    p = singing(t); p.tail_wag = 5*wave(t, 2); p.prop = "notes"; p.prop_t = t
    return p


def source_provenance():
    return {f"scripts/poses/{name}.png": hashlib.sha256((POSE_DIR/(name+".png")).read_bytes()).hexdigest() for name in POSE_FILES.values()}


def _render_frame(task):
    name, index, folder = task
    im = render(CLIPS[name][2](index/FPS)); rel = f"{name}/{name}_{index:03d}.webp"
    im.save(Path(folder)/rel, "WEBP", quality=92, method=6)
    return rel


def generate(destination, names, jobs):
    manifest = {"formatVersion": 1, "character": "xiaohei", "displayName": "小黑", "frameSize": [W, H], "transition": "single-frame",
                "license": "User-provided fan art; character © MTJJ / 北京寒木春华. See NOTICE.md.",
                "source": {"poses": source_provenance(), "generatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, "clips": {}}
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for name in names:
            count, loop, fn = CLIPS[name]; (destination/name).mkdir(parents=True, exist_ok=True)
            frames = list(pool.map(_render_frame, [(name, i, str(destination)) for i in range(count)], chunksize=8))
            manifest["clips"][name] = {"fps": FPS, "loop": loop, "frameCount": count, "durationMs": round(count/FPS*1000), "pose": fn(0).pose, "frames": frames,
                                       "sha256": [hashlib.sha256((destination/f).read_bytes()).hexdigest() for f in frames]}
            print(f"{name}: {count} frames", flush=True)
    return manifest


def publish(stage, manifest, destination=OUT):
    """先备齐整套文件，再切换目录；可捕获的发布异常恢复上一套目录。"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = Path(tempfile.mkdtemp(prefix=".xiaohei-publish-", dir=destination.parent))
    previous = Path(tempfile.mkdtemp(prefix=".xiaohei-previous-", dir=destination.parent))
    moved_old = False
    published = False
    try:
        for clip_info in manifest["clips"].values():
            for rel in clip_info["frames"]:
                source = stage / rel if (stage / rel).is_file() else destination / rel
                target = pending / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        (pending / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1)+"\n", encoding="utf-8")
        if destination.exists():
            os.replace(destination, previous)
            moved_old = True
        try:
            os.replace(pending, destination)
        except BaseException:
            if moved_old:
                os.replace(previous, destination)
                moved_old = False
            raise
        published = True
    finally:
        shutil.rmtree(pending, ignore_errors=True)
        # 若恢复本身失败，旧目录留在.previous供人工恢复，不能顺手删掉。
        if published or not moved_old:
            shutil.rmtree(previous, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", nargs="*", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    args = ap.parse_args()
    if args.preview is not None:
        for name in args.preview or CLIPS:
            sheet = Image.new("RGBA", (W*5, H*3), (248, 246, 240, 255))
            for i in range(15):
                sheet.alpha_composite(render(CLIPS[name][2](i/15*CLIPS[name][0]/FPS)), ((i%5)*W, (i//5)*H))
            sheet.convert("RGB").save(f"/tmp/xiaohei_{name}_sheet.jpg")
        return
    names = args.only or list(CLIPS)
    if not set(names) <= set(CLIPS) or args.jobs < 1:
        ap.error("unknown clip or invalid jobs")
    if args.only:
        old = json.loads((OUT/"manifest.json").read_text()) if (OUT/"manifest.json").exists() else {}
        source = old.get("source", {})
        if source.get("generatorSha256") != hashlib.sha256(Path(__file__).read_bytes()).hexdigest() or source.get("poses") != source_provenance():
            ap.error("source changed: a full rebuild is required before --only")
    # 所有帧在本地staging渲染成功后才发布；异常不先删活跃帧。
    with tempfile.TemporaryDirectory(prefix="xiaohei-render-") as temp:
        stage = Path(temp); manifest = generate(stage, names, args.jobs)
        if args.only and (OUT/"manifest.json").exists():
            old = json.loads((OUT/"manifest.json").read_text())
            old["clips"].update(manifest["clips"]); manifest["clips"] = old["clips"]
        publish(stage, manifest)
    size = sum((OUT/f).stat().st_size for c in manifest["clips"].values() for f in c["frames"])
    print(f"manifest: {len(manifest['clips'])} clips / {sum(c['frameCount'] for c in manifest['clips'].values())} frames / {size/1048576:.2f} MB (referenced frames)")


if __name__ == "__main__":
    main()
