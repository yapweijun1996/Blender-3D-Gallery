# Mall Escalator Landing

V2.1 P0 item **429**, the tenth logical asset of this batch. A compact static landing threshold/access-plate module, **not full escalator 430** and not moving transport.

**Local checks: PASS. Overall: NEEDS REVIEW.** Physical Android/iOS devices remain untested. No mechanical compatibility, slip resistance, engineering, safety, manufacturer or building-code certification is claimed.

## Simple editable parts

Eight independently editable closed mesh objects under ASSET_MallEscalatorLanding:

- MODULE_AccessPlate_Front and MODULE_AccessPlate_Rear: two separate closed corrugated service plates, each with 25 broad ribs rather than hundreds of small objects.
- MODULE_SideTrim_Left and MODULE_SideTrim_Right: eased stainless edge trims.
- MODULE_FloorThreshold: flat mall-facing transition strip.
- MODULE_SupportTray: dark recessed backing below the access plates and comb base.
- MODULE_CombTransition: one closed simplified comb silhouette.
- MODULE_YellowMarker: independent yellow visual transition marker.

Five named Principled materials remain editable. The two access plates share one satin-aluminium material. Source trims retain editable bevels. No external texture, linked library, downloaded model, logo or font is used.

## Dimensions and placement

The module is **1.20 m wide × 1.20 m deep × 0.030 m high**. Blender uses +Z up; the GLB uses +Y up. The local origin is the underside centre. Blender -Y / glTF +Z is the mall-floor side; the opposite edge faces a future escalator.

The two 1.076 m-wide plates have a 2 mm central joint, with 2 mm side reveals. The plate wearing ribs are 3 mm above their valleys, finishing at 30 mm. Side trims are 60 mm wide; the front threshold is 60 mm deep. The simplified 27-finger comb spans 1.08 m, with 40 mm pitch and 80 mm projecting fingers. Comb top is 29 mm, intentionally 1 mm below the nominal wearing height. These are original **visual-asset dimensions, not fabrication specifications**.

Named connector empties survive export:
- FloorSide: glTF (0, 0.03, 0.6).
- FutureEscalator: glTF (0, 0.03, -0.6).
- LeftEdge / RightEdge: glTF (-0.6, 0.03, 0) / (0.6, 0.03, 0).
- Underside: (0, 0, 0).

All names have the CONNECTOR_ prefix in the source/export.

### Actual floor connection

Place the unchanged project 421 floor root at glTF **(0,0,1.2)**. This brings its edge directly against the landing threshold with the same 30 mm nominal top. Side floor roots may instead be placed at **(-1.2,0,0)** or **(1.2,0,0)** against the trims. Do not scale either module.

The validator loads both actual GLBs, checks all 72 mesh pairs per connection for positive-volume AABB intersection, checks edge alignment to 1 µm, and raycasts four actual wearing-surface pairs per connection. The original floor's 2 mm perimeter grout is intentionally 1 mm recessed; that is not an accidental gap. This is a visual floor connection, not installation engineering.

The assembly-floor preview shows the delivered landing beside the **actual original 421 GLB**, not a replacement tile illustration. That floor is not embedded in the standalone landing export or counted as another asset.

### Future escalator envelope

The layouts.json file documents a provisional 1.2 m outer envelope and 1.08 m central comb interface at glTF Z=-0.6. **No full escalator exists in this contribution, so compatibility is NOT TESTED.** Future item 430 must validate its own mating geometry, tread/comb relationship, elevation and clearances. No animation, balustrade, handrail, motor, runtime transport or complete escalator is supplied.

## Artifacts and reproduction

Blender 4.0.2, Python with Pillow, Node 22 and the locked repository dependencies:

~~~sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-escalator-landing/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-escalator-landing/render_views.py
python3 models/mall-escalator-landing/prepare_previews.py
blender --background --threads 2 --python-exit-code 1 --python models/mall-escalator-landing/inspect_sources.py
node models/mall-escalator-landing/validate.mjs
node --test tests/mall-escalator-landing.test.mjs
npm test
npm run build
node scripts/test-mall-escalator-landing.mjs
npm run test:library
~~~

Normal generation rebuilds the model and replaces its source. Preserve manual edits by using generate.py with --export-source --skip-render, which reopens and exports the saved .blend instead.

The genuine edit test opens the shipped .blend, lowers only the front plate ribs from 30 to 29 mm, changes shared plate roughness from 0.34 to 0.50, saves into an isolated directory and exports using its copied self-contained generator. It verifies all eight components are present, all seven unrelated meshes remain unchanged, other materials remain unchanged, and the delivered source is unchanged. To repeat, pass a fresh absolute directory after inspect_sources.py -- /fresh/directory, run that directory's copied generator with --export-source --skip-render, then run verify_source_edit.mjs /fresh/directory.

The optimized.glb is 83,352 bytes, 1,616 triangles, 2,616 vertices and eight material primitives. Exact duplicate material definitions are consolidated without flattening component nodes. There are no textures, animations, cameras, lights, external URLs or compression-decoder requirements. The five 768 px studio PNG masters and lightweight WebP previews are generated by importing the actual exported GLB.

## Rights and coverage

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Public downloads remain disabled. Existing 421 assembly-floor rights are unchanged. See provenance.json, LICENSE.md, verification.md and reports/.
