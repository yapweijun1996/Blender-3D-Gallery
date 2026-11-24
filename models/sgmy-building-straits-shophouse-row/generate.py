"""Lorong Pala — original procedural SG/MY streetscape asset.
Rebuild with Blender 5.2: blender -b --python generate.py
Metres; front -Y; base origin. GLB requires a Draco decoder. No external inputs.
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


def block(section, mat, x0, x1, y0, y1, z0, z1, b=0):
    box(section, mat, ((x0+x1)/2,(y0+y1)/2,(z0+z1)/2), (x1-x0,y1-y0,z1-z0), b)


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


def arch(section, mat, cx, y0, y1, spring, radius, rise, thick, steps=16):
    # Elliptic arch moulding with radial joints excluded from the visible face.
    verts = []
    for k in range(steps+1):
        t = math.pi*k/steps
        for y in (y0,y1):
            for d in (0,thick):
                verts.append((cx+(radius+d)*math.cos(t),y,spring+(rise+d)*math.sin(t)))
    faces = [(0,1,3,2),(4*steps,4*steps+2,4*steps+3,4*steps+1)]
    for k in range(steps):
        a = 4*k
        for j,l in ((0,1),(1,3),(3,2),(2,0)):
            faces.append((a+j,a+l,a+l+4,a+j+4))
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
    cam.data.ortho_scale = 1.21 * max(max(xx)-min(xx),(max(yy)-min(yy))*aspect)
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
    scene.cycles.samples = 24
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

SLUG = 'sgmy-building-straits-shophouse-row'
TITLE = 'Lorong Pala | Straits Shophouse Row'


def clay_roof(sec, clay, ridge, x, w, y0, y1, lo, hi):
    mid = (y0+y1)/2
    prism(sec,clay[0],[(y0,lo-.15),(mid,hi-.15),(y1,lo-.15),(y1,lo),(mid,hi),(y0,lo)],x-w/2,x+w/2,'X')
    for side in (-1,1):
        dy = (y1-y0)/2
        n = 12 if dy>2.75 else 9
        for k in range(n):
            a,b = k/n,(k+1)/n
            p0,p1 = mid+side*dy*a,mid+side*dy*b
            z0,z1 = hi-(hi-lo)*a,hi-(hi-lo)*b
            for j in range(int(w/.26)+1):
                xx = x-w/2+.13+j*.249
                if xx+.1>x+w/2:
                    break
                profile = [(-1,-.006),(-.72,.036),(0,.057),(.72,.036),(1,-.006)]
                verts = [(xx+.066*u*t,p,z+h+v) for p,z,t,v in ((p0,z0,.89,0),(p1,z1,1,.01))
                         for u,h in profile]
                faces = [(l,l+1,l+6,l+5) for l in range(4)] + [(5,9,8,7,6)]
                add(sec,clay[(k*17+j*13+k*j)%len(clay)],verts,faces)
        rod(sec,ridge,(x-w/2,mid+side*dy,lo-.017),(x+w/2,mid+side*dy,lo-.017),.064,8)
    rod(sec,ridge,(x-w/2,mid,hi+.034),(x+w/2,mid,hi+.034),.125,10)


def build():
    paving, ground, upper, crown, back, graphics = 'Five-Foot Way and Plinth','Open Arcade and Shopfronts','Shutters and Plasterwork','Clay Roofs and Party Walls','Airwell and Service Lane','Shop Lettering'
    stone = material('Grey Lime Terrazzo','9b9285')
    dark = material('Blackened Iron','373c3b',.47)
    cream = material('Ivory Lime Mouldings','f0deb4')
    ochre = material('Ochre Plaster Detail','c5a064')
    tints = [material(n,c) for n,c in [('Seafoam Limewash','7eaaa1'),('Peach Limewash','ce8e76'),('Butter Limewash','dcc281')]]
    shutters = [material(n,c,.52) for n,c in [('Petrol Timber','24535c'),('Oxide Vermilion Timber','894838'),('Kaya Green Timber','4f6346')]]
    slats = [material(n,c) for n,c in [('Blue Shutter Blades','3c7480'),('Red Shutter Blades','ab6251'),('Green Shutter Blades','748356')]]
    glass = material('Deep Shop Glazing','465b55',.28,.18)
    amber = material('Amber Transom Glass','ba8d50',.36)
    tiles = [material(n,c,.43) for n,c in [('Jade Glazed Tile','3d7d73'),('Milk Glazed Tile','e9d4ad'),('Oxblood Glazed Tile','a25545')]]
    clay = [material(n,c) for n,c in [('Roof Clay','9a5340'),('Soft Terracotta','ad5e46'),('Darker Terracotta','874b3d'),('Rose Terracotta','b16950')]]
    ridge = material('Glazed Red Ridge','784233',.53)
    service = material('Patinated Downpipe','799193',.42,.24)
    block(paving,stone,-8.16,8.16,-8.28,8.24,0,.19,.047)
    block(paving,cream,-8.09,8.09,-8.11,-5.63,.185,.223,.024)
    for i in range(37):
        x = -7.91+.44*i
        for j in range(4):
            yy = -7.84+.54*j
            box(paving,tiles[1] if (i+j)%2 else tiles[0],(x,yy,.227),(.421,.517,.012))
            if (i+j)%2 == 0:
                box(paving,tiles[1],(x,yy,.235),(.17,.17,.009),yaw=math.pi/4)
    for i,x in enumerate((-5.4,0,5.4)):
        wall, shutter, slat = tints[i],shutters[i],slats[i]
        # Detached ground-level shop front behind a shared, walkable arcade.
        block(ground,wall,x-2.67,x+2.67,-5.76,7.72,.23,3.82,.025)
        box(ground,shutter,(x,-5.826,1.78),(4.45,.23,3.08),.025)
        for j in range(6):
            xx = x+(j-2.5)*.695
            box(ground,glass,(xx,-5.954,1.64),(.58,.025,1.92),.012)
            box(ground,amber,(xx,-5.954,2.965),(.58,.026,.54),.016)
            if j not in (2,3):
                box(ground,slat,(xx,-5.963,.51),(.59,.04,.42),.009)
            else:
                box(ground,ochre,(xx+(.18 if j==2 else -.18),-5.998,1.31),(.042,.062,.29),.012)
        for z in (1.33,2.61,3.31):
            box(ground,shutter,(x,-5.984,z),(4.35,.065,.082),.016)
        block(upper,wall,x-2.7,x+2.7,-7.8,-.78,3.77,7.19,.025)
        block(upper,wall,x-2.7,x+2.7,1.42,7.73,3.77,7.19,.025)
        for side in (-1,1):
            xx = x+side*2.5
            block(back,wall,xx-.2,xx+.2,-.8,1.45,3.75,7.15,.02)
        block(back,stone,x-2.4,x+2.4,-.84,1.45,3.77,3.84,.015)
        block(ground,wall,x-2.7,x+2.7,-7.83,-5.75,3.29,3.79,.032)
        # Curved arcade moulding; the void below it is not filled with geometry.
        arch(ground,cream,x,-8.025,-7.68,2.73,2.39,.55,.18,20)
        # Fan spandrels meet the lintel; add the masonry above the inner arch.
        shell = [(x+2.54*math.cos(math.pi*k/20),2.73+.70*math.sin(math.pi*k/20)) for k in range(21)]
        prism(ground,wall,shell+[(x-2.54,3.52),(x+2.54,3.52)],-7.94,-7.8)
        box(ground,cream,(x,-7.99,3.21),(.25,.15,.28),.024)
        box(upper,cream,(x,-7.93,3.76),(5.37,.4,.23),.032)
        box(upper,cream,(x,-7.9,4.14),(5.37,.22,.095),.02)
        for j in range(22):
            xx = x+(j-10.5)*.235
            box(upper,tiles[(j+2*i)%3],(xx,-7.877,3.975),(.215,.09,.224),.011)
        for j in (-1,0,1):
            xx = x+1.49*j
            yy = -7.88
            # Raised reveals and full-height louvred shutters under a vent fanlight.
            box(upper,cream,(xx,yy,5.54),(1.28,.23,2.09),.035)
            box(upper,shutter,(xx,yy-.14,5.54),(1.08,.105,1.88),.020)
            prism(upper,cream,[(xx+.64*math.cos(math.pi*k/16),6.57+.39*math.sin(math.pi*k/16)) for k in range(17)],yy-.12,yy+.09)
            prism(upper,shutter,[(xx+.49*math.cos(math.pi*k/12),6.565+.265*math.sin(math.pi*k/12)) for k in range(13)],yy-.16,yy-.116)
            for k in range(1,6):
                ang = k*math.pi/6
                beam(upper,ochre,(xx,yy-.176,6.57),(xx+.47*math.cos(ang),yy-.176,6.57+.249*math.sin(ang)),.037)
            for s in (-1,1):
                for k in range(11):
                    box(upper,slat,(xx+.253*s,yy-.2,4.77+.139*k),(.437,.076,.092),.008)
            box(upper,cream,(xx,yy-.074,4.48),(1.37,.4,.13),.025)
            box(upper,wall,(xx,yy,4.319),(1.2,.19,.147))
        for xx in (x-2.49,x+2.49):
            box(upper,cream,(xx,-7.9,5.55),(.24,.23,2.69),.026)
            for z in (4.43,6.66,6.9):
                box(upper,cream,(xx,-7.94,z),(.38,.3,.12),.025)
        box(upper,cream,(x,-7.94,7.115),(5.42,.44,.23),.042)
        box(upper,ochre,(x,-7.97,6.966),(5.38,.28,.10),.024)
        for j in range(16):
            box(upper,cream,(x+(j-7.5)*.315,-8.055,6.972),(.11,.12,.13),.013)
        # Freestanding party walls trace two ridges divided by an open rooftop airwell.
        clay_roof(crown,clay,ridge,x,5.04,-8.17,-.75,7.22,9.0)
        clay_roof(crown,clay,ridge,x,5.04,1.4,7.99,7.2,8.72)
        for yy in (-.81,1.45):
            box(crown,cream,(x,yy,7.35),(5.12,.28,.28),.034)
        box(back,stone,(x,7.82,.48),(1.24,.37,.52),.025)
        box(back,shutter,(x,7.812,1.58),(1.05,.21,2.19),.027)
        box(back,dark,(x+.36,7.93,1.45),(.07,.049,.13))
        for xx in (x-1.33,x+1.32):
            box(back,cream,(xx,7.806,5.59),(1.14,.227,1.41),.03)
            box(back,glass,(xx,7.929,5.59),(.87,.039,1.21))
            for k in range(6):
                box(back,shutter,(xx,7.963,5.07+k*.203),(.89,.056,.079),.009)
        rod(back,service,(x+2.27,7.849,.32),(x+2.27,7.849,7.13),.066,10)
        for z in (1,3.97,6.45):
            box(back,dark,(x+2.27,7.855,z),(.184,.176,.075),.011)
        box(graphics,shutter,(x,-8.163,3.701),(2.64,.115,.307),.042)
        sign(graphics,cream,('KEDAI KOPI','KEDAI JAHIT','KEDAI BUNGA')[i],(x,-8.226,3.705),2.38,.169)
        for xx in (x-1.91,x+1.91):
            rod(ground,ochre,(xx,-7.38,3.49),(xx,-7.38,3.10),.026,8)
            lathe(ground,amber,xx,-7.38,[(2.83,.091),(2.887,.194),(3.013,.203),(3.10,.072)],12)
    for x in (-8.1,-2.7,2.7,8.1):
        box(ground,cream,(x,-7.66,1.87),(.426,.507,3.31),.034)
        box(ground,stone,(x,-7.66,.375),(.55,.62,.31),.032)
        box(ground,cream,(x,-7.66,2.736),(.58,.62,.18),.034)
        box(ground,tiles[0],(x,-7.948,.69),(.317,.024,.21),.009)
        pts = [(-7.98,7.10),(-7.98,7.55),(-4.46,9.16),(-.70,7.54),(1.4,7.54),(4.69,8.92),(7.98,7.54),(7.98,7.10)]
        prism(crown,cream,pts,x-.17,x+.17,'X')
        for a,b in zip(pts[1:-2],pts[2:-1]):
            beam(crown,ridge,(x,*a),(x,*b),.365,.12,.018)
    for yy in (-4.1,-1.5,1.3,4.05,6.63):
        box(back,cream,(8.131,yy,5.31),(.115,.69,3.48),.021)
    for yy in (-2.72,3.42,5.56):
        box(back,cream,(8.145,yy,5.56),(.16,1.12,1.72),.023)
        box(back,shutters[2],(8.242,yy,5.57),(.035,.93,1.46),.011)
        for j in range(8):
            box(back,slats[2],(8.271,yy,4.94+j*.18),(.046,.81,.088),.006)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, (.50,-1,.55), (1176,900))
