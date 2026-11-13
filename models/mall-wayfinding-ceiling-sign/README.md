# Mall Wayfinding Ceiling Sign · V2.1 P0 438

Original overhead suspended, double-sided **North Walk / Level 02** wayfinding sign.
Midnight-blue housing, ivory lettering and original shop/food/lift pictograms, orange divider and satin aluminium hangers reuse the visual language of the existing floor-direction sign without duplicating its freestanding silhouette.

## Source, geometry and anchors

- Blender 4.0.2 source and deterministic Python generator; texture-free optimized GLB.
- Overall dimensions: 2.10 m wide × 0.162 m deep × 0.94 m drop. Housing is 0.46 m high.
- Origin: ceiling mounting-plane centre, Blender Z=0 / glTF Y=0. All geometry is below the plane. There is no floor base.
- Two named exported mount anchors: ANCHOR_CeilingLeft and ANCHOR_CeilingRight at X=-0.70 and +0.70 m.
- Eleven independently replaceable mesh-bearing export modules: Housing, HangerLeft, HangerRight, FrontFace, FrontText, FrontIcons, FrontArrows, RearFace, RearText, RearIcons, RearArrows.
- Front: Blender -Y / glTF +Z. Rear is a proper 180-degree rotation with positive scale, not mirrored text. Its left/right arrows are reversed for the opposite viewpoint.
- The source retains ten editable FONT labels. Icons and arrows are original solid meshes. Studio lights, camera and the render-only ceiling context are not exported.

## Edit and reproduce

Open sources/mall-wayfinding-ceiling-sign.blend. Edit the FONT objects in FrontText or RearText, then change matching solid arrows in FrontArrows or RearArrows when the illustrative route changes. Face panels, icons, housing and hangers remain separate collections. Text is not automatically fitted: keep labels within their column and recheck both faces after edits.

Export the saved edited source without rebuilding:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-wayfinding-ceiling-sign/generate.py -- --export-source
blender --background --threads 2 --python-exit-code 1 --python models/mall-wayfinding-ceiling-sign/render_views.py
python3 models/mall-wayfinding-ceiling-sign/prepare_previews.py
node models/mall-wayfinding-ceiling-sign/validate.mjs
```

Running generate.py without --export-source rebuilds the original and replaces manual edits. Export evaluates labels/bevels and joins only within the eleven semantic modules. It welds coincident Bfont boundaries and dissolves collinear degenerate cap diagonals on temporary export copies before triangulating. The delivered FONT source remains editable.

inspect_sources.py reopens the delivered source, verifies label fit, positive orientation, scale, positive volumes and closed evaluated geometry. It makes a real saved-source edit fixture: SHOPS becomes STORES and the front FOOD arrow changes from left to right. The saved fixture is reopened and exported without regeneration. verify_source_edit.mjs proves only FrontText and FrontArrows changed, all nine other modules and all module transforms remain identical, and the shipped source remains untouched.

After intentional edits, update metadata metrics/validation and corresponding source-label contracts. Run the focused unit test, full npm test, npm run build, strict scripts/test-mall-wayfinding-ceiling-sign.mjs and npm run test:library.

## Provenance, scope and limits

Original project-authored geometry/icons, Blender bundled Bfont labels, no external models, logos, textures or artwork. Existing actual floor-sign generator and metadata were inspected: that model is a 2.53 m freestanding totem with floor base, while this is a ceiling-mounted horizontal double-sided sign.

This is a static decorative scene prop with illustrative routes, not live navigation, an official mall route plan, safety/egress compliance, structural calculation, accessibility or fabrication specification. Public redistribution terms remain unspecified and downloads remain disabled.

Physical Android/iOS hardware **NOT TESTED**. Initial prepared-base evidence only; final merged-base integration **PENDING**. No push, PR, merge or deployment is included.
