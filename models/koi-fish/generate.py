"""Original metric pond koi. Blender 5.2.3; analytic geometry, no external assets."""
from pathlib import Path
import math
import sys
import bpy
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = 'ASSET_KoiFish'
SLUG = 'koi-fish'
PALETTE = ((.91, .90, .81), (.78, .105, .045), (.035, .043, .047))
PROFILE = [(-.150, .0035, .006, .047), (-.142, .012, .013, .048),
           (-.124, .020, .022, .048), (-.095, .025, .028, .048),
           (-.055, .026, .029, .048), (-.010, .023, .025, .047),
           (.030, .016, .019, .046), (.065, .0085, .011, .045),
           (.090, .004, .007, .045)]
SPINE = [('Head', -.15, -.065), ('Body', -.065, -.005),
         ('Peduncle', -.005, .048), ('Tail', .048, .090), ('Caudal', .090, .15)]


def linear(value):
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def material(name, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Coat Weight'].default_value = .16
    color = mat.node_tree.nodes.new('ShaderNodeVertexColor')
    color.layer_name = 'Color'
    mat.node_tree.links.new(color.outputs['Color'], shader.inputs['Base Color'])
    return mat


def profile(y):
    for a, b in zip(PROFILE, PROFILE[1:]):
        if y <= b[0]:
            t = max(0, min(1, (y - a[0]) / (b[0] - a[0])))
            t = t * t * (3 - 2 * t)
            return tuple(a[i] * (1 - t) + b[i] * t for i in (1, 2, 3))
    return PROFILE[-1][1:]


def pigment(y, angle):
    # Original irregular dorsal islands; no image, logo, lettering or copied pattern.
    color = PALETTE[0]
    patches = [(-.115, .038, 0, 1.75, 1), (-.048, .033, -.55, 1.6, 1),
               (.025, .031, .35, 1.9, 1), (-.080, .014, 1.08, .50, 2),
               (-.015, .015, -.65, .57, 2), (.046, .012, -.25, .65, 2),
               (-.046, .013, .55, .55, 2)]
    for index, (cy, ry, ca, ra, tone) in enumerate(patches):
        delta = math.atan2(math.sin(angle - ca), math.cos(angle - ca))
        edge = ((y - cy) / ry) ** 2 + (delta / ra) ** 2
        edge += .10 * math.sin(y * 500 + index) * math.cos(angle * 7)
        blend = max(0, min(1, (1.10 - edge) / .22))
        color = tuple(c * (1 - blend) + d * blend for c, d in zip(color, PALETTE[tone]))
    return color


def mesh(name, vertices, faces, colors, mat, root, fin=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = root
    data.materials.append(mat)
    attr = data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
    for cell, color in zip(attr.data, colors):
        cell.color = tuple(linear(c) for c in color) + (1,)
    for face in data.polygons:
        face.use_smooth = True
    if fin:
        obj['fin_bone'] = fin
    return obj


def body(root, mat):
    vertices, faces, colors = [], [], []
    rings, sides = 97, 56
    for i in range(rings):
        y = -.15 + .24 * i / (rings - 1)
        width, height, center = profile(y)
        for j in range(sides):
            angle = 2 * math.pi * j / sides
            vertices.append((width * math.sin(angle), y, center + height * math.cos(angle)))
            colors.append(pigment(y, angle))
    for i in range(rings - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces += [tuple(reversed(range(sides))), tuple((rings - 1) * sides + j for j in range(sides))]
    return mesh('BODY_PearlRedInk', vertices, faces, colors, mat, root)


def membrane(name, roots, tips, mat, root, bone=None):
    # A thin closed web retains a clean silhouette without alpha sorting.
    count, steps = len(roots), 5
    vertices, colors, faces = [], [], []
    for side in (-1, 1):
        for i, (start, end) in enumerate(zip(roots, tips)):
            for j in range(steps):
                t = j / (steps - 1)
                p = Vector(start).lerp(Vector(end), t)
                if bone or 'Pelvic' in name:
                    p.z += side * .00016
                else:
                    p.x += side * .00016
                vertices.append(tuple(p))
                shade = min(.98, .84 + .10 * t - .025 * math.cos(i * math.pi))
                colors.append((shade, shade * .98, shade * .90))
    layer = count * steps
    for side in range(2):
        for i in range(count - 1):
            for j in range(steps - 1):
                a = side * layer + i * steps + j
                face = (a, a + steps, a + steps + 1, a + 1)
                faces.append(face if side else tuple(reversed(face)))
    perimeter = list(range(steps)) + [i * steps + steps - 1 for i in range(1, count)]
    perimeter += [(count - 1) * steps + j for j in range(steps - 2, -1, -1)]
    perimeter += [i * steps for i in range(count - 2, 0, -1)]
    for a, b in zip(perimeter, perimeter[1:] + perimeter[:1]):
        faces.append((a, b, b + layer, a + layer))
    return mesh(name, vertices, faces, colors, mat, root, bone)


def tube(name, points, radius, mat, root, color):
    vertices, faces = [], []
    for i, point in enumerate(points):
        tangent = Vector(points[min(i + 1, len(points) - 1)]) - Vector(points[max(i - 1, 0)])
        tangent.normalize()
        u = tangent.cross(Vector((0, 0, 1)))
        if u.length < .01:
            u = tangent.cross(Vector((1, 0, 0)))
        u.normalize()
        v = tangent.cross(u).normalized()
        r = radius * (1 - .72 * i / (len(points) - 1))
        for j in range(6):
            a = 2 * math.pi * j / 6
            vertices.append(tuple(Vector(point) + r * (u * math.cos(a) + v * math.sin(a))))
    for i in range(len(points) - 1):
        for j in range(6):
            a = i * 6 + j
            b = i * 6 + (j + 1) % 6
            faces.append((a, b, b + 6, a + 6))
    faces += [tuple(reversed(range(6))), tuple((len(points) - 1) * 6 + j for j in range(6))]
    return mesh(name, vertices, faces, [color] * len(vertices), mat, root)


def ellipsoid(name, center, scale, mat, root, color):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)
    obj.parent = root
    obj.data.materials.append(mat)
    attr = obj.data.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
    for cell in attr.data:
        cell.color = tuple(linear(c) for c in color) + (1,)
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def build(root):
    pearl = material('Koi pearl pigment', .30)
    ivory = material('Koi ivory fin webs', .42)
    ink = material('Koi dark eyes', .19)
    body(root, pearl)
    roots, tips = [], []
    for i in range(21):
        u = -1 + 2 * i / 20
        roots.append((0, .080, .045 + .006 * u))
        tips.append((0, .15 - .025 * (1 - abs(u)) ** 1.5, .045 + .031 * u))
    membrane('FIN_CaudalFork', roots, tips, ivory, root)
    for label, sign, begin, end, height in [('Dorsal', 1, -.083, .063, .025),
                                           ('Anal', -1, .008, .064, .014)]:
        roots, tips = [], []
        for i in range(23):
            t = i / 22
            y = begin + (end - begin) * t
            _, radius, center = profile(y)
            z = center + sign * radius * .97
            roots.append((0, y, z))
            tips.append((0, y + .010 * math.sin(math.pi * t),
                         z + sign * (height * math.sin(math.pi * t) ** .7 + .0005)))
        membrane('FIN_' + label, roots, tips, ivory, root)
    for side, label in [(-1, 'L'), (1, 'R')]:
        roots, tips = [], []
        for i in range(21):
            t = i / 20
            roots.append((side * .020, -.091 + .009 * t, .043))
            tips.append((side * (.021 + .035 * math.sin(math.pi * t) ** .8),
                         -.091 + .059 * t, .043 - .019 * math.sin(math.pi * t)))
        membrane('FIN_Pectoral_' + label, roots, tips, ivory, root, 'Pectoral_' + label)
        roots, tips = [], []
        for i in range(15):
            t = i / 14
            roots.append((side * .014, -.008 + .008 * t, .026))
            tips.append((side * (.0149 + .013 * math.sin(math.pi * t)),
                         -.006 + .032 * t, .026 - .015 * math.sin(math.pi * t)))
        membrane('FIN_Pelvic_' + label, roots, tips, ivory, root)
        ellipsoid('EYE_' + label, (side * .0157, -.131, .057), (.0032, .0040, .0037),
                  ink, root, PALETTE[2])
        ellipsoid('EYE_Glint_' + label, (side * .0184, -.1325, .0585), (.0006, .0009, .0008),
                  pearl, root, PALETTE[0])
        # Two short barbels per side distinguish the small ornamental carp head.
        for index in range(2):
            x = .0045 + index * .004
            tube('BARBEL_' + label + '_' + str(index),
                 [(side * x, -.146 + index * .007, .043),
                  (side * (x + .004), -.150 + index * .006, .038),
                  (side * (x + .005), -.148 + index * .005, .034)],
                 .00060, ivory, root, PALETTE[0])
        # A restrained opercular crease follows the cheek, without floating discs.
        points = []
        for i in range(13):
            a = .45 + 2.1 * i / 12
            y = -.107 + .005 * math.sin(a)
            width, radius, center = profile(y)
            points.append((side * width * math.sin(a), y, center + radius * math.cos(a)))
        tube('GILL_' + label, points, .00024, pearl, root, (.58, .58, .52))
    ellipsoid('MOUTH_Lips', (0, -.1491, .0443), (.0045, .0009, .0024), pearl, root, (.70, .66, .54))
    ellipsoid('MOUTH_ClosedCrease', (0, -.1499, .0443), (.0031, .00012, .00045), ink, root, (.18, .15, .12))
    parts = sorted((o for o in root.children_recursive if o.type == 'MESH'), key=lambda o: o.name)
    # Place the actual mesh envelope at floor centre before rigging.
    points = [v.co for o in parts for v in o.data.vertices]
    low = min(p.z for p in points)
    center_y = (min(p.y for p in points) + max(p.y for p in points)) / 2
    for obj in parts:
        for v in obj.data.vertices:
            v.co.z -= low
            v.co.y -= center_y
    rig(root, parts, low, center_y)


def rig(root, parts, floor, center_y):
    data = bpy.data.armatures.new('Koi swim skeleton')
    armature = bpy.data.objects.new('RIG_KoiSwim', data)
    bpy.context.scene.collection.objects.link(armature)
    armature.parent = root
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    previous = None
    for name, start, end in SPINE:
        bone = data.edit_bones.new(name)
        bone.head = (0, start - center_y, .045 - floor)
        bone.tail = (0, end - center_y, .045 - floor)
        if previous:
            bone.parent = previous
            bone.use_connect = True
        previous = bone
    for side, label in [(-1, 'L'), (1, 'R')]:
        bone = data.edit_bones.new('Pectoral_' + label)
        bone.head = (side * .020, -.087 - center_y, .043 - floor)
        bone.tail = (side * .052, -.056 - center_y, .026 - floor)
        bone.parent = data.edit_bones['Head']
    bpy.ops.object.mode_set(mode='OBJECT')
    names = [row[0] for row in SPINE]
    anchors = [-.085, -.027, .027, .075, .112]
    for obj in parts:
        obj.parent = armature
        groups = {name: obj.vertex_groups.new(name=name) for name in data.bones.keys()}
        for vertex in obj.data.vertices:
            y = vertex.co.y + center_y
            weights = {names[0]: 1.}
            if y >= anchors[-1]:
                weights = {names[-1]: 1.}
            else:
                for i in range(len(anchors) - 1):
                    if anchors[i] <= y <= anchors[i + 1]:
                        t = (y - anchors[i]) / (anchors[i + 1] - anchors[i])
                        weights = {names[i]: 1 - t, names[i + 1]: t}
                        break
            if obj.get('fin_bone'):
                blend = min(.95, max(0, (abs(vertex.co.x) - .020) / .034))
                weights = {key: value * (1 - blend) for key, value in weights.items()}
                weights[obj['fin_bone']] = blend
            for name, weight in weights.items():
                if weight > 1e-8:
                    groups[name].add([vertex.index], weight, 'REPLACE')
        modifier = obj.modifiers.new('Portable skeletal swim', 'ARMATURE')
        modifier.object = armature
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start = 0
    scene.frame_end = 72
    for frame in range(0, 73, 2):
        phase = 0 if frame == 72 else 2 * math.pi * frame / 72
        for i, name in enumerate(names):
            bone = armature.pose.bones[name]
            bone.rotation_mode = 'XYZ'
            amplitude = [0, .025, .065, .13, .19][i]
            bone.rotation_euler.z = amplitude * (math.sin(phase) + .28 * math.sin(2 * phase) * i / 4)
            bone.keyframe_insert(data_path='rotation_euler', frame=frame, group=name)
        for side, label in [(-1, 'L'), (1, 'R')]:
            bone = armature.pose.bones['Pectoral_' + label]
            bone.rotation_mode = 'XYZ'
            bone.rotation_euler.x = side * .10 * math.sin(2 * phase)
            bone.keyframe_insert(data_path='rotation_euler', frame=frame, group=bone.name)
    action = armature.animation_data.action
    action.name = 'Swim_Loop'
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    scene.frame_set(0)


def export(path):
    """Join temporary weighted mesh copies; keep every saved source part editable."""
    root = bpy.data.objects[ROOT]
    parts = sorted((o for o in root.children_recursive if o.type == 'MESH'), key=lambda o: o.name)
    armature = next(o for o in root.children_recursive if o.type == 'ARMATURE')
    copies = []
    try:
        bpy.context.scene.frame_set(0)
        bpy.context.view_layer.update()
        for obj in parts:
            copy = obj.copy()
            copy.data = obj.data.copy()
            # Fix quad diagonals before glTF tessellation, which otherwise varies
            # triangle indices between identical headless rebuilds on this host.
            bm = bmesh.new()
            bm.from_mesh(copy.data)
            bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='FIXED', ngon_method='EAR_CLIP')
            bm.to_mesh(copy.data)
            bm.free()
            copy.data.update()
            bpy.context.scene.collection.objects.link(copy)
            copy.parent = None
            copy.matrix_world = obj.matrix_world.copy()
            copies.append(copy)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in copies:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join()
        merged = copies[0]
        merged.name = 'Koi_WeightedSurface'
        merged.data.name = 'Koi_ExportSurface'
        # glTF skinning ignores a mesh parent's transforms: export at scene root.
        merged.parent = None
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [root, armature, merged]:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=False, export_yup=True, export_animations=True,
                                  export_animation_mode='ACTIVE_ACTIONS', export_frame_range=True,
                                  export_force_sampling=True, export_nla_strips_merged_animation_name='Swim_Loop',
                                  export_texcoords=False, export_extras=True,
                                  export_cameras=False, export_lights=False)
    finally:
        for obj in copies:
            try:
                data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if data.users == 0:
                    bpy.data.meshes.remove(data)
            except ReferenceError:
                pass


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Neutral mall studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.13, .17, .19, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
    for name, location, power, size in [('Key', (.2, -.4, .6), 16, .45),
                                         ('Fill', (-.4, -.1, .2), 8, .35),
                                         ('Rim', (.1, .4, .5), 20, .3)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        obj = bpy.context.object
        obj.name = 'STUDIO_' + name
        obj.data.energy = power
        obj.data.shape = 'DISK'
        obj.data.size = size
        aim(obj, (0, 0, .045))
    bpy.ops.object.camera_add()
    scene.camera = bpy.context.object
    scene.camera.name = 'STUDIO_Camera'
    scene.camera.data.type = 'ORTHO'
    scene.camera.data.ortho_scale = .40
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.camera.location = (.46, -.38, .37)
    aim(scene.camera, (0, 0, .045))


def render_views():
    scene = bpy.context.scene
    views = [('hero', (.46, -.38, .37)), ('front', (0, -.65, .10)),
             ('side', (.65, 0, .06)), ('3q', (-.40, -.32, .45)), ('top', (0, .001, .70))]
    for name, location in views:
        scene.frame_set(0)
        scene.camera.location = location
        aim(scene.camera, (0, 0, .045))
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = str(HERE / 'previews' / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        scene.render.image_settings.file_format = 'WEBP'
        scene.render.image_settings.quality = 88
        bpy.data.images['Render Result'].save_render(str(HERE / 'previews' / (name + '.webp')), scene=scene)


def main():
    for folder in ['sources', 'exports', 'previews', 'metadata', 'reports']:
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
        root['origin'] = 'Floor centre of reference pose envelope'
        root['scope'] = 'Original small ornamental koi; in-place artist-tuned swim, no trajectory or water simulation'
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
