"""Apply the supplied signed-vertex and triangle predicates with direct Blender evaluation.

This batches the two original predicates on the same pose and shares the exact
body BVH across modules. It emits the same maximum counts and minimum signed
distance without invoking the original Workbench preview.
"""
from collections import defaultdict
import hashlib
import math
import sys

from asset_io import *
from body_audit import frame_grid, load_body_motion, posed, set_frame, use_action, pair_depth
from fit_module import FLOOR, nearest, read_module
from fitting_geometry import arrays, region, tree, weights
from modules import MODULES


def measure():
    scene,arm,body,actions = load_body_motion(MOTION)
    names = [b.name for b in arm.data.bones]
    bf = arrays(body)[1]
    body_faces = bf.tolist()
    body_groups = np.asarray(names)[weights(body,names)[bf].sum(axis=1).argmax(axis=1)]
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    targets = {}
    for name in args or list(MODULES):
        path = HERE/f'male-{name}.glb'
        garment = read_module(path,arm)
        gf = arrays(garment)[1]
        slot = MODULES[name][1]
        zones = ['head' if slot=='hair' else region(names[i]) for i in weights(garment,names).argmax(axis=1)]
        targets[name] = garment,gf,gf.tolist(),zones
    directory = HERE/'qa/direct'
    directory.mkdir(exist_ok=True)
    report = {name:dict(sha256=hashlib.sha256((HERE/f'male-{name}.glb').read_bytes()).hexdigest(),
                        motion_sha256=hashlib.sha256(MOTION.read_bytes()).hexdigest(),clips={})
              for name in targets}
    for clip in ('rest',*CLIPS):
        action = actions.get(clip)
        use_action(arm,action)
        if action:
            first,last = action.frame_range
            divisor = 2*(24 if clip in LEGACY else 30)/scene.render.fps
            ticks = range(math.ceil(first*divisor-1e-5),math.floor(last*divisor+1e-5)+1)
            frames = sorted({float(first),float(last),*(i/divisor for i in ticks)})
        else:
            frames = [1.]
        samples = {name:dict(samples=len(frames),max_vertices_inside=0,max_tri_pairs=0,
                             total_vertices_inside=0,total_tri_pairs=0,minimum_m=1.,
                             max_triangle_depth_mm=0,shortfall_samples=0,zones={}) for name in targets}
        for fr in frames:
            set_frame(scene,fr)
            b = posed(body)
            body_tree = tree(b,body_faces)
            for name,(item,gf,faces,zones) in targets.items():
                points = posed(item)
                distances,_,face_ids = nearest(body_tree,points)
                overlap = body_tree.overlap(tree(points,faces))
                verts = int(np.count_nonzero(distances<0))
                pairs = len(overlap)
                i = int(distances.argmin())
                mn = float(distances[i])
                row = samples[name]
                row['max_vertices_inside'] = max(row['max_vertices_inside'],verts)
                row['max_tri_pairs'] = max(row['max_tri_pairs'],pairs)
                row['total_vertices_inside'] += verts
                row['total_tri_pairs'] += pairs
                row['shortfall_samples'] += int(mn<FLOOR or pairs>0)
                if mn<row['minimum_m']:
                    row.update(minimum_m=mn,frame=round(fr,5),zone=zones[i],
                               body_joint=body_groups[face_ids[i]],vertex=i)
                for v in np.flatnonzero(distances<FLOOR):
                    zone = zones[v]
                    if zone not in row['zones'] or distances[v]<row['zones'][zone]['minimum_m']:
                        row['zones'][zone] = dict(minimum_m=float(distances[v]),frame=round(fr,5),
                                                  body_joint=body_groups[face_ids[v]])
                if pairs:
                    a,c = np.asarray(overlap).T
                    d = pair_depth(b[bf[a]],points[gf[c]])
                    k = int(d.argmax())
                    if d[k]>=row['max_triangle_depth_mm']:
                        row.update(max_triangle_depth_mm=float(d[k]),triangle_zone=zones[gf[c[k],0]],
                                   triangle_frame=round(fr,5),triangle_body_joint=body_groups[a[k]])
        for name,row in samples.items():
            report[name]['clips'][clip] = row
            final = directory/f'male-{name}.json'
            temp = final.with_suffix('.tmp')
            write_json(temp,report[name])
            temp.replace(final)
        print('DIRECT',clip,[(name,row['max_vertices_inside'],row['max_tri_pairs'],
                             round(row['minimum_m']*1000,4)) for name,row in samples.items()],flush=True)


if __name__=='__main__':
    measure()
