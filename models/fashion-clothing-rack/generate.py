"""Original deterministic boutique display. Blender 5.2.3; no external assets."""
from pathlib import Path
import bpy
import bmesh
import math
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'fashion-clothing-rack'
ROOT = 'ASSET_FashionClothingRack'
TARGET = (0, 0, .79)
COLORS = [(0.84, .81, .71), (.40, .54, .48), (.68, .39, .28),
          (.27, .37, .44), (.64, .61, .55), (.56, .68, .70)]


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def material(name, rgb, metallic=0, roughness=.5, colored=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = linear(rgb)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    mat.diffuse_color = linear(rgb)
    if colored:
        shader.inputs['Base Color'].default_value = (1, 1, 1, 1)
        node = mat.node_tree.nodes.new('ShaderNodeVertexColor')
        node.layer_name = 'Color'
        mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
    return mat


def empty(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def finish(obj, name, mat, parent, color=COLORS[0], bevel=0):
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod = obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if mat.name in ('Cotton', 'MatteSurface'):
        attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
        for item in attr.data:
            item.color = linear(color)
    return obj


def mesh_object(name, vertices, faces, mat, parent, color=COLORS[0], smooth=False):
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
    finish(obj, name, mat, parent, color)
    for polygon in mesh.polygons:
        polygon.use_smooth = smooth
    return obj


def box(name, location, dimensions, mat, parent, color=COLORS[0], bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(obj, name, mat, parent, color, min(bevel, min(dimensions) * .4))


def cylinder(name, location, radius, height, mat, parent, color=COLORS[0], sides=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=radius, depth=height, location=location)
    obj = finish(bpy.context.object, name, mat, parent, color, .001 if radius >= .01 else 0)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    return obj


def tube(name, points, radius, mat, parent, color=COLORS[0], sides=6, closed=False):
    points = [Vector(p) for p in points]
    vertices, faces = [], []
    count = len(points)
    for index, point in enumerate(points):
        a = points[(index - 1) % count] if closed else points[max(0, index - 1)]
        b = points[(index + 1) % count] if closed else points[min(count - 1, index + 1)]
        tangent = (b - a).normalized()
        reference = Vector((0, 1, 0)) if abs(tangent.y) < .9 else Vector((1, 0, 0))
        u = tangent.cross(reference).normalized()
        v = tangent.cross(u).normalized()
        for side in range(sides):
            angle = math.tau * side / sides
            vertices.append(point + radius * (math.cos(angle) * u + math.sin(angle) * v))
    for index in range(count if closed else count - 1):
        for side in range(sides):
            a = index * sides + side
            b = index * sides + (side + 1) % sides
            c = ((index + 1) % count) * sides
            faces.append((a, b, c + (side + 1) % sides, c + side))
    if not closed:
        faces += [tuple(reversed(range(sides))), tuple((count - 1) * sides + side for side in range(sides))]
    return mesh_object(name, vertices, faces, mat, parent, color, True)


def cloth_loft(name, rings, mat, parent, color, segments=16, thickness=.0022, axis=None):
    """Open neck/hem or sleeve shell, with a real thin wall and closed rim edges."""
    vertices, faces = [], []
    for row, (z, width, depth) in enumerate(rings):
        for index in range(segments):
            angle = math.tau * index / segments
            x = width * math.cos(angle)
            sine = math.sin(angle)
            y = depth * math.copysign(abs(sine) ** .45, sine)
            # Small deterministic folds: the colour remains plain and unprinted.
            y += .0032 * math.sin(4 * angle + .32 * row) * abs(sine)
            zz = z + (.002 * math.cos(6 * angle) if row == len(rings) - 1 else 0)
            point = Vector((x, y, zz))
            if axis:
                point = Vector(axis[0]) + axis[1] @ point
            vertices.append(point)
    for row in range(len(rings) - 1):
        for index in range(segments):
            a = row * segments + index
            b = row * segments + (index + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    obj = mesh_object(name, vertices, faces, mat, parent, color, True)
    modifier = obj.modifiers.new('Real cloth wall and bound rims', 'SOLIDIFY')
    modifier.thickness = thickness
    modifier.offset = 0
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def neck_band(name, z, width, depth, fabric, parent, color):
    points = [(width * math.cos(math.tau * i / 16), depth * math.sin(math.tau * i / 16), z) for i in range(16)]
    return tube(name, points, .005, fabric, parent, tuple(v * .88 for v in color), sides=4, closed=True)


def hanging_garment(index, kind, color, parent, cotton, matte, steel):
    angle = math.radians(18 + index * 36)
    group = empty(f'GARMENT_{index + 1:02d}_{kind}', parent, (.30 * math.cos(angle), .30 * math.sin(angle), 0))
    group.rotation_euler.z = angle
    group['garment_type'] = kind
    group['hanger_index'] = index + 1
    if kind == 'Dress':
        rings = [(1.448, .053, .025), (1.408, .144, .034), (1.29, .145, .037),
                 (1.15, .113, .032), (1.02, .143, .041), (.83, .171, .046),
                 (.62, .196, .052), (.405, .220, .059)]
    else:
        bottom = .858 if kind == 'Jacket' else .913 + .013 * (index % 3)
        rings = [(1.448, .053, .025), (1.405, .148, .034), (1.30, .153, .039),
                 (1.17, .143, .034), (bottom + .075, .150, .035), (bottom, .161, .037)]
    cloth_loft('CLOTH_' + group.name, rings, cotton, group, color)
    neck_band('COLLAR_' + group.name, 1.448, .053, .025, cotton, group, color)
    hem = rings[-1]
    neck_band('HEM_' + group.name, hem[0] + .005, hem[1], hem[2], cotton, group, color)
    if kind != 'Dress':
        for sign in (-1, 1):
            start = Vector((sign * .133, 0, 1.366))
            end = Vector((sign * (.216 if kind == 'Shirt' else .225), .002, 1.265 if kind == 'Shirt' else .93))
            direction = (end - start).normalized()
            rotation = direction.to_track_quat('Z', 'Y').to_matrix()
            length = (end - start).length
            rings_sleeve = [(0, .061, .038), (length * .52, .054, .032), (length, .043, .027)]
            cloth_loft(f'SLEEVE_{index:02d}_{sign}', rings_sleeve, cotton, group, color, segments=12, axis=(start, rotation))
            points = [start + rotation @ Vector((.043 * math.cos(math.tau * i / 8), .027 * math.sin(math.tau * i / 8), length)) for i in range(8)]
            tube(f'CUFF_{index:02d}_{sign}', points, .003, cotton, group, tuple(v * .9 for v in color), sides=4, closed=True)
    if kind == 'Jacket':
        # Shallow folded lapels and a front seam distinguish the jackets from tees.
        for sign in (-1, 1):
            vertices = [(sign * .048, -.028, 1.44), (sign * .105, -.042, 1.36),
                        (sign * .026, -.044, 1.20), (sign * .016, -.040, 1.31)]
            lapel = mesh_object(f'LAPEL_{index}_{sign}', vertices, [(0, 1, 2, 3)], cotton, group, tuple(min(1, v * 1.1) for v in color))
            mod = lapel.modifiers.new('Fold thickness', 'SOLIDIFY')
            mod.thickness = .003
            bpy.context.view_layer.objects.active = lapel
            bpy.ops.object.modifier_apply(modifier=mod.name)
        tube(f'PLACKET_{index}', [(0, -.039, 1.25), (0, -.036, 1.12), (0, -.040, .87)], .002, cotton, group, tuple(v * .7 for v in color))
        for z in (1.19, 1.07, .95):
            button = cylinder(f'BUTTON_{index}', (.014, -.041, z), .0035, .003, matte, group, (.25, .25, .23), 12)
            button.rotation_euler.x = math.pi / 2
    hanger = empty(f'HANGER_{index + 1:02d}', group)
    tube(f'HANGER_{index:02d}_Wood', [(-.155, 0, 1.397), (-.027, 0, 1.505), (.155, 0, 1.397)], .007, matte, hanger, (.55, .40, .27))
    tube(f'HANGER_{index:02d}_Crossbar', [(-.155, 0, 1.397), (.155, 0, 1.397)], .005, matte, hanger, (.55, .40, .27))
    hook = [(-.018, 0, 1.505), (-.018, 0, 1.560)]
    hook += [(.018 * math.cos(math.pi - math.pi * i / 10), 0, 1.560 + .018 * math.sin(math.pi - math.pi * i / 10)) for i in range(1, 11)]
    tube(f'HANGER_{index:02d}_Hook', hook, .0025, steel, hanger)
    return group


def build(root):
    steel = material('BrushedMetal', (.45, .47, .45), .78, .30)
    matte = material('MatteSurface', (1, 1, 1), .02, .48, True)
    cotton = material('Cotton', (1, 1, 1), 0, .86, True)
    rack = empty('RACK_Round', root, (-.85, 0, 0))
    rack['role'] = 'round clothing rack with ten hanging garments'
    dark = (.17, .20, .20)
    cylinder('RACK_Pedestal', (0, 0, .035), .085, .07, matte, rack, dark)
    cylinder('RACK_CentrePost', (0, 0, .809), .024, 1.478, steel, rack)
    cylinder('RACK_TopFinial', (0, 0, 1.574), .030, .052, steel, rack)
    for i in range(4):
        angle = math.radians(45 + i * 90)
        x, y = .33 * math.cos(angle), .33 * math.sin(angle)
        tube(f'RACK_Foot_{i}', [(0, 0, .060), (x * .7, y * .7, .042), (x, y, .023)], .015, steel, rack, sides=8)
        cylinder(f'RACK_FloorPad_{i}', (x, y, .009), .031, .018, matte, rack, dark, 16)
        x, y = .30 * math.cos(angle), .30 * math.sin(angle)
        tube(f'RACK_TopSpoke_{i}', [(0, 0, 1.529), (x, y, 1.529), (x, y, 1.560)], .009, steel, rack, sides=8)
    circle = [(.30 * math.cos(math.tau * i / 64), .30 * math.sin(math.tau * i / 64), 1.560) for i in range(64)]
    tube('RACK_CircularRail', circle, .012, steel, rack, sides=6, closed=True)
    kinds = ['Shirt', 'Jacket', 'Shirt', 'Shirt', 'Dress', 'Shirt', 'Jacket', 'Shirt', 'Shirt', 'Shirt']
    for i, kind in enumerate(kinds):
        hanging_garment(i, kind, COLORS[i % len(COLORS)], rack, cotton, matte, steel)
    table = empty('TABLE_FoldedDisplay', root, (.80, 0, 0))
    table['role'] = 'folded-clothes display table'
    fixture = empty('TABLE_Fixture', table)
    box('TABLE_Top', (0, 0, .780), (1.2, .6, .040), matte, fixture, (.71, .58, .43), .009)
    box('TABLE_UnderTopFrame', (0, 0, .747), (1.13, .53, .026), matte, fixture, dark)
    for x in (-.54, .54):
        for y in (-.24, .24):
            box('TABLE_Leg', (x, y, .383), (.033, .033, .750), steel, fixture, bevel=.003)
            box('TABLE_FloorPad', (x, y, .004), (.036, .036, .008), matte, fixture, dark, .001)
        box('TABLE_LowerStretcher', (x, 0, .24), (.024, .48, .024), steel, fixture)
    box('TABLE_LowerShelf', (0, 0, .254), (1.10, .47, .022), matte, fixture, (.71, .58, .43), .006)
    for stack_index, count in enumerate((4, 3, 4)):
        stack = empty(f'STACK_{stack_index + 1:02d}', table, ((stack_index - 1) * .37, 0, .8))
        for level in range(count):
            color = COLORS[(stack_index * 2 + level) % len(COLORS)]
            folded = empty(f'FOLDED_{stack_index + 1}_{level + 1}', stack)
            z = .016 + level * .033
            offset = .005 * (level % 2)
            box('FOLDED_SoftBody', (offset, 0, z), (.293, .358, .032), cotton, folded, color, .012)
            tube('FOLDED_FrontHem', [(-.128 + offset, -.179, z - .003), (offset, -.181, z - .002), (.128 + offset, -.179, z - .003)], .0018, cotton, folded, tuple(v * .88 for v in color))
            if level == count - 1:
                # Folded sleeve flaps and a ribbed collar make the top shirt readable.
                for sign in (-1, 1):
                    flap = box('FOLDED_SleeveFlap', (sign * .102 + offset, .025, z + .016), (.062, .23, .006), cotton, folded, color, .002)
                    flap.rotation_euler.z = sign * .10
                points = [(offset + .038 * math.cos(math.tau * i / 16), .102 + .027 * math.sin(math.tau * i / 16), z + .020) for i in range(16)]
                tube('FOLDED_Collar', points, .004, cotton, folded, tuple(v * .83 for v in color), sides=4, closed=True)
    # Centre the actual combined footprint at the authoring datum, preserving floor Z=0.
    bpy.context.view_layer.update()
    points = [obj.matrix_world @ vertex.co for obj in root.children_recursive if obj.type == 'MESH' for vertex in obj.data.vertices]
    center = Vector(((min(p.x for p in points) + max(p.x for p in points)) / 2,
                     (min(p.y for p in points) + max(p.y for p in points)) / 2, 0))
    rack.location -= center
    table.location -= center


def export(path):
    """Export evaluated saved meshes in three material batches; keep native parts editable."""
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
            bpy.context.object.name = 'BATCH_' + name
            batches.append(bpy.context.object)
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
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .25, .27, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
    floor = material('STUDIO_Floor', (.30, .33, .34), roughness=.8)
    box('STUDIO_Floor', (0, 0, -.027), (200, 200, .05), floor, None, bevel=0)
    for name, loc, power, size in [('Key', (-3, -4, 5), 1000, 3), ('Fill', (4, -2, 3), 650, 3), ('Rim', (1, 3, 4), 1100, 3)]:
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
    scene.camera.data.ortho_scale = 3.50
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    for name, position in [('hero', (2.4, -5.8, 2.7)), ('front', (0, -6, 2.0)),
                           ('side', (6, -.1, 1.8)), ('3q', (-3.8, -5.4, 2.6))]:
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
        bpy.context.preferences.filepaths.save_version = 0
        scene = bpy.context.scene
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.scale_length = 1
        root = empty(ROOT)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['origin'] = 'Floor centre of combined footprint'
        root['scope'] = 'Original static brand-neutral boutique clothing display'
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
