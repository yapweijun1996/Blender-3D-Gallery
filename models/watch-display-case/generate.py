"""Original deterministic watch showcase. Blender 5.2.3; no external assets."""
from pathlib import Path
import math
import sys
import json
import struct
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'watch-display-case'
ROOT = 'ASSET_WatchDisplayCase'
TARGET = (0, 0, .49)
IVORY = (.79, .79, .73)
CHARCOAL = (.13, .17, .18)
VELVET = (.12, .23, .24)
PILLOW = (.53, .57, .52)
SILVER = (.72, .76, .76)
CHAMPAGNE = (.68, .55, .35)


def linear(rgb):
    return tuple(min(.999, v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4)
                 for v in rgb) + (1,)


def materials():
    result = []
    for name, metallic, roughness in [('Soft surfaces', 0, .83), ('Hardware', .72, .27),
                                      ('Glass', 0, .08)]:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.use_backface_culling = True
        shader = mat.node_tree.nodes['Principled BSDF']
        shader.inputs['Metallic'].default_value = metallic
        shader.inputs['Roughness'].default_value = roughness
        if name == 'Glass':
            shader.inputs['Base Color'].default_value = (.33, .55, .57, 1)
            shader.inputs['Alpha'].default_value = .035
            mat.surface_render_method = 'DITHERED'
        else:
            color = mat.node_tree.nodes.new('ShaderNodeVertexColor')
            color.layer_name = 'Color'
            mat.node_tree.links.new(color.outputs['Color'], shader.inputs['Base Color'])
        if name == 'Hardware':
            # A tiny original emission mask keeps the strip in the shared hardware batch.
            image = bpy.data.images.new('Procedural edge light mask', width=4, height=2, alpha=False)
            image.colorspace_settings.name = 'sRGB'
            image.pixels = [v for _y in range(2) for x in range(4)
                            for v in ((0, 0, 0, 1) if x < 2 else (1, .88, .66, 1))]
            image.filepath_raw = str(HERE / 'sources' / 'edge-light-mask.png')
            image.file_format = 'PNG'
            image.save()
            image.pack()
            texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texture.image = image
            texture.interpolation = 'Closest'
            mat.node_tree.links.new(texture.outputs['Color'], shader.inputs['Emission Color'])
            shader.inputs['Emission Strength'].default_value = 2.4
        result.append(mat)
    return result


def finish(obj, name, mat, parent, color=IVORY, bevel=0, glow=False):
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    if mat.name != 'Glass':
        attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for entry in attr.data:
            entry.color = linear(color)
    if mat.name == 'Hardware':
        uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
        for entry in uv.data:
            entry.uv = (.75 if glow else .25, .5)
    else:
        for uv in list(obj.data.uv_layers):
            obj.data.uv_layers.remove(uv)
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, location, dimensions, mat, parent, color=IVORY, bevel=.002, glow=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, parent, color, min(bevel, min(dimensions) * .2), glow)


def disc(name, location, radius, depth, mat, parent, color=SILVER, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return finish(obj, name, mat, parent, color, min(.0006, depth * .18))


def strap(name, parent, mat, color, segmented=False):
    # Closed elliptical band around the cushion, with eight-metal-link colour variation.
    count = 40
    vertices, faces = [], []
    for i in range(count):
        angle = i * math.tau / count
        for radius_y, radius_z in [(.061, .032), (.064, .035)]:
            for x in (-.010, .010):
                vertices.append((x, radius_y * math.sin(angle), radius_z * math.cos(angle)))
    for i in range(count):
        j = (i + 1) % count
        a, b = 4 * i, 4 * j
        faces += [(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2),
                  (a, a + 2, b + 2, b), (a + 1, b + 1, b + 3, a + 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    finish(obj, name, mat, parent, color)
    if segmented:
        attr = mesh.color_attributes['Color']
        for face in mesh.polygons:
            if (face.index // 4) % 2:
                for index in face.loop_indices:
                    attr.data[index].color = linear(tuple(v * .68 for v in color))


def watch(root, index, x, y, soft, hardware):
    group = bpy.data.objects.new(f'WATCH_{index:02d}', None)
    bpy.context.scene.collection.objects.link(group)
    group.parent = root
    group.location = (x, y, .765)
    group.rotation_euler.x = math.radians(14)
    group['face_shape'] = 'round' if index % 2 == 0 else 'square'
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1)
    cushion = bpy.context.object
    cushion.scale = (.054, .058, .029)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for face in cushion.data.polygons:
        face.use_smooth = True
    finish(cushion, f'CUSHION_{index:02d}', soft, group, PILLOW)
    metal = SILVER if index % 3 else CHAMPAGNE
    strap(f'STRAP_{index:02d}', group, hardware if index % 3 == 0 else soft,
          metal if index % 3 == 0 else ((.22, .13, .09) if index % 2 else CHARCOAL), index % 3 == 0)
    face_color = [(.10, .23, .28), (.85, .82, .69), (.12, .14, .16), (.24, .36, .30)][index % 4]
    if index % 2 == 0:
        disc(f'CASE_Round_{index:02d}', (0, 0, .038), .025, .008, hardware, group, metal, 32)
        disc(f'DIAL_{index:02d}', (0, 0, .0425), .021, .0015, soft, group, face_color, 32)
    else:
        box(f'CASE_Square_{index:02d}', (0, 0, .038), (.047, .045, .008), hardware, group, metal, .0015)
        box(f'DIAL_{index:02d}', (0, 0, .0425), (.039, .037, .0015), soft, group, face_color, .0005)
    for side in (-1, 1):
        for xx in (-.010, .010):
            box(f'LUG_{index:02d}', (xx, side * .024, .034), (.006, .010, .008), hardware, group, metal, .0007)
    crown = disc(f'CROWN_{index:02d}', (.027, 0, .037), .003, .005, hardware, group, metal, 12)
    crown.rotation_euler.y = math.pi / 2
    # Geometric baton markers and hands only: no numerals, lettering or logo.
    marker_color = (.88, .83, .65) if index % 2 == 0 else (.25, .29, .27)
    for tick in range(12):
        angle = tick * math.tau / 12
        marker = box(f'MARKER_{index:02d}', (.017 * math.sin(angle), .017 * math.cos(angle), .0435),
                     (.0011, .0030 if tick % 3 == 0 else .0018, .0005), hardware, group, marker_color, 0)
        marker.rotation_euler.z = -angle
    for hand, length, angle in [('Hour', .012, -55), ('Minute', .017, 45)]:
        angle = math.radians(angle)
        obj = box(f'HAND_{hand}_{index:02d}', (math.sin(angle) * length / 2, math.cos(angle) * length / 2, .0442),
                  (.0014, length, .0008), hardware, group, marker_color, .0001)
        obj.rotation_euler.z = -angle
    disc(f'PIN_{index:02d}', (0, 0, .0448), .002, .001, hardware, group, metal, 12)


def build(root):
    soft, hardware, glass = materials()
    box('BASE_Platform', (0, 0, .033), (1, .5, .066), soft, root, CHARCOAL, .009)
    box('BASE_Recess', (0, 0, .082), (.91, .42, .032), soft, root, CHARCOAL, .004)
    box('CABINET_Core', (0, 0, .393), (.974, .474, .59), soft, root, CHARCOAL, .009)
    box('CABINET_FrontPanel', (0, -.240, .397), (.928, .006, .536), soft, root, IVORY, .002)
    for x in (-.239, .239):
        box('CABINET_RearDoor', (x, .239, .396), (.463, .006, .534), soft, root, IVORY, .002)
        box('CABINET_RecessedPull', (x, .243, .608), (.10, .004, .012), soft, root, CHARCOAL, .001)
    for x in (-.488, .488):
        box('CABINET_EndPanel', (x, 0, .397), (.006, .426, .536), soft, root, IVORY, .001)
    box('FRAME_Deck', (0, 0, .696), (1, .5, .028), hardware, root, CHAMPAGNE, .003)
    box('TRAY_Velvet', (0, 0, .718), (.914, .414, .020), soft, root, VELVET, .005)
    for x in (-.447, .447):
        box('TRAY_EndRim', (x, 0, .735), (.016, .398, .020), soft, root, VELVET, .003)
    for y in (-.192, .192):
        box('TRAY_LongRim', (0, y, .735), (.88, .016, .020), soft, root, VELVET, .003)
    for row, y in enumerate((-.098, .098)):
        for col, x in enumerate((-.324, -.108, .108, .324)):
            box('TRAY_Cell', (x, y, .732), (.165, .168, .012), soft, root, CHARCOAL, .004)
            watch(root, row * 4 + col, x, y, soft, hardware)
    for x in (-.489, .489):
        for y in (-.239, .239):
            box('FRAME_Post', (x, y, .827), (.018, .018, .238), hardware, root, CHAMPAGNE, .0015)
    for y in (-.239, .239):
        box('FRAME_TopLong', (0, y, .953), (1, .022, .014), hardware, root, CHAMPAGNE, .002)
        box('LIGHT_Diffuser', (0, y * .92, .940), (.944, .006, .005), hardware, root, (1, .92, .73), .0007, True)
        box('GLASS_Long', (0, y, .824), (.960, .004, .230), glass, root, bevel=.0003)
    for x in (-.489, .489):
        box('FRAME_TopEnd', (x, 0, .953), (.022, .456, .014), hardware, root, CHAMPAGNE, .002)
        box('GLASS_End', (x, 0, .824), (.004, .454, .230), glass, root, bevel=.0003)
    box('GLASS_Top', (0, 0, .951), (.964, .456, .006), glass, root, bevel=.0005)


def aim(obj):
    obj.rotation_euler = (Vector(TARGET) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .25, .29, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.001))
    bpy.context.object.name = 'STUDIO_Floor'
    floor = bpy.data.materials.new('Studio floor only')
    floor.diffuse_color = (.26, .30, .33, 1)
    bpy.context.object.data.materials.append(floor)
    for name, location, energy, size in [('Key', (-2, -3, 4), 500, 3),
                                         ('Fill', (3, -1, 3), 260, 2.5),
                                         ('Rim', (1, 3, 4), 550, 2)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy = energy
        obj.data.size = size
        aim(obj)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 1.53
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'


def export(path):
    """Bake evaluated editable parts into temporary batches without touching source."""
    root = bpy.data.objects[ROOT]
    root.name = 'SOURCE_WatchDisplayCase'
    export_root = bpy.data.objects.new(ROOT, None)
    bpy.context.scene.collection.objects.link(export_root)
    for key in root.keys():
        export_root[key] = root[key]
    try:
        bpy.context.view_layer.update()
        graph = bpy.context.evaluated_depsgraph_get()
        groups = {}
        for obj in sorted(root.children_recursive, key=lambda part: part.name):
            if obj.type != 'MESH':
                continue
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph), preserve_all_data_layers=True,
                                                  depsgraph=graph)
            mesh.transform(root.matrix_world.inverted() @ obj.matrix_world)
            copy = bpy.data.objects.new('EXPORT_' + obj.name, mesh)
            bpy.context.scene.collection.objects.link(copy)
            copy.parent = export_root
            groups.setdefault(obj.data.materials[0].name, []).append(copy)
        for name, parts in sorted(groups.items()):
            bpy.ops.object.select_all(action='DESELECT')
            for part in parts:
                part.select_set(True)
            bpy.context.view_layer.objects.active = parts[0]
            bpy.ops.object.join()
            parts[0].name = 'BATCH_' + name.replace(' ', '')
        bpy.ops.object.select_all(action='DESELECT')
        export_root.select_set(True)
        for obj in export_root.children_recursive:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=True, export_extras=True,
                                  export_cameras=False, export_lights=False)
        canonicalize_indices(path)
    finally:
        for obj in list(export_root.children_recursive):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.objects.remove(export_root, do_unlink=True)
        root.name = ROOT


def canonicalize_indices(path):
    """Stabilize exporter thread-dependent triangle order; retain every vertex and winding."""
    data = bytearray(path.read_bytes())
    json_size = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + json_size])
    binary_start = 28 + json_size
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            assert primitive.get('mode', 4) == 4
            accessor = document['accessors'][primitive['indices']]
            view = document['bufferViews'][accessor['bufferView']]
            assert not view.get('byteStride') and not accessor.get('sparse')
            code = {5121: 'B', 5123: 'H', 5125: 'I'}[accessor['componentType']]
            count = accessor['count']
            assert count % 3 == 0
            offset = binary_start + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            values = struct.unpack_from('<' + code * count, data, offset)
            triangles = sorted(tuple(values[i:i + 3]) for i in range(0, count, 3))
            struct.pack_into('<' + code * count, data, offset,
                             *(value for triangle in triangles for value in triangle))
    path.write_bytes(data)


def render_views():
    scene = bpy.context.scene
    for name, location in [('hero', (1.6, -2.5, 2.0)), ('front', (0, -3, .98)),
                           ('side', (3, 0, 1.1)), ('3q', (-1.6, -2.2, 2.6))]:
        scene.camera.location = location
        aim(scene.camera)
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.image_settings.quality = 88
        bpy.data.images['Render Result'].save_render(str(HERE / 'previews' / (name + '.webp')), scene=scene)


def main():
    for folder in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
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
        root['origin'] = 'Floor centre of base footprint'
        root['scope'] = 'Static unbranded watch showcase; S15 / P2'
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
