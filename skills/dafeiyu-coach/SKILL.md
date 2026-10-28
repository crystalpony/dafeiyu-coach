---
name: dafeiyu-coach
description: 桌面大肥鱼 Coach —— 在 macOS 桌面上用指针圈、语言气泡和 15 段动画陪用户一步一步完成任务。当用户说“让大肥鱼/桌宠指导我”“指着屏幕教我”“一步一步带我操作”“叫大肥鱼出来陪我”，或需要做可视化 onboarding、软件操作演示、界面导览、跟着我一步步点时使用。Use when the user wants a desktop fish/pet to point at UI, coach them step by step, or give visible on-screen guidance with a pointer ring, speech bubbles, and animations.
---

# 桌面大肥鱼 Coach

你可以在用户的 macOS 桌面上召唤一只大肥鱼。她会：

- 用**指针圈 + 虚线**指向屏幕上的具体位置（鼠标穿透，不挡操作）；
- 用**气泡**说一句很短的话，气泡上有步骤徽章和进度圆点；
- 播放**15 段动画**：待机、思考、工作、成功、出错、摸头、被戳、摇尾巴、吃东西、伸懒腰、打哈欠、被拖走、落地、吃饭、唱歌；
- 把任务拆成步骤，**一步一步陪用户做完**；
- 没任务时待机陪伴（伸懒腰、看应用说一句话、困了打哈欠），不会打扰。

她**不会**读屏、不会点鼠标、不会联网。所有控制都通过本机 UNIX socket（`~/.dafeiyu/coach.sock`）完成。

## 先决条件

```bash
dafeiyu doctor        # 检查守护进程、素材、体积、skills、MCP
dafeiyu start         # 需要时手动启动；多数命令会自动拉起
```

如果 `dafeiyu` 不在 PATH，用 `~/.local/bin/dafeiyu`（安装脚本默认位置）。

## 音乐 / 唱歌（用户放歌时）

当用户说“放歌的时候让大肥鱼唱歌/显示歌词”，或你自己发现系统正在播放音乐：

```bash
dafeiyu music status                 # 当前歌曲 + 监听状态
dafeiyu music on                     # 安装脚本通常已启动；没启动时用
dafeiyu music test --line "测试一句"  # 不联网验证气泡/唱歌
dafeiyu music import-lrc 晴天.lrc --title 晴天 --artist 周杰伦
dafeiyu music offset 0.4             # 歌词对不上时微调
```

- 只在**空闲**、非安静/会议模式时唱歌；有任务时歌词让位给指导。
- 歌词来自系统 Now Playing + LRCLIB/本地 LRC；中文歌缺失时可选网易云兜底（`music provider lrclib` 可关闭）。只发送歌名/歌手/时长，不读音频、不录音。
- 没有歌词就显示“跟着哼”，不要编造歌词。
- 用户说“安静点/在开会” → `dafeiyu quiet on --minutes 60`（会议模式），或菜单「会议模式 60 分钟」。
- 用户说“别指了 / 关掉指导 / 不用你带我” → `dafeiyu config --guide off`，等同菜单里取消勾选「任务指导（指引模式）」：当前任务、指针和指导气泡会立刻清空，桌宠回待机。之后 `guide` / `point` 会被拒绝，不要绕过；用户明确要恢复时再 `config --guide on`。
- 视觉唱歌（气泡+摇摆+音符），不播放 TTS 音频。

## 黄金流程（带用户做一件事）

1. **拆步骤**：把目标拆成 3–7 步，每步只做**一个动作**，一句话说清。能看见的按钮/菜单优先。
2. **打招呼**（每次会话一次）：
   ```bash
   dafeiyu hello --agent qoder      # 换成 codex / dsh / claude
   ```
3. **立任务**（推荐用 JSON 一次传完，带坐标）：
   ```bash
   dafeiyu guide --file guide.json --unit pt
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
   没有坐标也行，只显示气泡；坐标不是必须的。
4. **等用户做完**：不要按定时器自动推进。等用户说“好了/下一步”，或你用其它工具确认完成后，再：
   ```bash
   dafeiyu next --say "很好，接着来下一步。"
   ```
   最后一步 `next` 会自动撒花庆祝。
5. **收尾**：
   ```bash
   dafeiyu finish     # 如果用户想直接结束
   dafeiyu bye        # 回到待机陪伴，不要 quit（quit 会关掉用户的桌宠）
   ```

## 临时指路（不进任务流）

```bash
dafeiyu point --x 520 --y 360 --label "点这个按钮" --hold 12
dafeiyu say "先点这个按钮，再按 ⌘S 保存。" --step "1/3" --hold 8
dafeiyu play success --text "保存好了！"
```

`point` 和 `say` 可以分开调用；`say` 不会清掉指针。一次只指一个目标，用户操作时不要连续刷气泡。

## 坐标怎么给

- 默认 `pt`：**主屏左上角为原点**，x 向右、y 向下。多屏也以主屏左上角为基准。
- 截图量出来的是像素 → 加 `--unit px`（自动按主屏 Retina scale 换算，通常 2x）。
- 只知道大致位置 → 用 `--unit norm`，x/y 取 0~1。
- 指针偏了/想确认缩放：`dafeiyu info` 看主屏尺寸与 scale；`dafeiyu status --json` 里也有 `mainScale`、`screens`。
- 指向**大而稳定的目标**（按钮中心、菜单项、轨道头），不要指文字边缘。

## 气泡怎么写

- 一句话，**动词开头**，60 个汉字以内；需要时用 `hint` 补充“找不到怎么办”。
- 一步只讲一个动作；按键写清楚（⌘S、空格、双击）。
- 不要把整段教程塞进气泡——细节留在聊天里，气泡只给“现在做什么”。
- 语气温柔、具体，不催促；用户卡住时先 `play error --text "..."` 再重新指。

## 动画速查

| clip | 用途 |
| --- | --- |
| `idle` | 默认待机 |
| `thinking` | 你在思考、等待用户确认 |
| `working` | 长任务进行中、指针引导时 |
| `success` | 完成一步/整个任务（会撒花） |
| `error` | 操作失败、需要重试 |
| `pat` | 打招呼、被摸头、开心 |
| `poke` / `tail` | 用户戳她/碰尾巴时的反应 |
| `eat` | 投喂 |
| `stretch` / `yawn` | 待机小动作 / 困了 |
| `drag` / `drop` | 拖动与落地（用户手动拖动时自动播放） |

配合情绪：`dafeiyu mood thinking|focus|happy|sleepy`。

## 陪伴与小玩法

- `dafeiyu feed` 添一碗米饭；`dafeiyu dance` 跳个舞；`dafeiyu come` 游到鼠标旁；`dafeiyu focus --minutes 25` 番茄钟。
- 用户说“安静点” → `dafeiyu quiet on`；“可以说话了” → `dafeiyu quiet off`。
- 她会自己感知前台应用（写代码/查资料/回消息）偶尔说一句，频率有限；不要为了让她说话而反复调用。
- 想藏起来：`dafeiyu hide`；找回：`dafeiyu show`。

## MCP（可选，最省事的接法）

如果当前客户端已配置 `dafeiyu` MCP，可直接用这些工具，语义与 CLI 相同：

`dafeiyu_begin` → `dafeiyu_guide` → `dafeiyu_next` → `dafeiyu_finish` / `dafeiyu_end`
另有 `dafeiyu_point`、`dafeiyu_say`、`dafeiyu_play`、`dafeiyu_status`、`dafeiyu_music`、`dafeiyu_focus`、`dafeiyu_feed`（共 12 个）。

## 终端轻量版

没有 GUI 的机器（Windows/远程/轻量环境）：

```bash
dafeiyu tui                 # 打开 ASCII 宠物，空格下一步、f 添饭、p 摸摸、q 退出
dafeiyu tui --once          # 只渲染一帧（CI/验收）
```

- Windows 桌面窗口版：`dafeiyu gui`（透明置顶、动画/气泡/指针），与 TUI 共用同一核心；无 Pillow 时退回 `dafeiyu tui`。
- 原生版在跑时，`tui` 自动作为显示器附着；否则它自己当核心，CLI/MCP 通过本机 TCP + token 控制。
- 终端版没有鼠标指针圈；`point` 会显示“看这里：标签 (x,y)”。

配置片段在项目的 `adapters/mcp/`；命令为 `dafeiyu mcp`。

## 排障

| 现象 | 处理 |
| --- | --- |
| `连不上大肥鱼守护进程` | `dafeiyu doctor`；`dafeiyu start`；看 `~/.dafeiyu/coach.log` |
| 指针位置偏 | 确认单位（pt/px/norm）与主屏 scale；`dafeiyu info` |
| 气泡被用户收起 | 下一条 `say/guide/next` 会自动展开；也可 `dafeiyu show` |
| `guide` 报「指引模式已被用户关闭」 | 用户在菜单关了任务指导；不要重试或绕过，等用户自己打开，或征得同意后 `dafeiyu config --guide on` |
| 桌宠不见了 | `dafeiyu show`；或点屏幕上的“鱼”小圆点 |
| 动画不动 | 检查 `dafeiyu status` 是否 `sleeping`；任意命令会唤醒 |
| 想彻底退出 | `dafeiyu stop`（会移除 socket、保留设置） |

## 边界

- 只做**可视化指导**：不代替用户点击、不自动填表、不读取屏幕内容。
- 音乐只读系统 Now Playing 元数据（歌名/歌手/时长），不读音频、不录音；歌词可能来自 LRCLIB，注意版权与网络开关。
- 不改用户文件、不执行破坏性命令；需要改文件时先在对话里说明并征得同意。
- 不把坐标、路径、日志发到网络；一切都在本机。
- 用户没让你召唤时不要主动弹桌宠；任务结束后用 `bye`，别用 `quit`。

## 一段完整对话的样子

> 用户：教我把这段代码在 Xcode 里跑起来。
>
> Agent：好，我让大肥鱼出来带你。`dafeiyu hello --agent qoder`
> Agent：（拆 4 步，拿到 Xcode 工具栏坐标）`dafeiyu guide --file xcode.json`
> 大肥鱼：气泡「第 1/4 步 · 先选顶部的 iPhone 模拟器」，指针指着模拟器菜单。
> 用户：选好了。
> Agent：`dafeiyu next --say "选好了，按 ⌘R 运行。"`
> … 最后 `dafeiyu finish`，大肥鱼撒花；`dafeiyu bye` 回到待机。
