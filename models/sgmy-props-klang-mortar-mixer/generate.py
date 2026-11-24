"""Klang Site Mortar Mixer | sgmy-props-klang-mortar-mixer, revision 1.
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

TITLE = 'Klang Site Mortar Mixer'


def build():
    orange=material('Safety ochre paint','D58633',.44,.24);yellow=material('Lip enamel','E9AE52',.38,.31);iron=material('Gunmetal frame','384849',.45,.45);teal=material('Fleet green enamel','347470',.40,.32);tyre=material('Tread rubber','353A39',.76);rim=material('Wheel and bolt zinc','ABAEA3',.34,.67); rust=material('Oxide tooth edge','8A6245',.69,.31);mud=material('Mortar residue','BAAF93',.87); interior=material('Scoured inner steel','746D5C',.72,.28); white=material('Ivory stencil','EBDDB8');rng=random.Random(862)
    def wheel(x,y,z):
        ax=(1,0,0);p=(x,y,z);turn('Pneumatic tyre',p,[(.086,-.044),(.123,-.050),(.149,-.036),(.155,-.018),(.155,.018),(.149,.036),(.123,.050),(.086,.044)],tyre,'Road wheels',48,ax,True);turn('Stamped rim',p,[(.091,-.045),(.096,-.041),(.096,.041),(.091,.045),(.054,.035),(.032,.051)],teal,'Road wheels',40,ax)
        s=1 if x>0 else -1;turn('Hub cap',(x+s*.044,y,z),[(.035,0),(.033,.016),(.022,.027)],rim,'Road wheels',32,(s,0,0))
        for i in range(30):
            a=i*TAU/30;pa=(x-.025,y+.154*cos(a),z+.154*sin(a));pb=(x+.025,y+.154*cos(a+.062),z+.154*sin(a+.062));rod('Tread cleat',pa,pb,.004,tyre,'Road wheels',6)
    for s in (-1,1):
        wheel(s*.357,.241,.159);rod('A-frame leg',(s*.276,.241,.171),(s*.270,-.024,.720),.032,iron,'Welded frame');rod('Stand leg',(s*.251,-.387,.029),(s*.270,-.024,.720),.030,teal,'Welded frame');box('Stand shoe',(s*.251,-.387,.012),(.092,.171,.023),iron,'Welded frame',.005);rod('Tie bar',(s*.254,-.341,.117),(s*.276,.241,.176),.018,iron,'Welded frame')
    rod('Axle',(-.394,.241,.159),(.394,.241,.159),.024,iron,'Welded frame');rod('Foot rail',(-.263,-.388,.051),(.263,-.388,.051),.019,teal,'Welded frame')
    # Inclined open pear-shaped drum with internal mixing blades and toothed drive band.
    axis=Vector((0,-.808,.589)).normalized();base=Vector((0,.193,.708));frame=Vector((0,0,1)).rotation_difference(axis)
    def D(r,a,z):return base+frame@Vector((r*cos(a),r*sin(a),z))
    pro=[(.095,0),(.152,.021),(.216,.072),(.255,.157),(.261,.245),(.259,.319),(.239,.398),(.201,.481),(.166,.536),(.166,.551),(.156,.552),(.155,.532),(.190,.476),(.228,.394),(.248,.317),(.248,.242),(.244,.161),(.207,.081),(.143,.034),(.069,.025)]
    ob=turn('Mixer drum',base,pro,orange,'Drum',72,axis);ob.data.materials.append(interior)
    for p in ob.data.polygons:
        if p.index==1 or p.index>=2+10*72:p.material_index=1
    for z,r,w,m in ((.549,.164,.007,yellow),(.397,.238,.006,yellow),(.161,.256,.006,rust),(.277,.260,.012,iron),(.292,.260,.007,iron)):bead('Drum band',base+axis*z,r,w,m,'Drum hardware',72,axis)
    for j in range(52):
        a=TAU*j/52;rod('Cast ring gear tooth',D(.265,a,.267),D(.265,a+.018,.300),.007,rust,'Drum hardware',7)
    vane=material('Scoured blade steel','837B6C',.68,.28,two_sided=True)
    for j in range(3):
        a=j*TAU/3;path=[D(r,a+.70*t,z) for r,t,z in ((.211,0,.105),(.241,.29,.193),(.239,.52,.310),(.213,.78,.397),(.174,1,.479))];offs=[frame@Vector((-.009*cos(a+.7*i/4),-.009*sin(a+.7*i/4),.018)) for i in range(5)];ribbon('Welded mixing vane',path,offs,vane,'Drum hardware')
    for k in range(48):
        a=rng.random()*TAU;z=rng.uniform(.410,.535);r=.239-(z-.398)*(.073/.138);p=D(r+.0005,a,z);o=oval('Dried mortar speck',p,(.003,rng.uniform(.003,.009),.0013),mud,'Mortar splashes',rings=4,sides=8);o.rotation_euler=(D(1,a,0)-base+axis*.53).to_track_quat('Z','Y').to_euler()
    for s in (-1,1):
        sweep('Cradle arm',[(s*.11,.198,.66),(s*.221,.196,.64),(s*.276,.091,.666),(s*.279,-.023,.722)],[.031,.027,.025,.023],teal,'Cradle');turn('Trunnion',(s*.268,-.023,.722),[(.047,0),(.049,.016),(.039,.032)],rim,'Cradle',32,(s,0,0))
    # Operable-looking handwheel and fixed lock plate on the accessible side.
    p=Vector((.371,-.023,.722));ax=(1,0,0);rod('Handwheel shaft',(.273,-.023,.722),p,.018,iron,'Handwheel');bead('Tilt wheel',p,.176,.013,teal,'Handwheel',60,ax)
    for i in range(4):
        a=.36+i*PI/2;rod('Wheel spoke',p,p+Vector((0,.173*cos(a),.173*sin(a))),.009,teal,'Handwheel');
    turn('Tilt hub',p,[(.032,-.015),(.033,.014),(.020,.022)],rim,'Handwheel',24,ax);rod('Spinner handle',(.37,-.173,.644),(.438,-.173,.644),.014,iron,'Handwheel')
    box('Motor cover',(0,.339,.602),(.474,.271,.258),teal,'Motor housing',.027);box('Lower tray',(0,.343,.473),(.49,.29,.027),iron,'Motor housing',.007)
    for j in range(7):box('Air louvre',(.235,.253+j*.028,.641),(.014,.012,.086),iron,'Motor housing',.005)
    text('KLANG  08',(.243,.343,.540),.039,white,'Motor housing',.217,plane='X');
    for s in (-1,1):
        rod('Motor mount',(s*.19,.372,.466),(s*.273,.098,.466),.018,iron,'Welded frame');rod('Motor gusset',(s*.273,.176,.308),(s*.202,.318,.466),.013,iron,'Welded frame')
    box('Weatherproof switch box',(.002,.480,.613),(.142,.027,.099),iron,'Motor housing',.011)
    for x,m in ((-.029,orange),(.029,teal)):turn('Rubber switch',(x,.493,.613),[(.023,0),(.025,.005),(.022,.013)],m,'Motor housing',24,(0,1,0))
    deliver((1.03,-.86,.51),'BFC2B6',1.12)


if __name__ == '__main__':
    main()
