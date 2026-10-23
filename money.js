(() => {
  const fab = document.querySelector('.money-fab');
  const entryForm = document.getElementById('entry-form');
  if (fab && entryForm && 'IntersectionObserver' in window) new IntersectionObserver(([entry]) => { fab.classList.toggle('is-visible', !entry.isIntersecting); }, {rootMargin:'-84px 0px 0px 0px'}).observe(entryForm);
  const kind = document.getElementById('money-kind');
  const category = document.getElementById('money-category');
  if (!kind || !category) return;
  const update = () => {
    for (const option of category.options) {
      option.hidden = option.dataset.kind !== kind.value;
      option.disabled = option.hidden;
    }
    if (!category.selectedOptions.length || category.selectedOptions[0].disabled) {
      category.value = [...category.options].find((option) => !option.disabled).value;
    }
  };
  kind.addEventListener('change', update);
  update();
  document.querySelector('.money-form')?.addEventListener('submit', (event) => {
    event.target.querySelector('button[type="submit"]').disabled = true;
  });
})();
