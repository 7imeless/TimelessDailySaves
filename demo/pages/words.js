(() => {
  'use strict';

  const WORDS = window.TL_WORDS || [];
  const state = { index: 0, mode: 'meaning', revealed: false, reviewed: 0, ratings: [], answer: '' };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  const pad = (value) => String(value).padStart(2, '0');
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));

  const studyParts = [
    $('.study-head'),
    $('.session-bar'),
    $('.study-toolbar'),
    $('.study-prompt'),
    $('.study-form'),
    $('.study-hint')
  ].filter(Boolean);
  const complete = $('[data-complete]');
  const solution = $('[data-solution]');
  const wordEl = $('[data-word]');
  const phoneticEl = $('[data-phonetic]');
  const definitionEl = $('[data-definition]');
  const promptLabel = $('[data-prompt-label]');
  const answer = $('[data-answer]');
  const modeSelect = $('[data-mode]');
  const revealButton = $('[data-reveal]');
  const sessionCount = $('[data-session-count]');
  const sessionBar = $('[data-session-bar]');
  const solutionWord = $('[data-solution-word]');
  const solutionPhonetic = $('[data-solution-phonetic]');
  const solutionTranslation = $('[data-solution-translation]');
  const solutionDef = $('[data-solution-def]');
  const solutionResult = $('[data-solution-result]');
  const goalRing = $('[data-goal-ring]');
  const goalCount = $('[data-goal-count]');

  const current = () => WORDS[state.index];

  const updateStats = () => {
    const reviewed = state.reviewed;
    const total = WORDS.length;
    const set = (selector, value) => { const el = $(selector); if (el) el.textContent = value; };
    set('[data-stat-due]', String(Math.max(0, 12 - reviewed)));
    set('[data-stat-today]', pad(reviewed));
    set('[data-stat-learned]', String(128 + reviewed));
    set('[data-stat-total]', '5407');
    if (goalCount) goalCount.textContent = String(reviewed);
    if (goalRing) goalRing.style.setProperty('--p', `${total ? (reviewed / total) * 100 : 0}%`);
    if (sessionBar) sessionBar.style.width = `${total ? (Math.min(reviewed, total) / total) * 100 : 0}%`;
    if (sessionCount) sessionCount.textContent = state.index >= total ? 'COMPLETE' : `第 ${pad(state.index + 1)} / ${pad(total)} 个`;
  };

  const showComplete = () => {
    studyParts.forEach((part) => { part.hidden = true; });
    if (solution) solution.hidden = true;
    if (complete) complete.hidden = false;
    const remembered = state.ratings.filter((rating) => rating !== 'forgot').length;
    const set = (selector, value) => { const el = $(selector); if (el) el.textContent = value; };
    set('[data-complete-count]', String(state.reviewed));
    set('[data-complete-remembered]', String(remembered));
    set('[data-complete-time]', String(Math.max(1, Math.round(state.reviewed * 0.5))));
    updateStats();
  };

  const showStudy = () => {
    studyParts.forEach((part) => { part.hidden = false; });
    if (complete) complete.hidden = true;
  };

  const render = () => {
    if (!WORDS.length) return;
    if (state.index >= WORDS.length) {
      showComplete();
      return;
    }

    showStudy();
    const word = current();
    const isSpell = state.mode === 'spell';
    state.revealed = false;
    state.answer = '';

    if (modeSelect) modeSelect.value = state.mode;
    if (promptLabel) promptLabel.textContent = isSpell ? '根据释义，默写英文' : '这个词是什么意思？';
    if (wordEl) {
      wordEl.textContent = word.word;
      wordEl.hidden = isSpell;
    }
    if (phoneticEl) {
      phoneticEl.textContent = word.phonetic;
      phoneticEl.parentElement.hidden = isSpell;
    }
    if (definitionEl) {
      definitionEl.hidden = !isSpell;
      definitionEl.textContent = isSpell ? word.translation : '';
    }
    if (answer) {
      answer.value = '';
      answer.disabled = false;
      answer.placeholder = isSpell ? '默写英文单词' : '写下你回忆的词义（可选）';
    }
    if (modeSelect) modeSelect.disabled = false;
    if (revealButton) {
      revealButton.disabled = false;
      revealButton.textContent = '查看答案 ↵';
    }
    if (solution) solution.hidden = true;
    updateStats();
  };

  const reveal = () => {
    const word = current();
    if (!word || state.revealed) return;

    state.revealed = true;
    state.answer = answer?.value || '';

    if (solutionWord) solutionWord.textContent = word.word;
    if (solutionPhonetic) solutionPhonetic.textContent = word.phonetic;
    if (solutionTranslation) solutionTranslation.innerHTML = escapeHtml(word.translation).replace(/\n/g, '<br>');
    if (solutionDef) solutionDef.textContent = word.definition;
    if (solutionResult) {
      solutionResult.classList.remove('is-wrong');
      if (state.mode === 'spell') {
        const correct = state.answer.trim().toLowerCase() === word.word.toLowerCase();
        solutionResult.textContent = correct ? '拼写正确' : '拼写未匹配';
        solutionResult.classList.toggle('is-wrong', !correct);
      } else {
        solutionResult.textContent = '对照释义，判断是否回忆出来';
      }
    }

    if (answer) answer.disabled = true;
    if (modeSelect) modeSelect.disabled = true;
    if (revealButton) {
      revealButton.disabled = true;
      revealButton.textContent = '选择记忆程度';
    }
    if (solution) solution.hidden = false;
    solution?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
  };

  const rate = (value) => {
    if (!state.revealed) return;
    state.ratings.push(value);
    state.reviewed += 1;
    state.index += 1;
    const continueWithKeyboard = document.activeElement?.matches('[data-rate], [data-reveal]');
    render();
    if (continueWithKeyboard && state.index < WORDS.length) {
      answer?.focus({ preventScroll: true });
    }
  };

  document.querySelector('[data-study-form]')?.addEventListener('submit', (event) => {
    event.preventDefault();
    reveal();
  });

  document.querySelectorAll('[data-rate]').forEach((button) => {
    button.addEventListener('click', () => rate(button.dataset.rate));
  });

  modeSelect?.addEventListener('change', () => {
    state.mode = modeSelect.value;
    render();
  });

  const speak = () => {
    const word = current();
    if (!word) return;
    if (!('speechSynthesis' in window)) {
      window.TLToast?.('当前浏览器不支持语音朗读。');
      return;
    }
    window.speechSynthesis.cancel();
    const speech = new SpeechSynthesisUtterance(word.word);
    speech.lang = 'en-US';
    window.speechSynthesis.speak(speech);
  };
  document.querySelector('[data-speak]')?.addEventListener('click', speak);

  document.querySelector('[data-restart]')?.addEventListener('click', () => {
    state.index = 0;
    state.reviewed = 0;
    state.ratings = [];
    state.revealed = false;
    render();
  });

  document.addEventListener('keydown', (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const typing = Boolean(target && target.closest('input, textarea, select, [contenteditable="true"]'));
    if (typing) return;
    if (state.index >= WORDS.length) return;

    if (event.code === 'Space') {
      if (target?.closest('button, a')) return;
      if (!state.revealed) {
        event.preventDefault();
        reveal();
      }
      return;
    }
    if (state.revealed && ['1', '2', '3', '4'].includes(event.key)) {
      event.preventDefault();
      const map = { '1': 'forgot', '2': 'hard', '3': 'good', '4': 'easy' };
      rate(map[event.key]);
      return;
    }
    if (event.key.toLowerCase() === 's') {
      event.preventDefault();
      speak();
      return;
    }
    if (event.altKey && event.key.toLowerCase() === 'm') {
      event.preventDefault();
      state.mode = state.mode === 'meaning' ? 'spell' : 'meaning';
      if (modeSelect) modeSelect.value = state.mode;
      render();
    }
  });

  // Library -----------------------------------------------------------------

  const library = $('[data-library]');
  const libraryInput = $('[data-library-input]');
  const libraryEmpty = $('[data-library-empty]');

  const renderLibrary = (query = '') => {
    const term = query.trim().toLowerCase();
    const filtered = WORDS.filter((word) => {
      if (!term) return true;
      return [word.word, word.translation, word.definition, ...word.tags].join(' ').toLowerCase().includes(term);
    });
    if (library) {
      library.innerHTML = filtered.map((word) => `
        <article class="word-card">
          <div class="word-card-top"><strong>${escapeHtml(word.word)}</strong><small>${escapeHtml(word.phonetic)}</small></div>
          <p>${escapeHtml(word.translation.split('\n')[0])}</p>
          <div class="word-card-tags">${word.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join('')}</div>
        </article>
      `).join('');
    }
    if (libraryEmpty) libraryEmpty.hidden = filtered.length !== 0;
  };

  libraryInput?.addEventListener('input', () => renderLibrary(libraryInput.value));
  document.querySelector('[data-library-form]')?.addEventListener('submit', (event) => {
    event.preventDefault();
    renderLibrary(libraryInput?.value || '');
  });

  render();
  renderLibrary();
})();
