# Delivery Rider (267)

## Asset contract
One original character registration, with occupation-specific clothing and editable tool/prop components. All dimensions are metres; Blender +Z up / -Y front becomes glTF +Y up / +Z front. Root is CharacterRoot at floor level. This is rigid articulation, not a skin, IK rig, walking system, collision system or autonomous NPC.

Clips: Idle and CheckDelivery, each 2 seconds, 30 fps, frames 0–60. Explicit reset tracks are retained. The occupation action moves RightElbow and PhoneScreen; its motion contract is in contract.json. Props do not constitute additional model registrations.

## Evidence
Local asset **PASS**; release **NEEDS REVIEW**.
Final GLB SHA-256: cd51ab097af841bdd6123fa408a7d5a3d9b1ee203fe586d19d0b50d68ec276b7
4220 triangles, 425976 bytes, 44 primitives. Fixed pre-generation limits: 15,000 triangles, 2 MB, 120 primitives; never increased.

reports/assets.json contains raw endpoint, 41-sample transformed-foot, grip, root-drift, tool-clearance, occupation motion and clip-switching checks. reports/sources.json records a copied .blend mesh/material edit, save/reopen/export proof without generator execution and an unchanged canonical source.

Repository evidence: docs/verification/characters-six/final/gallery (three viewport cases per role), final/motion/delivery-rider (two clip cases, exact loop and switch screenshots), and final unit/build/lifecycle logs. Studio hero/front/rear/side and action frames are under previews/. Final actual pixels were reviewed before local acceptance.

## Reproduce
From repository root:
- node models/delivery-rider/validate.mjs
- Blender background with 2 threads: --python models/delivery-rider/inspect_sources.py
- node models/delivery-rider/verify_source_edit.mjs
- npm run build
- MALL_QA_DIR=<fresh-directory> node scripts/test-characters-six-browser.mjs
- MALL_QA_DIR=<different-fresh-directory> node scripts/test-delivery-rider-motion.mjs

Source-edit proofs operate on copies. Generator execution is not part of manual-edit validation.

## Limits and rights
Desktop Chromium viewport emulation is not physical Android/iOS or Safari/WebKit verification. No new Gallery animation UI is provided; isolated AnimationMixer tests exercise clips. No occupational, safety or engineering certification is claimed. Original procedural geometry/materials/motion, no third-party art, brands or real likenesses. Owner-project reuse is authorized; public redistribution terms have not been specified.
