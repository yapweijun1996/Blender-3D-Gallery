# Christmas envelope

The owner-approved design is reproduced by `build_envelope.py`. From the repository root, build the Blender source and export the animated GLB with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python models/christmas-envelope/build_envelope.py
```

The script saves `envelope.blend` before converting the trim curves to meshes for `envelope.glb` and stabilizes triangle ordering for repeat exports. The `Open` glTF clip begins with the seal shrinking on tap, rotates the lined flap to -174 degrees, and eases the letter out. The Blender timeline's Burst marker is exported as `burstTime` on the Envelope node, letting the web burst start during the final part of the flap swing and overlap the letter lift. The flap's folded shoulder pivots inside the back panel. Closed trim curves are cyclic, and the trim, letter and pocket surfaces are separated in depth to avoid coplanar artifacts. The web experience adds the address, stamp, particle burst and greeting text. The source design was supplied in the read-only Greeting-Card-3D project.

Check hinge contact and letter clearance at half-frame intervals with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup models/christmas-envelope/envelope.blend --python models/christmas-envelope/check-clearance.py
```
