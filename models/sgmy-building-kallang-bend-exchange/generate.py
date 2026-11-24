"""Kallang Bend | Telecom Exchange — original procedural SG/MY streetscape asset.
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


SLUG = 'sgmy-building-kallang-bend-exchange'
TITLE = 'Kallang Bend | Telecom Exchange'
ROLE = 'Tropical telecommunications exchange with salvaged-style ceramic sun screen'
VIEW = (.68,-1,.49)
RESOLUTION = (1020,1050)


def build():
    curb = material('Basalt plinth','879293')
    joint = material('Concrete joints','99958a')
    pavers = [material('Grey footway','bdbdb1'),material('Sand footway','c9bfaa'),material('Pearl footway','c2c3b8')]
    concrete = material('Ivory board marked concrete','e6d8bb')
    shadow = material('Shadow line concrete','b7aa90')
    glass = material('Dark tinted glazing','2f4d54',.24,.26)
    cyan = material('Opaque turquoise transom','517e84',.3,.21)
    ceramic = [material('Jade glazed ceramic','438d8a',.36),material('Celadon glazed ceramic','80aaa0',.37),
               material('Deep green glazed ceramic','336d6d',.37)]
    terracotta = material('Red oxide stair core','b37760')
    orange = material('Apricot identity strip','ddac72')
    steel = material('Mask grey aluminium','718485',.39,.39)
    dark = material('Petrol aluminium trim','354f54')
    cream = material('White enamel lettering','fff0cd')
    bark = material('Silver palm trunk','948670')
    greens = [material('Areca green','527545'),material('Areca sage','728f5b')]
    pavement('Exchange Footway',0,0,25.5,20.0,curb,pavers,joint,1.40)
    for x in (-8.42,8.42):
        shrub_row('Tropical Planting',shadow,joint,greens,x,-7.48,.238,3.64,1.37)
        palm('Tropical Planting',bark,greens,x,-7.48,.74,4.1,x*.25)
    box('Ground Floor Podium',curb,(0,1.72,.47),(21.66,14.65,.45),.069)
    box('Ground Floor Podium',concrete,(0,2.57,2.39),(20.36,12.27,3.73),.055)
    steps('Ground Floor Podium',shadow,steel,0,-5.94,7.25,3,.295,.152,.238)
    box('Ground Floor Podium',dark,(0,-4.38,2.61),(16.08,1.71,2.95),.061)
    for j in range(13):
        x = (j-6)*1.20
        box('Ground Floor Glazing',glass,(x,-5.253,2.45),(1.104,.096,2.29),.03)
        box('Ground Floor Glazing',cyan,(x,-5.257,3.83),(1.11,.094,.35),.025)
        box('Ground Floor Glazing',steel,(x-.578,-5.311,2.60),(.060,.074,2.70),.01)
        if abs(x)<2.50:
            box('Ground Floor Glazing',cream,(x+.30,-5.328,1.97),(.11,.056,.217),.012)
    box('Ground Floor Podium',concrete,(0,-5.12,4.43),(22.2,3.3,.59),.076)
    box('Ground Floor Podium',dark,(0,-6.79,4.38),(20.66,.19,.329),.038)
    sign('Exchange Lettering',cream,'KALLANG BEND  /  TELECOM EXCHANGE',(0,-6.896,4.376),8.32,.222)
    for x in (-7.59,-4.05,4.05,7.59):
        box('Ground Floor Podium',concrete,(x,-6.104,2.43),(.36,.46,3.63),.041)
        box('Ground Floor Podium',shadow,(x,-6.104,.79),(.46,.54,.31),.035)
    for x in (-5.78,0,5.78):
        box('Ground Floor Podium',cream,(x,-5.89,4.106),(1.65,.18,.073),.027)

    box('Exchange Structure',shadow,(-1.07,1.55,12.99),(16.94,12.53,17.82),.052)
    box('Exchange Structure',terracotta,(8.86,2.22,13.31),(3.18,13.63,18.68),.072)
    box('Exchange Structure',concrete,(9.03,2.22,22.72),(3.46,13.83,.39),.065)
    for z in (4.72,8.11,11.53,14.95,18.37,21.81):
        box('Exchange Structure',concrete,(-1.16,1.44,z),(17.5,13.50,.34),.046)
        box('Exchange Structure',orange,(8.84,-4.645,z),(2.92,.23,.12),.021)
    for s in (-1,1):
        x = -1.07+s*8.46
        for y in (-3.87,-.50,2.86,6.27):
            box('Exchange Structure',concrete,(x,y,13.06),(.45,.53,17.15),.05)
    for z in (6.35,9.77,13.19,16.61,20.02):
        for layer in range(3):
            y = -.05+layer*3.42
            louvre('Mechanical Louvres',concrete,dark,steel,-9.59,y,z,2.62,2.19,9,-math.pi/2)
            louvre('Mechanical Louvres',concrete,dark,steel,-5.87+layer*4.28,7.856,z,3.11,2.19,9,math.pi)
        for y in (-2.81,3.14,6.4):
            louvre('Core Windows',shadow,glass,orange,10.48,y,z,.94,1.9,5,math.pi/2)
        louvre('Core Windows',orange,glass,terracotta,8.86,-4.656,z,1.25,2.08,7)
    sign('Exchange Lettering',cream,'06',(8.87,-4.632,22.08),1.25,.57)

    # Deep screen panels set ahead of a service cavity; the diamond apertures are actual gaps.
    for i in range(4):
        cx = -7.48+i*4.19
        box('Ceramic Screen Frame',concrete,(cx-2.035,-4.831,13.21),(.23,.39,16.67),.025)
        box('Ceramic Screen Frame',concrete,(cx+2.035,-4.831,13.21),(.23,.39,16.67),.025)
        for k in range(5):
            z = 6.43+k*3.415
            box('Ceramic Screen Frame',dark,(cx,-4.748,z),(3.61,.17,2.84),.026)
            for j in range(6):
                x = cx+(j-2.5)*.607
                if (j+i)%2:
                    box('Ceramic Screen Frame',cyan,(x,-4.845,z),(.548,.069,2.16),.009)
            for ysign in (-1,1):
                box('Ceramic Screen Frame',steel,(cx,-5.092,z+ysign*1.49),(3.91,.22,.135),.019)
            for row in range(4):
                zz = z+(row-1.5)*.695
                box('Ceramic Screen Frame',steel,(cx,-4.923,zz-.264),(4.06,.21,.093),.009)
                for col in range(5):
                    xx = cx+(col-2)*.764 + (.12 if row%2==0 else -.12)
                    outside = [(xx+.318,zz),(xx,zz+.316),(xx-.318,zz),(xx,zz-.316)]
                    inside = [(xx+.201,zz),(xx,zz+.199),(xx-.201,zz),(xx,zz-.199)]
                    for a,b in zip(range(4),(1,2,3,0)):
                        style = ceramic[(i+k+row+col*2+(a%2 if row%2 else 0))%3]
                        # Blade depth brings out a visible shadow at street level.
                        prism('Breeze Block Diamonds',style,[outside[a],outside[b],inside[b],inside[a]],-5.223,-4.914)

    box('Roof Plant and Aerials',curb,(-1.06,1.51,22.09),(16.83,12.43,.28),.044)
    # One continuous parapet with no overlapping corner surfaces.
    for z,h,pad in ((22.18,.45,0),(22.621,.065,.025)):
        outer = [(-9.75-pad,-5.19-pad,z),(7.49+pad,-5.19-pad,z),
                 (7.49+pad,8.18+pad,z),(-9.75-pad,8.18+pad,z)]
        inner = [(-9.48+pad,-4.92+pad,z),(7.22-pad,-4.92+pad,z),
                 (7.22-pad,7.91-pad,z),(-9.48+pad,7.91-pad,z)]
        ring('Roof Plant and Aerials',concrete,outer,inner,h)
    box('Roof Plant and Aerials',concrete,(-2.71,3.79,23.33),(6.62,4.32,2.15),.064)
    box('Roof Plant and Aerials',dark,(-2.71,3.79,24.43),(6.81,4.49,.17),.036)
    louvre('Roof Plant and Aerials',shadow,dark,steel,-2.71,1.58,23.32,4.93,1.19,7)
    for side in (-1,1):
        x = -2.71+side*2.11
        rod('Roof Plant and Aerials',steel,(x,4.17,24.45),(x,4.17,27.12),.068,10)
        for y in (3.81,4.53):
            box('Roof Plant and Aerials',cream,(x,y,26.3),(.222,.119,1.18),.042)
        beam('Roof Plant and Aerials',steel,(x-.34,4.17,24.52),(x,4.17,25.51),.06)
    for x in (3.37,5.31):
        box('Roof Plant and Aerials',shadow,(x,-.09,22.72),(1.71,1.58,.94),.048)
        louvre('Roof Plant and Aerials',steel,dark,steel,x,-.908,22.76,1.45,.68,4)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, VIEW, RESOLUTION)
