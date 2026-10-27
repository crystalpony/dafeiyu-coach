#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""桌面大肥鱼 · 跨平台终端轻量版（macOS / Windows / Linux）。

没有 AppKit 也能有一只大肥鱼：ASCII 动画、步骤气泡、歌词、米饭、番茄钟。
macOS 上如果原生版正在运行，则自动作为“显示器”附着；否则自己当核心。
Windows 上通过本机 TCP（随机端口 + token）接收 CLI/MCP/skill 命令。

    dafeiyu tui                 # 打开终端宠物
    dafeiyu tui --once          # 只渲染一帧（验收/CI）
    dafeiyu tui --headless      # 只当核心，不渲染（测试/服务）
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import select
import shutil
import signal
import socket
import sys
import textwrap
import threading
import unicodedata
import time
from pathlib import Path


if os.name == "nt":
    for _stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if _stream is not None:
                _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

VERSION = "1.1.0"
HOME = Path(os.environ.get("DAFEIYU_HOME", str(Path.home() / ".dafeiyu")))
SOCKET = HOME / "coach.sock"
PORT_FILE = HOME / "coach.port"
MUSIC_PID = HOME / "music.pid"

FISH = [
    r"       /\ ",
    r"   ___/  \___",
    r"  <  o    o  >",
    r"   \__/\__/",
    r"      \/",
]
SLEEP_FISH = [
    r"       /\ ",
    r"   ___/  \___",
    r"  <  -    -  >   z",
    r"   \__/\__/      z",
    r"      \/",
]

COL = {
    "dim": "\033[2m", "reset": "\033[0m", "cyan": "\033[36m",
    "magenta": "\033[35m", "green": "\033[32m", "yellow": "\033[33m",
    "bold": "\033[1m", "gray": "\033[90m",
}


def enable_vt() -> None:
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
            k.SetConsoleOutputCP(65001)
            k.SetConsoleCP(65001)
        except Exception:
            pass


def read_port() -> dict | None:
    try:
        return json.loads(PORT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def call(payload: dict, timeout: float = 2.0) -> dict | None:
    """优先 UNIX（原生版），否则本机 TCP（终端版）。"""
    if SOCKET.exists() and os.name != "nt":
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect(str(SOCKET))
            s.sendall((json.dumps(payload) + "\n").encode())
            data = b""
            while not data.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
            s.close()
            return json.loads(data.decode()) if data.strip() else None
        except Exception:
            pass
    info = read_port()
    if not info:
        return None
    try:
        s = socket.create_connection(("127.0.0.1", int(info["port"])), timeout=timeout)
        payload = dict(payload)
        payload["token"] = info.get("token", "")
        s.sendall((json.dumps(payload) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
        s.close()
        return json.loads(data.decode()) if data.strip() else None
    except Exception:
        return None


def dwidth(text: str) -> int:
    n = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


def first_line(text: str, width: int) -> list[str]:
    # textwrap 按字符数；这里按显示宽度重新折行
    out, cur, curw = [], "", 0
    for ch in text or "":
        if ch == "\n":
            out.append(cur); cur, curw = "", 0; continue
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if curw + cw > max(20, width):
            out.append(cur); cur, curw = "", 0
        cur += ch; curw += cw
    out.append(cur)
    return out or [""]


class Core:
    """终端版核心：与 Swift 版同样的命令语义，但不依赖 AppKit。"""

    def __init__(self):
        self.lock = threading.Lock()
        self.stop = False
        self.title = ""
        self.steps: list[dict] = []
        self.index = 0
        self.done: list[bool] = []
        self.bubble = ""
        self.badge = ""
        self.bubble_title = ""
        self.tone = "coach"
        self.song = ""
        self.artist = ""
        self.lyric = ""
        self.next_lyric = ""
        self.singing = False
        self.music_at = 0.0
        self.rice = 0
        self.focus_until = 0.0
        self.quiet = False
        self.point = None
        self.anim = "idle"
        self._last_anim = "idle"
        self._anim_since = time.time()
        self.feeding_until = 0.0
        self.bubble_until = 0.0
        self.last = time.time()
        self.started = time.time()

    def _snap(self) -> dict:
        now = time.time()
        if self.anim != self._last_anim:
            self._last_anim = self.anim
            self._anim_since = now
        # 一次性动作播完回唱歌/待机，避免 GUI 停在最后一帧
        dur = {"pat": 4.0, "success": 4.8, "error": 3.2, "poke": 3.2, "tail": 3.2,
               "rice": 4.0, "yawn": 4.0, "stretch": 4.0, "drop": 1.6}.get(self.anim)
        if dur and now - self._anim_since > dur:
            self.anim = "sing" if self.singing else "idle"
            self._last_anim = self.anim
            self._anim_since = now
        remain = max(0, int(self.focus_until - now)) if self.focus_until else 0
        visible = bool(self.bubble) and (self.bubble_until == 0 or now < self.bubble_until)
        return dict(title=self.title, steps=list(self.steps), index=self.index, done=list(self.done),
                    bubble=self.bubble, badge=self.badge, bubble_title=self.bubble_title,
                    tone=self.tone, song=self.song, artist=self.artist, lyric=self.lyric,
                    next=self.next_lyric, singing=self.singing, rice=self.rice,
                    focusRemaining=remain, quiet=self.quiet, point=self.point,
                    clip=self.anim, bubbleVisible=visible,
                    bubbleCompact=bool(self.singing and self.tone == "music"),
                    feeding=time.time() < self.feeding_until,
                    total=len(self.steps), finished=bool(self.steps) and self.index >= len(self.steps))

    def snapshot(self) -> dict:
        with self.lock:
            return self._snap()

    def _status_unlocked(self) -> dict:
        s = self._snap()
        st = self._step()
        sess = None
        if self.steps:
            sess = {"title": self.title, "total": len(self.steps), "index": self.index,
                    "done": sum(1 for d in self.done if d), "finished": s["finished"],
                    "agent": "", "text": (st or {}).get("text", ""),
                    "hint": (st or {}).get("hint", ""), "label": (st or {}).get("label", ""),
                    "x": (st or {}).get("x"), "y": (st or {}).get("y")}
        s.update(ok=True, version=VERSION, protocol=1, mode="tui", tui=True,
                 petVisible=True, pointer=bool(s["point"]),
                 pid=os.getpid(), uptime=int(time.time() - self.started), mainScale=1,
                 screens=[], assets="terminal", clips=["tui"], socket=str(PORT_FILE),
                 agent="", playful=True, sleeping=False, petScale=1, bubbleScale=1,
                 quiet=self.quiet, session=sess, songTitle=s["song"], songArtist=s["artist"])
        return s

    def status(self) -> dict:
        with self.lock:
            return self._status_unlocked()

    def _step(self) -> dict | None:
        if 0 <= self.index < len(self.steps):
            return self.steps[self.index]
        return None

    def _show_step(self) -> None:
        st = self._step()
        if not st:
            return
        self.bubble_title = self.title
        self.badge = f"第 {min(self.index + 1, len(self.steps))}/{len(self.steps)} 步"
        self.bubble = st.get("text", "") + (("\n提示：" + st["hint"]) if st.get("hint") else "")
        self.tone = "coach"
        self.point = st.get("x"), st.get("y"), st.get("label", "") if st.get("x") is not None else None
        if self.point and (self.point[0] is None or self.point[1] is None):
            self.point = None

    def handle(self, cmd: dict) -> dict:
        name = cmd.get("cmd", "")
        with self.lock:
            if name == "ping":
                return {"ok": True, "pong": True, "version": VERSION, "mode": "tui"}
            if name == "status":
                return self._status_unlocked()
            if name == "hello":
                self.title = ""
                self.steps = []
                self.index = 0
                self.done = []
                self.bubble_title = "大肥鱼在听"
                self.badge = f"{cmd.get('agent') or 'agent'} 已连接"
                self.bubble = "我是大肥鱼。接下来我会一步一步说给你听。"
                self.tone = "coach"
                self.anim = "pat"; self.bubble_until = 0
                self.point = None
                return {"ok": True, "agent": cmd.get("agent") or "agent"}
            if name == "bye":
                self.steps = []; self.index = 0; self.done = []
                self.bubble_title = ""; self.badge = ""; self.bubble = "那我先安静陪你。"
                self.tone = "coach"; self.point = None; self.anim = "idle"
                return {"ok": True}
            if name == "say":
                self.bubble_title = cmd.get("title", "")
                self.badge = cmd.get("step", "")
                self.bubble = cmd.get("text", "")
                self.tone = cmd.get("tone", "coach")
                hold = float(cmd.get("hold") or 0)
                self.bubble_until = time.time() + hold if hold > 0 else 0
                self.anim = cmd.get("anim") or "idle"
                return {"ok": True}
            if name == "guide":
                steps = [s for s in (cmd.get("steps") or []) if isinstance(s, dict) and s.get("text")]
                if not steps:
                    return {"ok": False, "error": "guide 需要至少一个步骤"}
                self.title = cmd.get("title", "")
                self.steps = steps
                self.index = max(0, min(int(cmd.get("start") or 0), len(steps) - 1))
                self.done = [False] * len(steps)
                self._show_step()
                st = self._step()
                self.anim = "working" if st and st.get("x") is not None else "pat"
                return self._status_unlocked()
            if name == "next":
                if not self.steps:
                    return {"ok": False, "error": "当前没有进行中的 guide"}
                self.done[self.index] = True
                self.anim = "pat"
                if self.index + 1 >= len(self.steps):
                    self.index = len(self.steps)
                    self.bubble_title = "完成！"
                    self.badge = f"完成 {len(self.steps)}/{len(self.steps)}"
                    self.bubble = "全部步骤都完成了，辛苦啦。"
                    self.tone = "success"
                    self.point = None
                    self.anim = "success"
                else:
                    self.index += 1
                    self._show_step()
                return self._status_unlocked()
            if name == "prev":
                if not self.steps:
                    return {"ok": False, "error": "当前没有进行中的 guide"}
                self.index = max(0, self.index - 1)
                if self.index < len(self.done):
                    self.done[self.index] = False
                self._show_step()
                return self._status_unlocked()
            if name == "finish":
                if not self.steps:
                    return {"ok": False, "error": "当前没有进行中的 guide"}
                self.done = [True] * len(self.steps)
                self.index = len(self.steps)
                self.bubble_title = "完成！"
                self.badge = f"完成 {len(self.steps)}/{len(self.steps)}"
                self.bubble = "全部步骤都完成了，辛苦啦。"
                self.tone = "success"
                self.point = None
                self.anim = "success"
                return self._status_unlocked()
            if name == "cancel":
                self.steps = []; self.index = 0; self.done = []
                self.bubble_title = ""; self.badge = ""
                self.bubble = cmd.get("text") or "好，先做到这里。"
                self.tone = "coach"; self.point = None; self.anim = "idle"
                return {"ok": True}
            if name == "point":
                self.point = (cmd.get("x"), cmd.get("y"), cmd.get("label", ""))
                self.bubble_title = ""
                self.badge = "指针"
                self.bubble = f"看这里：{cmd.get('label') or '目标'}  (x={cmd.get('x')}, y={cmd.get('y')})"
                self.tone = "coach"; self.anim = "working"
                return {"ok": True, "x": cmd.get("x"), "y": cmd.get("y")}
            if name == "clear_point":
                self.point = None
                return {"ok": True}
            if name == "music_start":
                self.song = cmd.get("title", ""); self.artist = cmd.get("artist", "")
                self.singing = True; self.music_at = time.time()
                self.anim = "sing"; self.bubble_until = 0
                self.bubble_title = f"{self.song} · {self.artist}" if self.artist else self.song
                self.badge = "♪"; self.bubble = "准备开唱…"; self.tone = "music"
                return {"ok": True}
            if name == "lyric":
                if self.steps or self.quiet:
                    return {"ok": True, "suppressed": True}
                self.song = cmd.get("title", self.song)
                self.artist = cmd.get("artist", self.artist)
                self.lyric = cmd.get("line", "") or "♪ 跟着哼"
                self.next_lyric = cmd.get("next", "")
                self.singing = True; self.music_at = time.time()
                self.bubble_title = f"{self.song} · {self.artist}" if self.artist else self.song
                total = int(cmd.get("total") or 0); idx = int(cmd.get("index") or 0)
                self.badge = f"♪ {min(idx+1,total)}/{total}" if total else "♪"
                self.bubble = self.lyric
                self.tone = "music"; self.anim = "sing"; self.bubble_until = 0
                return {"ok": True}
            if name == "music_stop":
                self.singing = False; self.lyric = ""; self.next_lyric = ""; self.anim = "idle"
                if self.tone == "music":
                    self.bubble = ""; self.badge = ""; self.bubble_title = ""
                return {"ok": True}
            if name == "feed":
                self.rice += 1
                self.bubble_title = ""; self.badge = "添饭"
                self.bubble = f"米饭！谢谢投喂，第 {self.rice} 碗。"; self.tone = "success"; self.anim = "rice"
                self._last_anim = "rice"; self._anim_since = time.time()
                self.bubble_until = time.time() + 4.5
                self.feeding_until = time.time() + 3.5
                return {"ok": True, "rice": self.rice}
            if name == "focus":
                if cmd.get("cancel"):
                    self.focus_until = 0
                    self.bubble = "好，专注取消。"
                else:
                    minutes = float(cmd.get("minutes") or 25)
                    self.focus_until = time.time() + max(0.01, min(180, minutes)) * 60
                    self.bubble_title = f"专注 {int(minutes) if minutes >= 1 else int(minutes*60)} {'分钟' if minutes >= 1 else '秒'}"
                    self.badge = "番茄钟"
                    self.bubble = "时间到了叫你，先专心做事。"; self.tone = "thinking"; self.anim = "yawn"
                return {"ok": True, "focusRemaining": max(0, int(self.focus_until - time.time())) if self.focus_until else 0}
            if name == "quiet":
                self.quiet = bool(cmd.get("on", True))
                return {"ok": True, "quiet": self.quiet}
            if name == "anim":
                self.anim = cmd.get("clip") or "idle"
                return {"ok": True, "clip": self.anim}
            if name == "hide" or name == "show":
                return {"ok": True, "petVisible": True}
            if name == "quit":
                self.stop = True
                return {"ok": True, "quitting": True}
            if name == "play" or name == "mood":
                self.bubble_title = ""; self.badge = "动画"
                self.bubble = cmd.get("text") or f"（{cmd.get('clip') or cmd.get('value') or 'idle'}）"
                self.tone = "coach"; self.anim = cmd.get("clip") if name == "play" else {"happy":"pat","think":"thinking","thinking":"thinking","focus":"working","working":"working","sleepy":"yawn","error":"error"}.get(cmd.get("value"), "idle")
                return {"ok": True}
            return {"ok": False, "error": f"终端版暂不支持：{name}"}

    def tick(self) -> None:
        with self.lock:
            if self.focus_until and time.time() >= self.focus_until:
                self.focus_until = 0
                self.singing = False
                self.bubble_title = "时间到"
                self.badge = "番茄钟完成"
                self.bubble = "休息一下，喝口水，站起来走两步。"
                self.tone = "success"; self.anim = "success"
            if self.singing and self.music_at and time.time() - self.music_at > 30:
                self.singing = False
                if self.tone == "music":
                    self.bubble = ""; self.badge = ""; self.bubble_title = ""


class Server:
    def __init__(self, core: Core):
        self.core = core
        self.sock = None
        self.thread = None
        self.token = secrets.token_hex(16)

    def start(self) -> int:
        HOME.mkdir(parents=True, exist_ok=True)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        s.listen(8)
        self.sock = s
        port = s.getsockname()[1]
        PORT_FILE.write_text(json.dumps({"port": port, "token": self.token, "pid": os.getpid()}), encoding="utf-8")
        try:
            os.chmod(PORT_FILE, 0o600)
        except OSError:
            pass
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return port

    def _loop(self) -> None:
        while not self.core.stop:
            try:
                c, _ = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._client, args=(c,), daemon=True).start()

    def _client(self, c: socket.socket) -> None:
        try:
            c.settimeout(3)
            data = b""
            while not data.endswith(b"\n"):
                chunk = c.recv(65536)
                if not chunk:
                    break
                data += chunk
            req = json.loads(data.decode()) if data.strip() else {}
            if req.get("token") != self.token:
                resp = {"ok": False, "error": "token"}
            else:
                resp = self.core.handle(req)
            c.sendall((json.dumps(resp, ensure_ascii=False) + "\n").encode())
        except Exception as exc:  # noqa: BLE001
            try:
                c.sendall((json.dumps({"ok": False, "error": str(exc)}) + "\n").encode())
            except Exception:
                pass
        finally:
            c.close()

    def stop(self) -> None:
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass
        try:
            PORT_FILE.unlink()
        except OSError:
            pass


def render(core: Core, width: int, color: bool) -> str:
    s = core.snapshot()
    c = (lambda k: COL.get(k, "")) if color else (lambda k: "")
    reset = c("reset") if color else ""
    w = max(44, min(width, 72))
    lines = []
    compact = bool(s.get("bubbleCompact"))
    if compact:
        # 歌词贴在头顶：一行歌词 + 一行歌名，不铺大框
        lyric = s.get("lyric") or s.get("bubble") or "♪ 跟着哼"
        lines.append(f"{c('magenta')}   ♪ {first_line(lyric, w - 8)[0]}{reset}")
        meta = s.get("song") or ""
        if s.get("artist"):
            meta = f"{meta} · {s['artist']}" if meta else s["artist"]
        if s.get("badge"):
            meta = f"{meta}   {s['badge']}" if meta else s["badge"]
        if meta:
            lines.append(f"{c('gray')}     {first_line(meta, w - 8)[0]}{reset}")
        lines.append("")
    fish = SLEEP_FISH if not s["singing"] and not s["bubble"] and not s["steps"] else FISH
    for i, f in enumerate(fish):
        tail = ""
        if i == 2:
            if s["singing"]:
                tail = "   ♪"
            elif s["quiet"]:
                tail = "   -"
            else:
                tail = "   ~"
        lines.append(f"{c('cyan')}{f}{tail}{reset}")
    if s["singing"]:
        lines.append(f"{c('magenta')}      ♪   ♫{reset}")
    lines.append("")
    if (s["bubble"] or s["bubble_title"]) and s.get("bubbleVisible", True) and not compact:
        inner = w - 4
        box = []
        if s["bubble_title"]:
            box.append(s["bubble_title"])
        if s["badge"]:
            box.append(s["badge"])
        for raw_line in (s["bubble"] or "").splitlines():
            box.extend(first_line(raw_line, inner))
        lines.append(f"{c('gray')}+{'-' * (w - 2)}+{reset}")
        for b in box[:8]:
            pad = max(0, inner - dwidth(b))
            lines.append(f"{c('gray')}|{reset} {b}{' ' * pad} {c('gray')}|{reset}")
        lines.append(f"{c('gray')}+{'-' * (w - 2)}+{reset}")
    if s["total"]:
        done = sum(1 for d in s["done"] if d)
        bar = "#" * done + "-" * (s["total"] - done)
        lines.append(f"  [{bar}] {done}/{s['total']} 步")
    if s["singing"] and s["song"] and not compact:
        lines.append(f"{c('magenta')}  ♪ {s['song']} - {s['artist']}{reset}")
        if s["next"]:
            lines.append(f"{c('gray')}    {s['next'][:w-6]}{reset}")
    foot = f"  米饭 {s['rice']} 碗"
    if s["focusRemaining"]:
        foot += f" · 专注 {s['focusRemaining']//60:02d}:{s['focusRemaining']%60:02d}"
    foot += " · [f]添饭 [p]摸摸 [space]下一步 [q]退出"
    lines.append(f"{c('gray')}{foot}{reset}")
    return "\n".join(lines)


def start_music() -> None:
    """启动歌词 watcher（如果还没有）；失败静默。"""
    try:
        pid = int(MUSIC_PID.read_text().strip())
        os.kill(pid, 0)
        return
    except Exception:
        pass
    target = Path(__file__).resolve().parent / "dafeiyu_music.py"
    if not target.exists():
        return
    try:
        with open(HOME / "music.log", "ab") as logf:
            import subprocess
            p = subprocess.Popen([sys.executable, str(target), "watch"], stdin=subprocess.DEVNULL,
                                 stdout=logf, stderr=logf, start_new_session=True)
        MUSIC_PID.write_text(str(p.pid), encoding="utf-8")
    except Exception:
        pass


def tui_once(width: int, color: bool) -> int:
    core = Core()
    core.handle({"cmd": "feed"})
    core.handle({"cmd": "lyric", "title": "桌面大肥鱼", "artist": "测试", "line": "海风轻轻吹过，我在桌面上陪你。",
                 "next": "下一句也唱给你听。", "index": 0, "total": 2})
    print(render(core, width, color))
    return 0


def read_key(timeout: float = 0.2):
    if os.name == "nt":
        try:
            import msvcrt
            if msvcrt.kbhit():
                return msvcrt.getwch()
        except Exception:
            pass
        time.sleep(timeout)
        return None
    try:
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        if r:
            return sys.stdin.read(1)
    except Exception:
        time.sleep(timeout)
    return None


def tui_viewer(width: int, color: bool) -> int:
    """附着到原生版：只显示，不拥有会话。"""
    print("\033[?25l", end="")
    try:
        while True:
            st = call({"cmd": "status"})
            if not st:
                print("大肥鱼原生版/终端核心没有运行。")
                return 1
            core = Core()
            core.title = (st.get("session") or {}).get("title", "") if isinstance(st.get("session"), dict) else ""
            sess = st.get("session") if isinstance(st.get("session"), dict) else None
            if sess:
                core.steps = [{"text": sess.get("text", "")}]
                core.index = sess.get("index", 0)
                core.done = [True] * sess.get("done", 0) + [False] * max(0, sess.get("total", 0) - sess.get("done", 0))
                core.bubble = sess.get("text", "")
                core.bubble_title = core.title
                core.badge = f"第 {core.index+1}/{sess.get('total',0)} 步"
            core.song = st.get("songTitle", "") or ""
            core.artist = st.get("songArtist", "") or ""
            core.lyric = st.get("lyric", "") or ""
            core.singing = bool(st.get("singing"))
            core.bubble = st.get("lyric") or core.bubble
            core.bubble_title = core.song or core.bubble_title
            core.badge = "♪ 唱歌中" if core.singing else core.badge
            print("\033[2J\033[H" + render(core, width, color), end="", flush=True)
            ch = read_key(0.25)
            if ch in ("q", "Q"):
                return 0
            if ch == " ":
                call({"cmd": "next"})
            elif ch in ("f", "F"):
                call({"cmd": "feed"})
            elif ch in ("p", "P"):
                call({"cmd": "say", "text": "嘿嘿，摸头最舒服了。"})
    finally:
        print("\033[?25h", end="")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dafeiyu tui", description="桌面大肥鱼 · 终端轻量版")
    ap.add_argument("--once", action="store_true", help="渲染一帧后退出")
    ap.add_argument("--headless", action="store_true", help="只运行核心/服务，不渲染")
    ap.add_argument("--no-music", action="store_true", help="不自动启动歌词监听")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--width", type=int, default=0)
    args = ap.parse_args(argv)
    enable_vt()
    width = args.width or shutil.get_terminal_size((72, 24)).columns
    color = (not args.no_color) and sys.stdout.isatty()

    if args.once:
        return tui_once(width, color)

    # 原生版在跑 → 作为显示器附着
    if call({"cmd": "ping"}) and SOCKET.exists():
        if args.headless:
            print("原生版正在运行；终端版附着模式不支持 --headless")
            return 0
        return tui_viewer(width, color)

    core = Core()
    server = Server(core)
    port = server.start()
    if not args.no_music:
        start_music()
    print(f"终端大肥鱼已启动（127.0.0.1:{port}）。在其它终端运行 dafeiyu next / feed / focus。")
    if args.headless:
        try:
            while not core.stop:
                core.tick(); time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            server.stop()
        return 0

    # 交互渲染
    fd = sys.stdin.fileno()
    old = None
    try:
        import termios, tty
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    except Exception:
        old = None
    print("\033[?25l", end="")
    try:
        while not core.stop:
            core.tick()
            print("\033[2J\033[H" + render(core, width, color), end="", flush=True)
            ch = None
            if os.name == "nt":
                import msvcrt
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
            else:
                r, _, _ = select.select([sys.stdin], [], [], 0.15)
                if r:
                    ch = sys.stdin.read(1)
            if ch:
                if ch in ("q", "Q"):
                    break
                if ch == " ":
                    core.handle({"cmd": "next"})
                elif ch in ("f", "F"):
                    core.handle({"cmd": "feed"})
                elif ch in ("p", "P"):
                    core.handle({"cmd": "say", "text": "嘿嘿，摸头最舒服了。"})
                elif ch in ("s", "S"):
                    core.handle({"cmd": "status"})
            time.sleep(0.12)
    except KeyboardInterrupt:
        pass
    finally:
        print("\033[?25h", end="")
        if old is not None:
            try:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except Exception:
                pass
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
