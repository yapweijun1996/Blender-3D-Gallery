# GJH Abalone Cans

Four metre-scale canned-abalone props for the owner's GJH virtual mall: New Zealand, Australia, South Africa and Mexico. The can geometry is original, deterministic Blender Python. Each wrap-around label is **unrolled from the official front and reverse GJH eShop packshots** held in the owner's `Webpage-Design-Gallery` repository (`assets/companies/gjh/official`). No logo, certification mark or text was redrawn or generated.

| Asset | Origin | Pack | Chinese type name | Triangles | GLB bytes |
| --- | --- | --- | --- | ---: | ---: |
| `gjh-can-new-zealand-abalone` | New Zealand | 425g | 新西兰鲍鱼罐头 | 2,490 | see `reports/assets.json` |
| `gjh-can-australia-abalone` | Australia | 425g | 澳洲鲍鱼罐头 | 2,490 | see `reports/assets.json` |
| `gjh-can-south-africa-abalone` | South Africa | 425g | 南非鲍鱼罐头 | 2,490 | see `reports/assets.json` |
| `gjh-can-mexico-abalone` | Mexico | 454g | 墨西哥鲍鱼罐头 | 2,490 | see `reports/assets.json` |

## Contents

- `exports/*.glb`: self-contained glTF 2.0, one embedded JPEG label texture each, floor-centre origin, front toward glTF +Z. Parts: `CanBody`, `TopSeam`, `BottomSeam`, `Lid`, `PullTabPlate`, `PullTabRing`, `Label`.
- `sources/gjh-abalone-cans.blend`: editable scene with all four cans in a row (textures packed) and a non-exported `STUDIO` group.
- `textures/*-label.jpg`: the derived 1280-pixel label strips. `reports/build.json` records the SHA-256 of every source packshot used, the detected can bounds and texture sizes.
- `metadata/*.json`, `previews/*.webp`, `reports/assets.json`: gallery metadata, thumbnails and measured metrics.

## Reproduce

Blender 5.2.3 LTS, from the repository root. The generator reads the packshots from the sibling `Webpage-Design-Gallery` checkout by default, or from `--packshots`:

```sh
blender --background --factory-startup --python models/gjh-abalone-cans/generate.py -- --packshots /path/to/Webpage-Design-Gallery/assets/companies/gjh/official
node models/gjh-abalone-cans/validate.mjs
npm test
```

Thumbnails are 640 px WebP converted from the Blender PNG renders (any converter works; PNGs are not committed).

## Limits

- Diameter is a nominal 73.5 mm and height follows each packshot's aspect ratio (about 124 mm). These are not official packaging dimensions; the 454g Mexico SKU is not scaled differently because its photo has the same aspect.
- A single-view unroll: the strips near each side are blended between the front and reverse photographs, and lighting baked into those photographs remains in the texture. Resolution is limited by the roughly 350 px-wide can in each 1000 px source.
- Nutrition panels and the second side views of the NZ/AU/SA SKUs are not used.
- The label shows the New Moon brand (GJH house brand), and the cans are packaging props, not product claims. Certification marks printed on the label are part of the source photograph, not independently verified.

## Rights

Packaging artwork belongs to its respective owners (GJH / New Moon). It is used in the owner's project on the owner's confirmation; no independent licence document was supplied, and public redistribution terms have not been specified. Gallery downloads are disabled, but public interactive viewing still serves the GLBs. The can geometry and generator are original work for this repository.
