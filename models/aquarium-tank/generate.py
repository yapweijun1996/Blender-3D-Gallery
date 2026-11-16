"""Original deterministic aquarium. Blender 5.2.3; no external assets.

Template: self-checkout-machine. Native metres/+Z up/-Y front;
glTF metres/+Y up/+Z front. Editable source parts join by material on export.
"""
from pathlib import Path
import math
import random
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'aquarium-tank'
ROOT = 'ASSET_AquariumTank'
TARGET = (0, 0, .72)
RNG = random.Random(5283)
IVORY = (.74, .75, .69)
SLATE = (.12, .17, .18)
SAND = (.63, .55, .40)


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)


def material(name, rgb, alpha=1, roughness=.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*linear(rgb), 1)
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Alpha'].default_value = alpha
    m.diffuse_color = (*linear(rgb), alpha)
    if alpha < 1:
        m.surface_render_method = 'BLENDED'
        m.use_backface_culling = False
    else:
        attr = m.node_tree.nodes.new('ShaderNodeVertexColor')
        attr.layer_name = 'Color'
        m.node_tree.links.new(attr.outputs['Color'], p.inputs['Base Color'])
    return m


def empty(name, parent=None, location=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = location
    return o


def finish(o, name, m, root, rgb=None, bevel=0):
    o.name = name
    o.data.materials.append(m)
    bpy.context.view_layer.objects.active = o
    if bevel:
        mod = o.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = min(bevel, min(o.dimensions) * .45)
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if rgb is not None:
        attr = o.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for face in o.data.polygons:
            # Small deterministic per-face variation makes stones and leaves legible.
            factor = RNG.uniform(.93, 1.04) if name.startswith(('ROCK', 'LEAF', 'GRAVEL')) else 1
            color = (*linear(tuple(min(1, v * factor) for v in rgb)), 1)
            for i in face.loop_indices:
                attr.data[i].color = color
    o.parent = root
    return o


def box(name, location, dimensions, m, root, rgb=None, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    o = bpy.context.object
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, m, root, rgb, bevel)


def rod(name, a, b, radius, m, root, rgb):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=7, radius=radius, depth=d.length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return finish(o, name, m, root, rgb)


def rock(name, location, dimensions, m, root, rgb, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=location)
    o = bpy.context.object
    for v in o.data.vertices:
        v.co *= RNG.uniform(.89, 1.08)
    o.scale = dimensions
    o.rotation_euler = tuple(RNG.uniform(-.25, .25) for _ in range(3))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, m, root, rgb)


def leaf(name, base, angle, length, width, lean, m, root, rgb):
    vertices, faces = [], []
    bx, by, bz = base
    for step in range(7):
        t = step / 6
        # A closed pointed ribbon with a raised centre rib; no degenerate tips.
        w = width * (.045 + math.sin(math.pi * t) ** .8)
        offset = lean * t ** 1.5
        for side in (-1, 0, 1):
            vertices.append((max(-.94, min(.94, bx + math.cos(angle) * offset - math.sin(angle) * w * side)),
                             max(-.34, min(.34, by + math.sin(angle) * offset + math.cos(angle) * w * side)),
                             bz + length * t + (.006 * math.sin(math.pi * t) if side == 0 else 0)))
    for step in range(6):
        for lane in range(2):
            i = step * 3 + lane
            faces.append((i, i + 1, i + 4, i + 3))
    # Intentional leaf ribbons use the shared double-sided opaque material.
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    return finish(o, name, m, root, rgb)


def build(root):
    opaque = material('Opaque vertex palette', (1, 1, 1))
    glass = material('Clear pale glass', (.67, .84, .82), .035, .12)
    water = material('Transparent aqua water', (.19, .51, .48), .07, .18)
    box('CABINET_RecessedPlinth', (0, 0, .03), (1.86, .68, .06), opaque, root, SLATE, .006)
    box('CABINET_ShadowCore', (0, 0, .28), (1.96, .756, .44), opaque, root, SLATE, .005)
    for x in (-.484, .484):
        box('CABINET_Door', (x, -.383, .279), (.956, .026, .416), opaque, root, IVORY, .007)
        box('CABINET_RecessedGrip', (x, -.397, .459), (.22, .006, .015), opaque, root, SLATE, .003)
    for x in (-.979, .979):
        box('CABINET_EndPanel', (x, .004, .28), (.022, .76, .44), opaque, root, IVORY, .005)
    box('CABINET_Top', (0, 0, .52), (2, .8, .04), opaque, root, IVORY, .008)

    # Glass outside dimensions 1.96 x .76 x .80 m; wall thickness 12 mm.
    for y in (-.374, .374):
        box('GLASS_LongPane', (0, y, .94), (1.96, .012, .8), glass, root)
    for x in (-.974, .974):
        box('GLASS_EndPane', (x, 0, .94), (.012, .736, .8), glass, root)
    box('GLASS_Base', (0, 0, .546), (1.936, .736, .012), glass, root)
    for z, h in ((.551, .022), (1.331, .018)):
        for y in (-.377, .377):
            box('FRAME_LongRail', (0, y, z), (1.972, .018, h), opaque, root, SLATE, .002)
        for x in (-.977, .977):
            box('FRAME_EndRail', (x, 0, z), (.018, .736, h), opaque, root, SLATE, .002)
    for x in (-.975, .975):
        for y in (-.375, .375):
            box('GLASS_EdgeSeam', (x, y, .94), (.004, .004, .76), opaque, root, (.39, .55, .52))
    box('WATER_Volume', (0, 0, .9135), (1.932, .732, .723), water, root)
    for y in (-.365, .365):
        box('WATERLINE_Long', (0, y, 1.275), (1.932, .0015, .0025), opaque, root, (.39, .63, .59))
    for x in (-.965, .965):
        box('WATERLINE_End', (x, 0, 1.275), (.0015, .732, .0025), opaque, root, (.39, .63, .59))
    # Two removable clear lids; a rear service gap stays open.
    for x in (-.482, .482):
        box('LID_ClearPanel', (x, -.015, 1.343), (.95, .69, .006), glass, root)
        box('LID_LiftTab', (x, -.20, 1.350), (.055, .035, .008), opaque, root, SLATE, .002)
    for x in (-.85, .85):
        box('LIGHT_Foot', (x, .015, 1.352), (.07, .13, .025), opaque, root, SLATE, .003)
        box('LIGHT_Bracket', (x, .015, 1.378), (.025, .035, .05), opaque, root, SLATE, .002)
    box('LIGHT_Bar', (0, .015, 1.408), (1.83, .085, .03), opaque, root, SLATE, .007)
    box('LIGHT_Diffuser', (0, .014, 1.3915), (1.72, .060, .006), opaque, root, (.95, .96, .84), .002)

    box('SUBSTRATE_SandBed', (0, 0, .580), (1.928, .728, .056), opaque, root, SAND, .012)
    for i in range(90):
        x, y = RNG.uniform(-.92, .92), RNG.uniform(-.33, .33)
        r = RNG.uniform(.006, .015)
        rock(f'GRAVEL_{i:03}', (x, y, .609), (r, r * .8, r * .45), opaque, root,
             (.69, .62, .49))
    for i, (loc, size) in enumerate((
        ((-.66, .12, .72), (.23, .17, .17)),
        ((-.80, .13, .82), (.13, .12, .23)),
        ((-.48, .18, .66), (.17, .13, .08)),
        ((.70, .15, .69), (.22, .17, .13)),
        ((.51, .22, .65), (.12, .10, .07)),
        ((.82, -.02, .64), (.10, .08, .05)))):
        rock(f'ROCK_{i:02}', loc, size, opaque, root, (.36, .41, .38), 2)
    # Rear and side vegetation keeps the centre clear for a separately placed koi.
    for cluster, (x, y, height) in enumerate(((-.84, .26, .53), (-.56, .27, .44),
            (.83, .26, .55), (.60, .28, .47), (-.83, -.16, .24), (.75, -.18, .22))):
        for j in range(7):
            angle = j * math.tau / 7 + RNG.uniform(-.22, .22)
            length = height * RNG.uniform(.65, 1.0)
            lean = RNG.uniform(.05, .14)
            base = (x + RNG.uniform(-.025, .025), y + RNG.uniform(-.02, .02), .608)
            leaf(f'LEAF_Ribbon_{cluster}_{j}', base, angle, length, .018, lean,
                 opaque, root, (.20 + j * .008, .42 + j * .012, .22))
        for j in range(2):
            base = Vector((x, y, .61))
            top = Vector((x + .025 * (j * 2 - 1), y, .61 + height * .85))
            rod('PLANT_Stem', base, top, .004, opaque, root, (.23, .38, .19))
            for level in range(1, 4):
                p = base.lerp(top, level / 4)
                leaf(f'LEAF_Broad_{cluster}_{j}_{level}', p, j * math.pi + level * 2,
                     .075, .025, .065, opaque, root, (.28, .49, .25))

    anchor = empty('ANCHOR_Fish', root, (0, -.05, .98))
    anchor['purpose'] = 'Intended origin for a separately scaled koi; no fish included'
    # Z reverses during Blender-to-glTF conversion; names refer to glTF bounds.
    for name, loc in (('SWIM_Min', (-.38, .18, .80)), ('SWIM_Max', (.38, -.22, 1.18))):
        empty(name, root, loc)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['origin'] = 'floor centre'
    root['seed'] = 5283
    root['scope'] = 'Static visual aquarium; no fish, animation, simulation or exported lights'


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Neutral studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .27, .29, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    # Studio geometry is outside the asset root and excluded from export.
    floor = material('STUDIO_Stone', (.66, .69, .68))
    box('STUDIO_Floor', (0, 0, -.04), (200, 200, .08), floor, None, (.66, .69, .68))
    for name, loc, power, size in (('Key', (-3, -4, 6), 850, 4),
            ('Fill', (4, -1, 3), 600, 3), ('Rim', (0, 3, 4), 950, 3)):
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy, o.data.size = power, size
        aim(o, TARGET)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.location = (3.1, -4.8, 2.65)
    s.camera.data.ortho_scale = 2.8
    aim(s.camera, TARGET)
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.cycles.seed = 5283
    s.render.resolution_x = s.render.resolution_y = 768
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    requested = next((a.split('=', 1)[1].split(',') for a in sys.argv if a.startswith('--views=')), None)
    for name, loc in (('hero', (3.1, -4.8, 2.65)), ('front', (0, -10, 1.85)),
                       ('side', (10, 0, 1.85)), ('3q', (-3, -4, 2.1))):
        if requested and name not in requested:
            continue
        s.camera.location = loc
        s.camera.data.ortho_scale = 2.80 if name in ('hero', '3q') else 2.50
        aim(s.camera, TARGET)
        s.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def export(path):
    root = bpy.data.objects[ROOT]
    copies = []
    for material_name, name in (('Opaque vertex palette', 'DETAILS_Opaque'),
            ('Clear pale glass', 'GLASS_Panels'), ('Transparent aqua water', 'WATER_Volume')):
        bpy.ops.object.select_all(action='DESELECT')
        group = []
        for source in list(root.children_recursive):
            if source.type == 'MESH' and source.data.materials[0].name == material_name:
                o = source.copy()
                o.data = source.data.copy()
                bpy.context.scene.collection.objects.link(o)
                o.select_set(True)
                group.append(o)
        bpy.context.view_layer.objects.active = group[0]
        if len(group) > 1:
            bpy.ops.object.join()
        o = bpy.context.object
        o.name = 'EXPORT_' + name
        o.data.name = name
        copies.append(o)
    try:
        bpy.ops.object.select_all(action='DESELECT')
        root.select_set(True)
        for o in copies + [o for o in root.children if o.type == 'EMPTY']:
            o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
            export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
            export_extras=True, export_cameras=False, export_lights=False)
    finally:
        for o in copies:
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(mesh)


def main():
    for d in ('sources', 'exports', 'previews', 'reports', 'metadata'):
        (HERE / d).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        RNG.seed(5283)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system, s.unit_settings.scale_length = 'METRIC', 1
        build(empty(ROOT))
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    if '--render-only' not in sys.argv:
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
