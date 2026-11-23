"""Build static, metre-scale versions of the published gallery assets."""
import importlib.util
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

KIT = Path(__file__).resolve().parent
ROOT = KIT.parents[2]
MODELS = {
    'hdb-block': ('hdb_block', 2200, 'GROUND'),
    'hdb-void-deck': ('hdb_void_deck', 2500, 'GROUND_Slab'),
    'hdb-coffee-shop-frontage': ('hdb_coffee_shop', 1800, 'FLOOR_Sill'),
    'hdb-neighbourhood-shopfront': ('provision_shop', 1200, 'THRESHOLD'),
    'shoplot-building': ('shoplot', 1800, 'Base'),
    'public-market': ('public_market', 3000, 'Market_Slab'),
    'mrt-station-entrance': ('mrt_entrance', 2000, 'Landing'),
}
PALETTES = {
    'hdb-block': {'Ivory': 'wall', 'Steel': 'metal', 'Transit blue': 'paint',
                  'Warm timber': 'trim', 'Glazing blue-grey': 'window'},
    'hdb-void-deck': {'Ivory': 'wall', 'Steel': 'metal', 'Transit blue': 'paint'},
    'hdb-coffee-shop-frontage': {'Cream frontage plaster': 'wall', 'Kopitiam green trim': 'paint',
                                'Stainless counter': 'metal', 'Dark support and cup': 'trim',
                                'Pale canvas awning': 'roof'},
    'hdb-neighbourhood-shopfront': {'Cream perimeter piers': 'wall', 'Clear blue display glazing': 'glass',
                                   'Muted blue-green shop frames': 'paint', 'Black door handle': 'trim',
                                   'Blank replaceable sign face': 'plate'},
    'shoplot-building': {'Warm concrete': 'concrete', 'White': 'wall',
                         'Muted teal': 'window', 'Satin metal': 'metal'},
    'public-market': {'Warm concrete': 'concrete', 'White': 'wall', 'Satin metal': 'metal',
                      'Terracotta': 'roof', 'Palm green': 'plate'},
    'mrt-station-entrance': {'Warm concrete': 'concrete', 'Satin steel': 'metal',
                            'Warm white': 'roof', 'Muted teal': 'paint'},
}
ROLES = {
    'hdb-block': {'GROUND': 'concrete', 'ROOF_Service': 'roof', 'EDITABLE_BlockNumber': 'plate'},
    'hdb-void-deck': {'GROUND_Slab': 'concrete', 'CEILING_Light': 'light'},
    'hdb-coffee-shop-frontage': {'FASCIA_ReplaceableFace': 'plate', 'FLOOR_Sill': 'concrete'},
    'hdb-neighbourhood-shopfront': {'CANOPY': 'roof', 'THRESHOLD': 'concrete'},
    'shoplot-building': {'Modern_Awning': 'roof'},
    'public-market': {'Editable_Label_PUBLIC_MARKET': 'light'},
    'mrt-station-entrance': {'Replaceable_Station_Label': 'plate'},
}
SHARP = {
    'hdb-void-deck': ('STAIR_Step', 'TRANSFER_Beam', 'SERVICE_RiserDoor', 'CEILING_Light'),
    'hdb-coffee-shop-frontage': ('COUNTER_Side', 'COUNTER_Front', 'FASCIA_Support',
                                'FASCIA_ReplaceableFace'),
    'hdb-neighbourhood-shopfront': ('FRAME_', 'DOOR_Glass', 'DOOR_Rail_'),
    'shoplot-building': ('Party_Wall', 'Rear_Wall', 'Upper_Front_Wall', 'Flat_Slab'),
    'public-market': ('Open_Bay_Column', 'Fixed_Stall_Counter', 'Stall_Worktop', 'Market_Header'),
    'mrt-station-entrance': ('Rail_Post', 'Infill', 'Replaceable_Station_Label'),
}
BOX_FACES = [(0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)]


def original(slug):
    return next((ROOT / 'models' / slug / 'exports').glob('*.glb'))


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()


def box_vertices(low, high):
    x, y, z = low
    a, b, c = high
    return [(x,y,z), (a,y,z), (a,b,z), (x,b,z),
            (x,y,c), (a,y,c), (a,b,c), (x,b,c)]


def local_bounds(obj):
    return [Vector(point) for point in (obj.bound_box[0], obj.bound_box[6])]


def block_geometry():
    # Reuse exact procedural component dimensions before microscopic bevels.
    sys.dont_write_bytecode = True
    path = ROOT / 'models/hdb-block/generate.py'
    spec = importlib.util.spec_from_file_location('gallery_block', path)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    boxes = []
    generator.box = lambda name, loc, dims, mat, parent, bevel=0: (
        boxes.append((name, Vector(loc), Vector(dims), mat)))
    generator.combined = lambda *_: None
    generator.build(generator.empty(generator.ROOT))
    stacked = defaultdict(list)
    for name, center, size, material in boxes:
        if name in {'UNIT_Wall', 'REAR_Wall', 'END_Wall'}:
            stacked[name, center.x, center.y].append((name, center, size, material))
            continue
        faces = BOX_FACES
        if name == 'UNIT_Door':
            faces = [face for i, face in enumerate(faces) if i != 4]
        if name == 'REAR_Window':
            faces = [face for i, face in enumerate(faces) if i != 2]
        yield name, box_vertices(center-size/2, center+size/2), faces, material
    for segments in stacked.values():
        name, center, size, material = segments[0]
        low = center-size/2
        high = segments[-1][1]+size/2
        yield name, box_vertices(low, high), BOX_FACES, material
    label = bpy.data.objects['EDITABLE_BlockNumber']
    label.data.extrude = 0
    bpy.context.view_layer.update()
    yield from source_faces(label, label.matrix_world)


def source_faces(obj, transform, support_z=None):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    points = [transform @ vertex.co for vertex in mesh.vertices]
    if support_z is not None:
        low, high = min(v.z for v in points), max(v.z for v in points)
        for point in points:
            if point.z < (low+high)/2:
                point.z += support_z-low
    by_material = defaultdict(list)
    for triangle in mesh.loop_triangles:
        by_material[triangle.material_index].append(tuple(triangle.vertices))
    for index, faces in by_material.items():
        yield obj.name, points, faces, mesh.materials[index]
    evaluated.to_mesh_clear()


def sloped_slab(name, low, high, material):
    # Walk-in slopes at both frontage edges fit inside the existing slab footprint.
    x0, y0, z0 = low
    x1, y1, z1 = high
    run = (z1-z0)*8
    section = [(y0,z0), (y1,z0), (y1-run,z1), (y0+run,z1)]
    vertices = [(x,y,z) for x in (x0,x1) for y,z in section]
    faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return name, vertices, faces, material


def support_bottom(slug, name, y):
    # Embed the feet where an approach cut lowers the surrounding slab surface.
    if slug == 'hdb-void-deck' and name.startswith('COLUMN'):
        return .01
    if slug == 'public-market':
        if name.startswith('Open_Bay_Column') and abs(y) > 8:
            return .06
        if name.startswith('Fixed_Stall_Counter') and abs(y) > 5:
            return .22
    if slug in {'hdb-coffee-shop-frontage', 'hdb-neighbourhood-shopfront'} and name.startswith('PIER_'):
        return .008
    if slug == 'hdb-coffee-shop-frontage' and name.startswith(('COUNTER_Front', 'COUNTER_Side')):
        return .026
    if slug == 'hdb-neighbourhood-shopfront' and name.startswith('FRAME_Jamb_'):
        return .016
    return None


def export_geometry(slug, parts):
    for obj in parts:
        name = obj.name
        transform = obj.matrix_world.copy()
        low, high = local_bounds(obj)
        if slug == 'hdb-neighbourhood-shopfront':
            if name.startswith('DOOR_'):
                # Open the authored leaf inward on its original hinge.
                pivot = Vector((1.69,-.02,.08))
                transform = Matrix.Translation(pivot) @ Matrix.Rotation(-math.pi/2, 4, 'Z') @ Matrix.Translation(-pivot) @ transform
            elif name == 'FRAME_Jamb_0.45':
                transform.translation.x -= .34
            elif name.startswith(('FRAME_Rail_', 'DISPLAY_Glass')):
                high.x -= .34
        support_z = support_bottom(slug, name, transform.translation.y)
        if name == MODELS[slug][2] and slug in {'hdb-void-deck', 'public-market',
                                               'hdb-coffee-shop-frontage', 'hdb-neighbourhood-shopfront'}:
            low, high = transform @ low, transform @ high
            if slug == 'hdb-coffee-shop-frontage':
                high.y = 3.4
            if slug == 'hdb-neighbourhood-shopfront':
                high.y = 2.6
            yield sloped_slab(name, low, high, obj.data.materials[0])
        elif name.startswith(SHARP[slug]) or name == 'DISPLAY_Glass':
            vertices = [transform @ Vector(v) for v in box_vertices(low, high)]
            if support_z is not None:
                for point in vertices[:4]:
                    point.z = support_z
            yield name, vertices, BOX_FACES, obj.data.materials[0]
        else:
            yield from source_faces(obj, transform, support_z)


def add_box(name, center, size, material):
    center, size = Vector(center), Vector(size)
    return name, box_vertices(center-size/2, center+size/2), BOX_FACES, material


def add_cylinder(name, center, radius, depth, material, sides=12):
    x,y,z = center
    vertices = [(x+radius*math.cos(i*math.tau/sides), y+radius*math.sin(i*math.tau/sides), z+dz)
                for dz in (-depth/2, depth/2) for i in range(sides)]
    faces = [tuple(reversed(range(sides))), tuple(range(sides,2*sides))]
    faces += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
    return name, vertices, faces, material


def additions(slug):
    materials = bpy.data.materials
    if slug == 'hdb-void-deck':
        metal, paint, wall = (materials[name] for name in ('Steel', 'Transit blue', 'Ivory'))
        yield add_box('Mailbox_Body', (-3,1.94,1.19), (1.02,.23,.50), metal)
        for i in range(4):
            for j in range(2):
                x,z = -3.37+i*.245, 1.065+j*.245
                yield add_box('Mailbox_Door', (x,1.813,z), (.226,.033,.218), paint)
                yield add_box('Mailbox_Slot', (x,1.793,z+.038), (.128,.009,.018), wall)
        yield add_box('Notice_Board', (-3,1.985,1.89), (1.0,.09,.53), paint)
        yield add_box('Notice_Surface', (-3,1.935,1.89), (.92,.015,.45), wall)
        for x,z,w,h in [(-3.22,1.90,.21,.30), (-2.90,1.94,.25,.22), (-2.73,1.78,.15,.11)]:
            yield add_box('Notice_Pinup', (x,1.925,z), (w,.007,h), metal)
    if slug == 'hdb-coffee-shop-frontage':
        paint, metal, roof = (materials[name] for name in ('Kopitiam green trim', 'Stainless counter', 'Pale canvas awning'))
        for x in (-2.00,-.12):
            y = 1.66
            yield add_cylinder('Table_Top', (x,y,.84), .37,.06,roof)
            yield add_cylinder('Table_Post', (x,y,.455), .055,.71,metal,8)
            yield add_cylinder('Table_Foot', (x,y,.13), .22,.06,metal,10)
            for sy in (.99,2.33):
                yield add_cylinder('Stool_Seat', (x,sy,.54), .165,.055,paint,10)
                for dx,dy in [(-.073,-.070),(.073,-.070),(0,.085)]:
                    yield add_box('Stool_Leg', (x+dx,sy+dy,.307), (.034,.034,.414),metal)
    if slug == 'hdb-neighbourhood-shopfront':
        frame, wall, sign = (materials[name] for name in ('Muted blue-green shop frames', 'Cream perimeter piers', 'Blank replaceable sign face'))
        yield add_box('Counter_Body', (-.95,.80,.50), (1.48,.52,.84),wall)
        yield add_box('Counter_Front_Panel', (-.95,.535,.525), (1.36,.025,.66),frame)
        yield add_box('Counter_Top', (-.95,.80,.95), (1.58,.63,.07),sign)


def combine(slug, geometry, origin):
    points, faces, face_materials = [], [], []
    materials = {}
    for name, vertices, polygons, source in geometry:
        role = ROLES[slug].get(name.split('.')[0], PALETTES[slug][source.name.split('.')[0]])
        if role not in materials:
            materials[role] = source.copy()
        material = materials[role]
        used = sorted({i for face in polygons for i in face})
        mapping = {i: len(points)+j for j,i in enumerate(used)}
        points.extend(Vector(vertices[i])-origin for i in used)
        faces.extend(tuple(mapping[i] for i in face) for face in polygons)
        face_materials.extend([material] * len(polygons))
    for role, material in materials.items():
        material.name = role
    mesh = bpy.data.meshes.new(slug)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    for material in materials.values():
        mesh.materials.append(material)
    for polygon, material in zip(mesh.polygons, face_materials):
        polygon.material_index = mesh.materials.find(material.name)
    mesh.calc_loop_triangles()
    return mesh


def build(slug):
    stem, budget, base_name = MODELS[slug]
    load(original(slug))
    parts = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    ground = [bpy.data.objects[base_name]]
    if slug == 'mrt-station-entrance':
        ground += [obj for obj in parts if obj.name.startswith('Step_')]
    bounds = [obj.matrix_world @ Vector(v) for obj in ground for v in obj.bound_box]
    low = Vector([min(v[i] for v in bounds) for i in range(3)])
    high = Vector([max(v[i] for v in bounds) for i in range(3)])
    origin = (low+high)/2
    origin.z = low.z
    if slug == 'hdb-coffee-shop-frontage':
        origin.y = (low.y+3.4)/2
    if slug == 'hdb-neighbourhood-shopfront':
        origin.y = (low.y+2.6)/2
    if slug == 'hdb-block':
        for obj in list(bpy.context.scene.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for material in list(bpy.data.materials):
            bpy.data.materials.remove(material)
        geometry = list(block_geometry())
    else:
        geometry = list(export_geometry(slug, parts))
        geometry.extend(additions(slug))
    mesh = combine(slug, geometry, origin)
    triangles = len(mesh.loop_triangles)
    print(f'KIT {stem} triangles={triangles} origin={tuple(origin)}', flush=True)
    if triangles > budget:
        raise ValueError(f'{stem}: {triangles} triangles exceeds {budget}')
    for obj in list(bpy.context.scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    result = bpy.data.objects.new(stem, mesh)
    bpy.context.collection.objects.link(result)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1
    bpy.ops.export_scene.gltf(filepath=str(KIT / f'{stem}.glb'), export_format='GLB',
                              export_yup=True, export_animations=False, export_skins=False,
                              export_cameras=False, export_lights=False, export_texcoords=False,
                              export_extras=False)


if __name__ == '__main__':
    for slug in sys.argv[sys.argv.index('--')+1:] or MODELS:
        build(slug)
