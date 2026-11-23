# Mid-Autumn Rabbit Lantern

F06 is an original seated paper rabbit lantern. The lower-left rabbit on the
[festival concept board](../../docs/festival-models/regional-festival-concepts.png)
informed the warm paper, rose ear panels, thin bamboo ribs and blossom branch.
The geometry, materials and floral shapes are original. The model includes no
reference pixels, third-party textures, logos or fonts. Public redistribution
terms remain unspecified, so the gallery's download control is disabled.

The lantern is a static decorative interpretation with a warm emissive paper
material. It has no physical light source or animation. The gallery viewer provides
rotation, zoom and reset. The existing Mid-Autumn display and mooncake box are
separate assets.

## Source and rebuild

The `sources/` Blender file retains 141 editable meshes for the paper shells,
ribs, face, paws, tail and blossoming branches. The Blender 5.1.2 generator saves
the editable source first, then batches by material for the GLB. It uses only
Blender and its bundled glTF exporter.

From this directory:

```sh
blender -b --threads 4 --python-exit-code 1 --python generate.py
blender -b --threads 5 --python-exit-code 1 --python render.py -- hero front other-side rear
for view in hero front other-side rear; do
  cwebp -quiet -q 84 -resize 480 0 "previews/$view.png" -o "previews/$view.webp"
done
```

The preview script imports the actual GLB into a new scene before rendering.
The four WebP previews are derived from the 640 px Cycles renders. See
[verification](verification.md) for the exact export reviewed and the limits
of the rebuild comparison.
