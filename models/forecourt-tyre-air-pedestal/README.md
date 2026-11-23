# Forecourt Tyre Air Pedestal

Original unbranded SG/MY-inspired forecourt utility prop. One continuous rubber hose is coiled into an open lower cabinet, then routed past an exterior fairlead into a small stowed air chuck. There are separate reel and nozzle collars, a recess back wall, rear maintenance cover, a raised utility pad, and a sloped AIR / ANGIN panel. The label and dial are custom geometry with no fonts, logos, numbers, units or instructions. The dial is only decorative. No functional claim, pressure recommendation, fitting specification or real operator is represented.

## Reproduce and validate

- Blender 5.3.0: `blender -b --factory-startup --python-exit-code 31 --python generate.py -- --output .`. Use `--review <directory>` for native face and hose/chuck crops, or `--skip-render` for source and GLB only. An independent clean regeneration on this Blender version produced identical GLB bytes.
- Watertight hose topology, coil spacing, collar sockets, cradle fit and native/GLB re-import: `blender -b --factory-startup forecourt-tyre-air-pedestal.blend --python-exit-code 31 --python verify_blender.py -- exports/forecourt-tyre-air-pedestal.glb`.
- Repository npm dependencies: `node models/forecourt-tyre-air-pedestal/verify.mjs` from the repository root for Khronos, geometry, parts and digests.

Dimensions are model scale only, in metres. Blender +Z up and −Y front; glTF +Y up and +Z front. No downloaded models, textures or other external assets. The 512×512 studio preview is rendered from the same source; the studio floor, camera and lights are not exported. This is an original project asset; public redistribution terms for downloads are unspecified.
