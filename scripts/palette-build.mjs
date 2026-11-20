import { createHash } from "node:crypto";
import {
  DEFAULT_PALETTE,
  PALETTE_STORAGE_KEY,
  palettes,
  paletteThemes,
  resolvePalette,
  supportingRoles,
} from "../src/design/tokens.js";
import { applyPalette, readSavedPalette } from "../src/design/palette.js";

const cssId = "virtual:gallery-palette-colors.css";

export function paletteBuildPlugin() {
  return {
    name: "gallery-palette-colors",
    resolveId(id) {
      if (id === cssId) return "\0" + cssId;
    },
    load(id) {
      if (id !== "\0" + cssId) return;
      const aliases = Object.entries(supportingRoles).map(([role, [value, fallback]]) =>
        `--${role}:${fallback ? `var(--${fallback})` : value}`,
      );
      const rules = [`:root, [data-palette] {${aliases.join(";")}}`];
      for (const [paletteId, palette] of Object.entries(palettes)) {
        const isDefault = paletteId === DEFAULT_PALETTE;
        const { colorScheme, ...roles } = isDefault ? resolvePalette(paletteId) : palette;
        const selector = `[data-palette="${paletteId}"]`;
        const selectors = isDefault ? `:root:not([data-palette]), ${selector}` : selector;
        const declarations = Object.entries(roles).map(([role, value]) => `--${role}:${value}`);
        rules.push(`${selectors}{--palette-scheme:${colorScheme};${declarations.join(";")}}`);
      }
      return rules.join("\n");
    },
    transformIndexHtml(html) {
      // A parser-blocking head script applies the preference before page content or app JS.
      const saved = `(${readSavedPalette})(${JSON.stringify(PALETTE_STORAGE_KEY)})`;
      const script = `(${applyPalette})(${saved},${JSON.stringify(paletteThemes)},${JSON.stringify(DEFAULT_PALETTE)});`;
      const hash = createHash("sha256").update(script).digest("base64");
      const [background, scheme] = paletteThemes[DEFAULT_PALETTE];
      return html
        .replace('name="theme-color" content=""', `name="theme-color" content="${background}"`)
        .replace('name="color-scheme" content=""', `name="color-scheme" content="${scheme}"`)
        .replace(/script-src 'self'([^;]*);/, `script-src 'self'$1 'sha256-${hash}';`)
        .replace("<!-- palette-bootstrap -->", `<script>${script}</script>`);
    },
  };
}
