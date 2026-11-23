"""Shared Blender I/O for the chair and hand clips. Lengths are metres."""
from pathlib import Path
import json
import math
import struct
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

OUT = Path(__file__).resolve().parent
PARTS = OUT.parent
HANDS = PARTS / 'hand-gestures-astra/round2'
BODY = HANDS / 'base_body.glb'
GESTURES = HANDS / 'hand_gestures.glb'
PRESET = PARTS / 'studio-modules/actions/male_sit_preset.glb'
MOTION = PARTS.parent.parent / 'models/tripo-chibi-motion/motion.glb'
N = 'mixamorig:'
FPS = 30
CLIPS = {'sit_down': 36, 'sit_idle': 90, 'stand_up': 30, 'hold_item': 60}
X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS


def load(path):
    old = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return set(bpy.context.scene.objects) - old


def bind(arm, action):
    data = arm.animation_data_create()
    data.use_nla = False
    data.action = None
    for p in arm.pose.bones:
        p.matrix_basis = Matrix.Identity(4)
    if action:
        data.action = action
        data.action_slot = action.slots[0]
    bpy.context.view_layer.update()


def armature(objects):
    return next(o for o in objects if o.type == 'ARMATURE')


def coords(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    a = np.empty(3*len(ev.data.vertices), dtype=np.float32)
    ev.data.vertices.foreach_get('co', a)
    m = np.array(ev.matrix_world)
    return a.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


def export(ob, filename, **kwargs):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=str(OUT/filename), export_format='GLB',
                              use_selection=True, export_extras=True, **kwargs)


def glb(path):
    data = path.read_bytes()
    n = struct.unpack_from('<I', data, 12)[0]
    return json.loads(data[20:20+n]), data[28+n:]


def rot(axis, degrees):
    return Quaternion(axis, math.radians(degrees))
