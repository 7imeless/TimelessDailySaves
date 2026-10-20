(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const pad = (value) => String(value).padStart(2, '0');
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const replaceDashes = (value) => value.replaceAll('-', '.');
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const POSTS = [
    {
      id: 'cache',
      category: '工程实践',
      date: '2026-10-12',
      title: '缓存失效之后：一次关于“新鲜感”的系统思考',
      excerpt: '一个缓存 key 没有失效，整个首页却像失去了记忆。从一次线上事故出发，聊聊缓存、认知，以及我们为什么总会忘记更新。',
      minutes: 8,
      tags: ['系统设计', '缓存', '写作'],
      featured: true
    },
    {
      id: 'slow-query',
      category: '随笔',
      date: '2026-09-18',
      title: '把写作当成一次慢查询',
      excerpt: '不急着给结论，让问题在草稿里多待一会儿。写作和查库一样，慢一点，才看得见真正昂贵的部分。',
      minutes: 5,
      tags: ['写作', '注意力']
    },
    {
      id: 'best-practice',
      category: '前端',
      date: '2026-08-24',
      title: '当我不再追逐“最佳实践”',
      excerpt: '工具会变，但判断问题的方式可以留下。比起记住答案，我更想保留提问的顺序。',
      minutes: 6,
      tags: ['前端', '工程']
    },
    {
      id: 'design-defaults',
      category: '读书',
      date: '2026-07-16',
      title: '读《设计心理学》：好的默认值',
      excerpt: '少一个选择，有时就是多一点自由。好的默认值不替人做决定，它只是让正确的路更容易走。',
      minutes: 4,
      tags: ['设计', '阅读']
    },
    {
      id: 'observability',
      category: '工程实践',
      date: '2026-06-08',
      title: '把“可观测”从口号变成习惯',
      excerpt: '日志、指标和那些真正需要被看见的信号。可观测不是多接一块大屏，而是先想清楚要回答什么问题。',
      minutes: 9,
      tags: ['系统设计', '可观测性']
    },
    {
      id: 'workflow',
      category: '工具',
      date: '2026-05-21',
      title: '从一张便签到一套工具',
      excerpt: '工具不是越多越好。它应该沿着你原本的动作生长，而不是要求你换一种生活。',
      minutes: 7,
      tags: ['工具', '系统设计']
    },
    {
      id: 'quiet',
      category: '随笔',
      date: '2026-04-29',
      title: '给忙碌的人留一块没有通知的地方',
      excerpt: '关于注意力、边界和一个下午的散步。不是逃离连接，而是重新决定什么时候被找到。',
      minutes: 3,
      tags: ['注意力', '生活']
    },
    {
      id: 'paper-notes',
      category: '随笔',
      date: '2026-02-06',
      title: '为什么我又开始用纸质笔记',
      excerpt: '纸张不会提醒我同步，也不会在深夜推送一条回顾。它只是安静地等一支笔。',
      minutes: 4,
      tags: ['工具', '阅读', '注意力']
    }
  ];

  const POST_BY_ID = new Map(POSTS.map((post) => [post.id, post]));
  const TAG_ORDER = ['系统设计', '写作', '注意力', '工具', '阅读', '设计'];
  const state = { filter: 'all', tag: null, limit: 5 };

  const feature = $('[data-feature]');
  const postList = $('#postList');
  const listLabel = $('[data-list-label]');
  const resultCount = $('[data-result-count]');
  const moreButton = $('[data-more]');
  const moreCount = $('[data-more-count]');
  const moreWrap = $('.list-more-wrap');
  const emptyState = $('[data-empty]');
  const tagCloud = $('[data-tag-cloud]');
  const head = $('[data-head]');
  const toTop = $('[data-top]');
  const toast = $('[data-toast]');

  /* ------------------------------------------------------------------------
     Theme + header chrome
     ------------------------------------------------------------------------ */

  const themeKey = 'timeless-demo-theme';
  const themeToggle = $('[data-theme-toggle]');
  const themeColor = $('meta[name="theme-color"]');

  const applyTheme = (theme, persist = true) => {
    document.documentElement.dataset.theme = theme;
    if (themeColor) themeColor.setAttribute('content', theme === 'light' ? '#f2eee3' : '#080a09');
    const next = theme === 'light' ? '夜航' : '日间';
    themeToggle.setAttribute('aria-label', `切换到${next}模式`);
    themeToggle.setAttribute('title', `切换到${next}模式`);
    if (persist) {
      try { localStorage.setItem(themeKey, theme); } catch (_) { /* private mode */ }
    }
  };

  applyTheme(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark', false);
  themeToggle.addEventListener('click', () => {
    applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
  });

  let scrollTicking = false;
  const updateScrollChrome = () => {
    const y = window.scrollY;
    head.classList.toggle('is-stuck', y > 24);
    toTop.classList.toggle('is-on', y > 720);
    scrollTicking = false;
  };
  window.addEventListener('scroll', () => {
    if (!scrollTicking) {
      scrollTicking = true;
      window.requestAnimationFrame(updateScrollChrome);
    }
  }, { passive: true });
  updateScrollChrome();

  toTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  });

  /* ------------------------------------------------------------------------
     Clock
     ------------------------------------------------------------------------ */

  const clock = $('[data-clock]');
  const updateClock = () => {
    try {
      const time = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Hong_Kong',
        hour: '2-digit',
        minute: '2-digit',
        hourCycle: 'h23'
      }).format(new Date());
      clock.textContent = `HONG KONG · ${time}`;
    } catch (_) {
      clock.textContent = 'HONG KONG';
    }
  };
  updateClock();
  window.setInterval(updateClock, 30000);

  /* ------------------------------------------------------------------------
     Toast
     ------------------------------------------------------------------------ */

  let toastTimer = 0;
  const showToast = (message) => {
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('is-on');
    toastTimer = window.setTimeout(() => toast.classList.remove('is-on'), 2800);
  };

  $$('[data-demo]').forEach((link) => {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      showToast(link.dataset.demo);
    });
  });

  /* ------------------------------------------------------------------------
     Posts, filters, tags
     ------------------------------------------------------------------------ */

  const countByCategory = (category) => POSTS.filter((post) => post.category === category).length;
  const countByTag = (tag) => POSTS.filter((post) => post.tags.includes(tag)).length;

  const syncFilterUI = () => {
    $$('.filter').forEach((button) => {
      const active = button.dataset.filter === state.filter;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    $$('.tag').forEach((button) => {
      const active = button.dataset.tag === state.tag;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  };

  const filtered = () => state.filter !== 'all' || state.tag !== null;

  const postRow = (post, index) => `
    <article class="post-row" data-post-id="${post.id}" style="--i:${index}">
      <a class="post-row-link" href="#post-${post.id}" data-open-post="${post.id}">
        <span class="post-index" aria-hidden="true">${pad(POSTS.indexOf(post) + 1)}</span>
        <span class="post-body">
          <span class="post-cat">${escapeHtml(post.category)}</span>
          <span class="post-title">${escapeHtml(post.title)}</span>
          <span class="post-excerpt">${escapeHtml(post.excerpt)}</span>
        </span>
        <span class="post-aside">
          <span class="post-date">${replaceDashes(post.date)}</span>
          <span class="post-time">${post.minutes} MIN READ</span>
          <span class="post-arrow" aria-hidden="true">↗</span>
        </span>
      </a>
    </article>`;

  const currentMatches = () => POSTS.filter((post) => {
    if (state.filter !== 'all' && post.category !== state.filter) return false;
    if (state.tag && !post.tags.includes(state.tag)) return false;
    return true;
  });

  const render = () => {
    const isFiltered = filtered();
    const matches = currentMatches();
    const featuredPost = isFiltered ? null : POST_BY_ID.get('cache');
    const listPosts = featuredPost ? matches.filter((post) => post.id !== featuredPost.id) : matches;
    const visiblePosts = isFiltered ? listPosts : listPosts.slice(0, state.limit);

    feature.hidden = Boolean(featuredPost === null);
    postList.innerHTML = visiblePosts.map(postRow).join('');
    emptyState.hidden = listPosts.length !== 0;

    if (isFiltered) {
      const label = state.filter !== 'all' ? state.filter : `#${state.tag}`;
      listLabel.textContent = `${label} 的记录`;
      resultCount.textContent = `${listPosts.length} 篇`;
    } else {
      listLabel.textContent = '更多记录';
      resultCount.textContent = `${visiblePosts.length} / ${listPosts.length} 篇`;
    }

    moreWrap.hidden = isFiltered || state.limit >= listPosts.length;
    moreCount.textContent = `+${Math.max(0, listPosts.length - state.limit)}`;

    $$('[data-clear-filter]').forEach((button) => {
      button.hidden = !isFiltered;
    });

    syncFilterUI();
  };

  const setFilter = (category) => {
    state.filter = category;
    state.tag = null;
    state.limit = 5;
    render();
  };

  const setTag = (tag) => {
    state.tag = state.tag === tag ? null : tag;
    state.filter = 'all';
    state.limit = 5;
    render();
    if (window.matchMedia('(max-width: 1020px)').matches) {
      $('#latest').scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' });
    }
  };

  const clearFilters = () => {
    state.filter = 'all';
    state.tag = null;
    state.limit = 5;
    render();
  };

  $$('.filter').forEach((button) => {
    button.addEventListener('click', () => setFilter(button.dataset.filter));
  });

  $$('[data-count]').forEach((element) => {
    const category = element.dataset.count;
    element.textContent = pad(category === 'all' ? POSTS.length : countByCategory(category));
  });

  tagCloud.innerHTML = TAG_ORDER.map((tag) => `
    <button class="tag" type="button" data-tag="${tag}" aria-pressed="false">#${tag}<b>${pad(countByTag(tag))}</b></button>
  `).join('');

  $$('.tag', tagCloud).forEach((button) => {
    button.addEventListener('click', () => setTag(button.dataset.tag));
  });

  $$('[data-clear-filter]').forEach((button) => {
    button.addEventListener('click', clearFilters);
  });

  moreButton.addEventListener('click', () => {
    state.limit += 3;
    render();
  });

  /* ------------------------------------------------------------------------
     Calendar
     ------------------------------------------------------------------------ */

  const now = new Date();
  const todayKey = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const calendar = { year: now.getFullYear(), month: now.getMonth(), selected: todayKey };
  const calTitle = $('[data-cal-title]');
  const calCaption = $('[data-cal-caption]');
  const calGrid = $('[data-cal-grid]');
  const calNote = $('[data-cal-note]');

  const dateLabel = (key) => {
    const date = new Date(`${key}T12:00:00`);
    return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
  };

  const renderCalendarNote = () => {
    if (!calendar.selected) {
      calNote.textContent = '点击有圆点的日期查看当天记录。';
      return;
    }
    const label = dateLabel(calendar.selected);
    const isToday = calendar.selected === todayKey;
    const posts = POSTS.filter((post) => post.date === calendar.selected);
    if (!posts.length) {
      calNote.innerHTML = `<strong>${label}${isToday ? ' · 今天' : ''}</strong><br>${isToday ? '今天还没有写下什么。' : '这一天没有记录。'}`;
      return;
    }
    const extra = posts.length > 1 ? ` <span>+${posts.length - 1}</span>` : '';
    calNote.innerHTML = `<strong>${label}${isToday ? ' · 今天' : ''}</strong><br><button type="button" data-cal-open="${posts[0].id}">${escapeHtml(posts[0].title)}</button>${extra}`;
  };

  const renderCalendar = () => {
    const first = new Date(calendar.year, calendar.month, 1);
    const daysInMonth = new Date(calendar.year, calendar.month + 1, 0).getDate();
    const offset = (first.getDay() + 6) % 7;
    const cells = [];

    for (let i = 0; i < offset; i += 1) {
      cells.push('<span class="cal-blank" aria-hidden="true"></span>');
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const key = `${calendar.year}-${pad(calendar.month + 1)}-${pad(day)}`;
      const hasPost = POSTS.some((post) => post.date === key);
      const classes = ['cal-day'];
      if (key === todayKey) classes.push('is-today');
      if (key === calendar.selected) classes.push('is-selected');
      if (hasPost) classes.push('has-post');
      const fullLabel = `${calendar.year} 年 ${calendar.month + 1} 月 ${day} 日${hasPost ? '，有文章' : ''}`;
      cells.push(`<button type="button" class="${classes.join(' ')}" data-cal-date="${key}" aria-label="${fullLabel}" aria-pressed="${key === calendar.selected}">${day}</button>`);
    }

    calGrid.innerHTML = cells.join('');
    calTitle.textContent = `${calendar.year} 年 ${calendar.month + 1} 月`;
    calCaption.textContent = `${calendar.year} / ${pad(calendar.month + 1)}`;
    renderCalendarNote();
  };

  calGrid.addEventListener('click', (event) => {
    const button = event.target.closest('[data-cal-date]');
    if (!button) return;
    calendar.selected = button.dataset.calDate;
    renderCalendar();
  });

  $('[data-cal-prev]').addEventListener('click', () => {
    calendar.month -= 1;
    if (calendar.month < 0) {
      calendar.month = 11;
      calendar.year -= 1;
    }
    calendar.selected = null;
    renderCalendar();
  });

  $('[data-cal-next]').addEventListener('click', () => {
    calendar.month += 1;
    if (calendar.month > 11) {
      calendar.month = 0;
      calendar.year += 1;
    }
    calendar.selected = null;
    renderCalendar();
  });

  calNote.addEventListener('click', (event) => {
    const button = event.target.closest('[data-cal-open]');
    if (button) openPost(button.dataset.calOpen);
  });

  /* ------------------------------------------------------------------------
     Field notes (local todo)
     ------------------------------------------------------------------------ */

  const todoKey = 'timeless-demo-todos-v1';
  const todoList = $('[data-todo-list]');
  const todoCount = $('[data-todo-count]');
  const todoForm = $('[data-todo-form]');
  const todoInput = $('[data-todo-input]');
  const defaultTodos = [
    { id: 't1', text: '整理缓存事故的时间线', done: false },
    { id: 't2', text: '把《设计心理学》的划线归档', done: true },
    { id: 't3', text: '列一份十一月阅读清单', done: false }
  ];

  const loadTodos = () => {
    try {
      const raw = window.localStorage.getItem(todoKey);
      if (!raw) return defaultTodos.map((todo) => ({ ...todo }));
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return defaultTodos.map((todo) => ({ ...todo }));
      const cleaned = parsed
        .filter((todo) => todo && typeof todo.text === 'string' && todo.text.trim())
        .slice(0, 30)
        .map((todo, index) => ({
          id: String(todo.id || `local-${index}`),
          text: todo.text.slice(0, 60),
          done: Boolean(todo.done)
        }));
      return cleaned.length ? cleaned : defaultTodos.map((todo) => ({ ...todo }));
    } catch (_) {
      return defaultTodos.map((todo) => ({ ...todo }));
    }
  };

  let todos = loadTodos();

  const saveTodos = () => {
    try { window.localStorage.setItem(todoKey, JSON.stringify(todos)); } catch (_) { /* private mode */ }
  };

  const renderTodos = () => {
    todoList.innerHTML = todos.map((todo) => `
      <li class="todo-item" data-todo-id="${escapeHtml(todo.id)}">
        <label class="todo-main">
          <input class="todo-check" type="checkbox" ${todo.done ? 'checked' : ''} data-todo-toggle>
          <span class="todo-box" aria-hidden="true"></span>
          <span class="todo-text">${escapeHtml(todo.text)}</span>
        </label>
        <button class="todo-del" type="button" data-todo-del aria-label="删除待办：${escapeHtml(todo.text)}">×</button>
      </li>
    `).join('');
    const done = todos.filter((todo) => todo.done).length;
    todoCount.textContent = `${done} / ${todos.length}`;
  };

  todoList.addEventListener('change', (event) => {
    const checkbox = event.target.closest('[data-todo-toggle]');
    if (!checkbox) return;
    const item = checkbox.closest('[data-todo-id]');
    const todo = todos.find((entry) => entry.id === item.dataset.todoId);
    if (!todo) return;
    todo.done = checkbox.checked;
    saveTodos();
    renderTodos();
    todoList.querySelector(`[data-todo-id="${todo.id}"] [data-todo-toggle]`)?.focus();
  });

  todoList.addEventListener('click', (event) => {
    const button = event.target.closest('[data-todo-del]');
    if (!button) return;
    const item = button.closest('[data-todo-id]');
    todos = todos.filter((todo) => todo.id !== item.dataset.todoId);
    saveTodos();
    renderTodos();
    todoInput.focus();
  });

  todoForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = todoInput.value.trim().slice(0, 60);
    if (!text) {
      todoInput.focus();
      return;
    }
    const id = window.crypto && typeof window.crypto.randomUUID === 'function'
      ? window.crypto.randomUUID()
      : `local-${Date.now()}`;
    todos.push({ id, text, done: false });
    saveTodos();
    todoInput.value = '';
    renderTodos();
    todoInput.focus();
  });

  /* ------------------------------------------------------------------------
     Search dialog
     ------------------------------------------------------------------------ */

  const searchDialog = $('[data-search-dialog]');
  const searchLayer = $('[data-search-layer]');
  const searchInput = $('[data-search-input]');
  const searchResults = $('[data-search-results]');
  const searchHint = $('[data-search-hint]');
  let lastSearchTrigger = null;
  let searchResultsData = [];
  let activeSearchIndex = -1;

  const highlight = (text, query) => {
    if (!query) return escapeHtml(text);
    const pieces = String(text).split(new RegExp(`(${escapeRegExp(query)})`, 'gi'));
    return pieces.map((piece, index) => (index % 2 ? `<mark>${escapeHtml(piece)}</mark>` : escapeHtml(piece))).join('');
  };

  const setActiveSearchResult = (index) => {
    const options = $$('li[role="option"]', searchResults);
    activeSearchIndex = index;
    options.forEach((option, optionIndex) => {
      const active = optionIndex === index;
      option.classList.toggle('is-active', active);
      option.setAttribute('aria-selected', String(active));
    });
    if (index >= 0 && options[index]) {
      searchInput.setAttribute('aria-activedescendant', options[index].id);
      options[index].scrollIntoView({ block: 'nearest' });
    } else {
      searchInput.removeAttribute('aria-activedescendant');
    }
  };

  const renderSearch = (query) => {
    const term = query.trim();
    searchResultsData = term
      ? POSTS.filter((post) => {
          const haystack = [post.title, post.excerpt, post.category, ...post.tags].join(' ').toLowerCase();
          return haystack.includes(term.toLowerCase());
        })
      : POSTS.slice(0, 3);

    if (!searchResultsData.length) {
      searchHint.textContent = `没有找到“${term}”`;
      searchResults.innerHTML = `
        <li class="search-empty" role="presentation">
          <span class="empty-mark" aria-hidden="true">∅</span>
          没有找到对应的记录。
          <div class="search-suggestions">
            ${['缓存', '读书', '设计', '工具'].map((tag) => `<button type="button" data-suggest="${tag}">${tag}</button>`).join('')}
          </div>
        </li>`;
      activeSearchIndex = -1;
      searchInput.removeAttribute('aria-activedescendant');
      return;
    }

    searchHint.textContent = term
      ? `${searchResultsData.length} 条结果 · ↑↓ 选择 · ↵ 定位`
      : '最近记录 · 输入标题、分类或标签开始搜索';

    searchResults.innerHTML = searchResultsData.map((post, index) => `
      <li role="option" id="search-opt-${index}" aria-selected="${index === 0}">
        <button class="search-result" type="button" tabindex="-1" data-result-id="${post.id}">
          <span class="result-cat">${highlight(post.category, term)} <span class="result-tags">${post.tags.slice(0, 2).map((tag) => `#${highlight(tag, term)}`).join(' ')}</span></span>
          <span class="result-title">${highlight(post.title, term)}</span>
          <span class="result-excerpt">${highlight(post.excerpt, term)}</span>
          <span class="result-date">${replaceDashes(post.date)}</span>
        </button>
      </li>
    `).join('');

    setActiveSearchResult(0);
  };

  const openSearch = (trigger = null) => {
    lastSearchTrigger = trigger || document.activeElement;
    if (!searchDialog.open) searchDialog.showModal();
    document.body.classList.add('is-locked');
    searchInput.value = '';
    renderSearch('');
    window.requestAnimationFrame(() => searchInput.focus({ preventScroll: true }));
  };

  const closeSearch = (restoreFocus = true) => {
    if (searchDialog.open) searchDialog.close();
    document.body.classList.remove('is-locked');
    if (restoreFocus && lastSearchTrigger instanceof HTMLElement) {
      lastSearchTrigger.focus({ preventScroll: true });
    }
  };

  $$('[data-search-open]').forEach((button) => {
    button.addEventListener('click', () => openSearch(button));
  });

  $$('[data-search-close]').forEach((button) => {
    button.addEventListener('click', () => closeSearch());
  });

  searchDialog.addEventListener('cancel', (event) => {
    event.preventDefault();
    closeSearch();
  });

  searchDialog.addEventListener('close', () => {
    document.body.classList.remove('is-locked');
  });

  searchDialog.addEventListener('click', (event) => {
    if (event.target === searchDialog || event.target === searchLayer) closeSearch();
  });

  searchInput.addEventListener('input', () => renderSearch(searchInput.value));

  searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeSearch();
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!searchResultsData.length) return;
      setActiveSearchResult((activeSearchIndex + 1) % searchResultsData.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      if (!searchResultsData.length) return;
      setActiveSearchResult((activeSearchIndex - 1 + searchResultsData.length) % searchResultsData.length);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      const post = searchResultsData[activeSearchIndex];
      if (post) {
        closeSearch(false);
        openPost(post.id);
      }
    }
  });

  searchResults.addEventListener('click', (event) => {
    const button = event.target.closest('[data-result-id]');
    if (button) {
      closeSearch(false);
      openPost(button.dataset.resultId);
      return;
    }
    const suggestion = event.target.closest('[data-suggest]');
    if (suggestion) {
      searchInput.value = suggestion.dataset.suggest;
      renderSearch(suggestion.dataset.suggest);
      searchInput.focus();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && searchDialog.open) {
      event.preventDefault();
      closeSearch();
      return;
    }
    const target = event.target instanceof Element ? event.target : null;
    const typing = Boolean(target && target.closest('input, textarea, select, [contenteditable="true"]'));
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      if (searchDialog.open) closeSearch();
      else openSearch();
      return;
    }
    if (event.key === '/' && !typing && !searchDialog.open) {
      event.preventDefault();
      openSearch();
    }
  });

  /* ------------------------------------------------------------------------
     Open / locate a post (the concept stops at the homepage)
     ------------------------------------------------------------------------ */

  const openPost = (id) => {
    const post = POST_BY_ID.get(id);
    if (!post) return;

    if (id === 'cache') {
      window.location.href = 'pages/article.html';
      return;
    }

    state.filter = 'all';
    state.tag = null;
    state.limit = POSTS.length;
    render();

    window.requestAnimationFrame(() => {
      const target = document.querySelector(`[data-post-id="${id}"]`);
      if (!target) return;
      target.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' });
      target.classList.remove('is-flash');
      void target.offsetWidth;
      target.classList.add('is-flash');
      window.setTimeout(() => target.classList.remove('is-flash'), 1700);
      showToast('概念稿只接入了《缓存失效之后》的完整正文；其它文章可以在归档页查看。');
    });
  };

  document.addEventListener('click', (event) => {
    const opener = event.target.closest('[data-open-post]');
    if (!opener) return;
    event.preventDefault();
    openPost(opener.dataset.openPost);
  });

  /* ------------------------------------------------------------------------
     Platform hint
     ------------------------------------------------------------------------ */

  const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform || '');
  $$('.search-kbd').forEach((hint) => {
    hint.textContent = isMac ? '⌘K' : 'Ctrl K';
  });

  /* ------------------------------------------------------------------------
     Boot
     ------------------------------------------------------------------------ */

  render();
  renderCalendar();
  renderTodos();
})();
