"""Tepung Sagu • Mukah Starch Works | Original static SG/MY game architecture.
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

SLUG='sgmy-building-mukah-sago-works'
TITLE='Tepung Sagu • Mukah Starch Works'
ROLE='Sarawak sago-processing works with log infeed, inclined conveyor and cyclone separators'
VIEW=(.63,-1,.56)

def build():
    s='Mill House'; c='Cyclone Gantry'; r='Rasping Conveyor'; cream=material('Ivory zinc','d9d5b8',.54,.22); green=material('River green','497067'); red=material('Red lead primer','a84934'); bark=material('Sago bark','705442'); fresh=material('Pale pith','d8b482')
    pad(s,0,0,27,18.9,sand,rock)
    block(s,green,-5.75,1.44,.3,10.1,11.70,5.49); gable(s,cream,-5.75,1.44,11.26,12.83,5.77,8.57,steel,18)
    for side in (-1,1):
        yy=1.44+side*5.87
        tri=[(-10.78,yy,5.74),(-.72,yy,5.74),(-5.75,yy,8.18)]
        loft(s,green,[tri,[(a,b+side*.09,d) for a,b,d in tri]])
    for x in (-8.98,-2.66): window(s,cream,glass,x,-4.49,3.13,2.81,1.92,bays=3)
    shutter(s,-5.81,-4.51,.31,2.62,3.54); plaque(s,cream,green,'T E P U N G   S A G U',-5.75,-4.60,5.21,9,.78)
    for j in range(4): window(s,cream,glass,-.66,-2.74+j*2.74,3.47,2.19,1.87,math.pi/2,2)
    # Twin tapered separators above an open bagging platform, with return duct loop.
    for x in (2.9,8.0):
        for u in (-1.86,1.86):
            for v in (-1.63,1.63): block(c,red,x+u,2.81+v,.30,.21,.21,6.55)
        for y in (1.18,4.44):
            line(c,red,(x-1.86,y,.48),(x+1.86,y,5.27),.14); line(c,red,(x+1.86,y,.48),(x-1.86,y,5.27),.14)
        lathe(c,steel,x,2.81,[(3.05,.31),(3.29,.36),(6.64,1.62),(10.18,1.62),(10.78,.88)],32)
        for z in (6.72,8.36,10.06): lathe(c,cream,x,2.81,[(z,1.67),(z+.12,1.67)],32)
        lathe(c,red,x,2.81,[(2.87,.41),(3.17,.41)],16); beam(c,ivory,(x,2.81,10.57),(x,2.81,11.64),.48,20)
        beam(c,ivory,(x,2.81,11.64),(x,6.6,11.64),.48,20); beam(c,ivory,(x,6.6,11.64),(x,6.6,1.7),.48,20)
    block(c,steel,5.45,2.81,6.46,9.99,4.99,.19); balustrade(c,ochre,(.5,.41,6.65),(10.4,.41,6.65),1,12)
    balustrade(c,ochre,(10.4,.41,6.65),(10.4,5.22,6.65),1,6)
    for x in (1.48,2.19): beam(c,red,(x,.27,.31),(x,.27,7.69),.065)
    for j in range(22): beam(c,steel,(1.48,.25,.62+j*.32),(2.19,.25,.62+j*.32),.041)
    # Infeed slopes from the log deck to the side of the mill.
    for y in (-3.96,-2.34):
        line(r,red,(10.4,y,1.18),(-.82,y,4.8),.20); line(r,green,(10.4,y,2.03),(-.82,y,5.65),.14)
        for j in range(10):
            x=10.4-1.122*j; z=1.18+.362*j; line(r,red,(x,y,z),(x-1.12,y,z+1.21),.09)
    skin(r,shadow,[(10.4,-3.96,1.41),(-.82,-3.96,5.03),(-.82,-2.34,5.03),(10.4,-2.34,1.41)],.12)
    for j in range(16):
        x=10.3-.68*j; z=1.48+.22*j; beam(r,steel,(x,-3.98,z),(x,-2.32,z),.066)
    for x in (2.2,6.1,10.1): columns(r,green,[x],[-3.92,-2.37],.31,1.18+(10.4-x)*.322-.30,.15)
    for i in range(10):
        x=2.46+i*.95; y=-6.23+.14*math.sin(i*8); beam(r,bark,(x,y-1.35,.73),(x,y+1.35,.73),.42); beam(r,fresh,(x,y-1.38,.73),(x,y-1.35,.73),.36)
        for v in (-.61,.69): beam(r,wood,(x,y+v-.05,.73),(x,y+v+.05,.73),.43)


if __name__ == "__main__":
    scene = reset()
    palette()
    build()
    finalize(scene)
    preview(scene, VIEW, (880, 740))
