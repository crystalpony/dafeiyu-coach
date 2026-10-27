---
description: 召唤桌面大肥鱼，用指针、气泡和动画一步一步指导当前任务
---
请使用 `dafeiyu-coach` 技能来完成这次指导：

1. 先运行 `dafeiyu doctor`，必要时 `dafeiyu start`。
2. `dafeiyu hello --agent <当前客户端>`。
3. 把用户的目标拆成 3–7 步，用 `dafeiyu guide --file guide.json` 立任务；能确定位置就带 `x/y/label`。
4. 每完成一步再 `dafeiyu next`；最后自动庆祝。
5. 收尾 `dafeiyu bye`，不要用 `quit`。

如果没装技能，直接按上面的命令调用 CLI（默认在 `~/.local/bin/dafeiyu`）。
