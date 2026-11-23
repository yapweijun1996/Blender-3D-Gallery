"""Shared rest-space landmarks and naming for the chibi hand library."""
from pathlib import Path
import sys
import traceback
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parent
MASTER = OUT.parent / "master" / "GJH_Chibi_Master_rigged.blend"
DIGITS = ("Index", "Middle", "Ring", "Pinky", "Thumb")
SIDES = (("L", "Left", 1), ("R", "Right", -1))
GESTURES = ("fist", "open_relaxed", "point", "thumbs_up", "peace", "ok",
            "grip_small", "pinch", "open_wide")
Z = Vector((0, 0, 1))


def prefix(side):
    return "mixamorig:" + side + "Hand"


def smooth(a, b, x):
    u = min(1, max(0, (x-a)/(b-a)))
    return u*u*(3-2*u)


def vertex_weights(body, v):
    return {body.vertex_groups[g.group].name: g.weight for g in v.groups if g.weight > 0}


def rest_data(body, rig, side):
    base = prefix(side)
    mesh = body.data
    weights = [vertex_weights(body, v) for v in mesh.vertices]
    tips = {}
    for digit in DIGITS:
        bones = [rig.data.bones[base+digit+str(i)] for i in (1, 2, 3, 4)]
        direction = (bones[3].head_local-bones[0].head_local).normalized()
        distal = {tuple(v.co): v.index for v in mesh.vertices
                  if sum(weights[v.index].get(b.name, 0) for b in bones[2:]) > .60}
        end = max(Vector(p).dot(direction) for p in distal)
        tips[digit] = [i for p, i in distal.items() if Vector(p).dot(direction) > end-.0018]
    # Ray at halfway from the wrist to the mean MCP location. This is the
    # palmar skin landmark a fingertip can actually touch. Never refit per pose.
    wrist = rig.data.bones[base].head_local
    knuckles = sum((rig.data.bones[base+d+'1'].head_local for d in DIGITS[:4]), Vector())/4
    mid = (wrist+knuckles)/2
    tree = BVHTree.FromPolygons([v.co for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons])
    palm, normal, _, _ = tree.ray_cast(Vector((mid.x, mid.y, mid.z-.10)), Z, .2)
    back, _, _, _ = tree.ray_cast(Vector((mid.x, mid.y, mid.z+.10)), -Z, .2)
    return tips, palm, (back+palm)/2, normal


def clean_pose(arm):
    if arm.animation_data:
        arm.animation_data.action = None
    for p in arm.pose.bones:
        p.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def set_action(arm, action):
    clean_pose(arm)
    data = arm.animation_data_create()
    data.action = action
    data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()


def glb(path):
    import json
    import struct
    data = path.read_bytes()
    magic, version, length, n, kind = struct.unpack_from('<4sIIII', data)
    assert magic == b'glTF' and version == 2 and length == len(data) and kind == 0x4e4f534a
    return json.loads(data[20:20+n]), data[28+n:]


def run_batch(operation):
    """Propagate Python failures through Blender's headless process exit code."""
    try:
        operation()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        raise SystemExit(1)
