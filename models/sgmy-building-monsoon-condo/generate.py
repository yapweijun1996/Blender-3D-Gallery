"""Monsoon Court — original procedural SG/MY streetscape asset.
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


def palm(sec, bark, foliage, xyz, height, phase=0):
    x,y,z = xyz
    prev = (x,y,z)
    for i in range(1,6):
        t = i/5
        q = (x+.14*height*t*t,y+.025*height*t,z+height*t)
        rod(sec,bark,prev,q,height*(.040-.018*t),8,.91)
        prev = q
    head = Vector(prev)
    for i in range(9):
        a = phase+i*TAU/9
        u = Vector((math.cos(a),math.sin(a),0))
        v = Vector((-math.sin(a),math.cos(a),0))
        length = height*(.64+.046*((i*3)%7))
        verts = []
        for j,w in enumerate((.015,.075,.10,.084,.051,.001)):
            t = j/5
            p = head + u*(length*t) + Vector((0,0,length*(1.05*t-1.33*t*t)))
            verts.extend((p-v*w*length,p+Vector((0,0,length*w*.3)),p+v*w*length))
        faces = [(3*j+k,3*j+k+1,3*(j+1)+k+1,3*(j+1)+k) for j in range(5) for k in range(2)]
        add(sec,foliage[i%len(foliage)],verts,faces)

SLUG = 'sgmy-building-monsoon-condo'
TITLE = 'Monsoon Court | Tropical Condominium'


def terrace(sec, mat, x, y, w, d, z, thick, clip):
    x0,x1,y0,y1 = x-w/2,x+w/2,y-d/2,y+d/2
    xy = [(x0+clip,y0),(x1-clip,y0),(x1,y0+clip),(x1,y1-clip),
          (x1-clip,y1),(x0+clip,y1),(x0,y1-clip),(x0,y0+clip)]
    points = [(a,b,k) for k in (z-thick,z) for a,b in xy]
    faces = [tuple(reversed(range(8))),tuple(range(8,16))]
    faces += [(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
    add(sec,mat,points,faces)
    return xy


def balustrade(sec, rail, cap, xy, z, h=.96, edges=None):
    for i,(a,b) in enumerate(zip(xy,xy[1:]+xy[:1])):
        if edges is not None and i not in edges:
            continue
        ax,ay = a
        bx,by = b
        length = math.hypot(bx-ax,by-ay)
        yaw = math.atan2(by-ay,bx-ax)
        n = max(1,round(length/1.58))
        for j in range(n):
            t = (j+.5)/n
            p = (ax+t*(bx-ax),ay+t*(by-ay),z+h/2+.055)
            box(sec,rail,p,(length/n-.06,.075,h-.08),yaw=yaw)
            if j != n-1:
                t = (j+1)/n
                box(sec,cap,(ax+t*(bx-ax),ay+t*(by-ay),z+h/2+.075),(.049,.11,h),yaw=yaw)
        box(sec,cap,((ax+bx)/2,(ay+by)/2,z+h+.05),(length+.015,.115,.086),yaw=yaw)


def build():
    p, front, bal, fins, roof, garden, pool = 'Podium and Entry','Curtain Wall and Suites','Balcony Slabs and Guards','Screens and Risers','Sky Canopy','Sky Gardens and Palms','Pool Terrace'
    ivory = material('Warm Precast Band','ddd9c6')
    plaster = material('Sand Coloured Render','aaa395')
    graphite = material('Graphite Aluminium','3c494b',.43,.28)
    sand = material('Honed Sandstone','b7a991')
    timber = material('Merbau Solar Fins','9e6b43',.56)
    lightwood = material('Weathered Decking','ad8e68')
    panes = [material(n,c,.26,.22) for n,c in [('Blue Green Glazing','45767d'),('Ocean Glazing','39606b'),('Sky Glazing','66949a'),('Cloud Reflection','8caaaa')]]
    rail = material('Sea Glass Guards','79a8aa',.28,.14)
    water = material('Pool Surface','399896',.21,.24)
    mosaic = material('Lagoon Mosaic','2c6469',.51)
    leaf = [material(n,c) for n,c in [('Young Palm Leaves','789149'),('Palm Leaves','4b663d'),('Deep Jade Leaves','416050')]]
    dirt = material('Dark Planter Soil','685846')
    bark = material('Ringed Palm Stems','7d7551')
    block(p,plaster,-15.8,16,-11.8,11.9,0,.28,.14)
    block(p,sand,-15.56,15.77,-11.52,11.69,.28,.43,.067)
    block(p,graphite,-13.4,4.23,-6.85,7.7,.43,4.52,.08)
    block(p,ivory,-14.12,5.02,-8.0,8.42,4.27,4.81,.16)
    block(p,plaster,-13.8,4.7,-7.86,8.18,4.81,5.08,.09)
    for y in (-6.929,7.79):
        for j in range(11):
            x = -12.66+j*1.6
            box(p,panes[(j*3+1)%4],(x,y,2.3),(1.46,.185,3.16),.025)
            box(p,ivory,(x-.81,y,2.4),(.16,.285,3.64),.016)
    for x in (-13.5,4.34):
        for j in range(8):
            y = -6.11+j*1.83
            box(p,panes[(j+2)%4],(x,y,2.3),(.215,1.69,3.16),.025)
    box(p,ivory,(-4.38,-9.07,3.73),(9.26,4.12,.28),.09)
    box(p,timber,(-4.38,-9.1,3.55),(8.91,3.98,.10),.033)
    for x in (-8.53,-.23):
        box(p,graphite,(x,-10.32,1.97),(.23,.27,3.13),.023)
    box(p,graphite,(-4.38,-8.36,.516),(5.18,3.09,.16),.021)
    box(p,graphite,(-4.38,-11.175,3.76),(4.83,.11,.47),.019)
    sign(p,ivory,'MONSOON COURT',(-4.38,-11.24,3.76),4.54,.26)
    # Two offset stacks are tied together by a glazed lift and service spine.
    z0,dz,count = 5.08,3.06,18
    top = z0+dz*count
    block(fins,graphite,-6.95,-2.48,-3.4,5.95,4.87,top+2.0,.10)
    for j in range(count):
        z=z0+j*dz
        for y in (-3.52,6.06):
            box(fins,panes[(j+1)%3],(-4.52,y,z+1.55),(2.48,.19,2.67),.022)
            box(fins,graphite,(-4.52,y+(.13 if y>0 else -.13),z+1.55),(.12,.08,2.65))
        for i in range(7):
            box(fins,timber,(-5.94+i*.44,6.28,z+1.54),(.12,.37,2.85),.016)
    for volume,(cx,cy,w,d,levels,recess) in enumerate(((-9.08,-.98,9.22,11.5,count,(7,)),
                                                      (.18,1.17,8.58,11.9,count-2,(5,13)))):
        for j in range(levels):
            z = z0+dz*j
            shift = (.37 if j%4 in (1,2) else -.13) * (1 if volume else -1)
            bx,by = cx+shift,cy+(.20 if j%3==0 else 0)
            plan = terrace(bal,ivory,bx,by,w,d,z+.14,.27,.79 if volume else 1.0)
            guard = [(bx+.948*(x-bx),by+.956*(y-by)) for x,y in plan]
            balustrade(bal,rail,graphite,guard,z+.14,edges=(0,1,2,3,4,5,6,7))
            if j in recess:
                for x in (cx-w*.33,cx+w*.33):
                    for y in (cy-d*.3,cy+d*.3):
                        box(garden,ivory,(x,y,z+1.52),(.32,.39,2.82),.025)
                for k in range(4):
                    x = cx+(k-1.5)*1.76
                    y = cy-d*.346 if k%2==0 else cy+d*.34
                    box(garden,plaster,(x,y,z+.36),(1.42,.94,.44),.07)
                    box(garden,dirt,(x,y,z+.59),(1.27,.81,.053),.015)
                    palm(garden,bark,leaf,(x,y,z+.59),1.53,k+.4)
                for x in (cx-w*.32,cx+w*.32):
                    box(garden,timber,(x,cy,z+.66),(1.54,.50,.14),.033)
                    for y in (-.1,.1):
                        box(garden,graphite,(x,cy+y,z+.33),(1.3,.093,.4),.014)
                continue
            # Recessed opaque backpan preserves glass legibility in inexpensive web renderers.
            iw,idp = w-1.68,d-2.10
            box(front,graphite,(cx,cy,z+1.55),(iw,idp,2.83),.045)
            for side in (-1,1):
                y = cy+side*(idp/2+.047)
                for k in range(5):
                    x = cx+(k-2)*iw/5
                    box(front,panes[(k*13+j*7+volume+int(side>0)+k*j)%4],(x,y,z+1.58),(iw/5-.082,.104,2.68))
                x = cx+side*(iw/2+.047)
                for k in range(6):
                    y = cy+(k-2.5)*idp/6
                    box(front,panes[(k+j*3+int(side>0)+volume)%4],(x,y,z+1.58),(.104,idp/6-.082,2.68))
            for side in (-1,1):
                for k in range(3):
                    x = cx+side*w*.33 + (k-1)*.20
                    box(fins,timber,(x,cy-d/2+1.13,z+1.55),(.09,.39,2.81),.013)
            if j%3==1:
                for side in (-1,1):
                    x = cx-side*w*.31
                    y = cy+d*.401
                    box(garden,plaster,(x,y,z+.38),(1.53,.43,.51),.022)
                    for k in range(4):
                        lathe(garden,leaf[(k+j)%3],x+(k-1.5)*.33,y,[(z+.62,.18),(z+.86,.26),(z+1.06,.09)],6,k)
        z = z0+dz*levels
        xy = terrace(roof,ivory,cx,cy,w+.23,d+.23,z+.27,.34,1.0)
        balustrade(roof,rail,graphite,[(cx+.94*(x-cx),cy+.94*(y-cy)) for x,y in xy],z+.27)
        block(roof,plaster,cx-w*.19,cx+w*.23,cy-d*.18,cy+d*.30,z+.27,z+2.64,.095)
        for x in (cx-w*.39,cx+w*.39):
            for y in (cy-d*.38,cy+d*.38):
                box(roof,ivory,(x,y,z+1.98),(.30,.37,3.41),.038)
            box(roof,ivory,(x,cy,z+3.6),(.27,d*.84,.3),.057)
        for k in range(15):
            y = cy+(k-7)*d*.055
            box(roof,ivory,(cx,y,z+3.75),(w*.86,.24,.24),.048)
            box(roof,timber,(cx,y+.13,z+3.68),(w*.78,.085,.11),.017)
        for x in (cx-w*.3,cx+w*.31):
            box(garden,plaster,(x,cy-d*.30,z+.58),(2.2,1.05,.58),.07)
            palm(garden,bark,leaf,(x,cy-d*.30,z+.86),1.7,x)
    # Pool is recessed inside its coping; the water is an opaque low-cost material.
    block(pool,mosaic,6.6,14.22,-6.4,5.94,.425,.5,.022)
    block(pool,water,6.97,13.85,-6.04,5.58,.498,.515)
    for x in (6.76,14.05):
        box(pool,ivory,(x,-.23,.525),(.36,12.35,.165),.037)
    for y in (-6.23,5.78):
        box(pool,ivory,(10.4,y,.525),(7.1,.35,.165),.036)
    for x in (7.33,13.49):
        box(pool,mosaic,(x,-.23,.515),(.071,11.425,.003))
    for k in range(21):
        x = 6.63+k*.378
        for y in (-7.25,6.64):
            box(pool,lightwood,(x,y,.457),(.354,1.37,.06),.012)
    for x,y in ((-12.82,-9.83),(10.9,-9.42),(13.6,-9.42),(7.38,8.74),(12.94,8.76)):
        box(garden,plaster,(x,y,.72),(1.96,1.45,.58),.11)
        box(garden,dirt,(x,y,1.016),(1.7,1.23,.08),.033)
        palm(garden,bark,leaf,(x,y,1.025),2.77,(x+y)*.34)
    for x in (7.86,9.77,11.72,13.62):
        for d in (-.4,.4):
            box(pool,graphite,(x,7.26+d,.57),(.57,.12,.23),.018)
        box(pool,ivory,(x,7.19,.753),(.58,1.29,.13),.055)
        beam(pool,ivory,(x,7.53,.79),(x,7.88,1.13),.58,.115,.04)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, (.7,-1,.53), (980,1120))
