# 小黑姿态图 · 反面提示词与出图红线

> 用途：任何一次用生成式模型补图、扩图、修图（包括局部重绘）都必须带上这里的负面提示词；
> 出图后按第 4 节处理，再过 `scripts/xiaohei_qa.py`。正面全身、侧视、躺姿、睡姿、生气五张原稿是唯一造型基准，
> 生成结果只允许做“同造型的补充视角”，不允许重新设计角色。

## 2026-10-29 本轮实际翻车点与守卫

本轮没有调用生成式模型、没有修改五张原 PNG。只使用原稿像素与局部眼睑，不增画肢体、瞳孔或嘴。历史“mouth_clean=true”只是源码字符串守卫，不代表画面真的只有一张嘴。

| 现象 | 根因 | 对应新增守卫 / 处理 |
| --- | --- | --- |
| 喵叫每一帧都张口，首尾不闭嘴 | 同名 `@clip("meow")` 在文件末尾覆盖了前面的修复 | AST 必须25个唯一注册；重复注册真实抛错；meow首尾与静息姿态像素比对。撤掉整个程序张嘴层，保留原嘴，不再宣称开合口型 |
| 眼里多出月牙、五官不跟身体 | 先移动身体再按屏幕固定坐标画眼鼻 | 先局部表情后共同仿射；独立NumPy鼻头变换预测；原嘴全帧恒等；原眼常态ROI恒等 |
| 摆尾边缘存在两层透明轮廓 | `原图*(1-mask)+形变*mask` 同时留下两根尾巴 | 单次逆映射、预乘alpha；独立矩形负例检出旧算法9/12px宽边；新算法边宽不得超过2个原生像素 |
| 摆尾未动区域颜色差1级 | 浮点预乘再除法、截断8位值 | 不动区域必须RGBA逐像素相等，含透明像素；使用舍入而非截断 |
| 睡姿黑咻闭眼而小黑仍睁眼 | 原sleep稿改的是前景小角色眼睛；主眼眼白呈开口月牙，填孔算法漏掉左侧瞳孔 | 单独定位主眼眼睑；主眼亮像素下降>90%；检查旧眼圈不能残留成第二张嘴 |
| 呼吸/唱歌连影子一起浮动 | 帧内已做动作，View又叠加位移/旋转 | 小黑禁用View二次运动；接地阈值>=128的底边必须固定；原生离屏帧比较 |
| 切换变成双脸 | 播放器对任意姿态保存上一帧并淡化 | 小黑所有切换仅显示一帧；Swift与Python真实播放器快速/自动切换测试；大肥鱼淡化保持 |
| Windows标24fps却只显示约14fps | UI每70ms更新 | 小黑改16ms调度；伪时钟逐帧验证，70ms负例只能覆盖15/24帧 |
| 喵叫顶部小黑咻裁边 | 原稿贴近画布顶，伸展后越界 | 未放宽旧边界断言；正面整体等比缩小留余量；新增1992帧逐张解码边界检查 |
| 同名文件躲过冲突副本清理 | prune只比文件名，不比 `idle 2/idle_000.webp` 相对路径 | 改为manifest完整相对路径；打包从明确引用的帧建立干净快照 |
| QA报错但进程返回0 | `ok`在后续检查之前缓存 | 保留旧断言，最终聚合所有失败并返回非零；不能用管道尾命令退出码判断审计成功 |
| 生成器改了，压缩包却装旧帧 | 只查文件数量，不查内容与源码 | manifest记录五稿、生成器与1992帧SHA；QA重新渲染75帧逐字节比较；打包核对所有引用帧 |
| 发布中途失败，活跃目录混入半套新帧 | staging成功后仍逐文件覆盖旧目录 | 先备齐同文件系统的完整目录，再切换；复制失败、两次rename失败与恢复失败五类测试；恢复失败必须保留.previous旧数据。断电/强杀仍依赖外部tar备份，不声称跨进程事务 |
| 总帧数1992仍掩盖单段缺帧 | 只数全局帧、未校验每段路径顺序 | 每段路径必须精确等于name/name_000…序列，强制75重渲染样本数，不能用另一段多一帧抵账 |

表情取舍：眯眼使用原色眼区和闭合弧线，属于平涂符号化表情，不宣称已经完成真实眼睑或完整面部骨骼。常态的原瞳孔、原嘴必须逐像素保留。

立麦替代旧的尾巴分叉麦克风；完整转身、真跳扑、360°翻滚和尾巴卷握在当前五张静态稿中缺失中间姿态，不再用叠图或局部加线冒充。

## 1. 硬性禁止（负面提示词必带）

按项目踩过的坑排序，每条都对应一次真实返工：

| 禁止项 | 出现过的具体问题 | 对应守卫 |
| --- | --- | --- |
| 额外前肢 / 从背后长出的手臂 | 旧版在底图上叠 `arm_specs`，像两根火柴从背后伸出 | `limbs_clean` 禁止 `arm_specs` / `draw_arms` / `cover_front_lines` |
| 后腿 / 人形手臂 / 手指 | 加后腿后动作猎奇，用户要求全部删除 | `limbs_clean` 禁止 `hind_specs` / `draw_hind` / `后肢` / `后腿` |
| 第二张嘴 / 第二个鼻子 | 原画自带 `w` 嘴，再叠一层程序嘴就出现双嘴 | `mouth_clean`：正面/侧脸函数内不得出现嘴形参数 |
| 第二对瞳孔 / 月牙眼影 | 侧面覆盖瞳孔后重画，渲染出双瞳孔 | 侧脸只补蓝鼻头，不覆瞳孔 |
| 残影 / 双脸 / 半透明叠影 | 正面↔侧面交叉淡化做“转身”，出现四只眼 | 不做 morph 转身，只做同姿态内的位移旋转 |
| 悬空 / 缺下半身 | 早期用半身稿做正面，待机时整只飘在空中 | 正面必须全身稿，底边对齐画布 |
| 水印 / 签名 / 屏幕截图纹理 | 原稿是截屏，暗部有淡淡的重影和纹理 | `sanitize_pose()` 抹平暗部噪点 |
| 3D 渲染 / 渐变 / 喷枪 / 厚涂 | 与原著平涂风格冲突 | 只保留纯平涂 + 粗棕描边 |
| 背景 / 地面 / 投影烘焙 | 桌宠需要透明通道，投影由程序画 | 出图必须透明底，且不含任何背景元素 |
| 文字 / UI / 对话框 | 气泡与提示由 App 绘制 | 图像内不得含文字 |
| 换色 / 加花纹 / 加配饰 | 形象不能被改变 | 调色板锁定在第 2 节 |

### 英文负面提示词（直接粘贴）

```
extra limbs, third leg, hind legs, human arms, hands, fingers, detached limbs,
stick arms, arms behind back, duplicated body parts,
second mouth, extra mouth, duplicate nose, extra eyes, double pupils,
cross-eyed, deformed face, melted face, morphing, ghosting, double outline,
motion blur, motion smear, multiple tails, forked tail,
3d render, cgi, gradient shading, airbrush, thick paint, glossy highlight,
texture noise, jpeg artifacts, pixelation,
text, watermark, signature, logo, ui, speech bubble, frame, border,
background, floor, cast shadow, scenery, props not requested,
redesign, restyle, costume change, color shift, pattern, accessory,
cropped body, cut off legs, floating, out of frame
```

## 2. 正向锁定（形象参数，不得漂移）

```
flat color, thick warm dark-brown outline, matte black fur,
large cream sclera with dark oval pupils, tiny mint inner ear,
small blue-gray triangle nose, simple "w" mouth, no muzzle,
short round body, thick front paws, no visible hind legs,
clean silhouette, transparent background, centered, full body, same character sheet
```

统一墨色（`build_xiaohei.py`）：

| 用途 | 值 |
| --- | --- |
| 身体纯黑 | `#0D0B0F` (13, 11, 15) |
| 粗描边 | `#34261E` (52, 38, 30) |
| 奶油眼白 | `#ECF6BF` (236, 246, 191) |
| 薄荷耳内 | `#9CCB48` (156, 203, 72) |
| 鼻头蓝 | `#61A4F1` (97, 164, 241) |
| 舌头 | `#BA6C66` (186, 108, 102) |

## 3. 出图后的对位检查

1. 眼睛中心、鼻头、嘴的落点必须与原稿同坐标系（当前正面锚点：鼻 `(150,146)`、嘴 `(152,166)`）。
2. 侧视只补蓝鼻头；若侧视要张嘴，必须按同一锚点覆盖原嘴，不能新增第二处。
3. 任何新道具（帽子、麦克风、音符）单独一层绘制，允许整体旋转偏移，不合并进角色像素。
4. 暗部统一到第 2 节墨色，亮部（眼白/耳内/鼻头）原样保留。

## 4. 验收顺序

```
python3 scripts/build_xiaohei.py      # 重生成 25 段
python3 scripts/xiaohei_qa.py         # limbs_clean / mouth_clean / loops / 边界
python3 audit/audit.py                # 全量审计
```

三项全绿才算这张图可以进项目；只过其中一项不算。
