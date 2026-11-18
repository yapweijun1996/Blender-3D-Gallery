import { readFileSync } from "node:fs";
import { messages, plural, t } from "../src/i18n/index.js";
import { DEFAULT_LANGUAGE, languages } from "../src/i18n/preferences.js";
import { paletteThemes } from "../src/design/tokens.js";
import { categoryKey } from "../src/library/browse.js";

const read = path => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
const problems = [];
const english = messages[DEFAULT_LANGUAGE];
const placeholders = text => [...new Set(
  [...text.matchAll(/\{(\w+)\}/g)].map(match => match[1]),
)].sort().join(", ");

if (Object.keys(languages).sort().join() !== Object.keys(messages).sort().join())
  problems.push("The picker and message tables must support the same languages");

for (const [locale, table] of Object.entries(messages)) {
  for (const [key, value] of Object.entries(english)) {
    if (!Object.hasOwn(table, key)) problems.push(`${locale}: missing ${key}`);
    else if (typeof table[key] !== "string" || !table[key].trim())
      problems.push(`${locale}: empty or invalid value for ${key}`);
    else if (placeholders(value) !== placeholders(table[key]))
      problems.push(`${locale}: placeholders differ for ${key}`);
  }
  for (const key of Object.keys(table))
    if (!Object.hasOwn(english, key)) problems.push(`${locale}: extra ${key}`);

  const path = `src/i18n/messages/${locale}.js`;
  const declared = [...read(path).matchAll(/^  "([^"]+)":/gm)].map(([, key]) => key);
  if (declared.length !== new Set(declared).size)
    problems.push(`${path}: duplicate message key`);
}

function requireKey(key, path) {
  if (!Object.hasOwn(english, key)) problems.push(`${path}: unknown message ${key}`);
}

const catalog = JSON.parse(read("models/catalog.json"));
for (const { assets } of catalog.collections) {
  for (const asset of assets) {
    for (const value of [asset.category, asset.browseCategory, asset.previousCategory].filter(Boolean))
      requireKey(categoryKey(value), "models/catalog.json");
    if (asset.family === "solar-system") requireKey(`solar.body.${asset.solarId}`, "models/catalog.json");
  }
}
for (const id of Object.keys(paletteThemes)) requireKey(`palette.${id}`, "src/design/tokens.js");

const templateFiles = [
  "index.html", "src/game/page.js", "src/game/scene.js", "src/library/browse.js", "src/solar/page.js", "src/product-studio/page.js",
  "src/shelf-inspector/page.js", "src/chibi-motion/page.js", "src/main.js",
  "src/pwa/register.js", "src/pwa/update-ui.js", "src/design/palette-picker.js",
  "src/viewer.js", "src/chibi-rig-controls.js", "src/fish-motion.js",
  "src/tripo-animation-preview.js", "src/shopping-cart/demo.js",
  "src/visitor-v2/demo.js", "src/visitor-v3/demo.js", "src/scroll-to-top.js",
];
const authoredText = new Set(["Blender 3D Gallery", "BLENDER", "3D", "GALLERY", "BLENDER 3D GALLERY",
  "✳ BLENDER 3D GALLERY", "GitHub", "GitHub ↗"]);
const htmlLiteral = /(`|['"])(<\w[^\n]*?[\s\S]*?>)\1/g;
const literal = "(['\"`])((?:\\\\.|(?!\\1)[\\s\\S])*?)\\1";
const messageSink = new RegExp(
  "\\.(?:textContent|innerText|title|placeholder|alt)\\s*=\\s*" + literal, "g");
const attrSink = new RegExp(
  "\\bsetAttribute\\(\\s*['\"](?:aria-label|aria-valuetext|title|alt|placeholder)['\"]\\s*,\\s*" + literal, "g");

function checkLiteral(value, path) {
  const copy = value.replace(/\$\{[^}]*\}/g, "").replace(/&(?:#\w+|\w+);/g, " ")
    .replace(/\s+/g, " ").trim();
  if (/\p{L}/u.test(copy) && !authoredText.has(copy))
    problems.push(`${path}: literal user-facing copy "${copy}"`);
}

function checkMarkup(markup, path) {
  const clean = markup.replace(/<!--[\s\S]*?-->/g, "").replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "");
  for (const match of clean.matchAll(/<[^>]*>|[^<>]+/g)) {
    const token = match[0];
    if (token.startsWith("<")) {
      if (/^<meta\b/i.test(token) && !/name=["']description["']/i.test(token)) continue;
      for (const [, attr, , value] of token.matchAll(/\s(data-i18n(?:-[\w-]+)?|aria-label|aria-valuetext|title|alt|placeholder|content)\s*=\s*(["'])(.*?)\2/g)) {
        if (attr.startsWith("data-i18n")) requireKey(value, path);
        else checkLiteral(value, path);
      }
    } else checkLiteral(token, path);
  }
}

for (const path of templateFiles) {
  const source = read(path);
  if (path.endsWith(".html")) checkMarkup(source, path);
  else {
    for (const [, , markup] of source.matchAll(htmlLiteral)) checkMarkup(markup, path);
    for (const pattern of [messageSink, attrSink]) {
      for (const [, , value] of source.matchAll(pattern)) checkLiteral(value, path);
    }
    for (const [, , key] of source.matchAll(/\bt\(\s*(["'])([\w.-]+)\1/g)) requireKey(key, path);
  }
}

for (const path of ["src/style.css", "src/i18n/picker.css", "src/design/palette-picker.css",
  ...["game", "solar", "product-studio", "shelf-inspector", "chibi-motion"].map(dir => `src/${dir}/style.css`)]) {
  for (const [, , value] of read(path).matchAll(/\bcontent:\s*(["'])(.*?)\1/g)) checkLiteral(value, path);
}

// Formatting and fallback are also exercised outside the browser.
if (t("pwa.updateTo", { version: "1.2.3" }, "ms") !== "Kemas kini ke v1.2.3")
  problems.push("Named substitution failed");
if (t("nav.about", {}, "unsupported") !== english["nav.about"])
  problems.push("English fallback failed");
if (plural("library.modelCount", 1) !== "1 model" || plural("library.modelCount", 0) !== "0 models")
  problems.push("Plural selection failed");

if (problems.length) {
  console.error(problems.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`i18n OK: ${Object.keys(english).length} messages × ${Object.keys(messages).length} languages, matching placeholders, ${templateFiles.length} UI sources checked.`);
}
