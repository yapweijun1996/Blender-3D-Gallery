# Restaurant Table and Four Chairs

Original four-seat dining furniture for the planned GJH mall restaurant mini-game. Existing category: **Mall Fixtures**. Draft asset for owner review; no publication or mini-game implementation is claimed.

The square table measures 0.800 × 0.800 × 0.750 m. Four simple chairs face inward with 0.450 m seat tops, rounded sand laminate seats and backs, satin graphite frames and small feet. The blank table-number stand and shallow condiment tray sit on the tabletop; two plain ceramic shakers and a generic squeeze bottle carry no readable text, logos or packaging. All geometry and materials are original procedural work; no downloaded assets, textures, fonts or scripts.

The complete GLB measures approximately 1.899 × 0.899 × 1.899 m (glTF X/Y/Z). It contains **11,268 rendered triangles, 597,308 bytes, seven placement meshes, 15 material primitives/draw calls and three shared opaque materials**. These figures are measured from the exported delivery; complete scene performance depends on the consumer.

## Placement contract

One unit equals one metre. Root `ASSET_RestaurantTableChairSet` is at floor centre; glTF +Y is up and front is +Z. Blender uses +Z up/front -Y. Seven direct placement nodes are available in one GLB:

| Node | Pivot and purpose |
| --- | --- |
| `Table_Geometry` | Table floor centre |
| `Chair_North_Geometry` | Chair floor centre, initially +Z of the table |
| `Chair_East_Geometry` | Chair floor centre, initially +X |
| `Chair_South_Geometry` | Chair floor centre, initially -Z |
| `Chair_West_Geometry` | Chair floor centre, initially -X |
| `TableNumberStand_Geometry` | Stand base centre at tabletop height |
| `CondimentTray_Geometry` | Tray base centre at tabletop height |

Assign position/rotation on each named chair to arrange it independently; remove it from this root or use `Object3D.attach` to reparent while preserving its world transform. Each placement mesh can contain multiple material primitives, which Three.js loads as a group. The source retains 93 individually editable mesh parts. Export merges evaluated copies per placement node, preserving the source. There are no animation clips, physics colliders or game interactions; the consumer supplies them.

## Rebuild and verify

From repository root, using Blender 5.2.3 LTS:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/restaurant-table-chair-set/generate.py
# Re-export saved edits without regenerating original geometry:
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/restaurant-table-chair-set/generate.py -- --export-source --skip-render
node models/restaurant-table-chair-set/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/restaurant-table-chair-set/inspect_sources.py
node --input-type=module -e 'import fs from "node:fs"; import {spawnSync} from "node:child_process"; const p="models/restaurant-table-chair-set/"; const r=JSON.parse(fs.readFileSync(p+"reports/sources.json")); process.exit(spawnSync(process.execPath,[p+"validate.mjs",r.edited_glb],{stdio:"inherit"}).status??1);'
npm run validate:assets
npm test
npm run build
node models/restaurant-table-chair-set/verify_browser.mjs
```

The deterministic generator has no random or network inputs. Two original rebuilds produced identical GLB hashes (`reports/determinism.json`). Real EEVEE renders are `hero.png`, `front.png`, `side.png` and `3q.png`, all visually inspected. The studio floor/lights/camera are excluded from export. Source-edit verification saves and reopens a temporary copy, narrows the blank card and changes its material, then independently validates the changed export while preserving the delivery.

`reports/assets.json` measures GLB bounds, format, finite normals, triangle degeneracy, material budgets, independent chair transforms, floor contacts and table/accessory clearance. These are component and bounding-box checks, not a complete intersection or physical safety analysis. `reports/browser.json` records actual built-gallery loading, GLB hash, draw calls, triangles, keyboard orbit/zoom/reset, refresh and reopening at 1440×900. Screenshot: `~/Documents/MallQueue/reports/restaurant-table-chair-set-page.png`.

## Existing assets reviewed

Search covered all catalog and metadata IDs, names and tags; results are in `reports/existing-model-search.json`. `dining-table` is a 1.40 × 0.80 m rectangular table; `round-dining-table` is a 1.00 m diameter pedestal table; `plastic-dining-chair` is an individual red plastic chair; `restaurant-booth` is fixed upholstered bench seating. None supplies the requested four-seat square set with independent chairs, blank number stand and condiment tray. Built as a distinct original asset under the owner's explicit override. No existing models were edited. Nothing was skipped.

Physical Android/iOS, WebKit, full-mall integration, mini-game operation and sustained performance are unverified. Public redistribution terms are unspecified; owner-project reuse is authorized.
