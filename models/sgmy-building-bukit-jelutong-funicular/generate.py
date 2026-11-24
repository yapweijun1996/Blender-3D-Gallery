"""Bukit Jelutong | Lower Funicular Station — original procedural SG/MY streetscape asset.
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

def rod(section, mat, a, b, radius, n=10, taper=1):
    a, b = Vector(a), Vector(b)
    basis = (b-a).to_track_quat('Z','Y').to_matrix()
    verts = [p+basis @ Vector((rad*math.cos(TAU*j/n),rad*math.sin(TAU*j/n),0))
             for p,rad in ((a,radius),(b,radius*taper)) for j in range(n)]
    faces = [(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
    faces.extend((tuple(reversed(range(n))),tuple(range(n,2*n))))
    add(section, mat, verts, faces, [True]*n+[False,False])

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

def gable(section, mat, trim, x0, x1, y, e, ridge, pitch, gutter=True):
    """Standing seam gable spanning in Y, with its long ridge parallel to X."""
    for s in (-1,1):
        y0,y1 = y,y+s*pitch
        prism(section,mat,[(y0,ridge-.16),(y1,e-.16),(y1,e),(y0,ridge)],x0,x1,'X')
        count = math.ceil((x1-x0)/.41)
        for i in range(count):
            x = x0+(i+.5)*(x1-x0)/count
            beam(section,trim,(x,y0,ridge+.025),(x,y1,e+.025),.045,.048,.005)
        for x in (x0,x1):
            beam(section,trim,(x,y0,ridge+.04),(x,y1,e+.04),.12,.19,.012)
        if gutter:
            box(section,trim,((x0+x1)/2,y1,e-.08),(x1-x0+.14,.16,.23),.027)
    rod(section,trim,(x0-.065,y,ridge+.065),(x1+.065,y,ridge+.065),.085,10)

def rail(section, mat, a, b, height=1.03, spacing=1.2, mid=True):
    a,b = Vector(a),Vector(b)
    up = Vector((0,0,height))
    count = max(1,math.ceil((b-a).length/spacing))
    for j in range(count+1):
        v = a.lerp(b,j/count)
        rod(section,mat,v,v+up,.036,8)
    rod(section,mat,a+up,b+up,.047,10)
    if mid:
        rod(section,mat,a+.49*up,b+.49*up,.027,8)

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


SLUG = 'sgmy-building-bukit-jelutong-funicular'
TITLE = 'Bukit Jelutong | Lower Funicular Station'
ROLE = 'Penang-inspired lower funicular station with ascending track stub'
VIEW = (.77,-1,.49)
RESOLUTION = (1200,936)


def build():
    kerb = material('Hill granite','9c9a91')
    joint = material('Plaza joints','ad9e87')
    pavers = [material('Sand flagstone','d0bea1'),material('Pale stone flag','d9c9a9'),material('Grey stone flag','c8c0a8')]
    wall = material('Shell cream masonry','f1debb')
    pale = material('Terrazzo arch trim','e5c899')
    wood = material('Belian roof timber','765645')
    teal = material('Heritage bottle green','315c53')
    jade = material('Sage enamel','658a74')
    glass = material('Ticket booth glazing','335452',.28,.21)
    roof = material('Oxide red roofing','ae6b55')
    roofedge = material('Red oxide standing seams','c28566')
    base = material('Track bed concrete','a6a39a')
    dark = material('Dark rail foundations','414b48')
    steel = material('Drawn rail steel','809397',.34,.54)
    yellow = material('Platform ochre','e9b459')
    greens = [material('Hill garden olive','63814d'),material('Hill garden green','809357')]
    pavement('Station Ground',0,0,23.6,27.2,kerb,pavers,joint,1.40)
    for x in (-8.88,-3.96,9.97):
        shrub_row('Arrival Planting',pale,wood,greens,x,-10.44,.238,2.94,1.01)
    palm('Arrival Planting',wood,greens,-8.84,-10.42,.72,4.22,.6)

    # Lower concourse with a full-width awning, shuttered office and a separate queue opening.
    box('Ticket Hall',wall,(-5.66,-4.01,2.10),(8.52,7.88,3.75),.053)
    box('Ticket Hall',pale,(-5.66,-4.01,.51),(8.67,8.06,.45),.035)
    box('Ticket Hall',pale,(-5.66,-4.01,3.86),(8.69,8.06,.26),.034)
    gable('Ticket Hall Roof',roof,roofedge,-10.17,-1.13,-4.0,3.98,5.88,4.24)
    for x in (-10.10,-1.19):
        prism('Ticket Hall Roof',wall,[(-8.21,3.96),(.21,3.96),(-4.0,5.76)],x-.083,x+.083,'X')
        louvre('Ticket Hall Roof',pale,teal,jade,x,-4,4.63,1.62,.70,6,math.copysign(math.pi/2, x+5.66))
    for x in (-8.44,-6.04,-3.64):
        box('Ticket Windows',teal,(x,-8.013,2.22),(1.92,.22,1.77),.048)
        box('Ticket Windows',glass,(x,-8.144,2.29),(1.65,.068,1.41),.035)
        box('Ticket Windows',jade,(x,-8.210,2.49),(1.62,.046,.058),.012)
        box('Ticket Windows',wood,(x,-8.27,1.55),(1.84,.53,.112),.024)
    box('Ticket Windows',teal,(-6.05,-8.156,3.42),(5.65,.115,.33),.032)
    sign('Ticket Windows',wall,'K A U N T E R   T I K E T',(-6.05,-8.224,3.42),5.04,.18)
    for y in (-6.75,-4.10,-1.49):
        louvre('Ticket Windows',pale,teal,jade,-9.96,y,2.32,1.48,1.44,8,-math.pi/2)
    for x in (-9.8,-6.90,-4.0,-1.12,9.43):
        box('Arrival Veranda',teal,(x,-8.87,1.94),(.253,.271,3.39),.032)
        box('Arrival Veranda',pale,(x,-8.87,.54),(.388,.40,.56),.038)
    for x in (-5.67,4.13):
        box('Arrival Veranda',wood,(x,-8.79,3.54),(9.30,.26,.22),.024)
        prism('Arrival Veranda',jade,[(-9.58,3.53),(-7.86,3.92),(-7.86,4.07),(-9.58,3.68)],x-4.68,x+4.68,'X')
        box('Arrival Veranda',teal,(x,-9.58,3.61),(9.40,.17,.24),.031)
    box('Station Signs',pale,(4.16,-8.72,4.16),(8.64,.26,1.01),.062)
    box('Station Signs',teal,(4.16,-8.865,4.16),(8.43,.06,.82),.046)
    sign('Station Signs',wall,'STESEN BUKIT JELUTONG',(4.16,-8.90,4.337),7.9,.279)
    sign('Station Signs',yellow,'F U N I C U L A R   /   L O W E R   S T A T I O N',(4.16,-8.90,4.01),7.4,.157)

    y0,y1 = -6.28,13.25
    def track_z(y):
        return .48+(y-y0)*.237
    # Continuous exposed rail stubs and stepped side loading platforms.
    prism('Inclined Track Bed',base,[(y0,.237),(y1,.237),(y1,track_z(y1)),(y0,track_z(y0))],-.962,9.045,'X')
    box('Inclined Track Bed',base,(9.11,3.49,.394),(.237,19.35,.31),.029)
    for j in range(8):
        y = -4.91+2.36*j
        h = track_z(y)+(.52 if y<11.8 else -.30)
        box('Inclined Track Bed',base,(9.13,y,(h+.394)/2),(.26,.33,h-.394),.031)
    for x in (1.90,5.97):
        prism('Inclined Track Bed',dark,[(y0,track_z(y0)-.021),(y1,track_z(y1)-.021),
             (y1,track_z(y1)+.086),(y0,track_z(y0)+.086)],x-.98,x+.98,'X')
        for k in range(35):
            y = y0+.27+k*.561
            box('Rails and Cable Chairs',wood,(x,y,track_z(y)+.111),(1.82,.19,.14),.023,
                basis=Matrix.Rotation(.232,3,'X'))
            if k%2==0:
                rod('Rails and Cable Chairs',steel,(x-.095,y,track_z(y)+.17),(x+.095,y,track_z(y)+.17),.069,10)
        for xx in (x-.59,x+.59):
            beam('Rails and Cable Chairs',steel,(xx,y0,track_z(y0)+.189),(xx,y1,track_z(y1)+.189),.10,.12,.013)
        rod('Rails and Cable Chairs',dark,(x,y0,track_z(y0)+.218),(x,y1,track_z(y1)+.218),.027,8)
        box('Rails and Cable Chairs',teal,(x,y0+.09,track_z(y0)+.40),(1.63,.23,.47),.041)
        box('Rails and Cable Chairs',yellow,(x,y0-.042,track_z(y0)+.41),(1.49,.043,.15),.021)
    for x,w in ((-.28,1.41),(3.92,1.62),(8.12,2.0)):
        # Flat shallow treads, not a decorative line drawn on the slope.
        for i in range(24):
            a = y0+.766*i
            b = a+.766
            z = track_z(b)+.56
            block('Stepped Boarding Platforms',pale,x-w/2,x+w/2,a,b,.24,z,.015)
            box('Stepped Boarding Platforms',wall,(x,(a+b)/2,z+.026),(w-.027,b-a-.018,.052),.011)
            for xx in (x-w/2+.106,x+w/2-.106):
                box('Stepped Boarding Platforms',yellow,(xx,(a+b)/2,z+.062),(.086,b-a-.032,.023),.004)
    for x,w in ((-.28,1.39),(3.92,1.60),(8.12,1.98)):
        steps('Stepped Boarding Platforms',pale,jade,x,y0-1.56,w,4,.391,.244,.24)
    rail('Platform Guardrail',jade,(9.15,-6.3,1.18),(9.15,11.98,track_z(11.98)+.63),1.08,1.26)
    rail('Platform Guardrail',jade,(-1.07,.03,track_z(.03)+.64),(-1.07,11.98,track_z(11.98)+.64),1.08,1.26)

    # A raised zinc platform canopy follows the incline and stops before the rear track stub.
    for y in (-6.48,-2.76,1.19,5.14,8.78):
        z = track_z(y)
        for x in (-.90,8.96):
            box('Inclined Shelter Frame',teal,(x,y,z+2.28),(.31,.31,3.62),.029)
            box('Inclined Shelter Frame',pale,(x,y,z+.70),(.43,.43,.44),.034)
        for x in (-.85,8.91):
            beam('Inclined Shelter Frame',wood,(x,y,z+3.91),(4.02,y,z+5.68),.197,.202,.017)
        box('Inclined Shelter Frame',teal,(4.02,y,z+3.92),(9.98,.218,.23),.025)
    start,end = -7.05,9.18
    for x_edge in (-1.41,9.42):
        xy = [(4.02,start),(x_edge,start),(x_edge,end),(4.02,end)]
        top = [(x,y,track_z(y)+(5.91 if x==4.02 else 4.14)) for x,y in xy]
        add('Inclined Shelter Roof',jade,top+[(x,y,z-.17) for x,y,z in top],
            [(0,1,2,3),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
        for j in range(38):
            y = start+(j+.5)*(end-start)/38
            beam('Inclined Shelter Roof',pale,(4.02,y,track_z(y)+5.937),(x_edge,y,track_z(y)+4.167),.047,.049,.006)
        beam('Inclined Shelter Roof',teal,top[1],top[2],.193,.224,.024)
        for i,j in ((0,1),(3,2)):
            beam('Inclined Shelter Roof',teal,top[i],top[j],.127,.185,.018)
    rod('Inclined Shelter Roof',pale,(4.02,start,track_z(start)+5.95),(4.02,end,track_z(end)+5.95),.081,10)
    for x in (.92,6.91):
        box('Station Signs',teal,(x,-6.735,2.75),(2.34,.12,.42),.037)
        sign('Station Signs',wall,'PLATFORM 1' if x<2 else 'PLATFORM 2',(x,-6.806,2.749),2.13,.208)
        for dx in (-1.03,1.03):
            path('Station Signs',steel,[(x+dx,-6.71,2.9),(x+dx,-6.71,4.26),
                                        (x+dx,-6.48,4.37)],.021,8)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
