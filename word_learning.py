"""Small CET6 learning service, reusing the site's connection and account system."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def initialize(connection):
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS word_progress (
      user_id INTEGER NOT NULL, word TEXT COLLATE NOCASE NOT NULL,
      due_at TEXT NOT NULL, interval_days REAL NOT NULL, repetitions INTEGER NOT NULL,
      lapses INTEGER NOT NULL, updated_at TEXT NOT NULL,
      PRIMARY KEY(user_id, word));
    CREATE INDEX IF NOT EXISTS word_due ON word_progress(user_id, due_at);
    CREATE TABLE IF NOT EXISTS word_reviews (
      request_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, word TEXT NOT NULL,
      rating INTEGER NOT NULL, mode TEXT NOT NULL, correct INTEGER NOT NULL,
      reviewed_at TEXT NOT NULL, due_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS word_review_user ON word_reviews(user_id, reviewed_at);
    ''')


def dictionary(path):
    # Read-only: a missing dictionary must not silently create an empty database.
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def catalog(path, query='', page=1):
    with dictionary(path) as db:
        term = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        where = "WHERE word LIKE ? ESCAPE '\\' OR translation LIKE ? ESCAPE '\\'"
        total = db.execute('SELECT COUNT(*) FROM words ' + where, (term, term)).fetchone()[0]
        rows = db.execute('SELECT * FROM words ' + where +
                          ' ORDER BY frequency_rank IS NULL, frequency_rank, word LIMIT 30 OFFSET ?',
                          (term, term, (page-1)*30)).fetchall()
        return {'words': [dict(r) for r in rows], 'total': total, 'page': page}


def today(path, connection, user_id):
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    stats = {'learned': 0, 'due': 0, 'reviews_today': 0}
    states = {}
    if user_id is not None:
        states = {r['word'].casefold(): dict(r) for r in connection.execute(
            'SELECT * FROM word_progress WHERE user_id=?', (user_id,))}
        stats['learned'] = len(states)
        stats['due'] = sum(r['due_at'] <= now for r in states.values())
        midnight = datetime.now(ZoneInfo('Asia/Hong_Kong')).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat(timespec='seconds')
        stats['reviews_today'] = connection.execute(
            'SELECT COUNT(*) FROM word_reviews WHERE user_id=? AND reviewed_at>=?', (user_id, midnight)).fetchone()[0]
    with dictionary(path) as db:
        stats['total'] = db.execute('SELECT COUNT(*) FROM words').fetchone()[0]
        # A small dictionary (~5k entries); only the selected batch is sent to clients.
        rows = db.execute('SELECT * FROM words ORDER BY frequency_rank IS NULL, frequency_rank, word').fetchall()
    due, new = [], []
    for row in rows:
        state = states.get(row['word'].casefold())
        if state and state['due_at'] <= now:
            due.append((state['due_at'], dict(row)))
        elif state is None and len(new) < 10:
            new.append(dict(row))
    due.sort(key=lambda r: r[0])
    words = [w for _, w in due[:20]]
    if len(words) < 20:
        words.extend(new[:20-len(words)])
    return {'words': words, 'stats': stats, 'guest': user_id is None}


def review(path, connection, user_id, form):
    word = form.get('word', '')
    rating = int(form.get('rating', '0'))
    mode = form.get('mode', '')
    request_id = form.get('request_id', '')
    if rating not in (1, 2, 3, 4) or mode not in ('recall', 'spell') or not 16 <= len(request_id) <= 100:
        raise ValueError('无效的复习记录')
    with dictionary(path) as db:
        row = db.execute('SELECT word FROM words WHERE word=?', (word,)).fetchone()
    if row is None:
        raise ValueError('词条不存在')
    word = row['word']
    correct = mode == 'recall' or form.get('answer', '').strip().casefold() == word.casefold()
    if not correct:
        rating = 1
    now = datetime.now(timezone.utc)
    # Serialize progress updates and use request IDs to make retrying safe.
    connection.execute('BEGIN IMMEDIATE')
    previous = connection.execute('SELECT due_at FROM word_reviews WHERE request_id=? AND user_id=?', (request_id, user_id)).fetchone()
    if previous:
        return {'due_at': previous['due_at'], 'duplicate': True}
    state = connection.execute('SELECT * FROM word_progress WHERE user_id=? AND word=?', (user_id, word)).fetchone()
    interval = state['interval_days'] if state else 0
    reps = state['repetitions'] if state else 0
    lapses = state['lapses'] if state else 0
    # Transparent initial scheduler, not advertised as FSRS or calibrated SM-2.
    if rating == 1:
        interval, reps, lapses = 10/1440, 0, lapses+1
    elif rating == 2:
        interval, reps = max(1, interval*1.2), reps+1
    elif rating == 3:
        interval, reps = (1 if reps == 0 else 3 if reps == 1 else max(3, interval*2)), reps+1
    else:
        interval, reps = max(4, interval*2.5), reps+1
    interval = min(interval, 180)
    due_at = (now + timedelta(days=interval)).isoformat(timespec='seconds')
    stamp = now.isoformat(timespec='seconds')
    connection.execute('INSERT INTO word_reviews VALUES (?,?,?,?,?,?,?,?)',
                       (request_id, user_id, word, rating, mode, int(correct), stamp, due_at))
    connection.execute('INSERT OR REPLACE INTO word_progress VALUES (?,?,?,?,?,?,?)',
                       (user_id, word, due_at, interval, reps, lapses, stamp))
    return {'due_at': due_at, 'rating': rating, 'correct': correct}


def page(csrf, logged_in):
    notice = '进度保存到你的账号，可跨设备复习。' if logged_in else '游客体验：本次练习不保存。登录后记录学习进度。'
    return f'''<main class="words-shell" data-csrf="{csrf}" data-logged-in="{str(logged_in).lower()}">
      <nav class="words-nav"><a href="/">← 首页</a><a href="/login">账号登录</a><a href="#library">六级词库</a></nav>
      <div class="words-heading"><span class="eyebrow">CET-6 / DAILY PRACTICE</span><h1>把认识，练成记得。</h1><p>{notice}</p></div>
      <div id="words-stats" class="words-stats" aria-live="polite"></div>
      <section class="study-card" aria-labelledby="study-title">
        <div class="study-toolbar"><h2 id="study-title">今日学习</h2><label>练习方式 <select id="study-mode"><option value="recall">看英文，回忆词义</option><option value="spell">看释义，默写英文</option></select></label></div>
        <p class="words-hint">优先复习到期词，每批最多 20 词，包含最多 10 个新词。先尝试回忆，再查看答案。</p>
        <p id="study-progress"></p><div id="study-prompt"></div>
        <form id="study-form"><label for="study-answer" id="answer-label">写下你回忆的词义（可选）</label><input id="study-answer" autocomplete="off" autocapitalize="off" spellcheck="false"><button class="admin-button primary" id="reveal" type="submit">查看答案 ↵</button></form>
        <div id="study-solution" hidden><div id="study-result"></div><h3 id="solution-word"></h3><p id="solution-phonetic"></p><button class="admin-button" id="speak" type="button">听发音</button><p id="solution-translation"></p><p id="solution-definition"></p>
          <p class="words-hint">答错或没有回忆出来，请选“忘了”。默写错误自动按“忘了”记录。</p>
          <div class="rating-buttons"><button type="button" data-rating="1">忘了<small>10 分钟</small></button><button type="button" data-rating="2">很难<small>较短间隔</small></button><button type="button" data-rating="3">记得<small>正常间隔</small></button><button type="button" data-rating="4">很容易<small>较长间隔</small></button></div>
        </div><p id="study-message" role="status"></p><button class="admin-button" id="study-restart" type="button" hidden>加载下一批</button>
      </section>
      <section id="library" class="words-library"><h2>六级词库</h2><p class="words-hint">来源：ECDICT cet6 标签（5,407 条），释义尚未逐条校对。不是官方大纲认证词表。</p><form id="library-search" class="site-search"><label class="sr-only" for="library-query">搜索单词或中文释义</label><input id="library-query" maxlength="100" placeholder="搜索单词或中文释义"><button type="submit" aria-label="搜索">⌕</button></form><p id="library-count" role="status"></p><div id="library-list"></div><div class="words-pagination"><button class="admin-button" id="library-prev" type="button">上一页</button><button class="admin-button" id="library-next" type="button">下一页</button></div></section>
    </main><script src="/words.js?v=1" defer></script>'''
