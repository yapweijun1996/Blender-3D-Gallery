"""Kelantan Rebana Ubi | sgmy-props-kelantan-rebana-ubi | revision 1.
Original procedural static prop, no external assets. Metres; Z up, -Y front.
From this directory: blender -b --factory-startup -P generate.py
Default: rebuild model.glb (requires Draco) and studio preview.png.
Use -- --export-only or -- --preview-only to rebuild one. No runtime logic.
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
    scene.cycles.samples=18
    scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.37
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


def tube(name, points, radius, mat, group, sides=10):
    return limb(name,points,[radius]*len(points),mat,group,sides,ref=(0.13,0.81,0.57))


def hoop(name, at, radius, wire, mat, group, sides=64, axis=(0,0,1)):
    profile=[(radius+wire*cos(TAU*i/10),wire*sin(TAU*i/10)) for i in range(10)]
    return turn(name,at,profile,mat,group,sides,axis,True)


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


def stroke(name, points, radius, mat, group, sides=8, steps=5):
    # Sample Catmull-Rom curves through the authored control points.
    p=[Vector(v) for v in points]; out=[]
    for j in range(len(p)-1):
        a,b,c,d=p[max(0,j-1)],p[j],p[j+1],p[min(j+2,len(p)-1)]
        for i in range(steps):
            t=i/steps
            out.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t**3))
    return tube(name,out+[p[-1]],radius,mat,group,sides)


def disk(name, x,y,z, r,h, mat, group, sides=48):
    return turn(name,(x,y,z),[(r*.98,0),(r,.08*h),(r,.92*h),(r*.98,h)],mat,group,sides)


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


TITLE = 'Kelantan Rebana Ubi'


def build():
    red,wood,green,gold,bone,hide,tan,cord,ink=palette([('Lacquer vermilion','AB3936'),('Chengal heartwood','773E2E'),('Peacock green','216C61'),('Ochre lacquer','E9AD48'),('Cream pinstripe','F1DDB2'),('Buffalo hide','D9B682'),('Hide turnover','B88B57'),('Rawhide lacing','C99C65'),('Dark foot ring','413632')])
    # A low stand carries the large drum clear of its splayed tuning wedges.
    disk('Stand foot',0,0,0,.279,.045,ink,'Ring stand');disk('Stand seat',0,0,.045,.232,.14,wood,'Ring stand')
    turn('Turned timber body',(0,0,0),[(.245,.157),(.272,.185),(.272,.225),(.289,.26),(.319,.34),(.365,.50),(.409,.64),(.415,.67)],red,'Drum shell',96)
    for r,z,h,m in ((.271,.185,.036,green),(.283,.238,.014,gold),(.321,.337,.024,green),(.369,.503,.023,green),(.394,.592,.018,gold),(.411,.643,.018,green)):
        turn('Lathed paint band',(0,0,z),[(r,-.002),(r+.006,.001),(r+.006+h*.26,h),(r+h*.26,h+.002)],m,'Painted borders',96)
    for r,z in ((.273,.213),(.322,.340),(.327,.361),(.373,.528),(.400,.609)):
        hoop('Pinstripe',(0,0,z),r,.0022,bone,'Painted borders',96)
    def motif(angle,points,material,radius_offset):
        # Narrow triangles tessellate the motif onto the tapered shell, not a floating decal.
        vs=[]; n=16
        for j in range(n+1):
            t=j/n; zl,zh,w=points(t); u=angle+w
            for z in (zl,zh):
                r=.319+(z-.34)*.289+radius_offset;vs.append((r*cos(u),r*sin(u),z))
        mesh('Painted shoot panel',vs,[(2*j,2*j+2,2*j+3,2*j+1) for j in range(n)],material,'Pucuk rebung ornament')
    for i in range(16):
        a=TAU*i/16
        motif(a,lambda t:(.368,.377+.112*(1-abs(2*t-1)),-.166+.332*t),gold,.0017)
        motif(a,lambda t:(.371,.378+.074*(1-abs(2*t-1)),-.112+.224*t),green,.0027)
        motif(a,lambda t:(.376,.382+.035*(1-abs(2*t-1)),-.062+.124*t),bone,.0036)
    turn('Taut hide',(0,0,.647),[(.409,0),(.422,.008),(.425,.028),(.420,.042),(.411,.050),(.388,.052),(.335,.054)],hide,'Drumhead',96)
    for z,r,w,m in ((.656,.422,.007,wood),(.664,.424,.0052,cord),(.684,.419,.003,tan)):
        hoop('Hide hoop',(0,0,z),r,w,m,'Drumhead',96)
    for i in range(16):
        a=i*TAU/16; d=Vector((cos(a),sin(a),0)); b=a+TAU/32
        def p(r,a,z): return (r*cos(a),r*sin(a),z)
        # Chisel-shaped lower tensioning key and paired hide cords.
        limb('Driven tuning key',[p(.344,a,.086),p(.318,a,.152),p(.276,a,.238)],[(.022,.018),(.022,.018),(.014,.012)],gold,'Tuning keys',6,ref=(0,0,1))
        for s in (-1,1):
            c=a+s*.108
            stroke('Rawhide tension cord',[p(.308,a+s*.012,.158),p(.291,a+s*.032,.245),p(.338,a+s*.060,.396),p(.413,c,.635),p(.425,c,.660)],.0055,cord,'Tension lacing',7,4)
        oval('Hide tab',p(.419,a+.108,.650),(.009,.016,.019),tan,'Tension lacing',a)
    deliver((.55,-1,.45),'B8C6BB',1.13)


if __name__ == '__main__':
    main()
