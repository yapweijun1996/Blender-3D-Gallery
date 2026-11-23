# Mall module preview

A local interactive preview of nine Gallery assets and a corridor assembled from their exported GLBs. Start the project with `npm run dev`, then visit `/mall-modules-preview/` on the local Vite server. In the assembly, select **Open doors** and **Walk visitor** to explore the shops. The arrow keys, W A S D and touch pad move the visitor. Escape returns to orbit, and **Reset visitor** returns to the arrival point.

## Six-metre floor transition

Select **Floor grid transition** or open `/mall-modules-preview/?view=floor-transition`. Five bays of the [1.2 m tile](../models/mall-floor-tile/README.md) meet three of the [2 m straight module](../models/mall-floor-module-2m/README.md) along one 6 m edge. Each root retains its original scale. Set the 30 mm and 100 mm underside pivots to Y = −0.03 m and −0.10 m respectively to bring both walking surfaces to Y = 0. The second legacy row gives the visitor room to approach the joint. Quarter-turned copies exercise the same connectors in both directions. [Mixed floor preview](mixed-floor-grids.png)

Run `node --test tests/mall-floor-transition.test.mjs`. The test measures seven overlapping edge intervals between the two grids and 15 joins inside them. It casts 6,396 rays against individual floor meshes, allowing the 1 mm recess in the original grout. The visitor follows a 15.76 m path in each direction, with 15,875 independent floor-triangle probes per direction. The negative controls reproduce an 800 mm gap from reusing the old tile at the new pitch and a 70 mm step from lining up the two undersides.

With Vite running, `node scripts/test-mall-floor-transition.mjs` checks both actual GLB downloads, a failed load and retry, module selection and return to the furnished corridor. Set `MALL_PREVIEW_SITE` for a different Vite address. This sample covers a straight interior floor joint. Edge trim, corner details and the ceiling need their own measurements.

## Furnished corridor

The wall selection is the new 1.2 m solid wall; the corridor also retains the existing glass partitions for the shopfronts. The ceiling is intentionally a partial cutaway for visibility. This visual arrangement is not a construction or safety specification; see the individual asset READMEs and `docs/verification/p0-assembly/README.md` for actual dimensions, interfaces, prior checks, and rights. The preview does not change or export source assets, and it is not part of the production Gallery build.

The corridor also loads existing shopfront doors and fascia, ceiling light fixtures, lounge bench, planters, display shelves, directory and advertising lightbox. Each light replaces one ceiling panel following the fixture's documented placement; separate Three.js lights provide scene illumination. The two store names are fictional preview labels. The earlier individual views remain available alongside the corner floor tile and mitred trim; C1–C4 are display labels, not backlog IDs. The furnished visitor checks below cover a route past the seating and through both shops.

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

## 1.2 m shell verification — 2026-11-23

The three straight walls on the right now face the corridor. Their −90° rotation about GLB Y aligns the interior panels and skirting at the rear corner. The previous +90° pose aligned the joint plane but produced a 10 mm step in the interior profile. The corrected position leaves a maximum measured step of 0.21 μm at the sampled corner profiles.

Run `node mall-modules-preview/verify-shell.mjs` from the repository root. The command uses the same placements as the preview and prints a JSON report with the seven actual GLB hashes, Khronos validation, signed gaps and surface samples. All seven GLBs passed with zero errors and warnings. At a 1 μm tolerance the following checks passed.

- The 7 × 5 floor has 58 internal joins. The largest absolute gap was 0.048 μm. All 348 surface rays sampled matching heights across those joins, including the authored grout and bevel recesses. Nominal finished-floor Y is 0.
- Both straight-to-mitre joins and both adjacent corner-tile contacts align. The four diagonal probes hit the expected profile, and the corner inlay and trim samples meet finished-floor Y.
- All nine rear and right wall joins meet. Interior surface samples at both ends of the corner agree within tolerance. The verifier detects the previous outward orientation and a deliberately shifted floor module.
- Four ceiling grid contacts meet the wall top at Y = 3.00 m. The three fixture-panel openings and a sample through the cutaway remain open in the ceiling cassette meshes.

Local Chrome loaded all 20 exact GLBs and opened all nine module views at 1440 × 900 and emulated 390 × 844. Mouse orbit and wheel, touch orbit and pinch, Reset and backing-canvas resize passed without browser errors or horizontal overflow.

This evidence covers fixed samples in the current static cutaway. The visitor tests below cover movement near the rear-right corner. Other corner layouts, exhaustive assembly intersections, physical devices and the provisional 2 m production grid remain open. [Backlog and asset crosswalk](../docs/shopping-mall/README.md#12-m-corridor-shell-crosswalk).

## Visitor collision at the rear-right corner

Run `node --test tests/mall-corner-walk.test.mjs` from the repository root. The test builds the preview's 35 floor tiles and ten wall modules from their actual GLBs and places the [mall visitor controller](../docs/verification/mall-corridor/VISITOR.md) in that shell. Its upright cylinder is 1.80 m high with a 0.56 m radius and a maximum 25 mm movement substep. The test prints the four GLB SHA-256 hashes and compares the controller's movement with independent Rapier sweeps against the transformed wall triangles.

- The visitor walked 10.36 m around the inside corner and back. At 417 positions, 10,425 downward rays checked the centre and footprint perimeter against the floor triangles, including the 1 mm grout recess.
- Six approaches tested the straight walls, both L-wall arms and their mating planes. The controller stopped 5–20 mm before cylinder contact with the mesh. Under sustained outward input it slid 0.95 m along the rear join and 1.02 m along the right join. A diagonal approach stopped against both walls and the visitor could back away.
- Removing the L-wall let the visitor reach the floor edge and failed the wall contact check. Lowering one floor tile by 300 mm left the controller's flat floor map traversable and failed the triangle support check.

The shell path crosses space occupied by shopfronts in the furnished arrangement. It verifies the structural modules in isolation. The furnished route below uses different waypoints and includes the doors, seating and displays.

## Furnished walk through both shops

The assembly opens in orbit with both shop doors closed. Opening the doors turns the four authored hinge nodes by 90°. The door control checks the visitor's footprint at each degree and restores the previous pose when a leaf would hit the visitor. The visitor loads on the first walk. Individual module selections return to orbit. [Inside the west shop](west-shop-walk.png) · [Touch controls at arrival](furnished-touch.png).

The display shelves sit behind the two outer glazing bays. Their previous positions directly behind the doors stopped the 1.12 m wide visitor before its body could clear the frame. Moving the directory and advertising lightbox next to the columns clears both approach aisles. In the earlier layout the meshes of both signs actually intersected the columns.

Run `node --test tests/mall-furnished-walk.test.mjs` to exercise the layout shared with the preview. The test loads the 19 placed GLB types. With both doors open, the visitor walks around the bench, through one shop door, across the shared retail interior, out of the other door and back to arrival. The 15.982 m loop passed in both directions with 16,125 floor-triangle samples per direction and independent cylinder sweeps against the installed obstacles. The default closed doors and the occupied bench stop the body. A visitor clear at both 0° and 90° can still obstruct an intermediate angle. The test checks all four hinge rotations and their collision state after rollback. Restoring the previous furniture placement reproduces the shelf blockage and both column intersections.

The assembly batches fixed opaque meshes by compatible material and vertex attributes. The visible mesh count fell from 1,075 to 162 with the same triangle counts per material. Each moving door mesh and transparent object keeps its own draw geometry.

With the local Vite server running, `node scripts/test-mall-furnished-walk.mjs` checks the regular preview controls. Set `MALL_PREVIEW_SITE` if the server uses a base URL other than `http://127.0.0.1:5173/`. This route covers the current flat assembly and one visitor size. Other furnished layouts, population flow, the 2 m production grid and physical-device performance remain open.
