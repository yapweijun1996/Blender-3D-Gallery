# Oil Tanker Aframax

A fictional 245 m tanker with a 42 m beam, cargo pipelines, a raised walkway and manifold. Procedural node-baked 512 × 512 colour and roughness maps add paint bands, hull seams and waterline staining. The vessel remains stylised and is not a replica or an engineering model. The anchor, bridge fittings and bulb remain simplified at close range.

Blender units are metres, bow +X, up +Z; the origin is at the midships waterline Z=0. The GLB uses glTF +Y up with bow +X and waterline Y=0.

From the repository root, using Blender 5.3:

```sh
D=models/oil-tanker-aframax
blender -b --factory-startup -t 4 --python-exit-code 1 -P "$D/generate.py"
cwebp -quiet -resize 640 0 -q 85 "$D/previews/hero.png" -o "$D/previews/hero.webp"
blender -b --factory-startup -t 2 --python-exit-code 1 -P "$D/verify_blender.py"
node "$D/verify.mjs"
```

The generator bakes the hull maps, saves the editable source, exports the GLB and renders the imported GLB. The Blender check examines embedded PNGs, material references, orientation, bounds and degeneracy. The Node check enforces size and triangle limits and runs the pinned Khronos validator. Browser appearance has not been checked.

Three review rounds found: (1) square pipe runs, a box-like lifeboat and an indistinct manifold; (2) a low manifold and a featureless bridge side; (3) an unsupported walkway and broad rust patches. The generator was revised after each review to address these issues. Remaining hull and superstructure details are intentionally simplified.

Original project asset; redistribution terms for public downloads are not specified. No external model or texture was used.
