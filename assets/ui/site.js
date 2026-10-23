(() => {
  'use strict';
  const dialog = document.querySelector('[data-search-dialog]');
  const input = dialog?.querySelector('[data-search-input]');
  const results = dialog?.querySelector('[data-search-results]');
  const hint = dialog?.querySelector('[data-search-hint]');
  let opener, timer, generation = 0;
  const close = () => { dialog?.close(); opener?.focus(); };
  const open = (trigger) => { if (!dialog) return; opener = trigger; dialog.showModal(); input.focus(); };
  document.querySelectorAll('[data-search-open]').forEach(button => button.addEventListener('click', () => open(button)));
  document.querySelector('[data-search-close]')?.addEventListener('click', close);
  dialog?.addEventListener('click', event => { if (event.target === dialog) close(); });
  dialog?.addEventListener('cancel', () => opener?.focus());
  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); open(document.activeElement); }
    if (dialog?.open && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
      const links = [...results.querySelectorAll('a')];
      if (!links.length) return;
      event.preventDefault();
      const index = links.indexOf(document.activeElement);
      links[(index + (event.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length].focus();
    }
  });
  input?.addEventListener('input', () => {
    clearTimeout(timer);
    const request = ++generation;
    timer = setTimeout(async () => {
      try {
        const r = await fetch(`/search?q=${encodeURIComponent(input.value.trim())}`);
        if (!r.ok) throw Error('搜索失败');
        const data = await r.json();
        if (request !== generation) return;
        const source = document.createElement('template'); source.innerHTML = data.cards;
        results.replaceChildren();
        source.content.querySelectorAll('.feature h3 a, .post-row-link').forEach(link => {
          const result = document.createElement('a'); result.className = 'search-result'; result.href = link.getAttribute('href');
          result.textContent = link.querySelector('.post-title')?.textContent || link.textContent;
          results.append(result);
        });
        hint.textContent = results.childElementCount ? `${results.childElementCount} 篇匹配文章` : '没有符合条件的文章。';
      } catch (_) { if (request === generation) hint.textContent = '搜索暂不可用，可按回车打开完整结果。'; }
    }, 200);
  });
  document.querySelectorAll('[data-password-toggle]').forEach(button => button.addEventListener('click', () => {
    const field = document.getElementById(button.dataset.passwordToggle);
    field.type = field.type === 'password' ? 'text' : 'password';
    button.textContent = field.type === 'password' ? '显示' : '隐藏';
    button.setAttribute('aria-label', `${button.textContent}密码`);
  }));
  const clock = document.querySelector('[data-clock]');
  if (clock) {
    const update = () => { clock.textContent = '青岛 · ' + new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date()); };
    update(); setInterval(update, 60000);
  }
})();
