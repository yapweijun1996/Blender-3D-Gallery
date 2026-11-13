# Sixth 50 tranche A: 16 mall, domestic, food, transport and architecture assets

Base `d9d69a457bc4ab45c77aa9b8058873a9448a8745` (294 existing entries). Exact new scope: `mall038-slugs.json`, original V1 IDs 038,050,084,126,158,001,007,017,018,048,049,075,081,105,109,110.

All 16 local **PASS**. Release **NEEDS REVIEW**: real Android, iOS and WebKit/Safari were NOT TESTED. No deployment, remote push, PR or merge in this producer handoff. Asset-level mechanical clips are not a promise of gallery playback, security/payment functionality, medical operation or driving simulation.

## Evidence and final-hash mapping

- `asset-results.json`: per-type status, source/export SHA-256 and actual costs. Total 75,332 triangles, 3,974,308 GLB bytes.
- 382 unit tests and build passed. Initial and post-POS-correction full-suite logs preserved. After final quality metadata changed, all16 relevant asset tests and build were revalidated (unit-final.log/build-final.log); the earlier full382-suite PASS remains the complete-suite evidence. Documentation-only wording changes followed without changing tested runtime/assets.
- All 16 strict structural gates: self-contained GLB, finite positions/normals, Khronos zero errors/warnings, correct metre orientation/grounding, required editable components, fixed pre-generation polygon/file/primitive budgets. No budget increases or assertion weakening.
- All saved `.blend` files independently reopened. In a copy, mesh X vertices scaled to0.92 and material roughness changed to0.77, saved, reopened and exported without rebuilding geometry. Canonical source SHA unchanged. Evidence under each asset `reports/sources.json` and `reports/source-edit/`.
- Full48 Chromium cases passed at1440x900,768x1024,390x844. POS received a later parent fix and three further cases passed. `browser-final-results.json` maps45 unchanged final-hash cases in `browser/` plus3 final POS cases in `browser-pos-correction/`. Original48 remain intact. A separate hatchback pilot also passed three cases in `browser-pilot/`.
- Browser assertions include exact loaded final GLB hash, real WebGL draws, orbit/zoom, exact pixel reset/reopen, keyboard/focus/close behavior, no horizontal overflow and zero unfiltered request/page/console errors. All output paths honor `MALL_QA_DIR`.
- Actual visual inspection:64 final studio views,5 final action poses,48 final browser initial images. Studio views alone were not used to claim GLB appearance. Four initial/final contact sheets and full-resolution per-asset PNG/WebP/browser images are retained.

## Vehicle pilot and mechanical checks

109 Hatchback was gated before110 Motorcycle and shared as a reference, not blanket validation. Hatchback has independent cabin/seats, real wheel-arch voids, separate steering parents/rolling pivots and doors carrying their mirrors. Radius0.31m, track1.58m, wheelbase2.48m are checked against exported world-space geometry. All60 exported-frame samples check tyre ground contact and door bounding boxes against fixed meshes; observed maximum tyre contact error approximately1.366mm, within a fixed2mm tolerance for polygonal tyres. Raw track first/end values and timeline, midpoint steering0.28rad, wheel half-turn pi, door1.2rad and restoration are tested.

Motorcycle independently verifies radius0.32m, initial wheelbase1.44m, two actual tyre contacts, simplified vertical headstock steering0.30rad, wheels half-turn pi, body clearance over all60 samples and restoration. It is not a physically accurate motorcycle steering/lean dynamics model. Bar-end mirrors, engine/fins, tank, chassis, seat, exhaust, stand and spokes are distinct editable parts.

Wheel clips are **half-turn and return**, not full-spin/unwrapped odometry evidence. No velocity, suspension simulation or generic gallery driving controls are claimed. Existing Proton-only viewer controls were not modified. Remaining articulated types are apartment door, paired mall sliding doors and POS tilt; each has raw endpoint/actual midpoint/60-sample clearance tests. These are sampled-motion checks, not a continuous collision-solver certification.

## Preserved corrections and failure evidence

- Hatchback first draft had a sedan-like rear deck. Entire source/export/previews and generator snapshot were archived under `before-hatch-silhouette-correction/`; extended sloping hatch corrected the silhouette. Initial structural log also caught a harness error: seeking backwards after a clamped LoopOnce ended left its actions paused. Reset/play before seeking fixed the harness without loosening midpoint assertions.
- `before-visual-mechanical-correction/` archives full source/export/previews/generator for seven assets: apartment door, nasi lemak display, POS, cinema entrance, semi-detached house, MRT platform and motorcycle. Failed structural logs remain.
- Apartment sweep initially intersected the jamb: hinge pivot moved to the outer frame face and mounting plates supplied. Nasi lemak packet peak compensated for bevel loss and rice became a rounded mound, not a cylinder. Motorcycle gained physically attached bar-end mirrors and maintained its fixed envelope/budgets.
- Cinema poster panels needed actual stand supports. MRT benches gained floor-contact supports, and its end-view camera now uses projected bounds instead of leaving a tiny distant platform. Semi-detached roofs now meet rather than overlap at the shared boundary.
- POS gained a separate customer-facing total display and swipe channel to distinguish it from a desktop monitor. Its rear support initially overlapped the conservative moving-display clearance envelope; base/support were moved rearward with no assertion relaxation. Full before-state is in `before-customer-support-correction/`.
- Action inspection then found the POS swipe channel incorrectly parented to the static root. A new parent assertion failed as expected (`structural-parent-before-fix.log`). Full before-state is in `before-swipe-parent-correction/`. Channel now follows the display tilt; source proof, all structural/motion checks,382 unit tests/build and3 final-hash browser cases were rerun. This changed no other asset hashes.

## Originality and scope boundaries

Per-asset metadata/README record the specific novelty contract. No original user backlog item was silently marked complete by analogy. Existing294 entries remain unchanged;16 independent collections added,310 total, no duplicate IDs. The pair of semi-detached units is one asset, not two counts. Architecture shells and platform/stall/corridor modules are independent outputs, not extra registrations for furniture/components. All are original generic illustrative proportions, not copied landmarks or surveyed/code-certified buildings. Nasi lemak food shapes are original stylized geometry. No external models/textures, official operator liveries or real banking/security interfaces are included.

Source provenance: exact001–300 names came from the complete authorized indexed V1 production-list result; full-body retrieval had omitted content. No unavailable KB read is claimed and no private conversation URL is included. Names301–500 were user-supplied; this tranche uses V1 names only.

## Portable reproduction

From repository root with dependencies and Blender4.0.2:

1. `blender --background --threads 2 --python-exit-code 1 --python models/<slug>/generate.py`
2. `node models/<slug>/validate.mjs`
3. `blender --background --threads 2 --python-exit-code 1 --python models/<slug>/inspect_sources.py`
4. `node models/<slug>/verify_source_edit.mjs`
5. Animated types: `blender --background --threads 2 --python-exit-code 1 --python models/<slug>/render_open.py`
6. `npm test && npm run build`
7. `MALL_QA_DIR=/your/evidence node scripts/test-mall038-browser.mjs`

Optional `MALL_QA_ASSETS=pos-terminal` selects an asset but retains all three viewport assertions. `scripts/test-hatchback-pilot-browser.mjs` is the earlier one-asset pilot gate. The final16 gate is `test-mall038-browser.mjs`. Structural and animation checks are self-contained in each asset's `validate.mjs`.
