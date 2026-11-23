"""Endpoint quadric decimation with explicit boundary, material and UV constraints."""
from collections import Counter
from dataclasses import dataclass
import heapq

import numpy as np
from mathutils import Vector


@dataclass
class Face:
    vertices: tuple
    material: int
    uv: tuple
    color: tuple

    def corner(self, vertex):
        return self.vertices.index(vertex)


def topology(faces):
    edges = Counter()
    links = {}
    for face in faces:
        a, b, c = face.vertices
        for x, y in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((x, y)))] += 1
            links.setdefault(x, set()).add(y)
            links.setdefault(y, set()).add(x)
    boundaries = {}
    for (x, y), count in edges.items():
        if count == 1:
            boundaries.setdefault(x, set()).add(y)
            boundaries.setdefault(y, set()).add(x)

    def components(graph):
        remaining = set(graph)
        count = 0
        while remaining:
            count += 1
            queue = [remaining.pop()]
            while queue:
                neighbors = graph[queue.pop()] & remaining
                remaining -= neighbors
                queue.extend(neighbors)
        return count

    return dict(components=components(links), boundary_components=components(boundaries),
                nonmanifold_edges=sum(n > 2 for n in edges.values()),
                boundary_branches=sum(len(n) != 2 for n in boundaries.values()),
                euler=len(links)-len(edges)+len(faces))


class Decimator:
    def __init__(self, points, weights, faces, boundary_error, material_priority=None):
        self.points = [Vector(p) for p in points]
        self.faces = dict(enumerate(faces))
        self.original_faces = faces
        self.boundary_error = boundary_error
        self.vertex_faces = [set() for _ in points]
        self.quadrics = np.zeros((len(points), 4, 4))
        self.weights = weights
        self.positions = np.column_stack((points, np.ones(len(points))))
        self.versions = [0] * len(points)
        self.heap = []
        for idx, face in self.faces.items():
            vertices = face.vertices
            a, b, c = (self.points[v] for v in vertices)
            cross = (b-a).cross(c-a)
            area = cross.length
            if area > 0:
                normal = cross / area
                plane = np.array([*normal, -normal.dot(a)])
                importance = material_priority[face.material] if material_priority else 1.0
                self.quadrics[list(vertices)] += np.outer(plane, plane) * (area * importance)
            for v in vertices:
                self.vertex_faces[v].add(idx)
        for v in range(len(points)):
            for n in self.neighbors(v):
                if v < n:
                    self.enqueue(v, n)

    def neighbors(self, v):
        return {n for j in self.vertex_faces[v] for n in self.faces[j].vertices if n != v}

    def edge_feature(self, v, u):
        local = self.vertex_faces[v] & self.vertex_faces[u]
        if len(local) != 2:
            return ('boundary',) if len(local) == 1 else ('nonmanifold',)
        a, b = (self.faces[j] for j in local)
        feature = ()
        if a.material != b.material:
            feature += ('material',)
        if a.uv and any(a.uv[a.corner(w)] != b.uv[b.corner(w)] for w in (v, u)):
            feature += ('uv',)
        return feature

    def enqueue(self, v, u):
        q = self.quadrics[v] + self.quadrics[u]
        dp = self.points[v]-self.points[u]
        weight_change = float(np.abs(self.weights[v]-self.weights[u]).sum())
        regularizer = dp.length_squared**2 * (.006 + .07*weight_change)
        for remove, keep in ((v, u), (u, v)):
            x = self.positions[keep]
            cost = max(0., x @ q @ x) + regularizer
            heapq.heappush(self.heap, (cost, remove, keep, self.versions[remove], self.versions[keep]))

    def collapse_plan(self, v, u):
        v_faces, u_faces = self.vertex_faces[v], self.vertex_faces[u]
        common = v_faces & u_faces
        if len(common) not in (1, 2):
            return
        remaining = v_faces - common
        if not remaining:
            return
        v_neighbors, u_neighbors = self.neighbors(v), self.neighbors(u)
        opposite = {w for j in common for w in self.faces[j].vertices} - {v, u}
        if v_neighbors & u_neighbors != opposite:
            return

        features = {w: self.edge_feature(v, w) for w in v_neighbors}
        features = {w: kind for w, kind in features.items() if kind}
        feature = features.get(u, ())
        if features:
            if (len(features) != 2 or not feature or 'nonmanifold' in feature
                    or any(k != feature for k in features.values())):
                return
            other = next(w for w in features if w != u)
            a, b, p = self.points[u], self.points[other], self.points[v]
            segment = b-a
            if segment.length_squared == 0:
                return
            projection = (p-a).dot(segment) / segment.length_squared
            if not 0 < projection < 1:
                return
            limit = self.boundary_error if set(feature) & {'boundary', 'material'} else .0025
            if (p-a-projection*segment).length > limit:
                return

        uv_map = {}
        for idx in sorted(common):
            face = self.faces[idx]
            if not face.uv:
                continue
            old, new = face.uv[face.corner(v)], face.uv[face.corner(u)]
            if old in uv_map and uv_map[old] != new:
                return
            uv_map[old] = new
        if len(set(uv_map.values())) != len(uv_map):
            return

        existing = {frozenset(self.faces[j].vertices) for j in u_faces-common}
        plan = {}
        for j in sorted(remaining):
            face = self.faces[j]
            corner = face.corner(v)
            vertices = tuple(u if w == v else w for w in face.vertices)
            key = frozenset(vertices)
            if key in existing:
                return
            existing.add(key)
            a, b, c = (self.points[w] for w in face.vertices)
            x, y, z = (self.points[w] for w in vertices)
            old, new = (b-a).cross(c-a), (y-x).cross(z-x)
            if new.length < 1e-11 or old.dot(new) < .18 * old.length * new.length:
                return
            uv = face.uv
            if uv:
                replacement = uv_map.get(uv[corner])
                if replacement is None:
                    return
                uv = (*uv[:corner], replacement, *uv[corner+1:])
                # Preserve valid source chart orientation and avoid zero-area UV triangles.
                old_area = uv_area(face.uv)
                if abs(old_area) > 1e-10 and uv_area(uv) / old_area <= .008:
                    return
            colors = face.color
            if colors:
                all_colors = [self.faces[k].color[self.faces[k].corner(u)] for k in sorted(common)]
                replacement = min(all_colors, key=lambda c: sum((a-b)**2 for a, b in zip(c, colors[corner])))
                colors = (*colors[:corner], replacement, *colors[corner+1:])
            plan[j] = Face(vertices, face.material, uv, colors)
        return common, plan

    def run(self, limit, guard=None):
        while len(self.faces) > limit and self.heap:
            _, v, u, vr, ur = heapq.heappop(self.heap)
            if (vr, ur) != (self.versions[v], self.versions[u]):
                continue
            candidate = self.collapse_plan(v, u)
            if candidate is None:
                continue
            removed, plan = candidate
            if guard is not None and not guard(removed, plan):
                continue
            changed = self.neighbors(v) | self.neighbors(u) | {v, u}
            for j in sorted(removed | plan.keys()):
                for w in self.faces[j].vertices:
                    self.vertex_faces[w].remove(j)
                if j in removed:
                    del self.faces[j]
                else:
                    face = self.faces[j] = plan[j]
                    for w in face.vertices:
                        self.vertex_faces[w].add(j)
            self.quadrics[u] += self.quadrics[v]
            for w in sorted(changed):
                self.versions[w] += 1
            updated = {(min(w, n), max(w, n)) for w in changed for n in self.neighbors(w)}
            for w, n in sorted(updated):
                self.enqueue(w, n)
        return list(self.faces.values())


def uv_area(uv):
    (ax, ay), (bx, by), (cx, cy) = uv
    return (bx-ax)*(cy-ay) - (by-ay)*(cx-ax)
