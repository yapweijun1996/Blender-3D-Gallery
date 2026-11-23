# Female socket fit status

The cup passed the full mesh replay. The parcel trial failed the grip and penetration limits. The bag, jar and chair placements are working candidates. The Blender audit stopped progressing during the bag check. The exact jar handoff, revised chair contact and PNG renders are pending.

| Clip | Samples | Thumb and index, right, mm | Thumb and index, left, mm | Maximum penetration, mm | Status |
| --- | ---: | --- | --- | --- | --- |
| hold_item | 121 | 0.07234, 0.44860 | — | 0.08822 measured; 0.12323 upper bound | Pass |
| hold_box | 193 | 10.32199, 8.42581 | 3.62555, 7.01453 | 1.53901 measured; 1.57401 upper bound | Fail |
| hold_bag | 193 in socket fit | 0.76654, 0.41052 | — | 0.20189 sampled during fit | Full audit pending |
| take_item | Attached subset of 193 in socket fit | 0.59104, 0.98001 | — | 0.22989 sampled during attached fit | Approach, shelf and release pending |

The box trial kept 31.56198 mm of lower-head clearance. The baked box action poses both hands for support. Its rigid prop parent is the right hand. The bag uses the right hand.

The chair candidate uses a glTF translation of `(0, 0, -0.028)` m and an XYZ scale of `(1, 0.9600726966820066, 1)` about its floor origin. The cushion top is 241.93832 mm high. The chair checker found zero body vertices inside and zero intersecting triangle pairs at 73 sit-down, 181 seated and 61 stand-up samples. Representative bilateral seat gaps ranged from 0.25010 to 4.44725 mm. Full contact and per-foot verification is pending.

See [the candidate transforms](sockets_female.json) and [replay instructions](REPLAY.md). The exact cup and parcel audit observations are recorded in `verify.log`. 
