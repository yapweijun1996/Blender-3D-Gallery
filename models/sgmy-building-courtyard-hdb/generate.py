"""Block 318B — original procedural SG/MY streetscape asset.
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

SLUG = 'sgmy-building-courtyard-hdb'
TITLE = 'Block 318B | Courtyard HDB'


def build():
    slab, deck, facade, gallery = 'Footing and Void Deck', 'Community Fixtures', 'Apartment Fronts', 'Access Galleries'
    core, roof, signs = 'Lift and Stair Core', 'Roof Parapets and Plant', 'Block Identification'
    white = material('Warm Ivory Concrete','e0dac9')
    skim = material('Balcony Edge Concrete','f2e9d6')
    base = material('Slate Terrazzo','92978c')
    light = material('Void Deck Tile','b5b0a1')
    teal = material('Lagoon Blue Paint','327e82')
    pale = material('Washed Jade Panel','80a6a0')
    rust = material('Papaya Stairwell Paint','b96544')
    soil = material('Planter Soil','504538')
    leaves = material('Ixora Foliage','647c46')
    steel = material('Powder Coated Aluminium','4c5e60',.4,.26)
    g = [material(n,c,.36,.13) for n,c in [('Storm Glass','3d535d'),('Curtained Glass','657f84'),('Pale Sky Glass','899e9c')]]
    wood = material('Bench Hardwood','997350')
    paper = material('Community Notices','d9b775')
    dark = material('Charcoal Shadow Line','394046')
    block(slab,base,-23,23,-7.9,7.9,0,.16,.075)
    block(slab,light,-22.4,22.4,-7.5,7.5,.16,.21,.025)
    for x in range(-20,21,4):
        box(slab,base,(x,0,.213),(.035,14.8,.012))
    for x in (-20.7,-14.5,-8,-1.4,4.3,10.0,15.7,21.3):
        for y in (-5.68,4.56):
            block(slab,white,x-.36,x+.36,y-.43,y+.43,.2,3.68,.045)
            box(slab,teal,(x,y,.74),(.733,.873,1.07),.023)
            box(slab,base,(x,y,.27),(.86,.97,.14),.035)
    for y in (-5.68,4.56):
        box(slab,white,(0,y,3.38),(44,.79,.54),.03)
    block(core,white,-2.05,4.5,-6.65,4.41,.2,32.48,.07)
    block(core,rust,-1.88,4.35,-7.13,-6.54,.22,31.75,.045)
    block(core,white,.56,1.06,-7.32,-7.1,.2,32.23,.04)
    for x in (-.94,2.78):
        box(core,steel,(x,-7.18,1.54),(1.59,.13,2.45),.035)
        box(core,g[0],(x,-7.258,1.62),(1.36,.04,2.23),.02)
        box(core,steel,(x,-7.285,1.62),(.043,.018,2.2))
    block(core,teal,-2.31,4.77,-8.98,-6.84,3.04,3.28,.065)
    block(core,skim,-2.34,4.8,-8.96,-6.84,3.25,3.34,.025)
    box(signs,teal,(2.65,-7.223,28.8),(2.9,.23,2.78),.045)
    sign(signs,skim,'318B',(2.65,-7.348,29.05),2.49,1.02)
    sign(signs,skim,'BLOCK',(2.65,-7.348,28.04),1.75,.27)
    for group,x0,x1,levels in [('West',-22,-1.8,8),('East',4.3,22,9)]:
        xspan = x1-x0
        mid = (x0+x1)/2
        n_bays = 4
        pitch = xspan/n_bays
        zbase, storey = 3.64,3.04
        top = zbase+levels*storey
        block(facade,white,x0,x1,-6.58,3.45,zbase,top,.055)
        outer = x0 if group == 'West' else x1
        side = -1 if group == 'West' else 1
        for y0,y1,paint in [(-6.8,-5.51,teal),(-5.505,-2.78,pale),(-2.775,-.9,teal),
                            (-.895,1.4,white),(1.405,3.48,pale),(3.485,5.69,teal)]:
            box(facade,paint,(outer+side*.05,(y0+y1)/2,(top+zbase)/2),(.27,y1-y0,top-zbase),.028)
        inner = x1 if group == 'West' else x0
        box(facade,teal,(inner,-6.66,(top+zbase)/2),(.29,.29,top-zbase),.023)
        for level in range(levels):
            z = zbase+storey*level
            box(facade,skim,(mid,-6.65,z+.28),(xspan,.4,.38),.032)
            for y in (-4.21,.18,2.41):
                box(facade,steel,(outer+side*.2,y,z+1.58),(.09,1.46,1.2),.024)
                for dy in (-.343,.343):
                    box(facade,g[(level+int(y)+int(dy>0))%3],(outer+side*.257,y+dy,z+1.58),(.034,.638,1.08))
                box(facade,skim,(outer+side*.201,y,z+.963),(.20,1.53,.09),.02)
            block(gallery,white,x0,x1,3.31,5.86,z-.1,z+.25,.045)
            block(gallery,pale,x0,x1,5.64,5.83,z+.22,z+1.09)
            box(gallery,skim,(mid,5.73,z+1.15),(xspan,.28,.13),.025)
            for i in range(n_bays):
                x = x0+pitch*(i+.5)
                box(facade,teal if (i+level//3)%4 in (0,3) else pale,
                    (x,-6.63,z+1.47),(pitch-.28,.18,1.96),.035)
                wx = x-.27
                w = pitch-1.06
                box(facade,steel,(wx,-6.752,z+1.71),(w,.15,1.43))
                for j in range(4):
                    box(facade,g[(j//2+i*3+level*(1+j%2))%len(g)],
                        (wx+w*(j-1.5)/4,-6.837,z+1.71),(w/4-.048,.035,1.3))
                box(facade,skim,(wx,-6.85,z+1.0),(w+.19,.4,.11),.022)
                if (level+i)%3 != 0:
                    ax = x+pitch*.33
                    box(facade,skim,(ax,-6.91,z+.81),(.77,.48,.14))
                    box(facade,white,(ax,-6.88,z+1.08),(.65,.32,.41),.026)
                    box(facade,steel,(ax+.075,-7.048,z+1.08),(.34,.02,.255),.009)
                box(gallery,white,(x-pitch/2+.12,5.68,z+1.51),(.22,.31,2.65))
                box(gallery,steel,(x-.85,3.51,z+1.34),(.93,.15,2.21),.024)
                box(gallery,g[(level+i+1)%3],(x+.57,3.56,z+1.72),(1.55,.16,1.11))
                for j in range(2):
                    box(gallery,steel,(x+.3+j*.54,3.65,z+1.7),(.042,.035,1.07))
                if (i+level*2)%6 == 2:
                    for j,c in enumerate((rust,pale,skim)):
                        box(gallery,c,(x+.1+j*.28,5.85,z+.91),(.25,.025,.42+j*.1))
        block(roof,base,x0,x1,-6.7,5.87,top,top+.31,.06)
        for y in (-6.62,5.74):
            box(roof,white,(mid,y,top+.63),(xspan,.21,.67),.035)
        for x in (x0+.13,x1-.13):
            box(roof,white,(x,-.41,top+.63),(.24,12.42,.67),.035)
        box(roof,white,(mid+2,2,top+.84),(4.2,3.22,1.4),.04)
        box(roof,teal,(mid+2,2,top+1.56),(4.47,3.46,.23),.045)
        for j in range(3):
            box(roof,steel,(mid-5+j*1.38,1.9,top+.54),(1.05,.85,.56),.045)
            for d in (-.26,0,.26):
                box(roof,dark,(mid-5+j*1.38+d,1.9,top+.829),(.08,.57,.022))
    box(roof,skim,(1.25,-1.14,32.53),(7,11.5,.39),.08)
    box(roof,base,(1.24,1.2,33.12),(4.45,4.2,1),.06)
    box(roof,teal,(1.24,1.2,33.68),(4.75,4.5,.24),.05)
    for level in range(9):
        for i in range(5):
            if level == 8 and i >= 3:
                continue
            z = 4.84+3.04*level + .29*i
            box(core,steel,(-.73,-7.163,z),(1.32,.10,.14),.015)
            if level != 8:
                box(core,g[0],(2.61,-7.155,z),(1.68,.085,.18))
    for x in (-18,-11,12,18.2):
        y = -4.25 if x == -11 else -3.85
        for dx in (-.62,.62):
            box(deck,base,(x+dx,y,.42),(.24,.45,.42),.022)
        for i in range(3):
            box(deck,wood,(x,y+(.14*(i-1)),.66),(1.7,.12,.12),.024)
    for x,y in ((-10.1,.4),(15,2.2)):
        box(deck,base,(x,y,.54),(.43,.43,.68),.045)
        box(deck,light,(x,y,.91),(1.3,1.3,.15),.04)
        for dx in (-.31,.31):
            for dy in (-.31,.31):
                box(deck,steel,(x+dx,y+dy,.993),(.6,.6,.022))
        for dy in (-1,1):
            box(deck,base,(x,y+dy,.45),(1.07,.43,.48),.055)
    box(deck,steel,(-5.18,-4.2,1.93),(2.05,.22,1.16),.05)
    box(deck,wood,(-5.18,-4.325,1.94),(1.88,.06,.98))
    for i in range(4):
        box(deck,paper if i%2 else skim,(-5.81+i*.4,-4.365,1.99),(.27,.025,.41+i*.08),yaw=0)
    for x in (-16.45,16.75):
        box(deck,base,(x,-7.17,.44),(2.68,.91,.49),.08)
        box(deck,soil,(x,-7.17,.7),(2.46,.71,.06),.025)
        for j in range(7):
            lathe(deck,leaves,x+(j-3)*.33,-7.17,[(.71,.22),(.95+.045*(j%2),.32),(1.2,.25),(1.29,.1)],7,j)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, (.57,-1,.43), (1184,896))
