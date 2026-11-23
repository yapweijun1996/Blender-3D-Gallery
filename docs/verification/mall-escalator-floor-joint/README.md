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

## Installed Blender part

The [editable terminal part](../../../models/mall-escalator-floor-transition-2m/README.md) uses the profile above. The [local assembly](../../../mall-modules-preview/README.md#escalator-landings) installs one at each end of the original escalator. A centre slab meets the back of each profile. Two flank slabs reach the tread-edge plane and meet the profile along its full 120 mm sides.

On each side, the shoulder extends 225 mm past the tread. The first 5 mm continue the 15 mm top skin over the beam recess. The outer 220 mm have a closed, 100 mm-deep front face. The front terminates at the open escalator well. The side meets the flanking slab.

On all three detail levels, 341 surface probes per end cross the deck, transition and centre tile. The deepest sampled depression was 0.52 mm at the original tread bevel. The 48 paired side-face probes per end also distinguish the flush vertical faces from the flank slab's 2 mm underside bevel. One millimetre above the underside, that bevel leaves a 1 mm horizontal gap.

Run `node --test tests/mall-escalator-floor-transition.test.mjs` to check the three exported detail levels on both landings, including the exposed fronts, the slab contacts and the beam clearances. The tests also displace a flank slab to reproduce a broken side joint. The static installation and a passenger's journey between storeys have separate acceptance criteria. The passenger route remains open.
