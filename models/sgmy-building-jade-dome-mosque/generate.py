"""Jade Dome — original procedural SG/MY streetscape asset.
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

SLUG = 'sgmy-building-jade-dome-mosque'
TITLE = 'Jade Dome | Neighbourhood Mosque'


def pointed(u, r):
    q = .48*r
    return math.sqrt(max(0,(r+q)**2-(abs(u)+q)**2)) / math.sqrt((r+q)**2-q*q)


def portal(sec, trim, wall, x, y0, y1, spring, half, rise, lip, over):
    n = 24
    us = [-1+2*i/n for i in range(n+1)]
    inside = [(x+u*half,spring+rise*pointed(u*half,half)) for u in us]
    outside = [(x+u*(half+lip),spring+(rise+lip)*pointed(u*(half+lip),half+lip)) for u in us]
    verts = [(a,y,z) for y in (y0,y1) for a,z in inside+outside]
    s = n+1
    faces = [(0,s,3*s,2*s),(s-1,2*s-1,4*s-1,3*s-1)]
    for i in range(n):
        faces.extend(((i,i+1,s+i+1,s+i),(2*s+i,3*s+i,3*s+i+1,2*s+i+1),
                      (i,2*s+i,2*s+i+1,i+1),(s+i,s+i+1,3*s+i+1,3*s+i)))
    add(sec,trim,verts,faces)
    prism(sec,wall,outside+[(x+half+lip,over),(x-half-lip,over)],y0+.062,y1-.025)


def lancet(sec, x, y, base, w, h, stone, glass, bronze):
    r = w/2
    spring = base+h*.64
    def outline(wd,b,sp,rise):
        return [(x-wd,b),(x+wd,b)]+[(x+u*wd,sp+rise*pointed(u*wd,wd)) for u in [1-j/8 for j in range(17)]]
    prism(sec,stone,outline(r+.095,base-.08,spring+.06,h*.36+.085),y-.088,y+.088)
    prism(sec,glass,outline(r-.043,base+.045,spring,h*.36-.044),y-.125,y-.073)
    box(sec,bronze,(x,y-.137,(base+.10+spring)/2),(.063,.035,spring-base-.033),.008)
    box(sec,bronze,(x,y-.14,base+h*.46),(w-.107,.042,.063),.008)


def crescent(sec, mat, x,y,z,r):
    d = .68*r
    a = math.acos(d/(2*r))
    a2 = math.pi-a
    outer = [(r*math.cos(t),r*math.sin(t)) for t in [a+(TAU-2*a)*i/26 for i in range(27)]]
    inner = [(d+r*math.cos(t),r*math.sin(t)) for t in [TAU-a2-(TAU-2*a2)*i/18 for i in range(1,18)]]
    q = math.pi*.29
    poly = [(x+u*math.cos(q)-v*math.sin(q),z+u*math.sin(q)+v*math.cos(q)) for u,v in outer+inner]
    prism(sec,mat,poly,y-.075*r,y+.075*r)


def dome(sec, mats, seam, gold, x, y, z, r, h):
    # Profile is normalized from springing to finial, with blue-green glazed sectors.
    raw = [(0,.87),(.075,.96),(.165,1),(.24,.992),(.32,.963),(.41,.913),(.50,.832),(.59,.70),
           (.685,.55),(.768,.393),(.838,.271),(.894,.18),(.949,.102),(1,.034)]
    n = 64
    rings = [(z+k*h,v*r) for k,v in raw]
    verts = [(x+rr*math.cos(TAU*j/n),y+rr*math.sin(TAU*j/n),zz) for zz,rr in rings for j in range(n)]
    for k,mat in enumerate(mats):
        faces = [(i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j)
                 for i in range(len(rings)-1) for j in range(n) if (j//4+j//11)%len(mats)==k]
        used = sorted({v for f in faces for v in f})
        ix = {j:a for a,j in enumerate(used)}
        add(sec,mat,[verts[j] for j in used],[tuple(ix[j] for j in f) for f in faces],True)
    lathe(sec,seam,x,y,[(z-.12,r*.873),(z-.038,r*.911),(z+.09,r*.894)],48)
    # Low-profile standing seams follow the larger dome's ribs.
    if r>2:
        for j in range(16):
            c,s = math.cos(TAU*j/16),math.sin(TAU*j/16)
            for (zz,rad),(zz1,rad1) in zip(rings,rings[1:]):
                rod(sec,seam,(x+(rad+.016)*c,y+(rad+.016)*s,zz),
                    (x+(rad1+.016)*c,y+(rad1+.016)*s,zz1),.030,6)
    zz = z+h
    lathe(sec,gold,x,y,[(zz-.06,r*.049),(zz+.14,r*.072),(zz+.24,r*.070),(zz+.34,r*.041),
                       (zz+.58,r*.023),(zz+.7,r*.017)],18)
    crescent(sec,gold,x,y,zz+.67+max(.23,r*.126),max(.23,r*.126))


def build():
    base, hall, porch, screens, dome_sec, tower, fixtures = 'Paved Forecourt','Prayer Hall and Rear Wings','Pointed Entrance Arcade','Lancets and Geometric Screens','Jade Domes and Finials','Single Minaret','Entry Fittings'
    stone = material('Warm Limestone Render','ddd3bb')
    ivory = material('Polished Cream Mouldings','edddbb')
    base_m = material('Taupe Granite Plinth','979183')
    tile = material('Sage Courtyard Stone','a5aa9b')
    light_tile = material('Pale Courtyard Stone','bbb6a8')
    green = material('Celadon Architectural Trim','83a294')
    bronze = material('Dark Bronze Grilles','5b5949',.42,.30)
    gold = material('Satin Brass Finials','c79e5d',.38,.50)
    wood = material('Dark Merbau Entry Doors','725440',.56)
    glass = material('Dark Sea Green Glazing','486867',.34,.19)
    domes = [material(n,c,.42,.27) for n,c in [('Jade Roof Glaze','398579'),('Moss Jade Roof Glaze','45897b'),('Sea Jade Roof Glaze','347e78'),('Bright Jade Roof Glaze','4d9587')]]
    seam = material('Copper Patina Seams','477c6b',.49,.30)
    leaf = material('Ixora Leaves','557445')
    soil = material('Planter Earth','655346')
    block(base,base_m,-13.6,13.6,-12.2,10.8,0,.24,.096)
    block(base,light_tile,-13.36,13.36,-11.94,10.59,.24,.39,.058)
    for j in range(14):
        xx = (j-6.5)*1.86
        for k in range(3):
            yy = -11.33+k*1.28
            box(base,light_tile if (j+k)%3==1 else tile,(xx,yy,.4),(1.837,1.256,.029),.009)
    block(hall,stone,-8.78,8.78,-4.62,8.58,.60,6.79,.09)
    block(hall,base_m,-8.96,8.96,-4.78,8.76,.39,.82,.05)
    block(hall,ivory,-9.09,9.09,-4.93,8.94,6.48,6.81,.077)
    block(hall,stone,-8.86,8.86,-4.74,8.72,6.77,6.947,.028)
    block(hall,green,-8.96,8.96,-4.86,8.8,6.89,7.04,.043)
    block(hall,ivory,-9.02,9.02,-4.906,8.87,7.03,7.18,.047)
    for s in (-1,1):
        x = s*10.75
        box(hall,stone,(x,3.22,2.01),(4.42,9.69,3.24),.062)
        box(hall,green,(x,3.22,3.61),(4.62,9.97,.24),.043)
        box(hall,ivory,(x,3.22,3.82),(4.76,10.14,.21),.049)
        for y in (-.26,1.56,3.37,5.19,7.01):
            xx = s*12.98
            box(screens,green,(xx,y,2.11),(.15,1.04,1.68),.037)
            box(screens,glass,(xx+s*.094,y,2.123),(.061,.885,1.51),.029)
            for dy in (-.22,0,.22):
                box(screens,bronze,(xx+s*.133,y+dy,2.123),(.035,.037,1.49))
    # Eight-sided light drum, placed on the main hall roof.
    lathe(dome_sec,ivory,0,1.78,[(7.08,5.91),(7.30,5.99),(7.49,5.79)],8,math.pi/8,False)
    lathe(dome_sec,stone,0,1.78,[(7.43,5.64),(8.96,5.64)],8,math.pi/8,False)
    lathe(dome_sec,green,0,1.78,[(8.89,5.70),(9.047,5.75),(9.22,5.58)],8,math.pi/8,False)
    for i in range(8):
        q = i*math.pi/4
        for j in (-1,0,1):
            xx = math.sin(q)*5.25 + math.cos(q)*j*1.18
            yy = 1.78-math.cos(q)*5.25 + math.sin(q)*j*1.18
            box(dome_sec,ivory,(xx,yy,8.17),(.79,.158,1.19),.04,yaw=q)
            box(dome_sec,glass,(xx+.091*math.sin(q),yy-.091*math.cos(q),8.2),(.61,.05,.94),.026,yaw=q)
            box(dome_sec,bronze,(xx+.125*math.sin(q),yy-.125*math.cos(q),8.22),(.056,.035,.91),yaw=q)
    dome(dome_sec,domes,seam,gold,0,1.78,9.16,5.18,4.69)
    # Roofed entry with three uninterrupted walking routes and recessed main doors.
    for k,(w,z) in enumerate(((15.44,.535),(14.93,.68),(14.41,.83))):
        box(base,base_m,(0,-6.69+k*.16,z-.075),(w,4.37-k*.36,.15),.041)
    block(porch,ivory,-7.21,7.21,-8.32,-4.49,4.91,5.25,.045)
    block(porch,green,-7.31,7.31,-8.42,-4.43,5.22,5.45,.064)
    block(porch,stone,-7.16,7.16,-8.27,-4.51,5.44,5.61,.035)
    for x in (-6.57,-2.17,2.17,6.57):
        box(porch,stone,(x,-8.05,2.29),(.47,.56,2.98),.054)
        box(porch,base_m,(x,-8.05,.966),(.71,.8,.26),.05)
        box(porch,ivory,(x,-8.05,3.46),(.69,.76,.17),.036)
        box(porch,ivory,(x,-8.064,3.67),(.60,.68,.27),.041)
    for x in (-4.37,0,4.37):
        portal(porch,ivory,stone,x,-8.32,-7.77,3.67,1.87,1.145,.195,5.25)
        lancet(screens,x,-4.746,.83,2.38,3.47,ivory,wood,bronze)
        for d in (-.28,.28):
            rod(fixtures,gold,(x+d,-4.919,1.51),(x+d,-4.919,1.91),.035,10)
        rod(fixtures,bronze,(x,-6.52,4.92),(x,-6.52,4.33),.033,8)
        lathe(fixtures,gold,x,-6.52,[(3.99,.08),(4.075,.22),(4.23,.21),(4.35,.09)],12)
    for i in range(3):
        for x in (-7.96,7.96):
            lancet(screens,x,-4.73,1.14+i*1.77,.78,1.27,ivory,glass,bronze)
    for y in (-3.31,-.8,1.71,4.22,6.73):
        for x in (-8.79,8.79):
            box(screens,ivory,(x,y,5.0),(.155,1.38,2.29),.047)
            box(screens,glass,(x+math.copysign(.10,x),y,5.0),(.068,1.12,1.98),.036)
            for dz in (-.53,0,.53):
                box(screens,bronze,(x+math.copysign(.144,x),y,5+dz),(.049,1.12,.068),.011)
    for x in (-6,-3,0,3,6):
        box(screens,green,(x,8.66,4.12),(1.79,.177,2.69),.042)
        box(screens,glass,(x,8.764,4.12),(1.54,.084,2.42),.036)
    box(porch,green,(0,-8.375,5.16),(3.84,.085,.455),.055)
    sign(porch,ivory,'MASJID',(0,-8.426,5.172),2.57,.266)
    # Two interlocking squares form a simple eight-point motif on the lintel.
    for x in (-5.9,-2.61,2.61,5.9):
        for q in (0,math.pi/4):
            pts = [(x+.167*math.cos(q+i*TAU/4),-8.459,5.323+.167*math.sin(q+i*TAU/4)) for i in range(4)]
            for a,b in zip(pts,pts[1:]+pts[:1]):
                beam(porch,gold,a,b,.024)
    # Faceted minaret with a projecting muezzin gallery and a smaller jade cupola.
    x,y=10.48,6.22
    for za,zb,r,m in [(.39,.72,1.73,base_m),(.66,3.53,1.49,stone),(3.55,3.79,1.55,ivory),
                      (3.75,12.25,1.113,stone),(5.8,6.0,1.17,green),(11.7,11.9,1.19,green),
                      (12.18,12.43,1.50,ivory),(12.43,12.62,1.57,green),
                      (12.53,15.55,.91,stone),(15.46,15.71,1.04,ivory)]:
        lathe(tower,m,x,y,[(za,r),(zb,r*.982)],8,math.pi/8,False)
    for j in range(8):
        a = j*TAU/8
        corner = a+math.pi/8
        xx,yy = x+1.43*math.cos(corner), y+1.43*math.sin(corner)
        rod(tower,bronze,(xx,yy,12.57),(xx,yy,13.52),.059,8)
        for z in (12.94,13.53):
            b = corner+TAU/8
            beam(tower,bronze,(xx,yy,z),(x+1.43*math.cos(b),y+1.43*math.sin(b),z),.058)
        for z in (5.18,8.23,10.96,14.54):
            r = 1.045 if z<13 else .858
            xx, yy = x+r*math.cos(a),y+r*math.sin(a)
            box(tower,glass,(xx,yy,z),(.086,.313,1.23),.026,yaw=a)
    dome(tower,domes,seam,gold,x,y,15.67,1.066,1.29)
    for s in (-1,1):
        x = s*10.42
        box(fixtures,ivory,(x,-7.41,.66),(3.35,1.23,.50),.10)
        box(fixtures,soil,(x,-7.41,.921),(3.08,.95,.05),.035)
        for j in range(7):
            lathe(fixtures,leaf,x+(j-3)*.397,-7.42,[(.94,.25),(1.17,.39),(1.46+(j%2)*.12,.265),(1.58+(j%2)*.1,.102)],9,j)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, (.64,-1,.50), (1152,952))
