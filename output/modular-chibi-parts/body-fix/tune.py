"""Choose pose corrections against actual, unmasked master triangles."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bodycheck import *
from clearance import *


def set_time(scene,f):
    scene.frame_set(int(f),subframe=f-int(f))


def envelope(rows,slope,cyclic,radius=3):
    data=np.array(rows,dtype=float)
    n=len(data)
    for side in range(2):
        val=data[:,side].copy()
        distance=np.abs(np.arange(n)[:,None]-np.arange(n))
        if cyclic: distance=np.minimum(distance,n-1-distance)
        ramp=(val[None,:]-slope*distance).max(axis=1)
        pad=np.pad(ramp,(radius,radius),mode='wrap' if cyclic else 'edge')
        window=np.exp(-.5*(np.arange(-radius,radius+1)/(radius*.5))**2)
        smooth=np.convolve(pad,window/window.sum(),mode='valid')
        data[:,side]=np.maximum(smooth,val)
        if cyclic: data[0,side]=data[-1,side]=max(data[0,side],data[-1,side])
    return data.round(4).tolist()


def tune():
    scene,arm,body,_=load();c=Checker(body)
    config={}
    for clip in CLIPS:
        integer_frames=bind(arm,clip)
        step=.5 if clip=='run' else 1
        fs=np.arange(integer_frames.start,integer_frames.stop-1+step/2,step).tolist()
        ks=[];ss=[];relaxed=[]
        for f in fs:
            set_time(scene,f)
            vals=counts(c,posed(body),knee_contact)
            goal=[0 if v==0 else None for v in vals]
            for d in range(2,115,2):
                if None not in goal: break
                set_time(scene,f);legs(arm,(d,d))
                now=counts(c,posed(body),knee_contact)
                for i in range(2):
                    if goal[i] is None and now[i]==0: goal[i]=d+1
            if None in goal: raise RuntimeError((clip,f,goal))
            ks.append(goal)
        ks=envelope(ks,24*step,clip!='walk',radius=2)
        for f,kv in zip(fs,ks):
            set_time(scene,f);legs(arm,kv)
            vals=counts(c,posed(body),arm_contact)
            goal=[0 if v==0 else None for v in vals]
            best=list(vals);best_d=[0,0]
            for d in range(2,45,2):
                if None not in goal: break
                set_time(scene,f);legs(arm,kv);arms(arm,(d,d))
                now=counts(c,posed(body),arm_contact)
                for i in range(2):
                    if now[i]<best[i]: best[i]=now[i];best_d[i]=d
                    if goal[i] is None and now[i]==0: goal[i]=d+1
            ss.append([best_d[i] if d is None else d for i,d in enumerate(goal)])
        ss=envelope(ss,2.2*step,clip!='walk')
        for f,kv,av in zip(fs,ks,ss):
            set_time(scene,f); targets=hand_targets(arm)
            legs(arm,kv);arms(arm,av)
            quats=[bone(arm,s+'ForeArm').rotation_quaternion.copy() for s in SIDES]
            best=[0.,0.]
            # Bring the hand back toward its original path until it first meets
            # the torso. Keep a small margin from the first failing candidate.
            active=[True,True]
            for frac in (.15,.3,.45,.6,.75,.9,1.):
                for side,q in zip(SIDES,quats): bone(arm,side+'ForeArm').rotation_quaternion=q
                bpy.context.view_layer.update()
                relax_elbows(arm,targets,(frac,frac))
                now=counts(c,posed(body),arm_contact)
                for i in range(2):
                    if now[i]:active[i]=False
                    if active[i]:best[i]=frac
                if not any(active):break
            relaxed.append([max(0,v-.055) for v in best])
        # Smooth toward the more conservative side of neighboring clearance bounds.
        relax=(1-np.asarray(envelope(1-np.asarray(relaxed),.18*step,clip!='walk'))).round(4).tolist()
        config[clip]={'frames':fs,'arm_strength':ss,'knee_glide_mm':ks,'elbow_return':relax}
        print('TUNE',clip,'arm max',np.max(ss,axis=0),'knee max',np.max(ks,axis=0),flush=True)
    (OUT/'clearance_keys.json').write_text(json.dumps(config,indent=1)+'\n')


if __name__=='__main__':
    tune()
