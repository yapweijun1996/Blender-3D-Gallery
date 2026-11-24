"""sgmy-props-johor-belimbing-tree — original metric SG/MY static game prop, revision 1.
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

TITLE='Johor Belimbing • Fruiting Carambola'


def build():
    rng=random.Random(9806); bark=material('Warm fluted bark','735747',.92); twig=material('Young shoots','829054',.77)
    greens=palette([('Mature leaflet','326747'),('Emerald leaflet','478051'),('Sunlit leaflet','699755'),('New leaflet','93AB62')],rough=.6,two_sided=True)
    gold,ripe,unripe,edge=palette([('Starfruit ochre','D6A334'),('Golden starfruit','F4C34D'),('Unripe fruit','ACB953'),('Translucent rib','EFCE67')],rough=.32)
    pts=[(0,0,0),(.024,-.01,.16),(.052,.02,.54),(-.045,.04,1.00),(-.11,.01,1.48),(-.07,.11,1.94),(-.01,.17,2.31)]
    limb('Leaning trunk',pts,[.137,.100,.085,.070,.046,.027,.011],bark,'Trunk and limbs',12,flute=.11)
    for j in range(5):
        a=j*TAU/5; limb('Root flare',[(.23*cos(a),.23*sin(a),0),(.11*cos(a),.11*sin(a),.053),(.022,0,.19)],[.012,.044,.062],bark,'Trunk and limbs',8)
    def leaf(p,d,w,col):
        side=Vector((-d.y,d.x,0)).normalized(); vs=[]
        for t,ww,lift in ((0,.02,0),(.25,.76,.009),(.52,1,.011),(.83,.52,.004),(1,.02,-.006)):
            c=p+d*t+Vector((0,0,.014*sin(PI*t)+lift)); vs.extend([c-side*w*ww,c+Vector((0,0,w*.31*ww)),c+side*w*ww])
        mesh('Folded taper leaflet',vs,[(k*3+s,k*3+3+s,k*3+4+s,k*3+1+s) for k in range(4) for s in (0,1)],col,'Compound canopy',smooth=True)
    def spray(start,a,length):
        run=Vector((cos(a),sin(a),0))*length; side=Vector((-sin(a),cos(a),0)); ps=[start+run*t+Vector((0,0,.037*sin(t*PI)-.09*t*t)) for t in (0,.23,.46,.72,1)]; limb('Slender rachis',ps,[.0035,.0029,.0024,.0018,.0008],twig,'Leaf stems',5)
        for k in range(4):
            for s in (-1,1):
                t=.12+.205*k+.025*s; p=start+run*t+Vector((0,0,.037*sin(t*PI)-.09*t*t)); L=rng.uniform(.082,.123)*(1-.1*k/3); d=side*s*L+run*(.22+.10*t)+Vector((0,0,rng.uniform(-.052,.014))); leaf(p,d,.031*rng.uniform(.78,1.1),rng.choices(greens,[4,5,3,1])[0])
        leaf(ps[-1],run*.34+Vector((0,0,-.037)),.028,greens[rng.randrange(4)])
    def fruit(p,phase,scale,mat):
        length=.12*scale; sweep('Fruit stalk',[p,p+Vector((.006,-.004,-.031))],.0025,twig,'Fruit clusters',6); top=p+Vector((.006,-.004,-.027)); loops=[]
        for f,r in ((1,.003),(.89,.024),(.68,.039),(.33,.041),(.12,.028),(0,.006)):
            row=[]
            for k in range(20):
                a=k*TAU/20+phase; rr=r*scale*(1,.68,.56,.68)[k%4]; row.append(top+Vector((rr*cos(a)+.009*f*f,rr*sin(a),-length*f)))
            loops.append(row)
        ob=rings_mesh('Five winged starfruit',loops,mat,'Fruit clusters'); ob.data.materials.append(edge)
        for poly in list(ob.data.polygons)[2:]:
            if (poly.index-2)%4==0:poly.material_index=1
    for j in range(13):
        z=.54+.115*j; lo,hi=next((u,v) for u,v in zip(pts,pts[1:]) if u[2]<=z<=v[2]); base=Vector(lo).lerp(Vector(hi),(z-lo[2])/(hi[2]-lo[2])); a=j*2.399+.23*rng.random(); R=rng.uniform(.73,1.10)*(1-.44*j/13); rise=.85+.09*rng.random(); d=Vector((cos(a),sin(a),0)); side=Vector((-sin(a),cos(a),0)); end=base+d*R+Vector((0,0,rise)); mid=base+d*R*.37+Vector((0,0,rise*.62)); limb('Spreading bough',[base,mid,end],[.042*(1-.40*j/13),.028,.009],bark,'Trunk and limbs',9)
        for k in range(5):
            t=.36+.15*k; p=mid.lerp(end,max(0,(t-.37)/.63)); s=(-1)**k; b=a+s*rng.uniform(.58,1.3); reach=rng.uniform(.26,.42); v=Vector((cos(b)*reach,sin(b)*reach,rng.uniform(.14,.32))); branch=[p,p+v*.51+Vector((0,0,.03)),p+v]; limb('Fruiting twig',branch,[.016,.009,.0036],bark,'Trunk and limbs',7)
            for i in range(5): spray(p+v*(.21+i*.18),b+(-1)**i*rng.uniform(.55,1.26),rng.uniform(.21,.32))
            if k in (1,4) and j%3!=0:
                for i in range(rng.randint(2,3)):
                    fruit(p+v*(.28+.17*i),rng.uniform(0,TAU),rng.uniform(.85,1.12),rng.choice([ripe,ripe,gold,unripe]))
    deliver((.35,-1,.29),'BFC6B6',1.14)

if __name__ == '__main__':
    main()
