# 配图规范

## 总则

- 每张图只讲一个判断；图内大标题就是这个判断，不是「图 3 流程图」。
- 白底、扁平、无阴影、无渐变；线宽 1–2px；圆角 8。
- 宽度固定 `1240`，高度按内容 400–900。
- 字号：标题 22、副标题 15、正文 14–15、注释 12–13。
- 颜色只承担语义：红=危险/失败，绿=通过/修复，黄=警告/未决，蓝=中性/信息，灰=背景。
- 图内不出现正文没说的新结论；不堆英文术语。
- 所有图放在 `<article>.assets/`，同时保留 `.svg` 源文件与 `.png` 成品。

## 调色板

```python
INK   = "#212529"   SUB = "#495057"   MUTE = "#868e96"   LINE = "#dee2e6"
RED   = ("#fdecee", "#f0b3ba", "#a51d2b")
GREEN = ("#e4f4ea", "#a8d5b8", "#136c39")
WARN  = ("#fdf3e2", "#eccf9d", "#8a5a12")
BLUE  = ("#e7f1ff", "#a8c7f0", "#0b4ea2")
GRAY  = ("#f6f8fa", "#cdd4dc")
```

## 六种图型

| 图型 | 用途 | 要点 |
|---|---|---|
| 机制链 | 攻击/数据在组件间如何流动 | 3–6 个方框，箭头单向；每步写「谁做了什么」 |
| 对照矩阵 | 几种做法/视图的拦截率 | 行=载荷/场景，列=做法，命中用红、拦住用绿 |
| 数据条形 | 分类占比 | 条形长度按真实比例；右端标 `106 (40.6%)` |
| 时间线 | 披露、报告、修复、利用 | 只放有日期的节点；节点下写一句后果 |
| 分层防御 | 防御清单与优先级 | 三层以内；每层给一条可执行动作 |
| 决策树 | 「该不该拦/该不该信」 | 每个分叉是一个可回答的问题 |

## SVG 生成

用 `scripts/svgkit.py`：

```python
from svgkit import *
write(ASSETS, "fig-1-chain.svg", "".join(body), height=660)
```

`svgkit.py` 提供：`txt / rect / line / table / head / write`，`W=1240`，白底。

自定义 `box()` 与 `arrow()` 的写法见模板：

```python
def box(x, y, w, h, title, sub="", bg=GRY_BG, ln=GRY_LN, tc=INK, ts=15):
    ...
def arrow(x1, y1, x2, y2, color=LINE, sw=2):
    ...  # 主线 + 两条箭头边
```

注意：

- `txt` 使用 `text-anchor="middle"` 做居中，不要靠空格对齐。
- 多行副标题用 `\n` 手动拆行，每行 ≤ 18 个中文字符。
- 图形底部留 40px 空白，防止 PNG 裁切。
- 写一个 `check_bounds`：遍历 `<text>`，任何元素超出 viewBox 就报错。

## SVG → PNG

```bash
node scripts/svg2png.js articles/x.assets
# 或指定文件
node scripts/svg2png.js articles/x.assets/fig-1.svg articles/x.assets/fig-2.svg
```

脚本用 Playwright Chromium，`deviceScaleFactor: 2`，白底，按 SVG 自身宽高截图，并检查文字是否越界。

## 终端图

用 `scripts/mac_term_gen.py`：

```python
from mac_term_gen import render
render({
    "title": "复现 ① 正常配置加载",
    "prompt": ("PS", "C:\\LAB"),
    "lines": [
        ("cmd", "python exp_survey.py"),
        ("blank", ""),
        ("label", "[scan]  261 个配置"),
        ("green", "结论：exec 40.6% / approval 14.6% / 兼有 6.5%"),
        ("banner", "审批只看到「多了一个字段」，看不到后果"),
    ],
}, "articles/x.assets/term-1-survey.png")
```

行的语义色：`cmd / dim / label / green / red / yellow / orange / banner / banner-ok / header / blank`。
终端图必须是**真实运行输出**，不能编造。

## 真实截图

真实截图分三步，抓图、定位、标注分开做，坐标不靠肉眼估。

### 1. 抓图：`web_shot.js`

```bash
# 整页
node scripts/web_shot.js "https://example.com/post" out/page.png

# 只截包含某段文字的最小元素
node scripts/web_shot.js "https://example.com/post" out/page.png "text:CVE-2025-53773"

# 再往上数 2 层祖先，截更大的容器
node scripts/web_shot.js "https://example.com/post" out/page.png "text:CVE-2025-53773@2"

# 区域截图（页面坐标），同时给出要框文本的设备像素坐标
node scripts/web_shot.js "https://example.com/post" out/page.png "" "漏洞描述" \
  "0,300,1265,700" "autoApproveCommands"
```

脚本会：

- 1280×900、`deviceScaleFactor: 2`、桌面 UA；
- 自动删除 cookie/遮罩弹窗、左侧窄栏、右侧 fixed 浮标（`HIDE_LEFT` / `HIDE_RIGHT` 控制）；
- 支持 `waitText` 等待页面加载完成；
- 给 `boxText` 时输出 `BOX x,y,w,h`（已乘 2），供下一步画框。

### 2. 按段落精确定位：`shot_section_mark.js`

```bash
node scripts/shot_section_mark.js "https://example.com/post" \
  out/fig-7.png "漏洞描述" 4 0 1265 "CVE-2025-53773"
```

从包含「漏洞描述」的第一个 `<p>` 起取 4 段，滚到该区域截图，并把「CVE-2025-53773」所在段落的坐标写进 `out/fig-7.png.box.json`。

### 3. 画红框 + 来源条：`png_mark.py`

```bash
# 用上一步产出的坐标
python scripts/png_mark.py out/fig-7.png articles/x.assets/fig-7-page.png \
  --box-json out/fig-7.png.box.json \
  --caption "来源：example.com/post，抓取日期 2026-11-14"

# 或手动给坐标（输入图像像素）
python scripts/png_mark.py in.png out.png --box 120,340,680,90 \
  --caption "来源：NVD，抓取日期 2026-11-14" --pad 12
```

标注规范：

- 红框颜色 `(220, 30, 30)`，内外两层（2px + 4px），缩略图上也看得见；
- 来源条 46px 左右、灰底 `#f6f8fa`、细灰线分隔，写清「站点/路径 + 抓取日期」；
- 只框关键字段，一张图不超过 2 个框；
- 隐私信息打码；不截入自身账号、Cookie、内网地址；
- 需要滚动截长页时用固定 viewport，避免拼接错位。

### 截图验收

- 页面没有登录态、弹窗、浮标残留；
- 红框正好落在目标文字上，不偏半个字；
- 来源条文字完整、不压图；
- 2x 输出，宽度 ≥ 2000px；
- 与正文 alt 描述一致。

## 图注（alt）

- 格式：`![这张图说明了什么](path)`，一句话，20–50 字。
- 不写「图 1」「示意图」「如下所示」。
- alt 要与图内标题一致，图内标题与正文引用句一致。

示例：

```markdown
![配置注入的完整链条：不可信内容、Agent 读取、改配置、用户批准、下次加载、攻击者执行](x.assets/fig-1-injection-chain.png)
```

## 配图验收

| 检查 | 标准 |
|---|---|
| 数量 | 6–13 张，正文每 2–3 章至少 1 张 |
| 文件 | svg + png 成对；PNG 宽度 2480（2x） |
| 越界 | 0 个文字/图形超出画布 |
| alt | 非空，且不是「图 N」 |
| 位置 | 不落在表格中间、不连续堆叠 |
| 一致性 | CDN 图与本地图尺寸相同，像素差 < 5%，锐度差 < 3% |
| 来源 | 截图有来源条；终端图可复跑 |
