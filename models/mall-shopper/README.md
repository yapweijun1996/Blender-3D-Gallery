# Mall Shopper (263)

## Contract
One original editable character registration, with clothing and props as components, not additional asset counts. Metre units; Blender +Z up / -Y front converts to glTF +Y up / +Z front. CharacterRoot is floor-centred. Rigid articulation only: no skin, runtime IK or autonomous NPC behavior.
Idle and WalkInPlace are 2-second clips authored at 30 fps, frames 0–60.

WalkInPlace is an alternating rigid hip/knee/ankle step gait, not root locomotion. Right foot swings during seconds 0–1 while left is planted; left swings during 1–2 while right is planted. Equal 0.4 m leg segments use analytic joint angles baked every frame. Swing lift is 0.12*sin(pi*u)^2 metres and fore/aft displacement is -0.10*sin(2*pi*u); ankle compensation keeps the sole level. The root remains fixed. This is not a runtime IK rig, skinned character, navigation system or forward-moving walk.

At 61 samples per clip, actual transformed boot vertices match expected stance/swing trajectories. Stance error is zero; maximum trajectory error is below 0.000001 metre; both feet reach 0.12 m clearance. Knee and hip maxima are 1.110 and 0.606 radians. Raw first/last keys, exact loop pixels and clip switching are independently checked.

## Evidence
Local **PASS**, release **NEEDS REVIEW**. GLB SHA-256: 4654369b8c8c5060fb972c3425611b4d0b0130335e10d37506966ec4dc8c650f
4012 triangles, 408060 bytes and 40 primitives, within fixed pre-generation limits of 15,000 triangles, 2 MB and 120 primitives.
reports/assets.json contains structural and 61-sample motion evidence. reports/sources.json proves mesh/material edits saved to a copied blend, reopened and exported without regenerating geometry, with canonical source unchanged.
reports/visual-review.json binds final inspected images to the GLB hash. Seven studio angles/action frames and 12 browser pose/viewport frames were inspected per role.
Full evidence is under docs/verification/characters-walk-six/final. All 416 repository unit tests, build, 18 gallery cases, 12 motion cases and 4 lifecycle cases pass. Full library regression was not run in this tranche.

## Reproduce
From repository root:
- node models/mall-shopper/validate.mjs
- Blender background, 2 threads: --python models/mall-shopper/inspect_sources.py
- node models/mall-shopper/verify_source_edit.mjs
- npm run build
- MALL_QA_DIR=<fresh-directory> node scripts/test-characters-walk-six-browser.mjs
- MALL_QA_DIR=<separate-fresh-directory> node scripts/test-mall-shopper-walk.mjs

## Limitations and rights
Desktop Chromium viewport emulation is not physical Android/iOS or Safari/WebKit testing. No Gallery animation UI, public deployment, operational or safety certification is provided. Characters are wholly fictional. Original procedural geometry, materials and motion contain no third-party art, brands, fonts or real likeness. Owner-project reuse is authorized; public redistribution terms are unspecified.
Some screenshot filenames retain a lowercase “sweep” label from the pilot harness; the exact clip names and hashes in results.json identify the role's actual action.
