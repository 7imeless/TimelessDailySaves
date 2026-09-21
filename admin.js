(() => {
  const form = document.querySelector('.admin-form');
  if (!form) return;

  const csrf = form.querySelector('input[name="csrf"]').value;
  const maxSize = 8 * 1024 * 1024;

  const setStatus = (element, message, state = '') => {
    element.className = `image-upload-status${state ? ` is-${state}` : ''}`;
    element.textContent = message;
  };

  const uploadImage = async (file, status) => {
    if (file.size > maxSize) throw new Error('图片不能超过 8 MB');
    setStatus(status, '正在上传...');
    const response = await fetch('/admin/upload-image', {
      method: 'POST',
      headers: { 'Content-Type': file.type, 'X-CSRF-Token': csrf },
      body: file,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '上传失败');
    return result.url;
  };

  const bodyPicker = document.getElementById('article-image');
  const bodyButton = document.getElementById('image-upload-button');
  const bodyStatus = document.getElementById('image-upload-status');
  const content = document.getElementById('article-content');
  const preview = document.getElementById('article-preview');
  let previewTimer;
  const updatePreview = async () => {
    if (!preview) return;
    try {
      const response = await fetch('/admin/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'X-Requested-With': 'fetch' },
        body: new URLSearchParams({ csrf, content: content.value }),
      });
      if (!response.ok) throw new Error('preview failed');
      preview.innerHTML = (await response.json()).html || '<p class="empty-state">开始输入 Markdown...</p>';
    } catch (_) {
      preview.innerHTML = '<p class="empty-state">预览暂时不可用，保存后仍会正常渲染。</p>';
    }
  };
  const schedulePreview = () => { clearTimeout(previewTimer); previewTimer = setTimeout(updatePreview, 250); };
  if (content && preview) { content.addEventListener('input', schedulePreview); updatePreview(); }

  bodyButton.addEventListener('click', () => bodyPicker.click());
  bodyPicker.addEventListener('change', async () => {
    const file = bodyPicker.files[0];
    if (!file) return;
    bodyButton.disabled = true;
    try {
      const url = await uploadImage(file, bodyStatus);
      const alt = file.name.replace(/[.][^.]+$/, '').replaceAll('[', '').replaceAll(']', '') || '文章图片';
      const markdown = `![${alt}](${url})`;
      const start = content.selectionStart;
      const end = content.selectionEnd;
      const before = content.value.slice(0, start);
      const after = content.value.slice(end);
      const prefix = before && !before.endsWith('\n') ? '\n\n' : '';
      const suffix = after && !after.startsWith('\n') ? '\n\n' : '';
      content.value = before + prefix + markdown + suffix + after;
      const cursor = (before + prefix + markdown).length;
      content.focus();
      content.setSelectionRange(cursor, cursor);
      setStatus(bodyStatus, '图片已插入正文', 'success');
    } catch (error) {
      setStatus(bodyStatus, error.message, 'error');
    } finally {
      bodyButton.disabled = false;
      bodyPicker.value = '';
    }
  });

  const coverPicker = document.getElementById('cover-image-input');
  const coverButton = document.getElementById('cover-upload-button');
  const coverRemove = document.getElementById('cover-remove-button');
  const coverStatus = document.getElementById('cover-upload-status');
  const coverUrl = document.getElementById('cover-image-url');
  const coverPreview = document.getElementById('cover-preview');
  const coverImage = coverPreview.querySelector('img');

  coverButton.addEventListener('click', () => coverPicker.click());
  coverPicker.addEventListener('change', async () => {
    const file = coverPicker.files[0];
    if (!file) return;
    coverButton.disabled = true;
    try {
      const url = await uploadImage(file, coverStatus);
      coverUrl.value = url;
      coverImage.src = url;
      coverPreview.hidden = false;
      coverRemove.hidden = false;
      setStatus(coverStatus, '封面已上传，保存文章后生效', 'success');
    } catch (error) {
      setStatus(coverStatus, error.message, 'error');
    } finally {
      coverButton.disabled = false;
      coverPicker.value = '';
    }
  });

  coverRemove.addEventListener('click', () => {
    coverUrl.value = '';
    coverImage.removeAttribute('src');
    coverPreview.hidden = true;
    coverRemove.hidden = true;
    setStatus(coverStatus, '封面将在保存后移除');
  });
})();
