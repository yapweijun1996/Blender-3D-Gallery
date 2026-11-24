"""sgmy-props-pahang-bunga-kantan | revision 1 | static regional game prop.
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


def sheet(name,rows,mat,group,slots=None,indices=None):
    n=len(rows[0]); fs=[(j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i) for j in range(len(rows)-1) for i in range(n-1)]
    return mesh(name,[p for row in rows for p in row],fs,mat,group,smooth=True,slots=slots,indices=indices)


def radial(at,t,r,side,h):
    return (at[0]+r*cos(t)-side*sin(t),at[1]+r*sin(t)+side*cos(t),at[2]+h)


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


TITLE='Pahang • Torch Ginger Clump'


def build():
    stem,sheath,scar,vein=palette([('Wax green stalk','788747'),('Maroon sheath','854940'),('Old leaf sheath','AB8560'),('Pale midrib','99A65F')]); leaves=[material(n,c,.5,two_sided=True) for n,c in [('Jungle jade','36664A'),('Leaf emerald','458054'),('Young blade','759357'),('Leaf in shadow','315D45')]]
    petals=[material(n,c,.33,two_sided=True) for n,c in [('Raspberry bract','B54659'),('Coral rose','DD6371'),('Pink wax','F39B9E'),('Petal lip','FFBCC0'),('Carmine heart','A13D50')]]; pollen=material('Golden florets','FFC567',.49);rng=random.Random(582)
    for idx,(a,h,reach) in enumerate([(1.34,1.82,.32),(2.87,1.55,.37),(.24,1.38,.43),(4.15,.88,.40),(3.24,.63,.32),(.06,.76,.38)]):
        base=(.12*cos(a),.12*sin(a),0); path=[radial(base,a,reach*(j/8)**1.6,0,h*j/8) for j in range(9)]
        limb('Leafy pseudostem',path,[.021*(1-.72*j/8) for j in range(9)],stem,'Leaf shoots',14)
        for j in range(3):
            limb('Sheathing leaf base',path[j:j+2],[.024-j*.002,.022-j*.002],scar if j==0 else stem,'Leaf shoots',12)
        for j in range(6):
            f=.32+j*.117; p=radial(base,a,reach*f**1.6,0,h*f); t=a+(-1 if j%2 else 1)*1.25+rng.uniform(-.32,.32); L=(.49+.14*sin(PI*j/6))*(.76 if idx==3 else 1); W=L*.125
            tip=.32+.21*j/5; rows=[]; rib=[]
            for k in range(17):
                s=k/16; shape=sin(PI*s)**.81; w=W*shape+.0004; mid=L*(tip*s+.23*sin(PI*s)-.18*s**3); d=L*s; rib.append(radial(p,t,d,.016*sin(PI*s),mid+.0018)); row=[]
                for u in (-1,-.55,0,.55,1):
                    z=mid+(.013*abs(u)-.014*u)*shape+.005*abs(u)*sin(5*PI*s)*shape
                    row.append(radial(p,t,d-.017*u*u*shape,.016*sin(PI*s)+u*w,z))
                rows.append(row)
            m=leaves[(j+idx)%4]; sheet('Pleated lanceolate blade',rows,m,'Broad lance leaves'); limb('Cream tapering midrib',rib,[.0036*(1-.94*k/16) for k in range(17)],vein,'Leaf shoots',6)
    for idx,(x,y,h,a,scale) in enumerate([(-.22,-.21,1.12,3.7,1),(.21,-.34,.87,5.2,.91),(-.48,.03,.58,2.8,.63),(.37,.04,1.06,.72,.53)]):
        base=(x*.51,y*.5,0); head=(x,y,h); path=[(base[0]+(x-base[0])*(j/7)**1.4,base[1]+(y-base[1])*(j/7)**1.4,h*j/7) for j in range(8)]
        limb('Bare flowering scape',path,[.018*scale*(1-.25*j/7) for j in range(8)],stem,'Blooming scapes',14)
        for j in (0,2,4,6):limb('Clasping red scale',path[j:j+2],[.019*scale,.015*scale],sheath if j==6 else scar,'Blooming scapes',12)
        oval('Conical flower core',(x,y,h+.066*scale),(.080*scale,.080*scale,.107*scale),petals[4],'Torch heads',rings=12,sides=24)
        for layer,(n,reach,height,width,zbase) in enumerate([(10,.174,.093,.053,-.021),(11,.132,.131,.047,.003),(10,.096,.137,.036,.030),(9,.069,.115,.026,.062),(7,.042,.078,.019,.103)]):
            for k in range(n):
                t=TAU*k/n+layer*2.4+idx*.64; rows=[]; ids=[]
                for j in range(10):
                    s=j/9; bulge=sin(PI*s)**.67; midr=.016+reach*(1-cos(1.46*s))+.029*sin(PI*s); midz=zbase+height*(s+.17*sin(PI*s)); row=[]
                    for u in (-1,-.78,0,.78,1):row.append(radial(head,t,scale*(midr-.021*u*u*bulge),scale*(u*width*(bulge+.014)),scale*(midz+.014*u*u*bulge)))
                    rows.append(row)
                    if j:ids.extend([2 if layer<2 else 1,layer%2,1,3 if layer<2 else 2])
                sheet('Overlapping wax bract',rows,petals[0],'Torch heads',petals,ids)
        for k in range(22):
            t=k*2.4; r=.033*math.sqrt(k/22); p=radial(head,t,r*scale,0,(.181-.023*k/22)*scale); oval('Tiny fertile floret',p,(.005*scale,.003*scale,.006*scale),pollen,'Torch heads',t,5,8)
    deliver((.26,-1,.39),'BEBCAB',1.11)


if __name__ == "__main__":
    main()
