"""Retopologize the v11 service desk and render the reimported export."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build

import bmesh
import bpy
import numpy as np


PROP = next(prop for prop in build.PROPS if prop.suffix == 'desk_service')
OAK, GREEN, BRASS, CREAM = range(len(PROP.colors))


def contour(radius, front, tip_x, tip_y, arc_steps=24, arm_steps=4):
    """Follow the source's half-ellipse and two tangent, tapered return arms."""
    center_y = .040
    angles = np.linspace(-math.pi / 2, math.pi / 2, arc_steps + 1)
    arc = np.column_stack((radius * np.sin(angles), center_y - (center_y - front) * np.cos(angles)))
    controls = np.array([
        (radius, center_y), (radius, center_y + .105),
        (tip_x + .037, tip_y - .073), (tip_x, tip_y),
    ])
    t = np.linspace(0, 1, arm_steps + 1)[1:, None]
    arm = ((1 - t)**3 * controls[0] + 3 * (1 - t)**2 * t * controls[1]
           + 3 * (1 - t) * t**2 * controls[2] + t**3 * controls[3])
    return np.concatenate((arm[::-1] * (-1, 1), arc, arm))


def slatted_contour():
    # The source albedo and normal map carry the narrow slots. Cut a shallow
    # channel between each pair of oak faces so the spacing survives without maps.
    rail = contour(.786, -.342, .641, .283, arc_steps=360, arm_steps=90)
    lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(rail, axis=0), axis=1))]
    tangents = np.gradient(rail, lengths, axis=0)
    groove = ((0, -.0055), (.075, -.0055), (.150, 0), (.925, 0))
    count = 48
    stations = [(slat + phase, depth) for slat in range(count) for phase, depth in groove]
    stations.append((count, 0))
    points = []
    for position, depth in stations:
        distance = lengths[-1] * position / count
        point = np.array([np.interp(distance, lengths, rail[:, axis]) for axis in range(2)])
        dx, dy = (np.interp(distance, lengths, tangents[:, axis]) for axis in range(2))
        points.append(point + depth * np.array((dy, -dx)) / math.hypot(dx, dy))
    # Plain cream end cheeks continue the returns behind the last slat.
    return np.array([(-.612, .350), *points, (.612, .350)])


def outline_inset(outline, distance):
    """Inset a counterclockwise outline, including its concave corners."""
    edges = np.roll(outline, -1, axis=0) - outline
    edges /= np.linalg.norm(edges, axis=1)[:, None]
    inward = np.column_stack((-edges[:, 1], edges[:, 0]))
    previous = np.roll(inward, 1, axis=0)
    return outline + (previous + inward) * (distance / (1 + (previous * inward).sum(axis=1)))[:, None]


def face(bm, verts, material, smooth=False):
    result = bm.faces.new(verts)
    result.material_index = material
    result.smooth = smooth


def ring(bm, outline, height):
    return [bm.verts.new((x, y, height)) for x, y in outline]


def connect(bm, lower, upper, materials, smooth):
    for i, material in enumerate(materials):
        j = (i + 1) % len(lower)
        face(bm, (lower[i], lower[j], upper[j], upper[i]), material, smooth[i])


def solid(bm, outline, low, high, sides, caps, smooth, bevel=0):
    if bevel:
        inset = outline_inset(outline, bevel)
        profiles = ((inset, low), (outline, low + bevel), (outline, high - bevel), (inset, high))
    else:
        profiles = ((outline, low), (outline, high))
    rings = [ring(bm, profile, height) for profile, height in profiles]
    for lower, upper in zip(rings, rings[1:]):
        connect(bm, lower, upper, sides, smooth)
    face(bm, rings[0][::-1], caps)
    face(bm, rings[-1], caps)


def plinth(bm):
    # The rear crosspiece ties the U-shaped wall together at floor level.
    outer = contour(.772, -.331, .599, .344, arc_steps=22)
    inner = contour(.617, -.280, .505, .248, arc_steps=22)
    foot = ring(bm, outer, 0)
    shoulder = ring(bm, outer, .122)
    rim = ring(bm, outline_inset(outer, .005), .131)
    inner_bottom = ring(bm, inner, 0)[::-1]
    inner_top = ring(bm, inner, .131)[::-1]
    materials = [BRASS] * len(outer)
    round_sides = [True] * len(outer)
    connect(bm, foot, shoulder, materials, round_sides)
    connect(bm, shoulder, rim, materials, round_sides)
    connect(bm, inner_bottom, inner_top, materials, round_sides)
    for i in range(len(outer)):
        j = (i + 1) % len(outer)
        face(bm, (foot[j], foot[i], inner_bottom[-1-i], inner_bottom[-1-j]), BRASS)
        face(bm, (rim[i], rim[j], inner_top[-1-j], inner_top[-1-i]), BRASS)


def desk_mesh():
    bm = bmesh.new()
    plinth(bm)
    outer = slatted_contour()
    inner = contour(.633, -.272, .454, .350)
    wall = np.concatenate((outer, inner[::-1]))
    sides = [CREAM] + [OAK] * (len(outer) - 3) + [CREAM] * (len(inner) + 2)
    smooth = [False] * len(outer) + [True] * (len(inner) - 1) + [False]
    solid(bm, wall, .128, .991, sides, OAK, smooth)
    top = np.concatenate((contour(.800, -.350, .635, .343), contour(.594, -.249, .470, .343)[::-1]))
    solid(bm, top, .984, 1.050, [GREEN] * len(top), GREEN, [True] * len(top), bevel=.005)
    panel = np.array([(-.522, .251), (.522, .251), (.480, .347), (-.480, .347)])
    worktop = np.array([(-.529, .242), (.529, .242), (.483, .348), (-.483, .348)])
    solid(bm, panel, .128, .711, [CREAM] * 4, CREAM, [False] * 4, bevel=.003)
    solid(bm, worktop, .709, .735, [CREAM] * 4, CREAM, [False] * 4, bevel=.004)
    build.normalize(bm, PROP)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    return bm


def export(root):
    source = build.RAW / f'{PROP.stem}.glb'
    source_blob, document = build.read_glb(source)
    if document.get('skins') or document.get('animations'):
        raise ValueError(f'{source.name} must be a static mesh')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source), merge_vertices=True)
    original, = (obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
    raw = bmesh.new()
    raw.from_mesh(original.data)
    raw.transform(original.matrix_world)
    low, high = build.extents(raw.verts)
    build.clean(raw, float(max(high - low)) * .000015)
    source_topology = build.topology(raw)
    raw.free()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bm = desk_mesh()
    topology = build.topology(bm)
    if any(topology.values()) or len(bm.faces) > PROP.cap:
        raise ValueError(f'{PROP.asset_id} has {len(bm.faces)} triangles and topology {topology}')
    mesh = bpy.data.meshes.new(PROP.asset_id)
    for key in PROP.colors:
        mesh.materials.append(build.flat_material(key))
    bm.to_mesh(mesh)
    bm.free()
    if mesh.validate():
        raise ValueError(f'{PROP.asset_id} required unexpected mesh repairs')
    mesh.set_sharp_from_angle(angle=math.radians(36))
    obj = bpy.data.objects.new(PROP.asset_id, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj['asset_id'] = PROP.asset_id

    target = root / f'{PROP.asset_id}.glb'
    bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', export_yup=True, export_extras=True,
                              use_selection=True, export_texcoords=False, export_materials='EXPORT',
                              export_animations=False, export_skins=False, export_morph=False, export_image_format='NONE')
    blob, document = build.read_glb(target)
    primitives = document['meshes'][0]['primitives']
    accessors = document['accessors']
    positions = [accessors[p['attributes']['POSITION']] for p in primitives]
    return {
        'id': PROP.asset_id,
        'file': target.name,
        'tris': sum(accessors[p['indices']]['count'] // 3 for p in primitives),
        'bytes': len(blob),
        'sha256': hashlib.sha256(blob).hexdigest(),
        'dimensions_m': list(PROP.size),
        'bounds_min': np.round(np.min([p['min'] for p in positions], axis=0), 8).tolist(),
        'bounds_max': np.round(np.max([p['max'] for p in positions], axis=0), 8).tolist(),
        'materials': [material['name'] for material in document['materials']],
        'source': f'../raw/{source.name}',
        'source_sha256': hashlib.sha256(source_blob).hexdigest(),
        'topology': {'source_after_weld': source_topology, 'export_mesh_before_material_split': topology},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-dir', type=Path, help='write only the desk and its previews to this directory')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    root = args.preview_dir.resolve() if args.preview_dir else build.ROOT
    if args.preview_dir:
        build.ROOT = build.RENDERS = root
    entry = export(root)
    # The shallow footprint needs a higher three-quarter view to show the rear worktop.
    build.VIEW_DIRECTIONS['three-quarter'] = (-.48, -1, .72)
    build.render_prop(PROP)
    files = [build.RENDERS / f'{PROP.asset_id}-{view}.png' for view in build.VIEW_DIRECTIONS]
    entry['renders'] = {f'renders/{file.name}': hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
    if args.preview_dir:
        (root / 'desk-entry.json').write_text(json.dumps(entry, indent=2) + '\n')
        return
    manifest = root / 'manifest.json'
    entries = {item['id']: item for item in json.loads(manifest.read_text())}
    entries[PROP.asset_id] = entry
    ordered = [entries[prop.asset_id] for prop in build.PROPS if prop.asset_id in entries]
    manifest.write_text(json.dumps(ordered, indent=2) + '\n')
    build.contact_sheet(entries)


if __name__ == '__main__':
    main()
