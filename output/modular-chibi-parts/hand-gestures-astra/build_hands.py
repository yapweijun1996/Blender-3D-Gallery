"""Rebuild the gesture library offline from the unmodified repaired master."""
import hashlib
import json
import math
import sys
from pathlib import Path
from collections import defaultdict

import bmesh
import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hand_common import OUT, MASTER, DIGITS, SIDES, prefix, smooth, vertex_weights, clean_pose, run_batch


def refine(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # Subdivide long hand edges first, including both copies at UV seams.
    # Working from quantised endpoints keeps seam tessellation symmetric.
    split = []
    for sign in (-1, 1):
        options = defaultdict(list)
        for e in bm.edges:
            a, b = (v.co for v in e.verts)
            if min(sign*a.x, sign*b.x) <= .271:
                continue
            ends = tuple(sorted(tuple(round(q, 6) for q in p) for p in (a, b)))
            options[ends].append(e)
        scored = sorted(options.values(), key=lambda es: -es[0].calc_length())
        count = 0
        for es in scored:
            if count+len(es) > 425:
                break
            split.extend(es)
            count += len(es)
    bmesh.ops.subdivide_edges(bm, edges=split, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def soften(body):
    mesh = body.data
    # Work on welded spatial neighbours but keep the actual UV split.
    positions = [v.co.copy() for v in mesh.vertices]
    keys = [tuple(round(k, 6) for k in p) for p in positions]
    graph = defaultdict(set)
    ids = defaultdict(list)
    for i, k in enumerate(keys):
        ids[k].append(i)
    for e in mesh.edges:
        a, b = [keys[i] for i in e.vertices]
        if a != b:
            graph[a].add(b)
            graph[b].add(a)
    coords = {k: positions[g[0]] for k, g in ids.items()}
    w = {k: vertex_weights(body, mesh.vertices[g[0]]) for k, g in ids.items()}
    pure = {k: all(n[-1].isdigit() and 'Hand' in n for n in ws) for k, ws in w.items()}
    for _ in range(4):
        new = dict(w)
        xyz = dict(coords)
        for k in ids:
            x = abs(k[0])
            adj = graph[k]
            if x <= .271 or not adj:
                continue
            t = smooth(.271, .289, x)
            average = sum((coords[j] for j in adj), Vector())/len(adj)
            xyz[k] = coords[k].lerp(average, .35*t)
            # Restrict weight diffusion to the locally owned digit.
            own = {d: sum(v for n, v in w[k].items() if 'Hand'+d in n) for d in DIGITS}
            d = max(own, key=own.get)
            total = sum(own.values())
            accum = defaultdict(float)
            for j in adj:
                for n, v in w[j].items():
                    accum[n] += v/len(adj)
            pre = prefix('Left' if k[0] > 0 else 'Right')
            merged = defaultdict(float)
            factor = (.55 if d == 'Thumb' else .25)*t
            for n in w[k].keys() | accum.keys():
                val = (1-factor)*w[k].get(n, 0)+factor*accum[n]
                if n.startswith(pre) and n[-1].isdigit() and (not total or not n.startswith(pre+d)):
                    merged[pre] += val
                else:
                    merged[n] += val
            new[k] = dict(merged)
        coords, w = xyz, new
    for k, indices in ids.items():
        if abs(k[0]) <= .271:
            continue
        weights = w[k].copy()
        side = 'Left' if k[0] > 0 else 'Right'
        hand = prefix(side)
        owned = [n for n in weights if n.startswith(hand) and n[-1].isdigit()]
        if owned and hand in weights:
            # The shared saddle may blend with the palm. Beyond the web
            # each independent digit shaft is bound only to its own chain.
            thumb = all('Thumb' in n for n in owned)
            release = smooth(.051, .060, -coords[k].y) if thumb else smooth(.331, .339, abs(coords[k].x))
            weights[hand] *= 0 if pure[k] else 1-release
        q = coords[k]
        x = abs(q.x)
        # The heel can follow the wrist. Across the middle of the palm, the
        # palmar skin follows Hand rigidly, with a soft fade into both webs.
        center_y = -.01149 if side == 'Left' else -.01027
        band = smooth(.282, .292, x)*(1-smooth(.310, .321, x))
        pad = band*(1-smooth(.010, .016, abs(q.y-center_y)))*(1-smooth(.553, .568, q.z))
        thenar = band*(1-smooth(.009, .016, abs(q.y-center_y+.024)))*(1-smooth(.553, .566, q.z))
        if pad or thenar:
            for n in list(weights):
                if n == hand:
                    continue
                collapse = pad if 'Thumb' in n else max(pad, thenar)
                transfer = weights[n]*collapse
                weights[n] -= transfer
                weights[hand] = weights.get(hand, 0)+transfer
            other_chain = any(n[-1].isdigit() and 'Thumb' not in n and v > .0001 for n, v in weights.items())
            if thenar > 0 and not other_chain and weights.get(hand, 0) > 0:
                thumb = sum(v for n, v in weights.items() if 'Thumb' in n)
                transfer = min(weights[hand], max(0, .16*thenar-thumb))
                weights[hand] -= transfer
                weights[hand+'Thumb1'] = weights.get(hand+'Thumb1', 0)+transfer
        ws = sorted(((n, v) for n, v in weights.items() if v > .0001), key=lambda it: -it[1])[:4]
        total = sum(v for _, v in ws)
        for i in indices:
            vertex = mesh.vertices[i]
            vertex.co = coords[k]
            for n in list(vertex_weights(body, vertex)):
                body.vertex_groups[n].remove([i])
            for n, val in ws:
                body.vertex_groups[n].add([i], val/total, 'REPLACE')


def remodel(body, rig):
    mesh = body.data
    source_corner_normals = [n.vector.copy() for n in mesh.corner_normals]
    source_normals = {}
    normals_by_vertex = defaultdict(list)
    for f in mesh.polygons:
        key = tuple(sorted(f.vertices))
        for li in f.loop_indices:
            i = mesh.loops[li].vertex_index
            if abs(mesh.vertices[i].co.x) <= .271:
                normal = source_corner_normals[li]
                source_normals[key, i] = normal
                normals_by_vertex[i].append((f.normal.copy(), normal))
    refine(mesh)
    rest = [v.co.copy() for v in mesh.vertices]
    sides = {}
    for _, side, sg in SIDES:
        p = prefix(side)
        joints = {d: [rig.data.bones[p+d+str(i)].head_local.copy() for i in (1, 2, 3, 4)] for d in DIGITS}
        center = sum(a[0].y for d, a in joints.items() if d != 'Thumb')/4
        sides[sg] = (p, joints, center)

    def compact(v, center):
        q = v.copy()
        q.y -= .22*smooth(.271, .324, abs(q.x))*(q.y-center)
        return q
    for v in mesh.vertices:
        old = rest[v.index]
        x = abs(old.x)
        if x <= .271:
            continue
        p, joints, center = sides[1 if old.x > 0 else -1]
        q = compact(old, center)
        weights = vertex_weights(body, v)
        finger = {d: sum(weights.get(p+d+str(i), 0) for i in (1, 2, 3, 4)) for d in DIGITS}
        digit = max(finger, key=finger.get)
        chain = joints[digit]
        axis = (chain[3]-chain[0]).normalized()
        progress = (old-chain[0]).dot(axis)/(chain[3]-chain[0]).length
        near = chain[0]+axis*(old-chain[0]).dot(axis)
        taper = smooth(.32, 1, progress)*finger[digit]
        q.y -= (old.y-near.y)*.105*taper
        q.z -= (old.z-near.z)*.13*taper
        y = old.y-center
        def fall(a, b): return math.exp(-(a*a+b*b))
        underside = 1-smooth(.550, .571, old.z)
        pad = fall((x-.302)/.019, (y-.005)/.025)
        thenar = fall((x-.298)/.019, (y+.024)/.014)
        # Flatten the bulky dorsal carpus into a gentle slope to the MCPs.
        # The palmar pad, finger shafts and wrist attachment retain their height.
        dorsal = smooth(.548, .584, old.z)*smooth(.271, .296, x)*(1-smooth(.308, .342, x))
        q.z -= .0135*dorsal
        q.z -= underside*(.0027*pad+.0040*thenar)*smooth(.271, .286, x)
        q.y -= .0016*thenar*underside
        for d in DIGITS[:4]:
            for i, (width, rise) in enumerate(((.010, .0031), (.0065, .0018), (.005, .0011))):
                pivot = joints[d][i]
                bump = fall((old.x-pivot.x)/width, (old.y-pivot.y)/.008)
                q.z += rise*bump*smooth(pivot.z-.002, pivot.z+.010, old.z)
        v.co = q
        # Transfer an anatomically local part of the thenar pad to the CMC.
        # No foreign finger is introduced into another digit's web.
        if digit == 'Thumb' or finger[digit] < .000001:
            transfer = min(weights.get(p, 0), .22*thenar*underside*smooth(.278, .290, x))
            if transfer > .0001:
                weights[p] -= transfer
                weights[p+'Thumb1'] = weights.get(p+'Thumb1', 0)+transfer
        # Keep inherited longitudinal bind weights on the shafts. Renormalise
        # the entire edited patch after local thenar redistribution.
        for k in list(vertex_weights(body, v)):
            body.vertex_groups[k].remove([v.index])
        ws = sorted(((k, w) for k, w in weights.items() if w > .0001), key=lambda kv: -kv[1])[:4]
        total = sum(w for k, w in ws)
        for k, w in ws:
            body.vertex_groups[k].add([v.index], w/total, 'REPLACE')
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for sg, (p, joints, center) in sides.items():
        for d in DIGITS:
            for i in (1, 2, 3, 4):
                b = rig.data.edit_bones[p+d+str(i)]
                b.head, b.tail = compact(b.head, center), compact(b.tail, center)
                # Positive local X moves the shaft toward its local Z vector.
                # Thumb flexes in an oblique opposition plane.
                guide = Vector((sg*.85, .52, -.46)) if d == 'Thumb' else Vector((0, 0, -1))
                b.align_roll(guide)
    bpy.ops.object.mode_set(mode='OBJECT')
    soften(body)
    # Dissolve compatible triangle diagonals only on the rebuilt hands.
    # UV/normal seams, material boundaries and all body faces are retained.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    faces = [f for f in bm.faces if all(abs(v.co.x) > .280 for v in f.verts)]
    bmesh.ops.join_triangles(bm, faces=faces, cmp_seam=True, cmp_uvs=True, cmp_materials=True,
                             angle_face_threshold=math.radians(33), angle_shape_threshold=math.radians(48))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    for f in mesh.polygons:
        if all(abs(mesh.vertices[i].co.x) > .27 for i in f.vertices):
            f.use_smooth = True
    old = [n.vector.copy() for n in mesh.corner_normals]
    normals = defaultdict(Vector)
    for f in mesh.polygons:
        for i in f.vertices:
            if abs(mesh.vertices[i].co.x) > .271:
                normals[tuple(mesh.vertices[i].co)] += f.area*f.normal
    for loop in mesh.loops:
        q = mesh.vertices[loop.vertex_index].co
        if abs(q.x) > .271:
            old[loop.index] = old[loop.index].lerp(normals[tuple(q)].normalized(),
                                                   smooth(.271, .284, abs(q.x))).normalized()
    for f in mesh.polygons:
        key = tuple(sorted(f.vertices))
        for li in f.loop_indices:
            i = mesh.loops[li].vertex_index
            if i in normals_by_vertex:
                old[li] = source_normals.get((key, i)) or max(
                    normals_by_vertex[i], key=lambda pair: pair[0].dot(f.normal))[1]
    mesh.normals_split_custom_set(old)
    mesh.update()
    bpy.context.view_layer.update()


def build_actions(rig):
    library = json.loads((OUT/'hand_gestures.json').read_text())
    for name, rotations in library['gestures'].items():
        clean_pose(rig)
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        action.asset_mark()
        gesture, tag = name[5:].rsplit('_', 1)
        action.asset_data.description = gesture.replace(
            '_', ' ')+' | '+('Left' if tag == 'L' else 'Right')+' hand | frame 1'
        slot = action.slots.new('OBJECT', rig.name)
        anim = rig.animation_data_create()
        anim.action = action
        anim.action_slot = slot
        for bone_name, degrees in rotations.items():
            bone = rig.pose.bones[bone_name]
            bone.rotation_mode = 'XYZ'
            bone.rotation_euler = [math.radians(v) for v in degrees]
            bone.keyframe_insert(data_path='rotation_euler', frame=1, group=bone_name)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    rig = bpy.data.objects['Armature']
    body = bpy.data.objects['Base_Body']
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = 'NONE'
    remodel(body, rig)
    bpy.data.objects['Armature'].show_in_front = False
    build_actions(rig)
    clean_pose(rig)
    bpy.context.scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    for o in (body, rig):
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'hands_gestures.blend'))
    export = dict(export_format='GLB', use_selection=True, export_def_bones=False,
                  export_leaf_bone=False, export_rest_position_armature=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'base_body.glb'), export_animations=False,
                              export_influence_nb=4, **export)
    body.select_set(False)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'hand_gestures.glb'), export_animations=True,
                              export_animation_mode='ACTIONS', export_force_sampling=False, export_bake_animation=False,
                              export_anim_single_armature=True, export_optimize_animation_size=False,
                              export_frame_range=False, export_negative_frame='SLIDE', export_anim_slide_to_zero=True, **export)


def embed_previews():
    # Use captures from a successful render/check of this exact source.
    report = json.loads((OUT/'hand_check.json').read_text())
    blend = OUT/'hands_gestures.blend'
    assert not report['checks_failed']
    assert hashlib.sha256(blend.read_bytes()).hexdigest() == report['asset_sha256'][blend.name]
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False, use_scripts=False)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.preferences.filepaths.file_preview_type = 'NONE'
    for name, metrics in report['gestures'].items():
        gesture = name[5:].rsplit('_', 1)[0]
        view = 'thumb-side' if gesture in ('thumbs_up', 'grip_small', 'pinch') else 'palm'
        path = OUT/'renders'/f'{name}_{view}.png'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == metrics['renders_sha256'][view]
        action = bpy.data.actions[name]
        # Populate the resident Action preview without invoking the desktop
        # thumbnail cache. Read the PNG as display-referred colour.
        thumb = bpy.data.images.load(str(path), check_existing=False)
        thumb.colorspace_settings.name = 'Non-Color'
        thumb.scale(256, 224)
        preview = action.preview_ensure()
        preview.image_size = (256, 224)
        preview.image_pixels_float[:] = thumb.pixels[:]
        thumb.scale(32, 28)
        preview.icon_size = (32, 28)
        preview.icon_pixels_float[:] = thumb.pixels[:]
        bpy.data.images.remove(thumb)
        assert preview.image_size[0] == 256
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))


if __name__ == '__main__':
    run_batch(embed_previews if '--embed-previews' in sys.argv else main)
