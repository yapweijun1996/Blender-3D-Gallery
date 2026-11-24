"""Dataran Bunga Kantan | Original static SG/MY street architecture.
Rebuild: blender -b --python-exit-code 1 --python generate.py
Metres; centred ground origin; -Y street front. Geometry, UV0, palette, and
lettering are procedural. No downloaded inputs. Requires a Draco decoder.
Only the GLB is a game asset; studio floor, camera and lights are render-only.
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

def foliage(section, mat, pos, radii, n=8, phase=0):
    x,y,z = pos
    w,d,h = radii
    rings = []
    for k,(s,t) in enumerate(((.27,-.91),(.83,-.58),(1,.03),(.76,.56),(.27,.92))):
        rings.append([(x+w*s*math.cos(a),y+d*s*math.sin(a),z+h*t)
                      for a in [phase+TAU*(j+.48*(k%2))/n for j in range(n)]])
    loft(section,mat,rings,True)

def block(s,m,x,y,z,w,d,h,b=.025):
    """Box specified by its bottom elevation."""
    box(s,m,(x,y,z+h/2),(w,d,h),b)

def line(s,m,a,b,t,depth=None):
    a,b=Vector(a),Vector(b)
    box(s,m,(a+b)/2,(t,depth or t,(b-a).length),.008,basis=(b-a).to_track_quat('Z','Y').to_matrix())

def plaque(s,base,ink,txt,x,y,z,w,h):
    box(s,base,(x,y,z),(w,.14,h),.045)
    sign(s,ink,txt,(x,y-.079,z),w*.89,h*.66)

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

def circle(x,y,z,r,n=48,phase=0):
    return [(x+r*math.cos(TAU*j/n+phase),y+r*math.sin(TAU*j/n+phase),z) for j in range(n)]

def run():
    scene=reset(); palette(); build(); finalize(scene)
    preview(scene, VIEW, (760,680)); palette_png(OUT/'preview.png')

SLUG = 'sgmy-building-dataran-bunga-kantan'
TITLE='Dataran Bunga Kantan | Torch Ginger Fountain'
ROLE='Municipal plaza landmark celebrating the torch ginger of local laksa gardens'
VIEW=(.58,-1,.49)

def build():
    court='Octagonal Plaza';pool='Tiled Fountain';stem='Cast Stems';bloom='Enamel Bracts';leafwork='Leaf Blades';bench='Seats and Lamps'
    basalt=material('Basalt pavers','534f50');pink=material('Kantan rose','d65a71',.4,.20); coral=material('Coral blush enamel','f29391',.4,.18); plum=material('Deep carmine enamel','a23951',.47,.22);cream=material('Petal tips','ffc1a5',.4,.21);green=material('Oxidised green bronze','488775',.42,.37);gold=material('Polished bronze rib','c79a58',.36,.52); water=material('Celadon water tile','569b99',.20,.32)
    lathe(court,rock,0,0,[(0,10.44),(.20,10.44),(.31,10.37)],8,math.pi/8,False)
    lathe(court,sand,0,0,[(.31,10.36),(.41,10.30)],8,math.pi/8,False)
    for r in (8.18,8.40,9.50):ring(court,basalt,circle(0,0,.41,r,8,math.pi/8),circle(0,0,.41,r-.075,8,math.pi/8),.016)
    lathe(pool,basalt,0,0,[(.41,6.99),(.55,6.99),(.60,6.83),(.81,6.83)],64)
    lathe(pool,water,0,0,[(.81,6.69),(.96,6.69)],64)
    ring(pool,teal,circle(0,0,.80,6.85,64),circle(0,0,.80,6.54,64),.32)
    ring(pool,ivory,circle(0,0,1.12,6.90,64),circle(0,0,1.12,6.49,64),.12)
    for r in (2.54,4.63,5.76):ring(pool,green,circle(0,0,.960,r,80),circle(0,0,.960,r-.067,80),.011)
    lathe(pool,teal,0,0,[(.96,2.20),(1.22,2.25),(1.32,1.97),(1.46,1.79)],40)
    def torch(x,y,z,scale,az):
        h=scale;dx=.28*h*math.cos(az);dy=.28*h*math.sin(az)
        tube(stem,green,(x,y,z),(x+dx*.52,y+dy*.52,z+2.56*h),.19*h,.16*h,n=24)
        tube(stem,green,(x+dx*.52,y+dy*.52,z+2.54*h),(x+dx,y+dy,z+4.50*h),.16*h,.26*h,n=24)
        xx,yy,zz=x+dx,y+dy,z+4.21*h
        lathe(bloom,plum,xx,yy,[(zz,.22*h),(zz+.64*h,.99*h),(zz+1.27*h,.71*h),(zz+1.85*h,.45*h),(zz+2.04*h,.09*h)],32)
        # Hollowed, spoon-shaped bracts: the rolled margin and axial keel catch separate highlights.
        for layer,(count,base,reach,rise) in enumerate(((11,0,1.84,.95),(10,.42,1.46,1.23),(9,.85,1.03,1.27),(8,1.27,.65,1.03))):
            for j in range(count):
                a=az+TAU*j/count+layer*.31;R=Vector((math.cos(a),math.sin(a),0));S=Vector((-math.sin(a),math.cos(a),0)); Z=Vector((0,0,1))
                vv=[];ff=[];mm=[]
                for t,sw in ((0,.035),(.18,.74),(.43,1),(.70,.85),(.87,.55),(1,.027)):
                    rr=.16+reach*(t**.74); ht=base+rise*(1.20*t-.30*math.sin(math.pi*t)); wid=reach*.32*sw
                    c=Vector((xx,yy,zz))+h*(R*rr+Z*ht)
                    for u in (-1,-.74,0,.74,1): vv.append(c+h*(S*(wid*u)-R*(.14*u*u*sw)+Z*(.15*u*u*sw)))
                for k in range(5):
                    for l in range(4):
                        i=k*5+l;ff.append((i,i+1,i+6,i+5));mm.append(cream if k==4 and layer>1 else (coral if l in (0,3) else [pink,plum,pink,coral][layer]))
                for m in dict.fromkeys(mm):
                    faces=[p for p,col in zip(ff,mm) if col==m]; ids=sorted({i for p in faces for i in p}); index={v:k for k,v in enumerate(ids)}
                    add(bloom,m,[vv[i] for i in ids],[[index[i] for i in p] for p in faces],True)
        for k in range(17):
            a=k*2.399; rr=.37*h*math.sqrt(k/17);foliage(bloom,gold,(xx+rr*math.cos(a),yy+rr*math.sin(a),zz+(2.16-.010*k)*h),(.115*h,.11*h,.19*h),7,a)
    torch(-.69,.27,1.45,1.59,2.3);torch(.94,-.54,1.45,.97,-.12)
    for j in range(9):
        a=.16+j*TAU/9;R=Vector((math.cos(a),math.sin(a),0));S=Vector((-math.sin(a),math.cos(a),0));length=2.90+.43*(j%4);height=2.14+.72*(j%3);v=[]
        for t in (0,.20,.39,.60,.83,.994):
            p=Vector((0,0,1.40))+R*(.59+t*length)+Vector((0,0,height*(t+.30*math.sin(math.pi*t))));wd=.52*math.sin(math.pi*(.02+.95*t))
            v += [p-S*wd,p+Vector((0,0,wd*.64)),p+S*wd]
        add(leafwork,green,v,[(3*k+i,3*k+i+1,3*k+i+4,3*k+i+3) for k in range(5) for i in (0,1)],True)
        for k in range(5):line(leafwork,gold,v[3*k+1],v[3*k+4],.050)
    for j in range(8):
        a=TAU*j/8; xx=8.21*math.cos(a);yy=8.21*math.sin(a)
        if j==6:continue
        for u in (-.84,.84):
            box(bench,basalt,(xx-u*math.sin(a),yy+u*math.cos(a),.67),(.61,.25,.50),.03,yaw=a)
        for u in (-.22,0,.22):box(bench,wood,(xx+u*math.cos(a),yy+u*math.sin(a),.99),(.16,2.51,.17),.03,yaw=a)
    block(bench,basalt,0,-8.49,.41,3.06,.61,1.13);plaque(bench,teal,ivory,'B U N G A   K A N T A N',0,-8.84,1.19,2.91,.49)

if __name__ == '__main__':
    run()
