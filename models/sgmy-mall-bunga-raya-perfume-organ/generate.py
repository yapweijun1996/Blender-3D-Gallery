"""Bunga Raya: a mall perfumer's blending organ. Metres, base pivot, operator
at -Y. Original note bottles, scent strips, tiered shelves and hibiscus crest.
Geometry only, static, no external dependencies. blender -b -P generate.py
"""
TITLE = 'Bunga Raya Blending Organ'
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


def bar(name, a, b, width, depth, material, group='Structure', bevel=.006):
    a, b = Vector(a), Vector(b)
    obj = box(name, (0, 0, 0), (width, depth,(b-a).length),material,bevel,group)
    obj.location = (a + b) / 2
    obj.rotation_euler = (b - a).to_track_quat('Z', 'Y').to_euler()
    return obj


def rail(name, a, b, radius, material, group='Structure', sides=12):
    return tube(name, [a, b], radius, material, group,sides)


def patch(name, outline, y, material, group='Graphics'):
    return prism(name, outline, -y-.002, -y+.002, material, 'NEG_Y',group=group)


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


reset()
rose = mat('Wine lacquer', '7e3c4a', .29)
pink = mat('Rose enamel', 'd59089', .39)
cream = mat('Chalk porcelain', 'f8dfbd')
brass = mat('Brass banding','ce9e61',.31,.59)
ink=mat('Deep aubergine','413744')
moss=mat('Vetiver glaze','739e87',.20,.12); topaz=mat('Topaz glaze','d49b59',.21,.19); berry=mat('Hibiscus glaze','b95e65',.22,.12); walnut=mat('Carved walnut','795342')
# Kidney-shaped gondola: a shallow concave facing leaves space for the blender.
def organ(name, width, depth, z, h, color,front=-.38,group='Cabinet'):
    w = width / 2
    outline = []
    for j in range(27):
        a = PI * j / 26
        outline.append((w * math.cos(a), front + depth * math.sin(a)))
    for j in range(1, 26):
        a = PI + PI * j / 26
        outline.append((w * math.cos(a), front + .085 * math.sin(a)**2 + .046 * math.sin(a)))
    return prism(name, outline, z, z+h, color, bevel=.012,group=group)
# Broad satin worktop and a barrel-sided cabinet beneath the rising note galleries.
deck('Inset sole', 0, 0, 0, 1.78,.96,.084,.215,ink)
deck('Curved base', 0, 0, .08, 1.94,1.08,.75,.236,rose)
for i in range(7):
    for s in [-1, 1]:
        x = s * (.343 + i * .087)
        box('Gilt cabinet flute', (x, -.541+max(0, i-4)*.013, .44),(.009,.014,.51),brass,.003,'Cabinet')
plaque('House medallion', 0, -.55, .484, .565,.474,.026,.196,pink)
label('B R', (0, -.569, .52),.162,ink,.389)
label('P A R F U M', (0, -.569, .366),.057,ink)
deck('Beaded fascia', 0, 0, .823, 2.01,1.13,.045,.225,brass)
deck('Pale work surface', 0, 0, .862, 2.04,1.16,.067,.226,cream)
# A semicircular stair of scent families. Rows narrow toward the crest.
for i, (width, front, deep) in enumerate([(1.82, -.282, .796),(1.53,-.005,.528),(1.04,.202,.326)]):
    z = .929 + i * .193
    organ('Lacquer tier', width, deep, z,.17,rose,front,'Note organ')
    organ('Shelf binding', width+.012, deep, z+.165,.026,brass,front-.005,'Note organ')
    for j in range([6, 5, 4][i]):
        count = [6, 5, 4][i]
        x = (j-(count-1)/2)*[.256, .26, .219][i]
        y = front +.087 +.03 *(1 -abs(x))
        base = z +.191
        col = [moss, topaz, berry][i]
        r = [.060, .059, .055][i]
        H = [.166, .176, .17][i]
        if i == 0:
            lathe('Round base note flacon', x, y, [(r*.75, base), (r,base+.014),(r,base+H*.69),(r*.89,base+H*.79),(r*.39,base+H*.9),(r*.37,base+H)],col,28,'Flacons')
        elif i == 1:
            deck('Square heart note flacon', x, y-.001, base, .115,.088,.134,.018,col,'Flacons')
            lathe('Bottle shoulder', x, y, [(r*.73, base+.134),(r*.4,base+.151),(r*.37,base+H)],col,16,'Flacons')
        else:
            globe('Petal top note flacon', (x, y, base+.074), (.059,.05,.076),col,'Flacons',sides=20,bands=10)
            lathe('Narrow throat', x, y, [(.026, base+.132),(.020,base+H)],col,18,'Flacons')
        lathe('Stopper ferrule', x, y, [(.024, base+H),(.025,base+H+.018)],brass,18,'Flacons')
        globe('Faceted stopper', (x, y, base+H+.034), (.026,.026,.024),cream,'Flacons',sides=8,bands=4)
        plaque('Bottle cartouche', x, y-[.061, .047, .052][i],base+.074,.057,.049,.004,.011,cream,'Flacons')
        label('%02d'%(1+j+[0, 6, 11][i]), (x, y-[.064,.05,.055][i],base+.074),.031,ink)
    # Mount the note key together below the bottles, clear of their silhouettes.
    txt = ['I   /   BASE', 'II   /   HEART', 'III   /   TOP'][i]
    band((i-1)*.46, -.279, 1.014, .383, .092, ink,cream,txt,.048)
# Tall arched finial with a five-petal hibiscus detail.
for x in [-.28, .28]:
    rail('Crest standard', (x, .445, 1.47), (x,.445,1.946),.018,brass)
plaque('House crest', 0, .443, 1.957,.81,.479,.069,.17,ink)
plaque('Enamel face', 0, .403, 1.957,.757,.433,.013,.149,pink)
for i in range(5):
    a = TAU * i / 5 + PI / 2
    cx = -.22 + .049 * math.cos(a)
    cz = 1.96 + .049 * math.sin(a)
    p = [(cx + .046 * math.cos(TAU * k / 18), cz + .046 * math.sin(TAU * k / 18)) for k in range(18)]
    patch('Hibiscus petal', p, .392 -i *.002, rose)
disc_front('Flower eye', -.22, .378, 1.96, .025,.01,brass)
line_front('Hibiscus column', [(-.22, 1.96), (-.169, 2.01)],.37,.006,cream)
label('BUNGA', (.093, .391, 1.999), .105,ink,.369)
label('R A Y A', (.093, .391, 1.907), .073,ink,.335)
# Porcelain test cup with fan of blotters, a low brass mixing mortar and pipette.
x, y = -.687, -.431
lathe('Blotter cup', x, y, [(.043, .93), (.053,.935),(.066,1.053),(.064,1.069),(.055,1.07),(.047,1.01)],pink,24,'Worktop tools')
for k in range(5):
    bar('Blotter paper', (x+(k-2)*.009, y+(k%2)*.013, 1.014), (x+(k-2)*.042, y-.008,1.215-abs(k-2)*.012),.023,.004,cream,'Worktop tools',.001)
lathe('Mixing dish', .63, -.412, [(.051, .929),(.065,.935),(.086,.949),(.105,1.008),(.10,1.014),(.087,.999),(.058,.954)],brass,32,'Worktop tools')
rail('Dropper', (.601, -.408, .975),(.736,-.387,1.068),.005,cream,'Worktop tools')
globe('Dropper bulb', (.751, -.386, 1.079),(.023,.014,.019),ink,'Worktop tools')
deliver((2.27, -5.62, 2.91), '938b89', 1.13)
