"""Verify and render the exact exported boots using Blender and the supplied gates."""

from contextlib import redirect_stdout
import io
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from fit_shoes import (GLB, MASTER, MOTION, SOURCE, Foot, evaluated_points, file_hash, frames,
                       import_motion, master_scene, set_pose, signed_hits, source_boot, topology)

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
EXPORT = Path(ARGS[0]).resolve() if ARGS else GLB
OUTPUT = Path(ARGS[1]).resolve() if len(ARGS) > 1 else HERE / 'qa'
OUTPUT.mkdir(exist_ok=True, parents=True)
assert OUTPUT.is_relative_to(HERE)


def write_json(name, result):
    (OUTPUT / name).write_text(json.dumps(result, indent=2) + '\n')


def render_settings(scene, width, height, samples, transparent=False):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = not transparent
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    scene.render.film_transparent = transparent
    scene.world = bpy.data.worlds.new('Boot QA world')
    background = scene.world.node_tree.nodes.get('Background') if scene.world.node_tree else None
    if background is None:
        scene.world.use_nodes = True
        background = scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.72, .77, .85, 1)
    background.inputs['Strength'].default_value = .55
    data = bpy.data.cameras.new('Boot QA camera')
    data.type = 'ORTHO'
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def aim(camera, center, direction, scale):
    camera.location = Vector(center) + Vector(direction)
    camera.rotation_euler = (-Vector(direction)).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale


def studio(scene, center):
    for name, position, energy, size in (
        ('Warm key', (-.52, -.65, .82), 31, .75),
        ('Soft fill', (.72, -.39, .48), 13, .66),
        ('White rim', (.22, .61, .68), 23, .59),
    ):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = energy, 'DISK', size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = position
        light.rotation_euler = (Vector(center) - light.location).to_track_quat('-Z', 'Y').to_euler()


def render(scene, name, pixels=False):
    path = OUTPUT / f'{name}.png'
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    if pixels:
        image = bpy.data.images.load(str(path), check_existing=False)
        data = np.empty(len(image.pixels), np.float32)
        image.pixels.foreach_get(data)
        result = data.reshape(image.size[1], image.size[0], 4)
        bpy.data.images.remove(image)
        return result


def on_master():
    scene, arm, body = master_scene()
    original = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(EXPORT), merge_vertices=True)
    imported = [obj for obj in scene.objects if obj not in original]
    shoes, = (obj for obj in imported if obj.type == 'MESH' and obj.vertex_groups)
    world = shoes.matrix_world.copy()
    shoes.parent = None
    shoes.matrix_world = world
    for obj in imported:
        if obj != shoes:
            bpy.data.objects.remove(obj, do_unlink=True)
    for modifier in list(shoes.modifiers):
        shoes.modifiers.remove(modifier)
    shoes.modifiers.new('Master skin', 'ARMATURE').object = arm
    body.hide_render = False
    body.hide_set(False)
    import_motion(scene)
    return scene, arm, body, shoes


def supplied():
    passed = True
    for name in ('motion_check', 'motion_check_tri'):
        path = HERE / 'work' / f'{name}.py'
        source = path.read_text()
        workbench = ("sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';"
                     "sc.display.shading.color_type='MATERIAL'")
        assert source.count(workbench) == 1
        cpu = (
            "sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=8;"
            "sc.cycles.use_denoising=True;sc.render.use_compositing=False;sc.render.use_sequencer=False\n"
            "sc.world=bpy.data.worlds.new('Checker light');sc.world.use_nodes=True\n"
            "bg=sc.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.74,.78,.85,1);"
            "bg.inputs[1].default_value=.8"
        )
        source = source.replace(workbench, cpu)
        source = source.replace('{out}/motion_check.json', '{out}/' + name + '.json')
        if name.endswith('_tri'):
            source = source.replace('bpy.ops.render.render(write_still=True)', 'None')
        output = io.StringIO()
        argv = sys.argv
        try:
            sys.argv = [str(path), '--', str(MASTER), str(MOTION), str(EXPORT), str(OUTPUT)]
            with redirect_stdout(output):
                exec(compile(source, str(path), 'exec'), {})
        finally:
            sys.argv = argv
        results = [line for line in output.getvalue().splitlines() if line.startswith('RESULT ')]
        assert len(results) == 8
        result = '\n'.join(results) + '\n'
        (OUTPUT / (name + '.txt')).write_text(result)
        print(result, end='', flush=True)
        report = json.loads((OUTPUT / (name + '.json')).read_text())
        passed &= all(count == 0 and distance >= .0005 for count, distance in report.values())
    write_json('checker_manifest.json', {
        'export_sha256': file_hash(EXPORT),
        'checker_source_sha256': {
            name: file_hash(HERE / 'work' / (name + '.py'))
            for name in ('motion_check', 'motion_check_tri')
        },
        'passed': passed,
    })
    return passed


def dense_scan():
    scene, arm, body, shoes = on_master()
    bpy.context.view_layer.update()
    body_faces, shoe_faces = topology(body).tolist(), topology(shoes).tolist()
    result = {}
    rest_body = np.array([tuple(v.co) for v in body.data.vertices])
    for clip, time in frames():
        set_pose(scene, arm, clip, time)
        body_xyz, shoe_xyz = evaluated_points(body), evaluated_points(shoes)
        tree = BVHTree.FromPolygons(body_xyz.tolist(), body_faces, all_triangles=True)
        shoe_tree = BVHTree.FromPolygons(shoe_xyz.tolist(), shoe_faces, all_triangles=True)
        d, _, nearest = signed_hits(tree, shoe_xyz)
        minimum, pairs = float(d.min()), len(tree.overlap(shoe_tree))
        count = int((d < 0).sum())
        row = result.setdefault(clip, {'samples': 0, 'max_vertices_inside': 0, 'max_overlap_pairs': 0,
                                       'min_signed_distance_m': math.inf})
        row['samples'] += 1
        row['max_vertices_inside'] = max(row['max_vertices_inside'], count)
        row['max_overlap_pairs'] = max(row['max_overlap_pairs'], pairs)
        if minimum < row['min_signed_distance_m']:
            row.update(min_signed_distance_m=minimum, min_distance_frame=time,
                       closest_vertex_rest=list(shoes.data.vertices[int(d.argmin())].co),
                       closest_body_triangle_rest=rest_body[body_faces[nearest[d.argmin()]]].mean(0).tolist())
    print('DENSE', json.dumps(result), flush=True)
    write_json('dense_check.json', {'export_sha256': file_hash(EXPORT), 'clips': result})
    return all(row['max_vertices_inside'] == row['max_overlap_pairs'] == 0
               and row['min_signed_distance_m'] >= .0005 for row in result.values())


def previews():
    scene, arm, body, shoes = on_master()
    camera = render_settings(scene, 720, 650, 24)
    center = (0, -.017, .061)
    studio(scene, center)
    body.hide_render = True
    for name, direction, scale in (
        ('boots_preview', (.64, -.95, .52), .40),
        ('boots_front', (0, -1, .13), .40),
        ('boots_side', (1, -.06, .12), .40),
        ('boots_underside', (.16, -.13, -1), .40),
    ):
        aim(camera, center, direction, scale)
        render(scene, name)


def emission(name, rgb):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    node = nodes.new('ShaderNodeEmission')
    node.inputs['Color'].default_value = (*rgb, 1)
    output = nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(node.outputs[0], output.inputs[0])
    return material


def replace_materials(obj, replacement):
    for index in range(len(obj.data.materials)):
        obj.data.materials[index] = replacement


def filled_silhouette(mask):
    """Flood fill from the image perimeter to detect enclosed holes."""
    height, width = mask.shape
    padded = np.pad(mask, 1)
    stride = width + 2
    outside = bytearray((~padded).ravel())
    stack = [0]
    outside[0] = 0
    reached = np.zeros_like(padded)
    while stack:
        index = stack.pop()
        row, col = divmod(index, stride)
        reached[row, col] = True
        for adjacent in (index - 1 if col else 0,
                         index + 1 if col < width + 1 else 0,
                         index - stride if row else 0,
                         index + stride if row < height + 1 else 0):
            if outside[adjacent]:
                outside[adjacent] = 0
                stack.append(adjacent)
    return ~reached[1:-1, 1:-1]


def install_skin_mask(body):
    # Green identifies the selected foot's plantar skin. Magenta identifies
    # the rest of the body, so skin from either leg can expose a sole hole.
    magenta = emission('Body skin magenta', (1, 0, 1))
    green = emission('Selected plantar skin green', (0, 1, 0))
    replace_materials(body, magenta)
    body.data.materials.append(green)
    green_slot = len(body.data.materials) - 1
    vertices = np.array([tuple(v.co) for v in body.data.vertices])
    centers = np.array([vertices[list(face.vertices)].mean(axis=0) for face in body.data.polygons])

    def select_foot(side):
        selected = ((centers[:, 0] * side > 0) & (centers[:, 2] < .045)).astype(np.int32)
        body.data.polygons.foreach_set('material_index', selected * green_slot)
        body.data.update()
    return select_foot


def skin_gate():
    scene, arm, body, shoes = on_master()
    camera = render_settings(scene, 600, 540, 8, transparent=True)
    scene.cycles.max_bounces = 0
    scene.view_settings.view_transform = 'Standard'
    shoe_red = emission('Upper red', (1, 0, 0))
    shoe_blue = emission('Sole blue', (0, 0, 1))
    replace_materials(shoes, shoe_red)
    shoes.data.materials.append(shoe_blue)
    shoe_z = np.array([v.co.z for v in shoes.data.vertices])
    shoe_x = np.array([v.co.x for v in shoes.data.vertices])
    for face in shoes.data.polygons:
        if shoe_z[list(face.vertices)].mean() < .012:
            face.material_index = len(shoes.data.materials) - 1
    select_foot = install_skin_mask(body)
    # Include the high-heel cases from the sneaker review and the leg's
    # actual airborne maxima measured on each side of the supplied clips.
    cases = [('walk', 17, 1), ('walk', 19, 1), ('walk', 31, -1),
             ('run', 4, -1), ('run', 12, -1), ('run', 19, 1)]
    rest_skin = np.array([tuple(v.co) for v in body.data.vertices])
    result = {}
    for clip, time, side in cases:
        set_pose(scene, arm, clip, time)
        select_foot(side)
        posed = evaluated_points(shoes)
        plantar = (rest_skin[:, 0] * side > 0) & (rest_skin[:, 2] < .025)
        floor_range = evaluated_points(body)[plantar, 2]
        target = (shoe_x * side > 0) & (shoe_z < .031)
        sole_center = (posed[target].max(0) + posed[target].min(0)) / 2
        transform = arm.pose.bones[f'mixamorig:{"Left" if side > 0 else "Right"}Foot']
        motion = (transform.matrix @ transform.bone.matrix_local.inverted()).to_3x3()
        cameras = [('underside', (.08 * side, -.08, -1)), ('side', (side, -.14, -.05))]
        if (clip, time) in {('walk', 19), ('run', 4)}:
            cameras.append(('medial', (-side, -.14, -.05)))
        for view, vector in cameras:
            aim(camera, sole_center + Vector((0, 0, .001)), motion @ Vector(vector), .280)
            stem = f'{clip}_{time}_{view}'
            body.hide_render = True
            silhouette = render(scene, stem + '_silhouette', pixels=True)
            body.hide_render = False
            combined = render(scene, stem + '_skin', pixels=True)
            shoes.hide_render = True
            control = render(scene, stem + '_control', pixels=True)
            shoes.hide_render = False
            inside = filled_silhouette(silhouette[:, :, 3] >= .99)
            holes = inside & (silhouette[:, :, 3] == 0)
            sole = (silhouette[:, :, 2] > .02) | holes
            green = (combined[:, :, 1] > .025) & (combined[:, :, 3] > .02)
            # An overlying body contribution shows magenta on otherwise
            # blue soles, or fills an enclosed underside hole.
            magenta = (combined[:, :, 2] > .10) & (combined[:, :, 0] > .10)
            core_sole = ((silhouette[:, :, 2] > .98) & (silhouette[:, :, 0] < .02) &
                         (silhouette[:, :, 3] >= .99))
            row = {
                'lifted_side': 'Left' if side > 0 else 'Right',
                'frame': time,
                'body_plantar_z_range_m': [float(floor_range.min()), float(floor_range.max())],
                'plantar_pixels_through_or_around': int(green.sum()),
                'body_pixels_through_sole': int(((green & sole) | (magenta & (core_sole | holes))).sum()),
                'visible_plantar_pixels_inside_shoe_silhouette': int((green & inside).sum()),
                'plantar_control_pixels': int((control[:, :, 1] > .9).sum()),
                'camera_location': list(camera.location),
                'camera_rotation': list(camera.rotation_euler),
                'ortho_scale': camera.data.ortho_scale,
                'png_sha256': {kind: file_hash(OUTPUT / f'{stem}_{kind}.png')
                               for kind in ('silhouette', 'skin', 'control')},
            }
            print('SKIN', stem, {k: v for k, v in row.items() if 'pixels' in k}, flush=True)
            assert row['plantar_control_pixels'] > 500
            result[stem] = row
    passed = all(row['plantar_pixels_through_or_around'] == row['body_pixels_through_sole'] == 0
                 for row in result.values())
    write_json('skin_check.json', {'export_sha256': file_hash(EXPORT), 'views': result, 'passed': passed})
    return passed


def rest_geometry():
    scene, arm, body, shoes = on_master()
    set_pose(scene, arm, 'rest', 1)
    shoe_points, skin_points = evaluated_points(shoes), evaluated_points(body)
    tree = BVHTree.FromPolygons(skin_points.tolist(), topology(body).tolist(), all_triangles=True)
    signed = signed_hits(tree, shoe_points)[0]
    mesh = bmesh.new()
    mesh.from_mesh(shoes.data)
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=.000002)
    results = {}
    all_shoe_triangles = topology(shoes)
    for side, name in ((1, 'Left'), (-1, 'Right')):
        skin = skin_points[(skin_points[:, 0] * side > 0) & (skin_points[:, 2] < .073)]
        sole = shoe_points[(shoe_points[:, 0] * side > 0) & (shoe_points[:, 2] <= .013)]
        upper = signed[(shoe_points[:, 0] * side > 0) & (shoe_points[:, 2] >= .018)]
        flat = [Vector(point[:2]) for point in sole]
        hull = [flat[i] for i in geometry.convex_hull_2d(flat)]
        center = sum(hull, Vector((0, 0))) / len(hull)
        pad = math.inf
        for start, end in zip(hull, hull[1:] + hull[:1]):
            edge = end - start
            normal = Vector((edge.y, -edge.x)).normalized()
            if normal.dot(center - start) > 0:
                normal.negate()
            skin_support = (skin[:, :2] @ np.asarray(normal)).max()
            pad = min(pad, normal.dot(start) - skin_support)
        triangles = all_shoe_triangles[(shoe_points[all_shoe_triangles, 0] * side > 0).all(axis=1)]
        sole_surface = BVHTree.FromPolygons(shoe_points.tolist(), triangles.tolist(), all_triangles=True)
        center_2d = Vector((.000722 + side * .085205, .009))
        skin_flat = [Vector(point[:2]) for point in skin]
        skin_hull = [skin_flat[i] for i in geometry.convex_hull_2d(skin_flat)]
        pads = []
        for theta in np.linspace(0, math.tau, 361)[:-1]:
            direction = Vector((math.cos(theta), math.sin(theta)))
            caps = []
            for a, b in zip(skin_hull, skin_hull[1:] + skin_hull[:1]):
                edge = b - a
                normal = Vector((edge.y, -edge.x)).normalized()
                if normal.dot(center_2d - a) > 0:
                    normal.negate()
                if normal.dot(direction) > 1e-6:
                    caps.append(normal.dot(a - center_2d) / normal.dot(direction))
            skin_radius = min(caps)
            lo, hi = 0, .17
            for _ in range(18):
                midpoint = (lo + hi) / 2
                position = center_2d + midpoint * direction
                hit = sole_surface.ray_cast(Vector((*position, -.05)), (0, 0, 1), .067)[0]
                if hit is None:
                    hi = midpoint
                else:
                    lo = midpoint
            pads.append(lo - skin_radius)
        edges = [edge for edge in mesh.edges if all(v.co.x * side > 0 for v in edge.verts)]
        sole_edges = [edge for edge in edges if all(v.co.z <= .013 for v in edge.verts)]
        results[name] = {
            'body_plantar_min_z_m': float(skin[:, 2].min()),
            'body_foot_length_m': float(np.ptp(skin[:, 1])),
            'flat_tread_z_m': float(np.quantile(sole[:, 2], .10)),
            'minimum_tread_z_m': float(sole[:, 2].min()),
            'sole_length_m': float(np.ptp(sole[:, 1])),
            'min_projected_sole_hull_overhang_m': float(pad),
            'min_radial_projected_sole_overhang_m': float(min(pads)),
            'sole_boundary_edges_after_weld': sum(edge.is_boundary for edge in sole_edges),
            'sole_nonmanifold_edges_after_weld': sum(not edge.is_manifold for edge in sole_edges),
            'upper_boundary_edges_after_weld': sum(edge.is_boundary for edge in edges) -
                sum(edge.is_boundary for edge in sole_edges),
            'upper_vertex_clearance_quantiles_m': [float(q) for q in np.quantile(upper, [0, .1, .5, .9, 1])],
            'cuff_max_z_m': float(shoe_points[shoe_points[:, 0] * side > 0, 2].max()),
        }
    mesh.free()
    write_json('rest_geometry.json', {'export_sha256': file_hash(EXPORT), 'sides': results})
    print('GEOMETRY', json.dumps(results), flush=True)


def native_lining():
    bpy.ops.wm.open_mainfile(filepath=str(EXPORT.with_suffix('.blend')), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    body, shoes = (scene.objects[name] for name in ('Base_Body', 'shoes_boots_v1'))
    existing = set(scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE), merge_vertices=True)
    source, = (obj for obj in scene.objects if obj not in existing and obj.type == 'MESH')
    tree = BVHTree.FromPolygons([v.co for v in body.data.vertices], topology(body).tolist(),
                                all_triangles=True)
    points = np.array([tuple(v.co) for v in shoes.data.vertices])
    triangles = topology(shoes)
    signed = signed_hits(tree, points)[0]
    result, start = {}, 0
    for sign, side in ((1, 'Left'), (-1, 'Right')):
        bm, flags = source_boot(source, sign, Foot(body, sign))
        count = len(bm.verts)
        bm.free()
        ids = np.asarray(flags['lining']) + start
        bed = np.asarray(flags['footbed']) + start
        upper = ids[points[ids, 2] >= .018]
        inside = np.isin(triangles, ids).all(axis=1)
        same_shoe = ((triangles >= start) & (triangles < start + count)).all(axis=1)
        inner, outer = triangles[inside], triangles[~inside & same_shoe]
        inner_tree = BVHTree.FromPolygons(points.tolist(), inner.tolist(), all_triangles=True)
        outer_tree = BVHTree.FromPolygons(points.tolist(), outer.tolist(), all_triangles=True)
        pairs = [(a, b) for a, b in inner_tree.overlap(outer_tree)
                 if not set(inner[a]).intersection(outer[b])]
        heel = points[start:start + count]
        rear = heel[heel[:, 1] > .055]
        result[side] = {
            'lining_upper_clearance_quantiles_m': [float(q) for q in np.quantile(
                signed[upper], [0, .1, .5, .9, 1])],
            'footbed_z_range_m': [float(points[bed, 2].min()), float(points[bed, 2].max())],
            'rear_collar_z_m': float(rear[:, 2].max()),
            'rest_liner_outer_internal_pairs': len(pairs),
            'liner_outer_pair_centers_m': [points[inner[i]].mean(0).tolist() for i, _ in pairs],
        }
        start += count
    assert start == len(shoes.data.vertices)
    write_json('native_lining.json', {'export_sha256': file_hash(EXPORT), 'sides': result})
    print('LINING QA', json.dumps(result), flush=True)


def inverse_binds(document, blob):
    skin, = document['skins']
    accessor = document['accessors'][skin['inverseBindMatrices']]
    view = document['bufferViews'][accessor['bufferView']]
    offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    return blob[offset:offset + 64 * accessor['count']]


def inspect_glb():
    glb = EXPORT.read_bytes()
    magic, version, total, length = struct.unpack_from('<4sIII', glb)
    assert (magic, version, total) == (b'glTF', 2, len(glb))
    data = json.loads(glb[20:20 + length])
    blob = glb[28 + length:]
    access = data['accessors']
    primitives = data['meshes'][0]['primitives']
    skin, = data['skins']
    joints = [data['nodes'][index]['name'] for index in skin['joints']]
    base_glb = MASTER.with_name('base_body.glb').read_bytes()
    base_json_size, = struct.unpack_from('<I', base_glb, 12)
    base_document = json.loads(base_glb[20:20 + base_json_size])
    base_skin, = base_document['skins']
    base_joints = [base_document['nodes'][index]['name'] for index in base_skin['joints']]
    assert base_joints == joints
    assert inverse_binds(data, blob) == inverse_binds(base_document, base_glb[28 + base_json_size:])
    dimensions = []
    for item in data['images']:
        view = data['bufferViews'][item['bufferView']]
        offset = view.get('byteOffset', 0)
        assert blob[offset:offset + 8] == b'\x89PNG\r\n\x1a\n'
        dimensions.append(struct.unpack_from('>II', blob, offset + 16))
    triangles = 0
    max_influences = 0
    vertices = 0
    for primitive in primitives:
        attributes = primitive['attributes']
        assert 'WEIGHTS_1' not in attributes and 'TEXCOORD_0' in attributes
        triangles += access[primitive['indices']]['count'] // 3
        weights = access[attributes['WEIGHTS_0']]
        view = data['bufferViews'][weights['bufferView']]
        offset = view.get('byteOffset', 0) + weights.get('byteOffset', 0)
        assert weights['componentType'] == 5126
        positions = access[attributes['POSITION']]
        pos_view = data['bufferViews'][positions['bufferView']]
        pos_offset = pos_view.get('byteOffset', 0) + positions.get('byteOffset', 0)
        ids = access[attributes['JOINTS_0']]
        idx_view = data['bufferViews'][ids['bufferView']]
        idx_offset = idx_view.get('byteOffset', 0) + ids.get('byteOffset', 0)
        idx_type = 'B' if ids['componentType'] == 5121 else 'H'
        for i in range(weights['count']):
            values = struct.unpack_from('<4f', blob, offset + i * view.get('byteStride', 16))
            assert min(values) >= 0 and abs(sum(values) - 1) < 1e-5
            max_influences = max(max_influences, sum(value > 0 for value in values))
            x, y, z = struct.unpack_from('<3f', blob, pos_offset + i * pos_view.get('byteStride', 12))
            side = 'Left' if x > 0 else 'Right'
            id_values = struct.unpack_from('<4' + idx_type, blob, idx_offset +
                                           i * idx_view.get('byteStride', 4 * struct.calcsize(idx_type)))
            assert all(joints[idx].startswith(f'mixamorig:{side}')
                       for idx, value in zip(id_values, values) if value > 0)
        vertices += weights['count']
    assert len(joints) == 65 and len(data['meshes']) == 1
    assert not data.get('animations') and triangles <= 3500
    assert max(max(dim) for dim in dimensions) <= 1024
    _, master_arm, _ = master_scene()
    master_modes = {bone.name: bone.rotation_mode for bone in master_arm.pose.bones}
    bpy.ops.wm.open_mainfile(filepath=str(EXPORT.with_suffix('.blend')), load_ui=False, use_scripts=False)
    native = bpy.context.scene
    native_arm = native.objects['Armature']
    native_shoes = native.objects['shoes_boots_v1']
    assert len(native_arm.data.bones) == 65 and native_shoes.parent == native_arm
    assert len(native_shoes.modifiers) == 1 and native_shoes.modifiers[0].object == native_arm
    assert len(topology(native_shoes)) == triangles
    assert native.objects['Base_Body'].hide_render
    assert {bone.name: bone.rotation_mode for bone in native_arm.pose.bones} == master_modes
    assert all(node.image.packed_file for material in native_shoes.data.materials
               for node in material.node_tree.nodes if node.type == 'TEX_IMAGE')
    result = {
        'source_sha256': file_hash(SOURCE), 'export_sha256': file_hash(EXPORT),
        'master_sha256': file_hash(MASTER), 'motion_sha256': file_hash(MOTION),
        'reference_sha256': file_hash(HERE.parents[1] / 'white-bg/shoes-05-tan-lace-boots.png'),
        'glb_bytes': total, 'blend_bytes': EXPORT.with_suffix('.blend').stat().st_size,
        'blender_version': bpy.app.version_string, 'triangles': triangles, 'exported_vertices': vertices,
        'mesh_count': len(data['meshes']), 'animation_count': len(data.get('animations', [])),
        'native_rotation_modes_match_master': True, 'native_material_images_packed': True,
        'joint_count': len(joints), 'joint_names': joints, 'matches_base_inverse_binds': True,
        'max_influences': max_influences,
        'texture_dimensions': dimensions, 'preview_hashes': {
            path.name: file_hash(path) for path in sorted(OUTPUT.glob('boots_*.png'))
        }
    }
    write_json('asset_contract.json', result)
    print('EXPORT QA', {k: v for k, v in result.items() if k != 'joint_names'}, flush=True)


if __name__ == '__main__':
    stages = set(ARGS[2:]) or {'checkers', 'dense', 'geometry', 'lining', 'previews', 'skin', 'contract'}
    failed = []
    for name, function in (('checkers', supplied), ('dense', dense_scan), ('geometry', rest_geometry), ('lining', native_lining),
                           ('previews', previews), ('skin', skin_gate), ('contract', inspect_glb)):
        if name in stages and function() is False:
            failed.append(name)
    if failed:
        raise RuntimeError('Failed gates: ' + ', '.join(failed))
