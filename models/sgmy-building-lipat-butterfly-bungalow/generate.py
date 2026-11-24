"""Rumah Lipat | Malayan modern butterfly-roof bungalow.
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


def staircase(x,y,z,w,n,run,rise,mat=None):
    # y is the uppermost riser's centre, lower steps extend towards the street.
    for i in range(n):
        yy=y-(n-1-i)*run
        B('Entrance stair',mat or PAVE,x,yy,z,w,run+.015,rise*(i+1),.012)
        B('Entrance stair',SNOW,x,yy-.025,z+rise*(i+1)-.035,w+.04,run+.045,.038,.008)


def label(text,x,y,z,w,h,mat=None):
    sign('Cast lettering',mat or SNOW,text,(x,y,z),w,h)


def bandwin(x,y,z,w,h,n,seed):
    s='Aluminium ribbon casements'; B(s,DARK,x,y-.024,z,w,.08,h)
    gap=.074; pw=(w-gap)/n
    for i in range(n):
        xx=x-w/2+gap/2+(i+.5)*pw
        B(s,GLASS[(seed+i//2+(i%2)*2)%3],xx,y-.071,z+.074,pw-gap,.026,h-.148)
    B(s,SNOW,x,y-.115,z-.095,w+.19,.285,.095)


def roofseam(s,mat,x0,z0,x1,z1,y0,y1,thickness,spacing):
    # Folded sheet surface with raised standing seams along its fall.
    prism(s,mat,[(x0,z0-thickness),(x1,z1-thickness),(x1,z1),(x0,z0)],y0,y1)
    n=math.ceil((y1-y0)/spacing)
    for j in range(n+1):
        y=y0+(y1-y0)*j/n
        beam(s,mat,(x0,y,z0+.018),(x1,y,z1+.018),.045,.052)
    for y in (y0,y1): beam(s,SNOW,(x0,y,z0-.08),(x1,y,z1-.08),.14,.195)

SLUG = 'sgmy-building-lipat-butterfly-bungalow'
TITLE = 'Rumah Lipat | Malayan modern butterfly-roof bungalow'
VIEW = (.79,-1.55,.65)
RESOLUTION = (1040,920)

def build():
    palette('efe4ce','40766e','b98a58','548985','705340')
    s='Split-level villa'; r='Folded copper roof'; c='Car porch'; f='Cast circle screen'; q='Flagstone pier'; g='Forecourt'
    gray=material('Flagstone | slate brown','7f7466'); gold=material('Flagstone | sand','b49b7b'); umber=material('Flagstone | umber','8d7967')
    B(g,PAVE,0,0,0,18.25,14.6,.14,.12); B(g,MOSS,-5.0,-3.75,.14,7.8,6.3,.06,.04)
    # Street-facing V section: tall clerestories under the upturned ends, dining room half a level higher.
    def ceiling(x): return 4.29+(.31*(-1.1-x) if x < -1.1 else .225*(x+1.1))
    for x0,x1,bottom in ((-7.35,-1.1,.91),(-1.1,6.95,.38)):
        prism(s,WALL,[(x0,bottom),(x1,bottom),(x1,ceiling(x1)),(x0,ceiling(x0))],-2.55,5.6)
        B(s,gray,(x0+x1)/2,1.52,.14,x1-x0,8.22,bottom-.14)
    for x0,x1 in ((-8.12,-1.1),(-1.1,7.75)):
        roofseam(r,ROOF,x0,ceiling(x0)+.20,x1,ceiling(x1)+.20,-3.22,6.23,.20,.48)
    for j in range(15):
        x=-6.91+j*.937
        h=ceiling(x)-3.72
        B(s,DARK,x,-2.59,3.55,.835,.14,h)
        B(s,GLASS[j%3],x,-2.68,3.64,.735,.045,h-.18)
    bandwin(-4.46,-2.56,1.64,4.60,1.56,6,1); door(-.52,-2.56,.47,1.31,2.5,ACC)
    for dx in (1.42,3.73,6.02): shutter(dx,-2.58,.91,1.6,2.1,TIM)
    for side,x in ((-1,-7.35),(1,6.95)):
        with frame(x,1.53,side*90):
            for j in (-2.50,0,2.50): bandwin(j,0,1.62,1.84,1.57,3,2)
    with frame(0,5.62,180):
        for x in (-4.9,-2.5,.35,3.6,6): win(x,0,1.54,1.74,1.48)
    B(c,SNOW,3.4,-4.20,3.25,8.67,4.75,.21,.055)
    B(c,SEC,3.4,-6.56,3.23,8.67,.145,.16)
    # Tapered V props with splayed legs; an open concrete ring screen shades the driveway.
    for xx in (.15,6.82):
        for dx in (-.58,.58): beam(c,ACC,(xx,-6.18,.15),(xx+dx,-6.18,3.25),.14,.22)
    with frame(7.43,-4.39,90):
        for row in range(5):
            for j in range(6):
                x=(j-2.5)*.62; z=.56+row*.59; rad=.282
                vs=[]; n=20
                for y in (-.115,.115):
                    for ring in (0,1):
                        for k in range(n):
                            a=TAU*k/n; cr,sr=math.cos(a),math.sin(a)
                            rad0=.306/max(abs(cr),abs(sr)) if ring==0 else .212
                            vs.append((x+rad0*cr,y,z+rad0*sr))
                faces=[]
                for k in range(n):
                    u=(k+1)%n
                    for a,b in ((0,n),(n,3*n),(3*n,2*n),(2*n,0)): faces.append((a+k,a+u,b+u,b+k))
                add(f,WALL,vs,faces)
        B(f,SEC,0,0,.14,3.89,.31,.17)
    B(q,gray,-1.62,-2.8,.14,.98,.58,5.65)
    rng=random.Random(230)
    for row in range(21):
        widths=[.43+rng.uniform(-.12,.08)]; widths.append(.96-widths[0]); left=-2.10
        for i,w in enumerate(widths):
            zz=.17+row*.263
            prism(q,rng.choice((gray,gold,umber)),[(left+.015,zz+.02),(left+w-.018,zz+.009),(left+w-.04,zz+.243),(left+.027,zz+.225)],-3.112,-3.082)
            left+=w
    staircase(-.65,-2.85,.14,1.59,2,.35,.165); bed(-4.75,-3.34,4.5,1.19,.20)
    for j in range(6): pandan(-6.55+.73*j,-3.33,.56,.61,j+8)
    for j in range(6): B(g,SNOW,-.68,-3.76-j*.58,.145,1.46,.42,.063,.022)
    B(g,WALL,-3.0,-6.88,.18,2.61,.43,.97,.05); B(g,ACC,-3.81,-6.90,.18,.85,.47,1.22,.03)
    label('17',-3.80,-7.149,.96,.53,.42,SNOW)
    for j in range(5): pandan(-7.89+j*.96,-6.45,.2,.62,41+j)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
