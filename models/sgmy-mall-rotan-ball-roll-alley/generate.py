"""Liga Rotan: rattan-ball roll-up alley for a Straits arcade. Fixed scenic
machine with a ramp, scoring collars, guards and return. Metres; player at
-Y, common floor origin. Original graphics. blender -b -P generate.py
"""
TITLE = 'Liga Rotan'
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


def bar(name, a, b, width, depth, material, group='Structure', bevel=.006):
    a, b = Vector(a), Vector(b)
    obj = box(name, (0, 0, 0), (width, depth,(b-a).length),material,bevel,group)
    obj.location = (a + b) / 2
    obj.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    return obj


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
ink = mat('Indigo laminate', '24364b')
blue = mat('Peacock blue', '23717c')
red = mat('Cinnabar', 'da6244')
cane = mat('Bamboo maple','d49d64')
gold=mat('Cane highlight','e4b16b')
seam=mat('Rattan seams','845726'); mint=mat('Mint paint','a7d9bc'); glow=mat('Score segments','ffc663',.32,0,.55); hole=mat('Scoring pockets','1f3239')
# The lane rises gradually and then curls up towards a tilted target face.
profile = [(-1.51, .55), (-1.30, .559), (-.60,.59),(-.02,.62),(.30,.662),(.46,.735),(.598,.852),(.683,.973)]
outline = [(-1.51, .08), (1.49, .08),(1.49,1.943),(1.445,1.943),(.709,.903),(.683,.973)]+list(reversed(profile[:-1]))
prism('Lane cabinet', outline, -.509, .509, blue,'X',.018)
for x in [-.436, .436]:
    for y in [-1.29, 1.25]:
        deck('Adjustable foot', x, y, 0, .196,.245,.093,.036,ink)
for i in range(7):
    x = -.447 + i * .128
    vs = [(u, y, z+.012) for u in [x,x+.126] for y,z in profile]
    n = len(profile)
    mesh('Maple lane board', vs, [(k, n+k, n+k+1, k+1) for k in range(n-1)],cane if i not in [0,6] else gold,group='Lane')
for x in [-.507, .507]:
    rim = profile +[(y, z +.108) for y, z in reversed(profile)]
    prism('Raised bumper', rim, x-.036, x+.036,ink,'X',.012,'Lane')
    tube('Bright cushion stripe', [(x, y, z+.109) for y,z in profile],.015,mint,'Lane',10,reference=(1,0,0))
    for i in range(4):
        y = -1.13 + i * .115
        bar('Side lane chevron', (x*1.078, y, .25), (x*1.078,y+.096,.411),.016,.04,gold,'Lane')
# Return hopper is recessed into the front apron; show the plaited balls.
plaque('Return opening', -.095, -1.52, .344, .706,.244,.027,.089,hole)
deck('Return cradle', -.094, -1.55, .219, .754,.291,.049,.047,ink)


def woven_ball(x, y, z, r):
    globe('Rattan ball', (x, y, z), (r, r,r),gold,'Balls',sides=24,bands=12)
    # Three sets of offset great-circle seams form the interlaced panels.
    for k in range(3):
        a = k * PI / 3
        u = Vector((math.cos(a), math.sin(a), 0))
        v = Vector((-.46*math.sin(a), .46*math.cos(a),.888)).normalized()
        normal = u.cross(v)
        for dx in [-.14, .14]:
            pts = [Vector((x, y, z)) + r * (.991 * (u * math.cos(TAU * i / 28) + v * math.sin(TAU * i / 28)) + normal * dx) for i in range(29)]
            tube('Woven seam', pts, r*.021, seam, 'Balls', 6,reference=normal)


for j in range(3):
    woven_ball(-.296 +.183 *j, -1.536, .337, .088)
woven_ball(.029, -.882, .67, .079)
coin(.372, -1.522, .341, gold,ink,red)
# Target board coordinates: v up the bank, n towards the player.
base = Vector((0, .708, .910))
up = Vector((0, .58, .815)).normalized()
out = Vector((0, -up.z,up.y))
side = Vector((1, 0,0))
def board(x, v, n): return base + x * side + v * up + n * out
mesh('Banked target', [board(-.485, 0, 0), board(.485, 0, 0),board(.485,1.29,0),board(-.485,1.29,0)],[(0,1,2,3)],cane,group='Target')
for x, v, r, value, c in [(0, .367,.237,'10',mint),(-.218,.809,.153,'20',red),(.218,.809,.153,'30',blue),(0,1.112,.117,'50',red)]:
    pts = [board(x +r *math.cos(TAU *i /40), v +r *math.sin(TAU *i /40), .009) for i in range(40)]
    mesh('Scoring well', pts, [tuple(range(40))], hole, group='Target')
    vs = [board(x+r*math.cos(TAU*i/40), v+r*math.sin(TAU*i/40), h) for h in [.008, .060] for i in range(40)]
    mesh('Raised scoring collar', vs, [(i, (i+1)%40,(i+1)%40+40,i+40) for i in range(40)],c,group='Target')
    tube('Welt', [q+.054*out for q in pts+[pts[0]]], .009, gold,'Target',8,reference=out)
    o = label(value, board(x, v, .014),r*.73,gold)
    o.rotation_euler.x = math.atan2(up.z, up.y)
# Side guards and backboard with lit scores, inspired by a takraw league scoreboard.
for x in [-.505, .505]:
    for y, z in [(.54, 1.492), (1.48, 2.30)]:
        rail('Guard post', (x, y, .85 if y < 1 else 1.42),(x,y,z),.023,ink,'Guard')
    rail('Guard coping', (x, .54, 1.492), (x,1.48,2.30),.026,red,'Guard')
    rail('Lower guard chord', (x, .54, .85), (x, 1.48,1.94),.018,ink,'Guard')
    for j in range(1, 9):
        t = j / 9
        y = .54 + .94 * t
        rail('Safety grille', (x, y, .85+1.09*t),(x,y,1.492+.808*t),.007,ink,'Guard',8)
plaque('Backboard', 0, 1.478, 2.03, 1.09,.779,.118,.111,ink)
plaque('Header', 0, 1.41, 2.349, 1.19,.27,.080,.125,red)
label('L I G A   R O T A N', (0, 1.361, 2.349), .101,gold,1)
label('0 1 2 0', (0, 1.411, 2.105), .119,glow,.528)
for s in [-1, 1]:
    # Long tapered, ascending stripes echo the kick of the playing lane.
    for dz, col in [(0, mint), (.128, gold)]:
        fin = [(-.56, .223+dz), (.47, .287+dz), (1.46,.57+dz),(1.46,.669+dz),(.45,.337+dz)]
        prism('Swept flank inlay', fin, s*.512-.002, s*.512+.002, col, 'X',group='Graphics')
band(0, -1.519, .489, .744, .098, ink,gold,'G E L A N G G A N G    /    0 3',.043)
deliver((2.97, -5.25, 3.38), '858c8e', 1.13)
