"""Rumah Pucuk — original procedural SG/MY streetscape asset.
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

SLUG = 'sgmy-building-stilted-kampung'
TITLE = 'Rumah Pucuk | Stilted Kampung House'


def zinc_gable(sec, metals, fascia, x, y0, y1, eave, peak, halfw):
    # Folded edge, ribbed zinc panels, and exposed timber battens.
    for s in (-1,1):
        prism(sec,fascia,[(x,peak-.022),(x+s*(halfw-.035),eave-.026),
                          (x+s*(halfw-.035),eave-.128),(x,peak-.126)],y0+.02,y1-.02)
    n = round((y1-y0)/.65)
    for i in range(n):
        a,b = y0+(y1-y0)*i/n,y0+(y1-y0)*(i+1)/n
        for s in (-1,1):
            poly = [(x,eave+(peak-eave)),(x+s*halfw,eave),
                    (x+s*halfw,eave-.083),(x,peak-.083)]
            prism(sec,metals[(i*7+int(s>0)+i//3)%len(metals)],poly,a,b-.006)
        for s in (-1,1):
            for j in range(3):
                y = a+(b-a)*(j+.08)/3
                rod(sec,metals[1+i%2],(x,y,peak+.027),(x+s*halfw,y,eave+.024),.027,6)
    rod(sec,metals[0],(x,y0-.04,peak+.078),(x,y1+.05,peak+.078),.095,10)
    for y in (y0,y1):
        for s in (-1,1):
            beam(sec,fascia,(x,y,peak-.086),(x+s*(halfw+.07),y,eave-.11),.20,.14,.021)
            beam(sec,metals[0],(x,y-.04,peak+.023),(x+s*(halfw+.10),y-.04,eave+.026),.094,.132,.015)
    for s in (-1,1):
        box(sec,fascia,(x+s*halfw,(y0+y1)/2,eave-.137),(.124,y1-y0+.11,.227),.021)


def build():
    frame, boards, porch, joinery, gables, roof, ground = 'Raised Hardwood Frame','Shiplap Wall Boards','Serambi and Entry Stair','Louvred Timber Joinery','Gable Fretwork','Ribbed Zinc Roofs','Under-House Fittings'
    timber = material('Dark Chengal Framing','634a37')
    railing = material('Golden Varnished Hardwood','af8151')
    warm = material('Oxidized Meranti','9c6449')
    deck = [material(n,c) for n,c in [('Merbau Floorboards','a77751'),('Honey Floorboards','b4875e'),('Shaded Floorboards','986b4c')]]
    boards_m = [material(n,c) for n,c in [('Sage Timber Paint','758775'),('Cool Sage Timber Paint','718477'),('Bright Sage Timber Paint','819382'),('Sea Green Timber Paint','758b80')]]
    cream = material('Buttercream Wood Trim','e1c497')
    blue = material('Blue Green Louver Paint','315e58')
    sky = material('Shutter Edges','507c69')
    shadow = material('Dark Window Recess','353c32')
    zinc = [material(n,c,.51,.36) for n,c in [('Oxide Zinc Flashing','704b3e'),('Painted Zinc','8c5745'),('Weathered Zinc','976654'),('Light Oxide Zinc','916051')]]
    foot = material('Pier Foot Concrete','949183')
    pots = material('Earthenware','98613e')
    lids = material('Dark Kiln Glaze','52594a',.33)
    for x in (-3.64,0,3.64):
        for y in (-4.1,-.86,2.94,4.25):
            box(frame,foot,(x,y,.115),(.58,.58,.23),.055)
            block(frame,timber,x-.122,x+.122,y-.124,y+.124,.20,1.62,.018)
            for s in (-1,1):
                if (x<3.64 and s==1) or (x>-3.64 and s==-1):
                    beam(frame,timber,(x,y,.89),(x+s*.7,y,1.48),.115,.096,.009)
        box(frame,timber,(x,-.06,1.48),(.24,9.78,.31),.028)
    for y in (-3.95,-.8,2.95,4.16,4.62):
        box(frame,warm,(0,y,1.55),(8.04,.23,.25),.026)
    block(frame,timber,-4.03,4.03,-4.72,4.73,1.57,1.68,.025)
    # Continuous sills hide the smaller opaque wall backpans.
    block(boards,shadow,-3.85,3.85,-4.54,4.54,1.68,4.19,.024)
    for k in range(11):
        z = 1.79+k*.22
        for s in (-1,1):
            box(boards,boards_m[(k+int(s<0))%4],(0,s*4.547,z),(7.72,.10,.214),.009)
            box(boards,boards_m[(k+2*int(s<0))%4],(s*3.853,0,z),(.11,9.08,.213),.009)
    for x in (-3.93,3.93):
        for y in (-4.6,4.6):
            box(boards,warm,(x,y,2.92),(.22,.22,2.54),.019)
    for s in (-1,1):
        box(boards,warm,(s*3.91,0,1.73),(.194,9.34,.15),.021)
        box(boards,warm,(s*3.94,0,4.15),(.229,9.46,.21),.022)
        box(boards,warm,(0,s*4.647,4.153),(7.81,.18,.23),.025)
    # Main gables and cut fretwork under deeply overhanging eaves.
    for y in (-4.66,4.66):
        s = 1 if y>0 else -1
        prism(gables,timber,[(-3.83,4.15),(3.83,4.15),(0,7.02)],y-.09,y+.09)
        for j in range(-15,16):
            x = j*.238
            z1 = 6.99 - .735*abs(x)
            block(gables,warm if j%4 else timber,x-.111,x+.111,y+s*.11-.023,y+s*.11+.023,4.2,z1,.008)
        for i in range(3):
            w = (1.85,1.33,.71)[i]
            z = 4.55+i*.265
            box(gables,blue,(0,y+s*.158,z),(w*2+.16,.075,.23),.013)
            for j in range(-int(w/.22),int(w/.22)+1):
                box(gables,cream,(j*.22,y+s*.209,z),(.11,.035,.102),.006,yaw=0,
                    basis=Matrix.Rotation(.785,3,'Y'))
        for sg in (-1,1):
            beam(gables,cream,(0,y+s*.21,7.08),(sg*3.88,y+s*.21,4.22),.105,.11,.015)
    zinc_gable(roof,zinc,railing,0,-5.34,5.45,4.12,7.52,4.725)
    # Front serambi is held by separate slender posts. Its lower roof is cross-banded with a pierced fascia.
    for x in (-3.27,3.27,-1.18,1.18):
        box(frame,foot,(x,-6.22,.108),(.49,.46,.216),.045)
        box(frame,timber,(x,-6.22,.857),(.172,.194,1.47),.019)
        box(porch,railing,(x,-6.22,2.61),(.148,.165,1.89),.016)
        box(porch,cream,(x,-6.22,3.46),(.235,.25,.14),.015)
    for j in range(26):
        box(porch,deck[j%3],((j-12.5)*.256,-5.54,1.634),(.247,2.13,.132),.01)
    box(porch,warm,(0,-6.53,1.57),(6.72,.225,.24),.029)
    for y in (-6.31,-4.59):
        box(porch,warm,(0,y,3.48),(6.7,.23,.20),.022)
    for s in (-1,1):
        for z in (1.82,2.57):
            box(porch,railing,(s*2.262,-6.35,z),(2.058,.118,.105),.014)
            box(porch,railing,(s*3.29,-5.47,z),(.115,1.72,.10),.015)
        for j in range(12):
            box(porch,sky,(s*(1.32+j*.173),-6.35,2.18),(.074,.087,.687),.014)
        for j in range(8):
            box(porch,sky,(s*3.29,-6.175+j*.202,2.18),(.083,.075,.69),.016)
    zinc_gable(roof,zinc,railing,0,-6.98,-4.16,3.49,5.45,3.79)
    prism(gables,warm,[(-3.23,3.47),(3.23,3.47),(0,5.19)],-6.245,-6.13)
    for x in (-2.14,-1.70,-1.26,-.82,-.38,.38,.82,1.26,1.70,2.14):
        box(gables,blue,(x,-6.27,3.84),(.32,.063,.203),.016)
        box(gables,cream,(x,-6.313,3.84),(.118,.031,.118),.009,basis=Matrix.Rotation(math.pi/4,3,'Y'))
    for j in range(9):
        y=-8.97+j*.291
        z=(j+1)*.18
        box(porch,deck[j%3],(0,y,z-.056),(1.85,.308,.112),.022)
    for x in (-.79,.79):
        beam(porch,timber,(x,-9.14,.14),(x,-6.53,1.6),.18,.22,.015)
    for x in (-.958,.958):
        beam(porch,railing,(x,-8.97,.97),(x,-6.49,2.63),.098,.095,.017)
        for j in (0,2,4,6,8):
            y=-8.97+j*.291
            z=(j+1)*.18
            box(porch,warm,(x,y,z+.412),(.097,.105,.869),.014)
    box(joinery,cream,(0,-4.638,2.79),(1.50,.182,2.24),.026)
    for x in (-.325,.325):
        box(joinery,blue,(x,-4.744,2.76),(.622,.083,2.12),.023)
        for z in (2.18,3.05):
            box(joinery,sky,(x,-4.791,z),(.49,.035,.64),.016)
        box(joinery,railing,(x*.45,-4.838,2.64),(.06,.055,.179),.013)
    for wall in range(4):
        theta = math.pi/2*wall
        for u in ((-2.29,2.29) if wall%2==0 else (-2.75,.12,2.82)):
            def local(mat,x,z,w,h,d=.10,inset=0,bevel=.013):
                y = -(4.62 if wall%2==0 else 3.948)-inset
                box(joinery,mat,(x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta),z),
                    (w,d,h),bevel,yaw=theta)
            local(cream,u,2.94,1.61,1.85,.167,0,.025)
            local(blue,u,2.92,1.37,1.606,.108,.10,.02)
            for dx in (-.35,.35):
                for k in range(9):
                    local(sky,u+dx,2.28+k*.157,.51,.104,.078,.177,.008)
            local(railing,u,2.02,1.71,.12,.293,.015,.022)
            for k in range(6):
                local(warm,u+(k-2.5)*.24,3.99,.151,.15,.069,.001,.017)
    for x,y in ((2.82,-7.19),(3.3,-7.04)):
        lathe(ground,pots,x,y,[(0,.169),(.12,.23),(.37,.337),(.63,.283),(.71,.171)],18)
        lathe(ground,lids,x,y,[(.716,.181),(.742,.205),(.783,.140),(.802,.051)],18)
    for x in (-2.82,-1.49):
        box(ground,timber,(x,-4.83,.25),(.13,.4,.5),.021)
    for j in range(3):
        box(ground,deck[j],(-2.14,-4.99+j*.153,.527),(1.83,.135,.094),.021)


if __name__ == '__main__':
    scene = reset()
    build()
    finalize(scene)
    preview(scene, (.73,-1,.49), (1120,920))
