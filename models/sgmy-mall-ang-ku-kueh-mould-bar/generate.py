"""Kura Merah: Straits ang ku kueh moulding and tasting bar. Scale in metres.
Static original stall; front -Y, origin on floor. Modelled cakes and carved
paddles, no textures or external files. blender -b -P generate.py
"""
TITLE = 'Kura Merah'
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


def line_front(name, xz, y, radius, material, group='Graphics'):
    return tube(name, [(x, y, z) for x, z in xz], radius, material, group, sides=8)


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


def framed(x, y, z, w, h, rim, inner, title, detail, ink, accent):
    plaque(title+' | frame', x, y, z, w, h, .068,.059,rim)
    plaque(title+' | print', x, y-.036, z, w-.07, h-.07, .012,.037,inner)
    label(title, (x, y-.044, z+h*.19), h*.21, ink,w*.83)
    box(title+' | rule', (x, y-.045, z+h*.02), (w*.7, .004,.009),accent,.001,'Graphics')
    label(detail, (x, y-.044, z-h*.16), h*.113, ink,w*.81)


def rail(name, a, b, radius, material, group='Structure', sides=12):
    return tube(name, [a, b], radius, material, group,sides)


def patch(name, outline, y, material, group='Graphics'):
    return prism(name, outline, -y-.002, -y+.002, material, 'NEG_Y',group=group)


def diamond(name, x, y, z, w, h,material):
    return patch(name, [(x+w/2, z), (x, z+h/2), (x-w/2,z),(x,z-h/2)],y,material)


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


def rotated_box(name, center, dims, angle, material, group='Fixtures', bevel=.011):
    o = box(name, (0, 0, 0), dims, material,bevel,group)
    o.location = center
    o.rotation_euler.z = angle
    return o


def deck(name, x, y, z, w, d,h,r,material,group='Structure'):
    return prism(name, rounded(w, d, r, (x, y)),z,z+h,material,bevel=min(.009,h/5),group=group)


reset()
red = mat('Ox blood lacquer', 'a9423d', .31)
coral = mat('Vermilion glutinous rice', 'e4583e', .33)
ridge = mat('Raised rice paste', 'f5774c',.36)
green = mat('Banana leaf','42765a')
stone=mat('Almond quartz','ebd8b3')
jade=mat('Celadon pottery','9bbf9f'); wood=mat('Oiled pearwood','b97645'); cut=mat('Carved recess','864c31'); brass=mat('Warm brass','d6ac69',.32,.5); ink=mat('Deep forest enamel','2e4944')
# Cabinet and graphic: tiled field with a deliberately generous blank border.
deck('Kick', 0, 0, 0, 2.16,.91,.09,.08,ink)
deck('Lacquer cabinet', 0, 0, .085, 2.32,1.02,.76,.102,red)
for i in range(9):
    for j in range(2):
        x = (i - 4) * .231
        z = .287 + j * .292
        plaque('Biscuit tile', x, -.513, z, .223,.281,.012,.015,stone,'Tile frieze')
        diamond('Celadon lozenge', x, -.522, z,.173,.233,jade)
        diamond('Rosette', x, -.527, z,.063,.089,stone)
band(0, -.544, .446, 1.08, .313, ink,stone,'K U R A   M E R A H',.094)
deck('Counter shadow', 0, 0, .84, 2.40,1.09,.054,.115,brass)
deck('Stone counter', 0, 0, .889, 2.44,1.12,.073,.115,stone)
# Individual mould paddles hang from turned pegs on the mantel-like backing.
plaque('Display reredos', -.34, .429, 1.43, 1.49,.988,.096,.144,ink)
plaque('Heather panel', -.34, .374, 1.42, 1.405,.893,.016,.112,jade)
label('ANG KU KUEH', (-.34, .359, 1.744), .153,ink,1.25)
label('M O U L D   A T E L I E R', (-.34, .359, 1.612), .051,ink)
for i in range(3):
    x = -.78 + .44 * i
    rail('Paddle hook', (x, .373, 1.521), (x,.254,1.521),.015,brass)
    plaque('Mould handle', x, .277, 1.449,.069,.193,.042,.03,wood,'Moulds')
    disc_front('Peg head', x, .25, 1.523,.025,.028,brass)
    plaque('Pearwood block', x, .276, 1.235, .256, .31,.066,.075,wood,'Moulds')
    globe('Tortoise-shell cavity', (x, .241, 1.231), (.090, .010,.116),cut,'Moulds',sides=28,bands=12)
    # Hexagonal centre and short radial cuts read as a traditional shell stamp.
    circ = [(x +.039 *math.cos(TAU *k /6), 1.231 +.061 *math.sin(TAU *k /6)) for k in range(6)]
    line_front('Carved hexagon', circ+[circ[0]], .228, .005,wood,'Moulds')
    for X, Z in circ:
        line_front('Radial carving', [(X, Z), (x+(X-x)*1.9, 1.231+(Z-1.231)*1.61)],.229,.005,wood,'Moulds')
# Tiered trays of glossy, domed, leaf-backed tortoise cakes.
for row in range(2):
    y = -.327 + row * .319
    z = .963 + .069 * row
    if row:
        deck('Riser', -.254, y, .962, 1.48,.227,.071,.04,wood)
    deck('Display tray', -.254, y, z, 1.56,.31,.028,.047,ink,'Tasting trays')
    for j in range(6):
        x = -.877 + j * .249
        base = z + .031
        rotated_box('Banana leaf', (x, y, base), (.189, .24,.009),-.055+j*.017,green,'Tasting trays',.004)
        globe('Tortoise cake', (x, y, base+.024), (.079, .101,.039),coral,'Tasting trays',sides=20,bands=10)
        pts = [(x +.031 *math.cos(TAU *k /6), y +.047 *math.sin(TAU *k /6), base +.060) for k in range(7)]
        tube('Shell impression', pts, .004, ridge, 'Tasting trays',6,reference=(0,0,1))
        for X, Y, Z in pts[:6]:
            rail('Radial impression', (X, Y, Z), (x+(X-x)*2.01,y+(Y-y)*1.84,Z-.015),.003,ridge,'Tasting trays',6)
# Flour bowl, tamping pestle and classification card occupy the work end.
lathe('Flour bowl', .855, -.118, [(.097, .962),(.103,.974),(.136,.989),(.18,1.104),(.182,1.115),(.17,1.119),(.155,1.087),(.114,1.011)],jade,40,'Work board')
globe('Rice flour', (.855, -.118, 1.069),(.144,.144,.035),stone,'Work board')
rail('Tamping tool', (.83, -.12, 1.083),(.957,-.067,1.308),.026,wood,'Work board')
box('Notice foot', (.848, .333, 1.015), (.217,.196,.108),wood,.016)
framed(.848, .331, 1.226, .519, .307,wood,red,'KACANG','TORTOISE CAKE',stone,brass)
deliver((2.17, -5.35, 2.77), '90928a', 1.13)
