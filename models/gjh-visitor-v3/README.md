# GJH Mall Visitor v3 — development preview

Adult male visitor from the owner's "GJH Visitor v3.0" sheet: navy open zip hoodie over a white tee, khaki chinos, white sneakers, black backpack, blue lanyard with ID card, steel watch on the left wrist, short wavy black hair. Independent of v1 and v2.

## Build

Needs Blender 5.1+ with the MPFB extension (v2.0.18 tested) installed in the user extensions directory.

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python models/gjh-visitor-v3/generate.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python models/gjh-visitor-v3/validate.py
node --test tests/gjh-visitor-v3.test.mjs
```

`generate.py -- --quick` skips animation and pose renders for geometry iteration.

## Contract

glTF +Y up, metres, floor Y=0, front +Z, 1.78 m. MPFB `game_engine` skeleton (53 bones, bone names such as `pelvis`, `spine_03`, `upperarm_l`, `thigh_l`, `hand_l`, finger bones). Twelve actions: `idle`, `walk`, `run`, `turn_left`, `turn_right`, `sit_down`, `stand_up`, `pick_up`, `carry`, `wave`, `point`, `push_cart`. They are poses only; the mall owns collisions, seats and props. Walk, run, push, turn, sit/stand and pick-up keep the lowest shoe vertex on the floor in every frame.

Call `createVisitorCustomization(scene)` from `customization.js` before display (hair wavy/short, hair colour, hoodie on/off, skin tone, backpack, badge, watch; `dispose()` when discarded).

The gallery uses a shared preview controller with separate v2 and v3 choices and
clip lists. After building the gallery, run `node scripts/test-visitor-browser.mjs`
to check both previews with their exported GLBs.

## Layout

`generate.py` (body, clothing, hair, accessories), `materials.py`, `animations.py`, `export.py`, `validate.py` (re-imports the GLB in Blender). Node tests: `tests/gjh-visitor-v3.test.mjs`. Evidence images in `previews/` and `previews/poses/`.

## Measured

21 meshes (draw calls), 21,714 triangles, about 1.1 MB, 12 actions, 17 materials; glTF validator reports zero errors and zero warnings. Blender re-import and Three.js playback have been checked. The exporter places skinned meshes at the scene root while preserving the armature binding.

## Known gaps

No textures or UVs (flat PBR colours); face, hair and clothing are simpler than the sheet; the short-hair variant is a thin crop; clothing is rigidly offset from the body so loose fabric does not drape; no LOD; no IK or hand-to-prop contact; not benchmarked on phones; the plan's `GJH_VISITOR_V3` node tree and Python unit tests are not implemented. MPFB base-mesh output licensing must be confirmed before public redistribution.
