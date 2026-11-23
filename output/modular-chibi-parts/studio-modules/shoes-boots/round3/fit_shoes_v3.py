"""Rebuild the v2 outsole surfaces and keep the master's skin and texture roles."""
from collections import deque
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'round2'))
from fit_shoes_v2 import V2, digest, master_scene, mount, write_report
from fit_shoes import export_glb

TARGET = HERE / 'shoes_boots_v3'
SOURCE_SHA256 = 'bcc5cc2e061ee5077e0dcdb2f79b260ebf2dd2b0bc60ef07694f035f9d88a2b2'
CUT_Z = -.0115
TREAD_Z = -.0155
WELD_M = .000001
SIZE = 1024
ORIGINAL_SIZE = 768
PADDING = 12
PIXELS_PER_METRE = 1350
EXCESS_TRIS = (912, 1623, 1780, 2269, 2449, 2573, 2619)
TOE_BRIDGE_TRIS = (86, 495, 496, 1071, 1072, 1109, 1110, 1694)


def boundary_rings(edges):
    remaining = set(edges)
    adjacent = {}
    for edge in remaining:
        for vertex in edge.verts:
            adjacent.setdefault(vertex, []).append(edge)
    assert all(len(incident) == 2 for incident in adjacent.values())
    while remaining:
        edge = min(remaining, key=lambda e: tuple(sorted(v.index for v in e.verts)))
        remaining.remove(edge)
        start, vertex = sorted(edge.verts, key=lambda v: v.index)
        ring = [start]
        while vertex != start:
            ring.append(vertex)
            edge = next(e for e in adjacent[vertex] if e != edge)
            remaining.remove(edge)
            vertex = edge.other_vert(vertex)
        yield ring


def count_edges(bm):
    main = []
    for sign in (-1, 1):
        edges = [e for e in bm.edges if sign * e.verts[0].co.x > 0]
        main.append(dict(side='positive_X' if sign > 0 else 'negative_X',
                         boundary=sum(e.is_boundary for e in edges),
                         sole_zone_boundary=sum(e.is_boundary and min(v.co.z for v in e.verts) < .015
                                                for e in edges),
                         overfull=sum(len(e.link_faces) > 2 for e in edges),
                         wire=sum(e.is_wire for e in edges)))
    return main


def face_component(seed, candidates):
    component, queue = {seed}, deque([seed])
    while queue:
        for edge in queue.popleft().edges:
            for face in edge.link_faces:
                if face in candidates and face not in component:
                    component.add(face)
                    queue.append(face)
    return component


def close_accessory_rims(bm, uv):
    # These source triangles are extra sheets joined to edges already used twice.
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in EXCESS_TRIS], context='FACES')
    bm.verts.index_update()
    rings = list(boundary_rings(e for e in bm.edges if e.is_boundary))
    assert sorted(map(len, rings)) == [4, 6, 8, 8, 8, 8]
    for ring in rings:
        # Sample a compact patch from the adjoining metal or leather island.
        faces = {f for v in ring for f in v.link_faces}
        sample = max(faces, key=lambda f: (f.calc_area(), -f.index))
        tex = [l[uv].uv.copy() for l in sample.loops]
        center = sum(tex, Vector((0, 0))) / 3
        normal = geometry.normal([v.co for v in ring])
        up = normal.orthogonal().normalized()
        across = normal.cross(up)
        span = max((v.co-ring[0].co).length for v in ring)
        radius = .25 * min((tex[i] - center).length for i in range(3))
        midpoint = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
        deform = bm.verts.layers.deform.active
        nearest = min(ring, key=lambda v: (v.co - midpoint.co).length_squared)
        for group, weight in nearest[deform].items():
            midpoint[deform][group] = weight
        for a, b in zip(ring, ring[1:] + ring[:1]):
            face = bm.faces.new((a, b, midpoint))
            for loop in face.loops:
                p = (loop.vert.co - midpoint.co) / span
                loop[uv].uv = center + max(radius, .00002) * Vector((p.dot(up), p.dot(across)))
    return [len(ring) for ring in rings]


def inset_toe_welt(bm):
    # Bring the recessed toe bridge forward across the whole exposed edge.
    # Move shared rim vertices together so the skinned leather and welt stay joined.
    moves = [
        ((.04624, -.12624, .00745), (.04570, -.12965)),
        ((.07254, -.12292, .00907), (.07190, -.12800)),
        ((.10732, -.12117, .01006), (.10750, -.12698)),
        ((.10731, -.12189, .01128), (.10745, -.12675)),
        ((.13754, -.10980, .00910), (.13965, -.11190)),
        ((.13814, -.11034, .01010), (.13860, -.11170)),
        ((.15069, -.09762, .00810), (.15140, -.09860)),
    ]
    for location, xy in moves:
        point = Vector(location)
        vertex = min(bm.verts, key=lambda v: (v.co-point).length_squared)
        assert (vertex.co-point).length < .000012
        vertex.co.xy = xy
    return len(moves)


def sole_tiles(bm, uv):
    cut = bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                                dist=1e-7, plane_co=(0, 0, CUT_Z), plane_no=(0, 0, 1))
    boundary = {e for e in cut['geom_cut'] if isinstance(e, bmesh.types.BMEdge)}
    bm.verts.index_update()
    deform = bm.verts.layers.deform.active
    result = []
    for index, sign in enumerate((-1, 1)):
        eligible = {f for f in bm.faces if f.calc_center_median().z < CUT_Z - 1e-7 and
                    f.calc_center_median().x * sign > 0}
        patch = face_component(min(eligible, key=lambda f: (f.calc_center_median().z, f.index)), eligible)
        rim, = boundary_rings({e for f in patch for e in f.edges if e in boundary and
                               any(g not in patch for g in e.link_faces)})
        assert len(patch) > 350 and 65 <= len(rim) <= 80
        bmesh.ops.delete(bm, geom=list(patch), context='FACES')
        # The source liner has a few downward spikes that extend through the
        # cut plane. Tuck them above the new tread while retaining their skin.
        liner = {v for f in eligible - patch for v in f.verts if v.co.z < CUT_Z - 1e-6}
        for vertex in liner:
            vertex.co.z = CUT_Z + .25 * (vertex.co.z - CUT_Z)
        outline = np.array([v.co.xy[:] for v in rim])
        origin = np.array([outline[:, 0].min(), outline[:, 1].max()])
        tile_offset = np.array([796, 20 + index * 320])
        tile_dimensions = np.ceil((outline.max(0) - outline.min(0)) * PIXELS_PER_METRE).astype(int)
        assert tile_offset[0] + tile_dimensions[0] + PADDING < SIZE
        assert tile_dimensions[1] + 2 * PADDING < 320
        center = np.mean(outline, axis=0)
        base = []
        for vertex in rim:
            xy = np.array(vertex.co.xy[:])
            inward = (center - xy) / np.linalg.norm(center - xy)
            lower = bm.verts.new((*(xy + .00065 * inward), TREAD_Z))
            for group, weight in vertex[deform].items():
                lower[deform][group] = weight
            base.append(lower)

        def set_uv(face):
            for loop in face.loops:
                st = (np.array(loop.vert.co.xy[:]) - origin) * (1, -1)
                loop[uv].uv = (tile_offset + PIXELS_PER_METRE * st) / SIZE

        for i in range(len(rim)):
            j = (i + 1) % len(rim)
            set_uv(bm.faces.new((rim[i], rim[j], base[j], base[i])))
        flat = [v.co.xy.copy() for v in base]
        outline_ids = list(range(len(base)))
        # Keep skinning samples under the ball and heel so the cap bends with the
        # welt. Interior samples interpolate the two nearest perimeter weights.
        interior = []
        for y in np.arange(outline[:, 1].min() + .020, outline[:, 1].max() - .015, .021):
            for x in np.linspace(outline[:, 0].min() + .040, outline[:, 0].max() - .040, 3):
                interior.append(Vector((x, y)))
        points, _, triangles, sources, _, _ = geometry.delaunay_2d_cdt(
            flat + interior, [], [outline_ids], 1, 1e-8)
        mapped = []
        for point, ids in zip(points, sources):
            assert ids, 'The cut ring must remain a simple polygon'
            if ids[0] < len(base):
                mapped.append(base[ids[0]])
                continue
            new = bm.verts.new((*point, TREAD_Z))
            closest = sorted(base, key=lambda v: (v.co.xy-point).length_squared)[:2]
            factors = np.array([1 / max((v.co.xy-point).length, 1e-6) for v in closest])
            weights = {}
            for v, factor in zip(closest, factors / factors.sum()):
                for group, weight in v[deform].items():
                    weights[group] = weights.get(group, 0) + float(weight * factor)
            for group, weight in weights.items():
                new[deform][group] = weight
            mapped.append(new)
        for indexes in triangles:
            set_uv(bm.faces.new([mapped[i] for i in indexes]))
        for a, b in zip(base, base[1:] + base[:1]):
            bm.edges.get((a, b)).smooth = False
        result.append(dict(origin=origin, offset=tile_offset, dimensions=tile_dimensions,
                           removed_faces=len(patch), rim_vertices=len(rim), new_cap_faces=len(triangles),
                           tucked_liner_vertices=len(liner)))
    return result


def raster(triangle, width, height, margin=0):
    low = np.maximum(np.floor(triangle.min(0) - margin).astype(int), 0)
    high = np.minimum(np.ceil(triangle.max(0) + margin).astype(int), (width, height))
    if np.any(low >= high):
        return None
    p, q, r = triangle
    matrix = np.column_stack((q-p, r-p))
    if abs(np.linalg.det(matrix)) < 1e-10:
        return None
    y, x = np.mgrid[low[1]:high[1], low[0]:high[0]]
    st = np.stack((x + .5 - p[0], y + .5 - p[1]), axis=-1) @ np.linalg.inv(matrix).T
    weights = np.concatenate((1-st.sum(axis=-1, keepdims=True), st), axis=-1)
    return y, x, weights


def pixels(image):
    data = np.empty(len(image.pixels), np.float32)
    image.pixels.foreach_get(data)
    return data.reshape(image.size[1], image.size[0], 4)


def bilinear(image, coords):
    h, w = image.shape[:2]
    xy = np.clip(coords * (w, h) - .5, (0, 0), (w-1, h-1))
    uv = np.floor(xy).astype(int)
    x, y = uv.T
    dx, dy = (xy - uv).T[:, :, None]
    xp, yp = np.minimum(x+1, w-1), np.minimum(y+1, h-1)
    return ((image[y, x]*(1-dx) + image[y, xp]*dx)*(1-dy) +
            (image[yp, x]*(1-dx) + image[yp, xp]*dx)*dy)


def source_tread(mesh):
    verts = np.array([v.co[:] for v in mesh.vertices])
    tex = np.array([uv.uv[:] for uv in mesh.uv_layers.active.data])
    mesh.calc_loop_triangles()
    return [(verts[list(t.vertices)], tex[list(t.loops)]) for t in mesh.loop_triangles
            if t.normal.z < -.18 and max(verts[list(t.vertices), 2]) < .006]


def bake_tread(source, maps, tile):
    """Reproject the outside tread onto the new continuous sole, with its UV tangent basis."""
    width, height = tile['dimensions'] + 2 * PADDING
    depth = np.full((height, width), np.inf)
    uv = np.zeros((height, width, 2), dtype=np.float32)
    tangent = np.zeros((height, width, 2), dtype=np.float32)
    sign = np.zeros((height, width), dtype=np.float32)
    for xyz, texture in source:
        st = PADDING + PIXELS_PER_METRE * (xyz[:, :2] - tile['origin']) * (1, -1)
        region = raster(st, width, height)
        if region is None:
            continue
        y, x, weights = region
        z = weights @ xyz[:, 2]
        mask = (weights.min(-1) >= -1e-6) & (z < depth[y, x])
        if not mask.any():
            continue
        d_uv = (texture[1:] - texture[0]).T
        if abs(np.linalg.det(d_uv)) < 1e-12:
            continue
        basis = (st[1:] - st[0]).T @ np.linalg.inv(d_uv)
        direction = basis[:, 0] / np.linalg.norm(basis[:, 0])
        y, x = y[mask], x[mask]
        depth[y, x] = z[mask]
        uv[y, x] = weights[mask] @ texture
        tangent[y, x] = direction
        sign[y, x] = np.sign(np.linalg.det(basis))
    covered = np.isfinite(depth)
    y, x = np.where(covered)
    albedo = bilinear(maps['basecolor'][1], uv[y, x])
    # The cut cap is rubber. A few source rays land on orange leather or liner
    # beside the tread. Fill those texels from their nearest rubber neighbours.
    stray = (albedo[:, 0] > .36) & (albedo[:, 0] - albedo[:, 1] > .12)
    covered[y[stray], x[stray]] = False
    assert covered.sum() > width*height*.45
    y, x = np.where(covered)
    values = np.zeros((len(maps), height, width, 4), dtype=np.float32)
    for i, (role, (_, data)) in enumerate(maps.items()):
        color = bilinear(data, uv[y, x])
        if role == 'normal':
            src = color[:, :3] * 2 - 1
            t = tangent[y, x]
            b = np.column_stack((-t[:, 1], t[:, 0])) * sign[y, x, None]
            color[:, :2] = .5 + .5 * (t * src[:, :1] + b * src[:, 1:2])
        values[i, y, x] = color
    padded = extend_padding(values, covered, PADDING + 6)
    return values, padded, int(covered.sum()), int(stray.sum())


def extend_padding(values, covered, steps):
    filled = covered.copy()
    for _ in range(steps):
        border = np.zeros_like(filled)
        for y, x in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            src_y, dst_y = slice(max(0, -y), filled.shape[0] - max(0, y)), slice(max(0, y), filled.shape[0] - max(0, -y))
            src_x, dst_x = slice(max(0, -x), filled.shape[1] - max(0, x)), slice(max(0, x), filled.shape[1] - max(0, -x))
            new = filled[src_y, src_x] & ~(filled[dst_y, dst_x] | border[dst_y, dst_x])
            values[:, dst_y, dst_x, :][:, new] = values[:, src_y, src_x, :][:, new]
            border[dst_y, dst_x] |= new
        filled |= border
    return filled


def restore_welt_color(values, maps, faces):
    # The former crevice was imprinted in both the color and normal maps.
    # Keep the pale welt and match the narrow bridge to adjacent toe leather.
    bridge = np.zeros((SIZE, SIZE), dtype=bool)
    for triangle in faces:
        region = raster(triangle * ORIGINAL_SIZE, SIZE, SIZE)
        if region is None:
            continue
        y, x, weights = region
        mask = weights.min(-1) >= -1e-6
        bridge[y[mask], x[mask]] = True
    padded = np.pad(bridge, 1)
    margin = (padded[:-2, 1:-1] | padded[2:, 1:-1] |
              padded[1:-1, :-2] | padded[1:-1, 2:]) & ~bridge
    strength = np.where(bridge, .96, np.where(margin, .42, 0))
    area = strength > 0
    roles = list(maps)
    albedo = values[roles.index('basecolor')]
    leather = albedo[area, :3]
    dark = np.maximum(np.array([.552, .304, .175]) - leather, 0)
    albedo[area, :3] += strength[area, None] * dark
    normal = values[roles.index('normal')]
    normal[area, :3] += strength[area, None] * .8 * (np.array([.5, .5, 1]) - normal[area, :3])
    return int(bridge.sum())


def rebuild_atlases(boot, original, toe_maps, tread, tiles):
    material, = boot.data.materials
    nodes = [n for n in material.node_tree.nodes if n.type == 'TEX_IMAGE']
    maps = {n.image.name.rsplit('_', 1)[1]: (n, pixels(n.image)) for n in nodes}
    assert set(maps) == {'normal', 'basecolor', 'rm'}
    values = np.zeros((len(maps), SIZE, SIZE, 4), dtype=np.float32)
    defaults = {'basecolor': (.22, .13, .09, 1), 'normal': (.5, .5, 1, 1),
                'rm': (1, .78, 0, 1)}
    y, x = np.mgrid[:ORIGINAL_SIZE, :ORIGINAL_SIZE]
    coords = (np.column_stack((x.ravel(), y.ravel())) + .5) / ORIGINAL_SIZE
    for i, (role, (_, data)) in enumerate(maps.items()):
        values[i] = defaults[role]
        values[i, :ORIGINAL_SIZE, :ORIGINAL_SIZE] = bilinear(data, coords).reshape(ORIGINAL_SIZE, ORIGINAL_SIZE, 4)
    mask = np.zeros((SIZE, SIZE), dtype=bool)
    for triangle in original:
        region = raster(triangle * ORIGINAL_SIZE, SIZE, SIZE)
        if region is not None:
            y, x, weights = region
            inside = weights.min(-1) >= -1e-6
            mask[y[inside], x[inside]] = True
        xy = np.clip((triangle * ORIGINAL_SIZE).astype(int), 0, ORIGINAL_SIZE - 1)
        mask[xy[:, 1], xy[:, 0]] = True
    restored_welt_pixels = restore_welt_color(values, maps, toe_maps)
    grown = extend_padding(values, mask, PADDING)
    for i, role in enumerate(maps):
        values[i, ~grown] = defaults[role]
    info = dict(original_uv_covered=int(mask.sum()), original_uv_padding=int((grown & ~mask).sum()),
                padding_px=PADDING, restored_welt_pixels=restored_welt_pixels, tread=[])
    for tile in tiles:
        baked, valid, source_covered, stray = bake_tread(tread, maps, tile)
        x, y = tile['offset'] - PADDING
        h, w = valid.shape
        values[:, y:y+h, x:x+w, :][:, valid] = baked[:, valid]
        info['tread'].append(dict(source_pixels=source_covered, rejected_leather_pixels=stray,
                                  padded_pixels=int(valid.sum())-source_covered))
    for i, (role, (node, _)) in enumerate(maps.items()):
        image = bpy.data.images.new(f'Boots_v3_{role}', SIZE, SIZE, alpha=False)
        image.colorspace_settings.name = node.image.colorspace_settings.name
        image.pixels.foreach_set(values[i].ravel())
        image.file_format = 'PNG'
        image.pack()
        node.image = image
        image.file_format = 'JPEG'
        image.save(filepath=str(HERE / f'{image.name}.jpg'), quality=92)
        image.file_format = 'PNG'
    return info


def repair():
    source_hash = digest(V2)
    assert source_hash == SOURCE_SHA256, 'The face repairs refer to the exact v2 export'
    scene, arm, _ = master_scene()
    boot = mount(V2, arm)
    mesh = boot.data
    tread = source_tread(mesh)
    bpy.context.view_layer.objects.active = boot
    if mesh.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_M)
    before = count_edges(bm)
    uv = bm.loops.layers.uv.active
    bm.faces.ensure_lookup_table()
    toe_maps = [np.array([loop[uv].uv[:] for loop in bm.faces[i].loops])
                for i in TOE_BRIDGE_TRIS]
    accessory_rings = close_accessory_rims(bm, uv)
    toe_moves = inset_toe_welt(bm)
    original = [np.array([loop[uv].uv[:] for loop in face.loops]) for face in bm.faces]
    for face in bm.faces:
        for loop in face.loops:
            loop[uv].uv *= ORIGINAL_SIZE / SIZE
    tiles = sole_tiles(bm, uv)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) != 3])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for face in bm.faces:
        face.smooth = True
    after = count_edges(bm)
    assert all(row[key] == 0 for row in after for key in ('boundary', 'overfull', 'wire')), [(tuple(v.co[:] for v in e.verts), len(e.link_faces)) for e in bm.edges if not e.is_manifold]
    assert all(e.is_contiguous for e in bm.edges)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    for vertex in mesh.vertices:
        weights = [w for w in vertex.groups if w.weight > 0]
        total = sum(w.weight for w in weights)
        assert 1 <= len(weights) <= 4 and abs(total - 1) < 1e-4, (vertex.index, total)
    print('TOPOLOGY', len(mesh.vertices), len(mesh.polygons), before, after, flush=True)
    atlas = rebuild_atlases(boot, original, toe_maps, tread, tiles)
    boot.name = mesh.name = TARGET.name
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    arm.animation_data_clear()
    for obj in scene.objects:
        obj.hide_set(obj not in (boot, arm))
        obj.hide_render = obj != boot
    bpy.ops.object.select_all(action='DESELECT')
    for obj in (boot, arm):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = boot
    export_glb(HERE / 'boots_export_raw.glb')
    boot.parent = arm
    arm.select_set(False)
    arm.hide_set(True)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                view = area.spaces.active.region_3d
                view.view_location = (0, -.017, .062)
                view.view_distance = .46
                view.view_rotation = Vector((.65, -.93, .54)).to_track_quat('Z', 'Y')
                area.spaces.active.shading.color_type = 'TEXTURE'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET.with_suffix('.blend')), compress=True)
    write_report(HERE / 'fit_report.json', dict(
        source_sha256=source_hash, native_sha256=digest(TARGET.with_suffix('.blend')),
        weld_distance_m=WELD_M, cut_height_m=CUT_Z, tread_height_m=TREAD_Z,
        before_edges=before, after_edges=after, triangles=len(mesh.polygons),
        closed_upper_rim_sizes=accessory_rings, toe_vertices_changed=toe_moves,
        soles=[{k: v for k, v in tile.items() if isinstance(v, int)} for tile in tiles], atlas=atlas))


if __name__ == '__main__':
    repair()
