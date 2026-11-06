# Proton Saga 1985 door interior and clearance prototype

This isolated prototype extends the earlier wheel and door studies. It does not replace the production gallery asset. `scene.blend` contains the editable model, `exports/proton-saga-1985.glb` is the exported model, and `demo.html` offers independent door and wheel controls. The demo rotates nodes at runtime; the GLB contains no animation clips or collision system.

## Changes

Each door has a shaped inner card, separate padded vinyl upper rail, fabric insert with modeled pleats and piping, padded armrest, metal release, crank, storage pocket and fasteners. The supplied photographs show the exterior; these interior fittings are an informed visual interpretation, not a documented factory specification. Door hinges, latches, frame dimensions and clearances are also approximate.

The front hinge leaf was narrowed to clear the wing while retaining contact with its pin. The rear body bracket was offset along the pin to clear its moving leaf. The previously continuous window ledge and lower weatherstrip were split into door-mounted front and rear sections plus a short fixed rear section. A small A-pillar adjustment and removal of a redundant decorative vertical shutline reduce intersections; the separate panel seam remains.

## Checks and limitations

- Blender source checks validate four door and wheel hierarchies and the new interior, hinge, latch and weatherstrip parenting. Hardware is decorative; it does not impose a physical constraint.
- `verify_clearance.py` samples the main panels, windows, inner cards and selected body components every 5 degrees from 5 to 60 degrees for each door. Same-side main front and rear panels/windows/cards are also checked at all combinations of 0, 15, 30, 45 and 60 degrees except both closed. No selected triangle surfaces intersect in those sampled open poses.
- `verify_hardware.py` samples the selected moving hinge leaves, latch plates, window cranks, window frames and seals against nearby fixed body and hardware at 0, 1, 2, 3 and every 5 degrees through 60. Expected contacts are explicitly classified: the hinge leaves with their pins, latch/striker at 0–1 degrees, and the rear quarterlight frame/seal with the C-pillar when closed. No other intersections were detected in these samples.
- `verify_hardware_pairs.py` checks selected door hardware and seals against the adjacent door at 0, 1, 2, 5, 10, 15, 30, 45 and 60 degrees for either door with the other closed, and combinations of 5, 15, 30, 45 and 60 degrees for both open. No sampled triangle surface intersections were detected.
- These are discrete surface-intersection checks of selected objects, not continuous swept-volume, containment, or mechanical tolerance tests. They do not establish clearances between the sampled angles, full-scene clearance, material compression, manufacturing fidelity or real vehicle safety.
- Khronos glTF Validator: 0 errors, 0 warnings; 107 nodes, 96 meshes, 31 materials, no animation clips. GLB SHA-256 `2255f6e7ed4bb721fba817c0f413c2c56e222d333dd10f7d032132114d179981`.
- Browser checks verify individual door movement, windows and inner cards following their hinges, reset, wheel roll and steering, and mobile widths of 320 and 390 pixels. A single closed-door view has unchanged bounds versus `baseline-check.glb`; 1,765 of 613,800 pixels differ by more than 5/255. This is not a complete visual-equivalence test.
- `door-FL-interior.png` and `door-RL-interior.png` show the front and rear inner cards at 60 degrees.

The two reference images used for the headlamp textures are also present in the existing public Saga asset. Their source and redistribution limitations remain those documented in `models/proton-saga-1985/README.md`; no additional third-party redistribution rights are asserted.

## Rebuild and verification

With Blender 5.1.2 on macOS and the repository's Node dependencies installed, from this directory:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python generate.py -- --views none
/Applications/Blender.app/Contents/MacOS/Blender --background scene.blend --python-exit-code 1 --python verify_blend.py
/Applications/Blender.app/Contents/MacOS/Blender --background scene.blend --python-exit-code 1 --python verify_clearance.py
/Applications/Blender.app/Contents/MacOS/Blender --background scene.blend --python-exit-code 1 --python verify_hardware.py
/Applications/Blender.app/Contents/MacOS/Blender --background scene.blend --python-exit-code 1 --python verify_hardware_pairs.py
node verify_gltf.mjs
../../node_modules/.bin/vite --host 127.0.0.1 --port 4188 --strictPort
```

In another terminal:

```sh
node verify_doors.mjs
SAGA_PIVOT_URL=http://127.0.0.1:4188/demo.html node verify_browser.mjs
node capture_details.mjs
```

Set `SAGA_DOOR_URL` to test the door scripts at a different preview URL. `baseline-check.glb` is the preceding door-detail prototype used for the closed-pose comparison. The generator requires both bundled files in `textures/` and the Blender-bundled studio HDRI at the path indicated in `generate.py`.
