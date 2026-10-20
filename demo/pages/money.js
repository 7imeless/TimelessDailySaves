(() => {
  'use strict';

  const CATEGORIES = window.TL_CATEGORIES || { expense: [], income: [] };
  const entries = (window.TL_MONEY || []).map((entry) => ({ ...entry }));
  const state = { month: '2026-10', type: 'expense', categoryFilter: 'all', editId: null };

  const $ = (selector) => document.querySelector(selector);
  const pad = (value) => String(value).padStart(2, '0');
  const formatMoney = (cents) => `¥${new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(cents / 100)}`;
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));

  const elements = {
    monthLabel: $('[data-month-label]'),
    monthCaption: $('[data-month-caption]'),
    income: $('[data-income]'),
    expense: $('[data-expense]'),
    balance: $('[data-balance]'),
    incomeNote: $('[data-income-note]'),
    expenseNote: $('[data-expense-note]'),
    entryCount: $('[data-entry-count]'),
    ledger: $('[data-ledger]'),
    ledgerEmpty: $('[data-ledger-empty]'),
    filterCount: $('[data-filter-count]'),
    categoryFilter: $('[data-category-filter]'),
    breakdown: $('[data-breakdown]'),
    breakdownTotal: $('[data-breakdown-total]'),
    breakdownEmpty: $('[data-breakdown-empty]'),
    amount: $('[data-amount]'),
    amountError: $('[data-money-error]'),
    note: $('[data-note]'),
    date: $('[data-date]'),
    formCategory: $('[data-form-category]'),
    submit: $('[data-submit]'),
    form: $('[data-money-form]')
  };

  const monthEntries = () => entries.filter((entry) => entry.date.slice(0, 7) === state.month);
  const sum = (list) => list.reduce((total, entry) => total + entry.amount, 0);

  const monthLabel = () => {
    const [year, month] = state.month.split('-');
    return `${year} 年 ${Number(month)} 月`;
  };

  const setType = (type) => {
    state.type = type;
    document.querySelectorAll('[data-type]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.type === type));
    });
    renderFormCategories();
    if (elements.submit) elements.submit.textContent = state.editId ? '保存修改' : (type === 'expense' ? '保存支出' : '保存收入');
  };

  const renderFormCategories = () => {
    if (!elements.formCategory) return;
    const list = CATEGORIES[state.type] || [];
    const previous = elements.formCategory.value;
    elements.formCategory.innerHTML = list.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join('');
    if (list.includes(previous)) elements.formCategory.value = previous;
  };

  const renderSummary = () => {
    const list = monthEntries();
    const incomes = list.filter((entry) => entry.type === 'income');
    const expenses = list.filter((entry) => entry.type === 'expense');
    const income = sum(incomes);
    const expense = sum(expenses);
    if (elements.income) elements.income.textContent = formatMoney(income);
    if (elements.expense) elements.expense.textContent = formatMoney(expense);
    if (elements.balance) elements.balance.textContent = formatMoney(income - expense);
    if (elements.incomeNote) elements.incomeNote.textContent = `${incomes.length} 笔收入`;
    if (elements.expenseNote) elements.expenseNote.textContent = `${expenses.length} 笔支出`;
    if (elements.entryCount) elements.entryCount.textContent = `共 ${list.length} 笔记录`;
  };

  const renderCategoryFilter = () => {
    if (!elements.categoryFilter) return;
    const list = monthEntries();
    const categories = [...new Set(list.map((entry) => entry.category))].sort((a, b) => a.localeCompare(b));
    if (!categories.includes(state.categoryFilter)) state.categoryFilter = 'all';
    elements.categoryFilter.innerHTML = ['<option value="all">全部分类</option>']
      .concat(categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`))
      .join('');
    elements.categoryFilter.value = state.categoryFilter;
  };

  const renderTable = () => {
    if (!elements.ledger) return;
    const monthList = monthEntries();
    const visible = monthList
      .filter((entry) => state.categoryFilter === 'all' || entry.category === state.categoryFilter)
      .sort((a, b) => b.date.localeCompare(a.date));

    if (elements.filterCount) elements.filterCount.textContent = `${visible.length} 笔`;
    elements.ledger.innerHTML = visible.map((entry) => {
      const income = entry.type === 'income';
      return `
        <div class="ledger-row" data-entry-id="${entry.id}">
          <time class="ledger-date" datetime="${entry.date}">${entry.date.slice(5).replace('-', '.')}</time>
          <span class="ledger-cat">${escapeHtml(entry.category)}</span>
          <span class="ledger-note" title="${escapeHtml(entry.note || '')}">${escapeHtml(entry.note || '—')}</span>
          <span class="ledger-amount${income ? ' is-income' : ''}">${income ? '+' : '−'}${formatMoney(entry.amount)}</span>
          <div class="ledger-actions"><button class="ledger-action" type="button" data-edit aria-label="编辑 ${escapeHtml(entry.note || entry.category)}">编辑</button><button class="ledger-action" type="button" data-delete aria-label="删除 ${escapeHtml(entry.note || entry.category)}">删除</button></div>
        </div>
      `;
    }).join('');

    if (elements.ledgerEmpty) {
      elements.ledgerEmpty.hidden = visible.length !== 0;
      elements.ledgerEmpty.innerHTML = monthList.length
        ? '<span class="empty-mark" aria-hidden="true">∅</span>这个分类下还没有记录。'
        : '<span class="empty-mark" aria-hidden="true">∅</span>这个月还没有记录。<br>从右边记下第一笔。';
    }
  };

  const renderBreakdown = () => {
    const expenses = monthEntries().filter((entry) => entry.type === 'expense');
    const total = sum(expenses);
    const groups = new Map();
    expenses.forEach((entry) => {
      groups.set(entry.category, (groups.get(entry.category) || 0) + entry.amount);
    });
    const sorted = [...groups.entries()].sort((a, b) => b[1] - a[1]);
    if (elements.breakdownTotal) elements.breakdownTotal.textContent = formatMoney(total);
    if (elements.breakdownEmpty) elements.breakdownEmpty.hidden = sorted.length !== 0;
    if (!elements.breakdown) return;
    elements.breakdown.innerHTML = sorted.map(([category, amount]) => {
      const percent = total ? Math.round((amount / total) * 100) : 0;
      return `
        <div class="bar-row">
          <div class="bar-top"><span>${escapeHtml(category)}</span><span>${formatMoney(amount)} · ${percent}%</span></div>
          <div class="bar-track"><span style="width:${percent}%"></span></div>
        </div>
      `;
    }).join('');
  };

  const renderMonth = () => {
    if (elements.monthLabel) elements.monthLabel.textContent = monthLabel();
    if (elements.monthCaption) elements.monthCaption.textContent = state.month.replace('-', ' / ');
  };

  const render = () => {
    renderMonth();
    renderSummary();
    renderCategoryFilter();
    renderTable();
    renderBreakdown();
  };

  const setMonth = (month) => {
    state.month = month;
    state.categoryFilter = 'all';
    if (elements.date && !state.editId) elements.date.value = `${month}-01`;
    render();
  };

  const shiftMonth = (delta) => {
    const [year, month] = state.month.split('-').map(Number);
    const next = new Date(year, month - 1 + delta, 1);
    setMonth(`${next.getFullYear()}-${pad(next.getMonth() + 1)}`);
  };

  $('[data-month-prev]')?.addEventListener('click', () => shiftMonth(-1));
  $('[data-month-next]')?.addEventListener('click', () => shiftMonth(1));

  document.querySelectorAll('[data-type]').forEach((button) => {
    button.addEventListener('click', () => setType(button.dataset.type));
  });

  elements.formCategory?.addEventListener('change', () => { /* keep the selected category */ });

  elements.categoryFilter?.addEventListener('change', () => {
    state.categoryFilter = elements.categoryFilter.value;
    renderTable();
  });

  const resetEdit = () => {
    state.editId = null;
    $('[data-form-title]').textContent = '记一笔';
    $('[data-edit-cancel]').hidden = true;
    elements.amount.value = '';
    elements.note.value = '';
    elements.amountError.textContent = '';
    elements.amount.removeAttribute('aria-invalid');
    setType(state.type);
  };
  $('[data-edit-cancel]')?.addEventListener('click', resetEdit);

  elements.form?.addEventListener('submit', (event) => {
    event.preventDefault();
    const amountText = (elements.amount?.value || '').replace(/,/g, '').trim();
    const amount = Number(amountText);
    if (!/^\d+(?:\.\d{1,2})?$/.test(amountText) || !Number.isFinite(amount) || amount <= 0 || amount >= 100000000) {
      if (elements.amountError) elements.amountError.textContent = '请输入大于 0 且小于 1 亿元的金额，最多两位小数。';
      elements.amount?.setAttribute('aria-invalid', 'true');
      elements.amount?.focus();
      return;
    }
    if (!elements.date?.value) {
      if (elements.amountError) elements.amountError.textContent = '请选择日期。';
      elements.date?.focus();
      return;
    }
    if (elements.amountError) elements.amountError.textContent = '';
    elements.amount?.removeAttribute('aria-invalid');

    const cents = Math.round(amount * 100);
    const entry = {
      id: state.editId || `m-${crypto.randomUUID()}`,
      date: elements.date.value,
      type: state.type,
      category: elements.formCategory?.value || (state.type === 'expense' ? '其他' : '其他'),
      amount: cents,
      note: (elements.note?.value || '').trim().slice(0, 300)
    };
    const editing = Boolean(state.editId);
    if (editing) entries[entries.findIndex((item) => item.id === state.editId)] = entry;
    else entries.push(entry);

    if (entry.date.slice(0, 7) !== state.month) {
      state.month = entry.date.slice(0, 7);
      state.categoryFilter = 'all';
    }
    state.categoryFilter = 'all';
    resetEdit();
    render();
    window.TLToast?.(`${editing ? '已修改' : '已记一笔'}：${entry.category} ${formatMoney(entry.amount)}（演示）`);
    elements.amount?.focus({ preventScroll: true });
  });

  elements.amount?.addEventListener('input', () => {
    if (elements.amountError) elements.amountError.textContent = '';
    elements.amount?.removeAttribute('aria-invalid');
  });

  elements.ledger?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-delete], [data-edit]');
    if (!button) return;
    const row = button.closest('[data-entry-id]');
    if (!row) return;
    const index = entries.findIndex((entry) => entry.id === row.dataset.entryId);
    if (index === -1) return;
    if (button.hasAttribute('data-edit')) {
      const entry = entries[index];
      state.editId = entry.id;
      setType(entry.type);
      elements.formCategory.value = entry.category;
      elements.amount.value = (entry.amount / 100).toFixed(2);
      elements.date.value = entry.date;
      elements.note.value = entry.note || '';
      elements.amountError.textContent = '';
      elements.amount.removeAttribute('aria-invalid');
      $('[data-form-title]').textContent = '编辑记录';
      $('[data-edit-cancel]').hidden = false;
      $('#moneyForm').scrollIntoView({ block: 'start' });
      elements.amount.focus({ preventScroll: true });
      return;
    }
    if (!window.confirm('删除这笔演示记录？')) return;
    const [removed] = entries.splice(index, 1);
    if (state.editId === removed.id) resetEdit();
    render();
    window.TLToast?.(`已删除：${removed.category} ${formatMoney(removed.amount)}（演示）`);
  });

  const csvCell = (value) => {
    let text = String(value ?? '');
    if (/^[=+\-@]/.test(text)) text = `'${text}`;
    if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
    return text;
  };

  $('[data-export]')?.addEventListener('click', () => {
    const list = monthEntries().slice().sort((a, b) => a.date.localeCompare(b.date));
    const header = ['日期', '类型', '分类', '金额', '备注'];
    const rows = list.map((entry) => [
      entry.date,
      entry.type === 'income' ? '收入' : '支出',
      entry.category,
      (entry.amount / 100).toFixed(2),
      entry.note
    ]);
    const csv = '\ufeff' + [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `timeless-money-${state.month}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    window.TLToast?.(`已导出 ${state.month} 的 ${list.length} 笔记录（演示）。`);
  });

  setType('expense');
  if (elements.date) elements.date.value = '2026-10-19';
  render();
})();
