# Gallery IA local acceptance

## Result and scope

Implemented and locally verified on `feature/gallery-information-architecture-v1` in the sibling `Blender-3D-Gallery-ia-v1` worktree, based on `38350b3933aa5d60bc7207d50b2e5577ae8781c3`. Changes remain uncommitted for review. No main-branch edit, push, merge, workflow trigger, deployment, production write or KB write was performed. The original worktree still has only its pre-existing untracked local plan.

The navigation now separates 3D Models, Interactive Demos and About, with GitHub external. Models have search, combined category/collection filters, result counts, reset/empty states, query-addressed independent detail, measured metadata, existing downloads, related models and viewer fallback/retry/fullscreen. The Demo Index has two registry-driven poster cards, category/search controls and explicit launch/return actions. Existing Game/Solar JavaScript behavior, all 39 model identities, source assets and legacy query links remain intact.

See [architecture and URL compatibility matrix](../gallery-information-architecture.md), [baseline](../gallery-ia-baseline.md) and [eleven-perspective review](gallery-ia-persona-review.md). The eleven personas are explicitly labeled analytical perspectives from one QA worker, followed by independent manager review; they are not eleven separate reviewers.

## Final executed checks

Final acceptance used macOS, Node **24.21.0**, Vite **8.3.5**, Three.js **0.187.0** and Playwright **1.64.1**. A clean `npm ci` succeeded in a task-owned temporary install directory; that installed `node_modules` was moved into the isolated worktree. `npm ls --depth=0` confirmed the four pinned dependencies. No dependency or lockfile change was required. The initial temporary `--prefix` install invocation failed; running from the temporary directory succeeded. Original checkout dependencies were not modified.

| Command / check | Observed result | Evidence |
| --- | --- | --- |
| `npm test` | 33 passed, zero failed | `/tmp/b3g-final-unit.log` |
| `npm run build` | All catalog assets validated; production build passed | `/tmp/b3g-final-build.log` |
| `npm run test:library` | Nine scenarios passed, zero uncaught page errors | `/tmp/b3g-final-library.log`; `/tmp/b3g-ia-final/library/results.json` |
| `npm run test:browser` | 14 Game/gallery scenarios passed, including WebKit shot smoke | `/tmp/b3g-final-browser.log`; `/tmp/blender-gallery-game-qa/results.json` |
| `npm run test:pwa` | Nine scenarios passed, including cold offline start, integrity failures, guarded update and previous-pack preservation | `/tmp/b3g-final-pwa.log` |
| `node scripts/test-solar-scene.mjs` with external artifact directory | 1440, 768, 390 and 320 px scene scenarios passed | `/tmp/b3g-final-solar-scene.log`; `/tmp/b3g-ia-final/solar-scene/` |
| `npm run test:solar` | All 17 current Solar GLBs passed asset/loader/geometry checks | `/tmp/b3g-final-solar-assets.log`; `/tmp/b3g-ia-final/solar-assets/` |
| axe-core 4.14.0 WCAG A/AA tagged checks | Five sampled 390 px routes had zero automated violations; manual-review incompletes retained | `/tmp/b3g-axe-results.json`; `/tmp/b3g-final-axe.log` |
| `git diff --check`, JS syntax and final diff review | Passed; no model, source binary, lockfile or deployment-workflow diff | Git/source inspection |

The Solar asset test writes timestamped reports to the source tree by default. Final reports were copied into the external evidence directory before reverting only those task-generated report changes. Its visualReview field reuses existing hash-matched visual approvals; it is not a new manual review of all 17 artworks.

## UI, loading and rendering evidence

- Baseline and final index screenshots cover exactly 320×720, 390×844, 430×932, 768×1024, 1024×768, 1440×900 and 1920×1080. Final model/demo captures are in `/tmp/b3g-ia-final/library/`, and baseline gallery captures in `/tmp/b3g-ia-baseline/`. Viewport screenshots were used because the long one-column gallery exceeds Chrome's full-page capture capacity. No failed full-page capture is counted as a pass.
- Each static index retains 39 models or two demos, with zero initial GLB requests, zero canvas and no horizontal document overflow. These are application-request observations in fresh headless Chromium contexts with Service Workers blocked, on unthrottled localhost under the actual `/Blender-3D-Gallery/` subpath. PWA behavior was checked separately with Service Workers enabled.
- Search normalization, combined filters, empty/reset behavior, URL restoration/reload, legacy model links, related links, Back/Forward, demo launch/refresh/return and canvas disposal were exercised. Expected error tests cover a 503 GLB failure with retry, absent WebGL and unknown model ID.
- Keyboard checks cover menu focus containment, Escape, backdrop, focus return, scroll unlock, route navigation and model dismissal. Native dialog close state is awaited rather than asserted before its asynchronous close event.
- Viewer readiness now requires actual GL draw calls. Manager independently measured positive draws for Ball 08 and Earth after fixing a scheduler initialization defect; an idle viewer stops drawing, and reset causes another render. Leaving Game/Solar removes their canvas and stops draw-call growth. Representative baseline/final Ball 08 and Earth renders were visually compared; original lighting, tone mapping, materials and geometry were preserved. This does not prove fidelity on every GPU.
- Game now budgets its 44 px return row in the table height. Strengthened original touch checks measure Confirm cue/Pause during placement and Shoot/Pause during aiming at scroll position zero, requiring nonzero rectangles fully inside 320×568, 390×844 and 844×390 viewports. Existing first-entry complete-table, save/recovery, physics/gameplay, ownership and context-loss assertions remain.
- Final built entry: **72.22 kB raw / 15.13 kB gzip**, versus baseline **52.48 / 12.08 kB**; the increase includes model metadata, registries and discovery UI. Shared Three.js chunk remains **639.05 / 158.89 kB** and lazy activation is retained. The build's existing >500 kB shared-chunk warning is disclosed; no measured speedup is claimed.

The final locally served build identity is `330883a6822334a3`. Preview was started on `http://127.0.0.1:4178/` and its build-info response was verified. This identifies the local artifact, not a production release.

## Findings resolved and remaining limits

Resolved confirmed findings: filter reset/state inconsistency, blank viewer despite loaded canvas, low-contrast faint text, disconnected related-link focus return, duplicate demo launch routes, and Game clipping caused by the new return row. A dormant unavailable-demo branch was corrected so its poster/title cannot bypass unavailable status. No unresolved P0/P1 defect was observed in the executed scope.

Not measured or not established: production LCP/CLS/INP, future hundreds-of-model search benchmarks, sustained physical mobile GPU/memory behavior, physical iOS/Android installed-app behavior, real browser 200% zoom and complete WCAG 2.2 AA compliance. A 512 px equivalent half-width reflow check and reduced-motion emulation passed, but neither is proof of real browser zoom or every assistive-technology combination. Axe incomplete items are retained as manual-review prompts, not converted into passing conformance claims.

Artwork redistribution terms remain an owner decision. Existing downloads expose files without granting a new license. Further real-device validation and any future publication require their own evidence and authorization; this local task does not perform them.
