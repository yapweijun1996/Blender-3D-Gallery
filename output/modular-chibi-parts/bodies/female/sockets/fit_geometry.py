"""Geometry and playback shared by the socket fit and its verification."""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FEMALE = HERE.parent
PARTS = FEMALE.parents[1]
sys.path.insert(0, str(FEMALE))
from common import bind, load_glb
from glb_io import Glb

ASTRA = PARTS / 'actions-astra'
HOLD = PARTS / 'actions-hold2'
N = 'mixamorig:'
G = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
B = G.transposed()
PROPS = {
    'hold_item': (ASTRA / 'prop.glb', 'Tasting cup', ASTRA / 'attachment.json', 30, 60),
    'hold_box': (HOLD / 'props/box.glb', 'Parcel', HOLD / 'props/box.attachment.json', 24, 48),
    'hold_bag': (HOLD / 'props/bag.glb', 'Market bag', HOLD / 'props/bag.attachment.json', 24, 48),
    'take_item': (HOLD / 'props/shelf_item.glb', 'Jam jar', HOLD / 'props/shelf_item.attachment.json', 24, 48),
}
CHAIR = {'sit_down': 36, 'sit_idle': 90, 'stand_up': 30}
PICK = 29 / 24

def quat(xyzw):
    x, y, z, w = xyzw
    return Quaternion((w, x, y, z)).normalized()

def trs(row):
    return Matrix.LocRotScale(Vector(row.get('translation_m', (0, 0, 0))),
                              quat(row.get('quaternion_xyzw', (0, 0, 0, 1))),
                              Vector(row.get('scale_xyz', (1, 1, 1))))

def record(matrix, scale=False):
    t, q, s = matrix.decompose()
    r = dict(translation_m=list(t), quaternion_xyzw=[q.x, q.y, q.z, q.w])
    if scale:
        r['scale_xyz'] = list(s)
    return r

def transform(points, matrix):
    m = np.asarray(matrix, dtype=float)
    return points @ m[:3, :3].T + m[:3, 3]

def faces(obj):
    obj.data.calc_loop_triangles()
    return [tuple(tri.vertices) for tri in obj.data.loop_triangles]

def points(obj, evaluated=False, world=False):
    if evaluated:
        obj = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    coords = np.zeros(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', coords)
    v = coords.reshape(-1, 3).astype(float)
    return transform(v, obj.matrix_world) if world else v

def tree(v, f):
    return BVHTree.FromPolygons(v.tolist(), f, all_triangles=True)

def dominant(obj):
    return np.array([obj.vertex_groups[max(v.groups, key=lambda g: g.weight).group].name
                      if len(v.groups) else "" for v in obj.data.vertices])

def time_grid(fps, end):
    # Both the source clip's frame clock and the 30 fps female bake clock.
    from fractions import Fraction
    return [float(t) for t in sorted({Fraction(i, 2 * fps) for i in range(2 * end + 1)} |
                                   {Fraction(i, 60) for i in range(60 * end // fps + 1)})]

class Motion:
    def __init__(self, path):
        asset = Glb(path)
        self.nodes = asset.doc['nodes']
        self.parents = {child: i for i, n in enumerate(self.nodes) for child in n.get('children', [])}
        self.names = {n['name']: i for i, n in enumerate(self.nodes)}
        self.tracks = {}
        for clip in asset.doc['animations']:
            tracks = self.tracks[clip['name']] = {}
            for channel in clip['channels']:
                sampler = clip['samplers'][channel['sampler']]
                assert sampler.get('interpolation', 'LINEAR') == 'LINEAR'
                key = channel['target']
                times = asset.accessor(sampler['input']).ravel().astype(float)
                tracks.setdefault(key['node'], {})[key['path']] = (times, asset.accessor(sampler['output']))

    def world(self, name, clip=None, seconds=0):
        chain = []
        i = self.names[name]
        while i is not None:
            chain.append(i)
            i = self.parents.get(i)
        world = Matrix.Identity(4)
        for i in reversed(chain):
            node = self.nodes[i]
            t = node.get('translation', (0, 0, 0))
            q = quat(node.get('rotation', (0, 0, 0, 1)))
            s = node.get('scale', (1, 1, 1))
            if clip is not None:
                for path, (keys, values) in self.tracks[clip].get(i, {}).items():
                    hi = min(len(keys) - 1, int(np.searchsorted(keys, seconds)))
                    lo = max(0, hi - 1)
                    u = min(1., max(0., (seconds - keys[lo]) / (keys[hi] - keys[lo]))) if lo != hi else 0.
                    if path == 'rotation':
                        q = quat(values[lo]).slerp(quat(values[hi]), u)
                    elif path == 'translation':
                        t = values[lo] + u * (values[hi] - values[lo])
                    elif path == 'scale':
                        s = values[lo] + u * (values[hi] - values[lo])
                    else:
                        raise ValueError(path)
            world = world @ Matrix.LocRotScale(Vector(t), q, Vector(s))
        return world

class Stage:
    def __init__(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.render.fps = 60
        self.scene.render.threads_mode = 'FIXED'
        self.scene.render.threads = 2
        objects = load_glb(FEMALE / 'body_female.glb')
        self.arm = next(o for o in objects if o.type == 'ARMATURE')
        self.body = self.scene.objects['Base_Body']
        self.rest = points(self.body, world=True)
        self.faces = faces(self.body)
        self.labels = dominant(self.body)
        self.motion = Motion(FEMALE / 'motion_female.glb')
        self.actions = {}
        bank = load_glb(FEMALE / 'motion_female.glb')
        for name in (*PROPS, *CHAIR):
            self.actions[name] = bpy.data.actions[name]
        for obj in bank:
            bpy.data.objects.remove(obj, do_unlink=True)
        self.name = None

    def frame(self, clip, seconds):
        if self.name != clip:
            bind(self.arm, self.actions[clip])
            self.name = clip
        frame = seconds * 60
        self.scene.frame_set(int(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        return points(self.body, evaluated=True, world=True)

    def hand(self, seconds, side='Right'):
        return B @ self.motion.world(N + side + 'Hand', self.name, seconds)

    def asset(self, path):
        return {o.name: o for o in load_glb(path)}

def source_socket(name):
    return trs(json.loads(PROPS[name][2].read_text())['gltf_joint_local'])

def pads(stage, side):
    """Fixed terminal pulp patches, selected once on the undeformed female mesh."""
    p = stage.rest
    f = np.array(stage.faces)
    xyz = p[f]
    n = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
    n /= np.maximum(1e-18, np.linalg.norm(n, axis=1, keepdims=True))
    sets = {}
    for digit, terminal in [('Thumb', '3'), ('Index', '4')]:
        name = N + side + 'Hand' + digit
        bone = stage.arm.matrix_world @ stage.arm.data.bones[name + terminal].matrix_local
        distal, volar = np.array(bone.col[1][:3]), np.array(bone.col[2][:3])
        direction = distal + .65 * volar
        direction /= np.linalg.norm(direction)
        named = np.char.startswith(stage.labels, name)
        tip = (p[named] @ distal).max()
        # Require the terminal segment and the exposed palmar/distal side.
        candidate = (named[f].sum(1) >= 2) & ((xyz @ distal).min(1) >= tip-.017)
        support = (xyz[candidate] @ direction).max()
        selected = candidate & ((xyz @ direction).min(1) >= support-.0035) & (n @ direction > .25)
        sets[digit] = [tuple(face) for face in f[selected]]
        if not sets[digit]:
            raise ValueError(f'No pulp triangles for {name}')
    return sets

def components(p, f):
    """Find independently closed pieces across material and normal seams."""
    from collections import defaultdict
    touching = defaultdict(list)
    keys = [tuple(row) for row in np.round(p, 6)]
    for i, face in enumerate(f):
        for v in face:
            touching[keys[v]].append(i)
    remaining = set(range(len(f)))
    while remaining:
        pending = [remaining.pop()]
        part = []
        while pending:
            i = pending.pop()
            part.append(f[i])
            for v in f[i]:
                for neighbor in touching[keys[v]]:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        pending.append(neighbor)
        yield part

def subpoints(p, f):
    """Vertices, edge midpoints and triangle centroids as surface witnesses."""
    f = np.asarray(f)
    xyz = p[f]
    return np.concatenate((p[np.unique(f)], xyz.mean(1),
                           ((xyz + np.roll(xyz, 1, axis=1)) * .5).reshape(-1, 3)))

def near(bvh, p):
    return min(bvh.find_nearest(v)[3] for v in p)

def signed(bvh, v):
    hit, n, _, d = bvh.find_nearest(v)
    return -d if n.dot(Vector(v) - hit) < 0 else d

RAY = Vector((.731, .339, .592)).normalized()

def interior(bvh, point):
    """Test a consistently wound closed surface with an off-axis exit ray."""
    hit, normal, _, _ = bvh.ray_cast(point, RAY)
    return hit is not None and normal.dot(RAY) > 0

def mesh_bounds(p, f):
    used = p[np.unique(f)]
    return used.min(0), used.max(0)

class Solid:
    def __init__(self, p, f):
        self.p, self.f = p, f
        self.lo, self.hi = mesh_bounds(p, f)
        self.bvh = tree(p, f)

    def enclosed(self, other):
        selected = np.flatnonzero(((other >= self.lo) & (other <= self.hi)).all(1))
        return {int(i): d for i in selected
                if interior(self.bvh, other[i])
                and (d := self.bvh.find_nearest(other[i])[3]) > 1e-6}

def box_bounds(p, lo, hi):
    return ((p >= lo) & (p <= hi)).all(1)
