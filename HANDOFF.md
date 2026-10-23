# Timeless日常存档：项目接手文档

更新时间：2026-10-23（Asia/Hong_Kong）

这是一套部署在 `timelessice.xyz` 的个人博客与日常存档网站。项目位于 GitHub 仓库：<https://github.com/7imeless/TimelessDailySaves>。

## 项目结构

- `app.py`：Python 标准库 HTTP 服务、SQLite 数据库、路由、认证、Markdown 渲染和页面模板。
- `index.html`：首页静态骨架；启动时由 `app.py` 替换文章列表、搜索信息、日历、Todo 和登录导航占位符。
- `styles.css`：网站公共样式、文章样式、归档页样式、后台样式。
- `admin.js`：后台图片上传、封面上传和正文图片插入逻辑。
- `assets/background.jpg`：网站背景图。
- `assets/favicon.svg`：浏览器标签页图标。
- `uploads/`：文章正文图片和封面图片；生产环境必须备份。
- `requirements.txt`：当前依赖 `markdown-it-py>=3.0,<5.0`。
- `README.md`：基础运行说明。

项目使用 Python 3.12 和 SQLite，不使用前端框架。生产服务名为 `timelessice.service`，应用监听本机 `127.0.0.1:8000`，外部通过 Nginx 和 HTTPS 访问。

## 已完成的功能

### 公共页面

- 黑色极简首页，网站名称为“Timeless日常存档”。
- 首页文章列表、文章封面、分类、标签、阅读时长。
- 文章详情页、阅读进度条、封面图和自动目录。
- 文章归档页：`/archive`，按年份和月份展示已发布文章。
- 首页站内搜索：输入或提交搜索时通过 `/search?q=...` 无刷新更新文章列表。
- 标签筛选：文章卡片上的标签可以直接筛选首页内容。
- 日历和 Todo；日期切换、添加、编辑、完成和删除均使用局部请求，尽量避免整页刷新。
- 登录、注册、注册开关、邀请码注册。
- 页脚备案号：`鲁ICP备2026053385号`。

### 管理后台

- `/admin`：文章管理。
- `/admin/new`：新建文章。
- `/admin/edit?id=...`：编辑文章。
- `/admin/accounts`：注册设置、管理员密码修改、普通账号管理。
- 支持草稿、已发布、私密文章三种状态。
- 支持分类、逗号分隔的标签、摘要、URL 标识、正文封面和正文图片上传。
- 已删除实时 Markdown 预览功能；编辑页目前只有 Markdown 文本编辑器。

### Markdown

正文使用 `markdown-it-py` 渲染，禁止原始 HTML，避免把文章内容直接当作 HTML 执行。

目前支持：

- 一级至六级标题，并自动生成标题锚点。
- 有序列表、无序列表、任务列表。
- 代码块，支持三反引号和三波浪线。
- 表格、引用、粗体、斜体、行内代码。
- 普通链接、引用链接、标题锚点链接和直接粘贴 URL。
- 图片、脚注、下划线、高亮、下标、上标和 Emoji 短代码。
- 行内数学公式和多行块级数学公式；文章页通过 MathJax CDN 渲染。
- 正文图片会限制在文章内容宽度内，自动缩放，不应横向溢出。

示例：

```markdown
行内公式：$x^2$

$$
\\frac{\\partial f}{\\partial x} = 2\\sqrt{a}x
$$

```typescript
const message = "hello";
```
```

## 私密文章权限规则

- `published`：所有访客可见。
- `draft`：不出现在公共页面，管理员后台可管理，但详情页不会作为公开文章返回。
- `private`：只有已登录且角色为 `admin` 的用户可以访问。
- Admin 登录后，首页会显示私密文章，搜索也会返回私密文章。
- 普通访客和普通用户的首页、搜索、归档都不会显示私密文章。
- 私密文章详情地址仍然是 `/post/<slug>`；未授权用户得到 404。

## 数据库

默认数据库文件为项目目录下的 `timeless.db`，也可以通过环境变量 `TIMELESS_DB` 指定。

主要表：

- `users`：账号、密码摘要、角色、启用状态。
- `settings`：注册模式和邀请码摘要。
- `todos`：用户独立的 Todo。
- `articles`：标题、slug、分类、标签、摘要、封面、Markdown 正文、状态和时间字段。

`app.py` 启动时会执行 `init_db()`，会自动补充缺失的 `articles.tags` 和 `articles.cover_image` 字段。生产数据库迁移前仍建议先备份 `timeless.db`。

## 生产部署信息

- 服务器：阿里云 ECS，Ubuntu 24.04 LTS。
- SSH 用户：`admin`。
- 项目目录：`/home/admin/timelessice`。
- 服务：`timelessice.service`。
- 反向代理：Nginx。
- 域名：`https://timelessice.xyz`。
- GitHub：`https://github.com/7imeless/TimelessDailySaves`。

不要把私钥内容、管理员密码、Cookie、邀请码或数据库中的密码摘要写入 Git 或接手文档。当前 Windows 本地私钥文件由用户保存，后续操作前应向用户确认其本地路径是否仍有效。

常用生产命令：

```bash
sudo systemctl status timelessice --no-pager -l
sudo journalctl -u timelessice -n 80 --no-pager
sudo systemctl restart timelessice
curl -I http://127.0.0.1:8000/
sudo ss -lntp | grep ':8000'
```

代码或静态资源更新的一般流程：

```bash
git status
git add app.py admin.js index.html styles.css requirements.txt
git commit -m "描述本次修改"
git push origin main
# 使用用户授权的 SSH 私钥上传到 /home/admin/timelessice/
sudo systemctl restart timelessice
```

文章和图片保存于 SQLite/`uploads/`，发布文章会立即生效；修改 Python、HTML 或 CSS 后需要重启 systemd 服务。Ubuntu 的 PEP 668 可能阻止直接 `pip install --user`，生产机目前已经安装 `markdown-it-py`；如果依赖缺失，应创建虚拟环境或使用 `--break-system-packages` 前先评估影响。

## 最近提交

- `7c1e692`：限制正文图片在文章内容边界内。
- `12873ff`：让 admin 登录后在首页看到私密文章。
- `439bd7b`：加入无刷新搜索和私密文章基础状态。
- `d5ee3ec`：移除实时预览并加入文章归档页。
- `8b0b549`：加入实时预览、搜索、标签和文章目录（实时预览之后已被删除）。
- `3bff23f`：支持多行块级数学公式。
- `ad2bbc6`：修复代码块后正文被包进代码块的问题。

当前工作区在生成本文件前应保持干净；任何新改动都应先运行 `python -m py_compile app.py` 和 `git diff --check`，再做本地页面回归，最后再部署。

## 后续可以考虑

- 草稿自动保存和文章自动备份。
- 文章定时发布。
- RSS、站点地图和更完整的 SEO 元信息。
- 代码片段库、书签收藏、快速备忘录等站外工具。
- 图片拖拽上传和更完善的媒体管理。
- 生产数据库与 `uploads/` 的定期备份和恢复演练。

## 2026-10-23 正式前端更新

正式站前端已根据最新 `demo/` 适配。Demo 是设计参考，生产页面仍由 Python 服务端渲染并使用真实数据库与权限。

- `frontend.py`：共享页面外壳、首页、归档、文章和登录注册渲染。
- `templates/`：从 Demo 提取的共享导航、页脚、归档和账号模板。
- `assets/ui/`：复用 Demo 样式、导航、归档、阅读交互；`production.css` / `site.js` 为正式接口适配。
- 根目录 `index.html`：正式首页模板，不再包含示例文章；动态填充文章、分类、标签、收支概览和账号状态。
- `money.py`、`word_learning.py` 保留业务逻辑，更新页面结构；`money.js`、`words.js` 保留真实接口与 CSRF。
- 全站主题继续使用 `timeless-theme`；手机导航显示真实账号，待办跨设备保存。
- 单词仍为 ECDICT CET6 5,407 词，基础间隔规则，未接入 FSRS。
- 账本保留按账号隔离、整数分金额、编辑、筛选、分页、删除确认和服务端 CSV。
- 新增 `tests/test_frontend.py` 检查服务端内容、私密文章、转义、注册模式和真实表单。

部署需一起同步 `app.py`、`frontend.py`、`index.html`、`money.py`、`word_learning.py`、`money.js`、`words.js`、`templates/`、`assets/ui/`。不要覆盖生产数据库、上传文件或环境配置。旧后台仍沿用 `styles.css` / `admin.js`，公共页面使用新 UI 资源。

Sunny 已独立部署于 `/opt/sunny-web`，systemd 服务 `sunny`，监听 `127.0.0.1:8010`，公开入口为 `https://timelessice.xyz/sunny/`。本次博客前端部署不修改 Sunny。SSH 私钥仅用于连接，不进入部署包或 Git。
