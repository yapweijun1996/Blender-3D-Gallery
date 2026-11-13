# Public facilities and tropical assets454–469

Exact16-item V2.1 scope on baseline 3c797657f5693a1eb3b3e26f49d4e1d9f1c110b3. Existing194 entries and all existing files/evidence preserved; only16 collections appended using unchanged schema. No remote operations or deployment.

All16 local gates PASS; all16 overall NEEDS REVIEW. Physical Android/iOS, WebKit, hardware performance and combined50 integration gate remain unverified. Metadata stays draft.

| ID | Asset | Triangles | Bytes | Mesh primitives | Local | Overall |
|---|---|---:|---:|---:|---|---|
| 454 | Clinic Pharmacy Window | 1636 | 84812 | 12 | PASS | NEEDS REVIEW |
| 455 | Public Toilet Cubicle | 2548 | 136744 | 17 | PASS | NEEDS REVIEW |
| 456 | Accessible Toilet Grab Rail | 2080 | 103980 | 8 | PASS | NEEDS REVIEW |
| 457 | Prayer Room Shoe Rack | 2952 | 167032 | 25 | PASS | NEEDS REVIEW |
| 458 | Prayer Room Partition | 1672 | 93756 | 14 | PASS | NEEDS REVIEW |
| 459 | Public Building Security Scanner | 1944 | 98688 | 15 | PASS | NEEDS REVIEW |
| 460 | Visitor Registration Terminal | 1184 | 59908 | 9 | PASS | NEEDS REVIEW |
| 461 | Rain Tree | 2048 | 157104 | 30 | PASS | NEEDS REVIEW |
| 462 | Angsana Tree | 1044 | 78600 | 18 | PASS | NEEDS REVIEW |
| 463 | Tembusu Tree | 2436 | 179308 | 37 | PASS | NEEDS REVIEW |
| 464 | Frangipani Tree | 7452 | 473532 | 31 | PASS | NEEDS REVIEW |
| 465 | Banana Plant | 1104 | 71628 | 28 | PASS | NEEDS REVIEW |
| 466 | Coconut Palm | 16364 | 932056 | 30 | PASS | NEEDS REVIEW |
| 467 | Oil Palm | 25288 | 1469616 | 15 | PASS | NEEDS REVIEW |
| 468 | Bamboo Cluster | 14136 | 844392 | 49 | PASS | NEEDS REVIEW |
| 469 | Bougainvillea Bush | 16164 | 1039240 | 54 | PASS | NEEDS REVIEW |

## Executed gates
-286 existing unit tests PASS; build PASS with existing bundle-size advisory.
-16 Khronos/Three.js structure checks PASS, zero errors/warnings; independent mesh/material source edit/save/export proofs PASS. No source regeneration used for the edit proof.
-48 Chromium cases PASS, three desktop/tablet/mobile-size viewports each; these are not physical devices. Raw results preserve consumed GLB hashes, controls/reset/reopen hashes, lifecycle checks, network/console errors and screenshots.
-Actual64 multi-angle rendered previews inspected, then8 updated seam views inspected; all48 browser initial views inspected. Actual source frame30 open-pose previews inspected for454/455/458.
-Rendered images are under each model/previews; contact sheets and raw browser screenshots accompany this report. render-seam-final.jpg supersedes pre-seam458/459 images in render-contact-4.jpg.
-GLB and source hashes are verified against final files in asset-results.json and per-asset reports.

## Geometry and budget decisions
Fixed before generation: simple props6000 triangles/350000bytes/80 mesh primitives; assemblies9000/600000/80; plants26000/1500000/90. Dense leaf geometry justifies the plant allowance; static foliage is grouped by branch/frond rather than hundreds of draw calls. Budgets were not raised. Maximum measured plant primitives54; the largest asset is oil palm25288triangles/1469616bytes.

Species distinctions: rain tree flattened umbrella with central crown fill; angsana rounded branching crown; tembusu tall narrowing crown; frangipani stout forks, elongated leaves and five-petal flowers; banana paddle leaves/pseudostem; coconut curved slender trunk, arching pinnate fronds and coconuts; oil palm thick scarred trunk, denser upright crown and fruit bunch; bamboo segmented canes and lanceolate sprays; bougainvillea green bush clusters with magenta bracts. All are original stylizations, not botanical-reference accuracy.

454 pharmacy sash travels0.65m vertically with >0.63m transaction opening.455 cubicle door swings1.25rad with >0.65m clear width.458 partition folds0.75rad. Checks validate raw exported first/last track values independently of playback wrapping, exact2.5s timeline, intended midpoint motion, fixed-hinge/clearance behavior and LoopOnce restoration. Gallery offers orbit/zoom, not animation playback UI. No real clinical, screening, registration or security functionality is claimed.

## Corrections, failures and archival precision
Initial generation logs for all16 are retained. Ten draft assets had sources/exports/previews replaced during visual improvements:455,458,459,461,464,465,466,467,468,469. Six retain first-pass outputs. No complete before-source/GLB/preview archive is claimed; earliest contact images were viewed in memory, not saved separately. Later pre-seam458/459 contact sheet is retained and marked superseded. All actual failed validation/source-verification logs are preserved separately.

Visual corrections: close rain-canopy central hole; improve leaf-plane orientation and palm-leaf width; distinguish upright oil-palm crown; add denser bamboo and bougainvillea; give cubicle seat a real opening; improve folding hinge clearance; eliminate partition/scanner coplanar corner overlap.

Four feature assertions initially assumed named Mesh nodes, but multi-material grouped foliage exports named Groups with mesh descendants. Corrected tests require genuine named geometry-bearing groups. Bougainvillea edit verifier likewise now compares complete descendant vertex arrays with equal vertex count, not nonexistent Group.geometry. Coconut dimension check originally used a rotated local AABB approximation; size now uses precise actual world-space vertices via Box3 precise=true. Original analytical size range and all budgets retained. The initial failures remain in validate-initial.log and source-edit-initial-failure.log; final validations pass.

Original procedural geometry/materials only. No external textures, logos, marketplace assets or supplied font files. Rights retain project wording: owner-project reuse authorized, public redistribution terms unspecified. No medical/accessibility/structural certification.

## Reproduction
Use Blender4.0.2 and Node22 with repository dependencies. Each asset has generate.py, inspect_sources.py, validate.mjs and verify_source_edit.mjs. Movable assets also have render_open.py. Run node --check on scripts before execution, then all16 model validators, npm test, npm run build and node scripts/test-tropical454-browser.mjs. Source-edit fixtures never overwrite canonical sources.
