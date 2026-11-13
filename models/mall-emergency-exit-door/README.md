# Mall Emergency Exit Door · V2.1 P0 433

A single muted oxide-red leaf, warm-grey independent frame, three hinges, horizontal stainless push bar, rear pull, kick plate, articulated overhead closer and a small **original EXIT** plaque. This is a visual asset, not certified equipment. It is deliberately distinct from glazed shopfront door 424.

## Deliverables

- Editable `sources/mall-emergency-exit-door.blend`, deterministic `generate.py` and optimized self-contained `exports/optimized.glb`.
- 315,348 bytes; 6,004 triangles; 11,712 vertices; 35 independent mesh primitives; six materials; no textures or animation clips.
- Khronos glTF Validator: **0 errors / 0 warnings**.
- Six 768 × 768 PNG masters and lightweight WebPs: closed hero, front, side, rear, open and closer/label detail.
- Local metadata, interface, provenance, rights, measured geometry and real source-edit evidence.

## Placement

Units are **metres**. Blender +Z is up and -Y is front; glTF +Y is up and +Z is front. Origin is the floor centre of the wall opening.

- Frame: 1.10 m wide × 2.18 m high × 0.14 m deep; opening 0.96 × 2.10 m.
- Leaf: 0.95 × 2.083 × 0.05 m; bottom gap 12 mm, side and head gaps 5 mm.
- Hinge pivot: Blender (-0.48, -0.05, 0), glTF (-0.48, 0, 0.05).
- Push bar: 0.79 m long, centre 1.03 m above floor; authoring depression 0–18 mm.
- Overall closed hardware envelope: 1.10 × 2.18 × 0.465 m. The articulated closer extends beyond the 0.14 m frame.
- The source sweep reaches 1.008 m in front of the wall plane. Keep at least 1.10 m unobstructed for this **visual model's** front sweep. This is a scene-placement envelope, not an evacuation-clearance specification.

The consuming scene supplies the wall opening and floor. No wall, surrounding building, lock/strike mechanism, glazing, complete stairwell or evacuation system is included. Studio floor, cameras and lights are excluded from GLB export.

## Source posing and re-export

Root `ASSET_MallEmergencyExitDoor` has `door_angle_degrees` (0–100, initially 0) and `push_bar_depression_m` (0–0.018, initially 0). Call `apply_pose(root)` from the generator after editing these values. The hinge and push-bar pivots are independent; the closer's two 0.28 m links are posed from actual frame/leaf anchors. All mesh parts remain independently editable.

To preserve manual geometry and material edits in the saved source, use:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-emergency-exit-door/generate.py -- --export-source --skip-render
```

The default mode rebuilds the asset. `--export-source` instead opens the delivered source, applies its saved authoring pose and exports without regenerating meshes.

The actual proof reopens the delivered source, sweeps 101 angles and three push positions, changes it from 0°/unpressed to **85°/18 mm**, saves an isolated copy, reopens it and exports. All 35 mesh coordinate arrays and frame placements remain unchanged; hinge, bar and closer placements change. The shipped .blend hash is unchanged.

Collision checks use conservative oriented bounding boxes from real source meshes. 7,272 tested moving-part/frame pairs have no collision across the sampled range; joined hinge and closer bearings are intentionally excluded. These sampled visual checks are not mechanical engineering, fabrication tolerances or physical safety validation.

## Reproduction

Blender 4.0.2; standard Python, Pillow for WebP, and existing repository Node dependencies. No external downloads or assets.

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-emergency-exit-door/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-emergency-exit-door/render_views.py
python3 models/mall-emergency-exit-door/prepare_previews.py
node models/mall-emergency-exit-door/validate.mjs
blender --background --threads 2 --python-exit-code 1 --python models/mall-emergency-exit-door/inspect_sources.py
node models/mall-emergency-exit-door/verify_source_edit.mjs
node --test tests/mall-emergency-exit-door.test.mjs
npm test
npm run build
node scripts/test-mall-emergency-exit-door.mjs
npm run test:library
```

## Limits and rights

**No certification, fire resistance, building-code or evacuation-safety claims.** EXIT letters are original geometric strokes, with no standards mark, third-party logo or manufacturer attribution. The gallery is a static orbit viewer. There is **no runtime door or push-bar UI**, and opening the source does not implement simulated evacuation behavior.

Physical Android/iOS is **NOT TESTED**. Local asset/source quality is separate from initial-base browser status and final merged-base integration, which remains **PENDING / NEEDS REVIEW**. See `verification.md`.

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Downloads stay disabled. No remote push, PR, merge or deployment was performed for this prepared item.
