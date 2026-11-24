"""Paya Lebar airmail writing bureau with envelope pigeonholes, a posting chute and hand canceller.
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


TITLE='Mel Udara | Aerogram bureau'
reset()
navy,blue,red,paper,oat,wood,gold,rubber=colors(PostalNavy='24485E',AirlineBlue='5398AB',PostRed='C95447',Airletter='FAE8C4',Parchment='DDBE8F',Teak='99684C',Brass='BF9D66 .3 .55',Rubber='343C40')
# Splayed trestles support a wing-tipped correspondence desk.
for s in (-1,1):
    p=[(s*1.17,0),(s*.98,0),(s*.78,.84),(s*.99,.84)]
    polygon('Splayed writing desk leg',p,.018,.53,wood,'Trestle')
    box('Foot slipper',(s*1.072,.018,.035),(.225,.55,.070),navy,.021,'Trestle')
box('Stretcher',(0,.206,.322),(2.13,.088,.092),navy,.020,'Trestle')
slab('Blue wing edge',0,0,.82,2.63,1.02,.090,.23,navy)
slab('Birch writing surface',0,0,.91,2.61,1.00,.065,.225,oat)
# Pegboard back and pigeonholes with a genuine open front.
plaque('Blue backboard',-.22,.343,1.482,2.16,1.02,.106,.128,blue,'Casework')
for x in (-1.13,-.715,-.30,.115): box('Pigeonhole upright',(x,.169,1.392),(.038,.315,.606),wood,.009,'Casework')
for z in (1.09,1.377,1.682): box('Pigeonhole shelf',(-.508,.169,z),(1.29,.329,.039),wood,.010,'Casework')
for j in range(2):
    for k in range(3):
        x=-.922+.415*k; z=1.115+.286*j
        for l in range((j+k)%3+1):
            slab('Stack of folded airletters',x,.119,z+.025*l,.333,.210,.024,.012,paper if l%2==0 else oat,'Stationery')
        plaque('Sorting tab',x,-.004,z-.024,.15,.043,.010,.009,gold)
        word(f'{j+1}{chr(65+k)}',x,-.014,z-.024,.030,navy,.126)
# Route tablet and original paper-plane insignia under the vintage postmark.
plaque('Header cartouche',-.48,.275,1.846,1.39,.192,.035,.077,navy)
word('M E L   U D A R A',-.48,.249,1.853,.111,paper,1.25)
slab('Post box',.714,.077,.975,.755,.657,.778,.105,red,'Letter box')
slab('Post box lid',.714,.077,1.75,.786,.69,.067,.125,navy,'Letter box')
plaque('Posting flap frame',.714,-.258,1.557,.579,.139,.031,.055,gold,'Letter box')
plaque('Dark slot',.714,-.28,1.557,.49,.063,.018,.020,rubber,'Letter box')
plaque('Mail tablet',.714,-.258,1.270,.544,.296,.032,.065,paper)
word('S U R A T',.714,-.280,1.312,.090,navy,.482);word('PAYA  LEBAR',.714,-.280,1.209,.061,red,.464)
rod('Crest standard',(.71,.17,1.81),(.71,.17,2.05),.046,gold)
for y,r,d,m in [(.17,.386,.10,navy),(.111,.358,.027,paper),(.089,.31,.018,blue)]: disc_front('Postmark sign',.71,y,2.245,r,d,m,'Crest',60)
# A folded-paper plane, with a contrail of short broken strokes.
polygon('Plane silhouette',[(.482,2.256),(.932,2.399),(.799,2.112),(.705,2.20),(.624,2.137),(.626,2.207)],.071,.012,paper,'Crest')
polygon('Paper fold',[(.627,2.205),(.90,2.377),(.703,2.217),(.624,2.139)],.060,.009,navy,'Crest')
for i in range(3): line_front('Vapour trail',[(.472+.047*i,2.133+.015*i),(.503+.047*i,2.145+.016*i)],.068,.005,paper)
# A writing blotter, tiled airmail edging, letter, pen and hand cancellation stamp.
slab('Leather blotter',-.49,-.237,.976,1.06,.386,.013,.054,navy,'Stationery')
slab('Airletter',-.58,-.235,.990,.51,.25,.010,.007,paper,'Stationery')
for s in (-1,1):
    for i in range(11):
        x=-.819+i*.045; y=-.235+s*.106
        prism('Airmail stripe',[(x,y-.008),(x+.020,y-.008),(x+.036,y+.008),(x+.015,y+.008)],1.001,1.004,red if i%2 else blue,group='Stationery')
for j in range(3): box('Ruled address',(-.575,-.26+j*.026,1.004),(.17,.003,.002),blue,0,'Stationery')
box('Postage stamp',(-.387,-.182,1.005),(.055,.048,.004),red,.002,'Stationery')
rod('Writing pen',(-.232,-.354,1.005),(-.088,-.162,1.005),.011,blue)
lathe('Cancellation stamp',.161,-.231,.976,[(.064,0),(.064,.027),(.034,.038),(.020,.103),(.041,.130),(.043,.156),(.031,.173)],wood)
lathe('Stamp sole',.161,-.231,.975,[(.064,0),(.065,.012)],rubber)
deliver((-.40,-1,.42),'B5C0C2',1.13)
