#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""桌面大肥鱼 · 音乐/歌词/唱歌模块（macOS + Windows，按需联网）。

macOS：使用 Runtime/music 下的 BSD MediaRemote 适配器（Apple Music / 网易云 /
QQ 音乐等系统 Now Playing），不需要辅助功能或录屏权限。
Windows：调用 media_smtc.ps1（系统 SMTC，覆盖网易云 / QQ 音乐 / Apple Music）。
歌词：LRCLIB（开放歌词库），本地缓存；只发送歌名/歌手/时长，不发送任何个人数据。

    dafeiyu music now              # 当前在放什么
    dafeiyu music watch            # 常驻：把当前歌词推给桌宠
    dafeiyu music on / off         # 开关后台监听
    dafeiyu music test             # 不联网，测试唱歌气泡
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


if os.name == "nt":
    for _stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if _stream is not None:
                _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

VERSION = "1.1.0"
ROOT = Path(__file__).resolve().parent.parent
HOME = Path(os.environ.get("DAFEIYU_HOME", str(Path.home() / ".dafeiyu")))
SOCKET = HOME / "coach.sock"
LYRICS_DIR = HOME / "lyrics"
PID_FILE = HOME / "music.pid"
LOG_FILE = HOME / "music.log"
CONFIG_FILE = HOME / "music.json"
CACHE_TTL = 30 * 86400
NEGATIVE_TTL = 3600

UA = "dafeiyu-coach/1.1 (desktop pet; lyrics via lrclib.net)"


# ------------------------------------------------------------------ utils

def log(msg: str) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%H:%M:%S')}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
    if os.environ.get("DAFEIYU_DEBUG"):
        sys.stderr.write(line)


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\(.*?\)|（.*?）|\[.*?\]|【.*?】", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def music_dir() -> Path:
    env = os.environ.get("DAFEIYU_MUSIC_DIR")
    if env:
        return Path(env).expanduser()
    for p in (HOME / "music", ROOT / "Runtime" / "music"):
        if p.exists():
            return p
    return HOME / "music"


def config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"enabled": True, "offset": 0.0, "synced": True}


def save_config(cfg: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def send_daemon(payload: dict) -> dict | None:
    if SOCKET.exists() and os.name != "nt":
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect(str(SOCKET))
            s.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            data = b""
            while not data.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
            s.close()
            return json.loads(data.decode("utf-8")) if data.strip() else None
        except Exception:
            pass
    port_file = HOME / "coach.port"
    if port_file.exists():
        try:
            info = json.loads(port_file.read_text(encoding="utf-8"))
            s = socket.create_connection(("127.0.0.1", int(info["port"])), timeout=1.0)
            payload = dict(payload); payload["token"] = info.get("token", "")
            s.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            data = b""
            while not data.endswith(b"\n"):
                chunk = s.recv(65536)
                if not chunk:
                    break
                data += chunk
            s.close()
            return json.loads(data.decode("utf-8")) if data.strip() else None
        except Exception:
            return None
    return None


def run(cmd, timeout=8, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, env=e)
    except Exception as exc:  # noqa: BLE001
        log(f"run failed {cmd[0]}: {exc}")
        return None


# ------------------------------------------------------------------ now playing

def now_playing_macos() -> dict | None:
    d = music_dir()
    script = d / "mediaremote-adapter.pl"
    fw = d / "MediaRemoteAdapter.framework"
    if script.exists() and fw.exists():
        perl = "/usr/bin/perl" if Path("/usr/bin/perl").exists() else (shutil.which("perl") or "perl")
        p = run([perl, str(script), str(fw), "get"], timeout=8)
        if p and p.returncode == 0 and p.stdout.strip() and p.stdout.strip() != "null":
            try:
                raw = json.loads(p.stdout)
                return {
                    "title": raw.get("title") or "",
                    "artist": raw.get("artist") or "",
                    "album": raw.get("album") or "",
                    "duration": float(raw.get("duration") or 0),
                    "elapsed": float(raw.get("elapsedTime") or 0),
                    "playing": bool(raw.get("playing")) and (float(raw.get("playbackRate") or 0) > 0 or raw.get("playing") is True),
                    "app": raw.get("bundleIdentifier") or "",
                    "source": "mediaremote",
                }
            except Exception as exc:  # noqa: BLE001
                log(f"adapter parse: {exc}")
    # 兜底：Apple Music 的 AppleScript（不依赖 MediaRemote）
    p = run(["/usr/bin/osascript", "-e",
             'tell application "Music" to if player state is playing then return (name of current track) & "\t" & (artist of current track) & "\t" & (album of current track) & "\t" & (duration of current track) & "\t" & (player position) & "\tplaying"'], timeout=4)
    if p and p.returncode == 0 and p.stdout.strip():
        parts = p.stdout.strip().split("\t")
        if len(parts) >= 6:
            return {"title": parts[0], "artist": parts[1], "album": parts[2],
                    "duration": float(parts[3] or 0), "elapsed": float(parts[4] or 0),
                    "playing": True, "app": "com.apple.Music", "source": "applescript"}
    return None


def now_playing_windows() -> dict | None:
    d = music_dir()
    ps = d / "media_smtc.ps1"
    if not ps.exists():
        return None
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        return None
    p = run([exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps)], timeout=8)
    if p and p.returncode == 0 and p.stdout.strip():
        try:
            raw = json.loads(p.stdout)
            return {
                "title": raw.get("title") or "", "artist": raw.get("artist") or "",
                "album": raw.get("album") or "", "duration": float(raw.get("duration") or 0),
                "elapsed": float(raw.get("elapsed") or 0), "playing": bool(raw.get("playing")),
                "app": raw.get("app") or "", "source": "smtc",
            }
        except Exception as exc:  # noqa: BLE001
            log(f"smtc parse: {exc}")
    return None


def now_playing_linux() -> dict | None:
    exe = shutil.which("playerctl")
    if not exe:
        return None
    p = run([exe, "metadata", "--format",
             "{{status}}\t{{title}}\t{{artist}}\t{{album}}\t{{mpris:length}}\t{{position}}\t{{playerName}}"], timeout=4)
    if not p or p.returncode != 0 or not p.stdout.strip():
        return None
    parts = p.stdout.strip().split("\t")
    if len(parts) < 7:
        return None
    try:
        dur = float(parts[4]) / 1_000_000
    except ValueError:
        dur = 0
    try:
        pos = float(parts[5]) / 1_000_000
    except ValueError:
        pos = 0
    return {"title": parts[1], "artist": parts[2], "album": parts[3],
            "duration": dur, "elapsed": pos, "playing": parts[0].lower() == "playing",
            "app": parts[6], "source": "mpris"}


def now_playing() -> dict | None:
    fake = os.environ.get("DAFEIYU_NOWPLAYING_JSON")
    if fake:
        try:
            t = json.loads(fake)
            t.setdefault("playing", True); t.setdefault("title", ""); t.setdefault("artist", "")
            t.setdefault("album", ""); t.setdefault("duration", 0); t.setdefault("elapsed", 0)
            t.setdefault("app", "test"); t.setdefault("source", "test")
            return t
        except Exception as exc:  # noqa: BLE001
            log(f"fake now playing: {exc}")
    if sys.platform == "darwin":
        return now_playing_macos()
    if os.name == "nt":
        return now_playing_windows()
    return now_playing_linux()


# ------------------------------------------------------------------ lyrics

def http_json(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        try:
            import certifi  # type: ignore
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        log(f"urllib failed: {exc}; curl fallback")
        curl = shutil.which("curl")
        if not curl:
            raise
        p = run([curl, "-sS", "--max-time", str(timeout), "-A", UA, url], timeout=timeout + 2)
        if not p or p.returncode != 0 or not p.stdout.strip():
            raise RuntimeError(f"curl failed: {getattr(p, 'stderr', '')}")
        return json.loads(p.stdout)


def parse_lrc(text: str) -> list[list]:
    lines = []
    for raw in (text or "").splitlines():
        stamps = re.findall(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]", raw)
        content = re.sub(r"\[[^\]]*\]", "", raw).strip()
        if not stamps:
            continue
        for mm, ss, frac in stamps:
            try:
                t = int(mm) * 60 + int(ss) + (int(frac.ljust(3, "0")) / 1000 if frac else 0)
            except ValueError:
                continue
            if content:
                lines.append([round(t, 2), content])
    dedup = {}
    for t, s in lines:
        dedup.setdefault((t, s), True)
    out = [[t, s] for t, s in dedup]
    out.sort(key=lambda x: x[0])
    return out


def cache_path(track: dict) -> Path:
    key = sha1(f"{norm(track.get('title',''))}|{norm(track.get('artist',''))}|{int(float(track.get('duration') or 0))}")
    return LYRICS_DIR / f"{key}.json"


def load_cached(track: dict, allow_stale: bool = False) -> dict | None:
    p = cache_path(track)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    age = time.time() - float(d.get("fetchedAt") or 0)
    ttl = CACHE_TTL if d.get("lines") else NEGATIVE_TTL
    if not allow_stale and age > ttl:
        return None
    return d


def pick_result(results: list, track: dict) -> dict | None:
    title, artist = norm(track.get("title", "")), norm(track.get("artist", ""))
    dur = float(track.get("duration") or 0)
    best = None
    best_score = -1e9
    for r in results or []:
        if not isinstance(r, dict):
            continue
        if r.get("instrumental"):
            continue
        synced = r.get("syncedLyrics") or ""
        plain = r.get("plainLyrics") or ""
        if not synced and not plain:
            continue
        rt, ra = norm(r.get("trackName", "")), norm(r.get("artistName", ""))
        score = 0
        if title and title in rt: score += 30
        if artist and artist in ra: score += 30
        if synced: score += 50
        rd = float(r.get("duration") or 0)
        if dur and rd:
            diff = abs(rd - dur)
            score += max(-20, 20 - diff)
        if score > best_score:
            best, best_score = r, score
    return best


def local_lyrics(track: dict) -> dict | None:
    dirs = []
    env = os.environ.get("DAFEIYU_LYRICS_DIR")
    if env:
        dirs.append(Path(env).expanduser())
    dirs.append(LYRICS_DIR / "local")
    title = re.sub(r'[\\/:*?"<>|]', "_", track.get("title") or "").strip()
    artist = re.sub(r'[\\/:*?"<>|]', "_", track.get("artist") or "").strip()
    names = [f"{title} - {artist}.lrc", f"{title}.lrc", f"{artist} - {title}.lrc"]
    for d in dirs:
        for name in names:
            f = d / name
            if f.exists():
                try:
                    lines = parse_lrc(f.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
                if lines:
                    return {"title": track.get("title", ""), "artist": track.get("artist", ""),
                            "duration": track.get("duration", 0), "lines": lines, "synced": True,
                            "source": "local", "fetchedAt": time.time()}
    return None


def fetch_lyrics(track: dict, no_network: bool = False, allow_stale: bool = False) -> dict:
    local = local_lyrics(track)
    if local:
        return local
    cached = load_cached(track, allow_stale=allow_stale)
    if cached is not None:
        return cached
    if no_network:
        return {"title": track.get("title", ""), "artist": track.get("artist", ""),
                "duration": track.get("duration", 0), "lines": [], "synced": False,
                "source": "cache-miss", "fetchedAt": time.time()}
    title = track.get("title") or ""
    artist = track.get("artist") or ""
    dur = int(float(track.get("duration") or 0))
    data = None
    # 精确匹配优先（duration 必须 1..3600）
    if dur > 0:
        q = urllib.parse.urlencode({"track_name": title, "artist_name": artist, "duration": dur})
        try:
            data = http_json(f"https://lrclib.net/api/get?{q}")
        except Exception as exc:  # noqa: BLE001
            log(f"lrclib get: {exc}")
    if not data or not isinstance(data, dict) or not (data.get("syncedLyrics") or data.get("plainLyrics")):
        # 搜索兜底
        for params in ({"track_name": title, "artist_name": artist}, {"q": f"{title} {artist}"}):
            try:
                res = http_json("https://lrclib.net/api/search?" + urllib.parse.urlencode(params))
                if isinstance(res, list):
                    data = pick_result(res, track)
                    if data:
                        break
            except Exception as exc:  # noqa: BLE001
                log(f"lrclib search: {exc}")
                time.sleep(1.0)
    lines = []
    synced = False
    source = "lrclib"
    if isinstance(data, dict):
        synced_text = data.get("syncedLyrics") or ""
        plain_text = data.get("plainLyrics") or ""
        if synced_text:
            lines = parse_lrc(synced_text)
            synced = bool(lines)
        if not lines and plain_text:
            raw = [x.strip() for x in plain_text.splitlines() if x.strip()]
            if raw:
                # 没有时间轴时按歌长均匀铺开，只用于“跟着哼”
                for i, text in enumerate(raw):
                    t = (i / max(1, len(raw) - 1)) * max(1, dur - 6)
                    lines.append([round(t, 2), text])
        source = "lrclib"
    out = {"title": title, "artist": artist, "duration": dur, "lines": lines,
           "synced": synced, "source": source, "fetchedAt": time.time(),
           "instrumental": bool(isinstance(data, dict) and data.get("instrumental"))}
    LYRICS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        cache_path(track).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    log(f"lyrics {title} - {artist}: {len(lines)} lines synced={synced} source={source}")
    return out


def line_at(lines: list, t: float) -> int:
    idx = -1
    for i, (ts, _) in enumerate(lines):
        if ts <= t:
            idx = i
        else:
            break
    return idx


# ------------------------------------------------------------------ watch

def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def watch(interval: float = 1.0, no_network: bool = False, dry_run: bool = False,
          once: bool = False, limit: float | None = None) -> int:
    cfg = config()
    offset = float(cfg.get("offset") or 0)
    track = now_playing()
    if once:
        print(json.dumps(track, ensure_ascii=False, indent=2))
        if track and track.get("title"):
            lyr = fetch_lyrics(track, no_network=no_network)
            i = line_at(lyr.get("lines") or [], float(track.get("elapsed") or 0) + offset)
            print(json.dumps({"lyrics": lyr.get("lines", [])[:3], "lineIndex": i,
                              "synced": lyr.get("synced")}, ensure_ascii=False, indent=2))
        return 0
    last_track_key = None
    last_line = None
    last_playing = False
    lyrics = {"lines": [], "synced": False}
    last_send = 0.0
    started = time.time()
    while True:
        if limit and time.time() - started > limit:
            return 0
        track = now_playing()
        now = time.time()
        if not track or not track.get("playing") or not track.get("title"):
            if last_playing:
                if not dry_run:
                    send_daemon({"cmd": "music_stop"})
                print("♪ stopped")
                log("music stopped")
            last_playing = False
            last_track_key = None
            last_line = None
            time.sleep(max(1.0, interval))
            continue
        key = f"{norm(track.get('title',''))}|{norm(track.get('artist',''))}"
        if key != last_track_key:
            last_track_key = key
            last_line = None
            lyrics = fetch_lyrics(track, no_network=no_network)
            if not dry_run:
                send_daemon({"cmd": "music_start", "title": track.get("title", ""),
                             "artist": track.get("artist", ""), "album": track.get("album", ""),
                             "app": track.get("app", ""), "duration": track.get("duration", 0)})
            print(f"♪ {track.get('title')} - {track.get('artist')}  ({len(lyrics.get('lines') or [])} lines)")
            last_playing = True
        lines = lyrics.get("lines") or []
        elapsed = float(track.get("elapsed") or 0) + offset
        idx = line_at(lines, elapsed)
        if idx != last_line and idx >= 0 and idx < len(lines):
            last_line = idx
            line = lines[idx][1]
            nxt = lines[idx + 1][1] if idx + 1 < len(lines) else ""
            if not dry_run:
                send_daemon({"cmd": "lyric", "title": track.get("title", ""),
                             "artist": track.get("artist", ""), "album": track.get("album", ""),
                             "app": track.get("app", ""), "line": line, "next": nxt,
                             "index": idx, "total": len(lines), "synced": bool(lyrics.get("synced")),
                             "elapsed": elapsed})
            last_send = now
            print(f"  [{idx+1}/{len(lines)}] {line}")
        elif not lines and now - last_send > 10 and not dry_run:
            # 纯音乐/暂无歌词：心跳，避免桌面气泡 30s 后自动收起
            send_daemon({"cmd": "lyric", "title": track.get("title", ""),
                         "artist": track.get("artist", ""), "app": track.get("app", ""),
                         "line": "", "next": "", "index": 0, "total": 0,
                         "synced": False, "elapsed": elapsed})
            last_send = now
        elif lines and idx >= 0 and now - last_send > 10 and not dry_run:
            # 长间奏/长句：心跳同一句
            send_daemon({"cmd": "lyric", "title": track.get("title", ""),
                         "artist": track.get("artist", ""), "app": track.get("app", ""),
                         "line": lines[idx][1], "next": "", "index": idx, "total": len(lines),
                         "synced": bool(lyrics.get("synced")), "elapsed": elapsed})
            last_send = now
        last_playing = True
        time.sleep(max(0.5, interval))


def stop_watcher() -> bool:
    try:
        pid = int(PID_FILE.read_text().strip())
    except Exception:
        return False
    if not pid_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    for _ in range(20):
        if not pid_alive(pid):
            break
        time.sleep(0.1)
    PID_FILE.unlink(missing_ok=True)
    return True


def start_watcher() -> int:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if pid_alive(pid):
                print(f"音乐监听已在运行（pid {pid}）")
                return 0
        except Exception:
            pass
    HOME.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DAFEIYU_HOME"] = str(HOME)
    with open(LOG_FILE, "ab") as logf:
        p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "watch"],
                             stdin=subprocess.DEVNULL, stdout=logf, stderr=logf,
                             env=env, start_new_session=True)
    PID_FILE.write_text(str(p.pid), encoding="utf-8")
    cfg = config(); cfg["enabled"] = True; save_config(cfg)
    print(f"音乐监听已启动（pid {p.pid}）；放歌时大肥鱼会跟着歌词唱歌")
    return 0


# ------------------------------------------------------------------ main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dafeiyu music", description="音乐检测 / 歌词 / 唱歌")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("now", help="输出当前歌曲（JSON）")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("watch", help="常驻监听并推送歌词")
    s.add_argument("--interval", type=float, default=1.0)
    s.add_argument("--once", action="store_true")
    s.add_argument("--no-network", action="store_true")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--limit", type=float, default=None)
    s = sub.add_parser("on", help="启动后台监听")
    s = sub.add_parser("off", help="停止后台监听")
    s = sub.add_parser("status", help="状态")
    s = sub.add_parser("lyrics", help="只查歌词")
    s.add_argument("--title", default=None)
    s.add_argument("--artist", default=None)
    s.add_argument("--duration", type=float, default=0)
    s.add_argument("--no-network", action="store_true")
    s = sub.add_parser("test", help="不联网，让桌宠唱一段测试歌词")
    s.add_argument("--line", default="海风轻轻吹过，我在桌面上陪你。")
    s.add_argument("--title", default=None)
    s.add_argument("--artist", default=None)
    s = sub.add_parser("import-lrc", help="把本地 .lrc 放进歌词库（补 LRCLIB 没有的中文歌）")
    s.add_argument("file")
    s.add_argument("--title", required=True)
    s.add_argument("--artist", default="")
    s = sub.add_parser("local-dir", help="显示本地歌词目录")
    s = sub.add_parser("offset", help="歌词整体偏移秒数")
    s.add_argument("seconds", type=float)
    args = ap.parse_args(argv)

    if args.cmd == "now":
        t = now_playing()
        print(json.dumps(t or {}, ensure_ascii=False, indent=2))
        return 0 if t else 1
    if args.cmd == "watch":
        return watch(args.interval, args.no_network, args.dry_run, args.once, args.limit)
    if args.cmd == "on":
        return start_watcher()
    if args.cmd == "off":
        print("音乐监听已停止" if stop_watcher() else "音乐监听本来就没在运行")
        cfg = config(); cfg["enabled"] = False; save_config(cfg)
        send_daemon({"cmd": "music_stop"})
        return 0
    if args.cmd == "status":
        cfg = config()
        t = now_playing()
        print(f"监听：{'开' if cfg.get('enabled') else '关'} · 偏移 {cfg.get('offset', 0)}s")
        if t and t.get("playing"):
            print(f"正在播放：{t.get('title')} - {t.get('artist')}  {t.get('elapsed', 0):.1f}/{t.get('duration', 0):.0f}s")
        else:
            print("当前：没有在播放")
        return 0
    if args.cmd == "lyrics":
        t = {"title": args.title, "artist": args.artist, "duration": args.duration}
        if not args.title:
            cur = now_playing()
            if not cur:
                print("没有在播放，也没有给 --title")
                return 1
            t = cur
        lyr = fetch_lyrics(t, no_network=args.no_network)
        print(json.dumps({k: lyr.get(k) for k in ("title", "artist", "synced", "source")}, ensure_ascii=False))
        for i, (ts, line) in enumerate(lyr.get("lines") or []):
            if i < 8:
                print(f"{int(ts//60):02d}:{int(ts%60):02d} {line}")
        return 0 if lyr.get("lines") else 1
    if args.cmd == "test":
        t = now_playing() or {"title": "桌面大肥鱼", "artist": "测试", "duration": 0}
        if args.title:
            t["title"] = args.title
        if args.artist is not None:
            t["artist"] = args.artist
        send_daemon({"cmd": "music_start", "title": t.get("title", "桌面大肥鱼"),
                     "artist": t.get("artist", "测试"), "app": "test", "duration": 0})
        time.sleep(0.2)
        r = send_daemon({"cmd": "lyric", "title": t.get("title", "桌面大肥鱼"),
                         "artist": t.get("artist", "测试"), "line": args.line,
                         "next": "下一句也唱给你听。", "index": 0, "total": 2,
                         "synced": True, "elapsed": 0})
        print(json.dumps(r or {"ok": False, "error": "守护进程未运行"}, ensure_ascii=False))
        return 0 if r and r.get("ok") else 1
    if args.cmd == "import-lrc":
        src = Path(args.file).expanduser()
        if not src.exists():
            print(f"找不到：{src}")
            return 1
        safe = lambda x: re.sub(r'[\\/:*?"<>|]', "_", x).strip()
        d = LYRICS_DIR / "local"; d.mkdir(parents=True, exist_ok=True)
        name = f"{safe(args.title)} - {safe(args.artist)}.lrc" if args.artist else f"{safe(args.title)}.lrc"
        dest = d / name
        shutil.copy2(src, dest)
        print(f"已导入：{dest}")
        return 0
    if args.cmd == "local-dir":
        print(LYRICS_DIR / "local")
        return 0
    if args.cmd == "offset":
        cfg = config(); cfg["offset"] = args.seconds; save_config(cfg)
        print(f"歌词偏移已设为 {args.seconds}s")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
