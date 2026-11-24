"""Johor gambus workshop window showing a finished double-course lute and an open braced bowl.
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

TITLE='Petik | Johor gambus luthier'
reset()
bark,oak,belly,maple,rose,gold,cream,ink,green=colors(Rosewood='674333',Meranti='A66D4B',Soundboard='DEAB69',Sapwood='F1CDA0',DarkStave='815039',BrassWire='DEBA79 .32 .49',Bone='F9E5B7',Ebony='35332D',IndigoLacquer='354D5D')
slab('Plinth foot',0,0,0,1.52,.68,.067,.080,ink)
slab('Window podium',0,0,.067,1.60,.74,.296,.096,green)
slab('Edge binding',0,0,.36,1.61,.75,.024,.097,gold)
slab('Luthier bench',0,0,.382,1.64,.78,.061,.103,oak)
badge('P E T I K','G A M B U S    /    J O H O R',0,-.376,.223,1.033,.221,green,cream)
for x in [-.389,.397]:
    for y in [-.096,.173]:
        slab('Bowl saddle foot',x,y,.443,.35,.074,.051,.024,bark,'Stands')
    for s in [-1,1]:
        tube('Bowl saddle',[(x+s*.135,-.132,.563),(x+s*.136,-.10,.487),(x+s*.136,.17,.487),(x+s*.132,.21,.76)],.019,gold,'Stands')
# Each bowl is a vault of alternately coloured curved staves, like a sectioned boat hull.
profile=[(.033,.0),(.108,.026),(.183,.095),(.216,.194),(.218,.281),(.194,.381),(.146,.475),(.095,.545),(.054,.610),(.035,.641)]; base=.476
for idx,(x,y,scale) in enumerate([(-.389,-.09,1.13),(.401,-.02,.98)]):
    def xyz(radius,h,a,offset=0): return (x+(radius-offset)*scale*math.cos(a),y+(radius-offset)*scale*.88*math.sin(a),base+h*scale)
    for j in range(13):
        lo=PI*j/13; hi=PI*(j+1)/13
        vs=[xyz(r,h,lo+(hi-lo)*k/4,off) for off in [0,.009] for r,h in profile for k in range(5)]
        L=5*len(profile);fs=[]
        for level in range(len(profile)-1):
            for k in range(4):
                a=level*5+k;fs.extend([(a,a+1,a+6,a+5),(a+L+5,a+L+6,a+L+1,a+L)])
            for k in [0,4]:
                a=level*5+k;fs.append((a,a+5,a+5+L,a+L))
        for a in [0,L-5]:
            for k in range(4): fs.append((a+k,a+k+L,a+k+1+L,a+k+1))
        mesh('Carved bowl stave',vs,fs,[oak,rose,bark,rose][j%4],group='Bowl ribs',smooth=True)
    if idx:
        for r,h in profile[2:9:2]:
            pts=[xyz(r,h,k*PI/32,.014) for k in range(33)]
            tube('Internal bent lining',pts,.009,maple,'Open instrument',8,reference=(0,0,1))
        for h,r in [(.20,.212),(.37,.192),(.51,.113)]:
            rod('Cross brace',(x-r*scale,y,base+h*scale),(x+r*scale,y,base+h*scale),.008,belly,'Open instrument')
        continue
    outline=[(x+r*scale,base+h*scale) for r,h in profile]+[(x-r*scale,base+h*scale) for r,h in reversed(profile)]
    polygon('Spruce face',outline,y-.003,.013,belly,'Finished instrument')
    for u,h,r in [(0,.328,.068),(-.085,.417,.028),(.085,.417,.028)]:
        xx=x+u*scale; zz=base+h*scale
        ellipse('Rosette purfling',xx,y-.015,zz,r*scale,r*scale,cream,.009,'Sound holes')
        ellipse('Acoustic opening',xx,y-.022,zz,r*scale*.89,r*scale*.89,ink,.006,'Sound holes')
        for k in range(8):
            a=TAU*k/8; pts=[]
            for q in range(19):
                t=q*TAU/18;u=r*(.42+.39*math.cos(t));v=r*.145*math.sin(t)
                pts.append((xx+(u*math.cos(a)-v*math.sin(a))*scale,zz+(v*math.cos(a)+u*math.sin(a))*scale))
            piping('Pierced flower',pts,y-.027,.0025,maple,'Sound holes')
    polygon('Fretless fingerboard',[(x-.043,base+.53*scale),(x+.043,base+.53*scale),(x+.027,base+.916*scale),(x-.027,base+.916*scale)],y-.003,.046,bark,'Finished instrument')
    box('Bridge',(x,y-.023,base+.137*scale),(.181,.036,.023),ink,.006,'Finished instrument')
    box('Nut',(x,y-.030,base+.908*scale),(.058,.014,.013),cream,.003,'Finished instrument')
    for k in range(10):
        u=(k//2-2)*.015+(k%2)*.003
        rod('Double course',(x+u*1.39,y-.043,base+.138*scale),(x+u*.72,y-.036,base+.909*scale),.00125,gold,'Strings')
    tube('Bent pegbox',[(x,y,base+.909*scale),(x,y+.035,base+.944*scale),(x,y+.13,base+.97*scale),(x,y+.163,base+1.011*scale)],.030,oak,'Pegbox',12,reference=(1,0,0))
    for k in range(5):
        for s in [-1,1]:
            yy=y+.025+k*.028; zz=base+(.93+k*.013)*scale
            rod('Tuning peg',(x,yy,zz),(x+s*.064,yy,zz),.007,ink,'Pegbox')
            oval('Tuning key',x+s*.068,yy,zz,.014,.012,.023,cream,'Pegbox',16)
deliver((1.86,-6,2.46),'A49B8E',1.14)
