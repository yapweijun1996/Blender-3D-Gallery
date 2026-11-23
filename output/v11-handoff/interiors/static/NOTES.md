# GJH Virtual Mall v11 static interior props

The manifest identifies each delivered GLB by its exact SHA-256, source file, measured bounds and render hashes. Values in `dimensions_m` are the v11 declared sizes. Bounds use glTF XYZ in metres, with Y up and +Z facing the front.

The handoff contains all 12 interior props. The desk uses the corrected static source at `../raw/desk-01-service-desk.glb`. The other 11 manifest entries and GLB hashes match the previous handoff.

## Reproduce

Run from `output/v11-handoff/interiors/static`. Blender 5.1.2 uses its built-in glTF importer/exporter, BMesh and bundled NumPy. The supplied macOS guard enables headless startup. All orthographic previews use Cycles CPU at 512 × 512.

```sh
modular='/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular'
blender="$modular/B/Blender.app/Contents/MacOS/Blender"
TMPDIR="$PWD" BLENDER_USER_RESOURCES="$PWD/.blender" \
  DYLD_INSERT_LIBRARIES="$modular/guard.dylib" "$blender" \
  -b -noaudio --factory-startup --disable-autoexec --python-exit-code 1 \
  --python build_desk.py
node -e 'const v = require("../../../../node_modules/gltf-validator"); import("./validate.mjs").then(m => m.verify(v.validateBytes)).then(results => require("node:fs").writeFileSync("validation.json", JSON.stringify({validator: v.version(), results}, null, 2) + "\n")).catch(e => { console.error(e); process.exitCode = 1; })'
```

`build_desk.py` updates the desk GLB, its three reimported renders, its manifest entry and the contact sheet. Use `--python build.py -- --sheet-only` to refresh the sheet from the existing manifest and renders.

## Geometry and finishes

- The script removes loose elements and duplicate or degenerate geometry, checks for fully enclosed disconnected shells, welds UV seams, recalculates normals, and uses planar and collapse decimation. Meshes that were closed after welding stay closed through export. The planter and rack inherit non-manifold leaf or joint topology. The source counter, planter, rack, shelf, directory sign and table have open borders, recorded in the manifest. The previews show surface appearance under static scene lighting. The rack's split left hanger was repaired with its intact centre counterpart from the same source mesh, fitted to the original left hanger's bounds.
- Area-weighted k-means starts from bilinear albedo samples at face centres. Related clusters map to the fixture palette. Local material boundaries keep baked shadows from turning part of a board, leg or brass band into a different finish. The artwork's ochre is a matte pigment. Planter foliage uses two plant greens.
- Floor props sit on the floor at the horizontal centre of their bounds. The artwork starts at the centre of its back plane. The pendant hangs below its ceiling attachment. Extra pendant height is placed in the suspension so the diffuser remains round. The floor lamp arc is set diagonally inside its square footprint to keep the base and shade close to round.
- Texture removal trades wood grain and fabric weave for flat colour. The framed motif stays recognizable with angular boundaries. The planter still shows faceted and partly uneven Monstera leaf edges inherited from the source, with the round vessel and brass band retained. The directory sign has the five flat inserts shown in the reference, with slight waviness remaining along the gold frame and at its base.
- The service desk uses a low-poly reconstruction of the source's U-shaped plan and finish bands. It retains a slightly overhanging green top, 48 oak slats separated by shallow modeled grooves, a recessed brass plinth, and cream returns and worktop. The desk measures 1.60 × 1.05 × 0.70 m with its curved front facing glTF +Z. The three-quarter camera is raised to reveal the lower worktop. Independent review confirmed the silhouette, groove rhythm and all four finishes in the export renders. The top tips are more angular than the reference and the flat oak and brass lose their grain.

## Validation

`validate.mjs` checks the GLB container, hashes, palette, primitive and triangle budgets, root identity and extras, and the three PNG captures. It executes the unmodified v11 loader and its bundled Three.js in Node with a disk-backed fetch. It measures the loaded POSITION data independently from the glTF accessor bounds, checks the pivot rules and verifies closure for meshes from watertight sources. To pass a manifest entry to that loader, provide its `id` as `definition.asset_id`. The JSON receipt records the validator and loader results for the exact exported hashes.

All 12 GLBs passed Khronos glTF Validator 2.0.0-dev.3.10 with zero errors and zero warnings and loaded through the unmodified v11 loader in Node. They loaded with two to five primitives each. The maximum dimension difference measured by the loader was below 0.001 mm. The desk has 1,798 triangles, 68,508 bytes and four primitives. The loaded desk mesh has zero boundary, non-manifold or winding edges.
