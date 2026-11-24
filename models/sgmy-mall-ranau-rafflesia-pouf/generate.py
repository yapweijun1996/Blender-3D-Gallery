"""Ranau atrium conversation pouf with five spotted Rafflesia lobes and an inset buttoned seat.
Original static mall asset. Metric, ground-centred, front -Y.
Rebuild: blender -b -P generate.py (local Python/Pillow for preview packing).
No external art, fonts or textures.
"""
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
        scene.cycles.samples = 14
        scene.cycles.max_bounces = 5
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.84
    scene.render.dither_intensity = 0.0
    scene.render.resolution_x = 780
    scene.render.resolution_y = 624
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
    objs[0]['origin_note'] = 'Ground centre; customer face toward Blender -Y.'
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
    # For noisier renders, use a locally installed Pillow (no network access).
    image = dest/'preview.png'
    if image.stat().st_size > 250_000:
        import subprocess
        compress = """from PIL import Image
import sys, os
p=sys.argv[1]
im=Image.open(p).convert('RGB')
for w in (780,740,700,660,620,580,530):
    out=im.resize((w,round(w*im.height/im.width)), Image.Resampling.LANCZOS)
    out=out.point([min(255,round(i/2)*2) for i in range(256)]*3)
    out.save(p,optimize=True)
    if os.path.getsize(p)<=250000: break
"""
        subprocess.run(['python3', '-c', compress, str(image)], check=True)
    assert image.stat().st_size <= 250_000

def colors(**swatches):
    return [mat(name, *([s.split()[0]] + [float(n) for n in s.split()[1:]])) for name,s in swatches.items()]

def slab(name,x,y,z,w,d,h,r,material,group='Cabinetry'):
    return prism(name,rounded(w,d,r,(x,y),7),z,z+h,material,bevel=min(.01,h*.14),group=group)

def polygon(name,xzs,y,depth,material,group='Decoration'):
    area=sum(a*d-b*c for (a,b),(c,d) in zip(xzs,xzs[1:]+xzs[:1]))
    return prism(name,xzs if area>0 else xzs[::-1],-y-depth/2,-y+depth/2,material,'NEG_Y',min(depth*.12,.008),group)

def waves(name,x,y,z,width,amp,count,material):
    for j in range(count):
        line_front(name,[(x+width*(i/40-.5),z+.050*j+amp*math.sin(i*PI/10)) for i in range(41)],y,.007,material)

def wall(name,x,y,z,w,h,d,r,m):
    return plaque(name,x,y,z,w,h,d,r,m,'Shell')



from math import sin, cos, sqrt, radians


def lathe(name,x,y,z,profile,m,group='Turned fittings',n=40,sy=1):
    """Revolve a skirt-to-lip profile; folds back for an open bowl."""
    vs=[(x+r*cos(i*TAU/n),y+sy*r*sin(i*TAU/n),z+h) for r,h in profile for i in range(n)]
    fs=[tuple(reversed(range(n)))]
    for k in range(len(profile)-1):
        for i in range(n):
            j=(i+1)%n; fs.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
    fs.append(tuple(range(len(vs)-n,len(vs))))
    o=mesh(name,vs,fs,m,group=group,smooth=True)
    for i in [0,-1]: o.data.polygons[i].use_smooth=False
    return o


def egg(name,x,y,z,rx,ry,rz,m,group='Sculpture',yaw=0,n=24,rings=12):
    vs=[(x,y,z-rz)]
    for j in range(1,rings):
        p=PI*(j/rings-.5)
        for i in range(n):
            a=TAU*i/n; u=rx*cos(p)*cos(a); v=ry*cos(p)*sin(a)
            vs.append((x+u*cos(yaw)-v*sin(yaw),y+u*sin(yaw)+v*cos(yaw),z+rz*sin(p)))
    vs.append((x,y,z+rz)); fs=[]
    for i in range(n):
        j=(i+1)%n; fs.extend([(0,1+j,1+i),(len(vs)-n-1+i,len(vs)-n-1+j,len(vs)-1)])
        for k in range(rings-2):
            q=1+k*n; fs.append((q+i,q+j,q+n+j,q+n+i))
    return mesh(name,vs,fs,m,group=group,smooth=True)


def wire(name,points,r,m,group='Metalwork',sides=12):
    return tube(name,points,r,m,group,sides)


def rod(name,a,b,r,m,group='Metalwork',sides=16):
    return wire(name,[a,b],r,m,group,sides)


def loop_front(name,x,y,z,r,thick,m,n=64):
    # Use a parallel normal to prevent axial twist on vertical hoops.
    return tube(name,[(x+r*cos(TAU*i/n),y,z+r*sin(TAU*i/n)) for i in range(n+1)],thick,m,'Metalwork',12,reference=(0,1,0))


def word(s,x,y,z,size,m,width=None):
    return label(s,(x,y,z),size,m,width)


def dot(name,x,y,z,r,m,group='Decoration'):
    return disc_front(name,x,y,z,r,.008,m,group,20)


def rim(name,x,y,z,r,thick,m):
    return tube(name,[(x+r*cos(TAU*i/56),y+r*sin(TAU*i/56),z) for i in range(57)],thick,m,'Turned fittings',10,reference=(0,0,1))


TITLE='Bunga Ranau | Rafflesia pouf'
reset()
terracotta,brick,apricot,ochre,saffron,leaf,forest,cream,brass=colors(CoralVelvet='C5533F',RedClay='A94236',Papillae='F5C39E',DustedSienna='AD613B',GoldenPollen='EEAA50',Rainforest='659783',PineBase='284F4A',IvoryThread='FFE6BF',AntiqueBrass='BE995F .36 .5')
lathe('Stepped base',0,0,0,[(.89,0),(.93,.041),(.93,.105),(1.16,.13),(1.20,.20),(1.18,.27),(.88,.34)],forest,n=80)
rim('Skirting bead',0,0,.14,1.165,.014,brass)
# Five formed upholstered petals. Parametric top doubles as the template for spotted inlays.
def surface(i,u,v):
    a=TAU*i/5+.14
    w=.53*sin(PI*(.12+.88*u))**.59+.018
    radial=.30+1.036*u-.035*v*v
    sideways=v*w+.075*sin(PI*u)*(1 if i%2 else -1)
    z=.46+.158*sin(PI*(.03+.99*u))-.048*u+.046*cos(PI*u*1.8)*v*v-.091*v*v
    return (radial*cos(a)-sideways*sin(a),radial*sin(a)+sideways*cos(a),z)
rng=random.Random(8)
for i in range(5):
    nu,nv=21,14; vs=[]; fs=[]
    for layer in (0,1):
        for j in range(nu+1):
            for k in range(nv+1):
                u=j/nu; v=2*k/nv-1; x,y,z=surface(i,u,v)
                vs.append((x*(1-.045*layer),y*(1-.045*layer),z-layer*(.085+.07*sin(PI*u))))
    count=(nu+1)*(nv+1)
    for j in range(nu):
        for k in range(nv):
            p=j*(nv+1)+k; f=(p,p+nv+1,p+nv+2,p+1); fs.extend([f,tuple(count+q for q in reversed(f))])
    edge=[j*(nv+1) for j in range(nu+1)]+[nu*(nv+1)+k for k in range(1,nv+1)]+[j*(nv+1)+nv for j in reversed(range(nu))]+list(reversed(range(1,nv)))
    for p,q in zip(edge,edge[1:]+edge[:1]): fs.append((q,p,count+p,count+q))
    mesh('Cushioned lobe',vs,fs,brick if i%2 else terracotta,group='Corolla',smooth=True)
    wire('Welt', [vs[j] for j in edge+[edge[0]]],.009,ochre,'Corolla',8)
    for j in range(6):
        for k in range(5 if j<5 else 3):
            u=.20+j*.133+rng.uniform(-.031,.031); v=(k/(4 if j<5 else 2)-.5)*1.55+rng.uniform(-.07,.07)
            x,y,z=surface(i,u,v); size=rng.uniform(.025,.044)*(1.13-u*.37)
            egg('Dapple applique',x,y,z+.002,size*1.31,size*.78,.012,apricot,'Corolla embroidery',TAU*i/5+rng.uniform(-.8,.8),14,6)
# The rolled diaphragm surrounds a shallow golden cushion rather than a deep botanical cup.
lathe('Raised diaphragm',0,0,.45,[(.43,0),(.48,.07),(.462,.153),(.416,.211),(.34,.232),(.294,.193),(.292,.14)],terracotta,n=72)
rim('Pollen ruff',0,0,.651,.321,.017,apricot)
egg('Seat centre',0,0,.593,.314,.314,.065,saffron,'Cushions',n=48)
for i in range(8):
    a=TAU*i/8; egg('Button tuft',.191*cos(a),.191*sin(a),.645,.014,.014,.007,ochre,n=12,rings=6)
for i in range(34):
    a=TAU*i/34; egg('Throat fleck',.395*cos(a),.395*sin(a),.668,.019,.011,.009,cream,'Corolla embroidery',a,n=12,rings=6)
plaque('Museum cartouche',0,-1.204,.206,.56,.134,.049,.06,brass)
word('R A N A U',0,-1.234,.207,.084,forest,.45)
deliver((.34,-1,.89),'B9BFB0',1.13)
