"""Bukit Saga | District Post Office — original procedural SG/MY streetscape asset.
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
    # Blender's auto sensor fit uses the longer image dimension for ortho_scale.
    projected_w, projected_h = max(xx)-min(xx), max(yy)-min(yy)
    cam.data.ortho_scale = 1.16 * max(projected_w / min(1,aspect),projected_h * max(1,aspect))
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

def palm(section, bark, greens, x, y, z, height=4.4, phase=0):
    crown = Vector((x+.31,y-.18,z+height))
    path(section,bark,[(x,y,z),(x+.04,y,z+height*.30),
                       (x+.12,y-.05,z+height*.73),crown],.108,9)
    for i in range(9):
        a = i*TAU/9+phase
        axis = Vector((math.cos(a),math.sin(a),0))
        across = Vector((-axis.y,axis.x,0))
        length = 1.42+.23*(i%3)
        pts = [crown+axis*(length*t)+Vector((0,0,.53*math.sin(math.pi*t)-(.45+.10*(i%3))*t*t))
               for t in (0,.17,.35,.54,.73,.91,1)]
        widths = [.033,.14,.22,.205,.161,.091,.006]
        verts = [v+u*w*across-Vector((0,0,abs(u)*.082))
                 for v,w in zip(pts,widths) for u in (-1,0,1)]
        faces = [(k*3+j,k*3+j+1,(k+1)*3+j+1,(k+1)*3+j) for k in range(6) for j in range(2)]
        add(section,greens[i%len(greens)],verts,faces,True)
        rod(section,bark,pts[0],pts[2],.024,6,.54)


SLUG = 'sgmy-building-bukit-saga-post-office'
TITLE = 'Bukit Saga | District Post Office'
ROLE = 'Straits-era district postal hall with shaded arcade'
VIEW = (.55,-1,.52)
RESOLUTION = (1152,898)


def build():
    granite = material('Granite base','96928a')
    joint = material('Forecourt joints','b3a384')
    pavers = [material('Cream flagstone','dccaad'),material('Sand flagstone','c9b89b'),material('Ash flagstone','c7c2b0')]
    plaster = material('Shell limestone stucco','f4dfb7')
    trim = material('Ivory arch moulding','fff1ce')
    band = material('Ochre masonry','c9ab80')
    deep = material('Teak door panel','704d3e')
    indigo = material('Indigo shutters','346273')
    slat = material('Blue shutter slats','638699')
    tiled = [material('Baked clay base','ac5840'),material('Sun baked clay','bc6c53'),material('Pale clay tiles','c27758')]
    red = material('Oxide letterbox','963f32')
    gold = material('Letter slot brass','cbab62',.37,.37)
    grayblue = material('Verandah floor inlay','648690')
    glass = material('Transom blue glass','395056',.3,.18)
    bark = material('Palm trunk','907d60')
    greens = [material('Palm olive','517648'),material('Palm yellow green','839c5d')]
    pavement('Forecourt',0,0,22.8,20.8,granite,pavers,joint,1.24)
    for s in (-1,1):
        x = s*9.16
        shrub_row('Postal Gardens',band,deep,greens,x,-6.47,.238,2.88,1.39)
        palm('Postal Gardens',bark,greens,x,-6.47,.64,3.56,s*.8)
    box('Arcade and Stairs',granite,(0,1.91,.503),(18.16,14.36,.535),.062)
    box('Arcade and Stairs',band,(0,1.91,.746),(18.10,14.27,.16),.041)
    steps('Arcade and Stairs',granite,trim,0,-6.34,9.42,4,.269,.147,.238)
    for i in range(26):
        x = (i-12.5)*.657
        for j in range(4):
            y = -4.94+j*.499
            box('Arcade and Stairs',grayblue if (i+j)%2 else trim,(x,y,.833),(.641,.483,.027))
    box('Postal Hall',plaster,(0,3.17,3.49),(17.27,11.25,5.31),.069)
    for z,h,m in ((1.08,.41,band),(1.40,.10,trim),(3.91,.14,band),(5.55,.13,band),(5.94,.29,trim)):
        box('Postal Hall',m,(0,3.17,z),(17.43,11.44,h),.037)
    for s in (-1,1):
        for j in range(4):
            y = -1.11+j*2.89
            louvre('Shutter Bays',trim,indigo,slat,s*8.66,y,2.79,1.62,2.18,9,s*math.pi/2)
            box('Shutter Bays',band,(s*8.79,y,1.64),(.37,1.85,.145),.03)
        for x in (s*5.82,s*1.94):
            louvre('Shutter Bays',trim,indigo,slat,x,8.84,2.73,1.51,2.16,8,math.pi)
    for x in (-5.74,0,5.74):
        outer = 1.24
        for mat,r,spring,rise,y0,y1 in ((trim,outer,3.47,.69,-2.57,-2.455),
                                       (glass,outer-.13,3.42,.57,-2.605,-2.566)):
            poly = [(x+r*math.cos(math.pi*k/16),spring+rise*math.sin(math.pi*k/16)) for k in range(17)]
            prism('Postal Doors',mat,poly,y0,y1)
        box('Postal Doors',trim,(x,-2.466,2.20),(2.48,.214,2.55),.029)
        box('Postal Doors',indigo,(x,-2.60,2.22),(2.22,.104,2.37),.034)
        for s in (-1,1):
            xx = x+s*.53
            box('Postal Doors',glass,(xx,-2.663,2.54),(.876,.046,1.19),.03)
            box('Postal Doors',slat,(xx,-2.671,1.40),(.89,.049,.68),.026)
            for k in range(3):
                box('Postal Doors',deep,(xx,-2.705,2.14+k*.358),(.89,.035,.042),.007)
            box('Postal Doors',gold,(x+s*.115,-2.711,1.91),(.065,.070,.20),.016)
    # Four piers leave three open arcaded bays.
    for x in (-8.51,-2.84,2.84,8.51):
        for z,w,h,mat in ((1.025,.72,.39,band),(1.27,.62,.17,trim),(2.78,.46,2.91,plaster),
                          (4.23,.62,.19,trim),(4.40,.76,.17,band)):
            box('Arcade and Stairs',mat,(x,-5.03,z),(w,w,h),.035)
    for x in (-5.675,0,5.675):
        spring = 4.37
        arch('Arcade and Stairs',trim,x,-5.31,-4.76,spring,2.47,.87,.245,22)
        # Curtain above the arches closes the end wall up to the veranda roof.
        outline = [(x+2.69*math.cos(t),spring+1.09*math.sin(t))
                   for t in [math.pi*j/20 for j in range(21)]]
        prism('Arcade and Stairs',plaster,outline+[(x-2.69,5.67),(x+2.69,5.67)],-5.21,-4.81)
        box('Arcade and Stairs',band,(x,-5.302,5.30),(.27,.091,.31),.027)
    box('Arcade and Stairs',trim,(0,-5.033,5.64),(17.48,.70,.21),.04)
    for s in (-1,1):
        box('Arcade and Stairs',plaster,(s*8.56,-3.69,5.36),(.42,2.87,.50),.039)
        box('Arcade and Stairs',band,(s*8.56,-3.00,2.66),(.39,.43,3.66),.04)

    # Hipped tile roof. Every slope has a simple solid and repeated shallow clay rolls.
    eave = [(-9.26,-5.73,5.91),(9.26,-5.73,5.91),(9.26,9.31,5.91),(-9.26,9.31,5.91)]
    ridge = [(-3.90,1.79,9.33),(3.90,1.79,9.33),(3.90,1.79,9.33),(-3.90,1.79,9.33)]
    for i in range(4):
        j = (i+1)%4
        a,b,c,d = map(Vector,(eave[i],eave[j],ridge[j],ridge[i]))
        top = [a,b,c] if c==d else [a,b,c,d]
        n = len(top)
        verts = top+[v-Vector((0,0,.17)) for v in top]
        faces = [tuple(range(n)),tuple(range(n,2*n))]+[(k,(k+1)%n,(k+1)%n+n,k+n) for k in range(n)]
        add('Hipped Clay Roof',tiled[0],verts,faces)
        beam('Hipped Clay Roof',tiled[2],a,b,.171,.229,.018)
        rod('Hipped Clay Roof',tiled[2],a,d,.144,10)
        for row in range(14):
            t0,t1 = row/14,(row+1.03)/14
            t1 = min(t1,.997)
            p,q = a.lerp(d,t0),b.lerp(c,t0)
            pp,qq = a.lerp(d,t1),b.lerp(c,t1)
            num = max(1,round((q-p).length/.255))
            for k in range(num):
                u = (k+.5)/num
                p0,p1 = p.lerp(q,u),pp.lerp(qq,u)
                p0.z += .052
                p1.z += .031
                rod('Hipped Clay Roof',tiled[(row*3+k*17+k*row)%3],p0,p1,.065,5,1.04)
    rod('Hipped Clay Roof',tiled[2],(-4.03,1.79,9.37),(4.03,1.79,9.37),.147,12)
    for x in (-2.64,2.64):
        box('Postal Sign and Box',gold,(x,-5.349,5.49),(.14,.49,.13),.019)
    box('Postal Sign and Box',indigo,(0,-5.599,5.49),(6.55,.135,.59),.052)
    sign('Postal Sign and Box',trim,'PEJABAT POS  /  BUKIT SAGA',(0,-5.681,5.491),6.13,.31)
    x,y = 6.22,-7.86
    lathe('Postal Sign and Box',granite,x,y,[(.238,.42),(.40,.42),(.48,.38)],16)
    lathe('Postal Sign and Box',red,x,y,[(.47,.34),(.61,.34),(.65,.29),(1.51,.29),(1.65,.35),(1.76,.35),
                                      (1.85,.27),(1.91,.075)],20)
    box('Postal Sign and Box',gold,(x,y-.296,1.461),(.393,.069,.154),.028)
    box('Postal Sign and Box',deep,(x,y-.337,1.461),(.317,.021,.060),.01)
    sign('Postal Sign and Box',trim,'POS',(x,y-.309,1.148),.22,.17)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
