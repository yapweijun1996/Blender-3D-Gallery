# Mall Escalator Handrail · V2.1 P0 430

One reusable, static **handrail / glazed balustrade subsystem**, not a full escalator. The continuous black belt follows horizontal approaches, tangent curved transitions and a 30° incline, then returns through the lower channel with rounded 180° noses. Eight independent named meshes and five materials remain editable in both the Blender source and GLB.

This is not full escalator 004, landing 429, or stationary glass railing 006. There are no steps, landings, motor, drive, mechanical simulation, animation clips or runtime movement. The optional pair preview is two instances of this **one logical asset type**, not two new models.

## Files

- `sources/mall-escalator-handrail.blend`: actual editable Blender source and source-only studio.
- `exports/optimized.glb`: self-contained, texture-free glTF 2.0, 117,180 bytes, 5,100 triangles, 3,516 vertices, eight mesh primitives, five materials.
- `previews/`: six 768 × 768 PNG masters and lightweight WebPs: hero, side, reverse, lower return detail, underside, and paired-instance context. `contact-sheet.webp` is a review montage.
- `metadata/mall-escalator-handrail.json`, `interface.json`, `provenance.json`, `LICENSE.md`.
- `reports/assets.json`, `geometry.json`, `sources.json`, `source-edit.json`: measured artifact and real source-edit evidence.
- `verification.md`: executed checks, failures, current-base limits and pending final integration.

## Geometry and visual interface

Blender uses metres, +Z up and +X ascending. glTF uses +Y up, +X ascending and Z = -Blender Y. The origin is at the lower datum elevation and the plan midpoint of the two end tangencies, not at the midpoint of the sloped glass.

Measured GLB envelope is **7.041641 × 3.428000 × 0.140000 m** in glTF X/Y/Z. Lowest underside is at Y = 0. Nominal elevation difference is 2.4 m; central incline is 30°. Belt width is 80 mm and glazing thickness is 12 mm. Belt centreline return radius is 400 mm; tangent transition radius is 800 mm. The geometry is deliberately low-poly and generic, not a precision manufacturer model.

Named anchors, in Blender coordinates:

| Anchor | X | Y | Z |
| --- | ---: | ---: | ---: |
| `CONNECTOR_LowerDatum` | -3.092820 | 0 | 0 |
| `CONNECTOR_UpperDatum` | 3.092820 | 0 | 2.4 |
| `CONNECTOR_LowerBeltTangent` | -3.092820 | 0 | 1.0 |
| `CONNECTOR_UpperBeltTangent` | 3.092820 | 0 | 3.4 |
| `CONNECTOR_PairPlane` | 0 | 0 | 0 |

For a **visual pair only**, instantiate at Blender Y = -0.64 and +0.64 m, without changing the source mesh scale. This gives 1.14 m between the casing envelopes, measured from actual GLBs. It does not establish passenger-clearance compliance or a particular step width. The source is symmetric through its thickness, so no negative-scale mirror is required.

Actual GLB raycasts at the lower horizontal, central incline and upper horizontal verify that glass edges sit inside both guide rails. Belt/upper-guide clearance ranges from approximately 7.57 to 15 mm; lower-return/rail clearance ranges from 24.57 to 32 mm. Rounded nose belt/glass radial clearance is 49 mm, and return-belt/casing lateral clearance is 10 mm. These are modeled visual separations, **not validated operating clearances**. Guide rails intentionally overlap glazing and casing where they visually support them.

**Exact future full-escalator 004 integration is NOT VERIFIED.** No manufacturer dimensions, installation connections, load paths, strength, code/safety compliance, slip resistance or fabrication suitability are claimed. No existing landing or full escalator was copied into the asset. Engineering and application-specific adaptation remain necessary.

## Editable parts

- `MODULE_ContinuousRubberBelt`: one connected, closed genus-one manifold; no open ends.
- `MODULE_UpperGuideRail` and `MODULE_LowerGlazingRail`.
- `MODULE_CurvedGlazing`: solid 12 mm visual glass proxy with rounded ends.
- `MODULE_Casing_Near` and `MODULE_Casing_Far`.
- `MODULE_ChannelEnd_Lower` and `MODULE_ChannelEnd_Upper`.

All eight meshes are closed, consistently wound, positive-volume components. Glass uses alpha blending rather than a costly refraction/texture stack. No external resource or Draco/meshopt decoder is required. Studio ground, lights and camera are excluded from the GLB.

## Reproduction

Authored with Blender 4.0.2 on Ubuntu ARM64; CPU Cycles, deterministic geometry, no random seed and no external models, fonts or textures. Run from the repository root using Blender, Pillow and the existing Node dependencies:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-escalator-handrail/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-escalator-handrail/render_views.py
python3 models/mall-escalator-handrail/prepare_previews.py
blender --background --threads 2 --python-exit-code 1 --python models/mall-escalator-handrail/inspect_sources.py
node models/mall-escalator-handrail/validate.mjs
node --test tests/mall-escalator-handrail.test.mjs
npm test
npm run build
node scripts/test-mall-escalator-handrail.mjs
TEST_ARTIFACT_DIR=models/mall-escalator-handrail/reports/library npm run test:library
```

Normal generation replaces the source with the procedural design. To preserve manual `.blend` edits, run the generator with `-- --export-source --skip-render` instead. Reopen the source, select named meshes and edit their vertices/materials; do not change studio objects when editing the delivered geometry. Re-render previews and refresh measured metadata after design edits.

For a disposable source-edit test, pass a **new, nonexistent** output folder after `--` to `inspect_sources.py`. This saves an isolated source copy with only belt width 80 → 90 mm and rubber roughness 0.48 → 0.62 changed, plus a self-contained copied generator. Run that copy with `--export-source --skip-render`, then pass its GLB to `verify_source_edit.mjs`. The delivered source hash must remain unchanged and the other seven mesh geometries must be identical. The shipped reports record this real edit/reexport test.

Website builds consume checked-in artifacts, not Blender scripts. Render pixels may vary with Blender version and hardware. Browser viewport emulation does not verify physical Android/iOS hardware.

## Rights and delivery status

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Downloads remain disabled; interactive viewing still serves GLB bytes. No public CC0/MIT artwork grant or manufacturer endorsement is assumed.

Initial work is isolated on actual GitHub main `b7421d2`. No unmerged prior-batch asset commit or application fix was incorporated. Initial full unit/build/library checks pass, but all three strict browser cases fail the old-loader `net::ERR_ABORTED` gate. Final integration on main after PR 12 merges remains **PENDING**. This prepared local asset does not claim a push, PR, release or deployment.
