# Deepavali Lamps & Rangoli

Original P3 mall decoration in the existing Festivals & Local Life category.
Twelve hollow clay diyas with cotton wicks and static two-colour flame meshes
occupy a 2 x 2 m placement area on a 2.4 m round, 8 mm thick rangoli mosaic.
The original geometric twelve-petal tessellation uses three plain colours.
Two hanging U-shaped garlands have 25 ruffled marigold heads each and four
small fixing loops. Ceiling supports are intentionally not included.

Metres; origin at floor centre; Blender +Z up / -Y front, exported glTF +Y up /
+Z front. The editable source retains each lamp and garland as a named group.
Export merges geometry into three shared opaque material primitives. No
external geometry, images, fonts, textures, brands, text or religious figures.
Flames are static geometry without light sources or animation. The lamp area
is a placement envelope; the only supplied floor is the larger round mosaic.

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
saved source without rebuilding geometry. Local gate evidence is in `reports/`.
The overall status remains NEEDS REVIEW pending owner review; this is not a
deployed asset or a certification of real flame safety, suspension hardware,
physical devices or full-mall frame rates.

Existing `deepavali-oil-lamp`, `deepavali-kolam-floor-pattern` and
`deepavali-festive-arch` provide related individual props. None supplies this
complete lamp count, round mosaic size, three-material budget and double-garland
arrangement. This asset is newly authored; no existing model was copied or edited.
