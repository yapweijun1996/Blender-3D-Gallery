"""Original deterministic blank double-sided directory. Blender 5.2.3, metres.

Rebuild: blender --background --python generate.py
Preserve saved edits: append -- --export-source --skip-render
Optional --export-path writes the GLB to a separate inspection destination.
"""
from pathlib import Path
import argparse
import json
import math
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'mall-directory-standee'
ROOT = 'ASSET_MallDirectoryStandee'
TARGET = Vector((0, 0, .95))


def material(name, color, metallic=0, roughness=.4, emission=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    rgba = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                 for v in color) + (1,)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = rgba
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Emission Color'].default_value = rgba
    shader.inputs['Emission Strength'].default_value = emission
    mat.diffuse_color = rgba
    return mat


def finish(obj, name, mat, root, role, bevel=0):
    obj.name = name
    obj.parent = root
    obj['delivery_group'] = role
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, location, dimensions, mat, root, role, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, root, role, bevel)


def disk(name, location, radius, depth, mat, root, role):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth,
                                      location=location, rotation=(math.pi / 2, 0, 0))
    return finish(bpy.context.object, name, mat, root, role)


def build(root):
    jade = material('Deep jade powder coat', (.105, .225, .211), .24, .38)
    brass = material('Satin champagne aluminium', (.65, .55, .36), .66, .33)
    panel = material('Warm ivory backlit diffuser', (.92, .95, .92), 0, .32, .65)

    box('BASE_SlimWeightedFoot', (0, 0, .026), (.90, .35, .052), jade, root, 'Structure', .018)
    box('BASE_ChampagneReveal', (0, 0, .055), (.79, .255, .006), brass, root, 'Accents', .002)
    box('SUPPORT_CentralPedestal', (0, 0, .175), (.30, .085, .24), jade, root, 'Structure', .012)
    box('FRAME_DoubleSidedHousing', (0, 0, 1.0575), (.84, .12, 1.575), jade, root, 'Structure', .022)

    for side, sign in [('Front', -1), ('Rear', 1)]:
        # Blender -Y becomes glTF +Z. Both faces are solid, outward-facing panels.
        box('TRIM_' + side, (0, sign * .061, 1.065), (.782, .008, 1.438),
            brass, root, 'Accents', .003)
        box('PANEL_' + side, (0, sign * .068, 1.065), (.752, .008, 1.408),
            panel, root, 'Panel' + side, .003)
        # A plain two-tone locator dot: no font, icon, map, label or texture.
        x = sign * .175
        disk('MARKER_Halo_' + side, (x, sign * .073, .91), .030, .003,
             brass, root, 'Accents')
        disk('MARKER_Dot_' + side, (x, sign * .075, .91), .019, .003,
             jade, root, 'Structure')
        box('FRAME_LowerReveal_' + side, (0, sign * .061, .309), (.65, .004, .005),
            brass, root, 'Accents', .001)

    for x in (-.27, .27):
        box('LIGHTBAR_Mount', (x, 0, 1.849), (.020, .048, .030),
            jade, root, 'Structure', .003)
    box('LIGHTBAR_TopHousing', (0, 0, 1.881), (.76, .17, .038),
        jade, root, 'Structure', .009)
    for sign in (-1, 1):
        box('LIGHTBAR_Diffuser', (0, sign * .085, 1.878), (.656, .006, .014),
            panel, root, 'Lightbar', .002)


def export(path):
    """Batch evaluated copies by shared role; retain separate editable source parts."""
    root = bpy.data.objects[ROOT]
    source = sorted((o for o in root.children_recursive if o.type == 'MESH'), key=lambda o: o.name)
    groups = {}
    graph = bpy.context.evaluated_depsgraph_get()
    for obj in source:
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph))
        proxy = bpy.data.objects.new('DELIVERY_' + obj.name, mesh)
        bpy.context.scene.collection.objects.link(proxy)
        proxy.matrix_world = obj.matrix_world.copy()
        groups.setdefault(obj['delivery_group'], []).append(proxy)
    delivery = []
    for role, objects in sorted(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        proxy = bpy.context.object
        proxy.name = 'DELIVERY_' + role
        proxy.parent = root
        proxy['source_parts'] = [o.name for o in source if o['delivery_group'] == role]
        delivery.append(proxy)
    bpy.ops.object.select_all(action='DESELECT')
    root.select_set(True)
    for obj in delivery:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_animations=False,
                              export_texcoords=False, export_extras=True,
                              export_cameras=False, export_lights=False)
    for obj in delivery:
        bpy.data.objects.remove(obj, do_unlink=True)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral gallery studio')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.14, .18, .19, 1)
    background.inputs['Strength'].default_value = .5
    for name, loc, energy, size in [('Key', (-3, -4, 5), 480, 4),
                                     ('Fill', (3, -2, 3), 280, 3),
                                     ('Rim', (1, 3, 4), 650, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy = energy
        obj.data.shape = 'DISK'
        obj.data.size = size
        aim(obj, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 2.35
    scene.camera.location = (2.6, -4.5, 2.6)
    aim(scene.camera, TARGET)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    views = [('hero', (2.6, -4.5, 2.6)), ('front', (0, -5, .95)),
             ('side', (5, 0, 1.15)), ('3q', (-2.6, -4.5, 2.15)),
             ('rear', (2.6, 4.5, 2.15))]
    for name, location in views:
        scene.camera.location = location
        aim(scene.camera, TARGET)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--export-source', action='store_true')
    parser.add_argument('--skip-render', action='store_true')
    parser.add_argument('--export-path', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    for folder in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / folder).mkdir(exist_ok=True)
    if args.export_source:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        root = bpy.data.objects.new(ROOT, None)
        scene.collection.objects.link(root)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['scope'] = 'Static blank double-sided directory; no navigation runtime'
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(args.export_path or HERE / 'exports' / 'optimized.glb')
    if not args.skip_render:
        render_views()


if __name__ == '__main__':
    main()
