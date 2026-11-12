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


def bench():
    wood = material('Warm walnut', (111, 75, 49), .46)
    brass = material('Brushed champagne brass', (181, 155, 98), .32, .7)
    fabric = material('Sand upholstery', (203, 185, 151), .95)
    piping = material('Upholstery piping', (156, 133, 96), .9)
    jade = material('Jade back panels', (36, 76, 66), .48)
    for x in (-1.1, 1.1):
        for y in (-.31, .31):
            box('Brass foot', (x, y, .14), (.085, .085, .28), brass, .012)
        box('Arm support', (x, 0, .68), (.065, .82, .11), brass, .025)
        for y in (-.34, .34):
            box('Arm upright', (x, y, .53), (.065, .065, .43), brass, .018)
        box('Rounded walnut armrest', (x, .015, .82), (.13, .88, .09), wood, .035)
    box('Walnut plinth', (0, 0, .315), (2.5, .85, .18), wood, .04)
    box('Front brass trim', (0, .434, .37), (2.48, .02, .035), brass, .008)
    for i, x in enumerate((-.84, 0, .84)):
        box(f'Seat cushion {i + 1}', (x, .015, .525), (.825, .87, .22), fabric, .075)
        box(f'Seat piping {i + 1}', (x, .015, .513), (.833, .878, .018), piping, .008)
        back = box(f'Back cushion {i + 1}', (x, -.326, .975), (.825, .18, .59), fabric, .065)
        back.rotation_euler.x = -.075
        box(f'Rear jade panel {i + 1}', (x, -.43, .955), (.80, .05, .58), jade, .02)
    for x in (-1.18, 1.18):
        box('Back frame upright', (x, -.40, .86), (.07, .08, .85), wood, .018)
    box('Walnut top rail', (0, -.35, 1.285), (2.58, .21, .065), wood, .025)
    box('Back brass reveal', (0, -.46, 1.24), (2.48, .014, .025), brass, .005)


def planter():
    ceramic = material('Fluted jade ceramic', (42, 83, 67), .36)
    brass = material('Brushed champagne brass', (181, 155, 98), .32, .7)
    soil = material('Dark planting soil', (49, 39, 27), 1)
    stem = material('Palm stems', (116, 127, 66), .86)
    leaves = [material('Deep palm green', (42, 94, 54), .77),
              material('Young palm green', (80, 126, 65), .8)]
    lathe('Fluted ceramic vessel', [(0, .055), (.32, .055), (.36, .09),
          (.407, .56), (.421, .61), (.422, .64), (.39, .65), (.375, .61),
          (.365, .54), (0, .54)], ceramic, flutes=24)
    lathe('Brass foot ring', [(.30, 0), (.33, 0), (.34, .055), (.31, .055), (.30, 0)], brass)
    lathe('Brass rim', [(.418, .60), (.434, .60), (.434, .629), (.418, .629), (.418, .60)], brass)
    lathe('Visible soil', [(0, .59), (.373, .59), (.373, .582), (0, .582)], soil)
    # Real mesh leaflets with a folded ridge, no alpha cards or texture downloads.
    for frond in range(11):
        angle = frond * 2.399963
        height = 1.28 + (frond % 4) * .16
        reach = .51 + (frond % 3) * .08
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        side = Vector((-math.sin(angle), math.cos(angle), 0))
        def spine(t):
            return direction * (reach * t * t) + Vector((0, 0, .59 + height * math.sin(t * 1.47)))
        tube(f'Arching palm stem {frond + 1}', [spine(i / 12) for i in range(13)], .008, stem)
        for pair in range(9):
            t = .29 + pair * .077
            base = spine(t)
            length = .19 * math.sin(math.pi * (t - .1)) + .065
            for sign in (-1, 1):
                end = base + side * sign * length + direction * .075 + Vector((0, 0, -.10))
                midpoint = base.lerp(end, .46) + Vector((0, 0, .045))
                width = direction * (.023 * math.sin(math.pi * t) + .01)
                verts = [base, midpoint + width, midpoint + Vector((0, 0, .013)),
                         midpoint - width, end]
                mesh = bpy.data.meshes.new('Folded palm leaflet')
                mesh.from_pydata(verts, [], [(0, 1, 2), (0, 2, 3), (1, 4, 2), (2, 4, 3)])
                obj = bpy.data.objects.new(f'Palm leaflet {frond}-{pair}-{sign}', mesh)
                bpy.context.collection.objects.link(obj)
                finish(obj, obj.name, leaves[(frond + pair) % 2])
                for face in mesh.polygons:
                    face.use_smooth = True


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
    root['source'] = 'Blender-3D-Gallery / original GJH mall furniture'
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
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(HERE / 'previews' / f'{slug}.png')
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / f'{slug}.blend'), compress=True)
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    for folder in ('exports', 'previews', 'sources'):
        (HERE / folder).mkdir(parents=True, exist_ok=True)
    build('gjh-lounge-bench', 'ASSET_GJHLoungeBench', bench, (3.2, 4.6, 2.8), (0, 0, .65), 3.6)
    build('gjh-areca-planter', 'ASSET_GJHArecaPlanter', planter, (3, 4, 2.8), (0, 0, 1.1), 2.8)
