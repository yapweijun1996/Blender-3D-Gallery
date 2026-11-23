"""Bake shoulder/elbow IK into plain local quaternions on the unchanged demo skeleton."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from mathutils import Euler

BOX_Z=.399
BOX_TILT=15
BOX_Y=-.240
BOX_X=.002
# Lateral wrist offsets are fitted on each asymmetric hand at the lower box edge.
BOX_WRIST={'Right':.1896,'Left':.1858}
BOX_HEIGHT={'Right':.0670,'Left':.063}
JAR_HOME=Vector((-.146,-.130,.523))
JAR_PICK=Vector((-.145,-.228,.523))
BAG_BAR=Vector((-.190,-.035,.378))

# Fine finger articulation. Small rotations at consecutive knuckles compensate for
# the different phalanx bind axes on the older master and the fingertip-remeshed body.
FINGER_TRIM={
    'hold_box':{'RightHandMiddle1':(7.85,.67,13.15),'RightHandMiddle2':(-5.36,6.72,3.27),
                'RightHandRing1':(8.83,4.37,-1.41),'LeftHandRing1':(10.67,-4.32,1.95),
                'RightHandPinky1':(9.26,21.45,-9.60),'LeftHandPinky1':(12.66,-21.99,1.83)},
    'hold_bag':{},
    'take_item':{'RightHandThumb1':(-65,-24.18,17.05),'RightHandThumb2':(52.1,4.8,-18.89)}}

class Builder:
    def __init__(self):
        self.sc=setup()
        self.arm=armature(load(BODY))
        self.body=next(o for o in bpy.context.scene.objects if o.name=='Base_Body')
        self.bones={p.name[len(N):]:p for p in self.arm.pose.bones}
        self.h={n:p.bone.head_local.copy() for n,p in self.bones.items()}
        self.rest={n:p.bone.matrix_local.to_quaternion() for n,p in self.bones.items()}
        self.src={}
        for file,names in ((GESTURES,('hand_open_relaxed_R','hand_open_relaxed_L')),
                           (ASTRA/'actions.glb',('hold_item',))):
            imported=load(file)
            rig=armature(imported)
            for name in names:
                bind(rig,bpy.data.actions[name])
                self.sc.frame_set(0)
                self.src[name]={p.name[len(N):]:p.rotation_quaternion.copy() for p in rig.pose.bones}
            for obj in imported: bpy.data.objects.remove(obj,do_unlink=True)
        for a in list(bpy.data.actions): bpy.data.actions.remove(a)
        self.jar_q=rot(Z,-44) @ upper_basis(Z,Vector((-.99,.12,0))) @ upper_basis(GRIP_AXIS,Z).inverted()
        self.bag_q=rot(Y,40) @ upper_basis(-Y,-X) @ upper_basis(GRIP_AXIS,Z).inverted()
        self.direction={}
        self.position={}
        self.mounts={}

    def absolute(self,n,q):
        p=self.bones[n]
        parent=p.parent.name[len(N):] if p.parent else None
        par_q=self.direction.get(parent,ID)
        self.direction[n]=q
        self.position[n]=(self.position[parent]+par_q@(self.h[n]-self.h[parent])
                          if parent else self.h[n].copy())
        p.rotation_quaternion=(self.rest[n].inverted() @ par_q.inverted() @ q @ self.rest[n]).normalized()

    def local(self,n,q):
        parent=self.bones[n].parent.name[len(N):]
        self.absolute(n,self.direction[parent] @ self.rest[n] @ q @ self.rest[n].inverted())

    def arm_to(self,side,wrist,pole,hand_q):
        a,b,c=[side+k for k in ('Arm','ForeArm','Hand')]
        shoulder=side+'Shoulder'
        root=self.position[shoulder]+self.direction[shoulder]@(self.h[a]-self.h[shoulder])
        upper=self.h[b]-self.h[a]; lower=self.h[c]-self.h[b]
        reach=wrist-root
        d=reach.length
        assert abs(upper.length-lower.length)<d<upper.length+lower.length, (side,d,tuple(wrist))
        u=reach.normalized()
        v=(pole-u*pole.dot(u)).normalized()
        along=(upper.length_squared-lower.length_squared+d*d)/(2*d)
        elbow=root+u*along+v*math.sqrt(max(0,upper.length_squared-along*along))
        def aim(segment,goal,twist,weight):
            a0=segment.rotation_difference(goal)
            matched=(twist@segment).rotation_difference(goal)@twist
            return a0.slerp(matched,weight)
        fore=aim(lower,wrist-elbow,hand_q,.80)
        self.absolute(a,aim(upper,elbow-root,fore,.42))
        self.absolute(b,fore)
        self.absolute(c,hand_q)

    def pose(self,name,f):
        t=math.tau*f/48
        wave=math.sin(t)
        pulse=math.sin(t+.32)-math.sin(.32)
        reach=smooth(f/GRIP) if f<=GRIP else 1-smooth((f-GRIP)/(48-GRIP))
        grip=1.0
        for n in self.bones:
            self.absolute(n,ID)
        for n,d in [('Spine',.50),('Spine1',.65),('Spine2',.44),('Neck',-.58),('Head',-.55)]:
            parent=self.bones[n].parent.name[len(N):]
            tilt=({'hold_box':-1.5,'hold_bag':0,'take_item':reach*1.25}[name] +.55*wave)*d
            gaze=(-3 if name=='hold_box' else 0)+(reach*4 if name=='take_item' else 0)
            self.absolute(n,self.direction[parent] @ rot(Z,-gaze if n=='Head' else 0) @ rot(X,tilt))
        for side,sgn in [('Right',-1),('Left',1)]:
            hand=side+'Hand'
            self.absolute(side+'Shoulder',self.direction['Spine2'] @ rot(Z,-sgn*(23 if name=='hold_box' else 11 if name=='take_item' and side=='Right' else 0)))
            if name=='hold_box':
                q=rot(Y,sgn*96) @ rot(Z,-sgn*12)
                wrist=Vector((BOX_X+sgn*BOX_WRIST[side],-.130,BOX_Z+.023+BOX_HEIGHT[side]+.004*wave))
                self.arm_to(side,wrist,Vector((sgn*.7,.22,-1)),q)
                # Lead with the palm along the side panel, curl the fingertips under the base.
                for digit,angles in [('Index',(3,23,20)),('Middle',(8,47,42)),('Ring',(10,48,40)),
                                     ('Pinky',(12,50,38)),('Thumb',(4,13,16))]:
                    accumulated=q.copy()
                    for i,angle in enumerate((*angles,0),1):
                        n=hand+digit+str(i)
                        accumulated=accumulated @ rot(Y,sgn*angle)
                        self.absolute(n,accumulated)
            elif side=='Right':
                if name=='hold_bag':
                    swing=rot(X,4.5*wave)
                    q=swing@self.bag_q
                    center=BAG_BAR+Vector((-.002*pulse,-.007*wave,.002*(1-math.cos(t))))
                    wrist=center-q@(GRIP_CENTER-self.h[hand])
                    self.arm_to(side,wrist,Vector((-.55,.8,-.6)),q)
                    grip=1
                else:
                    q=self.jar_q
                    # Depart upward, reach over the sample, then pull it back over the rail.
                    if f<=GRIP:
                        phase=f/GRIP
                        center=JAR_HOME.lerp(JAR_PICK,smooth(phase))+Z*(.036*math.sin(math.pi*phase)**1.55)
                        center.y+=.025*math.sin(math.pi*phase)**1.15
                        grip=(1-smooth(min(1,f/7)))+smooth(max(0,min(1,(f-19)/10)))
                    else:
                        phase=(f-GRIP)/(48-GRIP)
                        center=JAR_PICK.lerp(JAR_HOME,smooth(phase))+Z*(.024*math.sin(math.pi*phase)**2)
                        grip=1
                    wrist=center-q@(GRIP_CENTER-self.h[hand])
                    self.arm_to(side,wrist,Vector((-1.35,.12,-.40)),q)
                for n in self.bones:
                    if n.startswith(hand) and n!=hand:
                        self.local(n,self.src['hand_open_relaxed_R'][n].slerp(self.src['hold_item'][n],grip))
            else:
                q=rot(Y,65) @ rot(X,-18)
                self.arm_to(side,Vector((.193,-.043-.002*wave,.429)),Vector((.75,.62,-.70)),q)
                for n in self.bones:
                    if n.startswith(hand) and n!=hand: self.local(n,self.src['hand_open_relaxed_L'][n])
        for n,angles in FINGER_TRIM[name].items():
            q=Euler(tuple(map(math.radians,angles))).to_quaternion()
            if name=='take_item':
                q=ID.slerp(q,grip)
            self.bones[n].rotation_quaternion=self.bones[n].rotation_quaternion @ q
        bpy.context.view_layer.update()
        if f==0:
            if name=='hold_box':
                prop=trs((BOX_X,BOX_Y,BOX_Z),rot(X,BOX_TILT))
            elif name=='hold_bag':
                prop=trs(BAG_BAR)
            else:
                prop=trs(JAR_HOME)
            self.mounts[name]=joint(self.arm).inverted() @ prop

    def build(self):
        for name in NAMES:
            bind(self.arm,None)
            act=bpy.data.actions.new(name);act.use_fake_user=True
            slot=act.slots.new(id_type='OBJECT',name=self.arm.name)
            self.arm.animation_data.action=act
            self.arm.animation_data.action_slot=slot
            prev={}
            for f in range(49):
                self.pose(name,f)
                for n,p in self.bones.items():
                    q=p.rotation_quaternion.copy()
                    if n in prev: q.make_compatible(prev[n])
                    prev[n]=q
                    p.rotation_quaternion=q
                    p.keyframe_insert('rotation_quaternion',frame=f,group=p.name)
            for fc in act.layers[0].strips[0].channelbag(slot).fcurves:
                for k in fc.keyframe_points:k.interpolation='LINEAR'
        bind(self.arm,None)
        export(self.arm,str(BANK),export_animations=True,export_animation_mode='ACTIONS',
               export_anim_single_armature=True,export_optimize_animation_size=False,
               export_force_sampling=False,export_bake_animation=False,export_frame_range=False,
               export_rest_position_armature=True,export_leaf_bone=False,export_def_bones=False,
               export_anim_slide_to_zero=True)
        # The v3 tread extends 6 mm below the barefoot rest plane. Equipment
        # placement is wardrobe-dependent and must stay outside the shared clips.
        config={'floor_world_m':0,'barefoot_root_lift_m':0,'sneaker_v3_root_lift_m':.0060002,
                'shelf_deck_z_m':float(JAR_PICK.z-.081),'character_up_blender':[0,0,1],
                'character_up_gltf':[0,1,0],
                'shelf_vertical_scale':'1 + root_lift_m / shelf_deck_z_m',
                'shelf_scale_origin':'floor; scale the static Display rail node only',
                'free_item':'add character root lift to the two world-space shelf stops'}
        (HERE/'placement.json').write_text(json.dumps(config,indent=2)+'\n')
        nodes=glb(BODY)[0]
        i=next(i for i,n in enumerate(nodes['nodes']) if n['name']==N+'RightHand')
        bind_world=self.arm.matrix_world @ self.bones['RightHand'].bone.matrix_local
        for name,m in self.mounts.items():
            engine=node_world(nodes,i).inverted() @ C @ bind_world @ m @ C.inverted()
            data=dict(clip=name,prop='props/'+FILES[name]+'.glb',bone=N+'RightHand',
                      fps=FPS,cycle_frames=48,apply_transform='replace node TRS',
                      node={'hold_box':'Parcel','hold_bag':'Market bag','take_item':'Jam jar'}[name],
                      composition='world_matrix_of_joint @ local_matrix_of_prop',
                      blender_pose_bone_head_local=record(m),gltf_joint_local=record(engine))
            if name=='take_item':
                data.update(attach_frame=GRIP,release_frame=0,
                            shelf_node='Display rail',shelf_world_blender=record(trs((0,0,0))),
                            shelf_world_gltf=record(trs((0,0,0))),return_stop_blender=record(trs(JAR_HOME)),
                            pickup_stop_blender=record(trs(JAR_PICK)),return_stop_gltf=record(C@trs(JAR_HOME)@C.inverted()),
                            pickup_stop_gltf=record(C@trs(JAR_PICK)@C.inverted()),return_frames=[3,16],
                            return_interpolation='smoothstep',item_default='pickup_stop',
                            first_play='hold at pickup_stop until attach_frame',
                            repeat_play='release at return_stop, slide to pickup_stop over return_frames, hold until attach_frame')
            (HERE/'props'/(FILES[name]+'.attachment.json')).write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':Builder().build()
