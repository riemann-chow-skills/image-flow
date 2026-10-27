# Prompt 配方 · Prompt Recipes

图生视频的 prompt 不是"描述画面"，而是**描述这 3 秒里发生了什么变化**。画面内容已经在图里了，重复描述画面是浪费 token，还会让模型重绘。

## 五段式结构

按这个顺序写，每段一到两句，总长控制在 **60–120 个英文单词**（工具上限 2500 字符，但超过 150 词就开始互相干扰）。

```
[1 Shot]      镜头怎么动 + 景别
[2 Subject]   主体做什么（幅度 + 速度 + 唯一主动者）
[3 Secondary] 次级运动（呼吸/发丝/衣料/光影）
[4 Ambient]   环境运动（风/水/云/鸟/人流）
[5 Anchor]    一致性与质感约束
```

**模板**

```
[1] Slow cinematic push-in, medium shot, shallow depth of field.
[2] {主体动作}
[3] {次级运动}
[4] {环境运动}
[5] Keep the subject's facial identity, hairstyle, clothing and body proportions exactly as in the input image. Consistent lighting and color. Photorealistic, 24fps film look. Subtle, continuous, slow motion throughout the 3 seconds.
```

**为什么第 5 段要这么写**：图生视频模型最大的失效模式是"身份漂移"（脸慢慢变成另一个人）和"结构漂移"（手指、建筑线条、文字）。把约束放在**最后**是因为大多数模型对 prompt 尾部的约束响应更强；同时 `Subtle, continuous, slow` 这句能压住"动作过大导致崩坏"。

---

## 负向词（默认就带上）

```
face morphing, identity change, different person, distorted face, extra fingers, deformed hands, warped limbs, melting edges, flickering, strobing, sudden cut, scene change, text artifacts, subtitles, watermark, logo distortion, oversaturated, plastic skin, cartoon, low resolution, blurry
```

按题材增删：
- 真人题材 → 加 `uncanny valley, dead eyes, frozen smile`
- 空镜 → 去掉人物相关词，加 `crowd, people, vehicles`（除非需要）
- 插画 → 去掉 `cartoon`，加 `photorealistic, 3d render`
- 产品 → 加 `product shape change, label distortion`

---

## 无缝循环：首尾帧锁死

图生视频工具支持 `last_image`（尾帧）。**把同一张原图同时作为首帧和尾帧**，模型会被迫在这 3 秒里"出去再回来"，得到一段可以无限循环的素材。

```
VideoGen(prompt=..., image=原图, last_image=原图, seconds=4)
```

适用：空镜、水面、烟雾、产品悬浮、氛围图。
不适用：人物说话（说到一半回弹会像鬼畜）。

配套写法：在 prompt 里加一句 `the motion returns to the starting pose at the end`。

若工具不支持或效果不闭合，用 `scripts/finish.py loop` 做回文拼接兜底（正放 + 倒放），视觉上一定无缝。

---

## 三档力度

| 档 | 什么时候用 | 关键词 |
|---|---|---|
| L1 微动 | 证件感肖像、产品主图、需要"高级感"的静态海报 | `very subtle`, `barely perceptible`, `nearly still`, 运镜 `holds nearly still` |
| L2 自然 | **默认**。绝大多数照片 | `subtle`, `gentle`, `slow` |
| L3 戏剧 | 情绪片、预告感、需要"眼前一亮" | `slow but expressive`, `a light breeze lifts`, `slow dolly-in` |

不确定就选 L2。L3 的翻车率大约是 L2 的三倍。

---

## 完整示例

### 例 1 · 双人咖啡桌交谈

```
[1] Slow push-in, medium two-shot, shallow depth of field, warm window light.
[2] The two people talk naturally: the person on the left speaks with small lip movement and a slight hand gesture, the person on the right listens, nods and smiles back. Only one person speaks at a time.
[3] Subtle breathing, natural blinking, hair and collars shift slightly.
[4] Steam rises from the coffee cups, background customers drift slowly out of focus.
[5] Keep every face, hairstyle and clothing identical to the input image. No one stands up or changes position. Consistent lighting. Photorealistic, 24fps. Subtle, continuous, slow motion throughout the 3 seconds.
```

### 例 2 · 湖边空镜

```
[1] Very slow lateral dolly, wide landscape shot.
[2] The water surface ripples continuously, reflections shimmer and shift.
[3] Reeds in the foreground sway gently; light flickers across the ripples.
[4] Clouds drift slowly above the far mountains, a small flock of birds crosses the distant sky.
[5] Keep the composition, horizon line and colors exactly as in the input image. No camera shake. Photorealistic, 24fps. Subtle, continuous, slow motion throughout the 3 seconds.
```

### 例 3 · 产品静物

```
[1] Slow orbit, macro shot, clean studio background.
[2] The product rotates a few degrees on its axis.
[3] A soft highlight sweeps across its surface, reflections glide slowly.
[4] Dust motes float through the key light; background bokeh breathes.
[5] Product shape, text and logo stay sharp and unchanged. Consistent studio lighting. Photorealistic, 24fps. Subtle, continuous motion.
```

---

## 三个进阶技巧

**1. 情绪时间流（3 秒讲一段时间）**
在 prompt 里允许光线变化：`the light gradually warms as if minutes pass, shadows lengthen slightly`。3 秒内看到"天色变了"，观感会比单纯晃动高级得多。

**2. 微事件彩蛋**
给画面塞一个**只发生一次**的小事件：`a bird crosses the frame once, at the second second`、`a single leaf drifts down in the foreground`、`someone walks past the window once`。一个就够，多了变杂耍。

**3. 镜头接龙（延长到 6–9 秒）**
生成 4 秒 → 用 `finish.py frame --at end` 抽出最后一帧 → 以该帧为首帧再生成一段 → `finish.py concat` 拼接。两段之间会有轻微色差，用 `--fade 0.15` 过渡盖掉。适合做慢速长镜头。
