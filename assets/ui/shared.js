(() => {
  'use strict';

  const root = document.documentElement;
  const themeKey = 'timeless-theme';
  const themeToggle = document.querySelector('[data-theme-toggle]');
  const themeColor = document.querySelector('meta[name="theme-color"]');
  const head = document.querySelector('[data-head]');
  const toTop = document.querySelector('[data-top]');
  const toast = document.querySelector('[data-toast]');

  const applyTheme = (theme, persist = true) => {
    root.dataset.theme = theme;
    if (themeColor) themeColor.setAttribute('content', theme === 'light' ? '#f2eee3' : '#080a09');
    if (themeToggle) {
      const next = theme === 'light' ? '夜航' : '日间';
      themeToggle.setAttribute('aria-label', `切换到${next}模式`);
      themeToggle.setAttribute('title', `切换到${next}模式`);
    }
    if (persist) {
      try { localStorage.setItem(themeKey, theme); } catch (_) { /* private mode */ }
    }
  };

  applyTheme(root.dataset.theme === 'light' ? 'light' : 'dark', false);
  themeToggle?.addEventListener('click', () => {
    applyTheme(root.dataset.theme === 'light' ? 'dark' : 'light');
  });

  let ticking = false;
  const updateScroll = () => {
    const y = window.scrollY;
    head?.classList.toggle('is-stuck', y > 24);
    toTop?.classList.toggle('is-on', y > 720);
    ticking = false;
  };
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(updateScroll);
  }, { passive: true });
  updateScroll();

  toTop?.addEventListener('click', () => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
  });

  let toastTimer = 0;
  const showToast = (message) => {
    if (!toast) return;
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('is-on');
    toastTimer = window.setTimeout(() => toast.classList.remove('is-on'), 2800);
  };
  window.TLToast = showToast;

  document.addEventListener('keydown', (event) => {
    if (event.key !== '/' || event.metaKey || event.ctrlKey || event.altKey || document.querySelector('dialog[open]')) return;
    const target = event.target instanceof Element ? event.target : null;
    const typing = Boolean(target && target.closest('input, textarea, select, [contenteditable="true"]'));
    if (typing) return;
    event.preventDefault();
    if (document.body.dataset.page === 'archive') {
      const input = document.querySelector('#archiveSearch');
      input?.focus();
      input?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      window.location.href = '/archive#search';
    }
  });

  document.querySelectorAll('.search-trigger').forEach((trigger) => {
    trigger.setAttribute('aria-label', '搜索文章');
  });
})();
