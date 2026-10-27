# NOTICE — 来源与许可

本项目是「桌面大肥鱼 Coach」独立版。以下列出直接复用的素材与参考过的开源项目，避免把别人的工作说成自己的。

## 1. 角色动画素材（直接复用，MIT）

- 上游角色：**dsh-pet** — <https://github.com/PC2005-cloud/dsh-pet>
  - 角色名：whale-tail maid（大肥鱼）
  - 许可：MIT（见 `Runtime/clips/ASSET-LICENSE.txt`，随包分发）
  - 采用 commit：`549fff2ea33c2acfb16612c76912c6137da4a758`（记录在 `Runtime/clips/manifest.json`）
- 中间打包：**dsh-dafeiyu** v0.1.18 — <https://github.com/QCYTSN/dsh-dafeiyu>
  - 其 `assets/pet/` 提供了 412×344、24 fps、带 alpha 的 WebP 帧序列与 manifest
  - 本项目只取 13 个剪辑（idle / thinking / working / success / error / pat / poke / tail / eat / stretch / yawn / drag / drop），每隔一帧取样、缩放到 300×250、WebP q45 重编码，得到 820 帧 / 6.90 MB
  - 生成逻辑见 `scripts/build_assets.py`，可复现
- 未使用 dsh-dafeiyu 归档在 `legacy/dafeiyu/` 的旧 BigFish 素材（其许可受限）。

## 2. 交互与工程设计的参考（未复制代码）

- **dsh-dafeiyu**（MIT）：参考了桌面原生 helper 的交互设计——拖拽时循环悬空段、松手播放落地、按头部/身体/尾巴分区、待机微动作与状态映射；本项目的 Swift 动画器、视图、气泡和指针均为新写。
- **openpets**（MIT，<https://github.com/alterhq/openpets>）：参考了「菜单栏 App + CLI + MCP 共享同一只桌宠」的产品分工与工具命名思路；未复制其源码。
- **Neco**（<https://github.com/winebarrel/Neco>）：参考了「桌宠靠近鼠标」的趣味玩法；本项目是独立的缓动实现。
- **原版 `Coach.swift`**（用户自有）：指针环、气泡、关闭按钮、找回圆点、右键菜单等交互延续自原版；独立版重写为多动画、多屏、任务状态机与 socket 控制。

## 2.5 音乐检测与歌词（直接复用 / 第三方服务）

- **MediaRemoteAdapter** — <https://github.com/ungive/mediaremote-adapter>
  - 许可：**BSD-3-Clause**；版权归 ungive 及其贡献者；许可全文见 `Runtime/music/LICENSE-MediaRemoteAdapter.txt`。
  - 本项目只使用 `get` 读取系统 Now Playing；framework 为 universal、ad-hoc 签名。
- **LRCLIB** — <https://lrclib.net/>：开放歌词查询服务。本项目仅发送歌名/歌手/时长，并在本地缓存；歌词版权归各自权利人，界面只作个人同步显示，不随项目再分发歌词文本。
- **Windows SMTC**：`Runtime/music/media_smtc.ps1` 为本项目原创脚本，调用 Windows 公开的 `GlobalSystemMediaTransportControlsSessionManager`；不复制第三方代码。

## 3. 本项目许可

- 代码、文档、skills、CLI、MCP：MIT（见 `LICENSE`）。
- `Runtime/clips/` 的角色素材：沿用上游 MIT 许可；再分发时请保留 `Runtime/clips/ASSET-LICENSE.txt` 与本 NOTICE。
- 本项目不是 DeepSeek Harness、dsh-dafeiyu、openpets 或 Neco 的官方项目，也不代表它们的立场。

## 4. 第三方依赖

- 运行期：macOS AppKit / Foundation / QuartzCore，Python 3 标准库。无第三方 Swift 包、无 pip 依赖、无网络服务。
- 构建素材时可选 Pillow（`python3 -m pip install --user Pillow`）；普通安装不需要，因为压缩后的素材已随包提供。
