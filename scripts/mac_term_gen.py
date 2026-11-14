# -*- coding: utf-8 -*-
"""仿 macOS 终端截图生成器。

输入：spec dict（标题 + 终端内容行，每行带语义色类）
输出：PNG（红绿灯窗口按钮 + 深色背景 + 等宽字体 + 语义配色）

行的语义色类：
  cmd       用户敲的命令行（提示符绿 + 命令白）
  dim       普通灰白输出
  label     蓝色标签，如 [agent] [guard] [memory]
  green     成功 / PASS / 结论正常
  red       恶意载荷 / 危险决策 / 攻击成功
  yellow    警告说明
  orange    代码片段 / 来源标签
  banner    底部结论横幅（暗红底）
  banner-ok 底部结论横幅（暗绿底）
  header    会话分隔行
  blank     空行

用法：
    from mac_term_gen import render
    render({"title": "...", "prompt": ("PS", "C:\\\\LAB"), "lines": [...]},
           "articles/x.assets/term-1.png")

依赖：node + playwright + 同目录 mac_term_shot.js。
"""
import os
import re
import subprocess
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { background: #e8eaed; }
  .wrap { display: inline-block; padding: 0; }
  .term {
    width: __WIDTH__px;
    background: #1a1d21;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 12px 32px rgba(0,0,0,.35), 0 2px 6px rgba(0,0,0,.25);
    font-family: "Cascadia Mono", Consolas, "JetBrains Mono", Menlo, "Microsoft YaHei", monospace;
  }
  .titlebar {
    height: 34px;
    background: #2b2f36;
    border-bottom: 1px solid #111;
    display: flex;
    align-items: center;
    padding: 0 12px;
    position: relative;
  }
  .dots { display: flex; gap: 7px; }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .dot.r { background: #ff5f57; }
  .dot.y { background: #febc2e; }
  .dot.g { background: #28c840; }
  .tb-title {
    position: absolute; left: 0; right: 0; text-align: center;
    color: #9aa0a6; font-size: 12.5px; user-select: none;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
  }
  .body { padding: 16px 18px 18px 18px; font-size: 14px; line-height: 1.72; color: #d5d8dd; white-space: pre-wrap; word-break: break-all; }
  .l { display: block; }
  .cmdline { color: #e8eaed; }
  .pfx  { color: #3fd15c; font-weight: 600; }
  .pfx2 { color: #56c2ff; }
  .dim  { color: #9aa0a6; }
  .lbl  { color: #58a6ff; font-weight: 600; }
  .ok   { color: #3fd15c; }
  .bad  { color: #ff6b6b; }
  .warn { color: #e3b341; }
  .code { color: #ffa657; }
  .hdr  { color: #d2a8ff; font-weight: 600; }
  .banner {
    display: block;
    margin-top: 10px;
    background: #4a1f24;
    border-left: 3px solid #ff6b6b;
    color: #ffd7d5;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 13.5px;
  }
  .banner.okb { background: #1d3a29; border-left-color: #3fd15c; color: #c9f0d4; }
</style>
</head>
<body>
<div class="wrap"><div class="term">
  <div class="titlebar">
    <div class="dots"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div></div>
    <div class="tb-title">__TITLE__</div>
  </div>
  <div class="body">
__LINES__
  </div>
</div></div>
</body>
</html>
"""


def _line_html(kind, text, prompt=None):
    if kind == "blank":
        return '<span class="l">&nbsp;</span>'
    if kind == "cmd" and prompt:
        style, path = prompt
        if style == "PS":
            pfx = '<span class="pfx">PS %s</span><span class="dim">&gt;</span> ' % path
        else:
            pfx = ('<span class="pfx2">user@host</span><span class="dim">:</span>'
                   '<span class="pfx">%s</span><span class="dim">$</span> ' % path)
        return '<span class="l cmd cmd-line">%s<span class="cmdline">%s</span></span>' % (pfx, text)
    if kind == "header":
        return '<span class="l hdr">%s</span>' % text
    if kind == "banner":
        return '<span class="banner">%s</span>' % text
    if kind == "banner-ok":
        return '<span class="banner okb">%s</span>' % text
    if kind == "label":
        m = re.match(r"^(\[[^\]]+\])(.*)$", text, re.S)
        if m:
            return '<span class="l"><span class="lbl">%s</span>%s</span>' % (m.group(1), m.group(2))
        return '<span class="l lbl">%s</span>' % text
    cls = {"dim": "dim", "green": "ok", "red": "bad",
           "yellow": "warn", "orange": "code"}.get(kind, "")
    return '<span class="l %s">%s</span>' % (cls, text)


def render(spec, out_png, width=1180):
    title = spec.get("title", "Terminal")
    prompt = spec.get("prompt", ("PS", "C:\\LAB"))
    lines_html = "\n".join(_line_html(k, t, prompt if k == "cmd" else None)
                           for k, t in spec["lines"])
    html = (TEMPLATE.replace("__TITLE__", title)
            .replace("__LINES__", lines_html)
            .replace("__WIDTH__", str(width)))
    n = len(spec["lines"])
    height = int(34 + 34 + n * 25 + 60)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8", dir=BASE) as f:
        f.write(html)
        htmlpath = f.name
    js = os.path.join(BASE, "mac_term_shot.js")
    out = subprocess.run(
        ["node", js, htmlpath, os.path.abspath(out_png), str(width), str(height)],
        capture_output=True, text=True, cwd=BASE, timeout=120)
    os.unlink(htmlpath)
    if out.returncode != 0:
        raise RuntimeError(out.stderr or out.stdout)
    return out_png


if __name__ == "__main__":
    spec = {
        "title": "复现 ① 对照组",
        "prompt": ("PS", "C:\\LAB"),
        "lines": [
            ("cmd", "python exp_survey.py"),
            ("blank", ""),
            ("header", "【会话 1】正常加载"),
            ("label", "[scan]  261 个配置"),
            ("dim", "        exec 106 / instr 43 / env 39 / approval 38"),
            ("green", "结论：exec 40.6%  approval 14.6%  兼有 6.5%"),
            ("banner", "审批只看到「多了一个字段」，看不到后果"),
        ],
    }
    render(spec, "_mac_term_test.png")
    print("OK -> _mac_term_test.png")
