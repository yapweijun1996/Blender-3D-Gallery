# Fourth 50-asset tranche: domestic, retail and food-service (16 types)

All 16 local PASS; release NEEDS REVIEW. Base 6d204af06acbd317ebb572436fba202c22e49e0a. Exact V1 IDs retained by V2.1 are in per-asset backlog.json and domestic011-slugs.json. Existing 244 entries preserved, 16 appended, 260 total in this isolated checkout. No equivalent independent model found: shopping cart differs from retail pop-up/cendol carts; closed shoe cabinet differs from open prayer shoe rack; conveyor retail checkout differs from library self-checkout or service counters.

## Verified evidence
- asset-results.json: per-asset status, final GLB/source hashes, budgets, clips and evidence paths. Total 54,604 triangles / 2,852,004 GLB bytes.
- Per-asset reports/assets.json and validation logs: Khronos 0 errors/warnings, finite meshes/normals, internal buffers, metric scale/orientation, source-root identity and fixed upfront budgets.
- reports/sources.json and source-edit logs: manifold source meshes and actual mesh/material edits saved to a copy, reopened and exported without generation; canonical source unchanged. Latest dispenser/sink evidence uses hollow-fixed/drain-fixed suffixes.
- All 64 final four-angle studio views and 10 final midpoint action views actually inspected. Sink additionally has a near-top detail view proving basin/drain geometry. Studio previews render the Blender source; browser screenshots render actual exported GLBs.
- All 48 final-hash initial browser screenshots visually inspected. browser/results.json has 48/48 cases PASS. Sink drain was corrected afterward: browser-sink-fixed/results.json has 3/3 final-hash cases; other 45 remain unchanged and hash-matched. Earlier results retained, not overwritten.
- Chromium at 1440x900, 768x1024 and 390x844: full GLB bytes/SHA actually consumed, WebGL draws, orbit/zoom/exact reset, close/reopen, no request/console errors or overflow. This is viewport emulation, not physical mobile.
- Unit gate 349/349 PASS and build PASS; final logs are authoritative.
- scripts/test-domestic011-browser.mjs defaults to all 48 cases; every output honors MALL_QA_DIR. Optional explicit MALL_QA_ASSETS runs the same assertions for selected assets.

## Preserved corrections
Initial numeric gates passed, but actual visual inspection found rear coplanar seams on refrigerator/letterboxes/checkout, cropped opening-lid previews, a solid dispenser tank under its lid, and the sink drain below the pedestal top. Geometry corrected without raising budgets or weakening assertions. Opening previews now frame actual animated bounds. Tanks have independent walls/bases and visible interior openings. Sink drain has a new clearance assertion and inspected detail view.
Before-rear-seam-fixes contains original generators, canonical sources, GLBs and four PNG angles for all three seam fixes. Before-lid-fixes contains rice-cooker/dispenser original generator/source/GLB/hero/open/report snapshots. Before-sink-drain-fix contains sink generator/source/GLB/report/four PNG angles. Initial contact sheets and all generation/QA logs retained. Not every intermediate source-edit copy or intermediate camera-only preview was archived; no complete archival claim is made.

## Limits
Metadata remains draft. Physical Android/iOS/WebKit NOT TESTED. Combined 50-asset integration remains coordinator work. Asset-level clips only; no gallery playback UI. No actual cooking, refrigeration, dispensing, plumbing or checkout/payment functionality. No engineering/accessibility/safety certification. No copied assets, brand marks, external textures, private source URL, remote push/PR/merge or deployment. Public redistribution license not specified; see LICENSE.md.
