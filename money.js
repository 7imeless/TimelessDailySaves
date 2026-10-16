(() => {
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
