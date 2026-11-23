"""Frame-local pose corrections. All transforms use the master armature space."""
import math
from collections import Counter
from mathutils import Quaternion, Vector
import bpy


SIDES = ('Left','Right')


def bone(arm, name):
    return arm.pose.bones['mixamorig:'+name]


def parent_frame(pb):
    return pb.parent.matrix @ pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local


def turn(pb, axis, degrees):
    base = parent_frame(pb).to_quaternion()
    local = base.inverted() @ Quaternion(axis, math.radians(degrees)) @ base
    pb.rotation_quaternion = (local @ pb.rotation_quaternion).normalized()


def slide(pb, movement):
    pb.location += parent_frame(pb).to_3x3().inverted() @ movement


def arms(arm, amounts):
    elbows = []
    for side,amount in zip(SIDES,amounts):
        if not amount:
            continue
        upper,fore,wrist = [bone(arm,side+p) for p in ('Arm','ForeArm','Hand')]
        outward = Vector((1 if side=='Left' else -1,0,0))
        # When a bent arm swings forward its useful clearance axis also turns.
        hanging_axis = Vector((0,-outward.x,0))
        reach = (wrist.head - upper.head).normalized()
        axis = reach.cross(outward)
        axis = (axis*.55 + hanging_axis*.45).normalized()
        fore_axis = (wrist.head-fore.head).normalized().cross(outward)
        slide(upper, outward * min(.010, amount*.00050))
        turn(upper,axis,amount*.76)
        if fore_axis.length > .15:
            elbows.append((fore,fore_axis.normalized(),amount*.20))
    bpy.context.view_layer.update()
    for fore,axis,amount in elbows:
        turn(fore,axis,amount)
    bpy.context.view_layer.update()


def legs(arm, amounts):
    for side,mm in zip(SIDES,amounts):
        if not mm:
            continue
        thigh,shin,foot = [bone(arm,side+p) for p in ('UpLeg','Leg','Foot')]
        upper,lower,ankle = [b.matrix.copy() for b in (thigh,shin,foot)]
        a,b,c = [m.translation for m in (upper,lower,ankle)]
        u,v = b-a,c-b
        delta=(u.normalized()+v.normalized()).normalized()*(mm*.001)
        share=.40
        anchored=.75
        # Roll the two skinning segments apart only in flexion. Part of the
        # slide is absorbed along each segment, retaining the ankle transform.
        for part,mat,old,new,origin in (
                (thigh,upper,u,u-share*anchored*delta,a-share*(1-anchored)*delta),
                (shin,lower,v,v-(1-share)*anchored*delta,b+(1-share)*delta)):
            rot=old.rotation_difference(new)
            basis=(rot.to_matrix() @ mat.to_3x3())*(new.length/old.length)
            corrected=basis.to_4x4()
            corrected.translation=origin
            part.matrix=corrected
            bpy.context.view_layer.update()
        foot.matrix=ankle
        bpy.context.view_layer.update()


def feet(arm, body, checker, ref_points):
    # In linear blend skinning a world translation of the foot moves each
    # influenced vertex by its total weight on the foot subtree times the shift.
    from bodycheck import posed
    points=posed(body)
    for side in SIDES:
        ids=checker.feet[side]
        goal=ref_points[ids,2].min()
        error=goal-points[ids,2].min()
        if abs(error)<.00001:
            continue
        shift=max((goal-points[ids,2])/checker.foot_weights[side])
        slide(bone(arm,side+'Foot'),Vector((0,0,float(shift))))
    bpy.context.view_layer.update()


def hand_targets(arm):
    return [(bone(arm,s+'Hand').head+bone(arm,s+'HandMiddle1').head)*.5 for s in SIDES]


def relax_elbows(arm, targets, amounts):
    for side,target,amount,current in zip(SIDES,targets,amounts,hand_targets(arm)):
        if not amount:
            continue
        elbow=bone(arm,side+'ForeArm')
        before=(current-elbow.head).normalized()
        after=(target-elbow.head).normalized()
        axis=before.cross(after)
        if axis.length>1.e-5:
            turn(elbow,axis.normalized(),min(30,math.degrees(before.angle(after)))*amount)
    bpy.context.view_layer.update()


def kind(name):
    if 'Hand' in name or 'Arm' in name or 'Shoulder' in name:
        return 'Left' if name.startswith('Left') else 'Right'
    return 'body'


def arm_contact(a,b,side):
    ka,kb=kind(a),kind(b)
    if {ka,kb}=={side,'body'}:
        return True
    return ka==kb==side and a in (side+'Shoulder',side+'Arm') and b in (side+'Shoulder',side+'Arm')


def knee_contact(a,b,side):
    return {a,b} == {side+'Leg',side+'UpLeg'}


def counts(checker,points,test):
    pairs,_=checker.overlap(points)
    return [sum(test(checker.regions[a],checker.regions[b],s) for a,b in pairs) for s in SIDES]
