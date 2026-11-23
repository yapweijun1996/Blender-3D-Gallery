# Wau Bulan Workshop Display

An original, static interpretation of a Malaysian crescent-tail kite. The front uses invented floral cut-paper ornament, while the rear shows the continuous bowed wing spar, vertical bamboo spine, separate crescent spar and lashings. The paired cotton bridle converges on the front; the generic bamboo cradle and loose spool are a display context, not part of the kite.

The [JKKN cultural register](https://pemetaanbudaya.jkkn.gov.my/en/senibudaya/detail/696) describes Wau Bulan in Kelantan and describes bamboo, paper, string and layered floral ornament in wau making. [Bank Negara Malaysia](https://www.bnm.gov.my/web/bnm-bank-notes/rm1-traditional-sport) describes the bamboo-and-paper Moon Kite and its decorative use. These are references for the cultural type only. The geometry and ornamental design are original, not copied from either reference or a banknote. This is neither a traditional-maker attribution nor a flight, instructional or certification claim.

## Reproduce and validate

- Blender 5.3.0: `blender -b --factory-startup --python-exit-code 31 --python generate.py -- --output .`. Add `--review <directory>` for native front and rear detail stills, or `--skip-render` for the model only. A clean repeat on the same native Blender version reproduced the exact GLB bytes.
- Blender physics-free shape and native/re-import check: `blender -b --factory-startup wau-bulan-workshop-display.blend --python-exit-code 31 --python verify_blender.py -- exports/wau-bulan-workshop-display.glb`.
- Khronos validator/size/required Blender part names and digest gate (requires the repository npm dependencies): `node models/wau-bulan-workshop-display/verify.mjs` from the repository root.

Dimensions are design scale in metres; Blender +Z up, −Y out, and glTF +Y up, +Z out. The GLB is self-contained with no images or animation. Its 512×512 studio poster is rendered directly from the same Blender asset. The studio, lights and camera are excluded from the GLB.

Original project asset; redistribution terms for public downloads are not specified.
