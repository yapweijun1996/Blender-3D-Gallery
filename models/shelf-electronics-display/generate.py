"""Original deterministic electronics cabinet; Blender 5.2.3, no external assets."""
from pathlib import Path
import bpy
import bmesh
import json
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'shelf-electronics-display'
ROOT = 'ASSET_ShelfElectronicsDisplay'
TARGET = (0, 0, .90)
IVORY = (.86, .87, .83)
SAGE = (.49, .62, .58)
CLAY = (.66, .48, .37)
GREY = (.52, .56, .58)


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def material(name, rgb, metallic=0, roughness=.45, colored=False, alpha=1):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = linear(rgb)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Alpha'].default_value = alpha
    mat.diffuse_color = linear(rgb)[:3] + (alpha,)
    if colored:
        shader.inputs['Base Color'].default_value = (1, 1, 1, 1)
        node = mat.node_tree.nodes.new('ShaderNodeVertexColor')
        node.layer_name = 'Color'
        mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
    if alpha < 1:
        mat.surface_render_method = 'DITHERED'
        mat.use_transparency_overlap = False
    return mat


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def finish(obj, name, mat, parent, bevel=0, color=IVORY):
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new('Manufactured edge', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        normal = obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
        bpy.ops.object.modifier_apply(modifier=normal.name)
    if mat.name == 'Ceramic':
        attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for item in attr.data:
            item.color = linear(color)
    return obj


def box(name, location, size, mat, parent, bevel=.003, color=IVORY):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, parent, min(bevel, min(size) * .40), color)


def cylinder(name, location, radius, height, mat, parent, color=IVORY, segments=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=height, location=location)
    obj = finish(bpy.context.object, name, mat, parent, min(.0015, height * .20, radius * .30), color)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def tube(name, points, radius, mat, parent, sides=8):
    points = [Vector(p) for p in points]
    vertices, faces = [], []
    for index, point in enumerate(points):
        tangent = (points[min(index + 1, len(points) - 1)] - points[max(index - 1, 0)]).normalized()
        reference = Vector((0, 1, 0)) if abs(tangent.y) < .9 else Vector((1, 0, 0))
        u = tangent.cross(reference).normalized()
        v = tangent.cross(u).normalized()
        for side in range(sides):
            angle = math.tau * side / sides
            vertices.append(point + radius * (math.cos(angle) * u + math.sin(angle) * v))
    for index in range(len(points) - 1):
        for side in range(sides):
            a = index * sides + side
            b = index * sides + (side + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.extend([tuple(reversed(range(sides))), tuple((len(points) - 1) * sides + side for side in range(sides))])
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
    finish(obj, name, mat, parent)
    for poly in mesh.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def gadget_box(name, x, y, floor, width, depth, height, color, ceramic, dark, root):
    group = empty(name, root)
    group['role'] = 'plain boxed device'
    box(name + '_Carton', (x, y, floor + height / 2), (width, depth, height), ceramic, group, .004, color)
    box(name + '_LidSeam', (x, y, floor + height * .81), (width + .001, depth + .001, .0025), dark, group, .0005)
    # A shallow unprinted inset suggests a generic device silhouette, never packaging text.
    box(name + '_BlankInset', (x, y - depth / 2 - .001, floor + height * .46),
        (width * .58, .002, height * .48), ceramic, group, .0007, IVORY)


def build(root):
    ceramic = material('Ceramic', IVORY, .02, .46, colored=True)
    dark = material('Graphite', (.13, .16, .17), .28, .38)
    glass = material('Glass', (.64, .81, .84), .02, .12, alpha=.055)
    fixture = empty('FIXTURE', root)
    for x in (-.50, .50):
        for y in (-.15, .15):
            box('BASE_FloorPad', (x, y, .008), (.10, .09, .016), dark, fixture, .003)
    box('BASE_ShadowPlinth', (0, 0, .062), (1.16, .41, .092), dark, fixture, .008)
    box('BASE_Cabinet', (0, 0, .147), (1.20, .45, .078), ceramic, fixture, .007)
    box('BACK_SolidPanel', (0, .208, .916), (1.15, .034, 1.46), ceramic, fixture, .003, GREY)
    for x in (-.58, .58):
        box('FRAME_SidePanel', (x, 0, .917), (.04, .45, 1.462), ceramic, fixture, .005)
        box('FRAME_FrontUpright', (x, -.218, .912), (.026, .014, 1.43), dark, fixture, .002)
    for index, z in enumerate((.207, .672, 1.137, 1.602), 1):
        box(f'SHELF_{index}_Deck', (0, -.004, z), (1.12, .416, .026), ceramic, fixture, .003)
        box(f'SHELF_{index}_Nosing', (0, -.218, z - .004), (1.118, .014, .022), dark, fixture, .002)
        for x in (-.547, .547):
            box(f'SHELF_{index}_Bracket', (x, .052, z - .034), (.018, .21, .042), dark, fixture, .002)
    box('HEADER_Frame', (0, 0, 1.7075), (1.20, .44, .185), dark, fixture, .006)
    box('HEADER_BlankPanel', (0, -.224, 1.7075), (1.11, .002, .125), ceramic, fixture, .0006)
    for tier, bottom in enumerate((.233, .698, 1.163), 1):
        for side in (-1, 1):
            x = side * .277
            box(f'GLASS_Tier{tier}_{side}_Pane', (x, -.209, bottom + .204), (.548, .003, .408), glass, fixture, .0005)
            box(f'DOOR_Tier{tier}_{side}_Edge', (side * .006, -.213, bottom + .204), (.009, .009, .408), dark, fixture, .001)
            box(f'DOOR_Tier{tier}_{side}_Handle', (side * .034, -.221, bottom + .205), (.013, .008, .075), dark, fixture, .002)
            for z in (bottom + .055, bottom + .353):
                box(f'DOOR_Tier{tier}_{side}_Hinge', (side * .548, -.211, z), (.018, .013, .027), dark, fixture, .002)
    # Lower boxed stock; upper cartons leave a dedicated hook rail at the right.
    for index, (x, width, height, color) in enumerate(((-.406, .17, .295, SAGE), (-.20, .16, .245, IVORY),
                                                      (.045, .195, .315, GREY), (.329, .225, .205, CLAY)), 1):
        gadget_box(f'BOX_Lower_{index}', x, -.013, .220, width, .17, height, color, ceramic, dark, root)
    for index, (x, width, height, color) in enumerate(((-.422, .14, .243, CLAY), (-.240, .145, .285, SAGE)), 1):
        gadget_box(f'BOX_Upper_{index}', x, .025, 1.150, width, .135, height, color, ceramic, dark, root)
    tablet = empty('TABLET_OnStand', root)
    tablet['role'] = 'generic tablet on a supported stand'
    box('TABLET_StandBase', (-.253, -.007, .698), (.255, .205, .026), dark, tablet, .007)
    tube('TABLET_StandStem', [(-.253, .045, .711), (-.253, .050, .788), (-.253, .055, .840)], .018, dark, tablet, 12)
    face = empty('TABLET_Tilt', tablet, (-.253, -.018, .905))
    face.rotation_euler.x = math.radians(-13)
    box('TABLET_Shell', (0, 0, 0), (.315, .023, .229), dark, face, .009)
    box('TABLET_BlankScreen', (0, -.0126, 0), (.282, .002, .195), ceramic, face, .0006, (.28, .39, .42))
    cylinder('TABLET_CameraDot', (0, -.014, .106), .002, .0015, dark, face, segments=12).rotation_euler.x = math.pi / 2
    speaker = empty('SPEAKER_Cylinder', root)
    speaker['role'] = 'generic cylindrical smart speaker'
    cylinder('SPEAKER_Foot', (.285, -.015, .695), .071, .020, dark, speaker)
    cylinder('SPEAKER_Body', (.285, -.015, .810), .073, .210, dark, speaker)
    cylinder('SPEAKER_Top', (.285, -.015, .922), .071, .014, ceramic, speaker, SAGE)
    for z in (.722, .750, .778, .806, .834, .862, .890):
        cylinder('SPEAKER_GrilleRib', (.285, -.015, z), .074, .004, ceramic, speaker, GREY)
    for x in (.265, .305):
        cylinder('SPEAKER_BlankButton', (x, -.015, .931), .006, .003, dark, speaker, segments=16)
    box('HOOK_Rail', (.258, .167, 1.495), (.514, .022, .032), dark, fixture, .003)
    for index, x in enumerate((.085, .258, .431), 1):
        cable = empty(f'CABLE_{index}_OnHook', root)
        cable['role'] = 'coiled cable on a J hook'
        points = [(x, .163, 1.495), (x, .105, 1.495), (x, .047, 1.495)]
        for step in range(1, 9):
            a = math.pi * step / 8
            points.append((x, .047 - .020 * math.sin(a), 1.515 - .020 * math.cos(a)))
        tube(f'HOOK_{index}_J', points, .004, dark, cable)
        coil = []
        for step in range(97):
            angle = math.tau * 2 * step / 96
            coil.append((x + .039 * math.sin(angle), .048 - .010 * step / 96, 1.408 + .082 * math.cos(angle)))
        tube(f'CABLE_{index}_Coil', coil, .003, dark, cable)
        tube(f'CABLE_{index}_Tail', [(x, .038, 1.490), (x + .047, .025, 1.462), (x + .053, .02, 1.323)], .003, dark, cable)
        box(f'CABLE_{index}_Connector', (x + .053, .02, 1.312), (.013, .012, .025), ceramic, cable, .002, GREY)
        box(f'CABLE_{index}_Plug', (x + .053, .02, 1.295), (.008, .008, .010), dark, cable, .001)
    return root


def export(path):
    """Batch evaluated saved source parts into three shared-material meshes."""
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    parts = sorted((obj for obj in root.children_recursive if obj.type == 'MESH'), key=lambda obj: obj.name)
    temporary = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    try:
        buckets = {}
        for obj in parts:
            data = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
            data.transform(obj.matrix_world)
            copy = bpy.data.objects.new('EXPORT_' + obj.name, data)
            bpy.context.scene.collection.objects.link(copy)
            copy.parent = root
            temporary.append(copy)
            buckets.setdefault(data.materials[0].name, []).append(copy)
        batches = []
        for name, objects in sorted(buckets.items()):
            bpy.ops.object.select_all(action='DESELECT')
            for obj in objects:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            batch = bpy.context.object
            batch.name = 'BATCH_' + name
            batches.append(batch)
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for obj in batches:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in temporary:
            try:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.meshes.remove(mesh)
            except ReferenceError:
                pass


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.23, .26, .29, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    floor = material('STUDIO_Floor', (.28, .31, .33), roughness=.8)
    box('STUDIO_Floor', (0, 0, -.027), (200, 200, .05), floor, None, 0)
    for name, loc, power, size in [('Key', (-3, -4, 5), 850, 3), ('Fill', (3, -2, 3), 500, 2.5), ('Rim', (1, 3, 4), 950, 2.5)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy = power
        obj.data.size = size
        aim(obj, TARGET)
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 2.27
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    for name, position in [('hero', (2.2, -4.4, 2.15)), ('front', (0, -5, 1.35)),
                           ('side', (5, 0, 1.35)), ('3q', (-2.5, -4, 2.1))]:
        if '--view' in sys.argv and name != sys.argv[sys.argv.index('--view') + 1]:
            continue
        scene.camera.location = position
        aim(scene.camera, TARGET)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for directory in ('sources', 'exports', 'metadata', 'previews', 'reports'):
        (HERE / directory).mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        root = empty(ROOT)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['origin'] = 'Floor centre'
        root['scope'] = 'Static original brand-neutral electronics display cabinet'
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
