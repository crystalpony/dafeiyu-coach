#!/usr/bin/env python3
"""Build the compact animation library for Desktop 大肥鱼 Coach.

Source frames come from the MIT-licensed `dsh-pet` character set as repacked by
`dsh-dafeiyu` (see Runtime/clips/ASSET-LICENSE.txt).  We intentionally keep only
the clips the coach uses, drop the source frame rate to 12 fps, and re-encode at
300x250 so the whole runtime stays in the single-digit megabyte range.

Usage:
    python3 scripts/build_assets.py [--source DIR] [--probe]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - build-machine guard
    sys.exit("需要 Pillow（python3 -m pip install --user Pillow）")

DEFAULT_SOURCE = Path(
    os.path.expanduser("~/.dsh/profiles/desktop/node_modules/dsh-dafeiyu/assets/pet")
)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Runtime" / "clips"
SIZE = (300, 250)
QUALITY = 45

# name in our manifest -> (source clip, keep every Nth frame, max frames, loop)
CLIPS = {
    "idle": ("idle", 2, 121, True),
    "thinking": ("thinking", 2, 121, True),
    "working": ("working", 2, 121, True),
    "success": ("success", 2, 60, False),
    "error": ("error", 2, 36, False),
    "pat": ("head_pat", 2, 48, False),
    "poke": ("poke", 2, 36, False),
    "tail": ("tail", 2, 36, False),
    "eat": ("eat_token", 2, 48, False),
    "stretch": ("idle_stretch", 2, 48, False),
    "yawn": ("idle_yawn", 2, 48, False),
    "drag": ("dragging", 2, 60, True),
    "drop": ("dragging_release", 1, 37, False),
}


def build(source: Path, probe: bool = False) -> None:
    manifest_path = source.parent / "pet-manifest.json"
    upstream = {}
    if manifest_path.exists():
        upstream = json.loads(manifest_path.read_text(encoding="utf-8"))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    manifest = {
        "formatVersion": 1,
        "character": upstream.get("characterId", "dafeiyu"),
        "displayName": "大肥鱼",
        "frameRateNote": "source 24fps, repacked to 12fps",
        "frameSize": list(SIZE),
        "license": "MIT — character assets from PC2005-cloud/dsh-pet",
        "source": {
            "repository": "https://github.com/PC2005-cloud/dsh-pet",
            "repack": "https://github.com/QCYTSN/dsh-dafeiyu",
            "commit": (upstream.get("assetSource") or {}).get("commit", ""),
        },
        "clips": {},
    }
    total_bytes = 0
    total_frames = 0
    for name, (src, step, limit, loop) in CLIPS.items():
        files = sorted((source / src).glob("*.webp"))
        if not files:
            raise SystemExit(f"缺少素材: {source / src}")
        picked = files[::step][:limit]
        if probe:
            picked = picked[:6]
        outdir = OUT / name
        outdir.mkdir(parents=True, exist_ok=True)
        names = []
        for i, f in enumerate(picked):
            im = Image.open(f).convert("RGBA").resize(SIZE, Image.LANCZOS)
            dest = outdir / f"{name}_{i:03d}.webp"
            im.save(dest, "WEBP", quality=QUALITY, method=6, alpha_quality=80)
            names.append(f"{name}/{dest.name}")
            total_bytes += dest.stat().st_size
            total_frames += 1
        fps = 24 if step == 1 else 12
        manifest["clips"][name] = {
            "fps": fps,
            "loop": loop,
            "frameCount": len(names),
            "durationMs": round(len(names) / fps * 1000),
            "frames": names,
        }
        print(f"  {name:9s} {len(names):3d} frames  {len(names)/fps:5.1f}s  -> {outdir}")

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    license_src = source.parent / "dsh-pet-LICENSE.txt"
    if license_src.exists():
        shutil.copy2(license_src, OUT / "ASSET-LICENSE.txt")

    # small still for fallback / docs
    first = Image.open(source / "idle" / "idle_001.webp").convert("RGBA")
    first = first.resize((180, 150), Image.LANCZOS)
    first.save(ROOT / "Runtime" / "mascot.png")

    print(
        f"\n{total_frames} frames, {total_bytes/1048576:.2f} MB "
        f"({total_bytes/max(total_frames,1)/1024:.1f} KB/frame) -> {OUT}"
    )

    # 米饭/唱歌是本地派生剪辑，跟着素材重建一起生成（不会回退成 eat）
    from derive_clips import build_rice, build_sing
    build_rice()
    build_sing()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.environ.get("DAFEIYU_ASSET_SOURCE", str(DEFAULT_SOURCE)))
    ap.add_argument("--probe", action="store_true", help="每个剪辑只导 6 帧，用于验尺寸")
    args = ap.parse_args()
    build(Path(args.source).expanduser(), args.probe)


if __name__ == "__main__":
    main()
