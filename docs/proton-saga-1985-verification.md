# Proton Saga (1985) asset integration

## Scope

Add one original Blender exterior study of the 1985 Proton Saga four-door sedan to the existing gallery catalog under the Proton Heritage collection. The model uses approximate proportions and simplified details. It represents the original sedan, rather than later Iswara, LMST, Aeroback or facelift versions. No mechanical, engineering-scale or trim-level accuracy is claimed.

The model remains part of the existing lazy-loaded gallery and viewer flow. Its identity is `proton-saga-1985`; the existing legacy deep link is `?model=proton-saga-1985`.

Catalog metadata validation now resolves identity using `solarId` when present and the catalog asset `id` otherwise. This retains existing Solar aliases while allowing metadata on other asset collections. Registry coverage checks the Saga identity, attribution, accuracy notes and disabled download policy. Full-catalog browser expectations derive their count from the registry so adding a genuine asset does not leave stale fixed-count checks.

## Artifacts and provenance

- Editable source and reproducible generator: `models/proton-saga-1985/scene.blend` and `generate.py`.
- Viewer asset: `models/proton-saga-1985/exports/proton-saga-1985.glb`.
- Catalog preview: `models/proton-saga-1985/preview.webp`.
- Asset-specific accuracy and attribution: `models/proton-saga-1985/metadata.json` and `README.md`.
- Historical launch reference: [Proton official milestones](https://www.proton.com/corporate/milestones).

This is an independently created artistic study with no official endorsement. Artwork redistribution terms remain pending, and the catalog disables the download action. This flag controls the interface; it does not prevent a browser from obtaining a GLB served for viewing.

## Verification status

The manager independently executed the following checks on the local production build:

| Check | Observed result |
| --- | --- |
| `npm run build` | Passed; all 40 catalog GLBs validated with zero errors and zero warnings. Vite retains the shared Three.js/OrbitControls chunk size warning at approximately 639 kB. |
| `npm test` | 76 passed, zero failed. |
| `npm run test:library` | Nine scenarios passed, including all 40 cards at seven viewport sizes and existing model/demo loading, fallback and navigation regressions. |
| `node scripts/test-saga-browser.mjs` | Desktop 1440×900 and mobile 390×844 scenarios passed: lazy search, actual GLB load and WebGL draws, rotation, zoom, reset, focus, direct link and reload. No network or console errors were observed in these scenarios. |
| Visual inspection | Manager inspected the Blender render and desktop/mobile browser images, including the front three-quarter presentation. Browser evidence is stored under `/tmp/blender-gallery-saga-qa`. |

Measured Saga export: **1,561,472 bytes**, **56,946 triangles**, **44,320 stored vertices**, **8 materials** and **0 animation clips**. The WebP preview is **1400×1000**, approximately **41 kB**. These measurements describe the exported asset; it is a static exterior study.

The browser checks use Chromium, mobile viewport emulation and mouse interactions. Physical iOS/Android devices, installed PWA behavior and physical touch gestures were not tested. The existing PWA standard test's full-catalog expectation was updated from 39 to 40; this update alone is not evidence that its entire suite was re-executed.

Metadata selects the front three-quarter preview orientation. After this final metadata adjustment, the manager re-ran the production build and Saga desktop/mobile browser checks; both completed successfully with exit code zero. The manager also inspected the updated front three-quarter browser screenshot.

No release commit, push or public deployment is claimed by this document.

Pre-existing unrelated working-tree changes must be preserved. This task does not authorize rewriting unrelated Solar reports or Game work.
