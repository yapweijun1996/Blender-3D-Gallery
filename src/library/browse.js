import { localize, t } from "../i18n/index.js";

export const normalized = (value) =>
  String(value ?? "")
    .trim()
    .replace(/\s+/g, " ")
    .toLocaleLowerCase();
export function matches(item, query, category = "", collection = "", theme = "", translated = []) {
  const text = normalized(
    [
      item.title,
      item.name,
      item.description,
      item.category,
      item.browseCategory,
      item.collectionName,
      ...(item.tags ?? []),
      ...translated,
    ].join(" "),
  );
  return (
    (!category || normalized(item.category) === normalized(category) ||
      normalized(item.previousCategory) === normalized(category)) &&
    (!theme || normalized(item.browseCategory) === normalized(theme)) &&
    (!collection || item.collectionId === collection) &&
    normalized(query)
      .split(" ")
      .every((word) => text.includes(word))
  );
}
export function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
let posterObserver;
// Only on-screen posters pulse: animating every pending card in the library drops frames.
function watchPoster(image) {
  posterObserver ??= new IntersectionObserver((entries) => {
    for (const { target, isIntersecting } of entries) target.toggleAttribute("data-visible", isIntersecting);
  });
  posterObserver.observe(image);
}
export function poster(url, title, live = false) {
  const image = element("img");
  image.src = url;
  const set = (node, key, attr) => {
    if (live) localize(node, key, { name: title }, attr);
    else node.setAttribute(attr, t(key, { name: title }));
  };
  set(image, "library.poster", "alt");
  image.width = 400;
  image.height = 400;
  image.loading = "lazy";
  // CSS shows the frame placeholder while this attribute is present.
  image.dataset.loading = "";
  watchPoster(image);
  const settle = () => {
    delete image.dataset.loading;
    posterObserver.unobserve(image);
  };
  image.addEventListener("load", settle, { once: true });
  image.addEventListener(
    "error",
    () => {
      settle();
      image.hidden = true;
      const frame = image.parentElement;
      frame.classList.add("poster-unavailable");
      set(frame, "library.posterUnavailable", "aria-label");
      const fallback = localize(element("span", "poster-fallback"), "library.previewUnavailable");
      fallback.setAttribute("aria-hidden", "true");
      frame.append(fallback);
    },
    { once: true },
  );
  return image;
}
export const categoryKey = value => `category.${value.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

export function options(select, values, key) {
  for (const value of [...new Set(values)].sort((a, b) => a.localeCompare(b))) {
    const option = localize(element("option"), key(value));
    option.value = value;
    select.append(option);
  }
}
export function emptyState(title, description) {
  const box = element("div", "empty-state");
  box.append(localize(element("p", "empty-title"), title), localize(element("p"), description));
  return box;
}
export function setupFilters(form, fields, onChange) {
  form.addEventListener("submit", (event) => event.preventDefault());
  const update = () => {
    const url = new URL(location.href);
    for (const [key, input] of Object.entries(fields)) {
      if (input.value.trim()) url.searchParams.set(key, input.value);
      else url.searchParams.delete(key);
    }
    history.replaceState(history.state, "", url);
    onChange();
  };
  form.addEventListener("input", update);
  form.addEventListener("reset", () => {
    setTimeout(update, 0);
  });
  return () => {
    const params = new URL(location.href).searchParams;
    for (const [key, input] of Object.entries(fields))
      input.value = params.get(key) ?? "";
    onChange();
  };
}
export function formatBytes(bytes) {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(2)} MiB`
    : `${(bytes / 1024).toFixed(1)} KiB`;
}
