"""sgmy-props-kampar-claypot-rice — original metric SG/MY static game prop, revision 1.
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

TITLE='Kampar Claypot Rice'


def build():
    rng=random.Random(340); g='Smoke fired casserole'
    clay,lip,black,rice,soy,meat,skin,lap,fat,green,reed=palette([('Red earthenware','A5522D'),('Salt glaze','75341F'),('Smoked umber','422B25'),('Pearl rice','FFF0CD'),('Dark soy rice','C9925C'),('Chicken flesh','C78C56'),('Glazed chicken skin','AD592B'),('Lap cheong','A44336'),('Sausage fat','F8BF97'),('Spring onion','559341'),('Rattan straw','D4A457')],rough=.42)
    # Low braided heat mat clears the table below the hot stoneware foot.
    disc('Wicker core',(0,0,.005),.088,.010,reed,'Trivet',sides=64)
    for r in (.074,.086):
        for j in (0,1):
            pts=[]
            for i in range(121):
                a=TAU*i/120; b=a*25+j*PI; rr=r+.0022*cos(b); pts.append((rr*cos(a),rr*sin(a),.006+.0022*sin(b)))
            sweep('Two ply coil',pts,.0024,reed,'Trivet',6)
    turn('Blackened base',(0,0,.010),[(.065,0),(.070,.002),(.077,.007),(.089,.019),(.095,.030)],black,g,80)
    turn('Sloping clay wall',(0,0,.010),[(.093,.026),(.097,.031),(.107,.055),(.109,.071),(.111,.073),(.111,.078),(.108,.080),(.103,.079),(.101,.071),(.097,.052),(.089,.036)],clay,g,80)
    for h,r in ((.068,.1075),(.073,.1085),(.087,.110)):
        hoop('Throwing line',(0,0,h),r,.0013,lip,g,80)
    turn('Hollow taper handle',(.092,0,.064),[(.017,0),(.020,.014),(.015,.034),(.012,.08),(.014,.087),(.013,.092),(.008,.093),(.006,.084)],clay,g,32,(1,0,.19))
    base=.085
    oval('Bed of soy rice',(0,0,base-.004),(.103,.103,.015),rice,'Rice and crust',sides=64,rings=12)
    for k in range(385):
        r=.100*rng.random()**.5; a=rng.random()*TAU; h=base-.004+.015*(1-(r/.103)**2)**.5
        oval('Separate grain',(r*cos(a),r*sin(a),h),(.0037,.00135,.0012),rice if rng.random()<.65 else soy,'Rice and crust',rng.uniform(0,TAU),rng.uniform(-.2,.2),6,3)
    tops=[]
    for k in range(8):
        x=(k%3-1)*.029+.009+rng.uniform(-.003,.003); y=(k//3-1)*.023; a=rng.uniform(-1,1); h=.099+.005*rng.random()
        # Uneven cleaver-cut pieces with drawn, caramelised skin.
        outline=[(-.017,-.008),(-.009,-.014),(.013,-.011),(.020,-.003),(.014,.009),(.002,.014),(-.014,.010)]
        levels=[]
        for scale,dz in ((.76,-.004),(1,.001),(.93,.011),(.70,.015),(.28,.017)):
            levels.append([(x+scale*(u*cos(a)-v*sin(a)),y+scale*(v*cos(a)+u*sin(a)),h+dz+.0017*sin(i*2+a)) for i,(u,v) in enumerate(outline)])
        ob=rings_mesh('Glazed chicken chunk',levels,skin,'Soy chicken'); ob.data.materials.append(meat)
        for f in list(ob.data.polygons)[2:13]: f.material_index=1
        for i in (-1,1):
            sweep('Caramelised crease',[(x+s*.009*cos(a)-i*.003*sin(a),y+s*.009*sin(a)+i*.003*cos(a),h+.017-.0015*abs(s)) for s in (-1,0,1)],.00065,lip,'Soy chicken',6)
        tops.append((x,y,h+.017))
    for k in range(7):
        a=PI*.62+k*.33; x=.068*cos(a); y=.063*sin(a); h=.097+.0014*k
        turn('Lap cheong slice',(x,y,h),[(.013,-.003),(.014,-.002),(.014,.0025),(.013,.0038)],lap,'Cured sausage',24)
        for j in range(4):
            t=rng.random()*TAU; d=rng.uniform(.002,.008); oval('Fat fleck',(x+d*cos(t),y+d*sin(t),h+.0038),(.0016,.001,.00055),fat,'Cured sausage',t,sides=8,rings=4)
    for k in range(27):
        x,y,h=rng.choice(tops); x+=rng.uniform(-.008,.008); y+=rng.uniform(-.007,.007)
        hoop('Scallion ring',(x,y,h+.0003),rng.uniform(.0018,.0032),.00085,green,'Scallion rings',12,(.15,.22,1))
    # Matching stepped lid leans against the back-left shoulder, showing its throwing marks.
    axis=Vector((-.78,-.30,.55)).normalized(); p=Vector((-.126,.064,.088))
    turn('Domed lid',p,[(.097,-.003),(.105,0),(.106,.005),(.102,.008),(.09,.010),(.079,.017),(.06,.022),(.029,.026),(.012,.026)],lip,'Resting cover',80,axis)
    for r,h in ((.101,.008),(.086,.0125),(.067,.021)):
        hoop('Glaze bead',p+axis*h,r,.0011,clay,'Resting cover',80,axis)
    turn('Clay button',p+axis*.025,[(.015,0),(.011,.005),(.017,.014),(.017,.017),(.014,.019)],clay,'Resting cover',36,axis)
    deliver((.35,-1,.78),'BCB5A6')

if __name__ == '__main__':
    main()
