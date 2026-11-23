"""Fit the original Tripo boot pair in Blender. See NOTES.md for QA commands."""

from collections import defaultdict, deque
import hashlib
import math
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
MASTER = HERE.parents[1] / 'master/GJH_Chibi_Master_rigged.blend'
MOTION = HERE.parents[3] / 'models/tripo-chibi-motion/motion.glb'
SOURCE = HERE / 'source_studio_retopo.glb'
NAME = 'shoes_boots_v1'
GLB = HERE / f'{NAME}.glb'
CLIPS = ('walk', 'run', 'wave', 'jump', 'idle', 'nod', 'dance')
SIDES = {1: 'Left', -1: 'Right'}
BONES = ('Foot', 'ToeBase', 'Leg')
GROUND = -.014
CUT_HEIGHT = .487
MARGIN = .0022


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind_names(sign):
    return [f'mixamorig:{SIDES[sign]}{bone}' for bone in BONES]


def master_scene():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ('Armature', 'Base_Body'))
    arm.animation_data_clear()
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    scene.frame_set(1)
    bpy.context.view_layer.update()
    assert np.allclose(arm.matrix_world, np.eye(4)) and np.allclose(body.matrix_world, np.eye(4))
    return scene, arm, body


def import_motion(scene):
    existing = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(MOTION))
    for ob in list(scene.objects):
        if ob not in existing:
            bpy.data.objects.remove(ob, do_unlink=True)
    assert all(clip in bpy.data.actions for clip in CLIPS)


def set_pose(scene, arm, clip, time):
    arm.animation_data_create()
    action = bpy.data.actions[clip] if clip != 'rest' else None
    if arm.animation_data.action != action:
        arm.animation_data.action = action
        if action:
            arm.animation_data.action_slot = action.slots[0]
        else:
            for bone in arm.pose.bones:
                bone.matrix_basis.identity()
    scene.frame_set(math.floor(time), subframe=time % 1)
    bpy.context.view_layer.update()


def frames(dense=True):
    yield 'rest', 1.0
    for clip in CLIPS:
        start, end = bpy.data.actions[clip].frame_range
        steps = 4 if dense and clip in ('walk', 'run') else 1
        times = {start, end, *(tick / steps for tick in range(math.ceil(start * steps),
                                                             math.floor(end * steps) + 1,
                                                             1 if dense else 3))}
        times.update(int(start + (end - start) * k / 12) for k in range(12))
        yield from ((clip, time) for time in sorted(times))


def topology(obj):
    obj.data.calc_loop_triangles()
    return np.array([tri.vertices[:] for tri in obj.data.loop_triangles], dtype=np.int32)


def evaluated_points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    coordinates = np.empty(3 * len(evaluated.data.vertices), dtype=np.float32)
    evaluated.data.vertices.foreach_get('co', coordinates)
    matrix = np.asarray(evaluated.matrix_world)
    return coordinates.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]


class Foot:
    def __init__(self, body, sign):
        self.center = Vector((.000722 + sign * .085205, .009, 0))
        points = np.array([tuple(v.co) for v in body.data.vertices])
        faces = topology(body)
        mask = (sign * points[:, 0] > 0) & (points[:, 2] < .202)
        self.faces = faces[mask[faces].all(axis=1)]
        self.points = [Vector(p) for p in points]
        self.tree = BVHTree.FromPolygons(self.points, self.faces.tolist(), all_triangles=True)
        points2d = [Vector(p[:2]) for p in points[mask & (points[:, 2] < .080)]]
        self.hull = [points2d[i] for i in geometry.convex_hull_2d(points2d)]
        self.minimum = points[mask & (points[:, 2] < .080)].min(0)
        self.maximum = points[mask & (points[:, 2] < .080)].max(0)
        groups = {body.vertex_groups[name].index: i for i, name in enumerate(bind_names(sign))}
        self.weights = np.zeros((len(points), len(groups)))
        for v in body.data.vertices:
            for group in v.groups:
                if group.group in groups:
                    self.weights[v.index, groups[group.group]] = group.weight

    def footprint_radius(self, direction, padding):
        center = self.center.xy
        limits = []
        for a, b in zip(self.hull, self.hull[1:] + self.hull[:1]):
            edge = b - a
            normal = Vector((edge.y, -edge.x)).normalized()
            if normal.dot(a - center) < 0:
                normal.negate()
            denominator = normal.dot(direction.xy)
            if denominator > 1e-6:
                limits.append((normal.dot(a - center) + padding) / denominator)
        return min(limits)

    def section(self, direction, height, padding):
        center = self.center.copy()
        center.z = height
        hit, _, _, distance = self.tree.ray_cast(center + .25 * direction, -direction, .25)
        assert hit is not None, (direction, height)
        return .25 - distance + padding

    def weight(self, point, plantar=False):
        hit = idx = None
        if plantar and point.z < .026:
            for inset in (0, .08, .18, .30):
                test = point.lerp(self.center, inset)
                hit, _, idx, _ = self.tree.ray_cast(Vector((test.x, test.y, -.05)), (0, 0, 1), .15)
                if hit is not None:
                    break
        if hit is None:
            hit, _, idx, _ = self.tree.find_nearest(point)
        corners = self.faces[idx]
        bary = geometry.barycentric_transform(hit, *(self.points[i] for i in corners),
                                              Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        weights = (self.weights[corners] * np.array(bary)[:, None]).sum(axis=0).clip(0)
        if weights.sum() < 1e-6:
            weights[2] = 1
        weights /= weights.sum()
        toe = smoothstep(.092, .116, -point.y)
        weights *= 1 - toe
        weights[1] += toe
        shaft = smoothstep(.077, .124, point.z)
        heel_collar = .92 * smoothstep(.033, .064, point.y) * smoothstep(.073, .092, point.z)
        leg = max(shaft, heel_collar)
        weights *= 1 - leg
        weights[2] += leg
        return weights


def boundary_cycles(edges):
    remaining = set(edges)
    while remaining:
        edge = min(remaining, key=lambda elem: elem.index)
        path = list(edge.verts)
        remaining.remove(edge)
        while path[-1] != path[0]:
            choices = [candidate for candidate in path[-1].link_edges if candidate in remaining]
            if not choices:
                break
            edge = min(choices, key=lambda elem: elem.index)
            remaining.remove(edge)
            path.append(edge.other_vert(path[-1]))
        yield path[:-1] if path[0] == path[-1] else path


def source_boot(source, sign, foot):
    # A rotation of +90 degrees maps the raw -X toe direction to -Y and
    # makes negative raw Y the character's left side.
    bm = bmesh.new()
    bm.from_mesh(source.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y * sign > 0], context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000005)
    bm.verts.index_update()
    bm.edges.index_update()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # Repair Tripo's small openings while reusing neighboring atlas islands.
    unseen = set(bm.verts)
    while unseen:
        first = min(unseen, key=lambda v: v.index)
        queue = [first]
        unseen.remove(first)
        component = []
        while queue:
            vertex = queue.pop()
            component.append(vertex)
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other in unseen:
                    unseen.remove(other)
                    queue.append(other)
        if len(component) > 100:
            patches = [e for e in bm.edges if e.is_boundary and e.verts[0] in component]
            filled = bmesh.ops.holes_fill(bm, edges=patches, sides=18)['faces']
            bmesh.ops.face_attribute_fill(bm, faces=filled, use_normals=True, use_data=True)

    raw = np.array([tuple(v.co) for v in bm.verts])
    upper = raw[raw[:, 2] > .515]
    center = (upper[:, :2].max(0) + upper[:, :2].min(0)) / 2
    toe = raw[raw[:, 0] < raw[:, 0].min() + .015, :2].mean(0)
    yaw = math.atan2(*(center - toe)[::-1])
    transform = Matrix.Rotation(math.pi / 2 - yaw, 3, 'Z')
    for vertex in bm.verts:
        vertex.co = transform @ (vertex.co - Vector((*center, 0)))

    # Split at a horizontal plane between the upper lip and the source's
    # shallow cup. The cup is its own connected component below that cut.
    cross = [f for f in bm.faces if min(v.co.z for v in f.verts) < CUT_HEIGHT <
             max(v.co.z for v in f.verts)]
    cut = list(dict.fromkeys([*cross, *(e for f in cross for e in f.edges),
                             *(v for f in cross for v in f.verts)]))
    bmesh.ops.bisect_plane(bm, geom=cut, dist=.000001, plane_co=(0, 0, CUT_HEIGHT),
                           plane_no=(0, 0, 1))
    below = {f for f in bm.faces if max(v.co.z for v in f.verts) < CUT_HEIGHT + .000003}
    center_faces = [f for f in below if f.calc_center_median().xy.length < .05]
    first = max(center_faces, key=lambda f: f.calc_center_median().z)
    cup = {first}
    queue = deque([first])
    while queue:
        face = queue.popleft()
        for edge in face.edges:
            for other in edge.link_faces:
                if other in below and other not in cup:
                    cup.add(other)
                    queue.append(other)
    assert 60 < len(cup) < 230, len(cup)
    bm.faces.index_update()
    border = [e for e in bm.edges if any(f in cup for f in e.link_faces) and
              any(f not in cup for f in e.link_faces)]
    bm.edges.index_update()
    ring, = list(boundary_cycles(border))
    assert len(ring) >= 15 and all(abs(v.co.z - CUT_HEIGHT) < .00001 for v in ring)
    if sum(a.co.xy.cross(b.co.xy) for a, b in zip(ring, ring[1:] + ring[:1])) < 0:
        ring.reverse()
    start = min(range(len(ring)), key=lambda i: math.atan2(ring[i].co.y, ring[i].co.x))
    ring = ring[start:] + ring[:start]
    ring_angles = np.maximum.accumulate([math.atan2(v.co.y, v.co.x) for v in ring])
    angles = ring_angles[0] + np.arange(21) * (math.tau / 21)

    # Retain the original UV under the laces, buckle, leather, welt and tread.
    # Map generated lining to a contiguous patch from the original footbed.
    # A separate UV island at the collar avoids crossing source atlas seams.
    uv = bm.loops.layers.uv.active
    sample = sum((loop[uv].uv for loop in first.loops), Vector((0, 0))) / len(first.loops)
    bmesh.ops.delete(bm, geom=sorted(cup, key=lambda f: f.index), context='FACES')

    # Remove redundant planar triangles while protecting the atlas seams and
    # the cut rim. The rebuilt lining gets the recovered triangle budget.
    rim = set(ring)
    eligible = [e for e in bm.edges if e.is_manifold and not any(v in rim for v in e.verts)]
    bmesh.ops.dissolve_limit(bm, angle_limit=.165, verts=[v for v in bm.verts if v not in rim], edges=eligible, delimit={'UV'})

    zmap = ((0, GROUND), (.030, GROUND), (.126, .011), (.152, .020),
            (.232, .052), (.312, .080), (.459, .121), (.556, .145))
    rotated = [v.co.copy() for v in bm.verts]
    bounds = np.asarray([tuple(v) for v in rotated if v.z < .136])
    y_min, y_max = bounds[:, 1].min(), bounds[:, 1].max()
    corner_y = lambda y: y / abs(y_min if y < 0 else y_max) * (
        (foot.center.y - foot.minimum[1] + .010) if y < 0 else
        (foot.maximum[1] - foot.center.y + .008))
    inner_xy = [Vector((v.co.x * .343, corner_y(v.co.y), 0)) for v in ring]
    inner_angles = np.array([math.atan2(v.y, v.x) for v in inner_xy])
    inner_radii = np.array([v.length for v in inner_xy])
    bottom = []
    for vertex in bm.verts:
        source_point = vertex.co.copy()
        x, y, z = source_point
        y = corner_y(y)
        z = float(np.interp(z, *zip(*zmap)))
        local = Vector((x * .343, y, 0))
        direction = local.normalized()
        if source_point.z < .156 and local.length > .033:
            wanted = foot.footprint_radius(direction, .0070)
            amount = smoothstep(.034, .065, local.length) * (1 - smoothstep(.129, .163, source_point.z))
            local += direction * max(0, wanted - local.length) * amount
        if z > .086 and local.length > .022:
            theta = math.atan2(local.y, local.x)
            original_inner = np.interp(theta, inner_angles, inner_radii, period=math.tau)
            desired_inner = foot.section(direction, z, .0042)
            shell_thickness = max(0, local.length - original_inner)
            desired = desired_inner + .56 * shell_thickness
            strength = smoothstep(.086, .121, z)
            local = local.lerp(direction * desired, strength)
        vertex.co = Vector((foot.center.x + local.x, foot.center.y + local.y, z))
        if source_point.z < .154 and vertex.normal.z < -.48:
            bottom.append(vertex)
    for vertex in bottom:
        # The central bridge of the block sole closes the high arch in the
        # source sculpt. The heel and forefoot share the same contact plane.
        vertex.co.z = min(vertex.co.z, GROUND + .0020)

    lining = set(ring)
    footbed = set()
    previous = ring
    for height, pad in ((.088, .0060), (.056, .0055), (.034, .0055),
                        (.016, .0048), (-.0080, .0045)):
        current = []
        for theta in angles:
            direction = Vector((math.cos(theta), math.sin(theta), 0))
            radius = (foot.section(direction, height, pad) if height > 0 else
                      foot.footprint_radius(direction, pad))
            p = foot.center + radius * direction
            p.z = height
            current.append(bm.verts.new(p))
        faces = []
        if previous is ring:
            i = j = 0
            while i < len(ring) or j < len(current):
                next_rim = ring_angles[i + 1] if i + 1 < len(ring) else angles[0] + math.tau
                next_inner = angles[j + 1] if j + 1 < len(current) else angles[0] + math.tau
                a, b = ring[i % len(ring)], current[j % len(current)]
                if i < len(ring) and (next_rim <= next_inner or j == len(current)):
                    faces.append((a, ring[(i + 1) % len(ring)], b))
                    i += 1
                else:
                    faces.append((a, current[(j + 1) % len(current)], b))
                    j += 1
        else:
            for i, a in enumerate(previous):
                j = (i + 1) % len(current)
                faces.append((a, previous[j], current[j], current[i]))
        for vertices in faces:
            f = bm.faces.new(vertices)
            f.smooth = True
            for loop in f.loops:
                loop[uv].uv = sample + .038 * (loop.vert.co - foot.center).xy
        lining.update(current)
        previous = current
        if height < 0:
            footbed.update(current)

    # Constrained triangulation provides skinning vertices inside the footbed
    # so the ball flexes along the same bands as the sidewall.
    flat = [v.co.xy for v in previous]
    outline = flat.copy()
    for y in np.linspace(foot.minimum[1], foot.maximum[1], 9):
        for x in np.linspace(foot.minimum[0] + .028, foot.maximum[0] - .028, 2):
            p = Vector((x, y))
            if all((b - a).cross(p - a) > .000045 for a, b in zip(outline, outline[1:] + outline[:1])):
                flat.append(p)
    out, _, faces, orig, _, _ = geometry.delaunay_2d_cdt(
        flat, [], [list(range(len(previous)))], 1, .000001)
    verts = []
    for p, sources in zip(out, orig):
        if sources and sources[0] < len(previous):
            verts.append(previous[sources[0]])
        else:
            new = bm.verts.new((*p, -.0080))
            verts.append(new)
            footbed.add(new)
            lining.add(new)
    for indices in faces:
        f = bm.faces.new([verts[i] for i in indices])
        f.smooth = True
        for loop in f.loops:
            loop[uv].uv = sample + .04 * (loop.vert.co - foot.center).xy

    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    separate_lining(bm, lining, rim, set(bottom), foot)
    for vertex in bm.verts:
        p = vertex.co
        # Give the posterior collar room during the high heel-to-thigh fold.
        rear = smoothstep(.014, .055, p.y)
        shaft = np.clip((p.z - .062) / .083, 0, 1)
        p.z -= .052 * rear * shaft
    bm.verts.index_update()
    flags = {
        'lining': [v.index for v in lining],
        'footbed': [v.index for v in footbed],
        'bottom': [v.index for v in bottom],
    }
    print('SOURCE', SIDES[sign], 'source toe angle from +X', round(180 + math.degrees(yaw), 2),
          'cup faces removed', len(cup), 'rim vertices', len(ring),
          'triangle count', len(bm.faces), flush=True)
    return bm, flags


def separate_lining(bm, lining, rim, bottom, foot):
    """Fit the Tripo surface around the rebuilt liner and keep the footbed hidden."""
    bm.verts.index_update()
    inner = [tuple(v.index for v in f.verts) for f in bm.faces if all(v in lining for v in f.verts)]
    outer_faces = [f for f in bm.faces if not all(v in lining for v in f.verts)]
    outer = [tuple(v.index for v in f.verts) for f in outer_faces]
    points = np.asarray([tuple(v.co) for v in bm.verts], np.float32)
    liner_tree = BVHTree.FromPolygons(points.tolist(), inner, all_triangles=True)
    top = min(v.co.z for v in rim)
    exterior = [v for v in bm.verts if v not in lining]
    center = foot.center
    for vertex in exterior:
        p = vertex.co
        if not -.008 < p.z < top - .0001:
            continue
        if vertex in bottom:
            p.z = GROUND + .0013
            continue
        start = Vector((center.x, center.y, p.z))
        radius = (p - start).length
        direction = (p - start).normalized()
        _, _, _, guide = liner_tree.ray_cast(start, direction, .20)
        if guide is not None:
            thickness = .0035 * smoothstep(0, .009, top - p.z)
            p += direction * max(0, guide + thickness - radius)
    points = np.asarray([tuple(v.co) for v in bm.verts], np.float32)
    pins = np.asarray([v in lining for v in bm.verts])
    is_bottom = np.asarray([v in bottom for v in bm.verts])
    points, pairs = push_around_liner(points, np.asarray(inner), np.asarray(outer), pins, is_bottom)
    for vertex in exterior:
        vertex.co = points[vertex.index]
    print('LINER SEPARATION', 'remaining internal pairs', pairs, flush=True)


def push_around_liner(points, inner, outer, pins, bottom, smooth=False):
    """Clear the liner along the real cut between outer and inner faces."""
    inner_list, outer_list = inner.tolist(), outer.tolist()
    liner_tree = BVHTree.FromPolygons(points.tolist(), inner_list, all_triangles=True)
    inside_corners = [set(poly) for poly in inner_list]
    outside_corners = [set(poly) for poly in outer_list]
    if smooth:
        adjacent = [set() for _ in points]
        for a, b, c in outer_list:
            adjacent[a].update((b, c))
            adjacent[b].update((a, c))
            adjacent[c].update((a, b))
        adjacent = [np.asarray(sorted(group), dtype=int) for group in adjacent]
    for _ in range(22 if smooth else 14):
        surface = BVHTree.FromPolygons(points.tolist(), outer_list, all_triangles=True)
        pairs = [(i, j) for i, j in sorted(liner_tree.overlap(surface))
                 if not inside_corners[i].intersection(outside_corners[j])]
        if not pairs:
            break
        inside, outside = np.asarray(pairs).T
        inside_tri = points[inner[inside]]
        outside_tri = points[outer[outside]]
        bary = intersection_probes(outside_tri, inside_tri)
        at = np.einsum('nki,nk->ni', outside_tri, bary)
        distances, normals, _ = signed_hits(liner_tree, at)
        offsets = np.zeros((len(points), 6), np.float32)
        constraints = np.zeros((len(points), 6, 3), np.float32)
        for corner in range(3):
            ids = outer[outside, corner]
            valid = ~pins[ids] & (bary[:, corner] > .075)
            ids = ids[valid]
            gradient = -normals[valid]
            stop = bottom[ids] & (gradient[:, 2] < -.15)
            gradient[stop] = (0, 0, -1)
            demand = (.00115 + distances[valid]).clip(.0007, .0024)
            if len(ids):
                accumulate_planes(ids, constraints, offsets, gradient, demand)
        move = (constraints * offsets[:, :, None]).sum(axis=1)
        if smooth:
            noise = np.array([move[ids].mean(axis=0) if len(ids) else np.zeros(3) for ids in adjacent])
            move = .92 * move + .29 * noise
            move[pins] = 0
            move[bottom & (offsets.max(axis=1) == 0), 2] = 0
        magnitude = np.linalg.norm(move, axis=1)
        move *= np.minimum(1, .0024 / magnitude.clip(1e-9))[:, None]
        points += move
    return points, len(pairs)


def finish_outer_shell(mesh, flags):
    mesh.calc_loop_triangles()
    triangles = np.asarray([tri.vertices[:] for tri in mesh.loop_triangles], dtype=np.int32)
    pins = np.zeros(len(mesh.vertices), dtype=bool)
    pins[flags['lining']] = True
    bottom = np.zeros(len(mesh.vertices), dtype=bool)
    bottom[flags['bottom']] = True
    points = np.asarray([tuple(v.co) for v in mesh.vertices], np.float32)
    original = points.copy()
    lining = pins[triangles].all(axis=1)
    points, remaining = push_around_liner(points, triangles[lining], triangles[~lining],
                                          pins, bottom, smooth=True)
    mesh.vertices.foreach_set('co', points.ravel())
    mesh.update()
    print('POST-FIT LINER', remaining, 'internal overlap pairs',
          'max outer shift mm', round(float(np.linalg.norm(points - original, axis=1).max() * 1000), 3),
          flush=True)


def cache_motion(scene, arm, body, dense):
    body_faces = topology(body)
    body_rest = np.array([tuple(v.co) for v in body.data.vertices])
    foot_region = (body_rest[body_faces, 2] < .203).all(axis=1)
    faces_list = body_faces.tolist()
    bind = [arm.pose.bones[name] for side in (1, -1) for name in bind_names(side)]
    inverse = [bone.bone.matrix_local.inverted() for bone in bind]
    samples, matrices, trees, body_positions = [], [], [], []
    for clip, time in frames(dense):
        set_pose(scene, arm, clip, time)
        samples.append((clip, time))
        matrices.append([np.asarray(bone.matrix @ inv)[:3] for bone, inv in zip(bind, inverse)])
        points = evaluated_points(body)
        body_positions.append(points)
        trees.append(BVHTree.FromPolygons(points.tolist(), faces_list,
                                          all_triangles=True))
    set_pose(scene, arm, 'rest', 1)
    signs = np.sign(body_rest[body_faces, 0].mean(axis=1))
    return samples, np.asarray(matrices, np.float32), trees, signs, body_positions, body_faces, foot_region


def posed_points(points, weights, transforms):
    homogeneous = np.column_stack((points, np.ones(len(points), dtype=np.float32)))
    return np.einsum('fbci,nb,ni->fnc', transforms, weights, homogeneous, optimize=True)


def signed_hits(tree, points):
    hits, normals, faces, _ = zip(*(tree.find_nearest(p) for p in points.tolist()))
    normal = np.asarray(normals, np.float32)
    distances = np.einsum('ij,ij->i', points - np.asarray(hits, np.float32), normal)
    return distances, normal, np.asarray(faces)


def intersection_probes(shoe_triangles, body_triangles):
    """Sample the segment crossing both triangles, using shoe barycentrics."""
    normals = [np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
               for t in (shoe_triangles, body_triangles)]
    row_ids, weights = [], []
    eye = np.eye(3)
    for reverse in (False, True):
        edge, plane = (body_triangles, shoe_triangles) if reverse else (shoe_triangles, body_triangles)
        normal = normals[0 if reverse else 1]
        heights = np.einsum('nki,ni->nk', edge - plane[:, :1], normal)
        for i in range(3):
            j = (i + 1) % 3
            h0, h1 = heights[:, i], heights[:, j]
            ids = np.flatnonzero((h0 * h1 <= 0) & (abs(h0 - h1) > 1e-15))
            mix = h0[ids] / (h0[ids] - h1[ids])
            hit = edge[ids, i] + mix[:, None] * (edge[ids, j] - edge[ids, i])
            a, b, c = plane[ids].transpose(1, 0, 2)
            u, v, w = b - a, c - a, hit - a
            dot = lambda x, y: np.einsum('ij,ij->i', x, y)
            uu, uv, vv = dot(u, u), dot(u, v), dot(v, v)
            wu, wv = dot(w, u), dot(w, v)
            determinant = (uu * vv - uv * uv).clip(1e-17)
            beta = (vv * wu - uv * wv) / determinant
            gamma = (uu * wv - uv * wu) / determinant
            bary = np.column_stack((1 - beta - gamma, beta, gamma))
            inside = bary.min(axis=1) > -.0005
            row_ids.append(ids[inside])
            weights.append(bary[inside] if reverse else eye[i] + mix[inside, None] * (eye[j] - eye[i]))
    indices, barys = np.concatenate(row_ids), np.concatenate(weights)
    count = np.bincount(indices, minlength=len(shoe_triangles))
    mean = np.zeros((len(shoe_triangles), 3))
    np.add.at(mean, indices, barys)
    mean[count == 0] = 1 / 3
    return (mean / count[:, None].clip(1)).clip(0, 1)


def accumulate_planes(active, normals, offsets, gradient, deficit):
    size = np.linalg.norm(gradient, axis=1)
    axis = np.abs(gradient).argmax(axis=1)
    group = 2 * axis + (gradient[np.arange(len(axis)), axis] > 0)
    for local in np.unique(group):
        selection = np.flatnonzero(group == local)
        ids = active[selection]
        demand = deficit[selection] / size[selection].clip(.28)
        order = np.lexsort((demand, ids))
        last = np.r_[np.diff(ids[order]) != 0, True]
        best = order[last]
        ids = ids[best]
        better = demand[best] > offsets[ids, local]
        winners = selection[best[better]]
        ids = active[winners]
        offsets[ids, local] = demand[best[better]]
        normals[ids, local] = gradient[winners] / size[winners, None].clip(.28)


def fit_boot(obj, foot, flags, side, samples, transforms, trees, body_signs, body_positions, body_faces, foot_region):
    points = np.array([tuple(v.co) for v in obj.data.vertices], dtype=np.float32)
    original = points.copy()
    polys = topology(obj)
    edges = np.asarray([edge.vertices[:] for edge in obj.data.edges], dtype=np.int32)
    probes = np.concatenate((np.column_stack((edges, edges[:, 1])), polys), axis=0)
    factors = np.full((len(probes), 3), 1 / 3, dtype=np.float32)
    factors[:len(edges)] = (.5, .5, 0)
    adjacency = [set() for _ in points]
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    adjacency = [np.asarray(sorted(group), dtype=int) for group in adjacency]
    weights = np.array([foot.weight(Vector(p), p[2] < .012) for p in points], np.float32)
    bottom = np.zeros(len(points), bool)
    bottom[flags['bottom']] = True
    bed = np.zeros(len(points), bool)
    bed[flags['footbed']] = True
    lining = np.zeros(len(points), bool)
    lining[flags['lining']] = True
    radial = points - np.array(foot.center, np.float32)
    radial[:, 2] = 0
    radial /= np.linalg.norm(radial, axis=1)[:, None].clip(1e-8)
    skin_linear = np.einsum('fbci,nb->fnci', transforms[..., :3], weights, optimize=True)
    count = len(points)
    best = None
    for iteration in range(14):
        posed = posed_points(points, weights, transforms)
        offsets = np.zeros((count, 6), np.float32)
        normals = np.zeros((count, 6, 3), np.float32)
        worst, overlaps, total_pairs, negative = (9, 0, 0, 0), 0, 0, 0
        for row, (tree, xyz) in enumerate(zip(trees, posed)):
            d, vertex_normal, vertex_face = signed_hits(tree, xyz)
            if d.min() < worst[0]:
                bad = int(d.argmin())
                worst = (float(d[bad]), row, bad, int(body_signs[vertex_face[bad]]))
            negative += int((d < .00055).sum())
            candidates = np.flatnonzero(d < MARGIN)
            corners = np.repeat(candidates[:, None], 3, axis=1)
            barys = np.tile((1, 0, 0), (len(candidates), 1))
            demands = MARGIN - d[candidates]
            contact_normals = vertex_normal[candidates]
            contact_faces = vertex_face[candidates]

            # A vertex with clearance greater than its distance to the probe
            # plus the margin certifies that the probe is clear.
            triangles = xyz[probes]
            pose_probes = np.einsum('nki,nk->ni', triangles, factors)
            delta = np.linalg.norm(triangles - pose_probes[:, None, :], axis=2)
            near = ((d[probes] - delta > .0017) & (factors > 0)).sum(axis=1) == 0
            if near.any():
                p, n, f = signed_hits(tree, pose_probes[near])
                masks = p < .0017
                corners = np.concatenate((corners, probes[near][masks]))
                barys = np.concatenate((barys, factors[near][masks]))
                demands = np.r_[demands, (.0017 - p[masks]) * .9]
                contact_normals = np.concatenate((contact_normals, n[masks]))
                contact_faces = np.r_[contact_faces, f[masks]]

            pairs = sorted(tree.overlap(BVHTree.FromPolygons(xyz.tolist(), polys.tolist(), all_triangles=True)))
            if pairs and iteration > 0:
                body_ids, shoe_ids = np.asarray(pairs).T
                face_corners = polys[shoe_ids]
                bary = intersection_probes(xyz[face_corners], body_positions[row][body_faces[body_ids]])
                xyz_hits = np.einsum('nki,nk->ni', xyz[face_corners], bary)
                p, n, f = signed_hits(tree, xyz_hits)
                masks = p < .00125
                corners = np.concatenate((corners, face_corners[masks]))
                barys = np.concatenate((barys, bary[masks]))
                demands = np.r_[demands, .00125 - p[masks]]
                contact_normals = np.concatenate((contact_normals, n[masks]))
                contact_faces = np.r_[contact_faces, f[masks]]

            own_side = (body_signs[contact_faces] == side) & foot_region[contact_faces]
            for col in range(3):
                valid = barys[:, col] > .035
                ids = corners[valid, col]
                gradient = np.einsum('nij,ni->nj', skin_linear[row][ids], contact_normals[valid])
                own = own_side[valid]
                underside = own & (bed[ids] | bottom[ids])
                gradient[underside, :2] *= .08
                gradient[underside, 2] = np.minimum(-.28, gradient[underside, 2])
                # Keep most shaft movement in the horizontal cross-section.
                shaft = own & (original[ids, 2] > .074)
                gradient[shaft, 2] *= .18
                projection = (gradient * radial[ids]).sum(axis=1)
                outward = shaft & (projection > .33)
                gradient[outward] = .56 * gradient[outward] + (
                    .44 * projection[outward, None] * radial[ids[outward]])
                if len(ids):
                    accumulate_planes(ids, normals, offsets, gradient, demands[valid])
            pairs = len(pairs)
            total_pairs += pairs
            overlaps = max(overlaps, pairs)
        quality = (total_pairs + negative * 2, -worst[0])
        if best is None or quality < best[0]:
            best = (quality, points.copy(), iteration)
        print('FIT', obj.name, iteration, 'min vertex', round(worst[0], 6),
              'worst', samples[worst[1]], 'at', points[worst[2]].round(4).tolist(),
              'same side', worst[3] == side, 'max/total pairs', overlaps, total_pairs,
              'max offset mm', round(float(offsets.max() * 1000), 3), flush=True)
        if not overlaps and worst[0] >= .0010 and offsets.max() < .0013:
            break
        move = np.zeros_like(points)
        order = np.argsort(offsets, axis=1, kind='stable')
        rows = np.arange(count)
        for _ in range(2):
            for col in range(6):
                active = order[:, col]
                n = normals[rows, active]
                deficit = offsets[rows, active] - np.einsum('ij,ij->i', move, n)
                move += n * deficit.clip(0, .0060)[:, None]
        avg = np.array([move[group].mean(axis=0) if len(group) else np.zeros(3) for group in adjacency])
        move = .91 * move + np.where(lining[:, None], .16, .24) * avg
        # The flat contact tread stays fixed except for a genuine clearance witness.
        low = original[:, 2] < GROUND + .0001
        move[low & (offsets.max(axis=1) == 0), 2] = 0
        length = np.linalg.norm(move, axis=1)
        points += move * np.minimum(1, .0038 / length.clip(1e-9))[:, None]

    _, points, chosen = best
    shift = np.linalg.norm(points - original, axis=1)
    print('BAKED', obj.name, 'iteration', chosen, 'max/median offset mm',
          round(float(shift.max() * 1000), 3), round(float(np.median(shift) * 1000), 3), flush=True)
    obj.data.vertices.foreach_set('co', points.ravel())
    obj.data.update()
    return weights


def restore_tread_microrelief(mesh):
    """Recover valid normals where flattening made tread triangles collinear."""
    fixed = 0
    for check_tangents in (False, True):
        for _ in range(12):
            if check_tangents:
                mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
            candidates = {}
            for poly in mesh.polygons:
                vertices = list(poly.vertices)
                points = [mesh.vertices[i].co for i in vertices]
                if max(p.z for p in points) > GROUND + .004:
                    continue
                weak = (any(mesh.loops[i].tangent.length_squared < .5 for i in poly.loop_indices)
                        if check_tangents else poly.area < 1e-9)
                if not weak:
                    continue
                middle = max(range(3), key=lambda k: (
                    points[(k + 1) % 3] - points[(k + 2) % 3]).length_squared)
                vertex = vertices[middle]
                candidates[vertex] = max(candidates.get(vertex, -math.inf), points[middle].z + .00014)
            if check_tangents:
                mesh.free_tangents()
            if not candidates:
                break
            for vertex, height in sorted(candidates.items()):
                mesh.vertices[vertex].co.z = height
            fixed += len(candidates)
            mesh.update()
    print('TREAD MICRORELIEF', fixed, 'vertices adjusted', flush=True)
    return fixed


def export_glb(output):
    # The Tripo normal map needs baked tangents to avoid renderer-dependent
    # tangent generation. Keep the skinned mesh node at the scene root.
    bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True,
                              export_animations=False, export_yup=True, export_skins=True,
                              export_all_influences=False, export_def_bones=False,
                              export_tangents=True)


def save_native(arm, body, parts, material, output):
    for node in material.node_tree.nodes:
        if node.type != 'TEX_IMAGE':
            continue
        image = node.image
        w, h = image.size
        if max(w, h) > 1024:
            image.scale(round(1024 * w / max(w, h)), round(1024 * h / max(w, h)))
            image.file_format = 'PNG'
            image.pack()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    shoes = parts[0]
    shoes.name = shoes.data.name = NAME
    shoes.modifiers.new('Master skin', 'ARMATURE').object = arm
    restore_tread_microrelief(shoes.data)
    print('EXPORT TRIANGLES', len(topology(shoes)), flush=True)
    assert len(topology(shoes)) <= 3500
    assert len(arm.data.bones) == 65
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    arm.animation_data_clear()
    shoes.parent = arm
    body.hide_render = True
    body.hide_set(True)
    arm.select_set(False)
    arm.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                view = area.spaces.active.region_3d
                view.view_location = (0, -.017, .062)
                view.view_distance = .46
                view.view_rotation = Vector((.65, -.93, .54)).to_track_quat('Z', 'Y')
                area.spaces.active.shading.color_type = 'TEXTURE'
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend')), compress=True)


def build(output=GLB, dense=True):
    scene, arm, body = master_scene()
    before = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE), merge_vertices=True)
    source, = (o for o in scene.objects if o not in before and o.type == 'MESH')
    material, = source.data.materials
    material.name = 'Tripo tan leather, hardware and tread'
    import_motion(scene)
    samples, matrices, trees, body_signs, positions, faces, foot_region = cache_motion(scene, arm, body, dense)
    parts = []
    for index, sign in enumerate((1, -1)):
        foot = Foot(body, sign)
        bm, flags = source_boot(source, sign, foot)
        mesh = bpy.data.meshes.new(f'{SIDES[sign]} boot')
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(material)
        boot = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(boot)
        weights = fit_boot(boot, foot, flags, sign, samples, matrices[:, index * 3:(index + 1) * 3],
                           trees, body_signs, positions, faces, foot_region)
        for col, name in enumerate(bind_names(sign)):
            group = boot.vertex_groups.new(name=name)
            for vertex in np.flatnonzero(weights[:, col] > 1e-7):
                group.add([int(vertex)], float(weights[vertex, col]), 'REPLACE')
        parts.append(boot)
    bpy.data.objects.remove(source, do_unlink=True)
    save_native(arm, body, parts, material, output)
    polish_native(output)


def polish_native(output):
    bpy.ops.wm.open_mainfile(filepath=str(output.with_suffix('.blend')), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    shoes, body = (scene.objects[name] for name in (NAME, 'Base_Body'))
    existing = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE), merge_vertices=True)
    source, = (o for o in scene.objects if o not in existing and o.type == 'MESH')
    flags = {'lining': [], 'bottom': []}
    start = 0
    for side in (1, -1):
        bm, region = source_boot(source, side, Foot(body, side))
        native = np.array([shoes.data.vertices[i].co[:] for i in range(start, start + len(bm.verts))])
        source_points = np.asarray([tuple(v.co) for v in bm.verts])
        assert np.all(native[:, 0] * side > 0)
        assert np.median(np.linalg.norm(native - source_points, axis=1)) < .00025
        for name in flags:
            flags[name].extend(i + start for i in region[name])
        start += len(bm.verts)
        bm.free()
    assert start == len(shoes.data.vertices)
    bpy.data.objects.remove(source, do_unlink=True)
    finish_outer_shell(shoes.data, flags)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    bpy.ops.object.select_all(action='DESELECT')
    shoes.select_set(True)
    bpy.context.view_layer.objects.active = shoes
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend')), compress=True)
    reexport(output)


def reexport(output):
    bpy.ops.wm.open_mainfile(filepath=str(output.with_suffix('.blend')), load_ui=False, use_scripts=False)
    arm, shoes = (bpy.context.scene.objects[name] for name in ('Armature', NAME))
    arm.hide_set(False)
    shoes.hide_set(False)
    fixed = restore_tread_microrelief(shoes.data)
    shoes.parent = None
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    shoes.select_set(True)
    bpy.context.view_layer.objects.active = shoes
    export_glb(output)
    if fixed:
        shoes.parent = arm
        arm.select_set(False)
        arm.hide_set(True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend')), compress=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    output = Path(args[args.index('--output') + 1]).resolve() if '--output' in args else GLB
    assert output.is_relative_to(HERE)
    if '--polish' in args:
        polish_native(output)
    elif '--reexport' in args:
        reexport(output)
    else:
        build(output, dense='--draft' not in args)
