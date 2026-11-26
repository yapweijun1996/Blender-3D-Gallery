import { codePointCount, encodeGreeting, greetingLimits, limitGreeting } from './greeting-link.js';

const copy = {
  en: {
    write: 'Write a card', title: 'Write a Christmas card', close: 'Close',
    privacy: 'Anyone with the link can read your message.',
    to: 'To', msg: 'Message', from: 'From (optional)', preview: 'Preview',
    copy: 'Copy link', whatsapp: 'Share on WhatsApp', share: 'Share link',
    link: 'Card link', copied: 'Link copied.', manual: 'Select and copy this link.',
    limit: 'The text was trimmed to fit the card.', lines: 'lines',
  },
  zh: {
    write: '写贺卡', title: '写一张圣诞贺卡', close: '关闭',
    privacy: '任何拿到链接的人都可以阅读你的留言。',
    to: '收件人', msg: '留言', from: '寄件人（选填）', preview: '预览',
    copy: '复制链接', whatsapp: '分享到 WhatsApp', share: '分享链接',
    link: '贺卡链接', copied: '链接已复制。', manual: '请选择并复制此链接。',
    limit: '文字已缩短，以便在贺卡上完整显示。', lines: '行',
  },
};

export function createComposer({getGreeting, preview}) {
  const dialog = document.getElementById('composer');
  const write = document.getElementById('write-card');
  const form = dialog.querySelector('form');
  const output = dialog.querySelector('#compose-link');
  const status = dialog.querySelector('#compose-status');
  const fields = Object.fromEntries(['to','msg','from'].map(key=>[key, form.elements.namedItem(key)]));
  const labels = dialog.querySelectorAll('[data-compose]');
  const share = dialog.querySelector('#compose-share');
  let lang = 'en', revision = 0;

  function count() {
    for (const [key, field] of Object.entries(fields)) {
      const lines = key === 'msg' ? ` · ${field.value.split('\n').length}/${greetingLimits.lines} ${copy[lang].lines}` : '';
      const counter = dialog.querySelector(`#compose-${key}-count`);
      const text = `${codePointCount(field.value)}/${greetingLimits[key]}${lines}`;
      if(counter.textContent !== text) counter.textContent = text;
    }
  }

  function link() {
    const destination = new URL(location.href);
    destination.search = '';
    destination.hash = encodeGreeting({...draft(), lang});
    return destination.href;
  }

  function draft() {
    return Object.fromEntries(Object.entries(fields).map(([key, field])=>[key, field.value]));
  }

  function displayLink(url) {
    output.parentElement.hidden = false;
    output.value = url;
    output.focus();
    output.select();
    status.textContent = copy[lang].manual;
  }

  function sizeDialog() {
    const viewport = window.visualViewport;
    if (viewport && dialog.open) {
      dialog.style.setProperty('--visible-height', `${viewport.height}px`);
      dialog.style.setProperty('--viewport-top', `${viewport.offsetTop}px`);
    }
  }

  write.addEventListener('click', ()=>{
    if (dialog.open) return;
    const greeting = getGreeting();
    for (const [key, field] of Object.entries(fields)) field.value = greeting[key];
    count();
    dialog.showModal();
    dialog.querySelector('#compose-title').focus({preventScroll:true});
    sizeDialog();
  });
  window.visualViewport?.addEventListener('resize', sizeDialog);
  window.visualViewport?.addEventListener('scroll', sizeDialog);
  form.addEventListener('submit', event=>event.preventDefault());
  dialog.addEventListener('close', ()=>{
    revision++;
    form.reset();
    output.parentElement.hidden = true;
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
      revision++;
      output.parentElement.hidden = true;
      output.value = '';
      status.textContent = trimmed ? copy[lang].limit : '';
    }
    field.addEventListener('input', update);
    field.addEventListener('compositionend', update);
  }
  dialog.querySelector('#compose-preview').addEventListener('click', ()=>{
    const fragment = encodeGreeting({...draft(), lang});
    dialog.close();
    preview(fragment);
  });
  dialog.querySelector('#compose-copy').addEventListener('click', async ()=>{
    const url = link(), action = ++revision;
    try {
      await navigator.clipboard.writeText(url);
      if (dialog.open && action === revision) status.textContent = copy[lang].copied;
    } catch {
      if (dialog.open && action === revision) displayLink(url);
    }
  });
  dialog.querySelector('#compose-whatsapp').addEventListener('click', ()=>{
    const whatsapp = new URL('https://wa.me/');
    whatsapp.searchParams.set('text', link());
    window.open(whatsapp.href, '_blank', 'noopener,noreferrer');
  });
  share.hidden = typeof navigator.share !== 'function';
  share.addEventListener('click', async ()=>{
    const url = link(), action = ++revision;
    try { await navigator.share({url}); }
    catch (error) {
      if (dialog.open && action === revision && error.name !== 'AbortError') displayLink(url);
    }
  });

  return locale=>{
    lang = locale;
    write.textContent = copy[lang].write;
    for (const label of labels) label.textContent = copy[lang][label.dataset.compose];
    if (dialog.open) count();
  };
}
