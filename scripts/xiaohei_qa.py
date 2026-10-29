#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小黑多视角/骨骼与新增动作 QA。

- 输出 audit/screenshots/10-xiaohei-rig.png（身体/头部骨骼叠加，无附加前臂）
- 输出 audit/screenshots/11-xiaohei-actions.png（新增动作总览）
- 逐帧检查新增动作的 alpha 边界，防止耳尖/前肢被裁
- 检查唱歌循环接缝，并守卫生成器不重新引入后肢/侧伸前爪模型
"""
from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "audit" / "screenshots"

spec = importlib.util.spec_from_file_location("xh_gen", ROOT / "scripts" / "build_xiaohei.py")
gen = importlib.util.module_from_spec(spec)
sys.modules["xh_gen"] = gen
spec.loader.exec_module(gen)

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
try:
    font = ImageFont.truetype(FONT_PATH, 22)
    small = ImageFont.truetype(FONT_PATH, 14)
except Exception:
    font = ImageFont.load_default()
    small = font


def frame(name: str, t: float, rig: bool = False) -> Image.Image:
    return gen.render(gen.CLIPS[name][2](t), rig=rig)


def card(name: str, t: float, label: str, rig: bool = False) -> Image.Image:
    im = frame(name, t, rig=rig)
    bg = Image.new("RGBA", (300, 250), (248, 246, 240, 255))
    bg.alpha_composite(im)
    card = Image.new("RGB", (600, 500), (255, 253, 248))
    card.paste(bg.convert("RGB").resize((600, 500), Image.LANCZOS), (0, 0))
    d = ImageDraw.Draw(card)
    d.rectangle([0, 0, 599, 499], outline=(231, 224, 212), width=2)
    d.text((22, 452), label, font=font, fill=(60, 42, 28))
    d.text((22, 478), f"{name} · {'ground reference (not a skeleton)' if rig else 'render'}", font=small, fill=(150, 128, 108))
    return card


def grid(cards, cols: int, gap: int = 20, pad: int = 20) -> Image.Image:
    rows = (len(cards) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 600 + (cols - 1) * gap + 2 * pad,
                              rows * 500 + (rows - 1) * gap + 2 * pad), (243, 240, 233))
    for i, c in enumerate(cards):
        x = pad + (i % cols) * (600 + gap)
        y = pad + (i // cols) * (500 + gap)
        sheet.paste(c, (x, y))
    return sheet


def save(sheet: Image.Image, name: str) -> Path:
    SHOTS.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.gettempdir()) / ("xh-qa-" + name)
    sheet.save(tmp, "PNG")
    out = SHOTS / name
    for attempt in range(4):
        try:
            shutil.copyfile(tmp, out)
            break
        except OSError:
            if attempt == 3:
                raise
    try:
        tmp.unlink()
    except OSError:
        pass
    return out


def deep_checks():
    """补充实际产物检查；不替换旧守卫。损坏帧、过期生成器、假循环都能失败。"""
    errors = []
    count = 0
    root = ROOT / "Runtime/characters/xiaohei"
    manifest = json.loads((root / "manifest.json").read_text())
    source = manifest.get("source", {})
    if source.get("poses") != gen.source_provenance():
        errors.append("pose-provenance-mismatch")
    if source.get("generatorSha256") != hashlib.sha256((ROOT / "scripts/build_xiaohei.py").read_bytes()).hexdigest():
        errors.append("generator-provenance-mismatch")
    if set(manifest["clips"]) != set(gen.CLIPS):
        errors.append("clip-set-mismatch")
    rerendered = 0
    for name, (frames, loop, fn) in gen.CLIPS.items():
        c = manifest["clips"].get(name, {})
        if (c.get("frameCount"), c.get("fps"), c.get("loop")) != (frames, gen.FPS, loop):
            errors.append((name, "timing-mismatch"))
        expected_frames = [f"{name}/{name}_{i:03d}.webp" for i in range(frames)]
        if c.get("frames") != expected_frames:
            errors.append((name, "frame-list-order-or-count"))
        hashes = c.get("sha256", [])
        if len(hashes) != frames:
            errors.append((name, "missing-frame-hashes"))
        for i, rel in enumerate(c.get("frames", [])):
            path = root / rel
            if not path.is_file():
                errors.append((name, i, "missing-frame")); continue
            data = path.read_bytes()
            if i < len(hashes) and hashlib.sha256(data).hexdigest() != hashes[i]:
                errors.append((name, i, "hash-mismatch"))
            with Image.open(io.BytesIO(data)) as image:
                image = image.convert("RGBA")
                box = image.getchannel("A").getbbox()
                if image.size != (300, 250) or not box or min(box[0], box[1]) < 2 or box[2] > 298 or box[3] > 248:
                    errors.append((name, i, "full-frame-boundary"))
            count += 1
            if i in (0, frames // 2, frames - 1):
                buf = io.BytesIO()
                gen.render(fn(i / gen.FPS)).save(buf, "WEBP", quality=92, method=6)
                if data != buf.getvalue():
                    errors.append((name, i, "render-file-mismatch"))
                rerendered += 1
        if loop:
            # 真正一个完整周期回到原值，而不只比较相邻帧的宽松阈值。
            if gen.render(fn(0)).tobytes() != gen.render(fn(frames / gen.FPS)).tobytes():
                errors.append((name, "non-integer-period"))
    if count != 1992:
        errors.append(("frame-count", count))
    if rerendered != 75:
        errors.append(("rerender-sample-count", rerendered))
    suites = {}
    for name in ("test_xiaohei_geometry.py", "test_xiaohei_player.py"):
        result = subprocess.run([sys.executable, str(ROOT / "tests" / name)], capture_output=True, text=True, timeout=90)
        suites[name] = result.returncode == 0
        if result.returncode:
            errors.append((name, result.stderr[-900:]))
    return {"decoded": count, "rerendered": rerendered, "suites": suites, "errors": errors}


def main() -> int:
    rig_states = [("success", 0.8, "完成庆祝"), ("stretch", 1.4, "伸懒腰"),
                  ("wash", 1.2, "眯眼摇头"), ("pounce", 0.8, "蓄势一下"),
                  ("pat", 0.8, "摸头"), ("fluff", 0.6, "受惊停顿")]
    action_states = [("wash", 1.2, "眯眼摇头"), ("roll", 0.6, "躺着晃晃"),
                     ("pounce", 0.8, "蓄势一下"), ("fluff", 0.6, "受惊停顿"),
                     ("heixiu", 1.8, "和黑咻玩"), ("sleep", 2.0, "睡觉"),
                     ("meow", 0.5, "喵"), ("idle", 0.2, "待机"),
                     ("sing", 1.0, "律动唱歌"), ("sing_mic", 1.0, "立麦伴唱"),
                     ("sing_hat", 1.0, "街舞帽"), ("sing_tail", 1.0, "坐直摇尾")]

    rig_cards = [card(n, t, label, rig=True) for n, t, label in rig_states]
    action_cards = [card(n, t, label) for n, t, label in action_states]
    rig_path = save(grid(rig_cards, 3), "10-xiaohei-rig.png")
    actions_path = save(grid(action_cards, 4), "11-xiaohei-actions.png")

    checked = 0
    min_top = 999
    max_right = 0
    bad = []
    new_clips = ["wash", "roll", "pounce", "fluff", "sleep", "meow", "heixiu",
                 "sing", "sing_mic", "sing_hat", "sing_tail"]
    for name in new_clips:
        frames, _, fn = gen.CLIPS[name]
        step = max(1, frames // 10)
        for i in range(0, frames, step):
            im = gen.render(fn(i / gen.FPS))
            bbox = im.getchannel("A").getbbox()
            checked += 1
            if im.size != (300, 250) or not bbox:
                bad.append((name, i, "empty/size"))
                continue
            left, top, right, bottom = bbox
            min_top = min(min_top, top)
            max_right = max(max_right, right)
            if left < 0 or top < 0 or right > 300 or bottom > 250 or top < 2:
                bad.append((name, i, bbox))

    ok = not bad and rig_path.exists() and actions_path.exists()

    # 代际守卫：生成器里不能重新出现后肢/侧伸前爪模型
    src = (ROOT / "scripts" / "build_xiaohei.py").read_text(encoding="utf-8")
    forbidden = ['p.arms = "splay"', 'p.arms == "splay"', "arm_specs", "draw_arms", "cover_front_lines", "hind_specs", "draw_hind", "后肢", "后腿"]
    limbs_clean = {k: k not in src for k in forbidden}
    if not all(limbs_clean.values()):
        bad.append(("build_xiaohei.py", "forbidden-limb-model"))

    # 第二张嘴回归守卫：正面/侧脸都不得再叠加嘴形（嘴在底图里）
    fs = src.find("def draw_front_face")
    fe = src.find("def draw_side_face", fs)
    front_face_src = src[fs:fe] if fs >= 0 and fe > fs else ""
    se = src.find("def render_pose", fe)
    side_face_src = src[fe:se] if fe >= 0 and se > fe else ""
    mouth_clean = ("p.mouth" not in front_face_src and "p.mouth" not in side_face_src)
    if not mouth_clean:
        bad.append(("build_xiaohei.py", "double-mouth-overlay"))

    # 唱歌循环接缝：最后一帧回到第 0 帧的差异不能明显大于相邻帧
    loops = {}
    for name in ("sing", "sing_mic", "sing_hat", "sing_tail", "idle", "tail", "drag", "sleep"):
        frames, _, fn = gen.CLIPS[name]
        a = gen.render(fn(0)).convert("RGB")
        b = gen.render(fn((frames - 1) / gen.FPS)).convert("RGB")
        c = gen.render(fn((frames - 2) / gen.FPS)).convert("RGB")
        seam = sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3
        step = sum(ImageStat.Stat(ImageChops.difference(c, b)).mean) / 3
        loops[name] = {"seam": round(seam, 2), "step": round(step, 2)}
        if seam > max(2.0, step * 2.2):
            bad.append((name, "loop-seam"))

    deep = deep_checks()
    bad.extend(deep["errors"])
    # 旧脚本只在JSON报错、退出码可能仍为0；新增的失败必须传递到CI。
    ok = ok and not bad
    print(json.dumps({
        "ok": ok and not bad,
        "deep": deep,
        "clips": len(gen.CLIPS),
        "checked": checked,
        "min_top": min_top,
        "max_right": max_right,
        "loops": loops,
        "limbs_clean": limbs_clean,
        "mouth_clean": mouth_clean,
        "bad": bad[:5],
        "rig": str(rig_path),
        "actions": str(actions_path),
    }, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
