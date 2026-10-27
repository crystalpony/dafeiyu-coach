# 桌面大肥鱼 Coach 1.1.0

> 一只住在 macOS 桌面上的大肥鱼。Agent 在对话里调用她，她就在屏幕上用**指针圈、语言气泡和 13 段动画**，一步一步带用户把事情做完；放歌时会跟着歌词轻轻唱；没有任务时，她安静地陪着。
>
> **平台**：macOS 原生桌宠（Swift/AppKit）· Windows 桌面窗口版（Tk + Pillow，透明置顶、动画/气泡/指针）· Windows/macOS/Linux 终端轻量版（Python TUI）· 同一套 skills / CLI / MCP。

这是 `Desktop/qoder-coach/Coach.swift` 的**独立版**：不再绑定某个固定教程的状态文件，而是通过 **skills / CLI / MCP** 被 Qoder、Codex、Claude Code、dsh 等 Agent 调用。原来的 `Coach.swift`、`state.json` 不动。

![指针 + 气泡 + 步骤](audit/screenshots/01-guide.png)

![放歌时跟着歌词唱](audit/screenshots/04-music.png)

![添一碗米饭](audit/screenshots/05-rice.png)

![Windows 桌面窗口版（CI 冒烟）](audit/screenshots/06-windows-gui.png)

![Windows 歌词唱歌（CI 冒烟）](audit/screenshots/07-windows-music.png)

![QQ 音乐真机唱歌](audit/screenshots/08-qq-music.png)

## 能做什么

- **指着屏幕教**：主屏任意坐标画脉冲圆环、箭头、虚线牵引和标签；窗口鼠标穿透，不挡操作。
- **一步一步**：`guide` 建任务，气泡显示「第 2/5 步」、标题、正文、提示与进度圆点；`next` 推进，最后一步撒花。
- **13 段动画**：待机、思考、工作、成功、出错、摸头、被戳、摇尾巴、吃东西、伸懒腰、打哈欠、被拖走、落地。
- **放歌时唱歌**：读系统 Now Playing（Apple Music / 网易云 / QQ 音乐 / Spotify），按歌词时间轴显示当前句和下一句，鱼会轻轻摇、飘音符；没有歌词就诚实显示“跟着哼”。歌词来自 LRCLIB 或本地 LRC，可完全离线。
- **陪伴**：待机小动作、按前台应用说一句（写代码 / 查资料 / 回消息 / 做音乐）、困了打哈欠睡觉；会议模式一键安静。
- **趣味互动**：摸头、戳身体、碰尾巴、拖拽、双击转圈、**添一碗米饭**、番茄钟专注、游到鼠标边、感知应用切换。
- **Windows 桌面窗口版**：`dafeiyu gui`，透明无边框置顶、13 段动画 + 交叉淡化、气泡、指针、米饭、右键菜单；与 TUI 共用同一核心。
- **终端轻量版**：`dafeiyu tui`，ASCII 鱼 + 歌词 + 步骤 + 米饭，Windows/macOS 共用同一核心；不依赖 AppKit。
- **小体积**：单二进制 1.1 MB（universal）；13 组 / 820 帧动画共 6.90 MB；音乐适配器 196 KB；运行体总计约 8.2 MB。
- **低占用**：待机 CPU 约 4.7%、RSS 约 71 MB；动画 + 指针约 7.2%、81 MB；冷启动 0.30 s（本机实测，见 [审计](docs/AUDIT.md)）。
- **好适配**：Qoder / Claude Code / Codex / dsh 四套 skill，三套 `/dafeiyu` 斜杠命令，一个 stdio MCP，外加通用 `AGENTS.md` 片段。

## 音乐与唱歌

支持的播放器：Apple Music、网易云音乐、QQ 音乐、Spotify 等**向系统 Now Playing 报告状态**的 App。

- macOS 用 BSD 许可的 MediaRemote 适配器读取系统 Now Playing，不需要辅助功能/录屏权限（Apple Music、网易云已真机验证）。
- Windows 用系统 SMTC（`media_smtc.ps1`），覆盖网易云/QQ 音乐/Apple Music/Spotify。
- 只发送 **歌名 / 歌手 / 时长** 到 LRCLIB 取歌词；不读音频、不录音、不上传任何本地文件。
- 没有网络或没有歌词时：用 `~/.dafeiyu/lyrics/local/` 的 `.lrc`；再没有就显示“跟着哼”。
- 只在**空闲、非安静模式、会议 App 不在前台**时唱歌；一有任务就让位给指导气泡。

```bash
dafeiyu music on                 # 启动歌词监听（安装脚本默认会启动）
dafeiyu music status             # 当前歌曲 + 监听状态
dafeiyu music now                # 只输出当前歌曲 JSON
dafeiyu music off                # 停止监听并收起歌词
dafeiyu music test --line "海风轻轻吹过"   # 不联网，测试唱歌
dafeiyu music import-lrc 晴天.lrc --title 晴天 --artist 周杰伦
dafeiyu music offset 0.4         # 歌词整体偏移
```

> 唱歌是**视觉卡拉 OK**：歌词气泡 + 摇摆 + 音符；不会播放 TTS/音频，避免盖住你的音乐。

## 安装

### macOS 原生版

要求：macOS 13+、Xcode Command Line Tools（`swiftc`）、Python 3.9+（系统自带或 CLT 提供）。二进制为 universal（arm64 + x86_64）。

```bash
cd DesktopFishCoach
scripts/install.sh            # 编译（如需要）+ 安装 + 四套 skills + 启动
scripts/install.sh --with-mcp # 额外写 Qoder/Claude/Codex 的 MCP 配置（自动备份）
scripts/install.sh --no-music # 只装桌宠，不启动音乐监听
```

### Windows 终端版

要求：Windows 10 1803+、Python 3.9+、PowerShell 5.1+。不需要编译，不需要 AppKit。

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
dafeiyu.cmd tui          # 或把安装目录加进 PATH 后： dafeiyu tui
```

Windows 同时提供：
- **桌面窗口版**：`dafeiyu-gui.cmd` 或 `dafeiyu gui`（Python 3.9+ / Pillow；安装脚本会装 Pillow、复制 clips）。透明置顶、拖拽、动画/气泡/指针/歌词/米饭；由 Win32 透明色 + 点击穿透实现。
- **终端轻量版**：`dafeiyu tui`（ASCII 宠物 + 歌词 + 米饭 + 步骤），无 Pillow 也能跑。

> Windows 桌面版是 Tk/Pillow 实现，视觉与 macOS AppKit 版不完全一致；CI 会跑窗口冒烟并上传截图，但不等同于真实 Windows 桌面人工验收。

安装位置：

| 内容 | 路径（macOS） |
| --- | --- |
| 命令 | `~/.local/bin/dafeiyu` |
| 守护进程 | `~/.local/bin/dafeiyu-daemon` |
| MCP | `~/.local/bin/dafeiyu_mcp.py` |
| 动画 / 音乐 / 设置 / 会话 | `~/.dafeiyu/` |
| 终端版 | `dafeiyu tui`（同一 `~/.dafeiyu`） |
| Skills | `~/.qoder/skills/dafeiyu-coach/`、`~/.claude/skills/…`、`~/.codex/skills/…`、`~/.dsh/skills/…` |
| 斜杠命令 | `~/.qoder/commands/dafeiyu.md`、`~/.claude/commands/…`、`~/.codex/prompts/…` |

可选：

```bash
scripts/install.sh --with-mcp   # 写入 Qoder/Claude/Codex 的 MCP 配置（自动备份）
scripts/install.sh --build      # 强制重编译
scripts/install.sh --no-start   # 只安装，不启动
```

没把 `~/.local/bin` 加进 PATH 也能用绝对路径调用。

### 直接跑起来

```bash
dafeiyu doctor                  # 自检（进程/素材/音乐/终端版/skills）
dafeiyu hello --agent qoder     # 打招呼
dafeiyu demo                    # 三步演示（指针 + 气泡 + 撒花）
dafeiyu tui                     # 终端轻量版（可同时作为 macOS 原生版的显示器）
dafeiyu stage on                # 演示舞台：盖住其它应用，方便截图/录屏（off 恢复）
```

## 在 Agent 里怎么用

### 1. Skills（推荐）

安装脚本已经把同一份 `SKILL.md` 放进四个 Agent 的技能目录。安装后 Qoder 会立即识别出 `dafeiyu-coach` 技能和 `/dafeiyu` 命令（本次安装已验证），其他客户端重启会话后生效。直接说：

> 让大肥鱼一步一步教我在 GarageBand 里做一段 EP。

Agent 会按 skill 的流程调用：

```bash
dafeiyu hello --agent qoder
dafeiyu guide --file guide.json
dafeiyu next --say "很好，继续。"
dafeiyu finish
dafeiyu bye
```

`guide.json`：

```json
{
  "title": "在 GarageBand 里做一段 EP",
  "steps": [
    {"text": "先点左侧的 Electric Piano 轨道。", "x": 640, "y": 300,
     "label": "点这个轨道", "hint": "没有 EP 轨就按 ⌘N 新建"},
    {"text": "按 ⌘T 打开乐器，选 Electric Piano。"},
    {"text": "用铅笔在第 1 小节点 4 个音：C#4 / E4 / G#4 / B4。",
     "x": 820, "y": 520, "label": "从这里开始画"},
    {"text": "按空格试听，确认味道。"}
  ]
}
```

### 2. `/dafeiyu` 斜杠命令

在 Qoder / Claude Code / Codex 里输入 `/dafeiyu`，让当前 Agent 立刻进入指导流程。

### 3. MCP

```json
{
  "mcpServers": {
    "dafeiyu": {"command": "dafeiyu", "args": ["mcp"]}
  }
}
```

工具：`dafeiyu_begin`、`dafeiyu_guide`、`dafeiyu_next`、`dafeiyu_point`、`dafeiyu_say`、`dafeiyu_play`、`dafeiyu_status`、`dafeiyu_finish`、`dafeiyu_end`、`dafeiyu_feed`。
Codex 的 TOML、Qoder/Claude 的 JSON 片段在 [`adapters/mcp/`](adapters/mcp/)。

### 4. 没有 skills 的 Agent

把 [`adapters/AGENTS.md`](adapters/AGENTS.md) 贴进项目 `AGENTS.md`（或 Cursor Rules）即可。dsh 的注意事项见 [`adapters/dsh.md`](adapters/dsh.md)：dsh 自带的 `dsh-dafeiyu` 原生桌宠和本项目可以二选一，避免两只鱼同时出现。

## CLI 速查

| 命令 | 作用 |
| --- | --- |
| `dafeiyu hello --agent qoder` | 打招呼、声明 Agent 已连接 |
| `dafeiyu guide --file g.json` / `--step "…"` | 开始分步任务（`--unit pt/px/norm`） |
| `dafeiyu next [--say "…"]` / `prev` / `finish` / `cancel` | 推进 / 回退 / 完成 / 取消 |
| `dafeiyu point --x 640 --y 300 --label "…"` | 只画指针（`--hold` 秒） |
| `dafeiyu say "…" --step 2/5 --tone success` | 只说话，可带徽章/情绪/动画 |
| `dafeiyu play success` | 播放动画 |
| `dafeiyu mood thinking\|focus\|happy\|sleepy` | 情绪 |
| `dafeiyu feed` / `dance` / `come` / `quip` | 添米饭 / 跳舞 / 游到鼠标边 / 随口一句 |
| `dafeiyu music on\|off\|status\|now\|test` | 歌词监听与唱歌 |
| `dafeiyu music import-lrc …` / `offset 0.4` | 本地歌词 / 偏移 |
| `dafeiyu focus --minutes 25` / `--cancel` | 番茄钟 |
| `dafeiyu quiet on --minutes 60` | 会议模式（到点自动解除） |
| `dafeiyu gui` | Windows/macOS 桌面窗口版 |
| `dafeiyu tui` | 终端轻量版（Windows/macOS） |
| `dafeiyu stage on\|off` | 演示舞台：盖住其它应用，截屏/录屏用 |
| `dafeiyu hide` / `show` / `quiet on\|off` / `scale 1.2` | 显隐 / 安静 / 大小 |
| `dafeiyu status [--json]` / `info` / `doctor` | 状态 / 屏幕 / 自检 |
| `dafeiyu start` / `stop` | 启动 / 退出守护进程 |
| `dafeiyu demo` | 三步演示 |
| `dafeiyu mcp` | 以 stdio MCP 运行 |

所有命令都支持 `--json`（放在子命令前后均可），便于 Agent 解析。

## 坐标

- 默认 `pt`：**主屏左上角**为原点，x 向右、y 向下；多屏以主屏左上角为基准。
- 截图里量的是像素 → `--unit px`，按主屏 Retina scale 自动换算。
- `--unit norm`：0~1 归一化。
- `dafeiyu info` 可看主屏尺寸与 scale；`status --json` 里有 `mainScale`、`screens`、`pet`、`bubble`、`clip`、`frame`。

## 动画

| clip | 时长 | 用途 |
| --- | --- | --- |
| idle | 10.1 s 循环 | 待机 |
| thinking | 10.1 s 循环 | 思考 / 等确认 |
| working | 10.1 s 循环 | 工作 / 指针引导 |
| success | 5.0 s | 完成（撒花） |
| error | 3.0 s | 出错 |
| pat | 4.0 s | 打招呼 / 摸头 |
| poke / tail | 3.0 s | 被戳 / 碰尾巴 |
| eat | 4.0 s | 投喂 |
| stretch / yawn | 4.0 s | 伸懒腰 / 困 |
| drag / drop | 5.0 s / 1.5 s | 拖拽 / 落地 |

素材为 300×250 WebP、12 fps，按需解码，LRU 28 帧；落地（drop）为 24 fps，其余为 12 fps。

**过渡**：动画有优先级（拖动 > 出错 > 成功 > 指导 > 说话 > 待机），同一剪辑不重复从头播放；切换时 120–180ms 双层交叉淡化 + 统一的脚底锚点；气泡内容淡入；避免旧版“next 一次 play 三次”的硬切。见 [架构](docs/ARCHITECTURE.md)。

## 架构

```
Agent (Qoder / Codex / Claude / dsh / MCP 客户端)
   │  skill / /dafeiyu / MCP tools / CLI
   ▼
dafeiyu (Python CLI)  ── UNIX 0600 ──►  dafeiyu-daemon (Swift/AppKit, macOS)
   │                              └──►  dafeiyu tui (Python, 本机 TCP+token, Windows/macOS)
   │
   └─ dafeiyu_music.py ── MediaRemote(macOS) / SMTC(Windows) ──► LRCLIB / 本地 LRC
                                      │
                                      └─ lyric 命令 ──► 歌词气泡 + 唱歌

dafeiyu-daemon (Swift + AppKit, universal 单二进制)
   ├─ PetView         13 段动画、拖拽、摸头/戳/尾巴、爱心/彩纸、zzz
   ├─ BubbleView      标题 / 正文 / 步骤徽章 / 进度点 / 自动收起
   ├─ PointerView     每屏一层，脉冲圈 + 箭头 + 虚线 + 标签
   ├─ AppController   任务状态机、设置/会话持久化、菜单栏
   └─ Companion       待机小动作、应用感知、游到鼠标、睡觉
```

- **无网络**：只使用 `AF_UNIX`；不读屏、不申请辅助功能、不合成点击、不读剪贴板。
- **协议**：一行一个 JSON；`{"cmd":"...", ...}` → `{"ok":true,...}`。
- **状态**：`~/.dafeiyu/settings.json`（位置/大小/安静）、`session.json`（未完成任务可跨重启恢复）。
- 细节见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 性能与体积（本机审计实测）

| 项目 | 实测 |
| --- | --- |
| 二进制 | 1.1 MB（universal arm64 + x86_64） |
| 动画素材 | 6.90 MB / 13 组 / 820 帧 |
| 音乐适配器 | 196 KB（MediaRemote framework + Perl 脚本） |
| 安装后运行体 | ≈ 8.2 MB |
| 冷启动 | 0.30 s |
| 待机 CPU / RSS | 4.7% / 71 MB |
| 动画 + 指针 CPU / RSS | 7.2% / 81 MB |

优化手段：24 Hz 主时钟 + 12 fps 动画、仅在换帧时重绘、窗口被遮挡/隐藏时暂停、LRU 帧缓存、指针层仅在激活时置顶、待机操作限频、10 分钟无交互后睡觉。

## 目录

```
DesktopFishCoach/
├── Sources/               Swift 守护进程（8 个文件）
├── bin/dafeiyu            CLI（Python，无第三方依赖）
├── bin/dafeiyu_mcp.py     stdio MCP
├── Runtime/clips/         压缩后的动画素材 + manifest（MIT）
├── Runtime/music/         BSD MediaRemote 适配器 + Windows SMTC 脚本
├── skills/dafeiyu-coach/  唯一一份 SKILL.md，安装到各 Agent
├── adapters/              各 Agent 配置、/dafeiyu 命令、AGENTS.md、dsh 说明
├── scripts/               build / install / uninstall / build_assets
├── .github/workflows/     macOS + Windows CI
├── audit/                 audit.py + 截图 + last-report.json
└── docs/                  架构、审计、变更记录
```

## 卸载

```bash
scripts/uninstall.sh            # 移除二进制、skills、斜杠命令，保留设置
scripts/uninstall.sh --purge    # 连 ~/.dafeiyu 一起删
```

MCP 配置（如果加过）需要手动从 Qoder/Claude/Codex 配置里移除 `dafeiyu`。

## 审计

```bash
python3 audit/audit.py            # 全量（安装到临时 HOME，不碰真实配置）
python3 audit/audit.py --no-visual
```

覆盖 129 项：编译 warning-free、体积预算、单元自测、安装/幂等/卸载、CLI 全流程、音乐/歌词/米饭/番茄钟/会议模式、过渡交叉淡化、终端版 TCP、像素级截图、MCP 协议、性能采样、隐私扫描、文档完整性。见 [审计](docs/AUDIT.md)、[三轮迭代](docs/ITERATIONS.md)、[发布素材](docs/SOCIAL.md)。最近一次结果见 [docs/AUDIT.md](docs/AUDIT.md) 与 `audit/last-report.json`。

## 许可与致谢

代码 MIT。角色动画素材来自 [PC2005-cloud/dsh-pet](https://github.com/PC2005-cloud/dsh-pet)（MIT），经 [QCYTSN/dsh-dafeiyu](https://github.com/QCYTSN/dsh-dafeiyu) 重新打包；本项目只取用其中的 idle/thinking/working/success/error/pat/poke/tail/eat/stretch/yawn/drag/drop，降采样重编码以控制体积。

设计上参考了 dsh-dafeiyu 的交互方式（拖拽/摸头/待机小动作）、[openpets](https://github.com/alterhq/openpets) 的 CLI + MCP 分工，以及 [Neco](https://github.com/winebarrel/Neco) 的“追鼠标”趣味。macOS 音乐检测使用 [ungive/mediaremote-adapter](https://github.com/ungive/mediaremote-adapter)（BSD-3-Clause）；歌词来自 [LRCLIB](https://lrclib.net/)。完整声明见 [NOTICE.md](NOTICE.md)。

## 平台支持矩阵

| 能力 | macOS 原生版 | Windows 终端版 | macOS/Linux 终端版 |
| --- | --- | --- | --- |
| 指针圈 / 悬浮气泡 / 13 段动画 | ✅ | 文本气泡 + 步骤（无指针） | 文本气泡 + 步骤 |
| Agent skills / CLI / MCP | ✅ | ✅ | ✅ |
| 音乐检测 / 歌词 / 唱歌 | ✅ Apple Music / 网易云 / QQ（系统 Now Playing） | ✅ 系统 SMTC | 取决于系统 |
| 米饭 / 番茄钟 / 会议模式 | ✅ | ✅（会议模式用 `quiet`） | ✅ |
| 桌面 GUI | ✅ AppKit | ✅ Tk/Pillow（CI 冒烟；视觉未真机人工验收） | ❌ |
