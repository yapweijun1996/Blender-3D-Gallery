# Christmas envelope

The owner-approved design is reproduced by `build_envelope.py`. From the repository root, build the Blender source and export the animated GLB with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python models/christmas-envelope/build_envelope.py
```

The script saves `envelope.blend` before converting the trim curves to meshes for `envelope.glb` and stabilizes triangle ordering for repeat exports. Five wax pieces carry the segmented ring and gold relief. Their seam endpoints are exported as `crackRays` on the Seal node. The `Open` glTF clip rotates the lined flap, bow and crossing ribbons to -174 degrees and lifts the letter fully out. The lower ribbon stays tucked against the pocket. The Seal break and Burst markers are exported on the Envelope node, and the Letter node exports its face bounds for the web flight and HTML alignment. The pocket and lining preserve clearance, and paper meshes export UVs for the web grain. The source design was supplied in the read-only Greeting-Card-3D project.

Check hinge contact, letter clearance, and bow clearance at half-frame intervals with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup models/christmas-envelope/envelope.blend --python models/christmas-envelope/check-clearance.py
```
