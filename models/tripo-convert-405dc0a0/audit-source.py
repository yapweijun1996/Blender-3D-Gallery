"""Measure the original FBX and sample skinned vertices before the GLB export."""

from collections import Counter
import json
from math import dist, sqrt
from pathlib import Path
from runpy import run_path
import sys
from tempfile import TemporaryDirectory

import bmesh
import bpy

import_character = run_path(str(Path(__file__).with_name('export.py')))['import_character']
output = Path(sys.argv[sys.argv.index('--') + 1])

with TemporaryDirectory(prefix='tripo_audit_') as directory:
    rig, obj, action = import_character(directory)
    scene = bpy.context.scene
    deform = {bone.name for bone in rig.data.bones if bone.use_deform}
    weights = [
        [group.weight for group in vertex.groups
         if obj.vertex_groups[group.group].name in deform and group.weight > 0]
        for vertex in obj.data.vertices
    ]
    totals = [sum(group) for group in weights]
    # The GLB surface has no primitives for vertices that belong to no face.
    surface_indices = sorted({index for face in obj.data.polygons for index in face.vertices})
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = {
        'blender': bpy.app.version_string,
        'fps': scene.render.fps / scene.render.fps_base,
        'vertices': len(obj.data.vertices),
        'surface_vertices': len(surface_indices),
        'faces': len(obj.data.polygons),
        'bones': len(rig.data.bones),
        'uv_maps': len(obj.data.uv_layers),
        'materials': len(obj.data.materials),
        'textures': {image.name: list(image.size) for image in bpy.data.images if image.type == 'IMAGE'},
        'weights': {
            'unweighted': sum(total < 1e-8 for total in totals),
            'min': min(totals),
            'max': max(totals),
            'influences': dict(Counter(map(len, weights))),
        },
        'mesh': {
            'boundary_edges': sum(edge.is_boundary for edge in bm.edges),
            'nonmanifold_edges': sum(not edge.is_manifold for edge in bm.edges),
            'wire_edges': sum(edge.is_wire for edge in bm.edges),
            'zero_area_faces': sum(face.calc_area() < 1e-12 for face in bm.faces),
        },
        'source_action': action.name,
        'samples': [],
    }
    bm.free()

    start, end = action.frame_range
    for index in range(5):
        frame = start + (end - start) * index / 4
        scene.frame_set(int(frame))
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        vertices = [list(evaluated.matrix_world @ mesh.vertices[index].co) for index in surface_indices]
        evaluated.to_mesh_clear()
        axes = tuple(zip(*vertices))
        result['samples'].append({
            'frame': frame,
            'vertices': vertices,
            'bounds': [min(axis) for axis in axes] + [max(axis) for axis in axes],
        })

    first = result['samples'][0]['vertices']
    last = result['samples'][-1]['vertices']
    displacement = [sum(b - a for a, b in zip(before, after)) / len(first)
                    for before, after in zip(zip(*first), zip(*last))]
    differences = [dist([coord + delta for coord, delta in zip(p, displacement)], q)
                   for p, q in zip(first, last)]
    result['endpoints'] = {
        'mean_displacement': displacement,
        'max_difference_after_translation': max(differences),
        'rms_difference_after_translation': sqrt(sum(d ** 2 for d in differences) / len(differences)),
    }

output.write_text(json.dumps(result), encoding='utf-8')
summary = {key: value for key, value in result.items() if key != 'samples'}
summary['sample_bounds'] = {sample['frame']: sample['bounds'] for sample in result['samples']}
print('Source audit:', summary)
