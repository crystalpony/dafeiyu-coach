# 桌面大肥鱼 Coach

本项目使用「桌面大肥鱼 Coach」做可视化指导。当用户要求“指着屏幕教我”“一步一步带我操作”“让桌宠/大肥鱼来指导”时：

1. 先确认可用：`dafeiyu doctor`（不在 PATH 时用 `~/.local/bin/dafeiyu`）。
2. 打招呼：`dafeiyu hello --agent <qoder|codex|dsh|claude>`。
3. 拆 3–7 步，每步只做一个动作；用 `dafeiyu guide --file guide.json` 立任务（每步可带 `x/y/label/hint`）。
4. 用户确认完成后再 `dafeiyu next --say "..."`；最后一步会自动庆祝。
5. 收尾用 `dafeiyu finish` / `dafeiyu bye`；不要用 `quit`（会关掉用户的桌宠）。

坐标默认是主屏左上角原点的 pt；截图像素加 `--unit px`，归一化用 `--unit norm`。
气泡一句话、动词开头、60 字以内；一次只指一个目标。
完整用法见 `~/.qoder/skills/dafeiyu-coach/SKILL.md`（其它 Agent 同理）。
