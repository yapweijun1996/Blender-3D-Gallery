"""Create original, metre-scale mall furniture with no external assets.

Run from any directory: blender --background --python generate.py
Only this collection's source, exports and previews are written.
"""
from pathlib import Path
import math

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent


def material(name, color, roughness=.6, metallic=0):
    item = bpy.data.materials.new(name)
    item.use_nodes = True
    shader = item.node_tree.nodes.get('Principled BSDF')
    # Authored sRGB swatches are converted to linear, as required by glTF.
    def linear(v):
        return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    rgba = (*[linear(v / 255) for v in color], 1)
    shader.inputs['Base Color'].default_value = rgba
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    item.diffuse_color = rgba
    return item


def finish(obj, name, mat, bevel=0):
    obj.name = name
    obj.data.materials.append(mat)
    if bevel:
        if hasattr(obj.data, 'use_auto_smooth'):
            obj.data.use_auto_smooth = True
        modifier = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        modifier = obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, location, dimensions, mat, bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, bevel)


def tube(name, points, radius, mat):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def lathe(name, profile, mat, flutes=0):
    count = 96 if flutes else 48
    vertices, faces = [], []
    for radius, height in profile:
        for i in range(count):
            a = i * math.tau / count
            r = radius + (math.cos(a * 24) * .008 if flutes else 0)
            vertices.append((r * math.cos(a), r * math.sin(a), height))
    for row in range(len(profile) - 1):
        for i in range(count):
            j = (i + 1) % count
            faces.append((row * count + i, row * count + j,
                          (row + 1) * count + j, (row + 1) * count + i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    finish(obj, name, mat)
    for face in mesh.polygons:
        face.use_smooth = True
    return obj



def palette():
    return {
        'jade': material('Deep jade powder coat', (36,76,66), .48),
        'brass': material('Brushed champagne brass', (181,155,98), .32, .7),
        'wood': material('Warm walnut', (111,75,49), .46),
        'cream': material('Warm ivory', (232,224,204), .65),
        'dark': material('Charcoal recess', (26,34,33), .7),
        'mint': material('Soft sage', (137,166,139), .65),
        'coral': material('Terracotta accent', (184,104,75), .65),
    }


def label(body, location, size, mat):
    # Blender's bundled Bfont; editable text in .blend, mesh outlines in GLB.
    curve = bpy.data.curves.new(body, 'FONT')
    curve.body = body
    curve.align_x = 'CENTER'
    curve.size = size
    curve.extrude = .0003
    curve.resolution_u = 2
    obj = bpy.data.objects.new('Label - ' + body, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.pi / 2, 0, math.pi)
    obj.data.materials.append(mat)
    return obj


def disk(name, location, radius, depth, mat, front=False):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    if front:
        obj.rotation_euler.x = math.pi / 2
    return finish(obj, name, mat, .002)


def directory():
    p = palette()
    box('Weighted rounded plinth', (0,0,.045), (.96,.68,.09), p['dark'], .035)
    box('Brass base reveal', (0,0,.105), (.86,.56,.03), p['brass'], .012)
    box('Jade pedestal', (0,-.03,.36), (.40,.27,.50), p['jade'], .035)
    box('Portrait kiosk housing', (0,0,1.235), (.94,.22,1.63), p['jade'], .055)
    box('Screen brass surround', (0,.116,1.255), (.84,.022,1.43), p['brass'], .018)
    box('Screen inset', (0,.130,1.255), (.79,.012,1.37), p['dark'], .014)
    label('DIRECTORY', (0,.139,1.79), .075, p['cream'])
    label('LEVEL 01', (0,.139,1.65), .038, p['mint'])
    # An original illustrative floor plan, not an actual building map.
    box('Map surface', (0,.14,1.235), (.69,.008,.61), p['cream'], .012)
    for x,z,w,h,m in [(-.21,1.40,.18,.18,'mint'),(.17,1.40,.23,.18,'coral'),
                       (-.23,1.15,.15,.21,'jade'),(.18,1.15,.24,.16,'mint')]:
        box('Illustrative shop block', (x,.148,z), (w,.008,h), p[m], .008)
    tube('Map route', [(-.05,.16,1.00),(-.05,.16,1.30),(.27,.16,1.30)], .008, p['brass'])
    disk('You are here pin', (-.05,.17,1.01), .025,.007,p['coral'],True)
    label('YOU ARE HERE', (0,.145,.82), .034, p['cream'])
    for x in (-.23,0,.23):
        box('Touch category tile', (x,.145,.685), (.19,.012,.075), p['jade'], .014)
    for x in (-.29,.29):
        box('Rear ventilation strip', (x,-.116,1.1), (.035,.01,.34), p['dark'], .006)
    box('Rear service cover', (0,-.12,.60), (.50,.015,.22), p['dark'], .014)
    label('01', (0,.147,.48), .045,p['brass'])


def lightbox():
    p=palette()
    box('Broad stable foot', (0,0,.045), (1.16,.58,.09),p['dark'],.03)
    box('Foot brass reveal', (0,0,.108), (1.05,.45,.035),p['brass'],.012)
    box('Jade lightbox frame', (0,0,1.22), (1.08,.19,2.18),p['jade'],.035)
    box('Fine brass front surround', (0,.102,1.23), (.98,.018,2.01),p['brass'],.018)
    panel = p['cream'].node_tree.nodes.get('Principled BSDF')
    panel.inputs['Emission Color'].default_value=(.25,.22,.15,1)
    panel.inputs['Emission Strength'].default_value=.22
    box('Illuminated poster face', (0,.116,1.23), (.92,.012,1.95),p['cream'],.012)
    # Geometric campaign artwork is authored as shallow mesh, not an external image.
    disk('Abstract sun',(-.13,.13,1.66),.23,.008,p['coral'],True)
    box('Abstract jade landscape',(.10,.14,1.22),(.50,.012,.58),p['jade'],.14)
    box('Abstract sage column',(-.22,.15,1.08),(.22,.012,.52),p['mint'],.10)
    box('Campaign gold underline',(0,.15,.75),(.56,.008,.018),p['brass'],.005)
    label('DISCOVER',(0,.145,2.03),.092,p['jade'])
    label('SOMETHING NEW',(0,.145,1.91),.042,p['jade'])
    label('EVERY DAY',(0,.145,.52),.06,p['jade'])
    label('THE MALL',(0,.145,.38),.035,p['jade'])
    box('Rear removable service panel',(0,-.102,1.23),(.90,.014,1.90),p['dark'],.02)
    for z in (.40,2.04):
        for x in (-.40,.40):
            disk('Rear cover fastener',(x,-.115,z),.012,.008,p['brass'],True)


def waste_bin():
    p=palette()
    lathe('Recessed charcoal foot',[(0,0),(.26,0),(.28,.035),(.28,.08),(0,.08)],p['dark'])
    lathe('Jade open vessel',[(.28,.06),(.30,.09),(.30,.84),(.28,.88),
                             (.25,.88),(.25,.12),(0,.12),(0,.06),(.28,.06)],p['jade'])
    lathe('Champagne base band',[(.292,.09),(.305,.09),(.305,.14),(.292,.14),(.292,.09)],p['brass'])
    lathe('Inset dark liner',[(.245,.13),(.245,.83),(.235,.83),(.235,.16),(0,.16),(0,.13)],p['dark'])
    # An annular top with a genuine opening into the liner, not a painted black disk.
    lathe('Removable brass aperture rim',[(.17,.89),(.29,.89),(.31,.91),(.31,.94),
                                        (.29,.96),(.17,.96),(.16,.94),(.16,.91),(.17,.89)],p['brass'])
    for i in range(24):
        a=i*math.tau/24
        part=box('Walnut vertical slat',(.301*math.sin(a),.301*math.cos(a),.49),
                 (.035,.016,.63),p['wood'],.006)
        part.rotation_euler.z=-a
    box('Front jade label badge',(0,.323,.57),(.24,.018,.18),p['jade'],.025)
    label('WASTE',(0,.336,.60),.046,p['cream'])
    label('THANK YOU',(0,.336,.54),.021,p['cream'])


def shelf():
    p=palette()
    for x in (-.71,.71):
        for y in (-.23,.23):
            box('Adjustable recessed foot',(x,y,.035),(.08,.08,.07),p['dark'],.012)
            box('Jade upright',(x,y,.95),(.055,.055,1.80),p['jade'],.012)
    for z in (.14,.65,1.16,1.67):
        box('Walnut display shelf',(0,0,z),(1.50,.57,.065),p['wood'],.02)
        box('Slim brass front nosing',(0,.289,z), (1.47,.012,.024),p['brass'],.006)
        for x in (-.69,.69):
            box('Shelf support rail',(x,0,z-.055),(.055,.49,.045),p['jade'],.01)
    # Rear diagonal tension rods are actual cylinders, keeping open shelves useful.
    tube('Rear diagonal left',[(-.71,-.24,.20),(.71,-.24,1.72)],.013,p['brass'])
    tube('Rear diagonal right',[(.71,-.24,.20),(-.71,-.24,1.72)],.013,p['brass'])
    box('Walnut header',(0,0,1.88),(1.52,.13,.15),p['wood'],.025)
    box('Jade header inset',(0,.073,1.88),(.80,.012,.10),p['jade'],.015)
    label('COLLECTION',(0,.083,1.858),.055,p['cream'])
    for x in (-.71,.71):
        box('Brass upright cap',(x,0,1.88),(.065,.14,.16),p['brass'],.012)
def point_at(obj, xyz):
    obj.rotation_euler = (Vector(xyz) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def build(slug, root_name, factory, camera, target, ortho):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    factory()
    objects = list(scene.objects)
    root = bpy.data.objects.new(root_name, None)
    scene.collection.objects.link(root)
    for obj in objects:
        obj.parent = root
    root['units'] = 'metres'
    root['origin'] = 'floor centre'
    root['source'] = 'Blender-3D-Gallery / original mall essentials'
    # Export a merged evaluated copy: editable authored objects remain in the blend.
    bpy.ops.object.select_all(action='DESELECT')
    copies = []
    for obj in objects:
        duplicate = obj.copy()
        duplicate.data = obj.data.copy()
        scene.collection.objects.link(duplicate)
        duplicate.select_set(True)
        copies.append(duplicate)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = slug
    scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    root.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(HERE / 'exports' / f'{slug}.glb'),
        export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    bpy.data.objects.remove(merged, do_unlink=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    # Studio setup is source-only; never part of the exported model.
    ground = material('Studio backdrop', (219, 222, 211), .95)
    box('Studio floor (not exported)', (0, 0, -.065), (200, 200, .1), ground, 0)
    for name, position, energy, size in [('Key', (3, 4, 6), 650, 5), ('Fill', (-4, 1, 3), 450, 4), ('Rim', (1, -4, 5), 750, 3)]:
        bpy.ops.object.light_add(type='AREA', location=position)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = 'DISK'
        light.data.size = size
        point_at(light, target)
    bpy.ops.object.camera_add(location=camera)
    scene.camera = bpy.context.object
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = ortho
    point_at(scene.camera, target)
    world = bpy.data.worlds.new('Studio environment')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.3, .36, .32, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    scene.world = world
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(HERE / 'previews' / f'{slug}.png')
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / f'{slug}.blend'), compress=True)
    bpy.ops.render.render(write_still=True)



if __name__ == '__main__':
    for folder in ('exports', 'previews', 'sources', 'reports'):
        (HERE / folder).mkdir(parents=True, exist_ok=True)
    build('mall-directory-kiosk', 'ASSET_MallDirectoryKiosk', directory, (3,4.8,2.7), (0,0,1.05), 2.8)
    build('mall-advertising-lightbox', 'ASSET_MallAdvertisingLightbox', lightbox, (3,4.8,2.7), (0,0,1.15), 3.05)
    build('mall-trash-bin', 'ASSET_MallTrashBin', waste_bin, (2,3,2.0), (0,0,.46), 1.38)
    build('mall-display-shelf', 'ASSET_MallDisplayShelf', shelf, (3,4.8,2.8), (0,0,.96), 2.75)
