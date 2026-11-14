# Two new designs and four derivative extractions

Local-only draft packet, base `3c41bcfd660c69a41fe3bb7f5f56baed6f4b4e0b`. No runtime changes, remote operations, deployment or PR21 merge.

| ID | Asset | Classification | Local asset gate |
|---|---|---|---|
|094|Round Dining Table|NEW DESIGN|PASS|
|005|Passenger Lift|NEW DESIGN|PASS|
|175|Public Bicycle Rack|DERIVED EXTRACTION|PASS|
|281|Singapore Shophouse Facade|DERIVED EXTRACTION|PASS|
|282|Malaysia Shoplot Facade|DERIVED EXTRACTION|PASS|
|296|Chinese Lantern|DERIVED EXTRACTION; pinned PR21 parent pending|PASS|

Overall: NEEDS REVIEW. Physical Android/iOS and WebKit remain untested. Four derivative packages are not four new designs and their contribution to backlog/50-model counting is PENDING OWNER POLICY. No reuse aliases or backlog-completion mappings created. Lantern is derived from an immutable parent source on blocked PR21; it does not inherit released status or the failed demo runtime.

Each asset includes independent procedural authoring, saved editable .blend, GLB, three or more actual inspected exported-GLB previews, metadata/provenance/license, unchanged upfront budgets, structural/Khronos checks, copied-source component-position and material edits surviving save/reopen/export without generation, consumed-SHA browser evidence and actual image inspection. Original parent geometry is preserved byte-evidently through selected vertices/normals, oriented triangle topology, materials and rigid transforms; only floor-centering differs.

Lift has four synchronized bottom-door clips OR one closed-door 3m carriage travel clip. These modes are mutually exclusive; upper landing doors remain static. It is an illustrative cutaway, not operational safety equipment, passenger simulation or a Gallery interaction feature. Validators test raw track endpoints, synchronized leaf travel, aperture rays, full121-pose clearance sweeps and exact reset. Browser motion checks both modes separately with final consumed SHA and exact pixel reset.

## Portable checks
From repository root, with existing project dependencies:
```
node scripts/validate-gapextract06.mjs
node scripts/test-gapextract06-extractions.mjs
node scripts/test-gapextract06-table.mjs
node models/passenger-lift/validate.mjs
node scripts/test-gapextract06-source-edit.mjs
npm test
npm run build
MALL_QA_DIR=output/gap-six-gallery node scripts/test-gapextract06-browser.mjs
MALL_QA_DIR=output/gap-lift-motion node models/passenger-lift/browser-motion.mjs
```
To independently rerun source-edit proof, copy new model folders and scripts into an isolated fixture preserving relative structure, then run Blender background/two threads `--python scripts/inspect-gapextract06.py` followed by the source-edit JS checker. This writes proof copies/reports, not canonical source. Do not overwrite prior shipped evidence.

## Preserved failure history
- Loaded Three.js node-name sanitation required looking up sanitized names while still asserting exact original GLB names.
- Parent lantern export reordered triangles. Proof retains exact position/normal arrays and compares the multiset of oriented triangles (cyclic rotations only, winding preserved), not arbitrary vertex-count equivalence.
- Initial Gallery build rejected missing accuracy_notes/attribution; added required metadata, did not alter schema or assertions.
- Initial lift motion pixel-reset check sampled nominal49/24 instead of actual Float32 track endpoint. Preserved before script/log/screenshots; corrected sampling to exported endpoint while retaining independent timing/pose checks and exact pixel equality.

All limitations and final asset hashes are in individual reports. No production certification or unverified compatibility claim.
