> Historical candidate evidence. The current registered illustrative version and its own hashes/proofs are in ../../reports/circulation-final/README.md. Candidate bytes and failure archives remain preserved.

# ID004 escalator circulation candidate

**Overall: NEEDS REVIEW. Not registered or deployed.** This is a bounded replacement candidate for the static ID004, not another model type. Original static and rejected rectangular-profile files remain byte-identical at baseline `2080cee2dabfae55f0d01f782de0cc6c0ede64c9` (which retains static `b4d71d7`). No other seven assets or catalog entries changed.

## Verified illustrative result
- 58 independently editable, complete rigid steps with curved risers and concealed return; four separate faceted-envelope guide rails; two handrail material-seam clips. No fading, scaling, texture-only conveyor or omitted riser.
- 65,300 triangles, 4,665,920 GLB bytes, 137 primitives. Original caps remain 70,000 / 6,000,000 / 220.
- Actual GLB Three.js sampling: 1,201 full-cycle poses; 1,985,253 step pairs, 47,376 fixed component narrow tests and 154,919,392 wheel/rail tests. No sampled intersection above the original 1e-6 m numerical tolerance.
- Actual deck and comb tops are 0 m / 3 m, aligned with horizontal tread level. The rejected 55 mm raised-cover candidate is archived. Solid covers were relocated outside the swept tread envelope, not pushed through steps.
- Raw clips now start at zero, close, and preserve near-0.5 m/s sampled travel. No hidden one-frame trim is required for ordinary looping. All 60 clips passed raw checks; Khronos reports zero errors/warnings.
- Saved-source mesh-width and material-roughness edits were reopened and exported without regeneration. Edited GLB independently confirms width ratio 0.92 and roughness 0.77; canonical source unchanged.
- Final seven studio views, four explicit diagnostic cutaways and eighteen browser images were actually inspected. Three Chromium viewport load/motion/reset tests match the final GLB SHA. Physical Android/iOS/Safari not tested; no Gallery controls added.

## Acceptance boundary remains explicit
The initial design declared a **1e-6 m nonintersection tolerance**, but no permissible physical wheel-contact gap. Final gap measurements are in `reports/final-contact-06.json`: approximately 0.190 mm maximum chain-roller gap and 0.388 mm guide gap, with 16-sided 35 mm rollers and 584/528 rail segments. These are measured faceting gaps, not a newly approved tolerance.

Attachment-to-attachment chord varies approximately 395.235–400.000 mm. A rigid constant-pitch drive chain, continuous physical contact, forces, independent wheel rolling physics, engineering suitability and safety certification are **not proven**. The uniform handrail surface is static geometry with an actual moving seam marker illustrating travel. This supports collision-free illustrative circulation, not a certified operating machine. Overall NEEDS REVIEW remains until the intended visual-library acceptance boundary is settled.

## Authoritative final evidence
- `reports/final-contracts.json`: dimensions, caps, source/GLB SHA, baseline preservation and explicit limits.
- `reports/raw-tracks-06.json`: zero-start clips, closure, speed, Khronos.
- `reports/actual-mesh-clearance-06.json`: actual exported step/body/comb/guard/enclosure checks.
- `reports/wheel-rail-sat-06.json`: actual rigid wheel polygons, source/export rail position equivalence, contact-plane nonintersection.
- `reports/final-contact-06.json`: residual gap measurements, no invented acceptance threshold.
- `reports/sources.json`, `reports/source-edit-export-proof.json`: editable saved-source/export proof.
- `reports/browser-06/results.json`, `reports/final-pixel-review.json`: final browser and inspected-pixel evidence.

## Reproduction from repository root
Use Blender 4.0.2 with two threads. `generate.py` depends only on adjacent original `kinematics.py` and `rail-profiles.json`; it does not need an existing GLB. The rail profiles retain their original analytic generation script and diagnostics.

```
P=models/escalator/candidates/curved-dual-track
blender --background --threads 2 --python-exit-code 1 --python $P/generate.py
blender --background --threads 2 --python-exit-code 1 --python $P/inspect_sources.py
node $P/capture_glb.mjs
node $P/check_raw.mjs
python3 $P/check_actual_mesh.py
python3 $P/check_wheel_rail.py
blender --background --threads 2 --python-exit-code 1 --python $P/check_final_contact.py
node $P/verify_edited_export.mjs
MALL_QA_DIR=/tmp/escalator-circulation-review node $P/browser_motion.mjs
```

Contact and final-contract scripts deliberately report NEEDS REVIEW, not a release approval. Browser harness uses the existing repository Playwright launch options. Diagnostic cutaway rendering hides only fixed opaque enclosure in memory and never saves/exports that state.

## Preserved failures
`reports/failed-generation-01` retains the 137,036-triangle / 7.99 MB candidate and exposed turnarounds. `failed-generation-02` retains incorrect seam speed and wheel/rail overlap. `failed-generation-03` retains corrected seam but old track collision. `failed-generation-04-raised-landing` retains corrected rails but the visible 55 mm deck error. `failed-generation-05-loop-offset` retains flush geometry with the one-frame raw clip hold. Each contains source, GLB, actual previews and relevant evidence. Rejected analytic tracks, the invalidated broad-phase harness report, dependency failure and raw logs also remain. No failure threshold was loosened; no old cache path was deleted.
