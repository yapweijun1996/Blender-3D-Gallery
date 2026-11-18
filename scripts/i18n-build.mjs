import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { t } from "../src/i18n/index.js";
import { DEFAULT_LANGUAGE, LANGUAGE_STORAGE_KEY, languages, readSavedLanguage } from "../src/i18n/preferences.js";

const escapeHtml = value => value.replace(/[&<>"']/g, char =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);

function startLanguage(read, storageKey, ids, fallback, titles) {
  const id = read(storageKey, ids, fallback);
  document.documentElement.lang = id;
  if (id !== fallback) document.documentElement.setAttribute("data-i18n-pending", "");
  const page = new URLSearchParams(location.search).get("page") || (location.hash === "#about" ? "about" : "");
  document.title = Object.hasOwn(titles[id], page) ? titles[id][page] : titles[id].gallery;
}

export function i18nBuildPlugin() {
  const demos = JSON.parse(readFileSync(new URL("../data/demos.json", import.meta.url), "utf8"));
  const routes = {
    gallery: "nav.models",
    about: "nav.about",
    demos: "nav.demos",
    ...Object.fromEntries(demos.map(demo => [demo.route.slice("?page=".length), `demo.${demo.id}.title`])),
  };
  const ids = Object.keys(languages);
  const titles = Object.fromEntries(ids.map(id => [id, Object.fromEntries(
    Object.entries(routes).map(([page, key]) => [page, t("shell.pageTitle", { title: t(key, {}, id) }, id)]),
  )]));
  const script = `(${startLanguage})(${readSavedLanguage},${JSON.stringify(LANGUAGE_STORAGE_KEY)},${JSON.stringify(ids)},${JSON.stringify(DEFAULT_LANGUAGE)},${JSON.stringify(titles).replace(/</g, "\\u003c")});`;
  const hash = createHash("sha256").update(script).digest("base64");

  return {
    name: "gallery-language",
    transformIndexHtml(html) {
      return html
        .replace(/script-src 'self'([^;]*);/, `script-src 'self'$1 'sha256-${hash}';`)
        .replace("<!-- language-bootstrap -->", `<script>${script}</script>`)
        .replace(/ data-i18n-(aria-label|alt|title|placeholder|content)="([^"]+)"/g,
          (binding, attr, key) => `${binding} ${attr}="${escapeHtml(t(key))}"`)
        .replace(/( data-i18n="([^"]+)"[^>]*>)(?=<)/g,
          (opening, _, key) => opening + escapeHtml(t(key)));
    },
  };
}
