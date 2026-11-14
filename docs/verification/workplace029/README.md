# Fifth 50, tranche A: 16 workplace, transport and modular shells

Base `9604912f6eded65d01424e6ff229f15fd739077d`. Local gate PASS for all 16; release NEEDS REVIEW pending physical Android, iOS and WebKit tests. No deployment, remote push or PR in this handoff.

Exact scope: `workplace029-slugs.json`; original V1 IDs 029,144,182,233,089,019,112,116,161,170,021,030,041,042,067,181. `asset-results.json` contains individual statuses, measured costs and source/export hashes. Original list was recovered from authorized indexed conversation content; no private chat links are published and no unavailable KB source is claimed.

## Evidence

- 349 unit tests and build passed. `unit-initial.log`, `build-initial.log`; final repeats after documentation below.
- All 16 strict GLB validators: self-contained glTF, finite geometry, Khronos zero errors/warnings, grounded metric orientation/dimensions, named component geometry, fixed upfront complexity budgets.
- Seven animated types (forklift carriage, two buffet lids, rear display sliding pane, ATM rear service door, barrier arm, meeting-room door, classroom door). Raw exported time/end values, intended midpoint travel/angle, measured opening/clearance and LoopOnce restoration are checked. This is illustrative asset animation, not physics or real operational functionality. Existing gallery UI was not changed and does not expose these clips.
- All saved sources reopened; mesh vertices and material roughness edited in independent copies, saved, reopened and exported without generator construction. Original source hashes unchanged. See each `reports/sources.json`, source-edit blend/GLB and logs.
- `browser/results.json`: 48/48 desktop Chromium cases, 1440x900, 768x1024 and 390x844. Exact loaded final GLB SHA, WebGL draws, orbit, zoom, exact reset/reopen, focus/disposal, no overflow or request/page/console errors. Viewport emulation is NOT physical-device testing.
- Actual visual inspection: all 64 final studio views, seven action poses (rear-access poses reframed separately), and all 48 final browser initial images. Four initial sheets and four final sheets aid comparison; full-resolution source and browser images remain present. Browser images prove GLB appearance; studio images alone do not.

## Corrections and archival scope

Initial source/export/preview directories plus generator snapshots were archived for office partition, office building, glass meeting room, HDB block, HDB void deck, school building and school classroom in `reports/before-studio-correction/`. Partition framing had clipped the ends; larger ortho framing now includes the full T layout. Large shells had fixed-size studio lights producing dark upper storeys/hotspots; studio lights were scaled and moved around each shell, without changing exported lighting (none exported). School roof caps now meet rather than overlap at equal heights.

Initial structural failures remain in logs. Buffet initially measured 1.43 m against its 1.45 m design envelope; the missing guard top rail was added, preserving intended dimension and tests. HDB outer corridor posts projected 0.01 m outside each slab edge; moved inward 0.01 m. Their before source/export/previews/generator are archived in `before-dimension-correction/`. No budget increases, assertion relaxation or hidden failure deletion.

Rear ATM access and display sliding pane were hidden in front-facing action screenshots. Original action screenshots retained as `reports/open-front-obscured.png`; only action preview camera changed to rear. Canonical source/export unaffected.

Shared-clone checkout failed before production due nested alternates depth. Partial clone preserved outside this independent repository. An ordinary read-only fetch of the exact published base created an independent object store. No upstream repository or Git history was changed.

## Novelty and limitations

Office partition is a low T workstation fabric-panel/cable-raceway assembly, not a tall prayer partition or glass screen. Student desk includes book basket, tubular sled frame and bag hook. Buffet has independent hollow wells/lids and sneeze guard; ambient food display has separate sliding rear pane. Architecture entries are independent reusable shells, not extra registrations for copied furniture. HDB slab block/common corridors differ from a condominium tower; void deck has structural bays, service core and stair aperture, not the existing pitched pavilion. Classroom is deliberately front/open-top cutaway, empty and furniture-ready. Road is a kerb/sidewalk/drain/marking module with end connector metadata. No brand logos, surveyed landmark accuracy, building-code/accessibility/fire certification, payment, medical or real vehicle functionality is claimed.

## Reproduce

From repository root with project dependencies and Blender 4.0.2 available:

1. `blender --background --threads 2 --python-exit-code 1 --python models/<slug>/generate.py`
2. `node models/<slug>/validate.mjs`
3. `blender --background --threads 2 --python-exit-code 1 --python models/<slug>/inspect_sources.py`
4. `node models/<slug>/verify_source_edit.mjs`
5. For animated assets: `blender --background --threads 2 --python-exit-code 1 --python models/<slug>/render_open.py`
6. `npm test && npm run build`
7. `MALL_QA_DIR=/your/evidence/path node scripts/test-workplace029-browser.mjs`

All browser output paths honor MALL_QA_DIR. Optional MALL_QA_ASSETS filters requested IDs but retains all three viewport cases per asset. Do not deploy until remaining release review is satisfied.
