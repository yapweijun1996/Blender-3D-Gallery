"""Search a small cushion roll when the two baked chair joins differ in height."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from chair_fit import *

def run():
    stage=Stage()
    chair=ChairFit(stage)
    body={name:[stage.frame(name,t) for t in time_grid(30,end)] for name,end in CHAIR.items()}
    st=[body['sit_down'][-1],*body['sit_idle'],body['stand_up'][0]]
    candidate=np.stack([p[chair.mask] for p in st])*1000
    coarse=candidate[np.r_[0,1,np.arange(4,len(candidate),8),len(candidate)-1]]
    p=coarse.transpose(2,0,1)
    options=[]
    for y in np.arange(-8.,45.,1.):
        in_depth=abs(p[1]-y)<101
        for x in (0.,-5.,5.,-12.,12.):
            inside=in_depth & (abs(p[0]-x)<151)
            for angle in [.0,.010,.015,.020,.025,.030,.035,.040,.045,.052]:
                height=p[2]+math.tan(angle)*(p[0]-x)
                left=np.where(inside&(p[0]>x+4),height,np.inf).min(1)
                right=np.where(inside&(p[0]<x-4),height,np.inf).min(1)
                low=min(left.min(),right.min())
                high=np.minimum(left,right).max()
                c=(12*max(0,high-low-1.55)
                   +.03*max(0,max(left.max(),right.max())-low-2)
                   +abs(y)*.021+abs(x)*.027+abs(angle)*32)
                options.append((c,x,y,angle,low-.20))
    best=None
    for _,x,y,angle,h in sorted(options)[:155]:
        def config(seat):
            tilt = Matrix.Rotation(angle,4,'Y')
            m=tilt@Matrix.Diagonal(Vector((1.,1.,seat/252.,1.)))
            m.translation=Vector((0.,y/1000,0.))
            m.translation.z=-float(transform(chair.raw,m)[:,2].min())
            m.translation.x=x/1000.-float(m[0][2])*.252
            return B @ (G @ m @ B) @ G
        for _ in range(4):
            m=config(h)
            actual=(m @ Vector((0,0,.252))).z*1000
            target=next(k[-1] for k in options if k[1:4]==(x,y,angle))
            if abs(target-actual)<.00005:break
            h+=target-actual
        for lowering in (0.,.15,.35,.65,1.05):
            conf=record(G@config(h-lowering)@B,scale=True)
            chair.placement(conf)
            g=[chair.gaps(p) for p in [st[0],st[1],st[45],st[90],st[135],st[-2],st[-1]]]
            nearest=[min(row.values()) for row in g if None not in row.values()]
            if len(nearest)!=len(g) or min(nearest)<0 or max(nearest)>2.05:
                continue
            contacts=[chair.contacts(p) for arr in body.values() for p in arr[::8]]
            if any(r['inside_vertices'] or r['triangle_pairs'] for r in contacts):
                continue
            g=[chair.gaps(p) for p in st]
            nearest=[min(row.values()) for row in g if None not in row.values()]
            if len(nearest)!=len(g) or min(nearest)<0 or max(nearest)>2:
                continue
            contacts=[chair.contacts(p) for arr in body.values() for p in arr]
            if any(r['inside_vertices'] or r['triangle_pairs'] for r in contacts):
                continue
            best=conf
            print('CHAIR ROLLED',best,min(nearest),max(nearest),flush=True)
            break
        if best:
            break
    if best:
        (HERE/'chair.trial.json').write_text(json.dumps(best,indent=2)+'\n')
    else:
        print('No additional stationary chair transform passed all three criteria.',flush=True)

if __name__=='__main__':run()
