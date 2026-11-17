# Grand Piano with Bench — P1

Original, brand-neutral baby grand for the S15 showroom podium. Reworked to the owner's **GJH Virtual Mall v11 P1 override (2026-11-17)** while preserving the curved glossy black case, warm gold details, tapered castered legs, three pedals and matching bench. Existing gallery ID, category, registration and default open-lid presentation are retained. No logos, lettering, textures, external models or network assets. The optional concept board `docs/references/gjh-mall-concept-board.png` was absent.

Original asset; reuse in the owner's projects is authorized.

## Measured delivery

`exports/optimized.glb` is self-contained glTF 2.0. **7,878 total triangles**, counting both lid variants and both collision boxes; **2 materials, 0 textures**. Default open state: 7,190 visible triangles / 4 draw calls. Closed state: 7,146 / 4 draw calls. The other state and collision boxes incur no draws. GLB size: 415,496 bytes.

Dimensions below use **glTF XYZ (width, height, depth)** in metres. One unit = one metre; origin = floor centre of the complete footprint; +Y up; front/keyboard faces +Z.

| Envelope | Width | Height | Depth |
| --- | ---: | ---: | ---: |
| Complete set, lid closed | 1.500 | 1.031 | 2.000 |
| Complete set, lid open | 1.500 | 1.812 | 2.000 |
| Bench | 0.660 | 0.550 | 0.307 |

The requested approximately 2.0 × 1.5 × 1.0 m is the closed set's depth × width × height. The raised lid requires 1.812 m vertical clearance. Case top is 0.993 m. Depth is compacted for chibi-friendly proportions while keeping the footprint centred. Authoring uses Blender +Z up / -Y front.

## Runtime contract

The default scene `GrandPiano_Open` has the single root `ASSET_GrandPiano`, with `piano_body`, `lid_open` and **`bench`** children. Body parts are merged by material; each lid and the complete bench are single meshes. The two materials are Black lacquer and Warm details; vertex colors distinguish ivory and brass-colored details. The 88-note A0–C8 keyboard uses **one ivory slab and 87 flat quads** (51 divisions and 36 accidentals), rather than individual key objects. It is visual only.

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

The bench has its **own floor-centre pivot** at `[0, 0, 0.846482]` relative to the asset root. Its extras provide `interaction: "sit"`, `seat_anchor_local_m: [0, 0.55, 0]` and `seat_facing_local: [0, 0, -1]` (toward the keyboard). Use `bench.localToWorld(...)` for the seat anchor after placement. These are registration data; seating gameplay remains the consuming application's responsibility.

Material-free **`collider_box`** (piano) and **`collider_box_bench`** (bench) live exclusively in `COLLISION_ONLY`, outside the default visual scene. They are hidden from viewport/render in the saved source, and must remain out of the render scene at runtime. Their extras identify the corresponding visual node. The piano box conservatively blocks its footprint up to closed-case height; the bench box matches its bounds. If moving the bench, move/rebind its proxy with it. Do not add collision geometry to the visible scene.

There is no audio, playable key actuation, continuous lid animation or pedal animation.

## Source and verification

`sources/grand-piano.blend` preserves 156 editable meshes: 155 closed solids plus one intentional flat keyboard pattern. The generator exports evaluated copies and bakes complete world matrices before merging, preserving the compacted geometry and manually saved edits. Studio cameras/lights are excluded from GLB. Front and three-quarter renders are provided for **both states**, plus the existing hero/card and side previews.

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

Evidence: `reports/assets.json` and `khronos.json` measure the actual GLB; `sources.json` verifies source reopen/manifold scope and saved-edit export; `reproducibility.json` compares a clean independent rebuild; `browser.json` records real gallery loads and opt-in state rendering. `reports/contact-1440.png` and `contact-390.png` show both states from front and three-quarter views rendered from the validated GLB. The desktop gallery screenshot replaces `~/Documents/MallQueue/reports/grand-piano-page.png`.

Status remains draft / NEEDS REVIEW for human art approval. Chromium desktop/mobile viewport checks do not establish physical Android/iOS, WebKit, complete S15 integration, seating gameplay or target-hardware performance. Public redistribution terms remain unspecified. No push or deployment is included.
