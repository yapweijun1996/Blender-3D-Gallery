"""Check fitted chair support and sampled Sit motion on the exported GLBs.

Run: blender -b -t 4 --python-exit-code 1 --python audit_chair.py -- [--chair PATH] [--report-only]
"""
import argparse
import json
import math
import os
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

asset_dir = os.path.dirname(os.path.abspath(__file__))
parser = argparse.ArgumentParser()
parser.add_argument('--chair', default=os.path.join(asset_dir, 'fitted-chair.glb'))
parser.add_argument('--character', default=os.path.join(asset_dir, 'character-motion.glb'))
parser.add_argument('--report-only', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=args.character)
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers))
rig.animation_data.action = bpy.data.actions['Sit']
scene = bpy.context.scene
previous = set(scene.objects)
bpy.ops.import_scene.gltf(filepath=args.chair)
chair_parts = [o for o in set(scene.objects) - previous if o.type == 'MESH']
if not chair_parts:
    raise ValueError('Chair has no meshes')
bpy.context.view_layer.update()
graph = bpy.context.evaluated_depsgraph_get()

def geometry(obj):
    evaluated = obj.evaluated_get(graph)
    data = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ v.co for v in data.vertices]
    normals = [evaluated.matrix_world.to_3x3() @ v.normal for v in data.vertices]
    faces = [tuple(p.vertices) for p in data.polygons]
    evaluated.to_mesh_clear()
    return vertices, faces, normals

chairs = {}
for part in chair_parts:
    vertices, faces, _ = geometry(part)
    chairs[part.name] = BVHTree.FromPolygons(vertices, faces, epsilon=1e-7)
if 'SEAT' not in chairs or 'Seat_Cushion' not in chairs:
    raise ValueError('The fitted seat and cushion are required')

collisions = []
floor_min = float('inf')
for tick in range(145):
    frame = tick / 2
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    vertices, faces, _ = geometry(mesh)
    floor_min = min(floor_min, min(v.z for v in vertices))
    body = BVHTree.FromPolygons(vertices, faces, epsilon=1e-7)
    hits = {name: len(body.overlap(tree)) for name, tree in chairs.items()}
    hits = {name: count for name, count in hits.items() if count}
    if hits:
        collisions.append({'frame': frame, 'parts': hits})

# Check downward-facing, bone-weighted samples over the actual seat/cushion.
scene.frame_set(24)
vertices, _, normals = geometry(mesh)
support = {}
for name in ('Hips', 'LeftUpLeg', 'RightUpLeg'):
    group = mesh.vertex_groups['mixamorig:' + name].index
    gaps = []
    for vertex in mesh.data.vertices:
        if not any(w.group == group and w.weight > .3 for w in vertex.groups):
            continue
        p = vertices[vertex.index]
        if not (-.092 < p.x < .102 and .026 < p.y < .1 and .17 < p.z < .24 and normals[vertex.index].z < -.2):
            continue
        distances = []
        for part in ('SEAT', 'Seat_Cushion'):
            hit, _, _, _ = chairs[part].ray_cast(p + Vector((0, 0, .00005)), Vector((0, 0, -1)), .08)
            if hit is not None:
                distances.append(p.z - hit.z)
        if distances:
            gaps.append(min(distances))
    if not gaps:
        raise ValueError('No support samples for ' + name)
    support[name] = {'samples': len(gaps), 'nearest_gap_m': min(gaps), 'within_2mm': sum(d <= .002 for d in gaps)}

result = {'samples': 145, 'frames_with_intersections': len(collisions), 'collisions': collisions,
          'minimum_ground_height_m': floor_min, 'hold_frame': 24, 'support': support}
print('CHAIR_AUDIT', json.dumps(result, sort_keys=True))
if not args.report_only:
    assert not collisions, 'Character intersects the chair during Sit'
    assert floor_min >= -.001, 'Character penetrates the ground by more than 1 mm'
    for name, evidence in support.items():
        assert evidence['nearest_gap_m'] <= .001, name + ': support gap exceeds 1 mm'
        assert evidence['within_2mm'] >= 2, name + ': insufficient near-contact samples'
    print('CHAIR_AUDIT PASS')
