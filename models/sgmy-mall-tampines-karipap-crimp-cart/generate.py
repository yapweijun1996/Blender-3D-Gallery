"""Lipat Emas, Tampines karipap pusing cart with an open fluted pastry press.
Rebuild with: blender -b -P generate.py [-- --export-only | --preview-only].
Original procedural mesh; metres, customer side -Y, static visual asset.
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
    scene.view_settings.exposure = -1.04
    scene.render.resolution_x = 760
    scene.render.resolution_y = 608
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.compression = 65
    return scene

def deliver(direction, backdrop, margin=1.19, engine='CYCLES'):
    objs = bake()
    dest = Path(__file__).resolve().parent
    assert abs(min(v.co.z for o in objs for v in o.data.vertices)) < 1e-6
    root = bpy.data.objects.new(TITLE, None)
    bpy.context.collection.objects.link(root)
    for obj in objs:
        obj.parent = root
    root['asset_id'] = dest.name
    root['origin_note'] = 'Floor datum at local (0, 0, 0); customer side faces -Y in Blender.'
    root['theme'] = 'Singapore / Malaysia mall'
    root['source_note'] = 'Original procedural geometry, solid PBR materials, built-in lettering.'
    root['units'] = 'metre'
    root['role'] = 'Static visual mesh (no collider or clips)'
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
    indexed_preview(dest / 'preview.png')

def colors(**swatches):
    return [mat(name, *([s.split()[0]] + [float(n) for n in s.split()[1:]])) for name,s in swatches.items()]

def slab(name,x,y,z,w,d,h,r,material,group='Cabinetry'):
    return prism(name,rounded(w,d,r,(x,y),7),z,z+h,material,bevel=min(.01,h*.14),group=group)

def polygon(name,xzs,y,depth,material,group='Decoration'):
    area=sum(a*d-b*c for (a,b),(c,d) in zip(xzs,xzs[1:]+xzs[:1]))
    return prism(name,xzs if area>0 else xzs[::-1],-y-depth/2,-y+depth/2,material,'NEG_Y',min(depth*.12,.008),group)

def turned(name,x,y,z,profile,m,group='Turned work',n=48,stretch=(1,1),flutes=0,ripple=0):
    """Revolve a radial section, from underside to lip and optionally back inside."""
    vs=[]
    for r,h in profile:
        for j in range(n):
            a=TAU*j/n
            rr=r*(1+ripple*math.cos(flutes*a))
            vs.append((x+stretch[0]*rr*math.cos(a),y+stretch[1]*rr*math.sin(a),z+h))
    fs=[tuple(reversed(range(n)))]
    for k in range(len(profile)-1):
        for j in range(n):
            a=k*n+j; b=k*n+(j+1)%n
            fs.append((a,b,b+n,a+n))
    fs.append(tuple(range(len(vs)-n,len(vs))))
    obj=mesh(name,vs,fs,m,group=group,smooth=True)
    for i in (0,-1): obj.data.polygons[i].use_smooth=False
    return obj

def ring(name,x,y,z,r,wire,m,group='Metalwork',n=48):
    # Closed torus with no doubled seam or end caps.
    vs=[]; fs=[]; k=8
    for i in range(n):
        a=i*TAU/n
        for j in range(k):
            b=j*TAU/k; rr=r+wire*math.cos(b)
            vs.append((x+rr*math.cos(a),y+rr*math.sin(a),z+wire*math.sin(b)))
            fs.append((i*k+j,((i+1)%n)*k+j,((i+1)%n)*k+(j+1)%k,i*k+(j+1)%k))
    return mesh(name,vs,fs,m,group=group,smooth=True)

def button(name,x,y,z,r,h,m,group='Fittings',n=32):
    return turned(name,x,y,z,[(r*.94,0),(r,.12*h),(r,.86*h),(r*.94,h)],m,group,n)

def oval(name,x,y,z,rx,ry,rz,m,group='Sculpture',n=32):
    profile=[(max(.01,math.cos(a)),rz*math.sin(a)) for a in [PI*(i/max(4,n//2)-.5) for i in range(max(4,n//2)+1)]]
    return turned(name,x,y,z,profile,m,group,n,(rx,ry))

def arch(name,x,y,z,w,h,d,m,group='Joinery'):
    r=w/2; spring=z+h-r
    pts=[(x-r,z),(x+r,z)]+[(x+r*math.cos(PI*i/40),spring+r*math.sin(PI*i/40)) for i in range(41)]
    return polygon(name,pts,y,d,m,group)

def star(name,x,y,z,r,m,points=8):
    polygon(name,[(x+r*(.49 if i%2 else 1)*math.cos(i*PI/points),z+r*(.49 if i%2 else 1)*math.sin(i*PI/points)) for i in range(points*2)],y,.006,m)

def badge(title,subtitle,x,y,z,w,h,field,ink):
    plaque('Enamel tablet',x,y,z,w,h,.032,min(h*.20,.06),field)
    label(title,(x,y-.019,z+h*.115),h*.46,ink,w*.86)
    label(subtitle,(x,y-.019,z-h*.245),h*.17,ink,w*.86)


def indexed_preview(path):
    """Use Blender's bundled NumPy to fit an indexed PNG if the RGB render is over budget."""
    if path.stat().st_size <= 245_000:
        return
    import struct, zlib
    import numpy as np
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    w, h = image.size
    raw = np.empty(w*h*4, dtype=np.float32)
    image.pixels.foreach_get(raw)
    rgb = (raw.reshape(h,w,4)[::-1,:,:3]*255+.5).astype('uint8')
    bpy.data.images.remove(image)
    def chunk(k,data):
        return struct.pack('>I',len(data))+k+data+struct.pack('>I',zlib.crc32(k+data))
    # Prefer a nearly lossless RGB file. Sub filtering compresses the studio sweep well.
    for step in (2,3,4,5,6):
        c=(np.rint(rgb/step)*step).clip(0,255).astype('uint8'); delta=c.copy(); delta[:,1:]-=c[:,:-1]
        scan=b''.join(b'\1'+row.tobytes() for row in delta); packed=zlib.compress(scan,9)
        if len(packed)<249_800:
            path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',packed)+chunk(b'IEND',b''))
            return
    # Split a weighted 6-bit/channel histogram, keeping the original mean colour of each cell.
    keys = (rgb[:,:,0].astype('int32')//4)*4096+(rgb[:,:,1].astype('int32')//4)*64+rgb[:,:,2]//4
    count=np.bincount(keys.ravel(),minlength=64**3)
    used=np.flatnonzero(count)
    color=np.column_stack([np.bincount(keys.ravel(),weights=c.ravel(),minlength=64**3)[used]/count[used] for c in rgb.transpose(2,0,1)])
    weights=count[used]
    groups=[np.arange(len(used))]
    def score(g):
        return 0 if len(g)<2 else np.ptp(color[g],axis=0).max()*np.sqrt(weights[g].sum())
    scores=[score(groups[0])]
    while len(groups)<256 and max(scores)>0:
        i=int(np.argmax(scores)); g=groups.pop(i); scores.pop(i)
        c=color[g]; axis=np.argmax(np.ptp(c,axis=0)); g=g[np.argsort(c[:,axis])]; s=weights[g].cumsum()
        j=min(len(g)-1,np.searchsorted(s,s[-1]*.5)+1)
        for v in [g[:j],g[j:]]:groups.append(v); scores.append(score(v))
    lut=np.zeros(64**3,dtype='uint8'); palette=[]
    for i,g in enumerate(groups):
        lut[used[g]]=i; palette.extend(np.round(np.average(color[g],axis=0,weights=weights[g])).astype('uint8'))
    data=b''.join(b'\0'+row.tobytes() for row in lut[keys]); packed=zlib.compress(data,9)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,3,0,0,0))+chunk(b'PLTE',bytes(palette))+chunk(b'IDAT',packed)+chunk(b'IEND',b''))
    assert path.stat().st_size<=250_000

from math import sin, cos, radians, sqrt

def disc(name,x,y,z,r,depth,m,group='Trim',sx=1,sz=1,n=48):
    return polygon(name,[(x+r*sx*cos(TAU*i/n),z+r*sz*sin(TAU*i/n)) for i in range(n)],y,depth,m,group)

def line(name,a,b,r,m,group='Trim'):
    return tube(name,[a,b],r,m,group,10)

def loop_xz(name,x,y,z,r,wire,m,group='Trim',sx=1,sz=1):
    return tube(name,[(x+r*sx*cos(TAU*i/64),y,z+r*sz*sin(TAU*i/64)) for i in range(65)],wire,m,group,8,reference=(0,1,0))

def lens(name,x,y,z,dx,dz,width,material):
    # Pointed silk-screen leaf in the front plane.
    pts=[]; length=math.hypot(dx,dz); nx=-dz/length; nz=dx/length
    for sign,ts in [(1,range(11)),(-1,range(9,0,-1))]:
        for i in ts:
            t=i/10; w=width*sin(t*PI)*sign
            pts.append((x+dx*t+nx*w,z+dz*t+nz*w))
    return polygon(name,pts,y,.003,material,'Inlay')


TITLE='Lipat Emas | Karipap crimp cart'
reset()
blue,red,cream,wood,metal,iron,dough,crust,brass=colors(PrussianBlue='233F52 .36',ChilliEnamel='AF4840 .42',FlourSack='F6E9CA',MapleBoard='CAA271',BrushedAluminium='9FADAB .32 .62',WheelRubber='313A3B .69',GoldenPastry='C98A3D .66',ToastedLayers='A8753B .71',WarmBrass='C29958 .33 .61')
# The cart rests on two tyres and a pair of parking feet. Customer side is the negative Y side.
for y in (-.39,.39):
    x=-.62;z=.216
    loop_xz('Rubber tyre',x,y,z,.188,.028,iron,'Undercarriage');loop_xz('Wheel rim',x,y,z,.166,.011,brass,'Undercarriage')
    for i in range(10):
        a=TAU*i/10;line('Wheel spoke',(x,y,z),(x+.165*cos(a),y,z+.165*sin(a)),.006,metal,'Undercarriage')
    disc('Axle nut',x,y,z,.045,.062,blue,'Undercarriage');
    line('Wheel fork',(x,y,z),(x+.077,y,.424),.025,iron,'Undercarriage')
    button('Parking foot',.70,y,0,.059,.034,iron,'Undercarriage');line('Stand leg',(.70,y,.034),(.65,y,.379),.026,metal,'Undercarriage')
slab('Rolled body',0,0,.337,1.83,.76,.53,.092,red)
slab('Lower belt',0,0,.341,1.84,.77,.032,.09,blue)
slab('Worktop lip',0,0,.862,1.95,.89,.039,.092,brass)
slab('Maple counter',0,0,.90,1.95,.90,.059,.089,wood)
for x in [-.81,-.75,-.69,.69,.75,.81]:box('Raised pressing',(x,-.38,.60),(.021,.013,.365),red,.005,'Coachwork')
badge('KARIPAP PUSING','L I P A T   E M A S    /    T A M P I N E S',0,-.390,.61,1.21,.298,cream,blue)
for y in (-.24,.24):tube('Push handle',[(.91,y,.773),(1.055,y,.79),(1.15,y,.913)],.018,metal,'Undercarriage',12,reference=(0,1,0))
line('Grip',(1.15,-.26,.913),(1.15,.26,.913),.027,blue,'Undercarriage')
# Press halves meet on a straight piano hinge; each half has a shallow basin and a serrated lip.
cx=-.46;cy=.055;cz=1.055
slab('Press foot',cx,-.003,.959,.55,.505,.071,.106,blue,'Crimper')
for side in (-1,1):button('Jaw support',cx+side*.19,cy,1.03,.036,.035,brass,'Crimper')
for theta,sign in [(0,-1),(radians(68),1)]:
    def pp(r,a,h):
        u=r*.291*cos(a);v=r*.228*sin(a)
        return (cx+u,cy+sign*v*cos(theta)-h*sin(theta),cz+v*sin(theta)+h*cos(theta))
    sec=[(.012,-.012),(.30,-.009),(.58,.002),(.79,.021),(.9,.039),(1,.041),(1,.020),(.91,.01),(.76,-.002),(.55,-.020),(.20,-.027),(.012,-.027)]
    n=41;vs=[pp(r,i*PI/(n-1),h) for r,h in sec for i in range(n)]
    fs=[(k*n+i,k*n+i+1,(k+1)*n+i+1,(k+1)*n+i) for k in range(len(sec)-1) for i in range(n-1)]
    fs+=[tuple(k*n for k in range(len(sec))),tuple(k*n+n-1 for k in range(len(sec)))]
    mesh('Half moon casting',vs,fs,metal,group='Crimper',smooth=True)
    for i in range(23):
        a=PI*(i+.5)/23
        tube('Crimp tooth',[pp(.83,a,.031),pp(.93,a,.049),pp(.988,a,.047)],.0064,cream,'Crimper',6)
    line('Finger lever',pp(.99,PI/2,.035),pp(1.29,PI/2,.034),.014,iron,'Crimper');line('Enamel grip',pp(1.29,PI/2,.034),pp(1.57,PI/2,.034),.026,blue,'Crimper')
line('Hinge pin',(cx-.299,cy,cz),(cx+.299,cy,cz),.016,brass,'Crimper')
# Pastries sit upright, their laminated crescents and hand-pinched seams facing the customer.
for y in (-.28,.27):box('Tray rail',(.47,y,1.005),(.812,.022,.022),metal,.006,'Cooling rack')
for x in (.09,.85):
    for y in (-.24,.24):button('Tray foot',x,y,.959,.016,.045,iron,'Cooling rack')
for i in range(19):line('Cooling wire',(.09+i*.042,-.28,1.016),(.09+i*.042,.27,1.016),.005,metal,'Cooling rack')
def pastry(x,y,z,s):
    n=27;pairs=[(1,0),(.99,-.012),(.85,-.029),(.56,-.043),(.014,-.047),(.014,.046),(.56,.043),(.85,.029),(.99,.012)]
    def p(r,a,depth):return (x+s*.114*r*cos(a),y+s*depth,z+s*(.001+.09*r*sin(a)))
    vs=[p(r,i*PI/(n-1),v) for r,v in pairs for i in range(n)]
    fs=[(k*n+i,k*n+i+1,(k+1)%len(pairs)*n+i+1,(k+1)%len(pairs)*n+i) for k in range(len(pairs)) for i in range(n-1)]
    fs.append(tuple(k*n for k in range(len(pairs))));fs.append(tuple(k*n+n-1 for k in range(len(pairs))))
    mesh('Flaky half moon',vs,fs,dough,group='Karipap',smooth=True)
    for stripe in range(5):
        # Offset arcs follow the layers of rolled laminated dough, not concentric mould grooves.
        curve=[]
        for k in range(24):
            t=k/23; a=PI*t; rr=.26+.12*stripe+.075*sin(2*a+.7); u=rr*cos(a)-.14; w=rr*sin(a)+.025
            radius=math.hypot(u,w); d=(-.047+.004*min(1,radius/.56)+.014*max(0,radius-.56)/.29)-.00065
            curve.append((x+s*.114*u,y+s*d,z+s*(.001+.09*w)))
        tube('Toasted spiral layer',curve,.00105*s,crust,'Karipap',6,reference=(0,1,0))
    for i in range(14):
        a=(i+.5)*PI/14
        tube('Pinched rim',[p(.93,a-.046,-.018),p(1.012,a,0),p(.96,a+.052,.014)],.0057*s,dough,'Karipap',6,reference=(0,1,0))
for j in range(3):
    for i in range(3):
        xx=.19+i*.255;yy=-.203+j*.177;zz=1.022;start=len(PARTS['Karipap']);pastry(xx,yy,zz,1-.033*((i+j)%3))
        from mathutils import Matrix
        base=Vector((xx,yy,zz));m=Matrix.Translation(base)@Matrix.Rotation(radians(9*sin(i*4+j*7)),4,'Z')@Matrix.Translation(-base)
        for part in PARTS['Karipap'][start:]:part.data.transform(m)
deliver((.37,-1,.64),'C6BDAE',1.12)
