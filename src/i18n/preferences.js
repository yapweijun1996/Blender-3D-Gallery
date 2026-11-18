export const DEFAULT_LANGUAGE = "en";
export const LANGUAGE_STORAGE_KEY = "b3g:language:v1";
export const languages = {
  en: { label: "English", short: "EN" },
  "zh-Hans": { label: "简体中文", short: "中文" },
  ms: { label: "Bahasa Melayu", short: "BM" },
};

export function readSavedLanguage(key, ids, fallback) {
  try {
    const saved = localStorage.getItem(key);
    if (ids.includes(saved)) return saved;
  } catch {
    // The live preference still works when storage is blocked.
  }
  return fallback;
}
