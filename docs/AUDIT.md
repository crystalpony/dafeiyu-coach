# 审计报告 · 桌面大肥鱼 Coach 1.2.0

> 最近运行：2026-10-28（见 `audit/last-report.json`）
> 环境：macOS 15.7.3 · Apple M1 Max · arm64 · 主屏 1728×1117 pt @2x · Xcode CLT Swift 6.0
> 方式：`python3 audit/audit.py`。默认在**临时 HOME** 中安装、运行、截图与卸载，不修改真实的 `~/.dafeiyu` 和 Agent 配置。

## 结论

**154/154 通过。**

| 分组 | 通过 |
| --- | --- |
| 构建与静态 | 11/11 |
| 体积 | 5/5 |
| 安装与适配 | 21/21 |
| 端到端 | 45/45 |
| 音乐 / 歌词 | 9/9 |
| 互动（米饭 / 番茄钟 / 会议） | 4/4 |
| 过渡 | 1/1 |
| 终端轻量版 | 5/5 |
| MCP | 10/10 |
| 性能 | 6/6 |
| 隐私 | 4/4 |
| 文档 | 16/16 |
| 可视化 | 14/14 |
| 卸载 | 3/3 |
| **总计** | **154/154** |

机器可读结果：`audit/last-report.json`；迭代记录见 [ITERATIONS](ITERATIONS.md)。

## 需求 → 证据

| 需求 | 实现 | 审计证据 |
| --- | --- | --- |
| 独立版，不再针对单一教程 | 守护进程 + UNIX socket；任务/设置/会话在 `~/.dafeiyu`；旧 `Coach.swift` 不动 | `e2e` 全组；重启恢复 |
| Agent 对话 / skills 调用 | Qoder / Claude / Codex / dsh 四套 skill、三套 `/dafeiyu`、12 个 MCP 工具 | `install`、`mcp` |
| 指针 + 气泡 | 每屏 overlay；标题/正文/下一句/徽章/进度点 | 截图 01；px 换算；music 截图 04 |
| 多种动画 | 15 段；优先级 + 120–180ms 交叉淡化 | 15 段 play；`blend<1`；截图 02 |
| 一步一步 | guide → next → finish；跨重启恢复 | 三步任务、完成态 |
| 用户主动关闭任务指导 | 菜单「任务指导（指引模式）」/ `config --guide off`：清空任务、指针、指导气泡并回 idle；关闭期间 `guide/point/demo` 拒绝，重启保持 | `e2e` 10 项（清空/拒绝/重启/恢复/hello）+ `--selftest` |
| 空闲陪伴 | 待机小动作、应用感知、游到鼠标、睡觉 | `quip`；截图 03 |
| 音乐检测 + 歌词 + 唱歌 | macOS BSD MediaRemote / Windows SMTC；LRCLIB/本地 LRC；独立唱歌动画 + 头顶紧凑歌词条 | 真机网易云/Apple Music；本地 LRC；`sing` 剪辑；截图 04 |
| 互动（米饭/番茄钟/会议/减少动态） | 独立 rice 动画（白瓷碗朝上/米饭/筷子/热气）+计数、番茄钟、会议模式、减少动态 | `interaction`；截图 05 |
| 储存/性能 | 1.2 MB universal + 7.48 MB 素材 + 669 KB 适配器 | `size`、`perf` |
| 各种 Agent 适配方便 | skills + 命令 + MCP + AGENTS.md + dsh 说明 | `install`、`mcp` |
| GitHub 复用并优化 | MIT 动画素材；BSD MediaRemote；LRCLIB；SMTC 原创 | `NOTICE`；`Runtime/music` |
| 趣味玩法 | 摸头/戳/尾巴/拖拽/双击/米饭/跳舞/游到鼠标/应用反应 | e2e、截图 |
| Windows + macOS | macOS 原生 GUI；Windows 桌面窗口版（Tk/Pillow）+ 终端版；SMTC | Windows CI GUI smoke；`tui` 组 |
| 通过所有审计 | 本文件 + 机器可读报告 | 154/154 |

## 关键数据

| 指标 | 实测 | 阈值 |
| --- | --- | --- |
| 单二进制（universal） | 1.2 MB | < 2 MB |
| 动画素材 | 7.48 MB / 15 组 / 890 帧 | < 8 MB |
| 音乐适配器 | 669 KB | < 1 MB |
| 运行体总计 | ≈ 9.3 MB | < 10 MB |
| 冷启动 | 0.30 s | < 4 s |
| 待机 CPU | 3.6% | < 6% |
| 待机 RSS | 71 MB | < 140 MB |
| 动画 + 指针 CPU | 7.4% | < 14% |
| 动画 + 指针 RSS | 80 MB | < 160 MB |

> 性能受屏幕尺寸、Retina、系统负载影响；此为 M1 Max 采样，不是上限承诺。

## 截图证据

背景已高斯模糊，只保留桌宠、气泡与指针区域，避免暴露桌面内容。

### 1. 指针 + 气泡 + 步骤

![指针 + 气泡 + 步骤](../audit/screenshots/01-guide.png)

### 2. 完成庆祝

![完成庆祝](../audit/screenshots/02-success.png)

### 3. 待机陪伴

![待机陪伴](../audit/screenshots/03-companion.png)

### 4. 歌词 + 唱歌

![歌词 + 唱歌](../audit/screenshots/04-music.png)

### 5. 米饭 + 饭碗

![米饭 + 饭碗](../audit/screenshots/05-rice.png)

### 6. Windows 桌面窗口版（CI 冒烟）

![Windows 桌面窗口版](../audit/screenshots/06-windows-gui.png)

- 真实 Windows Server 2025 CI 桌面：宠物窗口（二值 alpha 抠图）、独立 rice 动画、米饭气泡、指针圈/标签、虚线。
- 冒烟只覆盖渲染与启动；Windows 安装器（含 Pillow/clips）已在 CI 通过；真实 Windows 机器上的拖拽/点击穿透/字体仍需人工复核。

### 7. Windows 歌词唱歌（CI 冒烟）

![Windows 歌词唱歌](../audit/screenshots/07-windows-music.png)

- 同一 Windows CI 桌面上推送 `music_start/lyric`，播放 `sing` 动画，并在鱼头顶显示歌名/当前句的窄歌词条与音符。
- 真实 SMTC 读歌未在 CI 播放；Windows 网易云/QQ 音乐需真实机器验证。

### 8. QQ 音乐真机

![QQ 音乐真机识别](../audit/screenshots/08-qq-music.png)

- 网易云/QQ 音乐/Apple Music 都通过系统 Now Playing；QQ 音乐元数据已真机确认（截图保留的是旧版大气泡，当前版本已改为头顶紧凑条）。
- 该曲无 LRCLIB 歌词时立即显示歌名/歌手并“跟着哼”，不阻塞切歌/暂停。

### 9. 终端轻量版

```text
   /\ 
   ___/  \___
  <  o    o  >   ♪
   \__/\__/
      \/
      ♪   ♫

+----------------------------------------------------------------------+
| 桌面大肥鱼 · 测试                                                    |
| ♪ 1/2                                                                |
| 海风轻轻吹过，我在桌面上陪你。                                       |
+----------------------------------------------------------------------+
  ♪ 桌面大肥鱼 - 测试
    下一句也唱给你听。
  米饭 1 碗 · [f]添饭 [p]摸摸 [space]下一步 [q]退出
```

## 自动化检查覆盖（154 项）

1. **构建与静态（11）**：`swiftc -warnings-as-errors`、构建产物、Python/Shell 语法、内置自测（含会议 App 判断）、素材清单、米饭/唱歌独立剪辑、米饭碗朝上可见、单文件行数、manifest 许可。
2. **体积（5）**：二进制 / 素材 / 音乐适配器 / 运行体 / 源码。
3. **安装与适配（21）**：安装、CLI/daemon/MCP/音乐/终端/素材、四套 skill、三套命令、MCP 配置、doctor、幂等且保留自定义配置。
4. **端到端（45）**：hello、guide（px）、next/prev/finish/cancel、持久化、自动收起、Unicode/长文案、point、15 段 play、趣味互动、hide/show、quiet、scale、桌宠/气泡百分比、手动宽高、安全上限与最小可点击、错误参数、帧动画、stop、僵尸 socket、崩溃重启、会话恢复、socket 0600。
5. **音乐/歌词（9）**：MediaRemote 用 timestamp 补播放位置、music test 唱歌、歌词气泡、独立 sing 动画、歌词条贴头顶且紧凑、music off、暂停不误推空歌词、本地 LRC + watcher 当前行、随时间插值逐句推进。
6. **互动（4）**：米饭计数、独立 rice 动画、番茄钟到点、会议模式到点解除。
7. **过渡（1）**：切换时 `blend<1`。
8. **终端版（5）**：启动核心、CLI 经 TCP 读状态、guide、next/feed/status、stop 清理端口。
9. **MCP（10）**：initialize、12 工具、schema、begin/guide/next/finish/music/focus、完成态。
10. **性能（6）**：启动、待机 CPU/RSS、动画+指针 CPU/RSS、记录。
11. **隐私（4）**：无网络/读屏/合成点击 API（原生）、只监听本机、歌词只访问 LRCLIB、无 TODO。
12. **文档（16）**：README、LICENSE、NOTICE、CHANGELOG、ARCHITECTURE、AUDIT、ITERATIONS、SOCIAL、CI、music README、Windows 安装、AGENTS、dsh、素材署名。
13. **可视化（14）**：5 张 macOS 截图 + 终端渲染 + Windows GUI/歌词 CI 截图 + QQ 真机截图 + 非空检查。
14. **卸载（3）**：移除二进制/skills/music/tui、保留设置、`--purge`。

## 发布后验证（v1.1.0，2026-10-27）

- GitHub 仓库已 public，`v1.1.0` Release 已发布；tag 指向与源码/二进制一致的提交。
- 从 Release 重新下载 macOS / Windows 两个 zip，`shasum -a 256 -c SHA256SUMS` 均为 `OK`。
- Windows CI 对 GUI 冒烟做断言：普通冒烟必须结束在 `rice`，音乐冒烟必须使用 `sing`，并检查截图存在。
- 打包后的 `.app` 在独立 HOME 中启动，读到 15 个 clip；`feed` → `rice`，歌词测试 → `sing` + 280×50 紧凑条；气泡宽高/百分比与安全边界可回归。

## 发布后验证（v1.2.0，2026-10-28）

- GitHub `v1.2.0` Release 已发布，tag 指向 `ca41416`（与源码提交一致）。
- 从 Release 重新下载 macOS / Windows 两个 zip，`shasum -a 256 -c SHA256SUMS` 均为 `OK`。
- 打包后的 `.app` 在独立 HOME 中启动：CLI 与 daemon 均报告 `1.2.0`，读到 15 组 clip；`feed` → `rice`；`guide` 建任务正常。
- 全量审计 154/154；macOS + Windows CI 均通过（[run 40628650943](https://github.com/crystalpony/dafeiyu-coach/actions/runs/40628650943)）。

## 已知限制

- **Windows 桌面版是 Tk/Pillow 实现**，不是原生 WinUI；CI 跑窗口冒烟并上传截图，但尚未在真实 Windows 桌面上人工核对透明/点击穿透/字体。Windows 的 SMTC 也仅做脚本解析与 TUI 核心 CI，未在真实 Windows 上播放网易云/QQ 音乐验收。
- **QQ 音乐**已真机验证元数据（`com.tencent.QQMusicMac` / Avril Lavigne），但该曲 LRCLIB 无可用歌词，显示“跟着哼”；歌词覆盖仍取决于 LRCLIB/本地 LRC。
- **单屏实测**：多屏逻辑已实现，但没有第二块屏证据。
- **交互点击未自动化**：审计不申请辅助功能，不合成鼠标事件；摸头/戳/尾巴/拖拽/双击/关闭按钮/菜单为代码路径 + 手工验收项。
- **全屏 Space 未专门验收**：窗口使用 `.canJoinAllSpaces + .stationary + .fullScreenAuxiliary`。
- **Windows CI**：GitHub Actions 会跑 Python/TUI/TCP/SMTC 语法；真实 Windows GUI 不在本轮。
- **歌词覆盖**：LRCLIB 不是每首歌都有；本地 LRC/跟哼兜底；歌词版权归权利人，不再分发文本。
- **性能数字不是承诺**：RSS 含 AppKit/解码缓存，长时间运行会波动。

## 复现

```bash
cd dafeiyu-coach
python3 audit/audit.py               # 全量（含截图，临时 HOME）
python3 audit/audit.py --no-visual   # 无截图
python3 audit/audit.py --keep-temp   # 保留临时目录
```

手工验收：

```bash
scripts/install.sh
dafeiyu music on
dafeiyu demo
dafeiyu tui
# 播放网易云/Apple Music；观察头顶歌词条与唱歌动画；暂停应收起
# 拖动鱼、点头部/身体/尾巴、双击、右键菜单、添饭、番茄钟、会议模式
```
