"""Teluk Rumbia | Island Ferry Terminal — original procedural SG/MY streetscape asset.
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


SLUG = 'sgmy-building-teluk-rumbia-ferry-terminal'
TITLE = 'Teluk Rumbia | Island Ferry Terminal'
ROLE = 'Small Malay coastal ferry terminal with elevated access pier'
VIEW = (.92,-1,.55)
RESOLUTION = (1200,950)


def build():
    stone = material('Salt washed stone','9a9c8d')
    joint = material('Jetty approach joints','a49c89')
    pavers = [material('Coastal sandstone','ccbea3'),material('Pale approach flag','dfccac'),material('Damp approach flag','bdaf99')]
    wall = material('Cream fibre cement','f1dbb1')
    timber = material('Oiled belian','876348')
    pale = material('Sun bleached belian deck','af8a67')
    indigo = material('Petrol blue fascias','315f65')
    slat = material('Turquoise timber slats','51918a')
    roof = material('Blue green painted zinc','6a9690',.62,.13)
    seam = material('Zinc ribs','93b6ab',.57,.15)
    glass = material('Tinted sea green glass','33575b',.25,.24)
    metal = material('Marine galvanised steel','a8b3ad',.42,.42)
    dark = material('Mooring hardware','36474a')
    yellow = material('Jetty safety ochre','edb955')
    greens = [material('Fan palm leaf','567d4a'),material('Palm new growth','82995a')]
    pavement('Shore Approach',0,-6.18,24.5,16.4,stone,pavers,joint,1.2,.58)
    box('Shore Approach',pavers[1],(0,-3.72,.77),(19.38,12.18,.26),.038)
    steps('Shore Approach',stone,wall,0,-10.37,8.81,2,.283,.132,.638)
    for x in (-10.32,10.32):
        shrub_row('Shore Planting',wall,timber,greens,x,-11.36,.64,2.57,1.19)
        palm('Shore Planting',timber,greens,x,-11.31,1.12,3.65,x*.4)
    # Side boarding deck is visible beside the terminal, and the finger pier projects beyond it.
    for x0,x1,y0,y1,z in ((-9.54,9.54,2.17,6.47,.90),(4.90,9.54,6.46,15.35,.90)):
        count = max(1,round((y1-y0)/.238))
        for j in range(count):
            y = y0+(j+.5)*(y1-y0)/count
            box('Boardwalk and Piles',(pale,timber,pale,pale)[j%4],((x0+x1)/2,y,z-.058),
                (x1-x0,(y1-y0)/count-.012,.132),.011)
        for x in (x0+.17,x1-.17):
            box('Boardwalk and Piles',timber,(x,(y0+y1)/2,z-.24),(.23,y1-y0,.34),.035)
        for i in range(max(2,round((y1-y0)/2.37))):
            y = y0+.37+i*(y1-y0-.74)/(max(2,round((y1-y0)/2.37))-1)
            box('Boardwalk and Piles',timber,((x0+x1)/2,y,z-.24),(x1-x0,.246,.32),.032)
            for x in (x0+.27,x1-.27):
                lathe('Boardwalk and Piles',stone,x,y,[(0,.19),(.77,.19)],10)
    rail('Jetty Safety',metal,(9.49,2.08,.90),(9.49,15.32,.90),1.02,1.49)
    rail('Jetty Safety',metal,(4.99,6.50,.90),(4.99,12.06,.90),1.02,1.39)
    rail('Jetty Safety',metal,(-9.48,2.08,.90),(-9.48,6.40,.90),1.02,1.49)
    rail('Jetty Safety',metal,(-9.48,6.40,.90),(4.98,6.40,.90),1.02,1.58)
    for y in (12.48,14.96):
        box('Jetty Safety',dark,(4.89,y,.49),(.27,1.52,.30),.08)
        lathe('Jetty Safety',dark,5.15,y,[(.90,.17),(.98,.17),(1.01,.097),(1.148,.097),
                                        (1.175,.138),(1.223,.108)],12)
    for y in (12.46,14.95):
        box('Jetty Safety',yellow,(5.31,y,.912),(.66,.13,.019))
    for i in range(13):
        box('Jetty Safety',yellow,(5.33,12.76+i*.15,.912),(.092,.091,.019))

    # Three communicating public bays. Timber posts and screened gable ends keep the air moving.
    for i,x in enumerate((-6.60,0,6.60)):
        w = (5.88,6.70,5.88)[i]
        e,ridge = ((4.12,5.96),(4.78,6.90),(4.12,5.96))[i]
        for side in (-1,1):
            xx = x+side*(w/2-.24)
            for y in (-8.74,-4.23,.10,3.82):
                box('Terminal Timber Frame',timber,(xx,y,(e+.84)/2),(.26,.30,e-.84),.024)
                box('Terminal Timber Frame',wall,(xx,y,1.13),(.41,.43,.46),.037)
            box('Terminal Timber Frame',indigo,(xx,-2.49,e-.26),(.246,13.44,.34),.033)
        for side in (-1,1):
            xx = x+side*w/2
            prism('Terminal Zinc Roof',roof,[(x,ridge-.16),(xx,e-.16),(xx,e),(x,ridge)],-9.12,4.44)
            for j in range(34):
                y = -8.98+j*.395
                beam('Terminal Zinc Roof',seam,(x,y,ridge+.024),(xx,y,e+.024),.044,.047,.008)
            for y in (-9.13,4.45):
                beam('Terminal Zinc Roof',indigo,(x,y,ridge-.02),(xx,y,e-.02),.126,.173,.02)
            box('Terminal Zinc Roof',indigo,(xx,-2.34,e-.122),(.182,13.87,.23),.024)
        rod('Terminal Zinc Roof',seam,(x,-9.17,ridge+.047),(x,4.49,ridge+.047),.087,10)
        for y in (-8.96,4.16):
            prism('Battened Gable Screens',indigo,[(x-w/2+.22,e-.094),(x+w/2-.22,e-.094),(x,ridge-.16)],y-.067,y+.067)
            for j in range(16):
                xx = x+(j-7.5)*(w-.54)/16
                h = (ridge-e-.17)*(1-abs(xx-x)/(w/2-.12))
                box('Battened Gable Screens',slat,(xx,y-.080,e-.09+h/2),(.089,.19,h),.01)
            box('Battened Gable Screens',wall,(x,y,e-.12),(w-.2,.199,.199),.023)
        for y in (-7.79,-2.28,3.08):
            box('Terminal Timber Frame',wall,(x,y,e-.55),(w-.82,.115,.105),.026)

    for s in (-1,1):
        box('Terminal Zinc Roof',roof,(s*3.57,-2.35,3.98),(.68,13.50,.18),.026)
        path('Terminal Zinc Roof',indigo,[(s*3.55,-8.95,3.98),(s*3.55,-8.89,3.70),
             (s*3.67,-8.83,3.55),(s*3.67,-8.83,1.08)],.071,10)

    # Ticket office to the left, louvred waiting shelter to the right, open passage between.
    box('Ticket Office and Seating',wall,(-6.61,-4.91,2.24),(5.02,5.24,2.71),.042)
    for x in (-7.93,-5.28):
        box('Ticket Office and Seating',indigo,(x,-7.61,2.25),(2.22,.16,1.67),.042)
        box('Ticket Office and Seating',glass,(x,-7.708,2.24),(2.01,.073,1.30),.031)
        box('Ticket Office and Seating',timber,(x,-7.80,1.79),(2.15,.46,.09),.018)
    louvre('Ticket Office and Seating',indigo,glass,slat,-9.15,-4.52,2.39,2.14,1.42,8,-math.pi/2)
    box('Terminal Lettering',indigo,(-6.61,-7.69,3.37),(4.10,.17,.27),.023)
    sign('Terminal Lettering',wall,'TIKET FERI',(-6.61,-7.789,3.37),3.20,.187)
    for x in (4.16,8.89):
        for y in (-4.76,-1.15,2.46):
            for j in range(11):
                box('Waiting Screens',slat,(x,y+(j-5)*.257,2.43),(.124,.133,2.20),.014)
            box('Waiting Screens',indigo,(x,y,3.53),(.15,2.87,.14),.021)
            box('Waiting Screens',indigo,(x,y,1.34),(.16,2.87,.15),.019)
    for y in (-4.82,-1.15,2.44):
        for x in (4.94,8.02):
            box('Ticket Office and Seating',timber,(x,y,1.35),(.44,2.42,.135),.023)
            box('Ticket Office and Seating',pale,(x,y,1.65),(.13,2.44,.23),.021)
            for dy in (-.83,.83):
                box('Ticket Office and Seating',indigo,(x,y+dy,1.14),(.32,.13,.48),.016)
    box('Terminal Lettering',wall,(0,-9.042,4.17),(6.12,.19,.85),.048)
    box('Terminal Lettering',indigo,(0,-9.155,4.17),(5.96,.063,.69),.035)
    sign('Terminal Lettering',wall,'TERMINAL FERI',(0,-9.192,4.31),4.58,.198)
    sign('Terminal Lettering',yellow,'T E L U K   R U M B I A',(0,-9.192,4.047),4.85,.159)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
