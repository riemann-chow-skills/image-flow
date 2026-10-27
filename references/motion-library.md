# 动效词库 · Motion Library

按「画面里有什么」查表。每个场景给出：**可动元素**、**推荐运镜**、**三档力度的英文动效句**、**禁忌**。

英文句子可直接拼进 prompt。所有句子都刻意写得短、动词具体、幅度可量化（slow / subtle / slight），因为图生视频模型对"幅度副词"最敏感——写 `slight` 就真的轻微，写 `dynamic` 就容易崩脸。

---

## 1. 单人肖像 / 人像

**可动元素**：呼吸起伏、眨眼、眼珠微动、发丝、衣料、嘴角、肩线、背景虚化光斑。
**运镜**：极缓推近（slow push-in）> 轻微横移（micro lateral drift）。**不要**用摇镜（pan），摇镜最容易把脸摇变形。

| 力度 | 动效句 |
|---|---|
| L1 微动 | `The subject breathes softly, blinks naturally once, a few strands of hair shift slightly. Camera holds nearly still with a very slow push-in.` |
| L2 自然 | `The subject breathes, blinks, and gives a subtle smile; hair and collar move gently. Slow cinematic push-in.` |
| L3 戏剧 | `The subject slowly turns their head toward the light, hair lifts in a light breeze, eyes shift to camera. Slow dolly-in with shallow depth of field.` |

**禁忌**：大幅转头、嘴部大张（会崩牙）、快速眨眼（会闪烁）、手入画（会多指）。

---

## 2. 多人 / 群像（交谈场景）

这是最容易做砸的一类。核心原则：**指定唯一的主动者**，其他人只做"回应"，绝不让所有人同时动。

**可动元素**：转头对视、点头、口型、微笑、手势、肩部转向、杯/手机等手持物、背景人流。

**分镜写法**（把画面里的人按位置命名：left / center / right）：

| 力度 | 动效句 |
|---|---|
| L1 微动 | `The group stays in conversation: the person on the left nods slightly while the person on the right smiles; subtle head turns and natural blinking, no one leaves their position.` |
| L2 自然 | `The two people talk naturally: the person on the left speaks with small lip movement and a slight hand gesture, the person on the right listens, nods and smiles back. Eye contact switches between them. Camera slowly drifts right.` |
| L3 戏剧 | `The person on the left laughs and leans back slightly, the person on the right turns to face them and responds; shoulders and hands move naturally, background passers-by drift slowly out of focus. Slow push-in.` |

**三条硬约束**（必须写进 prompt）：
- `only one person speaks at a time`
- `no one stands up, walks away, or changes position`
- `keep every face and hairstyle identical to the input image`

**远景/合照**（人脸占画面很小）：放弃 lip-sync，只写 `subtle head turns and weight shifts`，否则小脸口型会糊成一片。人群用 `crowd sways gently, a few people walk past in the background`。

---

## 3. 空镜风景

**可动元素**：树叶/草/芦苇/麦浪、水面波纹与倒影、云、雾、光斑、飞鸟、雨雪、炊烟、花瓣。
**运镜**：极缓横移（slow lateral dolly）比推近更有呼吸感；水面题材用极缓下摇。

| 题材 | 动效句 |
|---|---|
| 树林/枝叶 | `Leaves sway gently in the breeze; a few leaves detach and drift slowly across the frame. Sunlight flickers through the canopy.` |
| 水面/溪流/海浪 | `Water flows continuously with rippling surface and shifting reflections; gentle waves break in rhythm.` |
| 天空/远山 | `Clouds drift slowly across the sky, their shadows sliding over the landscape; light gradually shifts.` |
| 花田/草地 | `Grass and flowers ripple in soft waves of wind, petals float past the lens.` |
| 雪/雾 | `Fine snow falls steadily, mist drifts slowly through the scene, visibility breathes.` |
| 鸟/动物入画 | `A small flock of birds crosses the distant sky; the scene otherwise holds still.` |

**加分句**（几乎任何空镜都适用）：`Distant birds cross the sky.` / `A light breeze moves the foreground.` / `The light changes subtly as a cloud passes.`

**禁忌**：不要给空镜加"镜头快速移动"，观众会晕；不要同时写风+雨+雪+雾，模型会画成噪点。

---

## 4. 城市街景 / 建筑

**可动元素**：车流、行人、红绿灯、招牌霓虹、云影、水面倒影、旗帜、晾晒衣物。
**运镜**：横向滑轨（lateral tracking）、轻微升镜（slow crane up）。

`Traffic flows steadily along the street, pedestrians walk past at different depths, neon signs flicker softly, clouds drift above the skyline. Slow lateral tracking shot.`

**禁忌**：建筑线条是模型最容易"融化"的地方——必须加 `straight architectural lines stay rigid and undistorted`。

---

## 5. 室内 / 家居 / 静物

**可动元素**：窗帘、尘埃光柱、蜡烛/香薰烟雾、热气、植物、宠物、窗外光影移动。
**运镜**：极缓推近或横移，不要手持。

`Curtains breathe gently in the draft, dust motes float through the beam of light, the shadows on the wall shift slowly. Very slow push-in.`

---

## 6. 美食

**可动元素**：热气/白烟、油脂反光、酱汁流动、饮料气泡、餐具微动、手部入画。
**运镜**：45° 缓推 + 浅景深。

`Steam rises continuously from the dish, oil glistens and shifts, condensation beads on the glass. Slow push-in with shallow depth of field.`

**禁忌**：别让食物"变形"——加 `the food keeps its exact shape, no melting or morphing`。

---

## 7. 动物 / 宠物

**可动元素**：呼吸、耳朵/尾巴摆动、眨眼、毛发、舌头、爪子。
**运镜**：与肖像同，极缓推。

`The animal breathes steadily, blinks, twitches an ear and flicks its tail once; fur moves slightly in the breeze.`

**禁忌**：四条腿是重灾区，别让它走路；只做"原地小动作"。

---

## 8. 产品 / 商品

**可动元素**：高光扫过、反光流动、烟雾/水花、背景虚化光斑、轻微悬浮旋转。
**运镜**：环绕（orbit）或直线推近。

`A soft highlight sweeps across the product surface, reflections glide slowly, the product rotates a few degrees on its axis. Clean studio lighting, slow orbit.`

**禁忌**：产品文字/logo 会糊——加 `product text and logo remain sharp and unchanged`。

---

## 9. 老照片 / 黑白 / 复古

**可动元素**：人物微动 + 胶片颗粒抖动 + 轻微曝光闪烁 + 边缘暗角呼吸。
**运镜**：几乎固定机位，只用 2% 的推近。

`The scene comes gently to life: the subject blinks and breathes, film grain shimmers, exposure flickers slightly like 8mm footage. Camera is nearly locked off.`

**注意**：先告知用户"老照片里的人物往往看不清五官，动起来会有轻微失真"，这是物理限制，不是 bug。

---

## 10. 插画 / 动漫 / 3D 渲染

**可动元素**：与真实题材一致，但风格约束必须写死。

`Keep the original illustration style, line weight and color palette exactly; animate within the existing 2D/3D style, no added realism, no style drift.`

**禁忌**：最容易被模型"真人化"，风格漂移是这类图的第一大问题。

---

## 不适用

- 纯文字截图、PPT 页、UI 界面、图表 → 动起来只会糊字，应直接拒绝并说明。
- 已含运动模糊的图 → 会双重模糊。
- 分辨率低于 640px 的图 → 生成必糊，先提醒。
