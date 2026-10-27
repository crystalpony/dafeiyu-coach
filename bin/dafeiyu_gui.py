#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""桌面大肥鱼 · Windows / macOS 桌面窗口版（Tk + Pillow）。

- 透明无边框置顶窗口、拖拽、摸头/戳、右键菜单
- 13 段 WebP 动画 + 120ms 交叉淡化
- 气泡步骤 / 歌词 / 米饭 / 番茄钟 / 指针圈
- 本机 TCP 核心与 CLI/MCP/skills 共用（与 dafeiyu tui 同一 Core/Server）

Windows 为原生窗口（透明色抠图 + Win32 点击穿透）；macOS 原生版仍优先使用 AppKit 版。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import ctypes
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dafeiyu_tui import Core, Server, start_music, HOME, PORT_FILE, call  # noqa: E402

try:
    import tkinter as tk
    from tkinter import font as tkfont
    from PIL import Image, ImageTk, ImageOps, ImageDraw
    GUI_ERR = None
except Exception as exc:  # pragma: no cover
    tk = None
    GUI_ERR = exc

KEY = "#ff00ff"
PET_W, PET_H = 210, 175
BUB_W = 342
IS_WIN = sys.platform == "win32"
FONT = "Microsoft YaHei" if IS_WIN else "PingFang SC"
ROOT = Path(__file__).resolve().parent.parent
GUI_CFG = HOME / "gui.json"


def find_assets() -> Path | None:
    for p in (HOME / "clips", ROOT / "Runtime" / "clips", Path(sys.executable).resolve().parent / "clips"):
        if (p / "manifest.json").exists():
            return p
    return None


def wrap_text(text: str, max_chars: int = 24) -> list[str]:
    out = []
    for raw in (text or "").splitlines():
        if not raw:
            out.append("")
            continue
        out.extend(textwrap.wrap(raw, width=max_chars, break_long_words=True) or [""])
    return out or [""]


def rounded(canvas: tk.Canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def set_transparent(win) -> None:
    if IS_WIN:
        try:
            win.wm_attributes("-transparentcolor", KEY)
        except Exception:
            pass


def click_through(win) -> None:
    if not IS_WIN:
        return
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetAncestor(win.winfo_id(), 2)
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
    except Exception:
        pass


class Animator:
    def __init__(self, assets: Path):
        self.manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
        self.assets = assets
        self.cache: dict[str, Image.Image] = {}
        self.current = "idle"
        self.frames: list[str] = []
        self.fps = 12.0
        self.loop = True
        self.idx = 0
        self.acc = 0.0
        self.last = time.monotonic()
        self.prev: Image.Image | None = None
        self.blend = 1.0
        self.transition = 0.16
        self.finished = False
        self.set_clip("idle", force=True)

    def resolve(self, name: str) -> str:
        return {"talk": "idle", "point": "working", "celebrate": "success", "dance": "success",
                "cheer": "success", "greet": "pat", "wave": "pat", "happy": "pat",
                "snack": "eat", "rice": "eat", "sleepy": "yawn"}.get(name, name)

    def _load(self, rel: str) -> Image.Image | None:
        if rel in self.cache:
            return self.cache[rel]
        try:
            im = Image.open(self.assets / rel).convert("RGBA")
        except Exception:
            return None
        im = ImageOps.contain(im, (PET_W - 12, PET_H - 12), Image.LANCZOS)
        canvas = Image.new("RGBA", (PET_W, PET_H), (0, 0, 0, 0))
        canvas.alpha_composite(im, ((PET_W - im.width) // 2, (PET_H - im.height) // 2))
        # Tk 在 Windows 上用 color key 抠图，半透明边缘会和洋红键色混合成描边；
        # 这里用二值 alpha 去掉洋红晕，边缘略硬但干净。
        alpha = canvas.getchannel("A").point(lambda a: 255 if a >= 96 else 0)
        canvas.putalpha(alpha)
        if len(self.cache) > 30:
            self.cache.clear()
        self.cache[rel] = canvas
        return canvas

    def set_clip(self, name: str, force: bool = False) -> None:
        key = self.resolve(name or "idle")
        clips = self.manifest.get("clips", {})
        if key not in clips:
            key = "idle"
        if key == self.current and not force:
            return
        old = self.image()
        c = clips[key]
        self.current = key
        self.frames = c.get("frames") or []
        self.fps = float(c.get("fps") or 12)
        self.loop = bool(c.get("loop", True))
        self.idx = 0
        self.acc = 0
        self.finished = False
        self.prev = old if not force else None
        self.blend = 0.0 if self.prev is not None else 1.0
        self.transition = 0.16
        for f in self.frames[:2]:
            self._load(f)

    def image(self) -> Image.Image | None:
        if not self.frames:
            return None
        cur = self._load(self.frames[min(self.idx, len(self.frames) - 1)])
        if cur is None:
            return None
        if self.prev is not None and self.blend < 1:
            return Image.blend(self.prev, cur, max(0.0, min(1.0, self.blend)))
        return cur

    def tick(self) -> Image.Image | None:
        now = time.monotonic()
        dt = min(0.2, max(0, now - self.last))
        self.last = now
        if self.blend < 1:
            self.blend = min(1, self.blend + dt / max(0.02, self.transition))
            if self.blend >= 1:
                self.prev = None
        if not self.frames:
            return None
        if not self.finished:
            self.acc += dt
            step = 1.0 / max(1, self.fps)
            if self.acc >= step:
                n = min(4, int(self.acc / step))
                self.acc -= n * step
                if self.loop:
                    self.idx = (self.idx + n) % len(self.frames)
                else:
                    self.idx = min(len(self.frames) - 1, self.idx + n)
                    if self.idx >= len(self.frames) - 1:
                        self.finished = True
        elif not self.loop and now - (self.last or now) > 0:
            pass
        return self.image()


class GuiApp:
    def __init__(self, assets: Path, no_music: bool = False, smoke: bool = False):
        self.assets = assets
        self.anim = Animator(assets)
        self.core = Core()
        self.server = Server(self.core)
        self.server.start()
        if not no_music:
            start_music()
        self.is_smoke = smoke
        self.last_clip = None
        self.last_sig = None
        self.user_hidden = False
        self.hidden_sig = None
        self.pet_hidden = False
        self.dragging = False
        self.drag_start = (0, 0, 0, 0)
        self.notes: list[int] = []
        self.hearts: list[int] = []
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=KEY if IS_WIN else "#f6f2ea")
        set_transparent(self.root)
        self.x, self.y = self.load_pos()
        self.root.geometry(f"{PET_W}x{PET_H}+{self.x}+{self.y}")
        self.pet_canvas = tk.Canvas(self.root, width=PET_W, height=PET_H,
                                    bg=KEY if IS_WIN else "#f6f2ea", highlightthickness=0)
        self.pet_canvas.pack()
        self.pet_item = self.pet_canvas.create_image(PET_W // 2, PET_H // 2, anchor="center")
        self.pet_canvas.bind("<ButtonPress-1>", self.on_press)
        self.pet_canvas.bind("<B1-Motion>", self.on_drag)
        self.pet_canvas.bind("<ButtonRelease-1>", self.on_release)
        self.pet_canvas.bind("<Double-Button-1>", lambda e: self.feed())
        self.pet_canvas.bind("<Button-3>", self.menu)
        self.bubble = tk.Toplevel(self.root)
        self.bubble.overrideredirect(True)
        self.bubble.attributes("-topmost", True)
        self.bubble.configure(bg=KEY if IS_WIN else "#f6f2ea")
        set_transparent(self.bubble)
        self.bub_canvas = tk.Canvas(self.bubble, width=BUB_W, height=110,
                                    bg=KEY if IS_WIN else "#f6f2ea", highlightthickness=0)
        self.bub_canvas.pack()
        self.bub_canvas.tag_bind("close", "<Button-1>", lambda e: self.hide_bubble())
        self.bubble.withdraw()
        self.pointer = tk.Toplevel(self.root)
        self.pointer.overrideredirect(True)
        self.pointer.attributes("-topmost", True)
        self.pointer.configure(bg=KEY if IS_WIN else "#f6f2ea")
        set_transparent(self.pointer)
        self.pointer.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        self.pointer_canvas = tk.Canvas(self.pointer, width=self.root.winfo_screenwidth(),
                                        height=self.root.winfo_screenheight(),
                                        bg=KEY if IS_WIN else "#f6f2ea", highlightthickness=0)
        self.pointer_canvas.pack()
        self.pointer.withdraw()
        click_through(self.pointer)
        self.phase = 0.0
        self.tick()

    def load_pos(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        default = (40, max(40, sh - PET_H - 90))
        try:
            d = json.loads(GUI_CFG.read_text(encoding="utf-8"))
            return int(d.get("x", default[0])), int(d.get("y", default[1]))
        except Exception:
            return default

    def save_pos(self):
        try:
            GUI_CFG.write_text(json.dumps({"x": self.x, "y": self.y}), encoding="utf-8")
        except Exception:
            pass

    def state(self):
        return self.core.snapshot()

    def on_press(self, e):
        self.dragging = True
        self.drag_start = (e.x_root, e.y_root, self.x, self.y)
        self.moved = False

    def on_drag(self, e):
        if not self.dragging:
            return
        dx = e.x_root - self.drag_start[0]
        dy = e.y_root - self.drag_start[1]
        if abs(dx) > 3 or abs(dy) > 3:
            self.moved = True
        self.x = self.drag_start[2] + dx
        self.y = self.drag_start[3] + dy
        self.x = max(0, min(self.x, self.root.winfo_screenwidth() - PET_W))
        self.y = max(0, min(self.y, self.root.winfo_screenheight() - PET_H))
        self.root.geometry(f"{PET_W}x{PET_H}+{self.x}+{self.y}")
        if self.moved:
            self.anim.set_clip("drag", force=True)
        self.place_bubble()

    def on_release(self, e):
        if not self.dragging:
            return
        self.dragging = False
        self.save_pos()
        if getattr(self, "moved", False):
            self.core.handle({"cmd": "anim", "clip": "drop"})
            self.anim.set_clip("drop", force=True)
            self.root.after(600, lambda: self.core.handle({"cmd": "anim", "clip": "idle"}))
            return
        y = e.y
        if y < PET_H * 0.42:
            self.core.handle({"cmd": "say", "text": "嘿嘿，摸头最舒服了。", "anim": "pat", "tone": "coach"})
            self.heart()
        elif e.x > PET_W * 0.70 and y > PET_H * 0.52:
            self.core.handle({"cmd": "say", "text": "尾巴不能乱碰啦～", "anim": "tail", "tone": "coach"})
        else:
            self.core.handle({"cmd": "say", "text": "呀！被戳到了。要帮忙就叫我一声。", "anim": "poke", "tone": "coach"})
        if self.user_hidden:
            self.user_hidden = False

    def feed(self):
        self.core.handle({"cmd": "feed"})

    def focus(self):
        self.core.handle({"cmd": "focus", "minutes": 25})

    def hide_bubble(self):
        self.user_hidden = True
        self.hidden_sig = self.last_sig
        self.bubble.withdraw()

    def menu(self, e):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="添一碗米饭", command=self.feed)
        m.add_command(label="专注 25 分钟", command=self.focus)
        m.add_command(label="取消专注", command=lambda: self.core.handle({"cmd": "focus", "cancel": True}))
        m.add_separator()
        m.add_command(label="停止唱歌", command=lambda: self.core.handle({"cmd": "music_stop"}))
        m.add_command(label="显示/收起气泡", command=self.toggle_bubble)
        m.add_command(label="隐藏桌宠", command=self.hide_pet)
        m.add_command(label="退出", command=self.quit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def toggle_bubble(self):
        self.user_hidden = not self.user_hidden
        if not self.user_hidden:
            self.hidden_sig = None
        self.update_bubble(self.state())

    def hide_pet(self):
        self.pet_hidden = True
        self.root.withdraw()
        self.bubble.withdraw()
        self.root.after(3000, self.show_pet)

    def show_pet(self):
        self.pet_hidden = False
        self.root.deiconify()

    def heart(self):
        x = PET_W * 0.5
        for i in range(4):
            item = self.pet_canvas.create_text(x + (i - 2) * 12, 45, text="♥",
                                               fill="#ff6b8b", font=(FONT, 13, "bold"))
            self.hearts.append(item)

    def place_bubble(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = BUB_W
        h = int(getattr(self, "bub_h", 110))
        x = self.x + PET_W + 8
        tail_right = False
        if x + w > sw - 6:
            x = self.x - w - 8
            tail_right = True
        x = max(6, min(x, sw - w - 6))
        y = max(6, min(self.y - 6, sh - h - 6))
        self.bubble.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        self.bub_tail_right = tail_right

    def update_bubble(self, s):
        title = s.get("bubble_title", "")
        badge = s.get("badge", "")
        text = s.get("bubble", "")
        nxt = s.get("next", "") if s.get("singing") else ""
        sig = (title, badge, text, nxt, s.get("tone"))
        if sig != self.last_sig:
            self.last_sig = sig
            if self.user_hidden and self.hidden_sig != sig:
                self.user_hidden = False
            self.render_bubble(title, badge, text, nxt, s.get("tone", "coach"))
        visible = bool(text or title) and s.get("bubbleVisible", True) and not self.user_hidden and not self.pet_hidden
        if visible:
            self.place_bubble()
            self.bubble.deiconify()
            self.bubble.lift()
        else:
            self.bubble.withdraw()

    def render_bubble(self, title, badge, text, nxt, tone="coach"):
        c = self.bub_canvas
        c.delete("all")
        lines = wrap_text(text, 23)
        tlines = wrap_text(title, 22) if title else []
        nlines = wrap_text(nxt, 25) if nxt else []
        h = 16 + (18 if badge else 0) + len(tlines) * 17 + len(lines) * 19 + len(nlines) * 15 + 18
        h = max(84, min(230, h))
        self.bub_h = h
        c.configure(height=h, width=BUB_W)
        accent = {"success": "#34ad75", "error": "#e04750", "music": "#8b61e6",
                  "thinking": "#597fd8"}.get(tone, "#f7873d")
        # tone from state not passed; infer music badge
        if badge.startswith("♪"):
            accent = "#8b61e6"
        tail = 10
        bx1, by1, bx2, by2 = (0 if getattr(self, "bub_tail_right", False) else tail), 4, BUB_W - (tail if getattr(self, "bub_tail_right", False) else 0), h - 4
        rounded(c, bx1, by1, bx2, by2, 14, fill="#fffdfa", outline=accent, width=2)
        # tail
        ty = h - 48
        if getattr(self, "bub_tail_right", False):
            c.create_polygon(bx2 - 1, ty, bx2 + tail, ty + 11, bx2 - 1, ty + 22, fill="#fffdfa", outline=accent, width=2)
        else:
            c.create_polygon(bx1 + 1, ty, bx1 - tail, ty + 11, bx1 + 1, ty + 22, fill="#fffdfa", outline=accent, width=2)
        x0, y = bx1 + 14, 13
        if badge:
            c.create_text(x0, y, text=badge, anchor="nw", fill=accent,
                          font=(FONT, 9, "bold"), width=BUB_W - 50)
            y += 17
        for ln in tlines:
            c.create_text(x0, y, text=ln, anchor="nw", fill="#20283a", font=(FONT, 11, "bold"), width=BUB_W - 50)
            y += 17
        for ln in lines:
            c.create_text(x0, y, text=ln, anchor="nw", fill="#20283a", font=(FONT, 11), width=BUB_W - 50)
            y += 19
        for ln in nlines:
            c.create_text(x0, y, text=ln, anchor="nw", fill="#8a8f9c", font=(FONT, 9), width=BUB_W - 50)
            y += 15
        c.create_oval(BUB_W - 27, 9, BUB_W - 11, 25, fill="#8a8f9c", outline="#fffdfa", tags="close")
        c.create_text(BUB_W - 19, 17, text="×", fill="#ffffff", font=(FONT, 9, "bold"), tags="close")

    def update_pointer(self, s):
        pt = s.get("point")
        if not pt:
            self.pointer.withdraw()
            return
        px, py = pt[0], pt[1]
        label = pt[2] if len(pt) > 2 else ""
        c = self.pointer_canvas
        c.delete("all")
        pulse = 26 + 5 * math.sin(self.phase)
        x, y = float(px), float(py)
        accent = "#f7873d"
        # dashed line from pet to target
        c.create_line(self.x + PET_W / 2, self.y + PET_H / 2, x, y, fill=accent,
                      dash=(4, 5), width=1)
        c.create_oval(x - pulse - 14, y - pulse - 14, x + pulse + 14, y + pulse + 14,
                      outline="", fill="")
        c.create_oval(x - pulse - 3, y - pulse - 3, x + pulse + 3, y + pulse + 3,
                      outline="#ffffff", width=6)
        c.create_oval(x - pulse, y - pulse, x + pulse, y + pulse, outline=accent, width=3)
        c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=accent, outline="")
        ay = y - pulse - 16
        c.create_polygon(x, ay + 14, x - 9, ay, x + 9, ay, fill=accent, outline="#ffffff", width=3)
        if label:
            tw = max(50, min(280, len(label) * 14 + 20))
            lx = max(8, min(x - tw / 2, self.root.winfo_screenwidth() - tw - 8))
            ly = y + pulse + 18
            if ly + 30 > self.root.winfo_screenheight() - 8:
                ly = y - pulse - 48
            rounded(c, lx, ly, lx + tw, ly + 28, 14, fill="#fffdfa", outline=accent, width=1)
            c.create_text(lx + tw / 2, ly + 14, text=label, fill="#20283a", font=(FONT, 10, "bold"))
        self.pointer.deiconify()
        self.pointer.lift()
        self.pointer.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")

    def update_notes(self, s):
        if s.get("singing") and self.phase % 0.6 < 0.06:
            n = self.pet_canvas.create_text(PET_W * 0.5 + (hash(time.time()) % 50 - 25), 50,
                                            text="♪", fill="#9a6bf0", font=(FONT, 15, "bold"))
            self.notes.append(n)
        for n in list(self.notes):
            try:
                self.pet_canvas.move(n, 0, -1.2)
                self.pet_canvas.itemconfigure(n, fill="#9a6bf0")
            except Exception:
                self.notes.remove(n)

    def tick(self):
        if self.core.stop:
            self.quit()
            return
        s = self.state()
        clip = s.get("clip") or "idle"
        if clip != self.last_clip:
            self.last_clip = clip
            self.anim.set_clip(clip)
        img = self.anim.tick()
        if img is not None:
            self.photo = ImageTk.PhotoImage(img)
            self.pet_canvas.itemconfigure(self.pet_item, image=self.photo)
        self.update_bubble(s)
        self.update_pointer(s)
        self.update_notes(s)
        self.phase += 0.06
        self.root.after(70, self.tick)

    def quit(self):
        try:
            self.save_pos()
        except Exception:
            pass
        try:
            self.server.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def smoke(self):
        # CI 桌面有日志窗口；冒烟时铺一层干净的浅色舞台，只保留宠物/气泡/指针。
        try:
            self.stage = tk.Toplevel(self.root)
            self.stage.overrideredirect(True)
            self.stage.configure(bg="#f6f2ea")
            self.stage.attributes("-topmost", True)
            self.stage.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
            self.stage.lower()
            self.root.lift()
        except Exception:
            self.stage = None
        self.core.handle({"cmd": "feed"})
        self.core.handle({"cmd": "say", "title": "桌面大肥鱼", "text": "Windows 桌面版冒烟测试。",
                          "anim": "pat", "tone": "coach"})
        self.core.handle({"cmd": "point", "x": 720, "y": 250, "label": "Windows 指针"})
        for _ in range(12):
            if getattr(self, "stage", None) is not None:
                self.stage.lower()
                self.root.lift()
                self.bubble.lift()
                self.pointer.lift()
            self.root.update()
            self.tick_smoke()
            time.sleep(0.05)
        out = Path("gui-smoke.png")
        try:
            from PIL import ImageGrab
            ImageGrab.grab().save(out)
        except Exception as exc:
            print(f"screenshot failed: {exc}")
        print(json.dumps({"ok": True, "smoke": True, "w": PET_W, "h": PET_H,
                          "core": self.core.snapshot().get("clip")}, ensure_ascii=False))
        self.quit()

    def tick_smoke(self):
        s = self.state()
        clip = s.get("clip") or "idle"
        if clip != self.last_clip:
            self.last_clip = clip
            self.anim.set_clip(clip)
        img = self.anim.tick()
        if img is not None:
            self.photo = ImageTk.PhotoImage(img)
            self.pet_canvas.itemconfigure(self.pet_item, image=self.photo)
        self.update_bubble(s)
        self.update_pointer(s)
        self.update_notes(s)
        self.phase += 0.06


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dafeiyu gui", description="桌面大肥鱼 · 桌面窗口版")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="创建窗口、渲染几帧、截图后退出（CI）")
    ap.add_argument("--check", action="store_true", help="只检查依赖/素材")
    args = ap.parse_args(argv)
    if GUI_ERR is not None:
        print(f"缺少 GUI 依赖：{GUI_ERR}\nWindows: python -m pip install --user Pillow")
        return 2
    assets = find_assets()
    if not assets:
        print("找不到动画素材 clips/manifest.json")
        return 2
    if not IS_WIN:
        print("提示：这是跨平台窗口版；macOS 原生桌宠请用已安装的 dafeiyu-daemon。")
    if args.check:
        print(json.dumps({"ok": True, "platform": sys.platform, "assets": str(assets),
                          "tk": tk.TkVersion, "pillow": Image.__version__}, ensure_ascii=False))
        return 0
    app = GuiApp(assets, no_music=args.no_music, smoke=args.smoke)
    if args.smoke:
        app.smoke()
        return 0
    app.root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
