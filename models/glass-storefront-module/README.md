# Glass Storefront Module

Original P1 asset for all GJH mall shops. **3.0 m wide × 3.6 m high**, 0.12 m deep; repeat at 3.0 m along X. P1 owner override supersedes the later 4.0 × 3.2 m dimensions. The entire GLB, including both variants and collision geometry, is below 8,000 triangles. Category: existing **Mall Fixtures**. Local review evidence is in `reports/`; publication is not claimed.

Original asset; reuse in the owner's projects is authorized.

No external assets, downloaded scripts, textures, brands, logos or readable asset text. All geometry and materials are generated procedurally. No random inputs or generation-time network access. `docs/references/gjh-mall-concept-board.png` was **NOT FOUND** in this checkout; warm pale aqua glazing, soft edges and neutral satin metal follow the written brief.

## Packaged variants

`exports/optimized.glb` contains four named core glTF scenes:

| Scene index | Name | Purpose |
| --- | --- | --- |
| 0 (default) | Closed | Two fixed glass panes, two frameless glass door leaves, four patch fittings, front/rear stainless pull handles, blank sign band and slim floor channels |
| 1 | Open | Same module without the door pair; a measured 1.0 m × 2.72 m unobstructed opening and flush floor |
| 2 | COLLISION_ONLY_Closed | Hidden, material-free `collider_box` |
| 3 | COLLISION_ONLY_Open | Hidden, material-free `collider_box_Open`; three box volumes preserve the opening |

The unchanged gallery displays scene 0. A consuming Three.js app can choose `gltf.scenes[1]` for Open; use one visual variant per placement. Variant root extras identify the matching collision scene. Core glTF has no visibility flag: collision scenes are opt-in and are absent from both visual scenes. They never render in the stock gallery. Do not add all four scenes together.

Both visual roots are at floor centre, X=0/Y=0/Z=0 in glTF; +Y up, front +Z; 1 unit = 1 metre. Blender authoring uses +Z up/front -Y and native Y-up glTF conversion. Repeat end planes at X ±1.5 m, with no vertical jamb or protruding end cap. A 0.22 m high blank header and 26 mm high side channels stay inside the module envelope. No threshold crosses the Open passage.

Each variant exports two merged visual meshes: all glass and all metal. They share exactly two materials across both scenes. Glass uses single-sided alpha BLEND, no transmission, refraction, images or custom shader. Neutral metal is directly tintable; the blank header uses the same material. Source objects preserve independently named panes, fittings, handles and header. Merged export extras list their source parts. Doors are static; no interaction or animation is claimed.

## Rebuild and check

From the repository root:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/glass-storefront-module/generate.py
# Preserve manual edits in the saved source:
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/glass-storefront-module/generate.py -- --export-source --skip-render
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/glass-storefront-module/inspect_sources.py -- --source-edit
node models/glass-storefront-module/validate.mjs --source-edit
npm run validate:assets
npm test
npm run build
node models/glass-storefront-module/verify_browser.mjs
```

Blender 5.2.3 LTS. `hero.png`, `front.png`, `side.png`, `3q.png` and corresponding `open-*` images are real Blender renders. Contact sheets at 1440/390 px render both actual GLB scenes in Chromium; the QA grid is not exported. `hero.jpg` is the gallery thumbnail derived locally from the hero render using `sips`.

The source-edit proof changes a temporary saved copy under `/tmp/` and leaves delivery untouched. Asset checks independently load glTF, measure scale, bounds, triangles, material/scene contracts, nondegeneracy, opening rays, collider clearance and tile seams. Browser evidence records the loaded GLB hash, draw calls, keyboard orbit/zoom/reset, overflow and console errors. Physical devices, WebKit, full-mall integration and sustained performance remain unverified. No structural or safety certification.

## Existing models checked

`mall-entrance` is an 8 m vestibule/canopy with framed sliding doors. `mall-shopfront-door` is a 2.10 × 2.40 m framed double-door module. `hdb-neighbourhood-shopfront` includes piers, a canopy and a framed single entrance. `mall-fit-finishes` provides fascia strips, and `mall-glass-partition` is a framed 1.20 × 2.40 m partition. None provides this frameless 3.0 × 3.6 m module with paired doors and a matching Open scene. All existing model sources and exports are unchanged.
