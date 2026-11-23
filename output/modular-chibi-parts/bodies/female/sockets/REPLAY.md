# Female prop and chair replay

The sockets use the GLB joint name `mixamorig:RightHand`. Multiply the evaluated joint world matrix by the socket local TRS. Replace the moving prop node's imported TRS. All socket scales are 1. Translations are in metres. World and local transforms use glTF axes and XYZW quaternions.

For `take_item`, apply the display rail's world TRS separately. The first play keeps the jar at the pickup stop until frame 29 on the source 24 fps clock, equivalent to 1.208333 s. On repeat, unparent the jar on frame 0 at the release world transform and follow the reset and return waypoints in the JSON. Apply smoothstep translation and quaternion slerp between successive waypoints. Reattach at frame 29. The female action bank stores tracks on a 60 Hz grid, so the attachment event is scheduled in seconds.

Apply the chair world TRS about the chair's local floor origin.

## Re-measure and render

From this directory, run:

```sh
sh run.sh verify.py
sh run.sh verify.py -- --render
sh run.sh verify.py -- --render-only
```

The verifier reimports `body_female.glb`, `motion_female.glb`, and the prop and chair GLBs. It binds each imported Blender 5 action slot to the female rig. It evaluates the finger tracks embedded in the relevant action, samples integer and half frames on both the source clock and the 30 fps female review clock, and compares the GLB joint chain with the imported pose. It uses fixed female thumb and index pulp triangle patches and signed surface-depth bounds on the posed meshes. The chair audit checks the chair at its original origin and at the configured fit. It measures seat contact at the end of `sit_down`, throughout `sit_idle`, and at the start of `stand_up`, and checks the feet and chair intersection across all three clips. Rendering uses Cycles CPU at two threads.

`verification.json` holds maxima and gate results. `verification-frames.json` records each sample. Verification exits with status 2 on a failed gate after writing its results. Use `sh run.sh verify.py -- hold_box` to verify one clip, or `sh run.sh verify.py -- chair` to recheck the seating sequence.
