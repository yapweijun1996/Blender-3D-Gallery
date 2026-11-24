"""Build sgmy-props-estate-e-waste-bank, revision 1.

A floor-mounted bilingual estate e-waste cabinet with a recessed drop slot and fixed service door.
Static original Blender geometry and materials; no external inputs or logos.
Set the origin at ground level; metres, front -Y and up +Z in Blender.

Blender 5.2.3: blender -b --python-exit-code 1 --python generate.py
Produces model.glb (requires KHR_draco_mesh_compression) and preview.png.
Append `-- --export-only` or `-- --preview-only` to rebuild just one artifact.
Edit build() to revise the source; rerunning is a rebuild, not a saved-scene export.
Studio lights, camera and floor are preview-only. No colliders or gameplay logic.
"""

import math
import random
from collections import defaultdict
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

PI, TAU = math.pi, math.tau
sin, cos = math.sin, math.cos
PARTS = defaultdict(list)


def material(name, hex_color, rough=.5, metal=0, emission=0, two_sided=False):
    def linear(v):
        return v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4
    rgb = tuple(linear(int(hex_color[k:k+2], 16) / 255) for k in (0, 2, 4))
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    m.use_backface_culling = not two_sided
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = rough
    shader.inputs['Metallic'].default_value = metal
    if emission:
        shader.inputs['Emission Color'].default_value = (*rgb, 1)
        shader.inputs['Emission Strength'].default_value = emission
    return m


def palette(rows, **kwargs):
    return [material(name, color, **kwargs) for name, color in rows]


def mesh(name, vertices, faces, m, group, bevel=0, smooth=False, uv=None, slots=None, indices=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for mat in (slots or [m]):
        data.materials.append(mat)
    if indices is not None:
        data.polygons.foreach_set('material_index', indices)
    if smooth:
        data.polygons.foreach_set('use_smooth', [True]*len(data.polygons))
    if uv is not None:
        layer = data.uv_layers.new(name='UV0')
        layer.uv.foreach_set('vector', [v for i in data.loops for v in uv[i.vertex_index]])
    if bevel:
        mod = obj.modifiers.new('Edge Softening', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.harden_normals = True
    if group:
        PARTS[group].append(obj)
    return obj


def box(name, at, dims, m, group='Body', bevel=.008, yaw=0):
    a, b, c = [d/2 for d in dims]
    x, y, z = at
    vs = [(x + u*cos(yaw)-v*sin(yaw), y + u*sin(yaw)+v*cos(yaw), z+w)
          for w in (-c,c) for u,v in ((-a,-b),(a,-b),(a,b),(-a,b))]
    fs = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return mesh(name, vs, fs, m, group, bevel)


def rounded(w, h, r, steps=5):
    return [(cx+r*cos(a+k*PI/(2*steps)), cy+r*sin(a+k*PI/(2*steps)))
            for cx,cy,a in ((w/2-r,h/2-r,0),(-w/2+r,h/2-r,PI/2),
                           (-w/2+r,-h/2+r,PI),(w/2-r,-h/2+r,3*PI/2))
            for k in range(steps+1)]


def faceplate(name, at, w, h, depth, r, m, group='Details', axis='-Y', bevel=.0015):
    outline = rounded(w,h,r)
    x,y,z = at
    def place(u,v,k):
        if axis == '-Y':
            return x+u,y-k,z+v
        if axis == 'X':
            return x+k,y+u,z+v
        return x+u,y+v,z+k
    vs = [place(u,v,k) for k in (-depth/2,depth/2) for u,v in outline]
    n = len(outline)
    fs = [tuple(reversed(range(n))),tuple(range(n,2*n))]
    fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,vs,fs,m,group,min(depth*.3,bevel))


def turn(name, at, profile, m, group='Body', sides=24, axis=(0,0,1), closed=False):
    frame = Vector((0,0,1)).rotation_difference(Vector(axis)).to_matrix()
    vs = [Vector(at)+frame @ Vector((r*cos(TAU*i/sides),r*sin(TAU*i/sides),z))
          for r,z in profile for i in range(sides)]
    n=len(profile)
    fs = [] if closed else [tuple(reversed(range(sides))),tuple(range((n-1)*sides,n*sides))]
    fs.extend((k*sides+i,k*sides+(i+1)%sides,((k+1)%n)*sides+(i+1)%sides,((k+1)%n)*sides+i)
              for k in range(n if closed else n-1) for i in range(sides))
    obj = mesh(name,vs,fs,m,group,smooth=True)
    if not closed:
        for i in range(2):
            obj.data.polygons[i].use_smooth = False
    return obj


def limb(name, path, radii, m, group='Branches', sides=8, ref=(0,1,0), flute=0, slots=None, rng=None):
    ps = [Vector(p) for p in path]
    vs = []
    for i,p in enumerate(ps):
        t = (ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
        u = t.cross(Vector(ref))
        if u.length < .02:
            u = t.cross(Vector((1,0,0)))
        u.normalize()
        v = t.cross(u).normalized()
        a,b = radii[i] if isinstance(radii[i],tuple) else (radii[i],radii[i])
        for j in range(sides):
            angle = TAU*j/sides
            r = 1 + flute*(.65*sin(angle*5+.12*i)+.35*cos(angle*3-1))
            point = p+r*(u*a*cos(angle)+v*b*sin(angle))
            if i == 0 and p.z == 0:
                point.z = 0  # Seat slanted trunks and posts on the placement plane.
            vs.append(point)
    fs = [tuple(reversed(range(sides))), tuple(range(len(vs)-sides,len(vs)))]
    ids = [0,0]
    band = [rng.choices(range(len(slots)), (7,2,1))[0] for i in range(sides)] if slots else []
    for k in range(len(ps)-1):
        for i in range(sides):
            j = (i+1)%sides
            fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
            if slots:
                ids.append(band[i])
    obj=mesh(name,vs,fs,m,group,smooth=True,slots=slots,indices=ids if slots else None)
    for i in range(2):
        obj.data.polygons[i].use_smooth = False
    return obj


def rod(name, a, b, r, m, group='Hardware', sides=12):
    return limb(name,[a,b],[r,r],m,group,sides)


def oval(name, at, dims, m, group='Details', sides=12, rings=8, axis=(0,0,1)):
    x,y,z = (d/2 for d in dims)
    rot = Vector((0,0,1)).rotation_difference(Vector(axis)).to_matrix()
    vs = [Vector(at)+rot @ Vector((x*sin(p)*cos(a),y*sin(p)*sin(a),z*cos(p)))
          for p in (PI*k/rings for k in range(1,rings)) for a in (TAU*j/sides for j in range(sides))]
    vs += [Vector(at)+rot @ Vector((0,0,s*z)) for s in (1,-1)]
    fs = []
    for i in range(sides):
        j=(i+1)%sides
        fs += [(len(vs)-2,i,j),(len(vs)-1,(rings-2)*sides+j,(rings-2)*sides+i)]
        fs += [(k*sides+i,(k+1)*sides+i,(k+1)*sides+j,k*sides+j) for k in range(rings-2)]
    return mesh(name,vs,fs,m,group,smooth=True)


def text(line, at, size, m, group='Lettering', width=None, plane='-Y', yaw=0):
    font = bpy.data.curves.new(line, 'FONT')
    font.body = line
    font.align_x = 'CENTER'
    font.align_y = 'CENTER'
    font.size = size
    font.resolution_u = 4
    o = bpy.data.objects.new(line,font)
    bpy.context.collection.objects.link(o)
    o.location = at
    o.rotation_euler = (0 if plane == 'Z' else PI/2, 0, yaw if plane != 'X' else PI/2)
    if width:
        o['Max Width'] = width
    font.materials.append(m)
    PARTS[group].append(o)
    return o


def ribbon(name, points, widths, m, group='Graphics', normal=(0,-1,0)):
    ps=[Vector(p) for p in points]
    vs=[]
    for j,p in enumerate(ps):
        t=ps[min(j+1,len(ps)-1)]-ps[max(j-1,0)]
        n=Vector(normal).cross(t).normalized()
        vs.extend((p-n*widths[j]/2,p+n*widths[j]/2))
    return mesh(name,vs,[(i,i+2,i+3,i+1) for i in range(0,len(vs)-2,2)],m,group)


def bake():
    # Evaluate authored surfaces and combine by semantic group/material, holding the floor origin.
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    root = bpy.data.objects.new(TITLE,None)
    bpy.context.collection.objects.link(root)
    root['Asset ID'] = Path(__file__).resolve().parent.name
    root['Category'] = 'SG/MY Street Props'
    root['Placement'] = 'Metres; base origin; Blender -Y front, Z up; glTF +Z front, +Y up'
    result = []
    for group, parts in PARTS.items():
        verts, faces, normals, uv, mats, ids = [], [], [], [], [], []
        for part in parts:
            eval_part=part.evaluated_get(dg)
            src=eval_part.to_mesh()
            mw=eval_part.matrix_world.copy()
            if 'Max Width' in part and src.vertices:
                xs=[v.co.x for v in src.vertices]
                factor=min(1,part['Max Width']/max(max(xs)-min(xs),.0001))
                mw = mw @ Matrix.Diagonal((factor,1,1,1))
            nm=mw.to_3x3().inverted_safe().transposed()
            coords=[mw @ v.co for v in src.vertices]
            offset=len(verts)
            verts.extend(coords)
            src.calc_loop_triangles()
            uv0=src.uv_layers.active
            local_normals=src.corner_normals
            for tri in src.loop_triangles:
                p,q,r=(coords[i] for i in tri.vertices)
                normal=(q-p).cross(r-p)
                if normal.length_squared < 1e-19:
                    continue
                faces.append(tuple(i+offset for i in tri.vertices))
                mat=part.data.materials[tri.material_index]
                if mat not in mats:
                    mats.append(mat)
                ids.append(mats.index(mat))
                normals.extend((nm @ local_normals[i].vector).normalized() for i in tri.loops)
                if uv0:
                    uv.extend(c for i in tri.loops for c in uv0.uv[i].vector)
                else:
                    # Oriented planar UVs for solid-color geometry; no external atlases.
                    k=max(range(3),key=lambda i:abs(normal[i]))
                    a,b=(k+1)%3,(k+2)%3
                    sign = 1 if normal[k]>0 else -1
                    uv.extend(v for p in (p,q,r) for v in (p[a]*sign,p[b]))
            eval_part.to_mesh_clear()
        used=sorted({i for f in faces for i in f})
        index={old:new for new,old in enumerate(used)}
        o=mesh(group,[verts[i] for i in used],[tuple(index[i] for i in f) for f in faces],
               None,None,smooth=True,slots=mats,indices=ids)
        o.data.uv_layers.new(name='UV0').uv.foreach_set('vector',uv)
        o.data.normals_split_custom_set(normals)
        o.parent=root
        result.append(o)
    # Leave all source objects linked until the last evaluated mesh has been read.
    for parts in PARTS.values():
        for part in parts:
            bpy.data.objects.remove(part,do_unlink=True)
    return result


def studio(objs, direction, backdrop, margin):
    scene=bpy.context.scene
    coords=[v.co for o in objs for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in coords) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in coords) for i in range(3)))
    center=(lo+hi)/2
    span=max(hi-lo)
    view=Vector(direction).normalized()
    rotation=(-view).to_track_quat('-Z','Y')
    projected=[rotation.inverted() @ (v-center) for v in coords]
    lo2=[min(p[i] for p in projected) for i in (0,1)]
    hi2=[max(p[i] for p in projected) for i in (0,1)]
    target=center+rotation @ Vector(((lo2[0]+hi2[0])/2,(lo2[1]+hi2[1])/2,0))
    camera=bpy.data.objects.new('Preview Camera',bpy.data.cameras.new('Orthographic Lens'))
    scene.collection.objects.link(camera)
    camera.location=target+view*span*3
    camera.rotation_euler=rotation.to_euler()
    camera.data.type='ORTHO'
    camera.data.clip_end = max(100,span*9)
    camera.data.ortho_scale=margin*max(hi2[0]-lo2[0],(hi2[1]-lo2[1])*1.2)
    scene.camera=camera
    box('Studio Floor',(0,0,-.013*span),(span*120,span*120,.0258*span),
        material('Preview Backdrop',backdrop,.82,emission=.35),None,0)
    world=bpy.data.worlds.new('Studio Ambient')
    scene.world=world
    world.use_nodes=True
    bg=world.node_tree.nodes['Background']
    bg.inputs[0].default_value=(.48,.55,.63,1)
    bg.inputs[1].default_value=.32
    def area(name,offset,power,size,color):
        data=bpy.data.lights.new(name,'AREA')
        o=bpy.data.objects.new(name,data)
        scene.collection.objects.link(o)
        o.location=center+Vector(offset)*span
        o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
        data.energy=power*span**2
        data.shape='DISK'
        data.size=size*span
        data.color=color
    area('Warm Softbox',(-.75,-1.05,1.25),131,1.09,(1,.88,.74))
    area('Cool Fill',(1.1,-.45,.51),55,1.25,(.77,.87,1))
    area('High Edge Light',(.48,1.03,1.3),173,1.05,(1,.94,.81))
    scene.render.engine='BLENDER_EEVEE'
    scene.eevee.taa_render_samples=40
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.37
    scene.render.resolution_x=1080
    scene.render.resolution_y=900
    scene.render.resolution_percentage=100
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.compression=65
    return scene


def deliver(direction, backdrop='BFC7C2', margin=1.16):
    objs=bake()
    out=Path(__file__).resolve().parent
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    print(f'{TITLE}: {sum(len(o.data.polygons) for o in objs):,} triangles')
    if '--preview-only' not in args:
        glb=out/'model.glb'
        bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',export_extras=True,
                                  export_draco_mesh_compression_enable=True,
                                  export_draco_mesh_compression_level=6,
                                  export_draco_position_quantization=18,
                                  export_draco_normal_quantization=12,
                                  export_draco_texcoord_quantization=16,
                                  export_animations=False,export_cameras=False,export_lights=False)
        assert glb.stat().st_size<=2_000_000
    if '--export-only' not in args:
        scene=studio(objs,direction,backdrop,margin)
        scene.render.filepath=str(out/'preview.png')
        bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    build()



TITLE = 'Estate E-waste Bank'


def build():
    blue,deep,light,charcoal,lime,cream,silver = palette([
        ('Ocean Blue Enamel','177784'),('Deep Teal Galvanised Shell','194D58'),('Marine Blue Edge','2B91A1'),
        ('Recycled Rubber and Chute Shadow','192830'),('Chartreuse Safety Insert','D6D96E'),
        ('Ivory Screen-Printed Ink','F0EEDB'),('Satin Steel Fasteners','A4B7B9')])
    silver.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value=.55
    box('Flush dark plinth',(0,0,.061),(.798,.604,.122),charcoal,bevel=.014)
    box('Drain clearance recess',(0,.011,.107),(.735,.571,.094),deep)
    box('Powder coated cabinet',(0,.019,.777),(.839,.621,1.328),deep,bevel=.016)
    box('Inset service door',(0,-.301,.546),(.765,.054,.842),blue,bevel=.014,group='Service Door')
    box('Door top safety reveal',(0,-.330,.935),(.728,.009,.020),lime,group='Service Door',bevel=.002)
    box('Chute pocket',(0,-.309,1.093),(.657,.044,.307),charcoal,group='Deposit Pocket')
    for s in (-1,1):
        box('Chute jamb',(s*.355,-.329,1.108),(.123,.074,.350),blue,group='Deposit Pocket')
    box('Above aperture',(0,-.334,1.300),(.825,.077,.222),blue,group='Deposit Pocket',bevel=.006)
    box('Below aperture',(0,-.335,1.003),(.734,.079,.091),blue,group='Deposit Pocket',bevel=.006)
    lip=[(-.302,-.337,1.039),(.302,-.337,1.039),(.302,-.371,1.016),(-.302,-.371,1.016),
         (-.302,-.350,1.003),(.302,-.350,1.003)]
    mesh('Pressed angled safety chute lip',lip,[(0,3,2,1),(3,4,5,2),(0,1,5,4),(0,4,3),(1,2,5)],
         lime,'Deposit Pocket',.003)
    box('Interior feed baffle',(0,-.333,1.150),(.599,.019,.078),deep,group='Deposit Pocket',bevel=.006)
    # Shed roof projects past the door and keeps water off the seam.
    roof=[(x,y,z) for x in (-.438,.438) for y,z in ((-.384,1.401),(.364,1.401),(.343,1.450),(-.331,1.513))]
    mesh('Formed rain-shedding cap',roof,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],
         light,'Cabinet Cap',.010)
    faceplate('Dual-language header',(0,-.377,1.303),.675,.151,.010,.022,deep)
    text('E-WASTE', (0,-.383,1.328),.085,cream,width=.568)
    text('SISA ELEKTRONIK', (0,-.383,1.267),.031,lime,width=.57)
    faceplate('Screen print label',(0,-.330,.575),.580,.407,.004,.025,deep)
    faceplate('Icon field',(0,-.333,.654),.142,.125,.002,.016,lime)
    # An original wall plug pictogram; no brand or municipal insignia.
    faceplate('Plug housing',(0,-.335,.659),.060,.045,.002,.010,deep)
    for s in (-1,1):
        box('Plug pin',(s*.016,-.336,.690),(.008,.002,.024),deep,'Graphics',.0005)
    ribbon('Plug cord',[(0,-.337,.640),(0,-.337,.620),(.027,-.337,.614)], [.010]*3,deep)
    text('UNPLUG & RECYCLE',(0,-.335,.552),.036,cream,width=.510)
    text('KABEL  /  TELEFON  /  PENGECAS',(0,-.335,.499),.020,cream,width=.50)
    text('ESTATE COLLECTION  •  07',(0,-.333,.282),.020,cream,width=.46)
    faceplate('Flush service latch',(-.338,-.334,.570),.046,.121,.013,.012,charcoal)
    turn('Cylinder lock',(-.338,-.345,.572),[(.012,0),(.012,.005),(.010,.007)],silver,'Hardware',16,(0,-1,0))
    box('Lock keyway',(-.338,-.353,.572),(.0025,.002,.011),charcoal,'Hardware',.001)
    for z in (.273,.815):
        turn('Service door exposed hinge',(.378,-.323,z),[(.015,-.039),(.017,-.034),(.017,.035),(.015,.040)],silver,'Hardware',12)
    for s in (-1,1):
        box('Side seam guard',(s*.421,.020,.750),(.028,.550,1.199),blue,group='Side Panels',bevel=.008)
        for z in (.362,.399,.436,.473):
            box('Louver slot',(s*.436,.059,z),(.002,.319,.015),charcoal,group='Side Panels',bevel=.0005)
            box('Louver drip hood',(s*.440,.059,z+.013),(.013,.332,.012),light,group='Side Panels',bevel=.003)
    faceplate('Side stream plate',(.438,-.035,.938),.366,.177,.008,.013,deep,'Side Panels',axis='X')
    text('07',(.444,-.035,.94),.116,lime,'Side Panels',plane='X')
    for x in (-.381,.381):
        for z in (1.345,1.245):
            turn('Door trim rivet',(x,-.375,z),[(.008,-.001),(.008,.003),(.006,.004)],silver,'Hardware',12,(0,-1,0))
    deliver((.57,-1,.38),'C5C7C1',1.18)


if __name__ == "__main__":
    main()
