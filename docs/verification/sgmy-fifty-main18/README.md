# SG/MY Library: 50-model batch on current main

**Local desktop quality gate: PASS. All 50 assets: overall NEEDS REVIEW for physical-device validation. No deployment.**

Exactly **50 new model types**, backlog **321–359 and 390–400**, in one PR. Current base is `f80e387` after the owner merged PR #18. All **140 existing main catalog entries** and existing files are preserved; the repository now has **190 unique entries**. This is not a claim that 190 of the planned 500 backlog models are complete.

## What was tested, and on which base

| Evidence | Tested base | Result |
|---|---|---|
| Full 50-asset desktop suite: 272 units, build, 150 viewport cases, 9 library, 4 lifecycle, 7 isolated animation assets, 14 legacy cases | `5ca54d3` before #18 merged | PASS |
| Fresh current-main suite: 277 units, build, 9 library, 4 lifecycle, 6 selected viewport cases, 14 legacy cases | `f80e387` after #18 merged | PASS |
| All 50 source/GLB/preview/metadata/evidence files copied without changes; 50 GLB and source hashes checked | current branch vs fully tested snapshot `7f414f2` | PASS |
| Existing runtime, public assets and dependency files unchanged between the two main bases | `5ca54d3` → `f80e387` | PASS |
| Actual exported animation-track endpoints and midpoint motion: 14 clips across 10 assets | unchanged GLB bytes | PASS |

The 150-case suite was **not rerun on f80e387**. Its exact evidence remains attributable to 5ca54d3; the files and runtime it exercised are unchanged. Fresh current-main checks cover the combined 190-entry catalog and representative model loading. All six fresh viewport images match the prior pixels/GLB hashes, and all 72 legacy PNGs match. All 150 prior initial-view hashes matched the applicable inspected producer evidence.

[Current stage exits](status.tsv) · [Preservation and provenance](preservation.json) · [Current pixel comparison](current-pixel-comparison.json) · [Per-asset statuses and hashes](asset-results.json) · [Full 50-model report/table and evidence](../sgmy-fifty-01/README.md)

## Deliverables and limits

- Each type has its own editable `.blend`, Blender Python generator, optimized `.glb`, multiangle rendered previews, metadata, license/provenance information and validation report.
- All 50 are local PASS; overall NEEDS REVIEW is explicit per asset. Total exported GLB payload: 5,579,856 bytes; 105,404 triangles across all 50 types, within their fixed individual budgets.
- Meter units, consistent axes, modular meshes/materials and separately editable movable parts. Ten assets contain 14 meaningful animation clips. Seven assets have additional isolated Three.js browser animation tests; transport clips have detailed Three.js AnimationMixer travel/clearance/restoration proofs. **No Gallery animation-playback UI was added.**
- Actual rendered previews were inspected. Some studio grain/backdrop bands remain documented. Signs and infrastructure are generic illustrative designs, not official routes or certified construction.
- Physical Android/iOS, Safari/WebKit and hardware performance are **NOT TESTED**. Desktop viewport emulation is not a substitute for those devices.
- Existing rights wording is preserved: owner-project reuse, public redistribution terms unspecified. Download flags remain unchanged in policy.
- Earlier failures and fixes are retained. The partial ten-model demo reload timeout did not recur in either subsequent fixed integrated suite; its cause was not assumed or hidden. Producer pending-combined-gate markers are historical; this report supplies the current integrated status.

A fresh unpublished branch was created from current main; only the 50 additions were copied, with exact provenance. No existing branch was merged or shared history rewritten. No main merge, deployment, or PR CI pass is claimed.
