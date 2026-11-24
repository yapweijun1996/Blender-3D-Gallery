"""Selat Pilot: countertop radio-controlled model-boat basin for a mall arcade.
Static water and boats, SI metres, common floor pivot, controls face -Y.
All boats, buoyage and lettering original. blender -b -P generate.py
"""
TITLE = 'Selat Pilot'
# Shared construction helpers, embedded to keep this generator standalone.
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

PI = math.pi
TAU = math.tau
PARTS = defaultdict(list)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0


def linear(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def mat(name, rgb, rough=0.47, metal=0.0, glow=0.0, alpha=1.0):
    color = tuple(linear(int(rgb[i:i + 2], 16) / 255) for i in (0, 2, 4))
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, alpha)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Alpha'].default_value = alpha
    if glow:
        bsdf.inputs['Emission Color'].default_value = (*color, 1)
        bsdf.inputs['Emission Strength'].default_value = glow
    if alpha < 1.0:
        material.surface_render_method = 'BLENDED'
    return material


def add(name, data, material, group):
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material)
    if group:
        PARTS[group].append(obj)
    return obj


def mesh(name, vertices, faces, material, bevel=0, group='Structure', smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = add(name, data, material, group)
    if smooth:
        for p in data.polygons:
            p.use_smooth = True
    if bevel:
        edge = obj.modifiers.new('Machined edge', 'BEVEL')
        edge.width = bevel
        edge.segments = 2
        edge.harden_normals = True
    return obj


def box(name, at, dims, material, bevel=0.012, group='Structure'):
    x, y, z = at
    a, b, c = (v * 0.5 for v in dims)
    vs = [(x + sx * a, y+sy*b, z+sz*c) for sz in (-1, 1)
          for sx, sy in [(-1, -1), (1, -1), (1, 1),(-1,1)]]
    return mesh(name, vs, [(3, 2, 1, 0), (4, 5,6,7),(0,1,5,4),(1,2,6,5),
                           (2, 3, 7, 6), (3, 0,4,7)], material, bevel, group)


def prism(name, outline, lo, hi, material, axis='Z', bevel=0, group='Structure'):
    # Outline is counterclockwise as viewed from the positive axis.
    n = len(outline)

    def xyz(u, v, w):
        return {'Z': (u, v, w), 'X': (w, u, v), 'NEG_Y': (u, -w,v)}[axis]
    vs = [xyz(u, v, w) for w in (lo, hi) for u, v in outline]
    fs = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    fs += [(i, (i + 1)%n, (i + 1)%n + n, i + n) for i in range(n)]
    return mesh(name, vs, fs, material, bevel, group)


def rounded(w, h, r, center=(0, 0), steps=5):
    cx, cy = center
    corners = [(w/2-r, h/2-r, 0), (-w/2+r, h/2-r, PI/2),
               (-w/2+r, -h/2+r, PI), (w/2-r, -h/2+r, 1.5*PI)]
    return [(cx + x + r *math.cos(a+t*PI/(2*steps)), cy+y+r*math.sin(a+t*PI/(2*steps)))
            for x, y, a in corners for t in range(steps + 1)]


def plaque(name, x, y, z, w, h, depth, radius, material, group='Graphics'):
    return prism(name, rounded(w, h, radius, (x, z)), -y -depth/2, -y+depth/2,
                 material, 'NEG_Y', min(depth * .23, .012), group)


def lathe(name, x, y, profile, material, sides=32, group='Structure', caps=True):
    # Profile runs from bottom to top on the outside, then back down any inside wall.
    vs = [(x + r * math.cos(TAU *i/sides), y+r*math.sin(TAU*i/sides), z)
          for r, z in profile for i in range(sides)]
    n = len(profile)
    fs = [tuple(reversed(range(sides))), tuple(range((n - 1) * sides, n * sides))] if caps else []
    for k in range(n - 1):
        for i in range(sides):
            j = (i + 1) % sides
            fs.append((k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i))
    obj = mesh(name, vs, fs, material, group=group, smooth=True)
    if caps:
        for face in list(obj.data.polygons)[:2]:
            face.use_smooth = False
    return obj


def tube(name, points, radius, material, group='Structure', sides=10, vertical_scale=1.0, reference=None):
    path = [Vector(p) for p in points]
    vs = []
    for i, p in enumerate(path):
        tangent = (path[min(i + 1, len(path) - 1)] - path[max(0, i - 1)]).normalized()
        ref = Vector(reference) if reference else (Vector((0, 0, 1)) if abs(tangent.z) < 0.97 else Vector((0, 1, 0)))
        u = tangent.cross(ref).normalized()
        v = tangent.cross(u)
        for j in range(sides):
            a = TAU * j / sides
            vs.append(p + radius * (u * math.cos(a) + v * math.sin(a) * vertical_scale))
    fs = [tuple(reversed(range(sides))), tuple(range(len(vs) - sides, len(vs)))]
    for k in range(len(path) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            fs.append((k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i))
    obj = mesh(name, vs, fs, material, group=group, smooth=True)
    for face in list(obj.data.polygons)[:2]:
        face.use_smooth = False
    return obj


def disc_front(name, x, y, z, r, depth, material, group='Graphics', sides=32):
    return prism(name, [(x + r * math.cos(TAU*i/sides), z+r*math.sin(TAU*i/sides))
                        for i in range(sides)], -y - depth / 2, -y +depth/2,
                 material, 'NEG_Y', min(depth * .2, .004), group)


def label(line, at, size, material, max_width=None, align='CENTER',
          group='Graphics', on_top=False, extrude=0.0):
    # Blender's built-in Bfont keeps lettering reproducible without an external font.
    data = bpy.data.curves.new(line, 'FONT')
    data.body = line
    data.align_x = align
    data.align_y = 'CENTER'
    data.size = size
    data.space_character = 1.05
    data.resolution_u = 5
    data.extrude = extrude
    obj = add(line, data, material, group)
    obj.location = at
    if not on_top:
        obj.rotation_euler.x = PI / 2
    if max_width:
        x_min = min(v[0] for v in obj.bound_box)
        x_max = max(v[0] for v in obj.bound_box)
        # bound_box may not be evaluated yet; constrain the final width in bake().
        if x_max > x_min:
            obj.scale.x = min(1.0, max_width / (x_max - x_min))
        obj['max_width'] = max_width
    return obj


def bake():
    # Flatten by semantic group; each group uses zero transforms at the same floor pivot.
    dg = bpy.context.evaluated_depsgraph_get()
    output = []
    for group, objects in PARTS.items():
        vs, fs, ids, uvs, normals, materials = [], [], [], [], [], []
        for obj in objects:
            state = obj.evaluated_get(dg)
            src = state.to_mesh()
            transform = state.matrix_world.copy()
            if 'max_width' in obj and len(src.vertices):
                xs = [v.co.x for v in src.vertices]
                width = (max(xs) - min(xs)) * transform.col[0].xyz.length
                if width > obj['max_width']:
                    for j in range(3):
                        transform[j][0] *= obj['max_width'] / width
            normal_matrix = transform.to_3x3().inverted_safe().transposed()
            offset = len(vs)
            points = [transform @ v.co for v in src.vertices]
            vs.extend(points)
            material = obj.data.materials[0]
            if material not in materials:
                materials.append(material)
            material_id = materials.index(material)
            src.calc_loop_triangles()
            src_normals = src.corner_normals
            for tri in src.loop_triangles:
                a, b, c = (points[k] for k in tri.vertices)
                normal = (b - a).cross(c - a)
                if normal.length_squared < 1.0e-17:
                    continue
                fs.append(tuple(offset + k for k in tri.vertices))
                ids.append(material_id)
                axis = max(range(3), key=lambda k: abs(normal[k]))
                i, j = ((1, 2), (0, 2), (0,1))[axis]
                flip = -1 if normal[axis] < 0 else 1
                uvs.extend((p[i] * flip, p[j]) for p in (a, b, c))
                normals.extend((normal_matrix @ src_normals[k].vector).normalized() for k in tri.loops)
            state.to_mesh_clear()
        # Discard vertices referenced only by degenerate conversion triangles.
        used = sorted({i for f in fs for i in f})
        index = {old: new for new, old in enumerate(used)}
        data = bpy.data.meshes.new(group)
        data.from_pydata([vs[i] for i in used], [], [tuple(index[i] for i in f) for f in fs])
        data.update()
        for material in materials:
            data.materials.append(material)
        data.polygons.foreach_set('material_index', ids)
        data.polygons.foreach_set('use_smooth', [True] * len(ids))
        uv_layer = data.uv_layers.new(name='UV0')
        uv_layer.uv.foreach_set('vector', [n for pair in uvs for n in pair])
        data.normals_split_custom_set(normals)
        obj = bpy.data.objects.new(f'{TITLE} - {group}', data)
        bpy.context.collection.objects.link(obj)
        output.append(obj)
    for objects in PARTS.values():
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    return output


def studio(direction, backdrop, margin=1.19, engine='BLENDER_EEVEE'):
    scene = bpy.context.scene
    coords = [v.co for o in scene.objects if o.type == 'MESH' for v in o.data.vertices]
    center = Vector([(max(v[i] for v in coords) + min(v[i] for v in coords)) / 2 for i in range(3)])
    span = max(max(v[i] for v in coords) - min(v[i] for v in coords) for i in range(3))
    arm = Vector(direction).normalized()
    rotation = (-arm).to_track_quat('-Z', 'Y')
    projection = [rotation.inverted() @ (v - center) for v in coords]
    lo = Vector([min(p[i] for p in projection) for i in range(3)])
    hi = Vector([max(p[i] for p in projection) for i in range(3)])
    target = center + rotation @ Vector(((hi.x + lo.x) / 2, (hi.y + lo.y) / 2, 0))
    camera = bpy.data.objects.new('Preview Camera', bpy.data.cameras.new('Orthographic Preview'))
    bpy.context.collection.objects.link(camera)
    camera.location = target + arm * span * 3
    camera.rotation_euler = rotation.to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(hi.x - lo.x, (hi.y - lo.y) * 1.25) * margin
    scene.camera = camera
    box('Preview Ground', (center.x, center.y, -0.035), (span *200, span*200, 0.06),
        mat('Studio Backdrop', backdrop, .82), 0, None)
    world = bpy.data.worlds.new('Studio Ambient')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.37, .43, .52, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .32

    def area(name, offset, watts, size, color):
        data = bpy.data.lights.new(name, 'AREA')
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = center + Vector(offset) * span
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
        data.energy = watts * span**2
        data.shape = 'DISK'
        data.size = size * span
        data.color = color
    area('Soft Warm Key', (-.65, -.95, 1.25), 143, 1.1,(1,.88,.73))
    area('Cool Front Fill', (.85, -.7, .58), 62, 1.1,(.75,.86,1))
    area('Overhead Rim', (.2, .9, 1.30), 186, .9,(1,.95,.86))
    scene.render.engine = engine
    if engine == 'CYCLES':
        scene.cycles.samples = 12
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.58
    scene.render.resolution_x = 900
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def deliver(direction, backdrop, margin=1.19, engine='CYCLES'):
    objs = bake()
    dest = Path(__file__).resolve().parent
    assert abs(min(v.co.z for o in objs for v in o.data.vertices)) < 1e-6
    objs[0]['asset_id'] = dest.name
    objs[0]['units'] = 'metre'
    objs[0]['role'] = 'Static visual mesh (no collider or clips)'
    flags = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    export = '--preview-only' not in flags
    print(f'{TITLE}: {sum(len(o.data.polygons) for o in objs):,} triangles')
    if export:
        bpy.ops.export_scene.gltf(filepath=str(dest / 'model.glb'), export_format='GLB',
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=18,
                                  export_draco_normal_quantization=12,
                                  export_draco_texcoord_quantization=16,
                                  export_cameras=False, export_lights=False,
                                  export_animations=False, export_extras=True)
        assert (dest / 'model.glb').stat().st_size <= 2_000_000
    if '--export-only' in flags:
        return
    scene = studio(direction, backdrop, margin, engine)
    scene.render.filepath = str(dest / 'preview.png')
    bpy.ops.render.render(write_still=True)


def band(x, y, z, w, h, lining, ink, line, size=None, group='Graphics'):
    plaque(line + ' | panel', x, y, z, w, h, .026, min(h * .34, .092), lining, group)
    label(line, (x, y - .015, z), size or h * .52, ink, w * .9, group=group)


def rail(name, a, b, radius, material, group='Structure', sides=12):
    return tube(name, [a, b], radius, material, group,sides)


def globe(name, xyz, radii, material, group='Fixtures', phase=0.0, sides=14, bands=8):
    x, y, z = xyz
    rx, ry, rz = radii
    co, si = math.cos(phase), math.sin(phase)
    points = [(x, y, z - rz)]
    for j in range(1, bands):
        t = -PI / 2 + PI * j / bands
        for i in range(sides):
            a = TAU * i / sides
            u, v = rx * math.cos(t) * math.cos(a), ry * math.cos(t) * math.sin(a)
            points.append((x + co * u - si * v, y + si * u + co * v, z + rz * math.sin(t)))
    points.append((x, y, z + rz))
    faces = []
    for i in range(sides):
        i1, j1 = i + 1, (i + 1) %sides + 1
        faces.append((0, j1, i1))
        for q in range(bands - 2):
            a, b = q * sides + i1, q * sides + j1
            faces.append((a, b, b + sides, a + sides))
        faces.append((i1 + (bands - 2) * sides, j1 + (bands - 2) * sides, len(points) - 1))
    return mesh(name, points, faces, material, group=group, smooth=True)


def deck(name, x, y, z, w, d,h,r,material,group='Structure'):
    return prism(name, rounded(w, d, r, (x, y)),z,z+h,material,bevel=min(.009,h/5),group=group)


def coin(x, y, z, steel, ink, accent):
    plaque('Token escutcheon', x, y, z, .16, .235,.024,.02,steel)
    plaque('Slot bezel', x, y-.015, z+.042, .092, .046,.012,.008,ink)
    box('Token throat', (x, y-.023, z+.042), (.064, .005,.007),accent,.001,'Fixtures')
    disc_front('Coin return', x, y-.017, z-.044, .025, .017,accent)
    for dx in [-.062, .062]:
        for dz in [-.095, .095]:
            disc_front('Countersunk screw', x+dx, y-.015, z+dz, .005, .004,ink,sides=8)


reset()
ink = mat('Port blue', '203d4b')
sea = mat('Basin turquoise', '43beb6', .22,.12)
mint = mat('Foam mint', 'a5e5ce')
red = mat('Vermilion','e66445')
cream=mat('Pilot house cream','ffe7b7')
brass=mat('Patinated brass','c69c57',.32,.48); wood=mat('Dock timber','ab704c'); stone=mat('Breakwater stone','606d6c'); light=mat('Beacon','ffe491',.25,0,.45)
deck('Recessed plinth', 0, 0, 0, 2.77,1.66,.10,.24,ink)
deck('Basin case', 0, 0, .085, 2.96,1.82,.65,.23,ink)
deck('Boot stripe', 0, 0, .62, 2.97,1.834,.05,.23,red)
deck('Quayside cap', 0, 0, .73,3.01,1.87,.085,.242,brass)
deck('Lagoon', 0, 0, .812,2.83,1.68,.027,.224,sea,'Harbour')
# Rounded coaming and small waves. The selected water graphic stays static.
pts = rounded(2.92, 1.78, .245)
tube('Safety coaming', [(x, y, .865) for x, y in pts+[pts[0]]],.046,wood,'Harbour',12,reference=(0,0,1))
for x, y in [(-1.08, .17), (.16, -.56), (.44,.43),(-.26,.51),(1.02,-.12)]:
    for j in range(2):
        tube('Wind ripple', [(x+i*.027, y+j*.038+.011*math.sin(i*.7), .840) for i in range(7-j*2)], .005,mint,'Harbour',6,reference=(0,0,1))
# Each harbour launch is built in its own coordinate system; transform about its keel.


def launch(cx, cy, heading, livery):
    group = 'Harbour launches'
    start = len(PARTS[group])
    z = .842
    profile = [(-.28, .096), (-.18, .109), (.10,.111),(.24,.073),(.31,.012)]
    vs = [(x, w*s*t, z+h) for h, t in [(0, .77),(.069,1)] for x,w in profile for s in [-1,1]]
    fs = [(i, i+2, i+12, i+10) for i in range(0, 8,2)]+[(i+10,i+12,i+2,i) for i in range(1,9,2)]+[(10+i,12+i,13+i,11+i) for i in range(0,8,2)]+[(0,10,11,1),(8,9,19,18)]
    mesh('Launch hull', vs, fs, livery, .003,group)
    box('Coach house', (-.037, 0, .945), (.24,.15,.084),cream,.014,group)
    for s in [-1, 1]:
        for x in [-.098, -.02, .052]:
            box('Wheelhouse window', (x, s*.076, .955), (.053,.003,.041),ink,.004,group)
    deck('Cab roof', -.037, 0, .98,.264,.18,.019,.037,ink,group)
    lathe('Funnel', -.194, 0, [(.026,.911),(.024,.976),(.027,.983)],brass,16,group)
    for o in PARTS[group][start:]:
        o.location = (cx, cy, 0)
        o.rotation_euler.z = heading
launch(-.58, -.28, -.30, red)
launch(.58, .15, 2.75, ink)
# Granite islet and a striped straits harbour light.
for x, y, rx in [(-.85, .46, .23),(-1.01,.43,.125),(-.73,.38,.15)]:
    globe('Granite skerry', (x, y, .854), (rx,rx*.73,.096),stone,'Harbour',sides=9,bands=5)
x, y = -.86, .46
lathe('Lighthouse', x, y, [(.103, .90),(.105,.955),(.08,.964),(.059,1.33),(.089,1.336),(.088,1.357)],cream,28,'Harbour')
lathe('Daymark band', x, y, [(.075,1.064),(.07,1.16)],red,28,'Harbour')
lathe('Lantern glass', x, y,[(.055,1.36),(.055,1.433)],light,20,'Harbour')
lathe('Lantern cap', x, y,[(.076,1.43),(.015,1.49)],ink,24,'Harbour')
for x, y in [(-1.1, -.31), (.03, .28),(1.03,.4)]:
    lathe('Channel marker', x, y, [(.055, .839),(.054,.859),(.033,.875),(.020,.95),(.009,.967)],red,16,'Harbour')
for x in [-.86, .86]:
    deck('Control binnacle', x, -.892, .65, .61,.32,.185,.07,wood)
    deck('Pilot dial panel', x, -.90, .832, .54,.27,.016,.055,ink)
    for dx in [-.12, .12]:
        lathe('Joystick gate', x+dx, -.914, [(.059, .849),(.043,.868),(.032,.874)],brass,24,'Controls')
        rail('Pilot stick', (x+dx, -.914, .868),(x+dx,-.93,.955),.014,ink,'Controls')
        globe('Stick knob', (x+dx, -.93,.962),(.030,.030,.028),red if dx < 0 else mint,'Controls')
    coin(x, -.914, .395, brass, ink, red)
band(0, -.922, .371, 1.15, .45,cream,ink,'SELAT PILOT',.163)
label('R A D I O    M A R I N A', (0, -.943, .234), .055,ink)
for s in [-1, 1]:
    for i in range(3):
        disc_front('Vent port', s*(1.06+.079*i), -.913, .34, .024,.008,mint)
deliver((2.5, -5.1, 3.72), '7a9291', 1.13)
