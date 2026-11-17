# Ice Cream Chest Freezer

Original P1 **Retail** asset: a low commercial display freezer with warm ivory enamel, deep teal trim, two staggered blank glass sliding panels, a recessed unlabelled control, ventilation and six generic frozen tubs. No brands, text, textures or external assets. Draft for owner review.

The requested upright beverage-cooler branch has a close existing match, `chiller-cabinet`. Its actual GLB measures 0.900 × 0.750 × 1.900 m in width/depth/height. The existing `freezer-cabinet` is a smaller utility chest with a hinged opaque lid and empty baskets. It does not supply the specified sliding panels or ice-cream tubs, so this asset implements the task's explicit fallback. Evidence and candidate hashes: `reports/existing-model-search.json`.

## Placement and motion contract

One unit is one metre. Blender uses +Z up/front -Y; GLB uses +Y up/front +Z. Root `ASSET_IceCreamChestFreezer` is at the floor centre. Actual GLB width/depth/height is **1.500 × 0.761 × 0.900 m**, including the slightly projecting front ventilation. Cabinet design envelope is 1.500 × 0.750 × 0.900 m.

The GLB preserves four placement nodes: `Cabinet_Geometry`, `Contents_Geometry`, `Lid_Left_Geometry` and `Lid_Right_Geometry`. The source retains individual manufacturing parts. The left lid is partly open to expose the tubs. Both lids translate along local X from their `closed_x_m` to `open_x_m` extras (−0.345 ↔ +0.345 m); separate tracks provide about **3 mm** vertical clearance including handles. Lid sweep stays above the contents and within the cabinet aperture. Validation samples eleven positions per lid and checks bounding-box clearance; it is not a continuous triangle-intersection analysis.

There are no clips, colliders or gallery lid controls. The consuming game must implement interaction. This delivery is a static display prop, not operational refrigeration.

## Measured export

**10,764 triangles; 450,008 GLB bytes; four placement meshes; 17 material primitives; 11 shared materials; zero textures and zero animation clips.** One translucent single-sided material is used for the glass. The fixed budget is 20,000 triangles, 1 MiB, 20 primitives and 11 materials. Khronos validation reports zero errors and warnings; independent geometry checks find zero degenerate triangles. Final hashes and measurements are in `reports/assets.json` and `reports/sources.json`.

## Reproduce

From repository root with Blender 5.2.3 LTS:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 4 --python-exit-code 1 --python models/ice-cream-chest-freezer/generate.py
# Re-export saved edits without rebuilding the original geometry:
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 4 --python-exit-code 1 --python models/ice-cream-chest-freezer/generate.py -- --export-source --skip-render
# Lightweight gallery thumbnail on macOS:
sips -s format jpeg -s formatOptions 82 models/ice-cream-chest-freezer/previews/hero.png --out models/ice-cream-chest-freezer/previews/hero.jpg
node models/ice-cream-chest-freezer/validate.mjs
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 2 --python-exit-code 1 --python models/ice-cream-chest-freezer/inspect_sources.py
node --input-type=module -e 'import fs from "node:fs";import {spawnSync} from "node:child_process";const p="models/ice-cream-chest-freezer/";const s=JSON.parse(fs.readFileSync(p+"reports/sources.json"));process.exit(spawnSync(process.execPath,[p+"validate.mjs",s.edited_glb],{stdio:"inherit"}).status??1);'
npm test
npm run build
node models/ice-cream-chest-freezer/verify_browser.mjs
```

Source QA reopens the native `.blend`, checks closed manifold positive-volume parts, edits a mesh/material and lid position, saves/reopens a temporary copy and exports it. Canonical source and GLB hashes remain unchanged. The canonical GLB is also independently imported into a clean Blender scene and rendered (`previews/reimport.png`). Four source studio views and the actual built-gallery view support visual inspection. Camera, lights and studio floor are excluded from GLB.

The initial geometry check found 64 degenerate triangles in thin bevelled recess parts. Limiting bevel radius to 22% of the smallest dimension removed the collapse; final independent validation passed. A fresh source export preserves the delivery GLB hash. `reports/browser.json` records exact consumed hash, rendered counts and keyboard orbit/zoom/reset plus refresh/reopen at desktop, tablet and mobile viewport sizes. Physical Android/iOS, WebKit, full-mall integration and sustained device performance remain unverified. No deployment or push. Rights: `LICENSE.md`.
