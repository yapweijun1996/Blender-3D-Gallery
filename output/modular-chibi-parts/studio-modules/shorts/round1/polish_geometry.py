"""Regularize the decimated Studio surface before the motion offset bake."""
import bmesh
import numpy as np


def edge_cleanup(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if e.is_wire], context="EDGES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context="VERTS")
    # Sliver faces from dense segmentation boundaries fold under solidification.
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.00135)
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if e.is_wire], context="EDGES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context="VERTS")
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(e.is_manifold or e.is_boundary for e in bm.edges)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


def relax(points, mesh, tree, api):
    graph = api["adjacency"](mesh)
    boundary = {}
    for face in mesh.polygons:
        row = face.vertices[:]
        for i, a in enumerate(row):
            b = row[(i + 1) % len(row)]
            key = tuple(sorted((a, b)))
            if key in boundary:
                del boundary[key]
            else:
                boundary[key] = (a, b)
    endpoints = np.asarray(list(boundary.values()), dtype=np.int32)
    boundary_src, boundary_dst = np.concatenate((endpoints, endpoints[:, ::-1])).T
    rim = np.unique(boundary_src)
    old_z = points[:, 2].copy()
    waist = api["smoothstep"](.380, .414, old_z)
    top = rim[points[rim, 2] > .37]
    # The back of the Studio cut rises into the stop between the master hips
    # and torso. A level band keeps the hem clear of that moving seam.
    points[:, 2] += waist * (.409 - np.maximum(.405, old_z))
    points[top, 2] = .409
    original = points.copy()
    for _ in range(9):
        displacement = api["average"](points, graph) - points
        rim_delta = np.zeros_like(points)
        np.add.at(rim_delta, boundary_src, points[boundary_dst])
        rim_delta = .5 * rim_delta - points
        displacement[rim] = rim_delta[rim]
        _, _, normals, _ = api["nearest"](tree, points)
        projection = (normals * displacement).sum(axis=1, keepdims=True) * normals
        points = points + .42 * (displacement - .60 * projection)
        points = .955 * points + .045 * original
        d, _, n, _ = api["nearest"](tree, points)
        points += np.maximum(.0062 - d, 0)[:, None] * n
        points[top, 2] = .409
    return points
