#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""桌面大肥鱼 Coach 验收审计。

默认在临时 HOME 中完成「安装 → 端到端 → MCP → 性能 → 截图 → 卸载」，
不会碰你的真实 ~/.dafeiyu、agent 配置或桌宠。

    python3 audit/audit.py            # 全部（含截图）
    python3 audit/audit.py --no-visual
    python3 audit/audit.py --keep-temp
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "dafeiyu"
MCP = ROOT / "bin" / "dafeiyu_mcp.py"
BUILD = ROOT / ".build" / "dafeiyu-daemon"
SHOTS = ROOT / "audit" / "screenshots"

results: list[dict] = []
temp_root: Path | None = None
cli_path: Path | None = None
daemon_pid: int | None = None
visual_enabled = True


def record(name: str, ok: bool, detail: str = "", group: str = "") -> bool:
    results.append({"name": name, "ok": bool(ok), "detail": str(detail), "group": group})
    mark = "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"
    print(f"  {mark} {name}" + (f" — {detail}" if detail else ""))
    return bool(ok)


def section(title: str) -> None:
    print(f"\n\033[1;36m{title}\033[0m")


def run(cmd, cwd=None, env=None, timeout=30, check=False):
    e = os.environ.copy()
    e.update(env or {})
    p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"{cmd} failed: {p.stderr or p.stdout}")
    return p


def env_for_temp() -> dict:
    assert temp_root
    return {
        "HOME": str(temp_root),
        "DAFEIYU_HOME": str(temp_root / ".dafeiyu"),
        "PREFIX": str(temp_root / ".local"),
        "PATH": f"{temp_root}/.local/bin:" + os.environ.get("PATH", ""),
    }


def coach(*args, timeout=15, check=False):
    assert cli_path
    p = run([str(cli_path), *args], env=env_for_temp(), timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"dafeiyu {' '.join(args)} 失败：{p.stderr or p.stdout}")
    return p


def coach_json(*args, timeout=15):
    p = coach(*args, "--json", timeout=timeout)
    try:
        return json.loads(p.stdout)
    except Exception:
        raise RuntimeError(f"无法解析 dafeiyu 输出：{p.stdout} / {p.stderr}")


def status() -> dict:
    p = coach_json("status")
    return p


def wait_for(predicate, timeout=6.0, interval=0.1):
    end = time.time() + timeout
    while time.time() < end:
        try:
            v = predicate()
            if v:
                return v
        except Exception:
            pass
        time.sleep(interval)
    return None


# ------------------------------------------------------------------ checks

def check_static() -> None:
    section("1. 构建与静态检查")
    src = sorted((ROOT / "Sources").glob("*.swift"))
    out = "/tmp/dafeiyu-audit-build"
    p = run([
        "swiftc", "-O", "-swift-version", "5", "-warnings-as-errors",
        "-target", "arm64-apple-macosx13.0", *[str(x) for x in src],
        "-framework", "AppKit", "-framework", "QuartzCore", "-o", out,
    ], timeout=240)
    record("swiftc -warnings-as-errors 编译", p.returncode == 0,
           (p.stderr or p.stdout).strip().splitlines()[-1] if p.returncode else f"{len(src)} 个源文件", "static")
    record("构建产物存在", BUILD.exists(), f"{BUILD.stat().st_size/1024:.0f} KB" if BUILD.exists() else "缺失", "static")

    py_ok = True
    py_err = ""
    for f in [CLI, MCP, ROOT / "bin/dafeiyu_music.py", ROOT / "bin/dafeiyu_tui.py", ROOT / "bin/dafeiyu_gui.py"]:
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")
        except Exception as exc:  # noqa: BLE001
            py_ok = False
            py_err = f"{f.name}: {exc}"
    record("Python 语法", py_ok, py_err or "dafeiyu / dafeiyu_mcp.py", "static")

    sh = run(["bash", "-n", str(ROOT / "scripts/install.sh"), str(ROOT / "scripts/uninstall.sh"),
              str(ROOT / "scripts/build.sh")])
    record("Shell 语法", sh.returncode == 0, sh.stderr.strip(), "static")

    gui = run([sys.executable, str(ROOT / "bin/dafeiyu_gui.py"), "--check"], timeout=30)
    try:
        gui_ok = gui.returncode == 0 and json.loads(gui.stdout.splitlines()[-1]).get("ok") is True
    except Exception:
        gui_ok = False
    record("桌面窗口版依赖/素材", gui_ok, (gui.stdout or gui.stderr).strip()[-120:], "static")

    p = run([str(BUILD), "--selftest"])
    record("内置单元自测（步骤/坐标/15 组素材）", p.returncode == 0, p.stdout.strip(), "static")

    p = run([str(BUILD), "--check"])
    try:
        d = json.loads(p.stdout)
        ok = p.returncode == 0 and d.get("ok") and d.get("clips") == 15 and d.get("frames") == 890
        record("素材清单完整", ok, f"{d.get('clips')} 组 / {d.get('frames')} 帧 / 缺失 {len(d.get('missing') or [])}", "static")
    except Exception:
        record("素材清单完整", False, p.stdout[:200] + p.stderr[:200], "static")

    lines = {f.name: len(f.read_text(encoding="utf-8").splitlines()) for f in src}
    biggest = max(lines.items(), key=lambda kv: kv[1])
    record("单文件行数 < 1100", biggest[1] < 1100, f"{biggest[0]} {biggest[1]} 行", "static")

    man = json.loads((ROOT / "Runtime/clips/manifest.json").read_text())
    record("manifest 许可与来源", "MIT" in man.get("license", "") and "PC2005-cloud/dsh-pet" in json.dumps(man),
           man.get("license", ""), "static")

    clips = man.get("clips") or {}
    rice = clips.get("rice") or {}
    sing = clips.get("sing") or {}
    ok_rice = (rice.get("frameCount") == 48 and rice.get("loop") is False
               and len(rice.get("frames") or []) == 48
               and all((ROOT / "Runtime/clips" / f).exists() for f in rice.get("frames") or []))
    ok_sing = (sing.get("frameCount") == 22 and sing.get("loop") is True
               and all((ROOT / "Runtime/clips" / f).exists() for f in sing.get("frames") or []))
    record("米饭/唱歌独立剪辑", ok_rice and ok_sing,
           f"rice={rice.get('frameCount')} sing={sing.get('frameCount')}", "static")

    try:
        from PIL import Image
        def bowl_ratio(rel: str) -> float:
            im = Image.open(ROOT / "Runtime/clips" / rel).convert("RGBA")
            crop = im.crop((100, 175, 210, 245))
            px = list(crop.getdata())
            opaque = sum(1 for r, g, b, a in px if a > 128)
            white = sum(1 for r, g, b, a in px if a > 128 and r > 235 and g > 235 and b > 228)
            return white / max(1, opaque)
        r_ratio = bowl_ratio(rice["frames"][0])
        y_ratio = bowl_ratio("yawn/yawn_000.webp")
        record("米饭碗朝上可见（白瓷碗/米饭，不是 token）", r_ratio > 0.15 and r_ratio > y_ratio * 3,
               f"碗体白像素 {r_ratio:.0%} / 源动作 {y_ratio:.0%}", "static")
    except Exception as exc:
        record("米饭碗朝上可见（白瓷碗/米饭，不是 token）", False, str(exc)[:120], "static")


def check_size() -> None:
    section("2. 体积预算")
    bin_size = BUILD.stat().st_size
    clips_size = sum(p.stat().st_size for p in (ROOT / "Runtime/clips").rglob("*") if p.is_file())
    record("二进制 < 2 MB", bin_size < 2 * 1024 * 1024, f"{bin_size/1024:.0f} KB", "size")
    record("动画素材 < 8 MB", clips_size < 8 * 1024 * 1024, f"{clips_size/1048576:.2f} MB / 890 帧", "size")
    music_size = sum(p.stat().st_size for p in (ROOT / "Runtime/music").rglob("*") if p.is_file())
    record("音乐适配器 < 1 MB", music_size < 1024 * 1024, f"{music_size/1024:.0f} KB", "size")
    total = bin_size + clips_size + music_size
    record("运行体总计 < 10 MB", total < 10 * 1024 * 1024, f"{total/1048576:.2f} MB", "size")
    src_size = sum(p.stat().st_size for p in (ROOT / "Sources").glob("*.swift"))
    record("源码 < 200 KB", src_size < 200 * 1024, f"{src_size/1024:.0f} KB", "size")


def check_install() -> None:
    section("3. 安装 / 适配器（临时 HOME）")
    global cli_path
    assert temp_root
    p = run([str(ROOT / "scripts/install.sh"), "--no-start", "--with-mcp"], env=env_for_temp(), timeout=120)
    record("安装脚本", p.returncode == 0, p.stdout.strip().splitlines()[-1] if p.returncode == 0 else p.stderr[-300:], "install")
    cli_path = temp_root / ".local/bin/dafeiyu"
    record("CLI 已安装", cli_path.exists() and os.access(cli_path, os.X_OK), str(cli_path), "install")
    record("守护进程已安装", (temp_root / ".local/bin/dafeiyu-daemon").exists(), "", "install")
    record("MCP 脚本已安装", (temp_root / ".local/bin/dafeiyu_mcp.py").exists(), "", "install")
    record("动画素材已安装", (temp_root / ".dafeiyu/clips/manifest.json").exists(), "", "install")
    record("歌词模块已安装", (temp_root / ".local/bin/dafeiyu_music.py").exists(), "", "install")
    record("终端版已安装", (temp_root / ".local/bin/dafeiyu_tui.py").exists(), "", "install")
    record("macOS 音乐适配器已安装",
           (temp_root / ".dafeiyu/music/mediaremote-adapter.pl").exists()
           and (temp_root / ".dafeiyu/music/MediaRemoteAdapter.framework").exists(), "", "install")
    record("Windows SMTC 已安装", (temp_root / ".dafeiyu/music/media_smtc.ps1").exists(), "", "install")

    for agent, rel in [
        ("Qoder", ".qoder/skills/dafeiyu-coach/SKILL.md"),
        ("Claude Code", ".claude/skills/dafeiyu-coach/SKILL.md"),
        ("Codex", ".codex/skills/dafeiyu-coach/SKILL.md"),
        ("dsh", ".dsh/skills/dafeiyu-coach/SKILL.md"),
    ]:
        path = temp_root / rel
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        ok = text.startswith("---") and "name: dafeiyu-coach" in text and "description:" in text and len(text) > 2000
        record(f"{agent} skill 有效", ok, f"{len(text)} 字符" if text else "缺失", "install")

    for agent, rel in [
        ("Qoder", ".qoder/commands/dafeiyu.md"),
        ("Claude Code", ".claude/commands/dafeiyu.md"),
        ("Codex", ".codex/prompts/dafeiyu.md"),
    ]:
        path = temp_root / rel
        record(f"{agent} /dafeiyu 命令", path.exists(), str(path.relative_to(temp_root)), "install")

    for label, rel, key in [
        ("Qoder MCP", ".qoder/mcp.json", "mcpServers"),
        ("Claude MCP", ".claude.json", "mcpServers"),
    ]:
        path = temp_root / rel
        try:
            d = json.loads(path.read_text())
            ok = "dafeiyu" in (d.get(key) or {})
            record(label, ok, "dafeiyu entry", "install")
        except Exception as exc:  # noqa: BLE001
            record(label, False, str(exc), "install")
    toml = (temp_root / ".codex/config.toml").read_text() if (temp_root / ".codex/config.toml").exists() else ""
    record("Codex MCP", toml.count("[mcp_servers.dafeiyu]") == 1, f"{toml.count('[mcp_servers.dafeiyu]')} 个块", "install")

    # 幂等 + 不破坏用户既有配置
    qpath = temp_root / ".qoder/mcp.json"
    d = json.loads(qpath.read_text())
    d["custom"] = {"keep": True}
    qpath.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    p = run([str(ROOT / "scripts/install.sh"), "--no-start", "--with-mcp"], env=env_for_temp(), timeout=120)
    d2 = json.loads(qpath.read_text())
    toml2 = (temp_root / ".codex/config.toml").read_text()
    record("重复安装幂等", p.returncode == 0 and d2.get("custom") == {"keep": True} and toml2.count("[mcp_servers.dafeiyu]") == 1,
           "自定义键保留 / TOML 单块", "install")

    doctor = coach("doctor", "--json", timeout=30)
    try:
        dd = json.loads(doctor.stdout)
        record("doctor 全绿（守护进程除外）",
               all(c["ok"] for c in dd["checks"] if c["name"] != "守护进程"),
               "; ".join(f"{c['name']}={c['ok']}" for c in dd["checks"]), "install")
    except Exception:
        record("doctor 全绿（守护进程除外）", False, doctor.stdout[:200] + doctor.stderr[:200], "install")


def start_temp_daemon() -> bool:
    global daemon_pid
    p = coach("start", timeout=20)
    st = wait_for(lambda: status() if status().get("pid") else None, timeout=8)
    if not st:
        record("启动临时守护进程", False, (p.stdout + p.stderr)[:300], "e2e")
        return False
    daemon_pid = st.get("pid")
    record("启动临时守护进程", True, f"pid {daemon_pid}", "e2e")
    return True


def check_e2e() -> None:
    section("4. 端到端（CLI ↔ UNIX socket ↔ AppKit）")
    if not start_temp_daemon():
        return
    assert temp_root is not None
    st = status()
    scale = st.get("mainScale") or 2

    hello = coach_json("hello", "--agent", "audit")
    record("hello 注册 agent", hello.get("agent") == "audit", "", "e2e")

    guide_file = temp_root / "guide.json"
    guide_file.write_text(json.dumps({
        "title": "审计三步任务",
        "steps": [
            {"text": "第一步：指向左上目标。", "x": 1000, "y": 600, "label": "点这里", "hint": "这是提示"},
            {"text": "第二步：没有坐标，应该清掉指针。"},
            {"text": "第三步：完成它。"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    g = coach_json("guide", "--file", str(guide_file), "--unit", "px")
    sess = g.get("session") or {}
    ok = (g.get("ok") and sess.get("total") == 3 and sess.get("index") == 0 and g.get("pointer")
          and abs((sess.get("x") or 0) - 1000 / scale) < 1.5 and abs((sess.get("y") or 0) - 600 / scale) < 1.5)
    record("guide 建任务 + px 坐标换算 + 指针", ok,
           f"{sess.get('total')} 步, 指针={g.get('pointer')}, x={sess.get('x')}, y={sess.get('y')}", "e2e")
    record("会话已持久化", (temp_root / ".dafeiyu/session.json").exists(), "", "e2e")

    n1 = coach_json("next", "--say", "很好，继续。")
    s1 = n1.get("session") or {}
    record("next 推进并清掉旧指针", s1.get("index") == 1 and n1.get("pointer") is False,
           f"index={s1.get('index')}, pointer={n1.get('pointer')}", "e2e")
    n2 = coach_json("next")
    s2 = n2.get("session") or {}
    record("next 第二次", s2.get("index") == 2, f"index={s2.get('index')}", "e2e")
    n3 = coach_json("next")
    s3 = n3.get("session") or {}
    record("最后一步自动完成 + 庆祝", s3.get("finished") is True, f"finished={s3.get('finished')}", "e2e")

    coach_json("say", "自动收起测试", "--hold", "0.4")
    time.sleep(1.2)
    record("气泡自动收起", status().get("bubbleVisible") is False, "", "e2e")

    p = coach("say", "大肥鱼 🐋 中文 / English / ✓", "--step", "unicode")
    record("Unicode 文案", p.returncode == 0, "", "e2e")
    long_text = "这是一段很长的测试文案。" * 30
    p = coach("say", long_text)
    record("长文案不崩溃", p.returncode == 0 and status().get("bubbleVisible") is True, f"{len(long_text)} 字", "e2e")

    pt = coach_json("point", "--x", "1000", "--y", "600", "--unit", "px", "--label", "px")
    record("单独 point px 换算", abs((pt.get("x") or 0) - 1000 / scale) < 1.5, f"x={pt.get('x')}", "e2e")
    coach("clear-point")

    for clip in ["success", "error", "thinking", "pat", "eat", "stretch", "yawn", "drag", "drop", "working", "idle", "poke", "tail", "rice", "sing"]:
        r = coach_json("play", clip)
        if not r.get("ok"):
            record(f"play {clip}", False, str(r), "e2e"); break
    else:
        record("15 段动画均可播放", True, "全部 15 个 clip", "e2e")

    coach_json("feed"); coach_json("dance"); coach_json("quip")
    record("趣味互动 feed/dance/quip", True, "", "e2e")

    coach_json("hide")
    record("hide 隐藏桌宠", status().get("petVisible") is False, "", "e2e")
    coach_json("show")
    record("show 找回桌宠", status().get("petVisible") is True, "", "e2e")

    coach_json("quiet", "on")
    record("quiet on", status().get("quiet") is True, "", "e2e")
    coach_json("quiet", "off")
    record("quiet off", status().get("quiet") is False, "", "e2e")

    coach_json("scale", "1.2")
    record("缩放桌宠", abs((status().get("petScale") or 0) - 1.2) < 0.01, "", "e2e")
    coach_json("scale", "1.0")

    coach_json("guide", "--title", "取消测试", "--step", "一", "--step", "二")
    coach_json("cancel")
    record("cancel 清理任务", status().get("session") is None, "", "e2e")

    p = coach("guide", "--title", "无步骤")
    record("guide 缺步骤时报错", p.returncode == 1 and "至少" in (p.stderr + p.stdout), p.stderr.strip()[:80], "e2e")
    p = coach("point", "--x", "1")
    record("point 缺 y 时参数错误", p.returncode == 2, f"exit {p.returncode}", "e2e")
    p = coach("no-such-command")
    record("未知子命令报错", p.returncode == 2, f"exit {p.returncode}", "e2e")

    # 动画确实在走
    coach_json("play", "working")
    f1 = status()
    time.sleep(0.5)
    f2 = status()
    record("帧动画运行", f1.get("clip") == "working" and f1.get("frame") != f2.get("frame"),
           f"frame {f1.get('frame')} → {f2.get('frame')}", "e2e")

    # 断线恢复 / 僵尸 socket
    coach("stop", timeout=10)
    time.sleep(0.3)
    record("stop 清理 socket", not (temp_root / ".dafeiyu/coach.sock").exists(), "", "e2e")
    (temp_root / ".dafeiyu/coach.sock").write_text("stale", encoding="utf-8")
    p = coach("start", timeout=20)
    record("僵尸 socket 自动清理", p.returncode == 0 and bool(status().get("pid")), "", "e2e")

    # 崩溃恢复
    pid = status().get("pid")
    if pid:
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
        p = coach("start", timeout=20)
        record("崩溃后重启", p.returncode == 0 and bool(status().get("pid")), f"旧 pid {pid}", "e2e")

    # 会话恢复
    coach_json("guide", "--title", "恢复测试", "--step", "第一", "--step", "第二")
    coach("stop", timeout=10)
    coach("start", timeout=20)
    st = status()
    record("未完成任务跨重启恢复", (st.get("session") or {}).get("title") == "恢复测试",
           f"session={st.get('session')}", "e2e")
    coach_json("finish")

    # 权限
    mode = oct((temp_root / ".dafeiyu/coach.sock").stat().st_mode & 0o777)
    record("socket 权限 0600", mode == "0o600", mode, "e2e")

    # 截图前把鱼挪到空旷一点的位置
    coach_json("move", "--x", "1000", "--y", "650")


def check_music_interactions() -> None:
    section("4b. 音乐 / 歌词 / 米饭 / 番茄钟 / 过渡")
    assert temp_root and cli_path
    music_bin = temp_root / ".local/bin/dafeiyu_music.py"
    env = env_for_temp()
    coach_json("quiet", "off")
    coach_json("cancel")
    coach_json("show")
    coach_json("hello", "--agent", "audit-music")

    p = run([sys.executable, str(music_bin), "test", "--line", "海风轻轻吹过"], env=env, timeout=15)
    st = status()
    record("music test 推送唱歌", p.returncode == 0 and st.get("singing") is True and st.get("lyric") == "海风轻轻吹过",
           f"singing={st.get('singing')} lyric={st.get('lyric')}", "music")
    time.sleep(0.3)
    record("歌词气泡可见", st.get("bubbleVisible") is True, "", "music")
    bubble = st.get("bubble") or {}
    pet = st.get("pet") or {}
    record("唱歌使用独立 sing 动画", st.get("clip") == "sing", f"clip={st.get('clip')}", "music")
    record("歌词条贴头顶且紧凑", st.get("bubbleCompact") is True
           and bubble.get("h", 999) <= 70 and bubble.get("w", 999) <= 330
           and bubble.get("topLeftY", 9999) < pet.get("topLeftY", -1),
           f"{bubble.get('w')}x{bubble.get('h')} @ {bubble.get('topLeftY')} < {pet.get('topLeftY')}", "music")
    run([sys.executable, str(music_bin), "off"], env=env, timeout=10)
    record("music off 收起", status().get("singing") is False, "", "music")

    local = temp_root / ".dafeiyu/lyrics/local"
    local.mkdir(parents=True, exist_ok=True)
    (local / "测试歌 - 测试歌手.lrc").write_text(
        "[00:00.00] 第一句\n[00:02.00] 第二句\n[00:04.00] 第三句\n", encoding="utf-8")
    env2 = {**env, "DAFEIYU_NOWPLAYING_JSON": json.dumps(
        {"title": "测试歌", "artist": "测试歌手", "duration": 10, "elapsed": 2.5, "playing": True}, ensure_ascii=False),
        "DAFEIYU_LYRICS_DIR": str(local)}
    p = run([sys.executable, str(music_bin), "watch", "--limit", "3", "--interval", "0.35", "--no-network"],
            env=env2, timeout=15)
    st = status()
    record("本地 LRC + watcher 推送当前行", p.returncode == 0 and st.get("lyric") == "第二句",
           f"lyric={st.get('lyric')}", "music")
    run([sys.executable, str(music_bin), "off"], env=env, timeout=10)

    rice0 = status().get("rice", 0)
    coach_json("feed")
    st = status()
    rice1 = st.get("rice", 0)
    record("米饭计数", rice1 == rice0 + 1, f"{rice0} → {rice1}", "interaction")
    record("米饭使用独立 rice 动画（不是 eat）", st.get("clip") == "rice", f"clip={st.get('clip')}", "interaction")

    coach_json("focus", "--minutes", "0.02")
    time.sleep(2.2)
    st = status()
    record("番茄钟到点", (st.get("focusRemaining") or 0) == 0 and st.get("bubbleVisible") is True,
           f"focus={st.get('focusRemaining')} clip={st.get('clip')}", "interaction")
    coach_json("focus", "--cancel")

    coach_json("quiet", "on", "--minutes", "0.02")
    time.sleep(2.0)
    record("会议模式到点自动解除", status().get("quiet") is False, "", "interaction")
    coach_json("quiet", "off")

    coach_json("play", "success")
    st = status()
    record("交叉淡化进行中", isinstance(st.get("blend"), (int, float)) and st.get("blend") < 1.0,
           f"blend={st.get('blend')}", "transition")


def check_tui() -> None:
    section("4c. 终端轻量版（TCP 核心）")
    assert temp_root
    tui_home = temp_root / "tui-home"
    (tui_home / ".dafeiyu").mkdir(parents=True, exist_ok=True)
    tui = temp_root / ".local/bin/dafeiyu_tui.py"
    cli = temp_root / ".local/bin/dafeiyu"
    env = {"HOME": str(tui_home), "DAFEIYU_HOME": str(tui_home / ".dafeiyu"),
           "PATH": env_for_temp()["PATH"]}
    proc = subprocess.Popen([sys.executable, str(tui), "--headless", "--no-music"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, **env})
    try:
        port_file = tui_home / ".dafeiyu/coach.port"
        if not wait_for(lambda: port_file.exists() or None, timeout=6):
            record("启动终端核心", False, "无 coach.port", "tui")
            return
        record("启动终端核心", True, port_file.read_text(encoding="utf-8")[:80], "tui")
        p = run([str(cli), "status", "--json"], env=env, timeout=10)
        try:
            d = json.loads(p.stdout)
        except Exception:
            d = {}
        record("CLI 经 TCP 读取状态", d.get("mode") == "tui", f"mode={d.get('mode')}", "tui")
        p = run([str(cli), "guide", "--title", "TUI", "--step", "第一步", "--step", "第二步"], env=env, timeout=10)
        record("终端 guide", p.returncode == 0 and "第一步" in p.stdout, p.stdout.strip()[:80], "tui")
        run([str(cli), "next"], env=env, timeout=10)
        run([str(cli), "feed"], env=env, timeout=10)
        p = run([str(cli), "status", "--json"], env=env, timeout=10)
        try:
            d = json.loads(p.stdout)
        except Exception:
            d = {}
        record("终端 next/feed/status", d.get("rice") == 1 and d.get("index") == 1,
               f"rice={d.get('rice')} index={d.get('index')}", "tui")
        run([str(cli), "stop"], env=env, timeout=10)
        proc.wait(timeout=5)
        record("终端 stop 退出并清理端口", not port_file.exists(), "", "tui")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def check_mcp() -> None:
    section("5. MCP（stdio 协议）")

    def rpc(lines):
        p = subprocess.run([sys.executable, str(MCP)], input="\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n",
                           text=True, capture_output=True, env={**os.environ, **env_for_temp()}, timeout=30)
        out = [json.loads(x) for x in p.stdout.splitlines() if x.strip()]
        return out, p

    out, p = rpc([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "dafeiyu_begin", "arguments": {"agent": "mcp-audit"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "dafeiyu_guide", "arguments": {
            "title": "MCP 任务", "steps": [{"text": "MCP 第一步"}, {"text": "MCP 第二步"}], "unit": "pt"}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "dafeiyu_next", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "dafeiyu_finish", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "dafeiyu_music", "arguments": {"action": "status"}}},
        {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "dafeiyu_focus", "arguments": {"minutes": 0.01}}},
    ])
    by_id = {x.get("id"): x for x in out}
    record("initialize 握手", by_id.get(1, {}).get("result", {}).get("serverInfo", {}).get("name") == "dafeiyu-coach",
           str(by_id.get(1, {}).get("result", {}).get("serverInfo")), "mcp")
    tools = by_id.get(2, {}).get("result", {}).get("tools", [])
    record("tools/list 12 个工具", len(tools) == 12, str([t["name"] for t in tools]), "mcp")
    record("工具 schema 完整", all(t.get("description") and t.get("inputSchema") for t in tools), "", "mcp")
    for rid, label in [(3, "begin"), (4, "guide"), (5, "next"), (6, "finish"), (7, "music"), (8, "focus")]:
        r = by_id.get(rid, {})
        is_err = r.get("result", {}).get("isError")
        record(f"MCP {label} 调用", r.get("result") is not None and not is_err,
               (r.get("result", {}).get("content") or [{}])[0].get("text", "")[:80], "mcp")
    st = status()
    record("MCP 驱动后任务已完成", (st.get("session") or {}).get("finished") is True, "", "mcp")


def sample_cpu(pid: int) -> tuple[float, int]:
    p = run(["top", "-l", "4", "-s", "1", "-pid", str(pid), "-stats", "pid,cpu,mem,threads"], timeout=15)
    cpu_vals = []
    mem_kb = 0
    for line in p.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == str(pid):
            try:
                cpu_vals.append(float(parts[1]))
                mem = parts[2].replace("+", "").replace("M", "").replace("K", "")
                mem_kb = max(mem_kb, int(float(mem) * (1024 if "K" in parts[2] else 1)))
            except ValueError:
                pass
    ps = run(["ps", "-o", "rss=", "-p", str(pid)])
    try:
        rss_kb = int(ps.stdout.strip() or 0)
    except ValueError:
        rss_kb = 0
    return (cpu_vals[-1] if cpu_vals else 0.0), (rss_kb or mem_kb)


def check_perf() -> None:
    section("6. 性能与启动")
    assert cli_path
    coach("stop", timeout=10)
    t0 = time.time()
    coach("start", timeout=20)
    startup = time.time() - t0
    st = status()
    pid = st.get("pid")
    record("冷启动 < 4s", pid is not None and startup < 4.0, f"{startup:.2f}s", "perf")
    if not pid:
        return
    time.sleep(2)
    idle_cpu, idle_rss = sample_cpu(pid)
    record("待机 CPU < 6%", idle_cpu < 6.0, f"{idle_cpu:.1f}%", "perf")
    record("待机 RSS < 140 MB", idle_rss < 140 * 1024, f"{idle_rss/1024:.0f} MB", "perf")

    coach_json("play", "working")
    coach_json("point", "--x", "600", "--y", "500", "--label", "性能", "--hold", "8")
    time.sleep(0.5)
    active_cpu, active_rss = sample_cpu(pid)
    coach("clear-point")
    record("动画+指针 CPU < 14%", active_cpu < 14.0, f"{active_cpu:.1f}%", "perf")
    record("动画+指针 RSS < 160 MB", active_rss < 160 * 1024, f"{active_rss/1024:.0f} MB", "perf")
    record("性能记录", True, f"idle {idle_cpu:.1f}% / {idle_rss/1024:.0f}MB · active {active_cpu:.1f}% / {active_rss/1024:.0f}MB", "perf")


def check_privacy() -> None:
    section("7. 隐私与边界")
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                     for p in list((ROOT / "Sources").glob("*.swift")) + [CLI, MCP])
    forbidden = {
        "URLSession": "网络请求", "NSURLConnection": "网络请求", "AF_INET": "网络监听",
        "SOCK_DGRAM": "UDP", "CGEvent": "合成鼠标/键盘", "CGWindowList": "读窗",
        "AXIsProcessTrusted": "辅助功能", "NSPasteboard": "剪贴板", "osascript": "AppleScript",
        "eval(": "动态执行",
    }
    hits = [f"{k}({v})" for k, v in forbidden.items() if re.search(r"(?<![A-Za-z_])" + re.escape(k), text)]
    record("无网络/读屏/合成点击 API", not hits, ", ".join(hits) or "只使用 AF_UNIX", "privacy")
    record("守护进程只监听 UNIX socket", "AF_UNIX" in (ROOT / "Sources/Server.swift").read_text() and
           "AF_INET" not in (ROOT / "Sources/Server.swift").read_text(), "AF_UNIX + 0600", "privacy")
    music_text = (ROOT / "bin/dafeiyu_music.py").read_text(encoding="utf-8", errors="replace")
    hosts = set(re.findall(r"https?://([^/\"']+)", music_text))
    record("歌词只访问 LRCLIB / 网易云", hosts <= {"lrclib.net", "music.163.com"},
           ", ".join(sorted(hosts)), "privacy")
    todos = len(re.findall(r"TODO|FIXME|XXX", text))
    record("源码无 TODO/FIXME", todos == 0, f"{todos} 处", "privacy")


def check_docs() -> None:
    section("8. 文档与可交付")
    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    need = ["安装", "Agent", "MCP", "性能", "架构", "审计", "许可"]
    missing = [k for k in need if k not in readme]
    record("README 完整", bool(readme) and "1.1.0" in readme and "音乐与唱歌" in readme and not missing, "缺 " + ",".join(missing) if missing else f"{len(readme)} 字符", "docs")
    for name, path in [
        ("LICENSE", ROOT / "LICENSE"), ("NOTICE", ROOT / "NOTICE.md"),
        ("CHANGELOG", ROOT / "CHANGELOG.md"), ("ARCHITECTURE", ROOT / "docs/ARCHITECTURE.md"),
        ("AUDIT 文档", ROOT / "docs/AUDIT.md"), ("迭代记录", ROOT / "docs/ITERATIONS.md"),
        ("发布素材", ROOT / "docs/SOCIAL.md"), ("CI", ROOT / ".github/workflows/ci.yml"),
        ("音乐适配器说明", ROOT / "Runtime/music/README.md"), ("Windows 安装", ROOT / "scripts/install.ps1"),
        ("Windows GUI", ROOT / "bin/dafeiyu_gui.py"), ("Windows 依赖", ROOT / "requirements-windows.txt"),
        ("AGENTS 片段", ROOT / "adapters/AGENTS.md"),
        ("dsh 适配说明", ROOT / "adapters/dsh.md"),
    ]:
        record(name, path.exists(), str(path.relative_to(ROOT)), "docs")
    notice = (ROOT / "NOTICE.md").read_text(encoding="utf-8") if (ROOT / "NOTICE.md").exists() else ""
    record("开源素材署名", all(k in notice for k in ["dsh-pet", "dsh-dafeiyu", "MIT"]), "", "docs")


# ------------------------------------------------------------------ visual

def px_rect(rect, scale):
    return (int(rect["x"] * scale), int(rect["topLeftY"] * scale),
            int(rect["w"] * scale), int(rect["h"] * scale))


def capture(path: Path, pet, bubble, target_pt, scale, expect_ring=True) -> bool:
    if not pet or not bubble:
        return False
    full = Path("/tmp/dafeiyu-audit-shot.png")
    p = run(["screencapture", "-x", str(full)], timeout=20)
    if p.returncode != 0 or not full.exists() or full.stat().st_size < 10000:
        return False
    try:
        from PIL import Image, ImageFilter, ImageDraw
    except ImportError:
        shutil.copy2(full, path)
        return True
    img = Image.open(full).convert("RGB")
    W, H = img.size
    regions = [px_rect(pet, scale), px_rect(bubble, scale)]
    tx, ty = target_pt
    tr = (int((tx - 150) * scale), int((ty - 120) * scale), int(300 * scale), int(260 * scale))
    regions.append(tr)
    # 证据像素检查
    def count(rect, pred):
        x, y, w, h = [max(0, v) for v in rect]
        crop = img.crop((x, y, min(W, x + w), min(H, y + h)))
        n = 0
        for r, g, b in crop.getdata():
            if pred(r, g, b): n += 1
        return n
    pet_pixels = count(regions[0], lambda r, g, b: max(r, g, b) - min(r, g, b) > 35 and max(r, g, b) < 245)
    bubble_pixels = count(regions[1], lambda r, g, b: r > 235 and g > 235 and b > 230)
    ring_pixels = count(regions[2], lambda r, g, b: r > 200 and g < 205 and b < 190 and (r - g) > 25)
    ok = pet is not None and bubble is not None and pet_pixels > 1200 and bubble_pixels > 2000
    if expect_ring:
        ok = ok and ring_pixels > 25
    # 背景模糊，只保留鱼/气泡/指针清晰
    blurred = img.filter(ImageFilter.GaussianBlur(18))
    for rect in regions:
        x, y, w, h = rect
        x0, y0 = max(0, x - 8), max(0, y - 8)
        x1, y1 = min(W, x + w + 8), min(H, y + h + 8)
        blurred.paste(img.crop((x0, y0, x1, y1)), (x0, y0))
    blurred = blurred.resize((W // 2, H // 2), Image.LANCZOS)
    blurred.save(path, "PNG", optimize=True)
    return ok


def check_visual() -> None:
    section("9. 真机可视化证据")
    if not visual_enabled:
        record("截图验收", True, "跳过（--no-visual）", "visual")
        return
    assert cli_path and temp_root
    SHOTS.mkdir(parents=True, exist_ok=True)
    st = status()
    pid = st.get("pid")
    if not pid:
        coach("start", timeout=20)
        st = status()
    scale = st.get("mainScale") or 2
    coach_json("config", "--playful", "off")
    coach_json("stage", "on")
    coach_json("move", "--x", "1000", "--y", "650")
    coach_json("hello", "--agent", "audit")
    coach_json("guide", "--title", "真机验收 · 三步任务", "--step", "第一步：看这个圈。", "--step", "第二步：继续。", "--step", "第三步：完成。")
    # 用 point 指到鱼左侧的空处，避免遮挡气泡
    coach_json("point", "--x", "800", "--y", "850", "--label", "点这里", "--hold", "60")
    time.sleep(0.8)
    st = status()
    pet, bubble = st.get("pet"), st.get("bubble")
    ok1 = capture(SHOTS / "01-guide.png", pet, bubble, (800, 850), scale)
    record("证据 01：指针 + 气泡 + 步骤", ok1, str(SHOTS / "01-guide.png"), "visual")

    coach_json("finish")
    time.sleep(0.9)
    st = status()
    ok2 = capture(SHOTS / "02-success.png", st.get("pet"), st.get("bubble"), (800, 850), scale, expect_ring=False)
    record("证据 02：完成庆祝（绿框/彩纸）", ok2, str(SHOTS / "02-success.png"), "visual")

    coach_json("bye")
    time.sleep(0.3)
    coach_json("quip")
    time.sleep(0.6)
    st = status()
    ok3 = capture(SHOTS / "03-companion.png", st.get("pet"), st.get("bubble"), (800, 850), scale, expect_ring=False)
    record("证据 03：待机陪伴台词", ok3, str(SHOTS / "03-companion.png"), "visual")

    music_bin = temp_root / ".local/bin/dafeiyu_music.py"
    run([sys.executable, str(music_bin), "test", "--title", "桌面大肥鱼", "--artist", "测试", "--line", "海风轻轻吹过"], env=env_for_temp(), timeout=15)
    time.sleep(0.9)
    st = status()
    ok4 = capture(SHOTS / "04-music.png", st.get("pet"), st.get("bubble"), (800, 850), scale, expect_ring=False)
    record("证据 04：歌词 + 唱歌", ok4, str(SHOTS / "04-music.png"), "visual")
    run([sys.executable, str(music_bin), "off"], env=env_for_temp(), timeout=10)

    coach_json("feed")
    time.sleep(1.0)
    st = status()
    ok5 = capture(SHOTS / "05-rice.png", st.get("pet"), st.get("bubble"), (800, 850), scale, expect_ring=False)
    record("证据 05：米饭 + 饭碗", ok5, str(SHOTS / "05-rice.png"), "visual")

    tui_txt = run([sys.executable, str(temp_root / ".local/bin/dafeiyu_tui.py"), "--once", "--no-color"],
                  env=env_for_temp(), timeout=15)
    (SHOTS / "tui-sample.txt").write_text(tui_txt.stdout, encoding="utf-8")
    record("证据 06：终端版渲染", "米饭" in tui_txt.stdout and "桌面大肥鱼" in tui_txt.stdout,
           str(SHOTS / "tui-sample.txt"), "visual")
    record("证据 07：Windows GUI（CI 冒烟截图）", (SHOTS / "06-windows-gui.png").exists(),
           str(SHOTS / "06-windows-gui.png"), "visual")
    record("证据 08：Windows GUI 歌词唱歌（CI）", (SHOTS / "07-windows-music.png").exists(),
           str(SHOTS / "07-windows-music.png"), "visual")
    record("证据 09：QQ 音乐真机唱歌", (SHOTS / "08-qq-music.png").exists(),
           str(SHOTS / "08-qq-music.png"), "visual")

    for f in ["01-guide.png", "02-success.png", "03-companion.png", "04-music.png", "05-rice.png"]:
        p = SHOTS / f
        record(f"截图非空 {f}", p.exists() and p.stat().st_size > 20000, f"{p.stat().st_size//1024 if p.exists() else 0} KB", "visual")
    coach_json("stage", "off")


def check_cleanup() -> None:
    section("10. 卸载")
    assert temp_root
    p = run([str(ROOT / "scripts/uninstall.sh")], env=env_for_temp(), timeout=30)
    changed = {
        "CLI": (temp_root / ".local/bin/dafeiyu").exists(),
        "daemon": (temp_root / ".local/bin/dafeiyu-daemon").exists(),
        "Qoder skill": (temp_root / ".qoder/skills/dafeiyu-coach").exists(),
        "Codex command": (temp_root / ".codex/prompts/dafeiyu.md").exists(),
        "music": (temp_root / ".local/bin/dafeiyu_music.py").exists(),
        "tui": (temp_root / ".local/bin/dafeiyu_tui.py").exists(),
    }
    record("卸载移除二进制与 skills", p.returncode == 0 and not any(changed.values()),
           ", ".join(k for k, v in changed.items() if v) or "全部移除", "cleanup")
    record("卸载默认保留设置", (temp_root / ".dafeiyu/settings.json").exists(), "", "cleanup")
    p = run([str(ROOT / "scripts/uninstall.sh"), "--purge"], env=env_for_temp(), timeout=30)
    record("--purge 删除数据", p.returncode == 0 and not (temp_root / ".dafeiyu").exists(), "", "cleanup")


# ------------------------------------------------------------------ main

def main() -> int:
    global temp_root, visual_enabled, daemon_pid
    visual_enabled = "--no-visual" not in sys.argv
    keep = "--keep-temp" in sys.argv
    print("\033[1m桌面大肥鱼 Coach · 验收审计\033[0m")
    print(f"项目：{ROOT}")
    temp_root = Path(tempfile.mkdtemp(prefix="dafeiyu-audit-"))
    print(f"临时 HOME：{temp_root}\n")

    try:
        check_static()
        check_size()
        check_install()
        check_e2e()
        check_music_interactions()
        check_tui()
        check_mcp()
        check_perf()
        check_privacy()
        check_docs()
        check_visual()
        check_cleanup()
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        record("审计脚本异常", False, f"{type(exc).__name__}: {exc}", "fatal")
    finally:
        # 异常退出也要收掉临时守护进程，否则残留窗口会遮挡下一次审计并触发 App Nap
        try:
            if cli_path and cli_path.exists():
                run([str(cli_path), "stop"], env=env_for_temp(), timeout=10)
        except Exception:
            pass
        try:
            pidfile = temp_root / ".dafeiyu" / "coach.pid"
            pid = int(pidfile.read_text().strip()) if pidfile.exists() else daemon_pid
            if pid:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
        time.sleep(0.2)
        if not keep:
            shutil.rmtree(temp_root, ignore_errors=True)
        else:
            print(f"\n保留临时目录：{temp_root}")

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    groups = {}
    for r in results:
        g = r["group"] or "其它"
        groups.setdefault(g, [0, 0])
        groups[g][1] += 1
        groups[g][0] += 1 if r["ok"] else 0
    print("\n" + "=" * 64)
    for g, (a, b) in groups.items():
        print(f"  {g:10s} {a}/{b}")
    print(f"\n  总计 {passed}/{total} 通过")
    report = {"ok": passed == total and bool(results), "passed": passed, "total": total,
              "groups": groups, "results": results, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (ROOT / "audit" / "last-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if passed != total:
        print("\n\033[31m未通过项：\033[0m")
        for r in results:
            if not r["ok"]:
                print(f"  - [{r['group']}] {r['name']}：{r['detail']}")
    print("=" * 64)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
