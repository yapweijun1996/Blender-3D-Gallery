"""Multi-start fits concentrated on the feasible carry and pickup poses."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from solve import *

def box_sdf(v):
    delta=np.abs(v-np.array([0.,0.,108.]))-np.array([152.,109.,108.])
    return np.linalg.norm(np.maximum(delta,0),axis=1)+np.minimum(delta.max(1),0.)

def box_cost(fit,x,ids,required=4):
    r=np.asarray(world_matrix(x))[:3,:3]
    gaps=np.zeros(4)
    dep=0
    chin=50
    for i in ids:
        _,pads,body,head=fit.geometry[i]
        for j,p in enumerate(pads):
            gaps[j]=max(gaps[j],np.abs(box_sdf((p-x[:3])@r)).min())
        body=(body-x[:3])@r
        body=body[(np.abs(body[:,0])<153)&(np.abs(body[:,1])<110)&(body[:,2]>=0)&(body[:,2]<=216)]
        if len(body):
            dep=max(dep,-float(box_sdf(body).min()))
        chin=min(chin,float(box_sdf((head-x[:3])@r).min()))
    bad=np.maximum(gaps[:required]-2.2,0)
    return 2*(bad**2).sum()+15*max(dep-.28,0)**2+3*max(11-chin,0)**2+ .07*(gaps[:required]**2).sum()+.03*(1-r[2,2])

def box_seeds(fit):
    from itertools import product
    pads=[p.mean(0) for p in fit.geometry[0][1]]
    center=np.mean(pads,axis=0)
    axis=Vector(pads[-1]-pads[1]).normalized()
    for signs in product((-1,1),repeat=3):
        diag=Vector(np.array([304.,218.,216.])*signs).normalized()
        align=diag.rotation_difference(axis)
        for angle in np.linspace(-math.pi,math.pi,12,endpoint=False):
            q=Quaternion(axis,angle)@align
            if q.to_matrix()[2][2]<.06:
                continue
            for offset in [(0,-48,0),(0,-15,20)]:
                yield np.r_[center+offset-np.asarray(q@Vector((0,0,108))),np.asarray(q.to_euler())*100.]

def box_search(fit):
    path=HERE/'hold_box.trial.json'
    original=json.loads(path.read_text())
    s0=np.array(original['x'])
    ids=np.r_[0, len(fit.geometry)//4, len(fit.geometry)*3//4]
    step=np.array([10.,10.,10.,12.,12.,12.])
    starts=[]
    for i,x in enumerate([s0, *box_seeds(fit)]):
        x,score=simplex(lambda z:box_cost(fit,z,[0]),x,step,105)
        starts.append((score,x))
        if i%20==0:print('BOX BROAD',i,min(k for k,x in starts),flush=True)
    best=[]
    for _,x in sorted(starts,key=lambda r:r[0])[:8]:
        x,score=simplex(lambda z:box_cost(fit,z,ids),x,step*.4,120)
        best.append((score,x))
    precise=sorted(best,key=lambda r:r[0])[:3]
    all_ids=range(len(fit.geometry))
    final=[]
    for _,x in precise:
        x,assess=simplex(lambda z:fit.cost(z,ids),x,step*.20,95)
        g,p,c=fit.values(x,all_ids)
        score=(np.maximum(g-3,0)**2).sum()+max(p-.65,0)**2*10+max(10-c,0)**2
        final.append((score,x))
        print('BOX BROAD RESULT',x,g,p,c,score,flush=True)
        if score < 1e-7:
            break
    deficit,x=min(final,key=lambda r:r[0])
    if deficit > 1e-7:
        # Keep a fallback rigid right-hand socket with the left hand measured separately.
        candidates=[]
        seeds=[np.array([x,y,z,r,p,a]) for x,y,z in [(-38,-325,387),(-48,-330,372),(-51,-344,376),(-58,-293,398)]
               for r,p,a in [(0,0,0),(0,-12,-14),(0,12,16),(0,-12,-35),(-10,20,17)]]
        seeds.extend(seed for _,seed in sorted(starts,key=lambda r:r[0])[:4])
        for seed in seeds:
            seed,_=simplex(lambda z:box_cost(fit,z,ids,required=2)+.30*np.linalg.norm(z[3:5])**2/10000,seed,step*.65,115)
            g,p,c=fit.values(seed,all_ids)
            score=(np.maximum(g[:2]-2.8,0)**2).sum()+20*max(p-.45,0)**2+max(11-c,0)**2+.00003*(g[2:]**2).sum()+.1*np.linalg.norm(seed[3:5])**2/10000
            candidates.append((score,seed))
            if score<.035:break
        score,right=min(candidates,key=lambda r:r[0])
        g,p,c=fit.values(right,all_ids)
        print('RIGHT FALLBACK',right,g,p,c,flush=True)
        if max(g[:2])<=3 and p<.7 and c>=10:
            # Preserve provenance of the bilateral search separately until the final report.
            (HERE/'box_bilateral_attempt.json').write_text(json.dumps(dict(x=x.tolist(),score=float(deficit))))
            x=right
    g,p,c=fit.values(x,all_ids)
    record_fit=dict(x=x.tolist(),socket=record(fit.hand_ref.inverted()@world_matrix(x)@B),gap=g.tolist(),depth=p,chin=c)
    path.write_text(json.dumps(record_fit,indent=2)+'\n')
    print('BOX FINAL',record_fit,flush=True)

if __name__=='__main__':
    s=Stage()
    box_search(GripFit(s,'hold_box',{side:pads(s,side) for side in ('Right','Left')}))
