#!/usr/bin/env bash
# 卸载桌面大肥鱼 Coach。默认保留设置/会话；--purge 连数据一起删。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
DATA="${DAFEIYU_HOME:-$HOME/.dafeiyu}"
BIN="$PREFIX/bin"
PURGE=0
for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

if [[ -x "$BIN/dafeiyu" ]]; then
  DAFEIYU_HOME="$DATA" "$BIN/dafeiyu" music off >/dev/null 2>&1 || true
  DAFEIYU_HOME="$DATA" "$BIN/dafeiyu" stop >/dev/null 2>&1 || true
fi
if [[ -f "$DATA/music.pid" ]]; then
  kill "$(cat "$DATA/music.pid")" >/dev/null 2>&1 || true
fi
rm -f "$BIN/dafeiyu" "$BIN/dafeiyu-daemon" "$BIN/dafeiyu_mcp.py" "$BIN/dafeiyu_music.py" "$BIN/dafeiyu_tui.py"
rm -f "$DATA/coach.port" "$DATA/music.pid"
for target in \
  "$HOME/.qoder/skills/dafeiyu-coach" \
  "$HOME/.claude/skills/dafeiyu-coach" \
  "$HOME/.codex/skills/dafeiyu-coach" \
  "$HOME/.dsh/skills/dafeiyu-coach"; do
  rm -rf "$target"
done
rm -f "$HOME/.qoder/commands/dafeiyu.md" "$HOME/.claude/commands/dafeiyu.md" "$HOME/.codex/prompts/dafeiyu.md"
rm -f "$DATA/install.json" "$DATA/coach.sock" "$DATA/coach.pid"
if [[ $PURGE -eq 1 ]]; then
  rm -rf "$DATA"
  echo "已卸载，并删除 $DATA"
else
  echo "已卸载。设置与会话保留在 ${DATA}（--purge 可一并删除）"
fi
echo "提示：MCP 配置（如有）需手动从 Qoder/Claude/Codex 配置里移除 dafeiyu。"
