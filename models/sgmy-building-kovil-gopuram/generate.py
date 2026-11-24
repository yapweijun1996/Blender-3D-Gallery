"""Taman Melor | Kovil with Gopuram — original procedural SG/MY streetscape asset.
Rebuild both outputs with Blender 5.2: blender -b --python-exit-code 1 --python generate.py
One unit = one metre; -Y is street-facing, base centre is the installation pivot.
Static visual geometry; texture-free palette with UV0; no external inputs or brand marks.
model.glb requires a Draco decoder. Studio lights and backdrop are preview-only.
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
    root['origin_note' = 'Ground centre'
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
    scene.cycles.samples = 24
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

def path(section, mat, points, radius, n=8):
    """Smooth straight segments passing through the cross section centres."""
    p = [Vector(v) for v in points]
    rings = []
    for i,v in enumerate(p):
        axis = p[min(i+1,len(p)-1)]-p[max(0,i-1)]
        b = axis.to_track_quat('Z','Y').to_matrix()
        rings.append([v+b@Vector((radius*math.cos(TAU*j/n),radius*math.sin(TAU*j/n),0))
                      for j in range(n)])
    loft(section,mat,rings,True)

def pavement(section, x, y, w, d, curb, paver, joint, pitch=1.2, z=.18):
    box(section,curb,(x,y,z/2),(w,d,z),.045)
    box(section,joint,(x,y,z+.018),(w-.1,d-.10,.05),.014)
    nx,ny = max(1,math.ceil(w/pitch)),max(1,math.ceil(d/pitch))
    dx,dy = (w-.13)/nx,(d-.13)/ny
    for i in range(nx):
        for j in range(ny):
            box(section,paver[(i*13+j*23+i*j)%len(paver)],
                (x+(i+.5-nx/2)*dx,y+(j+.5-ny/2)*dy,z+.048),(dx-.019,dy-.019,.02))

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

def louvre(section, frame, back, slat, x, y, z, w, h, count=7, yaw=0):
    basis = Matrix.Rotation(yaw,3,'Z')
    loc = Vector((x,y,z))
    def part(mat, p, dims, b=0):
        box(section,mat,loc+basis@Vector(p),dims,b,basis=basis)
    part(frame,(0,0,0),(w,.16,h),.022)
    part(back,(0,-.090,0),(w-.15,.038,h-.15),.018)
    for k in range(count):
        part(slat,(0,-.118,(k+.5-count/2)*(h-.17)/count),
             (w-.17,.062,(h-.17)/count*.48),.007)


SLUG = 'sgmy-building-kovil-gopuram'
TITLE = 'Taman Melor | Kovil with Gopuram'
ROLE = 'Tamil Hindu neighbourhood temple'
VIEW = (.68,-1,.58)
RESOLUTION = (1120,920)


def build():
    stone = material('Warm granite','93958e')
    joint = material('Courtyard joints','b4aa96')
    pavers = [material('Courtyard cream','e1d2aa'),material('Courtyard sand','d4be99'),material('Courtyard blush','dec9a4')]
    cream = material('Ivory lime plaster','f0dbac')
    rose = material('Terracotta limewash','ce735e')
    mint = material('Jade limewash','4d9389')
    navy = material('Petrol recess','225359')
    salmon = material('Coral moulding','e8876d')
    ochre = material('Ochre relief','e5b665')
    gold = material('Brass finials','c9924a',.37,.38)
    door = material('Carved red teak','6f372c')
    greens = [material('Temple garden olive','6e8451'),material('Temple garden myrtle','526f48')]
    pavement('Temple Court',0,0,16,21.6,stone,pavers,joint,1.1)
    for s in (-1,1):
        x = s*7.54
        box('Compound Walls',rose,(x,.48,.75),(.32,19.60,1.0),.028)
        box('Compound Walls',cream,(x,.48,1.29),(.47,19.7,.16),.023)
        for y in (-9.3,-5.2,-.75,3.7,8.2,10.2):
            box('Compound Walls',cream,(x,y,.81),(.56,.49,1.18),.028)
            box('Compound Walls',ochre,(x,y,1.45),(.66,.59,.16),.03)
        box('Compound Walls',rose,(s*5.2,-9.32,.73),(4.8,.34,.96),.024)
        box('Compound Walls',cream,(s*5.2,-9.32,1.29),(4.8,.49,.16),.021)
        shrub_row('Court Planters',stone,door,greens,s*5.34,-8.16,.238,2.18)
        shrub_row('Court Planters',stone,door,greens,s*5.84,6.14,.238,2.0)
    box('Compound Walls',rose,(0,10.2,.76),(15.3,.38,1.03),.03)
    box('Compound Walls',cream,(0,10.2,1.34),(15.42,.52,.161),.023)

    def tier(sec, x, y, z, w, d, h, count):
        # Successive dentilled, recessed storeys frame ornamental lotus niches.
        box(sec,mint,(x,y,z+h*.50),(w,d,h),.07)
        for offset,extra,hh,mat in ((.07,.39,.13,navy),(.17,.60,.12,ochre),(.28,.34,.11,rose),
                                    (.85,.14,.11,rose),(.96,.34,.14,salmon),(1,.49,.08,cream)):
            box(sec,mat,(x,y,z+h*offset),(w+extra,d+extra,hh),.028)
        for side in (-1,1):
            yy = y+side*(d/2+.05)
            for j in range(count):
                xx = x+(j+.5-count/2)*(w-.28)/count
                r = min(.36,w/count*.31)
                spring = z+h*.60
                box(sec,navy,(xx,yy,z+h*.52),(1.92*r,.12,h*.34),.035)
                arch(sec,cream,xx,yy-.073,yy+.073,spring,r,h*.18,.051,12)
                for s in (-1,1):
                    box(sec,ochre,(xx+s*r,yy,z+h*.470),(.08,.15,h*.275),.012)
                lathe(sec,salmon,xx,yy+side*.088,[(z+h*.38,r*.48),(z+h*.44,r*.57),
                      (z+h*.55,r*.28),(z+h*.65,.017)],10)
                box(sec,cream,(xx,yy+side*.086,z+h*.36),(r*1.61,.14,.075),.014)
            for j in range(max(3,count*3)):
                xx = x+(j+.5-count*1.5)*(w-.14)/(count*3)
                box(sec,cream,(xx,y+side*(d/2+.164),z+h*.895),(.105,.16,.128),.014)
        for s in (-1,1):
            n = max(1,round(d/1.2))
            xx = x+s*(w/2+.065)
            for j in range(n):
                yy = y+(j+.5-n/2)*(d-.34)/n
                louvre(sec,cream,navy,ochre,xx,yy,z+h*.58,min(.63,d*.48),.41,2,s*math.pi/2)
                lathe(sec,salmon,xx+s*.098,yy,[(z+h*.41,.084),(z+h*.48,.12),
                                             (z+h*.57,.082),(z+h*.64,.025)],10)
            for q in (-1,1):
                xx,yy = x+s*(w/2-.14),y+q*(d/2-.06)
                lathe(sec,ochre,xx,yy,[(z+h*.31,.12),(z+h*.48,.16),(z+h*.76,.098),(z+h*.85,.13)],8)

    def crown(sec,x,y,z,w,d):
        # Barrel-vault cap with a raised rib at each end and a row of brass pots.
        outline = [(y+d*.5*math.cos(math.pi*i/18),z+d*.49*math.sin(math.pi*i/18)) for i in range(19)]
        prism(sec,navy,outline,x-w/2,x+w/2,'X')
        for xx in (x-w/2,x-w*.24,x,x+w*.24,x+w/2):
            path(sec,ochre,[(xx,yy,zz+.028) for yy,zz in outline],.046,8)
        for i in range(5):
            xx = x+(i-2)*w/4.7
            top = z+d*.49
            lathe(sec,gold,xx,y,[(top,.13),(top+.09,.115),(top+.16,.18),(top+.29,.123),
                                (top+.40,.034),(top+.47,.016)],10)

    # The gate is a true open passage with a deep soffit under the upper stages.
    y = -9.1
    for s in (-1,1):
        x = s*1.997
        box('Gopuram Gateway',rose,(x,y,1.85),(1.42,1.91,3.22),.055)
        for z,w,h,mat in ((.43,1.59,.36,stone),(.73,1.58,.18,cream),(1.0,1.48,.13,ochre),
                           (3.18,1.52,.18,ochre),(3.38,1.62,.18,cream)):
            box('Gopuram Gateway',mat,(x,y,z),(w,2.00,h),.028)
        for xx in (x-.41,x+.41):
            box('Gopuram Gateway',cream,(xx,y-1.007,1.99),(.19,.19,2.09),.027)
        box('Gopuram Gateway',mint,(x,y-1.018,2.12),(.55,.116,1.28),.035)
        for k in range(4):
            box('Gopuram Gateway',ochre,(x,y-1.084,1.72+k*.267),(.337,.05,.145),.02,yaw=.015)
    arch('Gopuram Gateway',cream,0,-10.10,-8.15,2.66,1.33,.79,.19,20)
    for s in (-1,1):
        poly = [(s*2.55,2.66),(s*2.55,3.73),(0,3.73)]
        poly += [(s*1.515*math.cos(t),2.66+.97*math.sin(t))
                 for t in [math.pi/2*(1-i/12) for i in range(13)]]
        prism('Gopuram Gateway',rose,poly,-10.02,-8.18)
    for i in range(4):
        tier('Gopuram Ornament',0,y,3.57+i*.93,5.30-i*.84,1.92-i*.21,.93,(5,4,3,2)[i])
    crown('Gopuram Ornament',0,y,7.29,2.11,1.32)

    # Raised main shrine, open mandapa and crowning vimana behind the tall gate.
    box('Mandapa and Sanctum',stone,(0,3.75,.44),(11.4,11.62,.43),.052)
    box('Mandapa and Sanctum',cream,(0,3.75,.71),(11.18,11.5,.23),.042)
    steps('Mandapa and Sanctum',stone,ochre,0,-3.27,5.3,4,.30,.145,.238)
    box('Mandapa and Sanctum',cream,(0,5.68,2.53),(10.3,7.11,3.43),.069)
    for x in (-4.67,-2.39,2.39,4.67):
        lathe('Mandapa and Sanctum',rose,x,-1.50,[(.83,.37),(1.00,.37),(1.16,.27),
              (3.55,.245),(3.66,.32),(3.98,.36)],8)
        for z in (1.108,1.38,3.57,3.77):
            lathe('Mandapa and Sanctum',ochre,x,-1.50,[(z-.06,.31),(z+.06,.31)],10)
    for s in (-1,1):
        for y in (3.20,5.63,8.04):
            louvre('Mandapa and Sanctum',rose,navy,mint,s*5.16,y,2.59,1.19,1.47,6,s*math.pi/2)
    box('Mandapa and Sanctum',door,(0,2.057,2.10),(3.36,.15,2.55),.038)
    for j in range(12):
        for z in (1.48,2.04,2.59,3.04):
            box('Mandapa and Sanctum',gold,((j-5.5)*.26,1.966,z),(.104,.062,.106),.027)
    for z,w,d,mat,h in ((3.96,11.12,11.63,mint,.36),(4.19,11.52,11.95,ochre,.15),
                       (4.32,11.68,12.08,rose,.21),(4.55,10.64,11.01,cream,.35)):
        box('Sanctum Roof',mat,(0,3.75,z),(w,d,h),.043)
    for j in range(29):
        x = (j-14)*.379
        box('Sanctum Roof',cream,(x,-2.28,4.31),(.192,.174,.182),.012)
    for i in range(3):
        tier('Sanctum Vimana',0,5.7,4.68+i*.89,5.94-i*1.27,5.37-i*1.25,.92,5-i)
    lathe('Sanctum Vimana',mint,0,5.7,[(7.30,1.40),(7.52,1.53),(7.77,1.52),(8.19,1.21),
                                      (8.43,.74),(8.52,.28)],8,phase=math.pi/8, smooth=False)
    lathe('Sanctum Vimana',gold,0,5.7,[(8.48,.30),(8.65,.197),(8.82,.23),(9.02,.104),(9.17,.02)],14)
    box('Temple Inscription',navy,(-5.22,-9.58,1.31),(3.83,.14,.45),.045)
    sign('Temple Inscription',cream,'KOVIL TAMAN MELOR',(-5.22,-9.656,1.31),3.52,.274)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
