# Escalator 004 passenger clearance and tread support

The original GJH mall visitor rides the original escalator from machine time **0.30 to 18.10 seconds**, rising from 0 to 3 m. At both ends of this short inspection the visitor is standing on a flat moving tread. A [26.24 s floor-to-floor journey](journey.md) includes the approach, boarding, exit and departure. The [original gait study](transfers.md) records the unsupported frames that led to the authored transfers.

## How much room does the rider have?

The clearance study cuts the default-pose escalator at 13 longitudinal stations. At each station, two downward rays at X = 0 and +0.020 m find the highest comb or tread surface. Horizontal rays between the actual paired faces then measure the passage through the 1.80 m corridor body height. The smallest sampled opening is **1.015 m** between the lower belt seams at Z = 4.601603 m, Y = 0.937996 m. On the incline, the skirts are 1.065 m apart, the glass faces 1.080 m, and the handrails 1.020 m.

Each native visitor clip was sampled at 121 evenly spaced phases including the loop boundary. With the rider centred and facing uphill along −Z (yaw π), the width across visible idle vertices is 0.678935 m, leaving **168.03 mm per side** against the seam planes. The walk clip spans 0.670078 m at that heading. The corridor's 1.120 m movement circle overlaps each seam by 52.5 mm. Shifting the idle rider 0.330 m sideways puts a polo vertex inside the right glass. Turning the centred walking pose to −1.852364 radians also puts a vertex inside the glass.

## How are the shoes supported?

All native machine clips run together. The rider's root on the travelling `STEP_00` is at local (0, 0.200, 0.240) m. The two shoe meshes have a combined footprint 0.423582 m wide and 0.302559 m deep. Their lowest vertices and bounding boxes stayed fixed over 121 idle phases. Each tread has 25 steel crests, 23 mm wide, with 17 mm grooves.

The checker samples the 46.416668 s cycle at **120 Hz**. It keeps upright tread poses whose exposed depth fits the entire shoe footprint between the two fixed combs, accounting for the higher adjacent step. For each retained pose, two downward rays must meet the assigned tread first, one under each shoe's lowest vertex. The height tolerance is 1 µm. The lower and upper flats use the same 1 µm elevation tolerance.

| Native interval | First sample (s) | Last sample (s) |
| --- | ---: | ---: |
| All consecutive supported samples | 0.166667 | 18.358333 |
| Lower flat | 0.166667 | 2.458333 |
| Upper flat | 16.041667 | 18.358333 |

All **2,184 consecutive poses** passed, covering 4,368 sole contacts. The maximum height error was 0.085 µm. The smallest margins were 21.04 mm ahead of the toes on the exposed tread, 22.81 mm behind the heels and 8.89 mm from a sole contact point to the nearest crest edge. The footprint stays at least 66.76 mm from the fixed combs in the public ride. That distance falls to 0.115 mm at the limits of the full sampled interval.

Three controls expose incorrect placements. Centring the shoes on the geometric tread projects the toes under the higher tread's nose at 1,186 samples. Shifting the stance sideways by 20 mm puts both sole contacts over grooves 20 mm deep. At machine time 30 s the assigned step is inverted on its return.

## Reproduce

From the repository root with Node 24 and the project dependencies installed, run the following checks. The first compares the freshly measured geometry and source hashes with the [numeric report](report.json). The second exercises the preview controller against the same assets.

```sh
node docs/verification/mall-escalator-passenger/check.mjs | diff - docs/verification/mall-escalator-passenger/report.json
node --test tests/mall-escalator-passenger.test.mjs
```
