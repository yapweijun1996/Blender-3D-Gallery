import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DEFAULT_PALETTE, palettes, resolvePalette } from "../src/design/tokens.js";

function luminance(color) {
  assert.match(color, /^#[0-9a-f]{6}$/i);
  const channels = color.slice(1).match(/../g).map((hex) => {
    const value = Number.parseInt(hex, 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(foreground, background) {
  const colors = [luminance(foreground), luminance(background)];
  return (Math.max(...colors) + 0.05) / (Math.min(...colors) + 0.05);
}

const baseSurfaces = ["background", "surface", "surface-raised"];
const textPairs = [
  ...baseSurfaces.flatMap((surface) => ["text", "muted", "accent"].map((role) => [role, surface])),
  ["accent-contrast", "accent"],
  ["accent-contrast", "accent-hover"],
  ["navigation-text", "background"],
  ["footer-text", "background"],
  ["field-label-text", "background"],
  ["download-text", "surface"],
  ["notice-text", "notice-surface"],
  ["game-control-text", "surface-raised"],
  ["game-control-text", "game-control-hover"],
  ["game-primary-text", "accent"],
  ["game-player-index", "game-player-surface"],
  ["game-status-text", "game-panel-surface"],
  ["game-caption-text", "game-board-compact-surface"],
  ["game-loading-text", "game-board-surface"],
  ["power-handle-text", "power-handle"],
  ["solar-control-text", "solar-control-surface"],
  ["studio-text", "studio-surface"],
  ["studio-text", "studio-control-surface"],
  ["studio-muted", "studio-surface"],
  ["studio-badge-text", "studio-badge-surface"],
  ["studio-selected-text", "studio-selected"],
  ["shelf-text", "shelf-panel-surface"],
  ["shelf-muted", "shelf-panel-surface"],
  ["shelf-text", "shelf-control-surface"],
  ["shelf-selected-text", "shelf-selected"],
  ["motion-selected-text", "motion-selected"],
  ["preset-selected-text", "preset-selected"],
  ["text", "visitor-control-surface"],
];
const controlPairs = [
  ...baseSurfaces.flatMap((surface) => ["focus", "control-line"].map((role) => [role, surface])),
  ["power-focus", "power-track-surface"],
  ["solar-focus", "solar-control-surface"],
  ["studio-control-focus", "studio-surface"],
  ["studio-stage-focus", "studio-stage"],
  ["shelf-focus", "shelf-panel-surface"],
  ["shelf-focus", "studio-stage"],
  ["control-highlight", "preset-surface"],
];
const manifest = JSON.parse(readFileSync(new URL("../public/manifest.webmanifest", import.meta.url), "utf8"));
assert.equal(manifest.theme_color, palettes[DEFAULT_PALETTE].background);
assert.equal(manifest.background_color, palettes[DEFAULT_PALETTE].background);

const ids = Object.keys(palettes);
assert.ok(ids.filter((id) => palettes[id].colorScheme === "light").length >= 3);
const roles = Object.keys(resolvePalette(DEFAULT_PALETTE)).sort();
for (const id of ids) {
  const palette = resolvePalette(id);
  assert.deepEqual(Object.keys(palette).sort(), roles, `${id} must supply every role`);
  assert.match(palette.colorScheme, /^(dark|light)$/);
  for (const [role, value] of Object.entries(palette)) {
    if (role !== "colorScheme") assert.match(value ?? "", /^#[0-9a-f]{6}$/i, `${id}: invalid ${role}`);
  }

  for (const [pairs, minimum] of [[textPairs, 4.5], [controlPairs, 3]]) {
    for (const [foreground, background] of pairs) {
      const ratio = contrast(palette[foreground], palette[background]);
      assert.ok(ratio >= minimum, `${id}: ${foreground} on ${background} is ${ratio.toFixed(2)}:1, minimum ${minimum}:1`);
    }
  }
  console.log(`PASS ${id} (${palette.colorScheme})`);
}
console.log(`Palette contrast passed: ${ids.length} palettes, ${ids.length * (textPairs.length + controlPairs.length)} WCAG 2.2 AA pairs.`);
