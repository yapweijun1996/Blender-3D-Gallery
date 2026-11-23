# Escalator terminal and 2 m floor joint

The original [escalator](../../../models/escalator/README.md) has a 1.55 m-wide deck at each end. Beneath each deck, a crossbeam projects 20 mm past the tread and its top sits 20 mm below the finished surface. A 100 mm-thick [floor slab](../../../models/mall-floor-module-2m/README.md) placed flush against the tread overlaps the beam by 80 mm vertically. Moving the slab 20 mm outwards leaves the top of the beam exposed in a 20 mm-wide depression.

## Tested profile

The verification script builds a short transition piece in memory. It spans the slab’s 2.00 m width and extends 120 mm from the deck edge. Its central underside recess is 1.56 m wide and 25 mm long. A 15 mm skin above the recess allows the top to meet the deck and the original slab. Measured clearance around the beam was 5 mm on each side, above and behind it.

| Terminal | Profile origin, metres (X, Y, Z) | Yaw | Slab origin, metres (X, Y, Z) |
| --- | --- | ---: | --- |
| Lower | (0, 0, 5.441056) | 0° | (0, −0.100, 6.561056) |
| Upper | (0, 3.000, −5.441056) | 180° | (0, 2.900, −6.561056) |

Use the actual outer tread edge as the reference. The two named escalator connectors lie 350 mm and 475 mm inboard. The transition shoulders extend 225 mm past the deck on each side.

## Reproduce

Run `node docs/verification/mall-escalator-floor-joint/check.mjs` from the repository root. The script loads the original GLBs and prints the [recorded measurements](report.json), including source hashes and the results for the two ordinary-slab configurations.

At each terminal, 341 surface probes crossed the deck, profile and floor. The largest sampled depression was 0.52 mm at the original deck bevel. The occupied profile cells cleared the transformed bounds of the escalator meshes and the floor slab. Separate probes found that the 1.20 m-wide floor-facing edge on [landing 429](../../../models/mall-escalator-landing/README.md) can sit flush with a centred 2 m slab.

These measurements describe a static gallery model. An editable production part, treatment of the side shoulders and an end-to-end passenger route remain open.
