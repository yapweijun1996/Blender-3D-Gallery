"""Build a static, original SG/MY mall kopitiam frontage.
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


TITLE = 'Lorong Pagi Kopitiam'


def build():
    reset()
    green = mat('Deep Jade Lacquer','12423C')
    celadon = [mat(f'Celadon Glaze {i+1}',c,.29) for i,c in enumerate(['34877A','3F998A','469281','307D70'])]
    old = mat('Dark Tile Grout','234E45',.82)
    cream = mat('Warm Porcelain','F6E8CB',.36)
    warm = mat('Warm Milk Glass','FFE3A4',.38,glow=.7)
    brick = mat('Oxide Red Ceramic','B84F38',.38)
    orange = mat('Amber Accent Enamel','E5AD57',.43)
    walnut = mat('Meranti Timber','784A37',.43)
    dark = mat('Roasted Coffee Brown','35251F',.52)
    gold = mat('Satin Brass','C39C62',.37,.37)
    steel = mat('Brushed Kitchen Stainless','BAC4BF',.33,.66)
    tile = mat('Backsplash Porcelain','E2DBC1',.31)
    mortar = mat('Limestone Tile Joint','A69F87',.85)
    glass = mat('Glass Display Glazing','C9E8DD',.16,alpha=.19)
    toast = mat('Kaya Toast Centre','D99C59',.53)
    crust = mat('Toasted Bread Crust','8E4F2D',.65)
    prop = 'Service Equipment'

    box('Interior subfloor',(0,.42,.04),(5.6,2.38,.08),dark,.015)
    for i in range(14):
        for j in range(6):
            box('Checker floor',(i*.397-2.58,j*.391-.563,.083),(.388,.382,.017),
                (cream,green)[(i+j)%2],.002)
    box('Kitchen back wall',(0,1.56,1.54),(5.55,.15,3.0),dark)
    box('Back tile mortar',(0,1.475,1.55),(5.04,.035,1.08),mortar)
    for row in range(6):
        for col in range(20):
            box('Kitchen wall tile',(col*.25-2.375,1.45,1.095+row*.18),(.244,.028,.173),tile,.005)
    for x in (-2.69,2.69):
        box('Meranti return',(x,.43,1.56),(.205,2.22,3.1),walnut)
        box('Jade facing pier',(x,-.72,1.43),(.265,.22,2.86),green)
        box('Pier kick shoe',(x,-.73,.13),(.29,.235,.26),dark)
        box('Brass pilaster bead',(x,-.845,1.46),(.016,.02,2.57),gold,.004)
        for z in (1.30,1.59,1.88):
            plaque('Heritage square tile',x,-.843,z,.19,.19,.022,.011,cream)
            p = [(x-.071,z),(x,z-.071),(x+.071,z),(x,z+.071)]
            prism('Glaze diamond',p,.855,.857,brick,'NEG_Y',group='Graphics')
            disc_front('Jade tile rosette',x,-.86,z,.027,.009,green,sides=12)
    box('Canopy ceiling',(0,.52,2.79),(5.38,2.05,.15),walnut)
    for x in (-1.66,0,1.66):
        box('Canopy strip housing',(x,-.32,2.698),(.86,.094,.055),dark,.016)
        box('Diffused service strip',(x,-.323,2.665),(.77,.06,.013),warm,.006)
    box('Counter cabinet',(0,-.403,.535),(5.11,.78,.91),old,.033)
    box('Recessed plinth',(0,-.378,.139),(5.00,.73,.17),dark,.015)
    for i in range(36):
        x = (i-17.5)*.139
        for row in range(4):
            box('Glazed counter tile',(x,-.805,.291+.173*row),(.131,.05,.165),
                celadon[(i*3+row+((i+row)%6==0))%4] if row<3 else cream,.006)
    box('Oxide inset border',(0,-.835,.815),(5.05,.023,.028),brick,.005)
    box('Brass under-counter nosing',(0,-.808,.898),(5.18,.11,.041),gold,.008)
    box('Rounded counter slab',(0,-.417,.953),(5.22,.93,.109),walnut,.034)
    box('Inset serving surface',(0,-.44,1.01),(5.09,.801,.014),cream,.006)
    box('Back workbench',(0,1.17,.513),(5.15,.49,.851),walnut)
    box('Stainless prep top',(0,1.17,.963),(5.18,.53,.058),steel,.018)
    for x in (-2.14,-1.1,-.02,1.04,2.12):
        box('Cupboard pull',(x,.909,.789),(.16,.027,.024),gold,.007)

    # Projecting jade fascia with an original cup-and-steam medallion.
    plaque('Raised fascia back',0,-.743,3.05,5.70,.77,.276,.083,walnut,'Structure')
    plaque('Brass sign edge',0,-.886,3.06,5.56,.676,.039,.07,gold)
    plaque('Jade faceplate',0,-.916,3.06,5.47,.596,.033,.052,green)
    disc_front('Porcelain mark',-2.22,-.942,3.065,.217,.035,cream)
    disc_front('Jade mark field',-2.22,-.962,3.065,.189,.013,green)
    plaque('Cup silhouette',-2.238,-.974,3.018,.185,.095,.019,.039,warm)
    line_front('Cup handle',[(-2.16,3.055),(-2.118,3.053),(-2.109,3.034),(-2.124,3.01),(-2.162,3.01)],-.976,.011,warm)
    line_front('Saucer',[(-2.334,2.949),(-2.140,2.949)],-.975,.009,warm)
    for i in range(2):
        x = -2.263+.055*i
        line_front('Steam plumes',[(x,3.092),(x+.022,3.123),(x+.018,3.149),(x,3.178)],-.973,.009,warm)
    label('LORONG PAGI KOPITIAM',(-.01,-.939,3.119),.315,warm,3.84,extrude=.004)
    label('KOPI   /   KAYA TOAST   /   SOFT-BOILED EGGS',(-.03,-.939,2.912),.096,orange,3.52)
    plaque('Unit tag',2.25,-.957,3.073,.59,.245,.034,.03,brick)
    label('#01-08',(2.25,-.979,3.074),.118,cream,.466)

    # Shallow striped awning with rolled valance, under the sign rather than over it.
    for i in range(25):
        x = (i-12)*.217
        p = [(-1.115,2.701),(-.774,2.778),(-.774,2.819),(-1.115,2.744)]
        prism('Canopy stripe',p,x-.109,x+.109,(cream,celadon[0])[i%2],'X',.004)
        box('Striped valance',(x,-1.103,2.673),(.215,.055,.078),(cream,celadon[0])[i%2],.009)

    # Kitchen menu strips and counter service details.
    for i,(item,price) in enumerate((('KOPI C','$2.00'),('TEH TARIK','$2.30'),('KAYA SET','$5.20'))):
        x = (i-1)*1.60
        for bracket in (-.55,.55):
            box('Suspended menu bracket',(x+bracket,.22,2.51),(.033,.042,.47),gold,.007)
        plaque('Timber menu frame',x,.22,2.081,1.53,.46,.076,.035,walnut)
        plaque('Backlit menu panel',x,.173,2.081,1.42,.37,.033,.024,dark)
        label(item,(x,.151,2.128),.158,warm,1.29)
        label(price,(x,.151,1.986),.096,orange)
    for x,txt in ((-1.63,'ORDER / PESAN'),(1.81,'PICK UP / AMBIL')):
        plaque('Counter station plate',x,-.841,.668,1.12,.211,.03,.023,green)
        label(txt,(x,-.859,.67),.103,cream,1.03)

    # Glass toast case with trays and individual bread wedges.
    x,y = -1.56,-.432
    box('Display case wooden base',(x,y,1.073),(1.37,.54,.115),walnut,.026,prop)
    box('Display case top light rail',(x,y,1.528),(1.373,.55,.042),gold,.01,prop)
    for sx in (-1,1):
        for sy in (-1,1):
            box('Glass case post',(x+.66*sx,y+.254*sy,1.299),(.031,.032,.454),gold,.007,prop)
        xx=x+.674*sx
        mesh('Display side glass',[(xx,y-.254,1.12),(xx,y+.254,1.12),(xx,y+.254,1.51),(xx,y-.254,1.51)],
             [(0,1,2,3)],glass,group='Glazing')
    pane('Display case front glass',x,y-.265,1.315,1.32,.387,glass)
    for i in range(2):
        z = 1.134+i*.179
        box('Toast display tray',(x,y,z),(1.24,.475,.033),steel,.013,prop)
        for j in range(5):
            xx=x+(j-2)*.227
            prism('Toast crust',[ (xx-.094,z+.02),(xx+.093,z+.02),(xx-.029,z+.153)],
                  -y-.055,-y+.07,crust,'NEG_Y',.009,prop)
            prism('Toast cut face',[(xx-.078,z+.03),(xx+.073,z+.029),(xx-.025,z+.14)],
                  -y+.069,-y+.075,toast,'NEG_Y',.002,prop)
    x,y = .25,-.385
    lathe('Kettle belly',x,y,[(.117,1.018),(.143,1.045),(.168,1.12),(.168,1.232),(.129,1.305),
                            (.105,1.313),(.105,1.33),(.059,1.346),(.036,1.351)],steel,group=prop)
    lathe('Kettle lid knob',x,y,[(.024,1.342),(.034,1.36),(.034,1.392),(.024,1.400)],dark,group=prop)
    tube('Kettle curved pour spout',[(x+.12,y,1.14),(x+.224,y-.011,1.175),(x+.278,y-.015,1.237),
                                   (x+.31,y-.016,1.332)],.031,steel,prop,sides=14)
    tube('Kettle wrapped handle',[(x-.112,y,1.305),(x-.224,y,1.289),(x-.264,y,1.229),
                                 (x-.237,y,1.161),(x-.15,y,1.143)],.021,dark,prop)
    for i in range(4):
        z=1.018+i*.016
        lathe('Stacked kopitiam saucer',1.55,-.405,[(.085,z),(.105,z+.015),(.11,z+.017),(.083,z+.017)],cream,24,prop)
    for i in range(3):
        x=1.25+.31*i
        lathe('Kopitiam cup',x,-.215,[(.047,1.025),(.054,1.04),(.064,1.113),(.062,1.125),
                                    (.055,1.125),(.05,1.058)],cream,24,prop)
        tube('Cup ear',[(x+.056,-.215,1.11),(x+.087,-.215,1.111),(x+.095,-.215,1.086),
                        (x+.081,-.215,1.065),(x+.055,-.215,1.062)],.009,cream,prop)
    deliver((.35,-1,.236),'ACBBB0')


if __name__ == '__main__':
    build()
