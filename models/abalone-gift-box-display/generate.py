"""Original deterministic S10 countertop gift display. Blender 5.2.3, metres."""
from pathlib import Path
import bpy
import json
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'abalone-gift-box-display'
ROOT = 'ASSET_AbaloneGiftBoxDisplay'
PITCH = math.radians(62)
COLORS = {'red': (.43, .022, .032, 1), 'gold': (.66, .47, .22, 1),
          'black': (.025, .029, .033, 1), 'card': (.89, .84, .71, 1)}


def linear(c):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c[:3]) + (c[3],)


def material(name, color, metal, rough, vertex=False, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = linear(color)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    p.inputs['Alpha'].default_value = alpha
    m.diffuse_color = linear(color)
    if vertex:
        attr = m.node_tree.nodes.new('ShaderNodeVertexColor')
        attr.layer_name = 'Color'
        m.node_tree.links.new(attr.outputs['Color'], p.inputs['Base Color'])
    if alpha < 1:
        m.surface_render_method = 'BLENDED'
        m.use_transparency_overlap = False
    m.use_backface_culling = True
    return m


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    return o


def finish(o, name, mat, parent, color=None, bevel=0):
    o.name = name
    o.parent = parent
    o.data.materials.append(mat)
    if color:
        attr = o.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for value in attr.data:
            value.color = linear(color)
    if bevel:
        b = o.modifiers.new('Soft manufactured edges', 'BEVEL')
        b.width = bevel
        b.segments = 1
        o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o


def box(name, loc, dims, mat, parent, color=None, bevel=.001):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    finish(o, name, mat, parent, color, bevel)
    o.location = loc
    return o


def can(name, x, parent, gold):
    # One closed lathed tin with a raised rolled seam and recessed pressed lid.
    profile = [(.037, -.041), (.040, -.039), (.040, -.035), (.0385, -.033),
               (.0385, .032), (.040, .034), (.040, .039), (.037, .040),
               (.035, .037), (.029, .037), (.028, .036), (.024, .036)]
    n = 20
    verts = [(r * math.cos(math.tau * i / n), r * math.sin(math.tau * i / n), z)
             for r, z in profile for i in range(n)]
    faces = []
    for j in range(len(profile) - 1):
        for i in range(n):
            a = j * n + i
            b = j * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    faces.append(tuple(reversed(range(n))))
    faces.append(tuple((len(profile) - 1) * n + i for i in range(n)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    finish(o, name, gold, parent)
    o.location = (x, .006, -.002)
    for face in mesh.polygons:
        face.use_smooth = len(face.vertices) == 4 and face.index < n * 7
    return o


def gift(index, x, y, tier, color, root, lacquer, gold, glass):
    group = empty(f'GiftBox_{index:02d}', root)
    group['role'] = 'Clear-lid gift box with two unlabelled cans, ribbon and blank card'
    group['can_count'] = 2
    group.location = (x, y, tier + .079 * math.sin(PITCH) + .052 * math.cos(PITCH))
    group.rotation_euler.x = PITCH
    box('Gift_Floor', (0, 0, -.048), (.216, .15, .008), lacquer, group, color)
    for side in [-1, 1]:
        box('Gift_SideWall', (side * .104, 0, 0), (.008, .15, .088), lacquer, group, color)
        box('Gift_EndWall', (0, side * .071, 0), (.20, .008, .088), lacquer, group, color)
        box('Gift_LidRimSide', (side * .105, 0, .049), (.006, .152, .006), gold, group)
        box('Gift_LidRimEnd', (0, side * .073, .049), (.204, .006, .006), gold, group)
    # Thin clear top and four clear edge skirts; outward single-sided faces avoid
    # transparent back-face passes and keep the can lids visible in WebGL.
    w, d, z, bottom = .102, .070, .052, .043
    verts = [(-w, -d, z), (w, -d, z), (w, d, z), (-w, d, z),
             (-w, -d, bottom), (w, -d, bottom), (w, d, bottom), (-w, d, bottom)]
    faces = [(0, 1, 2, 3), (4, 5, 1, 0), (5, 6, 2, 1), (6, 7, 3, 2), (7, 4, 0, 3)]
    mesh = bpy.data.meshes.new('ClearLid')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    lid = bpy.data.objects.new('Gift_ClearLid', mesh)
    bpy.context.scene.collection.objects.link(lid)
    finish(lid, 'Gift_ClearLid', glass, group)
    can(f'PlainCan_{index:02d}_L', -.050, group, gold)
    can(f'PlainCan_{index:02d}_R', .050, group, gold)
    ribbon_mat = lacquer if color == COLORS['gold'] else gold
    ribbon_color = COLORS['red'] if ribbon_mat == lacquer else None
    box('Ribbon_Top', (0, 0, .054), (.013, .156, .003), ribbon_mat, group, ribbon_color, .0004)
    for side in [-1, 1]:
        box('Ribbon_End', (0, side * .077, .001), (.013, .002, .106), ribbon_mat, group, ribbon_color, .0004)
    card = box('BlankGiftCard', (.074, -.050, .056), (.043, .025, .002), lacquer, group, COLORS['card'], .0005)
    card.rotation_euler.z = -.12
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    low = min((o.matrix_world @ v.co).z for o in group.children
              if o.type == 'MESH' for v in o.evaluated_get(deps).data.vertices)
    group.location.z += tier - low
    bpy.context.view_layer.update()
    # A discreet cradle supports the leaning box's underside on the step.
    a = group.matrix_world @ Vector((0, -.035, -.052))
    b = group.matrix_world @ Vector((0, .065, -.052))
    verts = [(xx, yy, zz) for xx in [x - .055, x + .055]
             for yy, zz in [(a.y, tier), (b.y, tier), (b.y, b.z), (a.y, a.z)]]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh = bpy.data.meshes.new('Cradle')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    cradle = bpy.data.objects.new(f'Cradle_{index:02d}', mesh)
    bpy.context.scene.collection.objects.link(cradle)
    finish(cradle, cradle.name, lacquer, root, COLORS['black'])


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['origin'] = 'floor centre (countertop placement datum)'
    root['gift_boxes'] = 12
    root['plain_cans'] = 24
    lacquer = material('SharedLacquer', (1, 1, 1, 1), .12, .26, vertex=True)
    gold = material('SharedChampagneMetal', (.72, .61, .40, 1), .68, .29)
    glass = material('SharedClearLid', (.90, .96, 1, 1), 0, .12, alpha=.13)
    for name, loc, dims in [
        ('Riser_Base', (0, 0, .0225), (1, .5, .045)),
        ('Riser_Middle', (0, .083, .145), (1, .334, .20)),
        ('Riser_Rear', (0, .166, .345), (1, .168, .20))]:
        box(name, loc, dims, lacquer, root, COLORS['black'], .004)
    for y, h in [(-.244, .045), (-.078, .245), (.088, .445)]:
        box('Riser_ChampagneLip', (0, y, h + .003), (.96, .008, .006), gold, root, bevel=.001)
    for row, (y, h) in enumerate([(-.164, .045), (0, .245), (.164, .445)]):
        for col, x in enumerate([-.354, -.118, .118, .354]):
            color = [COLORS['red'], COLORS['gold'], COLORS['black']][(row + col) % 3]
            gift(row * 4 + col + 1, x, y, h, color, root, lacquer, gold, glass)
    for x in [-.12, .12]:
        box('Sign_Support', (x, .230, .580), (.009, .013, .270), gold, root)
    box('Sign_Frame', (0, .227, .805), (.37, .018, .19), gold, root, bevel=.003)
    box('BlankSignPanel', (0, .216, .805), (.349, .004, .169), lacquer, root, COLORS['card'], .0008)
    return root


def export(root, path):
    # Preserve separate editable source parts; only evaluated delivery copies merge.
    groups = {}
    deps = bpy.context.evaluated_depsgraph_get()
    copies = []
    for source in root.children_recursive:
        if source.type != 'MESH':
            continue
        mesh = bpy.data.meshes.new_from_object(source.evaluated_get(deps), depsgraph=deps)
        o = bpy.data.objects.new('BATCH_' + source.name, mesh)
        bpy.context.scene.collection.objects.link(o)
        o.matrix_world = source.matrix_world.copy()
        copies.append(o)
        groups.setdefault(source.data.materials[0].name, []).append(o)
    anchor = empty(ROOT + '_Export')
    anchor.name = ROOT + '_Delivery'
    for key, value in root.items():
        anchor[key] = value
    batches = []
    for name, objects in sorted(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = 'DISPLAY_' + name
        o.parent = anchor
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    anchor.select_set(True)
    for o in batches:
        o.select_set(True)
    original_name = root.name
    root.name = ROOT + '_Source'
    anchor.name = ROOT
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    for o in batches + [anchor]:
        bpy.data.objects.remove(o, do_unlink=True)
    root.name = original_name


def aim(o, point):
    o.rotation_euler = (Vector(point) - o.location).to_track_quat('-Z', 'Y').to_euler()


def render_views(root):
    # Render the delivered GLB, not a more detailed authoring substitute.
    for o in list(root.children_recursive) + [root]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE / 'exports/optimized.glb'))
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Neutral studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.14, .17, .21, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    target = (0, 0, .44)
    for name, loc, energy, size in [('Key', (-2, -3, 4), 420, 3), ('Fill', (3, -2, 2), 240, 2.5), ('Rim', (0, 3, 4), 480, 2)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        light = bpy.context.object
        light.name = 'STUDIO_' + name
        light.data.energy = energy
        light.data.shape = 'DISK'
        light.data.size = size
        aim(light, target)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 1.32
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 800
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'
    for name, pos in [('hero', (1.4, -2.8, 1.60)), ('front', (0, -3, .80)),
                      ('side', (3, -.05, .90)), ('3q', (-1.7, -2.7, 1.9))]:
        s.camera.location = pos
        aim(s.camera, target)
        s.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for name in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / name).mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
        root = bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = 1
        root = build()
        bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    bpy.context.view_layer.update()
    export(root, HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views(root)


if __name__ == '__main__':
    main()
