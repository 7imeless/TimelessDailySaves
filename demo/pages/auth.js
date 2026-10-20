(() => {
  'use strict';

  const tabs = Array.from(document.querySelectorAll('[data-auth-tab]'));
  const panes = Array.from(document.querySelectorAll('[data-auth-panel]'));
  const forms = Array.from(document.querySelectorAll('[data-auth-form]'));
  const tabsBar = document.querySelector('.auth-tabs');
  const success = document.querySelector('[data-auth-success]');
  const successTitle = document.querySelector('[data-success-title]');
  const successCopy = document.querySelector('[data-success-copy]');

  const setError = (input, message) => {
    const error = document.querySelector(`[data-error-for="${input.id}"]`);
    if (error) error.textContent = message;
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
  };

  const clearError = (input) => setError(input, '');

  const switchTab = (name, focus = false) => {
    if (success) success.hidden = true;
    if (tabsBar) tabsBar.hidden = false;
    tabs.forEach((tab) => {
      const active = tab.dataset.authTab === name;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panes.forEach((pane) => {
      const active = pane.dataset.authPanel === name;
      pane.hidden = !active;
    });
    forms.forEach((form) => {
      const button = form.querySelector('.auth-submit');
      if (button && button.dataset.label) {
        button.textContent = button.dataset.label;
        button.disabled = false;
      }
    });
    if (focus) {
      const pane = panes.find((item) => item.dataset.authPanel === name);
      pane?.querySelector('input')?.focus();
    }
    try {
      const nextHash = name === 'register' ? '#register' : '#login';
      window.history.replaceState({}, '', nextHash);
    } catch (_) { /* file:// */ }
  };

  const showSuccess = (mode) => {
    if (!success) return;
    if (tabsBar) tabsBar.hidden = true;
    panes.forEach((pane) => { pane.hidden = true; });
    success.hidden = false;
    success.setAttribute('tabindex', '-1');
    if (successTitle) successTitle.textContent = mode === 'register' ? '账号创建成功' : '登录成功';
    if (successCopy) {
      successCopy.textContent = mode === 'register'
        ? '演示通过。正式站点会创建账号、写入 timeless.db，并自动登录。'
        : '演示通过。正式站点会建立会话并跳转首页。';
    }
    success.focus({ preventScroll: true });
    window.TLToast?.(mode === 'register' ? '演示：注册表单校验通过。' : '演示：登录表单校验通过。');
  };

  const submitDemo = (form, mode) => {
    const button = form.querySelector('.auth-submit');
    if (!button) return;
    if (!button.dataset.label) button.dataset.label = button.textContent.trim();
    button.disabled = true;
    button.textContent = mode === 'register' ? '正在创建…' : '正在登录…';
    window.setTimeout(() => {
      button.disabled = false;
      showSuccess(mode);
    }, 700);
  };

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => switchTab(tab.dataset.authTab, true));
  });

  tabsBar?.addEventListener('keydown', (event) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    const current = tabs.findIndex((tab) => tab.getAttribute('aria-selected') === 'true');
    const next = (current + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    tabs[next].focus();
    switchTab(tabs[next].dataset.authTab);
  });

  document.querySelectorAll('[data-auth-switch]').forEach((button) => {
    button.addEventListener('click', () => switchTab(button.dataset.authSwitch, true));
  });

  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const input = button.closest('.password-wrap')?.querySelector('input');
      if (!input) return;
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.textContent = show ? '隐藏' : '显示';
      button.setAttribute('aria-label', show ? '隐藏密码' : '显示密码');
      input.focus();
    });
  });

  document.querySelectorAll('[data-auth-form] input').forEach((input) => {
    input.addEventListener('input', () => clearError(input));
  });

  const loginForm = document.querySelector('[data-auth-form="login"]');
  const registerForm = document.querySelector('[data-auth-form="register"]');

  loginForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    const username = loginForm.querySelector('#loginUser');
    const password = loginForm.querySelector('#loginPass');
    let first = null;

    if (!username.value.trim() || username.value.trim().length < 2) {
      setError(username, '请输入至少 2 个字符的用户名。');
      first ||= username;
    }
    if (password.value.length < 8) {
      setError(password, '密码至少需要 8 位。');
      first ||= password;
    }
    if (first) {
      first.focus();
      return;
    }
    submitDemo(loginForm, 'login');
  });

  registerForm?.addEventListener('submit', (event) => {
    event.preventDefault();
    const username = registerForm.querySelector('#regUser');
    const password = registerForm.querySelector('#regPass');
    const confirm = registerForm.querySelector('#regPass2');
    let first = null;

    if (!username.value.trim() || username.value.trim().length < 2) {
      setError(username, '请输入至少 2 个字符的用户名。');
      first ||= username;
    }
    if (password.value.length < 8) {
      setError(password, '密码至少需要 8 位。');
      first ||= password;
    }
    if (!confirm.value || confirm.value !== password.value) {
      setError(confirm, '两次输入的密码不一致。');
      first ||= confirm;
    }
    if (first) {
      first.focus();
      return;
    }
    submitDemo(registerForm, 'register');
  });

  document.querySelector('[data-auth-reset]')?.addEventListener('click', () => {
    forms.forEach((form) => {
      form.reset();
      form.querySelectorAll('input').forEach(clearError);
    });
    switchTab('login', true);
  });

  // Keep the tab state shareable / restorable.
  if (window.location.hash === '#register') switchTab('register');
  else switchTab('login');
})();
