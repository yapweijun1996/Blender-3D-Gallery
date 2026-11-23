"""Retessellate original Studio toe and cheek surface patches, preserving original positions."""
from collections import defaultdict
from pathlib import Path
import json

import bmesh
from mathutils import Vector
from mathutils.kdtree import KDTree


def repair(body):
    mesh = body.data
    patches = json.loads(Path(__file__).with_name("diagonals.json").read_text())
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.faces.index_update()
    face_centers = KDTree(len(bm.faces))
    for face in bm.faces:
        face_centers.insert(body.matrix_world @ face.calc_center_median(), face.index)
    face_centers.balance()
    jobs = []
    evidence = defaultdict(list)
    has_normals = mesh.has_custom_normals
    old_normals = [value.vector.copy() for value in mesh.corner_normals] if has_normals else []
    # World centroids identify the Studio triangles even after source UV seams are welded.
    for before, after in patches:
        before = [Vector(v) for v in before]
        center = sum(before, Vector()) / 3
        _, index, distance = face_centers.find(center)
        face = bm.faces[index]
        if distance > .0001 or len(face.verts) != 3:
            raise ValueError(f"Studio patch triangle missing near {tuple(center)} ({distance} m)")
        loops = list(face.loops)
        for co in before:
            loop = min(loops, key=lambda l: ((body.matrix_world @ l.vert.co)-co).length)
            if ((body.matrix_world @ loop.vert.co)-co).length > .0001:
                raise ValueError(f"Topology diverged at {tuple(co)}")
            evidence[tuple(co)].append(loop)
        jobs.append((face, [tuple(Vector(p)) for p in after]))
    normals_by_vertex_face = {}
    if has_normals:
        for poly in mesh.polygons:
            verts = tuple(sorted(poly.vertices))
            for i in poly.loop_indices:
                normals_by_vertex_face[verts,mesh.loops[i].vertex_index] = old_normals[i]
    old_keys = {frozenset(tuple(Vector(p)) for p in before) for before, _ in patches}
    new_keys = {frozenset(tuple(Vector(p)) for p in after) for _, after in patches}
    oldfaces = {job[0] for job,(before,_) in zip(jobs,patches) if frozenset(tuple(Vector(p)) for p in before) not in new_keys}
    for source, positions in jobs:
        if frozenset(positions) in old_keys:
            continue
        corners = []
        for key in positions:
            pool = evidence[key]
            # Retain source-face corners, then take the most similarly oriented
            # neighbour at the identical geometric vertex. Its UV stays attached.
            corners.append(max(pool, key=lambda l: (l.face == source, l.face.normal.dot(source.normal))))
        face = bm.faces.new([loop.vert for loop in corners])
        face.material_index = source.material_index
        face.smooth = source.smooth
        vkey = tuple(sorted(v.index for v in face.verts))
        for dest, original in zip(face.loops, corners):
            for uv in bm.loops.layers.uv.values():
                dest[uv].uv = original[uv].uv
            for layer in bm.loops.layers.color.values() + bm.loops.layers.float_color.values():
                dest[layer] = original[layer]
            if has_normals:
                orig_key=tuple(sorted(v.index for v in original.face.verts))
                normals_by_vertex_face[vkey, dest.vert.index] = normals_by_vertex_face[orig_key, original.vert.index]
    used_old_edges={e for f in oldfaces for e in f.edges}
    bmesh.ops.delete(bm, geom=list(oldfaces), context='FACES_ONLY')
    for e in used_old_edges:
        if e.is_valid and not e.link_faces:
            bm.edges.remove(e)
    # Two nearly coplanar original facial triangles meet just beyond their
    # endpoints. A 15 micrometre displacement preserves the original diagonal.
    source_vertex = Vector((.1234279498,-.1253412515,.7099483013))
    local_delta = body.matrix_world.to_3x3().inverted() @ Vector((0,-.000015,0))
    shifted = [v for v in bm.verts if ((body.matrix_world @ v.co)-source_vertex).length<1e-6]
    if not shifted:
        raise ValueError("The source facial crease vertex was not found")
    for v in shifted:
        v.co += local_delta
    bm.to_mesh(mesh)
    bm.free()
    if has_normals:
        all_normals = [None]*len(mesh.loops)
        for poly in mesh.polygons:
            key = tuple(sorted(poly.vertices))
            for i in poly.loop_indices:
                all_normals[i] = normals_by_vertex_face[key, mesh.loops[i].vertex_index]
        mesh.normals_split_custom_set(all_normals)
    mesh.update()
    return len(oldfaces)
