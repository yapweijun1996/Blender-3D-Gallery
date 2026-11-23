# Remaining clearance failures

## Body self-overlap by bone pair

The depth is the least separating translation of an intersecting triangle pair. Counts are summed over samples.

| Clip | Zone | Triangle pairs | Max depth (mm) | Frame at 24 fps |
| --- | --- | ---: | ---: | ---: |
| walk | Hips / Hips | 104 | 0.944713 | 9.4 |
| walk | LeftLeg / LeftUpLeg | 93 | 0.829586 | 41.4 |
| walk | RightLeg / RightUpLeg | 60 | 0.337231 | 54 |
| walk | Head / Head | 209 | 0.017036 | 7 |
| walk | LeftToeBase / LeftToeBase | 900 | 0.013129 | 9 |
| run | LeftFoot / LeftLeg | 233 | 1.842462 | 3.2 |
| run | LeftLeg / LeftUpLeg | 258 | 1.764486 | 1 |
| run | RightUpLeg / RightUpLeg | 369 | 1.544613 | 26.8 |
| run | RightFoot / RightLeg | 112 | 1.479140 | 0 |
| run | Hips / RightUpLeg | 154 | 1.362749 | 12 |
| run | Hips / LeftUpLeg | 246 | 1.101470 | 3 |
| run | LeftFoot / LeftFoot | 36 | 0.858829 | 2 |
| run | RightLeg / RightUpLeg | 100 | 0.762211 | 9.5 |
| run | RightFoot / RightFoot | 33 | 0.659953 | 0.5 |
| run | RightArm / RightForeArm | 2 | 0.563740 | 4 |
| run | LeftUpLeg / LeftUpLeg | 339 | 0.556030 | 18.5 |
| run | Head / Head | 114 | 0.073628 | 27 |
| run | LeftToeBase / LeftToeBase | 484 | 0.005776 | 14 |
| jump | Head / Head | 39 | 0.003711 | 9 |
| jump | LeftToeBase / LeftToeBase | 117 | 0.000006 | 8.5 |
| nod | Head / Head | 36 | 0.007323 | 8 |
| dance | Head / Head | 98 | 0.013228 | 40 |
| dance | LeftToeBase / LeftToeBase | 425 | 0.000016 | 43.6 |
| sit_down | Hips / LeftUpLeg | 1708 | 3.550143 | 26.4 |
| sit_down | Hips / RightUpLeg | 1518 | 3.246510 | 26 |
| sit_down | RightUpLeg / RightUpLeg | 243 | 1.043185 | 28.8 |
| sit_down | LeftUpLeg / LeftUpLeg | 163 | 0.719293 | 28.8 |
| sit_down | Head / Head | 84 | 0.006611 | 17.2 |
| sit_down | LeftToeBase / LeftToeBase | 241 | 0.000004 | 19.2 |
| sit_idle | Hips / LeftUpLeg | 17478 | 2.458847 | 56.8 |
| sit_idle | Hips / RightUpLeg | 14528 | 2.432835 | 52.8 |
| sit_idle | RightUpLeg / RightUpLeg | 3679 | 1.139755 | 18.4 |
| sit_idle | LeftUpLeg / LeftUpLeg | 3359 | 0.823815 | 17.6 |
| sit_idle | Head / Head | 183 | 0.010330 | 14.5 |
| sit_idle | LeftToeBase / LeftToeBase | 159 | 0.000004 | 47.5 |
| stand_up | Hips / LeftUpLeg | 1390 | 3.603852 | 2 |
| stand_up | Hips / RightUpLeg | 1235 | 3.319175 | 2.4 |
| stand_up | RightUpLeg / RightUpLeg | 195 | 1.043189 | 0 |
| stand_up | LeftUpLeg / LeftUpLeg | 124 | 0.719293 | 0 |
| stand_up | Head / Head | 72 | 0.008677 | 10.4 |
| stand_up | LeftToeBase / LeftToeBase | 155 | 0.000004 | 8 |
| hold_item | RightArm / RightForeArm | 5211 | 4.064592 | 10 |
| hold_item | LeftToeBase / LeftToeBase | 386 | 0.000002 | 0 |
| hold_box | RightForeArm / RightHand | 2061 | 1.254163 | 12 |
| hold_box | LeftForeArm / LeftHand | 842 | 0.448833 | 12 |
| take_item | RightArm / RightForeArm | 4023 | 6.694302 | 4.8 |

## Module clearance by clip

A negative signed distance is penetration depth with its sign retained. A positive distance below 0.5000 mm also fails the clearance gate. Triangle depth uses the same pairwise measure as the body audit. The body-joint label comes from the strongest pose influence on the contacted triangle.

| Module | Clip | Module zone · body joint | Frame at 24 fps | Peak inside verts | Peak pairs | Min signed (mm) | Peak triangle depth (mm) · zone · frame |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| tshirt | idle | Right arm · mixamorig:RightArm | 66 | 0 | 44 | 0.1534 | 1.4129 · torso · f81.5 |
| tshirt | walk | torso · mixamorig:Hips | 36 | 12 | 42 | -4.6015 | 1.5073 · torso · f48 |
| tshirt | run | Right arm · mixamorig:RightArm | 18 | 9 | 33 | -2.2482 | 2.1219 · Right arm · f18 |
| tshirt | wave | torso · mixamorig:LeftForeArm | 19 | 22 | 71 | -2.3008 | 1.6868 · torso · f33 |
| tshirt | jump | torso · mixamorig:RightArm | 8 | 0 | 46 | 0.1189 | 1.8371 · torso · f8.5 |
| tshirt | nod | torso · mixamorig:Head | 17 | 7 | 44 | -0.0986 | 1.1693 · torso · f1.5 |
| tshirt | dance | Right arm · mixamorig:RightArm | 8 | 0 | 16 | 0.7450 | 0.7089 · torso · f13.5 |
| tshirt | sit_down | torso · mixamorig:RightUpLeg | 26 | 1 | 0 | -0.4758 | — |
| tshirt | sit_idle | torso · mixamorig:RightUpLeg | 39.6 | 1 | 0 | -0.7769 | — |
| tshirt | stand_up | torso · mixamorig:RightUpLeg | 2 | 1 | 5 | -0.3163 | 0.1330 · torso · f8.8 |
| tshirt | hold_box | Left arm · mixamorig:LeftArm | 36 | 0 | 0 | 0.3335 | — |
| dress | idle | Right arm · mixamorig:RightArm | 66 | 0 | 0 | 0.3638 | — |
| dress | walk | Left leg · mixamorig:LeftHandThumb3 | 18 | 4 | 38 | -4.5832 | 2.8262 · Left leg · f17 |
| dress | run | Left leg · mixamorig:LeftUpLeg | 4.5 | 45 | 262 | -6.9323 | 4.7542 · torso · f20 |
| dress | jump | Right arm · mixamorig:RightArm | 8 | 1 | 11 | -0.0352 | 0.5666 · Right arm · f8 |
| dress | dance | Left leg · mixamorig:LeftUpLeg | 40 | 2 | 14 | -0.7463 | 0.7463 · Left leg · f40 |
| dress | sit_down | torso · mixamorig:Hips | 22 | 2 | 0 | -1.4097 | — |
| dress | stand_up | torso · mixamorig:Hips | 6.4 | 1 | 0 | -1.5731 | — |
| jeans | walk | torso · mixamorig:Hips | 34.5 | 13 | 30 | -7.8794 | 2.7018 · Left leg · f18 |
| jeans | run | Right leg · mixamorig:RightLeg | 9 | 66 | 193 | -3.9960 | 2.8919 · Left leg · f1 |
| jeans | jump | Left leg · mixamorig:LeftLeg | 9 | 1 | 6 | -0.2314 | 0.2314 · Left leg · f9 |
| jeans | sit_down | Left leg · mixamorig:LeftUpLeg | 21.2 | 11 | 61 | -1.6340 | 1.0885 · Right leg · f28.8 |
| jeans | sit_idle | Right leg · mixamorig:RightUpLeg | 59.2 | 7 | 63 | -1.0885 | 1.1056 · torso · f53.6 |
| jeans | stand_up | Right leg · mixamorig:Hips | 8 | 11 | 61 | -3.2147 | 1.0884 · Right leg · f0 |

## Every module zone below the signed-distance threshold

| Module | Clip | Module zone · body joint | Frame at 24 fps | Min signed (mm) |
| --- | --- | --- | ---: | ---: |
| tshirt | idle | Left arm · mixamorig:LeftArm | 80 | 0.2205 |
| tshirt | idle | torso · mixamorig:RightArm | 66 | 0.2812 |
| tshirt | idle | Right arm · mixamorig:RightArm | 66 | 0.1534 |
| tshirt | walk | Right arm · mixamorig:Spine1 | 21 | -1.2249 |
| tshirt | walk | torso · mixamorig:Hips | 36 | -4.6015 |
| tshirt | run | Right arm · mixamorig:RightArm | 18 | -2.2482 |
| tshirt | run | Left arm · mixamorig:LeftArm | 10 | 0.0558 |
| tshirt | run | torso · mixamorig:Hips | 12 | -1.7526 |
| tshirt | wave | Left arm · mixamorig:LeftArm | 10.5 | 0.2737 |
| tshirt | wave | torso · mixamorig:LeftForeArm | 19 | -2.3008 |
| tshirt | jump | Right arm · mixamorig:RightArm | 8 | 0.1223 |
| tshirt | jump | torso · mixamorig:RightArm | 8 | 0.1189 |
| tshirt | jump | Left arm · mixamorig:LeftArm | 9 | 0.4513 |
| tshirt | nod | Left arm · mixamorig:LeftArm | 1.5 | 0.2798 |
| tshirt | nod | torso · mixamorig:Head | 17 | -0.0986 |
| tshirt | sit_down | torso · mixamorig:RightUpLeg | 26 | -0.4758 |
| tshirt | sit_idle | torso · mixamorig:RightUpLeg | 39.6 | -0.7769 |
| tshirt | stand_up | torso · mixamorig:RightUpLeg | 2 | -0.3163 |
| tshirt | hold_box | Left arm · mixamorig:LeftArm | 36 | 0.3335 |
| dress | idle | Right arm · mixamorig:RightArm | 66 | 0.3638 |
| dress | walk | torso · mixamorig:Hips | 39 | -1.0845 |
| dress | walk | Left leg · mixamorig:LeftHandThumb3 | 18 | -4.5832 |
| dress | walk | Right arm · mixamorig:Spine1 | 20 | 0.0589 |
| dress | run | Left leg · mixamorig:LeftUpLeg | 4.5 | -6.9323 |
| dress | run | Right leg · mixamorig:RightLeg | 9 | -2.8705 |
| dress | run | torso · mixamorig:LeftUpLeg | 4 | -0.6526 |
| dress | run | Left arm · mixamorig:LeftArm | 9.5 | -0.1591 |
| dress | jump | torso · mixamorig:Hips | 6 | 0.4861 |
| dress | jump | Right arm · mixamorig:RightArm | 8 | -0.0352 |
| dress | dance | Left leg · mixamorig:LeftUpLeg | 40 | -0.7463 |
| dress | dance | Right arm · mixamorig:Spine1 | 8 | 0.4553 |
| dress | sit_down | torso · mixamorig:Hips | 22 | -1.4097 |
| dress | sit_down | Left leg · mixamorig:Hips | 16.8 | -0.4959 |
| dress | stand_up | torso · mixamorig:Hips | 6.4 | -1.5731 |
| jeans | walk | torso · mixamorig:Hips | 34.5 | -7.8794 |
| jeans | walk | Left leg · mixamorig:LeftLeg | 41 | -1.0960 |
| jeans | walk | Right leg · mixamorig:RightUpLeg | 22 | -0.7403 |
| jeans | run | Left leg · mixamorig:LeftLeg | 1 | -3.5062 |
| jeans | run | Right foot · mixamorig:RightLeg | 0 | 0.2743 |
| jeans | run | torso · mixamorig:LeftUpLeg | 4 | -1.5675 |
| jeans | run | Left foot · mixamorig:LeftLeg | 2 | -1.9519 |
| jeans | run | Right leg · mixamorig:RightLeg | 9 | -3.9960 |
| jeans | jump | Left leg · mixamorig:LeftLeg | 9 | -0.2314 |
| jeans | sit_down | torso · mixamorig:Hips | 20.4 | -1.2217 |
| jeans | sit_down | Right leg · mixamorig:RightUpLeg | 24 | -1.2408 |
| jeans | sit_down | Left leg · mixamorig:LeftUpLeg | 21.2 | -1.6340 |
| jeans | sit_idle | torso · mixamorig:Hips | 54.4 | -0.3399 |
| jeans | sit_idle | Left leg · mixamorig:LeftLeg | 1.6 | -1.0047 |
| jeans | sit_idle | Right leg · mixamorig:RightUpLeg | 59.2 | -1.0885 |
| jeans | stand_up | torso · mixamorig:Hips | 8.4 | -2.0312 |
| jeans | stand_up | Left leg · mixamorig:Hips | 5.6 | -1.6163 |
| jeans | stand_up | Right leg · mixamorig:Hips | 8 | -3.2147 |
