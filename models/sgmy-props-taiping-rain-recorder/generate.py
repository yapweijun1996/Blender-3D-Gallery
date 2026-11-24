"""Taiping Siphon Rain Recorder | sgmy-props-taiping-rain-recorder, revision 1.
Original procedural static mesh. Metres; base origin; Blender -Y front, +Z up.
Rebuild: blender -b --factory-startup --python-exit-code 1 -P generate.py
Optional: -- --export-only or -- --preview-only. Requires Blender with Draco.
No external images, fonts or model assets. UV0 is oriented planar for solid PBR materials.
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


def bead(name, xyz, r, thick, mat, group, sides=64, axis=(0,0,1)):
    profile=[(r+thick*cos(TAU*j/8),thick*sin(TAU*j/8)) for j in range(8)]
    return turn(name,xyz,profile,mat,group,sides,axis,True)


def outline(name, rings, mat, group, smooth=True):
    # A closed loft through equally sampled contours, bottom to top.
    n=len(rings[0]); fs=[tuple(reversed(range(n))),tuple(range(n*(len(rings)-1),n*len(rings)))]
    fs.extend((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for k in range(len(rings)-1) for i in range(n))
    ob=mesh(name,[p for ring in rings for p in ring],fs,mat,group,smooth=smooth)
    for p in ob.data.polygons[:2]:p.use_smooth=False
    return ob



def grid(name, nx, ny, fn, mat, group, smooth=True, flip=False):
    vs=[fn(i/nx,j/ny) for j in range(ny+1) for i in range(nx+1)]
    fs=[]
    for j in range(ny):
        for i in range(nx):
            k=j*(nx+1)+i
            f=(k,k+1,k+nx+2,k+nx+1); fs.append(f[::-1] if flip else f)
    return mesh(name,vs,fs,mat,group,smooth=smooth)


def panel(name, contour, y, depth, mat, group, bevel=0):
    # Extrude a silhouette drawn in the front (X,Z) plane towards the back.
    if sum(x*v-u*z for (x,z),(u,v) in zip(contour,contour[1:]+contour[:1]))<0:contour=contour[::-1]
    n=len(contour); vs=[(x,y+d,z) for d in (0,depth) for x,z in contour]
    fs=[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(j,i,i+n,j+n) for i in range(n) for j in [(i+1)%n]]
    return mesh(name,vs,fs,mat,group,bevel)


def samples(n):return [i*TAU/n for i in range(n)]


def line(name, points, radius, mat, group, sides=8):
    return limb(name,points,[radius]*len(points),mat,group,sides)


TITLE = 'Taiping Siphon Rain Recorder'


def build():
    enamel=material('Midnight blue enamel','284F60',.35,.22);jad=material('Verdigris instrument paint','629894',.35,.18);gold=material('Brushed brass','C99B53',.33,.62);dark=material('Oiled bronze','665441',.35,.49);paper=material('Ivory chart paper','F7EDCF',.85);rule=material('Muted cyan ruling','79ADB0');ink=material('Recorder ink','B24546'); cream=material('Ivory stencil','F9EBC7');steel=material('Spun catchment metal','ADBDB6',.32,.56)
    for x in (-.123,.123):
        for y in (-.065,.065):turn('Adjustable foot',(x,y,0),[(.019,0),(.020,.004),(.017,.012),(.009,.014),(.009,.03)],dark,'Bedplate',20)
    box('Cast instrument bed',(0,0,.049),(.335,.217,.054),enamel,'Bedplate',.014); box('Bed beading',(0,0,.075),(.329,.213,.008),gold,'Bedplate',.004)
    box('Serial face',(0,-.107,.049),(.235,.006,.038),jad,'Identification',.003);text('TAIPING   /   HUJAN',(0,-.111,.049),.0225,cream,'Identification')
    for x in (-.105,.105):turn('Plate fastener',(x,-.111,.049),[(.0032,0),(.0032,.001),(.002,.002)],gold,'Identification',12,(0,-1,0))
    # Clockwork drum with a continuous wrap of squared recording paper.
    X,Y=-.046,-.004
    def C(a,r,z):return (X+r*cos(a),Y+r*sin(a),z)
    turn('Chart drum',(X,Y,.079),[(.024,0),(.024,.014),(.067,.018),(.072,.021),(.072,.026),(.068,.027),(.068,.166),(.072,.167),(.073,.172),(.069,.176),(.022,.178),(.020,.187)],gold,'Clock drum',64)
    turn('Paper roll',(X,Y,0),[(.0683,.109),(.0686,.111),(.0686,.240),(.0683,.242)],paper,'Clock drum',80)
    for j in range(13):
        z=.114+j*.0101;bead('Millimetre ruling',(X,Y,z),.06864,.00044 if j%3==0 else .00025,rule,'Chart',80)
    for i in range(66):
        a=TAU*i/66;rod('Hour ruling',C(a,.06863,.114),C(a,.06863,.236),.00046 if i%6==0 else .00023,rule,'Chart',4)
    pts=[];rng=random.Random(451)
    for j in range(145):
        a=TAU*j/144;u=(.18+j/39)%1;z=.121+.100*(.75*u+.25*u**2)+.0009*rng.random();pts.append(C(a,.0694,z))
    line('Siphon sawtooth trace',pts,.00096,ink,'Chart',6)
    turn('Winding button',(X,Y,.264),[(.009,0),(.010,.004),(.008,.010),(.008,.018),(.012,.020),(.012,.024),(.009,.026)],dark,'Clock drum',24)
    # A float chamber, brass siphon and articulated pen up against the chart.
    turn('Float chamber',(.099,.000,.08),[(.029,0),(.031,.006),(.026,.009),(.025,.109),(.03,.110),(.03,.116),(.019,.121),(.007,.124)],jad,'Float mechanism',40)
    rod('Float spindle',(.099,0,.202),(.099,0,.273),.0038,gold,'Float mechanism');limb('Stylus linkage',[(.099,0,.254),(.101,-.037,.251),(.061,-.049,.215),(.016,-.041,.188)],[.005,.005,.003,.0009],dark,'Float mechanism',10)
    line('Brass siphon',[(.085,-.010,.113),(.072,-.029,.147),(.072,-.030,.200),(.070,-.030,.214),(.063,-.030,.221),(.055,-.030,.217),(.052,-.030,.205),(.052,-.030,.085)],.0028,gold,'Float mechanism')
    for x,y in ((-.141,.072),(.141,.072),(.143,-.069)):
        turn('Instrument pillar',(x,y,.079),[(.010,0),(.010,.006),(.006,.008),(.0058,.227),(.009,.229),(.009,.237)],gold,'Frame',20)
    box('Shoulder beam',(0,0,.318),(.327,.203,.014),enamel,'Frame',.006)
    turn('Spun collecting funnel',(0,0,.322),[(.030,0),(.036,.011),(.079,.026),(.126,.063),(.134,.066),(.134,.073),(.129,.075),(.123,.068),(.076,.033),(.030,.017),(.013,.012)],jad,'Collector',80)
    turn('Tinned interior',(0,0,.322),[(.012,.0125),(.030,.0176),(.077,.0338),(.124,.0696),(.128,.073),(.124,.0704),(.077,.0346),(.030,.0184),(.012,.0134)],steel,'Collector',80,closed=True)
    bead('Inlet lip',(0,0,.396),.131,.0029,gold,'Collector',80);turn('Strainer well',(0,0,.3349),[(.012,0),(.012,.001)],dark,'Collector',32)
    for i in range(-2,3):
        x=i*.004;y=math.sqrt(.011**2-x*x);rod('Strainer', (x,-y,.337),(x,y,.337),.0007,gold,'Collector',6)
    deliver((.56,-1,.44),'CCCBBA',1.13)


if __name__ == '__main__':
    main()
