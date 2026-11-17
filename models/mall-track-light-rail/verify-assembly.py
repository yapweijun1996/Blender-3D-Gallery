"""Verify two actual rail exports carrying two existing native spotlight head assemblies."""
import hashlib
import math
import json
from pathlib import Path
import runpy
import tempfile
import shutil
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
SPOTLIGHT = HERE.parent / 'mall-track-spotlight'
SOURCE = SPOTLIGHT / 'sources/mall-track-spotlight.blend'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def imported_mesh(path, x):
    previous = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = set(bpy.data.objects) - previous
    root, = [obj for obj in objects if obj.parent is None]
    root.location.x += x
    bpy.context.view_layer.update()
    obj, = [obj for obj in objects if obj.type == 'MESH']
    return obj


def surfaces(obj, test=lambda material: True):
    mesh = obj.data
    pts = [obj.matrix_world @ v.co for v in mesh.vertices]
    faces = [list(p.vertices) for p in mesh.polygons if test(obj.material_slots[p.material_index].name)]
    assert faces, 'A material subset did not resolve'
    used = [pts[i] for i in {i for face in faces for i in face}]
    return used, BVHTree.FromPolygons(pts, faces, epsilon=1e-7)


def query_height(bvh, x, y, start_z, dz):
    position, _, _, _ = bvh.ray_cast(Vector((x, y, start_z)), Vector((0, 0, dz)), .4)
    assert position is not None, f'No surface at {(x, y)}'
    return position.z


def verify_rails(head_files, export):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rails = [imported_mesh(export, x) for x in [-.9, .9]]
    heads = [imported_mesh(f, x) for f, x in zip(head_files, [-.62, .66])]
    (head_a, _), (head_b, _) = map(surfaces, heads)
    clearance = min(v.x for v in head_b) - max(v.x for v in head_a)
    assert clearance > 1.0, 'The two posed heads must have disjoint world-space extents'
    steel = [surfaces(obj, lambda m: m.startswith('Rail •')) for obj in rails]
    gap = min(v.x for v in steel[1][0]) - max(v.x for v in steel[0][0])
    assert abs(gap - .0006) < 1e-6
    assert not steel[0][1].overlap(steel[1][1]), 'Coincident or intersecting body ends'
    key, key_bvh = surfaces(rails[0], lambda m: m.startswith('Nickel splice key'))
    receiver, receiver_bvh = surfaces(rails[1], lambda m: not m.startswith('Nickel splice key'))
    insertion = max(v.x for v in key) - min(v.x for v in receiver)
    assert abs(insertion - .0177) < 1e-6
    assert not key_bvh.overlap(receiver_bvh), 'Splice key strikes the receiving channel'
    # The .085 × .016 m contact foot fits the central opening. The wider casing rests on both lips.
    measured = []
    for x, head, (_, rail_bvh) in zip([-.62, .66], heads, steel):
        _, head_bvh = surfaces(head)
        for dx in [-.025, .025]:
            for y in [-.013, .013]:
                support = query_height(rail_bvh, x + dx, y, -.14, 1)
                casing = query_height(head_bvh, x + dx, y, .01, -1)
                assert abs(support + .024) < 1e-6
                assert abs(casing - support - .0005) < 1e-6
                measured.append(round((casing - support) * 1000, 4))
        for sign in [-1, 1]:
            # Actual support lips start at |Y|=8.7 mm; the inserted foot ends at 8.0 mm.
            y_foot = head_bvh.ray_cast(Vector((x, sign*.025, -.018)),Vector((0,-sign,0)), .03)[0].y
            y_lip = rail_bvh.ray_cast(Vector((x, 0, -.0225)),Vector((0, sign, 0)), .03)[0].y
            assert abs(abs(y_foot) - .008) < 1e-6
            assert abs(abs(y_lip) - abs(y_foot) - .0007) < 1e-6
    if '--render' in sys.argv and export.name == 'optimized.glb':
        sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
        from mall_lighting_delivery import export_fixture, preview
        assembly = bpy.data.objects.new('ASSET_TwoRailAssembly', None)
        bpy.context.scene.collection.objects.link(assembly)
        for instance in rails + heads:
            instance.parent.parent = assembly
        bpy.context.view_layer.update()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            export_fixture(assembly, output / 'assembly.glb')
            preview(output / 'assembly.glb', output, Vector((5.5, -1.5, -.95)).normalized())
            shutil.copyfile(output / 'hero.png', HERE / 'previews' / 'two-rail-assembly.png')
    return dict(file=export.name, sha256=sha(export), pitch_m=1.8, body_gap_m=round(gap,7),
                key_insertion_m=round(insertion,7), lip_engagement_mm=measured,
                foot_clearance_per_side_mm=.7, head_station_separation_m=1.28,
                posed_head_x_clearance_m=round(clearance, 6), rail_instances=2, head_instances=2)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    base = bpy.data.objects['ASSET_MallTrackSpotlight']
    old_rail = bpy.data.objects['Ceiling_Track']
    removed = [o.name for o in old_rail.children_recursive if o.type == 'MESH']
    for obj in list(old_rail.children_recursive) + [old_rail]:
        bpy.data.objects.remove(obj, do_unlink=True)
    assert len(removed) == 11
    assert 'Tilt_Axle' in bpy.data.objects and 'Adapter_Carriage' in bpy.data.objects
    remaining = len([o for o in base.children_recursive if o.type == 'MESH'])
    assert remaining == 50
    bpy.context.view_layer.update()
    with tempfile.TemporaryDirectory() as tmp:
        head_file = Path(tmp) / 'existing-spotlight-without-short-rail.glb'
        export_source = runpy.run_path(str(SPOTLIGHT/'generate.py'))
        export_source['export_lod'](base, head_file, False)
        other_head = Path(tmp) / 'aimed-existing-spotlight-without-short-rail.glb'
        bpy.data.objects['Tilt_Axle'].rotation_euler.x = math.radians(104)
        bpy.data.objects['Swivel_Yoke'].rotation_euler.z = math.radians(30)
        bpy.context.view_layer.update()
        export_source['export_lod'](base, other_head, False)
        rows = [verify_rails([head_file, other_head], HERE/'exports'/file) for file in ['optimized.glb','lod1.glb']]
    print(json.dumps(dict(spotlight_source_sha256=sha(SOURCE),removed_embedded_rail_meshes=len(removed),
                          retained_adapter_yoke_and_head_meshes=remaining,
                          tilt_and_swivel_degrees=[[126, 0], [104, 30]], assemblies=rows), indent=2))


if __name__ == '__main__':
    main()
