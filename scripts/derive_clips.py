#!/usr/bin/env python3
"""Derive the rice / sing clips from the licensed yawn motion.

`rice` keeps the feeding motion but paints an upright bowl of rice in front of
the character (never the blue token orbs from `eat`).
`sing` is a shorter ping-pong loop of the open-mouth segment, used while the
music watcher is singing.

Run after scripts/build_assets.py:
    python3 scripts/derive_clips.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "Runtime" / "clips"
SIZE = (300, 250)
SS = 3  # supersample for smooth bowl edges
INK = (52, 76, 150, 255)
INK_LIGHT = (108, 136, 210, 255)
WOOD = (176, 124, 74, 255)
WOOD_DARK = (126, 84, 48, 255)


def alpha_bbox(im: Image.Image) -> tuple[int, int, int, int]:
    box = im.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
    return box or (60, 40, 240, 242)


def bowl_layer(cx: float, rim_y: float, frame: int, total: int) -> Image.Image:
    """One upright rice bowl, drawn at SS× then downsampled."""
    w, h = SIZE[0] * SS, SIZE[1] * SS
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, rim_y = cx * SS, rim_y * SS
    bw = 88 * SS
    rim_h = 14 * SS
    bottom = rim_y + 34 * SS
    foot_y = bottom + 3 * SS

    t = frame / max(1, total)
    bob = 1.0 * math.sin(t * math.tau) * SS
    rim_y += bob
    bottom += bob
    foot_y += bob

    # rice mound above the rim (textured so it reads as rice, not an empty bowl)
    mound = [cx - bw * 0.40, rim_y - 22 * SS, cx + bw * 0.40, rim_y + 12 * SS]
    d.ellipse(mound, fill=(255, 253, 244, 255))
    d.arc(mound, 195, 345, fill=(204, 207, 214, 255), width=max(1, int(1.6 * SS)))
    for i in range(22):
        gx = cx - bw * 0.36 + (i * 37 % 61) / 61 * bw * 0.72
        gy = rim_y - 20 * SS + (i * 17 % 23) / 23 * 17 * SS
        d.ellipse([gx, gy, gx + 4.2 * SS, gy + 1.9 * SS], fill=(226, 225, 214, 255))
    # a few grains sitting on the mound's top edge
    for i in range(5):
        gx = cx - bw * 0.26 + i * bw * 0.13
        gy = rim_y - 22 * SS - (i % 2) * 2 * SS
        d.ellipse([gx, gy, gx + 3.6 * SS, gy + 1.6 * SS], fill=(255, 255, 255, 255))

    # bowl body: rim wider than the rounded foot
    top_l, top_r = cx - bw / 2, cx + bw / 2
    bot_l, bot_r = cx - bw * 0.28, cx + bw * 0.28
    body = [
        (top_l, rim_y),
        (bot_l, bottom),
        (bot_l + 9 * SS, foot_y),
        (bot_r - 9 * SS, foot_y),
        (bot_r, bottom),
        (top_r, rim_y),
    ]
    # soft drop shadow so the bowl separates from the apron
    shadow = [(x + 2 * SS, y + 2 * SS) for x, y in body]
    d.polygon(shadow, fill=(28, 40, 80, 38))
    d.polygon(body, fill=(255, 254, 250, 255))

    # soft blue shading on the bowl's lower-left
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.polygon(body, fill=(208, 222, 247, 255))
    shade.putalpha(shade.getchannel("A").point(lambda v: int(v * 0.38)))
    layer.alpha_composite(shade)
    d.line(body[1:4], fill=(196, 211, 240, 255), width=max(1, int(1.1 * SS)))
    d.line(body[4:], fill=(196, 211, 240, 255), width=max(1, int(1.1 * SS)))

    # blue band just under the rim
    band = [top_l + 2 * SS, rim_y + 2 * SS, top_r - 2 * SS, rim_y + 9 * SS]
    d.arc([top_l + 2 * SS, rim_y - 4 * SS, top_r - 2 * SS, rim_y + 13 * SS], 0, 180,
          fill=(196, 212, 244, 255), width=max(1, int(2.4 * SS)))
    # blue rim (opening at the top, narrower foot at the bottom)
    d.arc([top_l, rim_y - rim_h / 2, top_r, rim_y + rim_h / 2], 0, 360,
          fill=INK, width=max(1, int(1.8 * SS)))
    d.arc([top_l + 5 * SS, rim_y - rim_h * 0.24, top_r - 5 * SS, rim_y + rim_h * 0.24],
          0, 360, fill=INK_LIGHT, width=max(1, SS))

    # rice visible just inside the rim
    inner = [top_l + 5 * SS, rim_y - rim_h * 0.30, top_r - 5 * SS, rim_y + rim_h * 0.22]
    d.ellipse(inner, fill=(255, 255, 251, 255))
    for i in range(7):
        gx = cx - bw * 0.30 + (i % 4) * bw * 0.18 + (i % 3) * SS
        gy = rim_y - 2 * SS + (i // 4) * 2 * SS
        d.ellipse([gx, gy, gx + 3.0 * SS, gy + 1.4 * SS], fill=(231, 230, 220, 255))

    # foot + wave band + a tiny fish motif, echoing the apron
    d.rounded_rectangle([cx - bw * 0.22, foot_y - 2 * SS, cx + bw * 0.22, foot_y + 3 * SS],
                        radius=2 * SS, fill=(238, 243, 254, 255), outline=INK_LIGHT,
                        width=max(1, SS))
    for i in range(3):
        wx = cx - 20 * SS + i * 16 * SS
        wy = rim_y + 11 * SS
        d.arc([wx, wy - 3 * SS, wx + 12 * SS, wy + 3 * SS], 200, 340,
              fill=(176, 198, 240, 255), width=max(1, SS))
    fx, fy = cx, rim_y + 24 * SS
    d.ellipse([fx - 9 * SS, fy - 4.5 * SS, fx + 7 * SS, fy + 4.5 * SS], fill=(170, 194, 238, 255))
    d.polygon([(fx + 6 * SS, fy), (fx + 13 * SS, fy - 5 * SS), (fx + 13 * SS, fy + 5 * SS)],
              fill=(170, 194, 238, 255))
    d.ellipse([fx - 5 * SS, fy - 2 * SS, fx - 3 * SS, fy], fill=INK)

    # chopsticks resting across the rim
    for k in (0, 1):
        x0, y0 = cx - 43 * SS, rim_y - (4 + k * 5) * SS
        x1, y1 = cx + 39 * SS, rim_y - (20 + k * 5) * SS
        d.line([(x0, y0), (x1, y1)], fill=WOOD, width=max(1, int(1.8 * SS)))
        d.ellipse([x1 - 2 * SS, y1 - 2 * SS, x1 + 2 * SS, y1 + 2 * SS], fill=WOOD_DARK)

    # steam
    for i in range(2):
        sx = cx - bw * 0.16 + i * bw * 0.30
        sy = rim_y - 20 * SS
        pts = []
        for k in range(10):
            u = k / 9
            pts.append((sx + math.sin(u * math.tau + t * math.tau + i) * 3.5 * SS,
                        sy - u * 21 * SS))
        d.line(pts, fill=(181, 198, 232, 120), width=max(1, int(1.2 * SS)), joint="curve")

    # a few grains drifting from the bowl toward the mouth
    for i in range(4):
        u = (t + i * 0.27) % 1.0
        gx = cx + 8 * SS + math.sin(u * math.pi) * 14 * SS
        gy = rim_y - 10 * SS - u * 48 * SS
        a = int(235 * (1 - u) ** 1.4)
        if a <= 4:
            continue
        r = 1.9 * SS
        d.ellipse([gx - r, gy - r * 0.6, gx + r, gy + r * 0.6],
                  fill=(255, 255, 255, a), outline=(214, 214, 206, a), width=1)

    return layer.resize(SIZE, Image.LANCZOS)


def build_rice() -> None:
    src = sorted((CLIPS / "yawn").glob("*.webp"))
    if not src:
        raise SystemExit("缺少 yawn 源帧")
    out = CLIPS / "rice"
    out.mkdir(parents=True, exist_ok=True)
    names = []
    for i, p in enumerate(src):
        im = Image.open(p).convert("RGBA")
        x0, y0, x1, y1 = alpha_bbox(im)
        cx = (x0 + x1) / 2
        rim_y = y1 - 50
        rice = bowl_layer(cx, rim_y, i, len(src))
        im.alpha_composite(rice)
        dest = out / f"rice_{i:03d}.webp"
        im.save(dest, "WEBP", quality=52, method=6, alpha_quality=90)
        names.append(f"rice/{dest.name}")
    update_manifest("rice", names, fps=12, loop=False)


def build_sing() -> None:
    src = sorted((CLIPS / "yawn").glob("*.webp"))[23:35]  # open-mouth segment
    if len(src) < 8:
        raise SystemExit("缺少 yawn 源帧")
    seq = src + list(reversed(src[1:-1]))
    out = CLIPS / "sing"
    out.mkdir(parents=True, exist_ok=True)
    names = []
    for i, p in enumerate(seq):
        im = Image.open(p).convert("RGBA")
        # subtle baked sway so a still open mouth reads as singing, not yawning
        dx = round(1.6 * math.sin(i / max(1, len(seq)) * math.tau))
        dy = round(1.0 * math.sin(i / max(1, len(seq)) * math.tau * 2))
        canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        canvas.alpha_composite(im, (dx, dy))
        dest = out / f"sing_{i:03d}.webp"
        canvas.save(dest, "WEBP", quality=52, method=6, alpha_quality=90)
        names.append(f"sing/{dest.name}")
    update_manifest("sing", names, fps=12, loop=True)


def update_manifest(name: str, names: list[str], fps: int, loop: bool) -> None:
    path = CLIPS / "manifest.json"
    man = json.loads(path.read_text(encoding="utf-8"))
    man["clips"][name] = {
        "fps": fps,
        "loop": loop,
        "frameCount": len(names),
        "durationMs": round(len(names) / fps * 1000),
        "frames": names,
    }
    # keep idle first and append derived clips in a stable order
    order = [k for k in man["clips"] if k not in ("rice", "sing")] + [k for k in ("rice", "sing") if k in man["clips"]]
    man["clips"] = {k: man["clips"][k] for k in order}
    path.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: {len(names)} frames, {len(names)/fps:.2f}s")


def main() -> None:
    build_rice()
    build_sing()


if __name__ == "__main__":
    main()
