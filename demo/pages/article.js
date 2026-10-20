(() => {
  'use strict';

  const bar = document.querySelector('[data-progress-bar]');
  const ring = document.querySelector('[data-progress-ring]');
  const label = document.querySelector('[data-progress-label]');
  const headings = Array.from(document.querySelectorAll('.prose h2[id]'));
  const tocLinks = Array.from(document.querySelectorAll('[data-toc] a, .toc-mobile a'));
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const setActiveToc = () => {
    let activeId = headings.length ? headings[0].id : '';
    headings.forEach((heading) => {
      if (heading.getBoundingClientRect().top <= 150) activeId = heading.id;
    });
    tocLinks.forEach((link) => {
      link.classList.toggle('is-active', link.getAttribute('href') === `#${activeId}`);
    });
  };

  let ticking = false;
  const update = () => {
    const doc = document.documentElement;
    const distance = doc.scrollHeight - window.innerHeight;
    const progress = distance > 0 ? Math.min(Math.max(window.scrollY / distance, 0), 1) : 1;
    if (bar) bar.style.transform = `scaleX(${progress})`;
    if (ring) ring.style.setProperty('--p', `${(progress * 100).toFixed(1)}%`);
    if (label) label.textContent = `${Math.round(progress * 100)}%`;
    setActiveToc();
    ticking = false;
  };

  const schedule = () => {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(update);
  };

  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  update();

  document.querySelectorAll('.toc-mobile a').forEach((link) => {
    link.addEventListener('click', () => {
      const details = link.closest('.toc-mobile');
      if (details) details.open = false;
    });
  });

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      const area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
  };

  document.querySelectorAll('[data-copy]').forEach((button) => {
    button.addEventListener('click', async () => {
      const target = document.querySelector(button.dataset.copy);
      if (!target) return;
      await copyText(target.textContent);
      button.textContent = '已复制';
      window.TLToast?.('代码已复制到剪贴板。');
      window.setTimeout(() => { button.textContent = '复制'; }, 1800);
    });
  });

  document.querySelectorAll('[data-copy-link]').forEach((button) => {
    button.addEventListener('click', async () => {
      await copyText(window.location.href);
      window.TLToast?.('文章链接已复制。');
    });
  });

  // If the page is opened directly at an anchor, leave a little room under the header.
  if (window.location.hash) {
    window.setTimeout(() => {
      const target = document.querySelector(window.location.hash);
      if (target) {
        target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
      }
    }, 80);
  }
})();
