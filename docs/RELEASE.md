# 发布说明 · 1.1.0 · 134/134 审计

> 这是**发布准备**，仓库仍为 private；确认验收后转 public 并发布本 release。

## 资产

| 平台 | 文件 | 说明 |
| --- | --- | --- |
| macOS | `dafeiyu-coach-1.1.0-macos.zip` | `Dafeiyu Coach.app`（universal，含 15 段动画/音乐适配器/skills）+ CLI |
| Windows | `dafeiyu-coach-1.1.0-windows.zip` | 桌面窗口版 `dafeiyu gui` + 终端版 `dafeiyu tui` + `install.ps1` + SMTC/clips |
| 校验 | `SHA256SUMS` | 见 `dist/SHA256SUMS`；当前 8.6 MB / 7.7 MB |

## macOS

```bash
unzip dafeiyu-coach-1.1.0-macos.zip
open "Dafeiyu Coach.app"        # 双击后菜单栏出现大肥鱼；自动尝试启动歌词监听
~/.dafeiyu/bin/dafeiyu ...      # 如使用 CLI，建议 scripts/install.sh 安装
```

- app 为 ad-hoc 签名（`codesign --verify --deep --strict` 已通过），但未公证；首次打开如被 Gatekeeper 拦截：右键 → 打开，或 `xattr -dr com.apple.quarantine "Dafeiyu Coach.app"`。
- 已实测：打包 app 用独立 `DAFEIYU_HOME` 启动，菜单栏/桌宠/素材路径正常，CLI `status/stop` 可控制。
- 动画/指针/气泡/米饭/番茄钟/会议模式；Apple Music/网易云/QQ 音乐走系统 Now Playing。
- 歌词：LRCLIB → 可选网易云兜底 → 本地 LRC；`music provider lrclib` 可关闭网易云；中文歌缺失时“跟着哼”。

## Windows

```powershell
Expand-Archive dafeiyu-coach-1.1.0-windows.zip -DestinationPath .
cd dafeiyu-coach-1.1.0-windows
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
# 安装完成后：
dafeiyu-gui.cmd        # 桌面窗口版（需要 Python 3.9+ / Pillow，安装器会装 Pillow）
dafeiyu.cmd tui        # 无 Pillow 的终端版
```

- Windows GUI 为 Tk/Pillow，不是 WinUI/Tauri 原生；CI 冒烟已过，真实机器交互仍需复核。
- 音乐检测用系统 SMTC；歌词来自 LRCLIB/本地 LRC；不读音频、不录音。

## 已知边界

- macOS app 为 ad-hoc 签名，未公证。
- Windows 桌面版透明/点击穿透依赖 Tk/Win32，实际机器字体与边缘需复核。
- 歌词不保证每首歌都有；没有时“跟着哼”。
- 点击/拖拽/菜单属于手工验收项；审计不合成鼠标事件。

## 生成

```bash
./scripts/package.sh
```

产物在 `dist/`（已被 .gitignore 忽略；发布时上传到 GitHub Release）。
