"""Penang Asam Laksa Bowl | sgmy-props-penang-asam-laksa, revision 1.
Original procedural static mesh. Metres; base origin; Blender -Y front, +Z up.
Rebuild: blender -b --factory-startup --python-exit-code 1 -P generate.py
Optional: -- --export-only or -- --preview-only. Requires Blender with Draco.
No external images, fonts or model assets. UV0 is oriented planar for solid PBR materials.
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


def turn(name, at, profile, m, group='Body', sides=24, axis=(0,0,1), closed=False):
    frame = Vector((0,0,1)).rotation_difference(Vector(axis)).to_matrix()
    vs = [Vector(at)+frame @ Vector((r*cos(TAU*i/sides),r*sin(TAU*i/sides),z))
          for r,z in profile for i in range(sides)]
    n=len(profile)
    fs = [] if closed else [tuple(reversed(range(sides))),tuple(range((n-1)*sides,n*sides))]
    fs.extend((k*sides+i,k*sides+(i+1)%sides,((k+1)%n)*sides+(i+1)%sides,((k+1)%n)*sides+i)
              for k in range(n if closed else n-1) for i in range(sides))
    obj = mesh(name,vs,fs,m,group,smooth=True)
    if not closed:
        for i in range(2):
            obj.data.polygons[i].use_smooth = False
    return obj


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


def rod(name, a, b, r, m, group='Hardware', sides=12):
    return limb(name,[a,b],[r,r],m,group,sides)


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
    scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-1.38
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


def text(line, at, size, m, group='Lettering', width=None, plane='-Y', yaw=0):
    font = bpy.data.curves.new(line, 'FONT')
    font.body = line
    font.align_x = 'CENTER'
    font.align_y = 'CENTER'
    font.size = size
    font.resolution_u = 4
    o = bpy.data.objects.new(line,font)
    bpy.context.collection.objects.link(o)
    o.location = at
    o.rotation_euler = (0 if plane == 'Z' else PI/2, 0, yaw if plane != 'X' else PI/2)
    if width:
        o['Max Width'] = width
    font.materials.append(m)
    PARTS[group].append(o)
    return o


def bead(name, xyz, r, thick, mat, group, sides=64, axis=(0,0,1)):
    profile=[(r+thick*cos(TAU*j/8),thick*sin(TAU*j/8)) for j in range(8)]
    return turn(name,xyz,profile,mat,group,sides,axis,True)


def outline(name, rings, mat, group, smooth=True):
    # A closed loft through equally sampled contours, bottom to top.
    n=len(rings[0]); fs=[tuple(reversed(range(n))),tuple(range(n*(len(rings)-1),n*len(rings)))]
    fs.extend((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for k in range(len(rings)-1) for i in range(n))
    ob=mesh(name,[p for ring in rings for p in ring],fs,mat,group,smooth=smooth)
    for p in ob.data.polygons[:2]:p.use_smooth=False
    return ob



def grid(name, nx, ny, fn, mat, group, smooth=True, flip=False):
    vs=[fn(i/nx,j/ny) for j in range(ny+1) for i in range(nx+1)]
    fs=[]
    for j in range(ny):
        for i in range(nx):
            k=j*(nx+1)+i
            f=(k,k+1,k+nx+2,k+nx+1); fs.append(f[::-1] if flip else f)
    return mesh(name,vs,fs,mat,group,smooth=smooth)


def panel(name, contour, y, depth, mat, group, bevel=0):
    # Extrude a silhouette drawn in the front (X,Z) plane towards the back.
    if sum(x*v-u*z for (x,z),(u,v) in zip(contour,contour[1:]+contour[:1]))<0:contour=contour[::-1]
    n=len(contour); vs=[(x,y+d,z) for d in (0,depth) for x,z in contour]
    fs=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(j,i,i+n,j+n) for i in range(n) for j in [(i+1)%n]]
    return mesh(name,vs,fs,mat,group,bevel)


def samples(n):return [i*TAU/n for i in range(n)]


def line(name, points, radius, mat, group, sides=8):
    return limb(name,points,[radius]*len(points),mat,group,sides)


TITLE = 'Penang Asam Laksa Bowl'


def build():
    rng=random.Random(292);china=material('Warm white stoneware','F4E7CC',.23);blue=material('Cobalt glaze','265878',.26);aqua=material('Jade spoon glaze','7FAEA3',.26);broth=material('Tamarind fish broth','985033',.32);oil=material('Chilli oil','BD642E',.25);noodle=material('Thick rice noodles','F3DDB6',.45);onion=material('Shallot skin','AB5180',.45);rose=material('Sliced shallot','F4C9D5');yellow=material('Pineapple yellow','F6CB5C');eye=material('Pineapple eye','D89439');flesh=material('Cucumber flesh','DBE3A2');peel=material('Cucumber peel','59834F');fish=palette([('Flaked mackerel','AE8261'),('Poached mackerel','C49B78'),('Mackerel skin','64746B')]);garnish=palette([('Bunga kantan pink','E7738C'),('Ginger flower tip','FEB2B5'),('Mint leaf','4A8B53'),('Mint midrib','9BB566')]);paste=material('Dark prawn paste','54382C',.20)
    turn('Footed noodle bowl',(0,0,0),[(.044,0),(.048,.002),(.049,.008),(.046,.011),(.049,.014),(.063,.016),(.079,.027),(.096,.045),(.109,.063),(.117,.080),(.119,.084),(.118,.087),(.115,.0875),(.113,.084),(.106,.067),(.094,.049),(.076,.032),(.062,.024),(.043,.020),(.006,.020)],china,'Noodle bowl',96)
    for r,z,w in ((.048,.006,.001),(.108,.062,.0011),(.111,.068,.0007),(.118,.0835,.0015)):bead('Cobalt brush band',(0,0,z),r,w,blue,'Porcelain motif',96)
    # Brushwork carp on the bowl follows its curved surface, not a flat badge.
    def R(z):return .079+(z-.027)*(.096-.079)/.018 if z<.045 else .096+(z-.045)*(.109-.096)/.018
    for k in range(12):
        a=TAU*k/12
        def surf(dx,z):r=R(z)+.0007;return (r*cos(a+dx),r*sin(a+dx),z)
        p=[surf(-.12+.25*t/22,.045+.006*sin(PI*t/22)) for t in range(23)]+[surf(.13-.25*t/22,.045-.005*sin(PI*t/22)) for t in range(1,22)]
        mesh('Brush fish',p,[tuple(reversed(range(len(p))))],blue,'Porcelain motif');tri=[surf(-.10,.045),surf(-.19,.052),surf(-.182,.038)];mesh('Fish tail',tri,[(0,1,2)],blue,'Porcelain motif');q=surf(.081,.047);oval('Ceramic eye',q,(.0013,.0013,.0013),china,'Porcelain motif',rings=4,sides=8)
    Z=.070;turn('Assam broth',(0,0,0),[(.096,.054),(.105,.066),(.1066,Z),(.102,Z+.0009),(.088,Z+.00045),(.066,Z+.0006)],broth,'Soup',88)
    for k in range(165):
        r=.102*math.sqrt(rng.random());a=rng.random()*TAU;w=rng.uniform(.00065,.003);oval('Chilli oil lens',(r*cos(a),r*sin(a),Z+.00085),(w,w*rng.uniform(.48,.95),.00035),oil,'Soup',a,rings=4,sides=9)
    # Fine suspended flakes, in clusters around the surface of the tamarind broth.
    solids=[];faces=[];col=[]
    for k in range(470):
        r=.102*math.sqrt(rng.random());a=rng.random()*TAU;x,y=r*cos(a),r*sin(a);L=rng.uniform(.00045,.0022);w=L*rng.uniform(.23,.53);a=rng.random()*TAU;D=Vector((cos(a),sin(a),0));B=Vector((-sin(a),cos(a),0));q=Vector((x,y,Z+.001));i=len(solids);solids.extend((q-D*L,q-B*w,q+D*L,q+B*w*.63,q+Vector((0,0,.0004))));faces.extend((i+j,i+(j+1)%4,i+4) for j in range(4));col.extend([k%3]*4)
    mesh('Broth flakes',solids,faces,None,'Soup seasoning',slots=fish,indices=col)
    # Noodles surface and disappear into the broth in irregular overlapping laps.
    for j in range(14):
        pts=[];ax=rng.uniform(.049,.080);ay=rng.uniform(.028,.055);cx=rng.uniform(-.020,.002);cy=rng.uniform(-.024,.002);phase=rng.random()*TAU;off=rng.uniform(-.8,.8);arc=rng.uniform(3.55,6.10)
        for i in range(41):
            a=phase+arc*i/40;x=(ax+.006*sin(3*a+phase))*cos(a);y=(ay+.005*sin(2*a-phase))*sin(a);pts.append((cx+x*cos(off)-y*sin(off),cy+x*sin(off)+y*cos(off),Z+.0018+.0035*cos(2*a+phase)+.0016*sin(3*a)-.013*(abs(i-20)/20)**7))
        line('Rice noodle',pts,.00255,noodle,'Noodles',9)
    # Ragged splits expose the flakes; a few fragments retain a silver skin edge.
    for k in range(32):
        a=rng.random()*TAU;r=rng.uniform(.004,.040);x=.010+r*cos(a);y=-.027+r*sin(a);z=Z+.004+.007*(1-r/.042);L=rng.uniform(.006,.012);w=L*rng.uniform(.25,.53);yaw=rng.uniform(-.8,.7);rings=[]
        for sc,h in ((.84,0),(1,.0018),(.74,.0033)):
            rings.append([(x+sc*(L*cos(t)*cos(yaw)-w*(1+.17*sin(3*t+k))*sin(t)*sin(yaw)),y+sc*(L*cos(t)*sin(yaw)+w*(1+.17*sin(3*t+k))*sin(t)*cos(yaw)),z+h+.0007*cos(3*t+k)) for t in samples(12)])
        outline('Fish flake',rings,fish[2 if k%7==0 else k%2],'Fish topping')
    # Pineapple wedges, cucumber matchsticks, shallot arcs and torch ginger slivers.
    for k in range(5):
        x=-.064+.006*k;y=.026+.005*k;z=Z+.001+k*.0015;a=-.32+.15*k;co,si=cos(a),sin(a)
        def P(u,v,h):return (x+u*co-v*si,y+u*si+v*co,z+h)
        profile=[(-.019,-.007),(.019,-.003),(.014,.007),(-.008,.008)];outline('Pineapple wedge',[[P(u*s,v*s,h) for u,v in profile] for s,h in ((.96,0),(1,.004),(.90,.009))],yellow,'Garnishes')
        for j in range(2):oval('Fruit eye',P(-.008+j*.013,.0045,.009),(.0016,.001,.0005),eye,'Garnishes',a,rings=4,sides=8)
    for k in range(13):
        x=-.015+(k%6)*.0044;y=.033+.004*(k//6);az=1.87+.10*(k%6)+rng.uniform(-.18,.18);z=Z+.005+.0033*(k//6);L=rng.uniform(.039,.057);w=rng.uniform(.002,.0035);box('Cucumber matchstick',(x,y,z),(L,w,.0037),flesh,'Garnishes',.00065,az)
        if k%3!=1:box('Dark peel edge',(x+.45*w*sin(az),y-.45*w*cos(az),z+.00165),(L,w*.30,.0008),peel,'Garnishes',.00022,az)
    for k in range(7):
        x=-.042+.0035*k;y=-.010+.006*(k%3);rad=.017+.002*(k%4);angle=k*.95;pts=[(x+rad*cos(a+angle),y+.64*rad*sin(a+angle),Z+.007+k*.0012+.003*sin(a)) for a in [i*.104 for i in range(34)]];line('Shallot crescent',pts,.0016,rose,'Garnishes',8);line('Violet onion edge',[(x,y,z+.00118) for x,y,z in pts],.00066,onion,'Garnishes',6)
    for k in range(17):
        a=rng.random()*TAU;r=rng.uniform(.003,.018);x=.020+r*cos(a);y=.001+r*sin(a);L=rng.uniform(.011,.019);D=Vector((cos(a),sin(a),0));B=Vector((-sin(a),cos(a),0));P=Vector((x,y,Z+.015+rng.uniform(0,.006)));grid('Torch ginger ribbon',2,8,lambda u,v:P+D*L*v+B*((2*u-1)*.0020*(.1+sin(PI*v))+.002*sin(PI*v))+Vector((0,0,.003*sin(PI*v)-.006*v)),garnish[k%2],'Garnishes',flip=True)
    for i,a in enumerate((.4,2.1,3.3,5.1)):
        base=Vector((-.014,.017,Z+.024));D=Vector((cos(a),sin(a),.28));B=Vector((-sin(a),cos(a),0));L=.024+.002*i
        def blade(u,v):return base+D*(L*v)+B*((2*u-1)*.008*(.035+sin(PI*v))*(1+.075*cos(7*PI*v)))+Vector((0,0,.003*sin(PI*v)*(1-.75*abs(2*u-1))))
        grid('Mint blade',2,16,blade,garnish[2],'Garnishes',flip=True);line('Mint rib',[blade(.5,i/8) for i in range(9)],.00055,garnish[3],'Garnishes',5)
    # A ceramic soup spoon carries the customary separate dab of hae ko.
    x,y=.065,.026; az=-.34;S=lambda u,v,h:(x+u*cos(az)-v*sin(az),y+u*sin(az)+v*cos(az),Z+h+.09*v)
    outline('Spoon bowl',[[S(.019*r*cos(a),.032*r*sin(a),h) for a in samples(48)] for r,h in ((.50,.001),(.82,.004),(1,.011),(1,.013),(.93,.014),(.78,.009),(.45,.006))],aqua,'Serving spoon')
    def handle(u,v):
        w=.005+.0035*v+.0015*sin(PI*v);return S((u*2-1)*w,.025+.110*v,.010+.038*v+.007*sin(PI*v)+.0011*(1-(2*u-1)**2))
    grid('Spoon handle',4,20,handle,aqua,'Serving spoon');grid('Spoon back',4,20,lambda u,v:Vector(handle(u,v))-Vector((0,0,.0035)),aqua,'Serving spoon',flip=True)
    for u in (0,1):line('Rounded handle edge',[Vector(handle(u,j/20))-Vector((0,0,.0016)) for j in range(21)],.0018,aqua,'Serving spoon',8)
    oval('Spoon end',S(0,.135,.0466),(.0085,.004,.002),aqua,'Serving spoon',az,rings=8,sides=20);oval('Prawn paste',S(0,-.002,.008),(.014,.021,.0048),paste,'Serving spoon',az,rings=10,sides=28)
    deliver((.52,-1,.88),'D1C9BA',1.13)


if __name__ == '__main__':
    main()
