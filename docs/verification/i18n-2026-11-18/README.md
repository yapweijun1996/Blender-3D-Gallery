# Interface language verification

Chromium 156.0.8078.4 loaded production build `1d920b32ecee4033` (`v0.2.0`) at the GitHub Pages subpath with the emitted HTML, CSS, scripts and real GLBs. Playwright request interception supplied those files because the sandbox denied the localhost bind. The browser retained the production CSP. The test used emulated touch at 375 px and reduced motion for stable captures.

| Viewport | Route × language checks | Console or page errors | Layout findings |
| --- | ---: | ---: | ---: |
| [375 × 812](chromium-375.json) | 27 | 0 | 0 |
| [768 × 1024](chromium-768.json) | 27 | 0 | 0 |
| [1440 × 900](chromium-1440.json) | 27 | 0 | 0 |

The matrix covers Gallery, Demos, About, Game, Solar System, Product Studio, Shelf Inspector, Chibi Motion Studio and Tripo Chibi Motion Studio in English, 简体中文 and Bahasa Melayu. It checks the translated heading and document title, idle and switched layout, live selection without document reload, and locale restoration on reload. The default opened in English with a `zh-CN` browser preference.

The [81 page captures](pages/) include the full Demos index at each width. The [23 control captures](controls/) include the mobile Menu, language picker, Palette, filtered library, real GLB viewer, Game rules, install help and an available Update state. The page and control captures were inspected at the tested widths. The final pass includes the narrow Update layout, bounded Solar selectors, compact Game focus rings, and shorter or balanced Chinese and Malay copy where the screenshots showed awkward wraps.

## Interaction checks

- Arrow keys selected a locale in the native radio group. Escape restored focus to the opener, including inside the mobile Menu at 375 and 768 px.
- Delaying the entry scripts by 700 ms on Gallery reload showed the requested `lang` while the shell was hidden. Its visible text appeared in the saved language. The browser reported zero CSP violations.
- A second same-origin tab changed the live locale in the first tab while its model viewer was open. The model name, canvas and filter value stayed in place, and the aria-labels and metadata labels changed. An invalid preference restored English.
- The active Game match stayed in its existing phase with the same player and balls. The Tripo animation clip and timeline, Solar body and scale, Product pose and label, and Shelf fixture and unsaved text stayed selected during a language change. Demos search matched a Chinese tag and its original English tag.
- A staged waiting-version UI event rendered the full localized `v1.2.3` action and accessible label, including the compact topbar and the mobile Menu. The Malay install help displayed from Game options.
- Against a local build of the pre-change source, the visible area below the header was pixel-identical on English Gallery, Demos and About at all three widths. The new picker, minimum target sizing and the corrected demo and dialog layouts are visible in the current captures.

## Command results

```text
$ node scripts/check-i18n.mjs
i18n OK: 652 messages × 3 languages, matching placeholders, 20 UI sources checked.

$ node scripts/check-color-tokens.mjs
Color token ratchet passed: 9 stylesheets, 0 color literals.

$ node scripts/check-palette-contrast.mjs
Palette contrast passed: 10 palettes, 500 WCAG 2.2 AA pairs.

$ npm test
ℹ tests 744
ℹ pass 744
ℹ fail 0
```

`npm run validate:assets` exited 0. Its 661 catalog validation lines each reported `0 errors, 0 warnings`, and the two supplemental validators exited successfully.

`npm run build:deploy` exited 0. Vite 8.3.5 reported `✓ 1447 modules transformed.` and `✓ built in 2.78s` along with its existing chunk-size warning. The emitted HTML contained two inline bootstraps with two matching SHA-256 hashes and no `unsafe-inline` script allowance. Negative checks in a temporary copy showed that the i18n gate rejects a missing locale key, an extra key, placeholder drift and hard-coded copy in HTML or a checked DOM assignment.

The requested report checkout encountered a sandbox denial on `.git/index.lock`. The tracked report was restored from its HEAD bytes and verified with `git diff --exit-code -- models/demo-beverage-can/reports/structure-motion.json`.

## Scope limits

The intercepted browser sessions blocked service worker registration. Actual service worker installation, offline pack preparation, waiting-worker activation and OS-owned PWA installation remain for `npm run test:standard`, `npm run test:pwa` and physical-device testing outside this sandbox. The browser emitted expected service worker and software-WebGL warnings. Individual asset-specific controls and simulated failure branches received source checks and selected browser exercises.
