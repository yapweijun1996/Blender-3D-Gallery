# Escalator boarding and exit study

The unmodified [escalator](../../../models/escalator/exports/optimized.glb) and [GJH visitor](../../../models/gjh-mall-visitor/exports/gjh-mall-visitor.glb) support a bounded standing ride. Smooth forward root travel using the native walk and idle animations failed the tested lower and upper handoffs.

## Boarding and exit

Two static poses can span the comb visually. At machine times 0.2167 s below and 18.2333 s above, one leading shoe touches the receiving surface while the opposite shoe is still 72.78 mm above its departing surface. These are individual poses.

The trajectory search uses the original walk and idle clips. It varies walking phase, duration, fixed-deck starting or stopping position and rendezvous time with `STEP_00`. The root follows a smooth cubic between the static deck and the moving stance, matching 0 and approximately −0.500 m/s at the appropriate ends. It blends smoothly between idle and walk for 130 ms. The screen admits rib contact inside the comb zone and ranks 12,992 lower and 10,048 upper trajectories under a 1.2 m/s maximum root speed. The best 60 from each end are rescored with exact native poses at 120 Hz. The highest-ranked pair is then replayed against the actual machine triangles at 240 and 480 Hz.

| Best screened trajectory at 480 Hz | Lower boarding | Upper exit |
| --- | ---: | ---: |
| Elapsed time | 1.00 s | 1.40 s |
| Frames sampled | 481 | 673 |
| Frames with neither near-ground shoe patch overlapping a machine surface, including the comb and neighboring steps | 22 | 54 |
| Corresponding result at 240 Hz | 11 / 241 | 27 / 337 |
| Cumulative planted shoe-material travel relative to the same supporting part, summed over both shoes | 1.974 m | 2.860 m |
| Largest machine protrusion found above the terminal plane in the shoe rectangle | 0 mm | 0 mm |

The support replay first tests the actual lowest sole vertex against the machine. When that fails, it probes all near-ground sole vertices, then tests overlap of the actual near-ground triangles of the shoe and machine projected into X/Z. Each side gets a generous 0.7 mm height tolerance. A frame counted as unsupported fails even this last test. The penetration check clips obstructing machine triangles against a rectangle enclosing both complete shoes. Its zero result bounds the sampled frames only. The sliding measurement follows the same vertex of the same shoe relative to the same native supporting node across consecutive frames, allowing the contact point to change when a rounded shoe rolls.

As a separate gait diagnostic, cancelling horizontal displacement of the lowest shoe material on a stationary floor requires approximately 1.021 m of forward root travel and 0.987 m of backward travel over one 1.0083 s native walk cycle (240 intervals). This explains why simply moving that cycle forward produces sliding. Other timing families and independently constrained leg animation remain untested. A boarding feature still needs contact-locked shoe placement and full clearance checks through both handoffs. The existing fixed-floor visitor controller's width is a separate integration issue.

## Contact anchors for a separate animation

The following world coordinates are in metres, with +Y up and the visitor facing −Z (yaw π). They come from the native walk pose at 0.256285 s. The leading left shoe touches the listed surface. The trailing right shoe is 72.78 mm above its projected contact anchor in both cases.

| Candidate | Lower boarding | Upper exit |
| --- | --- | --- |
| Machine time | 0.216667 s | 18.233333 s |
| Visitor root | (0, 0, 4.583379) | (0, 3, −4.412428) |
| Left shoe on receiving surface, world | STEP_00 (+0.117393, 0, 4.404128) | Upper landing (+0.117393, 3, −4.591679) |
| Right shoe projected onto departing surface, world | Lower landing (−0.117393, 0, 4.974816) | STEP_00 (−0.117393, 3, −4.020991) |
| Moving shoe anchor in STEP_00 local coordinates | Left (+0.117393, 0.200000, +0.271367) | Right (−0.117393, 0.200000, +0.084391) |
| Window for this moving shoe's full projection on the exposed flat at its local anchor | 0.1083–2.4583 s | 16.0417–18.3667 s |

The measured native pose reaches a 0.570688 m longitudinal and 0.617097 m horizontal spread between the two sole projections. Its left hip–knee and knee–ankle distances are 0.278354 and 0.371288 m, with 0.649232 m between hip and ankle. The trailing raised shoe needs a new contact-locked animation. The moving shoe's timing window describes its fixed longitudinal shape at the reported local anchor. A changing pose needs the same support and clearance checks on the final animation.

## Reproduction

From the repository root with its existing Node dependencies, run the search and then the physical replay.

```sh
node docs/verification/mall-escalator-passenger/search-transfers.mjs
node docs/verification/mall-escalator-passenger/verify-transfer.mjs
```

The search reads both GLBs, obtains STEP_00 bounds from the native position attributes and its circulation period from the native clip, and writes [transfer-open-ribs.json](transfer-open-ribs.json). The replay reads that report and the same GLBs and writes [transfer-replay.json](transfer-replay.json), including shoe-patch contact, sliding relative to each supporting part, missing-surface witnesses and anchor locations.
