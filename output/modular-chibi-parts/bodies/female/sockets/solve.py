"""Search six rigid degrees of freedom against the actual posed surface."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fit_geometry import *
from mathutils import Euler

def simplex(fun, initial, step, iterations):
    n = len(initial)
    x = np.vstack((initial, initial + np.diag(step)))
    y = np.array([fun(a) for a in x])
    for i in range(iterations):
        order = np.argsort(y)
        x, y = x[order], y[order]
        center = x[:-1].mean(0)
        reflected = 2 * center - x[-1]
        r = fun(reflected)
        if r < y[0]:
            extended = center + 2 * (reflected - center)
            e = fun(extended)
            x[-1], y[-1] = (extended, e) if e < r else (reflected, r)
        elif r < y[-2]:
            x[-1], y[-1] = reflected, r
        else:
            other, target = (reflected, r) if r < y[-1] else (x[-1], y[-1])
            contracted = (center + other) / 2
            c = fun(contracted)
            if c < target:
                x[-1], y[-1] = contracted, c
            else:
                x[1:] = (x[1:] + x[0]) / 2
                y[1:] = [fun(a) for a in x[1:]]
    best = np.argmin(y)
    return x[best], float(y[best])

def world_matrix(x):
    # All coordinates and angular parameters have comparable optimizer scales.
    m = Euler(x[3:] / 100).to_matrix().to_4x4()
    m.translation = Vector(x[:3] / 1000)
    return m

class GripFit:
    def __init__(self, stage, clip, patches):
        self.clip = clip
        file, node, _, fps, end = PROPS[clip]
        self.objects = stage.asset(file)
        self.prop = self.objects[node]
        self.p = points(self.prop)
        self.f = faces(self.prop)
        self.sides = ('Right', 'Left') if clip == 'hold_box' else ('Right',)
        ref = PICK if clip == 'take_item' else 0
        t = [a for a in time_grid(fps, end) if a >= ref]
        stage.frame(clip, ref)
        self.hand_ref = stage.hand(ref)
        self.ref = ref
        self.geometry = []
        body_samples = np.array(stage.faces)
        body_edges = np.unique(np.sort(np.concatenate([body_samples[:,[0, 1]], body_samples[:,[1, 2]], body_samples[:,[2, 0]]]),axis=1),axis=0)
        self.patches = [patches[side][digit] for side in self.sides for digit in ('Thumb', 'Index')]
        for time in t:
            body = stage.frame(clip, time)
            rel = self.hand_ref @ stage.hand(time).inverted()
            body = transform(body, rel) * 1000
            pads = [body[np.unique(part)] for part in self.patches]
            if clip == 'hold_box':
                region = ((abs(body[:,0]) < 270) & (body[:,1] < -35) & (body[:,2] > 305) & (body[:,2] < 750))
            else:
                # Enclose the right grip and the possible hanging prop and nearby torso.
                center = pads[0].mean(0)
                region = (abs(body[:,0] - center[0]) < 150) & (abs(body[:,1] - center[1]) < 190)
                region &= (body[:,2] > center[2] - 350) & (body[:,2] < center[2] + 130)
            b = np.unique(np.round(body[region], 3), axis=0)
            sf = body_samples[region[body_samples].all(1)]
            se = body_edges[region[body_edges].all(1)]
            b = np.vstack((b, body[sf].mean(1), body[se].mean(1)))
            h = body[stage.labels == N + 'Head']
            self.geometry.append((time, pads, b, h))
        self.lo = self.p.min(0)*1000
        self.hi = self.p.max(0)*1000
        self.parts = []
        self.full = tree(self.p*1000, self.f)
        for part in components(self.p,self.f):
            pv = self.p[np.unique(part)]*1000
            self.parts.append((pv.min(0),pv.max(0),tree(self.p*1000,part)))
        self.grip = self.full
        if clip == 'hold_bag':
            options = [bvh for lo, hi, bvh in self.parts
                       if hi[2] > -1 and lo[2] > -22 and (hi-lo)[1] > 105]
            assert len(options) == 1, [(a,b) for a,b,_ in self.parts]
            self.grip = options[0]

    def values(self, x, indices):
        m = np.asarray(world_matrix(x))
        r = m[:3,:3]
        trans = x[:3]
        gap = np.zeros(len(self.patches))
        depth = 0.
        head_clearance = 50.
        for i in indices:
            time, pads, body, head = self.geometry[i]
            for j, p in enumerate(pads):
                d = near(self.grip, (p-trans)@r)
                gap[j] = max(gap[j], d)
            local = (body - trans) @ r
            for lo, hi, bvh in self.parts:
                candidate = local[((local>lo)&(local<hi)).all(1)]
                if len(candidate):
                    depth = max(depth, -min(signed(bvh,p) for p in candidate))
            if self.clip == 'hold_box':
                loc = (head-trans) @ r
                offset = np.maximum(0, np.maximum(loc - self.hi, self.lo - loc))
                head_clearance = min(head_clearance, float(np.linalg.norm(offset,axis=1).min()))
        return gap, depth, head_clearance

    def cost(self, x, indices):
        gaps, depth, chin = self.values(x, indices)
        bad_gaps = np.maximum(gaps - 2.45, 0)
        bad_depth = max(0.,depth -.45)
        bad_chin = max(0., 12.-chin)
        # Preserve recognizable prop orientation among comparable contact fits.
        tilt = np.linalg.norm(x[3:5]) / 100
        orientation = {'hold_item': .35, 'hold_box': .7, 'hold_bag': .45, 'take_item': .8}[self.clip]
        return float((bad_gaps**2).sum() + 10*bad_depth**2 + 2*bad_chin**2 +
                     .04*(gaps**2).sum() + .2*depth**2 + orientation*tilt**2)

    def seeds(self):
        pads = [p.mean(0) for p in self.geometry[0][1]]
        a,b = pads[:2]
        center = (a+b)/2
        if self.clip == 'hold_box':
            return [np.r_[t,angles] for t in [(-6,-350,395),(-10,-340,378),(-12,-330,370),
                     (-40,-352,391),(2,-341,372),(-8,-340,390)] for angles in
                     [(0,0,0),(0,-16,0),(0,16,0),(-12,-15,0),(0,-12,18),(0,-12,-18)]]
        if self.clip == 'hold_bag':
            axis = Vector(b-a).normalized()
            q = Vector((0,1,0)).rotation_difference(axis)
            q2 = Vector((0,1,0)).rotation_difference(-axis)
            return [np.r_[center + offset, angles] for offset in [(0,0,0),(9,-4,8),(-10,-6,5),(0,-9,6)]
                    for angles in [np.asarray((q@Quaternion((0,1,0), twist)).to_euler())*100 for twist in [0,.65,1.3,2,-.65,-1.3]]+
                                  [np.asarray((q2@Quaternion((0,1,0), twist)).to_euler())*100 for twist in [0,.65,1.3,2,-.65,-1.3]]]
        axis = Vector(a-b if a[2]>b[2] else b-a).normalized()
        tilt = Vector((0,0,1)).rotation_difference(axis).to_euler()
        return [np.r_[center + offset, np.asarray(tilt)*amount + [0,0,yaw]]
                for offset in [(0,-16,0),(0,-23,-7),(7,-22,-10),(-7,-20,-4),(0,10,0),(0,0,-20)]
                for amount in (0,35,70,100) for yaw in [0]]

    def solve(self):
        stem = HERE / (self.clip+'.trial.json')
        if stem.exists():
            saved = np.array(json.loads(stem.read_text())['x'])
            seeds = [saved]
        else:
            seeds = self.seeds()
        size = len(self.geometry)
        coarse = np.unique(np.linspace(0,size-1,3,dtype=int))
        mid = np.unique(np.r_[np.linspace(0,size-1,9,dtype=int), size//4, 3*size//4])
        step = np.array([7.,7.,7.,9.,9.,9.])
        results = []
        def fit(seed, step, ids, rounds):
            return simplex(lambda x:self.cost(x,ids), seed, step, rounds)
        for i, seed in enumerate(seeds):
            x, score = fit(seed, step, [coarse[0]], 115)
            results.append((score, x))
            if (i+1)%8 == 0:
                best = min(results,key=lambda v:v[0])
                print(self.clip,'seed',i+1,'of',len(seeds),best[0], best[1].round(2),flush=True)
        best = []
        for _, x in sorted(results, key=lambda v:v[0])[:8]:
            x, score = fit(x,step*.55,mid,165)
            best.append((score,x))
        x = min(best,key=lambda v:v[0])[1]
        check = range(size)
        for _ in range(2):
            # Refine on extrema so the finite sample grid stays practical.
            items = [(i,self.cost(x,[i])) for i in check]
            active = np.unique(np.r_[mid,[i for i,_ in sorted(items,key=lambda r:-r[1])[:7]]])
            x, score = fit(x,step*.18,active,155)
        v = self.values(x,check)
        world = world_matrix(x)
        mount = self.hand_ref.inverted() @ world @ B
        stem.write_text(json.dumps(dict(x=x.tolist(), socket=record(mount),
                                        gap=v[0].tolist(), depth=v[1], chin=v[2]),indent=2)+'\n')
        print(self.clip, 'SOLUTION', x, score, v, flush=True)
        for o in self.objects.values():
            bpy.data.objects.remove(o,do_unlink=True)

if __name__=='__main__':
    stage=Stage()
    patches={side:pads(stage,side) for side in ('Right','Left')}
    for clip in sys.argv[sys.argv.index('--')+1:]:
        GripFit(stage,clip,patches).solve()
