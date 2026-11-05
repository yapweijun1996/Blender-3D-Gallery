export const normalized = (value) =>
  String(value ?? "")
    .trim()
    .replace(/\s+/g, " ")
    .toLocaleLowerCase();
export function matches(item, query, category = "", collection = "") {
  const text = normalized(
    [
      item.title,
      item.name,
      item.description,
      item.category,
      item.collectionName,
      ...(item.tags ?? []),
    ].join(" "),
  );
  return (
    (!category || normalized(item.category) === normalized(category)) &&
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
export function poster(url, title) {
  const image = element("img");
  image.src = url;
  image.alt = `${title} preview`;
  image.width = 400;
  image.height = 400;
  image.loading = "lazy";
  image.addEventListener(
    "error",
    () => {
      image.hidden = true;
      image.parentElement.classList.add("poster-unavailable");
      image.parentElement.setAttribute(
        "aria-label",
        `${title} — preview unavailable`,
      );
    },
    { once: true },
  );
  return image;
}
export function options(select, values) {
  for (const value of [...new Set(values)].sort((a, b) => a.localeCompare(b))) {
    const option = element("option", "", value);
    option.value = value;
    select.append(option);
  }
}
export function emptyState(title, description) {
  const box = element("div", "empty-state");
  box.append(element("p", "empty-title", title), element("p", "", description));
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
