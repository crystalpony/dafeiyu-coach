# dsh (DeepSeek Harness) 适配

dsh 会话里的 Agent 能执行 shell，也能读取 skills（`~/.dsh/skills` 或项目的 `.dsh/skills`）。安装脚本会把同一份 `SKILL.md` 放到 `~/.dsh/skills/dafeiyu-coach/`。

用法和 Qoder/Codex 完全一致：

```text
用户：让大肥鱼一步步教我把这个项目跑起来
Agent：dafeiyu hello --agent dsh
       dafeiyu guide --file /tmp/guide.json
       dafeiyu next
       dafeiyu finish
       dafeiyu bye
```

注意：dsh 自带 `dsh-dafeiyu` 原生桌宠插件。两者可以同时装，但会各有一只桌宠。日常二选一：

- 想要**跟随 Agent 会话状态**的桌宠 → 用 dsh 原生插件；
- 想要**跨 Agent 的指针指导 / 分步教学 / 陪伴** → 用本项目，并可在 dsh 插件设置里关闭原生角色。

如果 dsh 的 MCP 客户端支持 `mcpServers`，也可以把 `adapters/mcp/generic.json` 里的 `dafeiyu` 项加进去，用 MCP 工具而不是 shell。
