"""Sabah Striped Pitcher | sgmy-props-sabah-striped-pitcher | revision 1.
Original procedural static prop, no external assets. Metres; Z up, -Y front.
From this directory: blender -b --factory-startup -P generate.py
Default: rebuild model.glb (requires Draco) and studio preview.png.
Use -- --export-only or -- --preview-only to rebuild one. No runtime logic.
"""
import math
import random
from collections import defaultdict
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

PI, TAU = math.pi, math.tau
sin, cos = math.sin, math.cos
PARTS = defaultdict(list)


def material(name, hex_color, rough=.5, metal=0, emission=0, two_sided=False):
    def linear(v):
        return v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4
    rgb = tuple(linear(int(hex_color[k:k+2], 16) / 255) for k in (0, 2, 4))
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    m.use_backface_culling = not two_sided
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    if emission:
        shader.inputs['Emission Color'].default_value = (*rgb, 1)
        shader.inputs['Emission Strength'].default_value = emission
    return m


def palette(rows, **kwargs):
    return [material(name, color, **kwargs) for name, color in rows]


def mesh(name, vertices, faces, m, group, bevel=0, smooth=False, uv=None, slots=None, indices=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for mat in (slots or [m]):
        data.materials.append(mat)
    if indices is not None:
        data.polygons.foreach_set('material_index', indices)
    if smooth:
        data.polygons.foreach_set('use_smooth', [True]*len(data.polygons))
    if uv is not None:
        layer = data.uv_layers.new(name='UV0')
        layer.uv.foreach_set('vector', [v for i in data.loops for v in uv[i.vertex_index]])
    if bevel:
        mod = obj.modifiers.new('Edge Softening', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.harden_normals = True
    if group:
        PARTS[group].append(obj)
    return obj


def box(name, at, dims, m, group='Body', bevel=.003, yaw=0):
    a, b, c = [d/2 for d in dims]
    x, y, z = at
    vs = [(x + u*cos(yaw)-v*sin(yaw), y + u*sin(yaw)+v*cos(yaw), z+w)
          for w in (-c,c) for u,v in ((-a,-b),(a,-b),(a,b),(-a,b))]
    fs = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return mesh(name, vs, fs, m, group, bevel)


def limb(name, path, radii, m, group='Branches', sides=8, ref=(0,1,0), flute=0, slots=None, rng=None):
    ps = [Vector(p) for p in path]
    vs = []
    for i,p in enumerate(ps):
        t = (ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
        u = t.cross(Vector(ref))
        if u.length < .02:
            u = t.cross(Vector((1,0,0)))
        u.normalize()
        v = t.cross(u).normalized()
        a,b = radii[i] if isinstance(radii[i],tuple) else (radii[i],radii[i])
        for j in range(sides):
            angle = TAU*j/sides
            r = 1 + flute*(.65*sin(angle*5+.12*i)+.35*cos(angle*3-1))
            point = p+r*(u*a*cos(angle)+v*b*sin(angle))
            if i == 0 and p.z == 0:
                point.z = 0  # Seat slanted trunks and posts on the placement plane.
            vs.append(point)
    fs = [tuple(reversed(range(sides))), tuple(range(len(vs)-sides,len(vs)))]
    ids = [0,0]
    band = [rng.choices(range(len(slots)), (7,2,1))[0] for i in range(sides)] if slots else []
    for k in range(len(ps)-1):
        for i in range(sides):
            j = (i+1)%sides
            fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
            if slots:
                ids.append(band[i])
    obj=mesh(name,vs,fs,m,group,smooth=True,slots=slots,indices=ids if slots else None)
    for i in range(2):
        obj.data.polygons[i].use_smooth = False
    return obj


def bake():
    # Evaluate authored surfaces and combine by semantic group/material, holding the floor origin.
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    root = bpy.data.objects.new(TITLE,None)
    bpy.context.collection.objects.link(root)
    root['Asset ID'] = Path(__file__).resolve().parent.name
    root['Revision'] = 1
    root['Role'] = 'Static visual mesh; no gameplay or collider'
    root['Category'] = 'SG/MY Street Props'
    root['origin_note'] = 'Metres; base origin; Blender -Y front, Z up; glTF +Z front, +Y up'
    result = []
    for group, parts in PARTS.items():
        verts, faces, normals, uv, mats, ids = [], [], [], [], [], []
        for part in parts:
            eval_part=part.evaluated_get(dg)
            src=eval_part.to_mesh()
            mw=eval_part.matrix_world.copy()
            if 'Max Width' in part and src.vertices:
                xs=[v.co.x for v in src.vertices]
                factor=min(1,part['Max Width']/max(max(xs)-min(xs),.0001))
                mw = mw @ Matrix.Diagonal((factor,1,1,1))
            nm=mw.to_3x3().inverted_safe().transposed()
            coords=[mw @ v.co for v in src.vertices]
            offset=len(verts)
            verts.extend(coords)
            src.calc_loop_triangles()
            uv0=src.uv_layers.active
            local_normals=src.corner_normals
            for tri in src.loop_triangles:
                p,q,r=(coords[i] for i in tri.vertices)
                normal=(q-p).cross(r-p)
                if normal.length_squared < 1e-19:
                    continue
                faces.append(tuple(i+offset for i in tri.vertices))
                mat=part.data.materials[tri.material_index]
                if mat not in mats:
                    mats.append(mat)
                ids.append(mats.index(mat))
                normals.extend((nm @ local_normals[i].vector).normalized() for i in tri.loops)
                if uv0:
                    uv.extend(c for i in tri.loops for c in uv0.uv[i].vector)
                else:
                    # Oriented planar UVs for solid-color geometry; no external atlases.
                    k=max(range(3),key=lambda i:abs(normal[i]))
                    a,b=(k+1)%3,(k+2)%3
                    sign = 1 if normal[k]>0 else -1
                    uv.extend(v for p in (p,q,r) for v in (p[a]*sign,p[b]))
            eval_part.to_mesh_clear()
        used=sorted({i for f in faces for i in f})
        index={old:new for new,old in enumerate(used)}
        o=mesh(group,[verts[i] for i in used],[tuple(index[i] for i in f) for f in faces],
               None,None,smooth=True,slots=mats,indices=ids)
        o.data.uv_layers.new(name='UV0').uv.foreach_set('vector',uv)
        o.data.normals_split_custom_set(normals)
        o.parent=root
        result.append(o)
    # Leave all source objects linked until the last evaluated mesh has been read.
    for parts in PARTS.values():
        for part in parts:
            bpy.data.objects.remove(part,do_unlink=True)
    floor_z=min(v.co.z for o in result for v in o.data.vertices)
    for o in result:
        o.data.transform(Matrix.Translation((0,0,-floor_z)))
    return result


def studio(objs, direction, backdrop, margin):
    scene=bpy.context.scene
    coords=[v.co for o in objs for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in coords) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in coords) for i in range(3)))
    center=(lo+hi)/2
    span=max(hi-lo)
    view=Vector(direction).normalized()
    rotation=(-view).to_track_quat('-Z','Y')
    projected=[rotation.inverted() @ (v-center) for v in coords]
    lo2=[min(p[i] for p in projected) for i in (0,1)]
    hi2=[max(p[i] for p in projected) for i in (0,1)]
    target=center+rotation @ Vector(((lo2[0]+hi2[0])/2,(lo2[1]+hi2[1])/2,0))
    camera=bpy.data.objects.new('Preview Camera',bpy.data.cameras.new('Orthographic Lens'))
    scene.collection.objects.link(camera)
    camera.location=target+view*span*3
    camera.rotation_euler=rotation.to_euler()
    camera.data.type='ORTHO'
    camera.data.clip_start = .001
    camera.data.clip_end = max(100,span*9)
    camera.data.ortho_scale=margin*max(hi2[0]-lo2[0],(hi2[1]-lo2[1])*1.2)
    scene.camera=camera
    box('Studio Floor',(0,0,-.013*span),(span*120,span*120,.0258*span),
        material('Preview Backdrop',backdrop,.82,emission=.35),None,0)
    world=bpy.data.worlds.new('Studio Ambient')
    scene.world=world
    world.use_nodes=True
    bg=world.node_tree.nodes['Background']
    bg.inputs[0].default_value=(.48,.55,.63,1)
    bg.inputs[1].default_value=.32
    def area(name,offset,power,size,color):
        data=bpy.data.lights.new(name,'AREA')
        o=bpy.data.objects.new(name,data)
        scene.collection.objects.link(o)
        o.location=center+Vector(offset)*span
        o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
        data.energy=power*span**2
        data.shape='DISK'
        data.size=size*span
        data.color=color
    area('Warm Softbox',(-.75,-1.05,1.25),131,1.09,(1,.88,.74))
    area('Cool Fill',(1.1,-.45,.51),55,1.25,(.77,.87,1))
    area('High Edge Light',(.48,1.03,1.3),173,1.05,(1,.94,.81))
    scene.render.engine='CYCLES'
    scene.cycles.samples=18
    scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.37
    scene.render.resolution_x=720
    scene.render.resolution_y=600
    scene.render.resolution_percentage=100
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.compression=95
    return scene


def deliver(direction, backdrop='BFC7C2', margin=1.16):
    objs=bake()
    out=Path(__file__).resolve().parent
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    print(f'{TITLE}: {sum(len(o.data.polygons) for o in objs):,} triangles')
    if '--preview-only' not in args:
        glb=out/'model.glb'
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',export_extras=True,
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=18,
                                  export_draco_normal_quantization=12,
                                  export_draco_texcoord_quantization=16,
                                  export_animations=False,export_cameras=False,export_lights=False)
        assert glb.stat().st_size<=2_000_000
    if '--export-only' not in args:
        scene=studio(objs,direction,backdrop,margin)
        scene.render.filepath=str(out/'preview.png')
        bpy.ops.render.render(write_still=True)
        quantize_png(out/'preview.png')


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    build()


def tube(name, points, radius, mat, group, sides=10):
    return limb(name,points,[radius]*len(points),mat,group,sides,ref=(0.13,0.81,0.57))


def oval(name, at, radii, m, group, yaw=0, tilt=0, rings=12, sides=24):
    # A closed ellipsoid with single pole vertices.
    rx, ry, rz = radii
    vs = [(0,0,-rz)]
    for j in range(1,rings):
        a = -PI/2+PI*j/rings
        vs += [(rx*cos(a)*cos(i*TAU/sides), ry*cos(a)*sin(i*TAU/sides), rz*sin(a)) for i in range(sides)]
    vs.append((0,0,rz)); top=len(vs)-1
    fs = [(0,1+(i+1)%sides,1+i) for i in range(sides)]
    for j in range(rings-2):
        k=1+j*sides
        fs.extend((k+i,k+(i+1)%sides,k+sides+(i+1)%sides,k+sides+i) for i in range(sides))
    fs.extend((top,top-sides+i,top-sides+(i+1)%sides) for i in range(sides))
    o=mesh(name,vs,fs,m,group,smooth=True); o.location=at; o.rotation_euler=(0,tilt,yaw)
    return o


def stroke(name, points, radius, mat, group, sides=8, steps=5):
    # Sample Catmull-Rom curves through the authored control points.
    p=[Vector(v) for v in points]; out=[]
    for j in range(len(p)-1):
        a,b,c,d=p[max(0,j-1)],p[j],p[j+1],p[min(j+2,len(p)-1)]
        for i in range(steps):
            t=i/steps
            out.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t**3))
    return tube(name,out+[p[-1]],radius,mat,group,sides)


def leaf(name, base, angle, length, width, lift, droop, mat, vein, group, broad=.8):
    # A ridged, curved blade; its narrowing tip turns down at the end.
    vs=[]; fs=[]; rib=[]; base=Vector(base)
    d=Vector((cos(angle),sin(angle),0)); side=Vector((-d.y,d.x,0))
    for j in range(11):
        t=j/10; w=width*(max(.012,sin(PI*t**broad)))**.8
        c=base+d*length*t+Vector((0,0,lift*t-droop*t*t)); rib.append(c+Vector((0,0,.002*length)))
        for k in (-1,0,1):
            vs.append(c+side*w*k+Vector((0,0,-w*(.20+.11*sin(2*PI*t))*abs(k))))
        if j:
            a=3*(j-1); fs.extend([(a,a+3,a+4,a+1),(a+1,a+4,a+5,a+2)])
    mesh(name,vs,fs,mat,group,smooth=True)
    if vein: limb('Midrib',rib,[length*(.009*(1-j/11)+.001) for j in range(11)],vein,group,6)
    return rib[-1]


def quantize_png(path):
    """Keep full RGB gradients, reducing only low bits until the card fits."""
    if path.stat().st_size <= 250000: return
    import numpy as np
    import struct, zlib
    im=bpy.data.images.load(str(path),check_existing=False)
    im.colorspace_settings.name='Non-Color'  # The input is already display-encoded.
    w,h=im.size; buf=np.empty(w*h*4,dtype=np.float32); im.pixels.foreach_get(buf)
    rgb=np.uint16(np.clip(buf.reshape(h,w,4)[::-1,:,:3]*255+.5,0,255)); bpy.data.images.remove(im)
    def chunk(t,data):
        return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data))
    for drop in range(5):
        step=1<<drop; pic=np.uint8(np.minimum(255,((rgb+step//2)//step)*step))
        # Per scanline, choose between horizontal and vertical prediction.
        left=np.zeros_like(pic); left[:,1:]=pic[:,:-1]
        up=np.zeros_like(pic); up[1:]=pic[:-1]
        a,b=pic-left,pic-up
        cost=lambda v: np.abs(v.view('int8').astype('int16')).sum(axis=(1,2))
        horizontal=cost(a)<cost(b)
        raw=b''.join((b'\1'+a[j].tobytes()) if horizontal[j] else (b'\2'+b[j].tobytes()) for j in range(h))
        image=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'sRGB',b'\0')+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
        if len(image)<=250000:
            path.write_bytes(image); return
    raise ValueError('Preview exceeds the gallery size budget')


TITLE = 'Sabah Striped Pitcher'


def build():
    moss,bark,twig,vein=palette([('Forest moss','596947'),('Peat and bark','64503D'),('Tendril russet','A57550'),('Leaf midrib','9D9B61')]);leaves=palette([('Olive blade','5F804F'),('Deep leaf green','426F51'),('New bronze blade','98A267')],rough=.40,two_sided=True)
    trap,rosy,scarlet,lemon,inside,spot,lid=palette([('Blushed pitcher','BA9667'),('Wine pitcher','A35B59'),('Peristome carmine','913747'),('Peristome straw','F1CE84'),('Pitcher throat','753F48'),('Claret freckles','914C5D'),('Lid olive reverse','B5A468')]); lid.use_backface_culling=False
    rng=random.Random(357)
    # A small root-bound island is part of the prop, not a presentation pedestal.
    poly=[((.187+.009*sin(i*5))*cos(TAU*i/26),(.146+.013*cos(i*3))*sin(TAU*i/26)) for i in range(26)]
    vs=[(x*s,y*s,z) for z,s in ((0,.78),(.012,1),(.028,.95),(.046,.75)) for x,y in poly];fs=[tuple(range(26))[::-1],tuple(range(78,104))];ids=[0,1]
    for j in range(3):
        for i in range(26):fs.append((26*j+i,26*j+(i+1)%26,26*(j+1)+(i+1)%26,26*(j+1)+i));ids.append(int(j==2))
    mesh('Peaty root hummock',vs,fs,None,'Root hummock',smooth=True,slots=[bark,moss],indices=ids)
    for j in range(42):
        a=rng.random()*TAU;r=rng.random()**.5; oval('Moss cushion',(.145*r*cos(a),.111*r*sin(a),.041-.009*r),(.025,.020,.012+rng.random()*.005),moss,'Root hummock',a,rings=5,sides=10)
    stem=[(0,0,.038),(-.012,.011,.092),(-.009,.003,.145),(.014,.007,.216),(.011,.021,.27)]
    limb('Leafy stem',stem,[.015,.012,.011,.009,.006],twig,'Rosette',10)
    pitchers=((- .166,-.094,.065,.200,.046,-1.77,trap),(.132,-.122,.059,.168,.048,-1.12,rosy),(.184,.074,.130,.187,.043,-.29,trap),(-.109,.155,.142,.155,.039,2.24,rosy),(-.011,-.180,.035,.097,.030,-1.27,trap))
    for i in range(18):
        t=i/17;a=i*2.398;length=.163+.054*sin(PI*t);base=Vector((.01*sin(t*4),.012*t,.056+.211*t));w=.033+.009*sin(PI*t);lift=.105+.053*t;drop=.089+.076*(1-t)
        # Keep the radiating blades out of the mouths and shoulders of hanging traps.
        for attempt in range(12):
            blocked=False
            for k in range(1,13):
                u=k/12; q=base+Vector((length*u*cos(a),length*u*sin(a),lift*u-drop*u*u))
                for x,y,z,H,R,*_ in pitchers:
                    if z-.008<q.z<z+H+R*.70 and math.hypot(q.x-x,q.y-y)<R*1.15+w*sin(PI*u):blocked=True
            if not blocked:break
            a+=.16
        if not blocked:leaf('Lanceolate leaf',base,a,length,w,lift,drop,leaves[i%3],vein,'Rosette',.91)
    def pitcher(x,y,z,H,R,angle,col):
        # Local +Y is the back of the mouth, where the lid hinges. The high back
        # and lowered front edge give the peristome its oblique oval silhouette.
        O=Vector((x,y,z)); f=Vector((cos(angle),sin(angle),0)); side=Vector((-sin(angle),cos(angle),0)); up=Vector((0,0,1))
        def xyz(u,v,w):return O+side*u-f*v+up*w
        prof=[(.09,0),(.58,.035),(.90,.15),(1,.30),(.95,.44),(.80,.61),(.69,.76),(.77,.92),(.80,1)]
        def point(r,t,a,bias=0):return xyz(R*r*cos(a),R*r*.88*sin(a),H*t+(.50*sin(a))*R*t**4+bias)
        n=48;V=[point(r,t,TAU*i/n) for r,t in prof for i in range(n)];F=[tuple(range(n))[::-1]];inds=[0]
        for j in range(len(prof)-1):
            for i in range(n):F.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i));inds.append(0)
        mesh('Swollen trap',V,F,col,'Pitcher bodies',smooth=True)
        # The inside is modeled down to a dark, closed bottom well.
        V=[];F=[];inds=[]
        lip=[(.77,.913),(.954,.91),(1.015,.934),(1.04,.963),(.99,.985),(.87,1.006),(.72,1.005),(.63,.987),(.60,.95),(.59,.78),(.51,.62),(.29,.53)]
        n=80
        for j,(r,t) in enumerate(lip):
            for i in range(n):
                a=TAU*i/n;rr=r+.009*cos(a*40)*(j<9);V.append(point(rr,t,a))
                if j:
                    F.append(((j-1)*n+i,(j-1)*n+(i+1)%n,j*n+(i+1)%n,j*n+i));inds.append(2 if j>=9 else int((i+int(1.4*sin(3*a))+(j>4))%5>=2))
        F.append(tuple(range(len(V)-n,len(V))));inds.append(2);mesh('Striped ribbed lip and well',V,F,None,'Fluted collars',smooth=True,slots=[scarlet,lemon,inside],indices=inds)
        # Spots taper around the shoulders and are made from adhered surface patches.
        for j in range(73):
            k=rng.randrange(1,7); t=rng.uniform(.12,.85); r0,h0=prof[k];r1,h1=prof[k+1];r=r0+(r1-r0)*t;h=h0+(h1-h0)*t;a=rng.random()*TAU
            v=[]
            for l in range(9):
                b=TAU*l/9;dt=.008*sin(b);dr=(r1-r0)*dt/(h1-h0);v.append(point(r+dr+.0028,h+dt,a+.050*cos(b)))
            mesh('Pitcher speckle',v,[tuple(range(9))],spot,'Pitcher markings');spot.use_backface_culling=False
        for s in (-1,1):
            a=-PI/2+.41*s; p=[point(r,t,a) for r,t in prof[1:8]];tube('Ventral fringe keel',p,R*.030,rosy,'Pitcher markings',6)
            for k in range(1,len(p)-1):limb('Fringe tooth',[p[k],p[k]+f*R*.09+up*H*.009,p[k]+f*R*.12+up*H*.032],[R*.026,R*.016,.00025],rosy,'Pitcher markings',5)
        hinge=point(.77,.993,PI/2);back=hinge-f*.008+up*.012
        limb('Lid hinge',[hinge,back,back+up*.009],[.004,.004,.003],col,'Pitcher lids',8)
        V=[];F=[];mid=[]
        for j in range(13):
            t=j/12;w=R*.69*max(.035,sin(PI*t**.82))**.67;c=back+f*(R*.88*t)+up*(R*1.10*t+.009);mid.append(c)
            for k in (-1,0,1):V.append(c+side*k*w-up*(abs(k)*w*.16))
            if j:
                b=3*(j-1);F.extend(((b,b+3,b+4,b+1),(b+1,b+4,b+5,b+2)))
        mesh('Arched operculum',V,F,lid,'Pitcher lids',smooth=True);tube('Lid stripe',mid,R*.021,rosy,'Pitcher lids',6)
        # Connect each trap at its foot to a recurved continuation of a leaf's midrib.
        distance=math.hypot(x,y);a=math.atan2(y,x);base=Vector((0,.006,min(.24,.11+z*.46)));tip=leaf('Pitcher-bearing blade',base,a,distance*.68,R*.66,.089,.062,leaves[1],vein,'Rosette',.83)
        tail=xyz(0,R*.32,H*.02);stroke('Looping tendril',[tip,tip+f*.016-up*.014,tail-f*.032+up*.021,tail-f*.014-up*.004,tail],.0025,twig,'Tendrils')
    for params in pitchers:
        pitcher(*params)
    deliver((.48,-1,.54),'B4C2AD',1.13)


if __name__ == '__main__':
    main()
