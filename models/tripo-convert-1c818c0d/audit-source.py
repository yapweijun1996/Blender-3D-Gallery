"""Inspect original skin and record sampled deformed FBX vertices for browser comparison.

Run with Blender and pass an output JSON path after --.
"""
import bpy, bmesh, json, sys
from collections import Counter
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
STEM = 'tripo_convert_1c818c0d-87d5-4ff0-a21c-bac7bb1956e7'
output = Path(sys.argv[sys.argv.index('--') + 1])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
with TemporaryDirectory(prefix='tripo_audit_') as directory:
    with ZipFile(HERE / (STEM + '.zip')) as archive:
        for item in archive.infolist():
            p = PurePosixPath(item.filename)
            if p.is_absolute() or '..' in p.parts:
                raise ValueError('Unsafe ZIP entry')
        archive.extractall(directory)
    bpy.ops.import_scene.fbx(filepath=str(Path(directory) / (STEM + '.fbx')))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    deform = {b.name for b in rig.data.bones if b.use_deform}
    weight, influences = [], []
    for vertex in obj.data.vertices:
        w = [g.weight for g in vertex.groups if obj.vertex_groups[g.group].name in deform and g.weight > 0]
        weight.append(sum(w)); influences.append(len(w))
    bm = bmesh.new(); bm.from_mesh(obj.data)
    result = {'blender': bpy.app.version_string, 'fps': bpy.context.scene.render.fps / bpy.context.scene.render.fps_base,
              'vertices': len(obj.data.vertices), 'faces': len(obj.data.polygons), 'bones': len(rig.data.bones),
              'weights': {'unweighted': sum(x < 1e-8 for x in weight), 'min': min(weight), 'max': max(weight),
                          'influences': dict(Counter(influences))},
              'mesh': {'boundary_edges': sum(e.is_boundary for e in bm.edges), 'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
                       'wire_edges': sum(e.is_wire for e in bm.edges), 'zero_area_faces': sum(f.calc_area() < 1e-12 for f in bm.faces)}, 'samples': {}}
    bm.free()
    rig.animation_data_create()
    for action in bpy.data.actions:
        name = next((n for n in ('run', 'sit') if ('|' + n + '.') in action.name), None)
        if not name: continue
        rig.animation_data.action = action
        start, end = action.frame_range
        result['samples'][name] = []
        for i in range(5):
            frame = start + (end - start) * i / 4
            bpy.context.scene.frame_set(int(frame), subframe=frame-int(frame))
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
            vertices = [list(evaluated.matrix_world @ v.co) for v in mesh.vertices]
            evaluated.to_mesh_clear()
            result['samples'][name].append({'frame': frame, 'vertices': vertices})
    output.write_text(json.dumps(result))
    print('Source audit:', {k: v for k, v in result.items() if k != 'samples'})
