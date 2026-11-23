"""Restore foot placement while clearing the two ends of a deeply bent shin."""
from collections import Counter
import sys

from motion_repair import *
from gltf_pose import normalized


def shorten(engine,state,side,mm,fraction,spread=0.):
    abi = engine.abi
    w = abi.world(state)
    shin,foot = [engine.joint(side,n) for n in ('Leg','Foot')]
    knee,ankle = w[[shin,foot],:3,3]
    segment = ankle-knee
    length = np.linalg.norm(segment)
    amount = mm*.001
    factor = max(.62,1-amount/length)
    state[2][shin] *= factor
    state[2][foot] /= factor
    shifted = knee + segment*(1-factor)*fraction
    if spread:
        shifted[0] += (1 if side=='Left' else -1)*spread*.001
    engine.position(state,abi.world(state),shin,shifted)
    engine.position(state,abi.world(state),foot,ankle)
    return state


def options(engine,states,reference,clip,side):
    abi = engine.abi
    knee,ankle = side+' knee',side+' ankle'
    best = None
    for mm in (0,1.5,3,4.5,6,8,10,13,16,20,25,31,39):
        for start,prior in enumerate(states):
            for fraction,spread in ((.5,0),(.2,0),(.8,0),(.5,1.5),(.5,-1.5),(.05,0),(.95,0)):
                if not mm and (fraction,spread)!=(.5,0):
                    continue
                candidate = shorten(engine,[v.copy() for v in prior],side,mm,fraction,spread)
                engine.feet(candidate,reference,clip)
                p = engine.posed(abi.world(candidate))
                collisions = [len(engine.c.check_unit(p,u)) for u in (knee,ankle)]
                score = (*collisions, mm+abs(spread)+start)
                if best is None or score<best[0]:
                    best = (score,candidate,(mm,fraction,spread,start))
                if sum(collisions)==0:
                    return best
    return best


def remap(engine,clip,times,pre,source):
    output, failures, params = [],[],[]
    for i,(frame,current,ref) in enumerate(zip(times,zip(*pre),zip(*source))):
        state = [a.copy() for a in current]
        points = engine.posed(engine.abi.world(state))
        trial = []
        for side in SIDES:
            active = [u for u in (side+' knee',side+' ankle') if engine.c.check_unit(points,u)]
            if not active:
                continue
            alt = [a.copy() for a in state]
            indexes = [engine.joint(side,k) for k in ('UpLeg','Leg','Foot')]
            for j in range(3):
                alt[j][indexes] = ref[j][indexes]
            score,state,params_used = options(engine,[state,alt],ref,clip,side)
            trial.append([side,params_used,score[:2]])
            points = engine.posed(engine.abi.world(state))
        if trial:
            params.append([float(frame*24),trial])
        hits = engine.c.target_pairs(points)
        if hits:
            failures.append([float(frame*24),{u:len(v) for u,v in hits.items()}])
        output.append(state)
    return [np.asarray(x) for x in zip(*output)],params,failures


def bank(input_path,output_path,selected,trial_path=None):
    _,_,body,_ = load_body_motion(MOTION)
    target,source,prior = GLB(BODY_PATH),GLB(MOTION),GLB(input_path)
    engine = Repair(body,target)
    trial = GLB(trial_path) if trial_path else None
    polished = {a['name']:a for a in trial.doc['animations']} if trial else {}
    out = Writer(skeleton_doc(target))
    out.doc['skins'] = deepcopy(target.doc['skins'])
    for item in out.doc['skins']:
        item['inverseBindMatrices'] = out.accessor(target.accessor(item['inverseBindMatrices']),'MAT4')
    by_name = {a['name']:a for a in source.doc['animations']}
    reports = {}
    for anim in prior.doc['animations']:
        clip = anim['name']
        bank = trial if clip in selected and clip in polished else prior
        if bank is trial:
            anim = polished[clip]
        # The Hips channel can be constant. Pick the longest input accessor.
        times = max((bank.accessor(s['input']).ravel() for s in anim['samplers']),key=len)
        if clip=='walk':
            t0,end = times[[0,-1]]
            extra = t0 + np.arange(int((end-t0)*60+1.e-5)+1,dtype=np.float32)/60
            sampled = np.sort(np.r_[times,extra])
            times = sampled[np.r_[True,np.diff(sampled)>1.e-6]]
        data = engine.abi.sample(bank,anim,times)
        if clip in selected and bank is prior:
            original = engine.abi.sample(source,by_name[clip],times)
            data,params,failures = remap(engine,clip,times,data,original)
            reports[clip] = dict(samples=len(times),changes=params,remaining=failures)
            print('POLISH',clip,len(params),failures[:30],flush=True)
        append_action(out,target,engine.abi,clip,times,data)
    if reports:
        write_json(OUT/'qa/leg_polish.json',reports)
    out.write(output_path)

if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    trial = OUT/args[2] if len(args)>2 and args[2].endswith('.glb') else None
    selected = args[(3 if trial else 2):] or ('walk','run')
    bank(OUT/args[0],OUT/args[1],set(selected),trial)
