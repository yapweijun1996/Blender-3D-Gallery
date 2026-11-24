"""Menara Serunai | Reed Courts Office Tower — original SG/MY streetscape model.
Rebuild: blender -b --python-exit-code 1 --python generate.py
Metres; centre-base origin; street front -Y. Static, baked transforms and UV0.
Draco decoder required. No third-party geometry or texture inputs.
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

SLUG='sgmy-building-menara-serunai-offices'
TITLE='Menara Serunai | Reed Courts Office Tower'
ROLE='Malaysian commercial tower with five graduated sun-screened office bays'
VIEW=(.58,-1,.36)

def build():
    b='Arcaded Banking Podium'; t='Reed Office Bays'; f='Copper Sun Blades'; c='Open Diadems'; a='Public Forecourt'
    blue=material('Deep lagoon facade','376878',.25,.38); sea=material('Sea blue facade','427c83',.24,.32); ivory2=material('Shell precast','ead9b9'); orange=material('Anodised cinnamon','b57751',.36,.44); gold=material('Champagne anodised edge','d9b378',.37,.38); dark=material('Graphite spandrel','354e59',.44,.22)
    pad(a,0,0,33.8,25.40,sand,rock)
    rounded(b,rock,0,1.13,29.2,18.4,.30,.75,1.25);rounded(b,glass,0,1.34,26.93,15.64,.75,4.53,1.16)
    rounded(b,ivory2,0,1.0,29.2,18.7,4.50,4.99,1.16);rounded(b,orange,0,1.0,29.03,18.52,4.99,5.19,1.09)
    rounded(b,glass,0,1.0,27.7,17.15,5.18,7.27,.96);rounded(b,ivory2,0,1.0,29.05,18.38,7.25,7.82,1.15)
    rounded(b,dark,0,1.0,28.5,17.85,7.81,7.93,1.11)
    for x in (-12.4,-8.3,-4.15,0,4.15,8.3,12.4):
        for y in (-7.53,9.54):
            block(b,ivory2,x,y,.75,.44,.57,3.75)
        for y in (-7.63,9.63):block(b,gold,x,y,5.19,.18,.21,2.05)
    steps(a,sand,ivory,0,-9.97,6.24,3,.43,.15,.30)
    plaque(b,dark,ivory,'M E N A R A   S E R U N A I',0,-8.37,4.78,12.45,.85)
    for x in (-10.26,10.26):shrub_row(a,ivory2,shadow,[leaf,sage],x,-9.86,.30,4.86,1.0)
    # A recessed spine links the reeds. Slit loggias separate their projecting noses.
    for j,levels in enumerate((16,15,13,11,8)):
        x=-9.64+4.82*j; cy=1.04+(j%2)*.40; w=4.44; depth=14.20-abs(j-2)*1.16; z=7.93; pitch=3.23; top=z+levels*pitch
        if j: block(t,dark,x-2.41,cy,z,.46,6.49,top-z-1)
        def loop(level,extra=0):return round_ring(x,cy,level,w+extra,depth+extra,1.82+extra/2,4)
        loft(t,(blue,sea)[j%2],[loop(z),loop(top)])
        for i in range(1,levels+1):
            h=z+i*pitch
            loft(t,dark,[loop(h-.64,.068),loop(h-.12,.068)])
            loft(t,ivory2,[loop(h-.20,.29),loop(h+.06,.29)])
        for side in (-1,1):
            yy=cy+side*(depth/2+.09)
            for dx in (-1.06,0,1.06):block(f,orange,x+dx,yy,z,.18,.48,top-z+1.23,.045)
            xx=x+side*(w/2+.046)
            for dy in (-3.12,-1.02,1.02,3.12):block(f,gold,xx,cy+dy,z,.16,.12,top-z)
        # An open bias-cut crown, rather than a sloping lid. The planted upper terraces remain visible.
        outer=loop(top,.23);inner=loop(top,-.28)
        def height(v):return 1.00+(v[1]-cy+depth/2)*.27+(v[0]-x)*-.145
        def upper(ring0,off):return [(u,v,h+height((u,v))+off) for u,v,h in ring0]
        ro,ri=upper(outer,0),upper(inner,0)
        for i in range(len(ro)):
            jj=(i+1)%len(ro)
            skin(c,gold,[ro[i],ro[jj],ri[jj],ri[i]],.38)
            if i%2==0:line(c,orange,outer[i],ro[i],.19)
        for dy in (-2.31,2.31):
            xx=x-.7
            block(c,sand,xx,cy+dy,top+.061,1.88,2.94,.45)
            for q in (-.81,0,.81):foliage(c,sage if q else leaf,(xx,cy+dy+q,top+.72),(.68,.64,.58),8,j+q)
    for side in (-1,1):
        x=side*13.03
        for y in (-4.67,-.47,3.73,7.93):foliage(b,leaf,(x,y,8.30),(.85,1.15,.69),9,y)


if __name__ == '__main__':
    scene = reset()
    palette()
    build()
    finalize(scene)
    preview(scene, VIEW, (768, 660))
