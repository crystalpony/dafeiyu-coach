#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按每个形象的 manifest 清理冲突副本（iCloud 的 “xxx 2.webp” 等）。"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main(root: str) -> int:
    base = Path(root)
    if not base.exists():
        return 0
    removed = 0
    for d in base.iterdir():
        mp = d / "manifest.json"
        if not mp.exists():
            continue
        try:
            m = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            continue
        keep = {Path(f).as_posix() for c in (m.get("clips") or {}).values()
                for f in c.get("frames") or []}
        if not keep:
            continue
        for p in d.rglob("*.webp"):
            if p.relative_to(d).as_posix() not in keep:
                p.unlink()
                removed += 1
    print(f"pruned {removed} files under {base}")
    return 0


def snapshot(root: str, destination: str) -> int:
    """只复制manifest明确引用的帧；不先拷贝整套iCloud副本再删。"""
    base, target = Path(root), Path(destination)
    if target.exists() and any(target.iterdir()):
        raise ValueError("snapshot destination must be empty")
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for directory in base.iterdir():
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            continue
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw)
        for clip in manifest["clips"].values():
            hashes = clip.get("sha256", [])
            for i, rel in enumerate(clip["frames"]):
                path = Path(rel)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError(f"invalid frame path: {rel}")
                source = directory / path
                data = source.read_bytes()
                if hashes and hashlib.sha256(data).hexdigest() != hashes[i]:
                    raise ValueError(f"frame changed during snapshot: {source}")
                dest = target / directory.name / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                copied += 1
        (target / directory.name / "manifest.json").write_bytes(raw)
    print(f"snapshot {copied} referenced frames into {target}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--snapshot", help="copy referenced frames into a local staging directory")
    args = parser.parse_args()
    sys.exit(snapshot(args.root, args.snapshot) if args.snapshot else main(args.root))
