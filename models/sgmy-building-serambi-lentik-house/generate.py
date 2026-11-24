"""Serambi Lentik | Negeri Sembilan upswept-roof house.
Original, deterministic exterior; no external inputs. Static scenery, metres, front -Y,
origin at ground level. Built-in font and solid PBR finishes, UV0 per mesh.
Rebuild both derivatives with: blender -b --python generate.py (Blender 5.2).
The glTF delivery requires a Draco decoder.
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


def rod(section, mat, a, b, radius, n=10, taper=1):
    a, b = Vector(a), Vector(b)
    basis = (b-a).to_track_quat('Z','Y').to_matrix()
    verts = [p+basis @ Vector((rad*math.cos(TAU*j/n),rad*math.sin(TAU*j/n),0))
             for p,rad in ((a,radius),(b,radius*taper)) for j in range(n)]
    faces = [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
    faces.extend((tuple(reversed(range(n))),tuple(range(n,2*n))))
    add(section, mat, verts, faces, [True]*n+[False,False])


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
    cam.data.ortho_scale = 1.135 * max(max(xx)-min(xx),(max(yy)-min(yy))*aspect)
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

def bed(x,y,w,d,z=.10):
    B('Garden beds',PAVE,x,y,z,w,d,.34,.047)
    B('Garden beds',EARTH,x,y,z+.33,w-.16,d-.16,.035)

def pandan(x,y,z,r,seed=1):
    # Each folded, pointed strap leaf has a raised midrib.
    rng=random.Random(seed); s='Pandan planting'
    for j in range(14):
        a=j*2.4+rng.uniform(-.18,.18); c=math.cos(a); t=math.sin(a)
        l=r*rng.uniform(.58,1.02); w=r*rng.uniform(.068,.135); h=r*rng.uniform(.6,1.25)
        verts=[(x,y,z),(x+c*l*.48-t*w,y+t*l*.48+c*w,z+h*.85),(x+c*l*.50,y+t*l*.50,z+h),(x+c*l*.48+t*w,y+t*l*.48-c*w,z+h*.85),(x+c*l,y+t*l,z+h*.72)]
        add(s,[MOSS,LEAF,FERN,LEAF][j%4],verts,[(0,1,2),(0,2,3),(1,4,2),(2,4,3)])


def lattice(x,y,z,w,h,mat):
    # Diamond-shaped ventilation lights formed by intersecting diagonal strips.
    step=.36
    for sign_ in (-1,1):
        for j in range(-math.ceil(h/step)-1,math.ceil((w+h)/step)+1):
            q=j*step; lo=max(0,-q) if sign_==1 else max(0,q-w); hi=min(h,w-q) if sign_==1 else min(h,q)
            if hi-lo>.035: beam('Ventilation lattice',mat,(x-w/2+q+sign_*lo,y,z+lo),(x-w/2+q+sign_*hi,y,z+hi),.042,.046)


SLUG = 'sgmy-building-serambi-lentik-house'
TITLE = 'Serambi Lentik | Negeri Sembilan upswept-roof house'
VIEW = (.99,-1.53,.64)

def build():
    palette('a26643','934a38','c59c64','49494a','614338'); s='Hardwood frame'; g='Woven gable ends'; r='Swept roof and ridge'; t='Shaded serambi'
    B(s,PAVE,0,-.43,0,14.9,11.12,.13,.06)
    for xx in (-5.95,-4,-2,0,2,4,5.95):
        for yy in (-3.20,-1.18,2.80):
            B(s,SEC,xx,yy,.13,.35,.38,.37,.04); B(s,TIM,xx,yy,.5,.22,.24,.66)
    B(s,TIM,0,-.19,1.14,12.43,6.62,.28,.034); B(s,WALL,0,.86,1.42,12.01,4.81,3.03)
    for xx in range(-5,6,2):
        if xx==-1: door(xx,-1.55,1.42,1.30,2.25); continue
        win(xx,-1.55,2.04,1.27,1.52,2,xx,TIM); shutter(xx,-1.65,2.10,.91,1.38,ACC)
    with frame(0,3.265,180):
        for xx in (-4.80,-2.43,0,2.43,4.80): win(xx,0,2.07,1.32,1.46,2,2,TIM)
    for side in (-1,1):
        with frame(side*6.005,.85,side*90):
            for xx in (-1.14,1.14): win(xx,0,2.08,1.19,1.50,3,1,TIM)
    # One roof profile sampled at several stations. Eaves remain shaded and low;
    # the ridge and the rake flare progressively at the gable ends.
    def pt(a,f,side):
        # a runs along the ridge, f runs from eave (0) to ridge (1).
        return (a*(6.56+1.03*f),.65+side*(3.44*(1-f)),4.47+.12*abs(a)**4+(2.20+2.13*abs(a)**4)*f**1.22)
    def offset(v,dz): return (v[0],v[1],v[2]+dz)
    for side in (-1,1):
        nx,ny=32,10
        vs=[pt(i*2/nx-1,j/ny,side) for i in range(nx+1) for j in range(ny+1)]
        faces=[]
        for i in range(nx):
            for j in range(ny):
                k=i*(ny+1)+j; faces.extend(((k,k+ny+1,k+ny+2),(k,k+ny+2,k+1)))
        add(r,ROOF,vs,faces)
        for j in range(1,10):
            for i in range(20): rod(r,ROOF,pt(i*.10-1,j*.1,side),pt((i+1)*.10-1,j*.1,side),.033,6)
        for j in range(11):
            a=j*.20-1
            for k in range(5): rod(r,ROOF,pt(a,k*.20,side),pt(a,(k+1)*.20,side),.035,6)
        for end in (-1,1):
            for k in range(10):
                v1=pt(end,k*.10,side); v2=pt(end,(k+1)*.10,side)
                beam(g,SEC,v1,v2,.15,.16)
                beam(g,ACC,offset(v1,-.11),offset(v2,-.11),.095,.12)
                # Triangular woven gable follows the swept canopy edge rather than a flat cap.
                a=pt(end*.987,k*.10,side); b=pt(end*.987,(k+1)*.10,side)
                add(g,SEC,[(a[0],a[1],4.42),(b[0],b[1],4.42),b,a],[(0,1,2,3)])
                for m in range(1,8):
                    zz=4.42+m*.44; height=min(a[2],b[2])-zz
                    if height>.21:
                        ax,ay=a[:2]; bx,by=b[:2]; xx=(ax+bx)/2+end*.013; yy=(ay+by)/2
                        add(g,ACC if m%2 else TIM,[(xx,yy,zz-.15),(bx+end*.015,by,zz),(xx,yy,zz+.15),(ax+end*.015,ay,zz)],[(0,1,2,3)])
        beam(g,TIM,pt(-1,0,side),pt(1,0,side),.13,.16)
    for i in range(32): rod(r,TIM,pt(i/16-1,1,1),pt((i+1)/16-1,1,1),.09,8)
    # Low lean-to roof is structurally separate from the ceremonial main roof.
    prism(t,ROOF,[(-3.98,3.58),(-1.05,4.73),(-1.05,4.87),(-3.98,3.71)],-6.43,6.43,'X')
    for j in range(36):
        xx=(j-17.5)*.352; rod(t,ROOF,(xx,-3.98,3.72),(xx,-1.05,4.88),.031,6)
    for xx in (-6,-4,-2,0,2,4,6):
        B(t,TIM,xx,-3.27,1.42,.16,.18,2.46)
        for dx in (-.43,.43): beam(t,SEC,(xx,-3.27,3.27),(xx+dx,-3.27,3.78),.085)
    for xx in (-5,-3,1,3,5):
        B(t,SEC,xx,-3.30,1.45,1.90,.10,.18)
        lattice(xx,-3.3,1.62,1.84,.56,TIM); B(t,SEC,xx,-3.30,2.18,1.94,.15,.09,.016)
    for j in range(7):
        B(t,WALL,-1,-5.13+j*.25,.24+j*.18,1.69,.31,.10,.015)
    for xx in (-1.78,-.22): beam(t,TIM,(xx,-5.28,.13),(xx,-3.45,1.39),.14,.18)
    for xx in (-4.6,3.89):
        bed(xx,-4.39,2.6,1.12,.13)
        for k in (-1,0,1): pandan(xx+k*.78,-4.39,.49,.60,8+k)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, (1040, 920))
