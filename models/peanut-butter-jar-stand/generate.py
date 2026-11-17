"""Original deterministic S08 jar display; Blender 5.2.3, metres, no inputs."""
from pathlib import Path
import bpy
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'peanut-butter-jar-stand'
ROOT = 'ASSET_PeanutButterJarStand'
PALETTE = {
    'ivory': (.79, .76, .66), 'paper': (.94, .91, .80),
    'toe': (.22, .26, .22), 'paste': (.63, .39, .18),
    'lid': (.47, .24, .14), 'inset': (.69, .67, .57),
}


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def material(name, color, roughness, vertex=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = linear(color)
    p.inputs['Roughness'].default_value = roughness
    m.diffuse_color = linear(color)
    if vertex:
        attr = m.node_tree.nodes.new('ShaderNodeVertexColor')
        attr.layer_name = 'Color'
        m.node_tree.links.new(attr.outputs['Color'], p.inputs['Base Color'])
    m.use_backface_culling = True
    return m


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    return o


def color_mesh(o, colors):
    attr = o.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    for poly in o.data.polygons:
        c = linear(colors[poly.index] if isinstance(colors, list) else colors)
        for i in poly.loop_indices:
            attr.data[i].color = c


def box(name, loc, dims, mat, parent, color, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.parent = parent
    o.location = loc
    o.data.materials.append(mat)
    color_mesh(o, color)
    if bevel:
        b = o.modifiers.new('Rounded manufactured edges', 'BEVEL')
        b.width = min(bevel, min(dims) * .4)
        b.segments = 2
        o.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
    return o


def lathe(name, profile, parent, materials, label_segment=None):
    n = 24
    verts = [(r * math.cos(i * math.tau / n), r * math.sin(i * math.tau / n), z)
             for r, z in profile for i in range(n)]
    faces = []
    for ring in range(len(profile) - 1):
        for i in range(n):
            a = ring * n + i
            b = ring * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    faces += [tuple(reversed(range(n))), tuple((len(profile) - 1) * n + i for i in range(n))]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    for mat in materials:
        mesh.materials.append(mat)
    for p in mesh.polygons:
        p.use_smooth = p.index < (len(profile) - 1) * n
        if label_segment is not None and p.index // n == label_segment:
            p.material_index = 1
    if label_segment is not None:
        color_mesh(o, PALETTE['paper'])
    return o


def jar(index, tier, x, y, z, root, paste, satin, lid):
    group = empty(f'Jar_{index:02d}', root)
    group.location = (x, y, z)
    group['tier'] = tier
    group['role'] = 'Unlabelled peanut-butter style jar with a blank band and plain lid'
    lathe(f'JarBody_{index:02d}', [(.044, 0), (.050, .006), (.050, .025),
          (.0507, .026), (.0507, .078), (.050, .079), (.048, .095), (.041, .104)],
          group, [paste, satin], label_segment=3)
    lathe(f'PlainLid_{index:02d}', [(.043, .101), (.050, .102), (.052, .105),
          (.052, .117), (.049, .120)], group, [lid])


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['origin'] = 'floor centre'
    satin = material('SharedMatteFixtureAndBlankPaper', (1, 1, 1), .58, vertex=True)
    paste = material('SharedOpaquePeanutTone', PALETTE['paste'], .33)
    lid = material('SharedPlainTerracottaLid', PALETTE['lid'], .29)
    # Recessed toe and a quiet inset panel keep the tall pedestal visually light.
    box('Pedestal_RecessedToe', (0, 0, .035), (.72, .42, .07), satin, root, PALETTE['toe'], .008)
    box('Pedestal_Cabinet', (0, 0, .33), (.76, .46, .54), satin, root, PALETTE['ivory'], .014)
    box('Pedestal_FrontInset', (0, -.231, .335), (.68, .008, .435), satin, root, PALETTE['inset'], .009)
    box('Pedestal_FrontPanel', (0, -.237, .335), (.659, .006, .414), satin, root, PALETTE['ivory'], .008)
    box('Tier_1_Deck', (0, 0, .61), (.8, .5, .02), satin, root, PALETTE['ivory'], .007)
    box('Tier_1_EdgeReveal', (0, -.246, .603), (.762, .004, .005), satin, root, PALETTE['toe'], .001)
    box('Tier_2_Core', (0, 0, .682), (.43, .23, .124), satin, root, PALETTE['ivory'], .004)
    box('Tier_2_Deck', (0, 0, .752), (.50, .34, .016), satin, root, PALETTE['ivory'], .004)
    box('Tier_3_Core', (0, 0, .822), (.16, .05, .124), satin, root, PALETTE['ivory'], .003)
    box('Tier_3_Deck', (0, 0, .892), (.23, .13, .016), satin, root, PALETTE['ivory'], .003)
    positions = []
    # Fourteen lower perimeter jars surround a solid riser; eight middle jars
    # surround the upper support; two jars crown the tapered display.
    for j, y in enumerate([-.174, -.058, .058, .174]):
        for i, x in enumerate([-.274, -.137, 0, .137, .274]):
            if j in (0, 3) or i in (0, 4):
                positions.append((1, x, y, .62))
    for j, y in enumerate([-.11, 0, .11]):
        for i, x in enumerate([-.145, 0, .145]):
            if i != 1 or j != 1:
                positions.append((2, x, y, .76))
    positions += [(3, -.057, 0, .90), (3, .057, 0, .90)]
    for i, (tier, x, y, z) in enumerate(positions, 1):
        jar(i, tier, x, y, z, root, paste, satin, lid)
    for x in [-.092, .092]:
        box('Sign_RearPost', (x, .239, .765), (.008, .012, .29), satin, root, PALETTE['toe'], .001)
    box('Sign_Frame', (0, .239, .925), (.285, .016, .150), satin, root, PALETTE['toe'], .004)
    box('BlankSign_Front', (0, .229, .925), (.266, .004, .131), satin, root, PALETTE['paper'], .002)
    box('BlankSign_Back', (0, .249, .925), (.266, .002, .131), satin, root, PALETTE['paper'], .001)
    return root


def export(path):
    # Keep authoring objects editable; merge only evaluated delivery copies by material.
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    parts = []
    for source in root.children_recursive:
        if source.type == 'MESH':
            mesh = bpy.data.meshes.new_from_object(source.evaluated_get(deps), depsgraph=deps)
            for slot, mat in enumerate(source.data.materials):
                if not any(p.material_index == slot for p in mesh.polygons):
                    continue
                copy = mesh.copy()
                o = bpy.data.objects.new('DELIVERY_' + source.name, copy)
                bpy.context.scene.collection.objects.link(o)
                o.matrix_world = source.matrix_world.copy()
                bpy.context.view_layer.objects.active = o
                o.select_set(True)
                import bmesh
                bm = bmesh.new()
                bm.from_mesh(copy)
                bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != slot], context='FACES')
                bm.to_mesh(copy)
                bm.free()
                copy.materials.clear()
                copy.materials.append(mat)
                for p in copy.polygons:
                    p.material_index = 0
                parts.append(o)
            bpy.data.meshes.remove(mesh)
    root.name = ROOT + '_Source'
    anchor = empty(ROOT)
    for key, value in root.items():
        anchor[key] = value
    batches = []
    groups = {}
    for o in parts:
        groups.setdefault(o.data.materials[0].name, []).append(o)
    for name, group in sorted(groups.items()):
        mat = group[0].data.materials[0]
        bpy.ops.object.select_all(action='DESELECT')
        for o in group:
            o.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = 'DISPLAY_' + mat.name
        o.parent = anchor
        # Batch local origin is the common floor datum.
        bpy.context.scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        batches.append(o)
    bpy.ops.object.select_all(action='DESELECT')
    anchor.select_set(True)
    for o in batches:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
        export_extras=True, export_cameras=False, export_lights=False)
    for o in batches + [anchor]:
        bpy.data.objects.remove(o, do_unlink=True)
    root.name = ROOT


def aim(o, point):
    o.rotation_euler = (Vector(point) - o.location).to_track_quat('-Z', 'Y').to_euler()


def render_views():
    # Preview the actual exported GLB after reimport, keeping the saved source intact.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE / 'exports/optimized.glb'))
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Neutral studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.16, .18, .20, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    target = (0, 0, .51)
    for name, loc, energy, size in [('Key', (-2.5, -3, 4), 380, 3),
                                   ('Fill', (3, -1, 2), 220, 2.5),
                                   ('Rim', (0, 3, 3.5), 360, 2)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy = energy
        o.data.size = size
        aim(o, target)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 1.30
    s.render.engine = 'CYCLES'
    s.cycles.samples = 24
    s.cycles.use_denoising = True
    s.render.resolution_x = s.render.resolution_y = 900
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.render.film_transparent = False
    s.view_settings.view_transform = 'AgX'
    for name, delta in [('hero', (1.45, -2.6, 1.3)), ('front', (0, -3, .36)),
                        ('side', (3, 0, .42)), ('3q', (-1.9, -2.7, 1.85))]:
        s.camera.location = Vector(target) + Vector(delta)
        aim(s.camera, target)
        s.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        if name == 'hero':
            s.render.image_settings.file_format = 'JPEG'
            s.render.image_settings.quality = 86
            bpy.data.images['Render Result'].save_render(str(HERE / 'previews/hero.jpg'), scene=s)
            s.render.image_settings.file_format = 'PNG'


def main():
    for d in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / d).mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        s = bpy.context.scene
        s.unit_settings.system = 'METRIC'
        s.unit_settings.scale_length = 1
        build()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
