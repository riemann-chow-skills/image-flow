# 出片质检 · QA Checklist

生成完先自己看一遍再交给用户。图生视频的失败有很强的规律性，按这张表扫一遍能拦住 90% 的废片。

## 逐帧扫视（3 秒的片子，看 4 个时间点就够）

| 时间点 | 看什么 | 常见问题 |
|---|---|---|
| 第 0 帧 | 是否和原图一致 | 首帧就偏色/变形 → 原图被重绘了，加一致性约束重跑 |
| 0.5s | 主体轮廓 | 脸开始漂、手指变多 |
| 1.5s | 运动是否连续 | 动作卡顿、重复鬼畜、突然跳帧 |
| 末帧 | 是否有崩坏 | 边缘撕裂、线条融化、出现新物体 |

## 六类高频崩坏与对症改法

| 症状 | 原因 | 改法 |
|---|---|---|
| 脸变成另一个人 | 动作幅度太大 / 缺身份锚定 | 降一档力度，prompt 尾部加 `keep the subject's facial identity exactly as in the input image` |
| 手指变多、手变面条 | 手入画 | prompt 里禁止手部动作 `hands stay still and out of frame`，或改构图 |
| 画面整体"融化" | 描述太抽象或动作太快 | 删掉 `dynamic / dramatic / fast`，只留 `slow / subtle` |
| 闪烁、频闪 | 模型逐帧不一致 | 加负向词 `flickering, strobing`，并加 `consistent lighting throughout` |
| 建筑/直线扭曲 | 结构约束缺失 | 加 `straight architectural lines stay rigid and undistorted` |
| 风格漂移（插画变真人） | 缺风格锁 | 加 `keep the original illustration style, line weight and palette exactly` |

## 三条硬门槛

1. **首帧必须等于原图**。如果生成结果的第一帧就和原图不一样，这条片子直接作废——它不再是"这张照片动起来"，而是"照着这张照片另画了一个视频"。
2. **不能有文字**。视频模型生成的文字一定是乱码。原图里有招牌/logo 时，检查是否被改写；必要时在 prompt 里锁 `text and logo remain unchanged`。
3. **动作要"没发生过什么大事"**。3 秒的动图，最好的状态是"你没注意它在动，但盯着看觉得活的"。一旦有大幅度动作，就变成廉价特效。

## 交付前

- 时长是否落在 3 秒（用 `finish.py info` 确认，不要凭感觉）
- 需要循环的，用 `finish.py loop` 出回文版
- 需要发微信/网页的，用 `finish.py gif --webp` 出 webp（比 gif 小 60%，画质好）
- 同一张图做了多版，用 `finish.py compare` 拼成对比条一起交付，让用户挑
