"""Retarget the seated preset, plant the feet, and bake four independent clips."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chibi import *

SEAT = .252
THIGH_ANGLE = -82
# The grip test in the source library fits a cylinder through the four curled digits.
GRIP_CENTER = Vector((-.303460, -.010269, .520307))
GRIP_AXIS = Vector((-.41036, -.91192, 0)).normalized()
IDENTITY = Quaternion()


def smooth(x):
    return x*x*(3-2*x)


def source_pose(arm, action, frame):
    bind(arm, bpy.data.actions[action])
    bpy.context.scene.frame_set(frame)
    return {p.name: p.rotation_quaternion.copy() for p in arm.pose.bones}


def upper_basis(axis, dorsal):
    axis = axis.normalized()
    dorsal = (dorsal-axis*dorsal.dot(axis)).normalized()
    return Matrix((axis, dorsal, axis.cross(dorsal))).transposed().to_quaternion()


class Builder:
    def __init__(self):
        fresh()
        self.arm = armature(load(BODY))
        self.body = bpy.data.objects['Base_Body']
        self.bones = {p.name[len(N):]:p for p in self.arm.pose.bones}
        self.rest = {n:p.bone.matrix_local.to_quaternion() for n,p in self.bones.items()}
        self.head = {n:p.bone.head_local.copy() for n,p in self.bones.items()}
        self.feet_offset = Vector((-.00267, -.202, 0))
        self.upper = {}
        for path, samples in [
            (MOTION, [('standing','idle',0)]),
            (PRESET, [('seated','sit.001',2),('inhaled','sit.001',35)]),
            (GESTURES, [('left','hand_open_relaxed_L',0),('right','hand_open_relaxed_R',0),
                        ('grip','hand_grip_small_R',0)])
        ]:
            source_objects = load(path)
            rig = armature(source_objects)
            for label,action,frame in samples:
                values = source_pose(rig, action, frame)
                # Map local source quaternions through each joint's world bind axes.
                self.upper[label] = {}
                for n in self.bones:
                    src = rig.data.bones[N+n].matrix_local.to_quaternion()
                    q = src @ values[N+n] @ src.inverted()
                    self.upper[label][n] = q.normalized()
            for ob in source_objects:
                bpy.data.objects.remove(ob, do_unlink=True)
        for action in list(bpy.data.actions):
            bpy.data.actions.remove(action)
        self.q_abs = {}
        self.grip_world = upper_basis(Z, Vector((-.99,.12,0))) @ upper_basis(GRIP_AXIS,Z).inverted()

    def absolute(self, n, q):
        p = self.bones[n]
        parent = p.parent
        q_parent = self.q_abs.get(parent.name[len(N):], IDENTITY) if parent else IDENTITY
        basis = self.rest[n]
        p.rotation_quaternion = (basis.inverted() @ q_parent.inverted() @ q @ basis).normalized()
        self.q_abs[n] = q

    def relative(self, n, q):
        p = self.bones[n]
        q_parent = self.q_abs.get(p.parent.name[len(N):], IDENTITY) if p.parent else IDENTITY
        self.absolute(n, q_parent @ q)

    def pose(self, seated, effort, breath, head_turn, hold=False):
        self.q_abs.clear()
        h = self.head
        self.absolute('Hips', IDENTITY)
        offset = Vector((0,0,0)) if hold else self.feet_offset
        # Keep the fitted shin geometry fixed across all three chair clips.
        # Both sole contact patches then stay stationary during hip travel.
        thigh = rot(X, THIGH_ANGLE*seated)
        scale = 1 if hold else 1+self.stretch
        targets = {}
        for side in ['Left','Right']:
            leg = side+'Leg'
            foot = side+'Foot'
            basis = self.rest[leg].to_matrix()
            S = basis @ Matrix.Diagonal(Vector((1,scale,1))) @ basis.transposed()
            shin = h[foot]-h[leg]
            vertical = Vector((0,0,-1))
            R = IDENTITY if hold else (S @ shin).rotation_difference(vertical)
            A = R.to_matrix() @ S
            pivot = Vector((h[foot].x, h[foot].y, 0))
            knee = pivot + A @ (h[leg]-pivot) + offset
            if not hold:
                knee.z += self.lift[side]
            targets[side] = (knee, R, A)
        left, right = targets['Left'][0], targets['Right'][0]
        up = (h['LeftUpLeg']+h['RightUpLeg'])*.5
        mid = (h['LeftLeg']+h['RightLeg'])*.5
        shift = (left+right)*.5 - (up+thigh @ (mid-up))
        self.bones['Hips'].location = self.rest['Hips'].inverted() @ shift
        for side in ['Left','Right']:
            upper, leg, foot = side+'UpLeg', side+'Leg', side+'Foot'
            knee, R, A = targets[side]
            goal = knee-(h[upper]+shift)
            segment = h[leg]-h[upper]
            # Both knee centres remain fixed; joint-local translation absorbs the
            # small left/right asymmetry of the bind axes.
            q = thigh
            self.absolute(upper,q)
            self.absolute(leg,R)
            self.bones[leg].scale = (1,scale,1)
            self.bones[leg].location = self.rest[leg].inverted() @ (q.inverted() @ goal - segment)
            # Flat forefoot: the transformed sole normal must be vertical.
            # The translation is relative to the joint head, after inherited scale.
            correction = Z.rotation_difference((A.transposed() @ Z).normalized())
            self.relative(foot,correction)
            ankle = knee + A @ (h[foot]-h[leg])
            sole_scale = (A @ correction.to_matrix() @ Z).z
            dz = sole_scale*h[foot].z-ankle.z
            self.bones[foot].location = (A @ self.rest[foot].to_matrix()).inverted() @ (Z*dz)
        for n, tilt in [('Spine',6),('Spine1',6),('Spine2',4),('Neck',-5),('Head',-4)]:
            source = self.upper['seated'][n].slerp(self.upper['inhaled'][n],(breath+1)*.42)
            q = IDENTITY.slerp(source,.40*seated)
            breathe_angle = breath*({'Spine':.85,'Spine1':.72,'Spine2':.55,'Neck':-.6,'Head':-.7}[n])
            self.relative(n, rot(X,tilt*effort+breathe_angle) @ rot(Z,head_turn*(1.65 if n=='Head' else .18)) @ q)

        for side, sign in [('Right',-1),('Left',1)]:
            shoulder, arm, fore, hand = [side+s for s in ['Shoulder','Arm','ForeArm','Hand']]
            self.relative(shoulder, IDENTITY.slerp(self.upper['seated'][shoulder],.27*seated))
            # The relaxed standing silhouette comes from the existing idle clip.
            arm0 = self.upper['standing'][arm]
            fore0 = arm0 @ self.upper['standing'][fore]
            hand0 = fore0 @ self.upper['standing'][hand]
            fore0 = fore0.slerp(rot(Z,-sign*40) @ rot(Y,sign*53),.38)
            # Keep the long chibi fingers beside the leg in the standing pose.
            hand0 = fore0 @ rot(X,-sign*12)
            upper_dir = Vector((sign*.42,-.23,-.88))
            fore_dir = Vector((-sign*.26,-.72,-.64))
            uc = (h[fore]-h[arm]).rotation_difference(upper_dir)
            fc = (h[hand]-h[fore]).rotation_difference(fore_dir)
            hc = rot(Z,-sign*69) @ rot(Y,sign*13)
            w = seated
            if hold and side=='Right':
                uc = (h[fore]-h[arm]).rotation_difference(Vector((-.49,-.46,-.74)))
                fc = (h[hand]-h[fore]).rotation_difference(Vector((.25,-.77,.58)))
                hc = self.grip_world
                # Distribute pronation up the forearm so the wrist stays full
                # while preserving the cup axis and all fingertip contacts.
                shaft = h[hand]-h[fore]
                aimed = fc @ shaft
                matched = (hc @ shaft).rotation_difference(aimed) @ hc
                fc = fc.slerp(matched,.87)
                humerus = h[fore]-h[arm]
                matched = (fc @ humerus).rotation_difference(uc @ humerus) @ fc
                uc = uc.slerp(matched,.40)
                w = 1
            elif hold:
                w = 0
            motion = rot(X,(-8 if side=='Right' else -6)*effort+.70*breath)
            self.absolute(arm, motion @ arm0.slerp(uc,w))
            self.absolute(fore, motion @ fore0.slerp(fc,w))
            self.absolute(hand, motion @ hand0.slerp(hc,w))
            label = 'grip' if hold and side=='Right' else side.lower()
            for n in self.bones:
                if n.startswith(hand) and n!=hand:
                    self.relative(n,self.upper[label][n])
        bpy.context.view_layer.update()

    def calibrate(self):
        # Use the underside above the flat seat footprint, including buttocks
        # and the load-bearing portions of both thighs.
        self.lift = dict(Left=0,Right=0)
        rest = coords(self.body)
        supports = {side:(sg*rest[:,0]>0)&(rest[:,2]<.002)&(rest[:,1]>.02)
                    for side,sg in [('Left',1),('Right',-1)]}
        def plant():
            # Rear skin blends calf and foot. Ground each heel independently,
            # holding the forefoot transform fixed on the floor plane.
            for _ in range(3):
                self.pose(1,0,0,0)
                base=coords(self.body)
                for side in supports:self.lift[side]+=.0002
                self.pose(1,0,0,0)
                test=coords(self.body)
                for side,mask in supports.items():
                    h0,h1=base[mask,2].min(),test[mask,2].min()
                    self.lift[side]-=.0002+.0002*h0/(h1-h0)
        lo,hi = 0,.82
        for _ in range(17):
            self.stretch = (lo+hi)/2
            plant()
            self.pose(1,0,0,0)
            pts=coords(self.body)
            # Feet and shins are identified in bind space so a heel beneath the
            # cushion cannot be mistaken for its load-bearing contact.
            mask=(rest[:,2]>.21)&(rest[:,2]<.41)&(abs(pts[:,1])<.099)&(abs(pts[:,0])<.145)
            bottom=pts[mask,2].min()
            if bottom<SEAT+.00020:lo=self.stretch
            else:hi=self.stretch
        print('SEAT FIT',self.stretch,bottom,flush=True)

    def build(self):
        self.calibrate()
        for clip, count in CLIPS.items():
            bind(self.arm,None)
            action = bpy.data.actions.new(clip)
            action.use_fake_user = True
            self.arm.animation_data.action = action
            previous = {}
            for f in range(count+1):
                t = f/count
                if clip=='sit_down':
                    s = smooth(t); e = math.sin(math.pi*t)**2
                elif clip=='stand_up':
                    s = 1-smooth(t); e = math.sin(math.pi*t)**2*1.28
                else:
                    s = float(clip=='sit_idle'); e = 0
                loop = clip in ('sit_idle','hold_item')
                breath = math.sin(2*math.pi*t) if loop and f<count else 0
                turn = (.68*math.sin(2*math.pi*t)+.32*math.sin(4*math.pi*t)) if loop and f<count else 0
                self.pose(s,e,breath,turn,clip=='hold_item')
                for name,p in self.bones.items():
                    q = p.rotation_quaternion.copy()
                    if name in previous: q.make_compatible(previous[name])
                    previous[name] = q
                    p.rotation_quaternion = q
                    p.keyframe_insert('rotation_quaternion',frame=f,group=p.name)
                    if name in ['Hips','LeftLeg','RightLeg','LeftFoot','RightFoot']:
                        p.keyframe_insert('location',frame=f,group=p.name)
                    if name in ['LeftLeg','RightLeg']:
                        p.keyframe_insert('scale',frame=f,group=p.name)
            bag = action.layers[0].strips[0].channelbag(self.arm.animation_data.action_slot)
            for curve in bag.fcurves:
                for k in curve.keyframe_points: k.interpolation='LINEAR'
        bind(self.arm,None)
        export(self.arm,'actions.glb',export_animations=True,export_animation_mode='ACTIONS',
               export_anim_single_armature=True,export_optimize_animation_size=False,
               export_force_sampling=False,export_bake_animation=False,export_frame_range=False,
               export_rest_position_armature=True,export_leaf_bone=False,export_def_bones=False,
               export_anim_slide_to_zero=True)
        # Bone-local mount is defined relative to the joint head, not Blender's
        # bone-parent tail convention. The engine mount also accounts for the
        # Y-up conversion applied to the independently exported cup.
        # Choose local +Z along the cylinder, local +X along bind-hand dorsal.
        mount = Matrix.LocRotScale(GRIP_CENTER, Matrix((Z,GRIP_AXIS.cross(Z),GRIP_AXIS)).transposed().to_quaternion(), Vector((1,1,1)))
        local = self.bones['RightHand'].bone.matrix_local.inverted() @ mount
        # Compute the engine attachment separately from the exact glTF node rest matrices.
        root_to_gltf = rot(X,-90).to_matrix().to_4x4()
        def node_matrix(nodes,i):
            n = nodes[i]
            t = Vector(n.get('translation',(0,0,0)))
            x,y,z,w = n.get('rotation',(0,0,0,1))
            m = Matrix.LocRotScale(t,Quaternion((w,x,y,z)),Vector(n.get('scale',(1,1,1))))
            par = next((j for j,node in enumerate(nodes) if i in node.get('children',[])),None)
            return node_matrix(nodes,par) @ m if par is not None else m
        nodes = glb(BODY)[0]['nodes']
        i = next(i for i,n in enumerate(nodes) if n['name']==N+'RightHand')
        gltf = node_matrix(nodes,i).inverted() @ root_to_gltf @ mount @ root_to_gltf.inverted()
        def transform(m):
            t,q,_=m.decompose()
            return dict(translation_m=list(t),quaternion_xyzw=[q.x,q.y,q.z,q.w])
        (OUT/'attachment.json').write_text(json.dumps(dict(bone=N+'RightHand',
                blender_pose_bone_head_local=transform(local),gltf_joint_local=transform(gltf),
                composition='world_matrix_of_joint @ local_matrix_of_prop',seat_top_m=SEAT,
                shin_axial_scale_at_contact=1+self.stretch),indent=2)+'\n')


if __name__=='__main__':
    Builder().build()
