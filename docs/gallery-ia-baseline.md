# Gallery information architecture baseline

## Scope and isolation

- Inspected revision: `38350b3933aa5d60bc7207d50b2e5577ae8781c3` (`main`).
- Original worktree: `Blender-3D-Gallery`; only pre-existing change was untracked `docs/game-implementation-plan.local.md`. It was left in place and excluded from this work.
- Development worktree: sibling `Blender-3D-Gallery-ia-v1`, branch `feature/gallery-information-architecture-v1`.
- Authorization: local implementation and verification only; no production modification, push, merge, deployment or KB write.
- Read-only KB workflows loaded: `agent:auto-manager`, `agent:delegate-and-follow-up`, coding and UI routing hubs. The explicit current task overrides the manager skill's historical release/KB defaults. In-process workers implement bounded file sets; the manager independently accepts results. No delayed scheduler or future background completion is promised.

## Observed implementation

Vite 8.3.5, native JavaScript ES modules and Three.js 0.187.0. No React, TypeScript, backend, database or CMS. `package-lock.json` v3 pins dependencies; dev tools are Playwright 1.64.1 and gltf-validator 2.0.0-dev.3.10. Tests use Node's test runner plus standalone Playwright scripts. Local Node was 23.10.0; README/CI specify Node 24. Local Node satisfies Vite's declared engine range, but Node 24 execution is separately reported if performed.

`index.html` provides the static shell. `src/main.js` creates cards and owns query-based navigation and the model dialog. `src/viewer.js` dynamically imports Three.js controls/loader and renders one selected model. Game and Solar modules load only on their routes. Game has independent planar physics/rules, IndexedDB stable-turn checkpoints and a prepared offline pack. Solar composes 17 independent GLBs with circular orbits, two display scales and selection; it is an illustration, not an ephemeris.

`models/catalog.json` owns 39 identities: 21 individual billiards assets, one assembled billiards scene and 17 Solar System assets. Source `.blend`, exports, previews, metadata and authoring generators remain in `models/`. Build-time `scripts/catalog.mjs` computes bytes and triangles; the Vite virtual catalog resolves asset URLs. Baseline model directory is approximately 137 MiB; built artifact approximately 47 MiB. Authoring scripts were inspected as source references, not executed.

The build-time PWA plugin emits integrity-hashed shell/pack data and a Service Worker. Installation caches shell JS/CSS/icons, not every GLB. Explicit Game offline preparation caches 18 Game GLBs. Solar GLBs remain online-only. Retain that contract.

## Routes before change

| URL | Baseline behavior |
| --- | --- |
| `/Blender-3D-Gallery/` | Editorial hero and grouped gallery |
| `#collection` | Gallery collection anchor |
| `#about` | Gallery About section |
| `?model=<asset-id>` | Independent GLB viewer dialog |
| `?page=game` | Local two-player casual eight-ball |
| `?page=solar` | Solar System interactive atlas |

Vite uses relative base `./`. GitHub Pages workflow deploys `dist/` after a `main` push or explicit workflow dispatch. This task does not change or trigger that workflow. Static hosting has no general pathname rewrite; keep query routes and old asset identities.

## Baseline execution evidence

- `npm test`: 23 passed, zero failed.
- `npm run build`: asset validation and Vite build passed. Existing shared Three.js chunk warning: 639.05 kB raw / 158.89 kB gzip. Entry chunk 52.48 kB raw / 12.08 kB gzip.
- `npm run test:browser`: 14 checks passed, including Chromium game lifecycle, touch layouts, IndexedDB ownership/recovery, all 39 independent model previews/downloads and WebKit shot smoke.
- Seven exact gallery screenshot viewports: 320×720, 390×844, 430×932, 768×1024, 1024×768, 1440×900, 1920×1080. At each: 39 cards, zero GLB requests, zero canvas, no horizontal overflow, no page errors.
- Local running Game and Solar were loaded and captured at 1440×900. Production gallery HTML was fetched read-only; its entry bundle matched the baseline build name, and a production desktop screenshot was captured.
- Baseline screenshots/logs: `/tmp/b3g-ia-baseline/`, `/tmp/b3g-baseline-unit.log`, `/tmp/b3g-baseline-build.log`, `/tmp/b3g-baseline-browser.log`. Full-page capture initially exceeded Chrome screenshot capacity for the long gallery; viewport captures succeeded. No screenshot failure is counted as a pass.

## Design tokens and layout

Preserve background `#111513`, primary text `#e8eae3`, accent `#c7e39c`, muted text `#929b92`, line `#343c36`; Georgia serif display headings and system sans-serif body. Existing shell max width 1320 px, desktop side clearance 48 px and narrow clearance 20 px. Thin dividers, uppercase labels, quiet borders, original brand mark, no new font service. Baseline card grid: 4 columns desktop, 3 at 900 px, 2 at 650 px. Actual new controls/menu will be checked at all seven requested sizes.

## Confirmed gaps, risks and decisions

| Priority | Kind | Evidence and impact | Decision / acceptance |
| --- | --- | --- | --- |
| P1 | Confirmed product gap | No model search/filter or Demo Index; every demo is top-level navigation | Add registry-driven model and demo discovery; launch one demo at a time |
| P1 | Confirmed accessibility gap | Narrow CSS hides About and GitHub | Modal navigation exposes all links, restores focus, supports Escape and backdrop |
| P2 | Confirmed content gap | Model dialog offers minimal metadata, Solar attribution text only | Show measured metadata and actual rights disclosures without fabricated license claims |
| P2 | Supported scaling risk | Every future demo would require a top-level item | Two primary areas, registry-driven index, explicit lazy module mapping |
| P2 | Existing performance limit | Shared 639 kB Three.js chunk | Preserve on-demand loading; measure new index requests, do not recompress original artwork speculatively |
| P2 | Untested hardware | Desktop software WebGL does not represent mobile GPU or installed iOS PWA | Disclose actual browser/device scope; no unmeasured CWV or WCAG conformance claims |

Original artwork redistribution terms are pending. Preserve existing file availability and display the pending terms; do not invent a permissive license or publish new assets. There are no external runtime registry requests. Unknown model/route cases need useful recovery, and malformed registry data must fail during validation.

Additional baseline results: PWA suite passed all nine scenarios (offline cold start, 18-file integrity pack, update refusal/recovery and multi-tab coordination). Solar asset suite passed all 17 assets. The solar test writes time-varying source report files by default; its task-generated timestamp changes were removed after inspection. Final verification directs artifacts to `/tmp/` to avoid replacing retained source reports.
