#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""奇安信（补天）图床批量推送：上传本地图并替换 MD 中的相对路径。

凭证（二选一，绝不写死在脚本里）：
  1. 环境变量 BUTIAN_SESSION / BUTIAN_XSRF
  2. 本地 .butian-token.json：{"host_session": "...", "xsrf": "..."}
     —— 该文件必须加入 .gitignore

用法：
  python cdn_push.py articles/x.md --check
  python cdn_push.py articles/x.md --dry-run
  python cdn_push.py articles/x.md
  python cdn_push.py articles/x.md --apply-map cdn_map.txt
  python cdn_push.py --token            # 交互式写入 .butian-token.json

说明：
  - X-Requested-With 必带，否则论坛返回 HTML 登录页；
  - 不要手动设置 Host / Connection 头；
  - 上传间隔 0.5s；Cookie 约 1-2 小时过期。
"""
import argparse
import json
import os
import re
import sys
import time
import warnings

import requests

warnings.filterwarnings("ignore")

UPLOAD_URL = "https://forum.butian.net/image/uploadS3"
CDN_PREFIX = "cdn-yg-zzbm"
LOCAL_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+\.assets/[^)]+\.(?:png|jpe?g))\)")
TOKEN_FILE = ".butian-token.json"


def load_tokens():
    host = os.environ.get("BUTIAN_SESSION", "")
    xsrf = os.environ.get("BUTIAN_XSRF", "")
    if host and xsrf:
        return host, xsrf
    if os.path.exists(TOKEN_FILE):
        try:
            d = json.load(open(TOKEN_FILE, encoding="utf-8"))
            return d.get("host_session", ""), d.get("xsrf", "")
        except Exception:
            pass
    return "", ""


def save_tokens_interactive():
    print("从浏览器 DevTools > Application > Cookies 拷贝：")
    host = input("__Host-attack_session: ").strip()
    xsrf = input("XSRF-TOKEN: ").strip()
    if not (host and xsrf):
        print("输入为空，未保存。")
        return
    json.dump({"host_session": host, "xsrf": xsrf},
              open(TOKEN_FILE, "w", encoding="utf-8"), indent=2)
    print("已写入 %s（记得加入 .gitignore）" % TOKEN_FILE)


def headers(host, xsrf):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) "
                      "Gecko/20100101 Firefox/95.0",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
        # 关键：缺这个头会返回登录页 HTML
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-TOKEN": xsrf,
        "Cookie": "__Host-attack_session=%s; XSRF-TOKEN=%s" % (host, xsrf),
        "Referer": "https://forum.butian.net/share/create",
    }


def md_stats(md_path):
    text = open(md_path, encoding="utf-8").read()
    local = len(LOCAL_IMG.findall(text))
    cdn = text.count(CDN_PREFIX)
    status = "CDN" if cdn and not local else ("LOCAL" if local else "NO_IMG")
    return local, cdn, status


def push(md_path, host, xsrf, dry_run=False, delay=0.5):
    base = os.path.dirname(os.path.abspath(md_path))
    text = open(md_path, encoding="utf-8").read()
    imgs = LOCAL_IMG.findall(text)
    if not imgs:
        print("  %s: 没有本地图片" % os.path.basename(md_path))
        return 0, 0

    print("\n%s  (%d 张本地图)" % (os.path.basename(md_path), len(imgs)))
    ok = fail = 0
    for i, (_alt, rel) in enumerate(imgs, 1):
        full = os.path.join(base, rel.replace("/", os.sep))
        name = os.path.basename(full)
        if not os.path.exists(full):
            print("  [%d/%d] %s 文件不存在" % (i, len(imgs), name))
            fail += 1
            continue
        if dry_run:
            print("  [%d/%d] %s (%.0fKB) DRY-RUN" % (
                i, len(imgs), name, os.path.getsize(full) / 1024))
            ok += 1
            continue
        print("  [%d/%d] %s ..." % (i, len(imgs), name), end=" ", flush=True)
        try:
            with open(full, "rb") as f:
                r = requests.post(UPLOAD_URL, headers=headers(host, xsrf),
                                  files={"file": f}, verify=False, timeout=30)
            url = r.text.strip()
            if url.startswith("http"):
                print("OK")
                print("       " + url)
                text = text.replace("](%s)" % rel, "](%s)" % url)
                open(md_path, "w", encoding="utf-8").write(text)
                ok += 1
            else:
                low = url.lower()
                if "login" in low or "<html" in low:
                    print("FAIL: Cookie 过期或未登录")
                    return ok, fail + (len(imgs) - i + 1)
                print("FAIL: " + url[:120])
                fail += 1
        except Exception as e:
            print("ERROR: %s" % e)
            fail += 1
        time.sleep(delay)
    return ok, fail


def apply_map(md_path, map_path):
    base = os.path.dirname(os.path.abspath(md_path))
    mapping = {}
    for line in open(map_path, encoding="utf-8"):
        line = line.strip()
        if line and "|" in line:
            k, v = line.split("|", 1)
            mapping[k.strip()] = v.strip()
    text = open(md_path, encoding="utf-8").read()
    n = 0
    for name, url in mapping.items():
        before = text
        text = re.sub(r"\]\(([^)]*%s)\)" % re.escape(name), "](%s)" % url, text)
        if text != before:
            n += 1
    open(md_path, "w", encoding="utf-8").write(text)
    print("按 cdn_map 替换 %d 张图" % n)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="奇安信图床推送")
    ap.add_argument("md", nargs="*", help="Markdown 文件；留空则扫描当前目录")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply-map", default="", help="图片名|URL 映射表")
    ap.add_argument("--token", action="store_true", help="交互式更新凭证")
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()

    if args.token:
        save_tokens_interactive()
        return

    mds = args.md or sorted(
        os.path.join(".", f) for f in os.listdir(".")
        if f.endswith(".md") and not f.startswith("_"))
    if not mds:
        print("没有找到 Markdown 文件")
        return

    if args.apply_map:
        for md in mds:
            apply_map(md, args.apply_map)
        return

    if args.check:
        print("%-58s %4s %4s %6s" % ("文件", "本地", "CDN", "状态"))
        print("-" * 76)
        for md in mds:
            local, cdn, status = md_stats(md)
            if local or cdn:
                print("%-58s %4d %4d %6s" % (os.path.basename(md), local, cdn, status))
        return

    host, xsrf = load_tokens()
    if not (host and xsrf):
        print("缺少凭证。设置 BUTIAN_SESSION / BUTIAN_XSRF，"
              "或先运行 --token 写入 %s" % TOKEN_FILE)
        sys.exit(2)

    total_ok = total_fail = 0
    for md in mds:
        ok, fail = push(md, host, xsrf, dry_run=args.dry_run, delay=args.delay)
        total_ok += ok
        total_fail += fail

    print("\n%s: 成功 %d，失败 %d" % (
        "DRY-RUN" if args.dry_run else "完成", total_ok, total_fail))
    if not args.dry_run:
        print("\n本地路径残留检查：")
        for md in mds:
            local, cdn, status = md_stats(md)
            print("  %s: 本地=%d, CDN=%d, 状态=%s" % (
                os.path.basename(md), local, cdn, status))


if __name__ == "__main__":
    main()
