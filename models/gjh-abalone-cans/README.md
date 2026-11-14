# GJH Abalone Cans

Four metre-scale canned-abalone props for the owner's GJH virtual mall: New Zealand, Australia, South Africa and Mexico. The can geometry is original, deterministic Blender Python. Each wrap-around label is **unrolled from the official front and reverse GJH eShop packshots** held in the owner's `Webpage-Design-Gallery` repository (`assets/companies/gjh/official`). No logo, certification mark or text was redrawn or generated.

| Asset | Origin | Pack | Chinese type name | Triangles (LOD0 / LOD1) | GLB bytes |
| --- | --- | --- | --- | ---: | ---: |
| `gjh-can-new-zealand-abalone` | New Zealand | 425g | 新西兰鲍鱼罐头 | 4,888 / 3,044 | see `reports/assets.json` |
| `gjh-can-australia-abalone` | Australia | 425g | 澳洲鲍鱼罐头 | 4,888 / 3,044 | see `reports/assets.json` |
| `gjh-can-south-africa-abalone` | South Africa | 425g | 南非鲍鱼罐头 | 4,888 / 3,044 | see `reports/assets.json` |
| `gjh-can-mexico-abalone` | Mexico | 454g | 墨西哥鲍鱼罐头 | 4,888 / 3,044 | see `reports/assets.json` |

## Contents

- `exports/*.glb` (LOD0, shown in the gallery): self-contained glTF 2.0, one embedded JPEG label texture, floor-centre origin, front toward glTF +Z, three materials and three draw calls (`GoldRim`, `SilverMetal`, `Label`). Thin rolled seams, a recessed lid with pressed rings, opening score, ring-pull with rivet, and a recessed base.
- `exports/lod1/*-lod1.glb`: shelf-display LOD with 3,044 triangles, a 640 px texture and no hidden body, also three draw calls. Not in the gallery catalog.
- `sources/gjh-abalone-cans.blend`: editable scene with all four cans in a row (textures packed, parts as separate objects) and a non-exported `STUDIO` group.
- `textures/*-label.jpg` and `textures/lod1/`: the derived label strips (1280 and 640 px wide). `reports/build.json` records the SHA-256 of every source packshot, the chosen panel layout and seam costs, and texture sizes. `reports/qa/` holds 24-view and six-view contact sheets; `reports/golden/` the regression goldens.
- `metadata/*.json`, `previews/*.webp`, `reports/assets.json`: gallery metadata, thumbnails and measured metrics.

## Reproduce

Blender 5.2.3 LTS, from the repository root. The generator reads the packshots from the sibling `Webpage-Design-Gallery` checkout by default, or from `--packshots`:

```sh
blender --background --factory-startup --python models/gjh-abalone-cans/generate.py -- --packshots /path/to/Webpage-Design-Gallery/assets/companies/gjh/official
node models/gjh-abalone-cans/validate.mjs
npm test
npm run build && npm run test:cans   # golden-screenshot regression; add --update after reviewing intended changes
```

Thumbnails are 640 px WebP converted from the Blender PNG renders (any converter works; PNGs are not committed).

## Limits

- **Label layout.** The official eShop packshots show three faces (front, food photo, nutrition) for New Zealand, Australia and South Africa, and two for Mexico. Each is treated as a cylinder panel and used only in its reliable centre. Panel **order and spacing are estimates** chosen for the best seam match; they are not verified against a physical can or die-line. Mexico has no third face, so about 121 degrees are an **unprinted placeholder** (two flat colours); nothing is redrawn or invented. See `label_layout` in each metadata file.
- **Flat badges.** In the official packshots the Wild Caught badge (New Zealand, Australia, Mexico) is pasted on flat instead of foreshortened by the cylinder, so unrolling it normally made it about 1.4 to 1.7 times too wide when viewed face-on. A column remap inside the badge's rows restores a round badge without redrawing anything (`OVERLAY_BADGES` in `generate.py`; the plain background beside the badge is stretched slightly). Printed logos (halal, ASME, the South Africa seal) were measured and left unchanged.
- **Label boundaries.** The printed label runs from packshot row 313 to 848 (measured on all 11 photos); the scale comes from the measured body silhouette, so label artwork keeps its proportions on the mesh (texel density differs by under 0.1% between horizontal and vertical).
- **Sharpness.** The official page offers at most 1000 x 1000 px (the can is about 350 px wide), which caps detail; fine print is soft when zoomed. Resampling is bicubic with light sharpening, and the baked vertical shading is divided out so the viewer lights the model. A larger official original is picked up automatically by `--packshots`.
- **Dimensions.** Diameter is a nominal 73.5 mm and height follows the packshot aspect ratio (about 125 mm). A retailer listing (7.5 x 11 x 7.5, no unit) disagrees with the height, so real dimensions are unverified.
- **Look.** The label is a glossy lacquered print (metallic 0.2, roughness 0.3) and the viewer lighting is tuned per can (`display.previewLighting`, environment intensity 1.0) so the cylinder shows a soft highlight band and edge falloff; the result depends on the viewer's RoomEnvironment.
- **Viewer.** The can metadata opts in to the viewer's studio environment (`display.studioEnvironment`) and tuned lighting. No texture compression or runtime LOD switching is provided; Firefox, Safari and mobile devices were not tested. See [verification.md](verification.md) for the full PASS/FAIL/UNVERIFIED list.

## Codex flat-label comparison set

A second set of the same four cans, `gjh-can-<sku>-abalone-codex` (collection `gjh-abalone-cans-codex`), whose label is an **AI-generated flat artwork** made with the Codex CLI's built-in image generation from the official packshots, for side-by-side comparison with the photo-unrolled set above. It looks crisper (clean vector-like print, round logos, no photo seams) but is **not official artwork**: text, numbers, seals, QR codes and barcodes may differ from the real label. A second Codex pass corrected the text errors found in review (Mexico 454 g, GJH logo and official addresses; Australia cholesterol 150 mg; New Zealand distributor and packer lines; South Africa's invented crown and star seals removed) against the official information-face photos. Each metadata file still lists the remaining differences (for example Mexico has an invented third face, and all seals, QR codes and barcodes are redrawn and unverified).

- Flat labels: `sources/flat-labels/<slug>-flat.jpg` (1774 x 887, from the model's PNG output). Prompts demanded exact Chinese strings, no certificate numbers or years, and round logos.
- Build: `blender --background --factory-startup --python models/gjh-abalone-cans/generate.py -- --label-source flat` writes `exports/codex/`, `textures/codex/`, `reports/codex/` and `sources/gjh-abalone-cans-codex.blend`. Validate with `node models/gjh-abalone-cans/validate.mjs codex`.
- Same geometry and budgets as the photo set (4,888 triangles, 3 materials, 3 draw calls, under 500 KiB); no LOD1 for this set.
- Comparison images: `reports/codex/compare/<sku>-photo-vs-codex.jpg` (same viewer and camera) and `<sku>-flat-labels.jpg` (the two flat labels).
- Regression: `npm run test:cans:codex` (5 views per can).

## Rights

Packaging artwork belongs to its respective owners (GJH / New Moon). It is used in the owner's project on the owner's confirmation; no independent licence document was supplied, and public redistribution terms have not been specified. Gallery downloads are disabled, but public interactive viewing still serves the GLBs. The can geometry and generator are original work for this repository.
