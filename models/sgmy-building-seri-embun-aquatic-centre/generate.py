"""Seri Embun | Public Aquatic Centre — original procedural SG/MY streetscape asset.
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
    root['pivot'] = 'Ground centre'
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

def round_ring(x, y, z, w, d, r, n=5):
    return [(x+cx+r*math.cos(a),y+cy+r*math.sin(a),z)
            for i,(cx,cy) in enumerate(((w/2-r,d/2-r),(-w/2+r,d/2-r),
                                        (-w/2+r,-d/2+r),(w/2-r,-d/2+r)))
            for a in [(i+j/n)*math.pi/2 for j in range(n+1)]]

def rounded(section, mat, x, y, w, d, lower, upper, radius):
    loft(section, mat, [round_ring(x,y,z,w,d,radius) for z in (lower,upper)])

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


SLUG = 'sgmy-building-seri-embun-aquatic-centre'
TITLE = 'Seri Embun | Public Aquatic Centre'
ROLE = 'Open-air municipal 25 m pool with shaded grandstand'
VIEW = (.50,-1,.64)
RESOLUTION = (1210,852)


def build():
    base = material('Pool slab concrete','a5a89f')
    joint = material('Deck joints','a4a38e')
    pavers = [material('Warm anti slip tile','dbd0b4'),material('Cream anti slip tile','e8dbbb'),material('Sand anti slip tile','cbc3aa')]
    white = material('Shell coping','f1e7cb')
    coral = material('Oxide brick','b9745e')
    sand = material('Shaded concrete','b9ac93')
    blue = material('Dark turquoise wayfinding','326e74')
    green = material('Celadon steelwork','5f9692')
    seam = material('Light monitor seams','8fb6a9')
    water = material('Swimming pool aqua','54c3c3',.26,.13)
    marks = material('Submerged cyan lane marking','3b9da7',.44,.10)
    tile = material('Glazed turquoise pool edge','459c9d',.36,.12)
    reds = material('Coral lane floats','c16f5c')
    yellow = material('Ochre lane floats','dfb66a')
    steel = material('Satin rails','a2b1ad',.33,.47)
    glass = material('Petrol pavilion glazing','305457',.28,.2)
    bark = material('Palm bark','8c7c64')
    greens = [material('Poolside palm green','65854e'),material('Poolside sunlit green','82935a')]
    pavement('Facility Deck',0,0,35.2,25.4,base,pavers,joint,1.33,.64)

    # Pool surface is recessed visually below an actual ring of coping and blue tile.
    yc = -1.46
    outer = round_ring(1.56,yc,.70,26.14,12.63,.26,4)
    inner = round_ring(1.56,yc,.70,25.00,11.82,.16,4)
    # The surrounding flagstones are masked by a thin recessed liner sitting above the plinth.
    rounded('Lined Pool',tile,1.56,yc,26.14,12.63,.689,.870,.25)
    rounded('Lined Pool',water,1.56,yc,25,11.82,.86,.902,.158)
    ring('Lined Pool',tile,[(x,y,.855) for x,y,_ in outer],[(x,y,.855) for x,y,_ in inner],.179)
    for z,w,d in ((.946,26.20,12.71),(1.026,26.23,12.74)):
        ring('Lined Pool',white,round_ring(1.56,yc,z,w,d,.29,4),
             round_ring(1.56,yc,z,25.11,11.95,.216,4),.045)
    for lane in range(6):
        y = yc+(lane-2.5)*1.866
        box('Pool Markings',marks,(1.56,y,.9024),(22.14,.142,.006),.004)
        for x in (-9.31,12.43):
            box('Pool Markings',marks,(x,y,.9024),(.149,.73,.006),.004)
    for j in range(5):
        y = yc+(j-2)*1.866
        rod('Course Lane Ropes',blue,(-10.88,y,.968),(13.98,y,.968),.023,8)
        for i in range(78):
            x = -10.79+i*.319
            mat = reds if abs(x-1.56)>9.60 else (yellow if i%2 else white)
            rod('Course Lane Ropes',mat,(x-.092,y,.976),(x+.092,y,.976),.072,10)
    for j in range(6):
        y = yc+(j-2.5)*1.866
        x = 14.46
        box('Starting Blocks',steel,(x,y,1.19),(.27,.30,.47),.031)
        box('Starting Blocks',blue,(x-.14,y,1.434),(.62,.53,.105),.026)
        box('Starting Blocks',white,(x-.14,y,1.49),(.51,.433,.024),.012)
        sign('Starting Blocks',blue,str(j+1),(x-.145,y,1.507),.28,.22,flat=True)
    for x in (-9.55,12.33):
        for dx in (-.258,.258):
            path('Safety Hardware',steel,[(x+dx,-7.76,1.07),(x+dx,-7.72,1.73),(x+dx,-7.60,1.94),
                (x+dx,-7.38,1.97),(x+dx,-7.13,1.86),(x+dx,-6.97,1.56),(x+dx,-6.97,.904)],.035,9)
        for h in (1.04,1.20):
            rod('Safety Hardware',steel,(x-.274,-6.96,h),(x+.274,-6.96,h),.028,10)
    for x in (-5.4,4.6,10.6):
        box('Safety Hardware',white,(x,-8.40,.717),(1.34,.46,.028),.017)
        sign('Safety Hardware',blue,'1.2 M',(x,-8.40,.734),1.16,.23,flat=True)

    # Raked stands with an articulated, ventilated steel shade canopy.
    for i in range(5):
        y = 6.59+.81*i
        z = .70+.434*(i+1)
        for bay,(a,b) in enumerate(((-10.59,-3.16),(-2.26,4.80),(5.70,13.13))):
            block('Grandstand',sand,a,b,y-.412,y+.412,.70,z,.026)
            x = (bay-1)*7.96+1.27
            box('Grandstand',blue if bay!=1 else green,(x,y+.156,z+.081),(7.05,.466,.15),.027)
            for k in range(15):
                xx = x+(k-7)*.459
                box('Grandstand',green if bay!=1 else blue,(xx,y+.13,z+.162),(.421,.425,.048),.014)
    for x in (-11.05,-2.71,5.25,13.59):
        steps('Grandstand',sand,white,x,6.17,.91,10,.406,.217,.701)
    rail('Grandstand',steel,(-11.38,10.20,2.88),(13.91,10.20,2.88),.98,1.47)
    for x in (-10.67,-4.71,1.25,7.21,13.17):
        box('Grandstand Canopy',coral,(x,10.88,2.87),(.34,.34,4.34),.039)
        beam('Grandstand Canopy',coral,(x,10.83,3.41),(x,7.65,4.94),.235,.246,.023)
    box('Grandstand Canopy',coral,(1.29,10.87,4.98),(25.71,.23,.17),.022)
    profile = [(4.93,5.55),(6.52,5.22),(8.44,5.05),(10.46,5.10),(11.58,5.33)]
    outline = [(y,z-.173) for y,z in profile]+profile[::-1]
    prism('Grandstand Canopy',green,outline,-11.66,14.23,'X')
    for i in range(66):
        x = -11.51+.391*i
        path('Grandstand Canopy',seam,[(x,y,z+.022) for y,z in profile],.024,6)
    for x in (-11.67,14.24):
        path('Grandstand Canopy',coral,[(x,y,z-.04) for y,z in profile],.087,8)
    for y,z in (profile[0],profile[-1]):
        box('Grandstand Canopy',coral,(1.29,y,z-.071),(26.09,.145,.27),.026)

    # Tiled entrance and compact changing pavilion kept low to leave the pool legible.
    box('Changing Pavilion',coral,(-14.2,-.24,2.02),(4.65,8.25,2.69),.048)
    box('Changing Pavilion',white,(-14.2,-.24,3.43),(4.89,8.46,.272),.056)
    for y in (-2.95,-.32,2.35):
        louvre('Changing Pavilion',white,glass,green,-11.855,y,2.66,1.78,1.0,7,math.pi/2)
    box('Changing Pavilion',blue,(-14.20,-4.42,1.89),(2.30,.185,2.39),.037)
    for j in range(12):
        box('Changing Pavilion',green,(-15.22+j*.19,-4.528,2.03),(.063,.095,1.95),.007)
    for x in (-13.94,13.45):
        shrub_row('Pool Planting',white,joint,greens,x,-10.56,.70,3.56,1.28)
        palm('Pool Planting',bark,greens,x,-10.56,1.18,3.86,x*.118)
    for x in (-3.21,3.20):
        box('Facility Name',coral,(x,-11.14,1.51),(.23,.28,1.65),.027)
    box('Facility Name',blue,(0,-11.25,2.20),(6.84,.28,.87),.054)
    sign('Facility Name',white,'KOLAM RENANG SERI EMBUN',(0,-11.399,2.33),6.19,.273)
    sign('Facility Name',yellow,'A Q U A T I C   C E N T R E',(0,-11.399,2.03),5.31,.173)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
