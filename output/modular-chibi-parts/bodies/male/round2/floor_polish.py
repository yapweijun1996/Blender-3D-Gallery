"""Bring isolated offset-grid walk contacts onto the ground."""
from motion_repair import *


def main():
    _,_,body,_ = load_body_motion(MOTION)
    target,source,bank = GLB(BODY_PATH),GLB(MOTION),GLB(FIXED)
    repair = Repair(body,target)
    out = Writer(skeleton_doc(target))
    out.doc['skins'] = deepcopy(target.doc['skins'])
    for item in out.doc['skins']:
        item['inverseBindMatrices'] = out.accessor(target.accessor(item['inverseBindMatrices']),'MAT4')
    changes = []
    for clip in bank.doc['animations']:
        name = clip['name']
        times = max((bank.accessor(s['input']).ravel() for s in clip['samplers']),key=len)
        data = repair.abi.sample(bank,clip,times)
        if name=='walk':
            before = next(a for a in source.doc['animations'] if a['name']==name)
            original = repair.abi.sample(source,before,times)
            for i,(frm,state,prior) in enumerate(zip(times,zip(*data),zip(*original))):
                ref = repair.abi.world(prior)
                current = repair.abi.world(state)
                soles = np.array([repair.posed(ref,j)[:,2].min() for j in repair.sole_ids])
                for k,planted in enumerate(is_planted(name,soles)):
                    if not planted:
                        continue
                    pos = repair.posed(current,repair.sole_ids[k])[:,2]
                    if abs(pos.min())<=.00065:
                        continue
                    desired = .00017
                    shift = max((desired-pos)/repair.sole_share[k])
                    repair.add(state,current,repair.ankles[k],np.array([0,shift,0]))
                    changes.append([float(frm*24),SIDES[k],float(pos.min()*1000),float(shift*1000)])
        append_action(out,target,repair.abi,name,times,data)
    path = OUT/'.runtime/motion_floor.glb'
    out.write(path)
    path.replace(FIXED)
    write_json(OUT/'qa/floor_polish.json',changes)
    print('FLOOR',changes,flush=True)


if __name__=='__main__':
    main()
