"""Shared mesh reduction and binary glTF serialization."""
from collections import defaultdict
import json
import math
import struct

import bmesh
import bpy
from mathutils import Vector
import numpy as np

def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']


def extents(points):
    array = np.asarray(points)
    return array.min(axis=0), array.max(axis=0)


def fit(objects, length=None):
    lo, hi = extents([obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices])
    return Vector(((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, lo[2])), length/(hi[1]-lo[1]) if length else 1.0


def wheel_id(obj):
    axle = obj.parent.parent.name if obj.parent and obj.parent.name.startswith('ROLL_') else ''
    if axle in ('STEER_Front_L', 'STEER_Front_R', 'AXLE_Rear_L', 'AXLE_Rear_R'):
        axle = axle.replace('STEER_Front_', 'F').replace('AXLE_Rear_', 'R')
    elif axle:
        axle = axle.split('_', 1)[1]
    return f'wheel_{axle}' if axle else None


def new_mesh(name, vertices, faces, smooth=()):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    for index in smooth:
        mesh.polygons[index].use_smooth = True
    return mesh


def box_reduction(mesh, chamfer):
    """Reconstruct the source box from its measured local bounds and bevel inset."""
    points = np.array([tuple(v.co) for v in mesh.vertices])
    lo, hi = extents(points)
    bm = bmesh.new()
    result = bmesh.ops.create_cube(bm, size=1)
    for vert in result['verts']:
        vert.co = Vector(lo + (np.array(vert.co) + .5) * (hi-lo))
    if chamfer:
        inset = np.minimum(points - lo, hi - points)
        width = float(inset.max(axis=0).min())
        assert 0 < width < min(hi-lo)/2, (mesh.name, width, lo, hi)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=width,
                        segments=1, affect='EDGES', clamp_overlap=True)
    reduced = bpy.data.meshes.new(mesh.name + ' reduced')
    bm.to_mesh(reduced)
    bm.free()
    return reduced


def compact(obj, triangles):
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new('Reduce fine contour', 'DECIMATE')
    obj.data.calc_loop_triangles()
    modifier.ratio = triangles/len(obj.data.loop_triangles)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    reduced = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    obj.modifiers.remove(modifier)
    return reduced


def revolved(name, origin, axis, basis, profile, steps, closed):
    """Resample original surfaces of revolution with smooth curved bands."""
    tangent = axis.cross(basis)
    vertices = [
        origin + axis*float(depth) + float(radius)*(math.cos(angle)*basis + math.sin(angle)*tangent)
        for depth, radius in profile
        for angle in (2*math.pi*i/steps for i in range(steps))
    ]
    faces = []
    for ring in range(len(profile) if closed else len(profile)-1):
        next_ring = (ring+1) % len(profile)
        for i in range(steps):
            j = (i+1) % steps
            faces.append((ring*steps+i, ring*steps+j, next_ring*steps+j, next_ring*steps+i))
    smooth = range(len(faces))
    if not closed:
        faces.extend([tuple(reversed(range(steps))),
                      tuple(range(len(vertices)-steps, len(vertices)))])
    mesh = new_mesh(name, vertices, faces, smooth)
    return mesh


def torus_from_source(mesh, steps, cross_section):
    """Keep the measured torus cross-section and all four cardinal extrema."""
    rings = {}
    for v in mesh.vertices:
        x, y, z = v.co
        r = math.hypot(x, y)
        rings[(round(z, 5), round(r, 5))] = (z, r)
    profile = list(rings.values())
    radial_center = (min(r for _, r in profile) + max(r for _, r in profile))/2
    by_angle = {
        round(math.atan2(depth, radius-radial_center)/(math.tau/8)) % 8: (depth, radius)
        for depth, radius in profile
    }
    assert len(by_angle) == 8, (mesh.name, by_angle)
    return revolved(mesh.name, Vector(), Vector((0,0,1)), Vector((1,0,0)),
                    [by_angle[i] for i in cross_section], steps, closed=True)


def beveled_hub(mesh, steps):
    profile = {}
    for v in mesh.vertices:
        x, y, z = v.co
        profile[round(z, 5)] = (z, math.hypot(x,y))
    rings = sorted(profile.values())
    assert len(rings) == 6, (mesh.name, rings)
    # The outermost span and end-cap radii keep the original disc profile.
    return revolved(mesh.name, Vector(), Vector((0,0,1)), Vector((1,0,0)),
                    [rings[i] for i in (0,2,3,5)], steps, closed=False)


def radial_spokes(obj):
    # The five original spokes overlap at the wheel center. Use their source
    # construction with six sides, retaining the measured axial placement.
    mesh = obj.data
    roll = obj.parent.matrix_world
    roll_to_mesh = obj.matrix_world.inverted() @ roll
    mesh_to_roll = roll_to_mesh.inverted()
    source = [mesh_to_roll @ v.co for v in mesh.vertices]
    xs = [v.x for v in source]
    axial_center = (max(xs)+min(xs))/2
    radius = (max(xs)-min(xs))/2
    spoke_length = max(v.y for v in source)
    axial_center = math.copysign(abs(axial_center), roll.translation.x)
    vertices, faces, smooth = [], [], []
    for i in range(5):
        angle = i*math.tau/5
        axis = roll_to_mesh.to_3x3() @ Vector((0,math.cos(angle),math.sin(angle)))
        basis = roll_to_mesh.to_3x3() @ Vector((1,0,0))
        origin = roll_to_mesh @ Vector((axial_center,0,0))
        spoke = revolved(mesh.name, origin, axis, basis, [(0,radius), (spoke_length,radius)],
                         6, closed=False)
        smooth.extend(len(faces)+p.index for p in spoke.polygons if p.use_smooth)
        faces.extend(tuple(len(vertices)+i for i in p.vertices) for p in spoke.polygons)
        vertices.extend(v.co.copy() for v in spoke.vertices)
        bpy.data.meshes.remove(spoke)
    return new_mesh(mesh.name, vertices, faces, smooth)


def y_up(point):
    return (point[0], point[2], -point[1] if point[1] else 0.0)


class BinaryMesh:
    def __init__(self, materials):
        self.material_ids = {name: i for i, name in enumerate(materials)}
        self.doc = {'asset': {'version': '2.0', 'generator': 'Blender 5 vehicle reduction'},
                    'scene': 0, 'scenes': [{'nodes': []}], 'nodes': [], 'meshes': [],
                    'materials': list(materials.values()), 'bufferViews': [], 'accessors': []}
        self.data = bytearray()

    def accessor(self, array, component, kind, target, normalized=False, bounds=False):
        blob = array.tobytes()
        start = len(self.data)
        self.data.extend(blob)
        self.data.extend(b'\0' * ((-len(blob)) % 4))
        views = self.doc['bufferViews']
        accessors = self.doc['accessors']
        views.append({'buffer': 0, 'byteOffset': start, 'byteLength': len(blob), 'target': target})
        accessor = {'bufferView': len(views)-1, 'componentType': component,
                    'count': len(array), 'type': kind}
        if normalized:
            accessor['normalized'] = True
        if bounds:
            accessor.update(min=array.min(axis=0).tolist(), max=array.max(axis=0).tolist())
        accessors.append(accessor)
        return len(accessors)-1

    def primitive(self, slot, vertices, indices, color):
        array = np.array(vertices, dtype='<f4')
        attributes = {
            'POSITION': self.accessor(array[:,:3], 5126, 'VEC3', 34962, bounds=True),
            'NORMAL': self.accessor(array[:,3:6], 5126, 'VEC3', 34962),
        }
        if color:
            rgba = (array[:,6:10]*65535+.5).astype('<u2')
            attributes['COLOR_0'] = self.accessor(rgba, 5123, 'VEC4', 34962, normalized=True)
        assert len(vertices) < 65536
        return {'attributes': attributes, 'material': self.material_ids[slot],
                'indices': self.accessor(np.array(indices, dtype='<u2'), 5123, 'SCALAR', 34963)}

    def add_node(self, name, pivot, primitives):
        meshes = self.doc['meshes']
        nodes = self.doc['nodes']
        nodes.append({'name': name, 'mesh': len(meshes), 'translation': y_up(pivot)})
        meshes.append({'name': name, 'primitives': primitives})
        self.doc['scenes'][0]['nodes'].append(len(nodes)-1)

    def write(self, path):
        self.doc['buffers'] = [{'byteLength': len(self.data)}]
        encoded = json.dumps(self.doc, separators=(',', ':')).encode()
        encoded += b' '*((-len(encoded)) % 4)
        path.write_bytes(struct.pack('<IIIII', 0x46546c67, 2, 28+len(encoded)+len(self.data),
                                     len(encoded), 0x4e4f534a) + encoded
                         + struct.pack('<II', len(self.data), 0x004e4942) + self.data)


def emit_group(glb, name, parts, geometries, center, scale, pivot):
    groups = defaultdict(list)
    for part, mesh in zip(parts, geometries, strict=True):
        groups[part.slot].append((part, mesh))
    primitives = []
    total = 0
    for slot, sources in groups.items():
        components = {}
        color = slot not in {'paint', 'tire'}
        vertices, indices, lookup = [], [], {}
        for part, mesh in sources:
            first_triangle = len(indices)//3
            mesh.calc_loop_triangles()
            normals = mesh.corner_normals
            orientation = part.transform.to_3x3()
            assert orientation.determinant() > 0, part.obj.name
            normal_transform = orientation.inverted().transposed()
            positions = [((part.transform @ v.co-center)*scale-pivot) for v in mesh.vertices]
            for triangle in mesh.loop_triangles:
                a,b,c = (positions[i] for i in triangle.vertices)
                if (b-a).cross(c-a).length_squared < 1e-22:
                    continue
                triangle_vertices = []
                for vi, li in zip(triangle.vertices, triangle.loops, strict=True):
                    normal = (normal_transform @ normals[li].vector).normalized()
                    vertex = y_up(positions[vi])+y_up(normal)+(part.rgba if color else ())
                    triangle_vertices.append((tuple(round(v,7) for v in vertex),vertex))
                if len({key[:3] for key, _ in triangle_vertices}) != 3:
                    continue
                for key, vertex in triangle_vertices:
                    if key not in lookup:
                        lookup[key] = len(vertices)
                        vertices.append(vertex)
                    indices.append(lookup[key])
            if part.obj.name.startswith(('police_lamp_', 'taxi_lit_')):
                components[part.obj.name] = {'first_triangle': first_triangle,
                                              'triangle_count': len(indices)//3-first_triangle}
        assert len(indices) % 3 == 0 and all(len(set(indices[i:i+3])) == 3 for i in range(0,len(indices),3))
        total += len(indices)//3
        primitive = glb.primitive(slot, vertices, indices, color)
        if components:
            primitive['extras'] = {'components': components}
        primitives.append(primitive)
    glb.add_node(name, pivot, primitives)
    return total


