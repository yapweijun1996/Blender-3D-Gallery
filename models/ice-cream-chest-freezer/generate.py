"""Original metric sliding-lid freezer. Blender 5.2.3; no external inputs."""
from pathlib import Path
import json
import math
import struct
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'ice-cream-chest-freezer'
ROOT = 'ASSET_IceCreamChestFreezer'
GROUPS = ['Cabinet', 'Contents', 'Lid_Left', 'Lid_Right']


def linear_color(rgb, alpha=1):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (alpha,)


def material(name, rgb, roughness=.45, metallic=0, alpha=1, vertex_colors=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    color = linear_color(rgb, alpha)
    m.diffuse_color = color
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = color
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Alpha'].default_value = alpha
    if vertex_colors:
        attribute = m.node_tree.nodes.new('ShaderNodeVertexColor')
        attribute.layer_name = 'Color'
        m.node_tree.links.new(attribute.outputs['Color'], p.inputs['Base Color'])
    if alpha < 1:
        m.surface_render_method = 'DITHERED'
        m.use_backface_culling = True
    return m


def empty(name, parent=None, location=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = location
    return o


def finish(o, name, mat, parent, bevel=.003):
    o.name = name
    o.parent = parent
    if isinstance(mat, tuple):
        shared, color = mat
        o.data.materials.append(shared)
        attribute = o.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
        for item in attribute.data:
            item.color = color
    else:
        o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Manufactured radii', 'BEVEL')
        mod.width = bevel
        # Spend curvature on the large cabinet corners, not thin trim and recesses.
        mod.segments = 2 if bevel >= .016 else 1
        mod = o.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return o


def box(name, location, dimensions, mat, parent, bevel=.003):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = location
    return finish(o, name, mat, parent, min(bevel, min(dimensions) * .22))


def lathe(name, profile, location, mat, parent, segments=24):
    vertices, rings, faces = [], [], []
    for radius, height in profile:
        ring = []
        for i in range(1 if radius == 0 else segments):
            a = i * 2 * math.pi / segments
            ring.append(len(vertices))
            vertices.append((radius * math.cos(a), radius * math.sin(a), height))
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
    o.location = location
    finish(o, name, mat, parent, 0)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return o


def frozen_surface(name, location, paint, parent, variant):
    """Closed cream volume with soft billows and a broad, rounded scoop trail."""
    segments, ring_count = 32, 8
    phase = variant * .71

    def sample(x, y):
        u = x * math.cos(phase) - y * math.sin(phase)
        v = x * math.sin(phase) + y * math.cos(phase)
        r = math.hypot(x, y) / .115
        fade = max(0, 1 - r ** 4)
        bowl = math.sqrt(((u - .012) / .062) ** 2 + ((v + .027) / .041) ** 2)
        billows = .025 * math.exp(-((u + .048) / .042) ** 2 - ((v - .028) / .048) ** 2)
        billows += .018 * math.exp(-((u - .044) / .041) ** 2 - ((v - .037) / .038) ** 2)
        scoop = -.022 * math.exp(-bowl ** 2 * 1.8)
        rolled_edge = .010 * math.exp(-((bowl - 1.03) / .23) ** 2)
        return .264 + fade * (.010 + billows + scoop + rolled_edge)

    vertices = [(0, 0, sample(0, 0))]
    rings, faces = [], []
    for j in range(1, ring_count + 1):
        ring = []
        for i in range(segments):
            angle = i * math.tau / segments
            radius = .113 * j / ring_count * (1 + .018 * math.sin(3 * angle + phase) + .012 * math.sin(5 * angle - phase))
            x, y = radius * math.cos(angle), radius * math.sin(angle)
            ring.append(len(vertices))
            vertices.append((x, y, sample(x, y)))
        rings.append(ring)
    for i in range(segments):
        faces.append((0, rings[0][i], rings[0][(i + 1) % segments]))
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            k = (i + 1) % segments
            faces.append((a[i], b[i], b[k], a[k]))
    bottom = []
    for i in range(segments):
        angle = i * math.tau / segments
        bottom.append(len(vertices))
        vertices.append((.096 * math.cos(angle), .096 * math.sin(angle), .04))
    centre = len(vertices)
    vertices.append((0, 0, .04))
    for i in range(segments):
        k = (i + 1) % segments
        faces.append((rings[-1][i], bottom[i], bottom[k], rings[-1][k]))
        faces.append((centre, bottom[k], bottom[i]))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    finish(obj, name, paint, parent, 0)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    # Small tonal variation supports the actual sculpted relief, with no texture.
    for vertex, item in zip(mesh.vertices, mesh.color_attributes['Color'].data):
        shade = max(.92, min(1.04, .96 + (vertex.co.z - .255) * 2))
        item.color = tuple(c * shade for c in paint[1][:3]) + (1,)
    obj['surface'] = 'Soft billows, rounded scoop depression and irregular filled edge'
    return obj


def build():
    root = empty(ROOT)
    root['units'] = 'metres'
    root['front_axis'] = 'Blender -Y / glTF +Z'
    root['scope'] = 'P1 static display prop; independent sliding lids; no runtime interaction'
    opaque = material('Shared opaque vertex palette', (1, 1, 1), .43, vertex_colors=True)
    ivory = (opaque, linear_color((.89, .88, .82)))
    teal = (opaque, linear_color((.14, .32, .33)))
    dark = (opaque, linear_color((.085, .11, .12)))
    tub = (opaque, linear_color((.95, .93, .86)))
    glass = material('Blank glazing - pale aqua', (.68, .89, .88), .16, 0, .17)
    flavors = [(opaque, linear_color(color)) for name, color in [
        ('vanilla', (.94, .82, .56)), ('strawberry', (.86, .48, .52)),
        ('pistachio', (.60, .75, .50)), ('cocoa', (.39, .23, .16)),
        ('mango', (.96, .63, .26)), ('coconut', (.94, .93, .85))]]
    cabinet = empty('Cabinet', root)
    box('Plinth', (0, 0, .075), (1.43, .68, .09), dark, cabinet, .016)
    for x in [-.62, .62]:
        for y in [-.26, .26]:
            box('Foot', (x, y, .02), (.085, .085, .04), dark, cabinet, .009)
    box('Insulated floor', (0, 0, .285), (1.50, .75, .33), ivory, cabinet, .025)
    for x in [-.705, .705]:
        box('Insulated end', (x, 0, .645), (.09, .75, .39), ivory, cabinet, .018)
    for y in [-.33, .33]:
        box('Insulated wall', (0, y, .645), (1.32, .09, .39), ivory, cabinet, .016)
    box('Inner well floor', (0, 0, .456), (1.32, .57, .012), tub, cabinet, .004)
    for x in [-.72, .72]:
        box('Upper end rim', (x, 0, .87), (.06, .75, .06), teal, cabinet, .012)
    for y in [-.345, .345]:
        box('Upper long rim', (0, y, .87), (1.38, .06, .06), teal, cabinet, .009)
    # Recessed ventilation, drain and plain control bezel are geometry, not labels.
    box('Front vent recess', (.48, -.376, .235), (.30, .008, .105), dark, cabinet, .009)
    for i in range(7):
        box('Vent slat', (.365 + i * .038, -.382, .235), (.011, .008, .076), ivory, cabinet, .002)
    box('Blank thermostat bezel', (-.52, -.377, .735), (.115, .012, .045), teal, cabinet, .005)
    box('Blank thermostat inset', (-.537, -.384, .735), (.062, .003, .023), dark, cabinet, .002)
    lathe('Drain cap', [(0, 0), (.014, 0), (.014, .006), (0, .006)], (0, 0, 0), teal, cabinet, 16)
    drain = bpy.data.objects['Drain cap']
    drain.rotation_euler.x = math.pi / 2
    drain.location = (-.52, -.377, .20)
    contents = empty('Contents', root)
    for i, (x, y) in enumerate((x, y) for y in [-.142, .142] for x in [-.435, 0, .435]):
        loc = (x, y, .465)
        lathe('Tub_%02d' % (i + 1), [(0, 0), (.103, 0), (.109, .012), (.125, .261),
              (.129, .266), (.129, .272), (.119, .272), (.116, .260), (.097, .018), (0, .018)], loc, tub, contents)
        frozen_surface('Frozen_%02d' % (i + 1), loc, flavors[i], contents, i)
    # Both tracks stay within the 1.50 m cabinet envelope. Left is partly open.
    for name, x, z in [('Lid_Left', .06, .853), ('Lid_Right', .345, .881)]:
        group = empty(name, root, (x, 0, z))
        group['axis'] = 'local X'
        group['closed_x_m'] = -.345 if name == 'Lid_Left' else .345
        group['open_x_m'] = .345 if name == 'Lid_Left' else -.345
        group['track_z_m'] = z
        for xx in [-.3375, .3375]:
            box(name + '_End', (xx, 0, 0), (.025, .616, .018), teal, group, .005)
        for y in [-.2955, .2955]:
            box(name + '_Rail', (0, y, 0), (.65, .025, .018), teal, group, .005)
        box(name + '_BlankGlass', (0, 0, 0), (.65, .566, .006), glass, group, 0)
        box(name + '_Handle', (-.235 if name == 'Lid_Left' else .235, -.20, .011),
            (.045, .13, .010), ivory, group, .004)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -.0057, .45))
    collider = bpy.context.object
    collider.name = 'collider_box'
    collider.dimensions = (1.50, .7614, .90)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    collider.parent = root
    collider.display_type = 'WIRE'
    collider.hide_render = True
    collider.hide_set(True)
    collider['hidden'] = True
    collider['role'] = 'walkable-blocking AABB; no material; opt-in collision scene'
    root['collider_node'] = 'collider_box'
    root['collision_scene'] = 1
    return root


def export(destination):
    """Export evaluated copies per placement group without changing source meshes."""
    root = bpy.data.objects[ROOT]
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    temporary = []
    anchor = empty(ROOT + '_Export')
    temporary.append(anchor)
    for key, value in root.items():
        anchor[key] = value
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
        source = bpy.data.objects['collider_box']
        collider = bpy.data.objects.new('collider_box', source.data.copy())
        bpy.context.scene.collection.objects.link(collider)
        collider.matrix_world = source.matrix_world.copy()
        for key, value in source.items():
            collider[key] = value
        temporary.append(collider)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in temporary:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(destination), export_format='GLB', use_selection=True,
            export_apply=True, export_yup=True, export_animations=False, export_texcoords=False,
            export_extras=True, export_cameras=False, export_lights=False)
        # glTF has no core visibility flag: keep collision geometry in an opt-in
        # scene, outside the default gallery scene. Never give it a material.
        raw = destination.read_bytes()
        size = struct.unpack_from('<I', raw, 12)[0]
        doc = json.loads(raw[20:20 + size])
        by_name = {node['name']: i for i, node in enumerate(doc['nodes'])}
        collider_index = by_name[collider.name]
        doc['nodes'][collider_index]['name'] = 'collider_box'
        doc['scenes'] = [
            {'name': 'Ice Cream Chest Freezer', 'nodes': [by_name[ROOT]]},
            {'name': 'COLLISION_ONLY_NotVisible', 'nodes': [collider_index]},
        ]
        doc['scene'] = 0
        text = json.dumps(doc, separators=(',', ':')).encode()
        text += b' ' * (-len(text) % 4)
        binary = raw[20 + size:]
        destination.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(text) + len(binary)) +
                                struct.pack('<I4s', len(text), b'JSON') + text + binary)
    finally:
        for obj in reversed(temporary):
            mesh = obj.data if obj.type == 'MESH' else None
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        root.name = ROOT


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    floor = material('STUDIO neutral floor', (.77, .78, .75), .85)
    box('STUDIO_Floor', (0, 0, -.025), (200, 200, .05), floor, None, 0)
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.3, .34, .36, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    for name, location, energy, size in [('Key', (-3, -4, 5), 750, 3.5),
                                       ('Fill', (4, -1, 4), 500, 3), ('Rim', (1, 4, 5), 650, 2.5)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = energy, 'DISK', size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = location
        aim(obj, (0, 0, .4))
    data = bpy.data.cameras.new('Studio camera')
    obj = bpy.data.objects.new('Studio camera', data)
    scene.collection.objects.link(obj)
    scene.camera = obj
    data.type, data.ortho_scale = 'ORTHO', 2.25
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'


def render_views():
    scene = bpy.context.scene
    target = Vector((0, 0, .41))
    for name, direction in [('hero', (3, -4.2, 4.5)), ('front', (0, -5, 1.4)),
                            ('side', (5, 0, 2)), ('top', (-2.7, -3.7, 5.4))]:
        scene.camera.location = target + Vector(direction)
        aim(scene.camera, target)
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for name in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / name).mkdir(parents=True, exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = 1
        build()
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
