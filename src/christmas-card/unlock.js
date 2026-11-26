import { decryptGreeting, passwordLimit } from './greeting-link.js';

const copy = {
  en: {
    title: 'Unlock this Christmas card', language: '中文', languageLabel: 'Switch to Chinese',
    help: 'Enter the password the sender shared with you.', password: 'Password',
    submit: 'Unlock', cancel: 'View default card', checking: 'Unlocking…',
    retry: 'That password didn’t unlock the card. Try again, or view the default card if the link is damaged.',
  },
  zh: {
    title: '解锁圣诞贺卡', language: 'EN', languageLabel: '切换为英文',
    help: '请输入寄件人另行发送的密码。', password: '密码',
    submit: '解锁', cancel: '查看默认贺卡', checking: '正在解锁…',
    retry: '此密码无法解锁贺卡。请重试。如果链接已损坏，可以查看默认贺卡。',
  },
};

export function createUnlockDialog(toggleLanguage) {
  const dialog = document.getElementById('unlock-dialog');
  const form = dialog.querySelector('form');
  const password = dialog.querySelector('#unlock-password');
  const status = dialog.querySelector('#unlock-status');
  const submit = dialog.querySelector('#unlock-submit');
  const language = dialog.querySelector('#unlock-language');
  const labels = dialog.querySelectorAll('[data-unlock]');
  let resolve, packet, notice, lang = 'en';
  password.maxLength = passwordLimit;

  function report(next) {
    notice = next;
    status.textContent = copy[lang][notice] || '';
    if (notice === 'retry') password.setAttribute('aria-invalid', 'true');
    else password.removeAttribute('aria-invalid');
    submit.disabled = notice === 'checking';
  }

  function close(result) {
    const finish = resolve;
    resolve = packet = null;
    form.reset();
    report();
    if (dialog.open) dialog.close();
    finish?.(result);
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!resolve || notice === 'checking') return;
    const attempt = resolve;
    report('checking');
    const pending = decryptGreeting(packet, password.value);
    password.value = '';
    try {
      const greeting = await pending;
      if (resolve === attempt) close({greeting});
    } catch (error) {
      if (resolve !== attempt) return;
      if (error.name === 'OperationError') {
        report('retry');
        password.focus({preventScroll: true});
      } else close({invalid: true});
    }
  });
  password.addEventListener('input', () => { if (notice === 'retry') report(); });
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  dialog.querySelector('#unlock-cancel').addEventListener('click', () => close());
  language.addEventListener('click', toggleLanguage);

  return {
    request(link) {
      packet = link;
      dialog.showModal();
      return new Promise(finish => { resolve = finish; });
    },
    dismiss: close,
    localize(locale) {
      lang = locale;
      for (const label of labels) label.textContent = copy[lang][label.dataset.unlock];
      language.setAttribute('aria-label', copy[lang].languageLabel);
      report(notice);
    },
  };
}
