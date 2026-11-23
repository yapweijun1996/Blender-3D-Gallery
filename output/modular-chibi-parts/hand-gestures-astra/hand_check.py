"""Offline QA. Run with run_blender.sh hand_check.py [--render]."""
import hashlib
import json
import math
import sys
from pathlib import Path
import struct
from collections import Counter, defaultdict

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Euler, Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hand_common import (OUT, MASTER, DIGITS, SIDES, GESTURES, Z, prefix,
                         vertex_weights, rest_data, clean_pose, set_action, glb, run_batch)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def vec(v, n=5): return [round(float(k), n) for k in v]
def load(path): bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False, use_scripts=False)


def accessor(doc, buf, k):
    a = doc['accessors'][k]
    b = doc['bufferViews'][a['bufferView']]
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    fmt = '<'+{5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[a['componentType']]*width
    size = struct.calcsize(fmt)
    off = b.get('byteOffset', 0)+a.get('byteOffset', 0)
    return [struct.unpack_from(fmt, buf, off+i*b.get('byteStride', size)) for i in range(a['count'])]


def exports(rig, body, lib):
    base, binary = glb(OUT/'base_body.glb')
    clips, buf = glb(OUT/'hand_gestures.glb')
    def names(doc): return {n['name']: i for i, n in enumerate(doc['nodes'])}
    nodes = names(base)
    channels = {}
    rest = {}
    for doc in (base, clips):
        tree = {c: n['name'] for n in doc['nodes'] for c in n.get('children', [])}
        for b in rig.data.bones:
            n = names(doc)[b.name]
            assert tree.get(n) == (b.parent.name if b.parent else 'Armature')
    mesh = base['meshes'][0]
    skin = base['skins'][0]
    joint_names = [base['nodes'][i]['name'] for i in skin['joints']]
    assert set(joint_names) == set(rig.data.bones.keys())
    err = 0
    ntri = 0
    werr = 0
    nvert = 0
    rest_diff = 0
    parents = {c: i for i, n in enumerate(base['nodes']) for c in n.get('children', [])}

    def world(i):
        n = base['nodes'][i]
        if 'matrix' in n:
            m = Matrix(np.array(n['matrix']).reshape(4, 4).T.copy())
        else:
            x, y, z, w = n.get('rotation', (0, 0, 0, 1))
            m = Matrix.LocRotScale(Vector(n.get('translation', (0, 0, 0))),
                                   Quaternion((w, x, y, z)), Vector(n.get('scale', (1, 1, 1))))
        return world(parents[i])@m if i in parents else m
    mesh_i = next(i for i, n in enumerate(base['nodes']) if n.get('mesh') == 0 and n.get('skin') == 0)
    inverse_mesh = world(mesh_i).inverted()
    bind_error = 0
    matrices = accessor(base, binary, skin['inverseBindMatrices'])
    assert len(matrices) == len(joint_names)
    for i, v in zip(skin['joints'], matrices):
        inv = Matrix(np.array(v).reshape(4, 4).T.copy())
        bind_error = max(bind_error, float(np.max(np.abs(np.array(inverse_mesh@world(i)@inv)-np.eye(4)))))
    for n in clips['nodes']:
        orig = base['nodes'][nodes[n['name']]]
        for k in ('translation', 'rotation', 'scale', 'matrix'):
            lhs = n.get(k, ())
            rhs = orig.get(k, ())
            assert len(lhs) == len(rhs)
            rest_diff = max(rest_diff, max((abs(a-b) for a, b in zip(lhs, rhs)), default=0))
    weights = defaultdict(list)
    for v in body.data.vertices:
        weights[tuple(vec((v.co.x, v.co.z, -v.co.y), 6))].append(vertex_weights(body, v))
    for p in mesh['primitives']:
        attrs = p['attributes']
        ntri += base['accessors'][p['indices']]['count']//3
        assert 'WEIGHTS_1' not in attrs
        for pos, js, ws in zip(*[accessor(base, binary, attrs[key]) for key in ('POSITION', 'JOINTS_0', 'WEIGHTS_0')]):
            nvert += 1
            got = {joint_names[j]: w for j, w in zip(js, ws) if w > 0}
            expected = weights[tuple(vec(pos, 6))]
            assert expected
            werr = max(werr, min(max(abs(got.get(n, 0)-w.get(n, 0))
                       for n in got.keys() | w.keys()) for w in expected))
    for clip in clips['animations']:
        name = clip['name']
        channels[name] = []
        for c in clip['channels']:
            node = clips['nodes'][c['target']['node']]
            bone = node['name']
            s = clip['samplers'][c['sampler']]
            times = accessor(clips, buf, s['input'])
            samples = accessor(clips, buf, s['output'])
            assert c['target']['path'] == 'rotation' and len(times) == len(samples) == 1
            assert abs(times[0][0]) < 1e-7
            rot = node.get('rotation', (0, 0, 0, 1))
            q = Quaternion((rot[3], *rot[:3])) @ Euler(tuple(math.radians(v)
                                                             for v in lib[name][bone]), 'XYZ').to_quaternion()
            v = samples[0]
            expected = list(q)
            got = [v[3], *v[:3]]
            err = max(err, min(max(abs(a-sign*b) for a, b in zip(expected, got)) for sign in (1, -1)))
            channels[name].append(bone)
        assert set(channels[name]) == set(lib[name]) and len(channels[name]) == len(lib[name])
    assert set(channels) == set(lib) and len(channels) == 18
    return dict(base_meshes=len(base['meshes']), base_skins=len(base['skins']), joints=len(joint_names), base_animations=len(base.get('animations', [])),
                max_inverse_bind_identity_error=bind_error, base_export_vertices=nvert, base_triangles=ntri, max_export_weight_difference=werr, clip_meshes=len(
                    clips.get('meshes', [])),
                clip_nodes=len(clips['nodes']), rest_node_transform_difference=rest_diff,
                clip_names_channels={n: len(c) for n, c in channels.items()}, timestamps_seconds=[0], max_clip_quaternion_component_difference=err)


def hand_geometry(body, side, sg, tips):
    mesh = body.data
    mesh.calc_loop_triangles()
    rest = [v.co.copy() for v in mesh.vertices]
    tris = [tuple(t.vertices) for t in mesh.loop_triangles if max(sg*rest[i].x for i in t.vertices) > .255]
    p = prefix(side)
    totals = [{d: sum(w for n, w in vertex_weights(body, v).items() if n.startswith(p+d))
               for d in DIGITS} for v in mesh.vertices]
    labels = []
    for tri in tris:
        avg = {d: sum(totals[i][d] for i in tri)/3 for d in DIGITS}
        best = max(avg, key=avg.get)
        labels.append(best if avg[best] > .48 else 'Palm')
    # The palmar side of the hand, including rigid palm and thenar padding.
    palm_faces = [tr for tr, label in zip(tris, labels) if label == 'Palm' and
                  sum(rest[i].z for i in tr)/3 < .559 and min(sg*rest[i].x for i in tr) > .272]
    weld = [tuple(round(k, 7) for k in v) for v in rest]
    keys = [{weld[i] for i in tri} for tri in tris]
    return tris, labels, palm_faces, keys


def pose_numbers(body, rig, side, sg, tips, palm, volume, geom):
    tris, labels, palm_faces, keys = geom
    deps = bpy.context.evaluated_depsgraph_get()
    points = [v.co.copy() for v in body.evaluated_get(deps).data.vertices]
    hand = rig.pose.bones[prefix(side)]
    transform = hand.matrix@hand.bone.matrix_local.inverted()
    origin = transform@palm
    tip = {d: sum((points[i] for i in cap), Vector())/len(cap) for d, cap in tips.items()}
    tree = BVHTree.FromPolygons(points, tris, all_triangles=True)
    hits = [(i, j) for i, j in tree.overlap(tree) if i < j and not keys[i] & keys[j]]
    pairs = Counter('/'.join(sorted((labels[i], labels[j]))) for i, j in hits)
    palm_tree = BVHTree.FromPolygons(points, palm_faces, all_triangles=True)
    gap = {d: palm_tree.find_nearest(v)[3]*1000 for d, v in tip.items()}
    relative = {d: vec((v-origin)*1000, 3) for d, v in tip.items()}
    distances = {d: round((v-origin).length*1000, 3) for d, v in tip.items()}
    th = tip['Thumb']
    ix = tip['Index']
    distal_faces = {}
    for d in ('Index', 'Thumb'):
        rest_tip = sum((body.data.vertices[i].co for i in tips[d]), Vector())/len(tips[d])
        root = rig.data.bones[prefix(side)+d+'1'].head_local
        axis = (rest_tip-root).normalized()
        cut = .72*(rest_tip-root).length
        distal_faces[d] = [tri for tri, lab in zip(tris, labels) if lab == d and
                           all((body.data.vertices[i].co-root).dot(axis) > cut for i in tri)]
    pad_gap = 1e5
    for d, e in [('Index', 'Thumb'), ('Thumb', 'Index')]:
        distal_tree = BVHTree.FromPolygons(points, distal_faces[e], all_triangles=True)
        pad_gap = min(pad_gap, min(distal_tree.find_nearest(points[i])[
                      3]*1000 for i in {u for f in distal_faces[d] for u in f}))
    thumb_root = rig.pose.bones[prefix(side)+'Thumb1'].head
    thumb_elevation = 90.0 - math.degrees((th-thumb_root).angle(Z))
    return dict(thumb_elevation_above_horizontal_deg=round(thumb_elevation, 3),
                tip_relative_mm=relative, tip_relative_to_volume_mm={d: vec((v-transform@volume)*1000, 3) for d, v in tip.items()},
                distal_thumb_index_surface_gap_mm=round(pad_gap, 4), tip_radius_mm=distances, tip_to_palmar_skin_mm={d: round(x, 3) for d, x in gap.items()},
                tip_to_volume_center_mm={d: round((v-transform@volume).length*1000, 3)
                                         for d, v in tip.items()},
                thumb_index_mm=round((th-ix).length*1000, 3), thumb_above_highest_other_mm=round(1000*(th.z-max(v.z for d, v in tip.items() if d != 'Thumb')), 3),
                triangle_intersection_pairs=len(hits), intersections_by_part=dict(pairs),
                wrist_translation_mm=round((hand.head-hand.bone.head_local).length*1000, 5),
                wrist_rotation_deg=round(math.degrees(hand.matrix_basis.to_quaternion().angle), 4)), points


def cylinder(points, geom, palm, sg):
    # Given a centreline, its clearance to a triangle equals the distance
    # from the origin to that triangle projected onto its transverse plane.
    tris, labels, _, _ = geom
    axis = np.array([-.45*sg, 1, 0.])
    axis /= np.linalg.norm(axis)
    center = np.array(palm)*1000+[5*sg, 0, -23]
    tri = np.array(points)[np.array(tris)]*1000-center
    q = tri-(tri@axis)[:, :, None]*axis
    e = np.roll(q, -1, axis=1)-q
    u = np.clip(-(q*e).sum(2)/np.maximum((e*e).sum(2), 1e-18), 0, 1)
    dist = np.linalg.norm(q+u[:, :, None]*e, axis=2).min(1)
    signs = np.cross(e, -q)@axis
    dist[(signs.min(1) > 0) | (signs.max(1) < 0)] = 0
    return dict(axis_unit=vec(axis), point_mm=vec(center, 3), diameter_mm=40,
                penetrating_triangles=int(np.sum(dist < 20)), clearance_from_axis_mm={d: round(float(dist[np.array(labels) == d].min()), 4) for d in ('Palm', *DIGITS)})


def arm_state(rig):
    return {b.name: np.array(b.matrix_local) for b in rig.data.bones}


def imported_playback(native_positions):
    # Compare the actual imported animation against the authored skin on the
    # independently imported static body. Match UV-split copies in rest space.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(OUT/'base_body.glb'))
    rig = bpy.data.objects['Armature']
    body = bpy.data.objects['Base_Body']
    bpy.ops.import_scene.gltf(filepath=str(OUT/'hand_gestures.glb'))
    clean_pose(rig)
    neutral = native_positions['rest']
    from mathutils.kdtree import KDTree
    tree = KDTree(len(neutral))
    for i, p in enumerate(neutral):
        tree.insert(Vector(p), i)
    tree.balance()
    ids = []
    max_rest = 0
    for v in body.data.vertices:
        p = body.matrix_world@v.co
        near, idx, dist = tree.find(p)
        max_rest = max(max_rest, dist)
        ids.append(idx)
    result = {}
    for n, points in native_positions.items():
        if n == 'rest':
            continue
        action = bpy.data.actions[n]
        set_action(rig, action)
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        actual = np.array([ev.matrix_world@v.co for v in ev.data.vertices])
        result[n] = round(float(np.linalg.norm(actual-np.array(points)[ids], axis=1).max())*1000, 6)
    return dict(imported_actions=len(bpy.data.actions), rest_error_mm=round(max_rest*1000, 6),
                max_deformed_vertex_error_mm=result)


def main():
    checks = {}
    load(MASTER)
    old = bpy.data.objects['Base_Body']
    rig = bpy.data.objects['Armature']
    oldp = [v.co.copy() for v in old.data.vertices]
    oldw = [vertex_weights(old, v) for v in old.data.vertices]
    original_rig = arm_state(rig)
    lib = json.loads((OUT/'hand_gestures.json').read_text())['gestures']
    baseline = {}
    for key in ('L', 'R'):
        side = 'Left' if key == 'L' else 'Right'
        p = rig.pose.bones[prefix(side)]
        p.rotation_mode = 'XYZ'
        p.rotation_euler = [math.radians(v) for v in lib['hand_thumbs_up_'+key].get(p.name, (0, 0, 0))]
        bpy.context.view_layer.update()
        baseline[key] = [v.co.copy() for v in old.evaluated_get(
            bpy.context.evaluated_depsgraph_get()).data.vertices]
        p.matrix_basis = Matrix.Identity(4)
    oldrig = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    load(OUT/'hands_gestures.blend')
    body = bpy.data.objects['Base_Body']
    rig = bpy.data.objects['Armature']
    mesh = body.data
    clean_pose(rig)
    mesh.calc_loop_triangles()
    assert {b.name: b.parent.name if b.parent else None for b in rig.data.bones} == oldrig
    lib = json.loads((OUT/'hand_gestures.json').read_text())['gestures']
    non = [i for i, p in enumerate(oldp) if abs(p.x) <= .271]
    w = [vertex_weights(body, v) for v in mesh.vertices]
    bleed = anymix = 0
    for ws in w:
        ds = {d: sum(v for k, v in ws.items() if 'Hand'+d in k) for d in DIGITS}
        bleed += sum(x > .2 for x in ds.values()) > 1
        anymix += sum(x > 0 for x in ds.values()) > 1
    checks['asset_sha256'] = {f: sha(OUT/f) for f in ('hands_gestures.blend',
                                                      'base_body.glb', 'hand_gestures.glb', 'hand_gestures.json')}
    checks['source_sha256'] = sha(MASTER)
    checks['geometry'] = dict(vertices=len(mesh.vertices), triangles=len(mesh.loop_triangles), bones=len(oldrig), changed_parents=0,
                              vertex_groups=len(body.vertex_groups), unchanged_region_vertices=len(non), nonhand_max_displacement_m=max((mesh.vertices[i].co-oldp[i]).length for i in non),
                              nonhand_weight_changes=sum(w[i] != oldw[i] for i in non), max_influences=max(map(len, w)),
                              over_four=sum(len(ws) > 4 for ws in w), unweighted=sum(not ws for ws in w), max_sum_error=max(abs(sum(ws.values())-1) for ws in w),
                              finger_bleed_above_point_two=bleed, any_mixed_finger_chains=anymix)
    checks['export'] = exports(rig, body, lib)
    native_positions = {'rest': np.array([v.co for v in mesh.vertices])}
    checks['rest'] = {}
    checks['gestures'] = {}
    checks['checks_failed'] = []
    checks['blender_version'] = bpy.app.version_string
    checks['measurement_units'] = 'millimetres unless a field ends in _m'
    checks['self_intersection_tolerance_pairs'] = 0
    render = '--render' in sys.argv
    if render:
        from render_hands import Studio
        studio = Studio(body)
    for tag, side, sg in SIDES:
        clean_pose(rig)
        tips, palm, volume, n = rest_data(body, rig, side)
        geom = hand_geometry(body, side, sg, tips)
        handtris = sum(all(sg*mesh.vertices[i].co.x > .27 for i in t.vertices) for t in mesh.loop_triangles)
        handquads = sum(len(f.vertices) == 4 and all(
            sg*mesh.vertices[i].co.x > .27 for i in f.vertices) for f in mesh.polygons)
        thumbtip = sum((mesh.vertices[i].co for i in tips['Thumb']), Vector())/len(tips['Thumb'])
        thumbdir = (thumbtip-rig.data.bones[prefix(side)+'Thumb1'].head_local).normalized()
        checks['rest'][tag] = dict(palm_center_m=vec(palm), palm_volume_midpoint_m=vec(volume),
                                   palm_normal=vec(n), palm_degrees_from_down=round(math.degrees(n.angle(-Z)), 3),
                                   thumb_direction=vec(thumbdir), triangles=handtris, quads=handquads,
                                   cap_vertex_counts={d: len(z) for d, z in tips.items()})
        pfx = prefix(side)
        mesh.calc_loop_triangles()
        edge_use = Counter()
        coords = [tuple(round(q, 7) for q in v.co) for v in mesh.vertices]
        for t in mesh.loop_triangles:
            f = t.vertices[:]
            for a, b in zip(f, f[1:]+f[:1]):
                if min(sg*coords[a][0], sg*coords[b][0]) > .27:
                    edge_use[tuple(sorted((coords[a], coords[b])))] += 1
        checks['rest'][tag]['welded_nonmanifold_hand_edges'] = sum(v != 2 for v in edge_use.values())
        shafts = [v.index for v in mesh.vertices if sg*v.co.x > .340 or (sg*v.co.x > .275 and v.co.y < -.060)]
        pad = [v.index for v in mesh.vertices if abs(
            sg*v.co.x-.301) < .008 and abs(v.co.y-palm.y) < .009 and v.co.z < .552]
        thenar = [v.index for v in mesh.vertices if abs(
            sg*v.co.x-.300) < .009 and abs(v.co.y-palm.y+.024) < .009 and v.co.z < .553]
        checks['rest'][tag]['free_shaft_vertices'] = len(shafts)
        checks['rest'][tag]['free_shaft_with_non_digit_weight'] = sum(
            any(not k.startswith(pfx) or not k[-1].isdigit() for k in w[i]) for i in shafts)
        checks['rest'][tag]['central_palmar_vertices'] = len(pad)
        checks['rest'][tag]['central_palmar_minimum_hand_weight'] = min(w[i].get(pfx, 0) for i in pad)
        checks['rest'][tag]['thenar_vertices'] = len(thenar)
        checks['rest'][tag]['thenar_hand_weight_range'] = [
            round(fun(w[i].get(pfx, 0) for i in thenar), 6) for fun in (min, max)]
        checks['rest'][tag]['thenar_thumb_weight_range'] = [round(
            fun(sum(v for k, v in w[i].items() if k.startswith(pfx+'Thumb')) for i in thenar), 6) for fun in (min, max)]
        checks['rest'][tag]['local_axes_world'] = {d+str(j): {axis: vec(rig.data.bones[pfx+d+str(
            j)].matrix_local.col[k][:3]) for k, axis in enumerate('XYZ')} for d in DIGITS for j in (1, 2, 3, 4)}
        print(tag, 'REST', checks['rest'][tag], flush=True)
        for gesture in GESTURES:
            name = 'hand_'+gesture+'_'+tag
            action = bpy.data.actions[name]
            set_action(rig, action)
            bag = action.layers[0].strips[0].channelbag(action.slots[0])
            assert len(action.slots) == 1 and len(bag.fcurves) == 3*len(lib[name])
            assert all(len(f.keyframe_points) == 1 and f.keyframe_points[0].co.x == 1 and f.data_path.endswith(
                '.rotation_euler') for f in bag.fcurves)
            expected = {prefix(side)+d+str(i) for d in DIGITS for i in (1, 2, 3, 4)}
            if gesture == 'thumbs_up' and prefix(side) in lib[name]:
                expected.add(prefix(side))
            assert set(lib[name]) == expected
            for bone, angles in lib[name].items():
                assert max(abs(math.degrees(a)-b)
                           for a, b in zip(rig.pose.bones[bone].rotation_euler, angles)) < .0001
            r, points = pose_numbers(body, rig, side, sg, tips, palm, volume, geom)
            native_positions[name] = np.array(points)
            reference = baseline[tag] if gesture == 'thumbs_up' else oldp
            r['nonhand_pose_matched_displacement_m'] = max((points[i]-reference[i]).length for i in non)
            r['nonhand_motion_from_rest_mm'] = round(1000*max((points[i]-oldp[i]).length for i in non), 5)
            r['slot'] = action.slots[0].identifier
            r['keyed_bones'] = len(lib[name])
            r['asset_preview_pixels'] = list(action.preview.image_size) if action.preview else [0, 0]
            factors = {'zero_self_intersection': r['triangle_intersection_pairs'] == 0}
            ds = r['tip_radius_mm']
            gap = r['tip_to_palmar_skin_mm']
            if gesture == 'fist':
                tris, labels, _, _ = geom
                folded_skin = BVHTree.FromPolygons(points, [t for t, label in zip(tris, labels) if label in DIGITS[:4]], all_triangles=True)
                r['thumb_cap_to_folded_fingers_mm'] = round(1000*min(folded_skin.find_nearest(points[i])[3] for i in tips['Thumb']), 4)
                factors['thumb_wrap_contacts_folded_fingers'] = r['thumb_cap_to_folded_fingers_mm'] < 1
                factors['all_tips_within_25_mm'] = max(ds.values()) <= 25
            if gesture == 'thumbs_up':
                factors['four_within_25_mm'] = max(ds[d] for d in DIGITS[:4]) <= 25
                factors['thumb_highest'] = r['thumb_above_highest_other_mm'] > 0
            if gesture == 'point':
                factors['index_farthest'] = max(ds, key=ds.get) == 'Index'
                factors['other_three_curled'] = max(ds[d] for d in DIGITS[1:4]) <= 25
            if gesture == 'ok':
                factors['distal_pads_touch_within_0_1_mm'] = r['distal_thumb_index_surface_gap_mm'] < .1
            if gesture in ('ok', 'pinch'):
                factors['thumb_index_under_10_mm'] = r['thumb_index_mm'] < 10
            if gesture == 'grip_small':
                factors['all_skin_gaps_15_to_30_mm'] = all(15 <= x <= 30 for x in gap.values())
            volume_r = r['tip_to_volume_center_mm']
            if gesture in ('fist', 'point', 'thumbs_up'):
                closed = {'fist': DIGITS, 'thumbs_up': DIGITS[:4], 'point': DIGITS[1:4]}[gesture]
                factors['closed_tips_within_25_mm_of_volume_center'] = all(volume_r[d] <= 25 for d in closed)
            if gesture == 'grip_small':
                r['cylinder'] = cylinder(points, geom, palm, sg)
                factors['clear_40_mm_cylinder'] = r['cylinder']['penetrating_triangles'] == 0
            factors['wrist_position_fixed'] = r['wrist_translation_mm'] < .001
            if gesture != 'thumbs_up':
                factors['wrist_rotation_fixed'] = r['wrist_rotation_deg'] < .001
            factors['nonhand_motion_within_0_5_mm'] = r['nonhand_motion_from_rest_mm'] < .5
            factors['unchanged_nonhand_vs_same_pose'] = r['nonhand_pose_matched_displacement_m'] < .0005
            r['passes'] = factors
            checks['gestures'][name] = r
            checks['checks_failed'] += [name+' '+k for k, v in factors.items() if not v]
            print(name, 'TIP XYZ mm', r['tip_relative_mm'], 'RADII', ds, 'PALM GAPS', gap, 'TH-IX', r['thumb_index_mm'],
                  'UP', r['thumb_above_highest_other_mm'], 'INTERSECTIONS', r['intersections_by_part'], flush=True)
            if render:
                studio.render(name, side, sg, body, rig, points)
                if gesture == 'grip_small':
                    from bpy_extras.object_utils import world_to_camera_view
                    scene = bpy.context.scene
                    cam = scene.camera
                    center = Vector(r['cylinder']['point_mm']) / 1000
                    edge = center + cam.matrix_world.to_quaternion() @ Vector((.020, 0, 0))
                    c = world_to_camera_view(scene, cam, center)
                    e = world_to_camera_view(scene, cam, edge)
                    width, height = scene.render.resolution_x, scene.render.resolution_y
                    r['gauge_projection_pixels'] = dict(center=[c.x*width, (1-c.y)*height], radius=abs(e.x-c.x)*width)
                r['renders_sha256'] = {v: sha(OUT/'renders'/f'{name}_{v}.png')
                                       for v in ('palm', 'back', 'thumb-side')}
            print(name, 'VOLUME XYZ mm', r['tip_relative_to_volume_mm'], 'VOLUME RADII', volume_r,
                  'SKIN CONTACT mm', r['distal_thumb_index_surface_gap_mm'], 'COLLISIONS', r['triangle_intersection_pairs'],
                  'WRIST', r['wrist_rotation_deg'], r['wrist_translation_mm'], 'NONHAND m', r['nonhand_pose_matched_displacement_m'],
                  'CYLINDER', r.get('cylinder'), flush=True)
    checks['geometry']['max_nonfinger_bind_matrix_difference'] = max(float(
        np.max(np.abs(m-original_rig[n]))) for n, m in arm_state(rig).items() if not ('Hand' in n and n[-1].isdigit()))
    checks['roundtrip'] = imported_playback(native_positions)
    g = checks['geometry']
    ex = checks['export']
    rt = checks['roundtrip']
    gates = dict(hierarchy=g['bones'] == 65 and g['vertex_groups'] == 65 and g['changed_parents'] == 0,
                 tri_budget=g['triangles'] <= 10000 and all(
                     v['triangles'] <= 3000 for v in checks['rest'].values()),
                 weights=g['unweighted'] == 0 and g['over_four'] == 0 and g['any_mixed_finger_chains'] == 0 and g['max_sum_error'] < 1e-5,
                 shafts=all(v['free_shaft_with_non_digit_weight'] == 0 for v in checks['rest'].values()),
                 palm=all(v['central_palmar_minimum_hand_weight'] > .9999 for v in checks['rest'].values()),
                 thenar=all(v['thenar_hand_weight_range'][0] > 0 and v['thenar_thumb_weight_range']
                            [0] > 0 for v in checks['rest'].values()),
                 nonhand=g['nonhand_max_displacement_m'] <= .0005 and g['nonhand_weight_changes'] == 0,
                 topology=all(v['welded_nonmanifold_hand_edges'] == 0 for v in checks['rest'].values()),
                 orientation=all(v['palm_normal'][2] < -.95 and v['thumb_direction']
                                 [1] < -.65 for v in checks['rest'].values()),
                 exports=ex['base_meshes'] == 1 and ex['base_skins'] == 1 and ex['base_animations'] == 0 and ex['clip_meshes'] == 0 and ex['joints'] == 65 and ex['base_triangles'] == g[
                     'triangles'] and ex['max_clip_quaternion_component_difference'] < 1e-5 and ex['max_export_weight_difference'] < 1e-5 and ex['max_inverse_bind_identity_error'] < 1e-5,
                 roundtrip=rt['imported_actions'] == 18 and max(rt['max_deformed_vertex_error_mm'].values()) < .02)
    checks['global_gates'] = gates
    checks['checks_failed'].extend(k for k, v in gates.items() if not v)
    print('ROUNDTRIP', rt, flush=True)
    print('BODY', checks['geometry'], 'EXPORT', checks['export'],
          'FAILURES', checks['checks_failed'], flush=True)
    (OUT/'hand_check.json').write_text(json.dumps(checks, indent=2)+'\n')
    if checks['checks_failed']:
        raise AssertionError(checks['checks_failed'])


if __name__ == '__main__':
    run_batch(main)
