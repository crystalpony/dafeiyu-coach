#!/usr/bin/env bash
# 安装桌面大肥鱼 Coach：二进制 + 动画素材 + 四套 Agent skills（可选 MCP 配置）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
DATA="${DAFEIYU_HOME:-$HOME/.dafeiyu}"
BIN="$PREFIX/bin"
DO_BUILD=0
WITH_MCP=0
DO_START=1
NO_MUSIC=0
for arg in "$@"; do
  case "$arg" in
    --build) DO_BUILD=1 ;;
    --with-mcp) WITH_MCP=1 ;;
    --no-start) DO_START=0 ;;
    --no-music) NO_MUSIC=1 ;;
    --no-mcp) WITH_MCP=0 ;;
    -h|--help)
      sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

say() { printf '\033[36m▸\033[0m %s\n' "$*"; }

if [[ ! -f "$ROOT/Runtime/clips/manifest.json" ]]; then
  echo "缺少 Runtime/clips；先运行 python3 scripts/build_assets.py" >&2
  exit 2
fi
if [[ $DO_BUILD -eq 1 || ! -x "$ROOT/.build/dafeiyu-daemon" ]]; then
  say "编译守护进程"
  "$ROOT/scripts/build.sh"
fi

say "安装到 $BIN"
mkdir -p "$BIN" "$DATA"
install -m 0755 "$ROOT/.build/dafeiyu-daemon" "$BIN/dafeiyu-daemon"
install -m 0755 "$ROOT/bin/dafeiyu" "$BIN/dafeiyu"
install -m 0755 "$ROOT/bin/dafeiyu_mcp.py" "$BIN/dafeiyu_mcp.py"
install -m 0755 "$ROOT/bin/dafeiyu_music.py" "$BIN/dafeiyu_music.py"
install -m 0755 "$ROOT/bin/dafeiyu_tui.py" "$BIN/dafeiyu_tui.py"
install -m 0755 "$ROOT/bin/dafeiyu_gui.py" "$BIN/dafeiyu_gui.py"

say "安装动画素材到 $DATA/clips"
mkdir -p "$DATA/clips"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "$ROOT/Runtime/clips/" "$DATA/clips/"
else
  rm -rf "$DATA/clips"; cp -R "$ROOT/Runtime/clips" "$DATA/clips"
fi

if [[ -d "$ROOT/Runtime/characters" ]]; then
  say "安装可选形象（小黑）"
  mkdir -p "$DATA/characters"
  for d in "$ROOT"/Runtime/characters/*/; do
    [[ -f "$d/manifest.json" ]] || continue
    name="$(basename "$d")"
    mkdir -p "$DATA/characters/$name"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete "$d" "$DATA/characters/$name/"
    else
      rm -rf "$DATA/characters/$name"; cp -R "$d" "$DATA/characters/$name"
    fi
  done
  python3 "$ROOT/scripts/prune_characters.py" "$DATA/characters" >/dev/null 2>&1 || true
fi

if [[ -d "$ROOT/Runtime/sounds" ]]; then
  say "安装喵叫音效"
  mkdir -p "$DATA/sounds"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$ROOT/Runtime/sounds/" "$DATA/sounds/"
  else
    rm -rf "$DATA/sounds"; cp -R "$ROOT/Runtime/sounds" "$DATA/sounds"
  fi
fi

if [[ -d "$ROOT/Runtime/music" ]]; then
  say "安装音乐检测适配器"
  mkdir -p "$DATA/music"
  rsync -a --delete "$ROOT/Runtime/music/" "$DATA/music/" 2>/dev/null || { rm -rf "$DATA/music"; cp -R "$ROOT/Runtime/music" "$DATA/music"; }
fi

SKILLS=()
say "安装 skills"
for target in \
  "$HOME/.qoder/skills/dafeiyu-coach" \
  "$HOME/.claude/skills/dafeiyu-coach" \
  "$HOME/.codex/skills/dafeiyu-coach" \
  "$HOME/.dsh/skills/dafeiyu-coach"; do
  mkdir -p "$target"
  install -m 0644 "$ROOT/skills/dafeiyu-coach/SKILL.md" "$target/SKILL.md"
  SKILLS+=("$target/SKILL.md")
done

say "安装 /dafeiyu 斜杠命令"
for target in \
  "$HOME/.qoder/commands/dafeiyu.md" \
  "$HOME/.claude/commands/dafeiyu.md" \
  "$HOME/.codex/prompts/dafeiyu.md"; do
  mkdir -p "$(dirname "$target")"
  install -m 0644 "$ROOT/adapters/commands/dafeiyu.md" "$target"
done

if [[ $WITH_MCP -eq 1 ]]; then
  say "写入 MCP 配置（会先备份）"
  PYBIN="$(command -v python3 || true)"
  if [[ -z "$PYBIN" ]]; then echo "缺少 python3，跳过 MCP 配置" >&2; else
    DAFEIYU_BIN="$BIN/dafeiyu" "$PYBIN" - "$HOME" <<'PY'
import json, os, sys, time
from pathlib import Path
home = Path(sys.argv[1]); exe = os.environ["DAFEIYU_BIN"]; ts = time.strftime("%Y%m%d-%H%M%S")
entry = {"command": exe, "args": ["mcp"]}

def merge_json(path, top):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if path.exists():
        try: data = json.loads(path.read_text(encoding="utf-8"))
        except Exception: data = {}
        path.with_name(path.name + f".bak-{ts}").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    servers = data.setdefault(top, {})
    if not isinstance(servers, dict): servers = {}; data[top] = servers
    servers["dafeiyu"] = entry
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  更新 {path}")

merge_json(home / ".qoder" / "mcp.json", "mcpServers")
merge_json(home / ".claude.json", "mcpServers")

codex = home / ".codex" / "config.toml"
codex.parent.mkdir(parents=True, exist_ok=True)
text = codex.read_text(encoding="utf-8") if codex.exists() else ""
block = f'\n# >>> dafeiyu-coach >>>\n[mcp_servers.dafeiyu]\ncommand = "{exe}"\nargs = ["mcp"]\n# <<< dafeiyu-coach <<<\n'
if "[mcp_servers.dafeiyu]" not in text:
    if codex.exists(): codex.with_name(codex.name + f".bak-{ts}").write_text(text, encoding="utf-8")
    codex.write_text(text + block, encoding="utf-8")
    print(f"  更新 {codex}")
PY
  fi
fi

DAFEIYU_BIN="$BIN/dafeiyu" DAFEIYU_HOME="$DATA" HOME="$HOME" python3 - "$DATA" "$BIN" "${SKILLS[@]}" <<'PY'
import json, os, sys, time
data = {"version": "1.4.0", "installedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "bin": os.environ["DAFEIYU_BIN"], "data": sys.argv[1],
        "skills": sys.argv[3:], "mcp": "see qoder/claude/codex configs"}
Path = __import__("pathlib").Path
Path(sys.argv[1], "install.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

if [[ $DO_START -eq 1 ]]; then
  say "启动大肥鱼"
  # 升级安装时先停旧进程，确保刚复制的新二进制/新 watcher 真正生效
  DAFEIYU_HOME="$DATA" "$BIN/dafeiyu" music off >/dev/null 2>&1 || true
  DAFEIYU_HOME="$DATA" "$BIN/dafeiyu" stop >/dev/null 2>&1 || true
  DAFEIYU_HOME="$DATA" "$BIN/dafeiyu" start || true
  if [[ $NO_MUSIC -eq 0 ]]; then
    DAFEIYU_HOME="$DATA" "$BIN/dafeiyu" music on || true
  fi
fi

echo
echo "完成。"
echo "  命令：$BIN/dafeiyu"
case ":$PATH:" in
  *":$BIN:"*) : ;;
  *) echo "  提示：把 $BIN 加进 PATH，之后可直接运行 dafeiyu" ;;
esac
echo "  试试：dafeiyu hello --agent qoder && dafeiyu demo"
echo "  MCP：dafeiyu mcp（未写入配置时加 --with-mcp 重跑安装）"
echo "  卸载：$ROOT/scripts/uninstall.sh（--purge 连数据一起删）"
