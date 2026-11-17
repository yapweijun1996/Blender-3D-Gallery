"""Original deterministic S05/S12 health display, Blender 5.2.3, metres.

The editable source and export-source path follow self-checkout-machine.
Delivery geometry is batched by three shared vertex-colour materials.
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'medicine-health-box-set'
ROOT = 'ASSET_MedicineHealthBoxSet'
SHELF_TOPS = (.175, .435, .695, .955, 1.215)
TARGET = (0, 0, .85)
SEGMENTS = 24
IVORY = (.88, .89, .85)
PAPER = (.94, .935, .90)
TEAL = (.23, .36, .37)
BANDS = [(.40, .58, .54), (.48, .60, .68), (.73, .61, .42)]


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


def colorize(obj, colors):
    attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    for poly in obj.data.polygons:
        rgba = linear(colors(poly) if callable(colors) else colors)
        for index in poly.loop_indices:
            attr.data[index].color = rgba


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


def box(name, location, dimensions, mat, rgb, parent, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name, obj.dimensions, obj.parent = name, dimensions, parent
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width, mod.segments = min(bevel, min(dimensions) * .24), 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    colorize(obj, rgb)
    return obj


def anchor(name, location, kind, tier, root):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.location, obj.parent = location, root
    obj['kind'], obj['tier'] = kind, tier
    return obj


def carton(name, location, dimensions, tier, band, root, paper):
    parent = anchor(name, location, 'plain carton', tier, root)
    width, depth, height = dimensions
    clip = .0012
    outline = [(-width / 2 + clip, -depth / 2), (width / 2 - clip, -depth / 2),
               (width / 2, -depth / 2 + clip), (width / 2, depth / 2 - clip),
               (width / 2 - clip, depth / 2), (-width / 2 + clip, depth / 2),
               (-width / 2, depth / 2 - clip), (-width / 2, -depth / 2 + clip)]
    rings = [(0, .97), (.001, 1), (height * .31, 1), (height * .52, 1),
             (height - .001, 1), (height, .97)]
    vertices = [(x * scale, y * scale, z) for z, scale in rings for x, y in outline]
    faces = []
    for ring in range(len(rings) - 1):
        for i in range(8):
            j = (i + 1) % 8
            faces.append((ring * 8 + i, ring * 8 + j, (ring + 1) * 8 + j, (ring + 1) * 8 + i))
    faces.append(tuple(reversed(range(8))))
    # Two folded top panels meet along a shallow physical seam; no printed marks.
    top = (len(rings) - 1) * 8
    seam = len(vertices)
    vertices.extend([(0, -depth * .485, height - .0005),
                     (0, depth * .485, height - .0005)])
    last = (len(rings) - 2) * 8
    faces[last] = (last, last + 1, top + 1, seam, top)
    faces[last + 4] = (last + 4, last + 5, top + 5, seam + 1, top + 4)
    faces.extend([(top, seam, seam + 1, top + 5, top + 6, top + 7),
                  (seam, top + 1, top + 2, top + 3, top + 4, seam + 1)])
    mesh_object(name + '_FoldedBody', vertices, faces, paper,
                lambda p: band if 16 <= p.index < 24 else PAPER, parent)
    return parent


def lathe(name, profile, mat, rgb, parent):
    vertices = [(r * math.cos(i * math.tau / SEGMENTS),
                 r * math.sin(i * math.tau / SEGMENTS), z)
                for r, z in profile for i in range(SEGMENTS)]
    faces = []
    for ring in range(len(profile) - 1):
        for i in range(SEGMENTS):
            j = (i + 1) % SEGMENTS
            faces.append((ring * SEGMENTS + i, ring * SEGMENTS + j,
                          (ring + 1) * SEGMENTS + j, (ring + 1) * SEGMENTS + i))
    faces.extend([tuple(reversed(range(SEGMENTS))),
                  tuple((len(profile) - 1) * SEGMENTS + i for i in range(SEGMENTS))])
    obj = mesh_object(name, vertices, faces, mat, rgb, parent)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.index < (len(profile) - 1) * SEGMENTS
    return obj


def bottle(name, location, radius, height, tier, band, root, polymer):
    parent = anchor(name, location, 'plain supplement bottle', tier, root)
    body = [(radius * .90, 0), (radius, .003), (radius, height * .26),
            (radius, height * .58), (radius, height * .72),
            (radius * .90, height * .78), (radius * .65, height * .82),
            (radius * .65, height * .88)]
    lathe(name + '_Body', body, polymer,
          lambda p: band if p.index // SEGMENTS == 2 else PAPER, parent)
    cap_r = radius * .77
    cap = lathe(name + '_RibbedCap', [(cap_r * .96, height * .85),
                                    (cap_r, height * .87),
                                    (cap_r, height * .985),
                                    (cap_r * .92, height)], polymer, IVORY, parent)
    for vertex in cap.data.vertices:
        if vertex.index // SEGMENTS in (1, 2) and vertex.index % 2:
            vertex.co.x *= .965
            vertex.co.y *= .965
    lathe(name + '_TamperRing', [(cap_r * .90, height * .83),
                               (cap_r * .96, height * .835),
                               (cap_r * .96, height * .852)], polymer, IVORY, parent)
    return parent


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'], root['front_axis'] = 'metres', 'Blender -Y / glTF +Z'
    root['carton_count'], root['bottle_count'], root['tier_count'] = 20, 6, 5
    root['scope'] = 'S05/S12 P2 original blank medicine and health-supplement display'
    coating = material('Powdercoat', .18, .42)
    paper = material('Plain carton paper', 0, .72)
    polymer = material('Opaque bottle polymer', 0, .35)
    # The plinth fixes the exact footprint, centred on the floor origin.
    box('STAND_Plinth', (0, 0, .055), (.60, .35, .11), coating, TEAL, root, .012)
    box('STAND_InsetBase', (0, 0, .117), (.555, .306, .024), coating, IVORY, root)
    for x in (-.275, .275):
        box(f'STAND_RearUpright_{x}', (x, .127, .894), (.026, .032, 1.552), coating, TEAL, root)
        for tier, top in enumerate(SHELF_TOPS, 1):
            box(f'STAND_SideSupport_T{tier}_{x}', (x, -.006, top - .020),
                (.020, .286, .032), coating, TEAL, root)
    box('STAND_BackPanel', (0, .142, .807), (.536, .014, 1.36), coating, IVORY, root)
    for tier, top in enumerate(SHELF_TOPS, 1):
        box(f'SHELF_T{tier}', (0, -.005, top - .010), (.56, .300, .020), coating, IVORY, root)
        box(f'RAIL_BlankFront_T{tier}', (0, -.155, top - .004),
            (.56, .012, .030), coating, TEAL, root, .002)
        box(f'RAIL_PlainInset_T{tier}', (0, -.1615, top - .004),
            (.520, .002, .014), coating, IVORY, root, .0004)
    box('HEADER_Frame', (0, .115, 1.59), (.58, .045, .22), coating, TEAL, root, .009)
    box('HEADER_BlankPanel', (0, .0905, 1.59), (.536, .004, .174), coating, IVORY, root, .005)
    # All items stand in a single visible row, with at least 5 mm side clearance.
    for tier, top in enumerate(SHELF_TOPS, 1):
        for col in range(4):
            width = [.072, .078, .065, .075][(col + tier) % 4]
            height = [.174, .201, .220, .186][(col + 2 * tier) % 4]
            depth = [.076, .091, .083][(col + tier) % 3]
            if tier <= 2:
                x, width = -.210 + col * .140, width * 1.16
            else:
                x = -.216 + col * .094
            carton(f'CARTON_T{tier}_C{col + 1}', (x, -.065, top),
                   (width, depth, height), tier, BANDS[(col + tier) % 3], root, paper)
        if tier >= 3:
            for col in range(2):
                height = [.163, .192, .177][(tier + col) % 3]
                radius = [.025, .027][col]
                bottle(f'BOTTLE_T{tier}_C{col + 1}', (.157 + col * .069, -.068, top),
                       radius, height, tier, BANDS[(tier + col + 1) % 3], root, polymer)
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
            attr = obj.data.color_attributes['Color']
            if mat not in list(obj.data.materials):
                continue
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
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    for name, location, power, size in [
        ('Key', (-3, -4, 4), 650, 3), ('Fill', (3, -2, 2.8), 350, 2.5),
        ('Rim', (1, 3, 3), 600, 2)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.object
        light.name = 'STUDIO_' + name
        light.data.energy, light.data.size = power, size
        aim(light, TARGET)
    bpy.ops.object.camera_add(location=(1.7, -3.5, 1.9))
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type, scene.camera.data.ortho_scale = 'ORTHO', 2.05
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
    for name, location in [('hero', (1.7, -3.5, 1.9)), ('front', (0, -4, .85)),
                           ('side', (4, 0, .85)), ('3q', (-2.2, -3.5, 2.1))]:
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
