# Festival Flower-Garland Stall

Original metre-scale flower-vendor fit-out inspired by Singapore and Malaysia streets. Alternating pale jasmine-like and saffron marigold-like U strands hang from visible hooks and cotton loops. A scalloped textile awning, two stock and wrapping trays, leaf blanks, three thread spools and a slatted storage basket model a believable small retail stall. Flower varieties and arrangement are illustrative, not a claim about a specific vendor, tradition, venue or botanical species.

- `festival-flower-garland-stall.blend`: editable individual garland loops, strand meshes, stock and stall structures, with a studio setup.
- `exports/festival-flower-garland-stall.glb`: static material-batched +Y-up model, floor-level origin, no animation, lights, textures, cloth physics or transactional behavior. Front is Blender −Y.
- `previews/studio.webp`: real 512 px studio render. Original geometry only; no brand, third-party art or sampled textures. Public redistribution terms are unspecified, so the Gallery download control is disabled.

## Reproduce and verify

From repository root with Blender 5.3, WebP tools and the locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/festival-flower-garland-stall/generate.py
cwebp -quiet -resize 512 512 -q 83 models/festival-flower-garland-stall/previews/studio.png -o models/festival-flower-garland-stall/previews/studio.webp
node models/festival-flower-garland-stall/verify.mjs
blender -b models/festival-flower-garland-stall/festival-flower-garland-stall.blend --python-exit-code 1 --python models/festival-flower-garland-stall/verify_blender.py -- models/festival-flower-garland-stall/exports/festival-flower-garland-stall.glb
```

The Blender check verifies the alternating editable garlands and observed GLB bounds; Node pins exact bytes and static export. Any PNG or Blender backup is a local derivative.
