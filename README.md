# 安全文章写作 Skill

一套面向中文安全社区（奇安信攻防社区 / 补天）的长文写作流水线：**选题 → 事实核实 → 靶场实验 → 数据 → 分章起草 → 配图 → 机械终检 → 图床发布**。覆盖 AI 安全、漏洞复现、攻防分析。

## 安装

Claude Code：

```bash
git clone git@github.com:nihaodg/security-article-writing.git \
  ~/.claude/skills/security-article-writing
```

或把整个目录放到项目的 `.claude/skills/` 下。之后在对话里说「写一篇 AI 安全文章」「给这篇文章配图」「做投稿终检」即可触发。

## 快速开始

```bash
# 1. 建目录
mkdir -p my-article/articles my-article/_lab_x

# 2. 按模板起草（分章写，代码块先用占位）
cp templates/article-skeleton.md my-article/articles/x-2026-01-01.md
cp templates/lab-DESIGN.md my-article/_lab_x/DESIGN.md

# 3. 合并分章 + 回填 <<SRC:...>> 代码块（--base 指向靶场所在根目录）
python scripts/build_article.py my-article/articles/x-2026-01-01.md \
  my-article/_part_x1.md my-article/_part_x2.md --base my-article

# 4. 配图（SVG 源码 → 2x PNG）
node scripts/svg2png.js my-article/articles/x-2026-01-01.assets

# 5. 机械终检
python scripts/article_gate.py my-article/articles/x-2026-01-01.md \
  --src-list my-article/_lab_x/srcs.txt --src-base my-article
python scripts/humanizer_scan.py my-article/articles/x-2026-01-01.md
python scripts/reader_path.py my-article/articles/x-2026-01-01.md --base my-article \
  --repro "_lab_x/exp_survey.py:_lab_x/out_survey.txt"

# 6. 推图床并核对
export BUTIAN_SESSION='...' BUTIAN_XSRF='...'
python scripts/cdn_push.py my-article/articles/x-2026-01-01.md
python scripts/verify_cdn.py my-article/articles/x-2026-01-01.md --map cdn_map.txt
```

每一步的详细口径见 `references/` 下对应文档。

## 内容

```
security-article-writing/
├── SKILL.md                     # 入口：原则、流水线、硬规则
├── references/
│   ├── pipeline.md              # 八阶段详细操作
│   ├── style-guide.md           # 中文风格与结构模板
│   ├── figures.md               # 配图规范与工具
│   ├── quality-gates.md         # 终检口径
│   └── publishing.md            # 图床与投稿
├── scripts/
│   ├── build_article.py         # 合并分章 + 源码回填 + 统计
│   ├── article_gate.py          # 机械终检
│   ├── humanizer_scan.py        # 中文 AI 腔扫描
│   ├── reader_path.py           # 读者路径 / 复现校验
│   ├── svgkit.py                # 白底 SVG 绘图库
│   ├── svg2png.js               # SVG 批量转 PNG（Playwright）
│   ├── mac_term_gen.py          # 仿 macOS 终端图
│   ├── mac_term_shot.js         # 终端 HTML → PNG
│   ├── web_shot.js              # 真实网页截图（支持文本定位）
│   ├── shot_section_mark.js     # 按段落截区域 + 输出红框坐标
│   ├── png_mark.py              # 画红框 + 来源条 + 裁边/补白
│   ├── collect_corpus.py        # GitHub 语料采集
│   ├── cdn_push.py              # 奇安信图床推送（凭证走环境变量）
│   └── verify_cdn.py            # CDN 图与本地图一致性校验
└── templates/
    ├── article-skeleton.md      # 文章骨架
    ├── submission-checklist.md  # 投稿清单
    └── lab-DESIGN.md            # 靶场设计模板
```

## 依赖

- Python 3.9+：`requests`；`verify_cdn.py`、`png_mark.py` 另需 `Pillow`
- Node.js + `playwright`（配图转 PNG、真实网页截图需要）
  - 找不到模块时设 `PLAYWRIGHT_MODULE=/path/to/playwright`
  - Chromium 不在默认位置时设 `CHROME_PATH=/path/to/chrome`
- 图床上传需要登录 forum.butian.net，并把 Cookie 放到环境变量 `BUTIAN_SESSION` / `BUTIAN_XSRF`

## 安全说明

仓库内**不含任何凭证**。`.butian-token.json`、Cookie、GitHub PAT 均不应提交。脚本只从环境变量或本地被 gitignore 的文件读取。

## 设计来源

本 skill 抽象自 17 篇已发布/待发布的中文 AI 安全长文的实际生产流程，包含真实踩过的坑：语料覆盖、GitHub 限流、Windows 路径长度、CDN 二次校验、段落节奏与 AI 腔治理。
