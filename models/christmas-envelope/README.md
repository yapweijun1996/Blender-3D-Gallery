# Christmas envelope

The owner-approved design is reproduced by `build_envelope.py`. From the repository root, build the Blender source and export the animated GLB with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python models/christmas-envelope/build_envelope.py
```

The script saves `envelope.blend` before converting the trim curves to meshes for `envelope.glb`. The `Open` glTF clip shrinks the seal, rotates the flap to -178 degrees around its top hinge, pauses for the web particle burst, then raises the letter. Closed trim curves are cyclic and the trim, letter and pocket surfaces are separated in depth to avoid coplanar artifacts. The animated flap translates slightly as it rotates to keep its visible hinge edge joined to the envelope. The web experience adds the seal burst and greeting text. The source design was supplied in the read-only Greeting-Card-3D project.

To check the flap against the letter geometry at half-frame intervals:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup models/christmas-envelope/envelope.blend --python models/christmas-envelope/check-clearance.py
```
