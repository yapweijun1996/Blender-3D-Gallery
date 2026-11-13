# Cleaner character pilot (266)

## Results
Local asset **PASS**; release **NEEDS REVIEW**. One original rigid articulated character, not a skinned or IK-ready rig and not an autonomous NPC. No other characters are included.

- 3,924 triangles, 408,396 bytes, 46 primitives, within the pre-generation limits of 15,000 triangles, 2 MB and 120 primitives.
- Height 1.75 metres; Blender +Z up / -Y front, glTF +Y up / +Z front, floor-centred origin.
- Editable named meshes, materials and rigid joint hierarchy; broom is a component, not another catalog registration.
- Idle and Sweep are 2-second clips, authored at 30 fps from frame 0 to 60. Each exports 51 tracks with explicit reset channels.
- 41 samples per clip verify actual transformed foot vertices, root position, grip alignment and bristle contact. Foot/root/grip drift is zero; floor error is below 0.000001 metre. Sweep rotates the shoulder by 0.26 radians and moves the brush 0.152 metre from its initial pose.
- Raw first/last keys, loop reset and clip switching pass. No walking, navigation, collisions, skin deformation or universal animation-retargeting claim.
- Saved-copy mesh and roughness edits survive save, reopen and GLB export without rerunning procedural generation; canonical source remains unchanged.
- 406 unit tests, build, 3 gallery viewport cases, 4 gallery lifecycle cases and 2 isolated browser animation cases pass. Full library regression was not run for this pilot.

## Evidence
Final GLB SHA-256: a0d791797cfe8883aa738492b04aaa53b3feac12f8b76041723270dd0f0a35d4

See reports/assets.json and reports/sources.json beside the source. Repository evidence is under docs/verification/cleaner266-pilot:
- final/: unit, build, source-edit, gallery and lifecycle logs/results.
- reset-channels/animation/: independent Three.js animation results and pose/loop/switch screenshots.
- review-0.jpg through review-4.jpg: all 19 final studio, action and browser frames inspected. Full body and broom remain visible, work clothing and face readable, feet stationary and broom held while sweeping.
- first/: original failing reset-channel validator and complete initial artifact; initial/: earlier missing-script launch failure. Neither is presented as a pass.

The actual export correction retains constant joint animation channels. No validator assertions or budgets were weakened. One inherited gallery report label says “street asset camera”; the tested asset ID and exact GLB hash are cleaner, not a street asset.

## Reproduce
From repository root, with installed project dependencies:
- node models/cleaner/validate.mjs
- Blender background, 2 threads: --python models/cleaner/inspect_sources.py
- node models/cleaner/verify_source_edit.mjs
- npm run build
- MALL_QA_DIR=<fresh-output> node scripts/test-cleaner.mjs
- MALL_QA_DIR=<different-fresh-output> node scripts/test-cleaner-animation.mjs

Do not regenerate the canonical source to prove manual edits. Source-proof scripts use a copied blend.

## Limitations
Chromium viewport emulation is not physical Android/iOS testing. Safari/WebKit is untested for this asset. The existing gallery has no new animation-control UI; isolated AnimationMixer tests demonstrate the asset clips only. Visual style and broader character production require pilot acceptance. No deployment or release is claimed.
