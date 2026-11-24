"""Bayang Bulan: a Kelantan shadow-play viewing cabinet with two puppet controls.
Metre-scale static arcade prop, control side -Y, common floor pivot. The
puppets are original relief silhouettes; no animation. blender -b -P generate.py
"""
TITLE = 'Bayang Bulan'
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


def stripes(name, x, y, z, count, pitch,height,material):
    for i in range(count):
        box(name, (x+pitch*(i-(count-1)/2), y, z), (pitch*.46, .023,height),material,.006,'Joinery')


reset()
coal = mat('Shadow ink', '292a32')
green = mat('Petrol enamel', '245557')
rose = mat('Pomegranate', 'a94244')
brass = mat('Gilded trim','dda756',.35,.44)
amber=mat('Amber silk screen','ffcc7b',.8,0,.39)
rust=mat('Sepia leather','77443b'); cream=mat('Clotted cream','ffe8b6'); oak=mat('Stained meranti','694335')
deck('Shoe', 0, 0, 0, 1.36,.75,.096,.08,coal)
deck('Gilt shoe moulding', 0, 0, .091,1.40,.78,.039,.08,brass)
deck('Cabinet', 0, 0, .128,1.34,.724,1.71,.06,green)
stripes('Ribbed front', 0, -.365, .47, 25, .049,.590,oak)
plaque('Coin surround', 0, -.385, .50, .373,.477,.039,.126,green)
coin(0, -.418, .52, brass, coal,rose)
# Stepped proscenium with a luminous, shallow-set screen and side brocade panels.
plaque('Carved frame', 0, -.369, 1.404, 1.28,.82,.085,.078,oak)
plaque('Gilt liner', 0, -.415, 1.405,1.18,.73,.018,.055,brass)
plaque('Lit silk', 0, -.429, 1.405,1.111,.659,.015,.04,amber)
# Draw a pair of original long-nosed leather figures, facing across the stage.


def player(cx, scale, mirror, offset, color):
    cy = -.442 - offset
    ground = 1.102
    def p(x, z): return (cx + mirror * x * scale, ground + z * scale)

    def cut(name, shape, c):
        shape = [p(x, z) for x, z in shape]
        patch(name, shape if mirror == 1 else shape[::-1], cy, c,'Shadow theatre')
    cut('Carved leather figure', [(-.132, 0), (-.108, .065), (-.08,.119),(-.092,.211),(-.061,.278),(-.071,.302),(-.115,.351),(-.098,.387),(-.128,.448),(-.079,.415),(-.088,.486),(-.047,.451),(-.025,.514),(.006,.451),(.055,.469),(.049,.413),(.073,.393),(.074,.371),(.161,.318),(.079,.332),(.092,.296),(.056,.283),(.025,.289),(.009,.261),(.039,.242),(.078,.204),(.054,.167),(.047,.113),(.12,.042),(.149,.015),(.098,.013),(.022,.04),(-.02,.067),(-.041,.031),(-.003,.013),(-.009,0)],color)
    def rod(name, points, r, c, behind=0): line_front(name, [p(x,z) for x,z in points],cy-.006+behind,r*scale,c,'Shadow theatre')
    rod('Jointed arm', [(.023, .241), (.121, .149),(.184,.224),(.207,.224)],.012,color)
    rod('Arm wand', [(.184, .224), (.214, .0)],.0035,coal)
    for x, z in [(.022, .241), (.121, .149), (.049,.371)]:
        X, Z = p(x, z)
        disc_front('Pierced leather', X, cy-.009, Z, .009*scale,.004,amber,'Shadow theatre',12)
    for k in range(3):
        rod('Pierced skirt', [(-.071+.019*k, .156), (-.06+.019*k, .118)], .003,amber)
player(-.284, 1.04, 1, .006,coal)
player(.285, .88, -1, 0,rust)
# Tree-of-life silhouette between the performers: nested open diamonds.
for i in range(3):
    z = 1.25 + .087 * i
    line_front('Palm frond', [(-.081+i*.015, z+.075), (0, z),(.081-i*.015,z+.075)],-.441,.007,rust,'Shadow theatre')
line_front('Tree trunk', [(0, 1.102), (0, 1.549)], -.442,.006,rust,'Shadow theatre')
# Gabled crown with a scalloped fan and an inset title frieze.
outline = [(-.727, 1.764), (.727, 1.764), (.727,1.927),(.61,1.913),(.52,1.986),(.39,1.97),(.281,2.04),(.18,2.018),(0,2.161),(-.18,2.018),(-.281,2.04),(-.39,1.97),(-.52,1.986),(-.61,1.913),(-.727,1.927)]
prism('Crown silhouette', outline, -.34, .41, rose, 'NEG_Y',.012)
line_front('Crown gold edge', outline[2:], -.416, .012, brass)
label('B A Y A N G    B U L A N', (0, -.415, 1.875), .108,cream,1.23)
diamond('Crown gem', 0, -.419, 2.045, .10,.105,brass)
deck('Control shelf', 0, -.319, .824, 1.38,.49,.102,.076,brass)
deck('Control inlay', 0, -.322, .921, 1.333,.45,.022,.065,rose)
for x in [-.442, .442]:
    lathe('Rod socket', x, -.436, [(.068, .943),(.066,.957),(.046,.965)],coal,24,'Controls')
    rail('Control shaft', (x, -.436, .963),(x*.96,-.456,1.03),.015,brass,'Controls')
    globe('Turned grip', (x*.96, -.456, 1.046),(.034,.034,.037),oak,'Controls')
label('K E L A N T A N', (0, -.425, .945), .063, cream,.53,on_top=True)
deliver((2.0, -5.35, 1.83), '888787', 1.12)
