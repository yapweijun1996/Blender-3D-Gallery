# Skylight Roof Module

Original procedural glass-and-steel atrium roof tile. Category: existing **Shopping Mall**. No brands, lettering, downloaded geometry, textures, fonts or other external assets.

The measured GLB footprint is 4 × 4 m and height is 0.224 m. Origin is at the floor centre of the frame underside, with glTF +Y up and +Z front (native Blender +Z up, -Y front). For an overhead roof, translate the root to the desired underside elevation. Supports, walls and perimeter building flashing are separate scene responsibilities.

Sixteen 12 mm glass panes sit on graphite seals below satin steel pressure caps. Native parts remain separate editable meshes; export joins by material into three meshes and three primitives. Pale aqua glazing uses alpha BLEND 0.30 with double-sided faces; it is a lightweight visual approximation, without transmission, refraction, textures or a decoder dependency. Transparent surfaces can require extra renderer passes; three primitives are not a guarantee of three total draw calls in every engine.

Place roots at exact 4 m multiples in glTF X/Z without scaling. Opposite edges contain clipped half members and half fixings; adjacent copies meet to form complete members. Do not add another full beam on a shared boundary. Named connectors mark the four repeat planes. A 3 × 3 actual-export check verifies all twelve seams, matching boundary vertex profiles and absence of positive-volume overlap between tiles. No rotation is needed for tiling; alternating quarter-turn assemblies are not verified.

Rebuild from the repository root with Blender 5.2.3 and installed project dependencies:

```sh
/opt/homebrew/bin/blender --background --python models/skylight-roof-module/generate.py
python3 models/skylight-roof-module/prepare_previews.py
/opt/homebrew/bin/blender --background --python models/skylight-roof-module/inspect_sources.py
node models/skylight-roof-module/validate.mjs
npm run validate:assets
npm test
npm run build
node models/skylight-roof-module/check_browser.mjs
```

The generator supports `-- --skip-render` and `-- --export-source --skip-render`. The latter exports saved manual source edits; the default rebuild replaces the source. Previews are original Blender renders; the studio floor, camera and lights are excluded from the GLB. PNGs can be converted to gallery WebP using Pillow (`quality=88`, `method=6`). Reports contain measured geometry, hashes, source inspection, Khronos output and local check results.

Overall status remains **NEEDS REVIEW** for manager acceptance. This is a visual mall asset; load capacity, drainage, weatherproofing, building compliance, physical devices and complete-mall performance were not verified. No publication or push is included.
