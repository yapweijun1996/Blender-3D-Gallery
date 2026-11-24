"""Build a static, original SG/MY mall pharmacy frontage.
Origin: facade centreline at the subfloor base (0,0,0). The entry is
open; glazed leaves are parked and static. Recess the subfloor lip.

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


TITLE = 'Farmasi Selasar'


def build():
    reset()
    blue = mat('Deep Petrol Powder Coat','154552',.36)
    blue2 = mat('Sea Glass Enamel','357581',.40)
    teal = mat('Clinical Teal Vinyl','007C77',.43)
    ivory = mat('Warm White Composite','F6F0E1',.43)
    mint = mat('Dew Mint Composite','B9DBD1',.42)
    graphite = mat('Graphite Kick Plate','2B3438',.52)
    floor = mat('Ivory Vinyl Tile','D8D7CB',.63)
    joint = mat('Pale Floor Seam','AAAFA8',.78)
    bright = mat('Backlit Opal White','FFFAE7',.4,glow=1.0)
    glow = mat('Turquoise Wayfinding Light','63EACB',.44,glow=1.3)
    glass = mat('Low-Iron Glazing','BAE9DA',.14,alpha=.16)
    metal = mat('Satin Anodised Aluminium','BBC2BF',.30,.62)
    leaf = mat('Vitamin Package Fern','8CBA89',.47)
    violet = mat('Wellness Package Lilac','A99CCA',.47)
    peach = mat('Care Package Apricot','E1AC86',.47)
    aqua = mat('Hygiene Package Blue','79B5C8',.47)
    copper = mat('Amber Bottle Polymer','9B5A3A',.31)
    stock = 'Retail Display'
    palette = [leaf, violet, peach, aqua]

    # Open entry at x=-.55; shallow shell sized for a modular retail bay.
    box('Floor bed',(0,.583,.031),(5.49,2.65,.062),joint)
    for i in range(11):
        for j in range(5):
            box('Inset shop floor tile',(-2.475+i*.495,-.478+j*.521,.067),(.490,.516,.016),floor,.002)
    box('Door saddle',(-.56,-.734,.031),(2.30,.105,.062),metal,.004)
    box('Back wall',(0,1.831,1.56),(5.48,.15,3.02),mint,.017)
    for x in (-2.65,2.65):
        box('Solid return wall',(x,.554,1.57),(.175,2.59,3.11),blue2,.024)
        box('Return wall kick plate',(x,-.015,.117),(.198,1.43,.234),graphite,.009)
    box('Front header structure',(0,-.61,2.924),(5.49,.39,.82),blue,.031)
    box('Ceiling white slot',(0,.705,2.961),(5.25,2.25,.13),ivory,.022)
    for x in (-1.74,0,1.74):
        box('Ceiling diffuser channel',(x,.351,2.880),(.95,.095,.048),metal,.012)
        box('Backlit ceiling strip',(x,.346,2.85),(.87,.064,.016),bright,.007)
    box('Plinth at left',(-2.33,-.646,.107),(.75,.275,.214),graphite,.014)
    box('Mint pier at left',(-2.33,-.654,1.424),(.76,.24,2.43),mint,.026)
    box('Header soffit bead',(0,-.809,2.533),(5.38,.031,.028),glow,.008)
    for i in range(8):
        box('Ventilated pier fins',(-2.63+.065*i,-.789,2.324),(.018,.032,.231),blue,.003)

    # Deliberately original roundel: four offset capsules around a central negative space.
    disc_front('Medical roundel background',-2.187,-.831,2.943,.270,.087,ivory)
    disc_front('Roundel teal inlay',-2.187,-.884,2.943,.224,.031,teal)
    for xx,zz,ww,hh in ((0,.111,.078,.126),(0,-.111,.078,.126),(.111,0,.126,.078),(-.111,0,.126,.078)):
        plaque('Roundel capsule',-2.187+xx,-.904,2.943+zz,ww,hh,.012,.037,bright)
    disc_front('Roundel centre',-2.187,-.903,2.943,.025,.01,glow,sides=20)
    label('FARMASI SELASAR',(-.126,-.822,3.03),.338,bright,3.54,extrude=.004)
    label('PHARMACY   /   UBAT & PENJAGAAN',(-.126,-.822,2.789),.108,glow,3.31)
    plaque('Unit plaque',2.20,-.833,2.954,.654,.223,.043,.048,teal)
    label('#01-10',(2.20,-.862,2.958),.118,bright,.535)

    # Rail-mounted door leaves shown parked open; a separate large display window at right.
    box('Sliding door rail',(-.65,-.667,2.459),(2.67,.156,.118),metal,.012)
    for x in (-1.99,-1.64,.456,.628,2.659):
        box('Shop glazing mullion',(x,-.661,1.27),(.044,.128,2.43),metal,.007)
    pane('Parked left glass door',-1.812,-.69,1.245,.316,2.35,glass)
    box('Left door pull',(-1.672,-.754,1.215),(.027,.051,.316),metal,.012)
    pane('Parked right glass door',.537,-.69,1.245,.115,2.35,glass)
    box('Right door pull',(.470,-.754,1.215),(.024,.05,.316),metal,.011)
    pane('Retail display glazing',1.643,-.649,1.429,1.98,1.96,glass)
    box('Window display sill',(1.642,-.439,.406),(2.068,.554,.12),blue,.02)
    box('Window base panel',(1.643,-.658,.219),(2.03,.138,.38),teal,.019)
    label('HEALTH  /  KESIHATAN',(1.643,-.731,.223),.107,bright,1.70)
    box('Glass manifestation band',(1.647,-.654,1.128),(1.978,.006,.047),mint,.001)
    for i in range(19):
        disc_front('Glass band square',.756+i*.099,-.659,1.129,.011,.005,teal,sides=4)
    plaque('Bilingual opening hours sign',-2.295,-.788,1.612,.589,.524,.028,.045,ivory)
    label('BUKA',(-2.295,-.806,1.755),.103,teal,.42)
    label('OPEN DAILY',(-2.295,-.806,1.629),.065,blue,.49)
    label('10:00–22:00',(-2.295,-.806,1.488),.075,blue,.49)

    # Behind the glass, shallow product shelves maintain a genuinely open walk-through.
    def carton(x,y,z,w,h,tone,depth):
        box('Muted retail carton',(x,y,z+h/2),(w,depth,h),ivory,.004,stock)
        box('Unbranded carton colour block',(x,y-depth/2-.001,z+h*.635),(w*.87,.004,h*.54),tone,.001,stock)
        box('Unbranded carton copy',(x,y-depth/2-.0035,z+h*.187),(w*.61,.002,h*.045),blue2,0,stock)
    def bottle(x,y,z,r,h,tone):
        lathe('Amber or opaque supplement bottle',x,y,[(r*.85,z),(r,z+.01),(r,z+h*.78),
               (r*.78,z+h*.88),(r*.60,z+h*.91),(r*.60,z+h)],tone,16,stock)
        lathe('Plain white cap',x,y,[(r*.72,z+h*.88),(r*.73,z+h*1.035),(r*.68,z+h*1.065)],ivory,16,stock)
        lathe('Bottle paper band',x,y,[(r*1.012,z+h*.20),(r*1.012,z+h*.65)],mint,16,stock)
    for base_x,width,near_y,zones in ((1.648,1.72,-.298,[.563,.884,1.205,1.526]),
                                       (-1.436,2.05,1.34,[.47,.825,1.18,1.535]),
                                       (.792,2.05,1.34,[.47,.825,1.18,1.535])):
        at_window = near_y < 0
        box('Stock rack display back',(base_x,near_y+.252,1.035),(width,.075,1.6),mint,.013,stock)
        for side in (-1,1):
            box('Stock rack display stile',(base_x+side*(width/2-.035),near_y+.132,1.075),(.054,.259,1.526),blue2,.008,stock)
        for row,z in enumerate(zones):
            box('Fronted stock shelf',(base_x,near_y+.096,z-.02),(width,.323,.04),ivory,.008,stock)
            box('Shelf price channel',(base_x,near_y-.067,z-.023),(width-.05,.016,.030),teal,.003,stock)
            for i in range(10):
                x=base_x+(i-4.5)*(width-.21)/10
                if (i+2*row)%7 in (0,1) and i!=0:
                    bottle(x,near_y+.046,z,.037+.004*(i%4),.129+(i%3)*.029,copper if row%2 else palette[i%4])
                else:
                    carton(x,near_y+.052,z,.101+.011*(i%3),.161+((i+row)%4)*.032,palette[(row+i//2)%4],.112)
                box('Blank shelf price label',(x,near_y-.077,z-.022),(.067,.003,.015),ivory,.001,stock)
        plaque('Retail shelf header',base_x,near_y+.033,1.919,width,.224,.065,.041,blue,stock)
        title='WELLNESS / SIHAT' if at_window else ('PRESCRIPTIONS / PRESKRIPSI' if base_x<0 else 'VITAMINS / VITAMIN')
        label(title,(base_x,near_y-.005,1.922),.092,bright,width-.13,group=stock)
    plaque('Care service mini panel',1.659,-.156,2.216,1.72,.278,.079,.06,ivory,stock)
    label('ASK OUR PHARMACIST',(1.659,-.202,2.216),.101,teal,1.53,group=stock)
    deliver((-.31,-1,.221),'B6C6D2')


if __name__ == '__main__':
    build()
