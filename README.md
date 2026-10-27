# Image Flow · Bring a Still Photo to Life for 3 Seconds

Feed in one photo, get out a ~3 second living clip. Not "slap on a filter and shake it" — the things in the frame actually move according to physical rules.

Output: an `mp4` (3s, with ambient audio) + optional `webp` loop + optional multi-version comparison strip.

## Core Principles

1. **Look at the image before writing the prompt.** Writing a prompt without Reading the image is shooting with your eyes closed. Open it with the Read tool — count the people, trace where the light comes from, find the foreground.
2. **Describe the *change*, not the *picture*.** The picture is already there. Re-describing it tempts the model to redraw, and your first frame stops being your photo.
3. **Keep motion small.** The best 3-second state is "you didn't notice it moving, but it feels alive when you stare." Big gestures instantly read as cheap effects.
4. **Anchor identity hard.** The most common image-to-video failure is a face slowly morphing into someone else. Every prompt needs a consistency constraint.

## When to Use

Activate on a match:

- The user hands over one / a batch of photos and wants them "alive", "as video", "with motion".
- They want micro-expressions on a person, multiple people talking, or scenery flowing.
- They want a looping animation (web background, PPT art, social feed).
- "Reviving" an old photo after restoration.

Do **not** use (say why directly): plain text screenshots / PPT slides / UI screens / charts (motion only blurs the text), or images that already have motion blur (double blur).

## Workflow

> **Path convention**: `$SKILL` is the absolute path of this skill (the Base directory given when the skill loads). Scripts are called with absolute paths; intermediate products land in the user's current working directory so the skill directory stays clean.

### Step 0 · Lock parameters + report cost (required)

| Parameter | Default | Notes |
|---|---|---|
| Duration | Generate 4s → deliver trimmed 3s | The tail often breaks; trimming fixes it |
| Resolution | 1080P | Use 720P if the user finds it pricey / wants a preview |
| Strength | L2 natural | See the three strength tiers below |
| Versions | 1 | Only do A/B/C when the user says "give me a few" |
| Output | `./image-flow/` | Under the current working directory |

**Tell the user the credit cost before doing anything**: video generation charges extra credits (~50–100 credits per 5s). For batches, state "N photos total, roughly N×… expected" and wait for a nod.

### Step 1 · Probe

```bash
python3 $SKILL/scripts/probe.py photo.jpg
```

Read the dimensions, aspect ratio, EXIF orientation, brightness, and recommended parameters it reports. Two warnings must be handled:

- `EXIF orientation 6/8` → a phone portrait shot; straighten it first or the output lies on its side:
  ```bash
  python3 $SKILL/scripts/probe.py photo.jpg --normalize ./image-flow/fixed.jpg
  ```
- `Cannot parse dimensions` (HEIC/AVIF) → same `--normalize` to convert to JPEG.

### Step 2 · Read the image, pick a scene

Open the image with Read and answer four questions (silently — no need to output):

1. What is the main subject? Person / multiple people / empty landscape / city / interior / food / animal / product / old photo / illustration.
2. How many people, where is each (left/center/right), who is the better "actor".
3. Where the light comes from, what the weather is, any movable natural elements (water, trees, clouds, smoke).
4. What must **absolutely not move** (text, logo, facial features, building edges).

Then pull motion sentences from `references/motion-library.md` by scene. That table is pre-sorted into 10 scene categories, each with ready-made English sentences in three strengths plus taboos.

### Step 3 · Assemble the prompt

Follow the five-segment formula in `references/prompt-recipes.md`:

```
[1 Shot]       How the camera moves
[2 Subject]    What the subject does (single actor + amplitude + speed)
[3 Secondary]  Secondary motion (breathing / hair / fabric / light)
[4 Ambient]    Ambient motion (wind / water / clouds / birds / crowds)
[5 Anchor]     Identity and texture constraints
```

60–120 English words. **Write in English** — image-to-video models respond far more accurately to English action words. Use the recipe's default negative prompt string.

### Step 4 · Generate

Call VideoGen in image-to-video mode:

| Parameter | How to fill |
|---|---|
| `image` | Absolute path to the photo (straightened) |
| `prompt` | Result of Step 3 |
| `negative_prompt` | The recipe's negative words, add/remove by subject |
| `seconds` | Prefer `4`; omit if the model rejects custom duration and use its default |
| `resolution` | `1080P`, or `720P` for preview |
| `enable_audio` | `true` for people / real scenes; `false` for loops |
| `aspect_ratio` | **Do not pass** — image-to-video derives it from the image |
| `output_dir` | `./image-flow/` |

For a seamless loop, set `last_image` to the same photo (lock first and last frame; see the recipe doc).

Generation takes 1–3 minutes — **do not call repeatedly**, just wait.

### Step 5 · QA

Walk through `references/qa-checklist.md`: does the first frame equal the original, did the face drift, did fingers multiply, did the last frame melt. If it fails, drop one strength tier and rerun — don't指望 "rolling the dice again".

Quick full-frame preview: `python3 $SKILL/scripts/finish.py sheet result.mp4 -o qa.jpg`

### Step 6 · Finish & deliver

```bash
# Trim to 3 seconds
python3 $SKILL/scripts/finish.py trim result.mp4 -o final.mp4 -d 3
# Seamless loop (forward + reverse)
python3 $SKILL/scripts/finish.py loop final.mp4 -o loop.mp4
# Animated web/WeChat graphic (webp is ~60% smaller than gif)
python3 $SKILL/scripts/finish.py gif final.mp4 -o final.webp --webp --width 600
```

Deliver the trio: `final.mp4` (3s) + `loop.mp4` (loop) + `final.webp` (lightweight). Hand them all to the user at once with present_files.

## Scene Quick Reference

| What's in the frame | Animate | One-liner |
|---|---|---|
| Single person | Breathe, blink, hair, very slow push-in | Person still, mood moves |
| Multiple people | **One person talks**, others nod and smile, exchange glances | Only one actor allowed |
| Empty landscape | Leaves sway, water flows, clouds drift, a bird flies by | Lateral move beats push-in for "breath" |
| City | Traffic, pedestrians, neon flicker, cloud shadows on buildings | Building lines must stay locked |
| Interior | Curtains, dust light shafts, smoke, window light | A very slow push-in is enough |
| Food | Steam rising, oil sheen, condensation | Food shape must not change |
| Animal | Breathing, ears/tail, blink, fur | Don't make it walk |
| Product | Highlight sweep, micro-rotation, background bokeh | Text/logo must stay crisp |
| Old photo | Micro-motion + film grain flicker | Camera barely moves |
| Illustration | Same as real subject, but lock the style | Biggest fear is "real-person-ification" |

## Creative Plays (offer proactively when the user says "any ideas?")

1. **One image, many versions**: run the same image through three camera moves (push-in / lateral / orbit), then `finish.py compare a.mp4 b.mp4 c.mp4 -o compare.mp4` into a strip for the user to pick. Cost doubles, so ask first.
2. **First/last frame loop**: pass both `image` and `last_image` as the original; the model is forced to "go out and come back", yielding a naturally loopable 3 seconds.
3. **3 seconds tell a span of time**: in the prompt, let the light warm and the shadow lengthen — feels one tier above mere shaking.
4. **Micro-event easter egg**: a one-time small event — a bird swoops, a leaf falls, someone walks past the window. One is enough; more becomes a circus.
5. **Sound layer**: turn on `enable_audio` for real scenes; wind, water, and hushed voices lift a "motion graphic" straight to a "short film"; turn it off for loops.
6. **Shot relay**: `finish.py frame --at end` pulls the last frame → use it as the new first frame to generate again → `finish.py concat --fade 0.15` to stitch, making a 6–9s slow long take.
7. **Three emotion tiers**: produce L1 micro / L2 natural / L3 dramatic from the same image, let the user pick "how alive".

## Boundaries & Straight Talk

- Video models can't write; signage/logos in the original may be rewritten — check before delivery.
- Old-photo faces are already blurry; animating adds slight distortion. That's a physical limit — say so upfront.
- Don't lip-sync far-away crowds (tiny faces) — it smears; only write "slight head turn".
- No big head turns or laughs on face close-ups — almost certain to break.
- Video generation takes 1–3 minutes; do batches in order, don't flood concurrently.

## Scripts

| Script | What it does |
|---|---|
| `scripts/probe.py` | Pre-gen check: dimensions / aspect / EXIF orientation / brightness / detail amount → recommended params; `--normalize` to straighten & transcode |
| `scripts/finish.py` | Post-gen finishing: `info` `trim` `loop` `fade` `gif` `frame` `sheet` `compare` `concat` `speed` |

`finish.py` depends on ffmpeg. If not found it auto-searches `FFMPEG_BINARY`, the imageio-ffmpeg bundled binary, and the Homebrew path; if still missing it prompts `brew install ffmpeg` or `pip install imageio-ffmpeg`.
