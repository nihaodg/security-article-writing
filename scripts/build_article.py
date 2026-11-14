#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并分章草稿，回填 <<SRC>> 代码块，并输出文章统计。

用法：
    python build_article.py articles/x.md _part_x1.md _part_x2.md _part_x3.md
    python build_article.py articles/x.md _part_*.md --base .

占位写法（单独成块）：
    ```python
    # <<SRC:_lab_x/exp_survey.py>>
    ```
构建时整块替换为磁盘文件原文，语言标识沿用占位块。

规则：
  - 源文件路径相对 --base（默认当前目录）。
  - 源文件里若含裸围栏 ```，直接报错，避免破坏 Markdown。
  - 合并后不再手改代码块；改源文件后重新构建。
"""
import argparse
import io
import os
import re
import statistics
import sys

FENCE = chr(96) * 3
SRC_RE = re.compile(FENCE + r"(\w*)\n#\s*<<SRC:([^>\n]+)>>\n" + FENCE)


def sync_src(text, base):
    missing = []
    bad = []

    def repl(m):
        lang, rel = m.group(1), m.group(2).strip()
        full = os.path.join(base, rel.replace("/", os.sep))
        if not os.path.exists(full):
            missing.append(rel)
            return m.group(0)
        body = io.open(full, encoding="utf-8").read().rstrip("\n")
        if FENCE in body:
            bad.append(rel)
            return m.group(0)
        return FENCE + lang + "\n" + body + "\n" + FENCE

    out, n = SRC_RE.subn(repl, text)
    if missing:
        raise SystemExit("缺源文件: %s" % ", ".join(missing))
    if bad:
        raise SystemExit("源码里有裸围栏，拒绝回填: %s" % ", ".join(bad))
    return out, n


def stats(text):
    fences = re.findall(r"^" + FENCE + r"(\w*)", text, re.M)
    blocks = re.findall(FENCE + r"(\w*)\n(.*?)" + FENCE, text, re.S)
    body = re.sub(FENCE + r".*?" + FENCE, "", text, flags=re.S)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    paras = [p.strip() for p in body.split("\n\n")]
    paras = [p for p in paras if len(p) > 40 and not p.startswith("#")
             and not p.startswith("|") and not p.startswith(">")]
    lens = [len(p) for p in paras] or [1]
    sents = [s for s in re.split(r"[。！？\n]", "\n".join(paras)) if len(s.strip()) > 8]
    sl = [len(s) for s in sents] or [1]
    return {
        "字符": len(text),
        "行": text.count("\n") + 1,
        "章": len(re.findall(r"^## ", text, re.M)),
        "表": len(re.findall(r"^\|[\s:\-\|]+\|\s*$", text, re.M)),
        "代码块": len(blocks),
        "图": len(re.findall(r"!\[", text)),
        "破折号": text.count("——"),
        "不是而是": len(re.findall(r"不是[^。！？\n]{0,40}而是", body)),
        "加粗": len(re.findall(r"\*\*[^*]+\*\*", text)),
        "emoji": len(re.findall("[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]", text)),
        "LaTeX": len(re.findall(r"\$\$|\\\(|\\\[", text)),
        "本机路径": len(re.findall(r"[A-Za-z]:\\Users|Temp\\Kila|session-projects", text)),
        "段落CV": round(statistics.pstdev(lens) / max(1, statistics.mean(lens)), 3),
        "句长CV": round(statistics.pstdev(sl) / max(1, statistics.mean(sl)), 3),
        "围栏行": len(fences),
    }


def main():
    ap = argparse.ArgumentParser(description="合并分章 + 回填源码 + 统计")
    ap.add_argument("out", help="输出 md")
    ap.add_argument("parts", nargs="+", help="按顺序合并的分章文件")
    ap.add_argument("--base", default=".", help="<<SRC>> 路径的根目录（默认当前目录）")
    ap.add_argument("--no-write", action="store_true", help="只预览，不写文件")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    chunks = []
    for p in args.parts:
        chunks.append(io.open(p, encoding="utf-8").read().strip())
    text = "\n\n".join(chunks)
    text, n = sync_src(text, args.base)

    print("回填代码块: %d 处" % n)
    if not args.no_write:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        io.open(args.out, "w", encoding="utf-8", newline="\n").write(text)
        print("已写出", args.out)
    for k, v in stats(text).items():
        print("%-8s %s" % (k, v))


if __name__ == "__main__":
    main()
