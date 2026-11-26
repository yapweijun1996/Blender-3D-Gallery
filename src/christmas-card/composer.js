import { codePointCount, encodeGreeting, greetingLimits, limitGreeting, passwordLimit } from './greeting-link.js';

const copy = {
  en: {
    write: 'Write a card', title: 'Write a Christmas card', close: 'Close',
    privacy: 'Anyone with the full link can open this card unless you set a password.',
    to: 'To', msg: 'Message', from: 'From (optional)', preview: 'Preview',
    password: 'Password (optional)', passwordHelp: 'Send the password separately. A forgotten password cannot be recovered.',
    copy: 'Copy link', whatsapp: 'Share on WhatsApp', share: 'Share link',
    link: 'Card link', copied: 'Link copied.', manual: 'Select and copy this link.',
    limit: 'The text was trimmed to fit the card.', lines: 'lines',
    preparing: 'Preparing your link…', failed: 'Couldn’t create the card link. Edit the draft to try again.',
  },
  zh: {
    write: '写贺卡', title: '写一张圣诞贺卡', close: '关闭',
    privacy: '除非设置密码，否则任何拿到完整链接的人都能打开这张贺卡。',
    to: '收件人', msg: '留言', from: '寄件人（选填）', preview: '预览',
    password: '密码（选填）', passwordHelp: '请另行发送密码。忘记密码后无法找回。',
    copy: '复制链接', whatsapp: '分享到 WhatsApp', share: '分享链接',
    link: '贺卡链接', copied: '链接已复制。', manual: '请选择并复制此链接。',
    limit: '文字已缩短，以便在贺卡上完整显示。', lines: '行',
    preparing: '正在生成链接…', failed: '无法生成贺卡链接，请编辑草稿后重试。',
  },
};

export function createComposer({getGreeting, preview}) {
  const dialog = document.getElementById('composer');
  const write = document.getElementById('write-card');
  const form = dialog.querySelector('form');
  const output = dialog.querySelector('#compose-link');
  const status = dialog.querySelector('#compose-status');
  const fields = Object.fromEntries(['to','msg','from'].map(key=>[key, form.elements.namedItem(key)]));
  const password = dialog.querySelector('#compose-password');
  password.maxLength = passwordLimit;
  const labels = dialog.querySelectorAll('[data-compose]');
  const previewButton = dialog.querySelector('#compose-preview');
  const copyButton = dialog.querySelector('#compose-copy');
  const whatsappButton = dialog.querySelector('#compose-whatsapp');
  const share = dialog.querySelector('#compose-share');
  const actions = [previewButton, copyButton, whatsappButton, share];
  let lang = 'en', revision = 0, timer, prepared;

  function count() {
    for (const [key, field] of Object.entries(fields)) {
      const lines = key === 'msg' ? ` · ${field.value.split('\n').length}/${greetingLimits.lines} ${copy[lang].lines}` : '';
      const counter = dialog.querySelector(`#compose-${key}-count`);
      const text = `${codePointCount(field.value)}/${greetingLimits[key]}${lines}`;
      if(counter.textContent !== text) counter.textContent = text;
    }
  }

  function invalidate() {
    clearTimeout(timer);
    revision++;
    prepared = null;
    for (const button of actions) button.disabled = true;
    output.parentElement.hidden = true;
    output.value = '';
  }

  function prepare(trimmed = false) {
    invalidate();
    const draftRevision = revision;
    status.textContent = copy[lang][trimmed ? 'limit' : 'preparing'];
    // Prepare before a share gesture. Wait for a pause in typing before deriving a password key.
    timer = setTimeout(async () => {
      const greeting = limitGreeting({...Object.fromEntries(Object.entries(fields)
        .map(([key, field]) => [key, field.value])), lang});
      try {
        const fragment = await encodeGreeting(greeting, password.value);
        if (!dialog.open || draftRevision !== revision) return;
        const url = new URL(location.href);
        url.search = '';
        url.hash = fragment;
        prepared = {fragment, greeting, url: url.href};
        for (const button of actions) button.disabled = false;
        status.textContent = trimmed ? copy[lang].limit : '';
      } catch {
        if (dialog.open && draftRevision === revision) status.textContent = copy[lang].failed;
      }
    }, password.value ? 220 : 0);
  }

  function displayLink(url) {
    output.parentElement.hidden = false;
    output.value = url;
    output.focus();
    output.select();
    status.textContent = copy[lang].manual;
  }

  write.addEventListener('click', ()=>{
    if (dialog.open) return;
    form.reset();
    const greeting = getGreeting();
    for (const [key, field] of Object.entries(fields)) field.value = greeting[key];
    count();
    dialog.showModal();
    prepare();
  });
  form.addEventListener('submit', event=>event.preventDefault());
  dialog.addEventListener('close', ()=>{
    if (dialog.open) return;
    invalidate();
    form.reset();
    status.textContent = '';
    write.focus({preventScroll:true});
  });
  dialog.querySelector('#compose-close').addEventListener('click', ()=>dialog.close());
  for (const [key, field] of Object.entries(fields)) {
    function update(event) {
      if (event.isComposing) return;
      const limited = limitGreeting({[key]:field.value})[key];
      const trimmed = limited !== field.value;
      if (trimmed) field.value = limited;
      count();
      prepare(trimmed);
    }
    field.addEventListener('compositionstart', invalidate);
    field.addEventListener('input', update);
    field.addEventListener('compositionend', update);
  }
  password.addEventListener('compositionstart', invalidate);
  password.addEventListener('compositionend', () => prepare());
  password.addEventListener('input', event => { if (!event.isComposing) prepare(); });
  previewButton.addEventListener('click', ()=>{
    if (!prepared) return;
    const {fragment, greeting} = prepared;
    dialog.close();
    preview(fragment, greeting);
  });
  copyButton.addEventListener('click', async ()=>{
    if (!prepared) return;
    const {url} = prepared, action = ++revision;
    try {
      await navigator.clipboard.writeText(url);
      if (dialog.open && action === revision) status.textContent = copy[lang].copied;
    } catch {
      if (dialog.open && action === revision) displayLink(url);
    }
  });
  whatsappButton.addEventListener('click', ()=>{
    if (!prepared) return;
    const whatsapp = new URL('https://wa.me/');
    whatsapp.searchParams.set('text', prepared.url);
    window.open(whatsapp.href, '_blank', 'noopener,noreferrer');
  });
  share.hidden = typeof navigator.share !== 'function';
  share.addEventListener('click', async ()=>{
    if (!prepared) return;
    const {url} = prepared, action = ++revision;
    try { await navigator.share({url}); }
    catch (error) {
      if (dialog.open && action === revision && error.name !== 'AbortError') displayLink(url);
    }
  });

  return locale=>{
    const changed = lang !== locale;
    lang = locale;
    write.textContent = copy[lang].write;
    for (const label of labels) label.textContent = copy[lang][label.dataset.compose];
    if (dialog.open && changed) {
      count();
      prepare();
    }
  };
}
