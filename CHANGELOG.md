# Changelog

## 1.4.0 — 2026-10-29 五稿修正与可信验收

- **生成器收敛**：重写为582 行，仅使用 `scripts/poses/` 五稿；五张原 PNG 的 SHA 不变。删除旧 base 依赖与同名 `@clip` 覆盖，唯一注册 25 段 / 1992 帧 / 24fps；未使用图像生成，原大肥鱼行为不改。
- **纠正伪造表情**：恢复源眼原瞳孔，删除全部程序嘴，嘴像素保持原图；`meow` 仅吸气/眨眼 + 既有音效，不张嘴。上一轮“首尾闭嘴”结论错误：末尾定义覆盖成恒定 `0.55`。先做局部表情再共同仿射，避免脸漂移；`sleep` 改为闭主眼，旧版闭的是黑咻。
- **几何与播放**：摇尾改为单次预乘 alpha 逆映射，消除双轮廓；固定接地线。小黑所有播放切换均单帧切画，不再 crossfade，也不称作转身；关闭小黑 View 二次 bob/旋转，Python 小黑 GUI 调度由 70ms 改为 16ms。
- **诚实降级**：`sing_mic` ID 兼容，显示“立麦伴唱”，取消尾巴分叉持麦；`wash=眯眼摇头`、`roll=躺着晃晃`、`pounce=蓄势一下`、`fluff=受惊停顿`、`heixiu=和黑咻玩`、`yawn=困倦眯眼`。保留原图黑咻，不新增分身。五稿缺少真实转身、跳扑、全翻滚、尾巴卷握的中间姿态，在不补稿、不加肢体的约束下这些均未实现；本轮不是完整骨骼引擎。
- **验证机制**：保留原 QA 守卫，增强 QA 解码全部 1992 帧、核验 SHA、重新生成 75 帧逐 byte 比较并检查全循环周期；manifest 增加五稿/生成器/每帧 SHA，prune 按完整相对路径处理 `idle 2/` 与同名文件。
- **已验证**：10:01:55 开工；首轮 185/185，复核后补发布回滚与逐段帧序检查，最终完整回路于 10:54:47 达到 **186/186**。33 项新增单测全过；旧 ghost 与总数仍为1992的错段清单负例被拒绝。QA逐张解码1992帧、比对75张重渲染，全循环整数周期通过，旧抽样边界 min_top=6 / max_right=285。引用帧25.50 MiB，含清单25.69 MiB，双形象运行体35.29 MiB；像素对照16–17、AppKit真实截图18–20已复核。真实daemon观察30.031秒/799采样，无叠帧。跨平台单测在macOS运行，本轮没有Windows实机验收。
- **发布可靠性**：整套目录备齐后切换，捕获到发布失败即恢复旧目录；五类故障测试涵盖复制、移动及恢复失败，恢复失败保留旧备份。强杀/断电仍须依赖开工tar，不宣称跨进程原子事务。打包只按manifest引用复制、逐帧核对SHA，macOS包补齐NOTICE/LICENSE等声明；打包校验入口为 `scripts/verify_packages.py`。

> 以下版本记录保留历史原文；其中小黑程序张嘴、尾巴持麦、新分身、交叉淡化及“已完成”的描述均被本轮修正覆盖，旧审计和体积数字不代表当前产物。当前验收以 `docs/ACCEPTANCE-1.4.md` 为准。

## 1.4.0 — 2026-10-28（历史记录）

### 新增

- **前肢重做（本轮重点）**：正面改用新补的全身正面稿（厚前腿、自带嘴形、头顶小黑咻）；彻底删除旧的附加前臂 `arm_specs` / `draw_arms` / `cover_front_lines` 与相关 `p.arms` 逻辑；正面动作直接使用原画前腿，不再从背后长出“火柴棍”。新增用户插图的多视角姿态 `side` / `lie` / `sleep` / `angry`：拖拽、落地、摇尾用侧视，打滚/睡觉用躺姿，出错/被戳用生气脸；整身只做呼吸、弹跳、旋转与位移。QA 守卫扩展为禁止这些前臂名字回归。
- **小黑的唱歌舞台**：在原有 `sing` 上增加 `sing_mic`（尾巴卷起麦克风）、`sing_hat`（街舞帽弹跳）、`sing_tail`（坐直摇尾）3 种变体；4 种变体全部 24fps、300×250、96 帧无缝循环。麦克风、帽子、音符都是平涂道具，不新增手臂/腿，不改变手绘底图。
- **自动编排**：菜单「唱歌 → 唱歌花样」支持自动 / 只律动 / 尾巴麦克风 / 街舞帽 / 坐直摇尾；自动模式每 8–16 秒偶发切换，同曲不连续重复同一种特别动作，统一 0.36s 交叉淡化。新增「试唱一段（20 秒）」菜单，不依赖音乐监听即可预览；试唱/音乐超时后自动回到 idle，不会停在唱歌循环。
- **喵喵叫开关**：`settings.meowEnabled` 控制待机随机喵；「小黑设置 → 待机随机喵喵叫」或 `dafeiyu config --meow off` 关闭后，手动「喵一声 / 喵两声」仍可用。`喵两声` 复用同一段 36 帧动作连播；新增 CC0 猫叫音效 `Runtime/sounds/xiaohei_meow.wav`（0.85s）和独立「喵叫音效」开关；修复 `ClipPlayer` 回调后自动回 idle 会把第二段顶掉的问题；Windows GUI 也加入喵一声/喵两声与独立音效开关。
- **菜单信息架构**：顶层收敛为「互动与专注 / 小黑日常 / 唱歌 / 陪伴与指导 / 形象 / 显示与尺寸 / 小黑设置」7 组；原来的动作、陪伴、尺寸、气泡、位置功能全部保留。
- **唱歌 CLI**：`dafeiyu config --sing-style auto|sway|mic|hat|tail`；status 新增 `singStyle` / `singVariant` / `singVariants` / `meowEnabled`。
- **小黑日常菜单**：新增「小动作 / 玩耍 / 吃什么 / 时节 / 移动 / 说句话 / 碎碎念 / 工作状态」；时节含 15 个平涂实时道具（灯笼、粽子、月饼、南瓜、礼物、红包、菊花、落叶、雪人、烟花、腊八粥、年糕、青团、福字等），不烘焙进角色帧。
- **产品升级计划**：收到对标菜单截图，新增 [docs/PRODUCT_UPGRADE.md](docs/PRODUCT_UPGRADE.md) 的「3.1 与截图逐项对照」：覆盖 10/13 类目；转向与账号余额档位有意不做。
- **贴图统一与口型修正**：新增 `sanitize_pose()`，把五张手绘姿态稿的暗部收敛到同一套墨色（身体 `#0D0B0F`、描边 `#34261E`），抹掉截屏留下的浅色噪点，切换姿态不再跳色；侧脸去掉会飘到轮廓外的腮红；喵叫删除“戳脸线条”，改为对齐原画 `w` 嘴的张口层（含舌头），仍然只有一张嘴；街舞帽单独成层整体歪戴，完整盖住头顶小黑咻，不再出现“半张脸压在帽子下”；新增 `wag_tail_side()` 对侧视尾巴做根部固定的横向形变，`tail` 与 `sing_tail` 的尾巴是真的在摆，不再靠虚线道具暗示。反面提示词与红线见 [docs/POSE-NEGATIVE-PROMPTS.md](docs/POSE-NEGATIVE-PROMPTS.md)。

### 验证

- 小黑 **25 段 / 1992 帧 / 27.84 MB**；双形象合计 **40 组 / 2882 帧 / 37.44 MB**。
- QA 抽查 122 帧 alpha 边界，无裁切；新增唱歌变体全部进入动作总览。
- 审计新增喵喵叫开关、唱歌花样固定、尾巴麦克风变体 3 项，并把菜单/节日道具截图纳入非空校验，**178/178**；双平台包重建。
- 实机验证：固定 `sing_mic` / `sing_hat` / `sing_tail` 均能播放；自动模式 18 秒内从 `sing` 切到 `sing_mic`，切换期间 `blend=0.31` 平滑过渡。4 段唱歌循环的所有周期都取 4 秒整数分频，循环接缝差异 1.14–3.56，与相邻帧差 0.91–3.04 同级，无跳帧；QA 增加生成器“后肢/侧伸前爪”回归守卫。

## 1.3.0 — 2026-10-28

### 新增

- **第二形象：小黑（罗小黑猫形态）**。底图为**项目所有者手绘定稿并提供授权**；`scripts/build_xiaohei.py` 做透明化/去白边、眨眼与表情、嘴型、尾巴网格摆动、抬爪与道具的逐帧合成，300×250、24fps、**22 段动作**：通用 15 段（idle / thinking / working / success / error / pat / poke / tail / eat / stretch / yawn / drag / drop / rice / sing）+ 小黑专属 7 段（wash 洗脸 / roll 打滚 / pounce 扑 / fluff 炸毛 / sleep 睡觉 / meow 喵 / heixiu 召唤黑咻）。每段带独立表情与道具（鱼、饭、汗滴、落地星星、肥皂泡、速度线、黑咻小分身等）。`--preview` 出审稿 contact sheet。
- **手动切换形象**：菜单栏「形象」→ 大肥鱼 / 小黑；`dafeiyu character [name]`、`dafeiyu config --character xiaohei` 等价；选择写入 `settings.json`，重启保持。状态新增 `character` / `displayName` / `characters`。
- **动画器支持素材根目录**：`ClipPlayer` 接收 `assets`，两套 300×250 素材共用同一套动画/优先级/交叉淡化逻辑；切换后重建播放器并刷新菜单栏图标（鱼 / 猫爪）。
- **打包与安装**：macOS `.app`、Windows zip、`install.sh` / `install.ps1` 都带上 `Runtime/characters`；`.app` 启动脚本导出 `DAFEIYU_CHARACTERS`。
- **前肢与骨骼**：新增两前爪的肩/肘/腕关节路径；抬爪/持物时遮掉底图的三条静止前腿线；`scripts/xiaohei_qa.py` 输出前肢骨骼叠加图并抽查新增动作每帧的 alpha 边界（不裁耳、不越界）。小黑动作只驱动两前爪与尾巴，不含其他肢体动画。
- **小黑专属互动**：菜单「小黑互动」（洗脸/打滚/扑/炸毛/黑咻/喵/喂鱼/睡觉/叫醒）、双击打滚、待机随机小动作、闲置 10 分钟睡觉循环。
- **审计 172/172**：新增 22 段素材完整性、前肢/骨骼 QA（抽查 78 帧）、双形象切换与全部 22 段播放、骨骼叠加/新增动作两张证据图、安装产物、体积预算与真机截图。

### 修复

- **打滚/炸毛被误读为后腿**：删除向身体两侧平伸的附加前爪姿势，两个动作改由身体压缩/摆动、尾巴、表情与道具表现；帧数仍 1704，小黑素材 22.00 MB。
- **张嘴时胸前的“獠牙”**：张嘴帧遮住原画前腿线顶部，避免两条腿线从嘴下伸出像獠牙；全 22 段重生成，帧数仍 1704。

### 许可

- 小黑底图为项目所有者手绘并提供授权，派生动画与该底图**不适用 MIT 代码许可**；角色版权归 MTJJ / 北京寒木春华动画。调研过的社区仓库无 LICENSE，未复用其图片或代码。详见 NOTICE。

## 1.2.0 — 2026-10-28

### 修复

- **歌词整首不前进**：MediaRemote 的 `elapsedTime` 是 timestamp 时刻的位置，网易云/QQ 常返回 0；改为 `elapsedTime + timestamp + playbackRate` 推算真实位置。
- watcher 元数据 0.5 s 刷新 + 歌词行 0.1 s 本地插值；LRCLIB 与网易云并行、5 s 预算；暂停/切歌容错两拍。
- `music on` 会重启旧版本 watcher，并清理重复进程，避免两条歌词流互相覆盖。

### 新增 / 调整

- **任务指导总开关**：菜单栏 / 右键菜单新增「任务指导（指引模式）」。关闭时立刻清空当前任务、指针与指导气泡，桌宠回到待机；关闭期间拒绝 `guide` / `point` / 三步演示，重新开启即恢复。状态写入 `settings.json`，重启后仍保持关闭；CLI 对应 `config --guide on|off`。
- 歌词条默认 **280×50 pt**（原 316×62），字号/徽标随高度自适应。
- 菜单「桌宠大小」「气泡大小」支持直接输入百分比；气泡新增手动宽×高（pt）。
- 安全边界：桌宠最小 35%、气泡最小 40%，最大宽/高均不超过屏幕一半；对话气泡高度不足时自动抬高。
- CLI：`config --bubble-width/--bubble-height/--bubble-auto`；状态补充手动宽高与安全范围字段。
- 审计 154/154（在上一批 144 项基础上新增指引开关 10 项：清空/拒绝/重启/恢复/hello）。

## 1.1.0 — 2026-10-27

### 新增

- **音乐检测 / 歌词 / 唱歌**：Apple Music、网易云、QQ 音乐等系统 Now Playing；LRCLIB + 本地 LRC；空闲时播放独立唱歌动画，歌词以紧凑歌词条贴在头顶（只显示歌名与当前句，超长自动省略），并伴随摇摆和音符；`music on/off/status/now/test/import-lrc/offset`。
- **米饭动画独立**：新增 `rice` 剪辑，白瓷碗朝上、米饭、筷子、热气逐帧绘制，不再复用 eat token 动画。
- **BSD MediaRemote 适配器**（macOS 15.4+） + Windows SMTC 脚本；歌词 watcher 仅发送歌名/歌手/时长。
- **Windows 桌面窗口版** `dafeiyu gui`：Tk + Pillow，透明置顶、15 段动画/交叉淡化、气泡、指针、米饭、右键菜单；与 TUI 共用 Core/Server；`install.ps1` 安装 Pillow/clips；启动时声明 DPI 感知，避免高 DPI 位图拉伸发糊。
- **终端轻量版** `dafeiyu tui`：ASCII 宠物、歌词、步骤、米饭；Windows/macOS/Linux；本机 TCP + token；原生版运行时自动附着显示。
- **互动**：添一碗米饭（饭碗/米饭/筷子/热气 + 计数）、番茄钟、会议模式（到点自动解除、会议 App 抑制）、减少动态。
- **动画过渡**：优先级队列、同剪辑不重启、120–180ms 双层交叉淡化、气泡淡入、去重复 play。
- **Windows**：`scripts/install.ps1`、SMTC 适配器、GitHub Actions Windows CI；原生 GUI 仍是 macOS。
- 二进制 universal（arm64 + x86_64）；音乐 framework universal。
- MCP 12 个工具（新增 `dafeiyu_music`、`dafeiyu_focus`）。

### 修复 / 增强
- 网易云歌词兜底（可选）：LRCLIB 缺中文歌时补同步歌词；`music provider lrclib` 可关闭。
- 歌词先立即显示歌名，网络取词后台线程；LRCLIB 503 不再阻塞切歌/暂停。

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
