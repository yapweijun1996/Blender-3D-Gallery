"""Check saved world-space garment surfaces and conservative inner-sleeve gaps."""
from pathlib import Path
from itertools import combinations
import bpy
import hashlib
import json
import math
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
source = HERE / 'sources/fashion-clothing-rack.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.view_layer.update()
garments = sorted((obj for obj in bpy.data.objects if 'garment_type' in obj), key=lambda obj: obj.name)
assert len(garments) == 10


def surface(obj):
    obj.data.calc_loop_triangles()
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    triangles = [tuple(tri.vertices) for tri in obj.data.loop_triangles]
    return {'object': obj, 'points': points,
            'tree': BVHTree.FromPolygons(points, triangles, all_triangles=True, epsilon=0),
            'min': [min(p[i] for p in points) for i in range(3)],
            'max': [max(p[i] for p in points) for i in range(3)]}


parts = {group.name: [surface(obj) for obj in group.children_recursive if obj.type == 'MESH']
         for group in garments}
intersections = []
tested_pairs = 0
for a, b in combinations(garments, 2):
    for sa in parts[a.name]:
        for sb in parts[b.name]:
            tested_pairs += 1
            if any(sa['max'][i] < sb['min'][i] or sb['max'][i] < sa['min'][i] for i in range(3)):
                continue
            hits = sa['tree'].overlap(sb['tree'])
            if hits:
                intersections.append({'a': sa['object'].name, 'b': sb['object'].name,
                                      'intersecting_triangle_pairs': len(hits)})

# A positive projection gap separates the complete sleeve/cuff meshes by a plane.
# It is a conservative lower bound on distance, not a vertex-distance estimate.
gaps = []
for index, a in enumerate(garments):
    b = garments[(index + 1) % len(garments)]
    pa = [p for s in parts[a.name] if s['object'].name in
          (f'SLEEVE_{index:02d}_-1', f'CUFF_{index:02d}_-1') for p in s['points']]
    next_index = (index + 1) % len(garments)
    pb = [p for s in parts[b.name] if s['object'].name in
          (f'SLEEVE_{next_index:02d}_-1', f'CUFF_{next_index:02d}_-1') for p in s['points']]
    if a['garment_type'] == 'Dress' or b['garment_type'] == 'Dress':
        continue
    assert pa and pb, (a.name, b.name)
    angle = math.radians(18 + index * 36 + 18)
    normal = Vector((-math.sin(angle), math.cos(angle), 0))
    gap = min(p.dot(normal) for p in pb) - max(p.dot(normal) for p in pa)
    gaps.append({'a': a.name, 'b': b.name, 'separating_plane_gap_metres': gap})

report = {'result': 'PASS' if not intersections and min(g['separating_plane_gap_metres'] for g in gaps) > .005 else 'FAIL',
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'method': 'World-space triangle BVH overlap, epsilon 0; AABB rejection only skips disjoint pairs. Adjacent inner sleeves plus cuffs also require a separating-plane gap above 5 mm.',
          'scope': 'All meshes belonging to different garments, including hangers. Own-garment seams and rail-hook contacts are excluded.',
          'garment_pairs': math.comb(len(garments), 2), 'mesh_pairs': tested_pairs,
          'intersecting_mesh_pairs': intersections,
          'inner_sleeve_gaps': gaps,
          'minimum_inner_sleeve_gap_lower_bound_metres': min(g['separating_plane_gap_metres'] for g in gaps)}
print(json.dumps(report, indent=2))
if '--baseline' not in sys.argv:
    (HERE / 'reports/clearance.json').write_text(json.dumps(report, indent=2) + '\n')
    assert report['result'] == 'PASS', intersections
