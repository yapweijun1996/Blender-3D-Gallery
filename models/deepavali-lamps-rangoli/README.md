# Deepavali Lamps & Rangoli

Original P3 mall decoration in the existing Festivals & Local Life category.
Twelve hollow clay diyas with wicks and wide ivory-and-gold teardrop flames
stand on a 2.4 m round, 8 mm thick rangoli mosaic above an included 2 x 2 m floor.
The original geometric twelve-petal tessellation uses three plain colours.
Two hanging U-shaped garlands have 21 marigold heads each, with three staggered
scalloped petal tiers and varied orientation. Four fixing loops interlock with
a supplied crossbar carried by two posts and feet. No host ceiling is needed.

Metres; origin at floor centre; Blender +Z up / -Y front, exported glTF +Y up /
+Z front. The editable source retains each lamp and garland as a named group.
Export merges geometry into three shared opaque material primitives. No
external geometry, images, fonts, textures, brands, text or religious figures.
Flames are static geometry without light sources or animation. The square floor
spans X/Z [-1, 1] in glTF, from Y=0 to 0.012 m; the mosaic rests at Y=0.012 to
0.020 m and intentionally overhangs the square edges. All twelve lamps rest on
the mosaic inside the square footprint. Support feet rest on the square floor.
Place the origin on the host's level ground plane at Y=0.

Advisor round 1 measurements: 19,640 triangles; 464,324 GLB bytes (453.4 KiB);
14,221 exported vertices; three materials, meshes and measured browser draw
calls; overall 2.400 x 1.988 x 2.400 m (glTF X/Y/Z). The measured lamp-and-flame
footprint is 1.8924 x 1.8924 m. No textures, animations or degenerate triangles.
Khronos: zero errors and zero warnings. `reports/assets.json` records the exact
bounds and hash. The `lamps.png` preview provides a close view of all twelve flames.

From the repository root:

```sh
/opt/homebrew/bin/blender --background --python models/deepavali-lamps-rangoli/generate.py
node models/deepavali-lamps-rangoli/validate.mjs
/opt/homebrew/bin/blender --background --python models/deepavali-lamps-rangoli/inspect_sources.py
node models/deepavali-lamps-rangoli/validate.mjs models/deepavali-lamps-rangoli/reports/edited.glb
npm run validate:assets
npm test
npm run build
node models/deepavali-lamps-rangoli/browser-check.mjs
```

The generator also accepts `-- --export-source --skip-render` to export the
saved source without rebuilding geometry, or `-- --skip-render` for a fresh
procedural build without previews. Two fresh builds produce identical GLB bytes;
the saved source also re-exports identically. Local gate evidence is in `reports/`.
The overall status remains NEEDS REVIEW pending owner review; this is not a
deployed asset or a certification of real flame safety, suspension hardware,
physical devices or full-mall frame rates.

Existing `deepavali-oil-lamp`, `deepavali-kolam-floor-pattern` and
`deepavali-festive-arch` provide related individual props. None supplies this
complete lamp count, round mosaic size, three-material budget and double-garland
arrangement. This asset is newly authored; no existing model was copied or edited.
