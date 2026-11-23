# Male parcel carry

Use [sockets_male.json](sockets_male.json) with `body_male.glb` and the round-two bank `round2/motion_male_fixed.glb`. For `hold_box`, set the Parcel node's local TRS from the socket and parent it to `mixamorig:RightHand`. The translation is in metres and the quaternion is XYZW, both in the glTF joint frame. The parcel-local XYZ scale is 0.99343, 1.00039, 1.07780.

Use the fixed right-thumb (8.194°) and right-index (15.952°) deltas and the left-thumb (29.417–31.911°) and left-index (24.475–34.456°) delta tracks. The left tracks have 97 samples from 0 to 2 seconds at 48 Hz, inclusive. At playback time, slerp the adjacent delta samples, then postmultiply the animated joint-local quaternion by the delta before skinning. The first and last delta samples agree. This layer is scoped to `hold_box`.

Socket-only and socket-plus-scale fits left the pads too far away. A fixed left pose still brought the parcel corner inside the distal left index during part of the cycle. The left rotation tracks follow the support motion with one adjusted joint per digit. The right-hand joint drives the parcel. The frame-zero parcel TRS relative to the left joint and the left pad witnesses in parcel space are available under `leftHandSupport` for rigging or inspection.

## Verification

| Measure | Result | Limit |
| --- | ---: | ---: |
| Right thumb, maximum gap | 1.052 mm | ≤ 2 mm |
| Right index, maximum gap | 1.189 mm | ≤ 2 mm |
| Left thumb, maximum gap | 1.836 mm | ≤ 2 mm |
| Left index, maximum gap | 1.925 mm | ≤ 2 mm |
| Penetration, worst measured | 0.859 mm | ≤ 1 mm |
| Penetration, certified upper bound | 1.000 mm | ≤ 1 mm |
| Chin, minimum clearance | 10.489 mm | ≥ 10 mm |

[Verification JSON](verification.json) covers 1,153 poses over the full two-second clip on the 480 Hz grid, including the source 24 fps and male bank 96 Hz half-frame clocks. Gaps are closest-surface distances or conservative upper witnesses from the fixed distal pad patches. Penetration is checked in both mesh directions with adaptive triangle subdivision to bound unsampled spatial depth within each evaluated pose. Chin clearance is measured against the posed head region. The audit certifies the penetration limit at each sampled time.

From this directory, run the guarded Blender commands sequentially.

```sh
sh run.sh verify.py
sh run.sh render.py
```

[Front and both side render sheet](renders/hold_box.png), source frames 0, 12, 30, and 45. The runtime inputs and socket JSON are identified by SHA-256 in the audit.
