"""Fit with a stationary jar during the initial reach."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from solve import *

def run(fit,stage):
    path=HERE/'take_item.trial.json'
    prior=json.loads(path.read_text())
    x=np.array(prior['x'])
    approach=[]
    for t in time_grid(24,48):
        if t<PICK:
            a=stage.frame('take_item',t)
            a=a[(abs(a[:,0]-x[0]/1000)<.17)&(abs(a[:,1]-x[1]/1000)<.16)&(abs(a[:,2]-x[2]/1000)<.17)]
            approach.append((t,np.unique(a.round(6),axis=0)*1000))
    active=[a for t,a in approach if t>20/24]
    ids=np.r_[0, np.linspace(0,len(fit.geometry)-1,9,dtype=int)[1:]]
    lo,hi=fit.lo,fit.hi
    def wait_depth(x, frames):
        r=np.asarray(world_matrix(x))[:3,:3]
        p=np.vstack(frames)
        p=(p-x[:3])@r
        p=p[((p>=lo)&(p<=hi)).all(1)]
        return max(0,-min((signed(fit.full,v) for v in p),default=0))
    def cost(v,frames,ix):
        g,p,_=fit.values(v,ix)
        w=wait_depth(v,frames)
        tilt=math.acos(np.clip(np.asarray(world_matrix(v))[2,2],-1,1))
        return 20*(max(p-.28,0)**2+max(w-.28,0)**2)+10*(np.maximum(g-2.65,0)**2).sum()+.03*(g**2).sum()+1.3*tilt**2
    print('JAR APPROACH INITIAL',wait_depth(x,[a for _,a in approach]),flush=True)
    start=x.copy()
    step=np.array([5.,5.,5.,9.,9.,9.])
    for _ in range(2):
        x,_=simplex(lambda v:cost(v,active[::2],ids),x,step,210)
        step*=.35
    g,p,_=fit.values(x,range(len(fit.geometry)))
    wait=wait_depth(x,[a for _,a in approach])
    print('JAR REFIT',x,g,p,wait,flush=True)
    if max(g)<2.96 and p<.75 and wait<.70:
        path.write_text(json.dumps(dict(x=x.tolist(),socket=record(fit.hand_ref.inverted()@world_matrix(x)@B),
                                      gap=g.tolist(),depth=p,waiting_depth=wait),indent=2)+'\n')

if __name__=='__main__':
    stage=Stage()
    run(GripFit(stage,'take_item',{side:pads(stage,side) for side in ('Right','Left')}),stage)
