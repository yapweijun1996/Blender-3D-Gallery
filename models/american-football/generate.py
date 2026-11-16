"""Original deterministic procedural sports asset. All dimensions in metres; no external assets."""
C = {'slug': 'american-football', 'name': 'American Football', 'root': 'ASSET_AmericanFootball', 'kind': 'football', 'a': 0.1412875, 'b': 0.08539856358953375, 'p': 1.081791940464, 'long_circ': 0.71755, 'short_circ': 0.536575, 'size': 0.282575}

from pathlib import Path
import math
import json
import sys
import struct
import bpy
import bmesh
from mathutils import Vector
HERE = Path(__file__).resolve().parent
SLUG, ROOT = C['slug'], C['root']
PI=math.pi
TARGET=Vector((0,0,C.get('b', C['size']/2)))
PARTS=[]


def srgb(rgb):
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)


def material(name, color, rough=.6):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=srgb(color)
    bs.inputs['Metallic'].default_value=0
    bs.inputs['Roughness'].default_value=rough
    m.diffuse_color=srgb(color)
    return m


def mesh_object(name, verts, faces, mat, uv=None):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    for f in me.polygons: f.use_smooth=True
    if uv:
        layer=me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            for li in poly.loop_indices: layer.data[li].uv=uv[me.loops[li].vertex_index]
    PARTS.append(o)
    return o


def tube(name, points, radius, mat, closed=False, sides=8):
    # Editable poly curve; conversion is only performed on temporary export copies.
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'
    cu.bevel_depth=radius; cu.bevel_resolution=0 if radius<.0001 else 1; cu.resolution_u=1
    cu.use_fill_caps=True
    sp=cu.splines.new('POLY'); sp.points.add(len(points)-1)
    for v,p in zip(sp.points, points): v.co=(*p,1)
    sp.use_cyclic_u=closed
    o=bpy.data.objects.new(name,cu); bpy.context.scene.collection.objects.link(o)
    cu.materials.append(mat); PARTS.append(o)
    return o


def bake_grain(o, mats):
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=4; scene.cycles.seed=0
    im=bpy.data.images.new('T_Grip_Normal',width=1024,height=512,alpha=False)
    im.colorspace_settings.name='Non-Color'
    temp=material('BAKE_ProceduralGrip',(.5,.5,.5))
    ns,ls=temp.node_tree.nodes,temp.node_tree.links
    bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    coord=ns.new('ShaderNodeTexCoord'); vor=ns.new('ShaderNodeTexVoronoi')
    vor.feature='SMOOTH_F1'; vor.inputs['Scale'].default_value=520 if C['kind']=='rugby' else 420
    vor.inputs['Smoothness'].default_value=.35
    bump=ns.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.45
    bump.inputs['Distance'].default_value=.00020
    ls.new(coord.outputs['Object'],vor.inputs['Vector']); ls.new(vor.outputs['Distance'],bump.inputs['Height'])
    ls.new(bump.outputs['Normal'],bs.inputs['Normal'])
    tex=ns.new('ShaderNodeTexImage');tex.image=im;ns.active=tex
    old=list(o.data.materials);old_indices=[p.material_index for p in o.data.polygons];o.data.materials.clear();o.data.materials.append(temp)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',margin=6,use_clear=True)
    im.filepath_raw=str(HERE/'sources/textures/grip_normal.png');im.file_format='PNG';im.save()
    im.filepath='//textures/grip_normal.png'
    o.data.materials.clear()
    for m in old:o.data.materials.append(m)
    for p,idx in zip(o.data.polygons,old_indices):p.material_index=idx
    bpy.data.materials.remove(temp)
    for m in mats:
        ns,ls=m.node_tree.nodes,m.node_tree.links
        bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
        tex=ns.new('ShaderNodeTexImage');tex.image=im
        normal=ns.new('ShaderNodeNormalMap');normal.uv_map='UVMap'
        ls.new(tex.outputs['Color'],normal.inputs['Color']);ls.new(normal.outputs['Normal'],bs.inputs['Normal'])
    return im


def profile(t):return C['b']*max(0,math.sin(t))**C['p']


def oval():
    rugby=C['kind']=='rugby'
    skin=material('Grip white rubber' if rugby else 'Pebbled brown leather',(.9,.91,.87) if rugby else (.37,.145,.065),.67)
    band=material('Generic teal bands',(.025,.33,.31),.62) if rugby else skin
    seam=material('Recessed seam bed',(.08,.085,.075) if rugby else (.12,.046,.023),.78)
    a,b=C['a'],C['b']; N,M=48,16
    # A closed inset body is visible only through the four panel gaps.
    vv=[(-a,0,b)];uv=[(0,.5)];ff=[]
    for i in range(1,64):
        t=PI*i/64;r=max(0,profile(t)-.0013)
        for j in range(64):
            ang=2*PI*j/64;vv.append((a*math.cos(t),r*math.sin(ang),b+r*math.cos(ang)));uv.append((i/64,j/64))
    vv.append((a,0,b));uv.append((1,.5))
    for j in range(64):ff.append((len(vv)-1,1+j,1+(j+1)%64))
    # The first ring is at +X, the last at -X.
    for i in range(62):
        for j in range(64):
            q=1+i*64+j;qn=1+i*64+(j+1)%64;ff.append((q, q+64, qn+64, qn))
    for j in range(64):ff.append((0,1+62*64+(j+1)%64,1+62*64+j))
    core=mesh_object('SEAM_InsetBody',vv,[f[::-1] for f in ff],seam,uv)
    panels=[]
    # Boundaries lie at the top, bottom and two sides; the top seam receives laces.
    for k in range(4):
        vv=[];ff=[];uv=[]
        for i in range(N+1):
            t=.012+(PI-.024)*i/N;r=profile(t);gap=min(.20,.00065/max(r,.001))
            for j in range(M+1):
                ang=k*PI/2+gap+(PI/2-2*gap)*j/M
                vv.append((a*math.cos(t),r*math.sin(ang),b+r*math.cos(ang)))
                uv.append((i/N,j/M))
        for i in range(N):
            for j in range(M):
                q=i*(M+1)+j;ff.append((q,q+M+1,q+M+2,q+1))
        o=mesh_object('PANEL_%02d'%(k+1),vv,[f[::-1] for f in ff],skin,uv)
        o.data.materials.append(band)
        # Two plain transverse colour bands, split by seams; no signature swirl or text.
        if rugby:
            for f in o.data.polygons:
                x=sum(o.data.vertices[v].co.x for v in f.vertices)/len(f.vertices)
                f.material_index=1 if .065<abs(x)<.095 else 0
        solid=o.modifiers.new('Panel edge thickness','SOLIDIFY');solid.thickness=.0008;solid.offset=-1
        panels.append(o)
    bake_grain(panels[0],[skin,band] if rugby else [skin])
    if not rugby:
        lace=material('Ivory lace',(.91,.88,.77),.72)
        def z(x,y=0):
            t=math.acos(x/a);rr=profile(t)
            return b+math.sqrt(max(0,rr*rr-y*y))
        # One narrow white leather strip, and exactly eight curved crossing laces.
        vv=[]
        for i in range(33):
            x=-.052+.104*i/32
            for y in [-.004,.004]:vv.append((x,y,z(x,y)+.00035))
        strip=mesh_object('LACE_WhiteStrip',vv,[(2*i,2*i+2,2*i+3,2*i+1) for i in range(32)],lace)
        so=strip.modifiers.new('Leather strip thickness','SOLIDIFY');so.thickness=.0006
        tube('LACE_Long',[(x,0,z(x)+.0018) for x in [-.050+i*.100/48 for i in range(49)]],.0010,lace)
        for i in range(8):
            x=-.042+i*.012
            tube('LACE_Cross_%02d'%(i+1),[(x,y,z(x,y)+.0016+.0012*math.cos(y/.012*PI/2)) for y in [-.012+j*.024/12 for j in range(13)]],.0012,lace)
    return dict(panels=4, crossing_laces=0 if rugby else 8,long_laces=0 if rugby else 1,
        length_m=2*a,short_circumference_m=C['short_circ'],long_circumference_m=C['long_circ'],profile_exponent=C['p'],seam_width_m=.0013,seam_depth_m=.0013)


def shuttle():
    cork=material('White cork cover',(.86,.84,.77),.84)
    feather=material('Ivory feather vanes',(.93,.935,.90),.68)
    shaft=material('Feather shafts',(.76,.75,.65),.65)
    thread=material('Cream binding thread',(.69,.64,.47),.85)
    r=.01325;top=.022
    vv=[(0,0,0)];ff=[]
    for i in range(1,13):
        t=(PI/2)*i/12
        for j in range(64):
            q=2*PI*j/64;vv.append((r*math.sin(t)*math.cos(q),r*math.sin(t)*math.sin(q),r-r*math.cos(t)))
    for j in range(64):ff.append((0,1+(j+1)%64,1+j))
    for i in range(11):
        for j in range(64):
            q=1+i*64+j;n=1+i*64+(j+1)%64;ff.append((q,n,n+64,q+64))
    for j in range(64):
        q=2*PI*j/64;vv.append((r*math.cos(q),r*math.sin(q),top))
    for j in range(64):
        q=1+11*64+j;n=1+11*64+(j+1)%64;ff.append((q,n,n+64,q+64))
    ff.append(tuple(1+12*64+j for j in range(64)))
    mesh_object('CORK_RoundedBase',vv,ff,cork)
    rise=math.sqrt(.066**2-(.0315-.0105)**2)
    def centre(t,ang):
        rad=.0105+.021*t
        return Vector((rad*math.cos(ang),rad*math.sin(ang),top+rise*t))
    for k in range(16):
        ang=2*PI*k/16
        tube('SHAFT_%02d'%(k+1),[centre(i/24,ang) for i in range(25)],.00032,shaft)
        # Closed, slightly cupped vanes; upper tips form the 63 mm skirt circle.
        vv=[];ff=[]
        tangent=Vector((-math.sin(ang),math.cos(ang),0))
        radial=Vector((math.cos(ang),math.sin(ang),0))
        for i in range(17):
            t=.36+.64*i/16
            width=.0056*(.3+.7*math.sin((i/16)*PI/2)**.4)
            for j in range(5):
                s=(j-2)/2
                p=centre(t,ang)+tangent*(width*s)+radial*(.0005*(1-s*s)*math.sin(PI*i/16))
                p.z-=.0032*abs(s)**2*(i/16)**8
                vv.append(tuple(p))
        for i in range(16):
            for j in range(4):
                q=i*5+j;ff.append((q,q+1,q+6,q+5))
        o=mesh_object('FEATHER_%02d'%(k+1),vv,ff,feather)
        sol=o.modifiers.new('Vane thickness','SOLIDIFY');sol.thickness=.00012;sol.offset=0
        # Fine geometric quill barbs give readable feather structure without alpha images.
        for h in range(12):
            t=.43+h*.044
            for sign in [-1,1]:
                points=[centre(t,ang)+radial*.00062,centre(t+.027,ang)+tangent*(sign*.0049)+radial*.00018]
                tube('BARB_%02d_%02d_%s'%(k+1,h,sign),points,.000065,feather)
    for k,t in enumerate([.18,.30]):
        rad=.0105+.021*t+.00045;z=top+rise*t
        tube('BINDING_%02d'%(k+1),[(rad*math.cos(2*PI*j/128),rad*math.sin(2*PI*j/128),z) for j in range(128)],.00045,thread,True)
    return dict(feathers=16,thread_bands=2,feather_length_m=.066,tip_circle_diameter_m=.063,base_diameter_m=.0265,height_m=top+rise)


def ico_axes():
    g=(1+math.sqrt(5))/2
    pts=[Vector(p).normalized() for p in [(0,1,g),(0,-1,g),(1,g,0),(-1,g,0),(g,0,1),(g,0,-1)]]
    return pts


def takraw():
    mat=material('Golden synthetic woven strips',(.92,.57,.065),.48)
    axes=ico_axes();R=.43/(2*PI);half=.212;thickness=.0012
    # Icosahedral six-axis arrangement: twelve pentagonal voids; twenty triangular junction regions.
    # Every ribbon crosses the other five twice. Alternate radial offset at those crossings.
    for k,n in enumerate(axes):
        u=n.cross(Vector((0,0,1))).normalized();v=n.cross(u).normalized()
        events=[]
        for j,m in enumerate(axes):
            if j==k:continue
            for sign in [-1,1]:
                p=n.cross(m).normalized()*sign
                events.append((math.atan2(p.dot(v),p.dot(u))%(2*PI),j))
        events.sort()
        vv=[];ff=[];N=192;W=4
        # Surface cross section has a gentle crown, giving rounded longitudinal edges.
        for i in range(N):
            t=2*PI*i/N;d=u*math.cos(t)+v*math.sin(t)
            idx=min(range(10),key=lambda h:abs((t-events[h][0]+PI)%(2*PI)-PI))
            delta=(t-events[idx][0]+PI)%(2*PI)-PI
            offset=[1,1,-1,1,-1,1][k]*(1 if idx%2==0 else -1)*.00125*min(1,max(0,(PI/10-abs(delta))/.04))
            for layer in range(2):
                for j in range(W+1):
                    s=-half+2*half*j/W
                    radius=R-.0019+offset+(.00022*math.cos(s/half*PI/2))-(thickness if layer else 0)
                    p=(d*math.cos(s)+n*math.sin(s))*radius
                    vv.append(tuple(p))
        stride=2*(W+1)
        for i in range(N):
            ni=(i+1)%N
            for layer in range(2):
                for j in range(W):
                    a=i*stride+layer*(W+1)+j;b=ni*stride+layer*(W+1)+j
                    f=(a,a+1,b+1,b);ff.append(f if layer==0 else f[::-1])
            for j in [0,W]:
                a=i*stride+j;b=ni*stride+j
                ff.append((a,b,b+W+1,a+W+1) if j==0 else (a,a+W+1,b+W+1,b))
        mesh_object('STRIP_%02d'%(k+1),vv,[f[::-1] for f in ff],mat)
    # Scale the envelope to the requested midpoint circumference and put the actual mesh on the floor.
    extent=max(Vector(p).length for o in PARTS for p in [v.co for v in o.data.vertices])
    for o in PARTS:
        for p in o.data.vertices:p.co*=R/extent
    minz=min(v.co.z for o in PARTS for v in o.data.vertices)
    cx=(max(v.co.x for o in PARTS for v in o.data.vertices)+min(v.co.x for o in PARTS for v in o.data.vertices))/2
    cy=(max(v.co.y for o in PARTS for v in o.data.vertices)+min(v.co.y for o in PARTS for v in o.data.vertices))/2
    for o in PARTS:o.location=(-cx,-cy,-minz)
    return dict(strips=6,pentagonal_openings=12,triangular_junctions=20,circumference_m=.43,strip_half_angle_rad=half,
        strip_normals=[list(n) for n in axes],sphere_centre_glb=[-cx,-minz,cy],nominal_radius_m=R)


def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()


def studio():
    s=bpy.context.scene;s.world=bpy.data.worlds.new('Slate studio');s.world.use_nodes=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND')
    bg.inputs['Color'].default_value=(.12,.16,.2,1);bg.inputs['Strength'].default_value=.45
    for name,loc,energy,size in [('Key',(-.6,-.9,1.3),42,.9),('Fill',(.9,-.3,.8),26,.9),('Rim',(0,.9,.9),45,.6)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name
        o.data.energy=energy;o.data.shape='DISK';o.data.size=size;aim(o,TARGET)
    bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO'
    s.camera.data.ortho_scale=C['size']*1.40
    s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.seed=0;s.cycles.use_denoising=True
    s.render.resolution_x=s.render.resolution_y=900;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
    s.camera.location=TARGET+Vector((.38,-.9,.48));aim(s.camera,TARGET)


def render_views():
    s=bpy.context.scene
    for name,delta in [('hero',(.38,-.9,.48)),('front',(0,-1.1,.035)),('side',(1.1,0,.06)),('3q',(-.62,-.85,.60))]:
        s.camera.location=TARGET+Vector(delta);aim(s.camera,TARGET)
        s.render.image_settings.file_format='PNG';s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
        if name=='hero':
            s.render.image_settings.file_format='WEBP';s.render.image_settings.quality=86
            bpy.data.images['Render Result'].save_render(str(HERE/'previews/hero.webp'),scene=s)


def export():
    root=bpy.data.objects[ROOT];deps=bpy.context.evaluated_depsgraph_get();copies=[]
    for obj in root.children_recursive:
        if obj.type not in ['MESH','CURVE']:continue
        me=bpy.data.meshes.new_from_object(obj.evaluated_get(deps),depsgraph=deps)
        bm=bmesh.new();bm.from_mesh(me)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        # Narrow vane barbs and pointed tips are retained; zero-area end caps are removed.
        bad=[f for f in bm.faces if f.calc_area()<1e-14]
        bmesh.ops.delete(bm,geom=bad,context='FACES')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
        cp=bpy.data.objects.new('Export_'+obj.name,me);bpy.context.scene.collection.objects.link(cp)
        cp.matrix_world=obj.matrix_world.copy();copies.append(cp)
    bpy.ops.object.select_all(action='DESELECT')
    for o in copies:o.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
    o=bpy.context.object;o.name='MESH_'+ROOT[6:];o.parent=root
    root.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'exports/optimized.glb'),export_format='GLB',use_selection=True,
        export_yup=True,export_animations=False,export_extras=True,export_normals=True,export_tangents=True,
        export_cameras=False,export_lights=False,export_image_format='JPEG',export_jpeg_quality=82)
    bpy.data.objects.remove(o,do_unlink=True)
    # Blender may emit duplicate texture bindings for a shared image. Deduplicate
    # bindings only; the JPEG and geometry binary data remain unchanged.
    path=HERE/'exports/optimized.glb';data=path.read_bytes()
    size=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+size])
    if doc.get('textures'):
        unique=[];mapping={}
        for i,t in enumerate(doc['textures']):
            if t not in unique:unique.append(t)
            mapping[i]=unique.index(t)
        for m in doc.get('materials',[]):
            if 'normalTexture' in m:m['normalTexture']['index']=mapping[m['normalTexture']['index']]
        doc['textures']=unique
        chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*((-len(chunk))%4)
        tail=data[20+size:]
        path.write_bytes(struct.pack('<IIIII',0x46546c67,2,20+len(chunk)+len(tail),len(chunk),0x4e4f534a)+chunk+tail)


def main():
    for d in ['sources','sources/textures','exports','previews','metadata','reports']:(HERE/d).mkdir(parents=True,exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
        s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        s.render.threads_mode='FIXED';s.render.threads=4
        root=bpy.data.objects.new(ROOT,None);s.collection.objects.link(root)
        root['units']='metres';root['front_axis']='Blender -Y / glTF +Z';root['up_axis']='Blender +Z / glTF +Y'
        facts=oval() if C['kind'] in ['football','rugby'] else shuttle() if C['kind']=='shuttle' else takraw()
        for o in PARTS:o.parent=root
        for k,v in facts.items():
            if isinstance(v,(str,int,float)):root[k]=v
        facts['editable_objects']=[o.name for o in PARTS];facts['blender_version']=bpy.app.version_string
        (HERE/'reports/source-geometry.json').write_text(json.dumps(facts,indent=2)+'\n')
        studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    if '--previews-only' not in sys.argv:export()
    if '--skip-render' not in sys.argv:render_views()


if __name__=='__main__':
    main()
    # The supplied sandbox's PulseAudio worker can hang Blender during shutdown.
    # All writes and exports above are synchronous and closed. Only after success,
    # exit the background process directly; exceptions retain --python-exit-code 1.
    if bpy.app.background:
        import os
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
