"""Small pose changes for pelvis and elbow folds left by the primary clearance pass."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from clearance import SIDES, bone,turn

def hip(arm,side,mm):
    if not mm:return
    thigh,shin,foot=[bone(arm,side+k) for k in ('UpLeg','Leg','Foot')]
    first,second,ankle=[pb.matrix.copy() for pb in (thigh,shin,foot)]
    outward=1 if side=='Left' else -1
    shift=Vector((.60*outward,0,-1)).normalized()*(mm/1000)
    old=first.translation-ankle.translation
    new=old+shift
    # Use the ankle as a pivot for both leg segments so their relative knee
    # clearance survives a small change at the top of the thigh.
    transform=old.rotation_difference(new).to_matrix()*(new.length/old.length)
    for pb,matrix in ((thigh,first),(shin,second)):
        updated=(transform @ matrix.to_3x3()).to_4x4()
        updated.translation=ankle.translation+transform@(matrix.translation-ankle.translation)
        pb.matrix=updated
        bpy.context.view_layer.update()
    foot.matrix=ankle
    bpy.context.view_layer.update()

def elbow(arm,side,degrees):
    if not degrees:return
    upper,fore,hand=[bone(arm,side+k) for k in ('Arm','ForeArm','Hand')]
    axis=(fore.head-upper.head).cross(hand.head-fore.head)
    if axis.length>1.e-7:
        turn(fore,axis.normalized(),-degrees)
        bpy.context.view_layer.update()

def apply(arm,hips,elbows):
    for side,h,e in zip(SIDES,hips,elbows):
        hip(arm,side,h)
        elbow(arm,side,e)


def derive():
    import json
    from bodycheck import OUT,CLIPS,load,bind,posed,Checker
    from clearance import knee_contact,arm_contact,legs,feet,arms,hand_targets,relax_elbows
    from tune import set_time,envelope
    cfg=json.loads((OUT/'clearance_keys.json').read_text())
    scene,arm,body,_=load(); ch=Checker(body)
    offsets={}
    for clip in CLIPS:
        block=cfg[clip];fs=block['frames']; bind(arm,clip)
        hip_keys=[];elbow_keys=[]
        if clip not in ('run','wave'):
            offsets[clip]={'hip_mm':[[0,0]]*len(fs),'elbow_deg':[[0,0]]*len(fs)}
            continue
        for f,kv,av,rv in zip(fs,block['knee_glide_mm'],block['arm_strength'],block['elbow_return']):
            set_time(scene,f);ref=posed(body);target=hand_targets(arm)
            legs(arm,kv);arms(arm,av);relax_elbows(arm,target,rv)
            # Store explicit local TRS. Restoring it bypasses matrix decomposition.
            pbones=[bone(arm,s+n) for s in SIDES for n in ('UpLeg','Leg','Foot','ForeArm')]
            basis=[(p.location.copy(),p.rotation_quaternion.copy(),p.scale.copy()) for p in pbones]
            def restore():
                for p,(t,q,k) in zip(pbones,basis):
                    p.location=t;p.rotation_quaternion=q;p.scale=k
                bpy.context.view_layer.update()
            def hits():
                pairs,_=ch.overlap(posed(body))
                return [(ch.regions[i],ch.regions[j]) for i,j in pairs]
            legs_out=[];arms_out=[]
            for side in SIDES:
                best_h=(float('inf'),0)
                # Preserve surface clearance at the knee and across the arms while
                # increasing separation between the pelvis and the lifted thigh.
                for d in range(0,35,2):
                    restore(); hip(arm,side,d);pairs=hits()
                    if any(knee_contact(a,b,side) or arm_contact(a,b,side) for a,b in pairs):continue
                    n=sum({a,b}=={'Hips',side+'UpLeg'} for a,b in pairs)
                    best_h=min(best_h,(n,d))
                    if n==0:break
                h=best_h[1];legs_out.append(h+.4 if h else 0)
                best_e=(float('inf'),0)
                for d in range(0,35,2):
                    restore(); hip(arm,side,h);elbow(arm,side,d);pairs=hits()
                    if any(arm_contact(a,b,side) for a,b in pairs):continue
                    n=sum({a,b}=={side+'Arm',side+'ForeArm'} for a,b in pairs)
                    best_e=min(best_e,(n,d))
                    if n==0:break
                e=best_e[1];arms_out.append(e+.35 if e else 0)
            hip_keys.append(legs_out);elbow_keys.append(arms_out)
        step=fs[1]-fs[0]
        offsets[clip]={'hip_mm':envelope(hip_keys,10*step,True,2),
                       'elbow_deg':envelope(elbow_keys,7*step,True,2)}
        print('POLISH',clip,flush=True)
    (OUT/'fold_keys.json').write_text(json.dumps(offsets,indent=1)+'\n')


if __name__=='__main__':
    derive()
