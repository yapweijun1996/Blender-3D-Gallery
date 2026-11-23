# Mall wall corner — 1.2 m arms

A static 90° L-shaped wall module matching the existing 1.2 m mall solid wall and 3 m height. Each centreline arm reaches **1.20 m from the corner intersection**; outer GLB bounds are approximately **1.26 × 3.00 × 1.26 m** in X/Y/Z because wall thickness extends around the intersection.

## Assembly contract

- Root origin is at the ground-level intersection of the two wall centrelines; Blender +Z maps to glTF +Y. Connectors are at `(-1.2, 0, 0)` and `(0, 0, 1.2)` in glTF metres.
- For a corner at the origin, put a straight `mall-solid-wall` root at `(-1.8, 0, 0)` and another at `(0, 0, 1.8)` rotated **−90° about glTF Y**. The latter rotation faces its decorative front toward the corridor at negative X. The inside faces are finished with matching panels and skirting.
- The editable Blender source has 19 mesh parts; the GLB is static. No doorway, arbitrary-angle corner, collision, load-bearing, fire, acoustic, fabrication or building compliance is supplied.
- Original owner-project geometry and materials; no external artwork. Public redistribution terms are unspecified. Gallery download is disabled.

## Local verification — 2026-11-15

- Blender 5.1.2 reopened the editable source and reimported the GLB with matching bounds: [source/reimport report](reports/source-reimport.json).
- Actual GLB: **67,864 bytes, 804 triangles**, SHA-256 `8ea702d2b4f6b42d26f5248fd4d639654207e7c87c6d3e4ff038bf21e6fbcfa1`. Khronos glTF Validator reported **0 errors / 0 warnings**. Three.js checked both centreline connectors and straight-wall bounding-box contacts, with two rays confirming finished inner faces: [corner validation](reports/corner-validation.json).
- Local Chromium Gallery loaded the exact GLB hash and rendered WebGL at 1440 × 900 and emulated 390 × 844 with no normal-flow browser errors. Viewer close removed its canvas and downloads remained hidden: [desktop](reports/gallery-desktop.png), [mobile](reports/gallery-mobile.png). The corridor preview includes the wall corner on the right-hand side.

On 2026-11-23, the two straight-to-corner interfaces were rechecked with the corrected rotation. Eight ray pairs compared the matching core reveal, panels, skirting and top trim across both joints. The maximum measured step was 0.21 μm against a 1 μm check tolerance. [Updated corner validation](reports/corner-validation.json).

These checks cover one 90° configuration, bounding boxes and sample rays; they do not establish every triangle contact, arbitrary angles, full corridor collision/navigation, target-device performance or physical Android/iOS support. The 400-item backlog's 2 m wall dimensions remain provisional and are not automatically fulfilled.

## Reproduce

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --threads 4 --python-exit-code 1 --python models/mall-wall-corner/generate.py -- --export-source
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 --python models/mall-wall-corner/inspect-sources.py
node models/mall-wall-corner/validate-corners.mjs
```

`--export-source` retains the saved source but overwrites the GLB and PNG; `--rebuild` replaces the source. Preserve manual edits first and update JPEG/metadata hashes after intentional changes.
