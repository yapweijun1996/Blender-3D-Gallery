# Shophouse Retractable Fabric Awning

An original shophouse-inspired shop-front canopy module. Two rigid links on each side fold around joints. Dark sea-green and straw fabric, with a narrow rust accent and sewn scalloped valance, stays the same width as the header moves toward its cassette. An exposed roller moves with the apparent cloth take-up, while wall mounts and shoulders stay fixed. The decorative facade is a generic display sample, not a documented building, installed equipment or a marked place.

The only native GLB animation, `AWNING_FOLD_IN`, shows one 2.4-second retraction. The canvas initially displays the extended pose, holds the parked pose after playback and restores extended on reset. The Gallery's reduced-motion path presents the same parked result immediately. This is a fictional demonstration without installation, load, weather, electrical or safety claims. It is not an engineering plan or operating guide.

## Reproduce and validate

- Blender 5.3.0: `blender -b --factory-startup --python-exit-code 31 --python generate.py -- --output .`. Add `--review <dir>` for genuine extended, midway and parked stills, or `--skip-render` for the source and GLB only. Clean regeneration on the same Blender version produced identical GLB bytes.
- Authored arm articulation, cloth span, roller and exact GLB readback: `blender -b --factory-startup shophouse-retractable-fabric-awning.blend --python-exit-code 31 --python verify_blender.py -- exports/shophouse-retractable-fabric-awning.glb`.
- From the Gallery root: `node models/shophouse-retractable-fabric-awning/verify.mjs` checks Khronos validation, exact clip channels and SHA-256 digests.

Aesthetic model-scale metres, Blender +Z up and −Y outward; GLB +Y up and +Z outward. Native mesh assets and the render are original, with no external images, logos, materials or geometry. Redistribution terms for public downloads are not specified.
