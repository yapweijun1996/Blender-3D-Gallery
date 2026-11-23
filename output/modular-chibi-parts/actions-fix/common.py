"""Bind the 30 fps action bank to the original master, using Blender's glTF importer."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ASSETS = OUT.parent / "actions-astra"
SHARED = OUT.parent / "body-fix"
sys.path[:0] = [str(SHARED), str(ASSETS)]
import bpy
import numpy as np
from bodycheck import Checker, MASTER, posed, pair_depth, sha
from clearance import kind, knee_contact, bone, turn, SIDES
import chibi
from chibi import CLIPS, FPS
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

SOURCE = ASSETS / "actions.glb"
FIXED = OUT / "actions_fixed.glb"

def load(path=SOURCE):
    bpy.ops.wm.open_mainfile(filepath=str(MASTER), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1
    arm, body = scene.objects["Armature"], scene.objects["Base_Body"]
    chibi.bind(arm, None)
    before = set(bpy.data.actions)
    objects = chibi.load(path)
    actions = {a.name:a for a in set(bpy.data.actions) - before}
    assert set(actions) == set(CLIPS)
    imported = chibi.armature(objects)
    assert set(imported.data.bones.keys()) == set(arm.data.bones.keys())
    for ob in objects:
        ob.hide_viewport = ob.hide_render = True
    return scene, arm, body, actions

def at(scene, frame):
    scene.frame_set(int(frame), subframe=frame-int(frame))

def target(a,b):
    ka, kb = kind(a), kind(b)
    if ka != kb and 'body' in (ka,kb):
        return 'arm_body'
    if any(knee_contact(a,b,s) for s in SIDES):
        return 'shin_thigh'
    return None

class Surface:
    def __init__(self, checker, labels):
        self.faces = np.flatnonzero([labels(r) for r in checker.regions])
        self.verts, local = np.unique(checker.indices[self.faces].ravel(),return_inverse=True)
        self.local = local.reshape(-1,3).tolist()

    def tree(self, points):
        return BVHTree.FromPolygons(points[self.verts].tolist(), self.local, all_triangles=True)

class Zone:
    def __init__(self, checker, first, second):
        self.checker = checker
        self.a, self.b = Surface(checker, first), Surface(checker, second)

    def pairs(self, points):
        hits=self.a.tree(points).overlap(self.b.tree(points))
        faces=self.checker.surface_sets
        pairs=[(self.a.faces[i],self.b.faces[j]) for i,j in hits]
        return [(i,j) for i,j in pairs if faces[i].isdisjoint(faces[j])]

