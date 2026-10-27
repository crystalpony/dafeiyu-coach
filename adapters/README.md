# Agent 适配

同一套能力，四种接法。skills 让 Agent 知道**何时、怎么用**；MCP 让不支持 shell 解析的客户端也能调；CLI 是最终执行层。

| Agent | Skills | MCP | 说明 |
| --- | --- | --- | --- |
| Qoder | `~/.qoder/skills/dafeiyu-coach/` | `~/.qoder/mcp.json` | 安装脚本默认写入 skill；`--with-mcp` 写 MCP |
| Claude Code | `~/.claude/skills/dafeiyu-coach/` | `~/.claude.json` → `mcpServers` | 同上 |
| Codex | `~/.codex/skills/dafeiyu-coach/` | `~/.codex/config.toml` → `[mcp_servers.dafeiyu]` | 同上 |
| dsh (DeepSeek Harness) | `~/.dsh/skills/dafeiyu-coach/` | 通用 MCP 配置 | dsh 读取 `~/.dsh/skills` 与 `<project>/.dsh/skills` |
| Cursor / 其它 MCP 客户端 | 复制 `AGENTS.md` 片段 | 任意 `mcpServers` JSON | 命令 `dafeiyu mcp` |

安装：

```bash
scripts/install.sh                 # 二进制 + 素材 + 四套 skills
scripts/install.sh --with-mcp      # 额外写入 Qoder / Claude / Codex 的 MCP 配置（自动备份）
```

## 为什么 skills 与 MCP 都要有

- **skill** 负责“教学法”：拆步骤、每步一句话、等用户确认再 `next`、什么时候指屏幕、什么时候收尾。没有 skill，Agent 可能一上来就连续弹十个气泡。
- **MCP** 负责“跨客户端”：Qoder / Codex / Claude / Cursor / dsh 都能挂同一个 stdio 服务，工具语义和 CLI 完全一致。
- **CLI** 负责“可审计”：所有动作都能在终端复现，也方便脚本和 CI。

## 通用 MCP 配置

```json
{
  "mcpServers": {
    "dafeiyu": {
      "command": "/Users/you/.local/bin/dafeiyu",
      "args": ["mcp"]
    }
  }
}
```

Codex `config.toml`：

```toml
[mcp_servers.dafeiyu]
command = "/Users/you/.local/bin/dafeiyu"
args = ["mcp"]
```

## 没有 skills 的 Agent

把 `adapters/AGENTS.md` 的内容贴进项目的 `AGENTS.md`（或 Cursor Rules）。它会告诉 Agent：
先 `dafeiyu hello`，再用 `guide` 立任务，每完成一步 `next`，最后 `bye`；坐标单位与指针用法同 skill。
