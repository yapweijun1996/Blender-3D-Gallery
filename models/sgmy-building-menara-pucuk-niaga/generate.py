"""Menara Pucuk • Sprout Office Tower | Original static SG/MY game architecture.
Rebuild: blender -b --python-exit-code 1 --python generate.py
Metres, centre-base origin, -Y street face. UV0, procedural palette, no external inputs.
GLB requires a Draco decoder. Studio camera, floor and lights are render-only.
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

def lathe(s,m,x,y,profile,n=32,phase=0,smooth=False):
    loft(s,m,[[(x+r*math.cos(a),y+r*math.sin(a),z) for a in [phase+TAU*i/n for i in range(n)]] for z,r in profile],smooth)

def beam(s,m,a,b,r,n=12):
    a,b=Vector(a),Vector(b)
    basis=(b-a).to_track_quat('Z','Y').to_matrix()
    loft(s,m,[[p+basis@Vector((r*math.cos(TAU*i/n),r*math.sin(TAU*i/n),0)) for i in range(n)] for p in (a,b)])

def gable(s,m,x,y,w,d,low,high,metal,ribs=12):
    for k in (-1,1):
        q=[(x+k*w/2,y-d/2,low),(x,y-d/2,high),(x,y+d/2,high),(x+k*w/2,y+d/2,low)]
        skin(s,m,q,.16)
        for j in range(ribs+1):
            v=y+(j/ribs-.5)*d
            line(s,metal,(x+k*w/2,v,low+.03),(x,v,high+.03),.055)
    beam(s,metal,(x,y-d/2,high),(x,y+d/2,high),.09)

def balustrade(s,m,a,b,h,n):
    for i in range(n+1):
        p=Vector(a).lerp(Vector(b),i/n); line(s,m,p,p+Vector((0,0,h)),.075)
    for z in (h*.46,h): line(s,m,Vector(a)+Vector((0,0,z)),Vector(b)+Vector((0,0,z)),.083)

def shutter(s,x,y,z,w,h):
    block(s,shadow,x,y,z,w,.20,h); block(s,steel,x,y-.12,z+.08,w-.20,.09,h-.16)
    for i in range(1,round(h/.22)): block(s,shadow,x,y-.175,z+i*.22,w-.20,.032,.033,0)

def columns(s,m,xs,ys,z,h,t):
    for x in xs:
        for y in ys: block(s,m,x,y,z,t,t,h)

def hip(s,m,x,y,w,d,z,w2,d2,z2):
    def rect(w,d,z): return [(x+i*w/2,y+j*d/2,z) for i,j in ((-1,-1),(1,-1),(1,1),(-1,1))]
    loft(s,m,[rect(w,d,z-.17),rect(w,d,z),rect(w2,d2,z2)])

def fins(s,m,x,y,z,w,h,count):
    for j in range(count): block(s,m,x,y,z+j*h/count,w,.26,.105,.014)

SLUG='sgmy-building-menara-pucuk-niaga'
TITLE='Menara Pucuk • Sprout Office Tower'
ROLE='Singapore tropical office high-rise with two leaf-shaped office plates and elevated shade gardens'
VIEW=(.66,-1,.39)

def build():
    s='Street Podium'; tower='Twin Leaf Offices'; veil='Solar Fins'; gardens='Garden Floors'; top='Lantern Crowns'
    deep=material('Petrol spandrel','244b53',.36,.29); blue=material('Lagoon curtain glass','57858c',.21,.44); jade=material('Jade curtain glass','467a72',.23,.42); bronze=material('Warm anodised bronze','c0a16e',.41,.42); pearl=material('Pale limestone','e1d6bd'); moss=material('Fern crowns','648555')
    pad(s,0,0,43,34,sand,rock)
    rounded(s,pearl,0,1,35,24,.30,1.0,4.6); rounded(s,glass,0,1,33.5,22.5,.98,6.22,4.2)
    for j in range(13): block(s,bronze,-12.6+j*2.1,-10.27,1,.14,.27,5.20)
    for k in (-1,1):
        columns(s,pearl,[k*15.76],[-7.49,-3.26,1.01,5.28,9.56],1,5.53,.46)
        leafbed(s,k*14.54,-12.60,5.95,1.29)
    for i in range(3): rounded(s,(bronze,pearl,pearl)[i],0,1,37.4-.57*i,26.4-.57*i,6.20+i*.42,6.48+i*.42,4.9)
    rounded(s,teal,0,1,35.8,24.8,7.02,7.48,4.31)
    steps(s,pearl,brass,0,-12.89,10.3,4,.41,.175,.30)
    plaque(s,deep,pearl,'M E N A R A   P U C U K',0,-12.31,6.16,14.73,1.25)
    # Two complementary lancet leaves flank the central services spine. Each mechanical
    # garden level recesses behind the vertical fins; the top floors turn into sloped lanterns.
    rounded(tower,deep,0,1.08,7.76,13.8,7.48,63.85,1.8)
    for floor in range(15):
        z=8.45+3.67*floor
        block(tower,bronze,0,-5.86,z,7.37,.15,.16);block(tower,bronze,0,8.05,z,7.37,.15,.16)
    for k,floors,mat in ((-1,21,jade),(1,16,blue)):
        params=[(side,idx/12) for side,indices in ((1,range(13)),(-1,range(11,0,-1))) for idx in indices]
        def leafpt(side,t,z,scale=1):
            height=(z-7.48)/(floors*3.65); taper=1-.15*height**2
            x=(2*t-1)*7.50; y=side*6.39*math.sin(math.pi*t)**.81
            rot=k*.60; return (k*(6.97+.98*height)+scale*taper*(x*math.cos(rot)-y*math.sin(rot)),1+k*(-1.05)+scale*taper*(x*math.sin(rot)+y*math.cos(rot)),z)
        def wrap(z,scale=1): return [leafpt(side,t,z,scale) for side,t in params]
        for i in range(floors):
            z=7.48+3.65*i; sky=(i in (6,12,18)); sc=.81 if sky else 1
            loft(tower,deep if sky else mat,[wrap(z,sc),wrap(z+3.64,sc)])
            loft(tower,pearl if sky else deep,[wrap(z,1.05),wrap(z+.39,1.05)])
            loft(tower,bronze if i%3==0 else steel,[wrap(z+.37,1.052),wrap(z+.47,1.052)])
            if sky:
                for side in (-1,1):
                    for j in range(8):
                        xx,yy,_=leafpt(side,(j+1)/9,z+.48,.93)
                        foliage(gardens,moss if j%2 else leaf,(xx,yy,z+.98),(.76,.71,.54),7,j*.18)
        z=7.48+floors*3.65
        end=[(xx,yy,zz+1.55+7.08*(t if k==1 else 1-t)) for (xx,yy,zz),(side,t) in zip(wrap(z),params)]
        loft(top,mat,[wrap(z),end]); skin(top,deep,[(x,y,zz+.12) for x,y,zz in end],.13)
        for j,(side,t) in enumerate(params):
            start=leafpt(side,t,7.48,1.027); mid=leafpt(side,t,7.48+floors*1.83,1.027); ee=leafpt(side,t,z,1.027); ee=(ee[0],ee[1],end[j][2]+.17)
            line(veil,bronze if j%3==0 else pearl,start,mid,.28 if j%3==0 else .15)
            line(veil,bronze if j%3==0 else pearl,mid,ee,.28 if j%3==0 else .15)
            line(top,bronze,end[j],end[(j+1)%len(end)],.22)
    for x in (-13.3,13.3): shrub_row(gardens,pearl,shadow,[moss,sage],x,-7.02,7.48,4.51,1.05)


if __name__ == "__main__":
    scene = reset()
    palette()
    build()
    finalize(scene)
    preview(scene, VIEW, (880, 740))
