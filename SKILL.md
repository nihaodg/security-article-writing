---
name: security-article-writing
description: 证据驱动的中文安全长文写作流水线，覆盖 AI 安全、漏洞复现、攻防分析。包含选题、外部事实核实、真实语料实验、分章起草、SVG 与终端配图、机械终检、奇安信（补天）图床发布。当用户要写安全文章、漏洞复现、技术长文、给文章配图、生成投稿清单或推送图床时使用。
---

# 安全文章写作流水线

把「写一篇能过审、能被复现、数字经得起查的中文安全长文」拆成可执行、可机械检查的八步。适用平台：奇安信攻防社区（forum.butian.net）、补天等中文安全社区。

## 核心原则

1. **结论来自自己的数据。** 不复述新闻稿。要么自己采集语料跑统计，要么自己搭靶场跑实验，要么逐条读公开数据并给出处。
2. **外部事实逐条登记。** CVE 编号、CVSS、披露日期、修复版本、论文结论，全部进「外部事实核实记录」表，标来源与核实状态。
3. **代码块从磁盘回填。** 正文里的脚本、JSON、终端输出不手抄，用 `# <<SRC:path>>` 标记，构建时从真实文件同步。读者复制出去必须能跑。
4. **数字可追溯。** 本地统计数字必须来自 `out_*.txt`；外部数字必须有来源。正文出现的每个小数都能指回某个文件或某个 URL。
5. **图先有信息，再有装饰。** 每张图只讲一件事；白底、扁平、无阴影；图内不写正文没说的结论。
6. **终检机械化。** 风格、围栏、图片、路径、数字、代码一致性全部用脚本查，不靠肉眼。

## 目录约定

```
project/
├── articles/                    # 成稿：<slug>-<YYYY-MM-DD>.md
│   └── <slug>-<YYYY-MM-DD>.assets/   # 配图（png/svg/jpg）
├── _lab_<slug>/                 # 靶场：实验脚本、数据、out_*.txt、DESIGN.md
├── _part_<slug>1.md …           # 分章草稿（合并后可删）
├── _build_<slug>.py             # 合并 + 回填 + 统计
├── _gate_<slug>.py              # 本篇终检
├── _reader_path_<slug>.py       # 读者路径校验
├── _submission-checklist-<slug>-<date>.md
├── cdn_map.txt                  # 图片名|CDN URL，换稿后免重推
└── .butian-token.json           # 凭证，绝不入库
```

正文文件命名：`主题-slug-日期.md`，例如 `ai-agent-config-injection-persistence-2026-11-14.md`。

## 八阶段流水线

| 阶段 | 动作 | 产物 | 参考 |
|---|---|---|---|
| 0 选题 | 找「新落点 / 有数据 / 能复现」的交集 | 一句话卖点 + 章节表 | `references/pipeline.md` |
| 1 事实 | 官方公告、CVE、论文、仓库逐条核实 | 外部事实表 | `references/pipeline.md` |
| 2 靶场 | 建 `_lab_<slug>/`，写 DESIGN.md，跑通最小复现 | 可重跑脚本 | `references/pipeline.md` |
| 3 数据 | 采集语料 / 跑实验 / 逐条读轨迹 | `out_*.txt` + 原始数据 | `references/pipeline.md` |
| 4 起草 | 按章写 `_part_*.md`，每章至少一张表 | 分章稿 | `references/style-guide.md` |
| 5 配图 | 白底 SVG / 终端图 / 真实截图 | `*.assets/` | `references/figures.md` |
| 6 合并 | 合并分章 + `<<SRC>>` 回填 + 统计 | 成稿 md | `scripts/build_article.py` |
| 7 终检 | 门禁 + humanizer + 读者路径 | 0 问题 | `references/quality-gates.md` |
| 8 发布 | 推图床 + 写投稿清单 | CDN URL + checklist | `references/publishing.md` |

## 硬性风格规则

- 结构：标题 → `---` → **摘要**（三段：背景 / 方法 / 数字结论）→ **关键词** → 正文 10–12 章 → 结语。
- 每章 `## 一、二、三…`，至少一张表格；表格用中文表头，数字右对齐。
- 破折号 `——` **< 3 处/千字**；「不是…而是」**≤ 1 次**；加粗 **< 7 处/千字**。
- 段落长度 CV **≥ 0.5**（长短交错，别写成均匀的 AI 段落）。
- 禁止：emoji、LaTeX、附录章节、空代码块、无语言标识的围栏、本机绝对路径。
- 代码块内容必须来自磁盘真实文件；终端输出块必须是真实运行结果。
- 每张图 alt 非空，且描述「图说明了什么」，不是「图 1」。
- 不写「综上所述」「未来可期」「不仅…更是」这类收尾套话。

## 快速命令

```bash
# 合并分章 + 回填代码 + 统计
python scripts/build_article.py articles/x.md parts/_part_x1.md parts/_part_x2.md ...

# 机械终检（围栏/风格/图/路径/代码语法）
python scripts/article_gate.py articles/x.md --cdn-host cdn-yg-zzbm.yun.qianxin.com

# 中文 AI 腔扫描
python scripts/humanizer_scan.py articles/x.md

# 读者路径校验（代码块可跑、输出一致、关键事实在正文）
python scripts/reader_path.py articles/x.md --repro "_lab_x/exp_survey.py:_lab_x/out_survey.txt"

# SVG → PNG（2x，白底）
node scripts/svg2png.js articles/x.assets

# 真实网页截图 → 定位要框的句子 → 画红框 + 来源条
node scripts/web_shot.js "https://example.com/post" out/page.png "" "漏洞描述" "0,300,1265,700" "autoApproveCommands"
node scripts/shot_section_mark.js "https://example.com/post" out/fig-7.png "漏洞描述" 4 0 1265 "CVE-2025-53773"
python scripts/png_mark.py out/fig-7.png articles/x.assets/fig-7-page.png \
  --box-json out/fig-7.png.box.json --caption "来源：example.com/post，抓取日期 2026-11-14"

# 推奇安信图床（凭证走环境变量，勿写死）
export BUTIAN_SESSION='...' BUTIAN_XSRF='...'
python scripts/cdn_push.py articles/x.md --check
python scripts/cdn_push.py articles/x.md
```

## 交付判定

一篇文章算完成，必须同时满足：

- `article_gate.py` 问题数 **0**
- `humanizer_scan.py` 模式命中 **0**（或逐条人工豁免并记录）
- `reader_path.py` 全通过
- 每章至少 1 表，全文至少 6 图
- 所有本地图已推 CDN，MD 内本地路径残留 **0**
- 投稿清单已填：字符数、章节、表格、代码块、图、分类、CDN 状态、终检结果

## 常见坑

1. **语料文件名必须带仓库名**，否则同类文件互相覆盖，302 会莫名变成 211。
2. **删除前必须得到明确指令。** 实验目录里常有唯一副本。
3. **GitHub API 限流**，源码优先走 `cdn.jsdelivr.net/gh/<repo>@<ref>/<file>`。
4. **Windows 路径长度**会让深层解压失败，用短根目录（如 `C:/lab`）。
5. **中文 heredoc 走 .py 文件**，不要塞进 `bash -c`。
6. **带网络请求的循环要分批**，单次控制在 1 分钟内，避免命令被掐断。
7. **CDN 映射用 `cdn_map.txt`**：改稿后 build → apply → 终检，不重推图。
8. **凭证不入库。** `.butian-token.json` 加进 `.gitignore`；脚本只从环境变量或本地文件读。
9. **gate 的段落 CV 口径包含表格块**，不要用自己的严格口径去否定它。
10. **图推完后保留本地原图**，CDN 图要与本地做尺寸/像素/锐度比对。

## 参考文件

- `references/pipeline.md` — 八阶段详细操作与实验设计
- `references/style-guide.md` — 中文风格、结构模板、33 条 AI 腔模式
- `references/figures.md` — 配色、版式、SVG/终端/截图规范
- `references/quality-gates.md` — 终检口径、阈值、读者路径
- `references/publishing.md` — 图床、投稿清单、发布流程
- `scripts/` — 可直接复用的构建、终检、配图、采集、发布脚本
- `templates/` — 文章骨架、投稿清单、靶场设计模板
