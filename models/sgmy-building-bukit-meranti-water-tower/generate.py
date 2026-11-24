"""Bukit Meranti | District Water Tower — original procedural SG/MY streetscape asset.
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


SLUG = 'sgmy-building-bukit-meranti-water-tower'
TITLE = 'Bukit Meranti | District Water Tower'
ROLE = 'Tropical municipal elevated tank and pump enclosure'
VIEW = (.63,-1,.41)
RESOLUTION = (910,1100)


def build():
    curb = material('Cement kerb','9c998c')
    site = material('Rain washed pavement','b4b5a7')
    dark = material('Deep sea green service steel','2d5453')
    cream = material('Ivory structural concrete','e6d8b6')
    muted = material('Warm footing concrete','c1b292')
    teal = material('Water tank jade','53948f')
    band = material('White tank lettering','f9eccb')
    seam = material('Sealed panel seams','6ca7a0')
    ochre = material('Warning yellow enamel','daad57')
    glass = material('Smoked service glazing','3c5d5a',.30,.16)
    soil = material('Laterite fill','8c7d63')
    levels = [material('Berm grass','7f8e62'),material('Myrtle leaf','55724c'),material('Rambai leaf','729259')]
    box('Service Lot',curb,(0,0,.15),(18.5,16.5,.30),.071)
    box('Service Lot',site,(0,0,.314),(18.36,16.36,.068),.032)
    for x in (-5.54,5.54):
        box('Service Lot',soil,(x,-2.36,.357),(5.81,10.68,.025),.015)
        box('Service Lot',levels[0],(x,-2.36,.384),(5.77,10.64,.047),.018)
    for x in (-4.95,4.95):
        shrub_row('Service Lot',muted,soil,levels[1:],x,-6.43,.407,4.30,1.17)
    for x in (-8.68,8.68):
        for y in (-7.5,-3.76,0,3.76,7.5):
            box('Yard Fence',muted,(x,y,.577),(.36,.36,.48),.038)
            box('Yard Fence',dark,(x,y,1.279),(.112,.112,1.78),.018)
        for z in (1.070,1.98):
            box('Yard Fence',dark,(x,0,z),(.091,15,.108),.017)
        for j in range(50):
            box('Yard Fence',teal,(x,(j-24.5)*.30,1.515),(.047,.054,1.21),.005)
    for s in (-1,1):
        x = s*4.90
        for z in (1.07,1.98):
            box('Yard Fence',dark,(x,-7.52,z),(7.59,.11,.106),.014)
        for j in range(25):
            box('Yard Fence',teal,(s*(1.27+j*.30),-7.52,1.52),(.05,.048,1.21),.005)
        box('Yard Fence',dark,(s*1.14,-7.52,1.39),(.14,.16,1.85),.021)

    # Tapered concrete legs form a hexagon around visible supply and overflow risers.
    def point(radius, k, z):
        a = TAU*(k/6)+math.pi/6
        return (radius*math.cos(a),1.09+radius*math.sin(a),z)
    for i in range(6):
        a,b = point(4.39,i,.72),point(3.27,i,20.66)
        x,y,_ = a
        box('Concrete Pilotis',muted,(x,y,.54),(1.60,1.60,.39),.071,yaw=i*TAU/6)
        beam('Concrete Pilotis',cream,a,b,.81,.81,.064)
        for j,z in enumerate((6.65,13.26,19.42)):
            t = (z-.72)/(20.66-.72)
            r = 4.39+(3.27-4.39)*t
            beam('Pilotis Ring Beams',muted,point(r,i,z),point(r,i+1,z),.61,.63,.04)
            if j<2:
                beam('Pilotis Ring Beams',cream,point(r+.062,i,z-.88),point(r-.071,i+1,z+.77),.36,.36,.028)
    for x,mat,r in ((-.49,teal,.23),(.22,dark,.19),(.74,muted,.117)):
        path('Water Services',mat,[(x,4.35,.36),(x,2.30,.46),(x,1.68,.94),
                                  (x,1.68,19.23),(x,1.07,20.92)],r,14)
        for z in (2.41,6.41,12.91,19.03):
            lathe('Water Services',mat,x,1.68,[(z-.11,r+.073),(z+.11,r+.073)],12)
    for z,r in ((6.67,4.06),(13.29,3.69),(19.41,3.34)):
        box('Water Services',dark,(0,1.46,z),(2.03,.68,.133),.014)
        beam('Water Services',dark,point(r,0,z),(0,1.46,z),.14,.16,.018)
        beam('Water Services',dark,point(r,2,z),(0,1.46,z),.14,.16,.018)
    # The caged ladder inclines with the front concrete leg, leaving room for boots and brackets.
    x = .04
    def ladder_y(z):
        return -3.90+(z-.57)*.056
    for z,r in ((6.67,4.06),(13.29,3.69),(19.41,3.34)):
        beam('Caged Ladder',dark,point(r,4,z),(x,ladder_y(z),z),.129,.126,.012)
    for dx in (-.21,.21):
        rod('Caged Ladder',dark,(x+dx,ladder_y(.57),.57),(x+dx,ladder_y(20.58),20.58),.038,8)
    for z in [.97+.31*j for j in range(63)]:
        y = ladder_y(z)
        rod('Caged Ladder',dark,(x-.21,y,z),(x+.21,y,z),.025,8)
    for z in [2.28+1.27*i for i in range(14)]:
        y = ladder_y(z)
        pts = [(x+.40*math.cos(a),y-.22-.45*math.sin(a),z)
               for a in [math.pi*k/12 for k in range(13)]]
        path('Caged Ladder',teal,[(x+.21,y,z)]+pts+[(x-.21,y,z)],.027,8)
    for i in range(5):
        a = .23+(math.pi-.46)*i/4
        xx,dy = x+.40*math.cos(a),-.22-.45*math.sin(a)
        rod('Caged Ladder',teal,(xx,ladder_y(2.28)+dy,2.28),(xx,ladder_y(18.79)+dy,18.79),.020,8)

    # Ribbed tank bowl with a raised inspection curb and guardrail around the crown.
    cy = 1.09
    lathe('Tank Bowl',cream,0,cy,[(19.79,2.65),(20.17,3.37),(20.60,4.04),(21.29,4.81),
                                 (21.94,5.35),(22.31,5.63),(22.61,5.72)],64)
    lathe('Tank Bowl',teal,0,cy,[(22.59,5.719),(22.75,5.83),(25.72,5.83),(25.89,5.75)],64)
    lathe('Tank Bowl',cream,0,cy,[(25.86,5.79),(26.12,5.79),(26.18,5.49),(26.35,5.19),
                                 (26.63,3.86),(26.80,2.14),(26.87,1.22)],64)
    for z in (22.86,25.61):
        lathe('Tank Seams',seam,0,cy,[(z-.067,5.84),(z+.067,5.84)],64)
    for i in range(30):
        a = TAU*i/30
        x,y = 5.83*math.cos(a),cy+5.83*math.sin(a)
        rod('Tank Seams',seam,(x,y,22.83),(x,y,25.66),.028,8)
    for z in (21.74,22.55):
        r = 5.21 if z<22 else 5.72
        lathe('Tank Seams',muted,0,cy,[(z-.082,r),(z+.082,r+.115)],64)
    for i in range(20):
        a,b = TAU*i/20,TAU*(i+1)/20
        aa = (5.31*math.cos(a),cy+5.31*math.sin(a),26.35)
        bb = (5.31*math.cos(b),cy+5.31*math.sin(b),26.35)
        rail('Crown Walk',dark,aa,bb,.87,3.0,False)
    lathe('Crown Walk',dark,0,cy,[(26.84,.69),(26.98,.71),(27.11,.66)],24)
    rod('Crown Walk',dark,(0,cy,27.1),(0,cy,28.08),.048,10)
    rod('Crown Walk',ochre,(0,cy,27.96),(0,cy,28.13),.069,10)
    a = .19
    cx,yy = 5.79*math.sin(a),cy-5.79*math.cos(a)
    box('Tank Nameplate',dark,(cx,yy,24.25),(4.75,.14,1.45),.082,yaw=a)
    for z,text,w,h,mat in ((24.57,'BUKIT MERANTI',4.29,.434,band),(24.04,'TANGKI AIR  /  07',3.52,.297,band)):
        sign('Tank Nameplate',mat,text,(cx+.079*math.sin(a),yy-.079*math.cos(a),z),w,h,yaw=a)

    # Separate the utility shed from the loads of the tower frame.
    box('Pump Enclosure',cream,(6.43,4.71,1.49),(3.50,3.87,2.30),.064)
    box('Pump Enclosure',teal,(6.43,4.71,2.72),(3.74,4.12,.17),.041)
    louvre('Pump Enclosure',muted,glass,teal,8.20,4.71,1.72,2.57,1.34,8,math.pi/2)
    box('Pump Enclosure',dark,(6.70,2.749,1.29),(1.36,.127,1.88),.028)
    box('Pump Enclosure',ochre,(6.70,2.674,1.71),(.27,.022,.19),.015)
    box('Pump Enclosure',teal,(6.43,2.736,2.35),(3.09,.105,.432),.037)
    sign('Pump Enclosure',band,'RUMAH PAM',(6.43,2.674,2.35),2.56,.206)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
