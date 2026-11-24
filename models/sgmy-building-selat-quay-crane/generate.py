"""Selat Container Terminal | Quay Crane — original procedural SG/MY streetscape asset.
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


SLUG = 'sgmy-building-selat-quay-crane'
TITLE = 'Selat Container Terminal | Quay Crane'
ROLE = 'Static ship-to-shore portal crane on a harbour rail base'
VIEW = (.67,-1,.50)
RESOLUTION = (1180,970)


def build():
    concrete = material('Salt grey concrete','a9a9a4')
    quay = material('Quay pavement','8d9797')
    dark = material('Graphite steel','283b42',.53,.33)
    blue = material('Petrol crane enamel','427b8b',.58,.16)
    bright = material('Aegean steel highlights','60a4ad',.52,.18)
    cream = material('Maintenance cream','f0dfb8')
    yellow = material('Safety ochre','e7ad48')
    glass = material('Cab blue glass','294c57',.22,.24)
    steel = material('Rail steel','687e83',.32,.60)
    rust = material('Oxide containers','b0614e')
    moss = material('Sage containers','698b73')
    tyre = material('Rubber fenders','363c3b')
    box('Quay Section',concrete,(0,5.5,.44),(33,36,.88),.12)
    box('Quay Section',quay,(0,5.5,.935),(32.81,35.84,.15),.052)
    for x in (-13.2,-6.6,0,6.6,13.2):
        box('Quay Section',dark,(x,-12.54,.39),(.82,.20,.60),.04)
        box('Quay Section',tyre,(x,-12.69,.37),(1.10,.28,.56),.09)
    for y in (-11.92,-5.18,16.27,22.14):
        for i in range(14):
            box('Quay Markings',yellow,((i-6.5)*2.20,y,1.018),(1.46,.109,.017))
    for y in (-8.78,19.40):
        box('Quay Section',dark,(0,y,1.018),(32.5,.64,.037),.014)
        for s in (-1,1):
            box('Quay Section',steel,(0,y+s*.112,1.087),(32.5,.084,.100),.011)
        for i in range(22):
            box('Quay Section',steel,((i-10.5)*1.43,y,1.043),(.18,.56,.047),.007)

    # Rail bogies, upturned side frames and continuous overhead portal girders.
    for x in (-10.50,10.50):
        for y,zside in ((-8.78,-1),(19.40,1)):
            box('Gantry Bogies',dark,(x,y,1.92),(6.67,1.02,1.09),.10)
            box('Gantry Bogies',bright,(x,y,2.65),(5.36,1.38,.59),.06)
            for xx in [x+(j-2.5)*1.00 for j in range(6)]:
                rod('Gantry Bogies',tyre,(xx,y-.424,1.59),(xx,y+.424,1.59),.49,14)
                rod('Gantry Bogies',steel,(xx,y-.47,1.59),(xx,y+.47,1.59),.237,12)
            yy = y-zside*1.05
            beam('Portal Frames',blue,(x,y,2.79),(x*.79,yy,30.9),1.12,1.41,.063)
            beam('Portal Frames',bright,(x+( .54 if x<0 else -.54),y,3.05),
                 (x*.79+( .54 if x<0 else -.54),yy,30.8),.14,.22,.018)
            for t in (.15,.49,.73):
                box('Portal Frames',bright,(x*(1-.21*t),y-zside*1.05*t,2.8+28*t),(1.53,1.54,.23),.029)
        beam('Portal Frames',blue,(x*.93,-8.62,12.6),(x*.93,19.19,12.6),1.44,1.08,.061)
        beam('Portal Frames',blue,(x*.79,-8.1,29.85),(x*.79,18.6,29.85),1.38,1.15,.063)
        beam('Portal Braces',bright,(x*.96,-8.2,8.7),(x*.90,-2.2,12.51),.60,.65,.047)
        beam('Portal Braces',bright,(x*.96,18.3,8.7),(x*.90,12.4,12.51),.60,.65,.047)
        beam('Portal Braces',blue,(x*.885,18.84,18.2),(x*.93,13.1,12.73),.69,.66,.04)
        beam('Portal Braces',blue,(x*.885,-8.22,18.2),(x*.93,-2.24,12.73),.69,.66,.04)
    for y in (-8.07,18.66):
        for z in (12.6,29.85):
            box('Portal Frames',blue,(0,y,z),(19.77,1.22,1.30),.061)
        for s in (-1,1):
            beam('Portal Braces',bright,(s*9.38,y,17.0),(s*5.52,y,12.74),.66,.64,.035)
        box('Portal Signage',cream,(0,y-.65,12.56),(7.70,.12,.71),.055)
        sign('Portal Signage',dark,'SELAT  TERMINAL',(0,y-.728,12.56),6.13,.354)
    box('Portal Signage',yellow,(10.29,-9.42,5.46),(1.35,.15,1.05),.06)
    sign('Portal Signage',dark,'QC 04',(10.29,-9.503,5.47),1.10,.421)
    for y in (3.70,4.42):
        box('Portal Frames',blue,(0,y,29.85),(17.8,.83,1.11),.056)

    # Trussed fixed flying boom, hinge, forestays and backstays.
    stations = [-34,-28,-22,-16,-10,-4,2,8,14,20,25]
    for s in (-1,1):
        x = s*2.28
        for a,b in zip(stations,stations[1:]):
            for z,w in ((28.57,.60),(31.43,.69)):
                beam('Trolley Boom',blue,(x,a,z),(x,b,z),w,.68,.035)
            beam('Trolley Boom',bright,(x,a,28.71),(x,b,31.40),.402,.402,.025)
            beam('Trolley Boom',blue,(x,b,28.72),(x,b,31.29),.314,.315,.024)
        beam('Trolley Boom',blue,(x,-34,28.57),(x,-34,31.43),.60,.69,.04)
        box('Trolley Boom',cream,(x,-34.18,31.20),(.663,.26,.64),.047)
        beam('Trolley Boom',steel,(s*1.53,-34,28.13),(s*1.53,24.8,28.13),.18,.23,.015)
        beam('Apex and Pendants',blue,(s*6.56,4.42,29.88),(s*1.68,6.39,42.04),.83,.82,.049)
        beam('Apex and Pendants',bright,(s*6.3,3.7,29.8),(s*3.17,5.78,38.31),.29,.31,.02)
        for y,z in ((-22.3,31.79),(-13.3,31.70),(22.56,31.79)):
            beam('Apex and Pendants',dark,(s*1.69,6.30,41.85),(x,y,z),.165,.194,.013)
            box('Apex and Pendants',yellow,(x,y,z),(.446,.42,.51),.055)
    for i,y in enumerate(stations):
        box('Trolley Boom',blue,(0,y,31.405),(5.18,.35,.42),.028)
        if i < len(stations)-1:
            beam('Trolley Boom',bright,(-2.28,y,31.423),(2.28,stations[i+1],31.423),.31,.34,.028)
    box('Apex and Pendants',cream,(0,6.34,41.94),(4.02,.82,.87),.067)
    for x in (-1.45,1.45):
        rod('Apex and Pendants',yellow,(x,6.33,42.37),(x,6.33,42.64),.092,9)

    # Platform, service stairs and cable-fed driver's trolley with static spreader.
    box('Machinery and Catwalks',cream,(0,19.27,32.72),(7.92,7.59,2.31),.077)
    box('Machinery and Catwalks',blue,(0,19.27,33.92),(8.08,7.79,.20),.034)
    for x in (-3.09,-1.03,1.03,3.09):
        louvre('Machinery and Catwalks',blue,dark,bright,x,15.42,32.76,1.56,1.18,6)
    box('Machinery and Catwalks',steel,(8.17,5.63,13.43),(1.02,26.34,.16),.022)
    rail('Machinery and Catwalks',yellow,(8.63,-7.47,13.49),(8.63,18.71,13.49),1.02,1.57)
    for i in range(4):
        z0 = 2.91+i*2.62
        x = 10.54+i%2*1.12
        y0,y1 = (18.56,15.51) if i%2 == 0 else (15.51,18.56)
        for xx in (x-.54,x+.54):
            beam('Machinery and Catwalks',steel,(xx,y0,z0),(xx,y1,z0+2.62),.124,.131,.01)
            rail('Machinery and Catwalks',yellow,(xx,y0,z0),(xx,y1,z0+2.62),.97,1.2)
        for j in range(14):
            t = j/14
            box('Machinery and Catwalks',steel,(x,y0+(y1-y0)*t,z0+2.62*t),(1.063,.23,.086),.012)
        yy = y1+(.40 if i%2 else -.40)
        box('Machinery and Catwalks',steel,(10.75,yy,z0+2.62),(2.86,.98,.149),.017)
        rail('Machinery and Catwalks',yellow,(9.28,yy, z0+2.69),(12.17,yy,z0+2.69),.97,1.44)
    box('Machinery and Catwalks',steel,(9.20,18.41,13.39),(1.85,1.28,.16),.02)
    y = -23.78
    box('Trolley and Spreader',dark,(0,y,27.74),(4.82,3.01,.53),.055)
    box('Trolley and Spreader',yellow,(0,y,28.13),(4.04,2.76,.31),.037)
    box('Trolley and Spreader',cream,(2.56,y,26.30),(1.85,2.30,2.28),.086)
    box('Trolley and Spreader',glass,(2.56,y-1.173,26.68),(1.59,.105,1.25),.075)
    box('Trolley and Spreader',glass,(3.517,y,26.68),(.086,2.01,1.25),.065)
    for x in (-1.42,1.42):
        for yy in (y-.83,y+.83):
            rod('Trolley and Spreader',dark,(x,yy,27.46),(x,yy,16.40),.034,8)
    box('Trolley and Spreader',yellow,(0,y,16.16),(12.24,2.61,.45),.05)
    for x in (-5.72,5.72):
        box('Trolley and Spreader',dark,(x,y,15.82),(.63,2.63,.28),.027)
    for i in range(13):
        box('Trolley and Spreader',dark,((i-6)*.89,y-1.312,16.18),(.39,.032,.158),.013,yaw=.002)

    for x,y,z,mat in ((-3.27,6.0,1.02,rust),(-3.27,6.0,3.63,moss),(-5.98,6.0,1.02,blue),
                      (5.62,9.6,1.02,moss),(5.62,9.6,3.63,rust),(2.80,9.6,1.02,cream)):
        box('Landside Containers',mat,(x,y,z+1.30),(2.44,12.19,2.60),.030)
        for s in (-1,1):
            for j in range(37):
                box('Landside Containers',mat,(x+s*1.226,y+(j-18)*.315,z+1.30),(.079,.124,2.27),.014)
            for zz in (z+.13,z+2.50):
                box('Landside Containers',dark,(x+s*1.165,y,zz),(.142,12.21,.12),.012)
            for dx in (-.88,-.31,.31,.88):
                rod('Landside Containers',steel,(x+dx,y+s*6.108,z+.24),(x+dx,y+s*6.108,z+2.36),.035,7)
        for s in (-1,1):
            box('Landside Containers',dark,(x,y+s*6.124,z+1.30),(.036,.023,2.35))
    # Centre the install pivot on the rail base, not the overhanging boom envelope.
    for vertices,_,_,_ in PARTS.values():
        vertices[:] = [(x,y-5.5,z) for x,y,z in vertices]


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
