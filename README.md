# Timeless日常存档

这是一个带在线写作后台的个人博客。公共页面保持纯黑色极简风格，文章使用 SQLite 保存，正文使用 Markdown 编写。

## 本地运行

在项目目录执行：

```powershell
$env:TIMELESS_ADMIN_PASSWORD = "请换成你的本地密码"
python app.py
```

然后打开：

- 网站：`http://127.0.0.1:8000/`
- 写作后台：`http://127.0.0.1:8000/admin`

第一次启动会自动创建 `timeless.db`，并写入 5 篇当前页面的示例文章。之后从后台新建的文章都会直接保存到这个数据库。

## 写文章

1. 打开 `/admin`，输入管理员密码。
2. 点击“新建文章”。
3. 填写标题、分类、摘要和 Markdown 正文。
4. 选择“保存为草稿”或“立即发布”。
5. 已发布文章会出现在首页，并拥有 `/post/文章标识` 详情地址。

支持的 Markdown 基础语法包括标题、列表、引用、粗体、斜体、图片、行内代码、链接和代码块。编辑文章时点击“上传图片”，选择 JPEG、PNG、GIF 或 WebP 图片，上传完成后会自动插入正文；单张图片最大 8 MB。

文章可以单独上传横向封面，封面会显示在首页文章列表和文章详情页。文章详情页顶部会根据滚动位置显示阅读进度。

## 阿里云部署建议

服务器上安装 Python 3 后，将项目上传到独立目录，设置环境变量并运行：

```bash
export TIMELESS_ADMIN_PASSWORD='请设置一个强密码'
export TIMELESS_HOST='127.0.0.1'
export PORT='8000'
export TIMELESS_COOKIE_SECURE='1'  # 通过 HTTPS 访问时启用
python3 app.py
```

生产环境建议使用 Nginx 反向代理并配置 HTTPS，同时将 `client_max_body_size` 设置为不小于 `8m`。`timeless.db` 是文章数据库，`uploads/` 保存文章图片，两者都需要定期备份。发布文章是即时生效的，不需要重启进程；只有修改 HTML、CSS 或 Python 代码时才需要重新部署。

当前实现适合个人站点或低流量博客。正式公开前请使用强管理员密码、HTTPS，并限制服务器安全组只开放必要端口。
