"""Kuching Enggang Litter Bin | sgmy-props-kuching-enggang-bin, revision 1.
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


def panel(name, contour, y, thickness, mat, group, bevel=0):
    # Extrude a front-view silhouette along its thickness.
    pts=list(contour)
    if sum(x*pts[(i+1)%len(pts)][1]-z*pts[(i+1)%len(pts)][0] for i,(x,z) in enumerate(pts))<0:pts.reverse()
    n=len(pts); vs=[(x,yy,z) for yy in (y+thickness/2,y-thickness/2) for x,z in pts]
    fs=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    return mesh(name,vs,fs,mat,group,bevel)



TITLE = 'Kuching Enggang Litter Bin'


def build():
    black,blue,wing,cream,rust,orange,yellow,eye=palette([('Feather charcoal','233A3E'),('Deep river teal','165653'),('Wing coverts','28756D'),('Ivory flight feathers','EBDDC3'),('Vermilion casque','CF5736'),('Tangerine bill','E88D35'),('Horn gold','F4BF57'),('Pupil and lining','162726')]); metal=material('Retaining rivets','9CACA3',.37,.62)
    g='Moulded body';turn('Ballasted foot',(0,0,0),[(.264,0),(.30,.024),(.30,.064),(.276,.092)],black,g,56);turn('Foot collar',(0,0,.069),[(.267,0),(.273,.015),(.267,.035)],yellow,g,56)
    def loop(w,h,c):return [(w*math.copysign(abs(cos(a))**.48,cos(a)),c+h*math.copysign(abs(sin(a))**.48,sin(a))) for a in [i*TAU/64 for i in range(64)]]
    outer=loop(.316,.401,.475); inner=loop(.206,.095,.646)
    rings=[[(x*.94,.235,z) for x,z in outer],[(x,.217,z) for x,z in outer],[(x,-.178,z) for x,z in outer],[(x*.985,-.202,z) for x,z in outer],[(x,-.221,z) for x,z in inner],[(x*.962,-.195,.646+(z-.646)*.91) for x,z in inner]]; n=64
    vs=sum(rings,[]);fs=[tuple(reversed(range(n)))]+[(k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for k in range(5) for i in range(n)]
    ob=mesh('Shell with actual disposal mouth',vs,fs,blue,g,smooth=True,slots=[blue,black,yellow],indices=[0]+[0]*(3*n)+[0]*n+[2]*n);ob.data.polygons[0].use_smooth=False
    panel('Dark chute backing',loop(.23,.12,.646),-.085,.016,eye,g); box('Chute shelf',(0,-.145,.552),(.41,.13,.018),black,g)
    panel('Service door',loop(.222,.174,.326),-.210,.016,wing,g,.003);text('SISA AM',(0,-.222,.365),.061,cream,'Door markings');text('K U C H I N G',(0,-.222,.275),.031,cream,'Door markings')
    for s in (-1,1):
        for z in (.221,.437):turn('Door fastener',(s*.177,-.220,z),[(.009,0),(.008,.004)],metal,'Hardware',12,(0,-1,0))
    # The high upturned casque and two-colour bill identify the rhinoceros hornbill.
    oval('Bird crown',(.004,.009,.922),(.249,.210,.263),black,'Hornbill crown',rings=18,sides=40)
    panel('Sweeping bill',[(.136,1.02),(.18,1.10),(.31,1.108),(.47,1.072),(.573,1.015),(.617,.962),(.635,.910),(.564,.941),(.435,.956),(.312,.949),(.211,.960)],.003,.175,yellow,'Bill and casque',.023)
    panel('Lower mandible',[(.18,.979),(.268,.953),(.464,.966),(.606,.930),(.494,.927),(.375,.913),(.256,.914),(.196,.928)],.003,.14,orange,'Bill and casque',.014)
    panel('Rising casque',[(.109,1.088),(.143,1.173),(.23,1.212),(.333,1.218),(.422,1.274),(.446,1.303),(.438,1.218),(.396,1.15),(.345,1.091),(.236,1.067)],.003,.125,orange,'Bill and casque',.017)
    for s in (-1,1):
        panel('Crimson casque flash',[(.14,1.112),(.173,1.169),(.233,1.191),(.303,1.195),(.263,1.15),(.211,1.119)],.003+s*.064,.005,rust,'Bill and casque',.002)
        oval('Eye patch',(.084,.004+s*.179,1.045),(.072,.027,.058),cream,'Hornbill crown',rings=10,sides=24);oval('Golden iris',(.097,.003+s*.202,1.048),(.029,.010,.030),rust,'Hornbill crown');oval('Dark pupil',(.101,.003+s*.210,1.048),(.016,.006,.017),eye,'Hornbill crown')
    # Layered feather panels at the bin flanks, clear of the service opening.
    for s in (-1,1):
        for j in range(3):
            x=s*(.294+.006*j);o=oval('Primary feather',(x,.085-.08*j,.422+.079*j),(.038,.075,.222),cream if j==0 else black,'Flanks',rings=12,sides=24);o.rotation_euler.x=-.32
        o=oval('Teal shoulder',(s*.30,.02,.654),(.054,.176,.192),wing,'Flanks');o.rotation_euler.x=.27
    deliver((.52,-1,.34),'C5C7B9',1.13)


if __name__ == '__main__':
    main()
