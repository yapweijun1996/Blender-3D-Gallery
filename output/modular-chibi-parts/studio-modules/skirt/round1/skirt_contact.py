"""Bake bounded half-frame garment offsets in the master rest space."""
import numpy as np
import runpy
from mathutils.bvhtree import BVHTree

from fit_skirt import PARTS, nearest
from skirt_surface import SIDES, limit_weights

MARGIN = .0019
MAX_GAP = .0282


def sample_indices(motion, stride, include=()):
    clips = motion[0]
    return np.unique(np.r_[0, *(np.flatnonzero(clips == name)[::stride] for name in dict.fromkeys(clips)),
                           *include])


class ContactFit:
    def __init__(self, motion, triangles, pair_ids, selected):
        self.motion = motion
        self.triangles = triangles
        self.polys = triangles.tolist()
        self.pair_ids = pair_ids
        self.selected = selected
        self.bodies = {}
        self.body_polys = motion[3].tolist()
        self.index = np.arange(pair_ids.size//2)
        self.controls = motion[4].shape[1]
        self.rows = pair_ids.shape[0]
        self.other = np.zeros(self.rows*SIDES*2, dtype=np.int32)
        for outward, inward in pair_ids:
            self.other[outward] = outward
            self.other[inward] = outward

    def body(self, frame):
        if frame not in self.bodies:
            self.bodies[frame] = BVHTree.FromPolygons(self.motion[2][frame].tolist(),
                                                      self.body_polys, all_triangles=True)
        return self.bodies[frame]

    def scan(self, points, weights, edges=True, exact=None):
        transforms = self.motion[4][self.selected]
        skin = np.einsum("vk,fkij->fvij",weights,transforms,optimize=True)
        posed = np.einsum("fvij,vj->fvi",skin[:,:,:,:3],points) + skin[:,:,:,3]
        distances = np.empty(posed.shape[:2],dtype=np.float32)
        overlaps = np.zeros(len(posed),dtype=np.int32)
        vertices, normals, gaps, rows = [], [], [], []
        for i, frame in enumerate(self.selected):
            tree = self.body(frame)
            d, _, n, _ = nearest(tree,posed[i])
            clipped = d < MARGIN
            if i == 0 and frame == 0:
                clipped |= d > MAX_GAP
            active = np.flatnonzero(clipped)
            ns, ds = n[active], d[active]
            high = ds > MAX_GAP
            ns[high] *= -1
            ds[high] = MARGIN + MAX_GAP - ds[high]
            distances[i] = d
            garment = BVHTree.FromPolygons(posed[i].tolist(),self.polys,all_triangles=True)
            pairs = tree.overlap(garment)
            overlaps[i] = len(pairs)
            if edges and pairs:
                if exact:
                    hits, blend = exact(posed[i], self.triangles, self.motion[2][frame],
                                        self.motion[3], np.asarray(pairs)[:,::-1])
                    corners = self.triangles[hits]
                    probes = np.einsum("ki,kij->kj",blend,posed[i,corners])
                    ed, _, en, _ = nearest(tree,probes)
                    viable = (ed < MARGIN)
                    use = (blend>.10) & viable[:,None]
                    extra = corners[use]
                    edge_n = np.broadcast_to(en[:,None],(len(en),3,3))[use]
                    edge_d = np.broadcast_to(ed[:,None],(len(ed),3))[use]
                else:
                    hit_faces = np.unique(np.asarray(pairs)[:,1])
                    corners = self.triangles[hit_faces]
                    query = posed[i,corners]
                    probes = np.concatenate((query.mean(axis=1)[:,None,:],
                                            .5*(query+np.roll(query,1,axis=1))),axis=1)
                    ed, _, en, _ = nearest(tree,probes.reshape(-1,3))
                    ed, en = ed.reshape(-1,4),en.reshape(-1,4,3)
                    worst = ed.argmin(axis=1)
                    idx = np.arange(len(corners))
                    idx = idx[ed[idx,worst] < MARGIN]
                    witness = worst[idx]
                    affected = corners[idx]
                    use = (witness[:,None] == 0) | (witness[:,None]-1 == np.arange(3)) | (
                        witness[:,None]-1 == (np.arange(3)+1)%3)
                    extra = affected[use]
                    edge_n = np.broadcast_to(en[idx,witness,None],(len(idx),3,3))[use]
                    edge_d = np.broadcast_to(ed[idx,witness,None],(len(idx),3))[use]
                ns = np.concatenate((ns,edge_n))
                ds = np.concatenate((ds,edge_d))
                active = np.concatenate((active,extra))
            if len(active):
                vertices.append(active)
                normals.append(ns)
                gaps.append(ds)
                rows.append(np.full(len(active),i,dtype=np.int32))
        return distances, overlaps, skin, posed, tuple(map(np.concatenate, (vertices,normals,gaps,rows))) if rows else None

    def smooth(self, delta, angular, vertical):
        grid = delta.reshape(self.rows,SIDES,-1)
        az = .5*(np.roll(grid,1,axis=1)+np.roll(grid,-1,axis=1))
        along = np.concatenate((grid[:1],grid[:-1]))
        across = np.concatenate((grid[1:],grid[-1:]))
        return ((1-angular-vertical)*grid+angular*az+vertical*.5*(along+across)).reshape(delta.shape)

    def corrections(self, result, points, weight_strength, limit=.004, smoothing=1):
        _, _, skin, posed, contact = result
        if contact is None:
            return np.zeros_like(points), np.zeros((len(points),self.controls),dtype=np.float32)
        ids,n,gaps,rows = contact
        transforms = self.motion[4][self.selected]
        j = np.einsum("nij,ni->nj",skin[rows,ids,:,:3],n)
        pp = points[ids]
        motion = transforms[rows]
        relative = motion[:,1:]-motion[:,:1]
        dp = np.einsum("nkij,nj->nki",relative[:,:,:,:3],pp)+relative[:,:,:,3]
        jw = np.einsum("nki,ni->nk",dp,n)*weight_strength
        axes = np.concatenate((j,jw),axis=1).astype(np.float32)
        need = np.clip(MARGIN-gaps,0,.030)
        ids = self.other[ids]
        # Keep one constraint per vertex and solver direction. The strongest
        # pose in the group can drive the offset without duplicate poses
        # burying the opposite constraint.
        keys = np.argmax(np.abs(axes),axis=1)
        keys += axes.shape[1]*(axes[np.arange(len(axes)),keys] < 0)
        group = 2*axes.shape[1]*ids + keys
        order = np.lexsort((-need,group))
        order = order[np.r_[True,np.diff(group[order])!=0]]
        ids,axes,need = ids[order],axes[order],need[order]
        displacement = np.zeros((self.rows*SIDES,axes.shape[1]),dtype=np.float32)
        order = np.argsort(-need)
        for idx in np.array_split(order,10):
            chosen = ids[idx]
            axis = axes[idx]
            lacking = np.maximum(need[idx]-np.einsum("ij,ij->i",axis,displacement[chosen]),0)
            take = lacking / ((axis**2).sum(axis=1)+.05)
            average = np.zeros_like(displacement)
            total = np.zeros(len(displacement),dtype=np.int32)
            np.add.at(average,chosen,take[:,None]*axis)
            np.add.at(total,chosen,take>0)
            displacement += average/np.maximum(total[:,None],1)
        delta = displacement[:,:3]
        delta *= np.minimum(1,limit/np.maximum(np.linalg.norm(delta,axis=1),1e-8))[:,None]
        delta = self.smooth(self.smooth(delta,.32*smoothing,.20*smoothing),.17*smoothing,.10*smoothing)
        raw_dw = np.clip(displacement[:,3:]*weight_strength,-.10,.10)
        raw_dw = self.smooth(raw_dw,.27*smoothing,.15*smoothing)
        dw = np.column_stack((-raw_dw.sum(axis=1),raw_dw))
        return delta[self.other], dw[self.other]

    def constrain_rest(self, points):
        # Work on paired vertices together to keep the thickness and limit
        # measured outward clearance on the actual exterior wall.
        rest = self.body(0)
        for _ in range(5):
            d, _, normals, _ = nearest(rest,points)
            move = np.clip(np.maximum(.0018-d,0)-np.maximum(d-MAX_GAP,0),-.008,.008)
            if max(abs(move)) < .000015:
                break
            delta = np.zeros((self.rows*SIDES,3),dtype=np.float32)
            np.add.at(delta,self.other,move[:,None]*normals)
            points += delta[self.other]
        return points


def measure_score(result):
    distances,pairs = result[:2]
    return float((np.maximum(.00072-distances,0)*1000).sum() + .6*pairs.sum()
                 + 30000*max(0.,float(distances[0].max())-.0295))


def try_seeds(motion, body):
    from fit_skirt import make_tree
    from skirt_surface import build_loft
    rest = make_tree(motion[2][0],motion[3])
    candidates = [
        (.285,1.,1.,.010), (.302,1.,1.,.015), (.315,1.,1.,.015),
        (.297,1.12,1.12,.022), (.308,1.03,.85,.018),
        (.318,1.10,.80,.012), (.326,.93,.68,.010),
        (.294,1.04,.83,.021), (.303,1.12,1.10,.035),
    ]
    selected = sample_indices(motion,17)
    fitter, best, current = None, float("inf"), None
    for values in candidates:
        p,t,w,paired,depth,theta = build_loft(body,rest,*values)
        if fitter is None:
            fitter = ContactFit(motion,t,paired,selected)
        result = fitter.scan(p,w,edges=False)
        d,n = result[:2]
        score = measure_score(result)
        print("SEED", values, round(score,2), "pairs",int(n.sum()),
              "min",round(float(d.min()*1000),3),"rest max",round(float(d[0].max()*1000),3),flush=True)
        if score < best:
            best = score
            current = p,t,w,paired,depth,theta,values
    return current


def optimize(motion, body, checkpoint, iterations, resume=False):
    if resume:
        with np.load(checkpoint) as data:
            points,triangles,weights,paired,depth,theta,parameters = (
                data[key] for key in ("points","triangles","weights","paired","depth","theta","parameters"))
    else:
        points,triangles,weights,paired,depth,theta,parameters = try_seeds(motion,body)
    selected = sample_indices(motion,4)
    fitter = ContactFit(motion,triangles,paired,selected)
    result = fitter.scan(points,weights)
    score = measure_score(result)
    for step in range(iterations+1):
        d,n = result[:2]
        row, vertex = np.unravel_index(d.argmin(),d.shape)
        print("BAKE",step,round(score,3),"pairs",int(n.sum()),"min mm",float(d.min()*1000),
              "rest max mm",float(d[0].max()*1000),"where",motion[0][selected[row]],motion[1][selected[row]],
              "vertex",vertex,flush=True)
        np.savez(checkpoint,points=points,triangles=triangles,weights=weights,paired=paired,
                 depth=depth,theta=theta,parameters=parameters)
        if (d.min() > .0007 and not n.any()) or step == iterations:
            break
        accepted = False
        for strength, step_size in ((8.,1.),(3.,.85),(0.,.91),(8.,.46)):
            dp,dw = fitter.corrections(result,points,strength)
            p = fitter.constrain_rest(points+step_size*dp)
            w = limit_weights(weights+step_size*dw)
            test = fitter.scan(p,w)
            trial = measure_score(test)
            print("TRY",step,strength,step_size,round(trial,3),flush=True)
            if trial < score:
                points,weights,result,score = p,w,test,trial
                accepted = True
                break
        if not accepted:
            break
    return points,triangles,weights,paired,depth,theta,parameters


def fine_optimize(motion, checkpoint, iterations):
    witness = runpy.run_path(str(PARTS/"hoodie-fit-sol/round3/fit_hoodie_round3.py"))["pair_witnesses"]
    with np.load(checkpoint) as data:
        points,triangles,weights,paired,depth,theta,parameters = (
            data[key] for key in ("points","triangles","weights","paired","depth","theta","parameters"))
    all_rows = np.arange(len(motion[0]))
    fitter = ContactFit(motion,triangles,paired,all_rows)

    def save():
        np.savez(checkpoint,points=points,triangles=triangles,weights=weights,paired=paired,
                 depth=depth,theta=theta,parameters=parameters)

    def report(step, result):
        d, p = result[:2]
        r,v = np.unravel_index(d.argmin(),d.shape)
        print("FINE",step,"pairs",int(p.sum()),"below",int((d<.0007).sum()),"minimum mm",
              float(d[r,v]*1000),motion[0][all_rows[r]],motion[1][all_rows[r]],v,flush=True)

    for step in range(iterations):
        fitter.selected = all_rows
        dense = fitter.scan(points,weights,edges=False)
        save()
        report(step,dense)
        d, n = dense[:2]
        if d.min() >= .00070 and not n.any():
            break
        wanted = (d.min(axis=1)<.0022) | (n>0)
        fitter.selected = np.unique(np.r_[0, all_rows[wanted], sample_indices(motion,13)])
        result = fitter.scan(points,weights,exact=witness)
        d, n = result[:2]
        score = measure_score(result)
        best = score
        accepted = None
        for strength,step_size,smoothing in (
            (4.,.86,.60),(8.,.55,.40),(0.,.70,.58),(4.,.38,.13),(0.,.38,.12),
        ):
            dp,dw = fitter.corrections(result,points,strength,limit=.0028,smoothing=smoothing)
            p = fitter.constrain_rest(points+step_size*dp)
            w = limit_weights(weights+step_size*dw)
            trial = fitter.scan(p,w,edges=False)
            value = measure_score(trial)
            print("FINE TRY",step,strength,step_size,smoothing,round(value,4),flush=True)
            if value < best:
                best = value
                accepted = p,w
            if value < .74*score:
                break
        if accepted is None:
            break
        points,weights = accepted
    save()
