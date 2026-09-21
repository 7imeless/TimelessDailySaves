from __future__ import annotations

import html
import calendar
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit
from zoneinfo import ZoneInfo


BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "index.html"
STYLES_PATH = BASE_DIR / "styles.css"
ADMIN_JS_PATH = BASE_DIR / "admin.js"
ASSETS_DIR = BASE_DIR / "assets"
UPLOADS_DIR = BASE_DIR / "uploads"
FAVICON_PATH = ASSETS_DIR / "favicon.svg"
BRAND_MARK = '<span class="brand-mark" aria-hidden="true"></span>'
FAVICON_LINK = '<link rel="icon" href="/assets/favicon.svg?v=1" type="image/svg+xml">'
DB_PATH = Path(os.environ.get("TIMELESS_DB", str(BASE_DIR / "timeless.db")))
HOST = os.environ.get("TIMELESS_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
ADMIN_PASSWORD = os.environ.get("TIMELESS_ADMIN_PASSWORD", "local-change-this")
COOKIE_SECURE = os.environ.get("TIMELESS_COOKIE_SECURE", "0") == "1"
SESSIONS: dict[str, dict[str, str]] = {}
MAX_BODY_SIZE = 2 * 1024 * 1024
MAX_IMAGE_SIZE = 8 * 1024 * 1024

SEED_ARTICLES = [
    {
        "title": "缓存失效之后：一次关于“新鲜感”的系统思考",
        "slug": "cache-invalidation",
        "category": "工程实践",
        "excerpt": "从一个线上事故出发，聊聊缓存、认知和我们为什么总会忘记更新。",
        "content": """# 缓存失效之后\n\n从一个线上事故出发，聊聊缓存、认知和我们为什么总会忘记更新。\n\n## 新鲜感不是默认存在的\n\n系统里的每一份数据，都需要有人负责让它保持新鲜。代码如此，记忆也是如此。\n\n```ts\nconst nextValue = await refresh(cacheKey);\n```\n""",
        "date": "2026-08-24",
    },
    {
        "title": "当我不再追逐“最佳实践”",
        "slug": "less-best-practices",
        "category": "前端",
        "excerpt": "工具会变，但判断问题的方式可以留下。",
        "content": """# 当我不再追逐“最佳实践”\n\n工具会变，但判断问题的方式可以留下。\n\n所谓最佳实践，常常只是某个上下文里的好答案。先理解问题，再选择工具。\n""",
        "date": "2026-07-16",
    },
    {
        "title": "读《设计心理学》：好的默认值",
        "slug": "good-defaults",
        "category": "读书",
        "excerpt": "少一个选择，有时就是多一点自由。",
        "content": """# 好的默认值\n\n少一个选择，有时就是多一点自由。好的默认值不是替用户做决定，而是替用户省下不必要的决定。\n""",
        "date": "2026-06-08",
    },
    {
        "title": "给忙碌的人留一块没有通知的地方",
        "slug": "a-place-without-notifications",
        "category": "随笔",
        "excerpt": "关于注意力、边界和一个下午的散步。",
        "content": """# 没有通知的地方\n\n关于注意力、边界和一个下午的散步。\n\n有些空白不是浪费，它们只是还没有被安排。\n""",
        "date": "2026-04-29",
    },
    {
        "title": "把“可观测”从口号变成习惯",
        "slug": "observability-as-a-habit",
        "category": "系统设计",
        "excerpt": "日志、指标和那些真正需要被看见的信号。",
        "content": """# 把“可观测”从口号变成习惯\n\n日志、指标和那些真正需要被看见的信号。系统不会主动解释自己，除非我们提前为它留下足够的线索。\n""",
        "date": "2026-03-12",
    },
]


def db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL
            )
            """
        )
        user_columns = {row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        if "role" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        admin_user = connection.execute("SELECT id, password_hash FROM users WHERE username = 'admin'").fetchone()
        if admin_user is None:
            connection.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES ('admin', ?, 'admin', ?)",
                (hash_password(ADMIN_PASSWORD), utc_now()),
            )
        else:
            if not verify_password(ADMIN_PASSWORD, admin_user["password_hash"]):
                connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(ADMIN_PASSWORD), admin_user["id"]))
            connection.execute("UPDATE users SET role = 'admin' WHERE id = ?", (admin_user["id"],))
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL,
                is_done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL DEFAULT '随笔',
                excerpt TEXT NOT NULL DEFAULT '',
                cover_image TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
            """
        )
        article_columns = {row[1] for row in connection.execute("PRAGMA table_info(articles)").fetchall()}
        if "cover_image" not in article_columns:
            connection.execute("ALTER TABLE articles ADD COLUMN cover_image TEXT NOT NULL DEFAULT ''")
        if connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0:
            now = utc_now()
            connection.executemany(
                """
                INSERT INTO articles
                (title, slug, category, excerpt, content, status, created_at, updated_at, published_at)
                VALUES (?, ?, ?, ?, ?, 'published', ?, ?, ?)
                """,
                [
                    (
                        item["title"],
                        item["slug"],
                        item["category"],
                        item["excerpt"],
                        item["content"],
                        f"{item['date']}T09:00:00+08:00",
                        now,
                        f"{item['date']}T09:00:00+08:00",
                    )
                    for item in SEED_ARTICLES
                ],
            )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def display_date(value: str) -> str:
    return value[:10].replace("-", ".")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug[:70] or f"post-{secrets.token_hex(4)}"


def unique_slug(connection: sqlite3.Connection, value: str, article_id: int | None = None) -> str:
    base = slugify(value)
    candidate = base
    suffix = 2
    while True:
        row = connection.execute("SELECT id FROM articles WHERE slug = ?", (candidate,)).fetchone()
        if row is None or (article_id is not None and row["id"] == article_id):
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def valid_uploaded_image_url(value: str) -> bool:
    return re.fullmatch(r"/uploads/[0-9]{8}-[0-9]{6}-[a-f0-9]{10}\.(jpg|png|gif|webp)", value) is not None


def escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def inline_markdown(value: str) -> str:
    safe = html.escape(value, quote=True)
    safe = re.sub(
        r"!\[([^\]]*)\]\(((?:/uploads/[a-zA-Z0-9._-]+|https?://[^\s)]+))\)",
        r'<img src="\2" alt="\1" loading="lazy">',
        safe,
    )
    safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
    safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", safe)
    safe = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r'<a href="\2" target="_blank" rel="noreferrer">\1</a>',
        safe,
    )
    return safe


def markdown_to_html(markdown: str) -> str:
    output: list[str] = []
    in_code = False
    code_language = ""
    list_open = False
    for raw_line in markdown.replace("\r\n", "\n").split("\n"):
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                output.append("</code></pre>")
                in_code = False
            else:
                code_language = re.sub(r"[^a-zA-Z0-9_-]", "", line[3:])
                language_attr = f' class="language-{code_language}"' if code_language else ""
                output.append(f"<pre><code{language_attr}>")
                in_code = True
            continue
        if in_code:
            output.append(html.escape(line, quote=False))
            output.append("\n")
            continue
        if not line:
            if list_open:
                output.append("</ul>")
                list_open = False
            continue
        if line.startswith("### "):
            output.append(f"<h3>{inline_markdown(line[4:])}</h3>")
        elif line.startswith("## "):
            output.append(f"<h2>{inline_markdown(line[3:])}</h2>")
        elif line.startswith("# "):
            output.append(f"<h1>{inline_markdown(line[2:])}</h1>")
        elif line.startswith("- ") or line.startswith("* "):
            if not list_open:
                output.append("<ul>")
                list_open = True
            output.append(f"<li>{inline_markdown(line[2:])}</li>")
        elif line.startswith("> "):
            output.append(f"<blockquote>{inline_markdown(line[2:])}</blockquote>")
        elif re.fullmatch(r"-{3,}", line):
            output.append("<hr>")
        else:
            if list_open:
                output.append("</ul>")
                list_open = False
            output.append(f"<p>{inline_markdown(line)}</p>")
    if in_code:
        output.append("</code></pre>")
    if list_open:
        output.append("</ul>")
    return "\n".join(output)


def published_articles() -> list[sqlite3.Row]:
    with db_connection() as connection:
        return connection.execute(
            "SELECT * FROM articles WHERE status = 'published' ORDER BY published_at DESC, updated_at DESC"
        ).fetchall()


def all_articles() -> list[sqlite3.Row]:
    with db_connection() as connection:
        return connection.execute("SELECT * FROM articles ORDER BY updated_at DESC").fetchall()


def article_cards(posts: list[sqlite3.Row]) -> str:
    if not posts:
        return '<p class="empty-state">还没有发布的文章。</p>'
    cards: list[str] = []
    for index, post in enumerate(posts, start=1):
        featured = " article-entry-featured" if index == 1 else ""
        cover = ""
        cover_class = ""
        if post["cover_image"]:
            cover_class = " has-cover"
            cover = f'<a class="article-cover" href="/post/{quote(post["slug"])}" tabindex="-1" aria-hidden="true"><img src="{escape(post["cover_image"])}" alt="" loading="lazy"></a>'
        duration = max(1, round(len(post["content"]) / 500))
        cards.append(
            f"""
          <article class="article-entry{featured}{cover_class}">{cover}
            <div class="article-meta"><span class="article-number">{index:02d}</span><span>{escape(post['category'])}</span><time datetime="{escape(post['published_at'] or post['updated_at'])}">{display_date(post['published_at'] or post['updated_at'])}</time></div>
            <h2><a href="/post/{quote(post['slug'])}">{escape(post['title'])}</a></h2>
            <p>{escape(post['excerpt'])}</p>
            <span class="article-duration">{duration} min read</span>
          </article>"""
        )
    return "".join(cards)


def valid_date(value: str, fallback: date) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def valid_month(value: str, fallback: date) -> date:
    try:
        return date.fromisoformat(f"{value}-01")
    except ValueError:
        return fallback.replace(day=1)


def render_calendar(posts: list[sqlite3.Row], todos: list[sqlite3.Row] | None = None, month: date | None = None, selected_date: date | None = None) -> str:
    today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
    month = (month or today).replace(day=1)
    selected_date = selected_date or today
    prefix = f"{month.year:04d}-{month.month:02d}-"
    post_days = {
        int(value[8:10])
        for post in posts
        if (value := post["published_at"] or "").startswith(prefix)
    }
    todo_days = {
        int(value[8:10])
        for todo in todos or []
        if (value := todo["due_date"] or "").startswith(prefix)
    }
    weekdays = "一二三四五六日"
    cells = [f'<span class="calendar-weekday">{day}</span>' for day in weekdays]
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(month.year, month.month):
        for day in week:
            if day == 0:
                cells.append('<span class="calendar-day is-empty">0</span>')
                continue
            classes = ["calendar-day"]
            cell_date = date(month.year, month.month, day)
            if cell_date == today:
                classes.append("is-today")
            if cell_date == selected_date:
                classes.append("is-selected")
            if day in post_days:
                classes.append("has-post")
            if day in todo_days:
                classes.append("has-todo")
            target = cell_date.isoformat()
            cells.append(f'<a class="{" ".join(classes)}" href="/?month={month:%Y-%m}&amp;todo_date={target}#todo" aria-label="查看 {target} 的待办">{day}</a>')
    previous_month = (month - timedelta(days=1)).replace(day=1)
    next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    return f"""<section id="calendar"><div class="calendar-head"><a class="calendar-nav" href="/?month={previous_month:%Y-%m}&amp;todo_date={previous_month:%Y-%m}-01#calendar" aria-label="上个月">←</a><strong>{month.year} / {month.month:02d}</strong><a class="calendar-nav" href="/?month={next_month:%Y-%m}&amp;todo_date={next_month:%Y-%m}-01#calendar" aria-label="下个月">→</a></div><div class="calendar-grid">{''.join(cells)}</div><p class="calendar-note">点击日期查看当天 Todo</p></section>"""


def user_by_id(user_id: int) -> sqlite3.Row | None:
    with db_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def user_by_username(username: str) -> sqlite3.Row | None:
    with db_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def todos_for_user(user_id: int) -> list[sqlite3.Row]:
    with db_connection() as connection:
        return connection.execute(
            "SELECT * FROM todos WHERE user_id = ? ORDER BY due_date ASC, is_done ASC, updated_at DESC, id DESC",
            (user_id,),
        ).fetchall()


def auth_nav(user: sqlite3.Row | None, token: str | None) -> str:
    if user is None or not token:
        return '<span class="auth-nav"><a href="/login">登录</a><a href="/register">注册</a></span>'
    admin_link = '<a href="/admin">后台</a>' if user["role"] == "admin" else ""
    return f'<span class="auth-nav"><span class="user-greeting">{escape(user["username"])}</span>{admin_link}<form class="inline-form" method="post" action="/logout"><input type="hidden" name="csrf" value="{escape(csrf_for(token))}"><button type="submit">退出</button></form></span>'


def todo_list_items(items: list[sqlite3.Row], csrf: str, empty_text: str, selected_date: date) -> str:
    if not items:
        return f'<p class="todo-empty">{escape(empty_text)}</p>'
    rows: list[str] = []
    for todo in items:
        done_class = " is-done" if todo["is_done"] else ""
        checked = "✓" if todo["is_done"] else ""
        rows.append(
            f'''<li class="todo-item{done_class}">
              <form class="inline-form" method="post" action="/todo/toggle"><input type="hidden" name="csrf" value="{escape(csrf)}"><input type="hidden" name="id" value="{todo['id']}"><input type="hidden" name="view_date" value="{selected_date.isoformat()}"><button class="todo-check" type="submit" aria-label="{'取消完成' if todo['is_done'] else '标记完成'}">{checked}</button></form>
              <span class="todo-title">{escape(todo['title'])}</span><time>{display_date(todo['due_date'])}</time>
              <span class="todo-actions"><a href="/todo/edit?id={todo['id']}#todo">编辑</a><form class="inline-form" method="post" action="/todo/delete"><input type="hidden" name="csrf" value="{escape(csrf)}"><input type="hidden" name="id" value="{todo['id']}"><input type="hidden" name="view_date" value="{selected_date.isoformat()}"><button type="submit" aria-label="删除待办">删除</button></form></span>
            </li>'''
        )
    return "".join(rows)


def render_todo_panel(user: sqlite3.Row | None, token: str | None, selected_date: date, edit_todo: sqlite3.Row | None = None, message: str = "") -> str:
    if user is None or not token:
        return f'<section class="todo-panel" id="todo"><div class="todo-heading"><span>TODO</span><small>{selected_date:%Y.%m.%d}</small></div><p class="todo-login">登录后管理你的待办，并在日历中留下当天的标记。</p><a class="todo-login-link" href="/login">登录以继续 →</a></section>'
    items = todos_for_user(user["id"])
    today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
    selected_value = selected_date.isoformat()
    selected_items = [todo for todo in items if todo["due_date"] == selected_value]
    past_start = (today - timedelta(days=3)).isoformat()
    past = [todo for todo in items if past_start <= todo["due_date"] < today.isoformat() and todo["due_date"] != selected_value]
    editing = edit_todo is not None
    title_value = escape(edit_todo["title"] if editing else "")
    date_value = escape(edit_todo["due_date"] if editing else selected_value)
    todo_id = escape(edit_todo["id"] if editing else "")
    notice = f'<p class="todo-notice todo-flash" data-auto-hide="true">{escape(message)}</p>' if message else ""
    history = ""
    if past:
        history = f'<details class="todo-history"><summary>过去 3 天的 Todo <span>{len(past):02d}</span></summary><ul class="todo-list">{todo_list_items(past, csrf_for(token), "", selected_date)}</ul></details>'
    return f'''<section class="todo-panel" id="todo">
      <div class="todo-heading"><span>TODO</span><small>{selected_date:%Y.%m.%d}</small></div>{notice}
      <form class="todo-form" method="post" action="/todo/save">
        <input type="hidden" name="csrf" value="{escape(csrf_for(token))}"><input type="hidden" name="id" value="{todo_id}">
        <label class="sr-only" for="todo-title">待办内容</label><input id="todo-title" name="title" value="{title_value}" maxlength="200" placeholder="写下一个待办..." required>
        <label class="sr-only" for="todo-date">日期</label><input id="todo-date" name="due_date" type="date" value="{date_value}" required>
        <button type="submit">{'保存' if editing else '添加'} <span aria-hidden="true">↗</span></button>
      </form>
      <div class="todo-section"><div class="todo-section-label">当天的 Todo <span>{len(selected_items):02d}</span></div><ul class="todo-list">{todo_list_items(selected_items, csrf_for(token), '这一天还没有待办。', selected_date)}</ul></div>
      {history}
      <p class="todo-hint"><a class="todo-date-link" href="/?month={today:%Y-%m}&amp;todo_date={today.isoformat()}#todo">返回今天</a></p>
    </section>'''


def render_todo_update(user: sqlite3.Row, token: str, selected_date: date, message: str = "") -> str:
    posts = published_articles()
    todos = todos_for_user(user["id"])
    return render_calendar(posts, todos, selected_date, selected_date) + render_todo_panel(user, token, selected_date, message=message)


def homepage(user: sqlite3.Row | None = None, token: str | None = None, message: str = "", edit_todo: sqlite3.Row | None = None, selected_date: date | None = None, calendar_month: date | None = None) -> str:
    template = INDEX_PATH.read_text(encoding="utf-8")
    posts = published_articles()
    todos = todos_for_user(user["id"]) if user is not None else []
    today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
    selected_date = selected_date or today
    calendar_month = (calendar_month or selected_date).replace(day=1)
    count_label = f"01 — {len(posts):02d}" if posts else "暂无文章"
    template = template.replace("<!-- ARTICLE_COUNT -->", count_label)
    template = template.replace("<!-- AUTH_NAV -->", auth_nav(user, token))
    template = template.replace("<!-- CALENDAR -->", render_calendar(posts, todos, calendar_month, selected_date))
    template = template.replace("<!-- TODO_PANEL -->", render_todo_panel(user, token, selected_date, edit_todo, message))
    template = re.sub(
        r"<!-- ARTICLES_START -->.*?<!-- ARTICLES_END -->",
        f"<!-- ARTICLES_START -->{article_cards(posts)}<!-- ARTICLES_END -->",
        template,
        flags=re.DOTALL,
    )
    return template


def public_article(post: sqlite3.Row) -> str:
    title = escape(post["title"])
    date = display_date(post["published_at"] or post["updated_at"])
    cover = f'<img class="article-detail-cover" src="{escape(post["cover_image"])}" alt="{title}" fetchpriority="high">' if post["cover_image"] else ""
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="{escape(post['excerpt'])}"><title>{title} / Timeless日常存档</title>{FAVICON_LINK}<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="/styles.css?v=17"></head>
<body><div class="reading-progress" aria-hidden="true"><span></span></div><main class="page-shell article-page"><header class="site-header"><a class="brand" href="/">{BRAND_MARK}<span>Timeless日常存档</span></a><a class="article-back" href="/">← 返回首页</a></header><article class="article-detail"><div class="article-detail-meta"><span>{escape(post['category'])}</span><time datetime="{escape(post['published_at'] or post['updated_at'])}">{date}</time></div><h1>{title}</h1><p class="article-lead">{escape(post['excerpt'])}</p>{cover}<div class="article-content">{markdown_to_html(post['content'])}</div></article><footer class="site-footer"><span>© 2026 TIMELESS日常存档</span><span>鲁ICP备2026053385号</span><span>BUILT WITH CARE &amp; TOO MUCH TOKEN</span></footer></main><script>(()=>{{const bar=document.querySelector('.reading-progress span');let scheduled=false;const update=()=>{{const root=document.documentElement;const distance=root.scrollHeight-window.innerHeight;const progress=distance>0?Math.min(window.scrollY/distance,1):1;bar.style.transform=`scaleX(${{progress}})`;scheduled=false;}};const schedule=()=>{{if(!scheduled){{scheduled=true;requestAnimationFrame(update);}}}};update();addEventListener('scroll',schedule,{{passive:true}});addEventListener('resize',schedule);}})();</script></body></html>"""


def admin_css() -> str:
    return """<style>
      .admin-shell{width:min(1100px,calc(100% - 48px));margin:0 auto;padding:36px 0 70px}.admin-header{display:flex;align-items:center;justify-content:space-between;padding-bottom:28px;border-bottom:1px solid var(--line)}.admin-header h1{font:600 26px var(--display);letter-spacing:-.06em;margin:0}.admin-header p{color:var(--muted);font:10px var(--mono);margin:6px 0 0}.admin-actions{display:flex;gap:10px;align-items:center}.admin-button{display:inline-block;padding:11px 15px;border:1px solid var(--faint);color:var(--text);font:500 10px var(--mono);background:transparent;cursor:pointer}.admin-button.primary{background:var(--accent);color:#20331d;border-color:var(--accent)}.admin-button.danger{color:#efaa9b}.admin-list{margin-top:30px;border-top:1px solid var(--line)}.admin-row{display:grid;grid-template-columns:45px 1fr 100px 110px 75px;gap:18px;align-items:center;padding:19px 0;border-bottom:1px solid var(--line)}.admin-row .index{color:var(--accent);font:10px var(--mono)}.admin-row h2{margin:0 0 7px;font-size:16px;letter-spacing:-.04em}.admin-row p{margin:0;color:var(--muted);font:10px var(--mono)}.admin-status{font:9px var(--mono);color:var(--muted)}.admin-status.published{color:var(--accent)}.admin-row time{color:var(--muted);font:10px var(--mono)}.admin-row .edit-link{color:var(--accent);font:10px var(--mono);text-align:right}.admin-form{max-width:780px;margin:45px auto 0}.admin-form label{display:block;color:var(--muted);font:10px var(--mono);margin:0 0 23px}.admin-form input,.admin-form textarea,.admin-form select{display:block;width:100%;margin-top:9px;border:1px solid var(--line);background:var(--surface);color:var(--text);padding:13px 14px;outline:0;font:14px var(--sans)}.admin-form textarea{line-height:1.7;resize:vertical}.admin-form input:focus,.admin-form textarea:focus,.admin-form select:focus{border-color:var(--accent)}.admin-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.admin-form-actions{display:flex;align-items:center;gap:15px;margin-top:7px}.admin-note{color:var(--muted);font:10px var(--mono);line-height:1.7}.admin-error{color:#efaa9b;font:13px var(--mono);margin:18px 0}.admin-success{color:var(--accent);font:12px var(--mono);margin:16px 0}.login-shell{width:min(500px,calc(100% - 48px));max-width:calc(100vw - 24px);margin:10vh auto;padding:48px;overflow:hidden;background:rgba(9,11,10,.88);border:1px solid rgba(215,223,217,.12)}.login-shell .brand{margin-bottom:50px}.login-shell h1{font:600 38px var(--display);letter-spacing:-.05em;margin:0 0 14px}.login-shell>p{color:var(--muted);font-size:16px;line-height:1.7;margin:0 0 34px}.login-form{min-width:0}.login-form label{display:block;min-width:0;color:var(--muted);font:13px var(--mono)}.login-form input{display:block;width:100%;max-width:100%;min-width:0;margin:11px 0 23px;border:1px solid var(--line);background:rgba(17,21,18,.92);color:var(--text);padding:15px 16px;font:16px var(--sans);outline:0}.login-form input:focus{border-color:var(--accent)}.login-shell .admin-button{padding:13px 18px;font-size:14px}.login-shell .auth-switch{font-size:13px!important;margin-top:28px!important;margin-bottom:0!important}.empty-state{padding:35px 0;color:var(--muted);font:11px var(--mono)}
      .admin-header h1,.admin-row h2,.login-shell h1{letter-spacing:0}.image-upload{display:flex;align-items:center;gap:12px;margin:-8px 0 24px}.image-upload input,.cover-editor>input[type=file]{display:none}.image-upload-status{color:var(--muted);font:11px var(--mono)}.image-upload-status.is-error{color:#efaa9b}.image-upload-status.is-success{color:var(--accent)}.cover-editor{margin:0 0 24px;color:var(--muted);font:10px var(--mono)}.cover-preview{width:100%;aspect-ratio:16/7;margin:10px 0 12px;overflow:hidden;border:1px solid var(--line);background:var(--surface)}.cover-preview[hidden]{display:none}.cover-preview img{width:100%;height:100%;object-fit:cover}.cover-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
      @media(max-width:700px){.admin-shell{width:min(calc(100% - 38px),540px)}.admin-header{align-items:flex-start;gap:20px}.admin-actions{flex-direction:column;align-items:stretch}.admin-row{grid-template-columns:32px 1fr 65px;gap:10px}.admin-row time{display:none}.admin-row .edit-link{text-align:right}.admin-form-grid{grid-template-columns:1fr}.login-shell{width:calc(100% - 24px);margin:7vh auto;padding:34px 22px}.login-shell .brand{margin-bottom:42px}.login-shell h1{font-size:34px}.login-shell>p{font-size:15px}}
    </style>"""


def admin_layout(content: str, title: str = "后台") -> str:
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{escape(title)} / Timeless日常存档</title>{FAVICON_LINK}<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="/styles.css?v=17">{admin_css()}</head><body>{content}</body></html>"""


def login_page(error: str = "") -> str:
    message = f'<p class="admin-error">{escape(error)}</p>' if error else ""
    return admin_layout(
        f"""<main class="login-shell"><a class="brand" href="/">{BRAND_MARK}<span>Timeless日常存档</span></a><h1>进入写作后台</h1><p>登录后可以保存草稿并发布文章。</p>{message}<form class="login-form" method="post" action="/admin/login"><label>管理员密码<input type="password" name="password" autocomplete="current-password" required></label><button class="admin-button primary" type="submit">登录后台 →</button></form></main>""",
        "登录后台",
    )


def user_login_page(error: str = "") -> str:
    message = f'<p class="admin-error">{escape(error)}</p>' if error else ""
    return admin_layout(
        f'''<main class="login-shell"><a class="brand" href="/">{BRAND_MARK}<span>Timeless日常存档</span></a><h1>登录</h1><p>登录后管理你的日常待办。</p>{message}<form class="login-form" method="post" action="/login"><label>用户名<input name="username" autocomplete="username" required maxlength="30"></label><label>密码<input type="password" name="password" autocomplete="current-password" required></label><button class="admin-button primary" type="submit">登录 →</button></form><p class="auth-switch">还没有账号？<a href="/register">注册一个</a></p></main>''',
        "登录",
    )


def register_page(error: str = "") -> str:
    message = f'<p class="admin-error">{escape(error)}</p>' if error else ""
    return admin_layout(
        f'''<main class="login-shell"><a class="brand" href="/">{BRAND_MARK}<span>Timeless日常存档</span></a><h1>注册</h1><p>创建一个账号，开始记录自己的 Todo。</p>{message}<form class="login-form" method="post" action="/register"><label>用户名<input name="username" autocomplete="username" required maxlength="30"></label><label>密码<input type="password" name="password" autocomplete="new-password" minlength="8" required></label><label>确认密码<input type="password" name="password_confirm" autocomplete="new-password" minlength="8" required></label><button class="admin-button primary" type="submit">创建账号 →</button></form><p class="auth-switch">已经有账号？<a href="/login">返回登录</a></p></main>''',
        "注册",
    )


def csrf_for(token: str) -> str:
    return SESSIONS[token]["csrf"]


def dashboard_page(message: str = "", token: str = "") -> str:
    csrf = csrf_for(token) if token else ""
    rows: list[str] = []
    for index, post in enumerate(all_articles(), start=1):
        status_class = "published" if post["status"] == "published" else ""
        status_text = "已发布" if post["status"] == "published" else "草稿"
        rows.append(
            f"""<div class="admin-row"><span class="index">{index:02d}</span><div><h2>{escape(post['title'])}</h2><p>{escape(post['category'])} · /post/{escape(post['slug'])}</p></div><span class="admin-status {status_class}">{status_text}</span><time>{display_date(post['updated_at'])}</time><a class="edit-link" href="/admin/edit?id={post['id']}">编辑 ↗</a></div>"""
        )
    notice = f'<p class="admin-success">{escape(message)}</p>' if message else ""
    return admin_layout(
        f"""<main class="admin-shell"><header class="admin-header"><div><h1>Timeless日常存档</h1><p>写作后台 / {len(rows)} 篇文章</p></div><div class="admin-actions"><a class="admin-button primary" href="/admin/new">新建文章 +</a><a class="admin-button" href="/">查看网站 ↗</a><form method="post" action="/admin/logout"><input type="hidden" name="csrf" value="{escape(csrf)}"><button class="admin-button" type="submit">退出</button></form></div></header>{notice}<section class="admin-list">{''.join(rows) or '<p class="empty-state">还没有文章，点击右上角开始写第一篇。</p>'}</section></main>""",
        "文章管理",
    )


def editor_page(post: sqlite3.Row | None = None, error: str = "", token: str = "") -> str:
    csrf = csrf_for(token) if token else ""
    is_editing = post is not None
    value = lambda key, default="": escape(post[key] if post else default)
    message = f'<p class="admin-error">{escape(error)}</p>' if error else ""
    selected_published = " selected" if post and post["status"] == "published" else ""
    selected_draft = " selected" if not post or post["status"] != "published" else ""
    delete_form = (
        f'<form method="post" action="/admin/delete" onsubmit="return confirm(\'确定删除这篇文章吗？\')"><input type="hidden" name="csrf" value="{escape(csrf)}"><input type="hidden" name="id" value="{post["id"]}"><button class="admin-button danger" type="submit">删除文章</button></form>'
        if is_editing
        else ""
    )
    cover_url = value("cover_image")
    cover_hidden = "" if cover_url else " hidden"
    content = f"""<main class="admin-shell">
      <header class="admin-header"><div><h1>{'编辑文章' if is_editing else '写一篇新文章'}</h1><p>Markdown 内容会直接生成文章页面。</p></div><div class="admin-actions"><a class="admin-button" href="/admin">返回列表</a>{delete_form}</div></header>
      {message}
      <form class="admin-form" method="post" action="/admin/save">
        <input type="hidden" name="csrf" value="{escape(csrf)}"><input type="hidden" name="id" value="{value('id')}">
        <label>文章标题<input name="title" value="{value('title')}" placeholder="输入一个清楚的标题" required></label>
        <div class="admin-form-grid"><label>分类<input name="category" value="{value('category', '随笔')}" placeholder="例如：工程实践"></label><label>URL 标识<input name="slug" value="{value('slug')}" placeholder="例如：my-first-post"></label></div>
        <label>文章摘要<input name="excerpt" value="{value('excerpt')}" placeholder="显示在首页的一句话摘要"></label>
        <section class="cover-editor" aria-labelledby="cover-label">
          <span id="cover-label">文章封面</span><input id="cover-image-url" type="hidden" name="cover_image" value="{cover_url}"><input id="cover-image-input" type="file" accept="image/jpeg,image/png,image/gif,image/webp">
          <div class="cover-preview" id="cover-preview"{cover_hidden}><img src="{cover_url}" alt="封面预览"></div>
          <div class="cover-actions"><button class="admin-button" id="cover-upload-button" type="button">上传封面</button><button class="admin-button" id="cover-remove-button" type="button"{cover_hidden}>移除封面</button><span class="image-upload-status" id="cover-upload-status">建议使用横向图片</span></div>
        </section>
        <label>正文（Markdown）<textarea id="article-content" name="content" rows="23" placeholder="# 文章标题\n\n从这里开始写..." required>{value('content')}</textarea></label>
        <div class="image-upload"><input id="article-image" type="file" accept="image/jpeg,image/png,image/gif,image/webp"><button class="admin-button" id="image-upload-button" type="button">上传正文图片</button><span class="image-upload-status" id="image-upload-status">JPEG / PNG / GIF / WebP，最大 8 MB</span></div>
        <div class="admin-form-grid"><label>发布状态<select name="status"><option value="draft"{selected_draft}>保存为草稿</option><option value="published"{selected_published}>立即发布</option></select></label><div class="admin-note">支持标题、列表、引用、粗体、图片、行内代码和代码块。<br>保存后可从文章列表打开公开页面。</div></div>
        <div class="admin-form-actions"><button class="admin-button primary" type="submit">{'保存修改' if is_editing else '保存文章'} →</button><a class="admin-button" href="/admin">取消</a></div>
      </form>
    </main><script src="/admin.js?v=1"></script>"""
    return admin_layout(content, "编辑文章" if is_editing else "写文章")
class BlogHandler(BaseHTTPRequestHandler):
    server_version = "TimelessBlog/1.0"

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_html(self, body: str, status: int = 200) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, payload: dict[str, str], status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def redirect(self, location: str, cookie: str | None = None) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def session_token(self) -> str | None:
        raw = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie()
        jar.load(raw)
        token = jar.get("timeless_session")
        if token and token.value in SESSIONS:
            SESSIONS[token.value]["active"] = "1"
            return token.value
        return None

    def require_auth(self) -> str | None:
        token = self.session_token()
        if token and SESSIONS.get(token, {}).get("role") == "admin":
            return token
        return None

    def require_user(self) -> str | None:
        token = self.session_token()
        if token and SESSIONS.get(token, {}).get("role") in {"user", "admin"}:
            try:
                user_id = int(SESSIONS[token]["user_id"])
            except (KeyError, ValueError):
                return None
            if user_by_id(user_id) is not None:
                return token
        return None

    def read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY_SIZE:
            raise ValueError("提交内容过大")
        data = self.rfile.read(length).decode("utf-8", errors="replace")
        parsed = parse_qs(data, keep_blank_values=True)
        return {key: values[-1] for key, values in parsed.items()}

    def valid_csrf(self, form: dict[str, str], token: str) -> bool:
        return secrets.compare_digest(form.get("csrf", ""), csrf_for(token))

    def wants_partial(self) -> bool:
        return self.headers.get("X-Requested-With", "").lower() == "fetch"

    def handle_image_upload(self) -> None:
        token = self.require_auth()
        if token is None:
            self.send_json({"error": "请先登录后台。"}, 401)
            return
        supplied_csrf = self.headers.get("X-CSRF-Token", "")
        if not secrets.compare_digest(supplied_csrf, csrf_for(token)):
            self.send_json({"error": "请求已过期，请刷新页面后重试。"}, 403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            self.send_json({"error": "请选择图片。"}, 400)
            return
        if length > MAX_IMAGE_SIZE:
            self.send_json({"error": "图片不能超过 8 MB。"}, 413)
            return
        content = self.rfile.read(length)
        extension = ""
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            extension = ".png"
        elif content.startswith(b"\xff\xd8\xff"):
            extension = ".jpg"
        elif content.startswith((b"GIF87a", b"GIF89a")):
            extension = ".gif"
        elif len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            extension = ".webp"
        if not extension:
            self.send_json({"error": "仅支持 JPEG、PNG、GIF 和 WebP 图片。"}, 415)
            return
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{secrets.token_hex(5)}{extension}"
        (UPLOADS_DIR / filename).write_bytes(content)
        self.send_json({"url": f"/uploads/{filename}"}, 201)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            token = self.session_token()
            user = None
            if token and "user_id" in SESSIONS.get(token, {}):
                try:
                    user = user_by_id(int(SESSIONS[token]["user_id"]))
                except (KeyError, ValueError):
                    user = None
            query = parse_qs(urlsplit(self.path).query)
            today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
            selected_date = valid_date(query.get("todo_date", [""])[0], today)
            calendar_month = valid_month(query.get("month", [""])[0], selected_date)
            self.send_html(homepage(user, token, query.get("message", [""])[0], selected_date=selected_date, calendar_month=calendar_month))
            return
        if path == "/login":
            token = self.session_token()
            if token and SESSIONS.get(token, {}).get("role") in {"user", "admin"}:
                self.redirect("/")
            else:
                self.send_html(user_login_page())
            return
        if path == "/register":
            token = self.session_token()
            if token and SESSIONS.get(token, {}).get("role") in {"user", "admin"}:
                self.redirect("/")
            else:
                self.send_html(register_page())
            return
        if path == "/todo/edit":
            token = self.require_user()
            if not token:
                self.redirect("/login")
                return
            query = parse_qs(urlsplit(self.path).query)
            try:
                todo_id = int(query.get("id", [""])[0])
                user_id = int(SESSIONS[token]["user_id"])
            except (KeyError, ValueError):
                self.redirect("/?message=" + quote("找不到这条待办") + "#todo")
                return
            with db_connection() as connection:
                todo = connection.execute("SELECT * FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id)).fetchone()
            if todo is None:
                self.redirect("/?message=" + quote("找不到这条待办") + "#todo")
                return
            todo_date = date.fromisoformat(todo["due_date"])
            if self.wants_partial():
                self.send_html(render_todo_panel(user_by_id(user_id), token, todo_date, edit_todo=todo))
            else:
                self.send_html(homepage(user_by_id(user_id), token, edit_todo=todo, selected_date=todo_date, calendar_month=todo_date))
            return
        if path == "/todo/view":
            token = self.session_token()
            user = None
            if token and "user_id" in SESSIONS.get(token, {}):
                try:
                    user = user_by_id(int(SESSIONS[token]["user_id"]))
                except (KeyError, ValueError):
                    user = None
            query = parse_qs(urlsplit(self.path).query)
            today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
            selected_date = valid_date(query.get("date", [""])[0], today)
            self.send_html(render_todo_panel(user, token if user is not None else None, selected_date))
            return
        if path == "/calendar/view":
            token = self.session_token()
            user = None
            if token and "user_id" in SESSIONS.get(token, {}):
                try:
                    user = user_by_id(int(SESSIONS[token]["user_id"]))
                except (KeyError, ValueError):
                    user = None
            query = parse_qs(urlsplit(self.path).query)
            today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
            selected_date = valid_date(query.get("todo_date", [""])[0], today)
            month = valid_month(query.get("month", [""])[0], selected_date)
            posts = published_articles()
            todos = todos_for_user(user["id"]) if user is not None else []
            self.send_html(render_calendar(posts, todos, month, selected_date) + render_todo_panel(user, token if user is not None else None, selected_date))
            return
        if path == "/styles.css":
            self.send_file(STYLES_PATH, "text/css; charset=utf-8")
            return
        if path == "/admin.js":
            self.send_file(ADMIN_JS_PATH, "text/javascript; charset=utf-8")
            return
        if path == "/assets/background.jpg":
            self.send_file(ASSETS_DIR / "background.jpg", "image/jpeg")
            return
        if path == "/assets/favicon.svg":
            self.send_file(FAVICON_PATH, "image/svg+xml; charset=utf-8")
            return
        if path.startswith("/uploads/"):
            filename = path.removeprefix("/uploads/")
            match = re.fullmatch(r"[0-9]{8}-[0-9]{6}-[a-f0-9]{10}\.(jpg|png|gif|webp)", filename)
            if match is None:
                self.send_error(404)
                return
            content_types = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
            self.send_file(UPLOADS_DIR / filename, content_types[match.group(1)])
            return
        if path == "/admin":
            token = self.require_auth()
            if not token:
                self.send_html(login_page())
            else:
                query = parse_qs(urlsplit(self.path).query)
                self.send_html(dashboard_page(query.get("message", [""])[0], token))
            return
        if path == "/admin/new":
            token = self.require_auth()
            if not token:
                self.redirect("/admin")
            else:
                self.send_html(editor_page(token=token))
            return
        if path == "/admin/edit":
            token = self.require_auth()
            if not token:
                self.redirect("/admin")
                return
            query = parse_qs(urlsplit(self.path).query)
            try:
                article_id = int(query.get("id", [""])[0])
            except ValueError:
                self.send_error(400)
                return
            with db_connection() as connection:
                post = connection.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            self.send_html(editor_page(post, "找不到这篇文章。" if post is None else "", token), 404 if post is None else 200)
            return
        if path.startswith("/post/"):
            slug = path.removeprefix("/post/")
            with db_connection() as connection:
                post = connection.execute("SELECT * FROM articles WHERE slug = ? AND status = 'published'", (slug,)).fetchone()
            if post is None:
                self.send_error(404)
            else:
                self.send_html(public_article(post))
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/admin/upload-image":
            self.handle_image_upload()
            return
        try:
            form = self.read_form()
        except ValueError as error:
            self.send_html(login_page(str(error)), 413)
            return
        if path == "/admin/login":
            if secrets.compare_digest(form.get("password", ""), ADMIN_PASSWORD):
                token = secrets.token_urlsafe(32)
                admin_user = user_by_username("admin")
                session = {"csrf": secrets.token_urlsafe(24), "active": "1", "role": "admin"}
                if admin_user is not None:
                    session["user_id"] = str(admin_user["id"])
                SESSIONS[token] = session
                secure_suffix = "; Secure" if COOKIE_SECURE else ""
                cookie = f"timeless_session={token}; Path=/; HttpOnly; SameSite=Lax{secure_suffix}"
                self.redirect("/admin", cookie)
            else:
                self.send_html(login_page("密码不正确。"), 401)
            return
        if path == "/login":
            username = form.get("username", "").strip()
            password = form.get("password", "")
            user = user_by_username(username)
            if user is None or not verify_password(password, user["password_hash"]):
                self.send_html(user_login_page("用户名或密码不正确。"), 401)
                return
            token = secrets.token_urlsafe(32)
            SESSIONS[token] = {"csrf": secrets.token_urlsafe(24), "active": "1", "role": user["role"], "user_id": str(user["id"])}
            secure_suffix = "; Secure" if COOKIE_SECURE else ""
            cookie = f"timeless_session={token}; Path=/; HttpOnly; SameSite=Lax{secure_suffix}"
            self.redirect("/", cookie)
            return
        if path == "/register":
            username = form.get("username", "").strip()
            password = form.get("password", "")
            password_confirm = form.get("password_confirm", "")
            if not re.fullmatch(r"[\w\u4e00-\u9fff-]{2,30}", username):
                self.send_html(register_page("用户名需为 2-30 个字母、数字、汉字或短横线。"), 400)
                return
            if len(password) < 8:
                self.send_html(register_page("密码至少需要 8 位。"), 400)
                return
            if password != password_confirm:
                self.send_html(register_page("两次输入的密码不一致。"), 400)
                return
            if user_by_username(username) is not None:
                self.send_html(register_page("这个用户名已经被使用。"), 409)
                return
            now = utc_now()
            try:
                with db_connection() as connection:
                    cursor = connection.execute(
                        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                        (username, hash_password(password), now),
                    )
                    user_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                self.send_html(register_page("这个用户名已经被使用。"), 409)
                return
            token = secrets.token_urlsafe(32)
            SESSIONS[token] = {"csrf": secrets.token_urlsafe(24), "active": "1", "role": "user", "user_id": str(user_id)}
            secure_suffix = "; Secure" if COOKIE_SECURE else ""
            cookie = f"timeless_session={token}; Path=/; HttpOnly; SameSite=Lax{secure_suffix}"
            self.redirect("/", cookie)
            return
        if path == "/logout":
            token = self.require_user()
            if not token:
                self.redirect("/")
                return
            if not self.valid_csrf(form, token):
                self.send_html(user_login_page("请求已过期，请重新登录。"), 403)
                return
            SESSIONS.pop(token, None)
            self.redirect("/")
            return
        if path.startswith("/todo/"):
            token = self.require_user()
            if not token:
                self.redirect("/login")
                return
            if not self.valid_csrf(form, token):
                self.send_html(user_login_page("请求已过期，请重新登录。"), 403)
                return
            user_id = int(SESSIONS[token]["user_id"])
            if path == "/todo/save":
                title = form.get("title", "").strip()
                due_date = form.get("due_date", "").strip()
                today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
                selected_date = valid_date(due_date, today)
                if not title:
                    user = user_by_id(user_id)
                    if self.wants_partial():
                        self.send_html(render_todo_panel(user, token, selected_date, message="待办内容不能为空。"), 400)
                    else:
                        self.send_html(homepage(user, token, "待办内容不能为空。", selected_date=selected_date, calendar_month=selected_date), 400)
                    return
                if len(title) > 200:
                    user = user_by_id(user_id)
                    if self.wants_partial():
                        self.send_html(render_todo_panel(user, token, selected_date, message="待办内容不能超过 200 个字符。"), 400)
                    else:
                        self.send_html(homepage(user, token, "待办内容不能超过 200 个字符。", selected_date=selected_date, calendar_month=selected_date), 400)
                    return
                try:
                    date.fromisoformat(due_date)
                except ValueError:
                    user = user_by_id(user_id)
                    if self.wants_partial():
                        self.send_html(render_todo_panel(user, token, today, message="请选择有效日期。"), 400)
                    else:
                        self.send_html(homepage(user, token, "请选择有效日期。", selected_date=today, calendar_month=today), 400)
                    return
                now = utc_now()
                raw_id = form.get("id", "").strip()
                with db_connection() as connection:
                    if raw_id.isdigit():
                        todo_id = int(raw_id)
                        existing = connection.execute("SELECT id FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id)).fetchone()
                        if existing is None:
                            if self.wants_partial():
                                self.send_html(render_todo_update(user_by_id(user_id), token, selected_date, "找不到这条待办"), 404)
                                return
                            self.redirect(f"/?month={selected_date:%Y-%m}&todo_date={selected_date.isoformat()}&message=" + quote("找不到这条待办") + "#todo")
                            return
                        connection.execute("UPDATE todos SET title = ?, due_date = ?, updated_at = ? WHERE id = ? AND user_id = ?", (title, due_date, now, todo_id, user_id))
                        message = "待办已更新"
                    else:
                        connection.execute("INSERT INTO todos (user_id, title, due_date, is_done, created_at, updated_at) VALUES (?, ?, ?, 0, ?, ?)", (user_id, title, due_date, now, now))
                        message = "待办已添加"
                if self.wants_partial():
                    self.send_html(render_todo_update(user_by_id(user_id), token, selected_date, message))
                else:
                    self.redirect(f"/?month={selected_date:%Y-%m}&todo_date={selected_date.isoformat()}&message=" + quote(message) + "#todo")
                return
            try:
                todo_id = int(form.get("id", ""))
            except ValueError:
                self.redirect("/?message=" + quote("操作失败") + "#todo")
                return
            today = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
            selected_date = valid_date(form.get("view_date", ""), today)
            with db_connection() as connection:
                existing = connection.execute("SELECT id, is_done FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id)).fetchone()
                if existing is None:
                    if self.wants_partial():
                        self.send_html(render_todo_update(user_by_id(user_id), token, selected_date, "找不到这条待办"), 404)
                        return
                    self.redirect(f"/?month={selected_date:%Y-%m}&todo_date={selected_date.isoformat()}&message=" + quote("找不到这条待办") + "#todo")
                    return
                if path == "/todo/toggle":
                    connection.execute("UPDATE todos SET is_done = ?, updated_at = ? WHERE id = ? AND user_id = ?", (0 if existing["is_done"] else 1, utc_now(), todo_id, user_id))
                    message = "待办状态已更新"
                elif path == "/todo/delete":
                    connection.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
                    message = "待办已删除"
                else:
                    self.send_error(404)
                    return
            if self.wants_partial():
                self.send_html(render_todo_update(user_by_id(user_id), token, selected_date, message))
            else:
                self.redirect(f"/?month={selected_date:%Y-%m}&todo_date={selected_date.isoformat()}&message=" + quote(message) + "#todo")
            return
        token = self.require_auth()
        if token is None:
            self.redirect("/admin")
            return
        if not self.valid_csrf(form, token):
            self.send_html(admin_layout('<main class="login-shell"><h1>请求已过期</h1><p>请返回后台重新提交。</p><a class="admin-button" href="/admin">返回后台</a></main>', "请求已过期"), 403)
            return
        if path == "/admin/logout":
            SESSIONS.pop(token, None)
            self.redirect("/admin")
            return
        if path == "/admin/delete":
            try:
                article_id = int(form.get("id", ""))
            except ValueError:
                self.redirect("/admin?message=" + quote("删除失败"))
                return
            with db_connection() as connection:
                connection.execute("DELETE FROM articles WHERE id = ?", (article_id,))
            self.redirect("/admin?message=" + quote("文章已删除"))
            return
        if path == "/admin/save":
            title = form.get("title", "").strip()
            content = form.get("content", "").strip()
            if not title or not content:
                self.send_html(editor_page(None, "标题和正文不能为空。", token), 400)
                return
            category = form.get("category", "随笔").strip() or "随笔"
            excerpt = form.get("excerpt", "").strip() or content.replace("\n", " ")[:120]
            cover_image = form.get("cover_image", "").strip()
            if cover_image and not valid_uploaded_image_url(cover_image):
                cover_image = ""
            status = "published" if form.get("status") == "published" else "draft"
            now = utc_now()
            raw_id = form.get("id", "").strip()
            with db_connection() as connection:
                article_id = int(raw_id) if raw_id.isdigit() else None
                slug = unique_slug(connection, form.get("slug", "").strip() or title, article_id)
                if article_id is None:
                    connection.execute(
                        "INSERT INTO articles (title, slug, category, excerpt, cover_image, content, status, created_at, updated_at, published_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (title, slug, category, excerpt, cover_image, content, status, now, now, now if status == "published" else None),
                    )
                else:
                    existing = connection.execute("SELECT created_at, published_at FROM articles WHERE id = ?", (article_id,)).fetchone()
                    if existing is None:
                        self.send_html(editor_page(None, "找不到这篇文章。", token), 404)
                        return
                    published_at = existing["published_at"] or now if status == "published" else None
                    connection.execute(
                        "UPDATE articles SET title = ?, slug = ?, category = ?, excerpt = ?, cover_image = ?, content = ?, status = ?, updated_at = ?, published_at = ? WHERE id = ?",
                        (title, slug, category, excerpt, cover_image, content, status, now, published_at, article_id),
                    )
            self.redirect("/admin?message=" + quote("文章已保存"))
            return
        self.send_error(404)


if __name__ == "__main__":
    init_db()
    if ADMIN_PASSWORD == "local-change-this":
        print("WARNING: TIMELESS_ADMIN_PASSWORD is not set; change it before exposing this server.")
    server = ThreadingHTTPServer((HOST, PORT), BlogHandler)
    print(f"Timeless日常存档 running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.server_close()
