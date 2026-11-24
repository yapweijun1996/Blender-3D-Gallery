"""Balai Derma Darah | Original static SG/MY street architecture.
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

def relief(s,m,x,y,z,points,depth=.10):
    prism(s,m,[(x+u,z+v) for u,v in points],y-depth/2,y+depth/2)

def service_door(s,x,y,z,w,h):
    block(s,shadow,x,y,z,w+.23,.14,h+.14);block(s,wood,x,y-.12,z+.05,w,.13,h-.04)
    for side in (-1,1):
        window(s,shadow,glass,x+side*w*.235,y-.23,z+h*.67,w*.40,h*.43,bays=1)
        block(s,brass,x+side*.12,y-.24,z+h*.35,.042,.105,.32,.01)

def run():
    scene=reset(); palette(); build(); finalize(scene)
    preview(scene, VIEW, (760,680)); palette_png(OUT/'preview.png')

SLUG = 'sgmy-building-balai-derma-darah'
TITLE='Balai Derma Darah | District Blood Centre'
ROLE='Tropical public blood donation centre with shaded circular donor lounge'
VIEW=(.49,-1,.47)

def build():
    wing='Laboratory Wing'; lounge='Donor Lounge'; porch='Registration Porch'; roof='Roof Plant'; street='Arrival Court'
    berry=material('Mulberry enamel','97434c',.43); pink=material('Clay rose ceramic','d88278'); milk=material('Milk ceramic cladding','efeadd'); aqua=material('Lagoon glazing','4b8b95',.21,.33);blue=material('Night teal alloy','2d5760',.45,.27)
    pad(street,0,0,24,16.8,sand,rock)
    rounded(wing,milk,-2.14,1.75,17.54,10.03,.30,.84,.67)
    rounded(wing,milk,-2.14,1.75,16.96,9.61,.84,7.87,.63)
    for side in (-1,1):
        for j in range(3):
            for z in (2.38,5.64):window(wing,blue,aqua,-2.14+side*8.51,-1.33+j*3.00,z,2.32,1.67,side*math.pi/2,2)
    for yy,k in ((-3.08,0),(6.59,math.pi)):
        for j in range(6):
            x=-8.98+j*2.74
            for z in (2.42,5.82):window(wing,blue,aqua,x,yy,z,2.53,2.28,k,2)
    for z in (3.94,7.70):rounded(wing,milk,-2.14,1.75,18.03,10.49,z,z+.29,.83)
    # Projecting terracotta baguettes cast diagonal shade over the upstairs strip windows.
    for j in range(27):
        x=-10.18+j*.588;box(wing,pink,(x,-3.58,5.97),(.13,.84,3.46),.03,yaw=.40)
    for z in (4.29,7.58):block(wing,berry,-2.55,-3.64,z,15.85,.48,.14)
    for j in range(3):
        xx=-5.61+j*2.17;block(roof,blue,xx,3.79,8.0,1.85,2.26,.78)
        lathe(roof,steel,xx,3.8,[(8.78,.72),(8.86,.73)],20);lathe(roof,shadow,xx,3.8,[(8.86,.57),(8.90,.57)],20)
        for k in range(5):line(roof,steel,(xx-.38,3.48+.15*k,8.916),(xx+.38,3.48+.15*k,8.916),.048)
    cx,cy=6.11,1.34
    lathe(lounge,milk,cx,cy,[(.30,4.64),(.62,4.66),(.81,4.42)],64)
    lathe(lounge,aqua,cx,cy,[(.81,4.28),(6.02,4.28)],64)
    for j in range(40):
        a=TAU*j/40; pos=(cx+4.33*math.cos(a),cy+4.33*math.sin(a),3.43)
        box(lounge,milk,pos,(.38,.12,5.24),.02,yaw=a+.23)
    for z in (1.31,3.79,5.76):lathe(lounge,blue,cx,cy,[(z,4.44),(z+.12,4.44)],64)
    lathe(lounge,berry,cx,cy,[(5.95,4.73),(6.10,4.86),(6.28,4.86)],64);lathe(lounge,milk,cx,cy,[(6.28,4.87),(6.45,4.87),(6.47,4.68)],64)
    lathe(lounge,aqua,cx,cy,[(6.41,3.33),(7.16,2.80)],48);lathe(lounge,milk,cx,cy,[(7.14,2.87),(7.28,2.86)],48)
    # High-contrast wayfinding blade with a shaped blood-drop relief.
    rounded(porch,berry,2.52,-3.07,2.07,1.73,.30,9.26,.36)
    drop=[(0,1.04),(.27,.54),(.56,.08),(.62,-.19),(.56,-.46),(.39,-.66),(.12,-.78),(-.18,-.76),(-.46,-.63),(-.63,-.33),(-.61,-.03),(-.42,.31)]
    relief(porch,milk,2.52,-3.98,8.05,drop,.09)
    rounded(porch,milk,-2.31,-4.98,7.92,3.97,3.44,3.81,.81);rounded(porch,berry,-2.31,-4.98,7.82,3.87,3.32,3.44,.78)
    for dx in (-3.17,3.17):lathe(porch,blue,-2.31+dx,-6.41,[(.30,.14),(3.34,.14)],16)
    plaque(porch,blue,ivory,'D E R M A   D A R A H',-2.31,-6.99,3.59,6.41,.61)
    service_door(porch,-2.32,-3.30,.83,2.44,2.47)
    steps(street,rock,milk,-2.31,-5.84,3.90,3,.51,.17,.30)
    for xx in (-8.06,6.35):shrub_row(street,milk,shadow,[leaf,sage],xx,-5.89,.30,4.05,.94)
    for xx in (-5.59,.92):
        lathe(street,steel,xx,-7.36,[(.30,.14),(.40,.17),(1.10,.14),(1.16,.10)],16)
    # Slender vertical ribs mark the blank service end without adding another facade material.
    for j in range(7):block(wing,pink,-10.49,.01+j*.43,6.89,.22,.10,.81)

if __name__ == '__main__':
    run()
