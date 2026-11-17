"""Original metric potong cart. Blender 5.2.3; deterministic, no external inputs."""
from pathlib import Path
import bpy
import bmesh
import json
import math
import struct
import sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SLUG = 'ice-cream-cart-potong'
ROOT = 'ASSET_IceCreamCartPotong'
TARGET = Vector((0, 0, .86))
GROUPS = ['CART_InsulatedBoxWheelsHandleBell', 'UMBRELLA_Canopy',
          'FLAVOUR_ThreeTubs', 'SERVICE_Flap', 'TRAY_BarsAndWafers']
COLORS = {
    'cream': (.98, .88, .67), 'coral': (.86, .36, .24),
    'mint': (.38, .64, .51), 'vanilla': (1.0, .86, .55),
    'berry': (.87, .54, .60), 'cocoa': (.42, .25, .19),
    'steel': (.69, .75, .72), 'dark': (.18, .23, .23),
    'gold': (.91, .64, .26), 'wafer': (.77, .52, .29),
}


def linear(rgb):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)


def material(name, metallic, roughness, coat):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    tree = m.node_tree
    p = tree.nodes.get('Principled BSDF')
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Coat Weight'].default_value = coat
    p.inputs['Coat Roughness'].default_value = .24
    c = tree.nodes.new('ShaderNodeVertexColor')
    c.layer_name = 'Color'
    tree.links.new(c.outputs['Color'], p.inputs['Base Color'])
    return m


def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.parent = parent
    return o


def finish(o, name, group, color, mat, bevel=0):
    o.name = name
    # Keep world coordinates when parenting to the service flap hinge.
    bpy.context.view_layer.update()
    world = o.matrix_world.copy()
    o.parent = group
    o.matrix_world = world
    o.data.materials.append(mat)
    attr = o.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    rgba = linear(COLORS[color]) + (1,)
    for item in attr.data:
        item.color = rgba
    if bevel:
        mod = o.modifiers.new('Soft manufactured edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod = o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return o


def box(name, loc, dims, group, color, mat, bevel=.007):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    # Leave a real face between opposite bevels on thin panels.
    return finish(o, name, group, color, mat, min(bevel, min(dims) * .4))


def rod(name, a, b, radius, group, color, mat, vertices=12):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                      depth=d.length, location=(a + b) / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    finish(o, name, group, color, mat)
    for poly in o.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return o


def profile(name, center, rings, group, color, mat, segments=24, axis='Z'):
    # Closed surface of revolution with single-vertex caps (no zero-area pole faces).
    verts, faces = [], []
    for distance, radius in rings:
        for i in range(segments):
            a = 2 * math.pi * i / segments
            v = (radius * math.cos(a), radius * math.sin(a), distance)
            if axis == 'X':
                v = (distance, radius * math.cos(a), radius * math.sin(a))
            verts.append(tuple(center[j] + v[j] for j in range(3)))
    for k in range(len(rings) - 1):
        for i in range(segments):
            a = k * segments + i
            b = k * segments + (i + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple((len(rings) - 1) * segments + i for i in range(segments)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    finish(o, name, group, color, mat)
    for poly in mesh.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return o


def open_tub(name, x, group, mat):
    # One closed shell: underside, tapered exterior, rolled rim, interior and floor.
    rings = [(.262, .212, .022, .992), (.280, .230, .026, 1.003),
             (.285, .235, .028, 1.102), (.292, .242, .030, 1.110),
             (.251, .201, .023, 1.110), (.243, .193, .020, 1.102),
             (.232, .182, .018, 1.009)]
    verts, faces, colors = [], [], []
    for width, depth, radius, z in rings:
        for cx, cy, start in [(1, 1, 0), (-1, 1, 90),
                              (-1, -1, 180), (1, -1, 270)]:
            for step in range(4):
                a = math.radians(start + step * 30)
                verts.append((x + cx * (width / 2 - radius) + radius * math.cos(a),
                              -.128 + cy * (depth / 2 - radius) + radius * math.sin(a), z))
    n = 16
    faces.append(tuple(reversed(range(n))))
    colors.append('cream')
    for k in range(len(rings) - 1):
        for i in range(n):
            a, b = k * n + i, k * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
            colors.append('cream' if k < 4 else 'steel')
    faces.append(tuple((len(rings) - 1) * n + i for i in range(n)))
    colors.append('steel')
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    finish(o, name, group, 'cream', mat)
    attr = mesh.color_attributes['Color']
    for poly, color in zip(mesh.polygons, colors):
        for i in poly.loop_indices:
            attr.data[i].color = linear(COLORS[color]) + (1,)
    return o


def canopy(group, glossy):
    # Eight radial panels, each split twice; a narrow oval umbrella fits the P1 envelope.
    verts, faces, colors = [(0, .025, 1.78)], [], []
    n = 32
    for rx, ry, z in [(.24, .14, 1.735), (.53, .30, 1.635), (.70, .40, 1.53)]:
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append((rx * math.cos(a), ry * math.sin(a), z))
    for i in range(n):
        faces.append((0, 1 + i, 1 + (i + 1) % n))
        colors.append('cream' if (i // 4) % 2 else 'coral')
    for k in range(2):
        for i in range(n):
            a = 1 + k * n + i
            b = 1 + k * n + (i + 1) % n
            faces.append((a, a + n, b + n, b))
            colors.append('cream' if (i // 4) % 2 else 'coral')
    # Solid, scalloped valance, integrated with the umbrella mesh.
    for i in range(n):
        a = 2 * math.pi * i / n
        z = 1.476 + .024 * math.cos(8 * a)
        verts.append((.70 * math.cos(a), .40 * math.sin(a), z))
    for i in range(n):
        a = 1 + 2 * n + i
        b = 1 + 2 * n + (i + 1) % n
        faces.append((a, a + n, b + n, b))
        colors.append('cream' if (i // 4) % 2 else 'coral')
    mesh = bpy.data.meshes.new('Original paneled umbrella')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    o = bpy.data.objects.new('UMBRELLA_EightPaneledScallopedShell', mesh)
    bpy.context.scene.collection.objects.link(o)
    finish(o, o.name, group, 'coral', glossy)
    attr = mesh.color_attributes['Color']
    for poly, color in zip(mesh.polygons, colors):
        for i in poly.loop_indices:
            attr.data[i].color = linear(COLORS[color]) + (1,)
    solid = o.modifiers.new('Thin folded canopy shell', 'SOLIDIFY')
    solid.thickness = .004
    solid.offset = -1
    rod('UMBRELLA_Finial', (0, .025, 1.775), (0, .025, 1.80), .014,
        group, 'gold', glossy)
    for i in range(8):
        a = 2 * math.pi * i / 8
        rod('UMBRELLA_Rib_%02d' % i, (0, .025, 1.66),
            (.67 * math.cos(a), .375 * math.sin(a), 1.524), .004,
            group, 'cream', glossy, 8)


def build(root):
    glossy = material('Warm glazed enamel and food palette', .06, .28, .27)
    satin = material('Satin hardware and dark tyres', .28, .48, 0)
    groups = {name: empty(name, root) for name in GROUPS}
    body, umbrella, tubs, flap, tray = (groups[name] for name in GROUPS)
    flap.location = (0, -.298, .46)
    bpy.context.view_layer.update()
    body['features'] = 'closed insulated box; two main wheels; rear caster; handlebar; bell'
    tubs['inspect_target'] = True
    tubs['flavour_count'] = 3
    flap['hinge_axis'] = 'local X; static closed pose'
    tray['contents'] = 'three rounded ice bars with plain wood sticks; two wafer sandwiches'
    box('BOX_InsulatedCreamShell', (0, 0, .625), (1.10, .56, .65), body, 'cream', glossy, .035)
    box('BOX_CoralLowerPlinth', (0, 0, .335), (1.13, .59, .09), body, 'coral', glossy, .022)
    box('BOX_CoralWaistBand', (0, 0, .86), (1.115, .574, .06), body, 'coral', glossy, .012)
    box('COUNTER_RoundedLip', (0, 0, .964), (1.17, .63, .055), body, 'cream', glossy, .018)
    box('LID_DarkGasket', (0, .135, .996), (.86, .24, .014), body, 'dark', satin, .005)
    box('LID_ClosedInsulatedTop', (0, .135, 1.012), (.84, .22, .035), body, 'mint', glossy, .012)
    box('LID_LiftGrip', (0, .135, 1.041), (.15, .028, .025), body, 'cream', glossy, .01)
    for x in [-.32, .32]:
        rod('LID_RearHinge', (x - .035, .245, 1.017), (x + .035, .245, 1.017), .012,
            body, 'steel', satin)
    rod('CHASSIS_MainAxle', (-.64, .065, .21), (.64, .065, .21), .025, body, 'steel', satin)
    for side in [-1, 1]:
        x = side * .612
        profile('WHEEL_MainTyre_' + ('Left' if side < 0 else 'Right'), (x, .065, .21),
                [(-.036, .18), (-.025, .21), (.025, .21), (.036, .18)], body, 'dark', satin, axis='X')
        for sign in [-1, 1]:
            xx = x + sign * .037
            profile('WHEEL_CreamInsetHub', (xx, .065, .21), [(-.004, .139), (.004, .139)],
                    body, 'cream', glossy, axis='X')
            rod('WHEEL_AxleCap', (xx - .006, .065, .21), (xx + .006, .065, .21), .036,
                body, 'coral', glossy)
    # Rear supporting caster makes this a stable three-wheel push cart.
    profile('WHEEL_RearCaster', (0, .265, .075), [(-.025, .061), (-.018, .075), (.018, .075), (.025, .061)],
            body, 'dark', satin, segments=16, axis='X')
    for x in [-.037, .037]:
        rod('CASTER_Fork', (x, .265, .075), (x, .265, .32), .012, body, 'steel', satin)
    for x in [-.43, .43]:
        rod('HANDLE_SweptSupport', (x, .27, .71), (x, .352, 1.015), .018, body, 'steel', satin)
    rod('HANDLE_PushBar', (-.46, .352, 1.015), (.46, .352, 1.015), .02, body, 'steel', satin)
    for x in [-.34, .34]:
        rod('HANDLE_WarmGrip', (x - .09, .352, 1.015), (x + .09, .352, 1.015), .025, body, 'cocoa', glossy)
    rod('BELL_Bracket', (.235, .352, 1.02), (.235, .352, 1.065), .012, body, 'steel', satin)
    profile('BELL_GoldenDome', (.235, .352, 1.06), [(0, .035), (.018, .033), (.032, .022), (.038, .006)],
            body, 'gold', glossy, segments=16)
    rod('BELL_ThumbLever', (.258, .352, 1.065), (.295, .352, 1.065), .007, body, 'cocoa', glossy)
    rod('UMBRELLA_RearMast', (0, .25, .97), (0, .25, 1.51), .018, body, 'steel', satin)
    rod('UMBRELLA_OffsetCrownSupport', (0, .25, 1.51), (0, .025, 1.77), .016, body, 'steel', satin)
    canopy(umbrella, glossy)

    # Three shallow open flavour tubs sit above the closed insulated cabinet.
    for i, (x, color) in enumerate([(-.325, 'berry'), (0, 'vanilla'), (.325, 'mint')], 1):
        prefix = 'TUB_%02d_' % i
        open_tub(prefix + 'OpenContainer', x, tubs, glossy)
        # Food sits inside the tapered shell, 40 mm below the rim's top surface.
        box(prefix + 'FrozenSlab', (x, -.128, 1.040), (.232, .182, .060), tubs, color, glossy, .008)
    # Separate hinge node allows downstream inspection or future consumer animation.
    box('FLAP_RecessedGasket', (0, -.285, .635), (.77, .018, .39), body, 'cocoa', glossy, .016)
    box('FLAP_ClosedMintPanel', (0, -.302, .635), (.73, .028, .35), flap, 'mint', glossy, .018)
    box('FLAP_HandleShadow', (0, -.32, .742), (.165, .007, .032), flap, 'cocoa', glossy, .009)
    box('FLAP_Grip', (0, -.328, .752), (.14, .018, .021), flap, 'cream', glossy, .008)
    for x in [-.25, .25]:
        rod('FLAP_LowerHinge', (x - .04, -.321, .465), (x + .04, -.321, .465), .012,
            flap, 'cream', glossy)
    box('TRAY_FrontShelf', (0, -.333, .922), (.82, .13, .025), tray, 'coral', glossy, .01)
    box('TRAY_CreamInsert', (0, -.34, .939), (.76, .105, .012), tray, 'cream', glossy, .006)
    tray_top = .939 + .012 / 2
    for i, (x, color) in enumerate([(-.29, 'berry'), (-.145, 'vanilla'), (0, 'mint')], 1):
        box('BAR_%02d_RoundedStickIce' % i, (x, -.34, tray_top + .034 / 2),
            (.112, .052, .034), tray, color, glossy, .009)
        box('STICK_%02d_PlainWoodGrip' % i, (x + .067, -.34, tray_top + .008 / 2),
            (.046, .014, .008), tray, 'cocoa', glossy, .003)
    for i, x in enumerate([.155, .29], 1):
        box('WAFER_%02d_Filling' % i, (x, -.34, .972), (.105, .077, .036), tray, 'cocoa', glossy, .003)
        for z in [.95, .995]:
            box('WAFER_%02d_PlainBiscuit' % i, (x, -.34, z), (.112, .082, .012), tray, 'wafer', glossy, .002)
        for j in [-1, 0, 1]:
            rod('WAFER_%02d_EmbossedGrid' % i, (x + j * .027, -.372, 1.002),
                (x + j * .027, -.308, 1.002), .0015, tray, 'cream', glossy, 6)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, .53))
    collider = bpy.context.object
    collider.name = 'collider_box'
    collider.dimensions = (1.30, .79, 1.06)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    collider.parent = root
    collider.display_type = 'WIRE'
    collider.hide_render = True
    collider.hide_set(True)
    collider['role'] = 'walkable-blocking AABB; no material; not visual geometry'
    collider['hidden'] = True
    return groups


def export(path):
    # Export evaluated copies, preserving every named editable source object in the blend.
    copies = []
    root = bpy.data.objects[ROOT]
    export_root = empty(ROOT + '_Export')
    for key in root.keys():
        export_root[key] = root[key]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for name in GROUPS:
        group = bpy.data.objects[name]
        members = []
        for source in group.children_recursive:
            if source.type != 'MESH':
                continue
            mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
            # Bevel interpolation can overshoot a colour of 1 by one float ULP.
            for attribute in mesh.color_attributes:
                for item in attribute.data:
                    item.color = tuple(max(0.0, min(1.0, c)) for c in item.color)
            o = bpy.data.objects.new(source.name + '_Evaluated', mesh)
            bpy.context.scene.collection.objects.link(o)
            o.matrix_world = source.matrix_world.copy()
            members.append(o)
        bpy.ops.object.select_all(action='DESELECT')
        for o in members:
            o.select_set(True)
        bpy.context.view_layer.objects.active = members[0]
        bpy.ops.object.join()
        o = bpy.context.object
        o.name = name + '_Export'
        o.data.name = name
        # Set the exported local origin to the named source group's pivot.
        world = o.matrix_world.copy()
        pivot = group.matrix_world.copy()
        o.data.transform(pivot.inverted() @ world)
        o.matrix_world = pivot
        o.parent = export_root
        for key in group.keys():
            o[key] = group[key]
        o['source_parts'] = [s.name for s in group.children_recursive if s.type == 'MESH']
        copies.append(o)
    source = bpy.data.objects['collider_box']
    collider = bpy.data.objects.new('collider_box_Export', source.data.copy())
    bpy.context.scene.collection.objects.link(collider)
    collider.matrix_world = source.matrix_world.copy()
    collider.parent = export_root
    collider['hidden'] = True
    collider['role'] = source['role']
    copies.append(collider)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [export_root] + copies:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True, export_animations=False,
                              export_texcoords=False, export_normals=True, export_extras=True,
                              export_cameras=False, export_lights=False)
    for o in copies + [export_root]:
        bpy.data.objects.remove(o, do_unlink=True)
    # glTF has no core visibility flag. Keep the unmaterialed collider in a separate,
    # inactive scene, which stock GLTFLoader will not add to the gallery's visual scene.
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    binary = raw[20 + size:]
    for node in doc['nodes']:
        if node.get('name', '').endswith('_Export'):
            node['name'] = node['name'][:-7]
    root_index = next(i for i, n in enumerate(doc['nodes']) if n.get('name') == ROOT)
    collider_index = next(i for i, n in enumerate(doc['nodes']) if n.get('name') == 'collider_box')
    doc['nodes'][root_index]['children'].remove(collider_index)
    collision_scene = len(doc['scenes'])
    doc['scenes'].append({'name': 'COLLISION_ONLY_NotVisible', 'nodes': [collider_index]})
    doc['nodes'][root_index].setdefault('extras', {})['collision_scene'] = collision_scene
    doc['nodes'][root_index]['extras']['collider_node'] = 'collider_box'
    text = json.dumps(doc, separators=(',', ':')).encode()
    text += b' ' * (-len(text) % 4)
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(text) + len(binary)) +
                     struct.pack('<I4s', len(text), b'JSON') + text + binary)


def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    s = bpy.context.scene
    s.world = bpy.data.worlds.new('Warm slate studio')
    s.world.use_nodes = True
    s.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.16, .19, .20, 1)
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    for name, loc, energy, size in [('Key', (-3, -4, 5), 650, 4),
                                     ('Fill', (3, -1, 3), 430, 3),
                                     ('Rim', (0, 4, 4), 800, 3)]:
        bpy.ops.object.light_add(type='AREA', location=loc)
        o = bpy.context.object
        o.name = 'STUDIO_' + name
        o.data.energy = energy
        o.data.shape = 'DISK'
        o.data.size = size
        aim(o, TARGET)
    bpy.ops.object.camera_add()
    s.camera = bpy.context.object
    s.camera.name = 'STUDIO_Camera'
    s.camera.data.type = 'ORTHO'
    s.camera.data.ortho_scale = 2.16
    s.render.engine = 'CYCLES'
    s.cycles.samples = 32
    s.cycles.use_denoising = True
    s.cycles.seed = 0
    s.render.resolution_x = s.render.resolution_y = 768
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = 'PNG'
    s.view_settings.view_transform = 'AgX'


def render_views():
    s = bpy.context.scene
    for name, delta in [('hero', (2.5, -4, 2.0)), ('front', (0, -4, .25)),
                        ('side', (4, 0, .35)), ('3q', (-2.5, -4, 1.8))]:
        s.camera.location = TARGET + Vector(delta)
        aim(s.camera, TARGET)
        s.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def main():
    for d in ['sources', 'exports', 'previews', 'reports', 'metadata']:
        (HERE / d).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.context.scene.unit_settings.system = 'METRIC'
        bpy.context.scene.unit_settings.scale_length = 1
        root = empty(ROOT)
        root['units'] = 'metres'
        root['front_axis'] = 'Blender -Y / glTF +Z'
        root['up_axis'] = 'Blender +Z / glTF +Y'
        root['origin'] = 'floor centre'
        root['original_procedural_asset'] = True
        build(root)
        studio()
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'sources' / (SLUG + '.blend')), compress=True)
    export(HERE / 'exports' / 'optimized.glb')
    if '--skip-render' not in sys.argv:
        render_views()


if __name__ == '__main__':
    main()
