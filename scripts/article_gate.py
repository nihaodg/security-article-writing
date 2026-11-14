#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文章机械终检门禁。

用法：
    python article_gate.py articles/x.md
    python article_gate.py articles/x.md --cdn-host cdn-yg-zzbm.yun.qianxin.com
    python article_gate.py articles/x.md --src-list _lab_x/srcs.txt
    python article_gate.py articles/x.md --no-chapter-table

退出码：有问题返回 1，否则 0。
"""
import argparse
import ast
import io
import os
import re
import statistics
import sys

FENCE = chr(96) * 3
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\U0001F1E6-\U0001F1FF]")
TABLE_SEP = re.compile(r"^\|[\s:\-\|]+\|\s*$", re.M)
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")


def strip_code(md):
    md = re.sub(FENCE + r".*?" + FENCE, "", md, flags=re.S)
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)
    return md


def check(md_path, cdn_host, src_list, chapter_table=True, src_base=None):
    base = os.path.dirname(os.path.abspath(md_path))
    # 源文件清单的根目录：默认与 md 同目录；文章放 articles/、靶场在上一层时用 --src-base 指定
    sbase = src_base or base
    t = io.open(md_path, encoding="utf-8").read()
    body = strip_code(t)
    issues = []

    fences = re.findall(r"^" + FENCE + r"(\w*)", t, re.M)
    opens = [x for i, x in enumerate(fences) if i % 2 == 0]
    closes = [x for i, x in enumerate(fences) if i % 2 == 1]
    blocks = re.findall(FENCE + r"(\w*)\n(.*?)" + FENCE, t, re.S)
    empty = sum(1 for _lang, code in blocks if not code.strip())
    nolang = [x for i, x in enumerate(opens) if not x]
    rawfence = t.count(FENCE) - 2 * len(blocks)

    chapters = len(re.findall(r"^## ", t, re.M))
    tables = len(TABLE_SEP.findall(t))
    imgs = len(IMG.findall(t))
    emoji = EMOJI.findall(body)
    latex = re.findall(r"\$\$|\\\(|\\\[", body)
    appendix = re.findall(r"^#+\s*附录", t, re.M)
    zhuyi = re.findall(r"不是[^，。]{2,20}，而是", body)
    leak = re.findall(r"[A-Za-z]:\\Users|Temp\\Kila|session-projects", t)
    dash = round(body.count("——") / max(1, len(body)) * 1000, 2)
    bold = len(re.findall(r"\*\*[^*]+\*\*", body))
    bold_density = round(bold / max(1, len(body)) * 1000, 2)

    paras = [p.strip() for p in body.split("\n\n") if len(p.strip()) > 40]
    lens = [len(p) for p in paras]
    if len(lens) >= 4:
        cv = statistics.pstdev(lens) / max(1, statistics.mean(lens))
    else:
        cv = 0

    print("字符 %d  章 %d  表 %d  代码 %d  图 %d" % (len(t), chapters, tables, len(blocks), imgs))
    print("段落 %d  平均 %d  CV %.3f  破折号 %.2f/千字  加粗 %.2f/千字" % (
        len(paras), statistics.mean([len(p) for p in paras]) if paras else 0, cv, dash, bold_density))

    if empty:
        issues.append("空代码块 %d" % empty)
    if nolang:
        issues.append("无语言标识 %d" % len(nolang))
    if len(closes) != len(opens):
        issues.append("围栏不配对 %d/%d" % (len(opens), len(closes)))
    if rawfence:
        issues.append("裸围栏 %d" % rawfence)
    if emoji:
        issues.append("emoji %d" % len(emoji))
    if latex:
        issues.append("LaTeX %d" % len(latex))
    if appendix:
        issues.append("附录章节 %d" % len(appendix))
    if zhuyi:
        issues.append("不是…而是 %d" % len(zhuyi))
    if leak:
        issues.append("路径泄漏 %d" % len(leak))
    if dash > 4:
        issues.append("破折号 %.2f/千字" % dash)
    if bold_density >= 7:
        issues.append("加粗 %.2f/千字" % bold_density)
    if cv < 0.5:
        issues.append("段落 CV %.2f 偏均匀" % cv)

    if chapter_table:
        for part in re.split(r"\n(?=## )", t):
            if part.startswith("## ") and len(TABLE_SEP.findall(part)) < 1:
                issues.append("缺表: %s" % part.split("\n")[0][:28])

    for alt, p in IMG.findall(t):
        if not alt.strip():
            issues.append("配图 alt 为空: %s" % p)
        if p.startswith("http"):
            if cdn_host and cdn_host not in p:
                issues.append("外链域名不在白名单: %s" % p)
        elif p.startswith("data:"):
            continue
        else:
            if not os.path.exists(os.path.join(base, p.replace("/", os.sep))):
                issues.append("配图文件缺失: %s" % p)

    if src_list:
        if not os.path.exists(src_list):
            issues.append("--src-list 不存在: %s" % src_list)
        else:
            for rel in io.open(src_list, encoding="utf-8").read().splitlines():
                rel = rel.strip()
                if not rel or rel.startswith("#"):
                    continue
                full = os.path.join(sbase, rel.replace("/", os.sep))
                if not os.path.exists(full):
                    issues.append("缺源文件: %s" % rel)
                    continue
                disk = io.open(full, encoding="utf-8").read().rstrip("\n")
                hit = sum(1 for _lang, code in blocks if code.rstrip("\n") == disk)
                if hit != 1:
                    issues.append("代码块与磁盘不一致（出现 %d 次）: %s" % (hit, rel))

    for _lang, code in blocks:
        if _lang != "python":
            continue
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append("python 语法错 %s" % e)

    print("---")
    if issues:
        print("问题数: %d" % len(issues))
        for x in issues:
            print("  " + x)
        return 1
    print("问题数: 0")
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="文章机械终检")
    ap.add_argument("md")
    ap.add_argument("--cdn-host", default="cdn-yg-zzbm.yun.qianxin.com",
                    help="允许的外链图片域名；留空则不检查")
    ap.add_argument("--src-list", default="", help="必须与磁盘逐字一致的源文件清单")
    ap.add_argument("--src-base", default="", help="源文件清单的根目录（默认 md 所在目录）")
    ap.add_argument("--no-chapter-table", action="store_true", help="不要求每章有表")
    args = ap.parse_args()
    sys.exit(check(args.md, args.cdn_host, args.src_list,
                   chapter_table=not args.no_chapter_table,
                   src_base=args.src_base or None))


if __name__ == "__main__":
    main()
