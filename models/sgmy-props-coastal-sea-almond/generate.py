"""Build sgmy-props-coastal-sea-almond, revision 1.

Ketapang (Terminalia catappa), a coastal shade tree with spreading, stepped branch tiers.
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


Z = Vector((0,0,1))


def bearing(a):
    return Vector((cos(a),sin(a),0))


def bezier(points,t):
    a,b,c,d = (Vector(v) for v in points)
    u=1-t
    return a*u**3+3*b*u*u*t+3*c*u*t*t+d*t**3


class LeafBed:
    """Ribbed two-sided leaf surfaces with local, per-leaf UVs and a colored blade fold."""
    def __init__(self, slots):
        self.slots=slots
        self.v,self.f,self.uv,self.ids=[],[],[],[]

    def blade(self,path,side,width,tone,steps=5,shape=.78,ridge=.12,twist=0,notch=None):
        side=Vector(side).normalized()
        base=len(self.v)
        notch=notch or {}
        for i in range(steps+1):
            t=i/steps
            p=bezier(path,t)
            forward=(bezier(path,min(1,t+.013))-bezier(path,max(0,t-.013))).normalized()
            axis=(side-side.dot(forward)*forward).normalized()
            normal=forward.cross(axis).normalized()
            bank=axis*cos(twist*t)+normal*sin(twist*t)
            arch=forward.cross(bank)
            spread=width*(.012+.988*sin(PI*t)**shape)
            for h in (-1,0,1):
                dent=notch.get((i,h),1)
                self.v.append(p+bank*(spread*h*dent)+arch*(ridge*spread*(1-abs(h))-.05*spread*h*h))
                self.uv.append(((h+1)/2,t))
            if i:
                j=base+3*i
                self.f.extend(((j-3,j,j+1,j-2),(j-2,j+1,j+2,j-1)))
                self.ids.extend((tone, max(0,tone-1)))

    def build(self,name,group):
        mesh(name,self.v,self.f,None,group,smooth=True,uv=self.uv,slots=self.slots,indices=self.ids)


def leaf_spray(leaves, center, rng, n, radius, scale, tone_bias=0):
    a=rng.uniform(0,TAU)
    normal=Vector((0,0,1))
    for j in range(n):
        angle=a+2.40*j+rng.uniform(-.29,.29)
        d=bearing(angle)
        p=center+d*rng.uniform(.04,radius)+Z*rng.uniform(-radius*.55,radius*.65)
        length=scale*rng.uniform(.65,1.31)
        rise=rng.uniform(-.64,.54)*length
        path=(p,p+d*length*.36+normal*length*.27,
              p+d*length*.76+normal*rise*.60,p+d*length+normal*rise)
        tone=max(0,min(len(leaves.slots)-1,rng.randrange(len(leaves.slots))+tone_bias))
        leaves.blade(path,normal.cross(d),length*rng.uniform(.14,.26),tone,steps=4,
                     shape=.8,twist=rng.uniform(-.58,.58))


TITLE = 'Coastal Sea Almond'


def build():
    rng=random.Random(7291)
    bark=palette([('Sea Almond Weathered Bark','686157'),('Ash Bark Highlight','736856'),
                  ('Bark Furrow','595244')],rough=.83)
    foliage=palette([('Ketapang Shadow','204C37'),('Ketapang Green','3C673D'),('Ketapang Lime','54773A'),
                     ('Ketapang New Growth','718E43'),('Old Leaf Bronze','B27239'),
                     ('Old Leaf Paprika','974B33')],two_sided=True,rough=.61)
    leaves=LeafBed(foliage)
    trunk=[(0,0,0),(-.046,.062,.49),(-.089,.10,1.55),(-.13,.07,2.84),(-.10,-.03,4.37),
           (.03,-.10,5.43),(.19,-.12,6.56),(.18,-.10,7.30)]
    limb('Coarsely fissured central leader',trunk,[.52,.37,.28,.24,.192,.125,.077,.026],
         bark[0],'Trunk and Root Flare',19,flute=.12,slots=bark,rng=rng)
    for i in range(6):
        d=bearing(i*TAU/6+rng.uniform(-.24,.25))
        toe=d*rng.uniform(.67,.93)
        # Profile radii are flattened near ground; the upright central bole owns the plant pivot.
        limb('Low run of a buttress root',[d*.15+Z*.57,d*.38+Z*.19,toe*.83+Z*.083,toe+Z*.034],
             [(.14,.11),(.12,.10),(.087,.052),(.035,.024)],bark[0],'Trunk and Root Flare',8,
             ref=(0,0,1),flute=.19)
    levels=[(3.24,3.15,7),(4.73,2.55,7),(5.98,1.94,6),(7.08,1.25,5)]
    for layer,(z,reach,count) in enumerate(levels):
        for i in range(count):
            angle=(i+layer*.38)*TAU/count+rng.uniform(-.15,.15)
            d=bearing(angle)
            s=Z.cross(d)
            p=Vector((-.10+.085*layer,-.02,z+rng.uniform(-.17,.17)))
            L=reach*rng.uniform(.83,1.12)
            elbow=p+d*.42*L+Z*.37
            wrist=p+d*.79*L+s*rng.uniform(-.16,.16)+Z*.47
            end=p+d*L+Z*rng.uniform(.56,.85)
            radius=(.146-.026*layer)*rng.uniform(.83,1.04)
            limb('Tiered horizontal scaffold',[p,elbow,wrist,end],[radius,radius*.66,radius*.36,.007],
                 bark[0],'Tiered Branches',9,ref=(0,0,1),flute=.11)
            # Forked terminal branchlets carry flattened leaf whorls, typical of Terminalia catappa.
            for j in range(5):
                side=(-1 if j%2 else 1)
                t=.28+j*.15
                start=p.lerp(end,t)+Z*(.19*sin(PI*t))
                tip=start+(s*side*rng.uniform(.45,.77)+d*rng.uniform(.31,.57))*L/2.75+Z*rng.uniform(.28,.68)
                middle=(start+tip)*.5+Z*.09
                limb('Twig rising to terminal rosette',[start,middle,tip],[radius*.29,.022,.006],
                     bark[0],'Tiered Branches',6,ref=(0,0,1))
                for k in range(3):
                    f=(tip-middle).normalized()
                    c=middle.lerp(tip,.31+k*.38)+s*rng.uniform(-.22,.22)+f*rng.uniform(-.11,.18)
                    a=angle+rng.uniform(0,TAU)
                    for q in range(rng.randint(6,8)):
                        d2=bearing(a+q*.90+rng.uniform(-.22,.24))
                        length=rng.uniform(.24,.46)
                        rise=rng.uniform(-.22,.15)
                        pp=c+d2*rng.uniform(0,.13)+Z*rng.uniform(-.10,.10)
                        path=(pp,pp+d2*length*.39+Z*.10,pp+d2*length*.76+Z*rise*.4,pp+d2*length+Z*rise)
                        tone=rng.choices((1,2,3,4,5),(17,34,35,6,3))[0]
                        leaves.blade(path,Z.cross(d2),length*rng.uniform(.205,.315),tone,steps=4,
                                     shape=.58,twist=rng.uniform(-.67,.64))
            finish=random.Random(12190+layer*67+i)
            for j in range(11):
                spray=bearing(j*2.40+angle)
                pp=end+spray*finish.uniform(.025,.11)+Z*finish.uniform(-.065,.086)
                length=finish.uniform(.26,.45)
                tip=pp+spray*length+Z*finish.uniform(-.12,.095)
                leaves.blade((pp,pp+spray*length*.37+Z*.089,pp.lerp(tip,.72),tip),Z.cross(spray),
                             length*.29,1+j%3,steps=4,shape=.58,twist=finish.uniform(-.35,.41))
    leaves.build('Umbrella tier leaf whorls','Ketapang Foliage')
    deliver((.62,-1,.34),'C0CCC7',1.15)


if __name__ == "__main__":
    main()
