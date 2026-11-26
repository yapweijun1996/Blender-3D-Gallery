export const greetingLimits = Object.freeze({to: 40, msg: 240, from: 40, lines: 6});
export const fragmentLimit = 8192;

export const codePointCount = text => Array.from(text).length;

function clean(value, limit, multiline = false) {
  if (typeof value !== 'string') return '';
  const lines = value.replace(/\r\n?|[\u2028\u2029]/gu, '\n').split('\n');
  const sanitized = lines.slice(0, multiline ? greetingLimits.lines : lines.length)
    .map(line => line.replace(/[\p{Cc}\p{Bidi_Control}]/gu, ''))
    .join(multiline ? '\n' : ' ');
  return Array.from(sanitized).slice(0, limit).join('');
}

export function limitGreeting({to, msg, from, lang}) {
  return {
    to: clean(to, greetingLimits.to),
    msg: clean(msg, greetingLimits.msg, true),
    from: clean(from, greetingLimits.from),
    lang: lang === 'en' || lang === 'zh' ? lang : undefined,
  };
}

export function decodeGreeting(fragment = '') {
  const start = fragment.startsWith('#') ? 1 : 0;
  if (fragment.length - start > fragmentLimit) return limitGreeting({});
  const fields = new URLSearchParams(fragment.slice(start));
  return limitGreeting({
    to: fields.get('to'), msg: fields.get('msg'), from: fields.get('from'), lang: fields.get('lang'),
  });
}

export function encodeGreeting(input) {
  const fields = new URLSearchParams();
  const {to, msg, from, lang} = limitGreeting(input);
  for (const [key, value] of Object.entries({to, msg, from, lang: lang || 'en'})) {
    if (value.trim()) fields.set(key, value);
  }
  return '#' + fields.toString();
}
