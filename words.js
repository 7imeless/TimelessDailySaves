(() => {
  const root = document.querySelector('.words-shell');
  if (!root) return;
  const csrf = root.dataset.csrf;
  const loggedIn = root.dataset.loggedIn === 'true';
  const $ = (id) => document.getElementById(id);
  let cards = [], index = 0, current = null, revealed = false, busy = false, requestId = '', total = 0, submittedAnswer = '';

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const renderStats = (stats = {}) => { $('words-stats').innerHTML = [['待复习', stats.due || 0], ['今日复习', stats.reviews_today || 0], ['已学习', stats.learned || 0], ['词库', stats.total || 0]].map(([label, value]) => `<div class="stat-card"><strong>${value}</strong><span>${label}</span></div>`).join(''); };
  const renderPrompt = () => {
    current = cards[index] || null;
    $('study-solution').hidden = true;
    $('study-mode').disabled = false;
    $('study-answer').disabled = false;
    $('reveal').textContent = '查看答案 ↵';
    $('study-message').textContent = '';
    document.querySelectorAll('[data-rating]').forEach((b) => { b.disabled = false; });
    if (!current) { $('study-progress').textContent = `已完成 ${total} 个`; if ($('session-bar')) $('session-bar').style.width = '100%'; $('study-prompt').innerHTML = '<p class="words-empty">这一批已经完成。休息一下，或加载下一批。</p>'; $('study-form').hidden = true; $('study-restart').hidden = false; return; }
    $('study-form').hidden = false; $('study-restart').hidden = true; revealed = false; requestId = crypto.randomUUID();
    $('study-progress').textContent = `第 ${index + 1} / ${total} 个`;
    const mode = $('study-mode').value;
    $('study-prompt').innerHTML = mode === 'spell' ? `<p class="study-definition">${escapeHtml(current.translation).replace(/\n/g, '<br>')}</p>` : `<h3 class="study-word">${escapeHtml(current.word)}</h3><p class="study-phonetic">${escapeHtml(current.phonetic || '')}</p>`;
    $('answer-label').textContent = mode === 'spell' ? '默写英文单词' : '写下你回忆的词义（可选）'; $('study-answer').value = ''; $('study-answer').placeholder = $('answer-label').textContent;
    const bar = $('session-bar'); if (bar) bar.style.width = `${total ? index / total * 100 : 0}%`;
  };
  const loadToday = async () => { const r = await fetch('/words/api/today'); const data = await r.json(); if (!r.ok) throw Error(data.error); cards = data.words || []; total = cards.length; index = 0; renderStats(data.stats); renderPrompt(); };
  const reveal = () => {
    if (!current || revealed) return;
    revealed = true; submittedAnswer = $('study-answer').value;
    const mode = $('study-mode').value;
    $('study-mode').disabled = true; $('study-answer').disabled = true;
    $('solution-word').textContent = current.word;
    $('solution-phonetic').textContent = current.phonetic || '';
    $('solution-translation').innerHTML = escapeHtml(current.translation).replace(/\n/g, '<br>');
    $('solution-definition').innerHTML = escapeHtml(current.definition || '').replace(/\n/g, '<br>');
    $('study-result').textContent = mode === 'spell' ? (submittedAnswer.trim().toLowerCase() === current.word.toLowerCase() ? '拼写正确' : '拼写未匹配，按“忘了”记录') : '对照释义，判断自己是否回忆出来';
    $('study-solution').hidden = false; $('reveal').textContent = '选择记忆程度'; $('study-solution').scrollIntoView({block:'nearest', behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
  };
  $('study-form').addEventListener('submit', (event) => { event.preventDefault(); reveal(); });
  $('study-mode').addEventListener('change', renderPrompt);
  $('reveal').addEventListener('click', () => { if (revealed) return; });
  $('study-solution').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-rating]');
    if (!button || !current || !revealed || busy) return;
    busy = true;
    document.querySelectorAll('[data-rating]').forEach((b) => { b.disabled = true; });
    try {
      if (loggedIn) {
        const form = new URLSearchParams({csrf, word: current.word, rating: button.dataset.rating, mode: $('study-mode').value, answer: submittedAnswer, request_id: requestId});
        const r = await fetch('/words/api/review', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:form});
        const result = await r.json();
        if (!r.ok) throw Error(result.error);
      }
      index++; renderPrompt();
      if (loggedIn) fetch('/words/api/today').then((r) => r.json()).then((d) => renderStats(d.stats)).catch(() => {});
    } catch (error) {
      $('study-message').textContent = `${error.message}；可以重试，记录不会重复保存。`;
      document.querySelectorAll('[data-rating]').forEach((b) => { b.disabled = false; });
    } finally { busy = false; }
  });
  $('speak').addEventListener('click', () => { if ('speechSynthesis' in window && current) { speechSynthesis.cancel(); const speech = new SpeechSynthesisUtterance(current.word); speech.lang = 'en-US'; speechSynthesis.speak(speech); } else { $('study-message').textContent = '当前浏览器不支持语音朗读。'; } });
  $('study-restart').addEventListener('click', () => loadToday().catch((e) => { $('study-message').textContent = e.message; }));
  let libraryPage = 1;
  const loadLibrary = async () => { const q = encodeURIComponent($('library-query').value.trim()); const r = await fetch(`/words/api/library?q=${q}&page=${libraryPage}`); const data = await r.json(); $('library-count').textContent = `${data.total || 0} 条结果`; $('library-list').innerHTML = (data.words || []).map((word) => `<article class="word-card"><div><strong>${escapeHtml(word.word)}</strong><span>${escapeHtml(word.phonetic || '')}</span></div><p>${escapeHtml(word.translation).replace(/\n/g, '<br>')}</p></article>`).join('') || '<p class="words-empty">没有找到相关词条。</p>'; $('library-prev').disabled = libraryPage <= 1; $('library-next').disabled = libraryPage * 30 >= data.total; };
  $('library-search').addEventListener('submit', (e) => { e.preventDefault(); libraryPage = 1; loadLibrary(); }); $('library-prev').addEventListener('click', () => { libraryPage--; loadLibrary(); }); $('library-next').addEventListener('click', () => { libraryPage++; loadLibrary(); });
  document.addEventListener('keydown', (event) => { if (event.target.matches('input,textarea,select') || event.ctrlKey || event.metaKey || event.altKey || document.querySelector('dialog[open]')) return; if (event.key.toLowerCase() === 's') $('speak').click(); if (event.code === 'Space') { event.preventDefault(); reveal(); } if (['1','2','3','4'].includes(event.key) && revealed) document.querySelector(`[data-rating="${event.key}"]`)?.click(); });
  loadToday().catch((error) => { $('study-message').textContent = error.message; }); loadLibrary();
})();
