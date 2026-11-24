"""Laman Kenyalang | Canopy Aviary | Original static architecture for a Singapore / Malaysia street world.
Rebuild: blender -b --python-exit-code 1 --python generate.py
One unit = one metre; ground-centred origin, -Y street face. Procedural PBR palette,
UV0 and mesh lettering; no external assets. Export requires a glTF Draco decoder.
The camera, lights and studio floor are created only after the model export.
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

def prism(section, mat, poly, a, b, axis='Y'):
    # A simple cross-section, extruded along X or Y.
    verts = [(u,v,w) if axis == 'Y' else (v,u,w) for v in (a,b) for u,w in poly]
    n = len(poly)
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces.extend((i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n))
    add(section, mat, verts, faces)

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
                             export_draco_position_quantization=18,
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
    scene.cycles.samples = 10
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
    scene.render.filepath = str(OUT/'preview.png')
    bpy.ops.render.render(write_still=True)

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

def steps(section, stone, line, x, y, width, count, tread, rise, z0):
    for i in range(count):
        zz = z0 + (i+1)*rise
        yy = y+(i+.5)*tread
        box(section,stone,(x,yy,(z0+zz)/2),(width,tread+.012,zz-z0),.016)
        box(section,line,(x,yy-tread*.37,zz+.007),(width-.07,.039,.015),.004)

def foliage(section, mat, pos, radii, n=8, phase=0):
    x,y,z = pos
    w,d,h = radii
    rings = []
    for k,(s,t) in enumerate(((.27,-.91),(.83,-.58),(1,.03),(.76,.56),(.27,.92))):
        rings.append([(x+w*s*math.cos(a),y+d*s*math.sin(a),z+h*t)
                      for a in [phase+TAU*(j+.48*(k%2))/n for j in range(n)]])
    loft(section,mat,rings,True)

def shrub_row(section, pot, soil, greens, x, y, z, width, depth=.83):
    box(section,pot,(x,y,z+.24),(width,depth,.48),.065)
    box(section,soil,(x,y,z+.488),(width-.18,depth-.16,.022),.02)
    n = max(2,round(width/.4))
    for j in range(n):
        u = (j+.5-n/2)*(width-.13)/n
        foliage(section,greens[j%len(greens)],(x+u,y+.10*math.sin(j*13),z+.68),
                (.25+.035*(j%3),depth*.44,.29+.022*(j%4)),7,j*.618)

def block(s,m,x,y,z,w,d,h,b=.025):
    """Box specified by its bottom elevation."""
    box(s,m,(x,y,z+h/2),(w,d,h),b)

def line(s,m,a,b,t,depth=None):
    a,b=Vector(a),Vector(b)
    box(s,m,(a+b)/2,(t,depth or t,(b-a).length),.008,basis=(b-a).to_track_quat('Z','Y').to_matrix())

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

def leafbed(s,x,y,w,d):
    shrub_row(s,ivory,shadow,[leaf,sage],x,y,.30,w,d)

def palette():
    global ivory,ochre,steel,shadow,glass,sand,rock,oxide,teal,leaf,sage,wood,brass
    ivory=material('Limewashed cream','f2e4c7'); ochre=material('Saffron enamel','e9aa53',.45)
    steel=material('Galvanised alloy','9eaeb0',.46,.35); shadow=material('Deep indigo hardware','293f48',.48,.18)
    glass=material('Petrol blue glazing','325e69',.23,.34); sand=material('Sandstone flags','cdbda6'); rock=material('Granite kerb','928b80')
    oxide=material('Fired vermilion','b95440'); teal=material('Peacock enamel','30796e',.46,.12)
    leaf=material('Pandan green','597447'); sage=material('Young leaf','88995e'); wood=material('Oiled meranti','815641'); brass=material('Patinated brass','c69759',.38,.33)


def palette_png(path):
    """Quantize the display-referred render without any external image tools."""
    import struct, zlib
    import numpy as np
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    w,h = image.size[:]
    rgba = np.empty(w*h*4, np.float32)
    image.pixels.foreach_get(rgba)
    rgb = np.uint8(np.clip(rgba.reshape(h,w,4)[::-1,:,:3]*255+.5,0,255)).reshape(-1,3)
    bpy.data.images.remove(image)
    q = rgb.astype(np.int32) >> 1
    bins, key, weights = np.unique(q[:,0]*16384 + q[:,1]*128 + q[:,2], return_inverse=True, return_counts=True)
    used = np.arange(len(bins))
    colors = np.column_stack([np.bincount(key,weights=rgb[:,i])/weights for i in range(3)])
    def priority(ix):
        if len(ix)<2: return 0
        return np.max(np.ptp(colors[ix],axis=0))*math.sqrt(weights[ix].sum())
    cells = [np.arange(len(used))]
    for _ in range(255):
        idx=max(range(len(cells)),key=lambda i:priority(cells[i]))
        ix=cells.pop(idx)
        if len(ix)<2:
            cells.append(ix); break
        axis=np.argmax(np.ptp(colors[ix],axis=0)); ix=ix[np.argsort(colors[ix,axis])]
        cut=np.clip(np.searchsorted(np.cumsum(weights[ix]),weights[ix].sum()/2)+1,1,len(ix)-1)
        cells.extend([ix[:cut],ix[cut:]])
    pal=np.uint8([np.average(colors[ix],axis=0,weights=weights[ix])+.5 for ix in cells]); lut=np.zeros(len(used),np.uint8)
    for k in range(0,len(used),256):
        diff=colors[k:k+256,None,:]-pal[None,:,:]; lut[used[k:k+256]]=np.argmin((diff**2).sum(axis=2),axis=1)
    data=b''.join(b'\0'+r.tobytes() for r in lut[key].reshape(h,w))
    def chunk(tag,buf): return struct.pack('>I',len(buf))+tag+buf+struct.pack('>I',zlib.crc32(tag+buf)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,3,0,0,0))+chunk(b'PLTE',pal.tobytes())+chunk(b'IDAT',zlib.compress(data,9))+chunk(b'IEND',b'')
    assert len(png)<=250000
    path.write_bytes(png)

def tube(s,m,a,b,r,r2=None,n=16):
    a,b=Vector(a),Vector(b); R=(b-a).to_track_quat('Z','Y').to_matrix()
    loft(s,m,[[p+R@Vector((rr*math.cos(TAU*k/n),rr*math.sin(TAU*k/n),0)) for k in range(n)] for p,rr in ((a,r),(b,r if r2 is None else r2))],True)

def gable(s,m,trim,x,y,w,d,eave,ridge):
    for side in (-1,1):
        skin(s,m,[(x+side*w/2,y-d/2,eave),(x+side*w/2,y+d/2,eave),(x,y+d/2,ridge),(x,y-d/2,ridge)],.16)
        for j in range(1,round(d*1.3)):
            yy=y-d/2+d*j/round(d*1.3); line(s,trim,(x+side*w/2,yy,eave+.015),(x,yy,ridge+.015),.048)
        for yy in (y-d/2,y+d/2): line(s,trim,(x+side*w/2,yy,eave),(x,yy,ridge),.16)
    line(s,trim,(x,y-d/2-.12,ridge),(x,y+d/2+.12,ridge),.16)

def framehall(s,wall,roof,trim,x,y,w,d,z,h,rise):
    block(s,wall,x,y,z,w,d,h)
    prism(s,wall,[(x-w/2,z+h-.1),(x+w/2,z+h-.1),(x,z+h+rise)],y-d/2,y+d/2)
    gable(s,roof,trim,x,y,w+1.3,d+1.5,z+h-.18,z+h+rise+.12)

def rail(s,m,a,b,h=.95,posts=5):
    a,b=Vector(a),Vector(b); v=Vector((0,0,h))
    for p in (0.5,1): tube(s,m,a+v*p,b+v*p,.044,n=8)
    for j in range(posts):
        p=a+(b-a)*j/(posts-1);tube(s,m,p,p+v,.048,n=8)

def circle(x,y,z,r,n=48,phase=0):
    return [(x+r*math.cos(TAU*j/n+phase),y+r*math.sin(TAU*j/n+phase),z) for j in range(n)]

SLUG = 'sgmy-building-kenyalang-canopy-aviary'
TITLE = 'Laman Kenyalang | Canopy Aviary'
ROLE = 'Sarawak walk-through aviary with netted forest canopy and hornbill casque entrance'
VIEW = (.56,-1,.39)

def build():
    s='Forest Enclosure'; arch='Bent Portal Ribs'; net='Tension Net'; grove='Habitat Planting'; gate='Casque Gate'; path='Visitor Walk'
    black=material('Blue black steel','324950'); wire=material('Patinated net cable','84978d',.46,.24); amber=material('Hornbill amber','efa943'); orange=material('Crest orange','d16f3a'); bone=material('Buff sail canvas','e3caaa'); fern=material('Fern shade','457b57'); palm=material('Canopy jade','719455'); bark=material('Rain tree bark','79614c'); soil=material('Leaf litter','aa9770')
    pad(path,0,0,29.2,21.8,sand,rock)
    # Vault cross-sections swell at the east end; arch cross section rests on a low kerb.
    def P(u,t,lift=0):
        a=math.pi*t;bulge=max(0,1-u*u)**.60;w=1.84+5.56*bulge;h=1.68+7.35*bulge+1.04*u
        return Vector((12.63*u,1.86+w*math.cos(a),.88+h*math.sin(a)+lift))
    outline=[tuple(P(-1+2*j/48,0)) for j in range(49)]+[tuple(P(1-2*j/48,1)) for j in range(49)]
    loft(s,rock,[[(x,y,.30) for x,y,z in outline],outline]);loft(s,soil,[outline,[(x,y,z+.045) for x,y,z in outline]])
    # Two layers: widely spaced structural arches and a delicate, diagonally braced cable net.
    for j in range(13):
        u=-1+j/6; pts=[P(u,k/26,.035) for k in range(27)]
        for a,b in zip(pts,pts[1:]):tube(arch,black,a,b,.105,n=8)
        for a in (pts[0],pts[-1]):lathe(arch,rock,a.x,a.y,[(.88,.25),(1.19,.25),(1.26,.16)],12)
    for j in range(36):
        u=-1+j/18;v=u+1/18
        for k in range(22):
            a=k/22;b=(k+1)/22
            for a1,b1 in ((a,b),(b,a)):tube(net,wire,P(u,a1),P(v,b1),.023,n=5)
    for k in range(1,11):
        t=k/11
        for j in range(36):tube(net,wire,P(-1+j/18,t,.01),P(-1+(j+1)/18,t,.01),.034,n=6)
    for u in (-1,1):
        for j in range(1,14):
            p=P(u,j/14);tube(net,wire,(p.x,p.y,.90),p,.029,n=6)
    # Overlapping feather-shaped shade sails on the sunward half only; canopy still reads as mesh.
    for j in range(6):
        u=-.83+j*.275
        for k in range(5):
            v=u+k*.055;w=v+.055
            def tt(i):return .28+.20*math.sin(math.pi*i/6)
            corners=[P(v,.19,.11),P(w,.19,.11),P(w,tt(k+1),.15),P(v,tt(k),.15)]
            skin(arch,bone if j%2==0 else sage,corners,.045)
    # Elevated walkway, split perch trees and a broad-leaf understorey inside the net.
    coords=[(-10.6,.35,1.45),(-7.31,-.78,1.79),(-2.72,-1.66,2.01),(2.95,-1.16,2.01),(7.89,.15,1.78),(10.72,1.17,1.46)]
    for a,b in zip(coords,coords[1:]):
        p,q=Vector(a),Vector(b);corners=[p+Vector((0,-.67,0)),q+Vector((0,-.67,0)),q+Vector((0,.67,0)),p+Vector((0,.67,0))];skin(path,wood,corners,.16)
        for k in (-1,1):rail(path,wood,p+Vector((0,k*.63,0)),q+Vector((0,k*.63,0)),.91,4)
        block(path,bark,p.x,p.y,.90,.22,.32,p.z-.90)
    for i,(x,y,h) in enumerate([(-8.01,3.11,4.73),(-4.30,4.13,6.13),(.37,4.41,6.51),(6.42,4.11,5.80),(9.11,2.77,4.98),(-5.46,-2.54,3.07),(4.12,-2.81,3.45)]):
        p=Vector((x,y,.92));q=Vector((x+.36,y+.15,h-.62));tube(grove,bark,p,q,.24,.12)
        for j in range(5):
            a=TAU*j/5+i;r=.84+.22*((j+i)%3);v=Vector((x+r*math.cos(a),y+r*math.sin(a),h+.40*math.sin(2*a)))
            tube(grove,bark,q-Vector((0,0,.81)),v,.12,.054,n=9)
            foliage(grove,fern if (j+i)%3 else palm,v,(1.13,.96,.72),9,j*.567)
    # Ramped spur runs from the airlock to the raised walk. Pond and natural
    # perches give the enclosure a habitat at both ground and canopy level.
    skin(path,wood,[(-1.91,-4.11,1.38),(.11,-4.11,1.38),(.11,-1.50,2.01),(-1.91,-1.50,2.01)],.15)
    for xx in (-1.86,.06):rail(path,wood,(xx,-4.10,1.38),(xx,-1.52,2.01),.88,4)
    def pool(rr,z):return [(3.65+rr*2.51*math.cos(a),1.84+rr*1.61*math.sin(a),z) for a in [TAU*j/30 for j in range(30)]]
    loft(grove,rock,[pool(1,.92),pool(1.03,1.11)]);loft(grove,glass,[pool(.94,1.11),pool(.93,1.14)])
    for xx,yy,side in [(-7.21,-1.97,1),(6.97,-1.62,-1)]:
        p=Vector((xx,yy,.92));q=p+Vector((.48*side,0,2.09));v=q+Vector((1.42*side,.21,.35))
        tube(grove,bark,p,q,.19,.11);tube(grove,bark,q,v,.12,.067)
        tube(grove,bark,q,q+Vector((-.73*side,-.18,.89)),.11,.042)
        x0,y0,z0=v+Vector((-.28*side,0,.26))
        foliage(grove,black,(x0,y0,z0),(.34,.16,.21),12);foliage(grove,black,(x0+.21*side,y0,z0+.18),(.17,.14,.15),12)
        tube(grove,amber,(x0+.31*side,y0,z0+.18),(x0+.65*side,y0,z0+.14),.09,.018)
        foliage(grove,orange,(x0+.39*side,y0,z0+.25),(.12,.056,.065),10)
        tube(grove,bone,(x0-.25*side,y0,z0-.05),(x0-.72*side,y0,z0-.17),.092,.066)
    for i in range(14):
        u=-.85+i*.129;p=P(u,1);foliage(grove,sage if i%3 else leaf,(p.x,p.y+.74,1.14),(.51,.48,.48),7,i*.61)
    # Entry airlock under a sculptural hornbill bill/casque, cut from layered wooden sections.
    rounded(gate,black,-.87,-5.58,6.88,3.88,.30,3.24,.54)
    for xx in (-2.42,.68):window(gate,wood,glass,xx,-7.55,1.75,2.73,2.86)
    for xx in (-3.86,2.17):
        tube(gate,black,(xx,-8.03,.30),(xx,-8.03,3.69),.18,n=12)
    # Long tapered bill is supported by the airlock roof; a raised asymmetric casque sits on top.
    def bill_section(x,w,lo,hi):
        return [(x,-7.23+w*u,lo+(hi-lo)*v) for u,v in [(-.90,.04),(-1,.52),(-.74,.88),(0,1),(.74,.88),(1,.52),(.90,.04),(0,0)]]
    stations=[(-5.55,.85,3.56,4.33),(-4.90,1.54,3.34,4.70),(-3.35,1.67,3.27,4.87),(.25,1.70,3.38,4.94),(3.39,1.51,3.70,5.13),(5.62,1.04,4.17,5.33),(7.09,.59,4.82,5.55),(8.16,.055,5.73,5.89)]
    loft(gate,amber,[bill_section(*q) for q in stations[:-2]]);loft(gate,black,[bill_section(*q) for q in stations[-3:]])
    loft(gate,orange,[bill_section(*q) for q in [(-4.70,.46,4.46,4.82),(-3.92,.96,4.49,5.50),(-2.79,1.04,4.63,5.99),(-1.62,.87,4.69,6.09),(-.69,.76,4.71,6.21),(.79,.44,5.41,6.51),(1.58,.04,6.36,6.69)]])
    plaque(gate,black,ivory,'L A M A N   K E N Y A L A N G',-.98,-8.99,4.00,6.97,.65)

if __name__ == '__main__':
    scene = reset()
    palette()
    build()
    finalize(scene)
    preview(scene, VIEW, (780, 700))
    palette_png(OUT / 'preview.png')
