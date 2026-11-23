"""Containment witnesses for connected chair solids and the original cup-grip rig."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate_actions import mount,triangles
import json
from itertools import product

def exterior(parts, body_tree):
    # With disjoint surfaces, one ray reaching infinity proves the entire
    # connected chair component lies in the exterior of the body triangle soup.
    directions=[Vector(d).normalized() for d in product((-1,0,1), repeat=3) if any(d)]
    for lo,hi,t in parts:
        v=t.find_nearest(lo)[0]
        if all(body_tree.ray_cast(v,d)[0] is not None for d in directions):
            return False
    return True

def authored_grip(path):
    sys.path.insert(0,str(chibi.HANDS))
    from hand_common import rest_data
    from hand_check import hand_geometry
    from hand_surface import patches,nearest
    chibi.fresh()
    scene=bpy.context.scene
    arm=chibi.armature(chibi.load(chibi.BODY));body=scene.objects['Base_Body']
    tips,*_=rest_data(body,arm,'Right')
    pads=patches(body,arm,'Right',tips,hand_geometry(body,'Right',-1,tips))
    chibi.load(path);cup,=chibi.load(ASSETS/'prop.glb')
    verts,faces=posed(cup),triangles(cup)
    ptris=[tuple(i+len(body.data.vertices) for i in t) for t in faces]
    bfaces=triangles(body)
    socket=mount()
    chibi.bind(arm,bpy.data.actions['hold_item'])
    rows=[]
    for t in range(2*CLIPS['hold_item']+1):
        f=t/2;at(scene,f)
        p=posed(body)
        m=np.array(arm.matrix_world@bone(arm,'RightHand').matrix@socket)
        cuppts=verts@m[:3,:3].T+m[:3,3]
        tree=BVHTree.FromPolygons(p.tolist(),bfaces,all_triangles=True)
        ptree=BVHTree.FromPolygons(cuppts.tolist(),faces,all_triangles=True)
        both=np.concatenate((p,cuppts))
        rows.append({'frame':f,'cup_body_pairs':len(tree.overlap(ptree)),
                     'pad_gap_mm':{d:nearest(both,pads[d],ptris)['distance_mm'] for d in ('Thumb','Index')},
                     'cup_z_axis':m[:3,2].tolist()})
    return {'body_sha256':sha(chibi.BODY),'samples':rows}
