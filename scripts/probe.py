#!/usr/bin/env python3
"""图片预检 · 图生视频前的确定性体检

在图生视频之前把"这张图能不能动、该用什么参数"算清楚，避免白烧积分。

用法：
    python3 probe.py photo.jpg
    python3 probe.py ./photos/            # 整个目录
    python3 probe.py photo.heic --normalize out.jpg   # 转正 + 转码为 sRGB JPEG
    python3 probe.py photo.jpg --json     # 只输出 JSON，方便脚本消费

输出：每张图的尺寸、比例、EXIF 方向、亮度/清晰度（装了 Pillow 才有）、
风险提示，以及推荐的生成参数（时长 / 分辨率 / 是否需要先转正）。

只用标准库即可运行；装了 Pillow 会额外做亮度与细节量分析，并能 --normalize。
"""

import argparse
import json
import os
import struct
import sys

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic", ".heif", ".avif", ".tif", ".tiff"}

try:
    from PIL import Image, ImageStat, ImageFilter  # type: ignore
    HAS_PIL = True
except Exception:
    HAS_PIL = False


# ---------- 标准库尺寸解析 ----------

def _exif_orientation(tiff: bytes):
    """从 TIFF 头里读 IFD0 的 0x0112 方向标签。"""
    try:
        if len(tiff) < 8:
            return None
        bo = "<" if tiff[:2] == b"II" else ">"
        ifd_off = struct.unpack(bo + "I", tiff[4:8])[0]
        if ifd_off + 2 > len(tiff):
            return None
        count = struct.unpack(bo + "H", tiff[ifd_off:ifd_off + 2])[0]
        for i in range(count):
            base = ifd_off + 2 + i * 12
            if base + 12 > len(tiff):
                break
            tag, typ = struct.unpack(bo + "HH", tiff[base:base + 4])
            if tag == 0x0112 and typ == 3:
                return struct.unpack(bo + "H", tiff[base + 8:base + 10])[0]
    except Exception:
        pass
    return None


def _jpeg(data: bytes):
    w = h = None
    orient = None
    i = 2
    n = len(data)
    while i < n - 3:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
            i += 2 if marker != 0xFF else 1
            continue
        seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\x00\x00":
            orient = _exif_orientation(data[i + 10:i + 2 + seglen])
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            break
        i += 2 + seglen
    return w, h, orient


def _webp(data: bytes):
    if data[12:16] == b"VP8X":
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
        return w, h
    if data[12:16] == b"VP8L":
        b = int.from_bytes(data[21:25], "little")
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if data[12:16] == b"VP8 ":
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    return None, None


def dimensions(path: str):
    """返回 (width, height, exif_orientation)，解析不了就是 (None, None, None)。"""
    with open(path, "rb") as f:
        head = f.read(32)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", head[16:24])
            return w, h, None
        if head[:2] == b"\xff\xd8":
            f.seek(0)
            return _jpeg(f.read())
        if head[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", head[6:10])
            return w, h, None
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            f.seek(0)
            w, h = _webp(f.read(64))
            return w, h, None
        if head[:2] == b"BM":
            w, h = struct.unpack("<ii", head[18:26])
            return abs(w), abs(h), None
    return None, None, None


# ---------- 图像质量分析（需要 Pillow） ----------

def quality(path: str):
    """返回亮度均值、对比度、细节量（0-100 归一化），失败返回 None。"""
    try:
        with Image.open(path) as im:
            im = im.convert("L")
            if max(im.size) > 900:
                im.thumbnail((900, 900))
            stat = ImageStat.Stat(im)
            mean = stat.mean[0]
            std = stat.stddev[0]
            edge = im.filter(ImageFilter.FIND_EDGES)
            detail = ImageStat.Stat(edge).mean[0]
        return {
            "brightness": round(mean, 1),
            "contrast": round(std, 1),
            "detail": round(min(100.0, detail * 4), 1),
        }
    except Exception:
        return None


# ---------- 主流程 ----------

def human_size(n):
    return f"{n/1024:.0f}KB" if n < 1024 * 1024 else f"{n/1024/1024:.1f}MB"


def aspect_label(w, h):
    r = w / h
    for name, target in (("16:9", 16 / 9), ("9:16", 9 / 16), ("1:1", 1.0), ("4:3", 4 / 3), ("3:4", 3 / 4), ("3:2", 3 / 2), ("2:3", 2 / 3)):
        if abs(r - target) / target < 0.02:
            return name
    return f"{r:.2f}:1"


def analyze(path: str):
    size = os.path.getsize(path)
    w, h, orient = dimensions(path)
    info = {
        "file": os.path.abspath(path),
        "format": os.path.splitext(path)[1].lower().lstrip("."),
        "bytes": size,
        "width": w,
        "height": h,
        "aspect": aspect_label(w, h) if w and h else None,
        "exif_orientation": orient,
        "issues": [],
        "recommend": {},
    }

    ext = "." + info["format"]
    if w is None:
        info["issues"].append("无法解析尺寸：可能是 HEIC/AVIF，先转成 JPEG")
        info["recommend"] = {"need_convert": True}
        return info

    mp = w * h / 1e6
    info["megapixels"] = round(mp, 2)

    if orient and orient != 1:
        info["issues"].append(f"EXIF 方向为 {orient}（手机竖拍常见），生成前必须转正，否则视频会横躺")
    if min(w, h) < 640:
        info["issues"].append(f"短边仅 {min(w, h)}px，低于 640，生成结果会糊")
    if ext in (".heic", ".heif", ".avif"):
        info["issues"].append("HEIC/AVIF 兼容性差，先转 JPEG")
    if size > 25 * 1024 * 1024:
        info["issues"].append("文件超过 25MB，部分接口会拒收，建议压到 5MB 内")
    if info["aspect"] and info["aspect"] not in ("16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"):
        info["issues"].append("比例较极端（全景/长图），生成时会被裁切或加边")

    q = quality(path) if HAS_PIL else None
    if q:
        info["quality"] = q
        if q["brightness"] < 40:
            info["issues"].append("画面偏暗，暗部运动容易出噪点，建议先提亮或选 L1 微动")
        if q["brightness"] > 215:
            info["issues"].append("画面过曝，高光区运动会糊成一片")
        if q["detail"] < 6:
            info["issues"].append("细节量低（可能是大光圈虚化或失焦），动作幅度要小")
    elif not HAS_PIL:
        info["issues"].append("未安装 Pillow，跳过亮度/清晰度分析")

    # 推荐参数
    rec = {
        "seconds": 4,          # 生成 4s，交付时裁到 3s（尾部往往是崩坏段）
        "trim_to": 3,
        "resolution": "1080P" if min(w, h) >= 1080 else "720P",
        "aspect": info["aspect"],
        "intensity": "L1" if (q and q["detail"] < 8) else "L2",
        "need_normalize": bool(orient and orient != 1) or ext in (".heic", ".heif", ".avif"),
    }
    info["recommend"] = rec
    return info


def normalize(src: str, dst: str, max_side: int = 1920):
    if not HAS_PIL:
        print("需要 Pillow 才能转正：pip install pillow", file=sys.stderr)
        return False
    from PIL import ImageOps
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode != "RGB":
            im = im.convert("RGB")
        if max(im.size) > max_side:
            im.thumbnail((max_side, max_side), 3)
        im.save(dst, "JPEG", quality=94, subsampling=0)
    return True


def main():
    ap = argparse.ArgumentParser(description="图生视频前的图片体检")
    ap.add_argument("target", help="图片路径或目录")
    ap.add_argument("--normalize", metavar="OUT", help="转正 + 转码为 sRGB JPEG 后保存到 OUT（需 Pillow）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    ap.add_argument("--max-side", type=int, default=1920, help="--normalize 时的长边上限，默认 1920")
    args = ap.parse_args()

    if not os.path.exists(args.target):
        sys.exit(f"路径不存在：{args.target}")

    if os.path.isdir(args.target):
        files = sorted(
            os.path.join(args.target, f) for f in os.listdir(args.target)
            if os.path.splitext(f)[1].lower() in IMG_EXT and not f.startswith(".")
        )
        if not files:
            sys.exit("目录里没有可识别的图片")
    else:
        files = [args.target]

    if args.normalize:
        if len(files) != 1:
            sys.exit("--normalize 只支持单张图片")
        ok = normalize(files[0], args.normalize, args.max_side)
        if not ok:
            sys.exit(1)
        print(f"已转正保存：{os.path.abspath(args.normalize)}")
        return

    results = [analyze(p) for p in files]

    if args.json:
        print(json.dumps(results if len(results) > 1 else results[0], ensure_ascii=False, indent=2))
        return

    for r in results:
        print(f"\n▸ {os.path.basename(r['file'])}")
        if r["width"]:
            q = r.get("quality")
            qs = f"  亮度 {q['brightness']} / 对比 {q['contrast']} / 细节 {q['detail']}" if q else ""
            print(f"  {r['width']}×{r['height']}  {r['aspect']}  {r['megapixels']}MP  {human_size(r['bytes'])}{qs}")
        rec = r["recommend"]
        print(f"  推荐：{rec.get('resolution', '-')} · 生成 {rec.get('seconds', '-')}s → 交付裁 {rec.get('trim_to', '-')}s · 力度 {rec.get('intensity', '-')}")
        if rec.get("need_normalize"):
            print("  ⚠ 建议先转正：python3 probe.py 图片 --normalize fixed.jpg")
        for issue in r["issues"]:
            print(f"  · {issue}")
        if not r["issues"]:
            print("  ✓ 无风险项")

    if len(results) > 1:
        print(f"\n共 {len(results)} 张。批量生成前记得先跟用户确认积分消耗。")


if __name__ == "__main__":
    main()
