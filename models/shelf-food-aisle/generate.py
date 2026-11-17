"""Original five-level food gondola. Blender 5.2.3; metres; no external assets.

Source/export workflow follows self-checkout-machine. Export batches editable
parts into three shared vertex-colour material meshes; source parts stay separate.
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'shelf-food-aisle'
ROOT = 'ASSET_ShelfFoodAisle'
SHELF_TOPS = (.16, .46, .76, 1.06, 1.36)
TARGET = (0, 0, .90)
IVORY = (.88, .89, .85)
TEAL = (.23, .36, .37)
STEEL = (.70, .74, .74)
COLORS = [(.69, .42, .30), (.72, .61, .39), (.41, .57, .48),
          (.47, .58, .64), (.79, .72, .56)]


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                 for v in rgb) + (1,)


def material(name, metal, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    shader = mat.node_tree.nodes['Principled BSDF']
    colors = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    colors.layer_name = 'Color'
    mat.node_tree.links.new(colors.outputs['Color'], shader.inputs['Base Color'])
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = roughness
    return mat


def colorize(obj, rgb):
    attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    for poly in obj.data.polygons:
        color = linear(rgb(poly) if callable(rgb) else rgb)
        for index in poly.loop_indices:
            attr.data[index].color = color


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


def box(name, location, dimensions, mat, rgb, parent, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name, obj.dimensions, obj.parent = name, dimensions, parent
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Manufactured edge', 'BEVEL')
        mod.width, mod.segments = min(bevel, min(dimensions) * .24), 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    colorize(obj, rgb)
    return obj


def anchor(name, location, kind, tier, side, root):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location, obj.parent = location, root
    obj['kind'], obj['tier'], obj['side'] = kind, tier, side
    return obj


def lathe(name, profile, mat, rgb, parent):
    segments = 12
    vertices = [(r * math.cos(i * math.tau / segments),
                 r * math.sin(i * math.tau / segments), z)
                for r, z in profile for i in range(segments)]
    faces = []
    for ring in range(len(profile) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring * segments + i, ring * segments + j,
                          (ring + 1) * segments + j, (ring + 1) * segments + i))
    faces.extend([tuple(reversed(range(segments))),
                  tuple((len(profile) - 1) * segments + i for i in range(segments))])
    obj = mesh_object(name, vertices, faces, mat, rgb, parent)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.index < (len(profile) - 1) * segments
    return obj


def carton(parent, color, paper, width, height):
    box(parent.name + '_Body', (0, 0, height / 2), (width, .125, height),
        paper, color, parent, .002)
    # A shallow folded top flap is physical geometry, with no printed graphics.
    box(parent.name + '_TopFold', (0, 0, height + .0006), (width * .88, .116, .0012),
        paper, color, parent, .0002)


def can(parent, color, coating, metal, height):
    r = .044
    lathe(parent.name + '_Body', [(r * .94, 0), (r, .003),
                                (r, height - .003), (r * .94, height)],
          coating, color, parent)
    for label, z in [('Bottom', 0), ('Top', height - .007)]:
        # Closed rolled-seam profile with an inset lid; no external textures.
        lathe(parent.name + '_' + label + 'Seam',
              [(r * .96, z), (r * 1.025, z + .0015),
               (r * 1.025, z + .0055), (r * .97, z + .007),
               (r * .89, z + .005)], metal, STEEL, parent)


def bag(parent, color, paper, width, height):
    # Elliptical rings form a pillow pack with narrow top and bottom heat seals.
    segments = 8
    rings = [(0, .88, .013), (.010, .95, .020),
             (height * .23, 1, .050), (height * .65, .96, .053),
             (height - .018, .84, .019), (height, .84, .010)]
    vertices = [(width * .5 * w * math.cos(i * math.tau / segments),
                 depth * math.sin(i * math.tau / segments), z)
                for z, w, depth in rings for i in range(segments)]
    faces = []
    for ring in range(len(rings) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring * segments + i, ring * segments + j,
                          (ring + 1) * segments + j, (ring + 1) * segments + i))
    faces.extend([tuple(reversed(range(segments))),
                  tuple((len(rings) - 1) * segments + i for i in range(segments))])
    mesh_object(parent.name + '_Pillow', vertices, faces, paper, color, parent)
    for label, z in [('Bottom', .004), ('Top', height - .003)]:
        box(parent.name + '_' + label + 'Seal', (0, 0, z),
            (width * .90, .024, .006), paper, color, parent, .0005)


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'], root['front_axis'] = 'metres', 'Blender -Y / glTF +Z'
    root['scope'] = 'Static original five-level double-sided food gondola'
    coating = material('Powdercoat', .12, .43)
    paper = material('PlainPackaging', 0, .67)
    metal = material('SatinMetal', .65, .34)
    box('BASE_Plinth', (0, 0, .06), (1.2, .5, .12), coating, TEAL, root, .009)
    box('BACK_CentralPanel', (0, 0, .925), (1.106, .024, 1.61),
        coating, IVORY, root)
    for x in (-.557, .557):
        box('POST_' + str(x), (x, 0, .96), (.034, .054, 1.68),
            coating, TEAL, root)
        # Recess-coloured attachment slots are small closed solids on both faces.
        for side in (-1, 1):
            for index in range(20):
                box(f'SLOT_{x}_{side}_{index}', (x, side * .0276, .23 + index * .073),
                    (.007, .0012, .023), coating, (.14, .22, .23), root, 0)
    for side in (-1, 1):
        for tier, top in enumerate(SHELF_TOPS, 1):
            box(f'SHELF_S{side}_T{tier}', (0, side * .127, top - .009),
                (1.14, .212, .018), coating, IVORY, root)
            box(f'RAIL_S{side}_T{tier}', (0, side * .239, top - .002),
                (1.14, .016, .036), coating, TEAL, root)
            box(f'PRICE_Blank_S{side}_T{tier}', (0, side * .2475, top - .002),
                (1.10, .001, .019), coating, IVORY, root, .0002)
            for x in (-.53, .53):
                # Cantilever brackets visibly connect every deck to its upright.
                box(f'BRACKET_{side}_{tier}_{x}', (x, side * .123, top - .026),
                    (.018, .205, .025), coating, TEAL, root)
            for col, kind in enumerate(['box', 'box', 'can', 'can', 'bag', 'bag', 'box']):
                item = anchor(f'ITEM_S{side}_T{tier}_C{col + 1}',
                              (-.46 + col * .1533, side * .132, top),
                              kind, tier, side, root)
                color = COLORS[(tier + col + (side == 1)) % len(COLORS)]
                if kind == 'box':
                    carton(item, color, paper, [.104, .115, .108][(tier + col) % 3],
                           [.212, .238, .258][(tier + col) % 3])
                elif kind == 'can':
                    can(item, color, coating, metal, [.156, .182, .203][tier % 3])
                else:
                    bag(item, color, paper, .116, [.202, .222, .242][(tier + col) % 3])
    # End signs face the aisle ends (X), stay within the footprint, and are blank.
    for side in (-1, 1):
        box(f'ENDSIGN_Frame_{side}', (side * .585, 0, 1.69),
            (.028, .414, .22), coating, TEAL, root, .006)
        box(f'ENDSIGN_Blank_{side}', (side * .600 - side * .001, 0, 1.69),
            (.002, .372, .178), coating, IVORY, root, .0004)
        box(f'ENDSIGN_Support_{side}', (side * .557, 0, 1.57),
            (.034, .054, .10), coating, TEAL, root)
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
                assert obj.data.materials[poly.material_index] == mat
                faces.append(tuple(offset + i for i in poly.vertices))
                smooth.append(poly.use_smooth)
                colors.append([tuple(attr.data[i].color) for i in poly.loop_indices])
        mesh = bpy.data.meshes.new('Delivery ' + mat.name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.materials.append(mat)
        obj = bpy.data.objects.new('BATCH_' + mat.name, mesh)
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
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    for name, location, power, size in [
        ('Key', (-3, -4, 4), 650, 3), ('Fill', (3, -2, 2.8), 350, 2.5),
        ('Rim', (1, 3, 3), 600, 2)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.object
        light.name = 'STUDIO_' + name
        light.data.energy, light.data.size = power, size
        aim(light, TARGET)
    bpy.ops.object.camera_add(location=(2.4, -3.8, 2.2))
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type, scene.camera.data.ortho_scale = 'ORTHO', 2.20
    aim(scene.camera, TARGET)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.seed = 48, 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    for name, location in [('hero', (2.4, -3.8, 2.2)), ('front', (0, -4, .90)),
                           ('side', (4, 0, .90)), ('3q', (-2.4, 3.8, 2.2))]:
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
