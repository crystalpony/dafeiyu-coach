# 发布素材（GitHub / 小红书 / 抖音）

> 发布素材已定稿；小红书/抖音草稿等待登录账号后保存，发布前再做一次账号与措辞确认。

## GitHub

仓库已公开：<https://github.com/crystalpony/dafeiyu-coach>（MIT）

Release：[v1.2.0](https://github.com/crystalpony/dafeiyu-coach/releases/tag/v1.2.0)
Topics：`macos` `desktop-pet` `ai-agents` `mcp` `lyrics` `swift` `appkit` `terminal`

Release 1.2.0 资产（附 SHA256）：
- `dafeiyu-coach-1.2.0-macos.zip`（universal .app / 二进制 + Runtime）
- `dafeiyu-coach-1.2.0-windows.zip`（桌面窗口版 + 终端版 + SMTC 脚本 + 安装 ps1）
- `SHA256SUMS`

README 首屏：
- 一张原生桌宠指针+气泡截图
- 一张网易云歌词唱歌截图
- 一张终端版截图
- 一行安装命令 + 一句“macOS 原生 / Windows 终端轻量版”

发布前检查：
- [ ] `python3 audit/audit.py` 全绿
- [ ] GitHub Actions macOS + Windows 全绿
- [ ] LICENSE / NOTICE / 素材许可齐全
- [ ] 不包含用户聊天、桌面、歌曲封面等隐私截图
- [ ] 公开仓库前确认仓库名与 MIT 许可

## 小红书（图文，5 图）

已生成 6 张 1080×1440 图文：
1. `docs/social/xhs-01.png` — 封面
2. `docs/social/xhs-02.png` — Agent 指屏幕
3. `docs/social/xhs-03.png` — 放歌跟唱
4. `docs/social/xhs-04.png` — 添米饭
5. `docs/social/xhs-05.png` — Windows 桌面窗口版
6. `docs/social/xhs-06.png` — Windows 歌词唱歌
7. 可替换：`audit/screenshots/08-qq-music.png` — QQ 音乐真机

抖音竖屏：`docs/social/dafeiyu-demo-9x16.mp4`（15.3s，6 段图文，无音轨，上传后加平台音乐）。

标题：**我把大肥鱼桌宠做成了会唱歌的桌面搭子**

正文：
> 它会在你放歌的时候，趴在屏幕角落唱着歌，头顶一条窄歌词条一句一句显示歌词；点它是摸头，拖它是搬家，喂它是米饭，不是小鱼干。
>
> 更实用的是：Qoder / Codex / Claude / dsh 在对话里调用它，它就用指针圈和气泡一步一步带你操作软件。没有任务时，它会自己伸懒腰、打哈欠、偶尔说一句。
>
> Mac 原生版 + Windows 终端轻量版；本地 socket、不读屏、不录音，歌词只把歌名/歌手发给 LRCLIB，也可以完全离线用本地 .lrc。

标签：#桌宠 #大肥鱼 #AI工具 #效率工具 #Mac软件 #Windows软件 #独立开发

置顶评论：项目已开源，搜 `crystalpony/dafeiyu-coach`，Release 里有 macOS .app 和 Windows 包。

## 抖音（30 秒竖屏脚本 / 图文）

抖音优先竖屏 30 秒实拍：用 macOS 演示舞台 `dafeiyu stage on` 录屏，剪成 9:16；没有录屏时用 5 张竖版图文。

1. 0-3s：桌面角落的大肥鱼在待机，字幕“这是我的桌面搭子”。
2. 3-10s：打开网易云，头顶歌词条出现，鱼张嘴跟唱，字幕“放歌时它会跟着歌词唱”。
3. 10-18s：拖米饭到嘴边、点摸头、番茄钟，字幕“喂饭、摸头、专注，都会回应”。
4. 18-25s：Qoder 对话里 `dafeiyu guide`，指针圈指向按钮，字幕“Agent 还能让它指屏幕教你”。
5. 25-30s：终端版 `dafeiyu tui`，字幕“Mac 原生 + Windows 终端，GitHub 开源”。

## 抖音文案

> 它会指屏幕教你操作，也会在你放歌时跟着歌词摇。Mac 原生 + Windows 桌面窗口版，独立米饭动画、番茄钟、会议模式都有。GitHub 开源。 #桌宠 #大肥鱼 #AI工具 #效率工具

## 诚实边界（发布时保留）

- Windows 桌面窗口版是 Tk/Pillow 实现，不是 WinUI/Tauri 原生；CI 冒烟通过，真实机器交互仍需复核。
- 歌词来自 LRCLIB 或本地文件，不保证每首歌都有；没有的会显示“跟着哼”。
- 不读屏、不录音、不自动点击；指针坐标由 Agent 提供。
- 不使用饥饿/惩罚机制。


## 发布进度（2026-10-27）

- GitHub：仓库已公开，v1.1.0 Release 已发布（macOS/Windows/SHA256）。
- 抖音：已保存草稿（15.3s 竖屏视频 + 标题/简介/话题），未发布；在创作者中心“继续编辑”可复核。
- 小红书：Chrome 已登录（账号“驹长的 AI 工具日记”），6 图草稿已保存（2026-10-27 23:38，标题“放歌时跟着歌词唱的大肥鱼桌宠”，117 字正文+话题），未发布；草稿存于当前浏览器本地。
