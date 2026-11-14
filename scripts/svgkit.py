# -*- coding: utf-8 -*-
"""最小 SVG 绘图工具：白底、扁平、无阴影。

用法：
    from svgkit import *
    write(ASSETS, "fig-1-chain.svg", "".join(body), 660)
"""
import io
import os

W = 1240
INK = "#212529"
SUB = "#495057"
MUTE = "#868e96"
LINE = "#dee2e6"
RED_BG, RED_LN, RED_TX = "#fdecee", "#f0b3ba", "#a51d2b"
GRN_BG, GRN_LN, GRN_TX = "#e4f4ea", "#a8d5b8", "#136c39"
WARN_BG, WARN_LN, WARN_TX = "#fdf3e2", "#eccf9d", "#8a5a12"
BLUE_BG, BLUE_LN, BLUE_TX = "#e7f1ff", "#a8c7f0", "#0b4ea2"
GRY_BG, GRY_LN = "#f6f8fa", "#cdd4dc"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def head(h, w=W):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d" font-family="Helvetica,Arial,sans-serif">'
            '<rect width="%d" height="%d" fill="#ffffff"/>' % (w, h, w, h, w, h))


def txt(x, y, s, size=15, fill=INK, anchor="start", weight="normal"):
    return ('<text x="%s" y="%s" font-size="%s" fill="%s" text-anchor="%s" '
            'font-weight="%s">%s</text>'
            % (x, y, size, fill, anchor, weight, esc(s)))


def rect(x, y, w, h, fill, stroke="none", rx=0, sw=1):
    return ('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" '
            'rx="%s" stroke-width="%s"/>' % (x, y, w, h, fill, stroke, rx, sw))


def line(x1, y1, x2, y2, stroke=LINE, sw=1, dash=""):
    d = ' stroke-dasharray="%s"' % dash if dash else ""
    return ('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"%s/>'
            % (x1, y1, x2, y2, stroke, sw, d))


def write(assets, name, body, h, w=W):
    os.makedirs(assets, exist_ok=True)
    p = os.path.join(assets, name)
    io.open(p, "w", encoding="utf-8", newline="\n").write(head(h, w) + body + "</svg>")
    print("  写出", name)
    return p


def table(assets, name, title, sub, cols, rows, colw, y0=140, rowh=34, h=None):
    """画一张规整的表：cols 是表头，rows 是数据行（字符串）。

    单元格以 ! 开头标红，以 + 开头标绿。
    """
    b = [txt(50, 56, title, 22, INK, weight="bold")]
    if sub:
        b.append(txt(50, 84, sub, 15, MUTE))
    x = 50
    for i, c in enumerate(cols):
        b.append(txt(x, y0, c, 14, SUB, weight="bold"))
        x += colw[i]
    b.append(line(50, y0 + 10, W - 50, y0 + 10, LINE, 1))
    y = y0 + 38
    for r in rows:
        x = 50
        for i, cell in enumerate(r):
            fill = INK
            if cell.startswith("!"):
                fill = RED_TX
                cell = cell[1:]
            elif cell.startswith("+"):
                fill = GRN_TX
                cell = cell[1:]
            b.append(txt(x, y, cell, 14, fill))
            x += colw[i]
        y += rowh
    if h is None:
        h = y + 40
    write(assets, name, "".join(b), h)
    return b
