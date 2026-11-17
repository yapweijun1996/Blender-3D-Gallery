# Ice Cream Chest Freezer

Original P1 **Retail** asset: a low commercial display freezer with warm ivory enamel, deep teal trim, two staggered blank glass sliding panels, a recessed unlabelled control, ventilation and six generic ice-cream tubs. No brands, readable text, textures or external assets. Draft for owner review.

The original `MallQueue/tasks/glass-door-beverage-cooler.md` explicitly names this sliding-lid chest as its fallback when an upright cooler already exists. `chiller-cabinet` supplies that upright form; `freezer-cabinet` is a hinged opaque utility chest without the requested sliding panels or ice-cream tubs. Candidate evidence: `reports/existing-model-search.json`.

## Advisor round 1

The six cream surfaces now have soft billows, a rounded scoop depression and slightly irregular filled edges, with a different orientation per flavor. Their approximately 44 mm peak-to-trough relief replaces the nearly flat disks. Taller tubs retain their original base positions; the left lid is further open so the exposed pair is easier to identify from the default gallery camera. The cabinet palette is preserved through linear vertex colors on one shared opaque material; glazing uses the second, single-sided translucent material. Thin bevels and glass edges are simplified to meet the original P1 budget.

The requested `MallQueue/tasks/ice-cream-chest-freezer.md` is absent. Budget provenance was recovered from the original beverage-cooler task and its explicit fallback: **at most 8,000 triangles, 2 materials and 6 draw calls**, with a hidden unmaterialed collider. These P1 limits override the old README's incorrect 20,000-triangle / 11-material allowances. The retained **1 MiB** local file cap is stricter than the original common **1.5 MiB** limit. `reports/advisor-round-1.json` records the original task hash and measurements.

## Placement and motion contract

One unit is one metre. Blender uses +Z up/front -Y; GLB uses +Y up/front +Z. Root `ASSET_IceCreamChestFreezer` is at the floor centre. Visible GLB width/depth/height is **1.500 × 0.761 × 0.900 m**, including the slightly projecting front ventilation. Cabinet design envelope is 1.500 × 0.750 × 0.900 m.

The default scene preserves four placement nodes: `Cabinet_Geometry`, `Contents_Geometry`, `Lid_Left_Geometry` and `Lid_Right_Geometry`. The source retains 50 individual visual mesh parts. Both lids translate along local X using `closed_x_m` and `open_x_m` extras (−0.345 ↔ +0.345 m). Separate tracks leave about **3 mm** vertical clearance including handles; the cream surfaces clear the lower lid by at least **80 mm**. Validation samples eleven positions per lid and checks bounding-box clearance; it is not a continuous triangle-intersection analysis.

`collider_box` is a closed 12-triangle box with no material. It is hidden in the native source and stored in the GLB's separate, opt-in `COLLISION_ONLY_NotVisible` scene. The root extras identify that scene and node. A consumer must deliberately load it for collision; the gallery renders only the default visual scene.

There are no clips or gallery lid controls. The consuming game must implement lid interaction and collision behavior. This is a static display prop, not operational refrigeration.

## Measured export

**7,784 stored triangles (7,772 visible + 12 collision); 307,348 GLB bytes; four visual placement meshes plus one collision mesh; six visible material primitives/draw calls; two shared materials; zero textures and zero animation clips.** Khronos reports **0 errors, 0 warnings, 0 infos**. Independent visible-geometry checks find zero degenerate triangles. Final measurements and hashes are in `reports/assets.json`, `reports/khronos.json` and `reports/sources.json`.

The catalog already points to the same GLB, thumbnail and metadata. Its displayed triangle/material/file counts are derived from the GLB during the build, so no static catalog edit is needed.

## Reproduce

From repository root with Blender 5.2.3 LTS:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 4 --python-exit-code 1 --python models/ice-cream-chest-freezer/generate.py
# Re-export saved edits without rebuilding the original geometry:
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 4 --python-exit-code 1 --python models/ice-cream-chest-freezer/generate.py -- --export-source --skip-render
sips -s format jpeg -s formatOptions 82 models/ice-cream-chest-freezer/previews/hero.png --out models/ice-cream-chest-freezer/previews/hero.jpg
node models/ice-cream-chest-freezer/validate.mjs
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 2 --python-exit-code 1 --python models/ice-cream-chest-freezer/verify_rebuild.py
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec --threads 2 --python-exit-code 1 --python models/ice-cream-chest-freezer/inspect_sources.py
node --input-type=module -e 'import fs from "node:fs";import {spawnSync} from "node:child_process";const p="models/ice-cream-chest-freezer/";const s=JSON.parse(fs.readFileSync(p+"reports/sources.json"));process.exit(spawnSync(process.execPath,[p+"validate.mjs",s.edited_glb],{stdio:"inherit"}).status??1);'
npm test
npm run build
node models/ice-cream-chest-freezer/verify_browser.mjs
```

`verify_rebuild.py` compares an independent fresh procedural generation and an export of the saved native source against the exact delivered GLB bytes. This is same-version determinism, not a cross-version byte guarantee. Source QA reopens the native `.blend`, checks manifold positive-volume visual parts and the hidden collider, measures cream relief, then saves/reopens an edited temporary copy and exports it. Canonical source and GLB hashes remain unchanged. The canonical GLB is independently imported into Blender and rendered (`previews/reimport.png`). Cameras, lights and studio floor are excluded from GLB.

`reports/browser.json` records the exact consumed GLB hash, rendered counts and keyboard orbit/zoom/reset plus refresh/reopen at desktop, tablet and mobile viewport sizes. The screenshot command replaces `~/Documents/MallQueue/reports/ice-cream-chest-freezer-page.png` at 1440 × 900 and captures all three viewport sizes. Current checks are in `reports/checks.json`; `generate.log`, `validation.log` and `browser-prior-build.json` retain the original build history.

Physical Android/iOS, WebKit, full-mall integration and sustained device performance remain unverified. No deployment or push.

Original asset; reuse in the owner's projects is authorized. See `LICENSE.md` for the remaining redistribution limitation.
