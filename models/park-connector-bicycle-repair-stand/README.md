# Park Connector Bicycle Repair Stand

Original metre-scale roadside cycle repair fixture inspired by public cycling street furniture in Singapore and Malaysia. Two cantilevered support arms have modeled protective sleeves. Four hand-tool silhouettes hang on separate inset tethers. A distinct compact pump has a plunger, T-handle, unnumbered pressure dial, curved hose and docked valve head, all on a shared mounting pad.

- `park-connector-bicycle-repair-stand.blend`: grouped, independently editable parts and studio setup. Front faces Blender −Y.
- `exports/park-connector-bicycle-repair-stand.glb`: static material-batched model, +Y up and floor-level origin, no studio geometry or animation.
- `previews/studio.webp`: actual 512 px Blender studio render of the same geometry.
- Generic pictogram and wording, no operator or brand affiliation, real repair or calibration functionality, or accessibility/engineering certification. Public redistribution terms are not specified; Gallery download control is disabled.

## Reproduce and verify

From repository root with Blender 5.3, WebP tools and locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/park-connector-bicycle-repair-stand/generate.py
cwebp -quiet -resize 512 512 -q 85 models/park-connector-bicycle-repair-stand/previews/studio.png -o models/park-connector-bicycle-repair-stand/previews/studio.webp
node models/park-connector-bicycle-repair-stand/verify.mjs
blender -b models/park-connector-bicycle-repair-stand/park-connector-bicycle-repair-stand.blend --python-exit-code 1 --python models/park-connector-bicycle-repair-stand/verify_blender.py -- models/park-connector-bicycle-repair-stand/exports/park-connector-bicycle-repair-stand.glb
```

The Blender check measures reimported vertices and verifies authored tool count, tethers, contact sleeves and dial hardware. The Node check verifies exact bytes and static export. Generated PNG and Blender backup are local derivatives only.
