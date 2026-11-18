export function readSavedPalette(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function applyPalette(requested, themes, fallback) {
  const id = Object.hasOwn(themes, requested) ? requested : fallback;
  const [background, scheme] = themes[id];
  document.documentElement.dataset.palette = id;
  document.querySelector('meta[name="theme-color"]').content = background;
  document.querySelector('meta[name="color-scheme"]').content = scheme;
  return id;
}
