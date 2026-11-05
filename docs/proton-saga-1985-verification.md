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

## Initial asset verification (before silver showcase revision)

The manager independently executed these checks on the initial red exterior study. They do not establish verification of the subsequent silver showcase revision:

| Check | Observed result |
| --- | --- |
| `npm run build` | Passed; all 40 catalog GLBs validated with zero errors and zero warnings. Vite retains the shared Three.js/OrbitControls chunk size warning at approximately 639 kB. |
| `npm test` | 76 passed, zero failed. |
| `npm run test:library` | Nine scenarios passed, including all 40 cards at seven viewport sizes and existing model/demo loading, fallback and navigation regressions. |
| `node scripts/test-saga-browser.mjs` | Desktop 1440×900 and mobile 390×844 scenarios passed: lazy search, actual GLB load and WebGL draws, rotation, zoom, reset, focus, direct link and reload. No network or console errors were observed in these scenarios. |
| Visual inspection | Manager inspected the Blender render and desktop/mobile browser images, including the front three-quarter presentation. Browser evidence is stored under `/tmp/blender-gallery-saga-qa`. |

Initial export measurements (superseded by the silver asset below): **1,561,472 bytes**, **56,946 triangles**, **44,320 stored vertices**, **8 materials** and **0 animation clips**. The WebP preview is **1400×1000**, approximately **41 kB**. These measurements describe the exported asset; it is a static exterior study.

The browser checks use Chromium, mobile viewport emulation and mouse interactions. Physical iOS/Android devices, installed PWA behavior and physical touch gestures were not tested. The existing PWA standard test's full-catalog expectation was updated from 39 to 40; this update alone is not evidence that its entire suite was re-executed.

Metadata selects the front three-quarter preview orientation. After this final metadata adjustment, the manager re-ran the production build and Saga desktop/mobile browser checks; both completed successfully with exit code zero. The manager also inspected the updated front three-quarter browser screenshot.

## Silver heritage showcase revision

The owner supplied two heritage showcase images as visual guidance and requested a more polished vehicle with consistent front, rear, left and right presentation. These images guide the exterior interpretation; their text, dimensions and specifications are not treated as independently verified historical facts, and the images are not embedded in the asset or site.

The viewer adds a vehicle-only charcoal studio stage with grounded shadows, consistent lighting and camera fitting to the model bounds. Four native buttons select Front, Rear, Left and Right, with keyboard support, a selected-state label and touch targets at least 44 pixels tall. Free 360-degree rotation, zoom, reset and the existing loading/error recovery remain available. Closing the viewer disposes its vehicle controls and rendering resources. Other gallery assets retain their existing presentation.

The preset axes follow the actual Blender export: front is Blender -X, left is Blender -Y, then the exported glTF orientation and metadata preview rotation are applied. The four views depict one shared model rather than separately generated illustrations.

The silver GLB independently measured **2,089,168 bytes**, **57,325 triangles**, **53,775 stored vertices**, **13 materials** and **0 animation clips**. Its validator result is **zero errors and zero warnings**. The 1400×1000 preview is **49,156 bytes**. Four matching Blender studio renders are retained as `view-front.webp`, `view-rear.webp`, `view-left.webp` and `view-right.webp`.

The manager inspected the final silver preview, genuine front/rear/left/right Blender renders and desktop/mobile browser screenshots. The final vehicle body is free of the previously observed shadow acne; the matching studio floor has no visible horizon bar. Vehicle meshes cast onto the floor without receiving self-shadows.

Independent final acceptance after that shadow refinement:

| Check | Observed result |
| --- | --- |
| `npm test` | 76 passed, zero failed. |
| `npm run build` | Passed; all 40 catalog GLBs validated with zero errors and zero warnings. |
| `node scripts/test-saga-browser.mjs` | All four viewports passed: desktop 1440, tablet 768, mobile 390 and narrow 320 pixels. Each exercised four presets, keyboard activation, dialog top/middle/bottom scrolling, persistent close visibility, free rotation, zoom, reset, direct link and reload. All GLB responses completed; no browser, network or console errors were observed. |
| `npm run test:library` | All nine existing library regression scenarios passed. |
| Visual inspection | Final desktop/mobile screenshots and four genuine Blender angle renders inspected by the manager. |

These checks use Chromium viewport emulation and mouse/keyboard interactions. They do not establish physical iOS/Android touch or installed-PWA behavior. Initial red asset measurements above must not be reused for this revision.

## Release integration

The initial Saga changes were committed and pushed as `284a192`. Deployment was stopped by an inherited Game mobile layout failure at 360×800; no failed check was bypassed. The owner authorized a minimal independent fix, committed as `1beabe0`. The manager independently passed the Game browser suite (including WebKit) and ten responsive touch journeys after that fix. The original working tree and its unrelated uncommitted files were kept separate from the release worktree.

Final public deployment of the polished showcase remains pending; no successful live release is claimed here.

Pre-existing unrelated working-tree changes must be preserved. This task does not authorize rewriting unrelated Solar reports or Game work.
