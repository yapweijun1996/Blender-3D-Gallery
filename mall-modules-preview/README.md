# Mall module preview

A local interactive preview of nine Gallery assets and a corridor assembled from their exported GLBs. Start the project with `npm run dev`, then visit `/mall-modules-preview/` on the local Vite server.

The wall selection is the new 1.2 m solid wall; the corridor also retains the existing glass partitions for the shopfronts. The ceiling is intentionally a partial cutaway for visibility. This visual arrangement is not a construction or safety specification; see the individual asset READMEs and `docs/verification/p0-assembly/README.md` for actual dimensions, interfaces, prior checks, and rights. The preview does not change or export source assets, and it is not part of the production Gallery build.

The corridor also loads existing shopfront doors and fascia, ceiling light fixtures, lounge bench, planters, display shelves, directory and advertising lightbox. Each light replaces one ceiling panel following the fixture's documented placement; separate Three.js lights provide scene illumination. The two store names are fictional preview labels. The earlier individual views remain available alongside the corner floor tile and mitred trim; C1–C4 are display labels, not backlog IDs. These additions are visual context; their placement has not been certified for collision, navigation or construction.

The front and right floor edges use `mall-floor-edge-trim` in straight 1.2 m segments. At the front-right outside corner, `mall-floor-corner-tile` and the two-profile `mall-floor-mitred-trim` replace the terminal straight segments and square cap. The original square cap remains selectable as an alternative. `mall-wall-corner` forms the right rear wall corner. A separate 90° floor-edge and wall test is documented in the model reports; the entire corridor has not been accepted for fit or collision. The original floor cap is square; the new mitred pair and decorated corner tile are separate assets.

## Local verification — 2026-11-15

- The five GLBs loaded in Chromium; each module selection, assembly return, camera drag and reset were exercised. A keyboard Enter selection also worked.
- At 1440 × 900 and an emulated 390 × 844 viewport, the page had no horizontal overflow; the mobile full-page layout was inspected. No browser console or page errors were observed in the normal flow.
- An intentionally blocked floor GLB produced the error message; restoring the request and selecting the assembly successfully retried.
- `npm run validate:assets` passed on the current working tree. The existing Gallery production build also passed in a temporary output directory, but does not include this standalone preview.
- After the storefront and furniture additions, Chromium again exercised all five selections, assembly, orbit/reset, loading, desktop and 390 px layout without normal-flow errors. An intentionally blocked bench GLB produced an error; the floor view remained usable and the assembly loaded after retry. The light fixtures and placements were visually inspected in the rendered preview, not independently measured for fit.
- After adding `mall-solid-wall`, the assembly and individual solid-wall view loaded in a fresh local Chromium session. The specific wall GLB was also loaded in the Gallery at 1440 × 900 and emulated 390 × 844; its runtime SHA-256 matched the validated file and the viewer closed cleanly. Full corridor collision and physical-device testing remain open.
- After adding both corner modules, all seven individual views and the assembly loaded in Chromium. Orbit and reset were exercised, desktop and emulated 390 px layouts were inspected, and both new GLB hashes were verified in the Gallery at 1440 × 900 and 390 × 844. No normal-flow browser errors or horizontal overflow were observed. An intentionally blocked floor-corner GLB showed an error; keyboard selection of the wall corner and assembly retry then succeeded. Widths 320 and 768 px also had no horizontal overflow.

- After adding the corner tile and mitred pair, all nine views and the assembled corridor loaded in local Chromium. Each selection, orbit and reset were exercised; the 1440 × 900 and emulated 390 × 844 layouts had no horizontal overflow or normal-flow browser errors. Both new Gallery views rendered WebGL with the expected GLB hashes at both sizes and closed cleanly. [Corridor screenshot](preview-nine-modules.png). A fresh dev server was needed to refresh the generated Gallery catalog.

- On GitHub main baseline `17a0ed6f`, the nine-view browser check, exact hashes for the two new Gallery assets, asset validation, 6 catalog tests and the standard `npm run build` passed again. A custom-output build was not supported on that baseline because its PWA hook reads `dist`; it failed before the successful standard build.

## Shopfront seam verification — 2026-11-23

The outer glazing bays and their fascia panels now sit at X = ±3.30 m. This aligns the 1.20 m bays with the adjacent 2.10 m door bays and removes the 30 mm overlap at each outer join.

Run `node mall-modules-preview/verify-shopfront.mjs` from the repository root. The command loads the four actual GLBs, applies the preview placements and reports signed gaps and positive-volume intersections between adjacent mesh bounding boxes. All four joins in each row and all five fascia base joins measured 0 mm within 1 μm, with no positive-volume intersections at the horizontal joins. The four GLBs passed Khronos validation with zero errors and warnings. The check failed at the outer joins with the previous placements.

Local Chromium rendered the corridor, opened all nine modules, returned to the corridor and used Reset at 1440 × 900 and emulated 390 × 844. All 20 GLBs loaded without browser errors or horizontal overflow. Scope is limited to static shopfront fit and preview browsing. Physical devices, door movement, corridor collision and the 2 m planning grid remain unverified.

Run `npm run dev -- --port 4178` and open `http://127.0.0.1:4178/mall-modules-preview/` to browse the preview locally.
