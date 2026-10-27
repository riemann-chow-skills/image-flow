#!/usr/bin/env python3
"""成片收尾 · 图生视频之后的确定性加工

VideoGen 出来的片子通常是 4–5 秒、尾巴带崩坏、体积偏大、不能循环。
这个脚本用 ffmpeg 把它修成能交付的东西：裁到 3 秒、无缝循环、淡入淡出、
导出 webp/gif、抽帧、拼对比条、镜头接龙。

子命令：
    info    查看时长/分辨率/帧率/有无音轨
    trim    裁剪到指定时长（默认从 0 开始，可 --start 指定起点）
    loop    回文循环（正放+倒放），视觉上绝对无缝
    fade    淡入淡出（默认 0.3s）
    gif     导出 gif 或 webp（webp 体积小 60%，画质更好）
    frame   抽一帧（start / mid / end / 秒数）—— 镜头接龙用
    sheet   九宫格缩略图，快速质检
    compare 多条片子横向拼成对比条（一图多版时交付）
    concat  多条片子首尾相接（可带交叉淡化）
    speed   变速（1.25 加速 / 0.8 慢放）

示例：
    python3 finish.py trim in.mp4 -o out.mp4 -d 3
    python3 finish.py loop in.mp4 -o loop.mp4
    python3 finish.py gif in.mp4 -o out.webp --webp --width 600
    python3 finish.py compare a.mp4 b.mp4 c.mp4 -o compare.mp4
    python3 finish.py sheet in.mp4 -o sheet.jpg

ffmpeg 不在 PATH 时会自动找：环境变量 FFMPEG_BINARY、imageio-ffmpeg 自带的二进制、
常见 Homebrew 路径。都找不到会给出安装命令。
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

# ---------- ffmpeg 定位 ----------

def find_ffmpeg(explicit=None):
    for cand in (explicit, os.environ.get("FFMPEG_BINARY"), shutil.which("ffmpeg")):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    try:
        import imageio_ffmpeg  # type: ignore
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass
    patterns = [
        os.path.expanduser("~/.workbuddy-ai/binaries/python/envs/*/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*"),
        os.path.expanduser("~/Library/Python/*/lib/python/site-packages/imageio_ffmpeg/binaries/ffmpeg-*"),
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
    ]
    for pat in patterns:
        for p in glob.glob(pat):
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    return None


FFMPEG = None
DRY = False


def need_ffmpeg():
    global FFMPEG
    if FFMPEG:
        return FFMPEG
    FFMPEG = find_ffmpeg()
    if not FFMPEG:
        sys.exit(
            "找不到 ffmpeg。任选一种装上后重试：\n"
            "  brew install ffmpeg\n"
            "  pip install imageio-ffmpeg        # 会自带一份二进制，无需系统权限\n"
            "装好后重新运行本命令即可。"
        )
    return FFMPEG


def run(args, quiet=False):
    cmd = [need_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y"] + args
    if DRY:
        print(" ".join(cmd))
        return ""
    if not quiet:
        print("  $ " + " ".join(cmd[:3]) + " …")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        tail = (p.stderr or "").strip().splitlines()[-6:]
        sys.exit("ffmpeg 失败：\n  " + "\n  ".join(tail))
    return p.stderr or ""


def probe(path):
    if not os.path.isfile(path):
        sys.exit(f"文件不存在：{path}")
    cmd = [need_ffmpeg(), "-hide_banner", "-i", path]
    p = subprocess.run(cmd, capture_output=True, text=True)
    text = (p.stderr or "") + (p.stdout or "")
    info = {"file": os.path.abspath(path), "bytes": os.path.getsize(path)}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", text)
    if m:
        info["duration"] = round(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)), 3)
    m = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", text)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+\.?\d*)\s*fps", text)
    if m:
        info["fps"] = float(m.group(1))
    info["audio"] = "Audio:" in text
    info["codec"] = (re.search(r"Video:\s*([\w\d]+)", text).group(1) if re.search(r"Video:\s*([\w\d]+)", text) else None)
    return info


def duration_of(path):
    d = probe(path).get("duration")
    if not d:
        sys.exit(f"读不到时长：{path}")
    return d


def target_size(path):
    """取第一条片子的尺寸作为拼接目标（宽高取偶数，libx264 要求）。"""
    info = probe(path)
    w, h = info.get("width"), info.get("height")
    if not w or not h:
        return 1920, 1080
    return w - w % 2, h - h % 2


# ---------- 子命令 ----------

def cmd_info(a):
    info = probe(a.input)
    if a.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return
    print(f"\n▸ {os.path.basename(info['file'])}")
    if "width" in info:
        print(f"  {info['width']}×{info['height']}  {info.get('fps', '?')}fps  {info.get('codec')}")
    print(f"  时长 {info.get('duration', '?')}s   音轨 {'有' if info['audio'] else '无'}   {info['bytes']/1024/1024:.2f}MB")


def cmd_trim(a):
    start = a.start or 0
    dur = a.duration
    total = duration_of(a.input)
    if dur is None:
        dur = max(0.5, total - start)
    if start + dur > total + 0.05:
        print(f"  提示：片长只有 {total}s，裁到 {start}–{min(total, start+dur):.2f}s")
        dur = max(0.3, total - start)
    args = ["-ss", f"{start:.2f}", "-i", a.input, "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-crf", str(a.crf), "-preset", "medium",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    args += ["-an"] if a.no_audio else ["-c:a", "aac", "-b:a", "128k"]
    run(args + [a.output])
    print(f"✓ {a.output}  {dur:.2f}s")


def cmd_loop(a):
    """回文拼接：正放 + 倒放，首尾天然衔接。"""
    d = duration_of(a.input)
    fc = "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0[v]"
    run(["-i", a.input, "-filter_complex", fc, "-map", "[v]",
         "-c:v", "libx264", "-crf", str(a.crf), "-preset", "medium",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", a.output])
    print(f"✓ {a.output}  {d*2:.2f}s 无缝循环（静音）")


def cmd_fade(a):
    d = duration_of(a.input)
    f = min(a.duration, d / 2 - 0.05)
    vf = f"fade=t=in:st=0:d={f},fade=t=out:st={d-f:.2f}:d={f}"
    args = ["-i", a.input, "-vf", vf]
    if probe(a.input)["audio"] and not a.no_audio:
        args += ["-af", f"afade=t=in:st=0:d={f},afade=t=out:st={d-f:.2f}:d={f}", "-c:a", "aac"]
    else:
        args += ["-an"]
    run(args + ["-c:v", "libx264", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", a.output])
    print(f"✓ {a.output}  淡入淡出 {f:.2f}s")


def cmd_gif(a):
    fps = a.fps
    w = a.width
    if a.webp:
        vf = f"fps={fps},scale={w}:-1:flags=lanczos"
        run(["-i", a.input, "-vf", vf, "-c:v", "libwebp", "-lossless", "0",
             "-q:v", str(a.quality), "-compression_level", "6", "-loop", "0", "-an", a.output])
    else:
        vf = (f"fps={fps},scale={w}:-1:flags=lanczos,split[s0][s1];"
              f"[s0]palettegen=max_colors=160:stats_mode=diff[p];"
              f"[s1][p]paletteuse=dither=bayer:bayer_scale=3")
        run(["-i", a.input, "-filter_complex", vf, "-loop", "0", "-an", a.output])
    size = os.path.getsize(a.output) / 1024
    print(f"✓ {a.output}  {size:.0f}KB")


def cmd_frame(a):
    d = duration_of(a.input)
    at = a.at
    if at == "start":
        t = 0.0
    elif at == "mid":
        t = d / 2
    elif at == "end":
        t = max(0.0, d - 0.12)
    else:
        t = float(at)
        if t > d:
            t = max(0.0, d - 0.12)
    run(["-ss", f"{t:.3f}", "-i", a.input, "-frames:v", "1", "-q:v", "2", a.output])
    print(f"✓ {a.output}  @ {t:.2f}s")


def cmd_sheet(a):
    d = duration_of(a.input)
    cells = a.cols * a.rows
    fps = max(cells / max(d, 0.1), 0.1)
    vf = (f"fps={fps:.4f},scale={a.width}:-1:flags=lanczos,"
          f"drawtext=text='%{{pts\\:hms}}':x=8:y=8:fontsize=14:fontcolor=white@0.85:box=1:boxcolor=black@0.4,"
          f"tile={a.cols}x{a.rows}")
    try:
        run(["-i", a.input, "-vf", vf, "-frames:v", "1", "-q:v", "3", a.output], quiet=True)
    except SystemExit:
        # 部分 ffmpeg 构建没有 drawtext（缺 fontconfig），退化为无时间戳版本
        vf = f"fps={fps:.4f},scale={a.width}:-1:flags=lanczos,tile={a.cols}x{a.rows}"
        run(["-i", a.input, "-vf", vf, "-frames:v", "1", "-q:v", "3", a.output])
    print(f"✓ {a.output}  {a.cols}×{a.rows} 缩略图")


def cmd_compare(a):
    ins = a.inputs
    if len(ins) < 2:
        sys.exit("compare 至少需要两条视频")
    h = a.height
    parts, labels = [], []
    for i, p in enumerate(ins):
        parts.append(f"[{i}:v]scale=-2:{h},setsar=1[v{i}]")
        labels.append(f"[v{i}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"hstack=inputs={len(ins)}[v]"
    args = []
    for p in ins:
        args += ["-i", p]
    run(args + ["-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "20",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", a.output])
    print(f"✓ {a.output}  {len(ins)} 条并排对比")


def cmd_concat(a):
    ins = a.inputs
    if len(ins) < 2:
        sys.exit("concat 至少需要两条视频")
    W, H = target_size(ins[0])
    norm = ("[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            "pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[n{i}]")
    args = []
    for p in ins:
        args += ["-i", p]
    if a.fade > 0:
        # 交叉淡化：逐段 xfade，offset 必须按累计时长算，否则会黑屏
        durs = [duration_of(p) for p in ins]
        fc = [norm.format(i=i, w=W, h=H) for i in range(len(ins))]
        prev, acc = "n0", durs[0]
        for i in range(1, len(ins)):
            off = max(0.0, acc - a.fade)
            fc.append(f"[{prev}][n{i}]xfade=transition=fade:duration={a.fade}:offset={off:.3f}[x{i}]")
            acc = acc + durs[i] - a.fade
            prev = f"x{i}"
        out = prev
    else:
        fc = [norm.format(i=i, w=W, h=H) for i in range(len(ins))]
        fc.append("".join(f"[n{i}]" for i in range(len(ins))) + f"concat=n={len(ins)}:v=1:a=0[v]")
        out = "v"
    run(args + ["-filter_complex", ";".join(fc), "-map", f"[{out}]",
                "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", "-an", a.output])
    print(f"✓ {a.output}  {len(ins)} 段相接")


def cmd_speed(a):
    r = a.rate
    if r <= 0:
        sys.exit("--rate 必须大于 0")
    vf = f"setpts=PTS/{r}"
    af, tempo = [], r
    while tempo > 2.0:
        af.append("atempo=2.0")
        tempo /= 2.0
    while tempo < 0.5:
        af.append("atempo=0.5")
        tempo /= 0.5
    af.append(f"atempo={tempo:.4f}")
    args = ["-i", a.input, "-vf", vf]
    if probe(a.input)["audio"] and not a.no_audio:
        args += ["-af", ",".join(af), "-c:a", "aac"]
    else:
        args += ["-an"]
    run(args + ["-c:v", "libx264", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", a.output])
    print(f"✓ {a.output}  {r}× 变速")


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="图生视频成片收尾工具", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("示例：")[-1])
    ap.add_argument("--dry-run", action="store_true", help="只打印 ffmpeg 命令，不执行")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, multi=False, need_output=True):
        if multi:
            p.add_argument("inputs", nargs="+", help="输入视频")
        else:
            p.add_argument("input", help="输入视频")
        if need_output:
            p.add_argument("-o", "--output", required=True, help="输出文件")
        p.add_argument("--crf", type=int, default=18, help="画质，越小越好，默认 18")

    p = sub.add_parser("info", help="查看视频信息"); common(p, need_output=False)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("trim", help="裁剪时长"); common(p)
    p.add_argument("-d", "--duration", type=float, default=3.0, help="目标时长，默认 3")
    p.add_argument("-s", "--start", type=float, default=0.0, help="起点秒数")
    p.add_argument("--no-audio", action="store_true")
    p = sub.add_parser("loop", help="回文无缝循环"); common(p)
    p = sub.add_parser("fade", help="淡入淡出"); common(p)
    p.add_argument("-d", "--duration", type=float, default=0.3); p.add_argument("--no-audio", action="store_true")
    p = sub.add_parser("gif", help="导出 gif/webp"); common(p)
    p.add_argument("--webp", action="store_true", help="导出 webp（推荐）")
    p.add_argument("--width", type=int, default=480); p.add_argument("--fps", type=int, default=15)
    p.add_argument("--quality", type=int, default=75)
    p = sub.add_parser("frame", help="抽一帧"); common(p); p.add_argument("--at", default="end")
    p = sub.add_parser("sheet", help="九宫格质检图"); common(p)
    p.add_argument("--cols", type=int, default=3); p.add_argument("--rows", type=int, default=2)
    p.add_argument("--width", type=int, default=360)
    p = sub.add_parser("compare", help="并排对比"); common(p, multi=True); p.add_argument("--height", type=int, default=540)
    p = sub.add_parser("concat", help="首尾相接"); common(p, multi=True); p.add_argument("--fade", type=float, default=0.0)
    p = sub.add_parser("speed", help="变速"); common(p); p.add_argument("--rate", type=float, default=1.25)
    p.add_argument("--no-audio", action="store_true")

    a = ap.parse_args()
    global DRY
    DRY = a.dry_run
    {"info": cmd_info, "trim": cmd_trim, "loop": cmd_loop, "fade": cmd_fade, "gif": cmd_gif,
     "frame": cmd_frame, "sheet": cmd_sheet, "compare": cmd_compare, "concat": cmd_concat,
     "speed": cmd_speed}[a.cmd](a)


if __name__ == "__main__":
    main()
