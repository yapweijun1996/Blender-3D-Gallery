"""Original frameless storefront; deterministic Blender 5.2.3, no external assets."""
from pathlib import Path
import json
import math
import struct
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'glass-storefront-module'
ROOT = 'ASSET_GlassStorefrontModule'
TARGET = Vector((0, 0, 1.8))


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)


def material(name, rgb, metal, rough, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    rgba = linear(rgb) + (alpha,)
    p.inputs['Base Color'].default_value = rgba
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    p.inputs['Alpha'].default_value = alpha
    p.inputs['Transmission Weight'].default_value = 0
    m.diffuse_color = rgba
    m.use_backface_culling = True
    if alpha < 1:
        m.surface_render_method = 'DITHERED'
    return m


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    return o


def finish(o, name, mat, parent, bevel=0):
    o.name = name
    o.parent = parent
    if mat:
        o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Soft polished edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod = o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return o


def box(name, loc, dims, mat, parent, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, mat, parent, bevel)


def rod(name, a, b, radius, mat, parent):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius,
                                      depth=(b - a).length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    finish(o, name, mat, parent, .001)
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return o


def glass_panel(name, loc, dims, mat, parent):
    """One closed slab with a 5 mm polished rim; COLOR_0 shares one material."""
    w, d, h = dims
    bevel, rim = .002, .005
    vertices, faces, colors = [], [], []
    face_color = linear((.78, .92, .88)) + (.13,)
    rim_color = linear((.36, .64, .55)) + (.36,)
    edge_color = linear((.26, .53, .45)) + (.58,)
    rings = [(rim, -d / 2), (bevel, -d / 2), (0, -d / 2 + bevel),
             (0, d / 2 - bevel), (bevel, d / 2), (rim, d / 2)]
    for inset, y in rings:
        vertices.extend((sx * (w / 2 - inset), y, sz * (h / 2 - inset))
                        for sx, sz in [(-1, -1), (1, -1), (1, 1), (-1, 1)])
    faces.append((0, 1, 2, 3))
    colors.append(face_color)
    for ring in range(5):
        for corner in range(4):
            nxt = (corner + 1) % 4
            faces.append((4 * ring + corner, 4 * (ring + 1) + corner,
                          4 * (ring + 1) + nxt, 4 * ring + nxt))
            colors.append(rim_color if ring in [0, 4] else edge_color)
    faces.append((23, 22, 21, 20))
    colors.append(face_color)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    tint = mesh.color_attributes.new(name='GlazingTint', type='FLOAT_COLOR', domain='CORNER')
    for polygon, color in zip(mesh.polygons, colors):
        for loop in polygon.loop_indices:
            tint.data[loop].color = color
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return finish(o, name, mat, parent)


def build_variant(variant, glass, metal):
    root = empty(ROOT if variant == 'Closed' else ROOT + '_Open')
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['variant'] = variant
    root['repeat_pitch_m'] = 3.0
    root['collision_scene'] = 2 if variant == 'Closed' else 3
    root['opening_width_m'] = 0.0 if variant == 'Closed' else 1.0
    for side, x in [('Left', -1.0), ('Right', 1.0)]:
        glass_panel('GLASS_FixedPane_' + side + '_' + variant, (x, 0, 1.703),
                    (1.0, .012, 3.354), glass, root)
        # The channel stops at the aperture, leaving a completely flush passage.
        box('CHANNEL_Floor_' + side + '_' + variant, (x, 0, .013),
            (1.0, .036, .026), metal, root, .002)
    glass_panel('GLASS_OverdoorTransom_' + variant, (0, 0, 2.83),
                (1.0, .012, 1.10), glass, root)
    box('HEADER_BlankSignBand_' + variant, (0, 0, 3.49),
        (3.0, .12, .22), metal, root, .008)
    if variant == 'Closed':
        for side, sign in [('Left', -1), ('Right', 1)]:
            glass_panel('DOOR_FramelessLeaf_' + side, (sign * .2515, 0, 1.139),
                        (.491, .012, 2.25), glass, root)
            # Coaxial pins visibly join each door patch to a floor bearing and
            # a fixed transom receiver. All hardware fits inside the 120 mm depth.
            for z, level in [(.060, 'Bottom'), (2.216, 'Top')]:
                box('PATCH_' + side + '_' + level, (sign * .455, 0, z),
                    (.084, .034, .084), metal, root, .004)
            box('PIVOT_FloorBearing_' + side, (sign * .46, 0, .006),
                (.07, .054, .012), metal, root, .002)
            rod('PIVOT_BottomSpindle_' + side, (sign * .46, 0, .010),
                (sign * .46, 0, .036), .009, metal, root)
            rod('PIVOT_TopSpindle_' + side, (sign * .46, 0, 2.244),
                (sign * .46, 0, 2.300), .009, metal, root)
            box('PIVOT_TransomReceiver_' + side, (sign * .455, 0, 2.305),
                (.084, .036, .05), metal, root, .003)
            for face, y in [('Front', -.046), ('Rear', .046)]:
                rod('HANDLE_' + side + '_' + face, (sign * .085, y, .99),
                    (sign * .085, y, 1.41), .014, metal, root)
                for z in [1.02, 1.38]:
                    rod('HANDLE_Mount_' + side + '_' + face,
                        (sign * .085, 0, z), (sign * .085, y, z), .009, metal, root)
    return root


def build_colliders():
    closed = box('collider_box', (0, 0, 1.8), (3, .12, 3.6), None, None)
    parts = [box('collision_open_' + side, (x, 0, 1.8), (1, .12, 3.6), None, None)
             for side, x in [('Left', -1), ('Right', 1)]]
    parts.append(box('collision_open_Lintel', (0, 0, 2.94), (1, .12, 1.32), None, None))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    opened = bpy.context.object
    opened.name = 'collider_box_Open'
    for o in [closed, opened]:
        o['hidden'] = True
        o['role'] = 'collision_only'
        o.display_type = 'WIRE'
        o.hide_render = True
        o.hide_set(True)
    return [closed, opened]


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    floor = material('STUDIO_WarmFloor', (.82, .79, .73), 0, .78)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.002))
    bpy.context.object.name = 'STUDIO_Floor'
    bpy.context.object.data.materials.append(floor)
    for name, loc, power, size in [('Key', (-3, -5, 7), 1100, 4),
                                    ('Fill', (4, -2, 4), 800, 3),
                                    ('Rim', (1, 3, 6), 1400, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy, o.data.size = power, size
        aim(o, TARGET)
    s.world = bpy.data.worlds.new('STUDIO_WarmWorld')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.30, .34, .37, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 4.5
    s.render.engine = 'CYCLES'
    s.cycles.samples = 40
    s.cycles.seed = 0
    s.cycles.use_animated_seed = False
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 768
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def show_variant(variant):
    for suffix, root_name in [('Closed', ROOT), ('Open', ROOT + '_Open')]:
        root = bpy.data.objects[root_name]
        for o in [root] + list(root.children_recursive):
            o.hide_render = suffix != variant
            o.hide_set(suffix != variant)


def render_views():
    s = bpy.context.scene
    selected_views = next((arg.split('=', 1)[1].split(',') for arg in sys.argv if arg.startswith('--views=')), None)
    for variant in ['Closed', 'Open']:
        show_variant(variant)
        for view, delta in [('hero', (4, -8, 2.3)), ('front', (0, -9, .25)),
                            ('side', (9, -.8, .5)), ('3q', (-4.5, -8, 1.5))]:
            if selected_views and view not in selected_views:
                continue
            s.camera.location = TARGET + Vector(delta)
            aim(s.camera, TARGET)
            filename = view if variant == 'Closed' else 'open-' + view
            s.render.filepath = str(HERE / 'previews' / (filename + '.png'))
            bpy.ops.render.render(write_still=True)
    show_variant('Closed')


def export(path):
    # Merge evaluated copies only: the saved source keeps named, editable fittings.
    deps = bpy.context.evaluated_depsgraph_get()
    temporary = []
    roots = []
    renamed = []
    for variant, name in [('Closed', ROOT), ('Open', ROOT + '_Open')]:
        source = bpy.data.objects[name]
        source.name = name + '__Source'
        renamed.append((source, name))
        root = empty(name)
        for key in source.keys():
            root[key] = source[key]
        roots.append(root)
        temporary.append(root)
        for prefix in ['GLASS', 'METAL']:
            copies = []
            for original in source.children_recursive:
                if original.type != 'MESH':
                    continue
                is_glass = original.data.materials[0].name == 'Glass_PaleAqua_Alpha'
                if is_glass != (prefix == 'GLASS'):
                    continue
                evaluated = original.evaluated_get(deps)
                mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
                o = bpy.data.objects.new('EXPORT_' + original.name, mesh)
                bpy.context.scene.collection.objects.link(o)
                o.matrix_world = original.matrix_world.copy()
                copies.append(o)
            bpy.ops.object.select_all(action='DESELECT')
            for o in copies:
                o.select_set(True)
            bpy.context.view_layer.objects.active = copies[0]
            names = [o.name.removeprefix('EXPORT_') for o in copies]
            bpy.ops.object.join()
            o = bpy.context.object
            o.name = prefix + ('_FramelessPanes' if prefix == 'GLASS' else '_HeaderChannelFittings') + '_' + variant
            # Bake world positions around the shared floor-centre root.
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            o.parent = root
            o['source_parts'] = names
            temporary.append(o)
    colliders = [bpy.data.objects['collider_box'], bpy.data.objects['collider_box_Open']]
    bpy.ops.object.select_all(action='DESELECT')
    for o in temporary + colliders:
        o.hide_set(False)
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_extras=True,
        export_texcoords=False, export_cameras=False, export_lights=False,
        export_vertex_color='ACTIVE')
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    by_name = {n['name']: i for i, n in enumerate(doc['nodes'])}
    # Core glTF has no node visibility flag. Collision meshes live exclusively in
    # opt-in scenes, so stock gallery loaders never render their default material.
    doc['scenes'] = [
        {'name': 'Closed', 'nodes': [by_name[ROOT]]},
        {'name': 'Open', 'nodes': [by_name[ROOT + '_Open']]},
        {'name': 'COLLISION_ONLY_Closed', 'nodes': [by_name['collider_box']]},
        {'name': 'COLLISION_ONLY_Open', 'nodes': [by_name['collider_box_Open']]},
    ]
    doc['scene'] = 0
    text = json.dumps(doc, separators=(',', ':')).encode()
    text += b' ' * (-len(text) % 4)
    tail = raw[20 + size:]
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(text) + len(tail)) +
                     struct.pack('<I4s', len(text), b'JSON') + text + tail)
    for o in temporary:
        bpy.data.objects.remove(o, do_unlink=True)
    for o, name in renamed:
        o.name = name
    for o in colliders:
        o.hide_set(True)


def main():
    for name in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        glass = material('Glass_PaleAqua_Alpha', (1, 1, 1), 0, .055, .13)
        tint = glass.node_tree.nodes.new('ShaderNodeVertexColor')
        tint.layer_name = 'GlazingTint'
        shader = glass.node_tree.nodes['Principled BSDF']
        glass.node_tree.links.new(tint.outputs['Color'], shader.inputs['Base Color'])
        glass.node_tree.links.new(tint.outputs['Alpha'], shader.inputs['Alpha'])
        metal = material('Metal_NeutralSatin', (.57, .60, .58), .72, .23)
        build_variant('Closed', glass, metal)
        build_variant('Open', glass, metal)
        build_colliders()
        studio()
        show_variant('Closed')
        s.camera.location = TARGET + Vector((4, -8, 2.3))
        aim(s.camera, TARGET)
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
