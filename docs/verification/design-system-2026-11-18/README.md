# Color system verification · 2026-11-18

Production build `6f88df0a08c087f8`, gallery version `0.2.0`. Baseline source revision `7ea22e89`. Screenshots were reviewed at native size and in contact sheets.

## Commands

| Command | Result |
| --- | --- |
| `node scripts/check-color-tokens.mjs` | Exit 0. `Color token ratchet passed: 8 stylesheets, 0 color literals.` |
| `node scripts/check-palette-contrast.mjs` | Exit 0, one PASS per palette. `Palette contrast passed: 10 palettes, 500 WCAG 2.2 AA pairs.` |
| `npm run validate:assets` | Exit 0. All 661 catalog GLB output lines ended in `0 errors, 0 warnings`. The six Chibi Visitor assets and three Pomelo Stem variants also reported zero errors and warnings. |
| `npm test` | Exit 0. `tests 744`, `pass 744`, `fail 0`, `cancelled 0`, `skipped 0`, `todo 0`. Both color checks passed in this command. |
| `npm run build:deploy` | Exit 0. `✓ built in 1.70s`. The existing Vite chunk-size advisory appeared. |
| `git diff --check` | Exit 0. |

A temporary CSS fixture confirmed that the ratchet rejected both `#bad` and `rgb(1 2 3)` as declarations, including before a nested rule. A selector named `#abc` remained valid. The test-generated `models/demo-beverage-can/reports/structure-motion.json` was restored byte-for-byte from HEAD after `git checkout` was denied by the read-only Git metadata sandbox.

## Browser coverage

Chromium `156.0.8078.4`, desktop 1440×900 and mobile emulation 390×844, using emitted production files and actual GLBs at the GitHub Pages subpath. The test supplied responses through Playwright request interception because the sandbox denied the preview server's localhost bind. The production CSP remained active.

- Gallery, Interactive Demos, About, Game and Tripo Chibi Motion Studio were rendered in Editorial Moss, Midnight Ink, Nordic Frost, Porcelain Sage and Sand Dune at both widths.
- Solar, Product Studio, Shelf Inspector and Chibi Motion were also captured in Editorial Moss, Nordic Frost and Sand Dune at both widths. Across all ten palettes, checks of computed text and control colors in the six demos passed for 500 desktop and 490 mobile pairs at 4.5:1 or higher.
- There are 74 route screenshots and four picker screenshots here. File names give palette, route and viewport width. Picker screenshots show keyboard focus and checked state in both schemes.
- The picker passed native radio arrow selection, 44px target checks, Escape, close-button and backdrop dismissal, focus restoration, cross-breakpoint closure, nested mobile Menu behavior and internal scrolling with its heading fixed. Chrome reported zero console errors or uncaught page errors across 48 route and persistence checks per width.
- Cross-tab synchronization, unknown IDs, and simulated denied storage passed. The saved Porcelain Sage background was `rgb(241, 243, 237)` both on the first styled frame and at `DOMContentLoaded`, with CSS delayed by 300 ms and JavaScript delayed by 900 ms. First paint was recorded after the styled frame at both sizes.

| Startup probe | First styled frame | First paint | DOMContentLoaded |
| --- | ---: | ---: | ---: |
| 1440 | 388.4 ms | 416 ms | 1063.8 ms |
| 390 | 345.7 ms | 352 ms | 1020.5 ms |

RGB comparisons against the baseline on all nine routes found zero changed pixels at 390px. At 1440px, the page content below the topbar had zero changed pixels. The desktop topbar differences came from the added Palette control and the navigation spacing. The baseline captures use the ordinary page state. The Editorial Moss Shelf focus outline was darkened for 3:1 contrast against the stage placeholder.

## CSP and PWA

The SHA-256 hash of the emitted startup script matched the CSP directive, and the script ran on delayed reloads under that policy. The emitted service worker's install handler verified all 65 shell entries against the actual build bytes in a Node harness, including the HTML with its CSP and the generated palette stylesheet.

Playwright blocked browser worker registration in the intercepted sessions. Browser installation, offline reload and live update were therefore unverified in this run. The browser reported worker-block warnings and non-blocking WebGL screenshot readback warnings. Physical iOS/Android startup, system and standalone status-bar appearance, keyboard behavior and hardware GPU results remain **UNVERIFIED**.
