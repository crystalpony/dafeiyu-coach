# Changelog

## 1.1.0 — 2026-10-27

### 新增

- **音乐检测 / 歌词 / 唱歌**：Apple Music、网易云、QQ 音乐等系统 Now Playing；LRCLIB + 本地 LRC；空闲时歌词气泡、摇摆和音符；`music on/off/status/now/test/import-lrc/offset`。
- **BSD MediaRemote 适配器**（macOS 15.4+） + Windows SMTC 脚本；歌词 watcher 仅发送歌名/歌手/时长。
- **Windows 桌面窗口版** `dafeiyu gui`：Tk + Pillow，透明置顶、13 段动画/交叉淡化、气泡、指针、米饭、右键菜单；与 TUI 共用 Core/Server；`install.ps1` 安装 Pillow/clips。
- **终端轻量版** `dafeiyu tui`：ASCII 宠物、歌词、步骤、米饭；Windows/macOS/Linux；本机 TCP + token；原生版运行时自动附着显示。
- **互动**：添一碗米饭（饭碗/米饭/筷子/热气 + 计数）、番茄钟、会议模式（到点自动解除、会议 App 抑制）、减少动态。
- **动画过渡**：优先级队列、同剪辑不重启、120–180ms 双层交叉淡化、气泡淡入、去重复 play。
- **Windows**：`scripts/install.ps1`、SMTC 适配器、GitHub Actions Windows CI；原生 GUI 仍是 macOS。
- 二进制 universal（arm64 + x86_64）；音乐 framework universal。
- MCP 12 个工具（新增 `dafeiyu_music`、`dafeiyu_focus`）。

### 修复

- macOS 15.4+ 旧 MediaRemote C API 返回空 → BSD 适配器。
- `advanceStep/showCurrentStep` 重复 play、硬切。
- 空闲检查放错文件导致番茄钟/会议模式/音乐超时不生效。
- 终端核心 status 递归锁死、CLI 超时误拉起原生 daemon、状态字段不兼容、中文宽度错位。
- 安装/卸载脚本中文全角括号导致的变量解析错误。

### 文档/验收

- `docs/ITERATIONS.md` 三轮真实迭代；`docs/SOCIAL.md` 发布草稿；`Runtime/music/README.md`。

## 1.0.0 — 2026-10-27

首个独立版。项目立项名：**桌面大肥鱼 Coach**。

### 新增

- **AppKit 守护进程**（Swift 单二进制，494 KB）
  - 13 段动画：idle / thinking / working / success / error / pat / poke / tail / eat / stretch / yawn / drag / drop
  - 指针层：每屏一层，脉冲圈 + 箭头 + 虚线牵引 + 标签，鼠标穿透
  - 气泡：标题、正文、提示、步骤徽章、进度圆点、自动收起、关闭按钮
  - 分步任务状态机：guide / next / prev / finish / cancel；`session.json` 跨重启恢复
  - 陪伴：待机小动作、前台应用感知台词、游到鼠标边、10 分钟无交互睡觉
  - 趣味互动：摸头 / 戳 / 尾巴 / 拖拽落地 / 双击转圈 / 投喂 / 跳舞
  - 菜单栏与右键菜单：显隐、安静、互动开关、大小、演示、关于
- **`dafeiyu` CLI**（Python 3 单文件，无第三方依赖）
  - 全部命令、`--json`、自动拉起守护进程、僵尸 socket 清理
  - 坐标单位 pt / px（Retina 自动换算）/ norm
- **MCP**：stdio JSON-RPC，10 个工具，支持 Qoder / Codex / Claude / Cursor / dsh
- **Agent 适配**
  - Qoder / Claude Code / Codex / dsh 四套 skill（同一份 `SKILL.md`）
  - Qoder / Claude Code / Codex 的 `/dafeiyu` 斜杠命令
  - 通用 `AGENTS.md` 片段、dsh 共存说明、MCP 配置片段
- **安装器**：编译、安装、素材同步、skills、可选 MCP 合并（自动备份）、幂等；卸载与 `--purge`
- **审计**：`audit/audit.py`，覆盖构建、体积、单元、安装、E2E、MCP、性能、隐私、文档、截图、卸载

### 性能（本机实测）

- 待机 3.6% CPU / 71 MB RSS；动画 + 指针 6.0% / 83 MB
- 冷启动 0.30 s；运行体约 7.4 MB（二进制 494 KB + 素材 6.90 MB）

### 与旧版的关系

- 旧版 `Desktop/qoder-coach/Coach.swift` 保留不动：单动画、轮询 `state.json`、面向单个 GarageBand 教程。
- 独立版不再依赖 `state.json`，改为 skills / CLI / MCP 驱动；动画与交互素材来自 MIT 的 dsh-pet（见 `NOTICE.md`）。
