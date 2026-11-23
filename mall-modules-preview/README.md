# Mall module preview

A local interactive preview of nine Gallery assets and a corridor assembled from their exported GLBs. Start the project with `npm run dev`, then visit `/mall-modules-preview/` on the local Vite server. In the assembly, select **Open doors** and **Walk visitor** to explore the shops. The arrow keys, W A S D and touch pad move the visitor. Escape returns to orbit, and **Reset visitor** returns to the arrival point.

## Six-metre floor transition

Select **Floor grid transition** or open `/mall-modules-preview/?view=floor-transition`. Five bays of the [1.2 m tile](../models/mall-floor-tile/README.md) meet three of the [2 m straight module](../models/mall-floor-module-2m/README.md) along one 6 m edge. Each root retains its original scale. Set the 30 mm and 100 mm underside pivots to Y = −0.03 m and −0.10 m respectively to bring both walking surfaces to Y = 0. The second legacy row gives the visitor room to approach the joint. Quarter-turned copies exercise the same connectors in both directions. [Mixed floor preview](mixed-floor-grids.png)

Run `node --test tests/mall-floor-transition.test.mjs`. The test measures seven overlapping edge intervals between the two grids and 15 joins inside them. It casts 6,396 rays against individual floor meshes, allowing the 1 mm recess in the original grout. The visitor follows a 15.76 m path in each direction, with 15,875 independent floor-triangle probes per direction. The negative controls reproduce an 800 mm gap from reusing the old tile at the new pitch and a 70 mm step from lining up the two undersides.

With Vite running, `node scripts/test-mall-floor-transition.mjs` checks both actual GLB downloads, a failed load and retry, module selection and return to the furnished corridor. Set `MALL_PREVIEW_SITE` for a different Vite address. This sample covers a straight interior floor joint. Edge trim, corner details and the ceiling need their own measurements.

### Straight wall on the 2 m floor

Choose **Straight wall** from the **Assembly** menu in the floor view or open `/mall-modules-preview/?view=wall-run`. Three unscaled [straight wall modules](../models/mall-wall-module-2m/README.md) stand on the back edge of the 2 m floor. Their ground-centre pivots sit at X = −2, 0 and 2 m and Z = −1.925 m. The stone faces point toward the aisle. Both pairs of end connectors meet, and 615 paired floor and underside probes found contact at the finished surface. [Wall and floor preview](wall-on-floor.png)

The two half-joints form a 4 mm mortar strip recessed 10 mm from the limestone face. The bronze skirting and crown project 3 mm beyond it. The 1.80 m visitor travelled 8.4 m along the wall in both directions combined. At six approaches around the joins, the visitor stopped within one 25 mm movement step of the independent cylinder contact. A rounded capsule cleared the projecting skirt and touched the main face about 3 mm farther in.

Run `node --test tests/mall-wall-run.test.mjs` to repeat the contact check. At one shared triangle edge on the floor, a single-precision Rapier point ray returned the slab underside. The test records the raw value and checks that a Three.js ray and the nearest point on the actual Rapier triangles agree at the same coordinate within 1 μm. This check resolved 18 probes on the measured walk. Taking out the tile or lowering it by 100 mm still fails the support check.

At this pitch the original 1.2 m wall would leave two 800 mm openings. The original ceiling cassette placed at its 3 m grid height stands 200 mm above the new 2.8 m wall. The sample below seats the same cassette at the new datum.

### Wall and ceiling

Choose **Straight wall and ceiling**, or open `/mall-modules-preview/?view=wall-ceiling`. Five original 1.2 m cassettes cover the same 6 m as the three 2 m walls. Their underside rail sits at Y = 2.80 m, and the rear edge is at Z = −2 m. The 12 mm rear half-rail contacts the actual wall tops. The cassettes extend 1.2 m into the room, where this cutaway shows the underside.

Run `node --test tests/mall-wall-ceiling.test.mjs`. The check verifies four pairs of cassette connectors, 417 paired wall-top and rail contacts, and nine transverse rails extending into the aisle. Each of the 20 recessed panels sits 8 mm above the grid underside. The 20 hanger assemblies reach Y = 3.16 m. This sample covers one straight ceiling row. [Ceiling cutaway](ceiling-on-wall.png)

### Right-angle corner and return

Choose **Corner with two walls**, or open `/mall-modules-preview/?view=wall-corner`. The [2 m corner](../models/mall-wall-corner-2m/README.md) turns the wall along the right boundary of the same floor. Each arm measures 2 m from the centreline turn to its connector. The wall thickness brings the outside footprint to 2.075 m square. The rear straight faces +Z and the right return faces −X. [Installed corner](corner-on-floor.png)

Run `node --test tests/mall-wall-corner-2m.test.mjs`. Seventy mesh rays check the inside and outside of the mitre. Of 809 wall-base probes, 769 reach the floor at the same elevation and 40 meet the original tile’s shallow grout recess. The visitor traversed both joins and returned over a 9.128 m route. An earlier continuous L-shaped backing produced a rectangular collision box across the empty aisle. Each arm now has its own mesh bounds and meets its partner on the same mitre plane. Recombining the same triangles reproduces the obstruction.

### Two-metre outside floor corner

Choose **Outside floor corner** or open `/mall-modules-preview/?view=corner-floor`. Three straight slabs and one [corner slab](../models/mall-floor-corner-2m/README.md) make a 4 × 4 m floor. All four underside pivots sit at Y = −0.10 m. On the corner tile, the champagne and eucalyptus terrazzo inlays follow +X and +Z and meet at 45°. The adjacent straight slabs have a plain finish. [Installed corner tile](corner-tile-on-floor.png)

Run `node --test tests/mall-floor-corner-tile-2m.test.mjs`. The check inspects both sides of all four internal joins with 2,424 surface rays. It distinguishes the two champagne arms and samples both sides of their boundaries to 10 μm. Each direction of the 6.025 m visitor route has 6,075 footprint probes. A reversed tile still fills the square but places its bands on the wrong edges. Removing it leaves an unsupported quarter of the floor.

### Full-depth floor edging

Choose **Finished floor edge** or open `/mall-modules-preview/?view=finished-edge`. Two [2 m straight profiles and their mitred return](../models/mall-floor-edge-2m/README.md) finish the outside edges of the same four slabs. The 60 mm cap sits flush and its bronze fascia covers the 100 mm slab depth. The straight profiles use a top-centre pivot. The paired return uses the corner tile centre at finished-floor elevation. [Installed straight and mitred edges](finished-floor-edge.png)

Run `node --test tests/mall-floor-edge-kit-2m.test.mjs`. Both straight-to-return joints match at 56 paired end-face samples. Another 568 paired samples check the slab and trim, including a 1 mm relief at 99 mm depth where the underside bevel recedes. The old 1.2 m trim leaves an 800 mm opening at 2 m centres and exposes 70 mm of the side.

The visible cap extends beyond the four walkable cells. At each outer edge the visitor stops with its footprint on the slab. A ray cast exactly on the triangle boundary can miss in Rapier. The verifier checks the point against the actual GLB triangles and the closest point on the physics mesh within 1 μm, and verifies that probing 10 μm farther out finds no floor support.

### Enclosed shop on the 2 m grid

Choose **Enclosed shop** or open `/mall-modules-preview/?view=enclosed-shop`. The shop measures 6 × 6 m between wall centrelines. Nine 2 m tiles form the interior floor and 16 more support the wall perimeter and entrance apron. Four corner pieces and three straight walls leave a 2.00 m entrance. The original double-door frame is 2.10 m wide. Its back rests against the outside wall face with 50 mm of bearing on either side. A new [400 mm door header](../models/mall-shop-door-header-2m/README.md) closes the gap between the 2.40 m frame and the 2.80 m wall top. The legacy 600 mm fascia at this position would project 200 mm above the wall.

The ceiling starts hidden. Select **Show ceiling** to see the 25 cassettes, or **Open doors** and **Walk visitor** to enter from the apron. Switching between the furnished corridor and this room returns the same visitor to the selected entrance. Each scene retains its own door position. [Shop cutaway](enclosed-shop.png) · [Closed ceiling](enclosed-shop-ceiling.png)

Run `node --test tests/mall-enclosed-shop.test.mjs` for the geometry and visitor checks. The original door leaves retain 100 mm of vertical clearance through their 90° swing. Across 72 headings, all 144 cylinder and capsule sweeps struck a closed door or wall. The open-door route covers 6.614 m each way with 13,375 floor probes across both directions. The controller restores both hinges when closing would hit the visitor. The roof check covers 100 recessed panels and 244 paired contacts along the wall tops and door header. The ceiling ends on the wall centrelines, leaving the outer 75 mm of wall top visible. Removing a rear wall exposes a second walkable exit across the outside apron. With Vite running, `node scripts/test-mall-enclosed-shop.mjs` exercises the ceiling control, door, movement and a switch between scenes during visitor loading.

### Home furnishings shop

Choose **Home furnishings shop** or open `/mall-modules-preview/?view=home-furnishings`. This 6 m shop presents a living-room display on the left and a dining display on the right. It reuses six catalogued models, including two instances of the dining chair. All six metadata records allow reuse in the owner's projects. Their GLBs total 868,152 bytes. The preview loads them when this shop is selected.

| Living-room display | Dining display |
| --- | --- |
| [Sofa](../models/living-room-sofa/README.md), [side cabinet](../models/bedside-table/README.md) and [brass oil lamp](../models/deepavali-oil-lamp/README.md) | [Round dining table](../models/round-dining-table/README.md), two [chairs](../models/plastic-dining-chair/README.md) and an [orchid](../models/orchid-planter/README.md) |

Open the doors and enter from the apron. The two viewing points connect along a 13.5 m loop. Run `node --test tests/mall-home-furnishings.test.mjs` to verify the furnished route in both directions. The check samples 27,225 points under the visitor's footprint and 126 triangles at furniture supports, including the lamp on the 622.5 mm cabinet top. The controller stops within one 25 mm movement step of independent mesh sweeps against the sofa and dining table. Moving the sofa into the doorway blocks the route. The furniture is displayed in its static pose. [Showroom cutaway](home-furnishings.png)

### Pharmacy and beauty shop

Choose **Pharmacy and beauty shop** or open `/mall-modules-preview/?view=pharmacy-beauty`. Enter through the double doors. The new [cosmetics tester bar](../models/mall-cosmetics-tester-bar/README.md) stands on the left, the [stocked shelf](../models/medicine-health-box-set/README.md) on the right and the [pickup counter](../models/pharmacy-counter/README.md) at the back. **Inspect tester bar** frames the eight shade samples and mirror from the customer side. **Reset view** returns to the shop overview. [Shop cutaway](pharmacy-beauty.png) · [Tester close-up](pharmacy-beauty-tester.png)

The three fixtures sit at their original scale. The 0.814 m-wide pickup opening gives the customer a sightline to the tray, and the right-hand aisle leads staff to the open rear rack. The 18.18 m customer loop visits all three fixtures from the entrance. The 11.88 m staff route runs from the stock display around the counter and back.

Run `node --test tests/mall-pharmacy-beauty.test.mjs` to check floor support, sightlines and full-body clearance along both routes, including controls with the door shut, the tester reversed and the staff aisle obstructed. With the local server running, `MALL_PREVIEW_SITE=http://127.0.0.1:5173/ node scripts/test-mall-shop-inspection.mjs pharmacy-beauty` checks the nine loaded GLBs and the inspect, reset, roof and shop controls at desktop and touch viewport sizes. It also interrupts the tester download and retries through the shop selector.

### Computer shop

Choose **Computer shop** or open `/mall-modules-preview/?view=computer-shop`. Enter through the double doors to reach the central [TV demo table](../models/tv-demo-table/README.md). **Inspect demo laptop** frames the [open notebook](../models/laptop/README.md), its keyboard and both ends of the [product security tether](../models/mall-product-security-tether/README.md). The original three screens remain on the table. The right aisle leads to the [electronics shelf](../models/shelf-electronics-display/README.md) and the left aisle returns to the entrance. [Shop cutaway](computer-shop.png) · [Tethered laptop](computer-shop-laptop.png)

The 19.24 m visitor loop includes 775 checked positions. Both ends of the tether make physical contact, with the table base at desk height and the device pad 20 mm higher on the palm rest. The preview displays the laptop open. The geometry test independently runs its 2.5 s lid clip through 301 poses and measures clearance over the lead and sensor. Turning the tether around leaves a measurable 20 mm gap under the device pad.

Run `node --test tests/mall-computer-shop.test.mjs` to check the mounted fixtures, lid motion, display sightlines and both aisles. With the local server running, `MALL_PREVIEW_SITE=http://127.0.0.1:5173/ node scripts/test-mall-shop-inspection.mjs computer-shop` verifies ten exact GLBs, keyboard and touch inspection, reset, the roof toggle and recovery from a failed tether download.

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
