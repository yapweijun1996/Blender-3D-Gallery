# Verification: GJH Abalone Cans

Run on 2026-11-13 with Blender 5.2.3 LTS on macOS arm64.

| Check | Result |
| --- | --- |
| `generate.py` regenerates all four GLBs, textures, `.blend` and previews | PASS |
| `node models/gjh-abalone-cans/validate.mjs` (Khronos validator 2.0.0-dev.3.10, parts, UVs, bounds, budgets) | PASS: 0 errors, 0 warnings, 2,490 triangles each |
| `npm test` | PASS (all suites, including `tests/gjh-abalone-cans.test.mjs`) |
| `npm run validate:assets` and `npm run build` | PASS |
| Real browser (Chromium via Playwright, Vite dev server): `?model=<slug>` at 1440, 768 and 390 px wide | PASS: label texture visible, model rotatable viewer opens, 0 console errors |

## Not verified

- Appearance on physical phones or non-Chromium engines.
- The label is a single-view unroll of 1000 px packshots, so small print is soft. Judged by eye in the viewer and Blender previews only.
- Current packaging edition, certification validity and redistribution terms. Packaging artwork is used on the owner's confirmation only (see README, Rights).
- No deployment was checked. A push to `main` is not evidence of a live GitHub Pages release.
