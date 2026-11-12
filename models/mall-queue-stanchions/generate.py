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
    root['source'] = 'Blender-3D-Gallery / original modular mall queue stanchions'
    # Export a merged evaluated copy: editable authored objects remain in the blend.
    bpy.ops.object.select_all(action='DESELECT')
    exports = []
    for module in sorted({obj['module'] for obj in objects}):
        bpy.ops.object.select_all(action='DESELECT')
        copies = []
        for obj in objects:
            if obj['module'] != module:
                continue
            duplicate = obj.copy()
            duplicate.data = obj.data.copy()
            scene.collection.objects.link(duplicate)
            duplicate.select_set(True)
            copies.append(duplicate)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.join()
        merged = bpy.context.object
        merged.name = module
        scene.cursor.location = tuple(next(obj['module_origin'] for obj in objects if obj['module'] == module))
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        merged['module'] = module
        exports.append(merged)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in exports:
        obj.select_set(True)
    root.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(HERE / 'exports' / f'{slug}.glb'),
        export_format='GLB', use_selection=True, export_apply=True,
        export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    for merged in exports:
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




def post(x, p, name):
    start = set(bpy.context.scene.objects)
    # Low domed weighted foot and recessed rubber contact ring.
    lathe('Rubber sole', [(0,0),(.165,0),(.18,.012),(.18,.025),(0,.025)],p['dark'])
    lathe('Jade weighted base',[(0,.018),(.18,.018),(.185,.035),(.17,.052),(.11,.068),(.045,.075),(0,.075)],p['jade'])
    lathe('Base brass reveal',[(.175,.027),(.183,.027),(.183,.038),(.175,.038),(.175,.027)],p['brass'])
    lathe('Brass upright',[(0,.06),(.031,.06),(.031,.845),(.025,.865),(0,.865)],p['brass'])
    lathe('Jade belt cartridge',[(0,.83),(.055,.83),(.065,.85),(.065,.94),(.056,.96),(0,.96)],p['jade'])
    lathe('Cartridge top brass cap',[(0,.955),(.057,.955),(.06,.966),(.052,.976),(0,.976)],p['brass'])
    for angle in (0,math.pi/2,math.pi,3*math.pi/2):
        ob=box('Receiver socket',(.066*math.cos(angle),.066*math.sin(angle),.905),(.014,.030,.058),p['dark'],.003)
        ob.rotation_euler.z=angle
    for obj in set(bpy.context.scene.objects)-start:
        obj.location.x += x
        obj['module']=name
        obj['module_origin']=[x,0,0]


def queue(length=None):
    p=palette()
    if length is None:
        post(0,p,'MODULE_Post')
        return
    post(-length/2,p,'MODULE_Post_Left')
    post(length/2,p,'MODULE_Post_Right')
    start=set(bpy.context.scene.objects)
    # Belt meets receiver inner faces at +/- (post spacing / 2 - .073).
    span=length-.146
    box('Jade woven belt',(0,0,.905),(span,.009,.05),p['jade'],.002)
    for sign in (-1,1):
        box('Brass belt connector',(sign*(length/2-.083),0,.905),(.02,.015,.056),p['brass'],.003)
    for obj in set(bpy.context.scene.objects)-start:
        obj['module']='MODULE_Belt'
        obj['module_origin']=[0,0,0]


if __name__ == '__main__':
    for folder in ('exports','previews','sources','reports'):
        (HERE/folder).mkdir(parents=True,exist_ok=True)
    build('mall-queue-post','ASSET_MallQueuePost',lambda:queue(),(1.7,2.5,1.8),(0,0,.46),1.3)
    build('mall-queue-short','ASSET_MallQueueShort',lambda:queue(1.2),(2.5,4,2.2),(0,0,.46),2.1)
    build('mall-queue-long','ASSET_MallQueueLong',lambda:queue(2.0),(3,5,2.5),(0,0,.46),2.9)
