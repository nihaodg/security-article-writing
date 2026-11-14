#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 GitHub Code Search 采集真实语料，落盘并维护索引。

特点：
  - 断点续跑：已有 corpus_index.json 中 (repo, path) 不重复采集；
  - 分批执行：QSET=0:5 只跑前 5 个查询，避免单次命令被掐断；
  - 落盘文件名带仓库名，避免同名文件互相覆盖；
  - 只走 API（raw.githubusercontent.com 在部分网络下不可达）。

用法：
    export GH_TOKEN=<your_token>
    python collect_corpus.py --out _lab_x/corpus
    QSET=0:5 python collect_corpus.py --out _lab_x/corpus

注意：GitHub Code Search 需要已登录的 token；未登录会返回 401。
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.parse
from collections import Counter

import requests

# 示例查询：按你的主题替换。格式 (查询, 类别)。
QUERIES = [
    ('filename:.vscode/settings.json autoApproveCommands', "vscode-approval"),
    ('filename:.vscode/settings.json terminal.integrated.env', "vscode-env"),
    ('filename:.mcp.json mcpServers', "mcp"),
    ('filename:.claude/settings.json permissions', "claude-perm"),
    ('filename:.claude/settings.json hooks', "claude-hook"),
    ('filename:CLAUDE.md', "claude-md"),
    ('filename:.cursorrules', "cursorrules"),
    ('filename:.github/copilot-instructions.md', "copilot-instructions"),
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="GitHub 语料采集")
    ap.add_argument("--out", default="corpus", help="语料目录")
    ap.add_argument("--max-size", type=int, default=200000, help="单文件字节上限")
    ap.add_argument("--per-page", type=int, default=30)
    args = ap.parse_args()

    token = os.environ.get("GH_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Mozilla/5.0"}
    if token:
        headers["Authorization"] = "Bearer " + token

    def search(q):
        r = requests.get("https://api.github.com/search/code",
                         params={"q": q, "per_page": args.per_page},
                         headers=headers, timeout=90)
        if r.status_code != 200:
            print("  [search %d] %s" % (r.status_code, r.text[:120]))
            return []
        return r.json().get("items", [])

    def fetch(repo, path, branch):
        url = "https://api.github.com/repos/%s/contents/%s" % (repo, urllib.parse.quote(path))
        if branch:
            url += "?ref=" + urllib.parse.quote(branch)
        r = None
        for _ in range(2):
            try:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 200:
                    break
            except Exception:
                r = None
            time.sleep(1)
        if r is None or r.status_code != 200:
            return None
        d = r.json()
        if d.get("encoding") != "base64":
            return None
        try:
            return base64.b64decode(d["content"]).decode("utf-8", "replace")
        except Exception:
            return None

    os.makedirs(args.out, exist_ok=True)
    index_path = os.path.join(args.out, "corpus_index.json")
    index = []
    if os.path.exists(index_path):
        try:
            index = json.load(io.open(index_path, encoding="utf-8"))
        except Exception:
            index = []
    seen = set((i["repo"], i["path"]) for i in index)

    qs = QUERIES
    only = os.environ.get("QSET", "")
    if only:
        lo, hi = [int(x) for x in only.split(":")]
        qs = QUERIES[lo:hi]

    for q, kind in qs:
        items = search(q)
        got = 0
        for it in items:
            repo = it["repository"]["full_name"]
            path = it["path"]
            if (repo, path) in seen:
                continue
            seen.add((repo, path))
            branch = it.get("repository", {}).get("default_branch") or "main"
            txt = fetch(repo, path, branch)
            if not txt or len(txt) > args.max_size:
                continue
            # 关键：文件名必须带仓库名，否则同类文件互相覆盖
            name = "%s__%s__%s" % (kind, repo.replace("/", "_"),
                                    path.replace("/", "_"))
            io.open(os.path.join(args.out, name), "w",
                    encoding="utf-8", newline="\n").write(txt)
            index.append(dict(kind=kind, repo=repo, path=path, branch=branch,
                              size=len(txt), file=name))
            got += 1
            time.sleep(0.25)
        print("%-62s 命中 %d，收下 %d" % (q[:62], len(items), got))
        time.sleep(3)

    io.open(index_path, "w", encoding="utf-8").write(
        json.dumps(index, ensure_ascii=False, indent=1))
    print("\n共收集 %d 个文件" % len(index))
    for k, v in Counter(i["kind"] for i in index).most_common():
        print("   %-26s %d" % (k, v))

    # 完整性检查：索引条数应等于目录内文件数
    actual = len([f for f in os.listdir(args.out)
                  if os.path.isfile(os.path.join(args.out, f))
                  and f != "corpus_index.json"])
    print("索引 %d 条 / 落盘 %d 个" % (len(index), actual))
    if actual != len(index):
        print("[WARN] 索引与落盘数量不一致，检查是否有同名覆盖")


if __name__ == "__main__":
    main()
