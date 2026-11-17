"""Original S04 P2 counter display. Blender 5.2.3; no external assets.

Editable sources and source-only export follow self-checkout-machine.
The delivery export batches original geometry into three material meshes.
"""
from pathlib import Path
import json
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'mosquito-patch-pack'
ROOT = 'ASSET_MosquitoPatchPack'
TARGET = (0, 0, .17)
SAGE = (.32, .47, .43)
PAPER = (.94, .925, .865)
PATCH = (.76, .68, .49)


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                 for v in rgb) + (1,)


def material(name, roughness, glass=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    shader = mat.node_tree.nodes['Principled BSDF']
    if glass:
        shader.inputs['Base Color'].default_value = (.93, .98, 1, 1)
        shader.inputs['Alpha'].default_value = .13
        shader.inputs['IOR'].default_value = 1.46
        mat.surface_render_method = 'DITHERED'
    colors = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    colors.layer_name = 'Color'
    mat.node_tree.links.new(colors.outputs['Color'], shader.inputs['Base Color'])
    shader.inputs['Roughness'].default_value = roughness
    return mat


def colorize(obj, rgb):
    attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    for item in attr.data:
        item.color = linear(rgb)


def mesh_object(name, vertices, faces, mat, rgb, parent):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    mesh.materials.append(mat)
    colorize(obj, rgb)
    return obj


def box(name, location, dimensions, mat, rgb, parent, bevel=.0015):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name, obj.dimensions = name, dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent, obj.location = parent, location
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width, mod.segments = min(bevel, min(dimensions) * .23), 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    colorize(obj, rgb)
    return obj


def outline(width, height, radius):
    return [(cx + radius * math.cos(angle + i * math.pi / 6),
             cz + radius * math.sin(angle + i * math.pi / 6))
            for cx, cz, angle in [(width / 2 - radius, radius, -math.pi / 2),
                                  (width / 2 - radius, height - radius, 0),
                                  (-width / 2 + radius, height - radius, math.pi / 2),
                                  (-width / 2 + radius, radius, math.pi)]
            for i in range(4)]


def formed_panel(name, width, height, z, layers, mat, rgb, parent):
    vertices = []
    for inset, depth in layers:
        vertices.extend((x, depth, zz + z + inset)
                        for x, zz in outline(width - 2 * inset, height - 2 * inset,
                                             max(.001, .004 - inset * .25)))
    n = 16
    faces = [tuple(reversed(range(n)))]
    for ring in range(len(layers) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((ring * n + i, ring * n + j,
                          (ring + 1) * n + j, (ring + 1) * n + i))
    faces.append(tuple((len(layers) - 1) * n + i for i in range(n)))
    return mesh_object(name, vertices, faces, mat, rgb, parent)


def pack(name, location, scale, tier, root, paper, coating, glass, tilt=-8):
    parent = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(parent)
    parent.parent, parent.location = root, location
    parent.rotation_euler.x = math.radians(tilt)
    parent['kind'], parent['tier'] = 'flat six-patch blister pack', tier
    parent['pack_scale'], parent['patch_count'] = scale, 6
    # A rounded blank paper card, with a single shallow sealed clear window.
    formed_panel(name + '_BlankCard', .100 * scale, .140 * scale, 0,
                 [(0, .0006 * scale), (0, -.0006 * scale)], paper, PAPER, parent)
    formed_panel(name + '_ClearWindow', .078 * scale, .103 * scale, .014 * scale,
                 [(0, -.0008 * scale), (0, -.0012 * scale),
                  (.0025 * scale, -.0043 * scale)], glass, (1, 1, 1), parent)
    for row in range(3):
        for col in range(2):
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.0115 * scale,
                                               depth=.0011 * scale)
            obj = bpy.context.object
            obj.name = f'{name}_Patch_R{row + 1}_C{col + 1}'
            obj.parent = parent
            obj.location = ((col - .5) * .034 * scale, -.0020 * scale,
                            (.033 + row * .0315) * scale)
            obj.rotation_euler.x = math.pi / 2
            obj.data.materials.append(coating)
            for poly in obj.data.polygons:
                poly.use_smooth = len(poly.vertices) == 4
            colorize(obj, PATCH)
    return parent


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'], root['front_axis'] = 'metres', 'Blender -Y / glTF +Z'
    root['scope'] = 'S04 P2 original blank mosquito-patch counter display'
    coating = material('Sage polymer and round patches', .43)
    paper = material('Blank ivory card', .72)
    glass = material('Clear formed PET', .14, glass=True)
    box('BASE_RoundedPlinth', (0, 0, .010), (.50, .30, .020), coating, SAGE, root, .006)
    box('BASE_InsetDeck', (0, -.004, .023), (.474, .274, .006), coating, (.49, .61, .55), root)
    for tier, y, top in [(1, -.079, .026), (2, .027, .091)]:
        if tier == 2:
            box('TIER_2_Riser', (0, .056, .0545), (.464, .145, .061), coating, SAGE, root)
            box('TIER_2_Deck', (0, .056, .087), (.466, .148, .008), coating, (.49, .61, .55), root)
        box(f'TIER_{tier}_FrontLip', (0, y - .021, top + .006),
            (.466, .005, .015), coating, SAGE, root)
        box(f'TIER_{tier}_BlankInset', (0, y - .0238, top + .006),
            (.422, .0008, .007), paper, PAPER, root, .0001)
        for divider in range(5):
            x = -.226 + divider * .113
            box(f'TIER_{tier}_Divider_{divider}', (x, y + .009, top + .008),
                (.003, .052, .016), coating, SAGE, root)
        for column in range(4):
            x = (column - 1.5) * .113
            box(f'TIER_{tier}_StockStep_{column + 1}', (x, y + .026, top + .00275),
                (.101, .026, .0055), coating, (.49, .61, .55), root, 0)
            for stock in range(2):
                pack(f'PACK_T{tier}_C{column + 1}_S{stock + 1}',
                     (x, y + stock * .013, top + stock * .0055), 1, tier,
                     root, paper, coating, glass)
    # The enlarged back pack acts as the display header, on a visible short cradle.
    box('HERO_BackSupport', (0, .127, .133), (.035, .012, .218), coating, SAGE, root)
    box('HERO_Cradle', (0, .103, .151), (.152, .034, .006), coating, SAGE, root)
    pack('HERO_Pack', (0, .108, .154), 1.4, 3, root, paper, coating, glass, tilt=0)
    bpy.context.view_layer.update()
    return root


def export(path):
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    parts = sorted((o for o in root.children_recursive if o.type == 'MESH'), key=lambda o: o.name)
    materials = sorted({m for o in parts for m in o.data.materials}, key=lambda m: m.name)
    batches = []
    for mat in materials:
        vertices, faces, smooth, colors = [], [], [], []
        for obj in parts:
            if mat not in list(obj.data.materials):
                continue
            attr = obj.data.color_attributes['Color']
            offset = len(vertices)
            vertices.extend(tuple(obj.matrix_world @ v.co) for v in obj.data.vertices)
            for poly in obj.data.polygons:
                faces.append(tuple(offset + i for i in poly.vertices))
                smooth.append(poly.use_smooth)
                colors.append([tuple(attr.data[i].color) for i in poly.loop_indices])
        mesh = bpy.data.meshes.new('Delivery ' + mat.name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.materials.append(mat)
        obj = bpy.data.objects.new('BATCH_' + mat.name.replace(' ', ''), mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = root
        batches.append(obj)
        attr = mesh.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for poly, use_smooth, rgba in zip(mesh.polygons, smooth, colors):
            poly.use_smooth = use_smooth
            for index, color in zip(poly.loop_indices, rgba):
                attr.data[index].color = color
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for obj in batches:
        obj.select_set(True)
    try:
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in batches:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.meshes.remove(mesh)


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Slate studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.10, .14, .18, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
    for name, location, power, size in [('Key', (-1, -1.4, 1.7), 95, .9),
                                        ('Fill', (1.2, -.5, .7), 50, .8),
                                        ('Rim', (.3, .8, 1.1), 90, .7)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy, obj.data.size = power, size
        aim(obj, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type, scene.camera.data.ortho_scale = 'ORTHO', .65
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.seed = 48, 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    for name, location in [('hero', (.65, -1.3, .66)), ('front', (0, -1.5, .24)),
                           ('side', (1.5, 0, .30)), ('3q', (-.7, -1.3, .73))]:
        scene.camera.location = location
        aim(scene.camera, TARGET)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for folder in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / folder).mkdir(exist_ok=True)
    assert bpy.app.version[:3] == (5, 2, 3), bpy.app.version_string
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
