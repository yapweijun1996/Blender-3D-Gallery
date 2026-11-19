# Modular chibi: reusable template

Status: 2026-11-20. This is the recipe for adding a body, a garment, a hair style or a prop to the
modular chibi system, and for reusing it in the GJH Virtual Mall (v11) or a later web game. It
consolidates what shipped in the dress-up demo (`?page=chibi-dressup`): three bodies (Chibi, Girl,
Boy), 14 shared clips, 18 hand gestures, 4 hair families, tops, bottoms, shoes and four carry
props. Decisions and numbers live in `docs/chibi-dressup-progress.md`; mistakes live in
`docs/chibi-lessons-learned.md`; product rules in `docs/chibi-dressup-spec.md`.

## 1. Contract every asset follows

- One skeleton: 65 `mixamorig:*` bones, same names and parent hierarchy for every body.
- One mesh-only skinned GLB per module, at most 4 influences, textures at most 1024 px.
- Budgets: body 5k to 10k triangles, hair 1k to 3k, outfit 2k to 6k, shoes up to 3.5k, GLB at most 1.5 MiB.
- Clips are quaternion rotation plus optional hip/leg position and scale tracks, on the same bone names.
- Gestures are single-frame finger-only clips layered on top of any action.

## 2. Add a body

1. Build `body_<id>.glb` (feet on y=0, faces +Z), a retargeted 14-clip bank and a gesture bank on the same 65 joints.
2. Bake clip clearance so the body does not intersect itself (arms into hips, shins into thighs), then keep that bank as the single motion file for the body. Always check garments against the same bank the demo plays.
3. Strip the bank to skeleton and animations only: `python3 scripts/strip-motion-glb.py <bank.glb> <out.glb>`.
4. Copy `body.glb`, `motion.glb`, `gestures.glb` to `models/chibi-dressup/bodies/<id>/` (body at most about 1.2 MiB).
5. Measure per-body sockets (right-hand grips for cup, parcel, bag and jar, jar stops, shelf and chair placement) and, if the two-hand parcel needs it, finger corrections.
6. Add the body to `models/chibi-dressup/manifest.json` (`bodies[]`: `id`, `label` in three languages, `body`, `motion[]`, `gestures`, optional `sockets`, optional `layers.hold_box`). Validation lives in `src/chibi-dressup/config.js`.

## 3. Add a module (garment, hair, shoes)

1. Fit it to the body with the offset-bake method: required offset equals the deepest penetration plus 1.5 to 2 mm along the nearest surface direction, clamp 0 to 0.03 m, smooth, subdivide, re-smooth weights.
2. Run the motion gate (section 4) and an independent render review (section 5). At most three redo rounds per item, then record the reason and park it.
3. Add a candidate to `scripts/sync-chibi-dressup-modules.mjs` with `family` (the neutral id, so a choice follows the visitor across bodies) and `bodyIds`, then run `node scripts/sync-chibi-dressup-modules.mjs`. New or changed bytes come back `pending`; set `verified` only after both gates pass.
4. A garment that hides another slot (a dress covers bottoms) carries `excludesSlots`.

## 4. The motion gate (mandatory, every clip)

Scripts: `scripts/blender-chibi/motion_check_dense.py` (garment vertices inside the posed body) and `motion_check_tri.py` (garment-triangle against body-triangle overlap pairs). Both read a master `.blend` (objects `Armature` and `Base_Body`), the motion GLB and the garment GLB:

```text
DYLD_INSERT_LIBRARIES=<guard.dylib> Blender -b -noaudio -t 2 --python scripts/blender-chibi/motion_check_dense.py -- <master.blend> <motion.glb> <garment.glb> <out_dir>
```

Pass means 0 vertices inside, 0 triangle pairs and a minimum signed distance of at least 0.5 mm in every clip at integer and half frames, including rest, sit and the four carry clips. A T-pose pass alone proves nothing. Do not change pose-bone rotation modes (the clips animate quaternions). Use the same motion file the producer used, otherwise the check reports false penetrations. Run one Blender at a time with two threads on a shared machine.

## 5. Independent review

An independent model sees only the renders (six views) and the numbers, and answers PASS, PASS WITH NOTES or FAIL per item. A FAIL goes back for a fix. Small notes (a faint hairline, mild faceting) are accepted by the owner and recorded.

## 6. Web runtime rules

- 3D loads only when the page opens; the body, gestures and motion bank load first, and a module downloads the first time it is worn.
- Modules bind to the body skeleton by bone name; swapping one never reloads the body. Switching bodies rebuilds the character and falls back to the previous body if loading fails.
- Config (body, modules, clip, expression, gestures) is saved locally and restored.
- Run, in this order: `npm test`, `npm run validate:assets`, `npm run build`, then `CHIBI_DRESSUP_OFFLINE=1 node scripts/test-chibi-dressup-browser.mjs` (it tests the built output, so build first). Check exit codes before pushing.

## 7. Reuse in v11 and in a game

- v11 NPCs use the strict static-asset loader: no images, skins or animations in props; NPC wardrobe at most 1.5 MiB per GLB, 6 MiB total, 20k triangles per outfit; a `requireClothing` guard in the crowd code. See `docs/gjh-v11-npcs.md` in the Webpage-Design-Gallery repository.
- A game should load the same three files per body, the same manifest and the same rig code (`src/chibi-dressup/rig.js`: retarget by bone name, crossfade 0.2 to 0.4 s, sit and carry sequencing, finger layers). Keep props in shared GLBs and take per-body grips from `sockets`.
- Performance first: instance props, keep draw calls low, measure on a phone, and keep the iPhone free of stutter.
- Licence: Tripo output may be redistributed publicly in v11 and the gallery (owner confirmation, 2026-11-20). Record the licence of every other source before shipping it.
