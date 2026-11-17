# Peanut-Butter Jar Display Stand

Original S08 (P2) static merchandising prop in the existing Mall Fixtures category. A warm ivory floor pedestal carries a tapered three-tier arrangement of 24 short jars (14 / 8 / 2), plain terracotta lids, blank cream label bands and a blank sign card. All geometry and materials are original procedural work; no external assets, fonts, logos or packaging.

Measured GLB envelope: **0.800 × 0.500 × 1.020 m** (width × depth × height). Each source jar is **0.104 m diameter × 0.120 m high**. Floor-centred root; Blender +Z up / -Y front exports to glTF +Y up / +Z front. Source retains 63 independently editable meshes; delivery batches them into three opaque, single-sided material primitives. No textures, animation or decoder extensions. The 16,404-triangle, 514,704-byte GLB stays within this task's budgets. Three primitives describe this model's base rendering cost; they do not establish a whole-mall draw-call measurement.

From the repository root:

```sh
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/peanut-butter-jar-stand/generate.py
node models/peanut-butter-jar-stand/validate.mjs
/opt/homebrew/bin/blender --background --python-exit-code 1 --python models/peanut-butter-jar-stand/inspect_sources.py
node models/peanut-butter-jar-stand/verify_source_edit.mjs
npm run validate:assets
npm test
npm run build
node models/peanut-butter-jar-stand/browser-check.mjs
```

Append `-- --skip-render` to omit previews. Append `-- --export-source --skip-render` to export saved edits without rebuilding. The default rebuild replaces the generated source; preserve manual edits separately. Previews render the exported GLB after reimport. `inspect_sources.py` reopens the source, verifies manifold meshes, jar counts/dimensions, tier support and spacing, then saves and re-exports a separate edited copy. Source-edit verification checks the delivered cabinet width change and lid material edit.

`reports/` contains format, geometry, source, reproducibility, visual and Chromium evidence. The requested page screenshot and manager report live in `~/Documents/MallQueue/reports/`. Metadata remains `draft` / `NEEDS REVIEW`: local checks do not establish physical Android/iOS, WebKit, structural stability, collisions, per-jar interaction or integration in the complete 17-shop mall.

Existing `condiment-bottle-jar-set`, `stacked-can-pyramid` and `abalone-gift-box-display` are similar merchandising assets with different objects/features. No exact match was found; this is a distinct owner-requested asset, appended as its own collection. No gallery UI changes.
