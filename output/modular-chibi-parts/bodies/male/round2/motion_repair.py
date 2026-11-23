"""Search collision corrections on the male rig and bake to the original glTF skeleton."""
from collections import Counter
from itertools import combinations_with_replacement
from math import ceil
import hashlib
import sys

from asset_io import *
from body_audit import Checker, load_body_motion, pair_depth
from build_motion import append_action, skeleton_doc
from fitting_geometry import arrays, weights
from gltf_pose import GLTF_TO_BPY, Rig, clock, normalized
from batch_clear import angle_quat, conjugate, qmul, rotate
from mathutils.bvhtree import BVHTree

OUT = HERE/'round2'
BODY_PATH = HERE/'body_male.glb'
FIXED = OUT/'motion_male_fixed.glb'
SIDES = ('Left', 'Right')
BODY_REGIONS = {'Hips','Spine','Spine1','Spine2','Neck','Head','HeadTop_End'}
STATIONARY = {'idle','wave','nod','hold_item','hold_box','hold_bag','take_item'}
SEATED = {'sit_down','sit_idle','stand_up'}


def units_for(a,b):
    units = set()
    for side in SIDES:
        def arm(n):
            return n.startswith(side) and any(p in n for p in ('Arm','Hand','Shoulder'))
        def leg(n):
            return n.startswith(side) and any(p in n for p in ('Leg','Foot','Toe'))
        other = next(s for s in SIDES if s != side)
        def trunk(n):
            return n in BODY_REGIONS or any(n.startswith(s) and any(k in n for k in ('Leg','Foot','Toe')) for s in SIDES)
        if (arm(a) and trunk(b)) or (arm(b) and trunk(a)):
            units.add(side+' arm')
        if {a,b} <= {side+'Shoulder',side+'Arm'}:
            units.add(side+' arm')
        if {a,b} == {side+'Arm',side+'ForeArm'}:
            units.add(side+' elbow')
        if ((a==side+'ForeArm' and b.startswith(side+'Hand')) or
            (b==side+'ForeArm' and a.startswith(side+'Hand'))):
            units.add(side+' wrist')
        if (a==side+'Leg' and b.endswith('UpLeg')) or (b==side+'Leg' and a.endswith('UpLeg')):
            units.add(side+' knee')
        if {a,b} == {side+'Foot',side+'Leg'}:
            units.add(side+' ankle')
    return units


def is_planted(clip, soles):
    low = min(soles)
    if clip in STATIONARY:
        return np.ones(2,dtype=bool)
    if clip in SEATED:
        return soles < max(.013,low+.010)
    return (soles <= .002) | ((low <= .003) & (soles-low < .004))


class Contacts:
    def __init__(self,body):
        self.check = Checker(body)
        c = self.check
        points,_ = arrays(body)
        self.rest = set(c.overlap(points)[0])
        labels = tuple(sorted(set(c.regions)))
        self.regions = np.asarray([labels.index(n) for n in c.regions])
        joints = list(combinations_with_replacement(range(len(labels)),2))
        self.units = tuple(side+' '+part for part in ('knee','ankle','elbow','wrist','arm') for side in SIDES)
        self.groups = {}
        for unit in self.units:
            pairs = [(a,b) for a,b in joints if unit in units_for(labels[a],labels[b])]
            wanted = {a for a,_ in pairs}
            other = {b for _,b in pairs}
            af = np.flatnonzero(np.isin(self.regions,list(wanted)))
            bf = np.flatnonzero(np.isin(self.regions,list(other)))
            valid = np.zeros((len(labels),len(labels)),dtype=bool)
            for a,b in pairs:
                valid[a,b] = True
            ai,ar = np.unique(c.indices[af],return_inverse=True)
            bi,br = np.unique(c.indices[bf],return_inverse=True)
            self.groups[unit] = (af,bf,ai,bi,ar.reshape(-1,3).tolist(),
                                 br.reshape(-1,3).tolist(),valid)
        self.owns = {pair:units_for(*pair) for pair in combinations_with_replacement(labels,2)}
        self.welded = c.surface_sets

    def target(self,a,b):
        return self.owns[tuple(sorted((self.check.regions[a],self.check.regions[b])))]

    def check_unit(self,points,unit):
        aa,bb,ai,bi,af,bf,valid = self.groups[unit]
        first = BVHTree.FromPolygons(points[ai].tolist(),af,all_triangles=True)
        second = BVHTree.FromPolygons(points[bi].tolist(),bf,all_triangles=True)
        found = []
        for i,j in first.overlap(second):
            a,b = aa[i],bb[j]
            if valid[self.regions[a],self.regions[b]] and self.welded[a].isdisjoint(self.welded[b]):
                key = (min(a,b),max(a,b))
                if key not in self.rest:
                    found.append(key)
        return found

    def target_pairs(self,points):
        pairs,_ = self.check.overlap(points)
        hit = {u:[] for u in self.units}
        for a,b in pairs:
            if (a,b) not in self.rest:
                for unit in self.target(a,b):
                    hit[unit].append((a,b))
        return {u:v for u,v in hit.items() if v}


class Repair:
    def __init__(self, body, asset):
        self.abi = Rig(asset)
        self.c = Contacts(body)
        names = ['mixamorig:'+name for name in self.abi.names]
        p,_ = arrays(body)
        self.points = np.column_stack((p,np.ones(len(p),dtype=np.float32)))
        self.w = weights(body,names)
        self.ids = np.argpartition(self.w,-4,axis=1)[:,-4:]
        self.amount = self.w[np.arange(len(p))[:,None],self.ids]
        self.ib = self.abi.inv @ GLTF_TO_BPY.T
        self.local = np.einsum('vkij,vj->vki',self.ib[self.ids],self.points)*self.amount[:,:,None]
        self.hips = self.abi.index['Hips']
        self.ankles = [self.abi.index[s+'Foot'] for s in SIDES]
        self.sole_ids = [self.c.check.feet[side] for side in SIDES]
        self.sole_share = [self.c.check.foot_weights[side] for side in SIDES]

    def posed(self,world,vertices=None):
        ids,local = (self.ids,self.local) if vertices is None else (self.ids[vertices],self.local[vertices])
        axes = (GLTF_TO_BPY @ world)[ids,:3,:]
        return np.einsum('vkij,vkj->vi',axes,local)

    def joint(self,side,key):
        return self.abi.index[side+key]

    def add(self,state,world,j,movement):
        p = self.abi.parent[j]
        state[0][j] += np.linalg.solve(world[p,:3,:3],movement)

    def turn(self,state,world,j,axis,degrees):
        if abs(degrees)<1.e-8 or np.linalg.norm(axis)<1.e-8:
            return
        p = self.abi.parent[j]
        parent = world[p,:3,:3]
        local = normalized(np.linalg.solve(parent,axis))
        state[1][j] = normalized(qmul(angle_quat(local,degrees),state[1][j]))

    def position(self,state,w,j,goal):
        self.add(state,w,j,goal-w[j,:3,3])

    def apply(self,state,unit,option):
        side,part = unit.split()
        value,variant = option
        limb = ('UpLeg','Leg','Foot','ToeBase') if part in ('knee','ankle') else ('Arm','ForeArm','Hand','HandMiddle1')
        a,b,c,d = [self.joint(side,k) for k in limb]
        w = self.abi.world(state)
        first,middle,last,end = w[[a,b,c,d],:3,3]
        u,v,tail = (normalized(y-x) for x,y in ((first,middle),(middle,last),(last,end)))
        lateral = np.array([1. if side=='Left' else -1.,0.,0.])
        if part=='arm':
            outward = lateral if variant<2 else normalized(lateral+np.array([0.,0.,1. if variant==2 else -1.]))
            axis = np.cross(u,outward) if variant!=1 else np.cross(normalized(last-first),outward)
            axis = normalized(axis)
            self.add(state,w,a,outward*min(.012,value*.00055))
            self.turn(state,w,a,axis,value)
            self.turn(state,self.abi.world(state),b,axis,-value*(.90 if variant!=1 else .42))
        elif part in ('elbow','wrist'):
            joint,child,prior,after = (b,c,u,v) if part=='elbow' else (c,d,v,tail)
            axis = normalized(np.cross(prior,after))
            bisector = normalized(prior+after)
            if variant in (0,2):
                self.turn(state,w,joint,axis,-value)
                if part=='elbow':
                    self.turn(state,self.abi.world(state),child,axis,value*.82)
            if variant in (1,2):
                merge = value*.001 if variant==1 else value*.00035
                self.add(state,self.abi.world(state),joint,bisector*merge)
                if part=='elbow':
                    self.add(state,self.abi.world(state),child,-bisector*merge*.45)
            if variant in (3,4):
                sideways = normalized(np.cross(prior,axis)) * (1 if variant==3 else -1)
                self.add(state,w,joint,sideways*value*.001)
            if variant==5:
                # Decouple joint spacing from wrist reach for tight inner folds.
                self.add(state,w,joint,-after*value*.001)
                if part=='elbow':
                    self.add(state,self.abi.world(state),child,after*value*.00065)
        elif part=='knee':
            delta = normalized(u+v)*value*.001
            if variant in (0,1):
                upper = -delta*(.10 if variant==0 else .30)
                lower = delta*(.60 if variant==0 else .95)
                self.add(state,w,a,upper)
                self.add(state,self.abi.world(state),b,lower-upper)
            elif variant in (2,3):
                upper = -delta*.10
                lower = delta*.64
                for joint,direction,goal,shift in ((a,u,middle-first-.30*delta,first+upper),
                                                    (b,v,last-middle-.45*delta,middle+lower)):
                    updated = self.abi.world(state)
                    new = normalized(goal)
                    self.turn(state,updated,joint,np.cross(direction,new),
                              np.rad2deg(np.arccos(np.clip(np.dot(direction,new),-1,1))))
                    state[2][joint] *= np.linalg.norm(goal)/np.linalg.norm(middle-first if joint==a else last-middle)
                    self.position(state,self.abi.world(state),joint,shift)
                # Recover the original world ankle rotation and size in local TRS.
                from mathutils import Matrix
                updated = self.abi.world(state)
                m = np.linalg.solve(updated[b],w[c])
                _,q,s = Matrix(m).decompose()
                state[1][c] = (q.x,q.y,q.z,q.w)
                state[2][c] = s
            else:
                lateral_shift = lateral*value*.001 * (1 if variant==4 else -1)
                self.add(state,w,b,lateral_shift)
            self.position(state,self.abi.world(state),c,last)
        elif part=='ankle':
            # Keep the foot and toes in their original world transform and
            # slide the shin surface away from the ankle crease.
            radial = (v if variant==0 else normalized(v+tail) if variant==1 else lateral)
            self.add(state,w,b,-radial*value*.001)
            self.position(state,self.abi.world(state),c,last)
        return state

    def solve_option(self,state,unit,pairs,max_options=None):
        part = unit.split()[1]
        values,variants = {
            'arm':((2,4,6,9,13,18,25,35,45,60),4),
            'elbow':((2,4,6,8,11,15,20,26,34,43,54),6),
            'wrist':((2,4,6,8,11,15,20,26,34,43,54),6),
            'knee':((1,2,3,5,7,10,13,17,22,28,35,45,58,72),6),
            'ankle':((1,2,3,5,7,10,13,17,22,28,35,45),3)}[part]
        best = (len(pairs),0,None)
        for value in values:
            candidates = []
            for variant in range(variants):
                if max_options is not None and variant not in max_options:
                    continue
                if part in ('elbow','wrist') and variant in (1,3,4,5) and value>15:
                    continue
                option = (value,variant)
                candidate = self.apply([x.copy() for x in state],unit,option)
                pts = self.posed(self.abi.world(candidate))
                now = self.c.check_unit(pts,unit)
                if len(now)<best[0]:
                    best = (len(now),value,option)
                if not now:
                    return option
        return best[2]

    def feet(self,state,source,clip):
        original = self.abi.world(source)
        old = np.array([self.posed(original,ids)[:,2].min() for ids in self.sole_ids])
        for i,planted in enumerate(is_planted(clip,old)):
            if not planted:
                continue
            ids = self.sole_ids[i]
            w = self.abi.world(state)
            pos = self.posed(w,ids)[:,2]
            target = np.clip(old[i],-.00025,.00025)
            offset = max((target-pos)/self.sole_share[i])
            if abs(offset)>5.e-6:
                self.add(state,w,self.ankles[i],np.array([0,offset,0]))
        return state


def all_times(motion,anim):
    base = clock(motion,anim)
    return base


def smooth_track(t, options, part):
    values = np.array([x[0] if x else 0 for x in options],dtype=float)
    variants = np.array([x[1] if x else -1 for x in options])
    live = np.flatnonzero(values)
    best = (values.copy(),variants.copy())
    if not len(live):
        return [None]*len(t)
    # Borrow from the nearest correction. Across a transition the independent
    # exact-sample pass resolves any new contact using the unsmoothed solution.
    for i in range(len(t)):
        j = live[np.argmin(abs(t[i]-t[live]))]
        if i not in live:
            variants[i] = variants[j]
    speeds = {'arm':72,'elbow':115,'wrist':115,'knee':95,'ankle':105}
    for j in sorted(set(variants)):
        selected = np.flatnonzero((variants==j)&(values>0))
        if not len(selected):
            continue
        dist = abs(t[:,None]-t[selected][None,:])
        support = (values[selected] + (.55 if part!='ankle' else .35) - speeds[part]*dist).max(axis=1)
        use = (variants==j)&(support>0)
        best[0][use] = np.maximum(values[use],support[use])
    return [(float(v),int(j)) if v>0 else None for v,j in zip(*best)]


def main():
    _,arm,body,_ = load_body_motion(MOTION)
    target,source = GLB(BODY_PATH),GLB(MOTION)
    engine = Repair(body,target)
    report = {'rest_pairs':sorted(engine.c.rest),'clips':{}}
    out = Writer(skeleton_doc(target))
    out.doc['skins'] = deepcopy(target.doc['skins'])
    for item in out.doc['skins']:
        item['inverseBindMatrices'] = out.accessor(target.accessor(item['inverseBindMatrices']),'MAT4')
    resume = '--resume' in sys.argv
    checkpoint = OUT/'.runtime/motion_partial.glb'
    partial = OUT/('.runtime/motion_resumed.glb' if resume else '.runtime/motion_partial.glb')
    previous = GLB(checkpoint) if resume and checkpoint.exists() else None
    prior = {a['name']:a for a in previous.doc['animations']} if previous else {}
    if prior:
        report['clips'] = json.loads((OUT/'qa/motion_search.json').read_text())['clips']
    for anim in source.doc['animations']:
        clip = anim['name']
        if clip in prior:
            old = prior[clip]
            times = max((previous.accessor(s['input']).ravel() for s in old['samplers']),key=len)
            append_action(out,target,engine.abi,clip,times,engine.abi.sample(previous,old,times))
            continue
        times = all_times(source,anim)
        source_tracks = engine.abi.sample(source,anim,times)
        options = {u:[] for u in engine.c.units}
        before = Counter()
        for fr,row in zip(times,zip(*source_tracks)):
            state = [x.copy() for x in row]
            hits = engine.c.target_pairs(engine.posed(engine.abi.world(state)))
            before.update({u:len(v) for u,v in hits.items()})
            for unit in engine.c.units:
                active = hits.get(unit)
                choice = engine.solve_option(state,unit,active) if active else None
                options[unit].append(choice)
                if choice:
                    engine.apply(state,unit,choice)
        print('SEARCH',clip,len(times),dict(before), {u:dict(Counter(x[1] for x in v if x)) for u,v in options.items() if any(v)},flush=True)
        track = {u:smooth_track(times,v,u.split()[1]) for u,v in options.items()}
        output = []
        after = Counter()
        failures = []
        for i,(fr,row) in enumerate(zip(times,zip(*source_tracks))):
            state = [x.copy() for x in row]
            for unit in engine.c.units:
                if track[unit][i]:
                    engine.apply(state,unit,track[unit][i])
            engine.feet(state,row,clip)
            for trial in range(3):
                hits = engine.c.target_pairs(engine.posed(engine.abi.world(state)))
                if not hits:
                    break
                for unit,pairs in hits.items():
                    choice = engine.solve_option(state,unit,pairs)
                    if choice:
                        engine.apply(state,unit,choice)
                engine.feet(state,row,clip)
            hits = engine.c.target_pairs(engine.posed(engine.abi.world(state)))
            if hits:
                after.update({u:len(v) for u,v in hits.items()})
                failures.append([float(fr*24),{u:len(v) for u,v in hits.items()}])
            output.append(state)
        data = [np.asarray(x) for x in zip(*output)]
        append_action(out,target,engine.abi,clip,times,data)
        report['clips'][clip] = dict(samples=len(times),target_before=dict(before),target_after=dict(after),
                                     search=options,correction=track,remaining=failures)
        print('BAKE',clip,'before',dict(before),'after',dict(after),'failures',failures[:20],flush=True)
        write_json(OUT/('qa/motion_search_resumed.json' if resume else 'qa/motion_search.json'),report)
        out.write(partial)
    partial.replace(OUT/'.runtime/motion_base.glb')

if __name__=='__main__':
    main()
