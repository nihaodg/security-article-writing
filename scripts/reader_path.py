#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读者路径校验：读者按正文操作，能不能得到同样的结果。

用法：
    python reader_path.py articles/x.md
    python reader_path.py articles/x.md --repro "_lab_x/exp_survey.py:_lab_x/out_survey.txt"
    python reader_path.py articles/x.md --fact "CVE-2025-53773" --fact "2025-08-12"
    python reader_path.py articles/x.md --src _lab_x/snips/snip.py

检查：
  1. 所有 python 代码块可解析；
  2. 所有 <<SRC:path>> 标记与磁盘逐字一致；
  3. --repro script:expected：脚本可运行、输出与 expected 一致、该输出原样出现在正文；
  4. --fact：关键事实出现在正文；
  5. 正文不含本机绝对路径。
退出码：有失败返回 1。
"""
import argparse
import ast
import io
import os
import re
import subprocess
import sys

FENCE = chr(96) * 3
SRC_RE = re.compile(FENCE + r"\w*\n#\s*<<SRC:([^>\n]+)>>\n" + FENCE)
BLOCK_RE = re.compile(FENCE + r"(\w*)\n(.*?)" + FENCE, re.S)


def norm(s):
    return "\n".join(line.rstrip() for line in s.strip().split("\n"))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="读者路径校验")
    ap.add_argument("md")
    ap.add_argument("--base", default="", help="相对路径根目录（默认 md 所在目录）")
    ap.add_argument("--repro", action="append", default=[],
                    help="script.py:expected.txt，可重复")
    ap.add_argument("--fact", action="append", default=[], help="正文必须包含的事实，可重复")
    ap.add_argument("--src", action="append", default=[], help="必须逐字出现在正文的源文件")
    args = ap.parse_args()

    base = args.base or os.path.dirname(os.path.abspath(args.md))
    md = io.open(args.md, encoding="utf-8").read()
    blocks = BLOCK_RE.findall(md)
    fails = []

    def check(name, ok, detail=""):
        print("[%s] %s%s" % ("OK" if ok else "FAIL", name,
                             ("  " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    # 1. python 块语法
    bad = 0
    for i, (lang, code) in enumerate(blocks, 1):
        if lang != "python":
            continue
        try:
            ast.parse(code)
        except SyntaxError as e:
            bad += 1
            print("       第 %d 个 python 块: %s" % (i, e))
    check("python 代码块可解析", bad == 0)

    # 2. <<SRC>> 与磁盘一致
    miss = []
    for rel in SRC_RE.findall(md):
        rel = rel.strip()
        full = os.path.join(base, rel.replace("/", os.sep))
        if not os.path.exists(full):
            miss.append("缺文件: " + rel)
            continue
        disk = norm(io.open(full, encoding="utf-8").read())
        if not any(norm(code) == disk for _lang, code in blocks):
            miss.append("正文与磁盘不一致: " + rel)
    check("<<SRC>> 回填与磁盘一致", not miss)
    for m in miss:
        print("       " + m)

    # 3. 复现脚本
    for item in args.repro:
        if ":" not in item:
            check("--repro 格式错误: " + item, False)
            continue
        script, expected = item.split(":", 1)
        sp = os.path.join(base, script)
        ep = os.path.join(base, expected)
        if not os.path.exists(sp) or not os.path.exists(ep):
            check("复现文件存在: " + item, False)
            continue
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", os.path.basename(sp)],
                               cwd=os.path.dirname(os.path.abspath(sp)),
                               capture_output=True, text=True, encoding="utf-8",
                               timeout=300)
        except Exception as e:
            check("脚本可运行: " + script, False, str(e))
            continue
        check("脚本可运行: " + script, r.returncode == 0,
              "" if r.returncode == 0 else (r.stderr or "")[-200:])
        exp = norm(io.open(ep, encoding="utf-8").read())
        got = norm(r.stdout)
        check("输出与 %s 一致" % expected, got == exp)
        check("输出原样出现在正文", norm(exp) in norm(md))

    # 4. 必需源文件逐字出现
    for rel in args.src:
        full = os.path.join(base, rel.replace("/", os.sep))
        if not os.path.exists(full):
            check("源文件存在: " + rel, False)
            continue
        disk = norm(io.open(full, encoding="utf-8").read())
        check("源文件原样出现在正文: " + rel,
              any(norm(code) == disk for _lang, code in blocks))

    # 5. 关键事实
    for fact in args.fact:
        check("正文包含关键事实: " + fact, fact in md)

    # 6. 本机路径泄漏
    leak = re.findall(r"[A-Za-z]:\\Users|Temp\\Kila|session-projects", md)
    check("正文无本机绝对路径", not leak, "命中 %d 处" % len(leak) if leak else "")

    print("")
    if fails:
        print("失败 %d 项: %s" % (len(fails), "; ".join(fails)))
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
