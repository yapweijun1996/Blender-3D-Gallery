# GJH furniture verification

Date: 2026-11-12. Authoring: Blender 5.2.3 LTS on macOS ARM64. Browser validation uses a production Vite build served under `/Blender-3D-Gallery/`, Chromium 156.0.8078.4 with SwiftShader. This report describes a proposed PR, not a merged or deployed library release.

| Check | Result | Evidence |
| --- | --- | --- |
| Original sources regenerated | PASS | `generate.py`; source .blend, GLB and studio preview for each model |
| Source files reopened | PASS | [reports/sources.json](reports/sources.json); 30 bench parts, 213 planter parts; floor origin and metre scale |
| Khronos GLB validation | PASS | [reports/assets.json](reports/assets.json); both exports have zero errors and warnings |
| Geometry/material budget | PASS | 354,048 combined bytes, 10,800 combined triangles, 5/6 material primitives, no external resources |
| Unit tests | PASS | `npm test`: 90 passed, zero failures |
| Production build | PASS | `npm run build`: all 56 catalog GLBs validated; 5 collections; existing >500 kB chunk-size advisory remains |
| Furniture browser tests | PASS | `node scripts/test-gjh-furniture.mjs`: 9 cases at 1440, 768 and 390px; [browser report](reports/browser.json) |
| Existing model-library regressions | PASS | `npm run test:library`: 9 cases, including existing demo navigation, failed-model retry, no-WebGL recovery and responsive indexes |

The focused browser tests check decoded thumbnails, search/collection discovery without eager GLB downloads, real exported response hashes, completed WebGL draws, canvas bounds, keyboard orbit/zoom, reset, direct-link reload, Escape focus return, render-loop disposal, reopen and truthful rights/download states. Saved screenshots were reviewed separately from automated assertions.

Independent screenshot review found complete framing and materials for both models at desktop, tablet and mobile sizes, including rotated views. The scoped model/viewer presentation scored 88/100 under the KB UI taste rubric (hierarchy 18/20, spacing 17/20, typography 13/15, color 13/15, consistency 14/15, responsiveness 13/15). This is a subjective review, not a measured usability score. Duplicate introductory description text found during review was removed. The planter is deliberately stylized; physical botanical accuracy and photorealism are not claimed. Existing library mobile landing-page density was not redesigned by this asset addition.

The website consumes only the two registered GLBs and their WebP posters; editable `.blend` files and authoring scripts remain in the repository. Geometry and materials are original and deterministic. Preview studio lights and floor are excluded from GLB export. There are no NASA, Proton, GJH-logo or other third-party resources in this collection.

Owner-project reuse is authorized. Public redistribution terms remain unspecified. Hiding a download button is a presentation choice, not access control: the viewer necessarily serves the GLB publicly.

Physical-phone GPU performance, touch hardware, Safari, screen-reader sessions and real-device installation were not tested for this addition. Existing game physics, solar demos and PWA behavior are unchanged; their full specialist suites were not rerun for these asset-only additions. The repository's existing deployment workflow triggers on `main` or manual dispatch, not PRs, so local evidence must not be represented as a successful PR Actions run. Merge and subsequent Pages deployment are outside this PR's completed state.
