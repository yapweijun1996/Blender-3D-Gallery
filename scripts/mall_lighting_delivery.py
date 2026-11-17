"""Save editable mall lighting fixtures and render their actual static glTF export."""

import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def mesh_points(objects):
    return [obj.matrix_world @ vertex.co for obj in objects if obj.type == 'MESH'
            for vertex in obj.data.vertices]


def frame(points, direction):
    rotation = direction.to_track_quat('Z', 'Y')
    right, up = rotation @ Vector((1, 0, 0)), rotation @ Vector((0, 1, 0))
    ranges = []
    for axis in (right, up, direction):
        values = [point.dot(axis) for point in points]
        ranges.append((min(values), max(values)))
    center = sum((axis * ((low + high) / 2) for axis, (low, high) in
                  zip((right, up, direction), ranges)), Vector((0, 0, 0)))
    width, height, depth = (high - low for low, high in ranges)
    return center, rotation, max(width, height * 4 / 3) * 1.13, max(width, height, depth)


def export_fixture(root, path):
    # Bake evaluated copies so source bevels, object pivots and named parts stay editable.
    graph = bpy.context.evaluated_depsgraph_get()
    parts = []
    for source in sorted(root.children_recursive, key=lambda obj: obj.name):
        if source.type != 'MESH':
            continue
        evaluated = source.evaluated_get(graph)
        data = bpy.data.meshes.new_from_object(evaluated, depsgraph=graph)
        data.transform(root.matrix_world.inverted() @ evaluated.matrix_world)
        part = bpy.data.objects.new('Export_' + source.name, data)
        bpy.context.collection.objects.link(part)
        parts.append(part)
    if not parts:
        raise ValueError('No meshes parented to ' + root.name)
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    batch = bpy.context.object
    batch.name = 'Fixture'
    batch.data.name = 'Fixture'
    batch.parent = root
    root.select_set(True)
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_yup=True, export_animations=False, export_texcoords=False,
                              export_extras=True, export_cameras=False, export_lights=False)
    bpy.data.objects.remove(batch, do_unlink=True)


def preview(glb, output, direction):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    scene = bpy.context.scene
    center, rotation, span, scale = frame(mesh_points(scene.objects), direction)
    right, up = rotation @ Vector((1, 0, 0)), rotation @ Vector((0, 1, 0))
    scene.world = bpy.data.worlds.new('Studio environment')
    scene.world.use_nodes = True
    sky = scene.world.node_tree.nodes.get('Background')
    sky.inputs['Color'].default_value = (0.72, 0.78, 0.85, 1)
    sky.inputs['Strength'].default_value = 0.36
    # A matte card and three softboxes form a temporary, scale-relative product studio.
    bpy.ops.mesh.primitive_plane_add(size=scale * 12, location=center - direction * scale * 1.2)
    card = bpy.context.object
    card.rotation_euler = rotation.to_euler()
    backdrop = bpy.data.materials.new('Studio matte')
    backdrop.diffuse_color = (0.30, 0.34, 0.37, 1)
    card.data.materials.append(backdrop)
    for name, offset, power, diameter, color in (
        ('Softbox', -right * 1.4 + up * 1.8 + direction * 1.5, 145, 1.8, (1, .94, .84)),
        ('Fill', right * 1.6 - up * .6 + direction, 70, 1.25, (.81, .90, 1)),
        ('Edge', right + up * 1.5 - direction * .7, 115, 1.05, (1, .94, .87)),
    ):
        bpy.ops.object.light_add(type='AREA', location=center + scale * offset)
        light = bpy.context.object
        light.name = name
        light.data.energy = power * scale ** 2
        light.data.shape = 'DISK'
        light.data.size = diameter * scale
        light.data.color = color
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.object.camera_add(location=center + direction * scale * 3)
    camera = bpy.context.object
    camera.rotation_euler = rotation.to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = span
    camera.data.clip_start = scale * .001
    camera.data.clip_end = scale * 15
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'
    scene.render.resolution_x, scene.render.resolution_y = 880, 660
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    output.mkdir(exist_ok=True)
    scene.render.filepath = str(output / 'hero.png')
    bpy.ops.render.render(write_still=True)
    thumbnail = bpy.data.images.load(scene.render.filepath)
    thumbnail.scale(480, 360)
    thumbnail.file_format = 'WEBP'
    thumbnail.filepath_raw = str(output / 'thumbnail.webp')
    thumbnail.save()


def deliver(asset_dir, root_name, build, view_gltf):
    """Build(lod) creates and returns a single empty root in a fresh metric scene."""
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--export-source', action='store_true', help='Export L0 from the saved source.')
    mode.add_argument('--render-only', action='store_true', help='Render the existing L0 GLB.')
    parser.add_argument('--skip-render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    folder = Path(asset_dir).resolve()
    source = folder / 'sources' / (folder.name + '.blend')
    exports = folder / 'exports'
    exports.mkdir(exist_ok=True)
    high = exports / 'optimized.glb'
    direction = Vector((view_gltf[0], -view_gltf[2], view_gltf[1])).normalized()
    if args.export_source:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        export_fixture(bpy.data.objects[root_name], high)
    elif not args.render_only:
        for lod, output in enumerate((high, exports / 'lod1.glb')):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.context.scene.unit_settings.system = 'METRIC'
            root = build(lod)
            if root.type != 'EMPTY' or root.name != root_name or root.parent:
                raise ValueError('Builder must return the named top-level empty ' + root_name)
            bpy.context.view_layer.update()
            if lod == 0:
                center, rotation, span, _ = frame(mesh_points(root.children_recursive), direction)
                for screen in bpy.data.screens:
                    for area in screen.areas:
                        if area.type == 'VIEW_3D':
                            space = area.spaces.active
                            space.region_3d.view_rotation = rotation
                            space.region_3d.view_location = center
                            space.region_3d.view_distance = span * 1.6
                            space.clip_start = .001
                            space.shading.color_type = 'MATERIAL'
                            space.overlay.show_extras = False
                bpy.ops.object.select_all(action='DESELECT')
                source.parent.mkdir(exist_ok=True)
                bpy.context.preferences.filepaths.save_version = 0
                bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
            export_fixture(root, output)
    if not args.skip_render:
        preview(high, folder / 'previews', direction)
