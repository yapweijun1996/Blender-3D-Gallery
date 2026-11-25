# Container Ship Feeder

A feeder container ship with coloured stacked containers, stern bridge and funnel. This original generic vessel uses simplified, untextured geometry intended for aerial and game-scale views, not a detailed replica of a specific ship.

The hull is 170 m long by 27 m beam. Blender units are metres, bow +X, up +Z; the origin is at the midships waterline Z=0. The GLB uses glTF +Y up with the bow along +X and waterline Y=0. Accessories may extend beyond the quoted hull beam.

From the repository root, Blender 5.3:

```sh
D=models/container-ship-feeder
blender -b -t 4 --python-exit-code 1 -P "$D/generate.py"
cwebp -quiet -resize 640 0 -q 85 "$D/previews/hero.png" -o "$D/previews/hero.webp"
blender -b -t 2 --python-exit-code 1 -P "$D/verify_blender.py"
node "$D/verify.mjs"
```

The generator rebuilds the editable source, exports the GLB, then reimports it to render `hero.png`, `stern.png` and `top.png`. Geometry is batched by material; pieces can be edited as mesh components in the generated source. `verify_blender.py` checks container and binary accessors, reimports the GLB, checks hull dimensions, waterline and triangle degeneracy. `verify.mjs` uses the repository's pinned Khronos validator and requires installed npm dependencies. The Khronos and browser checks have not been run in the environment used for this candidate. The previews are studio renders, not screenshots from a target game.

Original project asset; redistribution terms for public downloads are not specified. No model, texture or brand was downloaded.
