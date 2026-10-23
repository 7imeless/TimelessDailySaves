(() => {
  'use strict';

  const POSTS = (window.TL_POSTS || []).slice().sort((a, b) => b.date.localeCompare(a.date));
  const state = { q: new URLSearchParams(location.search).get('q') || '', category: 'all', tag: new URLSearchParams(location.search).get('tag'), year: 'all' };

  const timeline = document.querySelector('[data-timeline]');
  const empty = document.querySelector('[data-empty]');
  const searchInput = document.querySelector('[data-search]');
  const resultLabel = document.querySelector('[data-result-label]');
  const totalCount = document.querySelector('[data-total-count]');
  const totalMinutes = document.querySelector('[data-total-minutes]');
  const categoryCount = document.querySelector('[data-category-count]');
  const totalPadded = document.querySelector('[data-total-padded]');
  const categoryChips = document.querySelector('[data-category-chips]');
  const yearChips = document.querySelector('[data-year-chips]');
  const tagChips = document.querySelector('[data-tag-chips]');

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
  const pad = (value) => String(value).padStart(2, '0');
  const uniq = (values) => [...new Set(values)];

  const categoryMap = new Map();
  const tagMap = new Map();
  POSTS.forEach((post) => {
    categoryMap.set(post.category, (categoryMap.get(post.category) || 0) + 1);
    post.tags.forEach((tag) => tagMap.set(tag, (tagMap.get(tag) || 0) + 1));
  });
  const years = uniq(POSTS.map((post) => post.date.slice(0, 4))).sort().reverse();
  const tags = [...tagMap.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const CATEGORY_ORDER = ['工程实践', '前端', '读书', '随笔', '工具'];
  const categories = [...categoryMap.entries()].sort((a, b) => {
    const ai = CATEGORY_ORDER.indexOf(a[0]);
    const bi = CATEGORY_ORDER.indexOf(b[0]);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi) || a[0].localeCompare(b[0]);
  });

  const categoryCountAll = categoryMap.size;
  totalCount.textContent = pad(POSTS.length);
  totalPadded.textContent = pad(POSTS.length);
  totalMinutes.textContent = POSTS.reduce((sum, post) => sum + post.minutes, 0);
  categoryCount.textContent = pad(categoryCountAll);

  const matches = (post) => {
    if (state.category !== 'all' && post.category !== state.category) return false;
    if (state.year !== 'all' && !post.date.startsWith(state.year)) return false;
    if (state.tag && !post.tags.includes(state.tag)) return false;
    if (state.q) {
      const haystack = [post.title, post.excerpt, post.category, ...post.tags].join(' ').toLowerCase();
      if (!haystack.includes(state.q.toLowerCase())) return false;
    }
    return true;
  };

  const chip = (label, value, active, count, type) => `
    <button class="chip${active ? ' is-active' : ''}" type="button" data-${type}="${escapeHtml(value)}" aria-pressed="${active}">
      ${escapeHtml(label)}${count != null ? `<b>${pad(count)}</b>` : ''}
    </button>`;

  const renderChips = () => {
    categoryChips.innerHTML = [
      chip('全部', 'all', state.category === 'all', POSTS.length, 'category'),
      categories.map(([name, count]) => (
        chip(name, name, state.category === name, count, 'category')
      )).join('')
    ].join('');

    yearChips.innerHTML = [
      chip('全部年份', 'all', state.year === 'all', null, 'year'),
      years.map((year) => chip(year, year, state.year === year, POSTS.filter((post) => post.date.startsWith(year)).length, 'year')).join('')
    ].join('');

    tagChips.innerHTML = [
      chip('全部标签', 'all', !state.tag, null, 'tag'),
      tags.map(([name, count]) => chip(`#${name}`, name, state.tag === name, count, 'tag')).join('')
    ].join('');
  };

  const render = () => {
    const visible = POSTS.filter(matches);
    resultLabel.textContent = `${pad(visible.length)} / ${pad(POSTS.length)}`;
    empty.hidden = visible.length !== 0;

    if (!visible.length) {
      timeline.innerHTML = '';
      renderChips();
      return;
    }

    const parts = [];
    let currentYear = '';
    let currentMonth = '';
    let yearCount = 0;
    let monthCount = 0;
    let monthOpen = false;

    const closeMonth = () => {
      if (monthOpen) {
        parts.push('</div>');
        monthOpen = false;
      }
    };
    const closeYear = () => {
      closeMonth();
      if (currentYear) {
        parts.push(`</section>`);
      }
    };

    visible.forEach((post, index) => {
      const year = post.date.slice(0, 4);
      const month = post.date.slice(5, 7);
      if (year !== currentYear) {
        closeYear();
        currentYear = year;
        currentMonth = '';
        yearCount = visible.filter((item) => item.date.startsWith(year)).length;
        parts.push(`
          <section class="year-block" data-year="${year}">
            <header class="year-head"><h2 aria-label="${year} 年">${year}</h2><span>${pad(yearCount)} 篇</span></header>
        `);
      }
      if (month !== currentMonth) {
        closeMonth();
        currentMonth = month;
        monthCount = visible.filter((item) => item.date.startsWith(`${year}-${month}`)).length;
        parts.push(`
          <div class="month-block">
            <div class="month-head"><strong>${Number(month)} 月</strong><span>${pad(monthCount)} ENTRIES</span></div>
        `);
        monthOpen = true;
      }

      const href = post.url;
      const tagLine = post.tags.slice(0, 2).map((tag) => `#${escapeHtml(tag)}`).join(' ');
      parts.push(`
        <a class="archive-row" href="${href}" data-post-id="${post.id}" style="--i:${index}">
          <time class="archive-date" datetime="${post.date}">${post.date.replaceAll('-', '.')}</time>
          <div class="archive-row-main">
            <h3>${escapeHtml(post.title)}</h3>
            <p>${escapeHtml(post.excerpt)}</p>
            <div class="archive-row-meta">
              <span class="archive-cat">${escapeHtml(post.category)}</span>
              <span class="archive-tags">${tagLine}</span>
            </div>
          </div>
          <div class="archive-row-aside">
            <span>${post.minutes} MIN</span>
            <span>READ</span>
          </div>
          <span class="archive-row-arrow" aria-hidden="true">↗</span>
        </a>
      `);
    });

    closeYear();
    timeline.innerHTML = parts.join('');
    renderChips();
  };

  const bindChips = () => {
    categoryChips.addEventListener('click', (event) => {
      const button = event.target.closest('[data-category]');
      if (!button) return;
      state.category = button.dataset.category;
      render();
    });
    yearChips.addEventListener('click', (event) => {
      const button = event.target.closest('[data-year]');
      if (!button) return;
      state.year = button.dataset.year;
      render();
    });
    tagChips.addEventListener('click', (event) => {
      const button = event.target.closest('[data-tag]');
      if (!button) return;
      const tag = button.dataset.tag;
      state.tag = tag === 'all' || state.tag === tag ? null : tag;
      render();
    });
  };

  const reset = () => {
    state.q = '';
    state.category = 'all';
    state.tag = null;
    state.year = 'all';
    if (searchInput) searchInput.value = '';
    render();
  };

  searchInput?.addEventListener('input', () => {
    state.q = searchInput.value.trim();
    render();
  });
  document.querySelector('[data-search-form]')?.addEventListener('submit', (event) => {
    event.preventDefault();
    state.q = searchInput.value.trim();
    render();
  });
  document.querySelectorAll('[data-reset]').forEach((button) => {
    button.addEventListener('click', reset);
  });

  if (searchInput) searchInput.value = state.q;
  bindChips();
  renderChips();
  render();

  if (window.location.hash === '#search') {
    window.setTimeout(() => searchInput?.focus({ preventScroll: true }), 350);
  }
})();
