# Grand Piano with Bench — P1

Original, brand-neutral baby grand for the S15 showroom podium. Advisor round 1 restores the original task's proportions and adds solid keys and near-floor pedals while preserving the curved glossy black case, warm gold details, tapered castered legs, three pedals and matching bench. Existing gallery ID, category, registration and default open-lid presentation are retained. No logos, lettering, textures, external models or network assets. The optional concept board `docs/references/gjh-mall-concept-board.png` was absent.

Original asset; reuse in the owner's projects is authorized.

## Measured delivery

`exports/optimized.glb` is self-contained glTF 2.0. **7,972 total triangles**, counting both lid variants and both collision boxes; **2 materials, 0 textures**. Default open state: 7,284 visible triangles / 4 draw calls. Closed state: 7,240 / 4 draw calls. The other state and collision boxes incur no draws. GLB size: 351,336 bytes.

Dimensions below use **glTF XYZ (width, height, depth)** in metres. One unit = one metre; origin = floor centre of the complete footprint; +Y up; front/keyboard faces +Z.

| Envelope | Width | Height | Depth |
| --- | ---: | ---: | ---: |
| Complete set, lid closed | 1.500 | 1.031 | 2.345 |
| Complete set, lid open | 1.500 | 1.812 | 2.345 |
| Bench | 0.660 | 0.550 | 0.360 |

The supplied `MallQueue/tasks/grand-piano.md` specifies a piano body approximately 1.50 m wide × 1.75 m deep × 1.0 m high, plus a bench. The measured body footprint is 1.500 × 1.750 m; case top is 0.993 m. The earlier 2.0 m complete-depth claim has no supporting dimension rule in that task or the available P1 rules. This revision removes uniform depth compression; the full set is 2.345 m deep, including the independently placed 0.360 m bench and its 0.235 m gap from the piano. The raised lid requires 1.812 m vertical clearance. Authoring uses Blender +Z up / -Y front. The stricter existing P1 budget remains 8,000 triangles, two materials, six draws and less than 1.5 MiB.

## Runtime contract

The default scene `GrandPiano_Open` has the single root `ASSET_GrandPiano`, with `piano_body`, `lid_open` and **`bench`** children. Body parts are merged by material; each lid and the complete bench are single meshes. The two materials are Black lacquer and Warm details; vertex colors distinguish ivory and brass-colored details. The 88-note A0–C8 keyboard uses **52 separated white key solids and 36 raised black key solids**. White keys have 25 mm thickness with 0.9 mm gaps; black keys rise 24 mm above the white surface and have a small leading chamfer. All keys merge into the existing body meshes by material, adding no draw calls. It is visual only. The lowered pedals clear the floor by 33.992 mm; extended lyre columns, braces and links meet the lowered crossbar. Small harp courses and pins use six radial sides, with a twelve-sample bridge, to preserve the strict triangle budget.

Core glTF has no standard node visibility flag. The **`lid_closed`** node is stored in the opt-in `VARIANT_LidClosed` scene so an unchanged gallery viewer renders only the open state. Its music desk is folded, and it has no prop stick. A consumer can cache both nodes and swap them under the same root:

```js
const root = gltf.scene.getObjectByName('ASSET_GrandPiano');
const open = root.getObjectByName('lid_open');
const closed = gltf.scenes.find(s => s.name === 'VARIANT_LidClosed')
  .getObjectByName('lid_closed');
function setLidOpen(isOpen) {
  open.removeFromParent();
  closed.removeFromParent();
  root.add(isOpen ? open : closed);
}
```

The bench has its **own floor-centre pivot** at `[0, 0, 0.992500]` relative to the asset root. Its extras provide `interaction: "sit"`, `seat_anchor_local_m: [0, 0.55, 0]` and `seat_facing_local: [0, 0, -1]` (toward the keyboard). Use `bench.localToWorld(...)` for the seat anchor after placement. These are registration data; seating gameplay remains the consuming application's responsibility.

Material-free **`collider_box`** (piano) and **`collider_box_bench`** (bench) live exclusively in `COLLISION_ONLY`, outside the default visual scene. They are hidden from viewport/render in the saved source, and must remain out of the render scene at runtime. Their extras identify the corresponding visual node. The piano box conservatively blocks its footprint up to closed-case height; the bench box matches its bounds. If moving the bench, move/rebind its proxy with it. Do not add collision geometry to the visible scene.

There is no audio, playable key actuation, continuous lid animation or pedal animation.

## Source and verification

`sources/grand-piano.blend` preserves 236 editable closed manifold meshes, including all 88 key solids. The generator exports evaluated copies and bakes complete world matrices before merging, preserving the authored geometry and manually saved edits. Studio cameras/lights are excluded from GLB. Front and three-quarter renders are provided for **both states**, plus hero/card, side and keyboard-closeup previews.

Run from the repository root:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/grand-piano/generate.py
node models/grand-piano/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/grand-piano/inspect_sources.py
node models/grand-piano/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/grand-piano/check_browser.mjs
```

Append `-- --skip-render` for a fresh rebuild without previews, `-- --export-source --skip-render` to export saved manual edits, or `-- --export-source --previews-only` to render saved geometry. Source-edit inspection uses disposable temporary copies. Restore `models/demo-beverage-can/reports/structure-motion.json` after npm test. Stage only this model folder and `models/catalog.json`.

Validated GLB SHA-256: `727fe758cb28cfe0fd6d2259550180a8e7b39e76dda5cfef9ee7977ace172d8e`.

Evidence: `reports/assets.json` and `khronos.json` measure the actual GLB; `sources.json` verifies source reopen/manifold scope and saved-edit export; `reproducibility.json` compares a clean independent rebuild; `browser.json` records real gallery loads and opt-in state rendering. `reports/contact-1440.png` and `contact-390.png` show both states from front and three-quarter views rendered from the validated GLB. The desktop gallery screenshot replaces `~/Documents/MallQueue/reports/grand-piano-page.png`.

Status remains draft / NEEDS REVIEW for human art approval. Chromium desktop/mobile viewport checks do not establish physical Android/iOS, WebKit, complete S15 integration, seating gameplay or target-hardware performance. Public redistribution terms remain unspecified. No push or deployment is included.
