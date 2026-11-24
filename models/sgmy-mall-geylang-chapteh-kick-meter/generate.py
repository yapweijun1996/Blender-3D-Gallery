"""Geylang chapteh arcade kick meter with a feather crest, kick pad and stepped light ladder.
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


TITLE='Sepak Tinggi | Chapteh kick meter'
reset()
purple,mid,red,gold,cream,turq,black,halo,peach=colors(Aubergine='42364F',InkPlum='59425F',Chilli='D7564A',Kuning='F1AB4F',Ivory='FFE8BC',EnamelMint='69BAAB',Rubber='313438',ScoreLamp='FFE296 .32 0 .5',Coral='EE9072')
slab('Moulded floor mat',0,-.1,0,1.08,1.55,.08,.22,black)
slab('Apron',0,-.12,.08,1.01,1.47,.045,.20,turq)
slab('Heel zone',0,-.44,.125,.79,.70,.021,.12,purple)
for x in (-.22,.22):
    for j in range(4): box('Traction rib',(x,-.64+j*.074,.151),(.24,.017,.012),mid,.005,'Pedal')
polygon('Booth silhouette',[(-.48,.124),(.48,.124),(.43,.53),(.29,.68),(.29,1.96),(.38,2.12),(.28,2.24),(-.28,2.24),(-.38,2.12),(-.29,1.96),(-.29,.68),(-.43,.53)],.30,.47,purple,'Tower')
for s in (-1,1):
    line_front('Cabinet piping',[(s*.42,.22),(s*.39,.47),(s*.25,.66),(s*.25,1.96),(s*.32,2.11)],.048,.019,red)
# Remotely visible light ladder with ascending colours; the numerals are static score graphics.
plaque('Scoreboard',0,.043,1.41,.392,1.16,.046,.090,black)
for i in range(12):
    z=.928+i*.085; w=.084+.007*i
    plaque('Score segment',-.026,.010,z,w,.048,.021,.019,turq if i<4 else gold if i<8 else red)
    if i in (0,3,6,9): word(str((i+1)*10),.126,-.004,z,.049,cream,.08)
plaque('Upper playfield',0,.007,2.092,.764,.286,.104,.12,gold)
plaque('Title ground',0,-.059,2.092,.724,.25,.039,.10,purple)
word('CHAPTEH',0,-.085,2.119,.130,cream,.62);word('G E Y L A N G',0,-.085,2.027,.046,peach,.47)
# Chapteh: stacked rubber washers and three graphic vanes with notched trailing edges.
lathe('Washer stack',0,.30,2.215,[(.158,0),(.161,.049),(.143,.055),(.153,.091),(.113,.106),(.091,.168)],red)
rim('Binding',0,.30,2.273,.145,.014,gold)
for i,(dx,dz,w,m) in enumerate([(-.27,.49,.111,turq),(.036,.63,.135,red),(.266,.43,.108,gold)]):
    x0=(i-1)*.035; z0=2.355; y=.25-i*.034
    def quill(t):return (x0+dx*(.55*t+.45*t*t),z0+dz*t)
    border=[]
    for side in (1,-1):
        ticks=range(17) if side==1 else reversed(range(17))
        for j in ticks:
            t=j/16; x,z=quill(t); b=(.010+w*sin(PI*t)**.75)*(.70 if j in (5,9,13) and side==1 else 1)
            border.append((x+side*b,z-side*dx/dz*b))
    polygon('Notched feather',border,y,.041,m,'Crest')
    line_front('Feather shaft',[quill(j/12) for j in range(13)],y-.031,.009,cream)
    for j in (3,6,9):
        x,z=quill(j/12); line_front('Vane rib',[(x,z),(x+.68*w,z+.057)],y-.031,.005,cream)
plaque('Instruction plate',0,.044,.712,.41,.138,.026,.046,gold)
word('SEPAK TINGGI',0,.025,.712,.054,purple,.35)
# Resilient kick paddle with a heel-side target. No moving parts are assumed by the GLB.
rod('Swivel arm',(0,.26,.28),(0,-.30,.415),.070,black)
for y,r,d,m in [(-.29,.178,.102,purple),(-.36,.158,.065,red),(-.402,.107,.024,cream),(-.421,.065,.022,red)]: disc_front('Padded kick target',0,y,.413,r,d,m,'Pedal',40)
for x in (-.31,.31): dot('Service screw',x,.047,.304,.024,gold)
deliver((.44,-1,.31),'BCC0B6',1.10)
