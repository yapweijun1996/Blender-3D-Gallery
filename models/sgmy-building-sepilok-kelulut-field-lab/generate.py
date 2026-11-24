"""Stesen Kelulut | Stingless Bee Field Lab — original exterior model.
Rebuild: blender -b -P generate.py (no external assets).
Metres, ground-centred, street front -Y. Section meshes with UV0 and baked transforms.
Static material colours; Draco decoder required. Studio is preview-only.
"""
import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

TAU = 2 * math.pi
OUT = Path(__file__).resolve().parent
# Section batches keep the hierarchy editable without one draw call per prop.
PARTS = defaultdict(lambda: ([], [], [], []))
MATS = {}


def material(name, srgb, rough=.68, metallic=0):
    def linear(c):
        c = int(c, 16) / 255
        return c / 12.92 if c < .04045 else ((c + .055) / 1.055) ** 2.4
    rgb = tuple(linear(srgb[i:i+2]) for i in (0, 2, 4))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*rgb, 1)
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = m.diffuse_color
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metallic
    MATS[name] = m
    return name

def add(section, mat, verts, faces, smooth=False):
    vs, fs, ms, ss = PARTS[section]
    offset = len(vs)
    vs.extend(tuple(v) for v in verts)
    fs.extend(tuple(i + offset for i in f) for f in faces)
    ms.extend([mat] * len(faces))
    ss.extend([smooth] * len(faces) if isinstance(smooth, bool) else smooth)

@lru_cache(maxsize=256)
def box_template(w, d, h, bevel):
    x, y, z = w/2, d/2, h/2
    verts = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
             (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    if not bevel:
        return verts, faces
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in verts]
    for f in faces:
        bm.faces.new([v[i] for i in f])
    bm.normal_update()
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bevel, .35*min(w,d,h)),
                    segments=1, affect='EDGES')
    bm.verts.index_update()
    result = ([tuple(p.co) for p in bm.verts],
              [tuple(p.index for p in f.verts) for f in bm.faces])
    bm.free()
    return result

def box(section, mat, pos, dims, b=0, yaw=0, basis=None):
    verts, faces = box_template(*dims, b)
    if yaw:
        basis = Matrix.Rotation(yaw, 3, 'Z')
    if basis is not None:
        verts = [basis @ Vector(v) for v in verts]
    x, y, z = pos
    add(section, mat, [(u+x, v+y, w+z) for u,v,w in verts], faces)


def lathe(section, mat, x, y, rings, n=24, phase=0, smooth=True):
    # Each ring is (elevation, radius); positive radii avoid duplicate pole vertices.
    verts = [(x+r*math.cos(phase+TAU*j/n),y+r*math.sin(phase+TAU*j/n),z)
             for z,r in rings for j in range(n)]
    faces = [(i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j)
             for i in range(len(rings)-1) for j in range(n)]
    faces.extend((tuple(reversed(range(n))), tuple(range(len(verts)-n,len(verts)))))
    add(section, mat, verts, faces, [smooth]*(len(faces)-2)+[False,False])

def sign(section, mat, text, pos, width, height, yaw=0, flat=False):
    # Use only the Blender built-in font. Freeze the lettering to mesh for GLB.
    curve = bpy.data.curves.new('Sign artwork', 'FONT')
    curve.body, curve.align_x, curve.align_y = text, 'CENTER', 'CENTER'
    curve.resolution_u = 5
    ob = bpy.data.objects.new('Sign cutter', curve)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    mesh = ev.to_mesh()
    coords = [tuple(v.co) for v in mesh.vertices]
    w = max(p[0] for p in coords)-min(p[0] for p in coords)
    h = max(p[1] for p in coords)-min(p[1] for p in coords)
    s = min(width/w,height/h)
    x,y,z = pos
    turn = Matrix.Rotation(yaw, 3, 'Z')
    mesh.calc_loop_triangles()
    world = [Vector((x,y,z)) + turn @ (s * Vector((u,-q,v) if not flat else (u,v,q)))
             for u,v,q in coords]
    add(section, mat, world,
        [tuple(t.vertices) for t in mesh.loop_triangles])
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(curve)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    return scene

def finalize(scene):
    root = bpy.data.objects.new(TITLE, None)
    scene.collection.objects.link(root)
    root['asset_id'] = SLUG
    root['units'] = 'metres'
    root['facing'] = 'Blender -Y / glTF +Z'
    root['origin_note'] = 'Ground centre'
    root['revision'] = '1'
    root['role'] = ROLE
    for name,(verts,faces,assets,smooth) in PARTS.items():
        mesh = bpy.data.meshes.new(name + ' Geometry')
        mesh.from_pydata(verts, [], faces)
        assert not mesh.validate(verbose=True), name
        slots = {m:i for i,m in enumerate(dict.fromkeys(assets))}
        for m in slots:
            mesh.materials.append(MATS[m])
        for p,m,s in zip(mesh.polygons,assets,smooth):
            p.material_index = slots[m]
            p.use_smooth = s
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        # Texture-free material palette; UV0 still provides a non-overlapping edit/lightmap layout.
        uv = mesh.uv_layers.new(name='Layout')
        cells = math.ceil(math.sqrt(len(mesh.polygons)))
        for i,p in enumerate(mesh.polygons):
            ids = list(p.loop_indices)
            coords = [mesh.vertices[mesh.loops[j].vertex_index].co for j in ids]
            edges = [b-a for a,b in zip(coords,coords[1:]+coords[:1])]
            u = max(edges,key=lambda v:v.length_squared).normalized()
            v = p.normal.cross(u).normalized()
            px = [c.dot(u) for c in coords]
            py = [c.dot(v) for c in coords]
            x0,y0 = min(px),min(py)
            scale = .84 / max(max(px)-x0,max(py)-y0,1e-6)
            for j,x,y in zip(ids,px,py):
                uv.uv[j].vector = ((i%cells + .08 + (x-x0)*scale)/cells,
                                   (i//cells + .08 + (y-y0)*scale)/cells)
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        ob.parent = root
    bpy.ops.export_scene.gltf(filepath=str(OUT/'model.glb'), export_format='GLB',
                             export_yup=True, export_extras=True, export_animations=False,
                             export_draco_mesh_compression_enable=True,
                             export_draco_mesh_compression_level=6,
                             export_draco_position_quantization=20,
                             export_draco_normal_quantization=12,
                             export_draco_texcoord_quantization=16)
    assert (OUT/'model.glb').stat().st_size <= 2_000_000

def preview(scene, direction, resolution):
    # Studio is made only after the export and is not part of the game model.
    points = [Vector(v) for verts,_,_,_ in PARTS.values() for v in verts]
    mins = Vector(tuple(min(v[i] for v in points) for i in range(3)))
    maxs = Vector(tuple(max(v[i] for v in points) for i in range(3)))
    extent = max(maxs-mins)
    center = (mins+maxs)/2
    eye = Vector(direction).normalized()
    basis = (-eye).to_track_quat('-Z','Y')
    right,up = basis @ Vector((1,0,0)),basis @ Vector((0,1,0))
    xx = [(p-center).dot(right) for p in points]
    yy = [(p-center).dot(up) for p in points]
    aim = center + right*((max(xx)+min(xx))/2) + up*((max(yy)+min(yy))/2)
    cam = bpy.data.objects.new('Studio Camera',bpy.data.cameras.new('Studio Camera'))
    scene.collection.objects.link(cam)
    cam.location = aim + 2.8*extent*eye
    cam.rotation_euler = basis.to_euler()
    cam.data.type = 'ORTHO'
    cam.data.clip_end = extent*16
    aspect = resolution[0]/resolution[1]
    cam.data.ortho_scale = 1.16 * max(max(xx)-min(xx),(max(yy)-min(yy))*aspect)
    scene.camera = cam
    bpy.ops.mesh.primitive_plane_add(size=extent*220, location=(0,0,-.012))
    bpy.context.object.data.materials.append(MATS[material('Studio Limestone','a7a096',.9)])
    world = bpy.data.worlds.new('Studio Ambient')
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (.65,.77,1,1)
    bg.inputs[1].default_value = .29
    def light(name,xyz,power,size,color):
        data = bpy.data.lights.new(name,'AREA')
        ob = bpy.data.objects.new(name,data)
        scene.collection.objects.link(ob)
        ob.location = center+extent*Vector(xyz)
        ob.rotation_euler = (center-ob.location).to_track_quat('-Z','Y').to_euler()
        data.energy, data.size, data.color = power*extent**2,size*extent,color
    light('Warm Daylight',(-.85,-1.05,1.5),155,.85,(1,.91,.82))
    light('Cool Facade Fill',(1,-.55,.55),46,.95,(.83,.91,1))
    light('Soft Rim',(.25,1.1,1.5),72,1.0,(1,.97,.91))
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 18
    scene.cycles.max_bounces = 4
    scene.render.image_settings.compression = 30
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.75
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.resolution_x,scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    indexed_preview(scene)

def loft(section, mat, rings, smooth=False):
    """Join equal-sized, ordered closed cross sections (with end caps)."""
    n = len(rings[0])
    vertices = [v for ring in rings for v in ring]
    faces = [(i*n+j, i*n+(j+1)%n, (i+1)*n+(j+1)%n, (i+1)*n+j)
             for i in range(len(rings)-1) for j in range(n)]
    faces.extend((tuple(reversed(range(n))),tuple(range(len(vertices)-n,len(vertices)))))
    add(section, mat, vertices, faces, [smooth]*(len(faces)-2)+[False,False])

def round_ring(x, y, z, w, d, r, n=5):
    return [(x+cx+r*math.cos(a),y+cy+r*math.sin(a),z)
            for i,(cx,cy) in enumerate(((w/2-r,d/2-r),(-w/2+r,d/2-r),
                                        (-w/2+r,-d/2+r),(w/2-r,-d/2+r)))
            for a in [(i+j/n)*math.pi/2 for j in range(n+1)]]

def rounded(section, mat, x, y, w, d, lower, upper, radius):
    loft(section, mat, [round_ring(x,y,z,w,d,radius) for z in (lower,upper)])

def ring(section, mat, outer, inner, h):
    """A thin hollow curb or drum with paired outlines, horizontal top and bottom."""
    n = len(outer)
    v = outer+inner+[(x,y,z+h) for x,y,z in outer]+[(x,y,z+h) for x,y,z in inner]
    f = []
    for i in range(n):
        j = (i+1)%n
        f += [(i,j,j+2*n,i+2*n),(i+n,i+3*n,j+3*n,j+n),
              (i+2*n,j+2*n,j+3*n,i+3*n),(i,i+n,j+n,j)]
    add(section, mat, v, f)


def block(s,m,x,y,z,w,d,h,b=.025):
    """Box specified by its bottom elevation."""
    box(s,m,(x,y,z+h/2),(w,d,h),b)


def skin(s,m,quad,thickness=.12):
    # Extrude a roof panel downwards; include a fascia on all edges.
    loft(s,m,[[(x,y,z-thickness) for x,y,z in quad],quad])

def window(s,frame,glass,x,y,z,w,h,yaw=0,bays=2):
    origin=Vector((x,y,z)); mat=Matrix.Rotation(yaw,3,'Z')
    def plate(m,u,v,t,a,b,c):
        box(s,m,origin+mat@Vector((u,v,t)),(a,b,c),.012,basis=mat)
    plate(frame,0,0,0,w,.19,h)
    plate(glass,0,-.109,0,w-.18,.05,h-.19)
    for j in range(1,bays): plate(frame,(j/bays-.5)*w,-.15,0,.072,.05,h-.16)
    plate(frame,0,-.15,h*.18,w-.14,.06,.065)
    plate(frame,0,-.10,-h/2,w+.18,.32,.1)

def plaque(s,base,ink,txt,x,y,z,w,h):
    box(s,base,(x,y,z),(w,.14,h),.045)
    sign(s,ink,txt,(x,y-.079,z),w*.89,h*.66)

def pad(s,x,y,w,d,cap,edge):
    rounded(s,edge,x,y,w,d,0,.23,.40)
    rounded(s,cap,x,y,w-.12,d-.12,.23,.30,.36)


def palette():
    global ivory,ochre,steel,shadow,glass,sand,rock,oxide,teal,leaf,sage,wood,brass
    ivory=material('Limewashed cream','f2e4c7'); ochre=material('Saffron enamel','e9aa53',.45)
    steel=material('Galvanised alloy','9eaeb0',.46,.35); shadow=material('Deep indigo hardware','293f48',.48,.18)
    glass=material('Petrol blue glazing','325e69',.23,.34); sand=material('Sandstone flags','cdbda6'); rock=material('Granite kerb','928b80')
    oxide=material('Fired vermilion','b95440'); teal=material('Peacock enamel','30796e',.46,.12)
    leaf=material('Pandan green','597447'); sage=material('Young leaf','88995e'); wood=material('Oiled meranti','815641'); brass=material('Patinated brass','c69759',.38,.33)

def pipe(s,m,a,b,r,n=12):
    a,b=Vector(a),Vector(b)
    rot=(b-a).to_track_quat('Z','Y').to_matrix()
    loft(s,m,[[p+rot@Vector((r*math.cos(TAU*i/n),r*math.sin(TAU*i/n),0)) for i in range(n)] for p in (a,b)],True)


def indexed_preview(scene):
    # Render an sRGB bitmap, then palette-pack that render as PNG8. No external encoder.
    import struct, zlib
    import numpy as np
    tmp=OUT/'.studio.bmp'
    scene.render.image_settings.file_format='BMP'
    scene.render.filepath=str(tmp)
    bpy.ops.render.render(write_still=True)
    try:
        data=tmp.read_bytes(); offset=struct.unpack_from('<I',data,10)[0]
        w,h=struct.unpack_from('<ii',data,18); bpp=struct.unpack_from('<H',data,28)[0]//8
        assert bpp in (3,4) and h>0
        stride=(w*bpp+3)&~3
        rgb=np.frombuffer(data,dtype='uint8',offset=offset,count=h*stride).reshape(h,stride)[::-1,:w*bpp].reshape(h,w,bpp)[:,:,:3][:,:,::-1]
        # Weighted median cuts on occupied sRGB bins preserve small accent materials.
        bins=rgb.astype(np.int32)//2; idx=(bins[:,:,0]*128+bins[:,:,1])*128+bins[:,:,2]
        keys,inverse,counts=np.unique(idx.ravel(),return_inverse=True,return_counts=True)
        colors=np.stack((keys//16384,(keys//128)%128,keys%128),axis=1)*2+1
        def stats(ids):
            c=colors[ids]; wt=counts[ids]; mean=np.average(c,axis=0,weights=wt)
            dev=np.sum((c-mean)**2*wt[:,None],axis=0); channel=int(dev.argmax())
            return (dev[channel],ids,channel,mean)
        groups=[stats(np.arange(len(keys)))]
        while len(groups)<256:
            g=max(range(len(groups)),key=lambda i:groups[i][0]); score,ids,k,_=groups.pop(g)
            if score==0: groups.append(stats(ids));break
            ids=ids[np.argsort(colors[ids,k],kind='stable')]; cum=counts[ids].cumsum()
            cut=max(1,min(len(ids)-1,int(np.searchsorted(cum,cum[-1]/2))+1))
            groups.extend((stats(ids[:cut]),stats(ids[cut:])))
        lut=np.zeros(len(keys),dtype=np.uint8); pal=[]
        for i,(_,ids,_,mean) in enumerate(groups):
            lut[ids]=i;pal.extend(mean.round().astype('uint8').tolist())
        rows=lut[inverse].reshape(h,w); raw=b''.join(b'\0'+row.tobytes() for row in rows)
        def chunk(tag,payload):
            return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload))
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,3,0,0,0))+chunk(b'PLTE',bytes(pal))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
        assert len(png)<=250000
        (OUT/'preview.png').write_bytes(png)
    finally:
        tmp.unlink(missing_ok=True)



def elevation(s,m,x,y,z,outline,depth):
    """Extrude a silhouette in the vertical street elevation."""
    loft(s,m,[[(x+u,y+j*depth/2,z+v) for u,v in outline] for j in (-1,1)])

def beam(s,m,a,b,w,d=None):
    a,b=Vector(a),Vector(b)
    box(s,m,(a+b)*.5,(w,d or w,(b-a).length),b=.009,basis=(b-a).to_track_quat('Z','Y').to_matrix())

def hip(s,m,trim,x,y,w,d,eave,rise,ridge):
    # Four broad slopes and raised ridge rolls, with narrow tile courses on each slope.
    x0,x1=x-w/2,x+w/2;y0,y1=y-d/2,y+d/2
    A=(x0,y0,eave);B=(x1,y0,eave);C=(x1,y1,eave);D=(x0,y1,eave)
    E=(x-ridge/2,y,eave+rise);F=(x+ridge/2,y,eave+rise)
    for poly in ([A,B,F,E],[D,E,F,C],[A,E,D],[B,C,F]):skin(s,m,poly,.16)
    def mix(a,b,t):return tuple(u*(1-t)+v*t for u,v in zip(a,b))
    for a,b,c,d1 in [(A,B,E,F),(D,C,E,F),(A,D,E,E),(B,C,F,F)]:
        for i in range(1,9):
            t=i/10;beam(s,m,mix(a,c,t),mix(b,d1,t),.06)
    for a,b in ((A,E),(B,F),(C,F),(D,E),(E,F),(A,B),(B,C),(C,D),(D,A)):beam(s,trim,a,b,.14)

def stair(s,m,x,front,w,tread,rise,n):
    for j in range(n):block(s,m,x,front+(j+.5)*tread,.30,w,tread,(j+1)*rise,.018)

def leafspray(s,x,y,z,k=1):
    # Pleated lanceolate leaves around a single crown; no alpha textures.
    for i in range(13):
        a=i*2.399; co,si=math.cos(a),math.sin(a);length=(.86+.23*(i%3))*k
        def at(t,w,h):return (x+co*length*t-si*w*k,y+si*length*t+co*w*k,z+k*h)
        pts=[at(0,0,.03),at(.55,-.14,.63),at(.53,0,.73),at(.55,.14,.63),at(1,0,.50+.15*(i%4))]
        add(s,leaf if i%3 else sage,pts,[(0,1,2),(0,2,3),(1,4,2),(2,4,3)])

def nameboard(s,txt,x,y,z,w,h,base=None):
    plaque(s,base or teal,ivory,txt,x,y,z,w,h)

SLUG='sgmy-building-sepilok-kelulut-field-lab'
TITLE='Stesen Kelulut | Stingless Bee Field Lab'
ROLE='Sabah stingless bee research apiary and honey sampling laboratory'
VIEW=(.53,-1,.67)

def build():
    a='Gravel Sampling Yard'; b='Hexagonal Field Lab'; r='Copper Cell Roofs'; h='Log Hive Stands'; g='Pollinator Beds'
    honey=material('Honey enamel','dea345'); cream=material('Pale kapur cladding','ead1a2'); rust=material('Copper patina','ac6c49',.50,.23);cocoa=material('Belian endgrain','5c4535');moss=material('Moss green hive cover','557a63');blue=material('Deep blue sash','304e56'); zinc=material('Roof flashing','beb9a9',.45,.28)
    pad(a,0,0,23.25,17.4,sand,rock)
    for j,(x,y,rad,H) in enumerate([(-5.71,3.65,3.95,4.14),(0,2.85,4.68,5.59),(6.22,3.70,3.80,4.32)]):
        phase=0
        def pt(rad,ang,z):return Vector((x+rad*math.cos(ang),y+rad*math.sin(ang),z))
        lathe(b,rock,x,y,[(.30,rad+.14),(.62,rad+.14)],6,phase,False)
        lathe(b,cream,x,y,[(.62,rad),(H,rad)],6,phase,False)
        for i in range(6):
            t=i*TAU/6;u=(i+1)*TAU/6; mid=(t+u)*.5
            for z,w in ((.66,.12),(H-.64,.11)):
                beam(b,honey,pt(rad+.024,t,z),pt(rad+.024,u,z),w)
            beam(b,cocoa,pt(rad,t,.62),pt(rad,t,H),.18)
            P=pt(rad*math.cos(math.pi/6)+.04,mid,.5*(.62+H))
            yaw=mid+math.pi/2
            if i==4 and j==1:window(b,cocoa,glass,P.x,P.y,2.05,2.39,2.81,yaw)
            else:window(b,blue,glass,P.x,P.y,P.z+.24,rad*.71,1.56,yaw,3)
        # Six folded facets broken by a glazed clerestory cap.
        for z1,R1,z2,R2,m in ((H,rad+.54,H+.21,rad+.54,cocoa),(H+.21,rad+.54,H+1.31,rad*.41,rust),(H+1.31,rad*.41,H+1.89,rad*.41,glass),(H+1.89,rad*.49,H+2.20,rad*.14,honey)):
            lathe(r,m,x,y,[(z1,R1),(z2,R2)],6,phase,False)
            for i in range(6):pipe(r,zinc,pt(R1,i*TAU/6,z1+.02),pt(R2,i*TAU/6,z2+.02),.052,8)
        if j==1:nameboard(b,'S T E S E N    K E L U L U T',x,y-rad*.866-.12,4.31,4.46,.70,blue)
    stair(a,wood,0,-2.55,2.63,.40,.11,3)
    for sy in (-2.95,-5.49):
        for side in (-1,1):
            rounded(a,rock,side*6.19,sy,7.21,1.72,.30,.44,.30)
            for i in range(3):
                x=side*(3.62+i*2.53);y=sy;v=.08*((i+side)%3)
                # Hollow-trunk meliponary with honey super, resin trumpet and pitched rain hat.
                lathe(h,zinc,x,y,[(.44,.38),(.57,.38),(.57,.12),(.91,.12)],12)
                lathe(h,cocoa,x,y,[(.91,.35),(1.08,.42),(1.63+v,.36),(1.83+v,.37)],11,.21*i,False)
                for k in (1.00,1.68+v):lathe(h,steel,x,y,[(k,.398),(k+.065,.398)],12)
                block(h,wood,x,y,1.81+v,1.18,1.02,.53);block(h,honey,x,y,1.99+v,1.21,1.05,.10)
                pipe(h,cocoa,(x,y-.27,1.40),(x+.12,y-.64,1.47),.092,12)
                pipe(h,ochre,(x+.10,y-.59,1.46),(x+.13,y-.69,1.48),.115,12)
                for sgn in (-1,1):skin(h,moss,[(x,-.70+y,2.63+v),(x+sgn*.82,y-.70,2.38+v),(x+sgn*.82,y+.70,2.38+v),(x,y+.70,2.63+v)],.075)
                plaque(h,blue,cream,'K'+str(i+1),x,y-.54,2.18+v,.44,.22)
    for x in (-8.88,8.88):
        rounded(g,moss,x,-7.30,3.96,1.52,.30,.68,.45)
        for dx in (-1.12,0,1.12):leafspray(g,x+dx,-7.30,.68,.69)
    # Sampling station identifier at the head of the hive aisle.
    for x in (-1.18,1.18):block(a,cocoa,x,-6.81,.30,.13,.13,1.51)
    nameboard(a,'MADU   /   01',0,-6.84,1.68,3.14,.85,blue)

if __name__ == '__main__':
    scene = reset()
    palette()
    build()
    finalize(scene)
    preview(scene, VIEW, (760, 650))
