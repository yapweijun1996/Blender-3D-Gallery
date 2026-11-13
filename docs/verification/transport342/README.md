# Transport assets342–359 local quality gate

Scope: exact18 titles from500 Model Master Production Backlog V2.1. Base commit: 85ceaa99165762f1f1d5a0e6dcb5bc2ee5a5be1a. No existing model was replaced, and only18 new collections were appended using the existing schema. Preservation evidence: preservation.json. Local files only; no push, PR, merge or deployment.

## Results
All18 local asset gates PASS; all18 overall NEEDS REVIEW. Physical Android/iOS, Safari/WebKit, hardware performance and the coordinator's combined50 gate are NOT TESTED here. Catalog metadata deliberately remains draft. Owner must not treat this evidence as release or physical-device approval.

| ID | Asset | Triangles | GLB bytes | Local | Overall |
|---|---|---:|---:|---|---|
| 342 | MRT Station Signage | 1256 | 50556 | PASS | NEEDS REVIEW |
| 343 | MRT Platform Screen Door | 2644 | 138844 | PASS | NEEDS REVIEW |
| 344 | MRT Route Map Panel | 3308 | 153728 | PASS | NEEDS REVIEW |
| 345 | MRT Ceiling Grab Handle | 860 | 47016 | PASS | NEEDS REVIEW |
| 346 | MRT Train Seat | 2180 | 114476 | PASS | NEEDS REVIEW |
| 347 | MRT Train Door | 1944 | 110584 | PASS | NEEDS REVIEW |
| 348 | LRT Station Entrance | 2652 | 130696 | PASS | NEEDS REVIEW |
| 349 | LRT Platform Shelter | 1672 | 92984 | PASS | NEEDS REVIEW |
| 350 | Bus Interchange Berth | 1676 | 85872 | PASS | NEEDS REVIEW |
| 351 | Bus Interchange Queue Rail | 1512 | 75504 | PASS | NEEDS REVIEW |
| 352 | Bus Arrival Display | 1800 | 70860 | PASS | NEEDS REVIEW |
| 353 | Bus Stop Pole | 2048 | 87400 | PASS | NEEDS REVIEW |
| 354 | Bus Stop Route Panel | 2768 | 114224 | PASS | NEEDS REVIEW |
| 355 | Bus Fare Card Reader | 1320 | 68468 | PASS | NEEDS REVIEW |
| 356 | Bus Interior Seat | 1372 | 71812 | PASS | NEEDS REVIEW |
| 357 | Bus Grab Pole | 1896 | 92576 | PASS | NEEDS REVIEW |
| 358 | Malaysia KTM Station Sign | 1692 | 72136 | PASS | NEEDS REVIEW |
| 359 | Malaysia KTM Platform Bench | 2316 | 121824 | PASS | NEEDS REVIEW |

## Executed evidence
-240 unit tests PASS: unit.log and unit-final.log.
-Production build PASS: build.log and build-final.log. Existing bundle-size advisory remains, not a test failure.
-18 independent source reopen/manifold/metre/edit/re-export gates PASS. Each source-edit fixture is retained and source hash proved unchanged.
-18 Khronos/Three.js structure, numeric bounds, budgets and internal-file gates PASS. Each asset has reports/assets.json and validate-final.log.
-Initial54 browser cases PASS: browser/results.json. After actual corrections,15 affected cases PASS: browser-final/results.json. Final geometry SHA matches the consumed GLB in its applicable report. Those15 supersede original cases for343,347,348,349,350; the other39 remain unchanged.
-Browser scenarios: desktop Chromium viewport1440x900, tablet768x1024, mobile390x844; hash-verified byte consumption, WebGL drawing, keyboard orbit/zoom, exact reset, exact reopen, cleanup/focus restoration, three repeated lifecycle cycles, no horizontal overflow, zero request/page/console errors. These are not real mobile devices.
-72 Blender previews inspected as actual pixels. Revised handle/shelter/queue views and then both revised door sets re-inspected. All54 browser initial views inspected; final15 after fixes also inspected. Contact sheets accompany full PNG evidence.

## Corrections and preserved failures
-345 triangular grip initially lacked usable opening; enlarged opening and closed the strap-to-rail gap, re-rendered and reviewed.
-351 duplicated horizontal rails removed, count asserted exactly2.
-349 render samples raised to64 for clearer sheltered surfaces.
-Initial345/357 width expectations incorrectly included cylinder radial radius along the cylinder axis. Source endpoints define exact0.56m and0.90m lengths; corrected to tighter analytical bounds. Failure logs retained.
-Strengthened343/347 animation tests exposed the need for separate leaf travel planes. Leaves now clear fixed jambs, with deeper header/threshold; regenerate/source-edit/structure/browser gates rerun.
-Exporter retains frame1 at1/24s and frame60 at2.5s, not a rebased59/24s duration. Timeline assertion corrected to source frame convention; initial failure retained.
-348/349/350 gallery default camera hid front features under roofs. Only existing supported per-asset previewCameraDirection metadata changed to[1,0.5,2]; final15 cases prove new reset/reopen behavior. No application UI code changed.
-The inherited raw browser report defaultView prose says existing default camera. For these three assets, the screenshots and metadata are the authoritative configured lower-camera evidence.

## Animation and limitations
343 has two sliding clips,1.05m opposing travel per leaf and >2.09m clear opening;347 has two sliding clips,0.90m opposing travel and >1.80m opening. Three.js AnimationMixer tests exact2.5s duration, midpoint travel, fixed-jamb clearance and end restoration.345 tests0.3rad bounded swing with fixed hinge and restoration. GLB clips are ready for consumer playback, but this gallery has no animation-playback UI; do not claim runtime door buttons. These are modular illustrative components, not certified transport hardware, complete rail mechanisms or measured operator installations.

All geometry/materials/signage original; no external textures, fonts supplied as files, logos or brand assets. Placeholder routes/station names are fictional. Existing project rights wording retained: owner-project reuse, public redistribution terms unspecified.

## Reproduce
Each model folder contains generate.py, inspect_sources.py, validate.mjs, verify_source_edit.mjs and README.md. Use Blender4.0.2 and Node22 with repository dependencies. Run all18 validation scripts, npm test, npm run build, then node scripts/test-transport342-browser.mjs. The focused correction suite is scripts/test-transport342-preview-fixes.mjs. Source edits are isolated under reports/source-edit, never the production source.
