"""Swallowtail Hall — original procedural SG/MY streetscape asset.
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

SLUG = 'sgmy-building-swallowtail-temple'
TITLE = 'Swallowtail Hall | Straits Chinese Temple'


def sweep_roof(sec, mats, jade, ochre, timber, ridge, cy, w, d, eave, rise, upsweep):
    half = w/2
    def base(x,t):
        up = max(0,(abs(x)/half-.62)/.38)**2
        return eave + rise*(1-t)**1.57 + upsweep*up*(.74+.26*t)
    n,m = 32,12
    xs = [-half+w*i/n for i in range(n+1)]
    for side in (-1,1):
        for k in range(m):
            a,b = k/m,(k+1)/m
            for j,(x0,x1) in enumerate(zip(xs,xs[1:])):
                top = [(x,cy+side*d*t,base(x,t)) for x,t in ((x0,a),(x1,a),(x1,b),(x0,b))]
                add(sec,mats[(j*11+j*k+k*7+j//4)%len(mats)],top,[(0,1,2,3)] if side>0 else [(3,2,1,0)])
                if k in (0,m-1) or j in (0,n-1):
                    for i,q,ok in ((0,1,k==0),(1,2,j==n-1),(2,3,k==m-1),(3,0,j==0)):
                        if ok:
                            u,v = top[i],top[q]
                            add(sec,timber,[u,v,(v[0],v[1],v[2]-.19),(u[0],u[1],u[2]-.19)],[(0,1,2,3)])
        # Continuous low rolls give the clay roof its rhythmic highlights.
        for j in range(46):
            x = -half+w*(j+.5)/46
            pts = [(x,cy+side*d*i/11,base(x,i/11)+.021+.007*(i%2)) for i in range(12)]
            for i,(a,b) in enumerate(zip(pts,pts[1:])):
                rod(sec,mats[(j*3+i*2+1)%len(mats)],a,b,.045,6,1.052)
            end = pts[-1]
            rod(sec,jade,(end[0],end[1]-side*.057,end[2]-.002),(end[0],end[1]+side*.12,end[2]-.002),.060,8)
        edges = [(x,cy+side*d,base(x,1)-.116) for x in xs[::2]]
        for a,b in zip(edges,edges[1:]):
            beam(sec,timber,a,b,.153,.17,.019)
            rod(sec,jade,(a[0],a[1]+side*.081,a[2]+.095),(b[0],b[1]+side*.081,b[2]+.095),.054,8)
        for x in (-half,half):
            for i in range(12):
                a,b = i/12,(i+1)/12
                rod(sec,jade,(x,cy+side*d*a,base(x,a)+.048),(x,cy+side*d*b,base(x,b)+.048),.074,8)
    z = eave+rise
    # Southern Chinese swallowtail ridge: the middle stays low while the two ends fork.
    profile = [(-half-.42,z+upsweep+.62),(-half-.04,z+upsweep+.20),(-half+.44,z+upsweep*.65+.05),
               (-half*.6,z+.28),(-half*.34,z+.23),(0,z+.225)]
    points = profile+ [(-x,t) for x,t in reversed(profile[:-1])]
    shape = [(x,t+.13) for x,t in points] + [(x,t-.13) for x,t in reversed(points)]
    prism(ridge,jade,shape,cy-.14,cy+.14)
    for (x,zq),(xx,zz) in zip(points,points[1:]):
        rod(ridge,ochre,(x,cy-.126,zq+.095),(xx,cy-.126,zz+.095),.045,8)
        rod(ridge,ochre,(x,cy+.126,zq+.095),(xx,cy+.126,zz+.095),.045,8)
    for s in (-1,1):
        prism(ridge,jade,[(s*(half-.29),z+upsweep*.72),(s*(half+.53),z+upsweep+.17),
                          (s*(half+.29),z+upsweep-.07),(s*(half-.5),z+upsweep*.55-.14)],cy-.108,cy+.108)


def lantern(sec, shade, ribs, x,y,z,r):
    profile = [(z-r*.8,r*.42),(z-r*.57,r*.8),(z-r*.30,r*.974),(z,r),
               (z+r*.36,r*.918),(z+r*.63,r*.715),(z+r*.8,r*.40)]
    lathe(sec,shade,x,y,profile,16)
    for k in range(10):
        a = k*TAU/10
        c,s = math.cos(a),math.sin(a)
        for (z0,r0),(z1,r1) in zip(profile,profile[1:]):
            rod(sec,ribs,(x+(r0+.006)*c,y+(r0+.006)*s,z0),
                (x+(r1+.006)*c,y+(r1+.006)*s,z1),r*.022,5)
    for zz in (-.83,.8):
        lathe(sec,ribs,x,y,[(z+r*zz-.024,r*.47),(z+r*zz+.021,r*.465)],16)
    rod(sec,ribs,(x,y,z-r*.83),(x,y,z-r*1.42),r*.092,8,.7)
    rod(sec,ribs,(x,y,z+r*.8),(x,y,z+r*2.22),.026,8)


def blessing(sec, mat, y, x,z,k):
    # Hand-laid strokes of the common blessing character Fu; no external font.
    strokes = [[(.16,.91),(.25,.82)],[(.08,.72),(.35,.72),(.225,.50),(.05,.39)],
               [(.216,.50),(.21,.06)],[(.26,.49),(.38,.37)],[(.48,.86),(.96,.86)],
               [(.54,.72),(.91,.72),(.90,.54),(.54,.54),(.54,.72)],[(.48,.43),(.95,.43),(.95,.09),(.48,.09),(.48,.43)],
               [(.51,.263),(.94,.263)],[(.722,.419),(.722,.091)]]
    for p in strokes:
        for (a,b),(c,d) in zip(p,p[1:]):
            beam(sec,mat,(x+k*(a-.5),y,z+k*(b-.5)),(x+k*(c-.5),y,z+k*(d-.5)),.052*k,.037,.006)


def build():
    base, hall, entry, roofs, ridges, decor, fixtures = 'Granite Threshold and Forecourt','Main Shrine and Side Walls','Vermilion Front Pavilion','Swept Tile Roofs','Swallowtail Ridges','Lanterns and Relief Panels','Incense Court'
    granite = material('Warm Grey Granite','a19a8b')
    socle = material('Darker Granite Base','777e75')
    grout = material('Courtyard Stone Mortar','b8a98b')
    lime = material('Ivory Lime Render','e1caa0')
    light = material('Pale Plaster Edges','eee0bb')
    red = material('Vermilion Lacquered Posts','9e4034',.53)
    scarlet = material('Red Orange Lantern Silk','d85038',.75)
    crimson = material('Oxblood Painted Timber','71392e',.53)
    wood = material('Blackwood Door Panels','413730',.48)
    gold = material('Brushed Brass Relief','c59c55',.41,.3)
    ochre = material('Gold Leaf Painted Trim','d4a763',.47)
    jade = material('Green Glazed Roof Border','3e7464',.39,.18)
    teal = material('Dark Green Coffer Paint','375a50',.61)
    ochres = [material(n,c,.69) for n,c in [('Old Red Clay','9d4d36'),('Burnt Terracotta','b16744'),('Weathered Red Clay','995742'),('Honey Terracotta','ba6b49')]]
    jade_tiles = [material(n,c,.45) for n,c in [('Dark Jade Enamel','42756a'),('Rain Jade Enamel','538978'),('Blue Jade Enamel','447f74')]]
    bronze = material('Patinated Bronze Burner','555949',.49,.38)
    sand = material('Incense Ash','8d8977')
    block(base,socle,-9.6,9.6,-10.45,8.27,0,.20,.074)
    block(base,granite,-9.44,9.44,-10.31,8.13,.195,.30,.042)
    for i in range(13):
        for j in range(3):
            box(base,granite if (i*2+j)%5 else grout,((i-6)*1.415,-9.57+j*.91,.306),(1.385,.879,.024),.011)
    block(hall,granite,-7.13,7.13,-3.87,7.31,.30,1.06,.068)
    block(hall,lime,-6.91,6.91,-3.18,7.08,1.06,5.42,.058)
    block(hall,light,-7.01,7.01,-3.31,7.21,4.98,5.27,.041)
    block(hall,crimson,-7.11,7.11,-3.41,7.29,5.24,5.55,.039)
    for s in (-1,1):
        profile = [(-3.16+j*(7.07+3.16)/18) for j in range(19)]
        prism(hall,lime,[(profile[0],5.36),(profile[-1],5.36)]+[
              (y,5.53+2.59*(1-abs(y-2.02)/5.70)**1.57) for y in reversed(profile)],
              s*6.69,s*6.94,'X')
        for y in (-1.78,1.12,4.03,6.26):
            box(hall,light,(s*6.955,y,3.29),(.214,1.46,1.88),.043)
            box(hall,jade,(s*7.075,y,3.29),(.074,1.24,1.65),.036)
            box(hall,wood,(s*7.124,y,3.29),(.045,1.07,1.47),.016)
            for j in (-2,-1,0,1,2):
                box(hall,ochre,(s*7.155,y+j*.19,3.29),(.045,.07,1.42),.009)
            box(hall,granite,(s*7.118,y,2.26),(.35,1.57,.151),.022)
        box(hall,red,(s*5.99,7.139,2.95),(1.19,.164,2.93),.042)
        box(hall,granite,(s*5.99,7.3,.675),(1.45,.67,.28),.037)
    for k in range(5):
        top = .44+k*.155
        box(base,granite,(0,-7.22+k*.167,top-.079),(4.35-.06*k,1.35-.14*k,.158),.028)
    block(entry,granite,-6.92,6.92,-6.69,-3.25,.3,1.072,.064)
    for s in (-1,1):
        x=s*4.57
        box(entry,granite,(x,-6.71,1.159),(4.23,.383,.249),.038)
        box(entry,light,(x,-6.79,1.306),(4.31,.396,.101),.031)
        box(entry,red,(s*5.78,-4.91,4.36),(.22,3.53,.25),.025)
    for x in (-5.76,-2.62,2.62,5.76):
        for y in (-6.18,-3.69):
            lathe(entry,granite,x,y,[(1.058,.298),(1.18,.315),(1.29,.276),(1.38,.254)],12)
            lathe(entry,red,x,y,[(1.354,.235),(2.97,.223),(4.33,.215)],16)
            lathe(entry,ochre,x,y,[(4.21,.233),(4.26,.251),(4.32,.250)],14)
            box(entry,crimson,(x,y,4.392),(.55,.50,.145),.034)
            box(entry,teal,(x,y,4.51),(.78,.65,.131),.038)
            box(entry,crimson,(x,y,4.637),(1.01,.86,.163),.031)
    for y in (-6.22,-3.67):
        box(entry,crimson,(0,y,4.724),(13.32,.47,.29),.036)
        box(entry,ochre,(0,y-.19,4.65),(12.65,.115,.08),.015)
        box(entry,teal,(0,y,4.936),(13.45,.36,.189),.034)
    block(entry,crimson,-6.61,6.61,-6.72,-3.41,4.974,5.059,.031)
    for y in (-6.27,-5.05,-3.63):
        box(entry,teal,(0,y,4.968),(13.03,.144,.071),.012)
    for j in range(21):
        x=(j-10)*.612
        box(entry,crimson,(x,-5.03,4.57),(.15,3.14,.15),.018)
        box(decor,ochre,(x,-6.466,4.796),(.28,.056,.103),.011)
    for x in (-4.29,-1.69,1.69,4.29):
        r = .235 if abs(x)<2 else .29
        box(entry,crimson,(x,-6.439,4.635),(.123,.5,.108),.012)
        rod(decor,gold,(x,-6.65,3.93+2.19*r),(x,-6.65,4.616),.021,8)
        lantern(decor,scarlet,gold,x,-6.65,3.93,r)
    for i,x in enumerate((-4.83,0,4.83)):
        w = 2.75 if i==1 else 2.23
        box(entry,granite,(x,-3.318,1.082),(w+.41,.56,.177),.038)
        box(entry,red,(x,-3.295,2.57),(w+.2,.217,3.13),.043)
        box(entry,wood,(x,-3.416,2.58),(w-.069,.044,2.923),.026)
        for j in (-1,1):
            xx = x+j*w*.251
            box(entry,crimson,(xx,-3.447,2.63),(w*.427,.049,2.74),.017)
            for z in (1.92,3.16):
                box(entry,wood,(xx,-3.481,z),(w*.33,.033,.972),.024)
                for d in (-.17,0,.17):
                    box(decor,gold,(xx+d,-3.506,z+.10),(.052,.024,.056),.009)
            rod(entry,gold,(x+j*.16,-3.537,2.26),(x+j*.16,-3.537,2.5),.025,8)
    for x in (-3.11,3.11):
        box(decor,jade,(x,-3.323,2.88),(.92,.19,1.92),.035)
        for j in range(5):
            for k in range(2):
                box(decor,ochre,(x+(k-.5)*.37,-3.442,2.16+j*.346),(.207,.041,.207),.017,
                    basis=Matrix.Rotation(math.pi/4,3,'Y'))
    box(decor,gold,(0,-6.518,4.653),(1.42,.152,.72),.035)
    box(decor,wood,(0,-6.602,4.653),(1.31,.045,.605),.024)
    blessing(decor,ochre,-6.636,0,4.655,.562)
    sweep_roof(roofs,ochres,jade,ochre,crimson,ridges,2.02,15.12,5.70,5.38,2.59,.44)
    sweep_roof(roofs,jade_tiles,jade,ochre,crimson,ridges,-5.05,14.5,2.43,4.83,1.284,.31)
    for y,z in ((2.02,8.32),(-5.05,6.49)):
        lathe(ridges,gold,0,y,[(z-.13,.15),(z+.02,.21),(z+.22,.181),(z+.31,.084),(z+.38,.012)],16)
        for s in (-1,1):
            for i in range(4):
                a = .18+i*.20
                beam(ridges,jade,(s*a,y,z-.069),(s*(a+.39),y,z+.06+.024*i),.089,.117,.019)
    # Outdoor incense vessel with three feet, bronze handles and an ash bed.
    by=-8.89
    lathe(fixtures,granite,0,by,[(.30,.70),(.41,.76),(.52,.67)],12,math.pi/12,False)
    for i in range(3):
        a = i*TAU/3+math.pi/2
        ux,uy = math.cos(a),math.sin(a)
        rod(fixtures,bronze,(ux*.43,by+uy*.43,.53),(ux*.40,by+uy*.40,.85),.107,10,1.07)
    lathe(fixtures,bronze,0,by,[(.78,.39),(.9,.52),(1.021,.59),(1.185,.59),(1.27,.518),
                              (1.30,.577),(1.365,.577),(1.366,.474),(1.27,.464)],24)
    lathe(fixtures,sand,0,by,[(1.258,.453),(1.279,.478)],24)
    for s in (-1,1):
        pts=[(s*.54,by,1.18),(s*.72,by,1.31),(s*.72,by,1.50),(s*.57,by,1.56),(s*.50,by,1.355)]
        for a,b in zip(pts,pts[1:]):
            rod(fixtures,bronze,a,b,.049,9)
    for j in range(5):
        a=j*.64
        x,y=.25*math.cos(a),by+.25*math.sin(a)
        rod(fixtures,crimson,(x,y,1.272),(x+.05,y,1.579+(j%3)*.082),.012,6,.63)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, (.52,-1,.46), (1192,938))
