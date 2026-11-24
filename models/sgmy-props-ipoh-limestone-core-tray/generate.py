"""Ipoh Limestone Core Tray | sgmy-props-ipoh-limestone-core-tray, revision 1.
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


TITLE = 'Ipoh Limestone Core Tray'


def build():
    rng=random.Random(192);wood=material('Oiled honey plywood','B88456',.68);edge=material('Ply end grain','CCA478');dark=material('Recessed dividers','876445');metal=material('Dull zinc corners','9DA69B',.43,.52);teal=material('Surveyor teal','2F6568');cream=material('Butter paper','F1E3B8');ink=material('Petrol survey ink','355D5D');lith=palette([('Cool limestone','AAB8B4'),('Pale calcite','E6DFCD'),('Blue grey limestone','899E9C'),('Iron oxide seam','B48661'),('Charcoal dolomite','727E78'),('Fracture green','90A798')],rough=.84)
    box('Case floor',(0,0,.012),(.842,.407,.024),wood,'Sample case',.006)
    for s in (-1,1):
        box('Long case wall',(0,s*.199,.056),(.844,.016,.088),wood,'Sample case',.004);box('Case end',(s*.413,0,.055),(.018,.392,.09),wood,'Sample case',.003)
        for t in (-1,1):
            box('Zinc corner plate',(s*.394,t*.208,.043),(.053,.003,.066),metal,'Case hardware',.003)
            for zz in (.022,.061):oval('Nail head',(s*.386,t*.210,zz),(.0033,.0015,.0033),dark,'Case hardware',rings=5,sides=10)
    # Lid components authored vertically, then tilted together about the hinge line.
    G='Raised lid';box('Lid shell',(0,.006,.201),(.842,.023,.404),wood,G,.007);box('Inset field',(0,-.006,.201),(.784,.011,.350),dark,G,.006)
    box('Lithology card',(0,-.015,.205),(.706,.004,.270),cream,G,.003);text('KINTA VALLEY',(-.137,-.018,.304),.041,ink,G);text('IPOH   /   GEOLOGY',(.204,-.018,.304),.018,ink,G)
    box('Header rule',(0,-.018,.273),(.654,.0009,.0022),ink,G,0)
    # Original stylised section through karst pinnacles, with alluvium below.
    hill=[(-.319,.143),(-.319,.166),(-.283,.174),(-.267,.192),(-.252,.195),(-.243,.236),(-.233,.239),(-.220,.220),(-.204,.224),(-.193,.192),(-.179,.190),(-.164,.215),(-.159,.245),(-.145,.255),(-.130,.244),(-.121,.222),(-.110,.220),(-.103,.198),(-.076,.19),(-.062,.170),(-.024,.166),(-.011,.181),(.012,.179),(.023,.163),(.059,.169),(.084,.161),(.105,.165),(.105,.143)]
    panel('Karst section',hill,-.0186,.001,lith[2],G);panel('Bedrock stratum',[(-.319,.106),(-.319,.14),(-.189,.14),(-.111,.137),(-.071,.146),(.009,.14),(.105,.14),(.105,.102),(.037,.108),(-.076,.106),(-.183,.116),(-.252,.105)],-.0188,.001,teal,G)
    for j,(label,mat) in enumerate((('ALLUVIUM',lith[3]),('LIMESTONE',lith[2]),('CALCITE',lith[1]))):
        z=.235-.054*j;box('Legend chip',(.152,-.019,z),(.024,.001,.018),mat,G,.001);text(label,(.243,-.019,z),.019,ink,G)
    for x in (-.340,.340):
        for z in (.080,.330):turn('Map pin',(x,-.019,z),[(.0048,0),(.004,.002)],metal,G,12,(0,-1,0))
    hinge=Matrix.Translation((0,.196,.102))@Matrix.Rotation(-.47,4,'X');bpy.context.view_layer.update()
    for o in PARTS[G]:o.matrix_world=hinge@o.matrix_world
    for x in (-.25,.25):turn('Piano hinge',(x-.05,.193,.104),[(.009,0),(.009,.10)],metal,'Case hardware',20,(1,0,0))
    for y in (-.096,0,.096):box('Compartment strip',(0,y,.058),(.808,.009,.071),edge,'Sample case',.0015)
    for row in range(4):
        Y=(row-1.5)*.096;z=.061;R=.037; endx=-.324
        box('Depth index',(-.365,Y,.061),(.072,.083,.068),teal,'Case labels',.0025);text(f'{12+row:02d} m',(-.365,Y,.0955),.019,cream,'Case labels',plane='Z')
        lengths=[rng.uniform(.07,.20) for _ in range(5)];total=sum(lengths)
        for j in range(5):
            x0=endx+.008;x1=x0+.680*lengths[j]/total if j<4 else .395;endx=x1;phase=rng.uniform(0,TAU);Rr=R*rng.uniform(.93,1);ang=samples(28);ts=[0,.045,.25,.35,.38,.43,.62,.75,.77,.91,.966,1];vs=[];fs=[];inds=[]
            for k,t in enumerate(ts):
                for a in ang:
                    W=sin(a+phase)+.42*cos(3*a-phase);rad=Rr*(1+.039*cos(5*a+phase)+.022*sin(a*3+2*t))*(.94 if k in (0,len(ts)-1) else 1);x=x0+(x1-x0)*t+.026*W*sin(PI*t)+.005*cos(a*2)+( .0017 if k in (0,len(ts)-1) else .0002)*cos(3*a-phase);vs.append((x,Y+rad*cos(a),z+rad*sin(a)))
            for k in range(len(ts)-1):
                for i,a in enumerate(ang):
                    b=(i+1)%len(ang);n=len(ang);fs.append((k*n+i,k*n+b,(k+1)*n+b,(k+1)*n+i));base=[2,0,4,5][(row+j//3)%4];inds.append((1 if j%3!=0 else 3) if k in (3,7) else base)
            for k in (0,len(ts)-1):
                ci=len(vs);vs.append((x0+.001 if k==0 else x1-.001,Y,z));n=len(ang)
                for i in range(n):
                    f=(k*n+i,k*n+(i+1)%n,ci);fs.append(f[::-1] if k==0 else f);inds.append(base if i%7 else 1)
            mesh('Diamond drilled core',vs,fs,None,'Karst rock cores',slots=lith,indices=inds,smooth=True)
            # Sparse angular calcite inclusions and iron freckles on the drilled shell.
            grains=[];facets=[];gids=[]
            for g in range(135):
                u=rng.uniform(.035,.965);a=rng.uniform(-.18,PI+.18);t=u;rad=Rr*(1+.039*cos(5*a+phase)+.022*sin(a*3+2*t));C=Vector((x0+(x1-x0)*t,Y+(rad+.00038)*cos(a),z+(rad+.00038)*sin(a)));D=Vector((1,0,0));E=Vector((0,-sin(a),cos(a)));w=rng.uniform(.00065,.0026);h=w*rng.uniform(.35,.84);b=len(grains);grains.extend([C-D*w,C-E*h,C+D*w,C+E*h*.75]);facets.append((b+3,b+2,b+1,b));gids.append(rng.choice([4,2,1,1,3]))
            mesh('Stone inclusions',grains,facets,None,'Mineral texture',slots=lith,indices=gids)
    box('Tray identifier',(0,-.210,.056),(.336,.005,.053),teal,'Case labels',.002);text('BATU KAPUR   /   K-04',(0,-.213,.056),.023,cream,'Case labels')
    deliver((.49,-1,.82),'CDCCBF',1.13)


if __name__ == '__main__':
    main()
