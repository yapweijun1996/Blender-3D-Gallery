"""Audit the selected exports together using a full body BVH at every pose."""
from asset_io import CLIPS, HERE, MALE, MASTER, MOTION, json, np, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import FLOOR, nearest, read_module
from fitting_geometry import arrays, tree, weights
from gate_module import grids, sha

ITEMS = ('shoes-boots','bottom-skirt','bottom-shorts','shoes-sandals','shoes-slipons','shoes-hightop')


def report_clip(samples, references):
    worst = min(samples,key=lambda row:row['min_signed_m'])
    return dict(samples=len(samples), peak_inside=max(r['inside'] for r in samples),
                peak_pairs=max(r['pairs'] for r in samples),
                min_signed_m=worst['min_signed_m'], minimum_frame=worst['frame'],
                layer_peaks={name:max(r['layer_pairs'][name] for r in samples) for name in references},
                frames=samples)


def test():
    scene, arm, body, actions = load_body_motion(MOTION)
    names = [bone.name for bone in arm.data.bones]
    body_faces = arrays(body)[1]
    body_tri = body_faces.tolist()
    labels = np.asarray(names)[weights(body,names)[body_faces].sum(axis=1).argmax(axis=1)]
    refs = {}
    for name in ('male-tshirt.glb','male-jeans.glb'):
        obj = read_module(MALE/name,arm)
        refs[name] = obj, arrays(obj)[1].tolist(), sha(MALE/name)
    reports, items = {},{}
    for item in ITEMS:
        result = json.loads((HERE/'qa'/f'{item}.result.json').read_text())
        path = HERE/(result['picked']['name']+'.glb')
        obj = read_module(path,arm)
        points, faces = arrays(obj)
        skin_weights = weights(obj,names)
        _, reps, remap = np.unique(np.column_stack((points,skin_weights)),axis=0,
                                   return_index=True,return_inverse=True)
        references = list(refs) if item.startswith('shoes-') else ['male-tshirt.glb']
        items[item] = obj, faces.tolist(), references, reps, remap.reshape(-1)
        reports[item] = dict(sha256=sha(path), motion_sha256=sha(MOTION), master_sha256=sha(MASTER),
            body_sha256=sha(MALE/'body_male.glb'), layers_sha256={name:refs[name][2] for name in references},
            body_measurement='full Blender BVH', sampling_fps=[24,30], blender_fps=scene.render.fps,
            triangles=len(faces), bytes=path.stat().st_size, clips={})
    for clip in ('rest',*CLIPS):
        action = actions.get(clip)
        use_action(arm,action)
        frame_rows = {item:[] for item in ITEMS}
        for frame in grids(action,scene.render.fps) if action else [0]:
            set_frame(scene,frame)
            surface = tree(posed(body),body_tri)
            layers = {name:tree(posed(obj),faces) for name,(obj,faces,_) in refs.items()}
            for item,(obj,faces,references,reps,remap) in items.items():
                fit = posed(obj)
                skin = tree(fit,faces)
                compact = fit[reps]
                if np.array_equal(compact[remap],fit):
                    depth,_,index = nearest(surface,compact)
                    depth,index = depth[remap],index[remap]
                else:
                    depth,_,index = nearest(surface,fit)
                vi = int(depth.argmin())
                row = dict(frame=frame, inside=int((depth<0).sum()), min_signed_m=float(depth[vi]),
                           pairs=len(surface.overlap(skin)),
                           layer_pairs={name:len(layers[name].overlap(skin)) for name in references})
                if depth[vi] < FLOOR:
                    row.update(vertex=vi,body_joint=labels[index[vi]])
                if clip=='rest' and item.startswith('shoes-'):
                    reports[item]['rest_sole_mm'] = {side:float(fit[fit[:,0]*sign>0,2].min()*1000)
                        for side,sign in [('left',1),('right',-1)]}
                frame_rows[item].append(row)
        summaries = {}
        for item, rows in frame_rows.items():
            summary = report_clip(rows,items[item][2])
            reports[item]['clips'][clip] = summary
            summaries[item] = (summary['peak_inside'],summary['peak_pairs'],summary['min_signed_m'],
                               max(summary['layer_peaks'].values()))
        print('FULL GATE',clip,summaries,flush=True)
    for item, report in reports.items():
        write_json(HERE/'qa'/f'{item}.full.gate.json',report)


if __name__ == '__main__':
    test()
