#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal stdio MCP server for 桌面大肥鱼 Coach.

Exposes the coaching controls as MCP tools so any MCP-capable agent (Qoder,
Codex, Claude Code, Cursor, dsh, …) can drive the fish without shell parsing.

Configure:
    {"mcpServers": {"dafeiyu": {"command": "dafeiyu", "args": ["mcp"]}}}
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
CLI_PATH = os.path.join(HERE, "dafeiyu")


def _load_cli():
    spec = importlib.util.spec_from_loader(
        "dafeiyu_cli", importlib.machinery.SourceFileLoader("dafeiyu_cli", CLI_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cli = _load_cli()

TOOLS = [
    {
        "name": "dafeiyu_begin",
        "description": "让桌面大肥鱼出现并与当前 Agent 打招呼。开始任何屏幕指导前先调用一次。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "调用方名称，如 qoder / codex / dsh / claude"},
            },
        },
    },
    {
        "name": "dafeiyu_guide",
        "description": "开始一个分步任务。大肥鱼会用气泡显示每一步；如果某步带 x/y，还会在主屏幕上画指针圈并在桌宠与目标之间拉虚线。步骤要短、可执行。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "任务名，例如「在 GarageBand 里做一段 EP」"},
                "steps": {
                    "type": "array",
                    "description": "步骤列表，按执行顺序",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "这一步要对用户说的话（尽量 60 字内）"},
                            "hint": {"type": "string", "description": "可选提示，显示在正文下一行"},
                            "x": {"type": "number", "description": "目标点 x（默认主屏左上角原点，单位见 unit）"},
                            "y": {"type": "number", "description": "目标点 y"},
                            "label": {"type": "string", "description": "指针旁的小标签，如「点这个轨道」"},
                        },
                        "required": ["text"],
                    },
                },
                "unit": {"type": "string", "enum": ["pt", "px", "norm"], "description": "坐标单位：pt 屏幕点；px Retina 截图像素；norm 0~1 归一化"},
                "start": {"type": "integer", "description": "从第几项开始，0 起，默认 0"},
            },
            "required": ["title", "steps"],
        },
    },
    {
        "name": "dafeiyu_next",
        "description": "完成当前步骤并进入下一步。最后一步会自动触发撒花庆祝。",
        "inputSchema": {
            "type": "object",
            "properties": {"say": {"type": "string", "description": "进入下一步时显示的自定义台词（可选）"}},
        },
    },
    {
        "name": "dafeiyu_point",
        "description": "只画指针圈和标签，不改变气泡文字。适合配合 dafeiyu_say 使用。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "unit": {"type": "string", "enum": ["pt", "px", "norm"]},
                "label": {"type": "string"},
                "hold": {"type": "number", "description": "秒数，0 表示保留到下一次命令"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "dafeiyu_say",
        "description": "让大肥鱼说一句话，可带步骤徽章、情绪和动画。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "title": {"type": "string"},
                "step": {"type": "string", "description": "徽章，如 2/5"},
                "hold": {"type": "number", "description": "自动收起秒数；0/省略为常驻"},
                "tone": {"type": "string", "enum": ["coach", "success", "error", "thinking"]},
                "anim": {"type": "string", "description": "idle/thinking/working/success/error/pat/poke/tail/eat/stretch/yawn"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "dafeiyu_play",
        "description": "播放一段动画：thinking 思考、working 工作、success 庆祝、error 出错、pat 开心、eat 吃东西、yawn 困了等。",
        "inputSchema": {
            "type": "object",
            "properties": {"clip": {"type": "string"}},
            "required": ["clip"],
        },
    },
    {
        "name": "dafeiyu_status",
        "description": "读取当前任务、步骤进度、桌宠/气泡可见性。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "dafeiyu_finish",
        "description": "立即完成整个任务并庆祝。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "dafeiyu_end",
        "description": "结束指导，让大肥鱼回到待机陪伴（不退出进程）。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "dafeiyu_music",
        "description": "音乐状态 / 开关歌词监听 / 测试唱歌。当前歌曲来自系统 Now Playing（Apple Music、网易云、QQ 音乐等）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["status", "on", "off", "test"]},
                "line": {"type": "string", "description": "test 时唱的一句"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "dafeiyu_focus",
        "description": "番茄钟：专注 N 分钟后让大肥鱼提醒休息；cancel 取消。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "minutes": {"type": "number", "description": "默认 25 分钟；测试可传小数"},
                "cancel": {"type": "boolean"},
            },
        },
    },
    {
        "name": "dafeiyu_feed",
        "description": "投喂一条小鱼干（趣味互动，会播放吃东西动画和爱心）。",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _text_result(obj, is_error: bool = False):
    return {
        "content": [{"type": "text", "text": json.dumps(obj, ensure_ascii=False)}],
        "isError": is_error,
    }


def _coerce_steps(steps, unit):
    out = []
    for s in steps or []:
        if not isinstance(s, dict) or not s.get("text"):
            raise cli.CoachError("每个 step 都需要 text")
        item = {"text": s["text"]}
        if s.get("hint"):
            item["hint"] = s["hint"]
        if s.get("label"):
            item["label"] = s["label"]
        if s.get("x") is not None and s.get("y") is not None:
            x, y = cli.convert(float(s["x"]), float(s["y"]), unit)
            item["x"], item["y"] = x, y
        out.append(item)
    if not out:
        raise cli.CoachError("steps 不能为空")
    return out


def call_tool(name, args):
    args = args or {}
    if name == "dafeiyu_begin":
        return cli.call({"cmd": "hello", "agent": args.get("agent") or os.environ.get("DAFEIYU_AGENT", "mcp")})
    if name == "dafeiyu_guide":
        steps = _coerce_steps(args.get("steps"), args.get("unit") or "pt")
        payload = {
            "cmd": "guide",
            "title": args.get("title") or "",
            "steps": steps,
            "start": max(0, int(args.get("start") or 0)),
            "agent": os.environ.get("DAFEIYU_AGENT", "mcp"),
        }
        return cli.call(payload)
    if name == "dafeiyu_next":
        p = {"cmd": "next"}
        if args.get("say"):
            p["say"] = args["say"]
        return cli.call(p)
    if name == "dafeiyu_point":
        x, y = cli.convert(float(args["x"]), float(args["y"]), args.get("unit") or "pt")
        p = {"cmd": "point", "x": x, "y": y, "unit": "pt"}
        for k in ("label", "hold", "tone"):
            if args.get(k) is not None:
                p[k] = args[k]
        return cli.call(p)
    if name == "dafeiyu_say":
        p = {"cmd": "say", "text": args.get("text", "")}
        for k in ("title", "step", "hold", "tone", "anim"):
            if args.get(k) is not None:
                p[k] = args[k]
        if not p["text"]:
            raise cli.CoachError("text 不能为空")
        return cli.call(p)
    if name == "dafeiyu_play":
        return cli.call({"cmd": "play", "clip": args.get("clip", "idle")})
    if name == "dafeiyu_status":
        st = cli.ping()
        if not st:
            return {"ok": True, "running": False}
        return cli.call({"cmd": "status"}, auto_start=False)
    if name == "dafeiyu_finish":
        return cli.call({"cmd": "finish"})
    if name == "dafeiyu_end":
        return cli.call({"cmd": "bye"})
    if name == "dafeiyu_music":
        action = args.get("action") or "status"
        if action == "status":
            return cli.call({"cmd": "music_status"})
        target = Path(cli.__file__).resolve().parent / "dafeiyu_music.py"
        if not target.exists():
            raise cli.CoachError("找不到 dafeiyu_music.py")
        cmd = [sys.executable, str(target)]
        if action == "test":
            cmd.append("test")
            if args.get("line"):
                cmd += ["--line", args["line"]]
        else:
            cmd.append(action)
        p = subprocess.run(cmd, capture_output=True, text=True,
                           env={**os.environ, "DAFEIYU_HOME": str(cli.HOME)})
        return {"ok": p.returncode == 0, "output": (p.stdout or p.stderr).strip()[-800:]}
    if name == "dafeiyu_focus":
        payload = {"cmd": "focus"}
        if args.get("minutes") is not None:
            payload["minutes"] = args["minutes"]
        if args.get("cancel"):
            payload["cancel"] = True
        return cli.call(payload)
    if name == "dafeiyu_feed":
        return cli.call({"cmd": "feed"})
    raise cli.CoachError(f"未知工具：{name}")


def handle(req):
    method = req.get("method")
    rid = req.get("id")
    params = req.get("params") or {}
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": params.get("protocolVersion") or "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "dafeiyu-coach", "version": cli.VERSION},
                "instructions": "桌面大肥鱼 Coach：先用 dafeiyu_begin，再用 dafeiyu_guide 立任务；每完成一步调用 dafeiyu_next。指针坐标默认是主屏左上角原点 pt，也可用 px/norm。",
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        try:
            result = call_tool(name, params.get("arguments"))
            return {"jsonrpc": "2.0", "id": rid, "result": _text_result(result)}
        except Exception as exc:  # noqa: BLE001
            return {"jsonrpc": "2.0", "id": rid, "result": _text_result({"ok": False, "error": str(exc)}, True)}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"resources": []}}
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"prompts": []}}
    if method == "shutdown":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method and method.startswith("notifications/"):
        return None
    if rid is None:
        return None
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}), flush=True)
            continue
        resp = handle(req)
        if resp is not None:
            print(json.dumps(resp, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
