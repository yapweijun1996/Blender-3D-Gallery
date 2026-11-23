"""Reimport the exact candidate and measure every pose using Blender's armature."""
import hashlib
import math
from pathlib import Path
import sys

from asset_io import CLIPS, HERE, MALE, MOTION, bpy, np, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import FLOOR, nearest, read_module
from fitting_geometry import arrays, tree, weights


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grids(action, fps):
    first, last = map(float, action.frame_range)
    frames = {first, last}
    for rate in (24, 30):
        divisor = 2 * rate / fps
        frames.update(n / divisor for n in range(math.ceil(first * divisor - 1e-5),
                                                 math.floor(last * divisor + 1e-5) + 1))
    return sorted({round(min(last, max(first, f)), 6) for f in frames})


def bounded_tree(points, faces, query, padding):
    lower, upper = query.min(axis=0)-padding, query.max(axis=0)+padding
    if (points.max(axis=0)<lower).any() or (points.min(axis=0)>upper).any():
        return None, np.empty(0,dtype=np.int32)
    triangles = points[faces]
    keep = np.flatnonzero(((triangles >= lower).any(axis=1) &
                           (triangles <= upper).any(axis=1)).all(axis=1))
    if not len(keep):
        return None, keep
    selected = faces[keep]
    ids, inverse = np.unique(selected, return_inverse=True)
    return tree(points[ids], inverse.reshape(-1,3).tolist()), keep


def body_measure(points, triangles, fit, fit_tree, representatives, inverse):
    surface = tree(points, triangles)
    query = fit[representatives]
    if not np.array_equal(query[inverse],fit):
        query, inverse = fit, slice(None)
    depth, _, ids = nearest(surface,query)
    return depth[inverse],ids[inverse],len(surface.overlap(fit_tree))


def measure(path, item):
    scene, arm, body, actions = load_body_motion(MOTION)
    target = read_module(path, arm)
    names = [b.name for b in arm.data.bones]
    body_faces = arrays(body)[1]
    body_triangles = body_faces.tolist()
    body_labels = np.array(names)[weights(body, names)[body_faces].sum(axis=1).argmax(axis=1)]
    points, faces = arrays(target)
    _, representatives, inverse = np.unique(np.column_stack((points,weights(target,names))),
        axis=0,return_index=True,return_inverse=True)
    inverse = inverse.reshape(-1)
    target_tri = faces.tolist()
    target_labels = np.array(names)[weights(target, names)[faces].sum(axis=1).argmax(axis=1)]
    references = ['male-tshirt.glb']
    if item.startswith('shoes-'):
        references.append('male-jeans.glb')
    layers = {}
    for file in references:
        layer = read_module(MALE / file, arm)
        layers[file] = layer, arrays(layer)[1]
    report = dict(sha256=sha(path), motion_sha256=sha(MOTION),
                  body_sha256=sha(MALE/'body_male.glb'), master_sha256=sha(MALE/'master_male.blend'),
                  layers_sha256={file:sha(MALE/file) for file in references},
                  body_measurement='full Blender BVH', sampling_fps=[24, 30], blender_fps=scene.render.fps,
                  triangles=len(faces), bytes=path.stat().st_size, clips={})
    for clip in ('rest', *CLIPS):
        action = None if clip == 'rest' else actions[clip]
        use_action(arm, action)
        samples = []
        for frame in grids(action, scene.render.fps) if action else [0]:
            set_frame(scene, frame)
            fit = posed(target)
            skin = tree(fit, target_tri)
            depth, nearest_id, pairs = body_measure(posed(body), body_triangles, fit, skin, representatives, inverse)
            worst = int(depth.argmin())
            row = dict(frame=frame, inside=int((depth < 0).sum()), pairs=pairs,
                       min_signed_m=float(depth[worst]), layer_pairs={})
            if depth[worst] < FLOOR:
                row.update(vertex=worst, body_joint=body_labels[nearest_id[worst]])
            for file, (obj, triangles) in layers.items():
                layer_points = posed(obj)
                surface, _ = bounded_tree(layer_points, triangles, fit, 0)
                collisions = surface.overlap(skin) if surface is not None else []
                row['layer_pairs'][file] = len(collisions)
                if collisions:
                    _, garment_face = collisions[0]
                    row.setdefault('layer_witness', {})[file] = dict(
                        triangle=garment_face, joint=target_labels[garment_face],
                        rest_center_m=points[faces[garment_face]].mean(axis=0).tolist())
            if clip == 'rest' and item.startswith('shoes-'):
                report['rest_sole_mm'] = {side:float(fit[(fit[:,0]*sign)>0,2].min()*1000)
                                          for side,sign in [('left',1),('right',-1)]}
            samples.append(row)
        worst_row = min(samples, key=lambda r:r['min_signed_m'])
        result = dict(samples=len(samples), peak_inside=max(r['inside'] for r in samples),
                      peak_pairs=max(r['pairs'] for r in samples),
                      min_signed_m=worst_row['min_signed_m'], minimum_frame=worst_row['frame'],
                      layer_peaks={file:max(r['layer_pairs'][file] for r in samples) for file in references},
                      frames=samples)
        report['clips'][clip] = result
        print('GATE', clip, {k:v for k,v in result.items() if k!='frames'}, flush=True)
    return report


if __name__ == '__main__':
    path, item, report = sys.argv[sys.argv.index('--')+1:]
    write_json(Path(report), measure(Path(path), item))
