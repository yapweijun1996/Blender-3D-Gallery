# Mall Atrium Balcony

V2.1 P0 item 428. One logical model in the ten-new-model batch, not another count for the included existing 006 railing or 421 flooring.

A simple reusable 2 m straight atrium-edge bay: ivory terrazzo deck, mineral slab, inset soffit, champagne fascia and existing sea-green glass railing. It is a modular edge piece, not an entire mall or a structural construction detail.

**Local checks: PASS. Overall: NEEDS REVIEW.** Physical Android/iOS devices remain untested. No deployment, engineering, structural-load, safety, barrier or building-code certification is asserted. See [verification.md](verification.md).

## Components, origin and repeat joints

- Source is in metres, Blender +Z up; export is glTF +Y up. The root is the **local slab-underside centre**, not building ground. Translate the whole root to the required installation elevation.
- Main deck is 2.00 × 1.20 m and 0.25 m thick to the finished tile surface. Railing base is exactly at that surface, with rail centre line 0.52 m toward the atrium edge. Total standalone bounds are 2.16 × 1.371 × 1.22 m (glTF X/Y/Z).
- `MODULE_Deck` contains independent slab, soffit, fascia, adapted filled grout and eight tiles. `MODULE_Post_Left`, `MODULE_Post_Right` and `MODULE_Infill` contain the real 43 editable source meshes from the existing two-metre railing.
- `MODULE_EndCap_Left/Right` are 80 mm exposed-end closures. They support the outer half of the end-post plates and close the slab ends. They are **not** repeated at internal joints.
- For a straight run, translate whole bay copies by exactly 2 m along X. Retain the left post only on the first bay; retain every right post. Retain the left end closure only on the first bay and the right closure only on the last. Keep every deck and infill. Thus three bays have **four posts, not six**, two end closures and a 6.16 m overall length.
- `layouts.json`, `render_views.py` and the live GLB validator apply that exact recipe. Do not chain complete bay exports without removing shared posts and internal end closures. Arbitrary corners, structural attachment details and a runtime assembly editor are not supplied.
- Named connector empties mark joint plate centres, the deck surface and underside. glTF position `(x,y,z)` maps to Blender `(x,-z,y)`.

## Actual reuse and source editing

Input SHA-256 values are recorded in [provenance.json](provenance.json). Existing input files are unchanged. The validator compares **all 3,236 original railing triangles**, transformed into the new assembly, to the actual 006 GLB. The original railing materials and alpha-glass design are reused. All original 421 material definitions and the embedded 512 × 512 original artwork match the existing flooring export.

The eight tiles derive from the actual 421 source mesh. Two outer tile strips are cropped to 396 mm; interior tiles remain 596 mm. UV coordinates retain original artwork scale rather than stretching it. The original filled-grout heightfield pattern is adapted to this 0.4/0.6/0.6/0.4 m deck grid. This is reuse within the balcony assembly, not a new flooring kit.

The saved `.blend` contains **57 independently editable closed meshes**, named materials, editable bevels and a packed texture. No linked library or external image is required to reopen it or export edits. `--export-source` exports **every assembled component**, including appended railing and flooring parts. Normal generation rebuilds the source from the existing repository inputs, so back up manual edits before rebuilding.

The GLB keeps component nodes and deduplicates only exactly identical material definitions. It is 486,156 bytes, 4,940 triangles and 65 material primitives, with one embedded texture and no animations, cameras, lights, external URLs or compression-decoder dependency. Gallery WebP previews are 14–23 kB; larger PNG masters are archival, not card payloads.

## Reproduce

Blender 4.0.2, Python with Pillow, Node 22 and the locked project dependencies, from repository root:

```sh
blender --background --threads 2 --python-exit-code 1 --python models/mall-atrium-balcony/generate.py -- --skip-render
blender --background --threads 2 --python-exit-code 1 --python models/mall-atrium-balcony/render_views.py
python3 models/mall-atrium-balcony/prepare_previews.py
blender --background --threads 2 --python-exit-code 1 --python models/mall-atrium-balcony/inspect_sources.py
node models/mall-atrium-balcony/validate.mjs
node --test tests/mall-atrium-balcony.test.mjs
npm test
npm run build
node scripts/test-mall-atrium-balcony.mjs
node scripts/test-mall-atrium-glass.mjs
npm run test:library
```

Preserve source edits with `generate.py -- --export-source --skip-render`. To reproduce the real isolated-edit test, pass a fresh absolute directory after `inspect_sources.py -- /fresh/directory`, run that directory's copied generator with `--export-source --skip-render`, then run `verify_source_edit.mjs /fresh/directory`. The test changes fascia height and roughness, verifies all other 64 export primitives and other materials remain unchanged, and checks the original source hash. The copied generator exports successfully with no sibling source assets.

Studio views import the actual exported GLB. Glass uses viewer-compatible alpha 0.28, not physically refractive/transmissive glass. The checker diagnostic compares unchanged original-glass output with opaque and hidden controls; the checker is not part of the model.

## Rights

Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified. Included original project railing/floor assets retain the same rights. Public downloads remain disabled.
