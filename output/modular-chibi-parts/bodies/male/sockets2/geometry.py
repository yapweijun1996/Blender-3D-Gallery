"""Load the demo geometry and evaluate the unmodified male action bank."""
import json
import math
import os
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
MALE = HERE.parent
PARTS = MALE.parents[1]
ASTRA = PARTS / 'actions-astra'
HOLD = PARTS / 'actions-hold2'
BODY = MALE / 'body_male.glb'
MOTION = MALE / 'round2/motion_male_fixed.glb'
C = Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
N = 'mixamorig:'
SIDES = ('Right', 'Left')
DIGITS = ('Thumb', 'Index')
CARRY = ('hold_item', 'hold_box', 'hold_bag', 'take_item')
CHAIR = ('sit_down', 'sit_idle', 'stand_up')
PROPS = {
    'hold_item': (ASTRA / 'prop.glb', 'Tasting cup'),
    'hold_box': (HOLD / 'props/box.glb', 'Parcel'),
    'hold_bag': (HOLD / 'props/bag.glb', 'Market bag'),
    'take_item': (HOLD / 'props/shelf_item.glb', 'Jam jar'),
    'sit_idle': (ASTRA / 'chair.glb', 'Chair'),
}
SOURCE_FPS = {name: 30 if name in CHAIR or name == 'hold_item' else 24 for name in (*CARRY, *CHAIR)}

sys.path[:0] = [str(MALE), str(PARTS / 'hand-gestures-astra/round2')]
from asset_io import GLB, import_objects
from hand_surface import nearest as surface_nearest


def transform(points, matrix):
    a = np.asarray(matrix, dtype=float)
    return points @ a[:3, :3].T + a[:3, 3]


def tree(points, faces):
    return BVHTree.FromPolygons(points.tolist(), faces, all_triangles=True)


def compose(translation=(0,0,0), rotation=(0,0,0,1), scale=(1,1,1)):
    return Matrix.LocRotScale(Vector(translation), Quaternion((rotation[3], *rotation[:3])), Vector(scale))


def record(matrix):
    translation, rotation, _ = matrix.decompose()
    if rotation.w < 0:
        rotation.negate()
    return {'translation': list(translation), 'rotation': [rotation.x, rotation.y, rotation.z, rotation.w]}


def read_pose(config):
    return compose(config['translation'], config['rotation'], config.get('scale', (1,1,1)))


def vertices(obj, posed=False):
    if posed:
        obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = np.empty(len(obj.data.vertices)*3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', points)
    return points.reshape(-1, 3).astype(float)


def faces(obj):
    obj.data.calc_loop_triangles()
    return [tuple(t.vertices) for t in obj.data.loop_triangles]


def track_bank(asset, name):
    anim = next(a for a in asset.doc['animations'] if a['name'] == name)
    tracks = {}
    for channel in anim['channels']:
        sampler = anim['samplers'][channel['sampler']]
        assert sampler.get('interpolation', 'LINEAR') == 'LINEAR'
        target = channel['target']
        tracks[target['node'], target['path']] = (
            asset.accessor(sampler['input']).ravel(), asset.accessor(sampler['output']))
    return tracks


def sample_track(track, time, rotation):
    ts, vs = track
    end = int(np.searchsorted(ts, time, side='right'))
    if end == 0 or end == len(ts):
        return vs[max(0, end-1)]
    start = end - 1
    alpha = (time-ts[start])/(ts[end]-ts[start])
    if rotation:
        q = Quaternion((vs[start,3], *vs[start,:3])).slerp(Quaternion((vs[end,3], *vs[end,:3])), alpha)
        return (q.x, q.y, q.z, q.w)
    return vs[start]*(1-alpha) + vs[end]*alpha


def gltf_world(asset, joint, tracks=None, time=0):
    tracks = tracks or {}
    index = asset.ids[N+joint]
    world = Matrix.Identity(4)
    while True:
        node = asset.nodes[index]
        parts = []
        for key, default in [('translation', (0,0,0)), ('rotation', (0,0,0,1)), ('scale', (1,1,1))]:
            track = tracks.get((index, key))
            parts.append(sample_track(track, time, key == 'rotation') if track else node.get(key, default))
        world = compose(*parts) @ world
        if index not in asset.parents:
            return world
        index = asset.parents[index]


class Prop:
    def __init__(self, obj):
        self.obj = obj
        self.points = vertices(obj)
        self.faces = faces(obj)
        self.tree = tree(self.points, self.faces)


class Replay:
    def __init__(self, body_path=BODY, motion_path=MOTION):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.render.fps = 120
        self.scene.render.threads_mode = 'FIXED'
        self.scene.render.threads = int(os.environ.get('SOCKET_THREADS', '2'))
        args = dict(bone_heuristic='BLENDER', import_pack_images=True)
        body_objects = import_objects(body_path, **args)
        self.body, = [obj for obj in body_objects if obj.name == 'Base_Body']
        self.arm, = [obj for obj in body_objects if obj.type == 'ARMATURE']
        before = set(bpy.data.actions)
        objects = import_objects(motion_path, **args)
        self.actions = {act.name: act for act in set(bpy.data.actions) - before}
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        self.data = self.arm.animation_data_create()
        self.data.use_nla = False
        self.motion = GLB(motion_path)
        self.rest = vertices(self.body)
        self.body_faces = faces(self.body)
        self.weights = self.get_weights()
        self.labels = np.array(list(self.weights))[np.stack(list(self.weights.values())).argmax(axis=0)]
        self.pads = self.get_pads()
        self.feet = {}
        for side in SIDES:
            mask = np.isin(self.labels, [side+'Foot', side+'ToeBase', side+'Toe_End'])
            ymin, ymax = self.rest[mask,1].min(), self.rest[mask,1].max()
            self.feet[side] = {
                'heel': np.flatnonzero(mask & (self.rest[:,1]>ymax-(ymax-ymin)*.35)),
                'forefoot': np.flatnonzero(mask & (self.rest[:,1]<ymin+(ymax-ymin)*.35)),
            }

    def get_weights(self):
        weights = {g.name.removeprefix(N): np.zeros(len(self.rest)) for g in self.body.vertex_groups}
        keys = list(weights)
        for v in self.body.data.vertices:
            for g in v.groups:
                weights[keys[g.group]][v.index] = g.weight
        return weights

    def get_pads(self):
        # Fixed distal skin patches. Recover the volar direction from palm
        # geometry so Blender's imported bone roll cannot flip the pad.
        result = {}
        for side in SIDES:
            hand = self.arm.data.bones[N+side+'Hand']
            knuckles = np.array([self.arm.data.bones[N+side+'Hand'+d+'1'].head_local
                                 for d in ('Index','Middle','Ring','Pinky')])
            along = knuckles.mean(0)-np.array(hand.head_local)
            across = knuckles[-1]-knuckles[0]
            palm_normal = np.cross(along, across)
            palm_normal /= np.linalg.norm(palm_normal)
            if palm_normal[2] > 0:
                palm_normal *= -1
            for digit in DIGITS:
                prefix = side+'Hand'+digit
                # The terminal joint is an end marker on this rig.
                tip_bone = self.arm.data.bones[N+prefix+('3' if digit == 'Thumb' else '4')]
                base = self.arm.data.bones[N+prefix+('2' if digit == 'Thumb' else '3')]
                distal = np.array(tip_bone.head_local-base.head_local)
                distal /= np.linalg.norm(distal)
                total = sum(w for name,w in self.weights.items() if name.startswith(prefix))
                normal = distal + .65*palm_normal
                normal /= np.linalg.norm(normal)
                tri = np.asarray(self.body_faces)
                region = tri[(total[tri].mean(1)>.48) &
                             (np.linalg.norm(self.rest[tri]-np.array(tip_bone.head_local), axis=2).max(1)<.021)]
                xyz = self.rest[region]
                support = xyz @ normal
                normals = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
                normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-20)
                patch = region[(support.min(1)>=support.max()-.0032) & (normals@normal>.25)]
                if not len(patch):
                    raise ValueError(f'No distal pad triangles for {side} {digit}')
                result[side,digit] = [tuple(f) for f in patch]
        return result

    def select(self, name):
        self.clip = name
        self.tracks = track_bank(self.motion, name)
        self.end_time = round(max(float(ts[-1]) for ts, _ in self.tracks.values()), 6)
        self.data.action = None
        for bone in self.arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        act = self.actions[name]
        self.data.action = act
        self.data.action_slot = act.slots[0]

    def time(self, time):
        frames = time*self.scene.render.fps
        self.scene.frame_set(math.floor(frames), subframe=frames%1)
        points = transform(vertices(self.body, posed=True), self.body.matrix_world)
        hand = C @ gltf_world(self.motion, 'RightHand', self.tracks, time) @ C.inverted()
        return points, hand

    def times(self):
        # Source authoring grid, the demo clock and the keys in the baked bank.
        rates = {SOURCE_FPS[self.clip], 24, 96}
        return sorted({round(n/(2*fps), 9) for fps in rates
                       for n in range(math.floor(self.end_time*2*fps+1e-6)+1)}
                      | {0., self.end_time})

    def prop(self, name):
        path, node = PROPS[name]
        objects = import_objects(path)
        prop, = [o for o in objects if o.name == node]
        other = [Prop(o) for o in objects if o.type == 'MESH' and o != prop]
        return Prop(prop), other

    def seat_mask(self, side, points):
        pelvis = np.isin(self.labels, ('Hips', side+'UpLeg'))
        hip = self.arm.matrix_world @ self.arm.pose.bones[N+'Hips'].head
        sign = 1 if side == 'Left' else -1
        return pelvis & (sign*points[:,0] > .008) & (np.abs(points[:,1]-hip.y)<.07)


def closed_components(points, triangles):
    """Connect triangles across exported vertex seams, without welding the replay."""
    _, weld = np.unique(points.round(6), axis=0, return_inverse=True)
    adjacency = [[] for _ in range(int(weld.max())+1)]
    for i, face in enumerate(triangles):
        for j in weld[list(face)]:
            adjacency[j].append(i)
    seen = set()
    for root in range(len(triangles)):
        if root in seen:
            continue
        pending, part, touched = [root], [], set()
        seen.add(root)
        while pending:
            i = pending.pop()
            part.append(triangles[i])
            for j in weld[list(triangles[i])]:
                if j in touched:
                    continue
                touched.add(j)
                for k in adjacency[j]:
                    if k not in seen:
                        seen.add(k)
                        pending.append(k)
        yield part


def prop_parts(points, components):
    result = []
    point_list = points.tolist()
    for triangles in components:
        patch = points[np.unique(triangles)]
        result.append((patch.min(0), patch.max(0), BVHTree.FromPolygons(point_list, triangles, all_triangles=True)))
    return result


RAYS = [Vector(axis).normalized() for axis in ((.735,.339,.587),(-.319,.871,.373),(.271,-.445,.853))]
EPSILON_M = .0000002


def inside(point, bvh):
    # An interior ray exits through an outward-facing triangle. Voting
    # avoids ambiguous hits on triangle seams or tangencies.
    votes = 0
    for direction in RAYS:
        _, normal, _, _ = bvh.ray_cast(point, direction)
        votes += normal is not None and normal.dot(direction) > 0
    return votes >= 2


def inside_depth(points, parts):
    depth = {}
    for lo, hi, surface in parts:
        for i in np.flatnonzero(((points >= lo) & (points <= hi)).all(1)):
            point = points[i]
            hit, normal, _, d = surface.find_nearest(point)
            if d > EPSILON_M and inside(point, surface):
                depth[i] = max(depth.get(i, 0), d)
    return depth


def bounds(prop, transform_matrix):
    return transform(prop.points, transform_matrix)


def nearest_witness_mm(body_points, pad_faces, prop_points, prop_faces):
    # Reindex input so the triangle query operates only on the chosen patch.
    ids, reindex = np.unique(pad_faces, return_inverse=True)
    fs = [tuple(row) for row in reindex.reshape(-1,3)]
    other = [tuple(i+len(ids) for i in face) for face in prop_faces]
    return surface_nearest(np.vstack((body_points[ids], prop_points)), fs, other)['distance_mm']


def bpy_pose(gl_pose):
    return C @ read_pose(gl_pose) @ C.inverted()


def json_pose(blender_pose):
    return record(C.inverted() @ blender_pose @ C)
