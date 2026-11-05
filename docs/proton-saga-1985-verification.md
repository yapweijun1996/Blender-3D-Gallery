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

## Released silver heritage showcase revision (`eb6ce80`)

The owner supplied two heritage showcase images as visual guidance and requested a more polished vehicle with consistent front, rear, left and right presentation. These images guide the exterior interpretation; their text, dimensions and specifications are not treated as independently verified historical facts, and the images are not embedded in the asset or site.

The viewer adds a vehicle-only charcoal studio stage with grounded shadows, consistent lighting and camera fitting to the model bounds. Four native buttons select Front, Rear, Left and Right, with keyboard support, a selected-state label and touch targets at least 44 pixels tall. Free 360-degree rotation, zoom, reset and the existing loading/error recovery remain available. Closing the viewer disposes its vehicle controls and rendering resources. Other gallery assets retain their existing presentation.

The preset axes follow the actual Blender export: front is Blender -X, left is Blender -Y, then the exported glTF orientation and metadata preview rotation are applied. The four views depict one shared model rather than separately generated illustrations.

The released `eb6ce80` silver GLB independently measured **2,089,168 bytes**, **57,325 triangles**, **53,775 stored vertices**, **13 materials** and **0 animation clips**. Its validator result is **zero errors and zero warnings**. The 1400×1000 preview is **49,156 bytes**. Four matching Blender studio renders are retained as `view-front.webp`, `view-rear.webp`, `view-left.webp` and `view-right.webp`. These measurements are historical and must not be reused for the subsequent reference-fidelity iteration below.

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

## Released reference-fidelity iteration (`7dc9f06`)

The owner requested another comparison against the same two supplied images, focusing on body proportions, lamps, wheels and glazing. The model revision targets a lower shoulder line and taller tapered glazing, thinner body-colored pillars and black seals, a separate rear quarterlight, reflector bowls and clear headlamp lenses, smaller recessed pressed-steel rims, parked wipers near the windscreen base, and continuous body-side molding. Front, rear, left and right are checked against the same shared geometry and reference criteria.

The Saga viewer now generates a local studio reflection environment with Three.js `RoomEnvironment` and `PMREMGenerator`. It supplies form-defining reflections for metallic paint and steel wheels while retaining the charcoal background and existing camera controls. Environment intensity is 0.6. No remote image or additional network request is used. Temporary room geometry/materials and the PMREM generator are released after generation; the retained environment render target is released, and `scene.environment` cleared, when the viewer closes or fails. The change applies only to this vehicle.

Opaque export batching reduces the cost of the added detail while transparent glazing remains separate. The manager measured **26 nodes** and **25 meshes** in the resulting export. Material separation and actual browser output remain part of acceptance.

This iteration remains an artistic reconstruction with approximate dimensions. Reference-image labels and specifications are not independently verified engineering measurements. The model does not claim an exact factory trim, scanned surface accuracy, working mechanical parts or physical-device compatibility.

The manager independently measured **2,594,816 bytes**, **72,152 triangles**, **67,063 stored vertices**, **16 materials** and **0 animation clips** for this iteration. Khronos validation reported **zero errors and zero warnings**. `npm test` passed **77 tests**, and the production build validated all **41 catalog GLBs**. The Saga browser checks passed at all four viewports, and all nine library regression scenarios passed.

The manager inspected the four browser views and confirmed the model and material improvements. Side-view ground shadows initially showed a small visible separation from the tires. A final viewer-only precision refinement narrows the directional shadow camera depth range to 0.1–30 meters and reduces normal bias to 0.003 and bias to -0.00002. Vehicle meshes continue to cast onto the floor without receiving self-shadows; no contact decal is added.

After that final shadow refinement, the manager independently re-ran the production build and all four Saga viewport scenarios; both completed with exit code zero. Logs are stored at `/tmp/saga-detail-verified-build.log` and `/tmp/saga-detail-verified-browser.log`. The manager inspected the resulting default, front, rear, left and right browser screenshots, confirming view directions, visible lamp bowls, inset steel wheels, continuous molding and clear panes. An additional Three.js `GLTFLoader`/`Box3` check measured tire minimum Y at 0 and the displayed floor at -0.00617 meters, ruling out raised tire geometry. These checks establish the observed rendering and geometry; they do not claim physically perfect shadow contact or photorealism.

## Surface-fidelity iteration (local acceptance)

The next model-only revision refines the same owner-supplied references: formed body shoulders and visible surface-fitted door seams, connected window reveals, lightly bowed rounded glazing, smaller rear quarterlights, flatter pressed-steel wheel centers with actual oval openings, finer headlamp fluting, richer amber/red lamps, true front apron intakes and a rear plate panel between the tail lamps. The source retains editable parts and reproduces the GLB plus five matching 1400×1000 studio views. No viewer behavior, reference-image pixels or third-party meshes were added.

Final export measurements independently match `metadata.json`: **2,983,952 bytes**, **84,080 triangles**, **77,352 stored vertices**, **16 materials**, **23 meshes / 24 nodes** and **0 animation clips**. The GLB uses the optional `KHR_materials_specular` extension. Its SHA-256 is `0df936d7ca1eb47cb71e9b9638edb118ff81461cce68590297f8572c3c93c127`.

The final geometry, metadata, five renders and saved Blender source were frozen before acceptance. Upstream NASA candidate additions at `4ff550f` and Game fixes at `715b5e8` were integrated without changing those Saga artifacts. All checks below were re-executed against the rebuilt distribution on the final `715b5e8` base; earlier-base results are not the final acceptance evidence for this revision.

| Check | Observed result |
| --- | --- |
| `npm test` | 78 passed, zero failed. |
| `npm run build` | Passed; all 52 catalog GLBs validated with zero errors and zero warnings. The shared Three.js/OrbitControls chunk retains a size warning, approximately 641 kB. |
| `node scripts/test-saga-browser.mjs` | Passed at 1440×900, 768×1024, 390×844 and 320×720. Actual GLB loading/WebGL draws, all four view presets, keyboard activation, scrolling/close visibility, rotation, zoom, reset, focus, direct link and reload were exercised. All GLB responses completed; no browser, console or network errors were recorded. |
| `npm run test:library` | All nine existing regression scenarios passed, including 52-card indexes at seven viewport sizes, search/filter/navigation, loading fallback, legacy demos and reduced-motion/reflow behavior. |
| Visual inspection | The manager and independent reviewer inspected the final Blender views. Actual browser front/rear/left/right views showed consistent clear panes without black centers, visible oval wheel openings on both sides, continuous door seams, and distinct red/amber lamps. Mobile front/right screenshots retained usable controls and a complete silhouette. |

Logs are `/tmp/saga-surface-tests.log`, `/tmp/saga-surface-build.log`, `/tmp/saga-surface-browser.log` and `/tmp/saga-surface-library.log`; browser evidence is under `/tmp/saga-surface-browser-qa` and `/tmp/saga-surface-library-qa`. These are local Chromium/SwiftShader checks with service workers blocked. Physical phones, physical touch and installed-PWA behavior remain unverified.

The inherited directional studio shadow can look separated from a near tire in some views. An independent `GLTFLoader`/`Box3` check found tire minimum Y at 0 and the floor at approximately -0.00617 meters, unchanged from the preceding model; there is no raised-wheel geometry regression. Shadow contact and surface reconstruction remain approximate. These checks describe the local release candidate; deployment is established separately by a successful Pages run and a matching live GLB hash.

## Release integration

The initial Saga changes were committed and pushed as `284a192`. Deployment was stopped by an inherited Game mobile layout failure at 360×800; no failed check was bypassed. The owner authorized a minimal independent fix, committed as `1beabe0`. The manager independently passed the Game browser suite (including WebKit) and ten responsive touch journeys after that fix. The original working tree and its unrelated uncommitted files were kept separate from the release worktree.

The silver showcase was subsequently committed as `eb6ce80391e5371f29db1780b83976c66d86798a` and successfully deployed by GitHub Pages workflow run `42035418409`. The manager checked the live vehicle at desktop 1440×900 and mobile 390×844, including all four preset controls and reset. The actual online GLB SHA-256 was `42d8c0466dfbfb4cfc3a7b6f59c805d1840ac6268a63056b96016855c88fe1cb`, matching the released artifact. That successful release supersedes the earlier pending deployment state; it does not establish deployment of the new reference-fidelity iteration.

The reference-fidelity iteration was subsequently committed as `7dc9f06a067551d89c280e38ba2f52986ca7f848`. GitHub Pages workflow run `42043016925` completed successfully; deployment `7576157218` targets that revision. During the following surface-refinement task, an independent check confirmed the public GLB returned HTTP 200 with **2,594,816 bytes** and SHA-256 `bcaa2234f580d9a3e3ae8cb0916de3fe52444b344eea7bbe07c2003373963c40`, matching the released artifact. This establishes publication of `7dc9f06`, not any later edits.

Pre-existing unrelated working-tree changes must be preserved. This task does not authorize rewriting unrelated Solar reports or Game work.
