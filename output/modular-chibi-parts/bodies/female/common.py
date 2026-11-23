"""Paths and action binding shared by the female build, fit and QA."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
PARTS = HERE.parents[1]
REPO = PARTS.parents[1]
STUDIO = PARTS / "studio-modules/body-female/work"
NEUTRAL = PARTS / "master/GJH_Chibi_Master_rigged.blend"
MASTER = HERE / "master_female.blend"
BODY = HERE / "body_female.glb"
MOTION = HERE / "motion_female.glb"
RUNTIME = HERE / ".runtime"
SHARED = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
SIT = ("sit_down", "sit_idle", "stand_up", "hold_item")
CARRY = ("hold_box", "hold_bag", "take_item")
CLIPS = SHARED + SIT + CARRY
SOURCES = [(PARTS / "body-fix/motion_fixed.glb", SHARED),
           (PARTS / "actions-fix/actions_fixed.glb", SIT),
           (PARTS / "actions-hold2/hold_actions.glb", CARRY)]
MODULES = {
    "hair-bob": ("hair-fit-astra/round2/hair_bob_v2.glb", 3000),
    "hair-spiky": ("studio-modules/hair-spiky/hair_spiky_v1.glb", 3000),
    "hair-sidepart": ("studio-modules/hair-sidepart/round3/hair_sidepart_v3.glb", 3000),
    "tshirt": ("studio-modules/tshirt/round5/tshirt_v5.glb", 6000),
    "dress": ("studio-modules/dress/round5/dress_v5.glb", 6000),
    "jeans": ("studio-modules/jeans/round5/jeans_v5.glb", 6000),
    "sneakers": ("shoes-sol/round3/shoes_sneaker_v3.glb", None),
}


def load_glb(path):
    scene = bpy.context.scene
    previous = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return set(scene.objects) - previous


def dispose(objects):
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def reset(arm):
    animation = arm.animation_data_create()
    animation.action = None
    animation.use_nla = False
    for bone in arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    return animation


def bind(arm, action):
    animation = reset(arm)
    if action is not None:
        animation.action = action
        animation.action_slot = action.slots[0]
    bpy.context.view_layer.update()


def set_frame(scene, frame):
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.context.view_layer.update()


def samples(first, last, rate=2):
    first, last = round(float(first), 5), round(float(last), 5)
    values = {first, last}
    values.update(i / rate for i in range(math.ceil(rate * first), math.floor(rate * last) + 1))
    return sorted(values)


def arguments():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
