import { DEFAULT_LANGUAGE, LANGUAGE_STORAGE_KEY, languages, readSavedLanguage } from "./preferences.js";
import en from "./messages/en.js";
import zhHans from "./messages/zh-Hans.js";
import ms from "./messages/ms.js";

export { languages };
export const messages = { en, "zh-Hans": zhHans, ms };
const ids = Object.keys(languages);
const rules = Object.fromEntries(ids.map(id => [id, new Intl.PluralRules(id)]));
const numbers = Object.fromEntries(ids.map(id => [id, new Intl.NumberFormat(id)]));
let language = ids.includes(globalThis.document?.documentElement.lang)
  ? document.documentElement.lang : DEFAULT_LANGUAGE;

export function getLanguage() {
  return language;
}

export function t(key, params = {}, locale = language) {
  const lookup = table => table && Object.hasOwn(table, key) ? table[key] : undefined;
  const template = lookup(Object.hasOwn(messages, locale) ? messages[locale] : en) ?? lookup(en) ?? key;
  return template.replace(/\{(\w+)\}/g, (placeholder, name) =>
    Object.hasOwn(params, name) ? String(params[name]) : placeholder);
}

export function number(value) {
  return numbers[language].format(value);
}

export function plural(key, count, params = {}) {
  const table = messages[language];
  const category = rules[language].select(count);
  const english = rules.en.select(count);
  const values = { count: number(count), ...params };
  if (Object.hasOwn(table, `${key}.${category}`)) return t(`${key}.${category}`, values);
  if (Object.hasOwn(table, `${key}.other`)) return t(`${key}.other`, values);
  return t(`${key}.${english}`, values, DEFAULT_LANGUAGE);
}

// Store parameters on their elements so detached views can be collected.
const parameters = new WeakMap();
const selector = "[data-i18n]";
const attributes = ["aria-label", "alt", "title", "placeholder", "content"];
const bindings = [selector, ...attributes.map(attr => `[data-i18n-${attr}]`)].join(",");

const resolveParams = params => typeof params === "function" ? params() : params;

export function localize(node, key, params, attr) {
  const marker = attr ? `data-i18n-${attr}` : "data-i18n";
  if (key && node.getAttribute(marker) !== key) node.setAttribute(marker, key);
  else if (!key) node.removeAttribute(marker);
  if (params || parameters.has(node)) {
    const values = parameters.get(node) ?? {};
    values[marker] = params;
    parameters.set(node, values);
  }
  const value = key ? t(key, resolveParams(params)) : "";
  if (attr) {
    if (node.getAttribute(attr) !== value) node.setAttribute(attr, value);
  } else if (node.textContent !== value) node.textContent = value;
  return node;
}

export function localizeTree(root = document) {
  for (const node of root.querySelectorAll(bindings)) {
    const values = parameters.get(node);
    for (const attr of attributes) {
      const marker = `data-i18n-${attr}`;
      if (node.hasAttribute(marker))
        node.setAttribute(attr, t(node.getAttribute(marker), resolveParams(values?.[marker])));
    }
    if (node.hasAttribute("data-i18n")) {
      const value = t(node.dataset.i18n, resolveParams(values?.["data-i18n"]));
      if (node.textContent !== value) node.textContent = value;
    }
  }
}

export function mountMarkup(root, markup) {
  root.innerHTML = markup;
  localizeTree(root);
}

export function onLanguageChange(callback, signal) {
  window.addEventListener("gallery-language-change", callback, { signal });
}

function applyLanguage(id) {
  if (id === language) return;
  language = id;
  document.documentElement.lang = id;
  localizeTree();
  window.dispatchEvent(new Event("gallery-language-change"));
}

export function setLanguage(id) {
  if (!ids.includes(id)) return;
  applyLanguage(id);
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, id);
  } catch {
    // Keep the in-memory choice.
  }
}

export function syncLanguageAcrossTabs() {
  window.addEventListener("storage", (event) => {
    if (event.key !== LANGUAGE_STORAGE_KEY && event.key !== null) return;
    try {
      if (event.storageArea !== localStorage) return;
    } catch {
      return;
    }
    applyLanguage(readSavedLanguage(LANGUAGE_STORAGE_KEY, ids, DEFAULT_LANGUAGE));
  });
}
