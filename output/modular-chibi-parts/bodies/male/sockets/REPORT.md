# Male prop sockets and chair fit

The socket poses use the right-hand glTF joint frame in `body_male.glb`. Translation is in metres and rotation is a quaternion in XYZW order. Multiply `jointWorld * socketTRS` to place each prop at unit scale. The parcel uses the right hand as its single rigid parent and needs left-hand support. The bag uses only the right hand. Keep the round-two motion translation and scale tracks when applying these measurements. The rail and chair transforms are in character-root space.

| Prop | Clip | Joint-local translation | Joint-local quaternion |
| --- | --- | --- | --- |
| Cup | `hold_item` | (-0.04959401, 0.08037566, -0.02424632) | (-0.04658692, 0.35610232, 0.06851655, 0.93076652) |
| Parcel | `hold_box` | (-0.10220344, 0.15550776, -0.15435663) | (-0.36467868, 0.16313389, 0.88695973, 0.23173097) |
| Market bag | `hold_bag` | (-0.07450011, 0.06157902, -0.00462160) | (-0.10601247, 0.44064006, 0.89135526, 0.00913738) |
| Jam jar | `take_item` | (-0.05461096, 0.11922517, -0.01838388) | (0.04178555, -0.98298472, -0.01577102, 0.17817499) |

## Carry verification

The box remains a fit candidate. The fixed right-hand attachment can keep the parcel clear of the chin, but the supplied two-hand pose leaves too much distance to the finger pads. The release and pickup placement are supplied for the jar, and the rail still has a clearance failure.

| Clip | Samples / grip samples | Right thumb / index gap, mm | Left thumb / index gap, mm | Deepest measured penetration, mm | Chin clearance, mm | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `hold_item` | 481 / 481 | <0.001 / <0.001 | — | 0.262 | — | Pass |
| `hold_box` | 385 / 385 | 11.143 / 10.329 | 11.198 / 10.019 | 0.865 | 10.047 | Candidate |
| `hold_bag` | 385 / 385 | 0.252 / 1.493 | — | 0.507 | — | Pass |
| `take_item` | 385 / 153 | 0.009 / 1.824 | — | 0.461 | — | Candidate |

The verifier takes the largest closest-surface witness for each anatomical finger pad. For a passing gap, a vertex-to-face witness certifies an upper bound. Near the gate it also checks edge-to-edge and reverse vertex-to-face witnesses. Penetration checks both directions and subdivides crossed triangles to certify the 1 mm limit. The reported depth is the largest measured depth. The box penetration check did not certify the 1 mm upper bound. The box clearance uses the lower head surface.

## Jar and display rail

At frame 29 (24 fps), the pickup pose is (-0.19790703, 0.59882504, 0.27100462) m with quaternion (0.14952782, 0.26493269, 0.40303576, 0.86314213). Right thumb and index gaps are 0.002 / 1.819 mm, and the largest handoff vertex displacement is 0.000031 mm.

Release at frame 0 of a repeat at (-0.26002100, 0.58494163, 0.17075849) m with quaternion (0.15333869, 0.22097628, 0.38759503, 0.88171816). The measured release displacement is 0.000030 mm. Ease the world-space position and quaternion from return to pickup over frames 3–16, then wait at pickup until frame 29. The first play starts with the jar at pickup.

The **Display rail** candidate uses offset (-0.02526050, -0.01547367, 0.04746266) m, quaternion (-0.05883089, 0.05497378, 0.02706215, 0.99638569) and scale (1.00547969, 1.18747759, 1.08232641). The free jar stops are in character-root space. Their measured maximum deck gap is 0.300 mm and the deepest excursion below the deck is 0.000 mm. The attached jar/body depth measured 0.455 mm. The rail-to-body depth measured 30.272 mm, so the complete shelf scene fails the clearance gate.

The frame-29 pads are separated horizontally by at least 79.822 mm along their separation axis. The upright jar is at most 60.000 mm wide along that axis. The candidate therefore uses a tilted jar.

A grip with an upright jar would require at least 13.822 mm less projected pad separation at frame 29 to make the two 3 mm contact bounds compatible. The tilted combination is a geometric handoff candidate. The rail intersects the right forearm, including along the supported path near the return stop.

## Chair

Keep the chair at the character origin and scale glTF Y by 0.93511904762. The seat moves from 252.000 mm to 235.650 mm. Seat gap is measured at the settled endpoint of `sit_down`, throughout `sit_idle`, and at the initial pose of `stand_up`.

| Clip | Samples | Peak inside vertices, original → fitted | Fitted triangle intersections | Right / left settled gap, mm | Right / left maximum foot contact error, mm | Maximum heel lift, mm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sit_down` | 289 | 112 → 0 | 0 | 0.268 / 0.254 | 0.090 / 0.090 | 14.783 |
| `sit_idle` | 721 | 112 → 0 | 0 | 0.268 / 0.254 | 0.090 / 0.090 | 10.234 |
| `stand_up` | 241 | 112 → 0 | 0 | 0.268 / 0.254 | 0.090 / 0.090 | 14.780 |

The bare feet meet the floor at the forefoot. The heel lift comes from the supplied motion and remains visible in the side views.

## Files

- [Runtime values](sockets_male.json) and [per-frame verification](verification.json).
- [Verification script](verify.py), [geometry and GLB replay](geometry.py), [Cycles render script](render.py) and [Blender runner](run.sh).
- Front and side review sheets with four frames each. [Cup](renders/hold_item.png), [parcel](renders/hold_box.png), [market bag](renders/hold_bag.png), [jar](renders/take_item.png), [sit down](renders/sit_down.png), [sit idle](renders/sit_idle.png) and [stand up](renders/stand_up.png).

Run from this directory using the provided guarded Blender 5 setup.

```sh
sh run.sh verify.py
sh run.sh render.py
```

The verification merges integer and half frames from the source and baked-bank clocks, including the demo 24 fps clock. It replays the supplied finger tracks. The gesture bank and Blender master are checked against the body bind. The script writes the per-frame measurements before returning a nonzero exit status for a failed gate.
