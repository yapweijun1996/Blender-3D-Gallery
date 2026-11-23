"""Bake a bounded envelope against the exact round-two pose grid."""
from pathlib import Path
import hashlib
import json
import sys
import time

import bmesh
import numpy as np

from asset_io import CLIPS, HERE, bpy, write_json
from body_audit import load_body_motion, posed, set_frame, use_action
from fit_module import CAP, FLOOR, TRI_LIMIT, Sample, influences, nearest, read_module, store_geometry
from fitting_geometry import arrays, laplacian, limit_weights, tree, weights, welded
from motion_repair import FIXED
from refit import Garment, BARYCENTRIC, unique_vertices
from verify import grids

OUT = Path(__file__).resolve().parent
ROUND2 = FIXED.parent
SLOTS = {'dress': 'dress', 'jeans': 'bottom'}
MARGIN = .002
TRIGGER = .00070


def source(key):
    return ROUND2 / f'male-{key}-v2.glb'


def cap(displacement):
    scale = np.linalg.norm(displacement, axis=1, keepdims=True)
    return displacement * np.minimum(1., CAP / np.maximum(scale, 1.e-9))


def smoothstep(value):
    value = np.clip(value, 0., 1.)
    return value * value * (3. - 2. * value)


def triangulate(mesh):
    bmesh.ops.triangulate(mesh, faces=[f for f in mesh.faces if len(f.verts) > 3])


def shorten_cuffs(mesh, height):
    topology = bmesh.new()
    topology.from_mesh(mesh)
    bmesh.ops.bisect_plane(
        topology, geom=[*topology.verts, *topology.edges, *topology.faces],
        dist=1.e-6, plane_co=(0., 0., height), plane_no=(0., 0., 1.),
        clear_inner=True,
    )
    triangulate(topology)
    topology.to_mesh(mesh)
    topology.free()
    mesh.update()


def split_crossings(obj, key, witnesses):
    points, faces = arrays(obj)
    if not witnesses:
        return np.zeros(len(points), dtype=bool)
    lengths = np.linalg.norm(points[faces] - points[faces[:, [1, 2, 0]]], axis=2)
    long_edges = set()
    for face in witnesses:
        corner = int(lengths[face].argmax())
        if lengths[face, corner] >= .009:
            edge = faces[face, [corner, (corner + 1) % 3]]
            long_edges.add(tuple(sorted(map(tuple, np.round(points[edge], 6)))))
    if not long_edges:
        return np.zeros(len(points), dtype=bool)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    existing = mesh.verts.layers.int.new('Source vertex')
    for vertex in mesh.verts:
        vertex[existing] = 1
    edge_keys = np.round(points, 6)
    edges = [e for e in mesh.edges if tuple(sorted(tuple(edge_keys[v.index]) for v in e.verts)) in long_edges]
    geometry = bmesh.ops.subdivide_edges(mesh, edges=edges, cuts=1, use_grid_fill=True)
    for vertex in geometry['geom_inner']:
        if isinstance(vertex, bmesh.types.BMVert):
            vertex[existing] = 0
    triangulate(mesh)
    mesh.verts.index_update()
    new = np.asarray([not vertex[existing] for vertex in mesh.verts])
    if len(mesh.faces) > TRI_LIMIT[SLOTS[key]]:
        raise ValueError(f'{key} exceeds its triangle budget after splitting')
    mesh.verts.layers.int.remove(existing)
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    return new


def cuff_height(sneaker):
    return np.ceil((arrays(sneaker)[0][:, 2].max() + .003) * 1000.) / 1000.


class Fit(Garment):
    def __init__(self, key, obj, names, split):
        super().__init__(key, obj, names, None)
        self.new = split
        self.refresh()
        self.reports = []

    def refresh(self):
        self.ids, self.packed = influences(self.w)
        self.representatives, self.inverse = unique_vertices(self.base, self.w)


    def blend_weights(self, mask, strength):
        if not mask.any():
            return
        w = self.w.copy()
        for _ in range(2):
            w[mask] = (1. - strength) * w[mask] + strength * laplacian(w, self.graph)[mask]
        self.w = limit_weights(welded(w, self.graph)).astype(np.float32)
        self.refresh()

    def measure(self, sample, bvh, collect, trigger=TRIGGER):
        basis = self.basis(sample)
        p = np.einsum('vij,vj->vi', basis[:, :, :3], self.position) + basis[:, :, 3]
        small = p[self.representatives]
        if np.array_equal(small[self.inverse], p):
            d, n, _ = nearest(bvh, small)
            d, n = d[self.inverse], n[self.inverse].copy()
            pairs = bvh.overlap(tree(small, self.inverse[self.faces].tolist()))
        else:
            d, n, _ = nearest(bvh, p)
            pairs = bvh.overlap(tree(p, self.face_list))
        report = (int((d < 0.).sum()), len(pairs), float(d.min()))
        if not collect:
            return report, None
        required = np.where(d < trigger, MARGIN + np.maximum(-d, 0.), 0.)
        if pairs:
            from body_audit import pair_depth
            b, g = np.asarray(pairs).T
            per_face = np.zeros(len(self.faces))
            np.maximum.at(per_face, g, pair_depth(sample.body[np.asarray(sample.faces)[b]], p[self.faces[g]]) * .001)
            unique_faces = np.unique(g)
            corners = self.faces[unique_faces]
            probes = (BARYCENTRIC @ p[corners]).reshape(-1, 3)
            probe_d, probe_n, _ = nearest(bvh, probes)
            probe_d = probe_d.reshape(len(corners), -1)
            probe_n = probe_n.reshape(len(corners), -1, 3)
            for face, triangle, ds, ns in zip(unique_faces, corners, probe_d, probe_n):
                worst = ds.argmin()
                request = MARGIN + max(0., -ds[worst], per_face[face])
                changed = triangle[required[triangle] < request]
                n[changed] = ns[worst]
                required[changed] = request
        active = np.flatnonzero(required)
        if not len(active):
            return report, None
        # Convert the posed normal to a bind-space clearance gradient.
        gradient = np.einsum('vji,vj->vi', basis[active, :, :3], n[active])
        magnitude = np.linalg.norm(gradient, axis=1).clip(.2, None)
        directions = gradient / magnitude[:, None]
        return report, (active, directions, np.clip(required[active] / magnitude, 0., CAP))

    def bake(self, constraints, gain=1., loft=0.):
        indices, headings, amounts = map(np.concatenate, zip(*constraints))
        inv, _, _, _, counts = self.graph
        group = inv[indices]
        strongest = np.zeros(len(counts))
        np.maximum.at(strongest, group, amounts)
        winners = np.flatnonzero(amounts == strongest[group])
        directions = np.zeros((len(counts), 3))
        directions[group[winners]] = headings[winners]
        # Propagate the requirement across neighboring vertices while
        # keeping its full projection along the worst-frame direction.
        floor = strongest[inv]
        axis = directions[inv]
        move = axis * floor[:, None]
        for _ in range(5):
            move = welded(.55 * move + .45 * laplacian(move, self.graph), self.graph)
            deficit = floor - np.einsum('vi,vi->v', move, axis)
            move += axis * np.maximum(deficit, 0.)[:, None]
        if loft:
            kernel = (floor > 0.).astype(np.float64)
            for _ in range(4):
                kernel = np.maximum(kernel, laplacian(kernel, self.graph) * .84)
            move += axis * loft * kernel[:, None]
            move += laplacian(axis * loft * kernel[:, None], self.graph) * .55
        return (self.base + cap(self.position - self.base + move * gain)).astype(np.float32)

    def regional_loft(self, strength):
        x, y, z = self.base.T
        front = smoothstep((-y - .065) / .056)
        span = smoothstep((z - .268) / .038) * smoothstep((.408 - z) / .041)
        width = smoothstep((.132 - abs(x)) / .041)
        trial = self.position.copy()
        trial[:, 1] -= strength * front * span * width
        if self.key == 'dress':
            # A shallow rear skirt flare follows the knee clearance patch.
            rear = smoothstep((y - .027) / .029) * smoothstep((.310 - z) / .046)
            trial[:, 1] += strength * .57 * rear
        return (self.base + cap(trial - self.base)).astype(np.float32)

    def export_v3(self, arm, names):
        store_geometry(self.obj, self.position, self.w, names)
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj
        path = OUT / f'male-{self.key}-v3.glb'
        bpy.ops.export_scene.gltf(
            filepath=str(path), export_format='GLB', use_selection=True,
            export_animations=False, export_skins=True, export_yup=True,
            export_tangents=bool(self.obj.data.uv_layers),
        )
        write_json(OUT / f'qa/fit-{self.key}.json', {
            'source_sha256': hashlib.sha256(source(self.key).read_bytes()).hexdigest(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'vertex_displacement_max_mm': float(np.linalg.norm(self.position - self.base, axis=1).max() * 1000),
            'split_vertices': int(self.new.sum()), 'triangles': len(self.faces),
            'passes': self.reports,
        })


def capture(scene, arm, body, actions, names, goal=None):
    bfaces = arrays(body)[1].tolist()
    rest_matrices = [arm.data.bones[n].matrix_local.inverted() for n in names]
    samples = []
    for clip in ('rest', *CLIPS):
        if goal is not None and clip not in goal:
            continue
        action = actions.get(clip)
        use_action(arm, action)
        frames = grids(action, scene.render.fps) if action else [0.]
        for frame in frames:
            set_frame(scene, frame)
            matrices = np.asarray([arm.pose.bones[n].matrix @ rest
                                   for n, rest in zip(names, rest_matrices)], dtype=np.float32)
            samples.append(Sample(clip, frame, posed(body), bfaces, matrices[:, :3]))
    use_action(arm, None)
    set_frame(scene, 0.)
    return samples


def scan(garments, samples, groups=None, collect=True):
    start = time.monotonic()
    ids = list(range(len(samples))) if groups is None else sorted(groups)
    rows = {g.key: [] for g in garments}
    requirements = {g.key: [] for g in garments}
    for i in ids:
        pose = samples[i]
        bvh = pose.cached_tree or tree(pose.body, pose.faces)
        for garment in garments:
            row, witness = garment.measure(pose, bvh, collect)
            rows[garment.key].append(row)
            if witness is not None:
                requirements[garment.key].append((i, witness))
    print('SCAN', len(ids), round(time.monotonic() - start, 1), flush=True)
    return {k: np.asarray(v) for k, v in rows.items()}, requirements


def bad(rows):
    return (rows[:, :2].sum(axis=1) > 0) | (rows[:, 2] < FLOOR)


def score(rows):
    d = rows[:, 2]
    return (int(bad(rows).sum()), int(rows[:, :2].sum()),
            float(np.maximum(FLOOR - d, 0.).sum()), -float(d.min()))


def report(garment, rows, samples, stage):
    failing = np.flatnonzero(bad(rows))
    stats = {
        'stage': stage, 'samples': len(rows), 'peak_inside': int(rows[:, 0].max()),
        'peak_pairs': int(rows[:, 1].max()), 'min_signed_m': float(rows[:, 2].min()),
        'failures': [[samples[i].clip, samples[i].frame, *rows[i].tolist()] for i in failing],
    }
    garment.reports.append(stats)
    print(garment.key, stage, score(rows), stats['failures'][:8], flush=True)


def setup(scene, arm, body, names, keys):
    use_action(arm, None)
    set_frame(scene, 0.)
    shoes = read_module(HERE / 'male-sneakers.glb', arm)
    garments = []
    for key in keys:
        obj = read_module(source(key), arm)
        baseline = (ROUND2 / f'qa/modules/{key}.json').read_text()
        overlaps = {row['triangle_witness'][1] for clip in json.loads(baseline)['clips'].values()
                    for row in clip['frames'] if 'triangle_witness' in row}
        split = split_crossings(obj, key, overlaps)
        if key == 'jeans':
            inserted = {tuple(point) for point in arrays(obj)[0][split]}
            height = cuff_height(shoes)
            print('Cuff opening height', height, flush=True)
            shorten_cuffs(obj.data, height)
            split = np.asarray([tuple(point) in inserted for point in arrays(obj)[0]])
        garment = Fit(key, obj, names, split)
        garments.append(garment)
    return garments


def fit(keys, rounds):
    scene, arm, body, actions = load_body_motion(FIXED)
    names = [bone.name for bone in arm.data.bones]
    garments = setup(scene, arm, body, names, keys)
    samples = capture(scene, arm, body, actions, names)
    print('Captured', len(samples), 'poses', flush=True)
    active = garments.copy()
    best = {}
    for cycle in range(rounds + 1):
        rows, constraints = scan(active, samples)
        for garment in active[:]:
            values = rows[garment.key]
            report(garment, values, samples, f'full bake {cycle}')
            severity = score(values)
            if garment.key not in best or severity < best[garment.key][0]:
                best[garment.key] = (severity, garment.position.copy(), garment.w.copy())
                garment.export_v3(arm, names)
            if not severity[0] or cycle == rounds:
                active.remove(garment)
                continue
            focus = {i for i, _ in constraints[garment.key]}
            guards = set(range(0, len(samples), 45))
            around = {j for i in focus for j in (i-1, i, i+1) if 0 <= j < len(samples)}
            probe = sorted(guards | around)
            needed = [w for _, w in constraints[garment.key]]
            origin, origin_w = garment.position.copy(), garment.w.copy()
            candidates = [('baseline', origin)]
            if needed:
                candidates.extend((f'bake {gain}', garment.bake(needed, gain))
                                  for gain in (1., .65, 1.4))
                candidates.append(('bake with local loft', garment.bake(needed, 1., .002)))
            candidates.extend((f'regional loft {gain}', garment.regional_loft(gain))
                              for gain in (.004, .008, .012))
            winner = None
            for title, proposal in candidates:
                garment.position = proposal
                test, _ = scan([garment], samples, probe, collect=False)
                trial_score = score(test[garment.key])
                print('TRIAL', garment.key, title, trial_score, flush=True)
                if winner is None or trial_score < winner[0]:
                    winner = (trial_score, title, proposal.copy(), garment.w.copy())
                if trial_score[0] == 0 and title != 'baseline':
                    break
            if winner[0][0] and needed:
                garment.w = origin_w.copy()
                mask = np.zeros(len(origin), dtype=bool)
                mask[np.concatenate([w[0] for w in needed])] = True
                mask = welded(mask.astype(float), garment.graph) > 0.
                garment.blend_weights(mask | (laplacian(mask.astype(float), garment.graph) > .25), .13)
                garment.position = winner[2]
                test, _ = scan([garment], samples, probe, collect=False)
                trial_score = score(test[garment.key])
                print('TRIAL', garment.key, 'weight smoothing', trial_score, flush=True)
                if trial_score < winner[0]:
                    winner = (trial_score, 'weight smoothing', garment.position.copy(), garment.w.copy())
            garment.position, garment.w = winner[2:]
            garment.refresh()
            print('SELECTED', garment.key, winner[:2], flush=True)
            if winner[1] == 'baseline':
                active.remove(garment)
        if not active:
            break


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    fit(args[0].split(',') if args else list(SLOTS), int(args[1]) if len(args) > 1 else 3)
