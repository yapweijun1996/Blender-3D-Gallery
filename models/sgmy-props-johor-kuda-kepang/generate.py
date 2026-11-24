"""sgmy-props-johor-kuda-kepang | revision 1 | static regional game prop.
Original procedural form, details and palette. No external assets or textures.
Metric, base origin, -Y front. No collision, gameplay scripts or animation.
Rebuild from any directory: blender -b --factory-startup --python-exit-code 1 -P generate.py
Options after -- : --export-only or --preview-only. GLB requires a Draco decoder.
Preview studio geometry is not exported."""
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
        material('Preview Backdrop',backdrop,.82,emission=.17),None,0)
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
        data.energy=.45*power*span**2
        data.shape='DISK'
        data.size=size*span
        data.color=color
    area('Warm Softbox',(-.75,-1.05,1.25),131,1.09,(1,.88,.74))
    area('Cool Fill',(1.1,-.45,.51),38,1.25,(.77,.87,1))
    area('High Edge Light',(.48,1.03,1.3),173,1.05,(1,.94,.81))
    scene.render.engine='CYCLES'
    scene.cycles.samples=10
    scene.cycles.use_denoising=True
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.72
    scene.render.resolution_x=720
    scene.render.resolution_y=600
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
        png_budget(out/'preview.png')


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    build()


def tube(name, points, radius, mat, group, sides=10):
    return limb(name,points,[radius]*len(points),mat,group,sides,ref=(0.13,0.81,0.57))


def oval(name, at, size, mat, group, yaw=0, rings=10, sides=20):
    # Ellipsoid with a single vertex at either pole.
    x,y,z=at; a,b,c=size
    vs=[(x,y,z-c)]
    for j in range(1,rings):
        lat=PI*(j/rings-.5)
        for i in range(sides):
            t=TAU*i/sides; u=a*cos(lat)*cos(t); v=b*cos(lat)*sin(t)
            vs.append((x+u*cos(yaw)-v*sin(yaw),y+u*sin(yaw)+v*cos(yaw),z+c*sin(lat)))
    vs.append((x,y,z+c)); end=len(vs)-1; fs=[]
    for i in range(sides):
        q=(i+1)%sides; fs.append((0,1+q,1+i)); fs.append((end,end-sides+i,end-sides+q))
        for j in range(rings-2):
            k=1+j*sides; fs.append((k+i,k+q,k+sides+q,k+sides+i))
    return mesh(name,vs,fs,mat,group,smooth=True)


def png_budget(path):
    # Quantize an RGB8 Blender PNG in sRGB space using frequency-weighted median cut.
    # No image utilities or third-party Python packages are needed for a rebuild.
    import zlib, struct
    from collections import Counter
    data=path.read_bytes()
    if len(data)<=250000: return
    pos=8; packed=bytearray()
    while pos<len(data):
        length=struct.unpack_from('>I',data,pos)[0]; kind=data[pos+4:pos+8]; payload=data[pos+8:pos+8+length]; pos+=12+length
        if kind==b'IHDR': w,h,depth,col,_,_,inter=struct.unpack('>2I5B',payload); assert (depth,col,inter)==(8,2,0)
        if kind==b'IDAT': packed.extend(payload)
    raw=zlib.decompress(packed); stride=w*3; prev=bytearray(stride); pix=bytearray(); cursor=0
    for y in range(h):
        f=raw[cursor]; line=bytearray(raw[cursor+1:cursor+1+stride]); cursor+=1+stride
        if f:
            for k in range(stride):
                a=line[k-3] if k>=3 else 0; b=prev[k]; c=prev[k-3] if k>=3 else 0
                if f==1: base=a
                elif f==2: base=b
                elif f==3: base=(a+b)//2
                else:
                    p=a+b-c; da,db,dc=abs(p-a),abs(p-b),abs(p-c); base=a if da<=db and da<=dc else b if db<=dc else c
                line[k]=(line[k]+base)&255
        pix.extend(line); prev=line
    keys=[(r>>3,g>>3,b>>3) for r,g,b in zip(pix[::3],pix[1::3],pix[2::3])]; hist=Counter(keys)
    def measure(colors):
        weight=sum(hist[c] for c in colors); mean=[sum(hist[c]*c[i] for c in colors)/weight for i in range(3)]
        var=[sum(hist[c]*(c[i]-mean[i])**2 for c in colors) for i in range(3)]; return max(var),var.index(max(var)),weight
    bins=[(measure(list(hist)),list(hist))]
    while len(bins)<min(240,len(hist)):
        q=max(range(len(bins)),key=lambda i:bins[i][0][0]); (_,axis,total),colors=bins.pop(q); colors.sort(key=lambda c:c[axis]); count=0
        for j in range(1,len(colors)):
            count+=hist[colors[j-1]]
            if 2*count>=total: break
        for half in (colors[:j],colors[j:]): bins.append((measure(half),half))
    lookup={c:i for i,(_,colors) in enumerate(bins) for c in colors}; idx=bytes(lookup[c] for c in keys); sums=[[0,0,0,0] for _ in bins]
    for i,r,g,b in zip(idx,pix[::3],pix[1::3],pix[2::3]):
        s=sums[i]; s[0]+=r; s[1]+=g; s[2]+=b; s[3]+=1
    pal=bytes(round(v/s[3]) for s in sums for v in s[:3]); lines=b''.join(b'\0'+idx[y*w:(y+1)*w] for y in range(h))
    def chunk(tag,body): return struct.pack('>I',len(body))+tag+body+struct.pack('>I',zlib.crc32(tag+body)&0xffffffff)
    path.write_bytes(data[:8]+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,3,0,0,0))+chunk(b'sRGB',b'\0')+chunk(b'PLTE',pal)+chunk(b'IDAT',zlib.compress(lines,9))+chunk(b'IEND',b'')); assert path.stat().st_size<=250000


TITLE='Batu Pahat • Woven Dance Horse'


def build():
    cane,light,edge,ink,red,teal,cream,brass=palette([('Honey split bamboo','C78A47'),('Straw silk','EDD49B'),('Dark cane rim','674132'),('Charcoal mane','343136'),('Vermilion bridle','B6473C'),('Peacock saddle cloth','186964'),('Milk tooth enamel','F5DFAB'),('Ochre braid','D9A14A')])
    # Flat, legless kuda kepang effigy. A closed woven silhouette, not a solid-bodied horse.
    outline=[(-.54,.22),(-.58,.31),(-.57,.46),(-.52,.57),(-.46,.605),(-.34,.58),(-.21,.535),(-.04,.54),(.04,.565),(.075,.67),(.13,.78),(.22,.875),(.31,.93),(.335,1.017),(.39,.955),(.43,.99),(.443,.91),(.505,.858),(.53,.797),(.645,.725),(.657,.681),(.615,.645),(.559,.654),(.515,.676),(.447,.68),(.398,.72),(.36,.698),(.303,.611),(.284,.479),(.258,.345),(.2,.24),(.09,.181),(-.04,.156),(-.25,.147),(-.43,.174)]
    def panel(name,p,y,depth,m,g):
        n=len(p); vs=[(x,y+off,z) for off in (-depth/2,depth/2) for x,z in p]; fs=[tuple(reversed(range(n))),tuple(range(n,n*2))]; fs +=[(j,(j+1)%n,n+(j+1)%n,n+j) for j in range(n)]; return mesh(name,vs,fs,m,g,bevel=.002)
    panel('Cut bamboo effigy',outline,0,.027,cane,'Woven horse')
    def trace(name,p,y,r,m,g):tube(name,[(x,y,z) for x,z in p],r,m,g,9)
    # Clip diagonal cane filaments to the cut edge using scanline intersections.
    for slope in (-.69,.69):
        for k in range(-16,63):
            b=k*.0265; xs=[]
            for (x,z),(u,v) in zip(outline,outline[1:]+outline[:1]):
                d,e=z-slope*x-b,v-slope*u-b
                if (d>0)!=(e>0):xs.append(x+(u-x)*d/(d-e))
            xs.sort()
            for x,u in zip(xs[::2],xs[1::2]):
                if u-x<.008:continue
                for side in (-1,1):trace('Diagonal cane',[(x,b+slope*x),(u,b+slope*u)],side*(.014 if slope<0 else .015),.003,light if slope<0 else brass,'Plaited cane')
    trace('Lashed border',outline+[outline[0]],0,.018,edge,'Woven horse')
    saddle=[(-.425,.587),(-.315,.568),(-.192,.539),(-.043,.544),(.036,.561),(.005,.441),(-.04,.388),(-.235,.323),(-.348,.362)]
    for s in (-1,1):
        y=s*.021; panel('Scalloped saddle',saddle,y,.005,teal,'Ceremonial tack'); trace('Blanket piping',saddle+saddle[:1],s*.025,.008,cream,'Ceremonial tack')
        for k in range(5):
            x=-.32+k*.064; z=.453+.013*cos(k); p=[(x-.026,z),(x,z+.042),(x+.026,z),(x,z-.042)];panel('Songket lozenge',p,s*.027,.002,brass,'Ceremonial tack'); oval('Ruby stitch',(x,s*.03,z),(.009,.003,.015),red,'Ceremonial tack')
        for i in range(9):
            x=-.339+i*.035; z=.36+(.045*(i/8) if i>3 else -.02*(i/3));trace('Tassel',[(x,z),(x-.009,z-.04)],s*.023,.006,red,'Ceremonial tack')
        trace('Headstall',[(.334,.932),(.378,.843),(.43,.79),(.523,.688)],s*.022,.012,red,'Ceremonial tack'); trace('Noseband',[(.535,.788),(.567,.728),(.602,.655)],s*.022,.012,teal,'Ceremonial tack')
        oval('Eye surround',(.439,s*.024,.838),(.038,.007,.026),cream,'Painted features'); oval('Black lacquer eye',(.45,s*.032,.835),(.017,.005,.017),ink,'Painted features');oval('Eye glint',(.456,s*.036,.842),(.005,.002,.005),light,'Painted features'); oval('Nostril',(.62,s*.019,.714),(.016,.006,.009),ink,'Painted features')
        for x,z in ((.429,.793),(.57,.72)):oval('Bridle boss',(x,s*.037,z),(.018,.006,.018),brass,'Ceremonial tack')
        trace('Looped rein',[(.58,.71),(.52,.591),(.47,.538),(.415,.53),(.34,.555),(.244,.595),(.06,.616),(-.061,.56)],s*.034,.007,red,'Ceremonial tack')
    rng=random.Random(46)
    for j in range(31):
        q=j/30; x=.326-.25*q; z=.942-.265*q**1.38; l=.088+.055*q+rng.uniform(-.012,.012)
        limb('Dyed fibre mane',[(x,0,z),(x-l*.42,-.006,z+.06),(x-l,.003,z+.051-.013*q),(x-l*1.15,0,z+.035)],[(.011,.012),(.011,.01),(.007,.007),.0015],ink if j%6 else red,'Mane and tail',7)
    for j in range(25):
        f=j/24; x=-.53+.035*f; z=.545+.047*f; y=rng.uniform(-.012,.012)
        limb('Splayed tail fibre',[(x,y,z),(-.625,y,z+.038),(-.701-f*.036,y,z+.005-.05*f),(-.75-.053*f,y,z-.082-.13*f),(-.79+.041*f,y,z-.106-.18*f)], [.008,.011,.012,.008,.0016],ink if j%5 else edge,'Mane and tail',7)
    for x in (-.33,.13):
        box('Display foot',(x,0,.018),(.095,.20,.036),edge,'Hardwood cradle',.009); box('Rest tenon',(x,0,.102),(.046,.047,.168),edge,'Hardwood cradle',.007)
        for s in (-1,1):box('Felted jaw',(x,s*.025,.185),(.046,.019,.086),ink,'Hardwood cradle',.007)
    deliver((.37,-1,.34),'B5BFB4',1.13)


if __name__ == "__main__":
    main()
