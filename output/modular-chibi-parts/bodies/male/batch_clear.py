"""Vectorized bind-relative clearance bake and floor preservation."""
from asset_io import *
from build_motion import append_action, skeleton_doc
from gltf_pose import Rig, Skin, clock, normalized

SIDES = ('Left','Right')
ARM = {'idle':(0,5),'walk':(10,12),'run':(8,12),'wave':(0,5),'jump':(3,8),'nod':(0,5),
       'dance':(5,8),'sit_down':(11,14),'sit_idle':(11,14),'stand_up':(11,14),'hold_item':(6,10),
       'hold_box':(2,3),'hold_bag':(0,0),'take_item':(3,6)}
DIGIT_RELAX = {'hold_box':.50,'take_item':.30}


def qmul(a,b):
    v,w = a[...,:3],a[...,3:]
    x,y = b[...,:3],b[...,3:]
    return np.concatenate((w*x+y*v+np.cross(v,x),w*y-(v*x).sum(axis=-1,keepdims=True)),axis=-1)


def conjugate(q):
    return q*np.array([-1,-1,-1,1],dtype=np.float32)


def angle_quat(axes,degrees):
    radians = np.broadcast_to(np.deg2rad(degrees)*.5, axes.shape[:-1])[...,None]
    return np.concatenate((normalized(axes)*np.sin(radians),np.cos(radians)),axis=-1)


def rotate(q,axis):
    v = q[...,:3]
    return axis+2*np.cross(v,np.cross(v,axis)+q[...,3:]*axis)


def world_rotations(rig,q):
    world = q.copy()
    for i,p in enumerate(rig.parent):
        if p>=0:
            world[:,i] = qmul(world[:,p],world[:,i])
    return normalized(world)


def rotate_joint(rig,baked,j,axes,degrees):
    parent = rig.parent[j]
    local_axes = rotate(conjugate(world_rotations(rig,baked[1])[:,parent]),axes)
    baked[1][:,j] = normalized(qmul(angle_quat(local_axes,degrees),baked[1][:,j]))


def translate_joint(rig,baked,j,world,offset):
    parent = rig.parent[j]
    baked[0][:,j] += np.linalg.solve(world[:,parent,:3,:3],np.asarray(offset)[...,None])[...,0]


def relax(rig,baked,joints,amount):
    for j in joints:
        q = baked[1][:,j]
        rest = rig.rest[1][j]
        same = (q*rest).sum(axis=-1,keepdims=True)>=0
        q[:] = normalized((1-amount)*q+amount*np.where(same,rest,-rest))
        for i in (0,2):
            baked[i][:,j] += amount*(rig.rest[i][j]-baked[i][:,j])


def sole(skin,world,side):
    indices = skin.feet[side]
    # Subset the skin projection to the support vertices.
    points = np.einsum('fvki,vki->fv',world[:,skin.ids[indices],1,:],skin.local[indices])
    return points


def batch_world(rig,state):
    t,q,s = state
    x,y,z,w = np.moveaxis(normalized(q),-1,0)
    out = np.zeros(t.shape[:2]+(4,4),dtype=np.float32)
    out[:,:,0,:3] = np.stack((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),axis=-1)
    out[:,:,1,:3] = np.stack((2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),axis=-1)
    out[:,:,2,:3] = np.stack((2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)),axis=-1)
    out[:,:,:3,:3] *= s[:,:,None,:]
    out[:,:,:3,3] = t
    out[:,:,3,3] = 1
    for i,p in enumerate(rig.parent):
        if p>=0:
            out[:,i] = out[:,p] @ out[:,i]
    return out


def correct_clip(rig,skin,source,clip):
    t,q,s = (a.copy() for a in source)
    baked = t,q,s
    before = batch_world(rig,baked)
    orig = np.stack([sole(skin,before,side).min(axis=1) for side in SIDES],axis=1)
    for side,amount in zip(SIDES,ARM[clip]):
        upper,fore,hand = [rig.index[side+x] for x in ('Arm','ForeArm','Hand')]
        if amount:
            reach = normalized(before[:,hand,:3,3]-before[:,upper,:3,3])
            lateral = 1 if side=='Left' else -1
            normal = np.array([lateral,0,0],dtype=np.float32)
            hang = np.array([0,0,lateral],dtype=np.float32)
            wrist_z = before[:,hand,1,3]-before[:,upper,1,3]
            if clip in ('wave','jump','dance','run'):
                # Keep the original raised arm silhouette during the sweep.
                strength = amount*np.clip((.045-wrist_z)/.10,.15,1)
            else:
                strength = np.full(len(t),amount)
            axis = normalized(np.cross(reach,normal)*.55 + hang*.45)
            elbow = np.cross(normalized(before[:,hand,:3,3]-before[:,fore,:3,3]),normal)
            translate_joint(rig,baked,upper,before,normal*np.minimum(.010,strength*.0005)[:,None])
            rotate_joint(rig,baked,upper,axis,strength*.76)
            rotate_joint(rig,baked,fore,elbow,strength*.20*np.clip(np.linalg.norm(elbow,axis=-1)*4,0,1))
        # Remove only the unstable overdriven toe curl. The independent
        # ankle and the root trajectory still carry heel lift and take-off.
        if clip in ('walk','run','jump','dance','sit_down','sit_idle','stand_up','hold_box','hold_bag','take_item'):
            relax(rig,baked,[rig.index[side+'ToeBase'],rig.index[side+'Toe_End']],.96 if side=='Left' else .28)
        if clip in DIGIT_RELAX:
            relax(rig,baked,[j for j,name in enumerate(rig.names) if name.startswith(side+'Hand') and name!=side+'Hand'],
                  DIGIT_RELAX[clip])
        # Give the shorts and thigh skin a small joint-level clearance
        # pulse in the flexed range, with an oppositely distributed shin glide.
        if clip in ('sit_down','sit_idle','stand_up','run','walk','jump'):
            thigh,shin,foot = [rig.index[side+name] for name in ('UpLeg','Leg','Foot')]
            a,b,c = (before[:,i,:3,3] for i in (thigh,shin,foot))
            u,v = normalized(b-a),normalized(c-b)
            bent = np.clip((.88-(u*v).sum(axis=-1))/.88,0,1)
            amount = (.030 if clip.startswith('sit') or clip=='stand_up' else .012)*bent
            delta = normalized(u+v)*amount[:,None]
            direction = 1 if side=='Left' else -1
            spread = np.array([direction,0,.25])*amount[:,None]*.27
            translate_joint(rig,baked,thigh,before,-.12*delta+spread)
            translate_joint(rig,baked,shin,before,.50*delta)
            translate_joint(rig,baked,foot,before,-.38*delta-spread)
    world = batch_world(rig,baked)
    ground = {'idle','wave','nod','hold_item','hold_box','hold_bag','take_item'}
    low = orig.min(axis=1)
    if clip in ground:
        planted = np.ones_like(orig,dtype=bool)
    elif clip in ('sit_down','sit_idle','stand_up'):
        planted = orig<np.maximum(.013,low+.010)[:,None]
    else:
        planted = (orig<=.002) | ((low[:,None]<=.003)&(orig-low[:,None]<.004))
    desired = np.where(planted,.00009,np.maximum(.00009,orig))
    for i,side in enumerate(SIDES):
        z = sole(skin,world,side)
        motion = np.max((desired[:,i,None]-z)/skin.shares[side],axis=1)
        offset = np.column_stack((np.zeros_like(motion),motion,np.zeros_like(motion)))
        for name,share in zip(('UpLeg','Leg','Foot'),(.22,.42,.36)):
            translate_joint(rig,baked,rig.index[side+name],world,offset*share)
    after = batch_world(rig,baked)
    floors = np.stack([sole(skin,after,side).min(axis=1) for side in SIDES],axis=1)
    error = np.max(abs(floors[planted]),initial=0)
    return baked,planted,error


def main():
    source = GLB(HERE/'.runtime/motion_relative.glb')
    target = GLB(HERE/'body_male.glb')
    rig = Rig(target)
    skin = Skin(target,rig)
    out = Writer(skeleton_doc(target))
    out.doc['skins'] = deepcopy(target.doc['skins'])
    for item in out.doc['skins']:
        item['inverseBindMatrices'] = out.accessor(target.accessor(item['inverseBindMatrices']),'MAT4')
    report = {}
    for anim in source.doc['animations']:
        name = anim['name']
        times = clock(source,anim)
        original = rig.sample(source,anim,times)
        baked,planted,error = correct_clip(rig,skin,original,name)
        append_action(out,target,rig,name,times,baked)
        report[name] = {'samples':len(times),'planted_samples':int(planted.sum()),
                        'max_planted_error_mm':float(error*1000),'arm_clearance_degrees':list(ARM[name])}
        print('BAKE',name,report[name],flush=True)
    temp = HERE/'.runtime/batch_motion_build.glb'
    out.write(temp)
    temp.replace(MOTION)
    write_json(HERE/'qa/body_bake_batch.json',report)


if __name__=='__main__':
    main()
