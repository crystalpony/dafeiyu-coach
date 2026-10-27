# 三轮迭代记录

> 版本：1.1.0 · 2026-10-27
> 原则：每轮都先写“用户是谁、会在哪里卡住”，再改代码/文案，最后用真实命令和截图验收。不是把功能名重复三遍。

## 基线（迭代前）

- 原生桌宠：13 段动画、指针、气泡、步骤、米饭、番茄钟、会议模式、减少动态。
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

- 新增 `bin/dafeiyu_gui.py`：Tk + Pillow，透明无边框置顶窗口、拖拽、13 段 WebP 动画 + `Image.blend` 交叉淡化、气泡、指针圈、米饭/番茄钟/右键菜单。
- 复用终端版 `Core/Server`：Windows GUI 自己当核心（本机 TCP + token），CLI/MCP/skills 仍可控制；不与 TUI 重复实现状态机。
- Windows 透明色抠图 + Win32 `WS_EX_TRANSPARENT/LAYERED/NOACTIVATE` 点击穿透；`pythonw` 启动无控制台。
- `dafeiyu gui` / `dafeiyu-gui.cmd`；`install.ps1` 复制 clips、安装 Pillow。
- GUI 冒烟：macOS `--check/--smoke`；GitHub Actions Windows 运行 `--smoke` 并上传 `gui-smoke.png`。
- 修：实例属性 `self.smoke` 覆盖方法导致 `TypeError`；默认位置在小屏越界；气泡 accent 未按 tone 着色。

**验收边界**：Windows 窗口版是 Tk/Pillow，视觉与 macOS AppKit 不等同；CI 冒烟≠真实 Windows 人工验收。若要求原生 WinUI/Tauri 级体验，需要下一轮重写。

## 刻意没做的事（避免“假完成”）

- Windows 桌面 GUI 已用 Tk/Pillow 补上，但不是 WinUI/Tauri 原生；Windows 的微交互/字体/透明边缘仍需真实机器核对。
- 没有读取歌曲音频、没有录音、没有 OCR 歌词；只读系统 Now Playing 元数据。
- 没有自动发布到自媒体；文案与素材已准备，发布前需要用户确认账号与措辞。
- 没有饥饿惩罚/强制投喂；米饭是互动，不是打卡压力。
