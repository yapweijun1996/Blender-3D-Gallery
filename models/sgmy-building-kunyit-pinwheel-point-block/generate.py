"""Kunyit Close | four-blade HDB point block.
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


def label(text,x,y,z,w,h,mat=None):
    sign('Cast lettering',mat or SNOW,text,(x,y,z),w,h)


def bandwin(x,y,z,w,h,n,seed):
    s='Aluminium ribbon casements'; B(s,DARK,x,y-.024,z,w,.08,h)
    gap=.074; pw=(w-gap)/n
    for i in range(n):
        xx=x-w/2+gap/2+(i+.5)*pw
        B(s,GLASS[(seed+i//2+(i%2)*2)%3],xx,y-.071,z+.074,pw-gap,.026,h-.148)
    B(s,SNOW,x,y-.115,z-.095,w+.19,.285,.095)

def skirting(s,mat,x,y,z,w,d,h,thick):
    for v in (-1,1):
        B(s,mat,x,y+v*(d-thick)/2,z,w,thick,h)
        B(s,mat,x+v*(w-thick)/2,y,z,thick,d-2*thick,h)


SLUG = 'sgmy-building-kunyit-pinwheel-point-block'
TITLE = 'Kunyit Close | four-blade HDB point block'
VIEW = (.66,-1.4,.53)
RESOLUTION = (920,1040)

def build():
    palette('e2dbc7','b85e3c','e6b657','7d918b','684736')
    s='Four offset dwelling stacks'; v='Void deck and benches'; p='Porcelain sunburst panels'
    B(v,PAVE,0,0,0,23.4,23.4,.18,.12)
    top=3.5+10*2.91
    B(s,SNOW,0,0,.18,9.8,9.8,top-.18)
    B('Lift overrun',ACC,0,0,top,5.8,5.8,2.4); B('Lift overrun',SNOW,0,0,top+2.4,6.2,6.2,.25,.055)
    for side in range(4):
        with frame(angle=side*90):
            B(s,WALL,2,-6.85,3.5,8.7,7.9,top-3.5)
            for x in (-1.88,2,5.84):
                for y in (-10.13,-6.1):
                    B(v,WALL,x,y,.18,.48,.60,3.32); B(v,ACC,x,y,.18,.50,.62,.72)
            B(v,SEC,2,-10.04,3.16,8.7,1.5,.34)
            B(v,SNOW,-.66,-7.8,.63,2.1,.49,.16,.045)
            for x in (-1.46,.14): B(v,ACC,x,-7.8,.18,.23,.42,.48)
            # Mosaic stair screen on the outer cheek. A projecting cornice caps each bay.
            B(p,ACC,5.31,-10.85,3.5,2.01,.19,top-3.5)
            for k in range(10):
                z=3.5+2.91*k
                bandwin(.92,-10.8,z+.86,5.55,1.46,6,k+side)
                B(s,SNOW,.92,-10.97,z+.50,6.5,.48,.20)
                if k<8:
                    for j in range(3):
                        for i in range(2):
                            box(p,[SEC,SNOW,TILE][(i+j+k//2)%3],(4.87+i*.82,-10.969,z+.62+j*.79),(.48,.065,.48),basis=Matrix.Rotation(math.pi/4,3,'Y'))
                with frame(6.35,-7.2,90):
                    bandwin(0,0,z+.86,5.40,1.46,5,k+1)
                with frame(-2.35,-8.1,-90): bandwin(0,0,z+1.1,3.3,1.18,3,k)
            label('318',5.31,-10.966,top-2.1,1.90,.98)
            B(s,SNOW,2,-6.85,top,9.1,8.25,.25,.045)
            B(s,ROOF,2,-6.85,top+.25,8.79,7.96,.09)
            B('Tank plinths',PAVE,2,-6.52,top+.34,2.62,2.26,.31)
            lathe('Pressed steel water tanks',METAL,2,-6.52,[(top+.65,1.01),(top+.74,1.07),(top+2.13,1.07),(top+2.28,.84),(top+2.31,.25)],20)
            for k in range(4): lathe('Tank hoops',DARK,2,-6.52,[(top+.80+.39*k,1.081),(top+.85+.39*k,1.081)],20)
            skirting(s,WALL,2,-6.85,top+.33,8.88,8.03,.45,.14)
            with frame(0,-4.92): door(-.8,0,.18,1.55,2.5)
            bed(-5.25,-8.65,3.1,2.25,.18)
            for j in range(3): pandan(-6.2+j*.92,-8.65,.55,.77,31+j)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
