export const greetingLimits = Object.freeze({to: 40, msg: 240, from: 40, lines: 6});
export const fragmentLimit = 8192;
export const passwordLimit = 256;

const version = 1, linkKey = 0, passwordKey = 1;
const ivLength = 12, keyLength = 32, saltLength = 16, tagLength = 16;
const iterations = 600_000;
const utf8 = new TextEncoder();

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

function encodeBytes(bytes) {
  return btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}

// V1 authenticates the header: version, mode, 96-bit IV, then the raw key or salt.
export function readGreetingFragment(fragment = '') {
  const start = fragment.startsWith('#') ? 1 : 0;
  if (fragment.length - start > fragmentLimit) throw new Error('Card fragment too long');
  const raw = fragment.slice(start);
  const fields = new URLSearchParams(raw);
  if (!fields.has('e')) {
    if (raw && !['to', 'msg', 'from', 'lang'].some(key => fields.has(key))) {
      throw new Error('Unknown card fragment');
    }
    return {greeting: limitGreeting({
      to: fields.get('to'), msg: fields.get('msg'), from: fields.get('from'), lang: fields.get('lang'),
    })};
  }
  if (!/^e=[A-Za-z0-9_-]+$/.test(raw)) throw new Error('Invalid encrypted card fragment');
  const encoded = raw.slice(2);
  const bytes = Uint8Array.from(atob(encoded.replaceAll('-', '+').replaceAll('_', '/')), c => c.charCodeAt(0));
  const [packetVersion, mode] = bytes;
  const passwordRequired = mode === passwordKey;
  const headerLength = 2 + ivLength + (passwordRequired ? saltLength : keyLength);
  if (packetVersion !== version || (mode !== linkKey && !passwordRequired) ||
      bytes.length <= headerLength + tagLength || encodeBytes(bytes) !== encoded) {
    throw new Error('Invalid encrypted card packet');
  }
  return {packet: bytes, headerLength, passwordRequired};
}

async function aesKey(material, password, usage) {
  if (password.length > passwordLimit) throw new Error('Card password too long');
  if (!password) return crypto.subtle.importKey('raw', material, 'AES-GCM', false, [usage]);
  const base = await crypto.subtle.importKey('raw', utf8.encode(password), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({name: 'PBKDF2', hash: 'SHA-256', salt: material, iterations},
    base, {name: 'AES-GCM', length: keyLength * 8}, false, [usage]);
}

function gcm(header) {
  return {name: 'AES-GCM', iv: header.subarray(2, 2 + ivLength), additionalData: header, tagLength: tagLength * 8};
}

export async function encodeGreeting(input, password = '') {
  const greeting = limitGreeting(input);
  greeting.lang ||= 'en';
  const header = new Uint8Array(2 + ivLength + (password ? saltLength : keyLength));
  header.set([version, password ? passwordKey : linkKey]);
  crypto.getRandomValues(header.subarray(2));
  const key = await aesKey(header.subarray(2 + ivLength), password, 'encrypt');
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt(gcm(header), key, utf8.encode(JSON.stringify(greeting))));
  const bytes = new Uint8Array(header.length + ciphertext.length);
  bytes.set(header);
  bytes.set(ciphertext, header.length);
  return '#e=' + encodeBytes(bytes);
}

export async function decryptGreeting({packet, headerLength, passwordRequired}, password = '') {
  if (passwordRequired !== Boolean(password)) throw new Error('Card password required');
  const header = packet.subarray(0, headerLength);
  const key = await aesKey(header.subarray(2 + ivLength), password, 'decrypt');
  const plaintext = await crypto.subtle.decrypt(gcm(header), key, packet.subarray(headerLength));
  const greeting = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(plaintext));
  if (typeof greeting?.to !== 'string' || typeof greeting.msg !== 'string' || typeof greeting.from !== 'string' ||
      (greeting.lang !== 'en' && greeting.lang !== 'zh')) throw new Error('Invalid card greeting');
  return limitGreeting(greeting);
}
