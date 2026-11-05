# Proton Saga (1985) — reference-led exterior study

Original procedural Blender interpretation of the first Saga four-door sedan. This revision follows the owner-supplied silver heritage references with formed body shoulders, continuous surface-fitted door shutlines, a crowned bonnet and connected screen-to-pillar reveals. Lightly bowed glazing has rounded corners, thin fitted seals and a smaller rear quarterlight; the roof headers sit flush with the screens. High-profile tires surround flatter pressed-steel wheels with actual tangential oval ventilation openings. Headlamps retain recessed reflector bowls under finely fluted rectangular lenses, with restrained bulbs and richer amber indicators. The front bumper contains real intake openings in its continuous apron, while the rear registration plate sits in the black panel between the segmented tail lamps. The connected lower apron and underbody faces are black, leaving the side panels silver.

The vehicle remains an artistic reconstruction with approximate dimensions and simplified surfacing, rather than a scan, factory CAD model or exact trim replica. The body proportions were inferred visually from reference images; their printed specifications were not independently verified. A basic right-hand-drive cabin can be seen through the smoky glazing. There is no engine, opening panel, animation or photographic texture. The small sun-and-shield crest is an original simplified identifying detail, not official logo artwork.

## Reproduce

Requires Blender 5.1.2 and `cwebp`. From the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python models/proton-saga-1985/generate.py
```

The deterministic generator replaces `exports/proton-saga-1985.glb`, editable `scene.blend`, `preview.webp`, and the four studio renders `view-front.webp`, `view-rear.webp`, `view-left.webp`, `view-right.webp`. Intermediate PNGs are converted and removed automatically. Metadata and this document are maintained separately and preserved. For an authoring preview, append `-- --quick`; this writes a smaller preview and skips the four angle renders, so run the normal command again before publication.

Only the vehicle hierarchy rooted at `ASSET_Proton_Saga_1985` is exported. Evaluated opaque export copies are batched by material to reduce draw calls while the saved Blender source preserves independently editable parts. Transparent windows remain separate; fine transparent prisms batch only within the same front lamp. Modifier evaluation, split normals and multiple material slots are retained. Pane normals are checked against their outward direction during generation; mirrored rim and cutter windings are corrected before wheel booleans. Camera, floor and lights remain in the source but are excluded from the GLB. No random seed, external images, downloaded scripts or third-party meshes are required.

Blender front is −X, physical left is −Y and up is +Z. All four views use the same charcoal studio, lighting and silver/black/red materials. Front/rear framing is fitted to their narrower silhouette; every view is a genuine render of this model.

## Provenance and verification

Historical sources: [PROTON milestones](https://www.proton.com/corporate/milestones) and [PROTON heritage gallery](https://www.proton.com/happenings/2021/november/proton-unveils-new-brand-gallery). Owner-supplied reference images guided this revision. References were viewed only; their pixels, specification tables and photographs are not bundled or embedded. Artwork redistribution terms remain pending owner decision; vehicle names identify the subject and imply no endorsement.

Measured export: **2,983,952 bytes**, **84,080 triangles**, **77,352 stored vertices**, **16 materials**, **23 meshes / 24 scene nodes**, and **0 animation clips**. Khronos validation reports zero errors and zero warnings. These values describe the batched GLB, not the editable source object count. Accuracy limits and machine-readable metrics are recorded in `metadata.json`. Run `npm run validate:assets` for glTF structural validation and `node scripts/test-saga-browser.mjs` for actual four-view browser operation. Source existence or a render alone does not establish browser compatibility. Chromium mobile viewport checks do not prove operation on every physical phone or engine.
