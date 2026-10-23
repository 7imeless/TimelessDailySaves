"""Server-rendered production templates adapted from the standalone demo."""
import json
import re
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
VERSION = '20261023'


def template(name):
    return (ROOT / 'templates' / f'{name}.html').read_text(encoding='utf-8')


def json_script(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def data_posts(site, posts):
    return [dict(id=str(p['id']), title=p['title'], excerpt=p['excerpt'], category=p['category'],
                 tags=site.article_tags(p), date=(p['published_at'] or p['updated_at'])[:10],
                 minutes=max(1, round(len(p['content']) / 500)), url='/post/' + quote(p['slug'], safe='')) for p in posts]


def head(page):
    styles = ['demo', 'shared']
    if page == 'home':
        styles += ['home-texture', 'home-pc']
    else:
        styles += [{'login': 'auth', 'register': 'auth'}.get(page, page)]
    styles += ['refinements', 'production']
    return '''<script>try { const t=localStorage.getItem('timeless-theme'); if(t==='dark'||t==='light')document.documentElement.dataset.theme=t; }catch(_){}</script>''' + ''.join(
        f'<link rel="stylesheet" href="/assets/ui/{name}.css?v={VERSION}">' for name in styles)


def scripts(page):
    names = ['shared', 'navigation', 'site']
    if page == 'home':
        names += ['todo']
    if page in ('article', 'archive'):
        names += [page]
    return ''.join(f'<script src="/assets/ui/{name}.js?v={VERSION}" defer></script>' for name in names)


def header(site, user=None, token=None):
    markup = template('header').replace('<!-- ACCOUNT -->', site.auth_nav(user, token))
    # Secondary pages use the same real search dialog as the homepage.
    return markup


def search_dialog():
    return '''<dialog class="search-dialog" data-search-dialog aria-labelledby="searchTitle"><div class="search-panel">
      <form action="/" method="get" class="search-field" role="search"><label class="sr-only" id="searchTitle" for="globalSearch">搜索文章</label>
      <input id="globalSearch" type="search" name="q" data-search-input placeholder="搜索文章、标签或正文" autocomplete="off">
      <button type="submit" class="search-esc">搜索</button><button type="button" class="search-esc" data-search-close aria-label="关闭搜索">ESC</button></form>
      <p class="search-hint" data-search-hint aria-live="polite">输入关键词查找文章。</p><div class="search-results" data-search-results></div></div></dialog>'''


def layout(site, content, title, page, user=None, token=None, extra_head='', bare=False):
    chrome = '' if bare else header(site, user, token)
    footer = '' if bare else template('footer')
    return f'''<!doctype html><html lang="zh-CN" data-theme="dark"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
      <meta name="theme-color" content="#080a09"><title>{escape(title)} · Timeless日常存档</title>{site.FAVICON_LINK}{head(page)}{extra_head}</head>
      <body data-page="{page}"><a class="skip-link" href="#main">跳到正文</a>{chrome}{content}{footer}{search_dialog()}
      <div class="toast" data-toast role="status" aria-live="polite"></div><button class="to-top" type="button" data-top aria-label="回到顶部">↑</button>{scripts(page)}</body></html>'''


def hero(title, description, label, page, meta=''):
    return f'''<section class="page-hero page-hero--compact" aria-labelledby="{page}-title"><div class="page-hero-inner">
      <nav class="breadcrumb" aria-label="面包屑"><a href="/">首页</a><span>/</span><span>{escape(title)}</span></nav>
      <p class="eyebrow">{escape(label)}</p><h1 id="{page}-title">{escape(title)}</h1><p class="page-lede">{escape(description)}</p>{meta}</div></section>'''


def cards(site, posts):
    if not posts:
        return '<p class="empty-state">没有符合条件的文章。</p>'
    data = data_posts(site, posts)
    items = []
    for i, (p, row) in enumerate(zip(data, posts), 1):
        title, excerpt, cat, url = (escape(str(p[k]), quote=True) for k in ('title', 'excerpt', 'category', 'url'))
        tags = ' '.join(f'<a href="/?tag={quote(tag)}#latest">#{escape(tag)}</a>' for tag in p['tags'])
        cover = f'<a href="{url}" class="post-cover"><img src="{escape(row["cover_image"])}" alt="" loading="lazy"></a>' if row['cover_image'] else ''
        meta = f'<time datetime="{p["date"]}">{p["date"].replace("-", ".")}</time><span>{p["minutes"]} MIN READ</span><span class="meta-tags">{tags}</span>'
        if i == 1:
            items.append(f'''<article class="feature"><div class="feature-index" aria-hidden="true"><span>01</span><small>FEATURED</small></div><div class="feature-body">
              <p class="post-kicker"><span>精选</span> / {cat}</p>{cover}<h3><a href="{url}">{title}</a></h3><p class="feature-excerpt">{excerpt}</p>
              <div class="post-meta">{meta}</div><a class="read-link" href="{url}">阅读全文 <span class="read-circle" aria-hidden="true">↗</span></a></div></article>
              <div class="list-head"><span class="list-label">更多记录</span><span class="list-count">{max(0,len(data)-1):02d} 篇</span></div>''')
        else:
            items.append(f'''<article class="post-row">{cover}<a class="post-row-link" href="{url}"><span class="post-index">{i:02d}</span><span class="post-body"><span class="post-cat">{cat}</span><span class="post-title">{title}</span><span class="post-excerpt">{excerpt}</span></span><span class="post-aside"><span class="post-date">{p['date'].replace('-', '.')}</span><span class="post-time">{p['minutes']} MIN READ</span><span class="post-arrow">↗</span></span></a></article>''')
    return ''.join(items)


def homepage(site, user=None, token=None, message='', edit_todo=None, selected_date=None, calendar_month=None, search='', tag=''):
    all_posts = site.published_articles(bool(user and user['role'] == 'admin'))
    posts = site.filtered_articles(search or tag, bool(user and user['role'] == 'admin'))
    if tag:
        posts = [p for p in posts if tag in site.article_tags(p)]
    today = datetime.now(ZoneInfo('Asia/Hong_Kong')).date()
    selected_date = selected_date or today
    calendar_month = calendar_month or selected_date.replace(day=1)
    todos = site.todos_for_user(user['id']) if user else []
    tags = Counter(tag for p in all_posts for tag in site.article_tags(p))
    categories = Counter(p['category'] for p in all_posts)
    filters = '<form action="/" method="get" class="home-filter-form" role="search"><label class="sr-only" for="site-search-input">搜索文章</label>' + f'<input id="site-search-input" type="search" name="q" value="{escape(search)}" placeholder="搜索文章、标签或正文"><button type="submit">搜索</button></form>'
    filters += '<div class="filters" aria-label="按分类浏览"><a class="filter" href="/#latest">全部</a>' + ''.join(f'<a class="filter" href="/?q={quote(c)}#latest">{escape(c)} <span class="filter-count">{n:02d}</span></a>' for c, n in categories.items()) + '</div>'
    if search or tag:
        filters += f'<p class="search-label">{escape(search or "#"+tag)} · {len(posts)} 篇 <a href="/#latest">清除筛选 ×</a></p>'
    expense = '登录后查看本月收支'
    if user:
        with site.db_connection() as db:
            value = db.execute("SELECT COALESCE(SUM(amount_fen),0) FROM money_entries WHERE user_id=? AND kind='expense' AND entry_date LIKE ?", (user['id'], today.strftime('%Y-%m')+'%')).fetchone()[0]
        expense = '本月支出 ¥' + site.money.currency(value)
    replacements = {
        'HEADER': header(site, user, token), 'FOOTER': template('footer'), 'HEAD': head('home'),
        'SCRIPTS': scripts('home'), 'FILTERS': filters,
        'CALENDAR': site.render_calendar(all_posts, todos, calendar_month, selected_date),
        'TODO_PANEL': site.render_todo_panel(user, token, selected_date, edit_todo, message),
        'TAGS': ''.join(f'<a class="tag" href="/?tag={quote(t)}#latest">#{escape(t)} <span>{n}</span></a>' for t, n in tags.items()),
        'TOTAL': f'{len(all_posts):02d}', 'UPDATED': (all_posts[0]['published_at'] or all_posts[0]['updated_at'])[:10].replace('-', '.') if all_posts else '—',
        'MINUTES': str(sum(max(1,round(len(p['content'])/500)) for p in all_posts)), 'TAG_COUNT': str(len(tags)),
        'MONTH': today.strftime('%Y / %m'), 'EXPENSE': escape(expense),
    }
    markup = (ROOT / 'index.html').read_text(encoding='utf-8')
    markup = re.sub(r'<!-- ARTICLES_START -->.*?<!-- ARTICLES_END -->', lambda _: cards(site, posts), markup, flags=re.S)
    markup = re.sub(r'<!-- ([A-Z_]+) -->', lambda m: replacements.get(m[1], m[0]), markup)
    # Use the same functional search markup on every page.
    markup = re.sub(r'<dialog class="search-dialog".*?</dialog>', lambda _: search_dialog(), markup, flags=re.S)
    return markup


def archive(site, user=None, token=None):
    posts = data_posts(site, site.published_articles())
    sections = []
    for year in sorted({p['date'][:4] for p in posts}, reverse=True):
        rows = ''.join(f'<a class="archive-row" href="{escape(p["url"])}"><time>{escape(p["date"])}</time><div class="archive-row-main"><h3>{escape(p["title"])}</h3><p>{escape(p["excerpt"])}</p></div><span>{escape(p["category"])}</span></a>' for p in posts if p['date'].startswith(year))
        sections.append(f'<section class="year-block"><header class="year-head"><h2>{year}</h2></header>{rows}</section>')
    content = template('archive').replace('<!-- TIMELINE -->', ''.join(sections) or '<p>还没有已发布的文章。</p>')
    content = content.replace('<main>', '<main id="main">', 1)
    content = content.replace('08</span> ENTRIES', f'{len(posts):02d}</span> ENTRIES')
    content = content.replace('data-total-count>08', f'data-total-count>{len(posts):02d}').replace('data-total-minutes>46', f'data-total-minutes>{sum(p["minutes"] for p in posts)}').replace('data-category-count>05', f'data-category-count>{len({p["category"] for p in posts}):02d}')
    content = content.replace('data-result-label aria-live="polite">08 / 08', f'data-result-label aria-live="polite">{len(posts):02d} / {len(posts):02d}')
    content += f'<script>window.TL_POSTS={json_script(posts)};</script>'
    return layout(site, content, '文章归档', 'archive', user, token)


def article(site, post, user=None, token=None):
    rendered = site.markdown_to_html(post['content'])
    headings = re.findall(r'<h([1-6]) id="([^"]+)">(.*?)</h\1>', rendered, re.S)
    links = ''.join(f'<a href="#{escape(anchor)}">{re.sub("<[^>]+>", "", label)}</a>' for _, anchor, label in headings)
    # Wrap native Markdown code blocks for the demo's copy controls.
    count = 0
    def code_block(match):
        nonlocal count
        count += 1
        return f'<div class="code-block"><div class="code-head"><span>CODE</span><button type="button" class="copy-code" data-copy="#code-{count}">复制</button></div><div id="code-{count}">{match[0]}</div></div>'
    rendered = re.sub(r'<pre><code\b.*?</code></pre>', code_block, rendered, flags=re.S)
    tags = ''.join(f'<a class="rail-tag" href="/archive?tag={quote(t)}">#{escape(t)}</a>' for t in site.article_tags(post))
    cover = f'<img class="article-image" src="{escape(post["cover_image"])}" alt="" fetchpriority="high">' if post['cover_image'] else ''
    available = site.published_articles(bool(user and user['role'] == 'admin'))
    position = next((i for i, p in enumerate(available) if p['id'] == post['id']), None)
    adjacent = ''
    if position is not None:
        for offset, label in [(-1, '较新一篇'), (1, '较早一篇')]:
            if 0 <= position + offset < len(available):
                p = available[position + offset]
                adjacent += f'<a class="rail-action" href="/post/{quote(p["slug"], safe="")}">{label} · {escape(p["title"])}</a>'
    meta = f'<div class="page-meta"><time>{site.display_date(post["published_at"] or post["updated_at"])}</time><span>{max(1,round(len(post["content"])/500))} MIN READ</span><span>{escape(post["category"])}</span></div>'
    content = f'''<div class="reading-progress" aria-hidden="true"><span data-progress-bar></span></div><main id="main">
      {hero(post['title'], post['excerpt'], 'ESSAY / '+post['category'], 'article', meta)}
      <div class="reading-layout"><article class="reading-body"><details class="toc-mobile"><summary>文章目录 · {len(headings)} 节</summary><nav class="toc">{links}</nav></details>
      {cover}<div class="prose">{rendered}</div><footer class="article-end"><div class="rail-tags">{tags}</div><nav aria-label="相邻文章">{adjacent}</nav><a class="rail-action" href="/archive">← 返回归档</a></footer></article>
      <aside class="article-rail"><div class="rail-block"><p class="rail-label">ON THIS PAGE</p><nav class="toc" data-toc>{links}</nav></div>
      <div class="rail-block"><p class="rail-label">READING</p><div class="rail-progress" data-progress-ring><div><strong data-progress-label>0%</strong><span>READ</span></div></div></div>
      <div class="rail-block"><p class="rail-label">TAGS</p><div class="rail-tags">{tags}</div></div><button class="rail-action" type="button" data-copy-link>复制链接 ↗</button></aside></div></main>'''
    mathjax = r'''<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\(','\\)']],displayMath:[['$$','$$'],['\\[','\\]']]},svg:{fontCache:'global'}};</script><script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'''
    return layout(site, content, post['title'], 'article', user, token,
                  f'<meta name="description" content="{escape(post["excerpt"])}">'+mathjax)


def auth(site, registering=False, error=''):
    mode = site.registration_mode()
    title = '创建账号' if registering else '欢迎回来'
    fields = ''
    if registering and mode == 'invite':
        fields += '<div class="field"><label for="invite">邀请码</label><input id="invite" name="invite_code" required autocomplete="off"></div>'
    fields += '<div class="field"><label for="username">用户名</label><input id="username" name="username" required maxlength="30" autocomplete="username"></div>'
    fields += f'''<div class="field"><label for="password">密码</label><div class="password-wrap"><input id="password" name="password" type="password" required {'minlength="8"' if registering else ''} autocomplete="{'new-password' if registering else 'current-password'}"><button type="button" class="password-toggle" data-password-toggle="password" aria-label="显示密码">显示</button></div></div>'''
    if registering:
        fields += '<div class="field"><label for="passwordConfirm">确认密码</label><input id="passwordConfirm" name="password_confirm" type="password" minlength="8" required autocomplete="new-password"></div>'
    tabs = '<nav class="auth-tabs" aria-label="账号"><a class="auth-tab" href="/login">登录</a>' + ('<a class="auth-tab" href="/register">注册</a>' if mode != 'closed' else '') + '</nav>'
    form = f'''{tabs}<h1>{title}</h1><p class="auth-sub">登录后管理你的待办、账本和学习进度。</p><p class="field-error" role="alert">{escape(error)}</p><form class="auth-form" method="post" action="{'/register' if registering else '/login'}">{fields}<button class="auth-submit" type="submit">{'创建账号' if registering else '登录'} →</button></form>'''
    if registering and mode == 'closed':
        form = '<h1>暂停注册</h1><p>目前没有开放新账号注册。</p><a href="/login">返回登录</a>'
    content = template('login').replace('<!-- AUTH_FORM -->', form).replace('<main class="auth-shell">', '<main class="auth-shell" id="main">')
    return layout(site, content, title, 'register' if registering else 'login', bare=True)
