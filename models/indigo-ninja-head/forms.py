"""Small Blender primitives for the Indigo ninja portrait, in world coordinates."""
from math import cos, pi, sin

import bpy
from mathutils import Vector


def material(name, hex_color, roughness=.48):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    code = hex_color.lstrip("#")
    rgb = [int(code[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*linear, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*linear, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat


def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    data.materials.append(mat)
    for polygon in data.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    return obj


def ellipsoid(name, center, radii, mat, rotation=(0, 0, 0), segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    obj.scale = radii
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def tube(name, points, radii, mat, sides=10):
    points = [Vector(point) for point in points]
    if isinstance(radii, (int, float)):
        radii = [radii] * len(points)
    verts, faces = [], []
    normal = None
    for i, point in enumerate(points):
        tangent = (points[min(i+1, len(points)-1)] - points[max(0, i-1)]).normalized()
        if normal is None:
            normal = tangent.orthogonal().normalized()
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        other = tangent.cross(normal)
        for j in range(sides):
            angle = 2 * pi * j / sides
            verts.append(point + radii[i] * (cos(angle)*normal + sin(angle)*other))
            if i:
                a = (i-1)*sides + j
                b = (i-1)*sides + (j+1) % sides
                faces.append((a, b, b+sides, a+sides))
    faces.extend([tuple(reversed(range(sides))), tuple(range(len(verts)-sides, len(verts)))])
    return mesh(name, verts, faces, mat)
