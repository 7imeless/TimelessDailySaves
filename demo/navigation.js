(() => {
  const menu = document.querySelector('.mobile-menu');
  if (!menu) return;
  const trigger = menu.querySelector('summary');
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menu.open) {
      menu.open = false;
      trigger.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!menu.contains(event.target)) menu.open = false;
    else if (event.target.closest('a')) menu.open = false;
  });
  document.addEventListener('focusin', (event) => {
    if (!menu.contains(event.target)) menu.open = false;
  });
  matchMedia('(min-width: 861px)').addEventListener('change', (event) => {
    if (event.matches) menu.open = false;
  });
})();
