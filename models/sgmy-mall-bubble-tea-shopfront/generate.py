"""Build a static, original SG/MY bubble-tea frontage.
Origin: facade centreline at the subfloor base (0,0,0). Shallow shop
shell, not a full room. Recess the subfloor lip into the playing surface.

Usage: blender -b --python generate.py
Blender 5.2.3; metres, Z up, customer side -Y (+Z in glTF).
Original deterministic geometry and artwork; built-in font, no external inputs.
Export requires a glTF KHR_draco_mesh_compression decoder at runtime.
"""

# Shared construction helpers, embedded to keep this generator standalone.
import math
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
    color = tuple(linear(int(rgb[i:i+2], 16) / 255) for i in (0, 2, 4))
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
    vs = [(x+sx*a, y+sy*b, z+sz*c) for sz in (-1,1)
          for sx, sy in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return mesh(name, vs, [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),
                           (2,3,7,6),(3,0,4,7)], material, bevel, group)


def prism(name, outline, lo, hi, material, axis='Z', bevel=0, group='Structure'):
    # Outline is counterclockwise as viewed from the positive axis.
    n = len(outline)
    def xyz(u, v, w):
        return {'Z': (u,v,w), 'X': (w,u,v), 'NEG_Y': (u,-w,v)}[axis]
    vs = [xyz(u,v,w) for w in (lo,hi) for u,v in outline]
    fs = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name, vs, fs, material, bevel, group)


def rounded(w, h, r, center=(0,0), steps=5):
    cx, cy = center
    corners = [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,PI/2),
               (-w/2+r,-h/2+r,PI),(w/2-r,-h/2+r,1.5*PI)]
    return [(cx+x+r*math.cos(a+t*PI/(2*steps)), cy+y+r*math.sin(a+t*PI/(2*steps)))
            for x,y,a in corners for t in range(steps+1)]


def plaque(name, x, y, z, w, h, depth, radius, material, group='Graphics'):
    return prism(name, rounded(w,h,radius,(x,z)), -y-depth/2, -y+depth/2,
                 material, 'NEG_Y', min(depth*.23,.012), group)


def ring(name, x, y, z, w, h, r, thickness, depth, material, group='Structure'):
    outside = rounded(w,h,r,(x,z))
    inside = rounded(w-2*thickness,h-2*thickness,r-thickness,(x,z))
    n = len(outside)
    vs = [(u,k,v) for k in (y+depth/2, y-depth/2) for pts in (outside,inside) for u,v in pts]
    fs = []
    for i in range(n):
        j = (i+1)%n
        fs += [(i,i+2*n,j+2*n,j),(i+n,j+n,j+3*n,i+3*n),
               (i+2*n,i+3*n,j+3*n,j+2*n),(i,j,j+n,i+n)]
    return mesh(name, vs, [tuple(reversed(f)) for f in fs], material, min(thickness*.18,.012), group)


def lathe(name, x, y, profile, material, sides=32, group='Structure', caps=True):
    # Profile runs from bottom to top on the outside, then back down any inside wall.
    vs = [(x+r*math.cos(TAU*i/sides), y+r*math.sin(TAU*i/sides), z)
          for r,z in profile for i in range(sides)]
    n = len(profile)
    fs = [tuple(reversed(range(sides))),tuple(range((n-1)*sides,n*sides))] if caps else []
    for k in range(n-1):
        for i in range(sides):
            j = (i+1)%sides
            fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    obj = mesh(name, vs, fs, material, group=group, smooth=True)
    if caps:
        for face in list(obj.data.polygons)[:2]:
            face.use_smooth = False
    return obj


def tube(name, points, radius, material, group='Structure', sides=10, vertical_scale=1.0, reference=None):
    path = [Vector(p) for p in points]
    vs = []
    for i,p in enumerate(path):
        tangent = (path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        ref = Vector(reference) if reference else (Vector((0,0,1)) if abs(tangent.z)<0.97 else Vector((0,1,0)))
        u = tangent.cross(ref).normalized()
        v = tangent.cross(u)
        for j in range(sides):
            a = TAU*j/sides
            vs.append(p+radius*(u*math.cos(a)+v*math.sin(a)*vertical_scale))
    fs = [tuple(reversed(range(sides))), tuple(range(len(vs)-sides,len(vs)))]
    for k in range(len(path)-1):
        for i in range(sides):
            j = (i+1)%sides
            fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    obj = mesh(name, vs, fs, material, group=group, smooth=True)
    for face in list(obj.data.polygons)[:2]:
        face.use_smooth = False
    return obj


def disc_front(name, x, y, z, r, depth, material, group='Graphics', sides=32):
    return prism(name, [(x+r*math.cos(TAU*i/sides),z+r*math.sin(TAU*i/sides))
                        for i in range(sides)], -y-depth/2, -y+depth/2,
                 material, 'NEG_Y', min(depth*.2, .004), group)


def pane(name, x, y, z, w, h, material):
    # Single sheet: no double tint on the back face of the panel.
    return mesh(name, [(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),
                       (x-w/2,y,z+h/2)], [(0,1,2,3)], material, group='Glazing')


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
        obj.rotation_euler.x = PI/2
    if max_width:
        x_min = min(v[0] for v in obj.bound_box)
        x_max = max(v[0] for v in obj.bound_box)
        # bound_box may not be evaluated yet; constrain the final width in bake().
        if x_max > x_min:
            obj.scale.x = min(1.0, max_width / (x_max-x_min))
        obj['max_width'] = max_width
    return obj


def line_front(name, xz, y, radius, material, group='Graphics'):
    return tube(name, [(x,y,z) for x,z in xz], radius, material, group, sides=8)


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
                width = (max(xs)-min(xs))*transform.col[0].xyz.length
                if width > obj['max_width']:
                    for j in range(3):
                        transform[j][0] *= obj['max_width']/width
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
                a,b,c = (points[k] for k in tri.vertices)
                normal = (b-a).cross(c-a)
                if normal.length_squared < 1.0e-17:
                    continue
                fs.append(tuple(offset+k for k in tri.vertices))
                ids.append(material_id)
                axis = max(range(3), key=lambda k: abs(normal[k]))
                i,j = ((1,2),(0,2),(0,1))[axis]
                flip = -1 if normal[axis] < 0 else 1
                uvs.extend((p[i]*flip,p[j]) for p in (a,b,c))
                normals.extend((normal_matrix @ src_normals[k].vector).normalized() for k in tri.loops)
            state.to_mesh_clear()
        # Discard vertices referenced only by degenerate conversion triangles.
        used = sorted({i for f in fs for i in f})
        index = {old:new for new,old in enumerate(used)}
        data = bpy.data.meshes.new(group)
        data.from_pydata([vs[i] for i in used], [], [tuple(index[i] for i in f) for f in fs])
        data.update()
        for material in materials:
            data.materials.append(material)
        data.polygons.foreach_set('material_index', ids)
        data.polygons.foreach_set('use_smooth', [True]*len(ids))
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
    center = Vector([(max(v[i] for v in coords)+min(v[i] for v in coords))/2 for i in range(3)])
    span = max(max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3))
    arm = Vector(direction).normalized()
    rotation = (-arm).to_track_quat('-Z','Y')
    projection = [rotation.inverted() @ (v-center) for v in coords]
    lo = Vector([min(p[i] for p in projection) for i in range(3)])
    hi = Vector([max(p[i] for p in projection) for i in range(3)])
    target = center + rotation @ Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,0))
    camera = bpy.data.objects.new('Preview Camera', bpy.data.cameras.new('Orthographic Preview'))
    bpy.context.collection.objects.link(camera)
    camera.location = target + arm*span*3
    camera.rotation_euler = rotation.to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max(hi.x-lo.x, (hi.y-lo.y)*1.25)*margin
    scene.camera = camera
    box('Preview Ground', (center.x,center.y,-0.035), (span*200,span*200,0.06),
        mat('Studio Backdrop',backdrop,.82), 0, None)
    world = bpy.data.worlds.new('Studio Ambient')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.37,.43,.52,1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .32
    def area(name, offset, watts, size, color):
        data = bpy.data.lights.new(name, 'AREA')
        light = bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(light)
        light.location = center + Vector(offset)*span
        light.rotation_euler = (center-light.location).to_track_quat('-Z','Y').to_euler()
        data.energy = watts*span**2
        data.shape = 'DISK'
        data.size = size*span
        data.color = color
    area('Soft Warm Key',(-.65,-.95,1.25),143,1.1,(1,.88,.73))
    area('Cool Front Fill',(.85,-.7,.58),62,1.1,(.75,.86,1))
    area('Overhead Rim',(.2,.9,1.30),186,.9,(1,.95,.86))
    scene.render.engine = engine
    if engine == 'CYCLES':
        scene.cycles.samples = 32
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.58
    scene.render.resolution_x = 1250
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene


def deliver(direction, backdrop, margin=1.19, engine='BLENDER_EEVEE'):
    objs = bake()
    dest = Path(__file__).resolve().parent
    if '--' in sys.argv and '--preview-only' in sys.argv[sys.argv.index('--')+1:]:
        export = False
    else:
        export = True
    print(f'{TITLE}: {sum(len(o.data.polygons) for o in objs):,} triangles')
    if export:
        bpy.ops.export_scene.gltf(filepath=str(dest/'model.glb'), export_format='GLB',
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=18,
                                  export_draco_normal_quantization=12,
                                  export_draco_texcoord_quantization=16,
                                  export_cameras=False, export_lights=False,
                                  export_animations=False)
        assert (dest/'model.glb').stat().st_size <= 2_000_000
    scene = studio(direction, backdrop, margin, engine)
    scene.render.filepath = str(dest/'preview.png')
    bpy.ops.render.render(write_still=True)


TITLE = 'Titik Teh Bubble Tea'


def build():
    reset()
    plum = mat('Blackcurrant Anodised Metal','45304F',.35,.26)
    violet = mat('Ube Powder Coat','A576CB',.43)
    flutes = mat('Lavender Fluted Ceramic','AE80CF',.34)
    pale = mat('Orchid Pastel','D8B9EA',.34)
    cream = mat('Porcelain Quartz','FAEBD9',.33)
    light = mat('Vanilla Light Diffuser','FFF3DC',.44,glow=.8)
    pink = mat('Pomelo Coral','EF8B80',.40)
    honey = mat('Gula Melaka Toffee','C58756',.37)
    jade = mat('Pandan Sage','90BB8D',.37)
    tea = mat('Oolong Amber','E6AD69',.37)
    board = mat('Menu Ink Background','392840',.5)
    straw = mat('Pearl Straw','EF7D73',.4)
    black = mat('Tapioca Pearls','3D2631',.33)
    metal = mat('Satin Appliance Steel','B7AFBD',.34,.55)
    prop = 'Counter Equipment'

    box('Shop floor',(0,.51,.041),(4.68,2.44,.082),plum)
    for i in range(9):
        for j in range(5):
            box('Porcelain floor tile',((i-4)*.507,-.45+j*.469,.086),(.502,.465,.016),pale,.003)
    box('Lilac back panel',(0,1.69,1.58),(4.68,.17,3.09),plum,.025)
    box('Vanilla service backsplash',(0,1.581,1.63),(4.18,.08,1.99),cream,.035)
    for x in (-2.24,2.24):
        box('Portal wall return',(x,.542,1.54),(.19,2.25,3.08),violet,.024)
    box('Portal soffit',(0,.47,2.94),(4.51,2.37,.23),violet,.029)
    box('Prep bench',(0,1.22,.538),(4.16,.64,.889),plum,.019)
    box('Prep bench quartz',(0,1.212,.996),(4.20,.693,.057),cream,.014)

    # Open portal with rounded corners, layered highlight and opaque backing columns.
    ring('Rounded lilac portal',0,-.648,1.604,4.60,3.16,.44,.163,.22,violet)
    ring('Cream edge highlight',0,-.772,1.604,4.47,3.04,.39,.022,.028,cream)
    for x in (-2.194,2.194):
        box('Portals meet the floor at a shoe',(x,-.636,.15),(.265,.256,.3),plum,.018)
    plaque('Floating plum fascia',.055,-.788,2.936,4.28,.66,.171,.296,plum,'Structure')
    plaque('Lavender sign inlay',.23,-.884,2.936,3.65,.506,.022,.224,violet)
    disc_front('Coral pearl emblem background',-1.64,-.898,2.935,.282,.08,pink)
    # Original take-away cup mark, punched from solid cream and plum shapes.
    cup = [(-1.719,2.831),(-1.564,2.831),(-1.53,3.001),(-1.751,3.001)]
    prism('Sign cup body',cup,.926,.945,light,'NEG_Y',.008,'Graphics')
    plaque('Sign cup lid',-1.64,-.95,3.015,.255,.039,.023,.016,cream)
    line_front('Sign diagonal straw',[(-1.624,3.003),(-1.583,3.096)],-.952,.015,plum)
    for x,z in [(-1.70,2.886),(-1.63,2.876),(-1.58,2.912),(-1.646,2.94)]:
        disc_front('Pearl dot',x,-.951,z,.019,.014,plum,sides=16)
    label('TITIK TEH',(.179,-.900,3.005),.393,light,2.29,extrude=.004)
    label('BUBBLE TEA  /  TEH MUTIARA',(.18,-.900,2.804),.102,cream,2.52)
    plaque('Unit pill',1.644,-.913,2.962,.63,.231,.038,.110,pink)
    label('#01-09',(1.644,-.937,2.962),.125,plum,.50)

    # Fluted counter ends in a contrasting pick-up wing.
    plaque('Counter core',-.18,-.294,.559,3.99,.89,.836,.24,plum,'Structure')
    plaque('Coral pick up panel',1.20,-.726,.582,1.19,.784,.065,.24,pink,'Structure')
    for i in range(36):
        x=-1.966+i*.073
        box('Rounded fluted cladding',(x,-.73,.54),(.062,.084,.726),flutes,.022)
    box('Quartz counter slab',(-.18,-.30,1.028),(3.99,.95,.111),cream,.041)
    box('Warm toe kick diffuser',(-.713,-.756,.147),(2.56,.032,.031),light,.012)
    for x,words,tone in ((-.94,'ORDER / PESAN',cream),(1.22,'PICK UP / AMBIL',pink)):
        plaque('Counter station capsule',x,-.786,.708,1.09,.212,.038,.084,plum)
        label(words,(x,-.812,.707),.106,tone,.94)

    # Digital menu mock-ups and three original featured drinks.
    menu = [('GULA MELAKA','PALM SUGAR MILK','5.20',honey),
            ('PANDAN FOAM','COCONUT CREMA','5.60',jade),
            ('OOLONG','ROASTED MILK TEA','4.90',tea)]
    menu_start = len(PARTS['Graphics'])
    for i,(name,desc,price,tone) in enumerate(menu):
        x=(i-1)*1.319
        plaque('Digital menu frame',x,1.496,2.157,1.257,.861,.072,.063,plum)
        plaque('Drink menu color card',x,1.451,2.158,1.142,.755,.026,.043,tone)
        label(name,(x,1.431,2.434),.122,board,1.00)
        label(desc,(x,1.430,2.326),.059,board,.98)
        g=x-.196
        p = [(g-.09,1.841),(g+.09,1.841),(g+.128,2.213),(g-.128,2.213)]
        prism('Menu cup illustration',p,-1.438,-1.423,cream,'NEG_Y',.004,'Graphics')
        plaque('Menu cap',g,1.417,2.229,.286,.033,.021,.013,board)
        line_front('Menu straw',[(g+.027,2.234),(g+.085,2.315)],1.421,.013,pink)
        for a,b in [(-.051,.051),(.02,.074),(.058,.107),(-.021,.112),(-.022,.023)]:
            disc_front('Menu tapioca',g+a,1.415,1.857+b,.018,.012,board,sides=10)
        plaque('Menu price capsule',x+.289,1.419,1.998,.383,.134,.025,.064,board)
        label('$'+price,(x+.289,1.400,2.002),.094,cream,.335)
    for obj in PARTS['Graphics'][menu_start:]:
        obj.location.y -= .94
        obj.location.z -= .154
    for x in (-1.317,0,1.317):
        for dx in (-.47,.47):
            box('Menu ceiling bracket',(x+dx,.574,2.60),(.034,.044,.475),plum,.008)
    for x in (-1.34,0,1.34):
        box('Warm recessed soffit strip',(x,-.24,2.812),(.79,.063,.024),light,.009)

    # Countertop sealing press, contactless till and cups waiting for collection.
    box('Cup sealer base',(-.123,1.18,1.105),(.51,.43,.163),metal,.036,prop)
    box('Cup sealer uprights',(-.123,1.309,1.313),(.43,.177,.343),plum,.027,prop)
    box('Sealer press head',(-.123,1.177,1.503),(.50,.428,.192),pink,.036,prop)
    plaque('Sealer controls',-.123,.956,1.512,.378,.099,.024,.026,plum,prop)
    for i in range(3):
        disc_front('Sealer indicator',-.22+i*.098,.940,1.508,.021,.012,(light,jade,pink)[i],prop,14)
    lathe('Cup sealing spindle',-.123,1.05,[(.083,1.194),(.11,1.216),(.103,1.238),(.087,1.244)],metal,28,prop)
    box('Till foot',(-1.45,-.28,1.098),(.32,.24,.038),plum,.016,prop)
    box('Till stand',(-1.45,-.264,1.20),(.071,.067,.182),plum,.012,prop)
    plaque('Customer reader',-1.45,-.287,1.284,.293,.172,.051,.034,plum,prop)
    plaque('Reader status strip',-1.45,-.314,1.31,.216,.046,.008,.015,light,prop)
    for x,y,tone,shift in ((.92,-.45,honey,0),(1.20,-.41,jade,0),(1.49,-.46,tea,-.029)):
        z=1.084
        lathe('Filled bubble tea cup',x,y,[(.042,z),(.046,z+.014),(.060,z+.195+shift),(.057,z+.201+shift)],tone,26,prop)
        lathe('Sealed milk cup rim',x,y,[(.056,z+.194+shift),(.065,z+.199+shift),(.064,z+.212+shift),(.052,z+.214+shift)],cream,26,prop)
        tube('Wide tapioca straw',[(x,y,z+.206+shift),(x+.015,y,z+.301+shift)],.008,straw,prop)
        for i in range(5):
            a=4.18+i*.25
            rr=.046+.0008*i
            p=(x+rr*math.cos(a),y+rr*math.sin(a),z+.031+(i%3)*.013)
            lathe('Visible tapioca silhouette',p[0],p[1],[(.003,p[2]-.005),(.007,p[2]),(.003,p[2]+.005)],black,10,prop)
    for x in (-1.46,-1.17):
        for j in range(6):
            z=1.027+.021*j
            lathe('Nested paper cup',x,1.207,[(.042,z),(.062,z+.151),(.066,z+.155),(.065,z+.161),
                                             (.059,z+.16),(.039,z+.009)],cream,22,prop)
    deliver((-.29,-1,.174),'B7ADCC')


if __name__ == '__main__':
    build()
