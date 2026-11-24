# Roadside Wheel-Lift Tow Cradle

An original, static, unbranded sectional sculpture of a recovery vehicle's rear body, a telescoping center member and two open wheel grids. A single reference tire makes the paired molded supports readable; one pocket is left bare. Two display feet and exposed front cut rail ends indicate this is only an exhibit, not a complete operational vehicle.

Regional context: [PLUS Malaysia](https://www.plus.com.my/road-safety/) describes local roadside tow services. [Allianz Malaysia's own 2022 fleet notice](https://www.allianz.com.my/personal/media-hub/5-hybrid-trucks-added-allianz-road-rangers.html) distinguishes spectacle/wheel lifts from flatbeds. The [Miller Industries primary parts catalog](https://www.millerind.com/images/uploads/parts/VULCAN_GEN_2_SERIES_10_MAR_21_WEB_PARTS.pdf) supplies generic component vocabulary (crossbar, paired wheel grids and L-arms), not reproduction dimensions, drawings, brand identity or a design specification. This original asset is not equipment, suitability advice, load guidance or a towing demonstration.

## Regeneration and checks

The editable scene uses Blender 5.3.0 and its built-in font; all meshes, lettering and finishes are original. Blender +Z is up and -Y faces the gallery camera; glTF +Y is up, +Z forward. Export has no motion, textures, studio lights or floor.

```sh
blender -b --factory-startup -P generate.py -- --output /tmp/tow-display --review /tmp/tow-display-review
blender -b --factory-startup --python-exit-code 9 -P verify_blender.py -- \
  roadside-wheel-lift-tow-cradle.blend exports/roadside-wheel-lift-tow-cradle.glb
node verify.mjs
```

Blender source, independently reimported GLB and Three GLTFLoader checks confirm the model's two near-tangent rubber contacts, open pockets, telescoping collar through-void and axle cap alignment. The measurements in the tests describe fits in this digital model only.

Original project asset; redistribution terms for public downloads are not specified.
