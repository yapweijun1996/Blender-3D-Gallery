# Bus Driver (268)

## Contract
One original editable character registration, with clothing and props as components, not additional asset counts. Metre units; Blender +Z up / -Y front converts to glTF +Y up / +Z front. CharacterRoot is floor-centred. Rigid articulation only: no skin, runtime IK or autonomous NPC behavior.
Idle and CheckMirror are 2-second clips authored at 30 fps, frames 0–60.

Occupation action CheckMirror moves HeadJoint with explicit reset tracks. Both hands remain aligned with separate steering-wheel grip markers. The seated torso, bent legs and seat are modeled explicitly. CheckMirror is a head-check pose, not wheel-turning or vehicle control.

## Evidence
Local **PASS**, release **NEEDS REVIEW**. GLB SHA-256: 54be97856b0e4f86a69d0964d91762e7d63b49d2bc1f50d47ceed47d9419dc51
4992 triangles, 477004 bytes and 65 primitives, within fixed pre-generation limits of 15,000 triangles, 2 MB and 120 primitives.
reports/assets.json contains structural and 41-sample motion evidence. reports/sources.json proves mesh/material edits saved to a copied blend, reopened and exported without regenerating geometry, with canonical source unchanged.
reports/visual-review.json binds final inspected images to the GLB hash. Seven studio angles/action frames and 12 browser pose/viewport frames were inspected per role.
Full evidence is under docs/verification/characters-walk-six/final. All 416 repository unit tests, build, 18 gallery cases, 12 motion cases and 4 lifecycle cases pass. Full library regression was not run in this tranche.

## Reproduce
From repository root:
- node models/bus-driver/validate.mjs
- Blender background, 2 threads: --python models/bus-driver/inspect_sources.py
- node models/bus-driver/verify_source_edit.mjs
- npm run build
- MALL_QA_DIR=<fresh-directory> node scripts/test-characters-walk-six-browser.mjs
- MALL_QA_DIR=<separate-fresh-directory> node scripts/test-bus-driver-motion.mjs

## Limitations and rights
Desktop Chromium viewport emulation is not physical Android/iOS or Safari/WebKit testing. No Gallery animation UI, public deployment, operational or safety certification is provided. Characters are wholly fictional. Original procedural geometry, materials and motion contain no third-party art, brands, fonts or real likeness. Owner-project reuse is authorized; public redistribution terms are unspecified.
Some screenshot filenames retain a lowercase “sweep” label from the pilot harness; the exact clip names and hashes in results.json identify the role's actual action.
