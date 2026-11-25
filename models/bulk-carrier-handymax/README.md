# Bulk Carrier Handymax

A fictional 190 m bulk carrier with a 32 m beam, five hatch coamings and four cargo cranes. Procedural node-baked 512 × 512 colour and roughness maps add paint bands, hull seams and waterline staining. The vessel remains stylised and is not a replica or engineering model. The anchor, crane mechanisms, bridge fittings and bulb remain simplified at close range.

Blender units are metres, bow +X, up +Z; the origin is at the midships waterline Z=0. The GLB uses glTF +Y up with bow +X and waterline Y=0.

From the repository root, using Blender 5.3:

```sh
D=models/bulk-carrier-handymax
blender -b --factory-startup -t 4 --python-exit-code 1 -P "$D/generate.py"
cwebp -quiet -resize 640 0 -q 85 "$D/previews/hero.png" -o "$D/previews/hero.webp"
blender -b --factory-startup -t 2 --python-exit-code 1 -P "$D/verify_blender.py"
node "$D/verify.mjs"
```

The generator bakes the hull maps, saves the editable source, exports the GLB and renders the imported GLB. The Blender check examines embedded PNGs, material references, orientation, bounds and degeneracy. The Node check enforces size and triangle limits and runs the pinned Khronos validator. Browser appearance has not been checked.

Three review rounds found: (1) a rectangular lifeboat, block-like crane hooks and low-contrast hatch rims; (2) hatch rims using the wrong part of the hull texture and featureless crane bases; (3) ladder rungs without rails and bare hatch covers. The generator was revised after each review to address these issues. Remaining hull and superstructure details are intentionally simplified.

Original project asset; redistribution terms for public downloads are not specified. No external model or texture was used.
