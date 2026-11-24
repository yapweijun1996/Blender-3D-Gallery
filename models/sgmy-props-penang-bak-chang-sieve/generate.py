"""Penang Bak Chang Bamboo Sieve | sgmy-props-penang-bak-chang-sieve, revision 1.
Original procedural visual prop. Metres; +Z up, -Y front, origin at base.
Rebuild: blender -b --factory-startup --python-exit-code 1 -P generate.py
Optional: -- --export-only or -- --preview-only. No external assets. Requires Draco.
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


def rod(name, a, b, r, m, group='Hardware', sides=12):
    return limb(name,[a,b],[r,r],m,group,sides)


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
    floor_z=min(v.co.z for o in result for v in o.data.vertices)
    for o in result:
        o.data.transform(Matrix.Translation((0,0,-floor_z)))
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
    scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.53
    scene.render.resolution_x=720
    scene.render.resolution_y=600
    scene.render.resolution_percentage=100
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.compression=95
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
        quantize_png(out/'preview.png')


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    build()


def oval(name, at, radii, m, group, yaw=0, tilt=0, rings=12, sides=24):
    # A closed ellipsoid with single pole vertices.
    rx, ry, rz = radii
    vs = [(0,0,-rz)]
    for j in range(1,rings):
        a = -PI/2+PI*j/rings
        vs += [(rx*cos(a)*cos(i*TAU/sides), ry*cos(a)*sin(i*TAU/sides), rz*sin(a)) for i in range(sides)]
    vs.append((0,0,rz)); top=len(vs)-1
    fs = [(0,1+(i+1)%sides,1+i) for i in range(sides)]
    for j in range(rings-2):
        k=1+j*sides
        fs.extend((k+i,k+(i+1)%sides,k+sides+(i+1)%sides,k+sides+i) for i in range(sides))
    fs.extend((top,top-sides+i,top-sides+(i+1)%sides) for i in range(sides))
    o=mesh(name,vs,fs,m,group,smooth=True); o.location=at; o.rotation_euler=(0,tilt,yaw)
    return o


def leaf(name, base, angle, length, width, lift, droop, mat, vein, group, broad=.8):
    # A ridged, curved blade; its narrowing tip turns down at the end.
    vs=[]; fs=[]; rib=[]; base=Vector(base)
    d=Vector((cos(angle),sin(angle),0)); side=Vector((-d.y,d.x,0))
    for j in range(11):
        t=j/10; w=width*(max(.012,sin(PI*t**broad)))**.8
        c=base+d*length*t+Vector((0,0,lift*t-droop*t*t)); rib.append(c+Vector((0,0,.002*length)))
        for k in (-1,0,1):
            vs.append(c+side*w*k+Vector((0,0,-w*(.20+.11*sin(2*PI*t))*abs(k))))
        if j:
            a=3*(j-1); fs.extend([(a,a+3,a+4,a+1),(a+1,a+4,a+5,a+2)])
    mesh(name,vs,fs,mat,group,smooth=True)
    if vein: limb('Midrib',rib,[length*(.009*(1-j/11)+.001) for j in range(11)],vein,group,6)
    return rib[-1]


def quantize_png(path):
    """Keep full RGB gradients, reducing only low bits until the card fits."""
    if path.stat().st_size <= 250000: return
    import numpy as np
    import struct, zlib
    im=bpy.data.images.load(str(path),check_existing=False)
    im.colorspace_settings.name='Non-Color'  # The input is already display-encoded.
    w,h=im.size; buf=np.empty(w*h*4,dtype=np.float32); im.pixels.foreach_get(buf)
    rgb=np.uint16(np.clip(buf.reshape(h,w,4)[::-1,:,:3]*255+.5,0,255)); bpy.data.images.remove(im)
    def chunk(t,data):
        return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data))
    for drop in range(5):
        step=1<<drop; pic=np.uint8(np.minimum(255,((rgb+step//2)//step)*step))
        # Per scanline, choose between horizontal and vertical prediction.
        left=np.zeros_like(pic); left[:,1:]=pic[:,:-1]
        up=np.zeros_like(pic); up[1:]=pic[:-1]
        a,b=pic-left,pic-up
        cost=lambda v: np.abs(v.view('int8').astype('int16')).sum(axis=(1,2))
        horizontal=cost(a)<cost(b)
        raw=b''.join((b'\1'+a[j].tobytes()) if horizontal[j] else (b'\2'+b[j].tobytes()) for j in range(h))
        image=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'sRGB',b'\0')+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
        if len(image)<=250000:
            path.write_bytes(image); return
    raise ValueError('Preview exceeds the gallery size budget')


def bead(name, xyz, r, thick, mat, group, sides=64, axis=(0,0,1)):
    profile=[(r+thick*cos(TAU*j/8),thick*sin(TAU*j/8)) for j in range(8)]
    return turn(name,xyz,profile,mat,group,sides,axis,True)


def sweep(name, pts, radii, mat, group, sides=8):
    # Catmull-Rom curve with interpolated thickness.
    p=[Vector(q) for q in pts]; samples=[]; rs=[]
    for i in range(len(p)-1):
        a,b,c,d=p[max(0,i-1)],p[i],p[i+1],p[min(i+2,len(p)-1)]
        for j in range(4):
            t=j/4; samples.append(.5*(2*b+(c-a)*t+(2*a-5*b+4*c-d)*t*t+(3*b-a-3*c+d)*t**3));rs.append(radii[i]*(1-t)+radii[i+1]*t)
    return limb(name,samples+[p[-1]],rs+[radii[-1]],mat,group,sides)


def ribbon(name, centers, offsets, mat, group):
    vertices=[Vector(p)+Vector(w)*s for p,w in zip(centers,offsets) for s in (-1,1)]
    return mesh(name,vertices,[(j,j+1,j+3,j+2) for j in range(0,len(vertices)-2,2)],mat,group,smooth=True)

TITLE = 'Penang Bak Chang Bamboo Sieve'


def build():
    bamboo,reed,rim,lash=palette([('Split bamboo','C89F64'),('Honey reed','DCB981'),('Bent hoop','97613E'),('Hoop binding','5A4639')],two_sided=True); leafm=palette([('Steamed bamboo leaf','717841'),('Olive leaf fold','86834B'),('Dark folded edge','58653F'),('Parallel leaf veins','98925B')]); cord=material('Cotton kitchen twine','E5D4AD',.86);g='Woven sieve';r=.167
    for k in range(-15,16):
        y=k*.0104; l=math.sqrt(r*r-y*y)
        for axis in range(2):
            path=[]; offsets=[]
            for j in range(51):
                x=l*(2*j/50-1);z=.010+.002*(1 if not axis else -1)*cos(PI*x/.0104+PI*k)+.001*axis
                path.append((y,x,z) if axis else (x,y,z));offsets.append((.004,0,.0002) if axis else (0,.004,.0002))
            # Each strip crosses alternately under and over the perpendicular family.
            ribbon('Over-under floor strip',path,offsets,reed if (axis+k)%3 else bamboo,g)
    for z,R,w in ((.005,.162,.0045),(.016,.167,.004),(.035,.173,.006),(.043,.175,.0045)):bead('Rigid tray hoop',(0,0,z),R,w,rim,g,96)
    for k in range(84):
        a=TAU*k/84;b=a+.032
        rod('Diagonal side weave',(.164*cos(a),.164*sin(a),.009),(.175*cos(b),.175*sin(b),.040),.003,bamboo if k%3 else reed,g,7)
        if k%7<2:rod('Hoop tie',(.17*cos(a),.17*sin(a),.032),(.177*cos(a),.177*sin(a),.046),.002,lash,g,7)
    rng=random.Random(130); v=Vector
    def parcel(cx,cy,z,yaw,scale):
        def P(x,y,h):return v((cx+scale*(cos(yaw)*x-sin(yaw)*y),cy+scale*(sin(yaw)*x+cos(yaw)*y),z+h*scale))
        corners=[P(-.064,-.038,.003),P(.062,-.043,0),P(.012,.070,.002)];apex=P(-.017,.005,.106); ctr=sum(corners,v())/3
        mesh('Four folded faces',corners+[apex],[(2,1,0),(0,1,3),(1,2,3),(2,0,3)],leafm[0],'Wrapped parcels',.0032,slots=leafm[:3],indices=[2,0,1,0])
        for k in range(3):
            A,B=corners[k],corners[(k+1)%3]; N=(B-A).cross(apex-A).normalized(); off=N*.0006
            def uv(u,v):return A+(B-A)*u+(apex-A)*v+off
            # Diagonal end flap with a cut trailing edge, then fine longitudinal striations.
            mesh('Fold over', [uv(.035,.04),uv(.88,.055),uv(.22,.60)],[(0,1,2)],leafm[(k+1)%3],'Wrapped parcels')
            for i in range(1,14):
                u=i/15; v1=(1-u)*.74; p=uv(u,.028)+N*.0004;q=uv(u*.93,v1)+N*.0004
                rod('Bamboo leaf vein',p,q,.00029,leafm[3 if i%4==0 else 2],'Veins',5)
        mid=[corners[k].lerp(corners[(k+1)%3],.53) for k in range(3)]
        for k in (0,1):
            A,B,C=corners[k],corners[(k+1)%3],corners[(k+2)%3];p=A.lerp(B,.41);q=B.lerp(C,.55);t=B.lerp(apex,.70)
            line=[p+v((0,0,-.0008)),q+v((0,0,-.0008)),t+v((0,0,.0008)),p+v((0,0,-.0008))];limb('Crossed string',line,[.00155]*4,cord,'String ties',8)
        knot=corners[1].lerp(apex,.70);oval('Twine knot',knot,(.004,.004,.004),cord,'String ties');
        for sign in (-1,1):
            d=v((sign*.019,-.009,.025));sweep('String loop',[knot,knot+d*.6+v((0,-.006,0)),knot+d,knot+d*.4+v((0,.004,0)),knot+v((0,0,.001))],[.00135]*5,cord,'String ties');sweep('Loose end',[knot,knot+v((.012*sign,-.004,-.006)),knot+v((.018*sign,-.012,-.017))],[.0013]*3,cord,'String ties')
    for x,y,yaw,s in [(-.070,-.051,-.40,1),(.064,-.054,.20,.96),(-.062,.067,2.68,1.02),(.065,.060,-2.5,1.02)]:parcel(x,y,.014,yaw,s)
    deliver((.47,-1,.78),'C4C4B7',1.13)


if __name__ == '__main__':
    main()
