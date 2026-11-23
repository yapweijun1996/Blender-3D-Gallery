"""Build the topology and texture candidates for the NPC wardrobe."""
import json
from pathlib import Path
import struct
import sys

import bmesh
import bpy
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from decimate import Decimator, Face, topology

ROOT = HERE.parents[2]
SOURCE = ROOT / 'models/chibi-dressup/modules'
WORK = HERE / '.work'
LIMITS = {'hair-bob': 2400, 'hair-spiky': 2400, 'hair-sidepart': 2400,
          'shoes-sneakers': 1500, 'top-tshirt': 2600, 'bottom-jeans': 2600, 'top-dress': 3000}


def load_mesh(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = set(bpy.context.scene.objects) - before
    garment, = [o for o in objects if o.type == 'MESH' and o.vertex_groups]
    arm, = [o for o in objects if o.type == 'ARMATURE']
    return garment, arm


def read_mesh(garment, arm):
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    # glTF splits vertices at UV and normal discontinuities. BMesh welds positions
    # for topology while retaining the chart's coordinates on each corner.
    bmesh.ops.remove_doubles(mesh, verts=list(mesh.verts), dist=1e-7)
    mesh.verts.index_update()
    uv = mesh.loops.layers.uv.active
    color = mesh.loops.layers.color.active
    weights = np.zeros((len(mesh.verts), len(arm.data.bones)))
    names = tuple(bone.name for bone in arm.data.bones)
    index = [names.index(group.name) for group in garment.vertex_groups]
    layer = mesh.verts.layers.deform.active
    points = np.asarray([tuple(v.co) for v in mesh.verts])
    for v in mesh.verts:
        for group, value in v[layer].items():
            weights[v.index, index[group]] = value
    def corners(face):
        return Face(tuple(loop.vert.index for loop in face.loops), face.material_index,
                    tuple(tuple(round(c, 7) for c in loop[uv].uv) for loop in face.loops) if uv else (),
                    tuple(tuple(loop[color]) for loop in face.loops) if color else ())
    faces = [corners(f) for f in mesh.faces]
    mesh.free()
    return points, weights, faces, names


def limit_weights(weights):
    weights = weights.copy()
    order = np.argsort(-weights, axis=1, kind='stable')
    rows = np.arange(len(weights))[:, None]
    weights[rows, order[:, 4:]] = 0
    total = weights.sum(axis=1)
    if np.any(total <= 0):
        raise ValueError('Unweighted vertex')
    return weights / total[:, None]


def smooth_weights(points, weights, faces, name):
    if name not in {'top-tshirt', 'bottom-jeans', 'top-dress'}:
        return limit_weights(weights)
    jeans = name.startswith('bottom-')
    neighbors = [set() for _ in points]
    for face in faces:
        for v in face.vertices:
            neighbors[v].update(set(face.vertices)-{v})
    smooth = weights.copy()
    for v, ring in enumerate(neighbors):
        x, _, z = points[v]
        region = ((.20 < z < .35 or .41 < z < .59) if jeans else
                  ((.60 < z < .82 and abs(x) > .045) or (name == 'top-dress' and .42 < z < .62)))
        if region and ring:
            ids = sorted(ring)
            inverse = 1 / np.maximum(.003, np.linalg.norm(points[ids]-points[v], axis=1))
            mean = np.average(weights[ids], axis=0, weights=inverse)
            smooth[v] = weights[v]*.94 + mean*.06
    return limit_weights(smooth)


def write_weights(garment, weights, names):
    garment.vertex_groups.clear()
    groups = [garment.vertex_groups.new(name=name) for name in names]
    for v, b in zip(*np.nonzero(weights), strict=True):
        groups[b].add([int(v)], float(weights[v,b]), 'REPLACE')


def rebuild(garment, points, weights, faces, names):
    used = sorted({v for face in faces for v in face.vertices})
    index = {v: i for i, v in enumerate(used)}
    old = garment.data
    mesh = bpy.data.meshes.new(old.name + '_NPC')
    mesh.from_pydata(points[used].tolist(), [],
                     [tuple(index[v] for v in face.vertices) for face in faces])
    for material in old.materials:
        mesh.materials.append(material)
    uv_layer = mesh.uv_layers.new(name=old.uv_layers.active.name) if faces[0].uv else None
    color_layer = mesh.color_attributes.new(name='Color', type='BYTE_COLOR', domain='CORNER') if faces[0].color else None
    for p, face in zip(mesh.polygons, faces, strict=True):
        p.material_index = face.material
        p.use_smooth = True
        if uv_layer is not None:
            for i, value in zip(p.loop_indices, face.uv, strict=True):
                uv_layer.uv[i].vector = value
        if color_layer is not None:
            for i, value in zip(p.loop_indices, face.color, strict=True):
                color_layer.data[i].color_srgb = value
    garment.data = mesh
    write_weights(garment, weights[used], names)
    # Keep visual creases at the sneaker sole, lateral panels and piping.
    if garment.name == 'Sneaker_Pair':
        bm = bmesh.new()
        bm.from_mesh(mesh)
        for edge in bm.edges:
            if edge.is_manifold and edge.calc_face_angle() > .8:
                edge.smooth = False
        bm.to_mesh(mesh)
        bm.free()
    mesh.update()


def export_mesh(garment, arm, path, textured):
    bpy.ops.object.select_all(action='DESELECT')
    garment.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = garment
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_animations=False, export_skins=True, export_all_influences=False,
        export_image_format='NONE', export_texcoords=True, export_tangents=textured,
        export_vertex_color='NAME' if garment.data.color_attributes else 'NONE',
        export_vertex_color_name='Color', export_all_vertex_colors=False, export_yup=True)


def texture_inputs(path, dest):
    raw = path.read_bytes()
    size, = struct.unpack_from('<I', raw, 12)
    gltf = json.loads(raw[20:20+size])
    images = gltf.get('images', [])
    receipt = []
    scene = bpy.context.scene
    scene.render.image_settings.quality = 93
    for i, source in enumerate(images):
        image = bpy.data.images[source['name']]
        old = tuple(image.size)
        scale = min(1.0, 512 / max(old))
        target = tuple(round(n*scale) for n in old)
        image.scale(*target)
        # All resized source maps are opaque. Keep lossless data maps when their
        # combined size fits, with high-quality JPEG versions available for the budget.
        for fmt in ('PNG', 'JPEG'):
            image.file_format = fmt
            image.save(filepath=str(dest / f'image-{i}.{fmt.lower()}'), save_copy=True)
        receipt.append({'source': source['name'], 'before': old, 'after': target})
    return receipt


def build(name):
    source = SOURCE / (name + '.glb')
    dest = WORK / name
    dest.mkdir(parents=True, exist_ok=True)
    garment, arm = load_mesh(source)
    points, weights, faces, names = read_mesh(garment, arm)
    original = topology(faces)
    print('SOURCE', name, len(faces), original, flush=True)
    # Preserve the near-coincident toe and sole layers above the internal lining.
    priority = (2.5, 8.0, .20, .028, 2.5, 7.0) if name == 'shoes-sneakers' else None
    simplified = Decimator(points, weights, faces, .00085, priority).run(LIMITS[name])
    check = topology(simplified)
    assert original == check, (name, original, check)
    print('SIMPLIFIED', name, len(simplified), check, flush=True)
    rebuild(garment, points, smooth_weights(points, weights, simplified, name), simplified, names)
    export_mesh(garment, arm, dest/'decimated.glb', bool(faces[0].uv) and name != 'hair-bob')
    texture = texture_inputs(source, dest)
    (dest/'decimation.json').write_text(json.dumps(
        dict(source_triangles=len(faces), triangles=len(simplified), source_topology=original,
             npc_topology=check, textures=texture), indent=2)+'\n')


if __name__ == '__main__':
    for name in sys.argv[sys.argv.index('--')+1:]:
        build(name)
