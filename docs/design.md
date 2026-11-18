# Design and accessibility

Blender 3D Gallery gives artwork room through restrained typography, consistent image proportions and an on-demand model viewer. Search and category controls sit before the collection. Use readable mobile text, generous touch targets, descriptive image alternatives, visible focus and meaningful loading, empty and failure states. Check layout at 320, 390, 768 and 1440 CSS pixels when changing the gallery or viewer.

## Color system

Choose **Palette** in the desktop topbar or the mobile **Menu**. The picker uses native radio buttons, so arrow keys move and select, Tab leaves the group, and Escape closes the dialog. Selection applies immediately. The checkmark identifies the selected card independently of color.

| Palette | Scheme | Intent |
| --- | --- | --- |
| Editorial Moss (default) | Dark | Ink-green pages and the original soft moss accent |
| Midnight Ink | Dark | Midnight blue with a quiet periwinkle accent |
| Obsidian Gold | Dark | Warm black, ivory text and brushed gold |
| Nordic Frost | Light | Cool white, glacier blue and slate |
| Porcelain Sage | Light | Porcelain, pale sage and deep botanical green |
| Ember Copper | Dark | Burnt umber with soft copper |
| Deep Ocean | Dark | Deep-water teal with a sea-glass accent |
| Plum Velvet | Dark | Aubergine with muted orchid |
| Graphite Mono | Dark | Charcoal and silver with a low-chroma accent |
| Sand Dune | Light | Parchment and warm terracotta |

[src/design/tokens.js](../src/design/tokens.js) owns the color values. Vite generates CSS custom properties from it. Components consume semantic roles. Use `color-mix(in srgb, var(--role), transparent)` for translucent treatments.

| Role | Use |
| --- | --- |
| `--background` | Page and topbar |
| `--surface`, `--surface-raised` | Panels and controls with increasing emphasis |
| `--text`, `--muted` | Primary text and readable secondary text |
| `--line`, `--control-line` | Decorative dividers and identifiable control boundaries |
| `--accent`, `--accent-contrast` | Accent text, indicators and fills, with readable labels on solid accent |
| `--focus` | Keyboard focus on surrounding surfaces |
| Supporting roles | Media overlays, Game power feedback, and existing gallery and demo treatments. Editorial Moss preserves the original pale Studio and Shelf panels. Other palettes map these roles to their own semantic colors. |

The palette covers page backgrounds, controls, menus and demo panels. WebGL clear colors, lighting, materials, textures, rendered canvas markings, thumbnails and artwork retain their authored colors. Media overlays keep a consistent scrim and text pairing over images. The Game power scale keeps its established low, mid and high colors.

### Add a palette

1. Add a stable kebab-case ID to `palettes` in [tokens.js](../src/design/tokens.js). Fill every base role with a six-digit sRGB hex value and choose a `colorScheme` of `light` or `dark`. Supporting roles resolve from those values.
2. Add a `palette.<id>` name in each [message table](../src/i18n/messages/). Preview chips use that palette's background, raised surface and accent automatically.
3. Run `node scripts/check-palette-contrast.mjs` and `node scripts/check-color-tokens.mjs`. Both run in `npm test`. The contrast gate checks normal text at 4.5:1 and focus and control boundaries at 3:1 on their tested surfaces. Accent also passes 4.5:1 on the base surfaces because it appears in small text. Check the new palette in the browser, including the demos. [WCAG 2.2 contrast requirements](https://www.w3.org/TR/WCAG22/#contrast-minimum)

### Persistence and first paint

The preference is a single palette ID in `localStorage` under `b3g:palette:v1`. Synchronous reads let the document restore it before paint. IndexedDB would add asynchronous initialization for one small preference. Missing, blocked or unknown values start with Editorial Moss. A browser that rejects storage still applies the current selection in memory. Other same-origin tabs synchronize through the `storage` event.

[scripts/palette-build.mjs](../scripts/palette-build.mjs) generates the small parser-blocking head script and its exact SHA-256 CSP hash from the same source. The script sets `data-palette` and the theme and color-scheme metas before the body. The production stylesheet blocks rendering until the token CSS is available. The built HTML and stylesheet are covered by the existing service worker shell manifest. The web manifest keeps the default palette's launch colors and the contrast gate checks that these values match the token source.

## Interface language

English, 简体中文 and Bahasa Melayu share the same controls, routes and palettes. The topbar uses a compact language identifier, and the mobile Menu shows the language control beside Palette. The picker uses a native dialog with a radio group, visible keyboard focus and 44 px rows. Test translations at phone, tablet and desktop widths, including dialogs and demo controls. See [Interface languages](i18n.md) for messages, first paint and authored content.

## Interaction

Gallery and viewer controls support keyboard and touch, with alternatives and loading or error feedback when 3D is unavailable. Respect reduced motion and keep viewer reset and help discoverable. For the PWA's offline scope, safe areas and update behavior, see [PWA Product Standard](pwa-standard.md).
