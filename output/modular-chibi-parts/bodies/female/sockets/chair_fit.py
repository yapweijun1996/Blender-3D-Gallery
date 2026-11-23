"""Find a floor-preserving chair placement for the fixed female clips."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_geometry import *

SEAT = .252
BASE_CHAIR = dict(translation_m=[0.,0.,0.], quaternion_xyzw=[0.,0.,0.,1.],scale_xyz=[1.,1.,1.])

def support_mask(stage):
    return np.isin(stage.labels, [N+'Hips', N+'LeftUpLeg', N+'RightUpLeg'])

def seated(clip, seconds):
    return clip == 'sit_idle' or (clip == 'sit_down' and abs(seconds - 1.2) < 1e-8) or (clip == 'stand_up' and seconds == 0)

class ChairFit:
    def __init__(self, stage):
        self.stage = stage
        self.chair = stage.asset(ASTRA / 'chair.glb')['Chair']
        self.raw, self.faces = points(self.chair), faces(self.chair)
        self.components = list(components(self.raw,self.faces))
        self.top_faces = [f for f in self.faces if abs(self.raw[list(f),2] - SEAT).max() < 1e-6]
        assert len(self.top_faces) and len(self.components) == 9
        self.mask = support_mask(stage)
        self.sole = {}
        self.heel = {}
        self.forefoot = {}
        for side in ('Left','Right'):
            s = np.char.startswith(stage.labels,N+side) & (stage.rest[:,2] < .006)
            y = stage.rest[s,1]
            self.sole[side] = s
            self.heel[side] = s & (stage.rest[:,1]> np.quantile(y,.65))
            self.forefoot[side] = s & (stage.rest[:,1]< np.quantile(y,.35))

    def placement(self, config):
        m = B @ trs(config) @ G
        posed = transform(self.raw,m)
        self.posed = posed
        self.whole = tree(posed * 1000,self.faces)
        self.solids = [Solid(posed * 1000,f) for f in self.components]
        self.top = tree(posed * 1000,self.top_faces)

    def gaps(self, p):
        p = p[self.mask]*1000
        bounds = self.posed[np.unique(self.top_faces)]*1000
        lo,hi = bounds.min(0),bounds.max(0)
        p = p[box_bounds(p[:,:2],lo[:2],hi[:2])]
        mid = (lo[0]+hi[0])/2
        results = {}
        for side,direction in [('Left',1),('Right',-1)]:
            distances = []
            for point in p[(p[:,0]-mid)*direction>4]:
                surface, _, _, _ = self.top.ray_cast((point[0],point[1],lo[2]-900),(0,0,1))
                if surface is not None:
                    distances.append(float(point[2]-surface.z))
            results[side] = min(distances,default=None)
        return results

    def contacts(self,p):
        body = p*1000
        inside = {}
        for solid in self.solids:
            for i,d in solid.enclosed(body).items():
                inside[i]=max(inside.get(i,0),d)
        pairs = self.whole.overlap(tree(body,self.stage.faces))
        return dict(inside_vertices=len(inside), depth_mm=max(inside.values(),default=0.),
                    triangle_pairs=len(pairs))

    def floors(self,p):
        return {side:dict(sole_mm=float(p[self.sole[side],2].min()*1000),
                          heel_mm=float(p[self.heel[side],2].min()*1000),
                          forefoot_mm=float(p[self.forefoot[side],2].min()*1000))
                for side in ('Left','Right')}

    def solve(self):
        body = {name:[self.stage.frame(name,t) for t in time_grid(30,end)] for name,end in CHAIR.items()}
        st = [body['sit_down'][-1], *body['sit_idle'], body['stand_up'][0]]
        candidate_pts = np.stack([p[self.mask] for p in st]) * 1000
        coat = self.raw[np.unique(self.top_faces)]
        lo,hi = coat.min(0)*1000,coat.max(0)*1000
        # Search the cushion flat footprint first; confirm its real triangles below.
        pool = []
        for y in np.arange(-10,51,.5):
            for x in (0,-10,10,-20,20):
                p = candidate_pts
                within = (p[:,:,0]>lo[0]+x+9)&(p[:,:,0]<hi[0]+x-9)&(p[:,:,1]>lo[1]+y)&(p[:,:,1]<hi[1]+y)
                left = np.where(within&(p[:,:,0]>x+4),p[:,:,2],np.inf).min(1)
                right = np.where(within&(p[:,:,0]<x-4),p[:,:,2],np.inf).min(1)
                if not np.isfinite([left,right]).all():
                    continue
                low = min(left.min(),right.min())
                high = max(left.max(),right.max())
                # Favor bilateral contact within 2 mm and a placement close to the origin.
                score = 10*max(0,high-low-1.65)+abs(y)*.026+abs(x)*.018+abs(252-low)*.018
                pool.append((score,x,y,low-.25))
        best = None
        for _,x,y,z in sorted(pool)[:70]:
            config = dict(BASE_CHAIR,translation_m=[x/1000.,0.,-y/1000.],scale_xyz=[1.,z/252.,1.])
            self.placement(config)
            seat_sample = [self.gaps(p) for p in [st[0], st[1], st[45],st[90],st[135],st[-2],st[-1]]]
            ds=[k for row in seat_sample for k in row.values() if k is not None]
            if len(ds) != len(seat_sample)*2 or min(ds) < -.01:
                continue
            collisions = [self.contacts(p) for a in body.values() for p in a[::8]]
            count = max(r['inside_vertices'] for r in collisions)
            pairs = max(r['triangle_pairs'] for r in collisions)
            score = (count>0,pairs>0,max(0,max(ds)-2),abs(y)*.026+abs(x)*.018+abs(252-z)*.018)
            if best is None or score < best[0]:
                best=(score,config)
                print('CHAIR IMPROVEMENT',score,config, min(ds),max(ds),flush=True)
            if not count and not pairs and max(ds) <= 2:
                break
        if best is None:
            raise RuntimeError('No chair height candidate kept the seat above the cushion.')
        config=best[1]
        self.placement(config)
        for c, arr in body.items():
            report=[self.contacts(p) for p in arr]
            print(c,'collision',max(r['inside_vertices'] for r in report),max(r['triangle_pairs'] for r in report),flush=True)
        (HERE/'chair.trial.json').write_text(json.dumps(config,indent=2)+'\n')

if __name__=='__main__':
    ChairFit(Stage()).solve()
