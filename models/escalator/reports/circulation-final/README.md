# ID004 Escalator: canonical illustrative circulation

Overall: **NEEDS REVIEW**. This report describes the existing registered ID004, not only an unregistered candidate. No release/deployment or engineering/safety certification is claimed.

## Replacement and provenance
The previous static b4d71d7 asset lacked step circulation and had a raised landing transition. The replacement implements original curved-riser rigid steps, dual guide tracks, concealed return run, matched-speed handrail seam motion and flush lower/upper walking deck/comb surfaces (0/3 metres). The same catalog ID and paths are retained; no extra asset registration. Static bytes are preserved under ../../archives/static-b4d71d7; candidate failed generations and diagnostics are preserved under ../../candidates/curved-dual-track and ../curved-riser-candidate. Historical root reports are NOT the current evidence.

Canonical editable generator: ../../generate.py + ../../kinematics.py + ../../rail-profiles.json. Source: ../../sources/escalator.blend. Export: ../../exports/optimized.glb. Metadata: ../../metadata/escalator.json.

## Current evidence
65,408 triangles, 4,672,692 bytes, 138 primitives; unchanged caps 70,000 / 6,000,000 / 220. assets.json and raw-tracks.json: Khronos zero errors/warnings. sources.json and source-edit-export-proof.json: independent mesh/material edit, save/reopen/export without regeneration; canonical source unchanged.

actual-mesh-clearance.json: 1,201 poses, 1,985,253 step pairs, 47,376 fixed-component narrow tests, zero overlap at original 1e-6 m numerical tolerance. wheel-rail-sat.json: 154,919,392 actual wheel/rail tests, zero overlap at that same tolerance, exported/source rail mesh equivalence. raw-tracks.json and actual-glb-samples.json bind this proof to the canonical GLB. All 60 raw clips start at zero; no QA time trimming. Step period 46.4166667 s, handrail seam period 40.625 s, nominal speed 0.5 m/s. The uniform rubber belt is a static surface with moving seam markers, not a simulated deforming belt.

## Unresolved physical fidelity, not silently accepted
contact.json retains NEEDS REVIEW: maximum faceted contact gaps CHAIN 0.1897415 mm and GUIDE 0.3881115 mm. Initial design specified collision tolerance but NO acceptable contact-gap threshold. Continuous physical wheel contact is not proven. Attachment chord changes approximately 0.39523526 to 0.39999992 m; constant-pitch rigid chain engineering is not proven. Sampled collision-free illustrative motion does not imply force/contact dynamics or a buildable machine.

## Visual/browser review
Actual canonical hero/front/rear/side/quarter/half/three-quarter renders, lower/upper end-landing closeups, all four labelled cutaways, Gallery initial/rear pixels at 1440/768/390 and standalone Mixer open pixels at 600/390/375 were inspected. End decks are flush, return mechanism is enclosed in normal views; cutaways hide the fixed truss only in memory for inspection, not in the source/export. Contact sheets: contact-sheet-canonical.jpg and contact-sheet-canonical-small.jpg. Exact reviewed paths in final-pixel-review.json.

Three actual Gallery cases PASS (gallery/results.json); three standalone motion cases PASS (motion/results.json), all matching final GLB SHA with no console/request errors. Gallery has orbit/zoom/reset/lifecycle controls, not generic mechanism playback; separate browser-motion.mjs exercises the untrimmed raw clips. These are desktop Chromium viewport emulations, NOT physical Android/iOS/Safari tests.

17 scoped unit tests and build PASS (scoped-unit.log, registry-preview-unit.log, build.log); existing bundle-size warning retained. Documentation/manifest were added after this tested asset state; no geometry/runtime changes followed. Portable scripts in this directory and canonical validate.mjs/inspect_sources.py/verify_source_edit.mjs retain the precise assertions. Use MALL_QA_DIR for browser output isolation; local build must serve canonical registry assets. No public UI or old other-asset files changed.

Source SHA256: `1c1f11e9cc120dc78295e32bc605914742009953e4e9d065cfcd95908bc548b8`

GLB SHA256: `f8f8bda8b28a4faaf1fb2b03ee2a832fe23b90621eee9ab0a24a26c1b2b89ada`
