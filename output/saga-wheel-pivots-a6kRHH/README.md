# Proton Saga (1985) — isolated wheel-pivot prototype

This directory is an isolated experiment. It does not replace the gallery model or modify the deployed site. `scene.blend` is the editable Blender copy and `exports/proton-saga-1985.glb` is the corresponding interactive-node export. `baseline-check.glb` is a copy of the pre-experiment local GLB used solely for rest-pose comparison.

## Hierarchy

```text
ASSET_Proton_Saga_1985
├── Wheel_FL_Steer → Wheel_FL_Roll → left-front wheel pieces
├── Wheel_FR_Steer → Wheel_FR_Roll → right-front wheel pieces
├── Wheel_RL_Roll → left-rear wheel pieces
└── Wheel_RR_Roll → right-rear wheel pieces
```

Source Blender empties have the same names with a `PIVOT_` prefix. The front brake backings follow steering without rolling. In Blender, roll is around local Y and steering around local Z; after glTF export, Three.js uses `rotation.z` for roll and `rotation.y` for steering. The GLB contains no animation clips: the prototype page changes node transforms at runtime.

## Preview and verification

From this directory, with the repository's Node dependencies already installed:

```sh
../../node_modules/.bin/vite --host 127.0.0.1 --port 4183 --strictPort
```

Open <http://127.0.0.1:4183/demo.html>. In another terminal, from this directory:

```sh
node verify_gltf.mjs
node verify_browser.mjs
node verify_mobile.mjs
SAGA_VIEW_WIDTH=320 node verify_mobile.mjs
/Applications/Blender.app/Contents/MacOS/Blender --background --disable-autoexec scene.blend --python-exit-code 1 --python verify_blend.py
```

To regenerate the isolated source and GLB without rerendering, use Blender 5.1.2 and the bundled Studio HDRI at the path in `generate.py`:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python generate.py -- --views none
```

`verification.json` records the checked artifact hashes and results. The browser comparison covers one fixed rest camera and lighting setup, not every possible viewpoint. Four independent roll operations, both front steering operations, static body/other wheels, brake backing and reset were checked in Chromium. Mobile checks used emulation, not physical devices.

The export has 69 mesh primitives versus 42 in the baseline; performance was not profiled. Steering clearance, suspension, tire/ground contact during rotation and collision behavior were not validated. This experiment is not a complete vehicle assembly and does not add controls to the production gallery.
