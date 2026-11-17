"""Editable metric profiles and metalwork for the four architectural ceiling luminaires."""
import math

import bpy
from mathutils import Vector


def material(name, hex_color, metallic=0, roughness=.4, emission=0):
    srgb = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
    rgba = tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in srgb) + (1,)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = rgba
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission:
        shader.inputs["Emission Color"].default_value = rgba
        shader.inputs["Emission Strength"].default_value = emission
    return mat


def group(name, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj.empty_display_size = .010
    return obj


def mesh(name, parent, material, vertices, faces, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    data.materials.append(material)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    if smooth:
        data.polygons.foreach_set("use_smooth", [True]*len(faces))
        data.set_sharp_from_angle(angle=math.radians(39))
    return obj


def revolve(name, parent, material, profile, segments, *, smooth=True, scallop=None, phase=0):
    """Spin radius/height pairs counterclockwise from the bottom along the outside."""
    verts, faces, rings = [], [], []
    for row, (radius, z) in enumerate(profile):
        ring = []
        for col in range(segments if radius else 1):
            angle = math.tau * (col + (phase if row % 2 else 0)) / segments
            r = radius + (scallop(radius, z, angle) if scallop and radius else 0)
            ring.append(len(verts))
            verts.append((r*math.cos(angle), r*math.sin(angle), z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for j in range(segments):
            k = (j+1) % segments
            if len(a) == 1 and len(b) > 1:
                faces.append((a[0], b[k], b[j]))
            elif len(b) == 1 and len(a) > 1:
                faces.append((a[j], a[k], b[0]))
            elif len(a) > 1 and len(b) > 1:
                faces.append((a[j], a[k], b[k], b[j]))
    return mesh(name, parent, material, verts, faces, smooth)


def disc(name, parent, mat, radius, z0, z1, sides, bevel=.0007):
    return revolve(name, parent, mat, [(0,z0), (radius-bevel,z0), (radius,z0+bevel),
        (radius,z1-bevel), (radius-bevel,z1), (0,z1)], sides)


def box(name, parent, mat, xyz, size, bevel, lod):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name = obj.data.name = name
    obj.parent = parent
    obj.location = xyz
    for v in obj.data.vertices:
        v.co = [a*b for a, b in zip(v.co, size)]
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new("Machined corners", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1 if lod else 3
        obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    return obj


def bar(name, parent, mat, start, end, width, thickness, lod):
    start, end = Vector(start), Vector(end)
    obj = box(name, parent, mat, (start+end)/2, (width,thickness,(end-start).length), .0006, lod)
    obj.rotation_euler = (end-start).to_track_quat("Z","Y").to_euler()
    return obj


def extrusion_x(name, parent, mat, section, x0, x1, smooth=False):
    """Extrude a counterclockwise YZ section along X."""
    n = len(section)
    verts = [(x,y,z) for x in (x0,x1) for y,z in section]
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n))
    return mesh(name, parent, mat, verts, faces, smooth)


def screw(name, parent, mat, position, rotation=(0,0,0), radius=.003):
    # A recessed hex socket and six-sided floor remain solid on reimport.
    obj = revolve(name, parent, mat, [(0,0),(radius,0),(radius,radius*.3),
        (radius*.86,radius*.43),(radius*.45,radius*.43),(radius*.45,radius*.24),
        (0,radius*.24)], 6, smooth=False)
    obj.location = position
    obj.rotation_euler = rotation
    return obj
