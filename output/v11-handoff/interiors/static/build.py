"""Build the GJH v11 static furniture GLBs and preview the exported bytes."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import numpy as np


ROOT = Path(__file__).resolve().parent
RAW = ROOT.parent / 'raw'
REF = ROOT.parent.parent / 'ref'
RENDERS = ROOT / 'renders'


@dataclass(frozen=True)
class Prop:
    stem: str
    suffix: str
    size: tuple
    cap: int
    colors: tuple
    pivot: str = 'floor'

    @property
    def asset_id(self):
        return f'GJH_NEW_{self.suffix}'


PROPS = (
    Prop('bench-01-wood-bench', 'bench_oak', (1.40, .45, .42), 1200, ('oak', 'brass')),
    Prop('counter-01-shop-counter', 'counter_shop', (1.80, 1.05, .60), 1500, ('oak', 'green', 'brass')),
    Prop('decor-01-wall-art-frame', 'wall_art', (.90, .90, .05), 400, ('oak', 'green', 'ochre', 'cream'), 'wall'),
    Prop('desk-01-service-desk', 'desk_service', (1.60, 1.05, .70), 1800, ('oak', 'green', 'brass', 'cream')),
    Prop('lamp-01-pendant-lamp', 'lamp_pendant', (.38, .85, .38), 1200, ('green', 'brass', 'cream'), 'ceiling'),
    Prop('lamp-02-floor-lamp', 'lamp_floor', (.60, 1.70, .60), 1500, ('oak', 'brass', 'cream')),
    Prop('planter-01-round-planter', 'planter_round', (.75, 1.40, .75), 1800, ('green', 'brass', 'charcoal', 'leaf', 'leaf_dark')),
    Prop('rack-01-clothes-rack', 'rack_clothes', (1.20, 1.60, .45), 1200, ('oak', 'brass')),
    Prop('seating-01-round-ottoman', 'ottoman_round', (.70, .45, .70), 800, ('brass', 'cream')),
    Prop('shelf-01-display-shelf', 'shelf_display', (.90, 1.80, .35), 1500, ('oak', 'green', 'brass')),
    Prop('sign-01-directory-sign', 'sign_directory', (.75, 1.95, .25), 1400, ('green', 'brass', 'cream')),
    Prop('table-01-display-table', 'table_display', (1.10, .85, .60), 1000, ('oak', 'brass')),
)

# Hexadecimal sRGB values, converted to linear before GLB export.
PALETTE = {
    'oak': ('Honey oak', 'D49A61', .67, 0),
    'green': ('Matte dark green', '354B36', .72, 0),
    'brass': ('Brushed brass', 'CEA655', .35, .8),
    'cream': ('Warm cream', 'E4CEAA', .78, 0),
    'charcoal': ('Charcoal', '332D26', .85, 0),
    'leaf': ('Plant green', '47752D', .75, 0),
    'ochre': ('Ochre pigment', 'B78236', .78, 0),
    'leaf_dark': ('Deep plant green', '335421', .75, 0),
}


def srgb(rgb):
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def hex_rgb(value):
    return np.array(tuple(bytes.fromhex(value))) / 255


def oklab(rgb):
    lms = np.cbrt(srgb(rgb) @ np.array([
        [.41222147, .21190350, .08830246],
        [.53633254, .68069955, .28171884],
        [.05144599, .10739696, .62997870],
    ]))
    return lms @ np.array([
        [.21045426, 1.97799850, .02590404],
        [.79361779, -2.42859221, .78277177],
        [-.00407205, .45059371, -.80867577],
    ])


def read_glb(path):
    blob = path.read_bytes()
    magic, version, size, length, chunk_type = struct.unpack_from('<4sIII4s', blob)
    if (magic, version, size, chunk_type) != (b'glTF', 2, len(blob), b'JSON'):
        raise ValueError(f'Invalid GLB header: {path.name}')
    return blob, json.loads(blob[20:20 + length])


def mesh_components(bm):
    remaining = set(bm.verts)
    while remaining:
        first = remaining.pop()
        verts = [first]
        for v in verts:
            for edge in v.link_edges:
                other = edge.other_vert(v)
                if other in remaining:
                    remaining.remove(other)
                    verts.append(other)
        yield verts


def topology(bm):
    return {
        'boundary_edges': sum(e.is_boundary for e in bm.edges),
        'nonmanifold_edges': sum(not e.is_manifold and not e.is_boundary for e in bm.edges),
        'winding_edges': sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
    }


def remove_enclosed_shells(bm, epsilon):
    """Cull disconnected shells inside another closed shell, with no cuts to outer skins."""
    components = []
    for verts in mesh_components(bm):
        faces = set(face for v in verts for face in v.link_faces)
        coordinates = np.array([tuple(v.co) for v in verts])
        low, high = coordinates.min(axis=0), coordinates.max(axis=0)
        closed = all(e.is_manifold for face in faces for e in face.edges)
        components.append((verts, faces, low, high, closed))
    removed = []
    direction = Vector((.712, .407, .573)).normalized()
    for verts, faces, low, high, _ in components:
        samples = [v.co for v in verts] + [face.calc_center_median() for face in faces]
        for _, outer_faces, outer_low, outer_high, closed in components:
            if not closed or not (np.all(outer_low + epsilon < low) and np.all(high < outer_high - epsilon)):
                continue
            outer_verts = list(set(v for face in outer_faces for v in face.verts))
            lookup = {v: i for i, v in enumerate(outer_verts)}
            tree = BVHTree.FromPolygons([v.co for v in outer_verts],
                                       [[lookup[v] for v in face.verts] for face in outer_faces])
            if all((hit := tree.ray_cast(sample, direction))[0] is not None
                   and hit[1].dot(direction) > 0 and hit[3] > epsilon
                   for sample in samples):
                removed.extend(verts)
                break
    bmesh.ops.delete(bm, geom=removed, context='VERTS')
    return len(components), len(removed)


def clean(bm, epsilon):
    hidden = [f for f in bm.faces if f.hide]
    bmesh.ops.delete(bm, geom=hidden, context='FACES')
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=epsilon)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=epsilon)
    loose_edges = [e for e in bm.edges if not e.link_faces]
    bmesh.ops.delete(bm, geom=loose_edges, context='EDGES')
    loose_verts = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def face_colors(bm, scene_image):
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        raise ValueError('Source mesh has no albedo UV layer')
    uv = np.array([np.mean([tuple(loop[uv_layer].uv) for loop in face.loops], axis=0) for face in bm.faces])
    width, height = scene_image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    scene_image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)
    sample = uv * (width, height) - .5
    cell = np.floor(sample).astype(int)
    tx, ty = (sample - cell).T
    x, y = cell.T
    return (
        pixels[y % height, x % width, :3] * ((1 - tx) * (1 - ty))[:, None]
        + pixels[y % height, (x + 1) % width, :3] * (tx * (1 - ty))[:, None]
        + pixels[(y + 1) % height, x % width, :3] * ((1 - tx) * ty)[:, None]
        + pixels[(y + 1) % height, (x + 1) % width, :3] * (tx * ty)[:, None]
    )


def kmeans(colors, areas, count=6):
    samples = oklab(colors) * (1, 2, 2)
    rng = np.random.default_rng(11)
    best_loss = math.inf
    for _ in range(5):
        centers = [samples[rng.choice(len(samples), p=areas / areas.sum())]]
        for _ in range(1, count):
            errors = np.min(np.sum((samples[:, None, :] - np.array(centers)) ** 2, axis=2), axis=1)
            probability = areas * errors
            total = probability.sum()
            if total <= 1e-15:
                break
            centers.append(samples[rng.choice(len(samples), p=probability / total)])
        centers = np.array(centers)
        for _ in range(36):
            distances = np.sum((samples[:, None, :] - centers) ** 2, axis=2)
            labels = distances.argmin(axis=1)
            updated = centers.copy()
            for i in range(len(centers)):
                in_cluster = labels == i
                if in_cluster.any():
                    updated[i] = np.average(samples[in_cluster], axis=0, weights=areas[in_cluster])
            if np.allclose(updated, centers):
                break
            centers = updated
        loss = np.dot(areas, distances.min(axis=1))
        if loss < best_loss:
            best_loss, best_labels, best_centers = loss, labels, centers
    return best_labels, best_centers


def extents(vertices):
    points = np.array([tuple(v.co) for v in vertices])
    return points.min(axis=0), points.max(axis=0)


# Horizontal finish transitions measured against the raw mesh and its albedo.
FINISH_CUTS = {
    'bench_oak': (.818,),
    'counter_shop': (.109, .818, .872),
    'lamp_floor': (.050,),
    'planter_round': (.039,),
    'rack_clothes': (.073, .913),
    'ottoman_round': (.065,),
    'shelf_display': (.026, .0683, .2855, .5008, .7219, .9548),
    'table_display': (.234, .311, .896),
}


def cut_material_bands(prop, bm, epsilon):
    low, high = extents(bm.verts)
    for t in FINISH_CUTS.get(prop.suffix, ()):
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                              dist=epsilon * .1, plane_co=(0, 0, low[2] + t * (high[2] - low[2])),
                              plane_no=(0, 0, 1))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()


def snap_colors(prop, bm, samples):
    faces = list(bm.faces)
    areas = np.array([face.calc_area() for face in faces])
    low, high = extents(bm.verts)
    x, y, z = ((np.array([tuple(f.calc_center_median()) for f in faces]) - low) / (high - low)).T
    normal = np.array([tuple(f.normal) for f in faces])
    red, green, _ = samples.T
    labels, centers = kmeans(samples, areas)
    palette = oklab(np.array([hex_rgb(PALETTE[key][1]) for key in prop.colors])) * (1, 2, 2)
    mapping = np.sum((centers[:, None, :] - palette) ** 2, axis=2).argmin(axis=1)
    names = np.array(prop.colors)[mapping[labels]]

    # The source bakes shadows into oak and brass with overlapping RGB ranges.
    # Align ambiguous colors to the construction parts and actual finish borders.
    key = prop.suffix
    bands = FINISH_CUTS.get(key, ())
    if key == 'bench_oak':
        names[:] = np.where(z < bands[0], 'brass', 'oak')
    elif key == 'counter_shop':
        names[:] = np.select([z < bands[0], (z > bands[1]) & (z < bands[2])],
                             ['brass', 'green'], default='oak')
    elif key == 'wall_art':
        names[(normal[:, 1] > .5) | (x < .013) | (x > .987) | (z < .015) | (z > .985)] = 'oak'
    elif key == 'lamp_floor':
        shade = (x > .50) & (z > .605) & (z < .841)
        near_shade_center = (np.abs(x - .78) < .04) & (np.abs(y - .50) < .085)
        names[:] = np.select([z <= bands[0], shade & (~near_shade_center | (green > .61))],
                             ['oak', 'cream'], default='brass')
    elif key == 'planter_round':
        pot = z < .314
        soil = (z > .275) & (z < .306) & (normal[:, 2] > .36) & (
            ((x - .46) / .32) ** 2 + ((y - .51) / .30) ** 2 < .90)
        names[~pot & ~np.isin(names, ('leaf', 'leaf_dark'))] = 'leaf_dark'
        names[pot] = 'green'
        names[z < bands[0]] = 'brass'
        names[soil] = 'charcoal'
    elif key == 'rack_clothes':
        hanger = (x > .130) & (x < .878) & (z > .779) & (z < bands[1])
        names[:] = np.where((z < bands[0]) | hanger, 'oak', 'brass')
    elif key == 'ottoman_round':
        names[:] = np.where(z < bands[0], 'brass', 'cream')
    elif key == 'shelf_display':
        level = np.zeros(len(faces), dtype=bool)
        for start, finish in zip(bands[1:], (.091, .308, .524, .745, .978)):
            level |= (z >= start) & (z <= finish)
        post = ((x < .038) | (x > .962)) & ((y < .12) | (y > .88))
        names[:] = np.where(level & (~post | (np.abs(normal[:, 2]) > .82)), 'oak', 'green')
        names[z < bands[0]] = 'brass'
    elif key == 'sign_directory':
        names[(z < .096) | (x < .105) | (x > .935)] = 'brass'
        names[(names == 'green') & (red > green + .04)] = 'brass'
    elif key == 'table_display':
        names[:] = np.where(((z >= bands[0]) & (z < bands[1])) | (z >= bands[2]), 'oak', 'brass')

    used = [color for color in prop.colors if color in names]
    for face, name in zip(faces, names):
        face.material_index = used.index(name)
    remove_material_specks(bm)
    return used


def remove_material_specks(bm):
    fixes = {}
    for face in bm.faces:
        neighbours = {f for edge in face.edges for f in edge.link_faces if f != face}
        if len(neighbours) >= 3 and len({f.material_index for f in neighbours}) == 1:
            fixes[face] = next(iter(neighbours)).material_index
    for face, material_index in fixes.items():
        face.material_index = material_index


def flat_material(key):
    name, hex_value, roughness, metallic = PALETTE[key]
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*srgb(hex_rgb(hex_value)), 1)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = material.diffuse_color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return material


def repair_rack_hanger(bm):
    # The left original has multiple tears. Its intact centre twin supplies
    # the same hanger geometry, UVs and finish within the original envelope.
    low, high = extents(bm.verts)
    hangers = []
    for verts in mesh_components(bm):
        lower, upper = extents(verts)
        point_min, point_max = (lower - low) / (high - low), (upper - low) / (high - low)
        if point_min[2] > .77 and point_max[2] < .94 and point_max[0] - point_min[0] > .18:
            hangers.append((verts, lower, upper))
    if len(hangers) != 3:
        return
    left, middle, _ = sorted(hangers, key=lambda item: item[1][0])
    damaged, damaged_min, damaged_max = left
    intact, intact_min, intact_max = middle
    edges = {edge for vert in intact for edge in vert.link_edges}
    faces = {face for vert in intact for face in vert.link_faces}
    selection = sorted(intact, key=lambda vert: vert.index)
    selection += sorted(edges, key=lambda edge: edge.index)
    selection += sorted(faces, key=lambda face: face.index)
    copied = bmesh.ops.duplicate(bm, geom=selection)['geom']
    for element in copied:
        if isinstance(element, bmesh.types.BMVert):
            relative = (np.array(element.co) - intact_min) / (intact_max - intact_min)
            element.co = damaged_min + relative * (damaged_max - damaged_min)
    bmesh.ops.delete(bm, geom=damaged, context='VERTS')
    bm.normal_update()


def reduce_mesh(bm, prop, materials, epsilon):
    # Preserve seams between palette regions during planar simplification.
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(3), use_dissolve_boundaries=False,
                            verts=list(bm.verts), edges=list(bm.edges), delimit={'MATERIAL'})
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    mesh = bpy.data.meshes.new(prop.asset_id)
    for key in materials:
        mesh.materials.append(flat_material(key))
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new(prop.asset_id, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if len(mesh.polygons) > prop.cap:
        collapse = obj.modifiers.new('Triangle budget', 'DECIMATE')
        collapse.ratio = (prop.cap - 2) / len(mesh.polygons)
        collapse.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=collapse.name)
    bm.clear()
    bm.from_mesh(obj.data)
    clean(bm, epsilon)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    return obj


def normalize(bm, prop):
    low, high = extents(bm.verts)
    width, height, depth = prop.size
    if prop.suffix == 'lamp_floor':
        # The arc has radial parts. Orient its plan diagonally within the square
        # footprint rather than stretching the circular base and shade in depth.
        bm.transform(Matrix.Rotation(math.pi / 4, 4, 'Z'))
        low, high = extents(bm.verts)
    scale = np.array((width, depth, height)) / (high - low)
    anchor = (low + high) / 2
    if prop.pivot == 'wall':
        anchor[1] = high[1]
    elif prop.pivot == 'ceiling':
        top = np.array([tuple(v.co) for v in bm.verts if v.co.z >= high[2] - .015 * (high[2] - low[2])])
        anchor[:2] = ((top.min(axis=0) + top.max(axis=0)) / 2)[:2]
        anchor[2] = high[2]
    else:
        anchor[2] = low[2]
    for vert in bm.verts:
        result = (np.array(vert.co) - anchor) * scale
        if prop.pivot == 'ceiling':
            # Keep the diffuser round and allocate the extra requested height
            # to the suspension cable, above the brass collar.
            level = (vert.co.z - low[2]) / (high[2] - low[2])
            collar = .815
            diffuser_scale = (width + depth) / (2 * (high[:2] - low[:2]).mean())
            collar_height = collar * (high[2] - low[2]) * diffuser_scale
            if level <= collar:
                result[2] = level / collar * collar_height - height
            else:
                result[2] = (level - 1) / (1 - collar) * (height - collar_height)
        vert.co = result


def convert(prop):
    source = RAW / f'{prop.stem}.glb'
    blob, document = read_glb(source)
    if document.get('skins') or document.get('animations'):
        raise ValueError(f'{source.name} contains a rig or animation. Supply the static furniture source.')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    regenerated_normals = ('sign_directory', 'lamp_floor', 'planter_round', 'rack_clothes')
    import_shading = 'SMOOTH' if prop.suffix in regenerated_normals else 'NORMALS'
    bpy.ops.import_scene.gltf(filepath=str(source), merge_vertices=True, import_shading=import_shading)
    sources = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.visible_get()]
    if len(sources) != 1:
        raise ValueError(f'{source.name}: expected one visible source mesh')
    src = sources[0]
    mesh = src.data
    bsdf = next(n for n in mesh.materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    image_node = bsdf.inputs['Base Color'].links[0].from_node
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.transform(src.matrix_world)
    low, high = extents(bm.verts)
    epsilon = float(max(high - low)) * 0.000015
    clean(bm, epsilon)
    components, removed = remove_enclosed_shells(bm, epsilon)
    before = topology(bm)
    print('SOURCE', prop.suffix, components, removed, before, flush=True)
    if prop.suffix == 'rack_clothes' and before['nonmanifold_edges']:
        bm.verts.index_update()
        bm.edges.index_update()
        bm.faces.index_update()
        repair_rack_hanger(bm)
    cut_material_bands(prop, bm, epsilon)
    materials = snap_colors(prop, bm, face_colors(bm, image_node.image))
    for old in list(bpy.context.scene.objects):
        bpy.data.objects.remove(old, do_unlink=True)
    obj = reduce_mesh(bm, prop, materials, epsilon)
    remove_material_specks(bm)
    after = topology(bm)
    if all(count == 0 for count in before.values()) and any(after.values()):
        raise ValueError(f'{prop.asset_id}: simplification opened a closed source mesh: {after}')
    print('RESULT', prop.suffix, len(bm.faces), after, flush=True)
    if prop.suffix == 'wall_art':
        # Tone down the source painting's shallow relief without merging
        # vertices that project to the same point in the front view.
        low, high = extents(bm.verts)
        for vert in bm.verts:
            x, y, z = (np.array(vert.co) - low) / (high - low)
            if .019 < x < .981 and .019 < z < .981 and .025 < y < .42:
                vert.co.y = low[1] + (.12 + y * .23) * (high[1] - low[1])
    normalize(bm, prop)
    for face in bm.faces:
        if prop.suffix == 'wall_art':
            face.smooth = materials[face.material_index] == 'oak'
        elif prop.suffix == 'sign_directory':
            # The flat sign inserts must not pick up shading normals from
            # the adjacent rolled brass edges.
            face.smooth = materials[face.material_index] == 'brass'
        else:
            face.smooth = True
    bm.normal_update()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.validate(verbose=True, clean_customdata=False)
    obj.data.update()
    crease_angle = 64 if prop.suffix == 'planter_round' else 36
    obj.data.set_sharp_from_angle(angle=math.radians(crease_angle))
    if prop.suffix in ('sign_directory', 'lamp_floor'):
        normals = obj.modifiers.new('Weighted surface normals', 'WEIGHTED_NORMAL')
        normals.keep_sharp = True
        bpy.ops.object.modifier_apply(modifier=normals.name)
    if len(obj.data.polygons) > prop.cap:
        raise ValueError(f'{prop.asset_id}: exceeded {prop.cap} triangles')
    obj['asset_id'] = prop.asset_id
    verified = bmesh.new()
    verified.from_mesh(obj.data)
    after = topology(verified)
    verified.free()
    if all(count == 0 for count in before.values()) and any(after.values()):
        raise ValueError(f'{prop.asset_id}: final mesh lost its closed surface: {after}')
    path = ROOT / f'{prop.asset_id}.glb'
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', export_yup=True,
                              export_extras=True, use_selection=True, export_texcoords=False,
                              export_materials='EXPORT', export_animations=False, export_skins=False,
                              export_morph=False, export_image_format='NONE', export_apply=False)
    data, output = read_glb(path)
    positions = [output['accessors'][p['attributes']['POSITION']]
                 for m in output['meshes'] for p in m['primitives']]
    min_bound = np.min([p['min'] for p in positions], axis=0)
    max_bound = np.max([p['max'] for p in positions], axis=0)
    tris = sum(output['accessors'][p['indices']]['count'] // 3
               for m in output['meshes'] for p in m['primitives'])
    return {
        'id': prop.asset_id,
        'file': path.name,
        'tris': tris,
        'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'dimensions_m': list(prop.size),
        'bounds_min': np.round(min_bound, 8).tolist(),
        'bounds_max': np.round(max_bound, 8).tolist(),
        'materials': [material['name'] for material in output['materials']],
        'source': f'../raw/{source.name}',
        'source_sha256': hashlib.sha256(blob).hexdigest(),
        'topology': {'source_after_weld': before, 'export_mesh_before_material_split': after},
    }


def aim(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()


def add_area(scene, name, center, scale, offset, energy, width):
    light = bpy.data.lights.new(name, 'AREA')
    light.shape = 'DISK'
    light.energy = energy * scale**2
    light.size = width * scale
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.location = center + scale * Vector(offset)
    aim(obj, center)


VIEW_DIRECTIONS = {
    'front': (0, -1, 0),
    'three-quarter': (-.58, -1, .40),
    'side': (1, 0, 0),
}


def render_prop(prop):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / f'{prop.asset_id}.glb'))
    scene = bpy.context.scene
    coords = np.array([tuple(o.matrix_world @ v.co) for o in scene.objects if o.type == 'MESH'
                       for v in o.data.vertices])
    center = Vector((coords.min(axis=0) + coords.max(axis=0)) / 2)
    scale = max(prop.size)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 6
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.exposure = -.65
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.world = bpy.data.worlds.new('Neutral studio')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.45, .45, .45, 1)
    background.inputs['Strength'].default_value = .63
    add_area(scene, 'Key', center, scale, (-1.5, -2.5, 3), 250, 4)
    add_area(scene, 'Fill', center, scale, (2.5, -1.5, .6), 125, 3)
    add_area(scene, 'Rim', center, scale, (1.2, 2.4, 2.0), 165, 3)
    camera = bpy.data.objects.new('Inspection camera', bpy.data.cameras.new('Orthographic'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    for view, direction in VIEW_DIRECTIONS.items():
        if prop.suffix == 'lamp_floor' and view == 'three-quarter':
            direction = (.58, -1, .40)
        camera.location = center + Vector(direction).normalized() * scale * 4
        aim(camera, center)
        rotation = camera.rotation_euler.to_matrix()
        view_coords = coords @ np.array(rotation)
        mid = (view_coords.min(axis=0) + view_coords.max(axis=0)) / 2
        for axis in (0, 1):
            vector = rotation.col[axis]
            camera.location += vector * (mid[axis] - camera.location.dot(vector))
        camera.data.ortho_scale = 1.17 * max(np.ptp(view_coords, axis=0)[:2])
        scene.render.filepath = str(RENDERS / f'{prop.asset_id}-{view}.png')
        bpy.ops.render.render(write_still=True)


def pixels_from_png(path, target_size=None):
    photo = bpy.data.images.load(str(path))
    width, height = photo.size
    if target_size and max(width, height) != target_size:
        ratio = target_size / max(width, height)
        width, height = round(width * ratio), round(height * ratio)
        photo.scale(width, height)
    pixels = np.empty(width * height * 4, dtype=np.float32)
    photo.pixels.foreach_get(pixels)
    bpy.data.images.remove(photo)
    return pixels.reshape(height, width, 4)


def sheet_labels(width, height, labels):
    """Rasterize the contact sheet captions with Blender's built-in font."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 3
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 6
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'Standard'
    camera = bpy.data.objects.new('Sheet camera', bpy.data.cameras.new('Sheet camera'))
    scene.collection.objects.link(camera)
    camera.location = (0, 0, 50)
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(width, height) / 100
    scene.camera = camera
    ink = bpy.data.materials.new('Forest ink')
    ink.use_nodes = True
    nodes = ink.node_tree.nodes
    nodes.clear()
    emission = nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = (*srgb(hex_rgb('263A30')), 1)
    ink.node_tree.links.new(emission.outputs[0], nodes.new('ShaderNodeOutputMaterial').inputs[0])
    for value, left, top, size in labels:
        curve = bpy.data.curves.new(value, type='FONT')
        curve.body = value
        curve.size = size / 100
        curve.materials.append(ink)
        obj = bpy.data.objects.new(value, curve)
        scene.collection.objects.link(obj)
        obj.location = ((left - width / 2) / 100, (height / 2 - top) / 100, 0)
    temp = ROOT / '.sheet-labels.png'
    scene.render.filepath = str(temp)
    try:
        bpy.ops.render.render(write_still=True)
        return pixels_from_png(temp)
    finally:
        temp.unlink(missing_ok=True)


def contact_sheet(entries):
    tile, gap, margin = 272, 12, 26
    row_height, header = tile + 50, 116
    width = margin * 2 + tile * 4 + gap * 3
    height = header + row_height * len(PROPS) + margin
    canvas = np.empty((height, width, 4), np.float32)
    canvas[:] = (*hex_rgb('EFF1EC'), 1)
    labels = [('GJH Virtual Mall', margin, 48, 33), ('V11 interior props', width - 244, 48, 22)]
    for col, name in enumerate(('Tripo reference', 'Front', 'Three-quarter', 'Side')):
        labels.append((name, margin + col * (tile + gap), 100, 18))
    for row, prop in enumerate(PROPS):
        entry = entries.get(prop.asset_id)
        title = ' '.join(prop.stem.split('-')[2:]).title()
        if not entry:
            title += '  |  Source mesh pending'
        top = header + row * row_height
        labels.append((title, margin + 8, top + 26, 20))
        if entry:
            details = f"{entry['tris']:,} tris  /  {entry['bytes']:,} bytes"
            labels.append((details, width - margin - 220, top + 26, 16))
        paths = [REF / f'{prop.stem}.png']
        paths += [RENDERS / f'{prop.asset_id}-{view}.png' for view in VIEW_DIRECTIONS]
        for col, path in enumerate(paths):
            left = margin + col * (tile + gap)
            bottom = height - top - 38 - tile
            canvas[bottom:bottom + tile, left:left + tile, :3] = 1
            if not path.exists() or (col and (not entry or 'renders' not in entry)):
                continue
            photo = pixels_from_png(path, tile - 10)
            photo_height, photo_width = photo.shape[:2]
            x, y = left + (tile - photo_width) // 2, bottom + (tile - photo_height) // 2
            canvas[y:y + photo_height, x:x + photo_width, :3] = (
                photo[:, :, :3] * photo[:, :, 3:4] + 1 - photo[:, :, 3:4])
    overlay = sheet_labels(width, height, labels)
    alpha = overlay[:, :, 3:4]
    canvas[:, :, :3] = canvas[:, :, :3] * (1 - alpha) + overlay[:, :, :3] * alpha
    image = bpy.data.images.new('V11 contact sheet', width=width, height=height, alpha=False)
    image.pixels.foreach_set(canvas.ravel())
    image.filepath_raw = str(ROOT / 'contact_sheet.png')
    image.file_format = 'PNG'
    image.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', nargs='+', choices=[p.suffix for p in PROPS])
    parser.add_argument('--geometry-only', action='store_true')
    parser.add_argument('--sheet-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    selected = [p for p in PROPS if args.assets is None or p.suffix in args.assets]
    manifest = ROOT / 'manifest.json'
    entries = {entry['id']: entry for entry in json.loads(manifest.read_text())} if manifest.exists() else {}
    if args.sheet_only:
        contact_sheet(entries)
        return
    RENDERS.mkdir(exist_ok=True)
    for prop in selected:
        entries[prop.asset_id] = convert(prop)
        if not args.geometry_only:
            render_prop(prop)
            files = [RENDERS / f'{prop.asset_id}-{view}.png' for view in VIEW_DIRECTIONS]
            entries[prop.asset_id]['renders'] = {
                f'renders/{path.name}': hashlib.sha256(path.read_bytes()).hexdigest() for path in files
            }
    ordered = [entries[prop.asset_id] for prop in PROPS if prop.asset_id in entries]
    manifest.write_text(json.dumps(ordered, indent=2) + '\n')
    if not args.geometry_only:
        contact_sheet(entries)


if __name__ == '__main__':
    main()
