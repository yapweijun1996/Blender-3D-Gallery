"""sgmy-props-kebun-baru-merbok-cage — original metric SG/MY static game prop, revision 1.
Rebuild: blender -b --factory-startup --python-exit-code 1 --python generate.py
Pass -- --export-only or -- --preview-only for a single artifact. Original solid-color
meshes with UV0; no external art or textures. Blender -Y front, Z up, base origin.
Draco decoder required. Dimensions authored in metres. Studio excluded from export.
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


def box(name, at, dims, m, group='Body', bevel=.003, yaw=0):
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


def bake():
    # Evaluate authored surfaces and combine by semantic group/material, holding the floor origin.
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    root = bpy.data.objects.new(TITLE,None)
    bpy.context.collection.objects.link(root)
    root['Asset ID'] = Path(__file__).resolve().parent.name
    root['Revision'] = 1
    root['Role'] = 'Static visual mesh; no gameplay or collider'
    root['Category'] = 'SG/MY Street Props'
    root['origin_note'] = 'Metres; base origin; Blender -Y front, Z up; glTF +Z front, +Y up'
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
    camera.data.clip_start = .001
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
    scene.render.engine='CYCLES'
    scene.cycles.samples=10
    scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.91
    scene.render.resolution_x=864
    scene.render.resolution_y=720
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


def tube(name, points, radius, mat, group, sides=10):
    return limb(name,points,[radius]*len(points),mat,group,sides,ref=(0.13,0.81,0.57))


def hoop(name, at, radius, wire, mat, group, sides=64, axis=(0,0,1)):
    profile=[(radius+wire*cos(TAU*i/10),wire*sin(TAU*i/10)) for i in range(10)]
    return turn(name,at,profile,mat,group,sides,axis,True)


def disc(name, at, r, h, mat, group, axis=(0,0,1), sides=48):
    return turn(name,at,[(r,-h/2),(r,h/2)],mat,group,sides,axis)



def oval(name, at, radii, mat, group, yaw=0, tilt=0, sides=16, rings=8):
    # A closed gridded ellipsoid with two single-vertex poles, rotated in world space.
    frame=Matrix.Rotation(yaw,3,'Z') @ Matrix.Rotation(tilt,3,'Y')
    at=Vector(at); a,b,c=radii
    def pos(x,y,z): return at+frame @ Vector((a*x,b*y,c*z))
    verts=[pos(0,0,-1)]
    for k in range(1,rings):
        v=PI*(k/rings-.5)
        verts.extend(pos(cos(v)*cos(i*TAU/sides),cos(v)*sin(i*TAU/sides),sin(v)) for i in range(sides))
    verts.append(pos(0,0,1)); faces=[]
    for i in range(sides):
        j=(i+1)%sides; faces.append((0,j+1,i+1))
        for k in range(rings-2):
            u=1+k*sides; faces.append((u+i,u+j,u+sides+j,u+sides+i))
        u=1+(rings-2)*sides; faces.append((u+i,u+j,len(verts)-1))
    return mesh(name,verts,faces,mat,group,smooth=True)


def legend(text, at, size, mat, group, angle=PI/2):
    font=bpy.data.curves.new('Sign lettering','FONT'); font.body=text
    font.align_x='CENTER'; font.align_y='CENTER'; font.size=size
    font.resolution_u=4; font.materials.append(mat)
    ob=bpy.data.objects.new('Inscription',font); bpy.context.collection.objects.link(ob)
    ob.location=at; ob.rotation_euler.x=angle; PARTS[group].append(ob)


def sweep(name, points, radius, mat, group, sides=8):
    return tube(name,points,radius,mat,group,sides)


def rings_mesh(name, rings, mat, group, smooth=True):
    n=len(rings[0]); verts=sum(rings,[])
    faces=[tuple(reversed(range(n))),tuple(range(len(verts)-n,len(verts)))]
    faces += [(r*n+i,r*n+(i+1)%n,(r+1)*n+(i+1)%n,(r+1)*n+i) for r in range(len(rings)-1) for i in range(n)]
    return mesh(name,verts,faces,mat,group,smooth=smooth)

TITLE='Kebun Baru • Merbok Songbird Cage'


def build():
    cane,reed,wood,dark,gold,jade,ivory,blue,seed=palette([('Split bamboo','CA9B59'),('Golden cane','E0BB76'),('Chengal wood','895239'),('Lacquered mahogany','59372D'),('Aged brass','BD9653'),('Jade enamel','2E7773'),('Rice porcelain','EEE2BF'),('Indigo brushwork','367886'),('Millet grain','D3AD62')],rough=.39)
    g='Turned base'
    for i in range(3):
        a=TAU*i/3-PI/2;turn('Bun foot',(.121*cos(a),.121*sin(a),0),[(.016,0),(.018,.003),(.020,.008),(.019,.011),(.015,.017),(.014,.021)],dark,g,24)
    turn('Removable tray',(0,0,.019),[(.132,0),(.146,.003),(.156,.011),(.154,.016),(.152,.018),(.153,.036),(.158,.040),(.159,.046),(.153,.050),(.145,.049),(.143,.038),(.140,.023),(.030,.023)],wood,g,80)
    for r,z,m in ((.151,.030,dark),(.154,.035,gold),(.154,.054,dark),(.156,.064,gold)):
        hoop('Inlaid band',(0,0,z),r,.0017,m,g,80)
    for i in range(40):
        a=i*TAU/40; x=.154*cos(a); y=.154*sin(a); oval('Shell lozenge',(x,y,.044),(.0045,.0012,.0025),ivory,g,a+PI/2,sides=8,rings=4)
    points=[(.148,.061),(.150,.09),(.151,.16),(.151,.238),(.149,.283),(.142,.31),(.129,.334),(.108,.353),(.079,.370),(.048,.381),(.025,.385)]
    for i in range(48):
        a=i*TAU/48-PI/2
        # Five rods become door spindles set in the arched frame below.
        path=[(r*cos(a),r*sin(a),z) for r,z in points];sweep('Domed cage stave',path,.00155,cane if i%4 else reed,'Crown staves',7)
    for r,h,w,m in ((.149,.076,.0023,wood),(.152,.152,.002,cane),(.152,.158,.002,cane),(.152,.250,.0034,wood),(.152,.257,.0018,reed),(.129,.335,.0026,cane),(.080,.370,.002,reed)):
        hoop('Bound bamboo hoop',(0,0,h),r,w,m,'Hoop bindings',80)
    # Sliding arched front wicket and engraved competition number on its lower rail.
    for dx in (-.052,.052):
        y=-math.sqrt(.151**2-dx**2); sweep('Wicket side',[(dx,y-.002,.067),(dx,y-.004,.211)],.0041,wood,'Door and badge',10)
    arch=[(.052*cos(a),-.148-.007*sin(a),.211+.037*sin(a)) for a in [PI*k/24 for k in range(25)]];sweep('Door arch',arch,.0041,wood,'Door and badge',10)
    for z in (.082,.180): sweep('Door rail',[(.052*cos(a),-.146-.009*sin(a),z) for a in [PI*k/12 for k in range(13)]],.0033,wood,'Door and badge',8)
    faceplate('Oval number surround',(0,-.157,.108),.093,.072,.006,.025,gold,'Door and badge',bevel=.001)
    faceplate('Jade number field',(0,-.161,.108),.087,.066,.004,.023,jade,'Door and badge',bevel=.0007)
    legend('K E B U N   B A R U',(0,-.1632,.128),.0078,ivory,'Door and badge');legend('27',(0,-.1632,.104),.036,ivory,'Door and badge');legend('M E R B O K',(0,-.1632,.085),.0067,ivory,'Door and badge')
    sweep('Natural perch',[(-.129,.065,.152),(-.067,.046,.157),(-.009,.026,.160),(.041,0,.156),(.142,-.041,.145)],.0058,wood,'Perch and cups',10)
    for i,(x,y) in enumerate(((-.095,-.069),(.081,-.083))):
        turn('Glazed feed cup',(x,y,.11),[(.015,0),(.020,.002),(.023,.008),(.026,.022),(.027,.027),(.026,.030),(.022,.029),(.019,.012),(.013,.006)],ivory,'Perch and cups',40)
        hoop('Blue lip',(x,y,.139),.0245,.0017,blue,'Perch and cups',40);hoop('Cup holder',(x,y,.123),.0247,.0015,gold,'Perch and cups',40)
        sweep('Cup support',[(x,y,.122),(x*1.16,y*1.16,.124),(x*1.28,y*1.28,.137)],.0025,gold,'Perch and cups')
        for k in range(10):
            a=TAU*k/10;oval('Painted petal',(x+.024*cos(a),y+.024*sin(a),.129),(.0025,.001,.003),blue,'Perch and cups',a+PI/2,sides=10,rings=5)
        if i==0:
            for k in range(32):
                a=k*2.399;r=.017*math.sqrt(k/32);oval('Millet',(x+r*cos(a),y+r*sin(a),.133),(.0028,.002,.0019),seed,'Perch and cups',a,sides=6,rings=4)
    turn('Crown rose',(0,0,.379),[(.032,0),(.037,.003),(.035,.007),(.029,.012),(.021,.015),(.018,.021),(.015,.023)],wood,'Crown and hanger',48)
    turn('Porcelain finial',(0,0,.400),[(.011,0),(.012,.002),(.009,.006),(.014,.011),(.016,.019),(.013,.028),(.009,.031),(.009,.035)],jade,'Crown and hanger',36)
    for z in (.406,.432):hoop('Finial collar',(0,0,z),.010,.0013,gold,'Crown and hanger',36)
    # Open brass carrying hook with a returned tip, not a solid decorative handle.
    path=[(0,0,.434),(0,0,.449),(.004,0,.457),(.014,0,.466),(.022,0,.476),(.024,0,.486),(.022,0,.497),(.015,0,.505),(.005,0,.51),(-.006,0,.509),(-.014,0,.504),(-.018,0,.497),(-.018,0,.490)];sweep('Swept hanger hook',path,.0037,gold,'Crown and hanger',12)
    oval('Hook bead',path[-1],(.005,.005,.005),wood,'Crown and hanger')
    deliver((.38,-1,.35),'B9C1B5')

if __name__ == '__main__':
    main()
