"""Fit the jeans waistband under the accepted T-shirt on the shared rig."""
import json
from hashlib import sha256

import numpy as np

from asset_io import bpy, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import FLOOR, nearest, read_module
from fitting_geometry import arrays, laplacian, tree, weld_graph
from fit_round3 import OUT, smoothstep
from motion_repair import FIXED
from verify_round3 import module_path

LAYER_FRAMES = (('rest', 0.), ('idle', 24.))
GUARDS = (('walk', 9.), ('run', 0.5), ('run', 3.), ('run', 12.),
          ('sit_down', 20.5), ('sit_idle', 56.8), ('stand_up', 11.2))


def fit_waist():
    scene, arm, body, actions = load_body_motion(FIXED)
    path = module_path('jeans')
    jeans = read_module(path, arm)
    shirt = read_module(module_path('tshirt'), arm)
    start, tris = arrays(jeans)
    graph = weld_graph(start, tris)
    body_tri = arrays(body)[1].tolist()
    shirt_tri = arrays(shirt)[1].tolist()
    jean_tri = tris.tolist()
    center = np.asarray(arm.data.bones['mixamorig:Hips'].head_local)
    radial = start - center
    radial[:, 2] = 0.
    radial /= np.linalg.norm(radial, axis=1, keepdims=True).clip(.001, None)
    height = smoothstep((start[:, 2] - .373) / .023)
    touched = np.zeros(len(start), dtype=float)
    history = []

    def evaluate(points, collect=False, guards=False):
        jeans.data.vertices.foreach_set('co', np.asarray(points, dtype=np.float32).ravel())
        jeans.data.update()
        counts, minimum, body_pairs, waist_min = [], [], [], []
        for clip, frame in (*LAYER_FRAMES, *(GUARDS if guards else ())):
            use_action(arm, actions.get(clip))
            set_frame(scene, frame)
            pants = posed(jeans)
            jean_bvh = tree(pants, jean_tri)
            body_bvh = tree(posed(body), body_tri)
            if clip in ('rest', 'idle'):
                hits = jean_bvh.overlap(tree(posed(shirt), shirt_tri))
                counts.append(len(hits))
                if collect and hits:
                    touched[tris[np.asarray(hits)[:, 0]].ravel()] = 1.
            clearance, _, _ = nearest(body_bvh, pants)
            minimum.append(float(clearance.min()))
            waist_min.append(float(clearance[height > 0.].min()))
            body_pairs.append(len(jean_bvh.overlap(body_bvh)))
        return counts, minimum, body_pairs, waist_min

    baseline = evaluate(start, collect=True, guards=True)
    print('WAIST BASELINE', baseline, flush=True)
    if sum(baseline[0]) == 0:
        return

    def preserves_clearance(result):
        return (all(a <= b for a, b in zip(result[2], baseline[2]))
                and all(a >= min(FLOOR, b) - 1.e-6 for a, b in zip(result[1], baseline[1]))
                and all(a >= min(FLOOR, b) - 1.e-6 for a, b in zip(result[3], baseline[3])))

    regional = touched.copy()
    for _ in range(6):
        regional = np.maximum(regional, laplacian(regional, graph) * .92)
    local = height * np.minimum(1., regional * 1.35)
    target = start.copy()
    best = (sum(baseline[0]), 0.)
    for mask, label in ((local, 'local'), (height, 'waist')):
        for lift in (0., .002, -.002, -.004, -.006):
            for inset in (.001, .002, .003, .004, .005, .0065, .008, .010, .012):
                move = -radial * (mask * inset)[:, None]
                move[:, 2] += lift * mask
                trial = start + move
                result = evaluate(trial)
                rank = (sum(result[0]), float(np.linalg.norm(move, axis=1).max()))
                if rank >= best or not preserves_clearance(result):
                    continue
                guarded = evaluate(trial, guards=True)
                if not preserves_clearance(guarded):
                    continue
                best, target = rank, trial.copy()
                history.append(dict(mask=label, inset_mm=inset * 1000, vertical_mm=lift * 1000,
                                    layer_pairs=guarded[0], guide_minima_m=guarded[1]))
                print('WAIST CANDIDATE', history[-1], flush=True)
                if best[0] == 0:
                    break
            if best[0] == 0:
                break
        if best[0] == 0:
            break
    if not history:
        return

    use_action(arm, None)
    set_frame(scene, 0.)
    jeans.data.vertices.foreach_set('co', target.astype(np.float32).ravel())
    jeans.data.update()
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    jeans.select_set(True)
    bpy.context.view_layer.objects.active = jeans
    prior = sha256(path.read_bytes()).hexdigest()
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format='GLB', use_selection=True, export_animations=False,
        export_skins=True, export_yup=True, export_tangents=bool(jeans.data.uv_layers),
    )
    record = OUT / 'qa/fit-jeans.json'
    fit = json.loads(record.read_text())
    previous = fit.get('waist_adjustment', {}).get('max_adjustment_mm', 0.)
    fit['waist_adjustment'] = {'input_sha256': prior, 'baseline_layer_pairs': baseline[0],
                              'history': history, 'max_adjustment_mm': previous + best[1] * 1000}
    fit['sha256'] = sha256(path.read_bytes()).hexdigest()
    write_json(record, fit)


if __name__ == '__main__':
    fit_waist()
