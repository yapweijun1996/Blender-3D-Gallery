"""Derive the static drive-demo GLBs from the three checked-in gallery exports."""
from collections import defaultdict
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct

import bmesh
import bpy
from mathutils import Vector
import numpy as np

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
VEHICLES = {
    'bus': ('singapore-public-bus', 'singapore-public-bus.glb', 12.0, 6500),
    'van': ('delivery-van', 'optimized.glb', 4.9, 4500),
    'truck': ('cargo-truck', 'cargo-truck.glb', 8.8, 5000),
}
WHEELS = ['wheel_FL', 'wheel_FR', 'wheel_RL', 'wheel_RR']
MATERIALS = ['paint', 'glass', 'tire', 'light', 'trim', 'metal', 'chrome', 'plate']


@dataclass
class Part:
    obj: object
    transform: object
    slot: str
    rgba: tuple
    metallic: float
    roughness: float
    wheel: str | None


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']


def extents(points):
    array = np.asarray(points)
    return array.min(axis=0), array.max(axis=0)


def fit(objects, length):
    lo, hi = extents([obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices])
    return Vector(((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, lo[2])), length/(hi[1]-lo[1])


def wheel_id(obj):
    axle = obj.parent.parent.name if obj.parent and obj.parent.name.startswith('ROLL_') else ''
    if axle in ('STEER_Front_L', 'STEER_Front_R', 'AXLE_Rear_L', 'AXLE_Rear_R'):
        axle = axle.replace('STEER_Front_', 'F').replace('AXLE_Rear_', 'R')
    elif axle:
        axle = axle.split('_', 1)[1]
    return f'wheel_{axle}' if axle else None


def classify(obj, shader, wheel, paint):
    name = obj.name.lower()
    original = obj.data.materials[0].name
    if wheel:
        return 'tire' if name.startswith('tyre') else 'metal'
    if name.startswith(('front_headlamp', 'headlight', 'tail_light')):
        return 'light'
    if name.startswith('editable_label'):
        return 'plate'
    if any(token in name for token in ('glass', 'pane', 'windscreen', 'window_band', 'end_window')):
        if 'frame' not in name:
            return 'glass'
    if name.startswith(('door_stile', 'door_top', 'front_bumper', 'rear_handle', 'door_lockbar')):
        return 'chrome'
    if original == paint and not name.startswith('seat'):
        return 'paint'
    if shader.inputs['Metallic'].default_value >= .2:
        return 'metal'
    return 'trim'


def part_for(obj, paint):
    shader = next(n for n in obj.data.materials[0].node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    assert len(obj.data.materials) == 1
    wheel = wheel_id(obj)
    return Part(obj, obj.matrix_world.copy(), classify(obj, shader, wheel, paint),
                tuple(shader.inputs['Base Color'].default_value[:3]) + (shader.inputs['Alpha'].default_value,),
                shader.inputs['Metallic'].default_value, shader.inputs['Roughness'].default_value, wheel)


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


def van_hub(mesh):
    profile = {}
    for v in mesh.vertices:
        x, y, z = v.co
        profile[round(z, 5)] = (z, math.hypot(x,y))
    rings = sorted(profile.values())
    assert len(rings) == 6, (mesh.name, rings)
    # The outermost span and end-cap radii keep the original disc profile.
    return revolved(mesh.name, Vector(), Vector((0,0,1)), Vector((1,0,0)),
                    [rings[i] for i in (0,2,3,5)], 20, closed=False)


def van_spokes(obj):
    # The five original spokes overlap at the wheel center. Use their source
    # construction with six sides, retaining the measured axial placement.
    mesh = obj.data
    roll = obj.parent.matrix_world
    roll_to_mesh = obj.matrix_world.inverted() @ roll
    mesh_to_roll = roll_to_mesh.inverted()
    xs = [(mesh_to_roll @ v.co).x for v in mesh.vertices]
    axial_center = (max(xs)+min(xs))/2
    radius = (max(xs)-min(xs))/2
    vertices, faces, smooth = [], [], []
    for i in range(5):
        angle = i*math.tau/5
        axis = roll_to_mesh.to_3x3() @ Vector((0,math.cos(angle),math.sin(angle)))
        basis = roll_to_mesh.to_3x3() @ Vector((1,0,0))
        origin = roll_to_mesh @ Vector((axial_center,0,0))
        spoke = revolved(mesh.name, origin, axis, basis, [(0,radius), (.18,radius)],
                         6, closed=False)
        smooth.extend(len(faces)+p.index for p in spoke.polygons if p.use_smooth)
        faces.extend(tuple(len(vertices)+i for i in p.vertices) for p in spoke.polygons)
        vertices.extend(v.co.copy() for v in spoke.vertices)
        bpy.data.meshes.remove(spoke)
    return new_mesh(mesh.name, vertices, faces, smooth)


def geometry(part, vehicle):
    obj = part.obj
    mesh = obj.data
    name = obj.name.split('.')[0].lower()
    mesh.calc_loop_triangles()
    if part.slot == 'tire':
        return torus_from_source(mesh, 32 if vehicle != 'van' else 24, (0,1,2,4,6,7))
    if name == 'rim_spokes':
        return van_spokes(obj)
    if name == 'hub' and vehicle == 'van':
        return van_hub(mesh)
    if name in ('steering_wheel', 'interior_steering'):
        return torus_from_source(mesh, 16, (0,2,4,6))
    if name == 'editable_label_bus':
        return compact(obj, 460)
    if len(mesh.loop_triangles) != 108:
        return mesh
    if name.startswith(('rim_spoke', 'seat_support', 'side_floor', 'centre_low_floor')):
        return box_reduction(mesh, chamfer=False)
    if vehicle == 'bus' and name.startswith(('seat_', 'door_stile', 'door_top',
                                              'window_post', 'end_window_frame')):
        return box_reduction(mesh, chamfer=False)
    if vehicle == 'van' and name.startswith(('cabin_pillar', 'cabin_floor', 'cargo_bulkhead',
                                              'cargo_floor', 'interior_dashboard',
                                              'rear_handle', 'cargo_slidinghandle')):
        return box_reduction(mesh, chamfer=False)
    if vehicle == 'van' and name in {'cabin_nose', 'cabin_roof', 'bumper', 'cabin_mirror',
                                        'cargo_roof', 'cargo_slidingleaf', 'rear_doorleaf', 'chassis'}:
        return mesh
    if vehicle == 'truck' and name.startswith('cab_door_'):
        if name != 'cab_door_lower':
            return mesh
        # The panel end caps originally share the stiles' exterior planes.
        # Tuck the caps inside the existing stiles to avoid coincident hits
        # through the merged paint primitive without moving its silhouette.
        shortened = mesh.copy()
        ys = [v.co.y for v in shortened.vertices]
        assert abs(max(ys)-min(ys)-1.76) < .0001
        midpoint = (min(ys)+max(ys))/2
        for vertex in shortened.vertices:
            vertex.co.y -= math.copysign(.002, vertex.co.y-midpoint)
        shortened.update()
        return shortened
    return box_reduction(mesh, chamfer=True)


def material_table(parts):
    table = {}
    for name in MATERIALS:
        subset = [p for p in parts if p.slot == name]
        if not subset:
            continue
        first = subset[0]
        properties = {'metallicFactor': first.metallic, 'roughnessFactor': first.roughness}
        if name in ('paint', 'tire'):
            properties['baseColorFactor'] = first.rgba
            assert all(p.rgba == first.rgba for p in subset)
        if name == 'trim':
            roughnesses = {p.roughness for p in subset}
            properties.update(metallicFactor=0, roughnessFactor=first.roughness if len(roughnesses) == 1 else .65)
        if name == 'metal':
            hub = next(p for p in subset if p.wheel and p.obj.name.lower().startswith('hub'))
            properties.update(metallicFactor=hub.metallic, roughnessFactor=hub.roughness)
        if name == 'glass':
            properties.update(roughnessFactor=.20 if any(p.rgba[3]<1 for p in subset) else first.roughness)
        material = {'name': name, 'pbrMetallicRoughness': properties, 'doubleSided': True}
        if name == 'glass' and any(p.rgba[3]<1 for p in subset):
            material['alphaMode'] = 'BLEND'
        if name == 'light':
            material['emissiveFactor'] = [0.003, 0.003, 0.003]
        table[name] = material
    return table


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
        color = slot not in {'paint', 'tire'}
        vertices, indices, lookup = [], [], {}
        for part, mesh in sources:
            mesh.calc_loop_triangles()
            normals = mesh.corner_normals
            normal_transform = part.transform.to_3x3().inverted().transposed()
            for triangle in mesh.loop_triangles:
                if triangle.area < 1e-12:
                    continue
                for vi, li in zip(triangle.vertices, triangle.loops, strict=True):
                    position = (part.transform @ mesh.vertices[vi].co - center)*scale - pivot
                    normal = (normal_transform @ normals[li].vector).normalized()
                    vertex = y_up(position) + y_up(normal) + (part.rgba if color else ())
                    key = tuple(round(v, 7) for v in vertex)
                    if key not in lookup:
                        lookup[key] = len(vertices)
                        vertices.append(vertex)
                    indices.append(lookup[key])
        assert len(indices) % 3 == 0 and all(len(set(indices[i:i+3])) == 3 for i in range(0,len(indices),3))
        total += len(indices)//3
        primitives.append(glb.primitive(slot, vertices, indices, color))
    glb.add_node(name, pivot, primitives)
    return total


def build(vehicle):
    slug, source_file, length, budget = VEHICLES[vehicle]
    source = REPO/'models'/slug/'exports'/source_file
    objects = load(source)
    center, scale = fit(objects, length)
    paint = {'bus': 'Palm green', 'van': 'Delivery ivory', 'truck': 'Muted teal'}[vehicle]
    parts = [part_for(o, paint) for o in objects]
    assert sorted({p.wheel for p in parts if p.wheel}) == sorted(WHEELS)
    geometry_by_name = {p.obj.name: geometry(p, vehicle) for p in parts}
    materials = material_table(parts)
    glb = BinaryMesh(materials)
    totals = {}
    for name in ['body', *WHEELS]:
        subset = [p for p in parts if (p.wheel or 'body') == name]
        pivot = Vector()
        if name != 'body':
            tire, = [p for p in subset if p.slot == 'tire']
            pivot = (tire.obj.parent.matrix_world.translation-center)*scale
        totals[name] = emit_group(glb, name, subset, [geometry_by_name[p.obj.name] for p in subset],
                                  center, scale, pivot)
    triangles = sum(totals.values())
    path = OUT/f'{vehicle}_hd.glb'
    glb.write(path)
    print('BUILD', vehicle, totals, triangles, path.stat().st_size, materials.keys(), flush=True)
    assert triangles <= budget and path.stat().st_size <= 350_000, (vehicle, triangles, budget)


if __name__ == '__main__':
    import sys
    for key in sys.argv[sys.argv.index('--')+1:] or VEHICLES:
        build(key)
