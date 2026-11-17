"""Original deterministic restaurant furniture. Blender 5.2.3; no external inputs."""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'restaurant-table-chair-set'
ROOT = 'ASSET_RestaurantTableChairSet'
GROUPS = ['Table', 'Chair_North', 'Chair_East', 'Chair_South', 'Chair_West',
          'TableNumberStand', 'CondimentTray']


def material(name, rgb, metallic=0, roughness=.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)
    m.diffuse_color = color
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    return m


def empty(name, parent=None, location=(0, 0, 0), angle=0):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = location
    o.rotation_euler.z = angle
    return o


def finish(o, name, mat, parent, bevel=.002):
    o.name = name
    o.parent = parent
    o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Soft manufactured edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod = o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return o


def box(name, location, dimensions, mat, parent, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = location
    return finish(o, name, mat, parent, bevel)


def mesh_object(name, vertices, faces, mat, parent, bevel=.002):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    return finish(o, name, mat, parent, bevel)


def rounded_panel(name, width, depth, thickness, radius, location, mat, parent, back=False):
    ring = []
    for x, y, start in [(width / 2 - radius, depth / 2 - radius, 0),
                        (-width / 2 + radius, depth / 2 - radius, 90),
                        (-width / 2 + radius, -depth / 2 + radius, 180),
                        (width / 2 - radius, -depth / 2 + radius, 270)]:
        for i in range(5):
            a = math.radians(start + i * 22.5)
            ring.append((x + radius * math.cos(a), y + radius * math.sin(a)))
    vertices = []
    for t in [-thickness / 2, thickness / 2]:
        for x, y in ring:
            if back:
                # A shallow wrap and recline, with rounded corners in the X/Z profile.
                vertices.append((x + location[0], location[1] + .14 * y - .025 * (x / (width / 2)) ** 2 + t, y + location[2]))
            else:
                vertices.append((x + location[0], y + location[1], t + location[2]))
    n = len(ring)
    faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return mesh_object(name, vertices, faces, mat, parent)


def beam(name, a, b, width, mat, parent):
    a, b = Vector(a), Vector(b)
    o = box(name, (a + b) / 2, (width, width, (b - a).length), mat, parent, .002)
    o.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    return o


def lathe(name, profile, location, mat, parent, segments=20):
    # Profile endpoints lie on the axis; unique poles avoid zero-area triangles.
    vertices, rings, faces = [], [], []
    for radius, height in profile:
        ring = []
        for i in range(1 if radius == 0 else segments):
            angle = i * 2 * math.pi / segments
            ring.append(len(vertices))
            vertices.append((location[0] + radius * math.cos(angle), location[1] + radius * math.sin(angle), location[2] + height))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(a) == 1:
                faces.append((a[0], b[j], b[i]))
            elif len(b) == 1:
                faces.append((a[i], a[j], b[0]))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
    return mesh_object(name, vertices, faces, mat, parent, 0)


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['seats'] = 4
    root['scope'] = 'Static original furniture; consumer implements game logic and collisions.'
    sand = material('Neutral sand laminate', (.72, .67, .58), roughness=.48)
    graphite = material('Satin graphite metal', (.25, .28, .28), .45, .4)
    ivory = material('Warm ivory ceramic and blank card', (.91, .90, .85), roughness=.42)
    table = empty('Table', root)
    rounded_panel('TableTop_800mm', .8, .8, .032, .035, (0, 0, .734), sand, table)
    for x in [-.327, .327]:
        for y in [-.327, .327]:
            box('TableLeg', (x, y, .359), (.036, .036, .718), graphite, table, .003)
        box('TableApronX', (0, x, .687), (.654, .025, .055), graphite, table)
        box('TableApronY', (x, 0, .687), (.025, .654, .055), graphite, table)
    table['top_height_m'] = .75
    table['placement_pivot'] = 'Floor centre'
    chairs = [('Chair_North', (0, -.72, 0), math.pi),
              ('Chair_East', (.72, 0, 0), -math.pi / 2),
              ('Chair_South', (0, .72, 0), 0),
              ('Chair_West', (-.72, 0, 0), math.pi / 2)]
    for name, location, angle in chairs:
        group = empty(name, root, location, angle)
        group['placement_pivot'] = 'Local floor centre; local -Y faces inward in Blender'
        group['seat_height_m'] = .45
        rounded_panel(name + '_Seat', .42, .43, .026, .045, (0, -.005, .437), sand, group)
        rounded_panel(name + '_Back', .405, .185, .022, .035, (0, .207, .7075), sand, group, back=True)
        for x in [-.16, .16]:
            for y in [-.155, .155]:
                beam(name + '_Leg', (x * 1.10, y * 1.13, .014), (x, y, .425), .028, graphite, group)
                box(name + '_Foot', (x * 1.10, y * 1.13, .007), (.031, .031, .014), graphite, group, .003)
            beam(name + '_BackPost', (x, .155, .416), (x, .219, .782), .022, graphite, group)
            box(name + '_SeatRailY', (x, 0, .412), (.022, .332, .024), graphite, group)
        for y in [-.155, .155]:
            box(name + '_SeatRailX', (0, y, .412), (.32, .022, .024), graphite, group)
    stand = empty('TableNumberStand', root, (-.155, -.01, .75))
    stand['placement_pivot'] = 'Base centre on tabletop'
    rounded_panel('StandBase', .105, .068, .008, .018, (0, 0, .004), graphite, stand)
    beam('StandStem', (0, .008, .008), (0, .008, .091), .009, graphite, stand)
    box('StandBlankCard', (0, .008, .113), (.103, .006, .071), ivory, stand, .0015)
    tray = empty('CondimentTray', root, (.105, .055, .75))
    tray['placement_pivot'] = 'Tray base centre on tabletop'
    rounded_panel('TrayDeck', .23, .145, .008, .021, (0, 0, .004), graphite, tray)
    for y in [-.067, .067]:
        box('TrayLongRim', (0, y, .017), (.188, .009, .026), graphite, tray, .004)
    for x in [-.109, .109]:
        box('TrayShortRim', (x, 0, .017), (.009, .107, .026), graphite, tray, .004)
    for x in [-.065, -.012]:
        loc = (x, -.018, .008)
        lathe('CeramicShaker', [(0, 0), (.018, 0), (.022, .006), (.022, .046), (.018, .057), (0, .057)], loc, ivory, tray)
        lathe('ShakerCap', [(0, .057), (.0185, .057), (.0185, .063), (.014, .067), (0, .067)], loc, graphite, tray)
        for dx, dy in [(-.005, 0), (.005, 0), (0, .006)]:
            lathe('CapHoleRecess', [(0, 0), (.0016, 0), (.0016, .0004), (0, .0004)],
                  (x + dx, -.018 + dy, .0751), ivory, tray, 8)
    loc = (.060, .006, .008)
    lathe('GenericCondimentBottle', [(0, 0), (.020, 0), (.023, .006), (.023, .070), (.012, .085), (.012, .093), (0, .093)], loc, sand, tray)
    lathe('PlainNozzleCap', [(0, .092), (.014, .092), (.014, .104), (.008, .108), (.003, .129), (0, .129)], loc, ivory, tray)
    return root


def export(destination):
    """Merge evaluated copies per placement group; keep editable source untouched."""
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    temporary = []
    anchor = empty(ROOT + '_Export')
    temporary.append(anchor)
    for key, value in root.items():
        anchor[key] = value
    original_name = root.name
    root.name = ROOT + '_Source'
    anchor.name = ROOT
    try:
        for name in GROUPS:
            group = bpy.data.objects[name]
            copies = []
            for source in group.children_recursive:
                if source.type != 'MESH':
                    continue
                mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
                mesh.transform(group.matrix_world.inverted() @ source.matrix_world)
                obj = bpy.data.objects.new(source.name + '_Export', mesh)
                bpy.context.scene.collection.objects.link(obj)
                copies.append(obj)
            bpy.ops.object.select_all(action='DESELECT')
            for obj in copies:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = copies[0]
            bpy.ops.object.join()
            obj = copies[0]
            obj.name = name + '_Geometry'
            obj.parent = anchor
            obj.matrix_basis = group.matrix_world.copy()
            for key, value in group.items():
                obj[key] = value
            obj['source_parts'] = [c.name for c in group.children_recursive if c.type == 'MESH']
            temporary.append(obj)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in temporary:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(destination), export_format='GLB', use_selection=True,
                                  export_apply=True, export_yup=True, export_animations=False,
                                  export_texcoords=False, export_extras=True, export_cameras=False, export_lights=False)
    finally:
        for obj in reversed(temporary):
            mesh = obj.data if obj.type == 'MESH' else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        root.name = original_name


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    floor_mat = material('STUDIO only neutral floor', (.77, .79, .77), roughness=.85)
    box('STUDIO_Floor', (0, 0, -.035), (200, 200, .07), floor_mat, None, 0)
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.28, .32, .35, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    for name, location, energy, size in [('Key', (-3, -4, 5), 750, 3.5),
                                          ('Fill', (4, -1, 3), 500, 3),
                                          ('Rim', (1, 4, 5), 850, 3)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.object
        light.name = 'STUDIO_' + name
        light.data.energy = energy
        light.data.shape = 'DISK'
        light.data.size = size
        aim(light, (0, 0, .35))
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = 2.85
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    target = Vector((0, 0, .36))
    for name, direction in [('hero', (3.0, -4.1, 3.3)), ('front', (0, -5, 1.4)),
                            ('side', (5, 0, 1.4)), ('3q', (-3.8, -4.2, 2.3))]:
        scene.camera.location = target + Vector(direction)
        aim(scene.camera, target)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for directory in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / directory).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
