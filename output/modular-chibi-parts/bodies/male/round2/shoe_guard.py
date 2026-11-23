"""Resolve the original sneaker's run-frame proximity with a small shin glide."""
from itertools import product

from motion_repair import *
from fit_module import influences, nearest, read_module
from fitting_geometry import tree


def main():
    _,arm,body,_ = load_body_motion(MOTION)
    target,source,bank = GLB(BODY_PATH),GLB(MOTION),GLB(FIXED)
    engine = Repair(body,target)
    module = read_module(HERE/'male-sneakers.glb',arm)
    shoe,faces = arrays(module)
    names = ['mixamorig:'+name for name in engine.abi.names]
    ids,w = influences(weights(module,names))
    local = np.einsum('vkij,vj->vki',engine.ib[ids],
                      np.column_stack((shoe,np.ones(len(shoe),dtype=np.float32))))*w[:,:,None]
    a,b = [engine.joint('Left',n) for n in ('Leg','Foot')]
    report = []
    witnesses = {row['frame'] for row in json.loads((OUT/'qa/modules/sneakers.json').read_text())
                 ['clips']['run']['frames'] if row['min_signed_m']<.0005 or row['triangle_pairs']}
    out = Writer(skeleton_doc(target))
    out.doc['skins'] = deepcopy(target.doc['skins'])
    for item in out.doc['skins']:
        item['inverseBindMatrices'] = out.accessor(target.accessor(item['inverseBindMatrices']),'MAT4')
    for anim in bank.doc['animations']:
        name = anim['name']
        times = max((bank.accessor(s['input']).ravel() for s in anim['samplers']),key=len)
        data = engine.abi.sample(bank,anim,times)
        if name=='run':
            for frame,state in zip(times*24,zip(*data)):
                if not any(abs(frame-w)<1.e-5 for w in witnesses):
                    continue
                before = engine.abi.world(state)
                ankle = before[b,:3,3].copy()
                g = np.einsum('vkij,vkj->vi',(GLTF_TO_BPY@before)[ids,:3,:],local)
                gtree = tree(g,faces.tolist())
                def quality(candidate):
                    w = engine.abi.world(candidate)
                    pose = engine.posed(w)
                    if engine.c.target_pairs(pose):
                        return -1.
                    sole = min(pose[engine.sole_ids[0],2])
                    original_sole = min(engine.posed(before,engine.sole_ids[0])[:,2])
                    if abs(sole-original_sole)>.0007:
                        return -1.
                    bvh = tree(pose,engine.c.check.faces)
                    if bvh.overlap(gtree):
                        return -1.
                    return float(nearest(bvh,g)[0].min())
                best = quality(state)
                chosen = None
                print('SHOE BASE',frame,best,flush=True)
                for mm in (.06,.10,.16,.24,.36,.52,.78,1.05):
                    for direction in product((-1,0,1),repeat=3):
                        if not any(direction):
                            continue
                        copy = [x.copy() for x in state]
                        slide = normalized(np.asarray(direction,dtype=float))*mm*.001
                        engine.add(copy,before,a,slide)
                        engine.position(copy,engine.abi.world(copy),b,ankle)
                        test = quality(copy)
                        if test>best:
                            best,chosen = test,(copy,slide.copy())
                        if best>=.00058:
                            break
                    if best>=.00058:
                        break
                if chosen is not None:
                    for result,value in zip(state,chosen[0]):
                        result[:] = value
                    report.append([float(frame),best,chosen[1].tolist()])
                    print('SHOE FIX',report[-1],flush=True)
        append_action(out,target,engine.abi,name,times,data)
    path = OUT/'.runtime/motion_shoe.glb'
    out.write(path)
    path.replace(FIXED)
    write_json(OUT/'qa/shoe_guard.json',report)


if __name__=='__main__':
    main()
