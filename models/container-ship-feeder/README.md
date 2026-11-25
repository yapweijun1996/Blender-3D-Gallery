# Container Ship Feeder

A fictional 170 m feeder with coloured containers, a stern bridge, mooring fittings and a raked bow. The hull has node-baked 512 × 512 colour and roughness maps with paint bands, plating seams and waterline staining. The vessel remains stylised and is not a replica or an engineering model. At close range the bridge fittings, anchors, container walls and bulb remain simplified.

Blender units are metres, bow +X, up +Z; the origin is at the midships waterline Z=0. The GLB uses glTF +Y up, bow +X and waterline Y=0. Accessories can extend beyond the 27 m hull beam.

From the repository root, using Blender 5.3:

```sh
D=models/container-ship-feeder
blender -b --factory-startup -t 4 --python-exit-code 1 -P "$D/generate.py"
cwebp -quiet -resize 640 0 -q 85 "$D/previews/hero.png" -o "$D/previews/hero.webp"
blender -b --factory-startup -t 2 --python-exit-code 1 -P "$D/verify_blender.py"
node "$D/verify.mjs"
```

The generator bakes the procedural atlas, saves the editable source, exports the GLB, then reimports it for side, three-quarter, bridge, stern and top studio renders. The independent Blender check inspects embedded PNG dimensions, material references, geometry, orientation and degeneracy; the Node check uses the pinned Khronos validator and enforces the triangle and byte limits. Browser appearance has not been checked.

The three review rounds found: (1) a detached-looking bulb, repetitive seams and a boxy lifeboat; (2) an unconvincing bulb, regular seams and a rectangular lifeboat; (3) a vertical bow and uniform staining. Subsequent changes reshaped the bulb and bow, added plating and rust variation, and tapered the lifeboat. The final render still shows simplified fittings and a visibly angular bulb.

Original project asset; redistribution terms for public downloads are not specified. No external model or texture was used.
