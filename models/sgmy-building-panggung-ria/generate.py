"""Panggung Ria | Streamline Picture House — original procedural SG/MY streetscape asset.
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


SLUG = 'sgmy-building-panggung-ria'
TITLE = 'Panggung Ria | Streamline Picture House'
ROLE = 'Malayan-inspired Art Deco neighbourhood cinema'
VIEW = (.56,-1,.51)
RESOLUTION = (1120,900)


def build():
    kerb = material('Terrazzo plinth','a28f7b')
    joint = material('Brick paving joints','a58b77')
    pavers = [material('Honey concrete flag','d3bc9a'),material('Pale cream flag','ddcaa9'),material('Biscuit flag','ccb18e')]
    wall = material('Vanilla stucco','ffe5b9')
    dusty = material('Peach stucco','dda47d')
    trim = material('Cream painted moulding','fff1d1')
    red = material('Cinema vermilion','a3463b')
    brick = material('Oxide tile','bc7661')
    gold = material('Brass stripe','d3aa63',.39,.22)
    petrol = material('Vitreous teal','245960')
    glass = material('Smoked scallop glass','31565e',.25,.22)
    slate = material('Roof concrete','897d70')
    dark = material('Iron grilles','3d3532')
    lamp = material('Marquee opal','ffe19d',.39)
    greens = [material('Dwarf pandan','668351'),material('Courtyard shrub','82945b')]
    pavement('Cinema Forecourt',0,0,20.4,27,kerb,pavers,joint,1.24)
    for i in range(21):
        x = (i-10)*.86
        box('Cinema Forecourt',pavers[0] if i%2 else petrol,(x,-12,.248),(.77,.58,.025))
    for x in (-7.52,7.52):
        shrub_row('Cinema Forecourt',wall,slate,greens,x,-10.75,.238,2.7,1.16)

    # Solid auditorium behind a narrower streamline lobby.
    box('Auditorium Shell',dusty,(0,2.95,4.61),(17.46,19.09,8.77),.115)
    for z,w,d,h,mat in ((.50,17.66,19.33,.48,brick),(2.54,17.64,19.31,.125,wall),
                        (6.72,17.63,19.28,.115,wall),(8.47,17.65,19.36,.145,trim),
                        (9.07,17.79,19.47,.217,wall),(9.20,16.91,18.71,.15,slate)):
        box('Auditorium Shell',mat,(0,2.95,z),(w,d,h),.05)
    for s in (-1,1):
        for j,y in enumerate((-5.58,-1.5,2.79,7.03,11.72)):
            box('Auditorium Shell',wall,(s*8.75,y,4.62),(.23,.49,7.37),.05)
            box('Auditorium Shell',trim,(s*8.81,y,8.13),(.28,.63,.21),.035)
            if j<4:
                louvre('Auditorium Ventilation',wall,petrol,red,s*8.77,y+1.99,7.55,1.74,.97,6,s*math.pi/2)
        louvre('Auditorium Ventilation',trim,petrol,red,s*5.45,12.55,6.85,2.67,1.12,6,math.pi)
        box('Auditorium Ventilation',wall,(s*8.77,5.36,1.53),(.19,1.76,2.54),.055)
        box('Auditorium Ventilation',petrol,(s*8.892,5.36,1.52),(.103,1.45,2.28),.021)
        box('Auditorium Ventilation',gold,(s*8.956,5.36,1.36),(.038,1.26,.045),.008)
    for x,y in ((-4.61,7.54),(4.23,7.77),(4.23,1.2)):
        box('Roof Plant',slate,(x,y,9.49),(2.14,2.01,.53),.043)
        box('Roof Plant',petrol,(x,y,9.76),(1.96,1.81,.15),.022)
        for j in range(7):
            box('Roof Plant',trim,(x+(j-3)*.23,y,9.86),(.062,1.43,.055),.01)

    rounded('Streamline Façade',wall,0,-6.84,16.09,5.12,.245,8.84,1.22)
    rounded('Streamline Façade',dusty,0,-6.90,14.85,4.74,8.60,9.44,1.04)
    rounded('Streamline Façade',trim,0,-6.92,14.94,4.82,9.44,9.62,1.08)
    rounded('Streamline Façade',brick,0,-6.84,16.17,5.25,.24,.81,1.23)
    for z,h,mat in ((3.84,.12,dusty),(4.04,.09,trim),(4.29,.12,gold),(6.44,.11,dusty),
                    (6.66,.09,dusty),(8.30,.10,dusty),(8.67,.15,trim)):
        rounded('Streamline Façade',mat,0,-6.84,16.21,5.27,z,z+h,1.26)
    for s in (-1,1):
        for i in range(3):
            x = s*(3.32+i*1.43)
            box('Streamline Façade',trim,(x,-9.40,5.48),(1.11,.157,1.48),.085)
            box('Streamline Façade',glass,(x,-9.496,5.48),(.85,.067,1.19),.065)
            for z in (5.14,5.48,5.83):
                box('Streamline Façade',gold,(x,-9.536,z),(.87,.041,.058),.013)
        for i in range(3):
            x = s*(2.04+i*.44)
            z = 7.49-i*.18
            box('Streamline Façade',red,(x,-9.45,z),(.169,.23,1.25),.028)
    # Vertical Art Deco sign fin layered over the horizontal bands.
    for i,(w,z,h,d) in enumerate(((3.54,7.52,5.34,.60),(2.96,8.57,5.23,.68),
                                  (2.32,9.26,4.85,.72),(1.72,10.07,4.49,.72))):
        box('Deco Sign Tower',(dusty,wall,trim,red)[i],(0,-9.41-i*.20,z),(w,d,h),.072)
        box('Deco Sign Tower',gold,(0,-9.43-i*.20,z+h/2),(w+.13,d+.09,.15),.024)
    for s in (-1,1):
        box('Deco Sign Tower',gold,(s*.67,-10.39,9.93),(.055,.058,4.01),.01)
    for i,ch in enumerate('R I A'.split()):
        sign('Deco Sign Tower',trim,ch,(0,-10.388,11.25-i*1.18),.71,.78)

    rounded('Street Marquee',red,0,-9.93,14.92,2.94,3.12,3.78,1.38)
    rounded('Street Marquee',gold,0,-9.94,15.04,2.98,3.71,3.82,1.41)
    rounded('Street Marquee',trim,0,-9.94,14.98,2.97,3.08,3.18,1.40)
    for i in range(25):
        x = (i-12)*.497
        lathe('Street Marquee',lamp,x,-11.18,[(3.015,.053),(3.04,.088),(3.08,.094)],10)
    sign('Street Marquee',trim,'P A N G G U N G   R I A',(0,-11.421,3.425),9.20,.307)
    for j in range(5):
        x = (j-2)*1.37
        box('Entry Doors',red,(x,-9.465,1.65),(1.29,.21,2.60),.034)
        for s in (-1,1):
            xx = x+s*.288
            box('Entry Doors',glass,(xx,-9.589,1.75),(.499,.064,1.79),.025)
            box('Entry Doors',gold,(xx,-9.638,1.49),(.346,.056,.053),.011)
        box('Entry Doors',gold,(x,-9.59,2.73),(1.14,.062,.061),.01)
    steps('Entry Doors',brick,gold,0,-10.11,7.67,2,.309,.084,.238)
    for s in (-1,1):
        x = s*5.96
        box('Poster Cases',petrol,(x,-9.48,1.78),(1.44,.244,2.07),.064)
        box('Poster Cases',gold,(x,-9.619,1.78),(1.31,.057,1.91),.038)
        box('Poster Cases',brick if s>0 else petrol,(x,-9.655,1.78),(1.21,.03,1.81),.031)
        prism('Poster Cases',lamp,[(x-.47,1.35),(x+.42,1.35),(x+.17,2.24),(x-.37,1.91)],-9.681,-9.670)
        rod('Poster Cases',dusty,(x+.21,-9.681,2.29),(x+.21,-9.669,2.29),.16,20)
        sign('Poster Cases',trim,'FILEM',(x,-9.688,2.52),.98,.196)
        sign('Poster Cases',trim,'MALAM INI',(x,-9.688,1.13),.95,.116)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
