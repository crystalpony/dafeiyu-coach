# 三轮迭代记录

> 版本：1.2.0 · 2026-10-28
> 原则：每轮都先写“用户是谁、会在哪里卡住”，再改代码/文案，最后用真实命令和截图验收。不是把功能名重复三遍。

## 基线（迭代前）

- 原生桌宠：15 段动画、指针、气泡、步骤、米饭、番茄钟、会议模式、减少动态。
- 音乐：macOS 用 BSD MediaRemoteAdapter 读系统 Now Playing（Apple Music / 网易云 / QQ 音乐），Windows 用 SMTC；LRCLIB + 本地 LRC；空闲时唱歌。
- 终端版：`dafeiyu tui`，ASCII 宠物、歌词、米饭、步骤，Windows/macOS 共用 Python 核心。

## 第 1 轮：第一次用“会唱歌的鱼”的学生

**画像**：23 岁，网易云/QQ 音乐重度用户；想让桌宠跟着歌词动，但怕它偷听、怕打扰、怕中文歌没歌词。

**发现的真实问题**

1. 网易云《一念之间》在 LRCLIB 没有歌词，桌面只显示“跟着哼”，用户会觉得功能坏了。
2. 安装完不知道歌词会联网，也不知道怎么关。
3. macOS 上打开 `dafeiyu tui` 时，如果原生版在跑，终端只能看不能操作。

**改动**

- 增加本地 LRC：`~/.dafeiyu/lyrics/local/`、`dafeiyu music import-lrc file.lrc --title … --artist …`；找不到网络歌词时优先用本地。
- 增加 `--no-network`、`music off`、安装参数 `--no-music`；README 写明只发送歌名/歌手/时长到 LRCLIB。
- 终端附着模式支持键盘：空格下一步、f 添饭、p 摸摸、q 退出。
- 给“没有歌词”一个诚实降级：显示歌名/歌手 + “跟着哼”，不再假装有词。

**验收**

- 本地 LRC fixture（3 行）→ `music lyrics --no-network` 输出 3 行；`watch --once` 在 2.5s 命中第 2 行。
- 真实网易云播放 → 桌宠显示“一念之间 · 陶喆 / ♪ 跟着哼”，暂停后气泡自动收起。
- 截图：`audit/screenshots/04-music.png`。

## 第 2 轮：开放工位 / 会议中的用户

**画像**：28 岁，产品经理；白天开腾讯会议、Zoom，偶尔在共享屏幕；对闪烁和打断敏感；希望“减少动态”。

**发现的真实问题**

1. 会议模式只写了命令，没有“到点自动解除”；而且音乐/番茄钟检查被放进了错误文件，实际不生效。
2. 会议 App 前台时，应用感知台词仍可能冒出来；音乐歌词也会继续弹。
3. 没有减少动态选项；对前庭敏感/专注用户不友好。
4. 终端版在浅色终端/无色环境下对比度一般。

**改动**

- 会议模式：`dafeiyu quiet on --minutes 60` / 菜单「会议模式 60 分钟」，到点自动恢复并说一句；会议 App（Zoom/Teams/腾讯会议/飞书会议等）前台时，不主动搭话、不显示新歌词，并收起音乐气泡。
- 减少动态：菜单开关，关闭唱歌摇摆、音符粒子和位移旋转；保留交叉淡化（不产生闪烁）。
- 修复空闲检查位置：`idleTick` 实际在 `Companion.swift`，把音乐超时/番茄钟/会议到期移过去；番茄钟现在会真的以 success 结束。
- TUI 支持 `--no-color`，并修正中文宽字符导致的气泡边框错位。

**验收**

- `quiet on --minutes 0.02` → 2s 后 `quiet=false`，气泡提示“会议模式结束”。
- `focus --minutes 0.05` → 4s 后 `focusRemaining=0`、clip=success、气泡出现。
- `daemon --selftest` 新增 Zoom/腾讯会议/非会议 App 断言，通过。
- 截图：`audit/screenshots/05-rice.png`（米饭+气泡）。

## 第 3 轮：跨平台开发者 / 准备发 GitHub 的人

**画像**：26 岁，macOS + Windows 双机；用 Qoder/Codex/Claude；希望终端能跑、Windows 能用、CI 能证明；不想装一堆依赖。

**发现的真实问题**

1. macOS 15.4+ 的旧 MediaRemote C API 返回空；必须走新的 `MRNowPlayingController` 类，或者用 BSD 适配器（最终选了 BSD 适配器，避免私有 API 的维护风险）。
2. 终端核心 `status` 在锁内再调 `status()`，递归死锁；CLI 超时后又误拉起原生守护进程，掩盖问题。
3. 终端 `status` 字段不兼容 CLI（没有 `session`/`pid`/`songTitle`），人类输出出现 `None`。
4. Windows 没有原生 GUI；用跨平台 Python 终端版 + 系统 SMTC 满足“能跑、能控制、能唱歌”。
5. 二进制只有 arm64；Intel Mac 不能跑。

**改动**

- macOS 音乐改用 BSD-3-Clause 的 `MediaRemoteAdapter`（Perl + 通用 framework），`get` 实测 Apple Music、网易云；Windows 提供 SMTC PowerShell 适配器。
- 终端核心改为本机 TCP + token（Windows 无可靠 AF_UNIX），CLI/MCP/歌词 watcher 都能连；修复锁递归、CLI 误拉起、状态字段。
- 终端渲染按东亚字符宽度补齐；`--once` 供 CI/验收。
- 原生二进制改为 universal（arm64 + x86_64，1.1 MB）；音乐 framework 也 universal。
- 新增 `scripts/install.ps1`、GitHub Actions macOS/Windows CI、`dafeiyu tui`、Windows 支持矩阵。
- 版本 1.1.0；审计增加音乐、过渡、米饭、番茄钟、会议模式、TUI/Windows 静态检查。

**验收**

- Windows CI 跑 `dafeiyu_tui --headless` + `dafeiyu status/guide/next/feed/stop`（TCP）与本地 LRC（见 `.github/workflows/ci.yml`）。
- macOS 真机：网易云/Apple Music 播放 → 歌词 → 唱歌 → 暂停收起；交叉淡化 `blend<1`；米饭计数；番茄钟；会议模式。
- 审计结果见 `docs/AUDIT.md` 与 `audit/last-report.json`。

## 追加轮：用户要求补 Windows 原生桌面 GUI（验收后追加）

**画像**：Windows 主力机用户，不接受“Windows 只有终端”。

**发现/改动**

- 新增 `bin/dafeiyu_gui.py`：Tk + Pillow，透明无边框置顶窗口、拖拽、15 段 WebP 动画 + `Image.blend` 交叉淡化、气泡、指针圈、米饭/番茄钟/右键菜单。
- 复用终端版 `Core/Server`：Windows GUI 自己当核心（本机 TCP + token），CLI/MCP/skills 仍可控制；不与 TUI 重复实现状态机。
- Windows 透明色抠图 + Win32 `WS_EX_TRANSPARENT/LAYERED/NOACTIVATE` 点击穿透；`pythonw` 启动无控制台。
- `dafeiyu gui` / `dafeiyu-gui.cmd`；`install.ps1` 复制 clips、安装 Pillow。
- GUI 冒烟：macOS `--check/--smoke`；GitHub Actions Windows 跑 `--smoke`（指针）与 `--smoke-music`（歌词/音符）并上传截图；`install.ps1` 也在 Windows CI 真跑。
- 修：Windows PowerShell 5.1 读取无 BOM 的 UTF-8 脚本导致中文引号解析失败 → `install.ps1`/`media_smtc.ps1` 改为 UTF-8 BOM。
- 修：实例属性 `self.smoke` 覆盖方法导致 `TypeError`；默认位置在小屏越界；气泡 accent 未按 tone 着色。

**追加验收（网易云兜底）**：LRCLIB 缺《一念之间》歌词，接入 `music.163.com` 可选兜底，拿到同步 LRC 并过滤作词/作曲行；`provider=lrclib` 可关闭，隐私说明同步。**追加验收（QQ 真机）**：QQ 音乐播放被系统识别为 `com.tencent.QQMusicMac`，歌名/歌手立即显示；发现 LRCLIB 网络慢会阻塞切歌，已改为“先推歌名，歌词后台 fetch”，暂停/切歌不再被网络卡住。该曲无歌词时“跟着哼”，不伪造。

**验收边界**：Windows 窗口版是 Tk/Pillow，视觉与 macOS AppKit 不等同；CI 冒烟≠真实 Windows 人工验收。若要求原生 WinUI/Tauri 级体验，需要下一轮重写。

## 用户反馈修正：米饭独立动画 + 头顶歌词条

**反馈原话**：米饭动画在吃 token 的动画上，碗是倒过来的；唱歌气泡太占地方，要求有唱歌动画、歌词在头上且不占地方。

**发现**

- `feed` 之前复用 `eat` 剪辑，画面里有四颗蓝色 token 光球；Swift 侧再叠一只倒扣的饭碗，既重复又方向错误。
- 唱歌只在原有待机动作上轻微摇摆，歌词走通用大气泡（约 336×78，带标题/徽章/下一句），视觉占用与“陪伴”定位不符。

**改动**

- 生成独立的 `rice` 剪辑（48 帧 / 4s / 一次性）：以 MIT 的 yawn 动作为底，逐帧绘制原创白瓷碗（碗口朝上）、米饭堆、筷子、热气与飞向嘴边的米粒；不再包含 token，也不再用运行时代码叠碗。
- 生成独立的 `sing` 剪辑（22 帧 / 1.8s / 循环）：取张口段做乒乓循环并烘焙轻微摇摆；唱歌时只播这一条，音符由粒子层补充。
- 歌词改为头顶紧凑条（316×62）：第一行歌名/歌手小字，第二行当前句，单行截断；尾巴向下指向鱼头，不再显示上一句/下一句、进度点和关闭按钮，也不占用侧边桌面。
- TUI 把歌词放到 ASCII 鱼上方一行；Windows GUI 使用 250×56 的窄条，居中贴头顶。
- 修：唱歌/米饭优先级低于正在收尾的 success 动画时会“起不来”，提高到 85；唱歌期间不再触发睡觉/待机小动作；吃完饭后若还在唱歌自动回到 `sing`；拖拽或一次性动作结束后自动恢复唱歌；歌词条不随气泡缩放放大（上限 1.08×）；音乐开始会唤醒睡着的鱼。
- 新增审计：`sing`/`rice` 独立性、歌词条尺寸与位置、米饭碗白像素占比（27% vs 源动作 2%）、喂饭剪辑名、15 段全播放。

**验收**

- 真机截图见 `audit/screenshots/04-music.png` / `05-rice.png`；TUI 样例见 `tui-sample.txt`；Windows GUI 冒烟覆盖 `sing` 与紧凑歌词条。
- 审计 134/134 通过；`rice=48` / `sing=22`，素材 15 组 / 890 帧 / 7.48 MB。

## 用户反馈修正：歌词延迟 + 气泡尺寸直调

**反馈原话**：歌词监测延迟很大，气泡太大了；大小调节改成用户直接输入百分值，可以很小很大，但要设安全值（不能小到鼠标点不到，不能大到屏幕一半）；再加一个气泡宽高手动调节。

**根因**

- MediaRemote 的 `elapsedTime` 是 **timestamp 那一刻** 的播放位置，不是“现在”；网易云/QQ 常常返回 `elapsedTime=0` 且 timestamp 停在歌曲开始。旧 watcher 直接把 0 当当前进度，歌词会永远停在第一句——不是“慢一秒”，而是整首不动。
- 旧循环固定 1 s 轮询，切句最多再晚 1 s；歌词网络请求串行 + 10 s 超时，网络差时要等很久才出现第一句。

**改动**

- macOS 读取 `--micros` 的 `elapsedTimeMicros + timestampEpochMicros + playbackRate`，按本地时钟算出真实位置；watcher 元数据 0.5 s 刷新，歌词行 0.1 s 插值，切句误差压到 0.1 s 内。运行中改 `music offset` 也会在 5 s 内生效。
- 歌词请求 LRCLIB 与网易云并行、5 s 预算；LRCLIB 有同步词立即用，不再等兜底。切换/暂停容错两拍，避免网络抖动误收麦。
- `music on` 会识别旧版本 watcher 并重启，清理重复进程，避免两条歌词流互相覆盖；重复扫描只认 python 进程，不会误杀 shell。
- 歌词条默认从 316×62 缩到 **280×50**；字号、徽标、内边距随高度自适应，低于 38 pt 只显示当前句。
- 菜单「桌宠大小」「气泡大小」新增 **输入百分比…**；气泡另有 **手动宽×高（pt）…**。气泡最小 40%、桌宠最小 35%（约 74×61 pt，仍点得到），最大宽/高均不超过当前屏幕一半；对话气泡高度不足时自动抬高，避免裁字。
- CLI 同步：`config --bubble-width/--bubble-height/--bubble-auto`；状态新增 `bubbleManual / bubbleW / bubbleH / bubbleScaleApplied` 与安全范围。

**验收**

- 审计 **144/144**：新增 MediaRemote 时间戳探针、逐句推进、暂停不误推、桌宠/气泡百分比、手动宽高、最小/最大安全边界等 10 项。
- 本机 280×50 歌词条截图、手动 400×70 截图；本地 LRC 实测第 2/3 句分别在 2.0 s / 4.0 s 切换，误差 <0.1 s。

## 刻意没做的事（避免“假完成”）

- Windows 桌面 GUI 已用 Tk/Pillow 补上，但不是 WinUI/Tauri 原生；Windows 的微交互/字体/透明边缘仍需真实机器核对。
- 没有读取歌曲音频、没有录音、没有 OCR 歌词；只读系统 Now Playing 元数据。
- 没有自动发布到自媒体；文案与素材已准备，发布前需要用户确认账号与措辞。
- 没有饥饿惩罚/强制投喂；米饭是互动，不是打卡压力。

## 用户反馈：主动关闭任务指导

**反馈原话**：加一个功能模块逻辑判断，如果用户想主动关闭任务指导。可以手动在大肥鱼设置里选择关闭指引模式，清空任务，恢复空闲状态。

**改动**

- 设置项 `guideEnabled`（默认开启，旧配置缺省按开启解码）；状态栏与右键菜单共用「任务指导（指引模式）」勾选项。
- 关闭瞬间：清空 `session` 与 `session.json`、收掉所有指针、撤下指导气泡、非唱歌状态强制回 `idle`；有任务时气泡确认「当前任务已清空」。
- 关闭期间 `guide` / `point` / 三步演示统一经 `GuideGate` 拒绝并返回可读错误；`hello` 会告知 Agent「指引已关」。
- 重新开启不做任务恢复，只恢复能力；重启后仍保持关闭，启动时丢弃旧任务。
- 菜单在任务进行中额外提供「结束当前指引」；CLI 增加 `config --guide on|off`，`status` 暴露 `guideEnabled / guideActive`。

**验收**

- 新增审计 10 项：关闭后拒绝 guide/point/demo、session 与指针清零、clip 回 idle、hello 告知、重启保持关闭、重新开启后 guide 恢复。
- 全量审计 **154/154** 通过；内置 `--selftest` 覆盖 `GuideGate` 默认开启/关闭拦截/旧配置缺省。
