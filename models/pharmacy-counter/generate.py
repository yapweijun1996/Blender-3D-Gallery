"""Original deterministic pharmacy service counter. Blender 5.2.3; no external assets."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'pharmacy-counter'
ROOT = 'ASSET_PharmacyCounter'
TARGET = (0, 0, 1.08)


def material(name, rgb, metallic=0, roughness=.4, alpha=1):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (alpha,)
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Alpha'].default_value = alpha
    mat.diffuse_color = color
    if alpha < 1:
        mat.surface_render_method = 'BLENDED'
        mat.use_transparency_overlap = False
    return mat


def box(name, location, dimensions, mat, root, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    obj.parent = root
    if bevel:
        mod = obj.modifiers.new('Manufactured edge', 'BEVEL')
        mod.width = min(bevel, min(dimensions) * .24)
        mod.segments = 2
        obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return obj


def digit(number, x, y, bottom, height, mat, root):
    # Original seven-segment geometry; no font, label, logo or packaging.
    patterns = {'0': 'abcdef', '4': 'fgbc', '2': 'abged'}
    for segment in patterns[number]:
        if segment in 'agd':
            z = {'a': .94, 'g': .50, 'd': .06}[segment]
            location = (x, y, bottom + z * height)
            dimensions = (.38 * height, .002, .065 * height)
        else:
            side = .22 if segment in 'bc' else -.22
            z = .72 if segment in 'bf' else .28
            location = (x + side * height, y, bottom + z * height)
            dimensions = (.065 * height, .002, .32 * height)
        box('QUEUE_Digit_' + number + '_' + segment, location, dimensions, mat, root, .0003)


def build(root):
    porcelain = material('Porcelain', (.86, .87, .84), roughness=.43)
    graphite = material('Graphite', (.20, .245, .255), metallic=.12, roughness=.36)
    glass = material('Glass', (.51, .72, .74), roughness=.16, alpha=.24)
    box('COUNTER_Platform', (0, 0, .045), (2.84, .68, .09), graphite, root, .008)
    box('COUNTER_Floor', (0, 0, .113), (2.94, .73, .046), porcelain, root, .006)
    for side, x in [('Left', -1.465), ('Right', 1.465)]:
        box('COUNTER_End_' + side, (x, 0, .493), (.07, .76, .714), porcelain, root, .009)
    for index, x in enumerate([-1, 0, 1]):
        box('COUNTER_Front_' + str(index), (x, -.357, .493), (.984, .056, .714), porcelain, root, .007)
    box('COUNTER_Reveal', (0, -.387, .739), (2.85, .006, .017), graphite, root, .001)
    box('COUNTER_Top', (0, 0, .876), (3, .8, .048), graphite, root, .012)
    # Open staff-side storage and a rear-edge rack keep the complete footprint at 3 x .8 m.
    box('STORAGE_LowerShelf', (0, .015, .455), (2.85, .65, .028), porcelain, root, .004)
    for x in [-.5, .5]:
        box('STORAGE_Divider_' + str(x), (x, .015, .493), (.03, .65, .714), porcelain, root)
    for side, x in [('Left', -1.43), ('Right', -.57)]:
        box('DISPENSING_Side_' + side, (x, .282, 1.36), (.028, .224, .92), porcelain, root, .004)
    box('DISPENSING_Divider', (-1, .282, 1.36), (.022, .224, .92), porcelain, root)
    for index, z in enumerate([.915, 1.213, 1.511, 1.809]):
        box('DISPENSING_Shelf_' + str(index), (-1, .282, z), (.888, .224, .022), graphite, root, .003)
        if index < 3:
            box('DISPENSING_FrontLip_' + str(index), (-1, .175, z + .019), (.86, .01, .028), porcelain, root, .001)
            box('DISPENSING_RearLip_' + str(index), (-1, .389, z + .019), (.86, .01, .028), porcelain, root, .001)
    # Glazing sits above the real service top; the central lower aperture is empty.
    for side, x in [('Left', -1.43), ('Right', 1.43)]:
        box('PARTITION_OuterPost_' + side, (x, -.19, 1.56), (.04, .05, 1.32), graphite, root, .003)
    for side, x in [('Left', -.42), ('Right', .42)]:
        box('PARTITION_WindowPost_' + side, (x, -.19, 1.402), (.026, .036, 1.004), graphite, root, .002)
    box('PARTITION_TopRail', (0, -.19, 1.89), (2.9, .038, .028), graphite, root, .002)
    for side, x in [('Left', -.925), ('Right', .925)]:
        box('GLASS_' + side, (x, -.19, 1.401), (.978, .012, .948), glass, root, .002)
        box('PARTITION_BottomRail_' + side, (x, -.19, .915), (.984, .032, .024), graphite, root, .002)
    box('PARTITION_PassThroughRail', (0, -.19, 1.218), (.814, .036, .028), graphite, root, .002)
    box('GLASS_CentreUpper', (0, -.19, 1.5535), (.814, .012, .643), glass, root, .002)
    box('SIGN_Frame', (0, -.19, 2.095), (3, .115, .25), graphite, root, .008)
    box('SIGN_BlankFront', (0, -.2505, 2.095), (2.864, .006, .166), porcelain, root, .003)
    box('SIGN_BlankRear', (0, -.1295, 2.095), (2.864, .006, .166), porcelain, root, .003)
    # Shallow pickup tray bridges the partition opening without blocking it.
    box('PICKUP_TrayBase', (0, -.10, .906), (.59, .54, .012), porcelain, root, .003)
    for side, x in [('Left', -.289), ('Right', .289)]:
        box('PICKUP_Side_' + side, (x, -.10, .923), (.012, .54, .034), porcelain, root, .002)
    box('PICKUP_RearLip', (0, .164, .923), (.566, .012, .034), porcelain, root, .002)
    box('PICKUP_FrontLip', (0, -.364, .918), (.566, .012, .024), porcelain, root, .002)
    box('QUEUE_Base', (.95, -.30, .908), (.23, .13, .016), porcelain, root, .004)
    box('QUEUE_Stem', (.95, -.285, .972), (.032, .032, .128), graphite, root, .003)
    box('QUEUE_Housing', (.95, -.302, 1.105), (.32, .055, .18), graphite, root, .006)
    for number, x in zip('042', [.87, .95, 1.03]):
        digit(number, x, -.331, 1.0625, .085, porcelain, root)


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .25, .29, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    floor_mat = material('Studio floor only', (.64, .67, .69), roughness=.8)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.004))
    bpy.context.object.name = 'STUDIO_Floor'
    bpy.context.object.data.materials.append(floor_mat)
    for name, location, energy, size in [('Key', (-3, -4, 6), 850, 4),
                                         ('Fill', (4, -1, 4), 550, 3),
                                         ('Rim', (0, 4, 5), 900, 3)]:
        bpy.ops.object.light_add(type='AREA', location=location)
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
    scene.camera.data.ortho_scale = 3.75
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.camera.location = (3.2, -5.5, 3.1)
    aim(scene.camera, TARGET)


def export(path):
    """Export evaluated copies, batching by the three shared materials; preserve saved edits."""
    root = bpy.data.objects[ROOT]
    root.name = 'SOURCE_PharmacyCounter'
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
            mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph))
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
            parts[0].name = 'BATCH_' + name
        bpy.ops.object.select_all(action='DESELECT')
        export_root.select_set(True)
        for obj in export_root.children_recursive:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in list(export_root.children_recursive):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.objects.remove(export_root, do_unlink=True)
        root.name = ROOT


def render_views():
    scene = bpy.context.scene
    selected = next((set(arg.split('=', 1)[1].split(',')) for arg in sys.argv if arg.startswith('--views=')), None)
    views = [('hero', (3.2, -5.5, 3.1)), ('front', (0, -6, 1.08)),
             ('side', (6, 0, 1.08)), ('3q', (-3.2, -5.5, 2.8)), ('rear', (3.2, 5.5, 3.1))]
    if selected is not None:
        assert selected <= {name for name, _ in views}, 'Unknown preview view'
    for name, location in views:
        if selected is not None and name not in selected:
            continue
        scene.camera.location = location
        aim(scene.camera, TARGET)
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.image_settings.quality = 85
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
        root['origin'] = 'Floor centre of complete 3 x 0.8 m counter footprint'
        root['scope'] = 'Static visual prop; no dispensing, queue logic or medical operation'
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
