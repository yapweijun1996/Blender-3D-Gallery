"""Asset paths, rigid sockets and preview placement. Blender world units are metres."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARTS = HERE.parent
ASTRA = PARTS / 'actions-astra'
sys.path.insert(0, str(ASTRA))
from chibi import (bpy, np, math, json, Matrix, Quaternion, Vector, N, X, Y, Z,
                   armature, bind, coords, fresh, glb, load, rot, export)
from build_actions import GRIP_AXIS, GRIP_CENTER, upper_basis, smooth
BODY = PARTS.parents[1] / 'models/chibi-dressup/base_body.glb'
GESTURES = BODY.with_name('hand_gestures.glb')
MASTER = PARTS / 'master/GJH_Chibi_Master_rigged.blend'
FIXED = PARTS / 'body-fix/motion_fixed.glb'
BANK = HERE / 'hold_actions.glb'
FPS = 24
NAMES = ('hold_box', 'hold_bag', 'take_item')
FILES = dict(zip(NAMES, ('box','bag','shelf_item')))
GRIP = 29
C = rot(X,-90).to_matrix().to_4x4()
ID = Quaternion()
ONE = Vector((1,1,1))

def trs(point, orientation=ID):
    return Matrix.LocRotScale(Vector(point), orientation, ONE)

def record(mat):
    t, q, _ = mat.decompose()
    return dict(translation_m=list(t), quaternion_xyzw=[q.x,q.y,q.z,q.w])

def matrix(data):
    x,y,z,w = data['quaternion_xyzw']
    return trs(data['translation_m'],Quaternion((w,x,y,z)))

def joint(arm, side='Right'):
    return arm.matrix_world @ arm.pose.bones[N+side+'Hand'].matrix

def node_world(doc, i):
    node = doc['nodes'][i]
    local = matrix(dict(translation_m=node.get('translation',[0]*3),
                        quaternion_xyzw=node.get('rotation',[0,0,0,1])))
    parent = next((j for j,n in enumerate(doc['nodes']) if i in n.get('children',[])),None)
    return node_world(doc,parent) @ local if parent is not None else local

def equipment(name, arm, f, cfg, root_lift=0, first_pick=False):
    local = matrix(cfg['blender_pose_bone_head_local'])
    if name=='take_item' and f < GRIP:
        # A level display rail returns the released sample to the pick stop.
        a,b = [matrix(cfg[k]) for k in ('return_stop_blender','pickup_stop_blender')]
        if first_pick:
            return trs((0,0,root_lift)) @ b
        start,end=cfg['return_frames']
        return trs((0,0,root_lift)) @ a.lerp(b,smooth(min(1,max(0,(f-start)/(end-start)))))
    return joint(arm) @ local

def setup():
    fresh()
    scene=bpy.context.scene
    scene.render.fps=FPS
    scene.render.fps_base=1
    scene.frame_start=0
    scene.frame_end=48
    return scene

def placement():
    return json.loads((HERE/'placement.json').read_text())

def place_shelf(shelf,config,lift):
    # Scale the pedestal in world Z around its floor origin. The deck, and
    # hence the waiting item, gains exactly the character's footwear lift.
    top=config['shelf_deck_z_m']
    shelf.matrix_world=Matrix.Diagonal(Vector((1,1,1+lift/top,1)))

def dress(arm,path):
    objects=load(path)
    mesh,=[o for o in objects if o.type=='MESH' and len(o.vertex_groups)]
    world=mesh.matrix_world.copy()
    mesh.parent=arm;mesh.matrix_world=world
    for modifier in mesh.modifiers:
        if modifier.type=='ARMATURE':modifier.object=arm
    for o in objects-{mesh}:bpy.data.objects.remove(o,do_unlink=True)
    return mesh

