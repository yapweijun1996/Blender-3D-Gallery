# Woodland Christmas Wreath

A wall or door wreath with five interwoven willow stems. Seventy-five individual sprays turn around the ring in successive layers of fir, silver fir and cedar. Four clusters of holly, three open cones and a folded crimson velvet bow break the radial pattern. The two cut tails and the older gold stitching follow the cloth folds.

![Front studio view of the hanging wreath](previews/hero.webp)

## Viewing and placement

The decorated face points along glTF +Z. +Y is up. The origin is at the centre of the willow ring on the nominal wall plane. The asymmetric foliage and hanging tails extend 0.4991 m wide, 0.5587 m high and 0.1782 m deep. At a height of 0.207 m above the origin the rear brass loop has 17.18 mm of internal width and 56.55 mm of free depth to the first front sprig along its centreline. Two wire lashings wrap the keyhole's lower bar and the willow. The [rear detail](previews/hanger.webp) shows the attachment.

## Editing

Open [the editable Blender file](sources/christmas-wreath.blend) in Blender 5.1.2. The four numbered collections contain the core and hanger, foliage, accents and bow. Expand a foliage object's vertex groups to select an individual spray. Each pinecone, fruit cluster, loop, tail and knot is a separate mesh. The finest double-sided needles have a longitudinal crease and per-vertex pigmentation. The cloth has an outer face, a darker reverse and a closed edge.

The generator uses seed 2512. The source and generator use metres. Geometry, pigment palettes, materials and both studio renders were authored for this gallery. The project supplied all artwork. Public downloads are disabled.

## Reproducing the export

From this directory, export your saved edits and render the two views from the resulting GLB. Replace `blender` with your installation's executable when necessary.

```sh
blender -b --factory-startup -Y --python-exit-code 1 -P generate.py -- \
  --export-source --out exports/christmas-wreath.glb \
  --preview previews/hero.webp --rear-preview previews/hanger.webp
```

To regenerate the model in an empty directory, give the builder a fresh source filename. The generator refuses to overwrite an existing editable source.

```sh
scratch=$(mktemp -d)
blender -b --factory-startup -Y --python-exit-code 1 -P generate.py -- \
  --build --source "$scratch/wreath.blend" --out "$scratch/wreath.glb"
```

With the gallery's normal Node dependencies installed, run the following checks. The first loads the GLB in Three.js and the Khronos validator, probes the rear aperture and casts 81 clearance rays through a 150 mm central disc. The second opens Blender, checks the hardware topology, compares both export modes byte for byte and moves one cone upwards by 12 mm in an isolated source copy.

```sh
node verify.mjs
blender -b --factory-startup -Y --python-exit-code 1 -P verify_source.py
```

The shipped [GLB measurements](reports/glb-validation.json) and [source edit results](reports/source-edit.json) include the SHA-256 digests.
