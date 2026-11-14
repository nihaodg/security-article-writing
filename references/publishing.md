# 图床与投稿

## 奇安信图床（主）

- 上传接口：`POST https://forum.butian.net/image/uploadS3`
- 返回：纯文本 CDN URL
- CDN 前缀：`https://cdn-yg-zzbm.yun.qianxin.com/attack-forum/`
- 必需请求头：
  - `X-Requested-With: XMLHttpRequest`（缺了会返回登录页 HTML）
  - `X-CSRF-TOKEN: <XSRF-TOKEN 值>`
  - `Cookie: __Host-attack_session=...; XSRF-TOKEN=...`
  - `Referer: https://forum.butian.net/share/create`
- 不要手动设置 `Host`、`Connection`，requests 会冲突。
- 上传间隔 0.5s；Cookie 约 1–2 小时过期。

### 凭证管理

**不要把 token 写进脚本或提交到仓库。**

```bash
# 方式一：环境变量
export BUTIAN_SESSION='__Host-attack_session 的值'
export BUTIAN_XSRF='XSRF-TOKEN 的值'

# 方式二：本地文件（加入 .gitignore）
# .butian-token.json
# {"host_session": "...", "xsrf": "..."}
```

`.gitignore` 至少包含：

```
.butian-token.json
*.token
.env
```

### 推送流程

```bash
# 1. 检查：本地图 / CDN 图各多少
python scripts/cdn_push.py articles/x.md --check

# 2. 预览
python scripts/cdn_push.py articles/x.md --dry-run

# 3. 实推并替换 MD 中的本地路径
python scripts/cdn_push.py articles/x.md

# 4. 验证 CDN 图与本地一致
python scripts/verify_cdn.py articles/x.md --map cdn_map.txt
```

推送只替换 `![...](<slug>.assets/xxx.png)` 这种相对路径，不动其他链接。

### CDN 映射表

`cdn_map.txt` 每行 `文件名|URL`。改稿后不要重推图：

```bash
python scripts/cdn_push.py articles/x.md --apply-map cdn_map.txt
```

## 备用图床

- GitHub 仓库 + jsDelivr：`https://cdn.jsdelivr.net/gh/<user>/<repo>@<branch>/<path>`
- 适合做灾备；正文可保留主图床，清单里记录备用 URL。
- 提交前用 `HEAD` 匿名验证一次可达性。

## 可达性验证

```bash
python scripts/verify_cdn.py articles/x.md --head-only
```

要求：每张图 HEAD 200，`Content-Type` 为 `image/*`，`Content-Length` > 0。
若失败：先重试 3 次（指数退避），再判断是否 Cookie/图床故障。

## 投稿清单

用 `templates/submission-checklist.md`。填写要点：

| 字段 | 说明 |
|---|---|
| 文件 / 标题 | 与成稿完全一致 |
| 频道 | AI 安全（forum.butian.net/ai_security） |
| 类型 | 998 / AI安全 |
| 主分类 | 117 数据安全（按内容调整） |
| 备选分类 | 114 安全开发 / 121 边界安全 / 118 业务安全 |
| 字符数 / 行数 | 用 `wc` 或构建脚本输出 |
| 章节 / 表格 / 代码块 / 图 | 脚本统计 |
| 第三方依赖 | 只列公开、免费、无需账号的 |
| 靶场 / 数据源 | 目录与公开来源 |
| 图床状态 | 已推张数 / 总张数 / HEAD 结果 |

## 发布步骤

1. 登录 forum.butian.net，新开投稿页，选频道「AI 安全」。
2. 粘贴标题。
3. 粘贴正文（Markdown 渲染后检查标题层级、表格、代码高亮）。
4. 逐张确认图片显示；正文里应全是 CDN URL。
5. 选主分类与备选分类。
6. 预览移动端：表格是否横向溢出、代码是否换行错乱。
7. 提交。
8. 发布后回填文章 URL 到投稿清单。

## 发布后

- 保留 `cdn_map.txt`、终检输出、原始数据目录，便于勘误。
- 若需改稿：本地改 → 重跑 gate → 重推变更图 → 更新文章，不要只在线编辑。
- 发现数字错误：在文末加勘误说明，同时修本地源文件与统计输出，避免下次复用错误数字。
