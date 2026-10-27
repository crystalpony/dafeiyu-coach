# 架构

## 目标

让任意能跑 shell 或 MCP 的 Agent，在 macOS 桌面上用**最小、离线、可视**的方式指导用户：指哪里、说什么、做到第几步、完成没有。没有 Agent 时，桌宠要能独立陪伴，且体积/占用足够小。

非目标：读屏、OCR、自动点击、自动填表、录屏、联网、跨平台。

## 组件

```
┌─────────────────────────────────────────────────────────────┐
│ Agent: Qoder / Codex / Claude Code / dsh / MCP client       │
│   skill 指令  ·  /dafeiyu 命令  ·  MCP tools  ·  直接 CLI    │
└───────────────┬─────────────────────────────────────────────┘
                │ 本地调用
┌───────────────▼─────────────────────────────────────────────┐
│ dafeiyu CLI（Python 3，单文件，无第三方依赖）                 │
│  - 参数解析 / 坐标换算 / --json                              │
│  - 自动拉起守护进程、僵尸 socket 清理                         │
│  - 只连 AF_UNIX，不发网络请求                                 │
└───────────────┬─────────────────────────────────────────────┘
                │ JSONL，一行一个请求/响应
                │ ~/.dafeiyu/coach.sock（0600）
┌───────────────▼─────────────────────────────────────────────┐
│ dafeiyu-daemon（Swift + AppKit，单二进制）                    │
│  AppController   任务状态机、设置/会话、菜单栏、命令分发       │
│  PetView         15 段动画、拖拽、摸头/戳/尾巴、爱心/彩纸/zzz  │
│  BubbleView      标题/正文/提示/徽章/进度点/自动收起           │
│  PointerView     每屏一层：脉冲圈、箭头、虚线、标签            │
│  ClipPlayer      按需解码 + NSCache(28 帧) + 12/24 fps        │
│  Companion       待机动作、应用感知、游到鼠标、睡觉            │
│  CoachServer     AF_UNIX 监听、JSON 解析、主线程串行处理        │
└─────────────────────────────────────────────────────────────┘
        ▲
        │ lyric/music_start/music_stop
┌───────┴───────────────┐      ┌──────────────────────────────┐
│ dafeiyu_music.py      │      │ dafeiyu_tui.py               │
│ 系统 Now Playing 轮询  │      │ 跨平台终端版（TCP+token）     │
│ macOS: BSD adapter    │      │ ASCII 宠物/歌词/步骤/米饭      │
│ Windows: SMTC ps1     │      │ Windows/macOS/Linux           │
│ LRCLIB / 本地 LRC     │      └──────────────────────────────┘
└───────────────────────┘
```

## 音乐与唱歌

```
macOS: MediaRemoteAdapter.framework + mediaremote-adapter.pl (BSD-3)
Windows: media_smtc.ps1 (WinRT SMTC)
        │ get 歌名/歌手/专辑/时长/进度/播放状态
        ▼
dafeiyu_music.py watch
        │ 1s 轮询；歌曲变化时取歌词；按 elapsed 找当前行
        │ 歌词源：本地 .lrc → LRCLIB 缓存/在线 → 网易云兜底（可关）
        ▼
JSONL: {"cmd":"music_start|lyric|music_stop", ...}
        ▼
GUI/TUI：只在空闲、非 quiet、会议 App 不在前台时显示歌词语气泡
```

- 歌词缓存：`~/.dafeiyu/lyrics/<sha1>.json`；负缓存 1h；正缓存 30 天。
- 本地优先级：`~/.dafeiyu/lyrics/local/<title> - <artist>.lrc`（可 `music import-lrc`）。
- 只向 LRCLIB / 网易云发送歌名/歌手/时长；无音频采集/录音/OCR；`provider=lrclib` 可关闭网易云。
- 纯音乐/长间奏每 10s 心跳，避免气泡被 30s 超时收起；watcher 退出后 30s 自动收起。
- 唱歌是视觉：`singing` 状态 + 音符粒子 + 摇摆；不播放 TTS。

## 终端轻量版（跨平台）

- `dafeiyu_tui.py`：Python 标准库，无 AppKit。核心实现与 Swift 版相同的 guide/next/finish/say/lyric/feed/focus 语义。
- 传输：优先 UNIX（macOS 原生版），否则本机 `127.0.0.1` 随机端口 + 32 字节 token；`~/.dafeiyu/coach.port`（0600）记录 port/token/pid。
- Windows：`msvcrt` 读键、启用 VT、CP 终端；PowerShell SMTC 取歌。
- 原生版运行时，`dafeiyu tui` 自动作为只读显示器附着（支持空格/f/p/q 快捷键）；否则自己当核心。
- 无指针圈：`point` 渲染为“看这里：标签 (x,y)”。

## 过渡状态机

- 优先级：drag 100 > error 90 > success 80 > point 70 > pat 60 > talk 50 > idle 10。
- 同一剪辑不从头重播；非循环动作播放中，低优先级请求被忽略；高优先级可打断。
- 播放新剪辑时保存上一帧，120–180ms 内双层 alpha 交叉淡化；统一脚底锚点，避免硬切。
- 非循环动作结束 → 0.18s 淡回 idle；气泡内容 120ms 淡入；猫/鱼摇摆只在低频叠加，不改变锚点。

## 互动模块

- 米饭：`feed` 计数 + 饭碗/米饭/筷子/热气绘制 + eat 动画 + 爱心；没有饥饿惩罚。
- 番茄钟：`focus --minutes`，到点 success + 休息气泡；会议模式/指导期间不抢台词。
- 会议模式：`quiet on --minutes`，到点自动恢复；Zoom/Teams/腾讯会议/飞书会议等前台时不主动说话、不收新歌词。
- 减少动态：关闭摇摆、音符、拖拽旋转，保留交叉淡化。

## 进程与生命周期

- CLI 的所有展示类命令默认**自动拉起**守护进程；`status` 不自动拉起，`start/stop` 显式控制。
- 守护进程是 accessory 应用：无 Dock 图标，菜单栏有「大肥鱼」。
- 单实例：socket 已存在且可连接 → 新进程退出；socket 是僵尸文件 → 删除后重建。
- 退出（菜单/`quit`/SIGTERM）→ 取消 DispatchSource、关闭 fd、删除 socket 与 pid 文件；保留设置和未完成任务。
- 守护进程崩溃：CLI 检测到连接失败会重新拉起；`session.json` 让未完成任务恢复到原步骤。

## IPC

请求：

```json
{"cmd":"guide","title":"…","steps":[{"text":"…","x":640,"y":300,"label":"…","hint":"…"}],"start":0,"agent":"qoder"}
```

响应：

```json
{"ok":true,"session":{"title":"…","index":0,"total":3,"done":0,"finished":false,"text":"…"}}
```

- 一行一个 JSON；读取上限 1 MB；客户端超时 3 s。
- 服务端在后台队列 accept/read，命令通过 `DispatchQueue.main.sync` 串行落到 AppKit 主线程。
- 错误统一 `{"ok":false,"error":"…"}`；CLI 退出码非 0。
- 命令：`ping/status/info/hello/bye/say/point/clear_point/guide/next/prev/finish/cancel/play/mood/hide/show/quiet/config/feed/dance/quip/come/move/demo/quit`。

## 任务模型

```swift
struct CoachStep { text, hint?, x?, y?, label? }
struct CoachSession { id, title, steps[], index, done[], agent, finished, updatedAt }
```

- `guide`：重置会话，`done` 全 false，`index=start`，展示当前步；有坐标则起指针，否则清指针。
- `next`：标记当前 `done[index]=true`；若已是最后一步 → `finished=true`、`index=total`、success + 撒花；否则 `index+=1` 并展示。
- `prev`：回退并清除该步的 done；已完成的会话回退会取消 finished。
- `finish`：全部标记完成并庆祝；`cancel`：清空会话，回到待机。
- 每次变化写 `session.json`；启动时只恢复未完成任务，已完成任务丢弃（避免每次开机弹旧气泡）。

## 坐标

- 对外统一：主屏左上角原点，x 右、y 下，单位 pt。
- AppKit：左下角原点。换算 `y_appkit = mainScreen.frame.maxY - y_topLeft`；对其他屏幕同样以主屏 maxY 为锚。
- `px`：CLI 先向守护进程取 `mainScale`（通常 2），再除以 scale；`norm`：乘以主屏宽高。
- 指针层：每块屏一个全屏透明窗口，触摸事件穿透，层级 `.screenSaver`；视图内坐标 = 全局 - 屏幕原点并翻转 y。虚线只在桌宠与目标同屏时绘制。

## 动画

- `Runtime/clips/manifest.json` 描述每个剪辑的 fps、loop、帧列表；帧为 300×250 WebP（带 alpha）。`rice` / `sing` 由 `scripts/derive_clips.py` 从 MIT 的 yawn 动作派生：前者逐帧绘制原创白瓷饭碗并一次性播放，后者取张口段乒乓循环。
- `ClipPlayer` 按需 `NSImage(contentsOfFile:)`，NSCache 限制 28 帧，避免 890 帧同时解码。
- 12 fps 主时钟逻辑：24 Hz Timer 累加 dt，只有跨过 1/fps 才换帧并 `needsDisplay`；`drop` 保留 24 fps 更顺。
- 非循环剪辑结束后回调；默认自动回 idle（autoIdle）。
- 窗口被遮挡（`occlusionState` 不含 `.visible`）或隐藏时暂停换帧；睡眠时仍保留低频时钟但不重绘。

## 气泡与指针

- 普通气泡宽度 336 pt，按内容测高；整体鼠标穿透，仅右上角 24×24 的关闭按钮窗口可点。
- 唱歌歌词条固定 316×62 pt，贴在鱼头顶居中（放不下则移到下方），只有歌名小字 + 当前句一行，单行截断，无关闭按钮。
- 普通气泡尾巴根据位置在左/右自动翻转；歌词条尾巴朝下指向鱼头；屏幕边缘 clamp。
- 指针在目标过期（`hold`）或新任务无坐标时清除；标签贴边 clamp，必要时移到圆环下方。
- 气泡关闭只是 `bubbleUserHidden`，下一条内容会重新展开；桌宠上保留「…」提示。

## 陪伴

- 1 Hz idle tick：10 分钟无命令 → yawn + zzz；否则每 70–150 s 随机：待机台词 / 伸懒腰或打哈欠 / 游到鼠标再回来。唱歌期间跳过睡觉与待机小动作，歌词超过 30 s 未更新自动收麦。
- 前台应用切换（NSWorkspace 通知）：非安静、无任务、气泡未显示、距上次 ≥150 s 时，按应用类型说一句。
- 安静模式关闭所有主动台词与游走；显式命令（feed/dance/quip）仍可用。

## 隐私与安全

- 原生版只使用 `AF_UNIX`；socket `0600`；终端版只用本机 loopback + token。无对外监听。
- 音乐模块只访问 `lrclib.net`（可关）和系统 Now Playing；不读音频、不录音、不上传本地文件。
- 不申请辅助功能/录屏/通知权限；不读屏、不读剪贴板、不合成键鼠事件。
- Agent 文本只作为 `NSAttributedString` 绘制，不执行；命令白名单解析，未知命令报错。
- CLI 只启动自己的守护进程，不执行用户传入的 shell。

## 性能取舍

- universal 单二进制约 1.1 MB，不引入 SwiftPM 依赖；素材 7.48 MB（15 组 / 890 帧）+ BSD 音乐适配器 669 KB。
- 待机 24 Hz 定时器 + 12 fps 换帧；指针激活时才 24 Hz 重绘全屏透明层。
- 70–82 MB RSS 主要来自 AppKit 窗口/图层与已解码帧缓存；不是帧全量常驻。
- 冷启动 0.30 s（AppKit + 首帧预取 3 帧）。

## 测试

- `dafeiyu-daemon --selftest`：坐标互换、步骤推进/回退、完成计数、manifest 与首帧存在性。
- `audit/audit.py`：临时 HOME 中真实安装 → CLI/E2E → MCP → 性能 → 截图 → 卸载，见 `docs/AUDIT.md`。
- 手工验收：拖动、摸头/戳/尾巴、双击、投喂、菜单、全屏置顶。自动审计不合成鼠标事件（不申请辅助功能）。
