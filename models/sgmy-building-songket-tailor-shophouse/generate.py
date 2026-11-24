"""Kedai Jahit Songket | gold-thread tailor shophouse.
Original static SG/MY streetscape exterior, procedurally modelled in metres.
Front: -Y. Base origin. Solid PBR palette, per-mesh UV0, no external inputs.
Rebuild: blender -b --python generate.py | Blender 5.2, GLB requires Draco.
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
    vs.extend(tuple(POSE @ Vector(v)) for v in verts)
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


def beam(section, mat, a, b, width, depth=None, bevel=0):
    a, b = Vector(a), Vector(b)
    axis = b - a
    basis = axis.to_track_quat('Z','Y').to_matrix()
    box(section, mat, (a+b)/2, (width, depth or width, axis.length), bevel, basis=basis)


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


def rod(section, mat, a, b, radius, n=10, taper=1):
    a, b = Vector(a), Vector(b)
    basis = (b-a).to_track_quat('Z','Y').to_matrix()
    verts = [p+basis @ Vector((rad*math.cos(TAU*j/n),rad*math.sin(TAU*j/n),0))
             for p,rad in ((a,radius),(b,radius*taper)) for j in range(n)]
    faces = [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
    faces.extend((tuple(reversed(range(n))),tuple(range(n,2*n))))
    add(section, mat, verts, faces, [True]*n+[False,False])


def sign(section, mat, text, pos, width, height):
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
    mesh.calc_loop_triangles()
    add(section, mat, [(x+u*s, y-q*s, z+v*s) for u,v,q in coords],
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
    root['origin_note'] = 'Local origin on ground at site centre'
    root['category'] = 'building'
    root['facing'] = 'Blender -Y / glTF +Z'
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
    cam.data.ortho_scale = 1.135 * max(max(xx)-min(xx),(max(yy)-min(yy))*aspect) / min(1.0, aspect)
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
    scene.cycles.samples = 14
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

from contextlib import contextmanager
import random

# A local frame lets the same joinery follow an angled or side elevation.
POSE = Matrix.Identity(4)
@contextmanager
def frame(x=0, y=0, angle=0, z=0):
    global POSE
    previous = POSE
    POSE = previous @ Matrix.Translation((x,y,z)) @ Matrix.Rotation(math.radians(angle),4,'Z')
    try:
        yield
    finally:
        POSE = previous

def palette(wall, accent, secondary, roof, wood):
    global WALL, ACC, SEC, ROOF, TIM, SNOW, DARK, GLASS, MOSS, LEAF, FERN, PAVE, METAL, TILE, SUN, EARTH
    WALL = material('Facade | body colour', wall)
    ACC = material('Facade | feature colour', accent)
    SEC = material('Facade | secondary colour', secondary)
    ROOF = material('Roof | weather face', roof)
    TIM = material('Carpentry | finished timber',wood)
    SNOW = material('Trim | rice porcelain','f3ebd4')
    DARK = material('Joinery | shadow bronze','303c3c')
    GLASS = [material('Glazing | '+n,c,.28,.19) for n,c in [('rain','3b5860'),('sky','769596'),('linen curtain','a2b1a5')]]
    MOSS = material('Garden | pandan shadow','3c634c')
    LEAF = material('Garden | palm green','638950')
    FERN = material('Garden | fresh shoot','9baf67')
    PAVE = material('Masonry | buff paving','b1a590')
    METAL = material('Metalwork | brushed pewter','697c7b',.42,.25)
    TILE = material('Ceramic | burnt sienna','b46b4c')
    SUN = material('Trim | gamboge','e8b05e')
    EARTH = material('Garden | potting mix','494335')

def B(part,mat,x,y,z,w,d,h,b=0):
    """Rectangle with its lower face at z."""
    box(part,mat,(x,y,z+h/2),(w,d,h),b)

def win(x,y,z,w,h,n=2,seed=0,trim=None):
    s='Casements and sills'; trim=trim or SNOW
    B(s,DARK,x,y-.036,z,w,.094,h,.012)
    pw=(w-.14)/n
    for j in range(n):
        xx=x-w/2+.07+pw*(j+.5)
        B(s,GLASS[(seed+2*j+(j//2))%3],xx,y-.09,z+.075,pw-.042,.038,h-.15)
    B(s,trim,x,y-.075,z-.07,w+.18,.25,.105,.014)
    B(s,trim,x,y-.07,z+h-.03,w+.10,.18,.08,.012)

def shutter(x,y,z,w,h,mat=None):
    s='Louvred shutters'; mat=mat or ACC
    B(s,DARK,x,y,z,w,.09,h)
    for j in range(11):
        B(s,mat,x,y-.075,z+.07+j*(h-.14)/11,w-.10,.10,(h-.14)/11*.68,.012)
    for dx in (-1,1): B(s,mat,x+dx*(w/2-.032),y-.07,z,.068,.14,h,.01)

def door(x,y,z,w=1.05,h=2.16,mat=None):
    s='Entrance joinery'; mat=mat or TIM
    B(s,DARK,x,y-.04,z,w+.13,.12,h+.08)
    for i in (-1,1):
        cx=x+i*w/4
        B(s,mat,cx,y-.12,z+.015,w/2-.022,.10,h-.02)
        for zz,hh in ((.14,h*.32),(h*.51,h*.40)):
            B(s,SEC,cx,y-.18,z+zz,w*.34,.04,hh,.015)
        B(s,SUN,x+i*.09,y-.235,z+.84,.032,.06,.21,.01)


def pandan(x,y,z,r,seed=1):
    # Each folded, pointed strap leaf has a raised midrib.
    rng=random.Random(seed); s='Pandan planting'
    for j in range(14):
        a=j*2.4+rng.uniform(-.18,.18); c=math.cos(a); t=math.sin(a)
        l=r*rng.uniform(.58,1.02); w=r*rng.uniform(.068,.135); h=r*rng.uniform(.6,1.25)
        verts=[(x,y,z),(x+c*l*.48-t*w,y+t*l*.48+c*w,z+h*.85),(x+c*l*.50,y+t*l*.50,z+h),(x+c*l*.48+t*w,y+t*l*.48-c*w,z+h*.85),(x+c*l,y+t*l,z+h*.72)]
        add(s,[MOSS,LEAF,FERN,LEAF][j%4],verts,[(0,1,2),(0,2,3),(1,4,2),(2,4,3)])


def hip(x,y,z,w,d,rise,cut,mat=None,metal=False):
    # Roof ridge runs east-west. Linear rows wrap consistently over all four planes.
    s='Roof covering'; mat=mat or ROOF
    ax,by=w/2,d/2; ridge=ax-cut
    corners=[(x-ax,y-by,z),(x+ax,y-by,z),(x+ax,y+by,z),(x-ax,y+by,z)]
    ends=[(x-ridge,y,z+rise),(x+ridge,y,z+rise)]
    add(s,mat,corners+ends,[(0,1,5,4),(1,2,5),(2,3,4,5),(3,0,4),(3,2,1,0)])
    for j in range(4): beam('Eave fascia',TIM,corners[j],corners[(j+1)%4],.14,.19)
    for i,k in ((0,0),(3,0),(1,1),(2,1)):
        if cut>.001: rod(s,mat,corners[i],ends[k],.084,8)
    rod(s,mat,ends[0],ends[1],.12,10)
    rows=max(5,round(math.hypot(by,rise)/.35))
    if not metal:
        for j in range(1,rows):
            f=j/rows; dx=ax-cut*f; dy=by*(1-f); zz=z+rise*f+.007
            for side in (-1,1):
                rod(s,mat,(x-dx,y+side*dy,zz),(x+dx,y+side*dy,zz),.028,6)
                if cut>.001: rod(s,mat,(x+side*dx,y-dy,zz),(x+side*dx,y+dy,zz),.024,6)
    # Raised roll tiles / standing seams; terminate each roll at its hip.
    for j in range(1,math.ceil(w/(.45 if metal else .50))):
        xx=-ax+j*w/math.ceil(w/(.45 if metal else .50)); f=min(1,(ax-abs(xx))/max(.001,cut))
        for side in (-1,1): rod(s,mat,(x+xx,y+side*by,z+.015),(x+xx,y+side*by*(1-f),z+rise*f+.015),.039 if not metal else .024,6)


def label(text,x,y,z,w,h,mat=None):
    sign('Cast lettering',mat or SNOW,text,(x,y,z),w,h)


def pot(x,y,z,r):
    lathe('Glazed planters',ACC,x,y,[(z,.60*r),(z+.12*r,.64*r),(z+.78*r,.95*r),(z+.83*r,r),(z+.93*r,r)],16)
    lathe('Glazed planters',EARTH,x,y,[(z+.933*r,r*.85),(z+.95*r,r*.85)],16)
    pandan(x,y,z+.95*r,r*1.65,round((abs(x)+abs(y))*11)+4)

def archpanel(s,mat,x,y,bottom,w,shoulder,depth):
    r=w/2
    poly=[(x-r,bottom),(x+r,bottom)]+[(x+r*math.cos(j*math.pi/20),shoulder+r*math.sin(j*math.pi/20)) for j in range(21)]
    prism(s,mat,poly,y-depth,y)


SLUG = 'sgmy-building-songket-tailor-shophouse'
TITLE = 'Kedai Jahit Songket | gold-thread tailor shophouse'
VIEW = (.61,-1.46,.65)
RESOLUTION = (1040,920)

def build():
    palette('e8cbbc','345d66','c68d53','984e3c','684335')
    plum=material('Silk | mulberry','925263'); mint=material('Silk | seafoam','81ab9c'); s='Party walls and airwell'; a='Pilasters and crown'; aw='Woven sunblind'; t='Cloth merchant display'
    B(s,PAVE,0,0,0,8.9,15.5,.16,.08)
    B(s,WALL,0,-2.35,.16,8.32,5.9,8.30); B(s,WALL,0,5.50,.16,8.32,3.9,6.80)
    B(s,WALL,0,-5.95,3.74,8.32,1.42,4.72)
    for x in (-4.05,4.05): B(s,WALL,x,2.075,.16,.22,2.95,6.78)
    B(s,TILE,0,2.05,.16,7.90,3.05,.10); pot(-1,2,.26,.51)
    hip(0,-3.04,8.44,8.28,6.91,1.60,0); hip(0,5.5,6.96,8.29,3.84,1.26,0)
    for x in (-3.95,0,3.95):
        B(a,ACC,x,-6.50,.16,.46,.48,3.64); B(a,SEC,x,-6.50,.16,.57,.58,.46,.02)
        B(a,SNOW,x,-6.50,3.25,.66,.65,.48,.025)
        B(a,SNOW,x,-6.69,3.8,.39,.24,4.85)
        for j in (-1,1): B(a,SEC,x+j*.115,-6.825,4.18,.046,.05,4.11)
        B(a,ACC,x,-6.68,8.50,.65,.38,.25,.035)
    for xx in (-1.97,1.97):
        for xx2 in (-.77,.77):
            x=xx+xx2
            archpanel(a,SEC,x,-6.68,4.60,1.52,6.94,.135)
            archpanel(a,SNOW,x,-6.82,4.72,1.32,6.92,.08)
            archpanel(a,GLASS[0],x,-6.905,4.77,1.10,6.91,.026)
            shutter(x,-6.95,4.84,1.02,2.01,ACC)
            for k in range(1,6):
                ang=k*math.pi/6
                beam(a,SEC,(x,-6.95,6.92),(x+.52*math.cos(ang),-6.95,6.92+.52*math.sin(ang)),.035)
            B(a,SNOW,x,-6.84,4.51,1.56,.38,.16,.025)
        B(a,plum,xx,-6.71,7.84,2.88,.12,.45,.045)
        for k in range(7):
            x=xx+(k-3)*.374
            box(a,SUN,(x,-6.79,8.066),(.205,.035,.205),basis=Matrix.Rotation(math.pi/4,3,'Y'))
    B(a,ACC,0,-6.68,3.65,8.48,.40,.41); B(a,SNOW,0,-6.72,4.02,8.65,.51,.16,.022)
    B(a,SNOW,0,-6.62,8.44,8.68,.48,.24,.025)
    poly=[(-4.15,8.63),(4.15,8.63),(4.15,8.99),(2.24,8.99),(1.96,9.33),(1.25,9.33),(.94,9.65),(-.94,9.65),(-1.25,9.33),(-1.96,9.33),(-2.24,8.99),(-4.15,8.99)]
    prism(a,WALL,poly,-6.74,-6.40)
    for i in range(2,len(poly)-1):
        (x,z),(u,v)=poly[i:i+2]; beam(a,SEC,(x,-6.63,z),(u,-6.63,v),.13,.37)
    label('1937',0,-6.76,9.10,1.38,.46,ACC)
    # Strip-by-strip canvas, with folded vertical valance.
    for j in range(16):
        x=(j-7.5)*.476; mat=ACC if j%2 else mint
        prism(aw,mat,[(-6.9,3.66),(-7.62,3.32),(-7.62,3.24),(-6.9,3.57)],x-.239,x+.239,'X')
        B(aw,mat,x,-7.6,3.06,.476,.05,.22,.02)
    door(-.92,-5.33,.16,1.22,2.43,ACC)
    for x,w in ((-2.84,1.89),(1.88,3.17)): win(x,-5.32,.73,w,1.81,3,2,ACC)
    B(t,TIM,0,-5.39,2.77,7.65,.17,.65,.025); label('KEDAI JAHIT   •   SONGKET',0,-6.895,3.86,6.22,.28,SNOW)
    for j in range(9):
        x=.54+j*.324; h=1.06+(j%3)*.105
        lathe(t,[mint,plum,SEC,ACC][j%4],x,-5.95,[(.35,.15),(.35+h,.15)],12)
        for zz in (.46,.59): lathe(t,SUN,x,-5.95,[(zz,.154),(zz+.04,.154)],12)
    B(t,TIM,1.84,-5.95,.16,3.11,.57,.21,.025)
    for side in (-1,1):
        with frame(side*4.16,0,side*90):
            for j in (-4.4,-2.25,-.3,4.58,6.38):
                win(j*side,0,4.82,1.05,1.49,2,1); shutter(j*side,-.15,4.88,.89,1.32,ACC)
    with frame(0,7.46,180):
        door(2,0,.16); win(-1.1,0,1.02,2.1,1.39); win(0,0,4.54,3.65,1.45,4)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
