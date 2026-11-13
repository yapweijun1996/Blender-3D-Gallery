# Mall Sprinkler Head · V2.1 P0 435

A compact **downward pendant visual prop** with a ridged fitting, hexagonal body, open yoke, glossy opaque red bulb representation, 12-tooth deflector and ivory ceiling trim. No brand or certification markings.

## Delivered asset

- Editable `sources/mall-sprinkler-head.blend` and deterministic `generate.py`.
- Self-contained `exports/optimized.glb`: **70,796 bytes, 2,752 triangles, 1,870 vertices, 13 independent meshes, four opaque materials**.
- Khronos glTF Validator **0 errors / 0 warnings**.
- No textures, animations, external buffers, cameras, lights or compression decoder.
- Six 768 × 768 PNG masters and lightweight WebPs: hero, front, side, top, underside and ceiling context.

Curved geometry is intentionally economical: 32 radial segments for the fitting/trim, 16 × 8 for the bulb and 48 outline vertices for the 12-tooth deflector. The annular fitting ridges suggest threads, but are not a functional helical thread or machining specification.

## Placement and orientation

Metres, Blender +Z up / glTF +Y up. The root and `CONNECTOR_CeilingMountPlane` are at the centre of the ceiling plane: Blender Z=0 / glTF Y=0.

- Overall envelope: **0.066 × 0.071 × 0.066 m** in glTF X/Y/Z.
- Fitting reaches 0.019 m above the plane; pendant reaches 0.052 m below.
- Ceiling trim diameter 0.066 m, underside depth 0.004 m.
- Pendant and deflector point **downward, Blender -Z / glTF -Y**. The model is not inverted to suit the gallery camera.
- Ceiling-context render uses a studio-only 0.030 m diameter opening. Measured minimum radial separation from all above-plane geometry is approximately 0.001 m, including the upper hex body; the fitting alone has 0.0045 m radial separation.
- The context ceiling is not in the exported GLB or asset hierarchy.

These numbers describe a visual envelope, **not installation instructions or safety clearances**. The consuming scene chooses placement. Intended assembly joins touch/overlap; components are individually closed meshes, not one printable/manufacturable volume.

## Materials and editing

The red bulb is an **opaque glossy representation**, not physical glass. No refraction/transmission or temperature encoding is claimed. All 13 meshes and four materials remain independently editable in Blender.

`inspect_sources.py` reopens the delivered source and verifies metric units, unit scales, manifold edges, nondegenerate faces, positive signed volumes, downward orientation and the actual above-plane mesh envelope.

The isolated edit proof widens only the bulb mesh by 15%, assigns it a copied amber material, saves a separate temporary source, reopens it and re-exports without regeneration. All 12 other mesh arrays and all component transforms remain unchanged. The shipped source hash is unchanged and the edited GLB validates 0/0. The temporary files are not shipped assets.

Default generator mode rebuilds the original geometry. To export an already-edited source without regeneration:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-sprinkler-head/generate.py -- --export-source --skip-render
```

## Reproduction

Blender 4.0.2, standard Python, Pillow for WebP and the repository's existing Node dependencies. No external input or random seed.

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-sprinkler-head/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-sprinkler-head/render_views.py
python3 models/mall-sprinkler-head/prepare_previews.py
node models/mall-sprinkler-head/validate.mjs
blender --background --threads 2 --python-exit-code 1 --python models/mall-sprinkler-head/inspect_sources.py
node models/mall-sprinkler-head/verify_source_edit.mjs
node --test tests/mall-sprinkler-head.test.mjs
npm test
npm run build
node scripts/test-mall-sprinkler-head.mjs
npm run test:library
```

Use isolated `MALL_QA_DIR` and `TEST_ARTIFACT_DIR` output directories for browser runs. The verification record preserves the single strict initial-base run rather than retrying or filtering failures.

## Scope, rights and limitations

**No temperature rating, flow, fire protection, installation or certification claims. No activation or simulation.** This is scenery, not functional fire-protection equipment, guidance or an engineering reference.

The old gallery camera looks down from above, partially hiding the yoke behind the ceiling trim. The underside/ceiling-context studio images document normal viewing orientation. Geometry stays physically downward and only the existing `previewRotationY` field is used. No viewer, schema or UI change is included.

Physical Android/iOS: **NOT TESTED**. Final merged-base integration: **PENDING / NEEDS REVIEW**. Local asset validation is not a release or merged-base acceptance; see `verification.md`.

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Downloads remain disabled. No remote push, PR, merge, history rewrite or deployment was performed.
