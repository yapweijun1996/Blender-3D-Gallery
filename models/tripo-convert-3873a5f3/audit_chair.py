"""Inspect the Sit hold against the selected dining chair; report, never alter either asset."""
import json
import os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

asset_dir = os.path.dirname(os.path.abspath(__file__))
chair_file = os.path.join(asset_dir, '..', 'plastic-dining-chair', 'exports', 'optimized.glb')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.join(asset_dir, 'character-motion.glb'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
rig.animation_data.action = bpy.data.actions['Sit']
bpy.context.scene.frame_set(24)  # Midpoint of the seated hold after export starts at frame 0.
previous = set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=chair_file)
chair_parts = set(bpy.context.scene.objects) - previous
chair_root = bpy.data.objects.new('ChairTestTransform', None)
bpy.context.collection.objects.link(chair_root)
for obj in chair_parts:
    if obj.parent is None:
        obj.parent = chair_root
chair_root.scale = (.35, .35, .35)
chair_root.location = (.01, .08, 0)
bpy.context.view_layer.update()
graph = bpy.context.evaluated_depsgraph_get()

def geometry(obj):
    evaluated = obj.evaluated_get(graph)
    data = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ v.co for v in data.vertices]
    faces = [tuple(p.vertices) for p in data.polygons]
    evaluated.to_mesh_clear()
    return vertices, faces

vertices, faces = geometry(mesh)
character_tree = BVHTree.FromPolygons(vertices, faces, epsilon=1e-6)
intersections = {}
for part in sorted(chair_parts, key=lambda o: o.name):
    if part.type != 'MESH':
        continue
    vertices2, faces2 = geometry(part)
    chair_tree = BVHTree.FromPolygons(vertices2, faces2, epsilon=1e-6)
    intersections[part.name] = len(character_tree.overlap(chair_tree))
seat = next(o for o in chair_parts if o.type == 'MESH' and o.name == 'SEAT')
corners = [seat.matrix_world @ Vector(v) for v in seat.bound_box]
lo = [min(v[i] for v in corners) for i in range(3)]
hi = [max(v[i] for v in corners) for i in range(3)]
groups = {g.index for g in mesh.vertex_groups if g.name in ('mixamorig:Hips', 'mixamorig:LeftUpLeg', 'mixamorig:RightUpLeg')}
points = []
for vertex in mesh.data.vertices:
    if any(w.group in groups and w.weight > .5 for w in vertex.groups):
        p = vertices[vertex.index]
        if lo[0] <= p.x <= hi[0] and lo[1] <= p.y <= hi[1] and hi[2] <= p.z < hi[2] + .1:
            points.append(p)
gap = min((p.z - hi[2] for p in points), default=None)
back_hits = sum(v for k, v in intersections.items() if k.startswith('BACK'))
result = {
    'chair': 'plastic-dining-chair/exports/optimized.glb', 'chair_scale': .35,
    'chair_location_blender_m': [.01, .08, 0], 'sit_frame': 24,
    'seat_height_m': hi[2], 'nearest_weighted_hip_or_thigh_gap_m': gap,
    'seat_triangle_overlap_pairs': intersections['SEAT'],
    'back_triangle_overlap_pairs': back_hits, 'parts': intersections,
    'fit_status': 'intersecting' if back_hits or intersections['SEAT'] else 'needs_support_review',
}
print('CHAIR_AUDIT', json.dumps(result, sort_keys=True))
