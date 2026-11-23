"""Editable mesh primitives in gallery coordinates (X right, Y up, Z front)."""

from math import cos, pi, sin

import bpy
from mathutils import Vector

TAU = 2 * pi


def point(x=0, y=0, z=0):
    return Vector((x, y, z))


def local(p):
    return (p.x, -p.z, p.y)


def colour(rgb):
    def linear(n):
        s = n / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    return tuple(linear(n) for n in rgb) + (1,)


def material(name, rgb, roughness, metal=0, sheen=0, tinted=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = colour(rgb)
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = colour(rgb)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Sheen Weight"].default_value = sheen
    if tinted:
        paint = mat.node_tree.nodes.new("ShaderNodeVertexColor")
        paint.layer_name = "Needle colour"
        mat.node_tree.links.new(paint.outputs["Color"], shader.inputs["Base Color"])
    return mat


class Builder:
    def __init__(self):
        self.vertices = []
        self.colors = []
        self.faces = []
        self.finishes = []
        self.smooth_faces = []
        self.groups = []

    def vertex(self, p, rgb=None):
        self.vertices.append(local(p))
        self.colors.append(rgb)
        return len(self.vertices) - 1

    def face(self, indices, finish, smooth=False):
        self.faces.append(tuple(indices))
        self.finishes.append(finish)
        self.smooth_faces.append(smooth)

    def tag(self, name, first):
        self.groups.append((name, first, len(self.vertices)))

    def make(self, name, collection, parent):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        finishes = list(dict.fromkeys(self.finishes))
        for mat in finishes:
            mesh.materials.append(mat)
        for face, mat, smooth in zip(mesh.polygons, self.finishes, self.smooth_faces):
            face.material_index = finishes.index(mat)
            face.use_smooth = smooth
        if any(self.colors):
            attr = mesh.color_attributes.new(
                name="Needle colour", type="BYTE_COLOR", domain="POINT"
            )
            for value, rgb in zip(attr.data, self.colors):
                value.color_srgb = tuple(c / 255 for c in rgb) + (1,) if rgb else (1, 1, 1, 1)
            mesh.color_attributes.active_color = attr
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.parent = parent
        for label, begin, end in self.groups:
            obj.vertex_groups.new(name=label).add(list(range(begin, end)), 1, "REPLACE")
        return obj

    def tube(self, points, radii, finish, sides=6, closed=False, reference=None):
        ref = reference if reference is not None else point(0, 0, 1)
        rings = []
        for i, (p, radius) in enumerate(zip(points, radii)):
            before = points[(i - 1) % len(points)] if closed or i else p
            after = points[(i + 1) % len(points)] if closed or i + 1 < len(points) else p
            tangent = (after - before).normalized()
            side = tangent.cross(ref)
            if side.length < 0.01:
                side = tangent.cross(point(0, 1, 0))
            side.normalize()
            normal = tangent.cross(side)
            rings.append(
                [
                    self.vertex(
                        p + radius * (side * cos(TAU * j / sides) + normal * sin(TAU * j / sides))
                    )
                    for j in range(sides)
                ]
            )
        segments = len(rings) if closed else len(rings) - 1
        for i in range(segments):
            a, b = rings[i], rings[(i + 1) % len(rings)]
            for j in range(sides):
                k = (j + 1) % sides
                self.face([a[j], a[k], b[k], b[j]], finish, True)
        if not closed:
            self.face(reversed(rings[0]), finish)
            self.face(rings[-1], finish)

    def oval(self, centre, axes, finish, rings=6, sides=10):
        ax, ay, az = axes
        bottom = self.vertex(centre - az)
        turns = []
        for i in range(1, rings):
            lat = -pi / 2 + pi * i / rings
            turns.append(
                [
                    self.vertex(
                        centre
                        + ax * (cos(lat) * cos(TAU * j / sides))
                        + ay * (cos(lat) * sin(TAU * j / sides))
                        + az * sin(lat)
                    )
                    for j in range(sides)
                ]
            )
        top = self.vertex(centre + az)
        for j in range(sides):
            k = (j + 1) % sides
            self.face([bottom, turns[0][k], turns[0][j]], finish, True)
            for a, b in zip(turns, turns[1:]):
                self.face([a[j], a[k], b[k], b[j]], finish, True)
            self.face([turns[-1][j], turns[-1][k], top], finish, True)

    def blade(self, base, end, width, lift, tint, finish):
        # A longitudinal crease gives each two-sided needle a front and back highlight.
        axis = end - base
        side = point(-axis.y, axis.x, 0).normalized() * width
        centre = base + axis * 0.43
        root = tuple(round(n * 0.77) for n in tint)
        tip = tuple(min(255, round(n * 1.12)) for n in tint)
        b = self.vertex(base, root)
        e = self.vertex(end, tip)
        shoulders = centre - point(0, 0, lift)
        l = self.vertex(shoulders + side, tint)
        r = self.vertex(shoulders - side, tint)
        self.face((b, r, e), finish)
        self.face((b, e, l), finish)
