# Mall Ride-Hail Pickup Bay

Original metre-scale mall curbside scene with one distinct marked vehicle berth, a B08 pickup marker, a curb-cut and tactile tile, a rear-supported weather canopy, channel lights, a connected downspout, and a sheltered bench. The standing seam roof, curb, paint, bollards and tile warning studs are modeled geometry. This scene is not representative of any specific venue, does not set driving rules and makes no road, drainage or accessibility-compliance claim.

- `mall-ride-hail-pickup-bay.blend`: editable source with separately named components and a studio setup. Front/road is Blender −Y.
- `exports/mall-ride-hail-pickup-bay.glb`: static material-batched model with no textures, branding, lighting objects, physics or animation. glTF +Y is up, +Z points to the road, and origin is the modular plinth underside.
- `previews/studio.webp`: actual 512 px Blender render of the exported design.
- Three non-rendering, named model-local anchor nodes are provided for reuse. `ANCHOR_PICKUP_B08` is the marker center, `ANCHOR_VEHICLE_STOP` uses the road surface as the tyre contact plane, and `ANCHOR_BOARDING_POINT` is on the road just ahead of the curb cut. Stable glTF coordinates are recorded in metadata. The drawn berth is 2.04 m deep, not a real-world design specification.
- No third-party model or artwork was used. Public redistribution terms are not specified, so the Gallery download control is disabled.

## Reproduce and verify

From repository root with Blender 5.3 and the project's locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/mall-ride-hail-pickup-bay/generate.py
cwebp -quiet -resize 512 512 -q 85 models/mall-ride-hail-pickup-bay/previews/studio.png -o models/mall-ride-hail-pickup-bay/previews/studio.webp
node models/mall-ride-hail-pickup-bay/verify.mjs
blender -b models/mall-ride-hail-pickup-bay/mall-ride-hail-pickup-bay.blend --python-exit-code 1 --python models/mall-ride-hail-pickup-bay/verify_blender.py -- models/mall-ride-hail-pickup-bay/exports/mall-ride-hail-pickup-bay.glb
```

The three intentional empty nodes must be the only Khronos informational issues. The generated PNG and Blender backup are local products, not Gallery assets.
