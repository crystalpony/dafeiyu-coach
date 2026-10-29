# 审计报告 · 桌面大肥鱼 Coach 1.4.0

最近完整运行：**2026-10-29 10:54:47，186/186通过**。权威机器结果：[audit/last-report.json](../audit/last-report.json)。

方式：`python3 audit/audit.py` 在临时HOME中安装、启动原生daemon、端到端调用、实际截图、卸载；不修改真实HOME的Agent配置。另对用户实际运行的daemon做30秒状态观察，记录分开保存。

## 分组

| 分组 | 通过 |
| --- | --- |
| 构建与静态 | 20/20 |
| 体积 | 7/7 |
| 安装与适配 | 22/22 |
| 端到端 | 45/45 |
| 双形象切换 | 9/9 |
| 音乐与歌词 | 9/9 |
| 互动 | 4/4 |
| 大肥鱼淡化过渡 | 1/1 |
| 终端轻量版 | 5/5 |
| MCP | 10/10 |
| 性能 | 6/6 |
| 隐私 | 4/4 |
| 文档 | 16/16 |
| 可视化 | 25/25 |
| 卸载 | 3/3 |
| **总计** | **186/186** |

原178项断言保留。新增8项：1992帧解码/哈希、75帧重渲染、几何/播放器回归、冲突清理回归、发布故障恢复、sleep/mic/hat三张实机无叠帧证据。通过数不等于完整骨骼或主观美术验收。

## 小黑具体检查

- 25段 / 1992帧 / 24fps / 300×250；五稿SHA与开工备份相同，生成器无第二造型源。
- QA保留原 `limbs_clean` / `mouth_clean` 和循环接缝断言；新增每段精确帧序、全帧alpha边界/哈希、75张重新编码逐字节一致、全部循环整周期一致。旧抽样122帧的 `min_top=6 / max_right=285`。
- 新增33项单测：几何14、双播放器8、清理快照6、发布故障5。旧双尾轮廓负例（9/12像素宽边）、总数仍1992的错段清单负例被拒绝。
- 正面原嘴像素保留，不再有程序张嘴。侧脸不增加嘴或新瞳孔。小黑所有姿态切换仅显示一帧；大肥鱼淡化测试仍通过。
- [实际daemon观察](../audit/xiaohei-live-soak.json)：30.031秒、799采样、239个不同动作帧，全部 `blend=1`。不把播放状态采样说成GPU呈现帧率。

## 实测体积与包

| 指标 | 实测 |
| --- | --- |
| universal二进制 | 1418 KiB |
| 大肥鱼素材 | 7.48 MiB / 890帧 |
| 小黑引用帧 | 26,737,722字节 / 25.50 MiB |
| 小黑含manifest | 25.69 MiB |
| 音乐适配器 | 669 KiB |
| 仅大肥鱼运行体 | 9.59 MiB |
| 双形象运行体 | 35.29 MiB |

双平台ZIP各2882帧，CRC、外层SHA、清单与工作区逐帧内容一致、NOTICE均通过：[包校验](../audit/package-verification.json)、[SHA256SUMS](../dist/SHA256SUMS)。这里只发布本地dist产物，未公开发布。

## 证据与限制

[嘴眼对照16](../audit/screenshots/16-xiaohei-face-evidence.png)与[尾巴对照17](../audit/screenshots/17-xiaohei-tail-evidence.png)来自实际WebP，不冒充屏幕截图。

[睡姿18](../audit/screenshots/18-xiaohei-sleep-live.png)、[立麦19](../audit/screenshots/19-xiaohei-mic-live.png)、[帽子20](../audit/screenshots/20-xiaohei-hat-live.png)是本轮AppKit真实截图。屏幕背景做隐私模糊，桌宠/气泡保留清晰。

本轮没有Windows真机、多屏、全屏Space或完整鼠标交互自动验收。历史Windows CI截图存在不代表新版本在Windows验收通过。测试中的跨平台播放器在macOS上运行；SMTC实际播放仍需Windows设备。

五稿缺少转身、跳扑、全翻滚和卷握中间姿态，本轮做有限动作并诚实改名，不冒充完整连续运动。详细逐条结论、备份和时间见 [ACCEPTANCE](ACCEPTANCE-1.4.md)；历史版本记录见 [ITERATIONS](ITERATIONS.md)。

## 复验

```bash
python3 scripts/prune_characters.py Runtime/characters
python3 scripts/build_xiaohei.py
python3 scripts/xiaohei_qa.py
bash scripts/build.sh
python3 audit/audit.py
python3 scripts/verify_packages.py dist
```

源码或素材变化后，旧ZIP应当被最后一项拒绝；必须重新封包。捕获到发布异常时恢复旧目录；断电/强杀仍需要外部tar，不保证跨进程原子事务。
