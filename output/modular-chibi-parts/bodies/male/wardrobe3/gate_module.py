"""Reimport the candidate and check all sampled Blender poses."""
import hashlib
import math

from asset_io import CLIPS, MALE, MASTER, MOTION, np
from body_audit import frame_grid, set_frame, use_action, posed
from fit_module import nearest, read_module, FLOOR
from fitting_geometry import arrays, tree, weights


SHIPPED = MALE.parents[3]/'models/chibi-dressup/modules'
JEANS = SHIPPED/'male-bottom-jeans.glb'
SHIRT = SHIPPED/'male-top-tshirt.glb'
SNEAKERS = SHIPPED/'male-shoes-sneakers.glb'
BODY = MALE/'body_male.glb'


def companions(item):
    if item.startswith('top'):
        return JEANS, SNEAKERS
    if item.startswith('bottom'):
        return SHIRT, SNEAKERS
    return JEANS, SHIRT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grids(action, fps):
    first, last = map(float, action.frame_range)
    frames = set(frame_grid(action,fps))
    for rate in (24, 30):
        divisor = 2 * rate / fps
        frames.update(n / divisor for n in range(math.ceil(first * divisor - 1e-5),
                                                 math.floor(last * divisor + 1e-5) + 1))
    return sorted({round(min(last, max(first, f)), 6) for f in frames})


def poses(scene, arm, actions):
    for clip in ('rest', *CLIPS):
        action = actions.get(clip)
        if clip != 'rest':
            assert action is not None, clip
        use_action(arm, action)
        for frame in grids(action,scene.render.fps) if action else [0.]:
            set_frame(scene, frame)
            yield clip, frame


def summarize(samples, refs):
    worst = min(samples,key=lambda row:row['min_signed_m'])
    return dict(samples=len(samples), peak_inside=max(r['inside'] for r in samples),
                peak_pairs=max(r['pairs'] for r in samples), min_signed_m=worst['min_signed_m'],
                worst_frame=worst['frame'],
                layer_peaks={name:max(r['layer_pairs'][name] for r in samples) for name in refs},
                frames=samples)


def measure(path, scene, arm, master_body, body, actions, layers):
    target = read_module(path, arm)
    names = [b.name for b in arm.data.bones]
    body_faces = arrays(body)[1].tolist()
    points, faces = arrays(target)
    face_list = faces.tolist()
    skin = weights(target,names)
    _, unique, inverse = np.unique(np.column_stack((points,skin)),axis=0,
                                    return_index=True,return_inverse=True)
    inverse = inverse.reshape(-1)
    triangles = {name:arrays(obj)[1].tolist() for name,obj in layers.items()}
    report = dict(sha256=sha(path), motion_sha256=sha(MOTION), body_sha256=sha(BODY),
                  master_sha256=sha(MASTER),
                  layers_sha256={name:sha(SHIPPED/name) for name in layers},
                  sampling_fps=[24,30], frame_grid="timeline and clip-relative", blender_fps=scene.render.fps,
                  triangles=len(faces), bytes=path.stat().st_size,
                  max_influences=int((skin>0).sum(axis=1).max()), joints=len(names), clips={})
    rows = {}
    delta = 0.
    for clip, frame in poses(scene,arm,actions):
        if clip not in rows:
            print('GATE',path.stem,clip,flush=True)
        body_points = posed(body)
        delta = max(delta,float(np.max(abs(body_points-posed(master_body)))))
        surface = tree(body_points,body_faces)
        fit = posed(target)
        target_tree = tree(fit,face_list)
        compact = fit[unique]
        if np.array_equal(compact[inverse],fit):
            depth,*_ = nearest(surface,compact)
            depth = depth[inverse]
        else:
            depth,*_ = nearest(surface,fit)
        pairs = surface.overlap(target_tree)
        layer_pairs, layer_witness = {}, {}
        for name,obj in layers.items():
            p = posed(obj)
            separate = (p.max(axis=0)<fit.min(axis=0)).any() or (fit.max(axis=0)<p.min(axis=0)).any()
            collisions = [] if separate else target_tree.overlap(tree(p,triangles[name]))
            layer_pairs[name] = len(collisions)
            if collisions:
                touched = np.unique(np.array(collisions)[:,0])[:4]
                layer_witness[name] = points[faces[touched]].mean(axis=1).tolist()
        row = dict(frame=frame, inside=int((depth<0).sum()), min_signed_m=float(depth.min()),
                   pairs=len(pairs), layer_pairs=layer_pairs)
        if layer_witness:
            row['layer_witness_m'] = layer_witness
        if depth.min()<FLOOR:
            row['worst_position_m'] = points[int(depth.argmin())].tolist()
        if pairs:
            row['overlap_centers_m'] = points[faces[np.unique(np.array(pairs)[:,1])[:6]]].mean(axis=1).tolist()
        rows.setdefault(clip,[]).append(row)
    report['clips'] = {clip:summarize(group,layers) for clip,group in rows.items()}
    report['master_body_max_coordinate_delta_m'] = delta
    report['samples'] = sum(len(group) for group in rows.values())
    assert delta < 1e-5, delta
    return report,target
