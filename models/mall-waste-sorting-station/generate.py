"""Original three-stream modular mall waste sorting station. Blender 4.0.2, metric geometry.
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
ID = 'mall-waste-sorting-station'
ROOT = 'ASSET_MallWasteSortingStation'
GROUPS = ('StationFrame', 'RecycleCompartment', 'FoodCompartment', 'GeneralCompartment',
          'RecycleLid', 'FoodLid', 'GeneralLid')
STREAMS = [('Recycle', .60, 'RECYCLE', 'BOTTLES + CANS', 'blue'),
           ('Food', 0, 'FOOD', 'FOOD SCRAPS', 'green'),
           ('General', -.60, 'GENERAL', 'OTHER WASTE', 'slate')]


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
        modifier.segments = 2
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


def silhouette(name, points, x, y, z, mat, group):
    # Solid geometric pictogram, independent of fonts. Front is +Y.
    vertices = [(-u+x, y+d, v+z) for d in (0, .004) for u, v in points]
    n = len(points)
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    put(obj, name, mat, group)
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
        merged.data.name = group_name + "Geometry"
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
        group['replaceable'] = name != 'StationFrame'
    root['units'] = 'metres'
    root['origin'] = 'floor centre'
    root['front_axis'] = '+Y'
    p = {
        'ink': material('Midnight blue powder coat', (24, 44, 61), .43),
        'ivory': material('Porcelain enamel', (237, 231, 212), .48),
        'blue': material('Recycle blue', (36, 124, 184), .42),
        'green': material('Food jade green', (44, 134, 106), .45),
        'slate': material('General slate', (96, 109, 119), .48),
        'metal': material('Satin aluminium', (156, 172, 181), .32, .72),
        'rubber': material('Dark recessed liner', (19, 25, 29), .86)
    }
    g = 'StationFrame'
    box('Recessed ground gasket', (0, 0, .013), (1.82, .55, .026), p['rubber'], g, .012)
    box('Common weighted plinth', (0, 0, .065), (1.90, .63, .08), p['ink'], g, .025)
    box('Plinth satin nosing', (0, .308, .082), (1.82, .014, .024), p['metal'], g, .004)
    for x in (-.9, .9):
        box('Rear upright', (x, -.27, .68), (.045, .05, 1.17), p['ink'], g, .008)
    box('Shared identification rail', (0, -.245, 1.265), (1.85, .07, .17), p['ink'], g, .022)
    label('Editable station title', 'SORT / RETURN', .835, -.205, 1.255, .077, p['ivory'], g)
    label('Editable station subline', 'THREE STREAMS. ONE SMALL STEP.', -.09, -.205, 1.261, .036, p['ivory'], g)
    for key, x, title, detail, color in STREAMS:
        g = key + 'Compartment'
        # Hollow, separated body. No solid cube beneath the real lid aperture.
        box(key+' liner bottom', (x, 0, .145), (.54, .52, .055), p['rubber'], g, .009)
        for side in (-1, 1):
            box(key+' body side', (x+side*.268, 0, .59), (.028, .55, .89), p['ink'], g, .012)
        box(key+' back wall', (x, -.263, .59), (.53, .025, .89), p['ink'], g, .01)
        box(key+' front door backing', (x, .263, .59), (.53, .025, .89), p['ink'], g, .012)
        box(key+' removable porcelain door', (x, .285, .59), (.488, .025, .81), p['ivory'], g, .023)
        # Subtle service handle and lower badge remain in each body module.
        box(key+' recessed door pull', (x-.17, .301, .905), (.052, .008, .018), p['ink'], g, .006)
        label(key+' editable stream detail', detail, x, .301, .31, .039, p['ink'], g, 'CENTER')
        label(key+' editable stream number', {'Recycle':'01', 'Food':'02', 'General':'03'}[key], x, .301, .22, .038, p[color], g, 'CENTER')
        # Large recognizable bottle, leaf and refuse-bag silhouettes.
        if key == 'Recycle':
            points=[(-.049,-.11),(.049,-.11),(.049,.045),(.026,.073),(.026,.12),(-.026,.12),(-.026,.073),(-.049,.045)]
            silhouette('Bottle pictogram', points, x, .302, .61, p[color], g)
            box('Bottle label stripe', (x, .309, .59), (.091, .005, .023), p['ivory'], g, .002)
        elif key == 'Food':
            points=[(-.09,-.075),(-.103,-.01),(-.065,.065),(.026,.11),(.107,.12),(.099,.025),(.056,-.051),(-.013,-.088)]
            silhouette('Leaf pictogram', points, x, .302, .61, p[color], g)
            stem=box('Leaf midrib', (x, .31, .62), (.012, .005, .17), p['ivory'], g, .002)
            stem.rotation_euler[1]=-.7
        else:
            points=[(-.08,-.105),(.08,-.105),(.097,-.049),(.063,.038),(.024,.076),(.043,.111),(-.043,.111),(-.024,.076),(-.063,.038),(-.097,-.049)]
            silhouette('Refuse bag pictogram', points, x, .302, .61, p[color], g)
            box('Refuse bag tie', (x, .309, .683), (.073, .005, .013), p['ivory'], g, .003)
        g = key + 'Lid'
        # Four separate rails form a genuine 0.38 x 0.34 m opening.
        # No hidden cap spans that aperture; the body liner is 0.9 m below it.
        for side in (-1,1):
            box(key+' lid side rim', (x+side*.238, 0, 1.055), (.096, .59, .07), p[color], g, .017)
        for side in (-1,1):
            box(key+' lid front back rim', (x, side*.2325, 1.055), (.39, .125, .07), p[color], g, .017)
        box(key+' labelled front fascia', (x, .287, 1.022), (.568, .027, .108), p[color], g, .012)
        label(key+' editable stream label', title, x, .304, 1.005, .063, p['ivory'], g, 'CENTER')
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
        point_at(obj, (0, 0, .66))
    bpy.ops.object.camera_add(location=(3.0, 6.5, 3.5))
    scene.camera = bpy.context.object
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 2.6
    point_at(scene.camera, (0, 0, .66))
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
