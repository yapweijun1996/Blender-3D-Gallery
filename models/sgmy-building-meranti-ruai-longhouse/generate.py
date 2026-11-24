"""Meranti Ruai | Sarawak gallery longhouse.
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


def door(x,y,z,w=1.05,h=2.16,mat=None):
    s='Entrance joinery'; mat=mat or TIM
    B(s,DARK,x,y-.04,z,w+.13,.12,h+.08)
    for i in (-1,1):
        cx=x+i*w/4
        B(s,mat,cx,y-.12,z+.015,w/2-.022,.10,h-.02)
        for zz,hh in ((.14,h*.32),(h*.51,h*.40)):
            B(s,SEC,cx,y-.18,z+zz,w*.34,.04,hh,.015)
        B(s,SUN,x+i*.09,y-.235,z+.84,.032,.06,.21,.01)


def porchrail(x,y,z,w,h,mat=None):
    s='Balcony joinery'; mat=mat or TIM
    B(s,mat,x,y,z+h-.07,w,.12,.09,.016)
    B(s,mat,x,y,z+.09,w,.09,.075)
    n=max(1,round(w/.27))
    for j in range(n):
        xx=x+w*((j+.5)/n-.5)
        B(s,mat,xx,y,z+.13,.068,.08,h-.18,.009)


SLUG = 'sgmy-building-meranti-ruai-longhouse'
TITLE = 'Meranti Ruai | Sarawak gallery longhouse'
VIEW = (.80,-1.60,.73)

def build():
    palette('a77750','805044','c29863','678589','614e40')
    s='Bilik rooms'; d='Shared ruai and tanju'; g='Partition joinery'; r='Continuous zinc roof'
    B(s,PAVE,0,-.53,0,28.6,12.55,.10,.08)
    for x in range(-13,14,2):
        for y in (-4.57,-2.57,-.22,3.43):
            lathe(d,TIM,x,y,[(.10,.19),(1.77,.155)],8)
        beam(d,TIM,(x,-4.57,.50),(x+.72,-4.57,1.69),.111)
    B(d,TIM,0,-.5,1.75,27.1,8.48,.23,.02); B(s,WALL,0,1.44,1.98,26.94,4.60,2.75)
    for j in range(19): B(d,SEC if j%4 else WALL,0,-4.66+j*.204,1.98,26.97,.186,.07,.009)
    for i in range(6):
        x=(i-2.5)*4.48
        door(x-.85,-.87,1.98,1.13,2.04); win(x+1.06,-.87,2.62,1.38,1.23,2,i,TIM)
        B(g,TIM,x-2.19,-1,1.98,.13,.14,2.74)
        for yy in (-3.1,3.76):
            B(g,TIM,x-2.13,yy,1.98,.18,.2,2.45)
            for dx in (-.47,.47): beam(g,SEC,(x-2.13,yy,3.68),(x-2.13+dx,yy,4.40),.10)
        with frame(x,3.74,180): win(0,0,2.66,1.88,1.11,3,i,TIM)
        # Woven sleeping mats airing on the sunny gallery rail.
        if i not in (0,4):
            porchrail(x,-4.54,2.05,4.36,.78,TIM)
            colour=[TILE,ACC,SEC][i%3]; B(g,colour,x-.45,-4.62,2.21,1.68,.10,.69,.015)
            for j in range(8):
                xx=x-1.20+j*.21
                box(g,SNOW,(xx,-4.677,2.55),(.112,.018,.112),basis=Matrix.Rotation(.785,3,'Y'))
            for zz in (2.29,2.78): B(g,SUN,x-.45,-4.683,zz,1.67,.012,.044)
        # Raised ridge sections show that this is a house of many adjoining households.
        clr=ROOF if i%2 else material('Zinc | bay '+str(i+1),['809391','809391','72898c','72898c','85928b','85928b'][i])
        # Cross section in Y/Z, shared between adjoining roofs; broad eave protects the ruai.
        yy=[(-3.86,4.42),(.60,6.82),(4.34,4.83)]
        prism(r,clr,[*yy,(4.34,4.71),(.60,6.70),(-3.86,4.30)],x-2.24,x+2.24,'X')
        for j in range(12):
            xx=x-2.14+j*.365
            for k in (0,1): rod(r,clr,(xx,yy[k][0],yy[k][1]+.008),(xx,yy[k+1][0],yy[k+1][1]+.008),.038,6)
        rod(r,METAL,(x-2.24,.6,6.84),(x+2.24,.6,6.84),.101,8)
    for side in (-1,1):
        with frame(side*13.48,1.44,side*90):
            win(0,0,2.52,1.94,1.51,3,2,TIM)
        prism(g,SEC,[(-3.83,4.34),(.60,6.74),(4.32,4.74),(3.75,4.67),(-.86,4.67)],side*13.44-.055,side*13.44+.055,'X')
        with frame(side*13.42,-3.22,90): porchrail(0,0,2.02,2.79,.79,TIM)
    # Plaited panels in both end gables. Repeated lozenges follow the roof pitch.
    indigo=material('Textile | indigo resist','394e5b')
    for side in (-1,1):
        with frame(side*13.51,0,side*90):
            for j in range(15):
                yy=-3.2+j*.50; xx=side*yy; roofline=6.72-abs(yy-.60)*.54
                for k in range(3):
                    zz=4.93+k*.47
                    if zz+.22>roofline: continue
                    poly=[(xx-.24,zz),(xx,zz+.204),(xx+.24,zz),(xx,zz-.204)]
                    prism(g,TIM if (k+j)%2 else ACC,poly,-.035,-.008)
                    poly=[(xx-.105,zz),(xx,zz+.096),(xx+.105,zz),(xx,zz-.096)]
                    prism(g,SEC,poly,-.05,-.035)
            B(g,TIM,side*.45,-.03,4.66,7.06,.10,.13)
    # Rolled reed blinds and shallow storage baskets populate the shared gallery.
    for i in (0,2,3,5):
        xx=(i-2.5)*4.48+.12; drop=(.54,.68,.86)[i%3]
        for k in range(8):
            zz=4.38-drop*k/8
            rod(g,TIM if k==7 else SEC,(xx-1.55,-3.24,zz),(xx+1.55,-3.24,zz),drop/16,8)
        for dx in (-1.13,.0,1.13): B(g,ACC,xx+dx,-3.31,4.38-drop*.92,.046,.05,drop*.97)
    for xx,yy,rad in ((-8.90,-3.64,.38),(-8.13,-3.55,.27),(3.10,-3.66,.32),(10.62,-3.56,.36)):
        lathe(d,SEC,xx,yy,[(2.05,rad*.74),(2.52,rad),(2.64,rad*.89)],16)
        lathe(d,TIM,xx,yy,[(2.64,rad*.89),(2.67,rad*.75)],16)
        for zz,rr in ((2.18,.85),(2.39,.95),(2.53,1.02)):
            lathe(d,indigo if zz==2.39 else TIM,xx,yy,[(zz,rad*rr),(zz+.042,rad*rr)],16)
    for i in (0,4):
        x=(i-2.5)*4.48
        for dx in (-.61,.61): beam(d,TIM,(x+dx,-6.56,.10),(x+dx,-4.70,2.05),.17,.21)
        for j in range(9): B(d,SEC,x,-6.46+j*.224,.24+j*.213,1.42,.28,.105,.016)
        rod(d,TIM,(x-.66,-6.5,.99),(x-.66,-4.66,2.90),.058,9)
        for y,z in ((-6.50,.20),(-4.68,2.00)): B(d,TIM,x-.66,y,z,.13,.13,.89)


if __name__ == "__main__":
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, (1216, 800))
