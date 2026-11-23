# Mall Returns & Exchange Counter

Original metre-scale service fit-out with distinct handover and parcel inspection heights. A high document shelf sits beside an acrylic divider, while the lower worktop contains a raised-lip inspection tray, one unmarked carton, an idle scan housing and a low weighing surface. Separate open intake and checked-return crates sit under the worktop; staff-side recessed drawers and shelves remain editable.

- `mall-returns-exchange-counter.blend`: editable parts by station and material with studio setup. Front is Blender −Y.
- `exports/mall-returns-exchange-counter.glb`: static material-batched +Y-up asset, floor-level origin, no studio geometry, cameras, lights, textures or animation.
- `previews/studio.webp`: actual 512 px Blender render of the same geometry.
- Generic sign and blank labels represented as geometry. No real customer details, retailer identity, POS/payment system, operational scanner, or accessibility/compliance claim. Public redistribution terms are not specified, so the Gallery download control is disabled.

## Reproduce and verify

From repository root with Blender 5.3, WebP tools and the locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/mall-returns-exchange-counter/generate.py
cwebp -quiet -resize 512 512 -q 85 models/mall-returns-exchange-counter/previews/studio.png -o models/mall-returns-exchange-counter/previews/studio.webp
node models/mall-returns-exchange-counter/verify.mjs
blender -b models/mall-returns-exchange-counter/mall-returns-exchange-counter.blend --python-exit-code 1 --python models/mall-returns-exchange-counter/verify_blender.py -- models/mall-returns-exchange-counter/exports/mall-returns-exchange-counter.glb
```

The Blender verifier measures the reimported vertices and checks the separate authoring stations and bins. The Node verifier pins exact bytes, geometry and zero animation. Generated PNG and Blender backup remain local derivatives.
