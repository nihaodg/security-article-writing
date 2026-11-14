#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 humanizer-zh 的 33 条模式扫一遍中文正文，只报可机械检查的那些。

用法：
    python humanizer_scan.py articles/x.md
退出码：模式命中合计为 0 时返回 0，否则 1（可人工豁免，但要在清单里记录）。
"""
import argparse
import io
import re
import sys

PATS = [
    ("01 空泛拔高", r"标志着|彰显了|彰显出|体现了|具有里程碑意义|注入新动能|开启新篇章|奠定了坚实基础|迈上新台阶"),
    ("02 媒体名单", r"多家权威媒体|业内广泛关注|全网热议|获得众多.{0,6}认可|引起广泛关注"),
    ("03 从而进而助力", r"从而|进而|进一步|有效推动|助力实现|持续赋能|有效提升"),
    ("04 广告腔", r"匠心|重磅推出|震撼来袭|沉浸式|全方位|极致|卓越|焕新|宝藏|必打卡|颠覆性"),
    ("05 模糊归因", r"有专家表示|业内人士认为|研究表明|相关数据显示|据悉|普遍认为|有分析指出"),
    ("06 挑战展望", r"尽管面临|机遇与挑战并存|未来仍需|展望未来|砥砺前行|任重道远"),
    ("08 定位宣言", r"定位于|致力于|旨在|作为.{0,12}的载体|扮演.{0,8}角色|重要抓手"),
    ("09 不仅更是", r"不仅.{0,20}更是|不只是.{0,20}而是|不是.{0,20}而是|绝非.{0,10}这么简单"),
    ("10 强凑三点", r"以.{1,6}为.{1,6}、以.{1,6}为.{1,6}、以.{1,6}为"),
    ("12 从到范围", r"从.{1,12}到.{1,12}，从.{1,12}到"),
    ("13 无主句", r"已得到|问题被解决|将自动保存|无需配置|已完成优化"),
    ("20 聊天残留", r"当然可以|以下是关于|希望对你有帮助|如果需要我|欢迎随时|如上所述，希望"),
    ("21 知识免责", r"截至我的知识|根据现有公开信息|资料较为有限|不排除|大概率|众所周知"),
    ("22 讨好附和", r"说得太对|非常棒的问题|毫无疑问|不得不说"),
    ("23 冗余套话", r"在当前这个时间节点|基于.{0,8}的基础上|进行深入的分析|有能力实现|值得注意的是|需要指出的是"),
    ("24 过度限定", r"在某种程度上可能|一定程度上可能|可能会对部分.{0,6}产生一定"),
    ("25 万能结尾", r"未来可期|拭目以待|共同努力下|书写新的篇章|行稳致远|再创辉煌|乘风破浪"),
    ("26 四字连用", r"凝心聚力|守正创新|踔厉奋发|笃行不怠|攻坚克难|锐意进取"),
    ("27 权威口吻", r"归根结底|从本质上看|真正重要的是|核心在于|底层逻辑|真正的.{0,6}在于"),
    ("28 预告式开场", r"让我们一起|接下来带你|下面将从.{0,8}个方面|话不多说|先说结论|看完你就懂|下面我们来"),
    ("30 改造过程中心", r"我们新增了|替代原有|原来只能|现在支持"),
    ("32 空洞比喻", r"是.{1,10}的底色|是通往.{1,10}的钥匙|让.{1,10}成为可能|时间会给出答案|是一面镜子"),
    ("33 假装坦诚反问", r"说实话？|答案可能出乎意料|问题来了|那么代价是什么|你真的了解"),
]

DENSITY = [
    ("14 破折号", r"——"),
    ("15 加粗", r"\*\*[^*]+\*\*"),
    ("18 emoji", "[\U0001F300-\U0001FAFF☀-➿️]"),
    ("19 直引号", r'[“”]?"[^"\n]{2,20}"'),
]


def scan(path, max_show=8):
    text = io.open(path, encoding="utf-8").read()
    chars = len(text)
    keep = []
    in_code = False
    for ln in text.split("\n"):
        if ln.startswith("```"):
            in_code = not in_code
            keep.append("")
            continue
        keep.append("" if in_code else ln)
    body = "\n".join(keep)

    print("=" * 60)
    print("humanizer-zh 模式扫描:", path, "(%d 字符)" % chars)
    print("=" * 60)

    total = 0
    for name, pat in PATS:
        hits = []
        for i, ln in enumerate(keep, 1):
            for m in re.finditer(pat, ln):
                hits.append((i, m.group(0), ln.strip()[:60]))
        if hits:
            total += len(hits)
            print("\n[%s] %d 处" % (name, len(hits)))
            for i, g, ctx in hits[:max_show]:
                print("  L%-5d %-10s | %s" % (i, g, ctx))
            if len(hits) > max_show:
                print("  ... 另 %d 处" % (len(hits) - max_show))

    print("\n" + "-" * 60)
    for name, pat in DENSITY:
        n = len(re.findall(pat, body))
        if name.startswith("19"):
            print("%-10s %d 处直引号包中文（需人工判断）" % (name, n))
            continue
        print("%-10s %3d 处  %.2f/千字" % (name, n, n * 1000.0 / max(1, chars)))

    print("-" * 60)
    print("模式命中合计: %d 处" % total)
    return total


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="中文 AI 腔扫描")
    ap.add_argument("md")
    ap.add_argument("--max-show", type=int, default=8)
    args = ap.parse_args()
    sys.exit(1 if scan(args.md, args.max_show) else 0)


if __name__ == "__main__":
    main()
