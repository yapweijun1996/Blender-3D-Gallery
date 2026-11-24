"""An original static woven bubu exhibit; no reproduction, construction or operation claim."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='woven-bubu-fish-trap-display'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 independent contemporary museum support')
last=collection('02 woven bamboo exterior and timber-rattan collars')
loose=collection('03 distinct tapered inward funnel insert')
studio=collection('04 studio only; excluded from export')
def material(name, hx, r, m=0):
    def linear(c):
        s = int(c, 16)/255
        return s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
    col = tuple(linear(hx[i:i+2]) for i in (0,2,4))+(1,)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = col
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = col
    bsdf.inputs['Roughness'].default_value = r
    bsdf.inputs['Metallic'].default_value = m
    return mat

def assign(o,n,c,p,mat=None):
    o.name=n
    if c not in list(o.users_collection):
        c.objects.link(o)
    for old in list(o.users_collection):
        if old != c:
            old.objects.unlink(o)
    o.parent=p
    if mat:
        o.data.materials.append(mat)
    return o

def empty(n,c,p=None,loc=(0,0,0)):
    o=bpy.data.objects.new(n,None)
    c.objects.link(o)
    o.parent=p
    o.location=loc
    o.empty_display_size=.036
    o.rotation_mode='QUATERNION'
    return o

def box(n,c,p,loc,d,mat,b=.003,seg=1):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object
    o.scale=d
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    assign(o,n,c,p,mat)
    o.location=loc
    if b:
        bv=o.modifiers.new('Rounded physical edges','BEVEL')
        bv.width=b
        bv.segments=seg
        wn=o.modifiers.new('Broad flat faces','WEIGHTED_NORMAL')
        wn.keep_sharp=True
    return o

def rod(n,c,p,a,b,r,mat,sides=12):
    a,b=Vector(a),Vector(b)
    d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length)
    o=assign(bpy.context.object,n,c,p,mat)
    o.location=(a+b)/2
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    for face in o.data.polygons:
        face.use_smooth=len(face.vertices)==4
    return o

def mesh(n,c,p,v,f,mat):
    data=bpy.data.meshes.new(n)
    data.from_pydata(v,[],f)
    data.update()
    o=bpy.data.objects.new(n,data)
    return assign(o,n,c,p,mat)

def sweep(n,c,p,coords,r,mat,sides=7,closed=False):
    points=[Vector(k) for k in coords]
    v=[]; f=[]; L=len(points)
    for i,q in enumerate(points):
        t=(points[(i+1)%L] if i<L-1 or closed else q)-(points[i-1] if i or closed else q)
        t.normalize()
        u=t.cross(Vector((0,1,0))).normalized()
        if not u.length:
            u=t.cross(Vector((1,0,0))).normalized()
        w=t.cross(u)
        for k in range(sides):
            theta=k*math.tau/sides
            v.append(q+r*(u*math.cos(theta)+w*math.sin(theta)))
    for i in range(L if closed else L-1):
        j=(i+1)%L
        for k in range(sides):
            l=(k+1)%sides
            f.append((i*sides+k,i*sides+l,j*sides+l,j*sides+k))
    if not closed:
        f.extend([tuple(reversed(range(sides))),tuple(range((L-1)*sides,L*sides))])
    o=mesh(n,c,p,v,f,mat)
    for face in o.data.polygons:
        face.use_smooth=len(face.vertices)==4
    return o

def etch(n,c,p,o,text,size,mat):
    data=bpy.data.curves.new(n,'FONT'); data.body=text; data.align_x='CENTER';data.size=size
    ob=bpy.data.objects.new(n,data);assign(ob,n,c,p,mat);ob.location=o
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH')
    return ob


def linear(x):
    x=max(0,min(255,x))/255
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def vmat(n,rough,metal=0):
    m=material(n,'FFFFFF',rough,metal)
    v=m.node_tree.nodes.new('ShaderNodeVertexColor');v.layer_name='Procedural surface grain'
    m.node_tree.links.new(v.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return m
def apply_color(o,fn):
    c=o.data.color_attributes.new(name='Procedural surface grain',type='FLOAT_COLOR',domain='POINT')
    for v,x in zip(o.data.vertices,c.data):x.color=tuple(linear(k) for k in fn(v.co))+(1,)
def multi(n,c,r,v,f,m,ids,smooth=False):
    o=mesh(n,c,r,v,f,m[0])
    for mat in m[1:]:o.data.materials.append(mat)
    for p,k in zip(o.data.polygons,ids):p.material_index=k;p.use_smooth=smooth and len(p.vertices)==4
    return o
def colored_board(n,c,r,p,d,mat,hue):
    o=box(n,c,r,p,d,mat,.0068,3)
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=o
    for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    apply_color(o,lambda v: tuple(k*(1+.065*math.sin(v.y*99+v.x*9)+.045*math.sin(v.y*186+v.z*5)+.042*math.cos(v.x*21+v.y*50)) for k in hue))
    return o
z0=.410
baseM=vmat('Quiet green slate exhibit base grain',.84)
standM=material('Blue-green enamel independent display cradles','405F5A',.57,.25)
railM=material('Darker quiet grey label fasteners','364943',.56)
strapM=material('Soft olive display bearing pad','879883',.78)
etchM=material('Original pale label letters','E5D2A3',.65)
staveM=vmat('Dry narrow bamboo blade tones',.74)
hoopM=vmat('Golden tan woven bands',.72)
insertM=vmat('Contrast lighter inward funnel basketry',.68)
insertHoop=vmat('Muted gold inward funnel rings',.73)
boundM=vmat('Deep freshly bound split rattan strapping',.76)
endM=vmat('Weathered naturally caramel rim strands',.72)
stone=material('Natural exhibition background matte','577163',.82)
R=empty('WOVEN_BUBU_STATIC_EXHIBIT',base)
S0=empty('INDEPENDENT_DISPLAY_BASE_AND_CRADLES',base,R)
B=empty('OPEN_WOVEN_BAMBOO_OUTER_BASKET',last,R)
P=empty('SEPARATE_INWARD_FUNNEL_AND_CLEAR_THROAT',loose,R)
def glassy(n,c,p,loc,d,mat,tint):
    o=colored_board(n,c,p,loc,d,mat,tint)
    return o
def coord(x,r,a):
    return (x,r*math.sin(a),z0+r*math.cos(a))
def profile(x,table):
    for (a,b),(c,d) in zip(table,table[1:]):
        if x<=c:
            w=max(0,min(1,(x-a)/(c-a)));return b+(d-b)*w
    return table[-1][1]
bodyTab=[(-.641,.223),(-.587,.234),(-.488,.250),(-.355,.257),(-.192,.265),(-.004,.250),
         (.183,.228),(.343,.190),(.464,.148),(.565,.098),(.641,.053)]
funnelTab=[(-.614,.205),(-.545,.183),(-.476,.161),(-.398,.125),(-.317,.098),(-.269,.089),(-.239,.082)]
def with_tone(ob,c,amp=1,seed=0):
    apply_color(ob,lambda v:tuple(k*(1+amp*(.043*math.cos(106*v.x+57*v.z+seed)+.026*math.sin(127*v.y+92*v.z+2*seed))) for k in c))
    return ob
def strip(o,c,p,q,rgb,ring=False,mat=None,seed=0):
    # Each object is a real closed rectangular strip, not a shaded cutout.
    v=[item for row in q for item in row]
    fs=[];n=len(q)
    for i in range(n if ring else n-1):
        for k in range(4):
            j=(i+1)%n;f=(k+1)%4
            fs.append((i*4+k,i*4+f,j*4+f,j*4+k))
    if not ring: fs.extend([(3,2,1,0),tuple(range(4*n-4,4*n))])
    ob=mesh(o,c,p,v,fs,mat)
    # Use the actual oriented volume to remove winding ambiguity.
    import bmesh
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    for f in ob.data.polygons:f.use_smooth=True
    return with_tone(ob,rgb,seed=seed)
def annulus(n,c,p,path,mat,rgb,N=64):
    v=[coord(x,r,j*math.tau/N) for x,r in path for j in range(N)];f=[];L=len(path)
    for i in range(L):
        for j in range(N):
            a=(i+1)%L;b=(j+1)%N
            f.append((i*N+j,i*N+b,a*N+b,a*N+j))
    q=mesh(n,c,p,v,f,mat)
    import bmesh
    bm=bmesh.new();bm.from_mesh(q.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(q.data);bm.free()
    for k in q.data.polygons:k.use_smooth=True
    return with_tone(q,rgb)
def woven(n,c,p,N,courses,edge0,edge1,tab,mLong,mRing,light=False):
    spacing=math.tau/N
    rows=[edge0]+courses+[edge1]
    sectors=[j*spacing for j in range(N)]
    for j,ang in enumerate(sectors):
        a=[]
        for i,xx in enumerate(rows):
            r=profile(xx,tab); phase=0 if i in (0,len(rows)-1) else (1 if (i-1+j)%2==0 else -1)
            rad=r+phase*(.0034 if light else .0055)
            halfw=min(.060*rad,.0073) if light else min(.068*rad,.0103)
            halfang=halfw/rad
            h=.00145 if light else .00225
            a.append([coord(xx,R,A) for R,A in [(rad-h,ang-halfang),(rad+h,ang-halfang),(rad+h,ang+halfang),(rad-h,ang+halfang)]])
        col=(182+(j*19)%29,131+(j*11)%32,76+(j*17)%27) if not light else (195+(j*11)%17,143+(j*13)%25,80+(j*9)%23)
        strip(n+' longitudinal strip '+str(j+1).zfill(2),c,p,a,col,mat=mLong,seed=j*3)
    for i,x in enumerate(courses):
        q=[];halfX=.0038 if light else .0064
        for j in range(N*2):
            a=j*spacing/2; ph=(1 if (i+j//2)%2 else -1) if j%2==0 else 0
            def c0(dx,dh):
                xx=x+dx;r=profile(xx,tab);r+=ph*(.0034 if light else .0055)+dh
                return coord(xx,r,a)
            h=.00155 if light else .00205
            q.append([c0(-halfX,-h),c0(-halfX,h),c0(halfX,h),c0(halfX,-h)])
        col=(152+(i*23)%33,104+(i*7)%24,58+(i*17)%21) if not light else (162+(i*13)%29,115+(i*13)%17,62+(i*11)%22)
        strip(n+' closed transverse weft band '+str(i+1).zfill(2),c,p,q,col,ring=True,mat=mRing,seed=i*4)
N=34
xBands=[-.549+i*.057 for i in range(21)]
yBands=[-.536+i*.039 for i in range(7)]
woven('Outer',last,B,N,xBands,-.613,.630,bodyTab,staveM,hoopM)
woven('Inset',loose,P,26,yBands,-.607,-.239,funnelTab,insertM,insertHoop,True)
# Readable broad mouth, physically overlapping both independent woven edges.
annulus('Actual dark rear mouth wrap seated around body',last,B,[(-.616,.211),(-.565,.214),(-.565,.244),(-.572,.249),(-.607,.246),(-.620,.239)],boundM,[137,91,53],68)
annulus('Original narrow rounded entrance face lip',last,B,[(-.634,.197),(-.616,.197),(-.602,.208),(-.601,.240),(-.614,.246),(-.632,.239),(-.639,.211)],endM,[175,122,67],72)
annulus('Inner throat physical open edge binder',loose,P,[(-.261,.075),(-.241,.073),(-.230,.077),(-.229,.087),(-.239,.093),(-.257,.091)],insertHoop,[149,96,55],52)
annulus('Inset attached wide entrance collar distinct from exterior',loose,P,[(-.622,.193),(-.594,.190),(-.582,.195),(-.585,.210),(-.608,.219),(-.622,.212)],insertHoop,[159,116,64],60)
# The tip is separately wrapped, with geometric overlapping return staves rather
# than a second matching entrance. No replica of a working closure is depicted.
annulus('Small distal dark bound taper end',last,B,[(.606,.046),(.650,.040),(.664,.048),(.664,.063),(.651,.071),(.618,.069),(.605,.061)],boundM,[127,82,49],46)
for j in range(0,N,3):
    a=j*math.tau/N
    p=[coord(x,r,a+t) for x,r,t in [( .627,.055,-.010),(.654,.058,-.009),(.672,.046,.01),(.682,.018,.043)]]
    sweep('Short separate folded tail-end bamboo ends',last,B,p,.003,etchM,7)
# Several true short transverse binder lash strokes on the outside rim, not a printed pattern.
for j in range(0,N,2):
    a=j*math.tau/N
    q=[coord(x,r,a+u) for x,r,u in [(-.621,.240,-.016),(-.611,.249,-.008),(-.588,.251,.009),(-.576,.244,.014)]]
    sweep('Original short separate rattan finish stroke',last,B,q,.0036,etchM,7)
# Two distinct blue-green pads hug the underside. They are contemporary
# exhibit fixtures supported by independent capped feet.
glassy('Independent museum base',base,S0,(.015,0,.034),(1.70,.785,.068),baseM,[81,109,99])
hs=[xBands[4],xBands[16]]
for x in hs:
    r=profile(x,bodyTab)
    # Contact arcs drawn in real cross-section from the lower basket radius.
    pad=[]
    for i in range(17):
        a=math.pi*.75+math.pi*.50*i/16;pad.append((x,r,a))
    v=[];f=[];n=len(pad)
    for X,d in [(x-.027,0),(x+.027,0),(x+.027,.020),(x-.027,.020)]:
        radius=profile(X,bodyTab)+.0076+d
        v += [coord(X,radius,a) for _,_,a in pad]
    for k in range(4):
        for j in range(n-1):
            q=((k+1)%4)*n;u=k*n
            f.append((u+j,u+j+1,q+j+1,q+j))
    f.extend([tuple(j*n for j in range(4)),tuple(j*n+n-1 for j in range(3,-1,-1))])
    o=mesh('Distinct concave exhibit cradle saddle',base,S0,v,f,standM)
    import bmesh
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    for q in o.data.polygons:q.use_smooth=len(q.vertices)==4
    zz=z0-r-.018
    box('Short contemporary upright under saddle',base,S0,(x,0,(.077+zz)/2),(.046,.076,zz-.077+.004),standM,.007,2)
    box('Independent flush exhibit cradle shoe',base,S0,(x,0,.076),(.154,.224,.019),railM,.006,2)
    for y in (-.076,.076):rod('Small dull contrast base foot pin',base,S0,(x,y,.078),(x,y,.089),.013,standM,10)
box('Separate modest exhibit caption strip',base,S0,(.08,-.400,.051),(.436,.026,.041),railM,.003)
etch('Original BUBU placard lettering',base,S0,(.08,-.415,.048),'BUBU  /  WOVEN  DISPLAY',.022,etchM)
box('Studio matte shadow only excluded',studio,None,(0,0,-.027),(100,100,.053),stone,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.33)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights natural split straw',(-2.46,-2.0,2.6),380,2.15,(1,.91,.80))
light('Cool quiet fill shapes old concave support',(1.94,-3.03,1.95),330,2.17,(.83,.94,1))
light('Upper reflected rim on handwoven form',(1.19,1.9,1.85),290,1.57,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(-2.65,-2.55,1.64);target=(0,0,.350)
cd.type='ORTHO';cd.ortho_scale=1.935;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=230;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=52
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_percentage=100;S.render.resolution_x=S.render.resolution_y=512
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=93
S.view_settings.view_transform='AgX';S.view_settings.exposure=.05
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,last,loose):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(slug+'.glb')),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,
                         export_lights=False,export_extras=False)
def still(to,pos,tgt,scale,wh):
    cam.location=pos;look(cam,tgt);cd.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,1.935,(512,512))
if opts.review:
    S.cycles.samples=145
    still(opts.review/'true-funnel-and-throat.webp',(-2.21,-.24,.75),(-.460,0,.410),.665,(650,635))
    still(opts.review/'over-under-open-lattice.webp',(-.37,-1.21,1.15),(-.01,-.153,.540),.915,(670,620))
    still(opts.review/'separate-cradles-and-taper.webp',(.89,-2.15,.695),(.20,0,.300),1.30,(670,610))
