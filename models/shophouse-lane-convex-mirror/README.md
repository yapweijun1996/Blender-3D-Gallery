# Shophouse Lane Convex Mirror

An original static SG/MY-inspired shophouse-lane prop: one forward-bulging
spherical-cap lens in a rolled orange rim, a real angled metal support and
rear plate, a short plaster/tile corner and a small fictional chevron plate.
The tint is an abstract vertex-color sheen, not a live mirror and not a
reflection of any street, vehicle or real location.

This is a display asset only. It is not a product replica, a traffic-control
device or a guide to placement, road safety, installation or compliance.

Authored from scratch in Blender 5.3.0. The original `.blend` keeps editable
mesh groups and non-exported studio lights. The static GLB is metres, +Y up
and +Z out; independent artistic context and mounting geometry remain.

```sh
blender -b --factory-startup --python-exit-code 7 -P generate.py -- --output /path/to/isolated-output
blender -b --factory-startup --python-exit-code 7 -P verify_blender.py -- \
  shophouse-lane-convex-mirror.blend exports/shophouse-lane-convex-mirror.glb
node verify.mjs
```

Optional `--review` produces lens and rear-support close-ups outside the
Gallery catalog. Native and reimported meshes are checked against the
spherical cap and sampled rays, including the real rear attachment.

All geometry and art are original, with no texture assets, brands, maps or
outside dependencies. Project asset; redistribution terms for public
downloads are not specified.
