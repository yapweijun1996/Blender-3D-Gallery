"""Original deterministic S02 soy-style bottle display. Blender 5.2.3, metres.

Editable source parts follow the self-checkout-machine template. The export
batches geometry into three shared material primitives for a web mall.
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'condiment-bottle-jar-set'
ROOT = 'ASSET_CondimentBottleJarSet'
SEGMENTS = 24
TARGET = (0, 0, .55)
# Keep full-size bottles and at least 70 mm of access below the next front rail.
SHELF_TOPS = (.095, .500, .820)
IVORY = (.81, .80, .74)
GRAPHITE = (.23, .28, .27)
CAP = (.29, .30, .27)
BANDS = [(.65, .39, .21), (.48, .56, .40), (.75, .65, .40)]


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def material(name, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nodes = mat.node_tree.nodes
    shader = nodes['Principled BSDF']
    colors = nodes.new('ShaderNodeVertexColor')
    colors.layer_name = 'Color'
    mat.node_tree.links.new(colors.outputs['Color'], shader.inputs['Base Color'])
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    return mat


def colorize(obj, colors):
    attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    for poly in obj.data.polygons:
        rgb = colors(poly) if callable(colors) else colors
        for index in poly.loop_indices:
            attr.data[index].color = linear(rgb)


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
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent = parent
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width, mod.segments = min(bevel, min(dimensions) * .24), 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    colorize(obj, rgb)
    return obj


def lathe(name, profile, mat, rgb, parent, closed=True):
    vertices = [(r * math.cos(2 * math.pi * i / SEGMENTS),
                 r * math.sin(2 * math.pi * i / SEGMENTS), z)
                for r, z in profile for i in range(SEGMENTS)]
    faces = []
    for ring in range(len(profile) - 1):
        for i in range(SEGMENTS):
            j = (i + 1) % SEGMENTS
            faces.append((ring * SEGMENTS + i, ring * SEGMENTS + j,
                          (ring + 1) * SEGMENTS + j, (ring + 1) * SEGMENTS + i))
    if closed:
        faces.extend([tuple(reversed(range(SEGMENTS))),
                      tuple((len(profile) - 1) * SEGMENTS + i for i in range(SEGMENTS))])
    obj = mesh_object(name, vertices, faces, mat, rgb, parent)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.index < (len(profile) - 1) * SEGMENTS
    return obj


def bottle(name, height, radius, location, tier, band, root, glass, matte):
    anchor = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(anchor)
    anchor.parent, anchor.location = root, location
    anchor['kind'], anchor['tier'] = 'soy-style bottle', tier
    # Closed low-cost shell: dark-filled amber appearance, no transmission pass.
    profile = [(radius * .83, 0), (radius * .96, height * .016),
               (radius, height * .04), (radius, height * .25),
               (radius, height * .51), (radius, height * .64),
               (radius * .94, height * .70), (radius * .66, height * .78),
               (radius * .38, height * .82), (radius * .37, height * .90),
               (radius * .41, height * .915)]
    body = lathe(name + '_Body', profile, glass,
                 lambda p: band if p.index // SEGMENTS == 3
                 else (.24, .115, .045) if p.index // SEGMENTS >= 8
                 else (.14, .073, .037), anchor)
    body['appearance'] = 'Opaque amber shell approximating dark soy liquid'
    # Flush band faces avoid overlapping shells and depth fighting in browsers.
    body.data.materials.append(matte)
    for polygon in body.data.polygons:
        if polygon.index // SEGMENTS == 3:
            polygon.material_index = 1
    body['blank_band'] = '24 flush material faces; no text or graphics'
    cap_r = radius * .45
    cap = lathe(name + '_Cap', [(cap_r * .94, height * .90),
                              (cap_r, height * .914),
                              (cap_r, height * .982),
                              (cap_r * .89, height)], matte, CAP, anchor)
    # Alternate shallow facets read as a plain ribbed grip at close range.
    for vertex in cap.data.vertices:
        ring = vertex.index // SEGMENTS
        if ring in (1, 2) and vertex.index % 2:
            vertex.co.x *= .97
            vertex.co.y *= .97
    return anchor


def build():
    root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(root)
    root['units'], root['front_axis'] = 'metres', 'Blender -Y / glTF +Z'
    root['bottle_count'], root['tier_count'] = 16, 3
    root['scope'] = 'S02 P2 original soy-style bottle display; no peanut-butter jars'
    glass = material('Dark filled amber', 0, .23)
    matte = material('Neutral caps and blank bands', 0, .53)
    metal = material('Powder-coated rack', .35, .38)
    # Four feet establish the exact floor-centred 0.90 x 0.35 m footprint.
    for x in (-.405, .405):
        for y in (-.1425, .1425):
            box(f'RACK_Foot_{x}_{y}', (x, y, .012), (.09, .065, .024), metal, GRAPHITE, root)
    for x in (-.416, .416):
        box(f'RACK_RearUpright_{x}', (x, .142, .547), (.028, .028, 1.046), metal, GRAPHITE, root)
        front_top = SHELF_TOPS[-1] + .045
        box(f'RACK_FrontUpright_{x}', (x, -.135, (front_top + .024) / 2),
            (.024, .024, front_top - .024), metal, GRAPHITE, root)
        for tier, top in enumerate(SHELF_TOPS, 1):
            box(f'RACK_SideSupport_T{tier}_{x}', (x, .005, top - .026),
                (.022, .284, .032), metal, GRAPHITE, root)
    for tier, top in enumerate(SHELF_TOPS, 1):
        box(f'RACK_Shelf_T{tier}', (0, 0, top - .012), (.86, .32, .024), matte, IVORY, root)
        box(f'RACK_BlankPriceRail_T{tier}', (0, -.166, top - .011),
            (.86, .018, .038), metal, GRAPHITE, root, .002)
        box(f'RACK_RearStop_T{tier}', (0, .151, top + .016),
            (.816, .012, .032), metal, GRAPHITE, root, .002)
    box('RACK_HeaderFrame', (0, .134, 1.036), (.9, .045, .128), metal, GRAPHITE, root, .008)
    box('RACK_BlankHeader', (0, .109, 1.036), (.846, .006, .078), matte, IVORY, root, .003)
    configurations = [(5, .30, .054, .16), (5, .22, .042, .16), (6, .12, .030, .138)]
    for tier, (count, height, radius, pitch) in enumerate(configurations, 1):
        for column in range(count):
            bottle(f'BOTTLE_T{tier}_C{column + 1:02d}', height, radius,
                   ((column - (count - 1) / 2) * pitch, -.035, SHELF_TOPS[tier - 1]),
                   tier, BANDS[tier - 1], root, glass, matte)
    return root


def export(path):
    root = bpy.data.objects[ROOT]
    parts = sorted((o for o in root.children_recursive if o.type == 'MESH'), key=lambda o: o.name)
    bpy.context.view_layer.update()
    materials = sorted({m for o in parts for m in o.data.materials}, key=lambda m: m.name)
    vertices, faces, indices, smooth, colors = [], [], [], [], []
    for obj in parts:
        offset = len(vertices)
        vertices.extend([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices])
        attr = obj.data.color_attributes['Color']
        for polygon in obj.data.polygons:
            faces.append(tuple(offset + i for i in polygon.vertices))
            indices.append(materials.index(obj.data.materials[polygon.material_index]))
            smooth.append(polygon.use_smooth)
            colors.append([tuple(attr.data[i].color) for i in polygon.loop_indices])
    mesh = bpy.data.meshes.new('Display delivery batch')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    batch = bpy.data.objects.new('DISPLAY_ThreeMaterialBatch', mesh)
    bpy.context.scene.collection.objects.link(batch)
    batch.parent = root
    for mat in materials:
        mesh.materials.append(mat)
    attr = mesh.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    for poly, mat_index, use_smooth, rgba in zip(mesh.polygons, indices, smooth, colors):
        poly.material_index, poly.use_smooth = mat_index, use_smooth
        for index, color in zip(poly.loop_indices, rgba):
            attr.data[index].color = color
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    batch.select_set(True)
    try:
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        bpy.data.objects.remove(batch, do_unlink=True)
        bpy.data.meshes.remove(mesh)


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Slate studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.10, .14, .18, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    for name, location, power, size in [
        ('Key', (-2, -3, 4), 500, 2.5), ('Fill', (3, -1, 2), 320, 2),
        ('Rim', (0, 3, 3), 650, 2)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.object
        light.name = 'STUDIO_' + name
        light.data.energy, light.data.size = power, size
        aim(light, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 1.46
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.seed = 48, 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.camera.location = (1.5, -2.8, 1.55)
    aim(scene.camera, TARGET)


def render_views():
    scene = bpy.context.scene
    for name, position in [('hero', (1.5, -2.8, 1.55)), ('front', (0, -4, .58)),
                           ('side', (4, 0, .58)), ('3q', (-1.7, -2.8, 1.9))]:
        scene.camera.location = position
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
    main()
