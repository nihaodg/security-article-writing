#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给真实网页截图加红框 + 来源条 + 裁边/补白/缩放。

用法：
  python png_mark.py in.png out.png [选项]

选项：
  --box x,y,w,h          画红框（可多次；坐标是输入图像像素）
  --box-color r,g,b      红框颜色（可多次，按顺序对应 --box）
  --box-json file.json   读取 shot_section_mark.js / web_shot.js 产出的框坐标
  --caption "文字"       底部来源条文字（站点 + 路径 + 抓取日期）
  --caption-pos top|bottom
  --trim-left N --trim-right N --trim-top N --trim-bottom N
  --pad N                四周补白边
  --scale F              整体缩放
  --font path.ttf        来源条字体（默认自动找微软雅黑 / Noto / DejaVu）

示例：
  python png_mark.py shot.png fig-7.png \
    --box-json shot.png.box.json \
    --caption "来源：forum.butian.net，抓取日期 2026-11-14" \
    --trim-left 0 --pad 12
"""
import argparse
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/PingFang.ttc",
]


def load_font(size, explicit=""):
    for p in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description="截图标注")
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--box", action="append", default=[], help="x,y,w,h，可多次")
    ap.add_argument("--box-color", action="append", default=[], help="r,g,b，可多次")
    ap.add_argument("--box-json", default="", help="读取框坐标 JSON")
    ap.add_argument("--caption", default="")
    ap.add_argument("--caption-pos", choices=["top", "bottom"], default="bottom")
    ap.add_argument("--trim-left", type=int, default=0)
    ap.add_argument("--trim-right", type=int, default=0)
    ap.add_argument("--trim-top", type=int, default=0)
    ap.add_argument("--trim-bottom", type=int, default=0)
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--font", default="")
    args = ap.parse_args()

    boxes = [tuple(int(v) for v in s.split(",")) for s in args.box]
    if args.box_json and os.path.exists(args.box_json):
        b = json.load(io.open(args.box_json, encoding="utf-8"))
        boxes.append((b["x"], b["y"], b["w"], b["h"]))
    colors = [tuple(int(v) for v in s.split(",")) for s in args.box_color]

    im = Image.open(args.inp).convert("RGB")

    # 1. 裁边（框坐标同步平移）
    if any([args.trim_left, args.trim_right, args.trim_top, args.trim_bottom]):
        w, h = im.size
        im = im.crop((args.trim_left, args.trim_top, w - args.trim_right, h - args.trim_bottom))
        boxes = [(x - args.trim_left, y - args.trim_top, bw, bh) for (x, y, bw, bh) in boxes]

    # 2. 缩放（框坐标同步缩放）
    if args.scale != 1.0:
        im = im.resize((int(im.width * args.scale), int(im.height * args.scale)),
                       Image.LANCZOS)
        boxes = [(int(x * args.scale), int(y * args.scale),
                  int(bw * args.scale), int(bh * args.scale))
                 for (x, y, bw, bh) in boxes]

    # 3. 红框：4px 外圈 + 2px 内圈，保证缩略图上也看得见
    if boxes:
        d = ImageDraw.Draw(im)
        for idx, (x, y, bw, bh) in enumerate(boxes):
            c = colors[idx] if idx < len(colors) else (220, 30, 30)
            for t in (2, 4):
                d.rectangle([x - t, y - t, x + bw + t, y + bh + t],
                            outline=c, width=2)

    # 4. 来源条
    if args.caption:
        fs = max(13, int(im.width * 0.0125))
        font = load_font(fs, args.font)
        probe = ImageDraw.Draw(im)
        tb = probe.textbbox((0, 0), args.caption, font=font)
        th = (tb[3] - tb[1]) + 12
        band = Image.new("RGB", (im.width, th), (247, 248, 249))
        bd = ImageDraw.Draw(band)
        bd.line([(0, 0), (im.width, 0)], fill=(215, 218, 222), width=1)
        bd.text((10, 5), args.caption, font=font, fill=(90, 96, 102))
        canvas = Image.new("RGB", (im.width, im.height + th), (255, 255, 255))
        if args.caption_pos == "top":
            canvas.paste(band, (0, 0))
            canvas.paste(im, (0, th))
        else:
            canvas.paste(im, (0, 0))
            canvas.paste(band, (0, im.height))
        im = canvas

    # 5. 补白
    if args.pad:
        canvas = Image.new("RGB", (im.width + args.pad * 2, im.height + args.pad * 2),
                           (255, 255, 255))
        canvas.paste(im, (args.pad, args.pad))
        im = canvas

    im.save(args.out)
    print("%s  %dx%d  %.0fKB" % (args.out, im.width, im.height,
                                 os.path.getsize(args.out) / 1024))


if __name__ == "__main__":
    main()
