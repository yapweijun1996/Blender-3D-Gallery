"""Original deterministic headphone fixture. Blender 5.2.3; no external assets."""
from pathlib import Path
import bpy
import json
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'headphone-display-stand'
ROOT = 'ASSET_HeadphoneDisplayStand'
TARGET = (0, 0, .71)


def material(name, rgb, metallic=0, roughness=.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    m.diffuse_color = color
    return m


def empty(name, parent=None, location=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = location
    return o


def mesh(name, vertices, faces, mat, parent, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    data.materials.append(mat)
    for p in data.polygons:
        p.use_smooth = smooth
    return o


def box(name, loc, dims, mat, parent, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.parent = parent
    o.data.materials.append(mat)
    if bevel:
        m = o.modifiers.new('Soft manufactured edges', 'BEVEL')
        m.width = min(bevel, min(dims) * .45)
        m.segments = 2
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)
        n = o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
        bpy.ops.object.modifier_apply(modifier=n.name)
    return o


def sweep(name, points, radius, mat, parent, sides=8):
    points = [Vector(p) for p in points]
    vertices, faces = [], []
    for i, p in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]).normalized()
        u = Vector((1, 0, 0))
        v = tangent.cross(u).normalized()
        for k in range(sides):
            a = 2 * math.pi * k / sides
            vertices.append(p + radius * (math.cos(a) * u + math.sin(a) * v))
    for i in range(len(points) - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + k for k in range(sides))])
    return mesh(name, vertices, faces, mat, parent, True)


def band(name, cx, cy, top, rx, rz, thickness, depth, mat, parent, steps=28):
    vertices, faces = [], []
    for i in range(steps + 1):
        a = math.pi * i / steps
        normal = Vector((math.cos(a) / rx, 0, math.sin(a) / rz)).normalized()
        center = Vector((cx + rx * math.cos(a), cy, top - .095 + rz * math.sin(a)))
        for radial, forward in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            vertices.append(center + normal * (radial * thickness / 2) + Vector((0, forward * depth / 2, 0)))
    for i in range(steps):
        for k in range(4):
            a, b = 4 * i + k, 4 * i + (k + 1) % 4
            faces.append((a, b, b + 4, a + 4))
    faces.extend([(3, 2, 1, 0), tuple(4 * steps + k for k in range(4))])
    return mesh(name, vertices, faces, mat, parent, True)


def cup_shape(name, center, side, yaw, profile, mat, parent, segments=24, pad=False):
    """Closed lathed oval shell, or an elliptical torus for the ear cushion."""
    vertices, faces = [], []
    def place(x, y, z):
        return (center[0] + side * (x * math.cos(yaw) - y * math.sin(yaw)),
                center[1] + x * math.sin(yaw) + y * math.cos(yaw), center[2] + z)
    if pad:
        for i in range(segments):
            a = 2 * math.pi * i / segments
            for j in range(8):
                b = 2 * math.pi * j / 8
                vertices.append(place(-.014 + .007 * math.sin(b),
                                      (.025 + .007 * math.cos(b)) * math.cos(a),
                                      (.037 + .007 * math.cos(b)) * math.sin(a)))
        for i in range(segments):
            for j in range(8):
                faces.append((i * 8 + j, ((i + 1) % segments) * 8 + j,
                              ((i + 1) % segments) * 8 + (j + 1) % 8, i * 8 + (j + 1) % 8))
    else:
        for x, scale in profile:
            for i in range(segments):
                a = 2 * math.pi * i / segments
                vertices.append(place(x, .033 * scale * math.cos(a), .045 * scale * math.sin(a)))
        for j in range(len(profile) - 1):
            for i in range(segments):
                faces.append((j * segments + i, j * segments + (i + 1) % segments,
                              (j + 1) * segments + (i + 1) % segments, (j + 1) * segments + i))
        faces.extend([tuple(reversed(range(segments))),
                      tuple((len(profile) - 1) * segments + i for i in range(segments))])
    # Reflecting the left cup reverses winding; keep all shells facing outwards.
    if side == -1:
        faces = [tuple(reversed(f)) for f in faces]
    return mesh(name, vertices, faces, mat, parent, True)


def headphone(index, cx, top, color, dark, grey, root):
    group = empty(f'HEADPHONE_{index:02d}', root)
    group['role'] = 'generic over-ear headphones'
    group['hanger_position_blender'] = [cx, -.125, top]
    band(f'HP{index:02d}_HeadbandShell', cx, -.125, top, .067, .095, .008, .029, color, group)
    band(f'HP{index:02d}_HeadbandPadding', cx, -.125, top - .006, .062, .093, .004, .024, dark, group)
    for side in [-1, 1]:
        suffix = 'L' if side < 0 else 'R'
        box(f'HP{index:02d}_{suffix}_TelescopicYoke', (cx + side * .067, -.125, top - .117),
            (.009, .014, .055), grey, group, .003)
        box(f'HP{index:02d}_{suffix}_SwivelBridge', (cx + side * .071, -.125, top - .145),
            (.016, .02, .018), color, group, .004)
        center = (cx + side * .069, -.125, top - .170)
        cup_shape(f'HP{index:02d}_{suffix}_OvalShell', center, side, .30,
                  [(-.009, .85), (-.005, 1), (.006, 1), (.012, .84)], color, group)
        cup_shape(f'HP{index:02d}_{suffix}_InsetFace', center, side, .30,
                  [(.0121, .73), (.014, .70)], grey if color == dark else color, group)
        cup_shape(f'HP{index:02d}_{suffix}_SoftEarCushion', center, side, .30, [], dark, group, pad=True)


def build(root):
    dark = material('Graphite', (.075, .083, .095), .12, .43)
    white = material('Porcelain', (.87, .88, .87), .02, .38)
    grey = material('Satin Grey', (.46, .49, .51), .42, .32)
    fixture = empty('FIXTURE', root)
    for x in [-.23, .23]:
        for y in [-.14, .14]:
            box('BASE_FloorPad', (x, y, .006), (.085, .075, .012), dark, fixture, .005)
    box('BASE_LowerPlinth', (0, 0, .037), (.60, .40, .05), dark, fixture, .018)
    box('BASE_SatinReveal', (0, 0, .064), (.575, .375, .010), grey, fixture, .004)
    box('BASE_UpperDeck', (0, 0, .078), (.566, .366, .020), white, fixture, .008)
    for x in [-.255, .255]:
        box('FRAME_Upright', (x, .098, .693), (.025, .035, 1.25), dark, fixture, .006)
        box('FRAME_BaseSocket', (x, .098, .108), (.055, .062, .046), grey, fixture, .007)
    box('TRAY_LowerShelf', (0, -.015, .398), (.54, .32, .025), dark, fixture, .008)
    box('TRAY_Inset', (0, -.016, .412), (.492, .273, .006), grey, fixture, .003)
    box('TRAY_FrontLip', (0, -.169, .416), (.52, .012, .028), dark, fixture, .004)
    box('PRICE_CardHolder', (0, -.152, .453), (.158, .019, .078), grey, fixture, .005)
    box('PRICE_BlankCard', (0, -.163, .453), (.143, .004, .064), white, fixture, .002)
    box('HEADER_Frame', (0, .082, 1.3075), (.58, .055, .185), dark, fixture, .012)
    box('HEADER_BlankFront', (0, .051, 1.3075), (.547, .008, .151), white, fixture, .006)
    box('HEADER_BlankBack', (0, .113, 1.3075), (.547, .008, .151), white, fixture, .006)
    colors = [dark, white, grey, white, grey, dark]
    index = 0
    for top in [1.159, .819]:
        rail_z = top - .029
        box('RAIL_HorizontalSupport', (0, .098, rail_z), (.51, .03, .028), grey, fixture, .005)
        for cx in [-.187, 0, .187]:
            index += 1
            box(f'HOOK_{index:02d}_Socket', (cx, .078, rail_z), (.036, .025, .043), dark, fixture, .005)
            points = [(cx, .081, rail_z), (cx, .025, rail_z), (cx, -.035, rail_z),
                      (cx, -.085, rail_z), (cx, -.12, rail_z + .004)]
            for k in range(1, 9):
                a = math.pi * k / 16
                points.append((cx, -.12 - .038 * math.sin(a), rail_z + .004 + .038 * (1 - math.cos(a))))
            sweep(f'HOOK_{index:02d}_CurvedJ', points, .006, grey, fixture)
            box(f'HOOK_{index:02d}_BandSaddle', (cx, -.125, top - .010), (.034, .026, .011), dark, fixture, .004)
            headphone(index, cx, top, colors[index - 1], dark, grey, root)


def export(path):
    """Export evaluated saved geometry, merging by material without editing the source."""
    source_root = bpy.data.objects[ROOT]
    temporary = []
    export_root = empty(ROOT + '_Export')
    for key in source_root.keys():
        export_root[key] = source_root[key]
    export_root['headphone_count'] = 6
    temporary.append(export_root)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    buckets = {}
    try:
        for obj in source_root.children_recursive:
            if obj.type != 'MESH':
                continue
            evaluated = obj.evaluated_get(depsgraph)
            data = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
            copy = bpy.data.objects.new('EXPORT_' + obj.name, data)
            bpy.context.scene.collection.objects.link(copy)
            data.transform(obj.matrix_world)
            copy.parent = export_root
            temporary.append(copy)
            buckets.setdefault(obj.data.materials[0].name, []).append(copy)
        for name, objects in buckets.items():
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            merged = bpy.context.object
            merged.name = 'MESH_' + name.replace(' ', '')
        source_root.name = ROOT + '_Source'
        export_root.name = ROOT
        bpy.ops.object.select_all(action='DESELECT')
        export_root.select_set(True)
        for obj in export_root.children_recursive:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True, export_cameras=False,
                                  export_lights=False, export_materials='EXPORT')
    finally:
        for obj in reversed(temporary):
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except ReferenceError:
                pass
        source_root.name = ROOT


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .25, .28, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    floor = material('STUDIO_Floor', (.25, .28, .31), 0, .8)
    box('STUDIO_Floor', (0, 0, -.026), (200, 200, .05), floor, None, 0)
    for name, loc, power, size in [('Key', (-3, -4, 5), 650, 3), ('Fill', (3, -2, 2.8), 450, 2.5), ('Rim', (1, 3, 4), 900, 2.5)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy = power
        obj.data.shape = 'DISK'
        obj.data.size = size
        aim(obj, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 1.78
    scene.camera.location = (2.1, -4, 2.15)
    aim(scene.camera, TARGET)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    for name, position in [('hero', (2.1, -4, 2.15)), ('front', (0, -4, 1.10)),
                           ('side', (4, -.10, 1.10)), ('3q', (-2.5, -4, 1.9))]:
        if '--view' in sys.argv and name != sys.argv[sys.argv.index('--view') + 1]:
            continue
        scene.camera.location = position
        aim(scene.camera, TARGET)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.image_settings.quality = 90
        bpy.data.images['Render Result'].save_render(str(HERE / 'previews' / (name + '.webp')), scene=scene)
        scene.render.image_settings.file_format = 'PNG'


def main():
    for directory in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / directory).mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        root = empty(ROOT)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['origin'] = 'Floor centre'
        root['scope'] = 'Static original unbranded S13 headphone display fixture'
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
