"""Kilat: raised shoe-shine chair with twin footrests and polish caddy.
Original shopping-arcade service furniture, in metres. Sitter faces -Y,
origin on floor. Static geometry. Rebuild: blender -b -P generate.py.
"""
TITLE = 'Kilat Shoe Saloon'
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


def deck(name, x, y, z, w, d,h,r,material,group='Structure'):
    return prism(name, rounded(w, d, r, (x, y)),z,z+h,material,bevel=min(.009,h/5),group=group)


def oval_line(name, x, y, z, r1, r2,width,material):
    pts = [(x + r1 * math.cos(TAU * i / 48), y + r2 * math.sin(TAU * i / 48), z) for i in range(49)]
    return tube(name, pts, width, material, 'Graphics', 8,reference=(0,0,1))


reset()
w = mat('Meranti stain', '824c31', .35)
trim = mat('Dark hardwood', '44362e')
brass = mat('Aged brass', 'd3a15d',.29,.65)
leather = mat('Bottle green leather','306258',.39)
piping=mat('Leather welt','578777')
cream=mat('Old ivory','f5ddab'); black=mat('Brush bristles','332e2c'); ox=mat('Oxide red','a9513d')
deck('Cabinet sole', 0, 0, 0, 1.29,1.64,.075,.08,trim)
deck('Service chest', 0, 0, .068,1.24,1.58,.385,.056,w)
deck('Platform edge', 0, 0,.441,1.32,1.65,.048,.06,brass)
deck('Stage cap', 0, 0,.484,1.32,1.65,.038,.06,trim)
for x in [-.285, .285]:
    plaque('Polish drawer', x, -.80, .263, .52,.288,.033,.025,trim)
    plaque('Drawer field', x, -.820, .263, .457,.227,.013,.019,w)
    for dx in [-.08, .08]:
        rail('Pull standoff', (x+dx, -.83, .275), (x+dx,-.866,.275),.011,brass)
    rail('Pull', (x-.08, -.865, .275), (x+.08,-.865,.275),.013,brass)
# Raised chair, turned supports with brass collars and padded, channelled back.
for x in [-.36, .36]:
    for y in [-.018, .616]:
        lathe('Turned chair leg', x, y, [(.055, .52), (.059,.553),(.04,.573),(.034,.756),(.062,.81),(.063,.835),(.049,.858),(.050,.928)],w,24)
        lathe('Ferrule', x, y, [(.056, .52), (.058,.553)],brass,24)
    for y in [.015, .56]:
        lathe('Arm baluster', x*1.17, y, [(.036, .951), (.037,1.02),(.024,1.06),(.024,1.14),(.036,1.173),(.036,1.205)],brass,20)
    deck('Arm cap', x*1.17, .291, 1.192, .107,.696,.069,.045,w)
    deck('Elbow pad', x*1.17, .29, 1.255, .09,.54,.033,.037,leather)
deck('Seat frame', 0, .302, .891, .939,.819,.090,.095,w)
deck('Seat welt', 0, .289, .977,.855,.755,.034,.112,piping)
deck('Seat cushion', 0, .289, 1.006,.853,.749,.098,.108,leather)
for x in [-.36, .36]:
    bar('Back stile', (x, .59, .94), (x,.735,1.82),.054,.073,w)
# Layers use rotation about their own centres for a gentle recline.


def pad(name, at, dims, col, roll):
    o = box(name, (0, 0, 0),dims,col,roll,'Upholstery')
    o.location = at
    o.rotation_euler.x = -.147
pad('Back shell', (0, .673, 1.47), (.89, .126,.857),w,.057)
for i in range(7):
    pad('Vertical leather channel', ((i-3)*.111, .597, 1.466), (.12,.104,.746),leather,.050)
for x in [-.256, .256]:
    # Shoe rests are capped with shaped cast-iron lasts, oriented toe-forward.
    lathe('Rest foot', x, -.50, [(.102, .52), (.103,.543),(.078,.561),(.054,.576),(.035,.60)],brass,28)
    bar('Raked footrest stem', (x, -.50, .56), (x, -.555,.727),.043,.053,brass)
    outline = [(-.055, -.13), (-.037, -.155), (.04,-.157),(.066,-.12),(.069,-.063),(.05,.034),(.038,.107),(-.034,.112),(-.055,.05),(-.070,-.064)]
    prism('Polished shoe last', [(x+u, -.55+v) for u, v in outline], .709, .76,brass,bevel=.013,group='Footrests')
    deck('Rubber heel grip', x, -.495, .756, .071, .086,.013,.02,black,'Footrests');
    for k in range(3):
        box('Grip rib', (x, -.608-k*.025, .762), (.095,.009,.005),black,.002,'Footrests')
# Sidecar shelf for tins and horsehair brush, secured to the platform edge.
deck('Polish caddy', .715, -.15, .486, .27,.787,.084,.042,w)
deck('Caddy liner', .714, -.15, .568, .235,.746,.009,.034,cream)
for j, col in enumerate([ox, leather, black]):
    y = .107 - .174 * j
    lathe('Wax tin', .715, y, [(.066,.579),(.068,.608),(.074,.613),(.074,.627),(.061,.63)],col,28,'Polishing kit')
    oval_line('Tin border', .715, y, .631,.054,.054,.003,brass)
box('Horsehair brush', (.717, -.411, .606), (.106,.155,.056),black,.014,'Polishing kit')
deck('Brush back', .717, -.411, .634, .113,.167,.03,.036,w,'Polishing kit')
band(0, -.836, .465, .525, .094, trim,cream,'K I L A T   /   J O H O R',.044)
deliver((2.9, -4.9, 2.24), '918d82', 1.13)
