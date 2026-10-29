# 1.4.0 验收清单 · 五稿修正轮

## 结论

2026-10-29：完整重建 → QA → 原生构建 → 审计 **186/186**，双平台包已核验。完成的是五稿约束下的修复版，不是完整骨骼引擎，也不宣称“陌生人绝对挑不出问题”。真实转身、跳扑、全翻滚、尾巴卷握仍未实现。

开工 10:01:55；最终完整审计于 10:54:47 结束，验证阶段52分52秒；双平台封包于10:59完成；11:03:45完成收尾检查，总历时约62分钟（包含构建与验证等待，不含此前会话）。收尾文档审计16/16、65个本地链接有效；解压后的macOS包签名、独立HOME素材自检与随包文档逐字节比对通过。

## 实际改动

| 项目 | 结果与边界 |
| --- | --- |
| 唯一造型来源 | 只读 `scripts/poses/{front,side,lie,sleep,angry}.png`。五张PNG与开工tar逐一比对SHA，全部未改；未用生图、未添加新角色素材 |
| 生成器 | 582行，25个唯一注册；删除旧base依赖与同名 `@clip` 覆盖。25段 / 1992帧 / 24fps / 300×250保持不变 |
| 嘴眼 | 常态使用原眼原瞳孔；全部正面动作保留原嘴像素。取消程序张嘴：meow是吸气/眨眼与既有猫叫音效，不再宣称嘴型开合。眯眼是平涂表情符号，不是物理眼睑建模 |
| 面部对位 | 先处理局部表情，再与身体做同一次仿射；鼻头独立坐标预测测试通过，五官不再固定在屏幕坐标上 |
| 尾巴 | 单次预乘alpha逆映射，移除原尾巴与变形尾巴的混合；根部/未动区域RGBA恒等，无原算法的宽透明双边 |
| 接地与睡觉 | 固定接地线；取消View对小黑烘焙帧的第二次漂浮/旋转。睡姿关闭真正的主眼，非只闭前景黑咻的眼睛 |
| 播放 | 小黑切换只显示一帧，不跨姿态淡化，不伪造转身。大肥鱼保持原淡化行为。Windows逻辑16ms调度通过伪时钟检查，未当作Windows实机帧率 |
| 立麦 | `sing_mic` 保留兼容ID，改为独立落地“立麦伴唱”，不再画分叉尾巴假装握麦 |
| 动作降级 | wash=眯眼摇头，roll=躺着晃晃，pounce=蓄势一下，fluff=受惊停顿，heixiu=和黑咻玩，yawn=困倦眯眼。原图黑咻保留，不另画新分身 |
| 产物可信度 | manifest记录五稿、生成器和全部帧SHA；每段路径顺序/数量严格核对；源码变化不允许用 `--only` 混入旧帧 |
| iCloud与发布 | 按完整相对路径清理副本，只复制manifest引用帧建立快照。整目录备齐后切换；可捕获异常恢复旧目录，恢复失败保留旧数据。断电/强杀仍依赖外部tar，不声称跨进程原子事务 |

## 已跑验证

- **33项新增单测**：几何14、Swift/Python播放器8、冲突清理与快照6、发布回滚5，全部通过。
- **QA**：1992张WebP逐张解码、边界和SHA检查；75张由当前源码重新生成并逐字节比较；全部循环完整周期回到起点。旧122帧抽样继续保留，`min_top=6 / max_right=285`；原 `limbs_clean`、`mouth_clean` 断言与旧接缝阈值未删除或放宽。
- **负例**：旧尾巴混合算法产生9/12原生像素宽边，被测试拒绝；把idle末帧转移到thinking、总数仍1992的清单被严格帧序检查拒绝，且重渲染数74触发失败。
- **审计186/186**：原178项保留，新增全帧、重渲染、几何/播放器、清理、发布回滚及3张实机证据。分组详见 [审计报告](AUDIT.md) 和 [机器结果](../audit/last-report.json)。
- **真实daemon**：另外观察30.031秒、799采样、239个不同动作帧，始终 `blend=1`，没有跨姿态叠帧；这是播放状态检查，不是GPU实际呈现帧率测试。记录见 [实机观察](../audit/xiaohei-live-soak.json)。
- **原稿完整性**：[五稿SHA对照](../audit/xiaohei-source-integrity.json)；[清单负例](../audit/xiaohei-manifest-negative.json)。

## 证据图（已打开复核）

| 证据 | 来源与对应改进 |
| --- | --- |
| [16：嘴眼对照](../audit/screenshots/16-xiaohei-face-evidence.png) | 开工tar与当前WebP解码：移除重复眼影/程序嘴；不是实机截图 |
| [17：尾巴轮廓](../audit/screenshots/17-xiaohei-tail-evidence.png) | 实际WebP局部放大：原宽透明双边与单次逆映射对照 |
| [18：睡姿实机](../audit/screenshots/18-xiaohei-sleep-live.png) | audit启动的AppKit daemon，主眼闭合 |
| [19：立麦实机](../audit/screenshots/19-xiaohei-mic-live.png) | audit真实屏幕截图，独立落地立麦、无分叉尾巴 |
| [20：帽子实机](../audit/screenshots/20-xiaohei-hat-live.png) | audit真实屏幕截图，帽子与身体共用变换、无叠帧 |

## 产物与体积

引用帧26,737,722字节（25.50 MiB）；含manifest的小黑目录25.69 MiB；双形象运行体35.29 MiB。与开工约27.78 MiB引用帧相比，差异来自移除重画瞳孔/嘴/分身和冗余装饰；段数、帧数、尺寸、帧率未减少。

| 包 | 字节 | 校验 |
| --- | ---: | --- |
| [macOS](../dist/dafeiyu-coach-1.4.0-macos.zip) | 36,703,099 | CRC通过，2882帧与工作区逐字节一致，NOTICE存在 |
| [Windows](../dist/dafeiyu-coach-1.4.0-windows.zip) | 35,543,133 | CRC通过，2882帧与工作区逐字节一致，NOTICE存在 |

[SHA256SUMS](../dist/SHA256SUMS) · [完整包校验结果](../audit/package-verification.json)

macOS SHA256：`02ab4be30ca1a4df25813acb50700a0b538c617e538fbb6f6941a1fa4031b12a`

Windows SHA256：`cb485cd103f4a28a857bb7803b0ac4b3daf967f1f6f6dbe9f11ad79d98541e17`

## 未完成与停点判断

没有真实Windows机器，本轮只在macOS运行跨平台单测，历史Windows CI截图不作为本轮证据。没有公开发布或创建Git提交。

五稿没有跨视角连续关键帧，也没有跳扑、全翻滚、尾巴卷握中间姿态。在“不重绘、不新增肢体、不用morph/淡化伪造转身”约束下，不能把这些动作做成可信的完整连续运动，因此做了明确降级而非继续叠画。**下一短板是跨姿态连续性，需要同造型的过渡关键帧；不是再加淡化。**

历史误报及本轮更正保留在 [CHANGELOG](../CHANGELOG.md) 与 [ITERATIONS](ITERATIONS.md)，不再作为当前通过结论。

## 复验

```bash
python3 scripts/prune_characters.py Runtime/characters
python3 scripts/build_xiaohei.py
python3 scripts/xiaohei_qa.py
bash scripts/build.sh
python3 audit/audit.py
python3 scripts/verify_packages.py dist
```

重建源码或更新帧后，旧ZIP应被包一致性检查拒绝；需要重新封包，不能仅修改校验值。
