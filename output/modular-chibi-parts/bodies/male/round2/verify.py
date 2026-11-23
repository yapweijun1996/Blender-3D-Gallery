"""Fresh Blender verification of the body and both round-one module predicates."""
from collections import defaultdict
import hashlib
import math
import sys

from asset_io import *
from body_audit import frame_grid, load_body_motion, posed, set_frame, use_action
from fit_module import FLOOR, nearest, read_module
from fitting_geometry import arrays, tree, weights
from motion_repair import OUT, FIXED, Contacts, SIDES, is_planted, pair_depth
from modules import MODULES
from refit import unique_vertices

QA = OUT/'qa'


def append_actions(path):
    prior = set(bpy.data.actions)
    imported = import_objects(path)
    actions = {a.name.split('.')[0]:a for a in set(bpy.data.actions)-prior}
    for obj in imported:
        bpy.data.objects.remove(obj,do_unlink=True)
    return actions


def grids(action, fps):
    grids = set(frame_grid(action,fps))
    first,last = action.frame_range
    for rate in (24,30):
        divisor = 2*rate/fps
        grids.update(n/divisor for n in range(math.ceil(first*divisor-1.e-5),
                                             math.floor(last*divisor+1.e-5)+1))
    # Differences below a millionth of a Blender frame are import rounding.
    return sorted({round(f,6) for f in grids})


def motion_audit():
    sc,arm,body,actions = load_body_motion(FIXED)
    sources = append_actions(MOTION)
    use_action(arm,None)
    bpy.context.view_layer.update()
    contact = Contacts(body)
    checker = contact.check
    rest = posed(body)
    out = dict(sha256=hashlib.sha256(FIXED.read_bytes()).hexdigest(),
               rest_pairs=checker.pair_records(rest,sorted(contact.rest)),
               rest_target_pair_count=sum(bool(contact.target(a,b)) for a,b in contact.rest),
               clips={})
    for clip in CLIPS:
        frames = grids(actions[clip],sc.render.fps)
        use_action(arm,sources[clip])
        src = []
        for frame in frames:
            set_frame(sc,frame)
            ref = posed(body)
            hip = arm.pose.bones['mixamorig:Hips'].head.z
            ankles = [arm.pose.bones['mixamorig:'+s+'Foot'].head.copy() for s in SIDES]
            src.append((hip,[float(ref[checker.feet[s],2].min()) for s in SIDES],ankles))
        use_action(arm,actions[clip])
        records, max_sole, max_sole_delta, max_ankle_xz, max_hip, planted = [],0.,0.,0.,0.,0
        region_totals = {}
        for frame,(hip,ref_soles,ankles) in zip(frames,src):
            set_frame(sc,frame)
            pts = posed(body)
            pairs,_ = checker.overlap(pts)
            pairs = [pair for pair in pairs if pair not in contact.rest]
            target = [pair for pair in pairs if contact.target(*pair)]
            stats = checker.pair_records(pts,pairs)
            for label,row in stats.items():
                total = region_totals.setdefault(label,dict(pairs=0,max_depth_mm=-1,frames=0))
                total['pairs'] += row['count']
                total['frames'] += 1
                if row['max_depth_mm']>total['max_depth_mm']:
                    total.update(max_depth_mm=row['max_depth_mm'],frame=frame)
            max_hip = max(max_hip,abs(arm.pose.bones['mixamorig:Hips'].head.z-hip))
            minimum = [float(pts[checker.feet[s],2].min()) for s in SIDES]
            mask = is_planted(clip,np.asarray(ref_soles))
            planted += int(mask.sum())
            for i,s in enumerate(SIDES):
                if mask[i]:
                    max_sole = max(max_sole,abs(minimum[i]))
                    max_sole_delta = max(max_sole_delta,abs(minimum[i]-ref_soles[i]))
                    diff = arm.pose.bones['mixamorig:'+s+'Foot'].head-ankles[i]
                    max_ankle_xz = max(max_ankle_xz,math.hypot(diff.x,diff.y))
            records.append(dict(frame=frame,pairs=len(pairs),target_pairs=len(target),
                                soles_mm=[x*1000 for x in minimum],planted=mask.tolist(),
                                regions={label:{k:v for k,v in row.items() if k!='triangles_and_depth_mm'}
                                         for label,row in stats.items()},
                                target_regions=checker.pair_records(pts,target) if target else {}))
        result = dict(samples=len(frames),planted_samples=planted,planted_height_mm=max_sole*1000,
                      planted_height_change_mm=max_sole_delta*1000,
                      planted_ankle_horizontal_change_mm=max_ankle_xz*1000,hip_height_change_mm=max_hip*1000,
                      total_pairs=sum(r['pairs'] for r in records),
                      peak_pairs=max(r['pairs'] for r in records),
                      target_pairs=sum(r['target_pairs'] for r in records),
                      regions=region_totals,frames=records)
        out['clips'][clip] = result
        write_json(QA/'body.json',out)
        print('BODY',clip,{k:v for k,v in result.items() if k not in ('regions','frames')},flush=True)


def module_path(key):
    return (OUT/f'male-{key}-v2.glb') if key in ('tshirt','dress','jeans') else (HERE/f'male-{key}.glb')


def module_audit(keys, clip_subset=None):
    sc,arm,body,actions = load_body_motion(FIXED)
    names = [b.name for b in arm.data.bones]
    bf = arrays(body)[1]
    bfaces = bf.tolist()
    bgroups = np.asarray(names)[weights(body,names)[bf].sum(axis=1).argmax(axis=1)]
    items = {}
    reports = {}
    motion_sha = hashlib.sha256(FIXED.read_bytes()).hexdigest()
    directory = QA/'modules'
    directory.mkdir(exist_ok=True,parents=True)
    for key in keys:
        path = module_path(key)
        garment = read_module(path,arm)
        coords,f = arrays(garment)
        reps,inverse = unique_vertices(coords,weights(garment,names))
        items[key] = garment,f,f.tolist(),reps,inverse,inverse[f].tolist()
        reports[key] = {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'motion_sha256':motion_sha,'triangles':len(f),'clips':{}}
    for clip in (clip_subset or ('rest',*CLIPS)):
        action = actions.get(clip)
        use_action(arm,action)
        frames = grids(action,sc.render.fps) if action else (0.,)
        samples = {k:[] for k in items}
        for frame in frames:
            set_frame(sc,frame)
            p = posed(body)
            body_bvh = tree(p,bfaces)
            for k,(obj,f,f_list,reps,inverse,compact) in items.items():
                gp = posed(obj)
                unique = gp[reps]
                if np.array_equal(unique[inverse],gp):
                    signed,_,ids = nearest(body_bvh,unique)
                    d,fids = signed[inverse],ids[inverse]
                    pairs = body_bvh.overlap(tree(unique,compact))
                else:
                    d,_,fids = nearest(body_bvh,gp)
                    pairs = body_bvh.overlap(tree(gp,f_list))
                worst = np.argmin(d)
                row = dict(frame=frame,inside=int(np.count_nonzero(d<0)),
                           min_signed_m=float(d[worst]),triangle_pairs=len(pairs))
                if row['min_signed_m']<FLOOR:
                    row.update(worst_vertex=int(worst),body_joint=bgroups[fids[worst]],
                               under_half_mm=int(np.count_nonzero(d<FLOOR)))
                if pairs:
                    a,b = np.asarray(pairs).T
                    depths = pair_depth(p[bf[a]],gp[f[b]])
                    deepest = depths.argmax()
                    row.update(triangle_depth_mm=float(depths[deepest]),triangle_body_joint=bgroups[a[deepest]],
                               triangle_witness=[int(a[deepest]),int(b[deepest])])
                samples[k].append(row)
        summary = []
        for k,rows in samples.items():
            worst = min(rows,key=lambda r:r['min_signed_m'])
            result = dict(samples=len(rows),peak_inside=max(r['inside'] for r in rows),
                          peak_triangle_pairs=max(r['triangle_pairs'] for r in rows),
                          total_inside=sum(r['inside'] for r in rows),
                          total_triangle_pairs=sum(r['triangle_pairs'] for r in rows),
                          min_signed_m=worst['min_signed_m'],minimum_frame=worst['frame'],
                          peak_triangle_depth_mm=max(r.get('triangle_depth_mm',0.) for r in rows),
                          shortfall_samples=sum(r['inside']>0 or r['triangle_pairs']>0 or
                                                r['min_signed_m']<FLOOR for r in rows),frames=rows)
            reports[k]['clips'][clip] = result
            write_json(directory/f'{k}.json',reports[k])
            summary.append((k,result['peak_inside'],result['peak_triangle_pairs'],round(worst['min_signed_m']*1000,4)))
        print('MODULE',clip,summary,flush=True)


if __name__=='__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    if args[0]=='body':
        motion_audit()
    else:
        if '--clips' in args:
            i = args.index('--clips')
            module_audit(args[1:i] or list(MODULES),tuple(args[i+1:]))
        else:
            module_audit(args[1:] or list(MODULES))
