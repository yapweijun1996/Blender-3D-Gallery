"""Build a static 4-seat SG/MY food-court table with a meal and kopi trays.
Origin: centre of the table at the floor (Z=0). Detach the Tabletop Props
node to use the table without the two trays and table marker.

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


TITLE = 'Serambi Food Court Table A12'


def build():
    import random
    reset()
    frame = mat('Dark Petrol Steel Frame','334A50',.38,.25)
    steel = mat('Satin Stainless Table Edge','ABB6B4',.32,.58)
    feet = mat('Rubber Levelling Feet','302D32',.65)
    terrazzo = mat('Warm Ivory Cast Terrazzo','ECE1CA',.41)
    chips = [mat(name,c,.45) for name,c in [('Sandstone Fleck','D1B9A2'),('Shell Fleck','F8F0DD'),
              ('Jade Fleck','859E8E'),('Terracotta Fleck','A87358')]]
    red = mat('Kopitiam Vermilion Seat','B8453C',.40)
    peach = mat('Oxide Orange Seat','D96B45',.40)
    cream = mat('Cream Ceramic','F5E6C5',.35)
    green = mat('Deep Jade Melamine','296753',.38)
    pale = mat('Mint Enamel Table Number','B0CFB3',.42)
    melamine = mat('Old Copper Tray','A75140',.44)
    gold = mat('Mustard Tray','C29354',.44)
    leaf = mat('Banana Leaf Emerald','4D8856',.51)
    vein = mat('Banana Leaf Vein','A5B46B',.53)
    rice = mat('Coconut Rice','E9E0BE',.58)
    sambal = mat('Sambal Red','9F3428',.41)
    yolk = mat('Egg Yolk Ochre','E5AD4C',.52)
    cucumber = mat('Cucumber Flesh','BED784',.49)
    coffee = mat('Kopi Liquid','3E2417',.29)
    navy = mat('Dark Blue Porcelain Band','225777',.34)
    props = 'Tabletop Props'
    base = 'Table Terrazzo and Frame'
    seats = 'Four Stool Shells'

    # Shared underframe anchors all four independently moulded seats.
    lathe('Central floor protector',0,0,[(.16,0),(.18,.007),(.18,.026),(.167,.034)],feet,40,base)
    lathe('Pressed central flange',0,0,[(.166,.033),(.173,.042),(.157,.064),(.107,.087),(.095,.108)],frame,40,base)
    lathe('Tubular central column',0,0,[(.087,.073),(.092,.095),(.079,.612),(.09,.659),(.104,.673)],frame,40,base)
    lathe('Table head mounting plate',0,0,[(.106,.665),(.141,.678),(.166,.694),(.167,.712)],steel,40,base)
    for x,y,color in ((.758,.668,peach),(-.758,.668,red),(-.758,-.668,peach),(.758,-.668,red)):
        tube('Radial floor link',[(x*.064,y*.064,.107),(x*.61,y*.61,.091),(x*.87,y*.87,.067),(x,y,.063)],
             .033,frame,base,sides=12,vertical_scale=.85)
        lathe('Levelling shoe',x,y,[(.077,0),(.087,.006),(.087,.027),(.073,.035)],feet,28,base)
        lathe('Stool upright socket',x,y,[(.070,.031),(.073,.047),(.060,.075),(.046,.104)],frame,28,base)
        lathe('Stool upright post',x,y,[(.043,.085),(.044,.112),(.040,.373),(.047,.400)],steel,28,base)
        lathe('Stool pressed underpan',x,y,[(.060,.387),(.115,.395),(.155,.408),(.155,.425)],frame,36,seats)
        lathe('Injection moulded stool',x,y,[(.149,.414),(.166,.422),(.178,.436),(.178,.450),(.169,.462),
             (.153,.466),(.129,.461),(.102,.456),(.045,.458)],color,44,seats)
        lathe('Stool mould parting detail',x,y,[(.1765,.437),(.1791,.44),(.1786,.444),(.1765,.445)],color,44,seats)
    lathe('Stainless rolled table edge',0,0,[(.55,.693),(.613,.696),(.637,.703),(.646,.713),
          (.646,.731),(.64,.74),(.626,.742)],steel,72,base)
    lathe('Round cast terrazzo top',0,0,[(.605,.709),(.626,.727),(.633,.737),(.628,.746)],terrazzo,72,base)

    # Seeded, flush terrazzo tesserae: geometric colour, no baked or external textures.
    rng=random.Random(10249)
    flecks = defaultdict(lambda: ([],[]))
    for i in range(1180):
        rr=.612*math.sqrt(rng.random())
        a=rng.uniform(0,TAU)
        x,y=rr*math.cos(a),rr*math.sin(a)
        r=rng.uniform(.0014,.0076)
        bias=rng.random()
        tone=chips[0 if bias<.45 else 1 if bias<.73 else 2 if bias<.91 else 3]
        vs,fs=flecks[tone]
        first=len(vs)
        angles=[rng.uniform(-.18,.18)+TAU*j/5 for j in range(5)]
        for a in angles:
            d=r*rng.uniform(.57,1.22)
            vs.append((x+d*math.cos(a),y+d*math.sin(a)*.82,.74628))
        fs.append(tuple(range(first,first+5)))
    for material,(vs,fs) in flecks.items():
        mesh('Polished exposed terrazzo aggregate',vs,fs,material,group=base)

    def tray(x,y,w,h,material):
        profile = rounded(w,h,.046,(x,y),steps=4)
        inner = rounded(w-.04,h-.04,.028,(x,y),steps=4)
        prism('Moulded tray floor',inner,.745,.767,material,'Z',.005,props)
        n=len(profile)
        vs=[(xx,yy,z) for pts,z in ((profile,.745),(profile,.786),(inner,.775),(inner,.760)) for xx,yy in pts]
        faces=[]
        for i in range(n):
            j=(i+1)%n
            faces.extend((k*n+i,k*n+j,(k+1)%4*n+j,(k+1)%4*n+i) for k in range(4))
        mesh('Tray rolled lip',vs,faces,material,.004,props)
    tray(-.289,.057,.461,.345,melamine)
    tray(.293,-.087,.43,.322,gold)
    x,y=-.33,.079
    lathe('Jade melamine rice plate',x,y,[(.097,.768),(.121,.776),(.136,.790),(.137,.803),
          (.128,.806),(.107,.791),(.093,.787)],green,42,props)
    outline=[(x-.104,y-.016),(x-.079,y-.079),(x+.036,y-.07),(x+.100,y-.033),
             (x+.099,y+.034),(x+.046,y+.074),(x-.069,y+.073)]
    prism('Banana leaf serving liner',outline,.790,.797,leaf,'Z',.002,props)
    tube('Banana leaf midrib',[(x-.095,y+.007,.799),(x,y+.007,.799),(x+.088,y+.007,.799)],.0019,vein,props,sides=6)
    for i in range(5):
        xx=x-.067+.032*i
        for sign in (-1,1):
            tube('Fine leaf vein',[(xx,y+.007,.799),(xx+.015,y+sign*.041,.799)],.0008,vein,props,sides=5)
    lathe('Moulded nasi lemak mound',x-.018,y+.010,[(.055,.798),(.060,.803),(.055,.832),(.046,.846),
          (.031,.852),(.013,.853)],rice,27,props)
    for i in range(28):
        a=rng.uniform(0,TAU)
        r=rng.uniform(.007,.029)
        rx,ry=x-.018+r*math.cos(a),y+.010+r*math.sin(a)
        prism('Individual coconut rice grain',rounded(.007,.0038,.001,(rx,ry),steps=2),.851,.855,rice,'Z',.001,props)
    for i in range(3):
        xx=x+.066-.022*i
        yy=y-.033-.015*i
        z=.798+.004*i
        lathe('Cucumber peel',xx,yy,[(.021,z),(.025,z+.003),(.023,z+.008)],leaf,20,props)
        lathe('Cucumber slice',xx,yy,[(.020,z+.007),(.021,z+.010)],cucumber,20,props)
    lathe('Spoonful of chilli sambal',x+.072,y+.038,[(.019,.797),(.026,.801),(.024,.815),(.016,.819),(.009,.820)],
          sambal,19,props)
    lathe('Boiled egg half',x-.074,y-.031,[(.015,.797),(.028,.805),(.030,.818),(.026,.824)],cream,26,props)
    lathe('Boiled egg yolk',x-.073,y-.031,[(.015,.823),(.017,.824),(.014,.829)],yolk,22,props)
    # Spoon parked in the channel beside the plate.
    prism('Spoon handle outline',rounded(.016,.124,.007,(-.114,.090)),.770,.779,steel,'Z',.002,props)
    prism('Spoon bowl',rounded(.042,.068,.018,(-.114,-.001)),.770,.787,steel,'Z',.005,props)

    x,y=.256,-.077
    lathe('Kopi porcelain saucer',x,y,[(.067,.768),(.093,.776),(.101,.782),(.100,.788),
          (.087,.788),(.065,.781),(.045,.781)],cream,40,props)
    lathe('Blue saucer stripe',x,y,[(.097,.785),(.100,.787),(.098,.791),(.091,.789)],navy,36,props,caps=False)
    lathe('Kopi porcelain cup',x,y,[(.044,.782),(.052,.792),(.056,.814),(.059,.868),(.058,.88),
          (.052,.882),(.049,.875),(.047,.808)],cream,40,props)
    lathe('Brewed kopi surface',x,y,[(.048,.859),(.050,.864),(.050,.868)],coffee,40,props)
    lathe('Cup blue caterers stripe',x,y,[(.0588,.851),(.0596,.854),(.0598,.86),(.0588,.864)],navy,40,props,caps=False)
    tube('Kopi cup curved ear',[(x+.054,y,.863),(x+.074,y,.863),(x+.084,y,.850),
         (x+.083,y,.834),(x+.070,y,.822),(x+.051,y,.818)],.0079,cream,props,sides=9)
    box('Folded tissue pack',(.421,-.142,.790),(.107,.075,.040),pale,.009,props)
    label('CHOPE',(.421,-.139,.811),.022,green,.079,group=props,on_top=True)
    box('Folded takeaway napkin',(.378,-.020,.778),(.140,.112,.019),cream,.004,props)
    # Table marker, visible on approach and separate from the cast top.
    box('Number stand foot',(.04,.325,.765),(.182,.092,.037),steel,.012,props)
    box('Number stand upright',(.04,.333,.835),(.045,.026,.135),steel,.008,props)
    plaque('Jade table number plaque',.04,.327,.911,.183,.142,.040,.028,green,props)
    label('MEJA / TABLE',(.04,.304,.952),.018,pale,.152,group=props)
    label('A12',(.04,.304,.899),.060,cream,.143,group=props)
    deliver((.59,-1,1.02),'C8BCAE',1.17)


if __name__ == '__main__':
    build()
