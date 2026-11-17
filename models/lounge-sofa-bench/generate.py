"""Original deterministic lounge group. Blender 5.2.3; no external assets.

Template: self-checkout-machine (native source, selected-root GLB, studio views).
Saved source parts stay editable; evaluated export copies form three material batches.
"""
from pathlib import Path
import bpy
import json
import math
import subprocess
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'lounge-sofa-bench'
ROOT = 'ASSET_LoungeSofaBench'
TARGET = (0, 0, .38)


def material(name, rgb, roughness, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    rgba = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = rgba
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    mat.diffuse_color = rgba
    return mat


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def box(name, location, dimensions, mat, parent, bevel=.02, segments=4):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    obj.parent = parent
    if bevel:
        mod = obj.modifiers.new('Rounded manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.harden_normals = True
        for face in obj.data.polygons:
            face.use_smooth = True
        obj.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
    return obj


def piping(name, cx, cy, width, depth, height, mat, parent):
    """Closed rounded rectangle, made from original points, converted to a real mesh."""
    radius = min(.055, depth / 3)
    points = []
    for x, y, start in [(width / 2 - radius, depth / 2 - radius, 0),
                         (-width / 2 + radius, depth / 2 - radius, 90),
                         (-width / 2 + radius, -depth / 2 + radius, 180),
                         (width / 2 - radius, -depth / 2 + radius, 270)]:
        for i in range(7):
            angle = math.radians(start + i * 15)
            points.append((cx + x + radius * math.cos(angle),
                           cy + y + radius * math.sin(angle), height))
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = .0022
    curve.bevel_resolution = 1
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, position in zip(spline.points, points):
        point.co = (*position, 1)
    spline.use_cyclic_u = True
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.parent = parent
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object


def build(root):
    fabric = material('GreigeFabric', (.735, .711, .665), .94)
    metal = material('GraphiteMetal', (.23, .255, .26), .42, .55)
    surface = material('WarmTableSurface', (.69, .55, .40), .56)
    sofa = empty('SOFA_ThreeSeat', root)
    bench = empty('BENCH_Backless', root)
    table = empty('TABLE_SlimShared', root)

    # Staggered parallel furniture envelopes; front is Blender -Y / glTF +Z.
    sx, sy = -.5, .325
    box('SOFA_UpholsteredBase', (sx, sy, .255), (2, .85, .25), fabric, sofa, .095, 6)
    box('SOFA_RecessedUnderframe', (sx, sy, .145), (1.78, .65, .055), metal, sofa, .015)
    for x in (sx - .82, sx + .82):
        for y in (sy - .29, sy + .29):
            box('SOFA_Foot', (x, y, .065), (.048, .048, .13), metal, sofa, .009, 3)
    for x in (sx - .905, sx + .905):
        box('SOFA_RoundedArm', (x, sy, .40), (.19, .81, .44), fabric, sofa, .085, 6)
    box('SOFA_BackShell', (sx, .67, .59), (1.80, .16, .42), fabric, sofa, .073, 6)
    for i, x in enumerate((sx - .546, sx, sx + .546), 1):
        box(f'SOFA_SeatCushion_{i}', (x, .228, .406), (.53, .59, .15), fabric, sofa, .065, 6)
        piping(f'SOFA_SeatWelt_{i}', x, .228, .497, .557, .428, fabric, sofa)
        pad = box(f'SOFA_BackCushion_{i}', (x, .557, .627), (.53, .185, .315), fabric, sofa, .064, 6)
        pad.rotation_euler.x = -.085

    bx, by = .3, -.56
    box('BENCH_UpholsteredBase', (bx, by, .265), (1.56, .34, .15), fabric, bench, .055, 5)
    box('BENCH_RecessedUnderframe', (bx, by, .178), (1.40, .27, .045), metal, bench, .012)
    for x in (bx - .67, bx + .67):
        for y in (by - .12, by + .12):
            box('BENCH_Foot', (x, y, .085), (.042, .042, .17), metal, bench, .008, 3)
    for i, x in enumerate((bx - .404, bx + .404), 1):
        box(f'BENCH_SeatCushion_{i}', (x, by, .385), (.792, .38, .13), fabric, bench, .057, 6)
        piping(f'BENCH_SeatWelt_{i}', x, by, .758, .346, .402, fabric, bench)

    # Shared reach table lies strictly between the sofa and bench depth envelopes.
    tx, ty = 1.075, -.235
    box('TABLE_RoundedTop', (tx, ty, .486), (.85, .22, .028), surface, table, .013, 5)
    box('TABLE_UnderTopReveal', (tx, ty, .464), (.78, .17, .018), metal, table, .007)
    for x in (tx - .265, tx + .265):
        box('TABLE_BladeSupport', (x, ty, .244), (.035, .145, .43), metal, table, .008, 3)
        box('TABLE_FloorShoe', (x, ty, .016), (.12, .18, .032), metal, table, .012, 4)


def measure_source():
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for group in root.children:
        coords = []
        parts = []
        for obj in group.children_recursive:
            if obj.type != 'MESH':
                continue
            evaluated = obj.evaluated_get(depsgraph)
            coords.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
            parts.append(obj.name)
        minimum = [min(v[i] for v in coords) for i in range(3)]
        maximum = [max(v[i] for v in coords) for i in range(3)]
        groups[group.name] = {'axis_order': 'Blender X,Y,Z (width,depth,height)',
                              'min': minimum, 'max': maximum,
                              'size': [b - a for a, b in zip(minimum, maximum)], 'parts': sorted(parts)}
    parts = [o for o in root.children_recursive if o.type == 'MESH']
    report = {'blender_version': bpy.app.version_string, 'root': root.name,
              'root_location': list(root.location), 'source_mesh_parts': len(parts),
              'source_materials': sorted({m.name for o in parts for m in o.data.materials}),
              'source_text_objects': sum(o.type == 'FONT' for o in root.children_recursive),
              'subassemblies': groups}
    (HERE / 'reports/sources.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def export(path):
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    parts = sorted((o for o in root.children_recursive if o.type == 'MESH'), key=lambda o: o.name)
    temporary = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    try:
        buckets = {}
        for obj in parts:
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
            mesh.transform(obj.matrix_world)
            copy = bpy.data.objects.new('EXPORT_' + obj.name, mesh)
            bpy.context.scene.collection.objects.link(copy)
            copy.parent = root
            temporary.append(copy)
            buckets.setdefault(mesh.materials[0].name, []).append(copy)
        batches = []
        for name, objects in sorted(buckets.items()):
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            bpy.context.object.name = 'BATCH_' + name
            batches.append(bpy.context.object)
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for obj in batches:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in temporary:
            try:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.meshes.remove(mesh)
            except ReferenceError:
                pass


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.24, .27, .29, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
    floor = material('STUDIO_Floor', (.36, .39, .40), .9)
    box('STUDIO_Floor', (0, 0, -.03), (200, 200, .06), floor, None, 0)
    for name, loc, power, size in [('Key', (-3, -4, 5), 850, 3.5),
                                    ('Fill', (4, -2, 3), 500, 3),
                                    ('Rim', (1, 3, 4), 1000, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy, obj.data.size = power, size
        aim(obj, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 3.65
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    for name, position in [('hero', (2.6, -5, 3.0)), ('front', (0, -6, 2.2)),
                           ('side', (6, 0, 2.2)), ('3q', (-3.7, -5, 3.8))]:
        if '--views' in sys.argv and name not in sys.argv[sys.argv.index('--views') + 1].split(','):
            continue
        scene.camera.location = position
        aim(scene.camera, TARGET)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    # Keep the gallery card light while retaining full-size inspection PNGs.
    hero = HERE / 'previews/hero.png'
    if hero.exists():
        subprocess.run(['python3', '-c',
                        'from PIL import Image; import sys; '
                        'Image.open(sys.argv[1]).resize((512,512), Image.Resampling.LANCZOS)'
                        '.save(sys.argv[2], format="WEBP", quality=84, method=6)',
                        str(hero), str(HERE / 'previews/hero.webp')], check=True)


def main():
    if bpy.app.version < (5, 2, 3):
        raise RuntimeError('Use Blender 5.2.3 or newer; do not downgrade the native source')
    for directory in ('sources', 'exports', 'metadata', 'previews', 'reports'):
        (HERE / directory).mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        root = empty(ROOT)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['origin'] = 'Floor centre of combined footprint'
        root['scope'] = 'Original static three-seat sofa, backless bench and shared slim table'
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    measure_source()
    export(HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
