"""Pulau Ubin quarry marble arcade with a bucket-wheel lift and a continuous four-pass gravity railway.
Original static SG/MY mall visual mesh. Metres; floor origin, front at -Y.
Rebuild: blender -b -P generate.py [-- --preview-only | --export-only].
No external assets. Orthographic studio is for preview only.
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
        scene.cycles.samples = 16
        scene.cycles.max_bounces = 5
        scene.cycles.use_denoising = True
    else:
        scene.eevee.taa_render_samples = 48
        scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.58
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
    optimize_preview(dest / "preview.png")

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

def oval(name,x,y,z,rx,ry,rz,m,group='Sculpture',n=32):
    profile=[(max(.01,math.cos(a)),rz*math.sin(a)) for a in [PI*(i/16-.5) for i in range(17)]]
    return turned(name,x,y,z,profile,m,group,n,(rx,ry))

def badge(title,subtitle,x,y,z,w,h,field,ink):
    plaque('Enamel tablet',x,y,z,w,h,.032,min(h*.20,.06),field)
    label(title,(x,y-.019,z+h*.115),h*.46,ink,w*.86)
    label(subtitle,(x,y-.019,z-h*.245),h*.17,ink,w*.86)


def optimize_preview(path):
    """Preserve the RGB render; discard only as many low bits as the PNG budget needs."""
    import numpy as np
    import struct, zlib
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    pixels = np.empty(w*h*4, dtype=np.float32)
    img.pixels.foreach_get(pixels)
    rgb = (pixels.reshape(h,w,4)[::-1,:,:3]*255+.5).astype(np.uint32)
    bpy.data.images.remove(img)
    def chunk(tag,data): return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
    for step in [1,2,3,4,5,6,8,10,12]:
        col=np.minimum(255,((rgb+step//2)//step)*step).astype(np.uint8)
        row=col.copy(); row[:,1:]=col[:,1:]-col[:,:-1]
        scan=np.ones((h,w*3+1),dtype=np.uint8); scan[:,1:]=row.reshape(h,w*3)
        data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan.tobytes(),9))+chunk(b'IEND',b'')
        if len(data)<=250000:
            path.write_bytes(data)
            return
    raise RuntimeError('Preview exceeds PNG budget')

def rod(name,a,b,r,m,group='Hardware'):
    return tube(name,[a,b],r,m,group,12)

def ellipse(name,x,y,z,rx,rz,m,depth=.022,group='Decoration'):
    return polygon(name,[(x+rx*math.cos(a*TAU/48),z+rz*math.sin(a*TAU/48)) for a in range(48)],y,depth,m,group)

def piping(name,points,y,r,m,group='Trim'):
    return tube(name,[(u,y,v) for u,v in points],r,m,group,10,reference=(0,1,0))

def arch(name,x,y,z,w,straight,depth,m):
    r=w/2; pts=[(x-r,z),(x+r,z)]+[(x+r*math.cos(j*PI/40),z+straight+r*math.sin(j*PI/40)) for j in range(41)]
    return polygon(name,pts,y,depth,m,'Joinery')

TITLE='Kuari | Quarry marble run'
reset()
slate,teal,light,cream,orange,gold,steel,red,water=colors(Basalt='344653',QuarryBlue='567E88',GraniteFace='91A5A3',MapIvory='F2DCAF',SafetyOchre='DA8950',Bronze='BB905C .36 .49',RailSteel='CCD1C8 .31 .67',RedMarble='C95137 .19 .15',Lake='579F9A .28')
slab('Heel',0,0,0,2.07,.95,.074,.122,slate)
slab('Arcade shell',0,0,.071,2.18,1.03,.72,.145,teal)
slab('Granite lip',0,0,.791,2.23,1.07,.059,.147,light)
# Bright sectional stripes echo the bench levels of the old granite quarries.
for i in range(3):
    piping('Bench contour',[(-.914,.21+i*.10),(-.81,.21+i*.10),(-.70,.34+i*.10),(-.48,.34+i*.10),(-.41,.42+i*.10)],-.518,.011,cream)
badge('K U A R I','P U L A U   U B I N    /    M A R B L E   W O R K S',.294,-.526,.435,1.16,.347,slate,cream)
# Layered crags form the quarry wall behind the rails, lower faces are intentionally stepped.
for y,m,p in [(.43,slate,[(-1.04,.85),(-1.04,1.36),(-.87,1.49),(-.81,1.66),(-.62,1.63),(-.51,1.79),(-.284,1.72),(-.10,1.92),(.076,1.84),(.213,1.67),(.442,1.63),(.55,1.44),(.81,1.40),(.997,1.18),(.997,.85)]),(.32,teal,[(-.98,.85),(-.98,1.33),(-.77,1.32),(-.66,1.46),(-.43,1.42),(-.26,1.60),(.008,1.59),(.161,1.47),(.33,1.47),(.49,1.31),(.69,1.30),(.77,1.19),(.98,1.16),(.98,.85)]),(.22,light,[(-.93,.85),(-.93,1.13),(-.61,1.13),(-.491,1.24),(-.35,1.24),(-.28,1.31),(-.074,1.31),(.049,1.23),(.28,1.22),(.38,1.12),(.59,1.12),(.67,1.015),(.94,1.008),(.94,.85)])]:
    polygon('Quarry escarpment',p,y,.090,m,'Landscape')
# Four passes are joined by hairpins. Offset from the tangent, not world Y, to keep track gauge even in turns.
path=[]
for k in range(4):
    ys=.125-.137*k;x0=.70 if not k%2 else -.87; x1=-.87 if not k%2 else .49
    if k==2:x0=.49
    if k==3:x1=.72
    z0=1.74-k*.191
    for j in range(25):
        t=j/24; path.append(Vector((x0+(x1-x0)*t,ys,z0-.150*t)))
    if k<3:
        for j in range(1,17):
            a=PI*j/16
            path.append(Vector((x1+(-1 if k%2==0 else 1)*.069*math.sin(a),ys-.0685*(1-math.cos(a)),z0-.150-.041*j/16)))
# Skip coincident points between a hairpin and the next straight section.
path=[p for i,p in enumerate(path) if i==0 or (p-path[i-1]).length>.00005]
rails=[[],[]]
for i,p in enumerate(path):
    tangent=path[min(i+1,len(path)-1)]-path[max(i-1,0)];side=Vector((-tangent.y,tangent.x,0)).normalized()
    for k,sign in enumerate([-1,1]):rails[k].append(p+sign*.027*side)
    if i%9==1:
        rod('Sleeper',p-.039*side-Vector((0,0,.006)),p+.039*side-Vector((0,0,.006)),.009,gold,'Railway')
    if i%22==5:
        rod('Rail support',(p.x,p.y,.846),p-Vector((0,0,.009)),.014,slate,'Railway')
for r in rails:tube('Continuous rail',r,.009,steel,'Railway',10,reference=(0,0,1))
for i in [10,51,95,130]:
    p=path[i];oval('Game marble',p.x,p.y,p.z+.023,.043,.043,.043,red,'Marbles',24)
# Spoked lift carries game balls from the bottom outlet to the head of the run.
cx=.743;cz=1.38;rad=.365; yy=-.18
for dy in [0,.139]:
    y=yy+dy
    loop=[(cx+rad*math.cos(i*TAU/64),cz+rad*math.sin(i*TAU/64)) for i in range(65)]
    piping('Bucket wheel rim',loop,y,.019,orange,'Lift')
    for j in range(8):
        a=TAU*j/8;xx=cx+rad*math.cos(a);zz=cz+rad*math.sin(a)
        rod('Lift spoke',(cx,y,cz),(xx,y,zz),.012,orange,'Lift')
        if not dy:
            # Three folded faces make a hollow pickup scoop between the flanges.
            for t0,t1 in [(-.04,0),(0,.04)]:
                def scoop(t,v):
                    h=.030*(abs(t)/.04)**2
                    return (xx+t*math.sin(a)-h*math.cos(a),y+v,zz-t*math.cos(a)-h*math.sin(a))
                mesh('Rolled pickup scoop',[scoop(t0,-.008),scoop(t1,-.008),scoop(t1,.148),scoop(t0,.148)],[(0,1,2,3)],slate,group='Lift')
# Transfer chutes bridge the axial offset between the wheel and switchbacks.
for centerline in [[(.746,-.105,1.771),(.794,-.04,1.763),(.805,.053,1.751),(.767,.105,1.744),(.70,.125,1.74)],[(.72,-.286,1.017),(.761,-.260,1.014),(.766,-.197,1.01),(.747,-.116,1.004)]]:
    vs=[]
    for j,xyz in enumerate(centerline):
        p=Vector(xyz);d=Vector(centerline[min(j+1,len(centerline)-1)])-Vector(centerline[max(0,j-1)]);side=Vector((-d.y,d.x,0)).normalized()
        for w,h in [(-.034,.022),(-.028,0),(.028,0),(.034,.022)]:vs.append(p+side*w+Vector((0,0,h)))
    mesh('Guide chute',vs,[(4*j+k,4*j+4+k,4*j+5+k,4*j+1+k) for j in range(len(centerline)-1) for k in range(3)],orange,group='Railway')
for y in [-.293,.172]:
    for s in [-1,1]:rod('Lift trestle',(cx+s*.184,y,.850),(cx,y,cz),.027,slate,'Lift')
rod('Axle',(cx,-.44,cz),(cx,.21,cz),.031,gold,'Lift')
rod('Crank arm',(cx,-.414,cz),(cx+.12,-.414,cz-.073),.021,orange,'Lift')
rod('Crank grip',(cx+.12,-.414,cz-.073),(cx+.12,-.522,cz-.073),.029,slate,'Lift')
deliver((1.44,-6,2.81),'9D9B8D',1.14)
