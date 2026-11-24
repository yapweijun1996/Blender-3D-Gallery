"""Build sgmy-props-kampung-papaya, revision 1: Kampung Papaya.

Original procedural mesh and palette; no external images, fonts, or models.
Metric, origin at ground level, Z up and -Y front. Static visual prop only.
Rebuild: blender -b --factory-startup --python-exit-code 1 --python generate.py
Use -- --export-only or -- --preview-only for a single output. GLB requires Draco.
The studio floor, lights and camera are added after export.
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
    camera.data.clip_start = .001
    camera.data.clip_end = max(100,span*9)
    camera.data.ortho_scale=margin*max(hi2[0]-lo2[0],(hi2[1]-lo2[1])*1.2)
    scene.camera=camera
    box('Studio Floor',(0,0,-.013*span),(span*120,span*120,.0258*span),
        material('Preview Backdrop',backdrop,.82,emission=.04),None,0)
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
    scene.cycles.samples=16
    scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.85
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


def tube(name, points, radius, mat, group, sides=10):
    return limb(name,points,[radius]*len(points),mat,group,sides,ref=(0.13,0.81,0.57))


TITLE = 'Kampung Papaya'


def build():
    rng=random.Random(7319)
    bark, scar, petiole, green, ripe, blush = palette([('Pawpaw olive bark','8D8D71'),('Corky leaf scars','AFA784'),('Lime petiole','9DB467'),('Unripe papaya','768E43'),('Ripening ochre skin','DBAD4C'),('Papaya yellow','E5BB58')])
    leaves=palette([('Mature lamina','21593D'),('Mature lamina light','346C41'),('New lamina','467C3E'),('New lamina light','629345')],two_sided=True,rough=.77)
    for m in leaves: m.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.20
    path=[(0,0,0),(-.025,.018,.17),(-.033,.009,.52),(-.022,-.01,1.05),(.032,.005,1.58),(.073,.003,2.10),(.075,0,2.48)]
    limb('Soft fluted bole',path,[.15,.116,.091,.084,.076,.068,.051],bark,'Trunk',18,flute=.038)
    def trunk(z):
        for a,b in zip(path,path[1:]):
            if a[2]<=z<=b[2]: return Vector(a).lerp(Vector(b),(z-a[2])/(b[2]-a[2]))
    # Crescent-shaped scars spiral up the trunk where old leaf stems detached.
    for k in range(45):
        z=.15+k*.047; a=k*2.40; c=trunk(z); r=next(ra+(rb-ra)*(z-p[2])/(q[2]-p[2]) for p,q,ra,rb in zip(path,path[1:],[.15,.116,.091,.084,.076,.068],[.116,.091,.084,.076,.068,.051]) if p[2]<=z<=q[2])-.001; points=[]
        for j in range(7):
            u=(j-3)/3; t=a+u*.69; points.append(c+Vector((r*cos(t),r*sin(t),.015*u*u)))
        limb('Leaf scar',points,[.002,.006,.009,.010,.009,.006,.002],scar,'Trunk markings',7)
    for k in range(15):
        a=k*2.400; z=1.96+.031*k; c=trunk(z); d=Vector((cos(a),sin(a),0)); ln=(.39 if k<6 else .30 if k<11 else .20)*rng.uniform(.90,1.07); stem=c+d*.115; stem.z+=.082
        tube('Fruit stalk',[c+d*.053,stem,stem+d*.035-Vector((0,0,.023))],.011,petiole,'Fruit cluster')
        axis=(.23*cos(a),.23*sin(a),-1); r=ln*.305; p=stem+d*.035-Vector((0,0,.018));
        turn('Pear-shaped papaya',p,[(r*.22,0),(r*.43,ln*.07),(r*.69,ln*.20),(r*.92,ln*.42),(r,ln*.62),(r*.92,ln*.78),(r*.64,ln*.94),(r*.20,ln)],(ripe if k in (0,2) else blush if k==1 else green),'Fruit cluster',24,axis)
    def leaf(k,z,reach,rise,span,young):
        a=k*2.399+rng.uniform(-.13,.13); d=Vector((cos(a),sin(a),0)); t=Vector((-sin(a),cos(a),0)); c=trunk(z); tip=c+d*reach+Vector((0,0,rise));
        limb('Hollow petiole',[c+d*.036,c+d*(reach*.33)+Vector((0,0,rise*.58+.04)),tip],[.023,.016,.009],petiole,'Leaf stalks',10)
        mats=leaves[2:] if young else leaves[:2]
        # Seven deep, pointed lobes share a folded basal fan. Serrated shoulders
        # and secondary points cut a recognisably palmate silhouette against the sky.
        n=7; angles=[(j-3)*.65 for j in range(n)]; vs=[tip]; fs=[]; ids=[]; roots=[]
        for j in range(n+1):
            b=angles[0]-.325+j*.65; v=tip+(d*cos(b)+t*sin(b))*span*.23+Vector((0,0,.021)); roots.append(v); vs.append(v)
            if j: fs.append((0,j,j+1)); ids.append(j%2)
        mesh('Central leaf web',vs,fs,None,'Palmate leaves',slots=mats,indices=ids)
        for j,b in enumerate(angles):
            ray=d*cos(b)+t*sin(b); side=t*cos(b)-d*sin(b); length=span*(1-.12*abs(j-3));
            mid=tip+ray*span*.216+Vector((0,0,.027)); verts=[roots[j],mid,roots[j+1]]; faces=[]; mi=[]
            for f,w in ((.17,.13),(.26,.11),(.40,.18),(.44,.078),(.62,.134),(.65,.060),(.82,.080),(1,.002)):
                p=tip+ray*(span*.216+f*(length-span*.216))+Vector((0,0,.026+.075*sin(PI*f)-(.045 if young else .135)*f*f)); wid=w*length
                verts.extend((p-side*wid-Vector((0,0,wid*.19)),p,p+side*wid-Vector((0,0,wid*.30))))
            for h in range(0,len(verts)-3,3): faces.extend(((h,h+3,h+4,h+1),(h+1,h+4,h+5,h+2))); mi.extend((0,1))
            mesh('Dissected leaf lobe',verts,faces,None,'Palmate leaves',slots=mats,indices=mi)
            limb('Pale leaf vein',[tip+Vector((0,0,.003)),mid+Vector((0,0,.003)),verts[10]+Vector((0,0,.003))],[.0045,.003,.0008],petiole,'Leaf veins',6)
    for k in range(19):
        f=k/18; leaf(k,2.13+.345*f,.77-.48*f,-.14+.69*f,(.68-.25*f)*rng.uniform(.93,1.09),k>12)
    deliver((.55,-1,.47),'AAA997',1.13)


if __name__ == "__main__":
    main()
