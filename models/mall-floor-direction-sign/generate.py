"""Original North Walk modular floor sign. Blender 4.0.2, metric geometry.
blender --background --python generate.py
blender --background --python generate.py -- --export-source
The second command exports the saved, manually edited .blend without rebuilding it.
"""
from pathlib import Path
import math
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ID = 'mall-floor-direction-sign'
ROOT = 'ASSET_MallFloorDirectionSign'
GROUPS = ('SignStructure', 'FloorIdentity', 'DirectionDining', 'DirectionShops',
          'DirectionCinema', 'DirectionFacilities')
# Labels are editable source text, not an in-browser editing feature.
LABELS = [('DirectionDining', 'Dining', 'FOOD HALL / 201-218', 'left'),
          ('DirectionShops', 'Shops', 'NORTH WALK / 220-248', 'up'),
          ('DirectionCinema', 'Cinema', 'SCREEN 01-06', 'right'),
          ('DirectionFacilities', 'Restrooms', 'LIFTS / FAMILY ROOM', 'right')]


def material(name, rgb, roughness=.5, metallic=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    def linear(v):
        v /= 255
        return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    rgba = tuple(linear(v) for v in rgb) + (1,)
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = rgba
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    m.diffuse_color = rgba
    return m


def put(obj, name, mat, group, bevel=0):
    obj.name = name
    obj.data.materials.append(mat)
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    bpy.data.collections[group].objects.link(obj)
    if bevel:
        modifier = obj.modifiers.new('Manufactured radiused edges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, location, dimensions, mat, group, bevel=.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return put(obj, name, mat, group, bevel)


def cylinder(name, location, radius, depth, mat, group, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                      depth=depth, location=location)
    return put(bpy.context.object, name, mat, group, .004)


def label(name, body, x, y, z, size, mat, group, align='LEFT'):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.extrude = .0005
    curve.resolution_u = 3
    obj = bpy.data.objects.new(name, curve)
    bpy.data.collections[group].objects.link(obj)
    obj.location = (x, y, z)
    # Text faces Blender +Y, glTF -Z. Metadata rotates it to the gallery camera.
    obj.rotation_euler = (math.pi / 2, 0, math.pi)
    curve.materials.append(mat)
    return obj


def arrow(name, direction, x, y, z, mat, group):
    # One real solid arrow with a shaft and head, not a font-dependent glyph.
    points = [(-.085, -.022), (.015, -.022), (.015, -.065),
              (.09, 0), (.015, .065), (.015, .022), (-.085, .022)]
    angle = {'right': 0, 'left': math.pi, 'up': math.pi / 2}[direction]
    coords = [(u*math.cos(angle)-v*math.sin(angle),
               u*math.sin(angle)+v*math.cos(angle)) for u, v in points]
    vertices = [(-u+x, y+d, v+z) for d in (0, .007) for u, v in coords]
    n = len(coords)
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj = put(obj, name, mat, group, .002)
    # Enforce consistent outward normals for this hand-authored extrusion.
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def export_asset():
    scene = bpy.context.scene
    root = bpy.data.objects.new(ROOT, None)
    scene.collection.objects.link(root)
    parts = [root]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for group_name in GROUPS:
        copies = []
        for original in bpy.data.collections[group_name].objects:
            if original.type not in ('MESH', 'FONT', 'CURVE'):
                continue
            mesh = bpy.data.meshes.new_from_object(original.evaluated_get(depsgraph),
                                                   depsgraph=depsgraph)
            obj = bpy.data.objects.new(original.name + ' export', mesh)
            scene.collection.objects.link(obj)
            obj.matrix_world = original.matrix_world.copy()
            copies.append(obj)
        assert copies, group_name
        bpy.ops.object.select_all(action='DESELECT')
        for obj in copies:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join()
        merged = bpy.context.object
        merged.name = group_name
        # Joining preserves evaluated geometry and material slots per module.
        merged.parent = root
        merged['source_collection'] = group_name
        parts.append(merged)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(HERE/'exports'/f'{ID}.glb'),
        export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
        export_animations=False, export_texcoords=False, export_extras=True,
        export_cameras=False, export_lights=False)
    for obj in reversed(parts):
        bpy.data.objects.remove(obj, do_unlink=True)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    root = bpy.data.collections.new(ROOT)
    scene.collection.children.link(root)
    for name in GROUPS:
        group = bpy.data.collections.new(name)
        root.children.link(group)
        group['replaceable'] = name != 'SignStructure'
    root['units'] = 'metres'
    root['origin'] = 'floor centre'
    root['front_axis'] = '+Y'
    p = {
        'ink': material('Midnight blue powder coat', (24, 44, 61), .43),
        'ivory': material('Porcelain enamel', (237, 231, 212), .48),
        'orange': material('Burnt orange wayfinding accent', (213, 101, 47), .5),
        'metal': material('Satin aluminium', (156, 172, 181), .32, .72),
        'rubber': material('Recessed dark rubber', (27, 31, 34), .86)
    }
    g = 'SignStructure'
    box('Recessed ground gasket', (0, 0, .012), (1.13, .48, .024), p['rubber'], g, .011)
    box('Weighted chamfered base', (0, 0, .058), (1.24, .54, .076), p['ink'], g, .025)
    box('Base inset cap', (0, 0, .103), (1.13, .43, .018), p['metal'], g, .008)
    for x in (-.49, .49):
        for y in (-.14, .14):
            cylinder('Recessed base fixing', (x, y, .115), .016, .008, p['rubber'], g, 12)
    box('Left continuous spine', (.53, -.035, 1.30), (.085, .17, 2.38), p['ink'], g, .018)
    box('Right continuous spine', (-.53, -.035, 1.30), (.085, .17, 2.38), p['ink'], g, .018)
    box('Inset rear service cover', (0, -.09, 1.49), (.99, .045, 1.93), p['ink'], g, .018)
    box('Lower crossrail', (0, .015, .47), (1.08, .14, .07), p['ink'], g)
    box('Crown cap', (0, -.015, 2.50), (1.16, .21, .06), p['metal'], g, .022)
    box('Orange vertical locator', (.59, -.01, 2.16), (.035, .16, .61), p['orange'], g, .008)
    # Air gap beneath the first cartridge exposes a pair of short structural legs.
    for x in (-.40, .40):
        box('Base support foot', (x, -.035, .29), (.085, .17, .36), p['metal'], g)
    g = 'FloorIdentity'
    box('Floor header cartridge', (0, .021, 2.20), (.995, .14, .53), p['ink'], g, .018)
    box('Floor number orange badge', (.315, .103, 2.22), (.31, .025, .36), p['orange'], g, .026)
    label('Editable floor number', '02', .315, .122, 2.115, .245, p['ivory'], g, 'CENTER')
    label('Editable level title', 'LEVEL', .07, .108, 2.29, .065, p['ivory'], g)
    label('Editable zone name', 'NORTH', .07, .108, 2.15, .115, p['ivory'], g)
    label('Editable zone subline', 'WALK', .07, .108, 2.06, .075, p['ivory'], g)
    for index, (group, title, detail, direction) in enumerate(LABELS):
        z = 1.72-index*.35
        box(f'{group} removable cartridge', (0, .028, z), (.995, .142, .31), p['ivory'], group, .018)
        # Orange edge tab is part of the replaceable cartridge.
        box(f'{group} edge tab', (.476, .102, z), (.025, .012, .218), p['orange'], group, .004)
        label(f'{group} editable destination', title, .408, .107, z+.015, .111, p['ink'], group)
        label(f'{group} editable detail', detail, .405, .107, z-.079, .038, p['ink'], group)
        arrow(f'{group} {direction} arrow', direction, -.367, .107, z+.015, p['ink'], group)
    export_asset()
    # Source-only studio, never included in selected asset export.
    studio = bpy.data.collections.new('Studio (not exported)')
    scene.collection.children.link(studio)
    floor = material('Studio limestone', (203, 208, 208), .93)
    box('Studio floor', (0, 0, -.065), (200, 200, .1), floor, studio.name, 0)
    for name, pos, energy, size in [('Key', (3.5, 4.5, 5), 700, 4),
                                    ('Fill', (-3, 2, 3), 420, 3),
                                    ('Rim', (1, -4, 4), 700, 3)]:
        bpy.ops.object.light_add(type='AREA', location=pos)
        obj = bpy.context.object
        obj.name = name
        obj.data.energy = energy
        obj.data.size = size
        point_at(obj, (0, 0, 1.25))
    bpy.ops.object.camera_add(location=(2.7, 6.8, 3.2))
    scene.camera = bpy.context.object
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 3.15
    point_at(scene.camera, (0, 0, 1.25))
    world = bpy.data.worlds.new('Neutral studio environment')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.3, .34, .38, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    scene.world = world
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.use_gtao = True
    scene.eevee.gtao_distance = 3
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(HERE/'previews'/f'{ID}.png')
    scene.view_settings.look = 'AgX - Medium High Contrast'
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'), compress=True)
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'))
        export_asset()
        bpy.context.scene.render.filepath = str(HERE/'previews'/f'{ID}.png')
        bpy.ops.render.render(write_still=True)
    else:
        build()
