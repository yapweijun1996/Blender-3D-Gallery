"""Akademi Rentak | Kompang Music School | Original static architecture for a Singapore / Malaysia street world.
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

SLUG = 'sgmy-building-dewan-kompang-music-school'
TITLE = 'Akademi Rentak | Kompang Music School'
ROLE = 'Johor percussion school with a pair of drum-shaped rehearsal halls'
VIEW = (.61,-1,.47)

def build():
    s='Teaching Wing'; halls='Kompang Studios'; art='Carved Acoustic Screens'; fore='Music Court'; roof='Drumhead Roofs'
    plum=material('Cinnamon lacquer','9a463c',.46); russet=material('Padauk timber','9c5942'); maple=material('Rim veneer','d4a164'); parchment=material('Warm hide roof membrane','f0d6a7'); ink=material('Indigo ceramic','364e58'); citron=material('Turmeric enamel','db9e42'); sea=material('Deep lagoon clerestory','44757a',.25,.35)
    pad(fore,0,0,28.6,19.2,sand,rock)
    rounded(s,rock,0,-.7,24.52,11.28,.30,.77,.91);rounded(s,parchment,0,-.7,24.24,10.98,.77,4.16,.84)
    for xx in (-9.65,-6.43,6.43,9.65):window(s,russet,sea,xx,-6.22,2.32,2.76,2.13,bays=3)
    for xx in (-2.61,0,2.61):window(s,ink,sea,xx,-6.24,2.26,2.47,2.96)
    rounded(s,ink,0,-.7,24.89,11.69,4.14,4.48,.97)
    # Parallel entry colonnade with a gilded writing band and syncopated sun baffles.
    for x in (-11.35,-8.43,-4.32,4.32,8.43,11.35):
        tube(s,plum,(x,-7.20,.32),(x,-7.20,3.79),.14,n=12)
    block(s,citron,0,-6.76,3.79,23.41,2.57,.43)
    for j in range(37):box(s,maple,(-11.19+j*.62,-7.98,4.07),(.12,.34,.61 if j%3 else .79),.014)
    plaque(s,plum,ivory,'A K A D E M I   R E N T A K',0,-8.11,4.02,10.42,.83)
    steps(fore,sand,brass,0,-9.14,7.65,3,.41,.1567,.30)
    for x in (-9.49,9.49):leafbed(fore,x,-8.31,4.31,1.04)
    for x,y,r,z0,lid,tilt in [(-6.40,2.46,5.38,.30,9.90,-.19),(6.38,2.63,4.65,.30,8.15,.21)]:
        N=48
        def pt(j,rr,z,sl=0):
            a=TAU*j/N;return (x+rr*math.cos(a),y+rr*math.sin(a),z+sl*rr*math.cos(a))
        def loop(rr,z,sl=0):return [pt(j,rr,z,sl) for j in range(N)]
        def wrap(m,r1,h1,t1,r2,h2,t2):loft(halls,m,[loop(r1,h1,t1),loop(r2,h2,t2)])
        wrap(ink,r*.88,z0,0,r*.88,4.62,0);wrap(sea,r*.92,4.54,0,r*.92,lid-2.52,tilt)
        for k in range(24):line(art,brass,pt(k*2,r*.925,4.50),pt(k*2,r*.925,lid-2.51,tilt),.12)
        wrap(maple,r*.92,lid-2.54,tilt,r,lid-2.24,tilt)
        wrap(russet,r,lid-2.24,tilt,r*1.057,lid-.36,tilt)
        # Repeated hand-carved lozenges and brass tack rosettes around the wooden shells.
        for j in range(24):
            pts=[pt(j*2-.81,r*1.045,lid-1.28,tilt),pt(j*2,r*1.062,lid-.62,tilt),pt(j*2+.81,r*1.045,lid-1.28,tilt),pt(j*2,r*1.016,lid-1.94,tilt)]
            for a,b in zip(pts,pts[1:]+pts[:1]):line(art,maple,a,b,.065)
            p=pt(j*2,r*1.045,lid-1.28,tilt);q=pt(j*2,r*1.059,lid-1.28,tilt);tube(art,citron,p,q,.13,n=12)
        wrap(plum,r*1.059,lid-.43,tilt,r*1.063,lid-.27,tilt);wrap(maple,r*1.07,lid-.26,tilt,r*1.078,lid+.04,tilt)
        loft(roof,parchment,[loop(r*1.080,lid+.04,tilt),loop(r*1.055,lid+.16,tilt),loop(r*.51,lid+.28,tilt)])
        if r>5:
            loft(roof,ink,[loop(r*.43,lid+.28,tilt),loop(r*.40,lid+.59,tilt)])
            loft(roof,sea,[loop(r*.397,lid+.59,tilt),loop(r*.13,lid+.91,tilt)])
            for j in range(0,N,4):line(roof,brass,pt(j,r*.40,lid+.60,tilt),pt(j,r*.13,lid+.93,tilt),.077)
    for yy in (-4.05,-1.30):window(s,russet,sea,12.17,yy,2.39,2.18,2.08,math.pi/2)

if __name__ == '__main__':
    scene = reset()
    palette()
    build()
    finalize(scene)
    preview(scene, VIEW, (780, 700))
    palette_png(OUT / 'preview.png')
