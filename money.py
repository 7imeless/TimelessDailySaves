"""Private CNY ledger. Amounts are stored as integer fen."""
import calendar
import csv
import io
import re
from datetime import date, datetime, timezone
from html import escape
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

CATEGORIES = {
    'expense': ('餐饮', '交通', '购物', '住房', '娱乐', '医疗', '学习', '其他支出'),
    'income': ('工资', '奖金', '兼职', '其他收入'),
}


def initialize(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS money_entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
      kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
      amount_fen INTEGER NOT NULL CHECK(amount_fen>0),
      category TEXT NOT NULL, entry_date TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS money_user_date ON money_entries(user_id,entry_date,id);
    ''')


def amount(value):
    value = value.strip()
    if not re.fullmatch(r'(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,2})?', value):
        raise ValueError('金额需大于零，最多两位小数，且小于 1 亿元。')
    whole, _, fraction = value.partition('.')
    fen = int(whole)*100 + int(fraction.ljust(2, '0') or '0')
    if fen <= 0:
        raise ValueError('金额需大于零。')
    return fen


def currency(fen):
    sign = '-' if fen < 0 else ''
    fen = abs(fen)
    return f'{sign}{fen//100:,}.{fen%100:02d}'


def filters(query):
    month = query.get('month', [''])[0] or datetime.now(ZoneInfo('Asia/Hong_Kong')).strftime('%Y-%m')
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}', month):
        raise ValueError('月份格式无效。')
    try:
        first = date.fromisoformat(month+'-01')
    except ValueError:
        raise ValueError('月份无效。')
    last = f'{month}-{calendar.monthrange(first.year, first.month)[1]:02d}'
    category = query.get('category', [''])[0]
    if category and category not in sum(CATEGORIES.values(), ()):
        raise ValueError('分类无效。')
    try:
        page = max(1, int(query.get('page', ['1'])[0]))
    except ValueError:
        raise ValueError('页码无效。')
    return month, first.isoformat(), last, category, min(page, 1000000)


def save(db, user_id, form):
    kind = form.get('kind', '')
    category = form.get('category', '')
    if kind not in CATEGORIES or category not in CATEGORIES[kind]:
        raise ValueError('请选择与收入或支出匹配的分类。')
    fen = amount(form.get('amount', ''))
    try:
        day = date.fromisoformat(form.get('entry_date', '')).isoformat()
    except ValueError:
        raise ValueError('日期无效。')
    note = form.get('note', '').strip()
    if len(note) > 300:
        raise ValueError('备注最多 300 字。')
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    entry_id = form.get('id', '')
    if entry_id:
        if not entry_id.isdecimal():
            raise ValueError('记录不存在。')
        cursor = db.execute('UPDATE money_entries SET kind=?,amount_fen=?,category=?,entry_date=?,note=?,updated_at=? WHERE id=? AND user_id=?',
                            (kind, fen, category, day, note, stamp, int(entry_id), user_id))
        if cursor.rowcount != 1:
            raise ValueError('记录不存在。')
    else:
        db.execute('INSERT INTO money_entries (user_id,kind,amount_fen,category,entry_date,note,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                   (user_id, kind, fen, category, day, note, stamp, stamp))
    return day[:7]


def delete(db, user_id, form):
    try:
        entry_id = int(form.get('id', ''))
    except ValueError:
        raise ValueError('记录不存在。')
    if db.execute('DELETE FROM money_entries WHERE id=? AND user_id=?', (entry_id, user_id)).rowcount != 1:
        raise ValueError('记录不存在。')


def selection(user_id, first, last, category):
    sql = ' FROM money_entries WHERE user_id=? AND entry_date BETWEEN ? AND ?'
    params = [user_id, first, last]
    if category:
        sql += ' AND category=?'
        params.append(category)
    return sql, params


def export_csv(db, user_id, query):
    month, first, last, category, _ = filters(query)
    sql, params = selection(user_id, first, last, category)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['日期', '类型', '金额（元）', '分类', '备注'])
    for row in db.execute('SELECT *'+sql+' ORDER BY entry_date DESC,id DESC', params):
        # Prevent notes interpreted as spreadsheet formulas when opening exports.
        note = row['note']
        if note.lstrip().startswith(('=', '+', '-', '@')) or note.startswith(('\t', '\r', '\n')):
            note = "'"+note
        writer.writerow([row['entry_date'], '收入' if row['kind']=='income' else '支出',
                         f"{row['amount_fen']//100}.{row['amount_fen']%100:02d}", row['category'], note])
    return month, ('\ufeff'+stream.getvalue()).encode('utf-8')


def page(db, user_id, username, csrf, query, message='', submitted=None):
    month, first, last, category, number = filters(query)
    sql, params = selection(user_id, first, last, category)
    count = db.execute('SELECT COUNT(*)'+sql, params).fetchone()[0]
    pages = max(1, (count+29)//30)
    number = min(number, pages)
    rows = db.execute('SELECT *'+sql+' ORDER BY entry_date DESC,id DESC LIMIT 30 OFFSET ?', params+[(number-1)*30]).fetchall()
    totals = {r['kind']: r['total'] for r in db.execute('SELECT kind,SUM(amount_fen) total FROM money_entries WHERE user_id=? AND entry_date BETWEEN ? AND ? GROUP BY kind', (user_id, first, last))}
    income, expense = totals.get('income', 0), totals.get('expense', 0)
    breakdown = db.execute("SELECT category,SUM(amount_fen) total FROM money_entries WHERE user_id=? AND entry_date BETWEEN ? AND ? AND kind='expense' GROUP BY category ORDER BY total DESC", (user_id, first, last)).fetchall()
    editing = None
    if query.get('edit', [''])[0]:
        try:
            editing = db.execute('SELECT * FROM money_entries WHERE id=? AND user_id=?', (int(query['edit'][0]), user_id)).fetchone()
        except ValueError:
            pass
        if editing is None:
            raise ValueError('记录不存在。')
    values = submitted if submitted is not None else (dict(editing) if editing else {})
    if editing and submitted is None:
        values['amount'] = f"{editing['amount_fen']//100}.{editing['amount_fen']%100:02d}"
    def val(key, default=''):
        return escape(str(values.get(key, default)), quote=True)
    selected_kind = values.get('kind', 'expense')
    category_options = ''.join(f'<option value="{escape(c)}" data-kind="{kind}"'+(' selected' if values.get('category', '餐饮')==c else '')+f'>{c}</option>' for kind, cats in CATEGORIES.items() for c in cats)
    filter_options = '<option value="">全部分类</option>'+''.join(f'<option'+(' selected' if category==c else '')+f'>{c}</option>' for cats in CATEGORIES.values() for c in cats)
    qs = urlencode({'month': month, 'category': category})
    entries = []
    for r in rows:
        entry_id = r['id']
        entries.append(f'''<article class="money-entry"><div><strong>{escape(r['category'])}</strong><time>{r['entry_date']}</time><p>{escape(r['note'])}</p></div><div class="money-entry-actions"><strong class="money-{r['kind']}">{'+' if r['kind']=='income' else '−'}¥{currency(r['amount_fen'])}</strong><div><a href="/money?{qs}&amp;edit={entry_id}#entry-form">编辑</a><form method="post" action="/money/delete" onsubmit="return confirm('确定删除这笔记录？')"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="id" value="{entry_id}"><input type="hidden" name="month" value="{month}"><button type="submit">删除</button></form></div></div></article>''')
    bars = ''.join(f'<div class="money-category"><span>{escape(r["category"])}</span><meter min="0" max="{expense or 1}" value="{r["total"]}" aria-label="{escape(r["category"])}支出"></meter><span>¥{currency(r["total"])} · {r["total"]*100/expense:.1f}%</span></div>' for r in breakdown)
    today = datetime.now(ZoneInfo('Asia/Hong_Kong')).date().isoformat()
    return f'''<main class="money-shell"><nav class="money-nav"><a href="/">← 首页</a><span>已登录 · {escape(username)}</span><a href="/words">背单词</a></nav><header class="money-heading"><p class="eyebrow">PERSONAL LEDGER / CNY</p><h1>日常账本</h1><p>记下每一笔，了解钱花在哪里。</p></header>
      <form class="money-filters" method="get" action="/money"><label>月份<input type="month" name="month" value="{month}" required></label><label>明细分类<select name="category">{filter_options}</select></label><button class="admin-button" type="submit">查看</button><a class="admin-button" href="/money/export?{qs}">导出 CSV</a></form>
      <div class="money-stats"><div><span>本月收入</span><strong>¥{currency(income)}</strong></div><div><span>本月支出</span><strong>¥{currency(expense)}</strong></div><div><span>本月结余</span><strong>¥{currency(income-expense)}</strong></div></div><p class="money-hint">月度概览包含当月全部分类；分类筛选仅影响明细和导出。</p>
      <p class="money-message" role="status">{escape(message)}</p><div class="money-layout"><section class="money-panel" id="entry-form"><h2>{'编辑记录' if values.get('id') else '记一笔'}</h2><form method="post" action="/money/save" class="money-form"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="id" value="{val('id')}"><label>类型<select name="kind" id="money-kind"><option value="expense"{' selected' if selected_kind=='expense' else ''}>支出</option><option value="income"{' selected' if selected_kind=='income' else ''}>收入</option></select></label><label>金额（元）<input name="amount" inputmode="decimal" placeholder="0.00" value="{val('amount')}" required maxlength="12"></label><label>分类<select name="category" id="money-category">{category_options}</select></label><label>日期<input type="date" name="entry_date" value="{val('entry_date',today)}" required></label><label class="money-wide">备注<input name="note" value="{val('note')}" maxlength="300" placeholder="可选，最多 300 字"></label><div class="money-wide money-form-actions"><button class="admin-button primary" type="submit">{'保存修改' if values.get('id') else '保存记录'}</button><a class="admin-button" href="/money?month={month}">清空 / 取消</a></div></form></section><section class="money-panel"><h2>本月支出去向</h2>{bars or '<p class="money-hint">本月还没有支出记录。</p>'}</section></div>
      <section class="money-panel money-list"><h2>{month} 收支明细</h2><p class="money-hint">{count} 笔 · 第 {number} / {pages} 页</p>{''.join(entries) or '<p class="money-hint">暂无记录，记下第一笔吧。</p>'}<nav class="money-pagination">{f'<a class="admin-button" href="/money?{qs}&amp;page={number-1}">上一页</a>' if number>1 else ''}{f'<a class="admin-button" href="/money?{qs}&amp;page={number+1}">下一页</a>' if number<pages else ''}</nav></section></main><script src="/money.js?v=1" defer></script>'''
