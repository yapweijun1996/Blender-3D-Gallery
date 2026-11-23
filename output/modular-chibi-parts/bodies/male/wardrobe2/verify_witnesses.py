"""Replay selected gate witnesses with full, uncropped BVH trees."""
from asset_io import HERE, MALE, MOTION, bpy, json, np, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import nearest, read_module
from fitting_geometry import arrays, tree
from gate_module import sha

ITEMS = ('shoes-boots','bottom-skirt','bottom-shorts','shoes-sandals','shoes-slipons','shoes-hightop')


def mesh(arm, path):
    obj = read_module(path, arm)
    return obj, arrays(obj)[1].tolist()


def replay():
    scene, arm, body, actions = load_body_motion(MOTION)
    body_faces = arrays(body)[1].tolist()
    references = {name:mesh(arm,MALE/name) for name in ('male-tshirt.glb','male-jeans.glb')}
    result = {}
    for item in ITEMS:
        gate = json.loads((HERE/'qa'/f'{item}.gate.json').read_text())
        run = json.loads((HERE/'qa'/f'{item}.result.json').read_text())
        path = HERE/(run['picked']['name']+'.glb')
        assert sha(path)==gate['sha256']
        obj, faces = mesh(arm,path)
        samples, delta = 0, 0.
        discrepancies = []
        for clip,data in gate['clips'].items():
            rows = data['frames']
            targets = [min(rows,key=lambda r:r['min_signed_m']), max(rows,key=lambda r:r['pairs']),
                       max(rows,key=lambda r:r['inside'])]
            targets.extend(max(rows,key=lambda r:r['layer_pairs'][key]) for key in data['layer_peaks'])
            use_action(arm,actions.get(clip))
            for frame, row in {r['frame']:r for r in targets}.items():
                set_frame(scene,frame)
                fit = posed(obj)
                garment = tree(fit,faces)
                target = tree(posed(body),body_faces)
                distances,_,_ = nearest(target,fit)
                error = abs(float(distances.min())-row['min_signed_m'])
                delta = max(delta,error)
                inside = int(np.count_nonzero(distances<0))
                body_pairs = len(target.overlap(garment))
                layer_pairs = {}
                for name in row['layer_pairs']:
                    reference,tri = references[name]
                    layer_pairs[name] = len(tree(posed(reference),tri).overlap(garment))
                if (inside!=row['inside'] or body_pairs!=row['pairs'] or error>=.00001
                        or layer_pairs!=row['layer_pairs']):
                    discrepancies.append(dict(clip=clip,frame=frame,
                        minimum_m=float(distances.min()), expected_min_m=row['min_signed_m'],
                        inside=inside, expected_inside=row['inside'], body_pairs=body_pairs,
                        expected_body_pairs=row['pairs'], layer_pairs=layer_pairs,
                        expected_layer_pairs=row['layer_pairs']))
                samples += 1
        result[item] = dict(sha256=sha(path), witnesses=samples, max_signed_delta_m=delta,discrepancies=discrepancies)
        bpy.data.objects.remove(obj,do_unlink=True)
        print('REPLAY',item,result[item],flush=True)
    write_json(HERE/'qa/witness-replay.json',result)


if __name__=='__main__':
    replay()
