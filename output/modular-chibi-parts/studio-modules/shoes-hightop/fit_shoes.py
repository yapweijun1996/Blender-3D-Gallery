"""Fit, skin and verify the original Tripo high-tops with Blender 5.1."""

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree


HERE = Path(__file__).resolve().parent
MASTER = HERE.parents[1] / "master" / "GJH_Chibi_Master_rigged.blend"
MOTION = HERE.parents[3] / "models" / "tripo-chibi-motion" / "motion.glb"
SOURCE = HERE / "source_studio_retopo.glb"
NAME = "shoes_hightop_v1"
GLB = HERE / f"{NAME}.glb"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
SIDES = ((1, "Left"), (-1, "Right"))
MARGIN = 0.0018
FLOOR = -0.009
CUT = 0.43


def smoothstep(lo, hi, value):
    t = np.clip((value - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def mesh_triangles(mesh):
    mesh.calc_loop_triangles()
    return [tuple(t.vertices) for t in mesh.loop_triangles]


def coords(obj):
    return np.array([obj.matrix_world @ vertex.co for vertex in obj.data.vertices])


def load_master():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body = (scene.objects[name] for name in ("Armature", "Base_Body"))
    arm.animation_data_clear()
    set_pose(scene, arm, "rest", 1)
    return scene, arm, body


def import_objects(path):
    old = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return sorted(set(bpy.context.scene.objects) - old, key=lambda o: o.name)


def load_actions():
    for obj in import_objects(MOTION):
        bpy.data.objects.remove(obj, do_unlink=True)
    for name in CLIPS:
        bpy.data.actions[name].use_fake_user = True


def set_pose(scene, arm, clip, frame):
    data = arm.animation_data_create()
    data.action = bpy.data.actions[clip] if clip != "rest" else None
    if data.action:
        data.action_slot = data.action.slots[0]
    else:
        for bone in arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
    whole = math.floor(frame)
    scene.frame_set(whole, subframe=frame - whole)
    bpy.context.view_layer.update()


def schedule():
    yield "rest", 1.0
    for clip in CLIPS:
        a, b = bpy.data.actions[clip].frame_range
        step = 4 if clip in ("walk", "run") else 2
        frames = {a, b, *(tick / step for tick in range(math.ceil(a * step), math.floor(b * step) + 1))}
        frames.update(int(a + (b - a) * tick / 12) for tick in range(12))
        frames.update(range(int(a), int(b) + 1, 3))
        yield from ((clip, frame) for frame in sorted(frames))


def bounds_polygon(points):
    vectors = [Vector(xy) for xy in points]
    return np.array([vectors[i] for i in geometry.convex_hull_2d(vectors)])


def cross2(u, v):
    return u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]


def radii(border, center, directions):
    """Intersections with the boundary of a convex section from its interior."""
    starts = border - center
    edges = np.roll(border, -1, axis=0) - border
    if cross2(starts, edges).mean() < 0:
        return radii(border[::-1], center, directions)
    denominators = cross2(directions[..., None, :], edges)
    distances = np.divide(cross2(starts, edges), denominators,
                          out=np.full(denominators.shape, np.inf), where=denominators > 1e-7)
    return distances.min(axis=-1)


def unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True).clip(1e-8)


def barycentric(q, corners):
    triangle = [Vector(p) for p in corners]
    return np.array(geometry.barycentric_transform(
        Vector(q), *triangle, Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))


class Foot:
    def __init__(self, body, side):
        sign, name = side
        self.sign = sign
        self.names = tuple(f"mixamorig:{name}{part}" for part in ("Foot", "ToeBase", "Leg"))
        self.all_points = coords(body)
        self.faces = np.array([t for t in mesh_triangles(body.data)
                               if all(sign * self.all_points[i, 0] > 0 and
                                      self.all_points[i, 2] < .205 for i in t)])
        self.tree = BVHTree.FromPolygons(self.all_points.tolist(), self.faces.tolist(), all_triangles=True)
        self.skin = np.zeros((len(self.all_points), len(self.names)))
        ids = {body.vertex_groups[n].index: i for i, n in enumerate(self.names)}
        for v in body.data.vertices:
            for assignment in v.groups:
                if assignment.group in ids:
                    self.skin[v.index, ids[assignment.group]] = assignment.weight
        skin_ids = np.unique(self.faces)
        self.low = self.all_points[skin_ids][self.all_points[skin_ids, 2] < .077]
        self.center = np.array([(self.low[:, 0].min() + self.low[:, 0].max()) / 2, .013])
        self.outline = bounds_polygon(self.low[:, :2])
        self.section_cache = {}
        self.tris = self.all_points[self.faces]

    def section(self, height):
        h = round(float(height), 3)
        if h not in self.section_cache:
            a = self.tris
            b = np.roll(a, 1, axis=1)
            dz = b[..., 2] - a[..., 2]
            ii, jj = np.where((np.minimum(a[..., 2], b[..., 2]) <= h) &
                              (h <= np.maximum(a[..., 2], b[..., 2])) & (abs(dz) > 1e-8))
            fraction = (h - a[ii, jj, 2]) / dz[ii, jj]
            xy = a[ii, jj, :2] + fraction[:, None] * (b[ii, jj, :2] - a[ii, jj, :2])
            self.section_cache[h] = bounds_polygon(xy)
        return self.section_cache[h]

    def radius(self, height, direction):
        return radii(self.section(height), self.center, direction)

    def blend(self, point, plantar=False):
        x, y, z = point
        if plantar:
            # Query the underside slightly inboard when outside the footprint.
            dv = np.array([x, y]) - self.center
            dr = unit(dv)
            reach = radii(self.outline, self.center, dr)
            if np.linalg.norm(dv) > reach - .002:
                x, y = self.center + dr * (reach - .002)
            hit, _, face, _ = self.tree.ray_cast((x, y, -.12), (0, 0, 1), .240)
        else:
            hit = None
        if hit is None:
            q, _, face, _ = self.tree.find_nearest((x, y, z))
        else:
            q = hit
        indices = self.faces[face]
        w = barycentric(q, self.all_points[indices]) @ self.skin[indices]
        w = w.clip(0)
        w /= w.sum()
        toe_bias = 0.8 * smoothstep(.082, .113, -y)
        w = w * (1 - toe_bias) + (0, toe_bias, 0)
        return w / w.sum()


@dataclass
class Shoe:
    foot: Foot
    points: np.ndarray
    weights: np.ndarray
    directions: np.ndarray
    faces: list
    uv: list
    sole_faces: list
    source_triangles: int
    outsole: np.ndarray
    bed: np.ndarray
    seam: np.ndarray


def cavity_cut(bm, sign):
    seed = min((f for f in bm.faces if f.calc_center_median().x * sign > 0
                and f.normal.z > .7),
               key=lambda f: (f.calc_center_median() - Vector((sign * .26, .15, .18))).length)
    inside = {seed}
    queue = [seed]
    for face in queue:
        for edge in face.edges:
            for candidate in edge.link_faces:
                if candidate not in inside and all(v.co.z < CUT for v in candidate.verts):
                    inside.add(candidate)
                    queue.append(candidate)
    boundary = {e for f in inside for e in f.edges if any(g not in inside for g in e.link_faces)}
    layer = bm.loops.layers.uv.active
    records = {}
    for edge in boundary:
        outside, = (f for f in edge.link_faces if f not in inside)
        loop, = (loop for loop in outside.loops if loop.edge == edge)
        # Traverse opposite to the exterior winding.
        a, b = loop.link_loop_next, loop
        records[a.vert] = b.vert, tuple(a[layer].uv)
    first = min(records, key=lambda v: v.index)
    ring = [first]
    while (nxt := records[ring[-1]][0]) != first:
        ring.append(nxt)
    assert len(ring) == len(records) and 12 <= len(ring) <= 24
    return inside, ring, [records[v][1] for v in ring]


def weld_source(source):
    bm = bmesh.new()
    bm.from_mesh(source.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bm.normal_update()
    bm.verts.index_update()
    bm.faces.index_update()
    # Tripo can put coincident flap triangles at a few lace seams.
    from collections import defaultdict
    by_corners = defaultdict(list)
    for face in bm.faces:
        by_corners[tuple(sorted(v.index for v in face.verts))].append(face)
    extras = [face for group in by_corners.values() if len(group) > 1 for face in group[1:]]
    if extras:
        bmesh.ops.delete(bm, geom=extras, context="FACES_ONLY")
    return bm


def shape_exterior(native, ring_source, foot):
    sign = foot.sign
    original_center = np.array([sign * .257, .145])
    xyz = np.copy(native)
    normal_width = .331
    yscale = .245
    base_xy = (native[:, :2] - original_center) * (normal_width, yscale)
    scaled_ring = (ring_source[:, :2] - original_center) * (normal_width, yscale)
    cuff = bounds_polygon(scaled_ring)
    source_sole = bounds_polygon(base_xy[native[:, 2] < .165])
    angle = unit(base_xy)
    r = np.linalg.norm(base_xy, axis=1)
    sole_radius = radii(source_sole, np.zeros(2), angle)
    desired_sole = radii(foot.outline, foot.center, angle) + .0072
    sole_ratio = 1 - smoothstep(.158, .295, native[:, 2])
    xy = base_xy * (1 + sole_ratio * (desired_sole / sole_radius - 1))[:, None]
    z = native[:, 2]
    xyz[:, 2] = np.where(z <= .083, FLOOR + .0021 * z / .083,
                         FLOOR + .0021 + .320 * (z - .083))
    # Retain the molded cuff but increase its opening for the stocky ankles.
    collar_fade = smoothstep(.204, .393, native[:, 2])
    collar_radius = radii(cuff, np.zeros(2), angle)
    target_radii = np.array([foot.radius(max(.049, min(.151, h)), d)
                             for h, d in zip(xyz[:, 2], angle)])
    cuff_r = target_radii + .0049 + (r - collar_radius) * .39
    xy = xy * (1 - collar_fade[:, None]) + angle * (collar_fade * cuff_r)[:, None]
    xyz[:, :2] = xy + foot.center
    return xyz


def make_shoe(bm, foot):
    inside, rim, rim_uv = cavity_cut(bm, foot.sign)
    layer = bm.loops.layers.uv.active
    outer_faces = [f for f in bm.faces if f not in inside and
                   all(foot.sign * v.co.x > 0 for v in f.verts)]
    used = sorted({v for f in outer_faces for v in f.verts}, key=lambda v: v.index)
    index = {v: i for i, v in enumerate(used)}
    faces = [tuple(index[v] for v in f.verts) for f in outer_faces]
    uv = [tuple(tuple(loop[layer].uv) for loop in f.loops) for f in outer_faces]
    native = np.array([v.co[:] for v in used])
    sole_faces = [bool(max(native[list(face), 2]) < .178) for face in faces]
    source_count = len(faces)
    ring = [index[v] for v in rim]
    seam = np.array(ring)
    ring_source = native[ring]
    x = shape_exterior(native, ring_source, foot)
    d = unit(x[:, :2] - foot.center)
    dirs = np.column_stack((d, np.zeros(len(x))))
    # At the toe and instep the outward ray also has an upward component.
    from_axis = x - np.column_stack((np.full(len(x), foot.center[0]),
                                     np.clip(x[:, 1], -.078, .030),
                                     np.full(len(x), .017)))
    vamp = smoothstep(-.018, -.078, x[:, 1]) * (1 - smoothstep(.063, .090, x[:, 2]))
    dirs = unit(dirs * (1 - vamp[:, None]) + unit(from_axis) * vamp[:, None])
    low = x[:, 2] < .001
    dirs[low] = unit(np.column_stack((.12 * d[low], -np.ones(low.sum()))))
    # Keep a toe-facing direction even for a low sidewall; the tread only
    # ever moves down, which preserves its coverage from below.
    x_list = list(x)
    d_list = list(dirs)
    w_list = [foot.blend(p, p[2] < .025) for p in x]
    bottom = np.flatnonzero(native[:, 2] <= .083)

    rim_dirs = unit(x[ring, :2] - foot.center)
    angles = np.unwrap(np.arctan2(rim_dirs[:, 1], rim_dirs[:, 0]))
    assert abs(angles[-1] - angles[0]) > 4, angles
    # Cavity UVs sample the original lining. Exterior loop UVs are retained.
    rim_uv = np.array(rim_uv)
    uv_center = rim_uv.mean(axis=0)
    current_uv = rim_uv
    prev_z = x[ring, 2]
    sections = (.085, .064, .045, .025, -.0044)
    bed = []
    for j, h in enumerate(sections):
        # A flexible transition under the tongue clears the instep without
        # placing the wall in the original shallow Tripo foot pocket.
        if j == 0:
            heights = np.minimum(prev_z - .006, h)
        else:
            heights = np.full(len(ring), h)
        if h < 0:
            radius = radii(foot.outline, foot.center, rim_dirs) + .0044
        else:
            radius = np.array([foot.radius(max(.02, z), d)
                               for z, d in zip(heights, rim_dirs)]) + .0057
            if h == .025:
                radius = np.maximum(radius, radii(foot.outline, foot.center, rim_dirs) + .0038)
        row = []
        row_uv = uv_center + (rim_uv - uv_center) * (1 - .09 * (j + 1))
        for direction, distance, z in zip(rim_dirs, radius, heights):
            p = np.r_[foot.center + direction * distance, z]
            row.append(len(x_list))
            x_list.append(p)
            d_list.append(np.r_[direction, 0.] if h > 0 else np.array([0., 0., -1.]))
            w_list.append(foot.blend(p, h <= .025))
        for i in range(len(ring)):
            k = (i + 1) % len(ring)
            faces.extend(((ring[i], ring[k], row[k]), (ring[i], row[k], row[i])))
            uv.extend(((current_uv[i], current_uv[k], row_uv[k]), (current_uv[i], row_uv[k], row_uv[i])))
            sole_faces.extend((h < 0, h < 0))
        ring, current_uv = row, row_uv
        prev_z = heights
    # A constrained triangulation with short diagonals across the ball of the
    # foot prevents the lining from bridging across flexing skin.
    planar = [Vector(x_list[i][:2]) for i in ring]
    all_uv = list(current_uv)
    bed = ring.copy()
    border = bounds_polygon(planar)
    for y in (-.100, -.080, -.062, -.039, -.013, .016, .045, .066):
        for dx in (-.036, 0, .036):
            p = np.array([foot.center[0] + dx, y])
            vec = p - foot.center
            if np.linalg.norm(vec) > radii(border, foot.center, unit(vec)) - .004:
                continue
            planar.append(Vector(p))
            bed.append(len(x_list))
            all_uv.append(uv_center + np.array([dx * .18, (y - .013) * .15]))
            pt = np.r_[p, -.0044]
            x_list.append(pt)
            d_list.append(np.array([0., 0., -1.]))
            w_list.append(foot.blend(pt, True))
    _, _, triangles, source, _, _ = geometry.delaunay_2d_cdt(
        planar, [], [list(range(len(ring)))], 1, 1e-6)
    winding = 1 if angles[-1] > angles[0] else -1
    for triangle in triangles:
        ids = [source[i][0] for i in triangle]
        a, b, c = [planar[i] for i in ids]
        if math.copysign(1, (b - a).cross(c - a)) != winding:
            ids.reverse()
        faces.append(tuple(bed[i] for i in ids))
        uv.append(tuple(all_uv[i] for i in ids))
        sole_faces.append(True)
    return Shoe(foot, np.array(x_list), np.array(w_list), np.array(d_list),
                faces, uv, sole_faces, source_count, bottom, np.array(bed), seam)


def close_bed_holes(shoe):
    # CDT can skip an almost collinear triangle at the bed seam.
    # Fill those pockets using their boundary order and original loop UVs.
    bed_set = set(shoe.bed)
    edges, bed_uv = {}, {}
    start = shoe.source_triangles
    for face, uv in zip(shoe.faces[start:], shoe.uv[start:]):
        bed_uv.update((v, st) for v, st in zip(face, uv) if v in bed_set)
        for a, b in zip(face, face[1:] + face[:1]):
            if a in bed_set and b in bed_set:
                edge = tuple(sorted((a, b)))
                edges[edge] = (b, a) if edge not in edges else None
    missing = {edge[0]: edge[1] for edge in edges.values() if edge}
    while missing:
        start = min(missing)
        hole = [start, missing.pop(start)]
        while (next_vert := missing.pop(hole[-1])) != start:
            hole.append(next_vert)
        assert len(hole) == 3
        shoe.faces.append(tuple(hole))
        shoe.uv.append(tuple(bed_uv[i] for i in hole))
        shoe.sole_faces.append(True)



def bake_motion(scene, arm, body, feet):
    if not all(name in bpy.data.actions for name in CLIPS):
        load_actions()
    bones = [[arm.pose.bones[n] for n in foot.names] for foot in feet]
    inverses = [[bone.bone.matrix_local.inverted() for bone in side] for side in bones]
    frames = list(schedule())
    matrices = [[], []]
    trees = [[], []]
    full = []
    body_faces = mesh_triangles(body.data)
    modes = tuple(b.rotation_mode for b in arm.pose.bones)
    for clip, frame in frames:
        set_pose(scene, arm, clip, frame)
        current = coords(body.evaluated_get(bpy.context.evaluated_depsgraph_get())).tolist()
        full.append(BVHTree.FromPolygons(current, body_faces, all_triangles=True))
        for i, foot in enumerate(feet):
            trees[i].append(BVHTree.FromPolygons(current, foot.faces.tolist(), all_triangles=True))
            matrices[i].append(np.array([bone.matrix @ inverse for bone, inverse
                                        in zip(bones[i], inverses[i])])[:, :3, :])
    assert modes == tuple(b.rotation_mode for b in arm.pose.bones)
    set_pose(scene, arm, "rest", 1)
    return frames, [(np.array(m), t) for m, t in zip(matrices, trees)], full


def signed(tree, point):
    near, normal, _, _ = tree.find_nearest(point)
    return (Vector(point) - near).dot(normal), normal


# Include the three edges because sparse vertices alone fail on long diagonals.
WITNESSES = np.array([(a / 5, b / 5, (5 - a - b) / 5)
                      for a in range(6) for b in range(6 - a)
                      if max(a, b, 5 - a - b) < 5])


def fit_motion(shoe, frames, data, label="foot"):
    """Project contact gradients through each vertex's blended rest transform."""
    matrices, trees = data
    skin = np.einsum("fbjk,vb->fvjk", matrices, shoe.weights)
    linear = skin[..., :3]
    preferred = shoe.directions
    triangles = np.array(shoe.faces, dtype=np.int32)
    tri_list = triangles.tolist()
    a, b = triangles.ravel(), np.roll(triangles, 1, axis=1).ravel()
    a, b = np.unique(np.c_[np.r_[a, b], np.r_[b, a]], axis=0).T
    degree = np.bincount(a)
    points = shoe.points.copy()
    underfoot = np.zeros(len(points), dtype=bool)
    underfoot[np.r_[shoe.bed, shoe.outsole]] = True
    target = np.full(len(points), MARGIN)
    target[underfoot] = .00155
    history = []
    best = None

    def store(ids, gradients, depths, largest, vectors):
        # Favor an outward solution, while allowing surface tangents to solve
        # triangle contacts between points whose nominal rays diverge.
        normal = preferred[ids]
        aligned = np.einsum("...i,...i->...", gradients, normal)
        correction = .55 * gradients + .45 * aligned[..., None] * normal
        tread = underfoot[ids]
        correction[tread, 2] = np.minimum(0, correction[tread, 2])
        correction[tread, :2] *= .22
        response = np.einsum("...i,...i->...", gradients, correction)
        sizes = depths / np.sum(response, axis=1).clip(.065)
        moves = sizes[:, None, None] * correction
        strength = np.linalg.norm(moves, axis=-1)
        axis = np.argmax(np.abs(moves), axis=-1)
        direction = np.take_along_axis(moves, axis[..., None], axis=-1)[..., 0] > 0
        slots = 6 * ids + 2 * axis + direction
        np.maximum.at(largest, slots, strength)
        chosen = (strength >= largest[slots]) & (strength > 0)
        vectors[slots[chosen]] = moves[chosen]

    for iteration in range(20):
        all_posed = np.einsum("fvij,vj->fvi", linear, points) + skin[..., 3]
        strongest = np.zeros(len(points) * 6)
        offsets = np.zeros((len(points) * 6, 3))
        stats = {"overlap_pairs": 0, "vertices_inside": 0, "minimum_m": 9.0}
        residuals = Counter()
        affected = Counter()
        for f, (posed, tree) in enumerate(zip(all_posed, trees)):
            posed_list = posed.tolist()
            hits = [signed(tree, p) for p in posed_list]
            distance = np.array([hit[0] for hit in hits])
            stats["minimum_m"] = min(stats["minimum_m"], float(distance.min()))
            stats["vertices_inside"] += int(np.count_nonzero(distance < 0))
            active, = np.where(distance < target)
            if len(active):
                normal = np.array([hits[i][1][:] for i in active])
                gradients = np.einsum("ni,nij->nj", normal, linear[f, active])
                store(active[:, None], gradients[:, None], target[active] - distance[active],
                      strongest, offsets)
                affected.update(active[distance[active] < .00045].tolist())
            shoe_tree = BVHTree.FromPolygons(posed_list, tri_list, all_triangles=True)
            pairs = tree.overlap(shoe_tree)
            stats["overlap_pairs"] += len(pairs)
            if pairs:
                residuals[frames[f]] += len(pairs)
                face_ids = sorted({pair[1] for pair in pairs})
                corners = triangles[face_ids]
                xyz = np.einsum("ab,fbc->fac", WITNESSES, posed[corners])
                hits = [signed(tree, p) for p in xyz.reshape(-1, 3).tolist()]
                values = np.array([h[0] for h in hits]).reshape(len(corners), -1)
                sample = values.argmin(axis=1)
                rows = np.arange(len(corners))
                n = np.array([hits[r * len(WITNESSES) + k][1][:] for r, k in zip(rows, sample)])
                factor = WITNESSES[sample]
                gradient = np.einsum("fi,fcij->fcj", n, linear[f, corners]) * factor[..., None]
                depth = np.maximum(.0008, MARGIN - values[rows, sample])
                store(corners, gradient, depth, strongest, offsets)
                affected.update(corners.ravel().tolist())

        stats["max_offset_m"] = float(np.linalg.norm(points - shoe.points, axis=1).max())
        history.append(stats)
        print("FIT", label, shoe.foot.sign, iteration, stats, residuals.most_common(3),
              [(i, np.round(points[i], 4).tolist(), n) for i, n in affected.most_common(3)], flush=True)
        score = stats["overlap_pairs"] + 10 * stats["vertices_inside"] + 10000 * max(0, .00115 - stats["minimum_m"])
        if best is None or score < best[0]:
            best = score, points.copy()
        if stats["overlap_pairs"] == 0 and stats["minimum_m"] >= .00115:
            break
        largest = strongest.reshape(-1, 6)
        all_offsets = offsets.reshape(-1, 6, 3)
        importance = largest ** 1.1
        delta = (all_offsets * importance[..., None]).sum(axis=1) / importance.sum(axis=1).clip(1e-10)[:, None]
        # Spread a small correction over one-ring neighbors. Keep fixes local
        # to preserve the molded toe, raised stars and broad plantar contact.
        neighbor = np.stack([np.bincount(a, delta[b, k], minlength=len(points)) / degree
                             for k in range(3)], axis=1)
        neighbor[underfoot, 2] = np.minimum(0, neighbor[underfoot, 2])
        delta += .19 * neighbor
        delta *= np.minimum(1.0, .005 / np.linalg.norm(delta, axis=1).clip(1e-10))[:, None]
        points += .88 * delta
    shoe.points = best[1]
    return history


def separate_wall(shoe, floor):
    """Place the opaque exterior outside the deeper liner and bed."""
    points = shoe.points
    exterior = np.array(shoe.faces[:shoe.source_triangles])
    interior = np.array(shoe.faces[shoe.source_triangles:])
    outer_count = exterior.max() + 1
    shell = points[:outer_count]
    z = shell[:, 2].copy()
    radial = unit(shell[:, :2] - shoe.foot.center)
    fade = 1 - smoothstep(.060, .087, z)
    shell[:, :2] += radial * (fade * .0037)[:, None]
    toe_cap = smoothstep(-.025, -.098, shell[:, 1]) * smoothstep(.008, .025, z)
    shell[:, 2] += .0038 * fade * toe_cap
    # Give both soles a continuous plantar floor while letting the sculpted
    # edge turn up. Upper/sole UV boundaries stay shared.
    old_floor = z[shoe.outsole].min()
    safe_floor = floor - old_floor
    shell[:, 2] += safe_floor * (1 - smoothstep(-.005, .016, z))
    shell[shoe.outsole, 2] = floor + .0012 * smoothstep(-.009, -.0067, z[shoe.outsole])

    pinned = np.zeros(outer_count, dtype=bool)
    pinned[shoe.seam] = True
    body_zone = z > .087
    a, b = exterior.ravel(), np.roll(exterior, 1, axis=1).ravel()
    a, b = np.unique(np.c_[np.r_[a, b], np.r_[b, a]], axis=0).T
    degree = np.bincount(a)
    inner_tree = BVHTree.FromPolygons(points.tolist(), interior.tolist(), all_triangles=True)
    initial = shell.copy()
    for iteration in range(14):
        outer_tree = BVHTree.FromPolygons(points.tolist(), exterior.tolist(), all_triangles=True)
        contacts = [(i, j) for i, j in inner_tree.overlap(outer_tree)
                    if not np.isin(interior[i], exterior[j]).any()
                    and z[exterior[j]].min() < .087]
        if not contacts:
            print("WALL", shoe.foot.sign, iteration, 0, flush=True)
            break
        active = sorted({j for _, j in contacts})
        corners = exterior[active]
        sample = np.einsum("ab,fbc->fac", WITNESSES, shell[corners])
        get = [signed(inner_tree, p) for p in sample.reshape(-1, 3).tolist()]
        distance = np.array([s for s, _ in get]).reshape(len(corners), -1)
        worst = distance.argmax(axis=1)
        depth = np.maximum(.0012, distance[np.arange(len(active)), worst] + .0013)
        normal = -np.array([get[r * len(WITNESSES) + k][1][:] for r, k in enumerate(worst)])
        bary = WITNESSES[worst]
        scores = np.zeros(outer_count)
        delta = np.zeros_like(shell)
        for i, (face, factors, direction, required) in enumerate(zip(corners, bary, normal, depth)):
            for v, factor in zip(face, factors):
                if pinned[v] or body_zone[v]:
                    continue
                value = float(required * (.25 + factor))
                if value > scores[v]:
                    delta[v] = value * direction
                    scores[v] = value
        avg = np.stack([np.bincount(a, delta[b, k], minlength=outer_count) / degree
                        for k in range(3)], axis=1)
        delta += .40 * avg
        delta[pinned | body_zone] = 0
        delta[shoe.outsole, 2] = np.minimum(0, delta[shoe.outsole, 2])
        delta *= np.minimum(1., .0036 / np.linalg.norm(delta, axis=1).clip(1e-10))[:, None]
        shell += delta
        print("WALL", shoe.foot.sign, iteration, len(contacts),
              float(np.linalg.norm(shell - initial, axis=1).max()), flush=True)


def texture_limit(material):
    for node in material.node_tree.nodes:
        if node.type != "TEX_IMAGE" or node.image is None:
            continue
        img = node.image
        w, h = img.size
        if max(w, h) <= 1024:
            continue
        scale = 1024 / max(w, h)
        img.scale(round(w * scale), round(h * scale))
        img.pack()


def make_mesh(arm, shoes, material):
    positions, faces, uvs, sole = [], [], [], []
    for shoe in shoes:
        shift = len(positions)
        positions.extend(shoe.points.tolist())
        faces.extend(tuple(i + shift for i in face) for face in shoe.faces)
        uvs.extend(shoe.uv)
        sole.extend(shoe.sole_faces)
    mesh = bpy.data.meshes.new("Tripo high-top pair")
    mesh.from_pydata(positions, [], faces, shade_flat=False)
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name="UVMap")
    for polygon, uv_face in zip(mesh.polygons, uvs):
        for loop, st in zip(polygon.loop_indices, uv_face):
            uv.uv[loop].vector = st
    band = mesh.attributes.new("sole_region", "BOOLEAN", "FACE")
    for attr, flag in zip(band.data, sole):
        attr.value = flag
    mesh.update()
    obj = bpy.data.objects.new(NAME, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = arm
    obj.modifiers.new("Master skin", "ARMATURE").object = arm
    start = 0
    for shoe in shoes:
        groups = [obj.vertex_groups.new(name=name) for name in shoe.foot.names]
        for i, weights in enumerate(shoe.weights, start):
            for group, weight in zip(groups, weights):
                if weight > 1e-7:
                    group.add([i], float(weight), "REPLACE")
        start += len(shoe.points)
    return obj


def report_json(name, data, folder=HERE):
    (folder / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select(*objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[-1]


def export_asset(arm, shoes, output=None):
    select(arm, shoes)
    bpy.ops.export_scene.gltf(filepath=str(output or GLB), export_format="GLB", use_selection=True,
                             export_animations=False, export_yup=True, export_def_bones=False,
                             export_armature_object_remove=True, export_all_influences=False,
                             export_tangents=True, export_lights=False, export_cameras=False)


def build(output=HERE):
    output.mkdir(exist_ok=True)
    scene, arm, body = load_master()
    feet = [Foot(body, side) for side in SIDES]
    input_objects = import_objects(SOURCE)
    source, = (obj for obj in input_objects if obj.type == "MESH")
    assert np.allclose(source.matrix_world, np.eye(4))
    mat, = source.data.materials
    bm = weld_source(source)
    shoes = [make_shoe(bm, foot) for foot in feet]
    bm.free()
    for obj in input_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    frames, motion, full = bake_motion(scene, arm, body, feet)
    fit = [fit_motion(shoe, frames, data) for shoe, data in zip(shoes, motion)]
    floor = min(-.014, min(shoe.points[shoe.bed, 2].min() for shoe in shoes) - .00175)
    for shoe in shoes:
        shoe.points = shoe.points.astype(np.float32).astype(float)
        close_bed_holes(shoe)
        separate_wall(shoe, floor)
        # Lower the rear collar for the runner's deepest knee bend. The
        # tongue and collar sides retain their high-top profile.
        y, z = shoe.points[:, 1:].T
        rear = smoothstep(.034, .073, y) * smoothstep(.056, .122, z)
        z -= .037 * rear
        y += .002 * rear
    full_fit = [fit_motion(shoe, frames, (matrices, full), label="full body")
                for shoe, (matrices, _) in zip(shoes, motion)]
    report_json("fit_history.json", {"pose_samples": len(frames), "fit": fit, "full_body_fit": full_fit,
                                    "source_sha256": sha(SOURCE)}, folder=output)
    sizes = []
    angles = np.linspace(0, math.tau, 720, endpoint=False)
    directions = np.stack((np.cos(angles), np.sin(angles)), axis=1)
    for shoe in shoes:
        edge_counts = Counter(tuple(sorted((a, b))) for face in shoe.faces
                              for a, b in zip(face, face[1:] + face[:1]))
        sole_faces = [face for face, flag in zip(shoe.faces[:shoe.source_triangles],
                                                shoe.sole_faces) if flag]
        sole_edges = {tuple(sorted((a, b))) for face in sole_faces
                      for a, b in zip(face, face[1:] + face[:1])}
        sole_ids = np.unique(sole_faces)
        sole_xy = shoe.points[sole_ids, :2]
        outline_overhang = ((sole_xy @ directions.T).max(axis=0) -
                            (shoe.foot.low[:, :2] @ directions.T).max(axis=0))
        distance = np.array([signed(shoe.foot.tree, p)[0] for p in shoe.points])
        upper = ((shoe.points[:, 2] > .03) & (shoe.points[:, 2] < .16) &
                 (np.arange(len(shoe.points)) < max(max(f) for f in
                  shoe.faces[:shoe.source_triangles]) + 1))
        sizes.append({"sign": shoe.foot.sign, "source_faces_retained": shoe.source_triangles,
                      "triangles": len(shoe.faces), "z_min_m": float(shoe.points[:, 2].min()),
                      "z_max_m": float(shoe.points[:, 2].max()),
                      "sole_length_m": float(np.ptp(sole_xy[:, 1])),
                      "body_foot_length_m": float(np.ptp(shoe.foot.low[:, 1])),
                      "sole_outline_min_support_overhang_m": float(outline_overhang.min()),
                      "upper_signed_clearance_m_p05_median_p95":
                          np.percentile(distance[upper], [5, 50, 95]).tolist(),
                      "sole_non_manifold_edges": sum(edge_counts[edge] != 2 for edge in sole_edges),
                      "all_non_manifold_edges": sum(n != 2 for n in edge_counts.values())})
    print("FIT SIZES", sizes, flush=True)
    report_json("fit_dimensions.json", sizes, folder=output)
    assert sum(s["triangles"] for s in sizes) <= 3500
    texture_limit(mat)
    shoes_obj = make_mesh(arm, shoes, mat)
    path = output / f"{NAME}.glb"
    export_asset(arm, shoes_obj, path)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output / f"{NAME}.blend"), compress=True)
    print("BUILD", sha(path), len(frames), flush=True)


def reimport_module():
    scene, arm, body = load_master()
    imported = import_objects(GLB)
    shoes, = (o for o in imported if o.type == "MESH" and o.vertex_groups)
    shoes.parent = None
    for obj in imported:
        if obj != shoes:
            bpy.data.objects.remove(obj, do_unlink=True)
    shoes.modifiers.clear()
    shoes.parent = arm
    shoes.modifiers.new("Master skin", "ARMATURE").object = arm
    load_actions()
    return scene, arm, body, shoes


def dense_check(scene, arm, body, shoes):
    body_faces, shoe_faces = [mesh_triangles(o.data) for o in (body, shoes)]
    per_clip = {}
    for clip, frame in schedule():
        set_pose(scene, arm, clip, frame)
        graph = bpy.context.evaluated_depsgraph_get()
        body_xyz, shoe_xyz = [coords(obj.evaluated_get(graph)).tolist() for obj in (body, shoes)]
        body_tree = BVHTree.FromPolygons(body_xyz, body_faces, all_triangles=True)
        shoe_tree = BVHTree.FromPolygons(shoe_xyz, shoe_faces, all_triangles=True)
        distances = [signed(body_tree, p)[0] for p in shoe_xyz]
        row = per_clip.setdefault(clip, {"samples": 0, "max_vertices_inside": 0,
                                        "max_triangle_pairs": 0, "min_signed_distance_m": 9.,
                                        "minimum_frame": None})
        row["samples"] += 1
        row["max_vertices_inside"] = max(row["max_vertices_inside"], sum(d < 0 for d in distances))
        row["max_triangle_pairs"] = max(row["max_triangle_pairs"], len(body_tree.overlap(shoe_tree)))
        if min(distances) < row["min_signed_distance_m"]:
            row["min_signed_distance_m"] = min(distances)
            row["minimum_frame"] = frame
    report_json("dense_check.json", {"export_sha256": sha(GLB), "clips": per_clip})
    for clip, row in per_clip.items():
        print("DENSE", clip, row, flush=True)
    assert all(row["max_vertices_inside"] == row["max_triangle_pairs"] == 0
               and row["min_signed_distance_m"] >= .0005 for row in per_clip.values())


def verify_editable():
    bpy.ops.wm.open_mainfile(filepath=str(HERE / f"{NAME}.blend"), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    arm, body, shoes = (scene.objects[n] for n in ("Armature", "Base_Body", NAME))
    assert all(bone.rotation_mode == "QUATERNION" for bone in arm.pose.bones)
    assert all(bpy.data.actions[name].slots for name in CLIPS)
    set_pose(scene, arm, "rest", 1)
    xyz = coords(shoes)
    faces = mesh_triangles(shoes.data)
    tag = shoes.data.attributes["sole_region"].data
    assert len(tag) == len(faces)
    boundary = Counter(tuple(sorted((a, b))) for face in faces for a, b in zip(face, face[1:] + face[:1]))
    directions = np.array([(math.cos(i * math.tau / 720), math.sin(i * math.tau / 720))
                           for i in range(720)])
    result = {}
    build_info = json.loads((HERE / "fit_dimensions.json").read_text())
    offset = 0
    for side, counts in zip(SIDES, build_info):
        foot = Foot(body, side)
        sign, name = side
        relevant = xyz[:, 0] * sign > 0
        sole_faces = [f for j, f in enumerate(faces) if tag[j].value and all(relevant[list(f)])]
        sole_verts = xyz[np.unique(sole_faces)]
        sole_edges = {tuple(sorted((a, b))) for f in sole_faces for a, b in zip(f, f[1:] + f[:1])}
        distances = [signed(foot.tree, p)[0] for p in xyz[relevant & (xyz[:, 2] >= .037)]]
        overhang = (sole_verts[:, :2] @ directions.T).max(axis=0) - (foot.low[:, :2] @ directions.T).max(axis=0)
        rest_z = xyz[relevant, 2]
        lining_faces = faces[offset + counts["source_faces_retained"]:offset + counts["triangles"]]
        offset += counts["triangles"]
        lining_points = xyz[np.unique(lining_faces)]
        liner_distances = [signed(foot.tree, p)[0] for p in lining_points if p[2] > .026]
        sole_tree = BVHTree.FromPolygons(xyz.tolist(), sole_faces, all_triangles=True)
        border = foot.outline
        edge_starts = np.roll(border, 1, axis=0)
        edges = border - edge_starts
        oriented = np.sign(cross2(edge_starts - foot.center, edges).mean())
        normals = oriented * unit(edges[:, ::-1] * (1, -1))
        near_edge = [(a + t * v + .003 * n).tolist()
                     for a, v, n in zip(edge_starts, edges, normals)
                     for t in np.linspace(0, 1, max(2, math.ceil(np.linalg.norm(v) / .001)))]
        outer_corners = border[(border @ directions.T).argmax(axis=0)] + .003 * directions
        rays = near_edge + outer_corners.tolist()
        missed = sum(sole_tree.ray_cast((x, y, -.095), (0, 0, 1), .160)[0] is None
                     for x, y in rays)
        result[name] = {"minimum_z_m": float(rest_z.min()), "highest_shaft_z_m": float(rest_z.max()),
                        "sole_length_m": float(np.ptp(sole_verts[:, 1])),
                        "foot_length_m": float(np.ptp(foot.low[:, 1])),
                        "sole_convex_projected_support_m": float(overhang.min()),
                        "upper_clearance_quantiles_m": np.percentile(distances, [5, 50, 95]).tolist(),
                        "lining_clearance_quantiles_m": np.percentile(liner_distances, [5, 50, 95]).tolist(),
                        "projected_3mm_sole_coverage_rays": len(rays),
                        "projected_3mm_sole_coverage_misses": missed,
                        "sole_edges_not_two_incident_faces": sum(boundary[e] != 2 for e in sole_edges),
                        "shoe_edges_not_two_incident_faces": sum(
                            n != 2 for edge, n in boundary.items() if relevant[edge[0]]),
                        "vertices_within_1mm_of_lowest": int((rest_z < rest_z.min() + .001).sum())}
        for v in shoes.data.vertices:
            if relevant[v.index]:
                assert all(shoes.vertex_groups[g.group].name in foot.names
                           for g in v.groups if g.weight > 0)
    report_json("sole_geometry_check.json", {"export_sha256": sha(GLB), "shoes": result,
                                           "blend_sha256": sha(HERE / f"{NAME}.blend")})
    print("SOLE", result, flush=True)


def run_checkers():
    from contextlib import redirect_stdout
    from tempfile import TemporaryDirectory

    workbench = ("sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
                 "sc.display.shading.color_type='MATERIAL'")
    cpu = """
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 6
sc.cycles.use_denoising = True
sc.render.resolution_percentage = 100
sc.render.use_compositing = False
sc.render.use_sequencer = False
sc.world = bpy.data.worlds.new('Checker studio')
sc.world.use_nodes = True
bg = sc.world.node_tree.nodes['Background']
bg.inputs[0].default_value = (.82, .85, .91, 1)
bg.inputs[1].default_value = .65
"""
    original = sys.argv
    passing = True
    try:
        for name in ("motion_check", "motion_check_tri"):
            path = HERE / "work" / f"{name}.py"
            source = path.read_text()
            assert source.count(workbench) == 1
            source = source.replace(workbench, cpu, 1)
            if "--checker-renders" not in original or name == "motion_check_tri":
                source = source.replace("bpy.ops.render.render(write_still=True)", "None")
            with TemporaryDirectory(prefix=".checker-", dir=HERE) as out:
                sys.argv = [str(path), "--", str(MASTER), str(MOTION), str(GLB), out]
                import io

                log = io.StringIO()
                with redirect_stdout(log):
                    exec(compile(source, str(path), "exec"), {"__name__": "__main__"})
                result = "\n".join(line for line in log.getvalue().splitlines() if line.startswith("RESULT "))
                rows = [line.split() for line in result.splitlines()]
                assert len(rows) == 8
                passing &= all(int(row[3]) == 0 and float(row[5]) >= .0005 for row in rows)
                (HERE / f"{name}.txt").write_text(result + "\n")
                out = Path(out)
                (out / "motion_check.json").replace(HERE / f"{name}.json")
                if name == "motion_check":
                    folder = HERE / "png"
                    folder.mkdir(exist_ok=True)
                    for image in out.glob("*.png"):
                        image.replace(folder / image.name)
                print(result, flush=True)
    finally:
        sys.argv = original
    assert passing, "A supplied motion gate failed"


def skin_bind_data(path):
    data = path.read_bytes()
    json_size, = struct.unpack_from("<I", data, 12)
    gltf = json.loads(data[20:20 + json_size])
    skin, = gltf["skins"]
    names = [gltf["nodes"][i]["name"] for i in skin["joints"]]
    accessor = gltf["accessors"][skin["inverseBindMatrices"]]
    view = gltf["bufferViews"][accessor["bufferView"]]
    start = 28 + json_size + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return names, data[start:start + 64 * len(names)]


def inspect_export():
    data = GLB.read_bytes()
    magic, version, size, json_size = struct.unpack_from("<4sIII", data)
    assert (magic, version, size) == (b"glTF", 2, len(data))
    gltf = json.loads(data[20:20 + json_size])
    blob = data[28 + json_size:]
    skin, = gltf["skins"]
    joint_names = [gltf["nodes"][i]["name"] for i in skin["joints"]]
    assert len(joint_names) == 65 and not gltf.get("animations")
    mesh, = gltf["meshes"]
    triangles = vertices = maximum = 0
    for primitive in mesh["primitives"]:
        attrs = primitive["attributes"]
        assert "TEXCOORD_0" in attrs and "WEIGHTS_1" not in attrs and "JOINTS_1" not in attrs
        triangles += gltf["accessors"][primitive["indices"]]["count"] // 3
        weights = gltf["accessors"][attrs["WEIGHTS_0"]]
        view = gltf["bufferViews"][weights["bufferView"]]
        start = view.get("byteOffset", 0) + weights.get("byteOffset", 0)
        stride = view.get("byteStride", 16)
        vertices += weights["count"]
        for i in range(weights["count"]):
            values = struct.unpack_from("<4f", blob, start + stride * i)
            assert min(values) >= 0 and abs(sum(values) - 1) < 1e-5
            maximum = max(maximum, sum(v > 0 for v in values))
    assert triangles <= 3500 and maximum <= 4
    result = {"export_sha256": sha(GLB), "triangles": triangles, "exported_vertices": vertices,
              "joint_names": joint_names, "max_influences": maximum, "mesh_count": 1,
              "clip_count": 0, "glb_bytes": len(data),
              "blend_bytes": (HERE / f"{NAME}.blend").stat().st_size}
    # Ask Blender to decode the embedded images; packed source dimensions are
    # not a reliable proxy for the dimensions actually in the GLB.
    old_images = set(bpy.data.images)
    imported = import_objects(GLB)
    images = {img.name: list(img.size) for img in set(bpy.data.images) - old_images}
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    result["images"] = dict(sorted(images.items()))
    prior = HERE.parents[1] / "shoes-sol" / "round3" / "shoes_sneaker_v3.glb"
    old_names, old_bind = skin_bind_data(prior)
    new_names, new_bind = skin_bind_data(GLB)
    result["joint_order_matches_sneaker_round3"] = new_names == old_names
    result["inverse_bind_bytes_match_sneaker_round3"] = new_bind == old_bind
    report_json("asset_contract.json", result)
    assert set(old_names) == set(new_names)
    assert len(images) == 3 and all(max(size) <= 1024 for size in images.values()), images
    print("CONTRACT", {k: v for k, v in result.items() if k != "joint_names"}, flush=True)


def camera_at(scene, position, target, scale):
    camera = scene.camera
    if camera is None:
        data = bpy.data.cameras.new("QA camera")
        camera = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(camera)
        scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    camera.location = position
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    return camera


def init_render(scene, width, height, samples):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.seed = 17
    scene.cycles.use_adaptive_sampling = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(HERE / "png")
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("QA studio")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (.79, .82, .89, 1)
    bg.inputs[1].default_value = .57


def photo(scene, name):
    folder = HERE / "png"
    folder.mkdir(exist_ok=True)
    path = folder / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def add_lights(scene, center):
    lights = []
    for name, location, energy, size in (
            ("Key", (-.24, -.4, .43), 4.5, .37),
            ("Fill", (.30, -.2, .19), 1.5, .35),
            ("Rim", (.10, .35, .36), 4.0, .24)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (Vector(center) - obj.location).to_track_quat("-Z", "Y").to_euler()
        lights.append(obj)
    return lights


def emission(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    shader = nodes.new("ShaderNodeEmission")
    shader.inputs["Color"].default_value = rgba
    output = nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(shader.outputs[0], output.inputs["Surface"])
    return mat


def skin_mask_material(body):
    points = coords(body)
    for name, values in (("rest_height", points[:, 2]), ("rest_side", points[:, 0])):
        attribute = body.data.attributes.new(name, "FLOAT", "POINT")
        attribute.data.foreach_set("value", values.astype(np.float32))
    mat = emission("Body ID", (0, 1, 0, 1))
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    height = nodes.new("ShaderNodeAttribute")
    height.attribute_name = "rest_height"
    below = nodes.new("ShaderNodeMath")
    below.operation = "LESS_THAN"
    below.inputs[1].default_value = .041
    links.new(height.outputs["Fac"], below.inputs[0])
    side = nodes.new("ShaderNodeAttribute")
    side.attribute_name = "rest_side"
    signed_x = nodes.new("ShaderNodeMath")
    signed_x.operation = "MULTIPLY"
    links.new(side.outputs["Fac"], signed_x.inputs[0])
    selected = nodes.new("ShaderNodeMath")
    selected.operation = "GREATER_THAN"
    selected.inputs[1].default_value = 0.
    links.new(signed_x.outputs[0], selected.inputs[0])
    combine = nodes.new("ShaderNodeMath")
    combine.operation = "MULTIPLY"
    links.new(below.outputs[0], combine.inputs[0])
    links.new(selected.outputs[0], combine.inputs[1])
    color = nodes.new("ShaderNodeMixRGB")
    # Green identifies the anatomically defined sole band. Red represents
    # visible shin and the opposite leg, so neither can register as a leak.
    color.inputs[1].default_value = (.8, 0, 0, 1)
    color.inputs[2].default_value = (0, 1, 0, 1)
    links.new(combine.outputs[0], color.inputs[0])
    links.new(color.outputs[0], nodes.get("Emission").inputs["Color"])
    return mat, signed_x.inputs[1]


def count_green(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    rgba = np.empty(len(img.pixels), dtype=np.float32)
    img.pixels.foreach_get(rgba)
    bpy.data.images.remove(img)
    rgba = rgba.reshape(-1, 4)
    return int(np.count_nonzero(rgba[:, 1] > .035))


def foot_camera(scene, arm, shoe_rest, shoe_posed, sign, view):
    name = "Left" if sign > 0 else "Right"
    bone = arm.pose.bones[f"mixamorig:{name}Foot"]
    rotation = (bone.matrix @ bone.bone.matrix_local.inverted()).to_quaternion()
    filt = (sign * shoe_rest[:, 0] > 0) & (shoe_rest[:, 2] < .039)
    target = Vector((shoe_posed[filt].min(axis=0) + shoe_posed[filt].max(axis=0)) / 2)
    local = {"underside": (.045 * sign, -.13, -1), "side": (sign, -.09, -.12),
             "inner_side": (-sign, -.13, -.17), "toe": (.55 * sign, -1, .45)}[view]
    direction = rotation @ Vector(local)
    return camera_at(scene, target + direction.normalized() * .72, target, .326)


def lift_cases(scene, arm, body):
    rest = coords(body)
    in_foot = [(s * rest[:, 0] > 0) & (rest[:, 2] < .041) for s, _ in SIDES]
    examples = {("walk", 19, 1), ("walk", 23, 1), ("run", 4, -1), ("run", 12, -1)}
    choices = {}
    for clip in ("walk", "run"):
        start, end = bpy.data.actions[clip].frame_range
        for frame in range(math.ceil(start), math.floor(end) + 1):
            set_pose(scene, arm, clip, frame)
            xyz = coords(body.evaluated_get(bpy.context.evaluated_depsgraph_get()))
            for (sign, _), filt in zip(SIDES, in_foot):
                lift = float(xyz[filt, 2].min())
                best = choices.get((clip, sign), (frame, -9.))
                if lift > best[1]:
                    choices[(clip, sign)] = (frame, lift)
                if (clip, frame, sign) in examples:
                    yield clip, frame, sign, lift
    for (clip, sign), (frame, lift) in choices.items():
        if (clip, frame, sign) not in examples:
            yield clip, frame, sign, lift


def render_qa(scene, arm, body, shoes, fast=False):
    set_pose(scene, arm, "rest", 1)
    shoe_rest = coords(shoes)
    init_render(scene, 660, 510, 18)
    scene.cycles.use_denoising = True
    target = Vector((0.001, -.021, .058))
    lights = add_lights(scene, target)
    stills = {}
    if not fast:
        body.hide_render = True
        camera_at(scene, (.46, -.72, .42), target, .383)
        stills["shoes_preview.png"] = sha(photo(scene, "shoes_preview"))
        camera_at(scene, (-.6, -.25, .29), target, .373)
        stills["shoes_opposite.png"] = sha(photo(scene, "shoes_opposite"))
        body.hide_render = False
        camera_at(scene, (.45, -.75, .32), Vector((0, -.016, .114)), .41)
        stills["fitted_rest.png"] = sha(photo(scene, "fitted_rest"))
    for light in lights:
        light.hide_render = True
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0
    scene.view_settings.view_transform = "Standard"
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 0
    scene.cycles.samples = 5 if not fast else 2
    scene.render.resolution_x, scene.render.resolution_y = (464, 360) if not fast else (300, 230)
    blue = emission("Shoe ID", (0, 0, 1, 1))
    flat_green = emission("Body flat green", (0, 1, 0, 1))
    masks, chosen_side = skin_mask_material(body)
    for i in range(len(shoes.data.materials)):
        shoes.data.materials[i] = blue
    reports = {}
    for clip, frame, sign, lift in lift_cases(scene, arm, body):
        set_pose(scene, arm, clip, frame)
        posed = coords(shoes.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        chosen_side.default_value = sign
        for view in ("underside", "side", "inner_side"):
            camera = foot_camera(scene, arm, shoe_rest, posed, sign, view)
            side = "left" if sign > 0 else "right"
            name = f"{clip}_{frame:02d}_{side}_{view}"
            for i in range(len(body.data.materials)):
                body.data.materials[i] = masks
            gate = photo(scene, f"{name}_sole_mask")
            if not fast:
                for i in range(len(body.data.materials)):
                    body.data.materials[i] = flat_green
                flat = photo(scene, f"{name}_flat_skin")
            else:
                flat = None
            # Render a body-only positive control for the same camera and
            # triangle band so a zero cannot come from a bad mask or crop.
            for i in range(len(body.data.materials)):
                body.data.materials[i] = masks
            shoes.hide_render = True
            control = photo(scene, "_foot_control")
            count = count_green(gate)
            unoccluded = count_green(control)
            control.unlink()
            shoes.hide_render = False
            assert unoccluded > 0, name
            record = {"clip": clip, "frame": frame, "side": side, "view": view,
                      "body_foot_min_world_z_m": lift, "skin_pixels": count,
                      "body_only_control_pixels": unoccluded,
                      "camera": list(camera.location), "camera_rotation": list(camera.rotation_euler),
                      "mask_sha256": sha(gate)}
            if flat:
                record["flat_body_png_sha256"] = sha(flat)
            reports[name] = record
            print("SKIN", name, count, "control", unoccluded, "lift", round(lift, 5), flush=True)
    total = sum(view["skin_pixels"] for view in reports.values())
    report_json("skin_check.json", {"export_sha256": sha(GLB), "total_skin_pixels": total,
                                   "roi": "Visible selected-side body below rest Z 0.041 m, including outside shoe silhouette",
                                   "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                                   "rest_png_sha256": stills, "views": reports})
    print("SKIN TOTAL", total, flush=True)
    assert total == 0, "Visible skin in the sole region"


def sweep_sole_visibility(scene, arm, body, shoes):
    """Trace orthographic samples at all lifted integer gait frames."""
    set_pose(scene, arm, "rest", 1)
    body_rest, shoe_rest = [coords(obj) for obj in (body, shoes)]
    body_faces = np.array(mesh_triangles(body.data))
    shoe_faces = mesh_triangles(shoes.data)
    baseline = {s: (s * body_rest[:, 0] > 0) & (body_rest[:, 2] < .041) for s, _ in SIDES}
    width, height = 112, 86
    pixels = np.array([(i + .5 - width / 2, j + .5 - height / 2)
                       for j in range(height) for i in range(width)])
    body_indices = body_faces.tolist()
    face_skin = body_rest[body_faces, 2].min(axis=1) < .041
    face_side = np.sign(body_rest[body_faces, 0].mean(axis=1))
    views = []
    for clip in ("walk", "run"):
        first, last = bpy.data.actions[clip].frame_range
        for frame in range(math.ceil(first), math.floor(last) + 1):
            set_pose(scene, arm, clip, frame)
            graph = bpy.context.evaluated_depsgraph_get()
            skin, gear = [coords(obj.evaluated_get(graph)) for obj in (body, shoes)]
            lifted = [(s, float(skin[baseline[s], 2].min())) for s, _ in SIDES]
            lifted = [(s, z) for s, z in lifted if z >= .010]
            if not lifted:
                continue
            body_tree = BVHTree.FromPolygons(skin.tolist(), body_indices, all_triangles=True)
            shoe_tree = BVHTree.FromPolygons(gear.tolist(), shoe_faces, all_triangles=True)
            for sign, lift in lifted:
                for view in ("underside", "side", "inner_side"):
                    camera = foot_camera(scene, arm, shoe_rest, gear, sign, view)
                    rotation = camera.rotation_euler.to_quaternion()
                    axes = np.array([rotation @ Vector((1, 0, 0)),
                                     rotation @ Vector((0, 1, 0))])
                    direction = rotation @ Vector((0, 0, -1))
                    starts = np.array(camera.location) + pixels @ axes * (camera.data.ortho_scale / width)
                    exposed = control = 0
                    for origin in starts.tolist():
                        point, _, face, body_dist = body_tree.ray_cast(origin, direction)
                        if point is None or not face_skin[face] or face_side[face] != sign:
                            continue
                        corners = body_faces[face]
                        z = barycentric(point, skin[corners]) @ body_rest[corners, 2]
                        if z >= .041:
                            continue
                        control += 1
                        block, _, _, _ = shoe_tree.ray_cast(origin, direction, body_dist)
                        exposed += block is None
                    assert control > 0
                    views.append({"clip": clip, "frame": frame, "sign": sign, "view": view,
                                  "lift_m": lift, "skin_pixels": exposed, "control_pixels": control})
    result = {"export_sha256": sha(GLB), "lift_threshold_m": .010,
              "raster_size": (width, height), "tested_views": len(views),
              "skin_pixels": sum(row["skin_pixels"] for row in views), "views": views}
    report_json("visibility_sweep.json", result)
    print("VISIBILITY", {k: v for k, v in result.items() if k != "views"}, flush=True)
    assert result["skin_pixels"] == 0, "Visible skin in the gait sweep"


def main():
    options = set(sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else set()
    if not options or "--build" in options:
        build()
    if "--rebuild-check" in options:
        build(HERE / "work" / "repro")
    if "--export" in options:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / f"{NAME}.blend"), load_ui=False, use_scripts=False)
        scene = bpy.context.scene
        export_asset(scene.objects["Armature"], scene.objects[NAME])
    if "--checkers" in options:
        run_checkers()
    if "--inspect-blend" in options:
        verify_editable()
    if "--verify" in options:
        inspect_export()
        dense_check(*reimport_module())
    if "--visibility" in options:
        sweep_sole_visibility(*reimport_module())
    if "--renders" in options or "--skin-fast" in options:
        render_qa(*reimport_module(), fast="--skin-fast" in options)


if __name__ == "__main__":
    main()
