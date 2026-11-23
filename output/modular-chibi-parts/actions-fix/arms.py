"""Find enough shoulder abduction for each side while retaining the authored palm orientation."""
import json
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from tune import envelope

def apply_arm(arm, side, degrees):
    if not degrees:
        return
    upper,fore=[bone(arm,side+p) for p in ('Arm','ForeArm')]
    out=Vector((1 if side=='Left' else -1,0,0))
    axis=(fore.head-upper.head).cross(out).normalized()
    turn(upper,axis,degrees)
    bpy.context.view_layer.update()
    turn(fore,axis,-degrees)
    bpy.context.view_layer.update()

def tune_arms():
    scene,arm,body,actions=load()
    c=Checker(body)
    zones={s:Zone(c,lambda r:kind(r)==s,lambda r:kind(r)=='body') for s in SIDES}
    configs={}
    for clip,last in CLIPS.items():
        chibi.bind(arm,actions[clip])
        rows=[]
        for f in range(last+1):
            angles=[]
            for s in SIDES:
                def clear(d):
                    at(scene,f)
                    apply_arm(arm,s,d)
                    return not zones[s].pairs(posed(body))
                if clear(0):
                    angles.append(0)
                    continue
                hi=next(n for n in range(2,45,2) if clear(n))
                lo=hi-2
                for _ in range(3):
                    mid=(lo+hi)/2
                    if clear(mid):hi=mid
                    else:lo=mid
                angles.append(hi+.65)
            rows.append(angles)
        configs[clip]=rows
    # Spread maxima over adjacent frames; the shared seated/standing poses meet
    # exactly at the four endpoints. Interpolate the broad envelope at source keys.
    idle=np.max(configs['sit_idle'],axis=0)
    stand=np.maximum(configs['sit_down'][0],configs['stand_up'][-1])
    for clip in ('sit_down','sit_idle','stand_up','hold_item'):
        rows=np.array(configs[clip])
        if clip=='sit_idle':
            rows[:]=np.maximum(idle,np.maximum(configs['sit_down'][-1],configs['stand_up'][0]))
        if clip in ('sit_down','stand_up'):
            forward=rows if clip=='sit_down' else rows[::-1]
            for end,values in ((forward,stand),(forward[::-1],idle)):
                end[0]=np.maximum(end[0],values)
        if clip=='hold_item':
            rows[:]=rows.max(0)
        cfg=np.asarray(envelope(rows,0.45,False,radius=4))
        cfg=np.maximum(cfg,rows)
        configs[clip]=cfg.tolist()
    # Shared endpoint angles also account for the smoothed neighboring poses.
    for refs in [(('sit_down',0),('stand_up',-1)),(('sit_down',-1),('sit_idle',0),('sit_idle',-1),('stand_up',0))]:
        goal=np.max([configs[clip][idx] for clip,idx in refs],axis=0)
        for clip,idx in refs:
            rows=np.asarray(configs[clip])
            if clip=='sit_idle': rows[:]=goal
            else:
                seq=rows if idx==0 else rows[::-1]
                for i in range(len(seq)):seq[i]=np.maximum(seq[i],goal-.40*i)
            configs[clip]=rows.tolist()
    (OUT/'arm_angles.json').write_text(json.dumps(configs,indent=1)+'\n')
    for clip,v in configs.items():print(clip,'degree ranges',np.min(v,axis=0),np.max(v,axis=0),flush=True)

if __name__=='__main__':
    tune_arms()
