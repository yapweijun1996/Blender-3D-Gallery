# Fashion Clothing Rack and Folded Display

Original static boutique fixture in metres. Blender +Z up / -Y front exports as glTF +Y up / +Z front. The combined footprint is centred on the floor origin. The native source preserves individually named garments, hangers, rack and table parts; the web GLB batches them into three shared opaque material meshes. Plain fabric colours use vertex colour, without image dependencies.

Rebuild in Blender 5.2.3:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/fashion-clothing-rack/generate.py
node models/fashion-clothing-rack/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/fashion-clothing-rack/inspect_clearance.py
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/fashion-clothing-rack/inspect_sources.py
node models/fashion-clothing-rack/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/fashion-clothing-rack/check_browser.mjs
```

Append `-- --export-source --skip-render` to export saved edits without regenerating; omit `--skip-render` to update the four previews. `--view hero` renders a single preview. The generator uses no random geometry or external inputs. Studio objects are excluded from the export. Source edit checks use a temporary directory.

Advisor round 1: inward sleeves fall closer to the torso with narrower sections and matching cuffs, keeping all ten garments and their original rail/hanger connections. The saved-source clearance gate checks all 45 garment pairs, including hangers, for triangle surface intersections. Adjacent inner sleeves and cuffs have a conservative separating-plane gap of at least 13.17 mm. Contacts within each garment and between hooks and the rail are intentional and excluded. Append `-- --export-source --clearance-views` to reproduce the 640px top and three close orbit views in `reports/clearance-*.png`; add `--view clearance` to render only these diagnostic views.

Measured export: 19,268 triangles, 12,584 vertices, 542,348 bytes, three meshes/primitives and three shared materials; no images or animation. Combined glTF dimensions remain 2.768633 × 1.600000 × 1.079701 m (width × height × depth), with the origin at floor centre. The table fixture remains 1.2 × 0.6 × 0.8 m. Geometry counts, byte size and dimensions are unchanged by this revision, so the catalog entry requires no change.

Seven shirts, two jackets and one dress hang on ten radial hangers; the table has three stacks of folded shirts. These are static visual props, without cloth physics, collisions or store interaction. Similar existing assets are documented in `reports/duplicate-search.json`; no existing models were changed. See measured reports and metadata for budgets and coverage. Physical devices and complete mall performance are unverified. Owner-project reuse is authorized; public redistribution terms remain unspecified.
