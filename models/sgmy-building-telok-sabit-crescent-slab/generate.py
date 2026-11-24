"""Telok Sabit | crescent access-gallery HDB slab.
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


def label(text,x,y,z,w,h,mat=None):
    sign('Cast lettering',mat or SNOW,text,(x,y,z),w,h)

def slab(s,mat,points,z,h):
    n=len(points)
    vs=[(x,y,zz) for zz in (z,z+h) for x,y in points]
    add(s,mat,vs,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])


def bandwin(x,y,z,w,h,n,seed):
    s='Aluminium ribbon casements'; B(s,DARK,x,y-.024,z,w,.08,h)
    gap=.074; pw=(w-gap)/n
    for i in range(n):
        xx=x-w/2+gap/2+(i+.5)*pw
        B(s,GLASS[(seed+i//2+(i%2)*2)%3],xx,y-.071,z+.074,pw-gap,.026,h-.148)
    B(s,SNOW,x,y-.115,z-.095,w+.19,.285,.095)


SLUG = 'sgmy-building-telok-sabit-crescent-slab'
TITLE = 'Telok Sabit | crescent access-gallery HDB slab'
VIEW = (.71,-1.67,.75)
RESOLUTION = (1120,880)

def build():
    palette('e4dcca','417c86','e2a656','879794','78614e')
    s='Crescent dwelling slab'; rails='Curved gallery balustrades'; e='Lift and service spine'; v='Open void deck'; zbase=3.18; step=2.88; floors=6; top=zbase+floors*step
    def xy(rad,a):
        q=math.radians(a); return (math.sin(q)*rad,16.2-math.cos(q)*rad)
    def arc(r,a,b,n=24): return [xy(r,a+(b-a)*j/n) for j in range(n+1)]
    def ring(section,mat,inner,outer,z,h,a=-58,b=58):
        slab(section,mat,arc(outer,a,b)+arc(inner,b,a),z,h)
    ring(v,PAVE,10,24.4,0,.17,-65,65); ring(s,WALL,12.0,19.48,zbase,top-zbase)
    ring(s,ROOF,11.90,19.65,top,.13)
    for rr in (12.02,19.50): ring(s,SNOW,rr-.11,rr+.11,top+.13,.48)
    for j in range(8):
        a=-50.75+j*14.5
        for rad in (13.42,20.23):
            with frame(*xy(rad,a),a):
                B(v,SNOW,0,0,.17,.48,.58,3.02); B(v,ACC,0,0,.17,.50,.60,.72)
        with frame(*xy(17,a),a):
            if j in (1,3,4,6):
                B(v,SEC,0,0,.62,2.20,.54,.13,.035)
                for xx in (-.8,.8): B(v,PAVE,xx,0,.17,.30,.49,.46)
        with frame(*xy(12,a),180+a):
            for k in range(floors): bandwin(0,0,zbase+.82+k*step,2.37,1.36,3,k+j)
        with frame(*xy(19.48,a),a):
            for k in range(floors):
                zz=zbase+k*step
                bandwin(-.78,0,zz+1.03,2.37,1.13,3,j+k)
                B('Gallery doors',TIM,1.12,-.08,zz+.15,.91,.105,2.13); B('Gallery doors',SEC,1.12,-.15,zz+.51,.64,.04,1.24)
                B('Gallery doors',SUN,1.45,-.18,zz+1.1,.046,.05,.15)
    for k in range(floors+1):
        zz=zbase+k*step
        ring(s,SNOW,19.39,21.48,zz,.17)
        if k==floors: break
        # Open slots in the outer parapet; a fine continuous top rail follows the same curve.
        ring(rails,ACC,21.22,21.42,zz+.17,.54)
        ring(rails,SNOW,21.24,21.43,zz+1.09,.095)
        for j in range(24):
            a=-58+(j+.5)*116/24
            with frame(*xy(21.33,a),a): B(rails,WALL,0,0,zz+.70,.20,.21,.40)
        for j in range(4):
            a=-46.5+j*31
            with frame(*xy(20.86,a),a):
                if (k+j)%3==1:
                    B('Drying towels',[SEC,TILE,GLASS[1]][j%3],0,-.60,zz+.59,.76,.10,.59)
                    B('Drying towels',SNOW,0,-.659,zz+.68,.76,.02,.064)
    # A cylindrical vertical-circulation tower anchors one end of the curve.
    x,y=xy(18.06,58)
    lathe(e,ACC,x,y,[(.17,2.38),(top+1.23,2.38)],36)
    for k in range(floors+1):
        zz=1.06+k*step
        for j in range(8):
            a=j*45; rad=2.385; q=math.radians(a)
            with frame(x+rad*math.sin(q),y-rad*math.cos(q),a):
                B(e,DARK,0,0,zz,1.05,.09,.89); B(e,GLASS[1],0,-.057,zz+.07,.93,.035,.75)
        lathe(e,SNOW,x,y,[(zz-.15,2.48),(zz-.035,2.48)],36)
    lathe(e,SNOW,x,y,[(top+1.23,2.58),(top+1.47,2.58)],36)
    # Opposite end-wall mural: sail shapes in glazed coloured concrete.
    with frame(*xy(15.76,-58),-148):
        B(e,WALL,0,-.05,.17,6.68,.31,top-.17)
        for side,mat in ((-1,ACC),(1,SEC)):
            prism(e,mat,[(side*.15,3.8),(side*2.65,5.52),(side*.15,15.96-side*.48)],-.225,-.207)
        label('67',0,-.224,top-2.04,2.29,1.42,ACC)
    with frame(*xy(21.8,-9),-9):
        B(v,ACC,0,0,2.65,6.0,4.63,.19,.065)
        for xx in (-2.62,2.62): B(v,SNOW,xx,-1.92,.17,.24,.28,2.50)
        label('BLOK  67',0,-2.337,2.75,2.41,.145)
    for j in (-44,-25,16,36):
        with frame(*xy(22.65,j),j):
            bed(0,0,3.91,1.39,.17)
            for k in range(4): pandan((k-1.5)*.91,0,.54,.74,k+j+50)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
