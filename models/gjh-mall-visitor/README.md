# GJH Mall Visitor

Original reference-led rounded mascot for the owner's GJH mall concept: swept chestnut hair, a warm smiling face, open round glasses, an emerald polo with cream collar, navy cuffed jeans, white sneakers and a wristwatch. This is a decorative concept, not an official GJH spokesperson. The private visual reference is neither embedded nor redistributed.

## Runtime contract

The self-contained `exports/gjh-mall-visitor.glb` uses native metres, glTF +Y up and front +Z. Rest geometry is normalized to 1.72 m with its feet at floor Y=0. Root: `GJHMallVisitor`. Clip names: `idle`, `walk`, `sprint`. All clips remain horizontally in place, with separately articulated elbows and knees. Foot contact is baked from actual posed sneaker vertices at 120 Hz; constant reset channels are retained in every clip so transitions restore the complete pose. The consuming application owns locomotion, collisions and camera movement. No texture, external buffer, decoder or runtime network dependency is required.

Editable geometry is grouped by articulation node and shares material primitives. The source preserves named joints, meshes, materials and NLA tracks; the deterministic generator is the authority for individual facial/clothing features. It uses Blender's bundled font converted to geometry only for the small concept wordmark. The reference artwork and third-party models are not used as model data.

## Reproduce

With Blender 5.2.3 LTS and the repository's existing Node dependencies:

```sh
blender --background --python models/gjh-mall-visitor/generate.py
blender --background --python models/gjh-mall-visitor/inspect_sources.py
node models/gjh-mall-visitor/validate.mjs
# Optional authoring dependency: Pillow, outside the website runtime.
python models/gjh-mall-visitor/prepare_assets.py
```

The generator writes only this collection's source, GLB and rendered previews. Review scripts before execution. Renders include front, side, back, portrait, walking and sprinting views. Geometry is deterministic; render pixels may vary across Blender releases or hardware. Studio lights, floor and camera remain source-only and are excluded from the export.

`reports/assets.json` records actual exported bounds, bytes, triangles, primitives, clip tracks and Khronos results. `reports/sources.json` records reopened source verification and source/generator hashes. Passing scripts does not establish visual acceptance or deployed browser compatibility; those require the consuming project's release checks.

## Rights

Original agent-assisted procedural geometry and materials authored for Blender-3D-Gallery. Reuse in the owner's projects is authorized. Public redistribution terms have not been specified; no CC0, MIT artwork license, official endorsement or trademark ownership is asserted. Public viewing necessarily serves the GLB; gallery download controls remain disabled.

Consumers should vendor the reviewed export, pin the upstream revision and retain hashes/provenance. The website build does not execute Blender and the mall does not fetch models from GitHub at runtime.

## Geometry budget

The supplied concept suggests 2,000–5,000 triangles. Detailed geometric eyewear, facial features, swept hair and articulated limbs exceed that aspirational range. The reviewed acceptance ceiling is 15,000 triangles, 25 material primitives and 2 MiB; measured results remain in `reports/assets.json`. This is a deliberate quality tradeoff, not a claim to meet the reference's smaller triangle target.
