"""Original SG/MY mall prepaid SIM vending and activation alcove: Nadi Data.
Envelope approximately 2.80 x 1.31 x 2.65 m. Origin at floor level on the
alcove centreline; face -Y (+Z in glTF). Static visual geometry: the UI and
payment details are fictional and non-functional. No brand or textures.
Blender 5.2.3: blender -b --python generate.py
"""

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
        scene.cycles.samples = 18
        scene.cycles.max_bounces = 5
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.58
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 880
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
    flags = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    export = '--preview-only' not in flags
    print(f'{TITLE}: {sum(len(o.data.polygons) for o in objs):,} triangles')
    if export:
        bpy.ops.export_scene.gltf(filepath=str(dest/'model.glb'), export_format='GLB',
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=19,
                                  export_draco_normal_quantization=12,
                                  export_draco_texcoord_quantization=16,
                                  export_cameras=False, export_lights=False,
                                  export_animations=False, export_extras=True)
        assert (dest/'model.glb').stat().st_size <= 2_000_000
    if '--export-only' in flags:
        return
    scene = studio(direction, backdrop, margin, engine)
    scene.render.filepath = str(dest/'preview.png')
    bpy.ops.render.render(write_still=True)


# Purpose-built details. Unless stated otherwise, lettering faces the customer at -Y.
def palette(spec):
    return {name: mat(name, *properties.split()) if ' ' not in properties else
            mat(name, properties.split()[0], *map(float, properties.split()[1:]))
            for name, properties in spec.items()}


def band(x, y, z, w, h, lining, ink, line, size=None, group='Graphics'):
    plaque(line + ' | panel', x, y, z, w, h, .026, min(h*.34,.092), lining, group)
    label(line, (x,y-.015,z), size or h*.52, ink, w*.9, group=group)


def framed(x, y, z, w, h, rim, inner, title, detail, ink, accent):
    plaque(title+' | frame', x,y,z,w,h,.068,.059,rim)
    plaque(title+' | print', x,y-.036,z,w-.07,h-.07,.012,.037,inner)
    label(title,(x,y-.044,z+h*.19),h*.21,ink,w*.83)
    box(title+' | rule',(x,y-.045,z+h*.02),(w*.7,.004,.009),accent,.001,'Graphics')
    label(detail,(x,y-.044,z-h*.16),h*.113,ink,w*.81)


def bar(name, a, b, width, depth, material, group='Structure', bevel=.006):
    a,b = Vector(a),Vector(b)
    obj = box(name,(0,0,0),(width,depth,(b-a).length),material,bevel,group)
    obj.location = (a+b)/2
    obj.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    return obj


def rail(name, a, b, radius, material, group='Structure', sides=12):
    return tube(name,[a,b],radius,material,group,sides)


def patch(name, outline, y, material, group='Graphics'):
    return prism(name,outline,-y-.002,-y+.002,material,'NEG_Y',group=group)


def diamond(name,x,y,z,w,h,material):
    return patch(name,[(x+w/2,z),(x,z+h/2),(x-w/2,z),(x,z-h/2)],y,material)


def globe(name, xyz, radii, material, group='Fixtures', phase=0.0, sides=14, bands=8):
    x,y,z = xyz
    rx,ry,rz = radii
    co,si = math.cos(phase),math.sin(phase)
    points = [(x,y,z-rz)]
    for j in range(1,bands):
        t = -PI/2+PI*j/bands
        for i in range(sides):
            a = TAU*i/sides
            u,v = rx*math.cos(t)*math.cos(a), ry*math.cos(t)*math.sin(a)
            points.append((x+co*u-si*v,y+si*u+co*v,z+rz*math.sin(t)))
    points.append((x,y,z+rz))
    faces = []
    for i in range(sides):
        i1,j1 = i+1,(i+1)%sides+1
        faces.append((0,j1,i1))
        for q in range(bands-2):
            a,b = q*sides+i1,q*sides+j1
            faces.append((a,b,b+sides,a+sides))
        faces.append((i1+(bands-2)*sides,j1+(bands-2)*sides,len(points)-1))
    return mesh(name,points,faces,material,group=group,smooth=True)


def plant(x,y,z,scale,pot,soil,greens,seed):
    rng = random.Random(seed)
    lathe('Tapered planter',x,y,[(r*scale,z+h*scale) for r,h in
          ((.17,0),(.19,.02),(.23,.31),(.23,.35),(.205,.35),(.195,.30))],pot,24,'Planting')
    lathe('Potting bed',x,y,[(.209*scale,z+.301*scale),(.209*scale,z+.324*scale)],soil,24,'Planting')
    for i in range(12):
        a = TAU*i/12+rng.uniform(-.17,.17)
        d = Vector((math.cos(a),math.sin(a),0))
        e = Vector((-d.y,d.x,0))
        base = Vector((x,y,z+scale*.31))
        run, height = rng.uniform(.16,.49)*scale,rng.uniform(.36,.72)*scale
        root = base+.064*scale*d
        mid = base+run*.39*d+Vector((0,0,height*.89))
        tip = base+run*d+Vector((0,0,height))
        width = e*scale*rng.uniform(.066,.108)
        fold = mid+Vector((0,0,.034*scale))
        rail('Leaf stem',root,mid,.006*scale,greens[0],'Planting',6)
        fs = [(0,1,4),(0,4,3),(1,2,4),(4,2,3)]
        mesh('Folded tropical leaf',[root, mid-width,tip,mid+width,fold], fs+[
             tuple(reversed(f)) for f in fs],greens[i%len(greens)],group='Planting')


def rotated_box(name, center, dims, angle, material, group='Fixtures', bevel=.011):
    o = box(name,(0,0,0),dims,material,bevel,group)
    o.location = center
    o.rotation_euler.z = angle
    return o


def ceiling_light(x,y,z,w,frame,lens):
    box('Linear luminaire housing',(x,y,z),(w,.075,.045),frame,.009,'Lighting')
    box('Warm diffuser',(x,y,z-.024),(w-.06,.043,.010),lens,.003,'Lighting')


def seat(x,y,z,mat_frame,mat_shell,sw=.43):
    box('Seat foot frame',(x,y,z+.045),(sw,.43,.090),mat_frame,.026,'Seating')
    box('Seat pedestal',(x,y,z+.21),(sw*.54,.31,.34),mat_frame,.028,'Seating')
    box('Seat cushion',(x,y,z+.417),(sw,.45,.105),mat_shell,.047,'Seating')
    box('Seat back',(x,y-.19,z+.62),(sw,.10,.405),mat_shell,.046,'Seating')


TITLE = 'Nadi Data | Prepaid SIM Alcove'
reset()
m = palette(dict(Slate='273850', Graphite='394651', Panel='6F7D8B', Pale='E4E8D9',
      Heliotrope='775893', Orchid='BA93CA', Acid='D6E797 .36 0 .28',
      Moss='63825E', Neon='A9EBDA .33 0 .77', Glass='DCEFEF .22 0 0 .095',
      Peach='F4B682', Blue='8BC3D7', Mint='BEDBB2', Steel='92A6AE .31 .64'))
box('Alcove skirting pad',(0,.11,.040),(2.80,1.12,.08),m['Graphite'],.024)
box('Alcove ribbed wall backing',(0,.626,1.327),(2.80,.126,2.50),m['Heliotrope'],.048)
for i in range(15):
    box('Moulded wall acoustic fin',(-1.25+i*.18,.550,1.252),(.048,.072,2.28),m['Orchid'],.013,'Cladding')
for x in (-1.32,1.32):
    box('Alcove wing',(x,.365,1.327),(.138,.52,2.50),m['Slate'],.027)
box('Lighting canopy',(0,.278,2.49),(2.8,.837,.168),m['Slate'],.039)
plaque('Data alcove wall header',0,-.157,2.458,2.74,.377,.136,.113,m['Slate'])
label('NADI DATA',(-.038,-.231,2.520),.232,m['Acid'],1.77)
label('SIM PRABAYAR  /  VISITOR DATA',(-.038,-.231,2.366),.073,m['Pale'],1.85)
# Stylised bars suggest signal quality without using a provider logo.
for i in range(4):
    h = .043+i*.027
    box('Signal emblem bar',(-1.19+i*.076,-.227,2.45+h/2),(.042,.014,h),m['Orchid'],.005,'Graphics')
band(1.038,-.233,2.475,.49,.152,m['Heliotrope'],m['Pale'],'SG / MY',.091)
ceiling_light(0,.08,2.378,2.43,m['Heliotrope'],m['Neon'])
# The vending unit holds card packs, a touch display and an offset payment reader.
x = -.54
box('Data vending unit chassis',(x,.066,1.153),(1.45,.89,2.15),m['Slate'],.062,'Dispenser')
plaque('Vending machine contrast face',x,-.385,1.18,1.39,2.00,.083,.092,m['Heliotrope'],'Dispenser')
plaque('Product display surround',x-.246,-.429,1.479,.842,1.057,.086,.073,m['Slate'],'Dispenser')
box('Stock display back', (x-.246,-.473,1.479),(.722,.030,.920),m['Graphite'],.009,'Product Bay')
for row,(type_name,style) in enumerate([('SG','Peach'),('MY','Blue'),('DUO','Mint')]):
    z = 1.212+row*.274
    box('Product track shelf',(x-.245,-.50,z-.095),(.75,.115,.034),m['Steel'],.006,'Product Bay')
    for k in range(3):
        px = x-.493+.244*k
        plaque('Visitor SIM card pack',px,-.527,z+.019,.202,.186,.033,.018,m[style],'Product Bay')
        plaque('Card data stripe',px,-.546,z+.059,.152,.043,.008,.010,m['Slate'],'Product Bay')
        label(type_name,(px,-.552,z+.058),.053,m['Pale'],.114,group='Product Bay')
        # Metallic chip contact illustration.
        for t in (-1,1):
            for u in (-1,1):
                box('Chip contact print',(px+.020*t,-.548,z-.009+.018*u),(.033,.004,.013),
                    m['Steel'],.002,'Product Bay')
for s in (-1,1):
    box('Glass display upright',(x-.246+s*.39,-.545,1.479),(.052,.126,1.04),m['Slate'],.010,'Dispenser')
for z in (.975,1.984):
    box('Glass display cap',(x-.246,-.546,z),(.82,.125,.045),m['Slate'],.008,'Dispenser')
pane('Vending safety glass',x-.246,-.606,1.48,.751,.986,m['Glass'])
framed(x+.433,-.429,1.681,.443,.494,m['Slate'],m['Neon'],'SIM / eSIM','PILIH PELAN',m['Slate'],m['Moss'])
for z,k,t in [(1.317,1,'BAYAR'),(1.147,2,'AMBIL')]:
    plaque('NFC reader recess' if k==1 else 'Receipt slot',x+.435,-.445,z,.384,.124,.058,.032,m['Slate'],'Dispenser')
    label(t,(x+.436,-.478,z),.058,m['Acid'],.29)
plaque('Vend retrieval recess',x,-.442,.570,1.043,.257,.09,.064,m['Graphite'],'Dispenser')
plaque('Retrieval push flap',x,-.491,.589,.840,.143,.026,.035,m['Slate'],'Dispenser')
label('AMBIL SIM  /  COLLECT SIM',(x,-.508,.588),.089,m['Pale'],.743)
band(x,-.452,2.085,1.06,.153,m['Acid'],m['Slate'],'PELAWAT / VISITOR',.085)
# Activation and USB shelf is a separate standing-height surface, not another kiosk.
framed(.815,.476,1.71,.854,.748,m['Slate'],m['Pale'],'AKTIFKAN','ACTIVATE YOUR SIM',m['Slate'],m['Heliotrope'])
box('Activation shelf cleat',(.811,.249,.909),(.79,.49,.15),m['Heliotrope'],.029,'Activation Shelf')
box('Activation shelf lip',(.811,.248,1.004),(.883,.57,.090),m['Pale'],.029,'Activation Shelf')
for px in (.648,.980):
    plaque('USB power outlet block',px,.436,1.093,.227,.113,.096,.021,m['Slate'],'Activation Shelf')
    for i in (-1,1):
        plaque('Type C charge port',px+i*.044,.385,1.091,.058,.023,.011,.010,m['Steel'],'Activation Shelf')
band(.809,-.049,1.005,.52,.064,m['Heliotrope'],m['Pale'],'CAS USB',.038)
plant(.825,.212,.080,.81,m['Heliotrope'],m['Graphite'],[m['Moss'],m['Mint']],940)
deliver((.27,-1,.27),'B6B2C2',margin=1.18)
