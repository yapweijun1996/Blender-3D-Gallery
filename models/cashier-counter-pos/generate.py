"""Original deterministic cashier station. Blender 5.2.3; no external assets."""
from pathlib import Path
import math
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'cashier-counter-pos'
ROOT = 'ASSET_CashierCounterPOS'
TARGET = (0, 0, .73)


def material(name, rgb, roughness, metallic=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    m.diffuse_color = color
    shader = m.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = color
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    return m


def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    return o


def finish(o, name, mat, parent, bevel):
    o.name = name
    o.data.materials.append(mat)
    o.parent = parent
    if bevel:
        mod = o.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = min(bevel, min(o.dimensions) * .4)
        mod.segments = 3
        o.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
    return o


def box(name, loc, dims, mat, parent, bevel=.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, mat, parent, bevel)


def rod(name, a, b, radius, mat, parent):
    a, b = Vector(a), Vector(b)
    delta = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=delta.length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_euler = delta.to_track_quat('Z', 'Y').to_euler()
    return finish(o, name, mat, parent, .001)


def build(root):
    ivory = material('Porcelain laminate', (.88, .86, .80), .48)
    petrol = material('Muted petrol enamel', (.22, .40, .41), .36, .12)
    dark = material('Graphite satin', (.065, .085, .095), .28, .10)
    # Counter front is Blender -Y; export converts this to glTF +Z.
    box('COUNTER_RecessedPlinth', (0, 0, .045), (1.25, .55, .09), dark, root, .006)
    box('COUNTER_LowerDeck', (0, 0, .105), (1.32, .61, .04), ivory, root)
    for x in [-.64, .64]:
        box('COUNTER_SidePanel', (x, 0, .51), (.04, .61, .81), ivory, root)
    box('COUNTER_FrontBacking', (0, -.282, .51), (1.24, .04, .81), dark, root)
    for x in [-.318, .318]:
        box('COUNTER_FrontFascia', (x, -.307, .51), (.625, .022, .80), petrol, root, .006)
    box('COUNTER_Reveal', (0, 0, .913), (1.35, .64, .014), dark, root, .003)
    box('COUNTER_Countertop', (0, 0, .935), (1.40, .70, .03), ivory, root, .012)
    box('COUNTER_Divider', (.08, .015, .50), (.032, .55, .77), ivory, root)
    box('COUNTER_OpenShelf', (.36, .01, .46), (.53, .55, .025), ivory, root)
    box('COUNTER_StaffCupboard', (-.28, .278, .42), (.64, .025, .58), petrol, root)
    box('COUNTER_CupboardPull', (-.04, .297, .64), (.08, .018, .018), dark, root, .005)
    # Cash drawer is beneath the worktop and faces the staff aisle (+Y).
    box('DRAWER_Case', (-.28, .04, .824), (.65, .52, .135), dark, root, .005)
    box('DRAWER_Front', (-.28, .307, .824), (.624, .018, .108), petrol, root, .006)
    box('DRAWER_FingerRecess', (-.28, .318, .835), (.23, .006, .019), dark, root, .004)
    box('DRAWER_Lock', (-.49, .318, .82), (.016, .006, .016), ivory, root, .005)
    # Main touchscreen has a deliberately blank, dark inset and no UI or text.
    box('POS_Base', (-.29, .045, .964), (.255, .225, .028), dark, root, .012)
    rod('POS_TiltStem', (-.29, .075, .977), (-.29, .075, 1.16), .026, petrol, root)
    rod('POS_TiltAxle', (-.35, .075, 1.16), (-.23, .075, 1.16), .029, dark, root)
    screen = empty('POS_ScreenTilt', root, (-.29, .07, 1.275))
    screen.rotation_euler.x = math.radians(14)
    box('POS_Housing', (0, 0, 0), (.435, .052, .295), petrol, screen, .014)
    box('POS_BlankDarkTouchscreen', (0, .030, .003), (.385, .009, .241), dark, screen, .009)
    box('POS_RearCover', (0, -.029, -.012), (.22, .015, .12), dark, screen, .01)
    rod('POS_Cable', (-.29, .10, .98), (-.29, .10, 1.15), .006, dark, root)
    # Receipt printer sits beside the POS, with a dark paper exit and blank receipt.
    box('PRINTER_Body', (.085, .14, 1.021), (.185, .205, .142), petrol, root, .014)
    box('PRINTER_Lid', (.085, .14, 1.093), (.178, .195, .018), dark, root, .009)
    box('PRINTER_PaperSlot', (.085, .246, 1.065), (.143, .006, .012), dark, root, .002)
    paper = box('PRINTER_BlankReceipt', (0, 0, 0), (.078, .067, .002), ivory, root, .0005)
    paper.rotation_euler.x = math.radians(-27)
    # Anchor the paper's rear edge inside the slot; the free end feeds downward.
    paper.location = Vector((.085, .244, 1.065)) + paper.rotation_euler.to_matrix() @ Vector((0, .0335, 0))
    box('PRINTER_FeedButton', (.151, .22, 1.106), (.018, .022, .005), ivory, root, .003)
    # Card reader is angled upward toward the customer, within the countertop.
    box('CARD_Base', (-.23, -.227, .958), (.135, .13, .016), dark, root, .006)
    reader = empty('CARD_CustomerTilt', root, (-.23, -.225, 1.053))
    reader.rotation_euler.x = math.radians(-55)
    # Embed the support tip 4 mm into the tilted housing's rear surface.
    attachment = reader.location + reader.rotation_euler.to_matrix() @ Vector((0, .0135, -.018))
    rod('CARD_Support', (-.23, -.22, .966), attachment, .018, petrol, root)
    box('CARD_Housing', (0, 0, 0), (.115, .035, .175), petrol, reader, .009)
    box('CARD_BlankScreen', (0, -.020, .034), (.087, .006, .063), dark, reader, .004)
    for x in [-.025, 0, .025]:
        for z in [-.01, -.035, -.06]:
            box('CARD_UnmarkedKey', (x, -.021, z), (.016, .006, .014), ivory, reader, .002)
    box('CARD_ChipSlot', (0, -.022, -.081), (.055, .004, .004), dark, reader, .001)
    # Compact T-bar bag holder with two forward hooks and raised end stops.
    box('BAG_Base', (.46, -.025, .961), (.27, .24, .022), dark, root, .009)
    rod('BAG_Upright', (.46, .035, .972), (.46, .035, 1.208), .010, petrol, root)
    rod('BAG_Crossbar', (.35, .035, 1.208), (.57, .035, 1.208), .008, petrol, root)
    for x in [.35, .57]:
        rod('BAG_Hook', (x, .035, 1.208), (x, -.13, 1.208), .008, petrol, root)
        rod('BAG_EndStop', (x, -.13, 1.208), (x, -.13, 1.238), .008, petrol, root)
    # Blank upright countertop sign, facing the customer.
    box('SIGN_Base', (.39, .237, .96), (.26, .12, .02), dark, root, .006)
    box('SIGN_Frame', (.39, .237, 1.087), (.25, .026, .22), petrol, root, .007)
    box('SIGN_BlankFace', (.39, .221, 1.087), (.219, .008, .188), ivory, root, .004)
    root['units'] = 'metres'
    root['up_axis'] = 'Blender +Z / glTF +Y'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['scope'] = 'Static original visual prop; no payment software or moving parts'


def export(path):
    """Batch evaluated copies by shared material; preserve editable source parts."""
    root = bpy.data.objects[ROOT]
    originals = [o for o in root.children_recursive if o.type == 'MESH']
    depsgraph = bpy.context.evaluated_depsgraph_get()
    groups = {}
    for o in originals:
        groups.setdefault(o.data.materials[0].name, []).append(o)
    batches = []
    try:
        for mat_name, parts in sorted(groups.items()):
            copies = []
            for part in parts:
                evaluated = part.evaluated_get(depsgraph)
                mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
                copy = bpy.data.objects.new('EXPORT_' + part.name, mesh)
                bpy.context.scene.collection.objects.link(copy)
                copy.matrix_world = part.matrix_world.copy()
                copies.append(copy)
            bpy.ops.object.select_all(action='DESELECT')
            for o in copies:
                o.select_set(True)
            bpy.context.view_layer.objects.active = copies[0]
            bpy.ops.object.join()
            batch = bpy.context.object
            batch.name = 'Geometry_' + mat_name.replace(' ', '_')
            batch.parent = root
            batch['source_parts'] = [o.name for o in parts]
            batches.append(batch)
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for o in batches:
            o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
            export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
            export_extras=True, export_cameras=False, export_lights=False)
    finally:
        for o in batches:
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Neutral studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.12, .15, .17, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .55
    for name, loc, energy, size in [('Key', (-3, 4, 5), 550, 4), ('Fill', (4, 1, 3), 350, 3), ('Rim', (0, -4, 4), 650, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy, o.data.size = energy, size
        aim(o, TARGET)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 2.05
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    views = [('hero', (2.3, 3.6, 2.35)), ('front', (0, -4, .95)),
             ('side', (4, .1, 1.25)), ('3q', (-2.5, -3.6, 2.6))]
    for name, position in views:
        s.camera.location = position
        aim(s.camera, TARGET)
        s.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        if name == 'hero':
            s.render.image_settings.file_format = 'JPEG'
            s.render.image_settings.quality = 90
            bpy.data.images['Render Result'].save_render(str(HERE / 'previews/hero.jpg'))
            s.render.image_settings.file_format = 'PNG'


def main():
    for folder in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / folder).mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        root = empty(ROOT)
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    bpy.context.view_layer.update()
    export(HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
