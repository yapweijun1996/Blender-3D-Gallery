"""Pose keys in Blender world-axis directions, relative to the binding pose.

Angles are degrees (X pitch, Y roll, Z yaw). Each joint inherits its parent's
rotation as usual. A pose's height is the distance from its lowest vertex to
the floor at that key, in metres.
"""


def pose(lift=0, **rotations):
    return rotations, lift


def arms(opening, bend, swing=0):
    return dict(LeftArm=(swing, opening, 0), RightArm=(-swing, -opening, 0),
                LeftForeArm=(0, 0, -bend), RightForeArm=(0, 0, bend))


def wave(elbow, wrist, lean=0):
    return pose(Spine1=(0, lean, 0), Head=(0, -lean, -3),
                LeftArm=(0, 64, 0), LeftForeArm=(0, 0, -12),
                RightArm=(-15, 6, 14), RightForeArm=(0, elbow, 31),
                RightHand=(0, wrist, 0))


def jump(thigh, knee, ankle, opening, pitch, lift=0):
    return pose(lift, Hips=(pitch * .45, 0, 0), Spine=(pitch * .55, 0, 0),
                Neck=(-pitch * .35, 0, 0), Head=(-pitch * .4, 0, 0),
                LeftUpLeg=(thigh, 0, 0), RightUpLeg=(thigh, 0, 0),
                LeftLeg=(knee, 0, 0), RightLeg=(knee, 0, 0),
                LeftFoot=(ankle, 0, 0), RightFoot=(ankle, 0, 0),
                **arms(opening, 18, pitch))


def dance(side, dip=0):
    return pose(Hips=(0, 5 * side, -5 * side),
                Spine=(0, -8 * side, 0), Spine2=(0, -4 * side, 14 * side),
                Head=(0, 5 * side, -7 * side),
                LeftArm=(7 * side, 44 - 13 * side, 0),
                RightArm=(-7 * side, -44 - 13 * side, 0),
                LeftForeArm=(0, -20 + 12 * side, -32 - 15 * side),
                RightForeArm=(0, 20 + 12 * side, 32 - 15 * side),
                LeftUpLeg=(-7 - dip, -8, 0), RightUpLeg=(-7 - dip, 8, 0),
                LeftLeg=(13 + 2 * dip, 0, 0), RightLeg=(13 + 2 * dip, 0, 0),
                LeftFoot=(-6 - dip, 8, 0), RightFoot=(-6 - dip, -8, 0))


def run_stride(side, front_leg, back_leg, arm_swing, lift):
    hips = 6
    rotations = dict(Hips=(hips, 0, -5 * side), Spine=(8, 0, 0),
                     Spine2=(0, 0, 12 * side), Neck=(-6, 0, 0), Head=(-5, 0, 0),
                     **arms(65, 55, side * arm_swing))
    legs = (front_leg, back_leg) if side == 1 else (back_leg, front_leg)
    for name, (thigh, knee, foot) in zip(("Left", "Right"), legs):
        rotations[name + "UpLeg"] = (thigh - hips, 0, 0)
        rotations[name + "Leg"] = (knee, 0, 0)
        rotations[name + "Foot"] = (foot, 0, 0)
    return pose(lift, **rotations)


def cycle(duration, keys):
    return [*keys, (duration, keys[0][1])]


def motion_keys():
    neutral = pose(**arms(64, 12))
    idle = cycle(88, [
        (0, neutral),
        (22, pose(Spine=(-2, 1.5, 0), Spine2=(-2, 1, 0),
                  Neck=(1, -1, 0), Head=(1, -1, 2), **arms(63, 14))),
        (44, neutral),
        (66, pose(Spine=(2, -1.5, 0), Spine2=(1, -1, 0),
                  Neck=(-1, 1, 0), Head=(-1, 1, -2), **arms(65, 10))),
    ])
    greeting = cycle(64, [
        (0, neutral), (12, wave(53, 0, 2)), (19, wave(63, 9, 3)),
        (26, wave(42, -13, 3)), (33, wave(63, 9, 3)),
        (40, wave(42, -13, 2)), (48, wave(53, 0, 1)), (60, neutral),
    ])
    nod = cycle(56, [
        (0, neutral), (8, pose(Head=(-7, 0, 0), **arms(64, 12))),
        (17, pose(Spine2=(3, 0, 0), Neck=(7, 0, 0), Head=(15, 0, 0), **arms(64, 12))),
        (26, pose(Neck=(-2, 0, 0), Head=(-5, 0, 0), **arms(64, 12))),
        (34, pose(Spine2=(2, 0, 0), Neck=(5, 0, 0), Head=(11, 0, 0), **arms(64, 12))),
        (45, neutral),
    ])
    hop = cycle(50, [
        (0, neutral), (9, jump(-29, 53, -24, 67, 13)),
        (13, jump(-8, 13, 3, 30, 4)),
        (19, jump(-18, 29, 9, 14, 5, .19)),
        (23, jump(-13, 23, 6, 23, 5, .22)),
        (29, jump(-8, 13, -4, 41, 4, .12)),
        (34, jump(-12, 18, -6, 52, 5)),
        (38, jump(-26, 44, -18, 65, 11)),
        (46, neutral),
    ])
    groove = cycle(64, [
        (0, dance(0, 5)), (8, dance(1)), (16, dance(1, 4)), (24, dance(.6)),
        (32, dance(0, 5)), (40, dance(-1)), (48, dance(-1, 4)), (56, dance(-.6)),
    ])
    stride = [
        ((-31, 15, 11), (18, 42, -14), 27, 0),
        ((-10, 27, -14), (6, 66, -26), 14, 0),
        ((11, 19, -24), (-18, 55, -8), -8, 0),
        ((22, 28, -17), (-33, 24, 11), -26, .047),
    ]
    run_in_place = cycle(20, [
        (index * 2 + offset, run_stride(side, *phase))
        for side, offset in ((1, 0), (-1, 10))
        for index, phase in enumerate(stride)
    ])
    return dict(idle=idle, wave=greeting, nod=nod, jump=hop, dance=groove,
                run_in_place=run_in_place)
