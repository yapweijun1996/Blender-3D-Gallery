# Assets325–341 local quality gate

Overall NEEDS REVIEW: local checks PASS; physical Android/iOS and Safari/WebKit NOT TESTED. No deployment or Gallery component-control UI.
17 independent .blend sources,17 embedded optimized GLBs,51 studio views. Six assets carry seven meaningful animation clips. Prior catalog/model values preserved.

## Executed checks
- Structural/Khronos17/17PASS,0errors/0warnings; explicit metre dimensions,budgets.
- Source edit/re-export17/17PASS,canonical hashes unchanged.
- All51 studio views and17 Gallery screenshots inspected; six browser animated open poses inspected.
- Unit257/257PASS; buildPASS (existing chunk-size advisory only).
- InitialGallery51/51PASS; finalaffected12/12PASS. Current evidence combines unchanged39cases with final12cases,all SHA-bound.
- Isolated browser AnimationMixer6/6PASS and expected-pose proof7clips.

## Corrected failures
- Coplanar frame/cabinet/beam/sink intersections and low-angle front clipping corrected.327 residualcrossrail overlap separately fixed and source/GLB/render/browser rechecked.
- Initial animation test assumed end2.0s. Exported keys1/25/49 at24fps give start0.0416667,end2.0416667. Finaltest samples actualtimes but asserts independent expected3.25m slide,0.30m lift,±1.3rad hinges,fixedcomponents,gateclearance and exactclosure. Failed trace retained.
- Source proof maps Blender .001 names through Three.js PropertyBinding.sanitizeNodeName; same0.123m assertion retained.

## Reproduce from repo root
    node scripts/validate325341.mjs
    blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-batch325341.py
    node scripts/test-batch325341-source-edit.mjs
    node scripts/test-batch325341-animation.mjs
    npm test
    npm run build
    MALL_QA_DIR=output/batch325341-browser node scripts/test-batch325341-browser.mjs
    MALL_QA_DIR=output/batch325341-animation node scripts/test-batch325341-animation-browser.mjs

Use an isolated fixture checkout to preserve prior reports. BATCH_ASSET_ID selects one sourceasset. BATCH_ASSET_IDS selects comma-separated Gallery slugs for boundedretest; omitted means all17.

| ID | Asset | Local | Overall | Bytes | Triangles |
|---|---|---|---|---:|---:|
|325|malaysia-sliding-metal-gate|PASS|NEEDS REVIEW|214740|3900|
|326|malaysia-roof-tile-module|PASS|NEEDS REVIEW|64336|1360|
|327|malaysia-window-grille|PASS|NEEDS REVIEW|101492|1836|
|328|malaysia-outdoor-water-tank|PASS|NEEDS REVIEW|52980|1020|
|329|malaysia-water-meter-box|PASS|NEEDS REVIEW|54144|936|
|330|malaysia-electric-meter-cabinet|PASS|NEEDS REVIEW|91848|1620|
|331|kampung-house-staircase|PASS|NEEDS REVIEW|83656|1536|
|332|kampung-timber-veranda|PASS|NEEDS REVIEW|253336|4644|
|333|kampung-stilt-column|PASS|NEEDS REVIEW|37892|660|
|334|kampung-zinc-roof|PASS|NEEDS REVIEW|50608|1132|
|335|kampung-timber-window|PASS|NEEDS REVIEW|114424|2052|
|336|village-roadside-drain|PASS|NEEDS REVIEW|95684|1748|
|337|village-wooden-fence|PASS|NEEDS REVIEW|100396|1836|
|338|village-chicken-coop|PASS|NEEDS REVIEW|655064|12096|
|339|village-outdoor-washing-area|PASS|NEEDS REVIEW|123672|2232|
|340|malaysia-taman-entrance-sign|PASS|NEEDS REVIEW|55512|984|
|341|mrt-station-entrance|PASS|NEEDS REVIEW|138860|2496|
