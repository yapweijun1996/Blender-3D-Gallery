# Fashion Clothing Rack and Folded Display

Original static boutique fixture in metres. Blender +Z up / -Y front exports as glTF +Y up / +Z front. The combined footprint is centred on the floor origin. The native source preserves individually named garments, hangers, rack and table parts; the web GLB batches them into three shared opaque material meshes. Plain fabric colours use vertex colour, without image dependencies.

Rebuild in Blender 5.2.3:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/fashion-clothing-rack/generate.py
node models/fashion-clothing-rack/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/fashion-clothing-rack/inspect_sources.py
node models/fashion-clothing-rack/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/fashion-clothing-rack/check_browser.mjs
```

Append `-- --export-source --skip-render` to export saved edits without regenerating; omit `--skip-render` to update the four previews. `--view hero` renders a single preview. The generator uses no random geometry or external inputs. Studio objects are excluded from the export. Source edit checks use a temporary directory.

Seven shirts, two jackets and one dress hang on ten radial hangers; the table has three stacks of folded shirts. These are static visual props, without cloth physics, collisions or store interaction. Similar existing assets are documented in `reports/duplicate-search.json`; no existing models were changed. See measured reports and metadata for budgets and coverage. Physical devices and complete mall performance are unverified. Owner-project reuse is authorized; public redistribution terms remain unspecified.
