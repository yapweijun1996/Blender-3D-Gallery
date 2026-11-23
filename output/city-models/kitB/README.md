# Singapore city kit B

The 16 GLBs use metres, +Y up and +Z street front. The origin is at ground level, centred on the mounting footprint or main floor. Tree pivots follow the trunk base. The dimensions in `models.json` are the full exported X × Y × Z bounds, including any entrance ramp.

- `signal_pole.glb` has three one-primitive nodes and meshes named `light`. Each has its own `light` material. Use the node's `extras.signalChannel` to identify `red`, `amber`, and `green` independently. The asset is static.
- `zebra_crossing.glb` is an 11 × 2.6 m road strip with eight raised-by-2-mm painted bars. It is intended to occupy a matching cutout in the road tile.
- Both stalls retain their street-facing counters. Enter from the rear via a 1.50 m wide ramp. Each ramp rises 0.12 m over 0.42 m. In the hawker stall, the source drain is flush with the deck. Both assets have a checked 1.50 m wide route with 1.50 m headroom. The manifest records the checked spans in local coordinates. The check uses the actual exported triangles, and game collision and controller integration are engine-side.
- Each gallery source is named in `models.json`. The GLB contains flat PBR colour factors. A material name can recur when the same category needs several colour swatches.

## Comparison renders

Every `renders/*.png` shows twelve Cycles CPU images, with six views of the original GLB and the same six views of the game export. Rows 1 and 2 run front, right, rear. Rows 3 and 4 run left, front-right three-quarter, top. Rows 1 and 3 are the gallery export. Rows 2 and 4 are the Kit B export. Blender 5.1.2 used two CPU threads.

## Rebuild and validate

From this directory, use the same guarded Blender executable specified for the kit:

```sh
PYTHONDONTWRITEBYTECODE=1 DYLD_INSERT_LIBRARIES="$guard" "$blender" \
  -b -noaudio -t 2 --python-exit-code 1 --python build.py -- --render
node validate.mjs
```

The build can take gallery IDs after `--render` to regenerate a subset. Use `--render-only` to compare existing GLBs. The validator uses the repository's installed Khronos `gltf-validator`, checks kit constraints and writes `models.json` on success.
