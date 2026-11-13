# Mall Fire Hose Reel Cabinet · V2.1 P0 434

A wall-mounted red metal enclosure with an independent opaque hinged door, original FIRE HOSE lettering, three-spoke reel, seven-turn dark hose coil, short displayed tail, clipped brass nozzle and simple hardware. This is a **visual module**, not equipment guidance.

## Deliverables and budget

- Editable `sources/mall-fire-hose-reel-cabinet.blend`, deterministic `generate.py`, and self-contained `exports/optimized.glb`.
- **474,576 bytes / 15,156 triangles / 15,464 vertices / 64 independent meshes / six materials**. No texture, glass, animation, external buffer or decoder.
- Khronos glTF Validator **0 errors / 0 warnings**.
- Six 768 × 768 PNG masters with lightweight WebPs: open hero, closed, front, side, rear and interior detail.
- Metadata, interface, provenance, rights, geometry/topology, source reopen and real isolated mesh-edit evidence.

The initial 96-section-per-turn hose and finely bevelled label strokes were unnecessarily dense (748,640 bytes / 23,060 triangles). The delivered version uses 64 sections per turn and single bevel segments on sub-millimetre label strokes, reducing bytes 36.6% and triangles 34.3%. Eight-sided hose cross-sections, seven turns and the interturn separation are retained. It remains well below repository candidate budgets of 5 MiB and 100,000 triangles.

## Scene placement and source structure

Units are **metres**, Blender +Z up / -Y front, glTF +Y up / +Z front. The origin is the cabinet bottom rear centre. The consuming scene supplies the wall and chooses the placement height; this asset includes no surrounding wall or building.

- Enclosure: 0.72 m wide × 0.82 m high × 0.235 m deep.
- Open authored display envelope: approximately 0.933 × 0.82 × 0.975 m, including the door and rear tabs.
- Reel diameter: 0.576 m. Hose diameter: 0.024 m; radial pitch 0.027 m; approximately 0.003 m radial interturn gap.
- Door pivot: Blender (-0.365, -0.257, 0), glTF (-0.365, 0, 0.257).
- Delivered pose is **105° open** so the coil/nozzle are visible. The closed preview shows the original label. All door strokes and hardware follow the independent pivot.
- Opaque metal only. No glass/transparency claim or test is applicable.

These dimensions describe rendered geometry, not installation or equipment specifications. Hinge joins, reel axle and nozzle clip are simplified visual connections.

## Source posing and actual editing

Root `ASSET_MallFireHoseReelCabinet` has `door_angle_degrees` from 0 to 105. Call `apply_pose(root)` after editing it. The saved .blend contains the independently editable enclosure, door, reel, coil, hose tail, nozzle and hardware.

Default generator mode rebuilds original meshes. To reopen an edited source and export it without regeneration:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-fire-hose-reel-cabinet/generate.py -- --export-source --skip-render
```

The actual proof reopens the delivered source, checks metric units/unit scales, manifold topology, zero degenerate faces and positive signed volume for all mesh parts. It samples **106 door angles** with conservative source mesh collision/clearance checks. Joined hinge bearings are excluded intentionally. These are visual geometry tests, not mechanical or safety validation.

A separate temporary source copy changes the door from 105° open to closed and lengthens the **nozzle-tip mesh by 20%**, then saves, reopens and exports. All other 63 mesh coordinate arrays remain identical, the enclosure/reel/hose placements are preserved, and the delivered source hash remains unchanged. The changed GLB also validates 0/0.

## Reproduction

Blender 4.0.2, standard Python, Pillow for WebP and existing repository Node dependencies. No external models, fonts, textures, downloads or random seed.

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-fire-hose-reel-cabinet/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-fire-hose-reel-cabinet/render_views.py
python3 models/mall-fire-hose-reel-cabinet/prepare_previews.py
node models/mall-fire-hose-reel-cabinet/validate.mjs
blender --background --threads 2 --python-exit-code 1 --python models/mall-fire-hose-reel-cabinet/inspect_sources.py
node models/mall-fire-hose-reel-cabinet/verify_source_edit.mjs
node --test tests/mall-fire-hose-reel-cabinet.test.mjs
npm test
npm run build
node scripts/test-mall-fire-hose-reel-cabinet.mjs
npm run test:library
```

## Scope, rights and acceptance limits

**No installation, fire-system operation, certification, pressure, flow or safety claims.** The letters are original simple geometric strokes, without manufacturer branding or certification marks. The gallery provides static orbit/zoom/reset, not runtime door controls or fire-system behavior.

Physical Android/iOS is **NOT TESTED**. Final merged-base integration remains **PENDING / NEEDS REVIEW**, distinct from local asset/source validation. See `verification.md` for initial-base browser evidence and preserved failures.

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Downloads remain disabled. No remote push, PR, merge or deployment was performed for this prepared item.
