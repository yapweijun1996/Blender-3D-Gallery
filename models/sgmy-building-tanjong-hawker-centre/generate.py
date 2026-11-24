"""Tanjong Serai | Hawker Centre — original procedural SG/MY streetscape asset.
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

def pavement(section, x, y, w, d, curb, paver, joint, pitch=1.2, z=.18):
    box(section,curb,(x,y,z/2),(w,d,z),.045)
    box(section,joint,(x,y,z+.018),(w-.1,d-.10,.05),.014)
    nx,ny = max(1,math.ceil(w/pitch)),max(1,math.ceil(d/pitch))
    dx,dy = (w-.13)/nx,(d-.13)/ny
    for i in range(nx):
        for j in range(ny):
            box(section,paver[(i*13+j*23+i*j)%len(paver)],
                (x+(i+.5-nx/2)*dx,y+(j+.5-ny/2)*dy,z+.048),(dx-.019,dy-.019,.02))

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


SLUG = 'sgmy-building-tanjong-hawker-centre'
TITLE = 'Tanjong Serai | Hawker Centre'
ROLE = 'Open-sided Singapore hawker centre with fixed seating and food stalls'
VIEW = (.65,-1,.37)
RESOLUTION = (1192,840)


def build():
    plinth = material('Granite kerb','a8a6a1')
    grout = material('Paver grout','9d8d7d')
    pavers = [material('Sand pavers','c9bba3'),material('Pink sand pavers','cdbba9'),material('Light sand pavers','d7c9b0')]
    white = material('Warm concrete','f0dfbf')
    red = material('Oxide steel','a45344')
    teal = material('Petrol enamel','295a60')
    jade = material('Jade roofing','54918a')
    seam = material('Raised standing seams','75a9a0')
    metal = material('Counter stainless','b2bab8',.34,.44)
    blue = material('Aegean ceramic','427f8d')
    ochre = material('Turmeric enamel','e5b75f')
    redseat = material('Papaya moulded seats','b05644')
    dark = material('Charcoal fittings','303f42')
    menu = material('Menu board ivory','fff1cc')
    lamp = material('Diffuse opal','ffe5a9',.42)
    greens = [material('Pandan green','52724a'),material('Fern green','78915b')]
    pavement('Paved Site',0,0,29,20,plinth,pavers,grout,1.30)
    box('Paved Site',teal,(0,3.49,.31),(26.15,4.81,.17),.039)
    box('Paved Site',white,(0,-2.58,.28),(26.15,7.40,.11),.033)
    for j in range(43):
        x = (j-21)*.58
        box('Paved Site',pavers[(j*7)%3],(x,-5.88,.347),(.562,.26,.028))
    for s in (-1,1):
        shrub_row('Street Planters',white,grout,greens,s*10.05,-7.89,.238,4.14)
        x = s*12.8
        for y,h in ((-5.6,3.43),(.82,3.67),(5.88,3.96),(8.58,3.37)):
            box('Canopy Structure',red,(x,y,.32+h/2),(.25,.28,h),.028)
            box('Canopy Structure',white,(x,y,.59),(.43,.45,.69),.038)
    for x in (-8.56,-4.29,0,4.29,8.56):
        for y,z in ((-5.60,3.38),(.82,3.59),(8.58,3.22)):
            box('Canopy Structure',red,(x,y,z/2+.22),(.28,.31,z),.023)
            box('Canopy Structure',white,(x,y,.52),(.43,.43,.46),.04)
    for y,z in ((-5.60,3.70),(.82,3.91),(8.58,3.60)):
        box('Canopy Structure',red,(0,y,z),(26.13,.24,.26),.025)

    # Three bays of raised monitor sheds, open by day and screened by angled vents.
    for i in range(3):
        x = (i-1)*8.88
        a,b = x-4.39,x+4.39
        for profile in (
            [(-6.38,3.86),(-1.13,4.87),(-1.13,5.06),(-6.38,4.03)],
            [(-1.28,5.49),(3.53,6.35),(3.53,6.54),(-1.28,5.68)],
            [(2.92,5.47),(9.17,3.63),(9.17,3.82),(2.92,5.66)],
        ):
            prism('Monitor Roof',jade,profile,a,b,'X')
            (y0,z0),(y1,z1) = profile[::-1][:2]
            for j in range(24):
                xx = a+(j+.5)*(b-a)/24
                beam('Monitor Roof',seam,(xx,y0,z0+.028),(xx,y1,z1+.028),.043,.044,.006)
            for xx in (a,b):
                beam('Monitor Roof',teal,(xx,y0,z0-.047),(xx,y1,z1-.047),.093,.19,.01)
            low_y,low_z = min(((y0,z0),(y1,z1)),key=lambda point: point[1])
            box('Monitor Roof',teal,((a+b)/2,low_y,low_z-.061),(b-a+.06,.18,.21),.022)
        for y,base,top in ((-1.16,4.99,5.59),(3.24,5.56,6.37)):
            for j in range(10):
                xx = x+(j-4.5)*.84
                box('Monitor Ventilation',white,(xx,y,(base+top)/2),(.095,.14,top-base),.007)
            for j in range(4):
                z = base+.086+(top-base-.17)*j/3
                box('Monitor Ventilation',teal,(x,y,z),(8.53,.17,.085),.009)
        for xx in (x-4.14,x+4.14):
            beam('Canopy Structure',red,(xx,-5.60,3.63),(xx,2.97,6.27),.104)
            beam('Canopy Structure',red,(xx,.82,3.96),(xx,2.97,6.27),.104)
            beam('Canopy Structure',red,(xx,8.58,3.57),(xx,2.97,6.27),.104)
    for i in range(7):
        x = (i-3)*3.68
        tint = (blue,red,teal,ochre,blue,red,teal)[i]
        box('Food Stall Row',white,(x,5.39,1.99),(3.62,3.65,2.92),.03)
        box('Food Stall Row',dark,(x,3.494,1.99),(3.43,.192,1.88),.021)
        box('Food Stall Row',tint,(x,3.35,.88),(3.03,.37,.991),.027)
        for j in range(13):
            box('Food Stall Row',white,(x+(j-6)*.223,3.15,.90),(.035,.042,.73),.004)
        box('Food Stall Row',metal,(x,3.26,1.40),(3.18,.72,.118),.024)
        box('Food Stall Row',tint,(x,3.39,2.89),(3.61,.23,.52),.028)
        label = ('NASI LEMAK','MEE REBUS','CHICKEN RICE','KOPI & TEH','SATAY','LAKSA','CUCUR')[i]
        sign('Stall Lettering',menu,label,(x+.19,3.26,2.887),2.82,.233)
        box('Food Stall Row',dark,(x-1.51,3.253,2.90),(.35,.053,.34),.021)
        sign('Stall Lettering',menu,f'{i+1:02}',(x-1.51,3.222,2.899),.30,.196)
        for j in range(3):
            box('Food Stall Row',menu,(x+.39+j*.21,3.352,2.11),(.17,.047,.249),.012)
            lathe('Food Stall Row',metal,x-.93+j*.225,3.42,[(1.461,.08),(1.62,.088),(1.651,.071)],9)
            box('Food Stall Row',ochre,(x+.58+j*.24,3.20,1.454),(.193,.153,.031),.009)
        louvre('Food Stall Row',white,teal,jade,x,7.24,2.54,2.10,.88,5,math.pi)
    for row,y in enumerate((-4.58,-1.64,1.00)):
        for j in range(7):
            x = (j-3)*3.46
            lathe('Dining Furniture',metal,x,y,[(.338,.145),(.39,.145),(.42,.073),(1.04,.073)],10)
            lathe('Dining Furniture',white,x,y,[(1.02,.55),(1.049,.623),(1.105,.625),(1.126,.60)],18)
            for dx,dy in ((-.86,0),(.86,0),(0,.86),(0,-.86)):
                lathe('Dining Furniture',dark,x+dx,y+dy,[(.338,.092),(.382,.092),(.401,.051),(.744,.052)],9)
                lathe('Dining Furniture',(blue,redseat,teal)[(j+row)%3],x+dx,y+dy,
                      [(.731,.17),(.75,.20),(.801,.20),(.816,.18)],12)
            box('Dining Furniture',ochre,(x,y,1.166),(.179,.115,.084),.015)
    for x in (-8.88,0,8.88):
        for y,anchor in ((-3.65,4.42),(.34,5.83)):
            rod('Ceiling Fans',dark,(x,y,anchor),(x,y,3.42),.039,8)
            lathe('Ceiling Fans',white,x,y,[(3.36,.12),(3.46,.149),(3.55,.109)],12)
            for j in range(3):
                a = j*TAU/3
                box('Ceiling Fans',white,(x+.404*math.cos(a),y+.404*math.sin(a),3.45),(.61,.118,.043),.012,yaw=a+.06)
        box('Ceiling Fans',lamp,(x,2.15,3.98),(3.34,.155,.115),.027)

    # Prominent hawker-centre blade, clear in the street view rather than under the dripline.
    for x in (-4.22,4.22):
        box('Street Sign and Return',red,(x,-6.40,3.26),(.153,.17,1.41),.018)
    box('Street Sign and Return',white,(0,-6.54,3.68),(8.73,.33,1.04),.071)
    box('Street Sign and Return',teal,(0,-6.724,3.68),(8.56,.046,.867),.046)
    sign('Street Sign and Return',menu,'TANJONG SERAI',(0,-6.755,3.908),5.80,.337)
    sign('Street Sign and Return',ochre,'H A W K E R   C E N T R E',(0,-6.755,3.540),5.62,.185)
    for x in (-13.18,13.18):
        box('Street Sign and Return',teal,(x,-4.25,.85),(1.00,1.39,1.22),.047)
        box('Street Sign and Return',metal,(x,-4.25,1.52),(1.049,1.45,.151),.027)
        box('Street Sign and Return',dark,(x,-4.953,1.195),(.76,.032,.291),.021)
        sign('Street Sign and Return',white,'TRAY RETURN',(x,-4.979,.765),.814,.122)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
