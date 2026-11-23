# Female parcel carry

Use [sockets_female.json](sockets_female.json) with `body_female.glb` and `motion_female.glb`. For `hold_box`, set the Parcel node's local TRS from the socket and parent it to `mixamorig:RightHand`. The translation is in metres and the quaternion is XYZW, both in the glTF joint frame. The parcel-local XYZ scale is 1.09462, 0.95151, 1.07977.

Apply each fixed finger delta by postmultiplying that joint's animated local quaternion before skinning. The right thumb uses 3.627°, the left thumb 12.658°, and the left index 26.921°. The right index reaches the parcel with its baked pose. Socket-only and socket-plus-scale fits still exceeded the contact and penetration limits. The chosen fit uses three finger joints, one per adjusted digit, and keeps the socket rigid through the loop.

The left hand supports the parcel through the baked wrist motion and the two left finger deltas. `leftHandSupport` includes the frame-zero parcel TRS relative to the left joint and the parcel-local thumb and index contact witnesses for rigging or inspection. The right-hand joint drives the parcel.

## Verification

| Measure | Result | Limit |
| --- | ---: | ---: |
| Right thumb, maximum gap | 0.888 mm | ≤ 2 mm |
| Right index, maximum gap | 1.404 mm | ≤ 2 mm |
| Left thumb, maximum gap | 1.455 mm | ≤ 2 mm |
| Left index, maximum gap | 1.727 mm | ≤ 2 mm |
| Penetration, worst measured | 0.382 mm | ≤ 1 mm |
| Penetration, certified upper bound | 1.000 mm | ≤ 1 mm |
| Chin, minimum clearance | 38.873 mm | ≥ 10 mm |

[Verification JSON](verification.json) covers 961 poses from 0 to 2 seconds. The 480 Hz grid includes both endpoints and the 24 fps source half-frame and 60 Hz bank half-frame grids. Gaps are closest-surface distances or conservative upper witnesses from the fixed distal pad patches. Penetration is checked in both mesh directions with adaptive triangle subdivision to bound unsampled spatial depth within each evaluated pose. Chin clearance is the minimum distance to the posed head region. The audit certifies the penetration limit at each sampled time.

From this directory, run the guarded Blender commands sequentially.

```sh
sh run.sh verify.py
sh run.sh render.py
```

[Front and both side render sheet](renders/hold_box.png), source frames 0, 12, 30, and 45. The runtime inputs and socket JSON are identified by SHA-256 in the audit.
