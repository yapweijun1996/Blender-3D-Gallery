"""Original shophouse corner mirror still life. Blender 5.3 procedural geometry."""
import argparse
from collections import defaultdict
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ID='shophouse-lane-convex-mirror'
N=48
RADIUS=.244
SPHERE_RADIUS=.575
BACK_EDGE=-.033
a=argparse.ArgumentParser()
a.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
a.add_argument('--review',type=Path)
a.add_argument('--skip-render',action='store_true')
args=a.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out=args.output.resolve()
for k in ('exports','previews'):(out/k).mkdir(parents=True,exist_ok=True)
if args.review:args.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
C={}
for n in ('01 Corner wall and lane apron','02 Static bolted mount and articulated-looking support',
          '03 Lens, neutral decorative sheen and rolled bezel','04 Fictional decorative chevrons','05 Studio not exported'):
    c=bpy.data.collections.new(n);scene.collection.children.link(c);C[n[:2]]=c

def lin(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def rgb(h):return tuple(lin(int(h[i:i+2],16)/255) for i in (0,2,4))
def mat(n,h,rough=.56,metal=0):
    m=bpy.data.materials.new(n);m.diffuse_color=(*rgb(h),1);m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m

wall=mat('Oat pale limewash','D0BB98',.79)
wall_side=mat('Weathered pale plaster','B8A482',.79)
wall_patch=mat('Subtle repainted patch','C6AC88',.78)
tile=mat('Dull sea green glazed skirting','597F75',.55)
tile2=mat('Moss-green skirting variation','6E9587',.50)
tile_shadow=mat('Warm cement joints','8C9486',.68)
asphalt=mat('Warm grey street surface','697674',.81)
kerb=mat('Worn pale concrete kerb','AEB4A2',.80)
graphite=mat('Warm galvanised paint','51575B',.46,.31)
metal=mat('Satin iron fittings','8F9B94',.44,.54)
rim=mat('Safety-orange fictional enamel','DC793D',.44,.10)
rim_shadow=mat('Orange casing return lip','9A4F32',.51,.16)
gasket=mat('Charcoal edge gasket','3F4545',.65)
white=mat('Faded cream warning plate','E0C18C',.65)
stripe=mat('Faded oxide chevrons','B15A3B',.57)
lens=mat('Convex lens | decorative abstract sheen','D7E6E9',.25,.25)
studio=mat('Cool studio floor','4E6061',.73)
attr=lens.node_tree.nodes.new('ShaderNodeVertexColor');attr.layer_name='LensSheen'
lens.node_tree.links.new(attr.outputs['Color'],lens.node_tree.nodes['Principled BSDF'].inputs['Base Color'])

def put(o,k):
    for c in list(o.users_collection):c.objects.unlink(o)
    C[k].objects.link(o);return o

def empty(n,k,xyz,rot):
    o=bpy.data.objects.new(n,None);C[k].objects.link(o);o.location=xyz;o.rotation_euler=rot;o.empty_display_size=.048;return o

def box(n,k,xyz,dims,m,bevel=.005,segments=1,parent=None):
    bpy.ops.mesh.primitive_cube_add();o=put(bpy.context.object,k);o.name=n;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.parent=parent;o.location=xyz;o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new('Soft visible edge','BEVEL');b.width=bevel;b.segments=segments
        w=o.modifiers.new('Planar corners','WEIGHTED_NORMAL');w.keep_sharp=True
    return o

def poly(n,k,v,f,mats,indices=None,parent=None,smooth=False):
    me=bpy.data.meshes.new(n);me.from_pydata(v,[],f);me.update()
    o=bpy.data.objects.new(n,me);C[k].objects.link(o);o.parent=parent
    for m in mats:me.materials.append(m)
    for i,p in enumerate(me.polygons):
        p.material_index=indices[i] if indices is not None else 0;p.use_smooth=smooth
    return o

def cyl_between(n,k,A,B,r,m,sides=12):
    AA,BB=Vector(A),Vector(B);mid=(AA+BB)/2
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=(BB-AA).length,location=mid)
    o=put(bpy.context.object,k);o.name=n
    o.rotation_euler=(BB-AA).to_track_quat('Z','Y').to_euler()
    o.data.materials.append(m)
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o

def bolt(n,k,x,y,z):
    cyl_between(n,k,(x,y-.013,z),(x,y+.004,z),.017,metal,6)

def bead(n,k,xyz,r,m,scale=(1,1,1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=r,location=xyz)
    ob=put(bpy.context.object,k);ob.name=n;ob.scale=scale;ob.data.materials.append(m)
    for p in ob.data.polygons:p.use_smooth=True
    return ob

# One small, unmistakably segmented corner of a generic lane, not a roadway layout.
box('Dark lane pavement offcut','01',(.004,-.140,.049),(1.12,.870,.098),asphalt,.016,2)
box('Casual pale corner kerb','01',(-.189,.100,.110),(.713,.381,.052),kerb,.010,1)
box('Main limewash pier','01',(-.126,.048,.859),(.654,.253,1.48),wall,.014,2)
box('Short perpendicular return','01',(-.421,.260,.857),(.204,.314,1.436),wall_side,.013,2)
box('Projecting corner cap','01',(-.132,.123,1.620),(.665,.473,.081),wall_side,.013,2)
box('Sunken cement tile bed','01',(-.123,-.088,.307),(.660,.025,.338),tile_shadow,.004)
for zi in range(2):
    for xi in range(5):
        x=-.387+xi*.132; z=.218+zi*.168
        box('Ceramic skirting segment','01',(x,-.106,z),(.124,.026,.156),tile2 if (zi+2*xi)%5 in (0,1) else tile,.004)
for j in range(3):
    box('Angle-return skirting segment','01',(-.520,.121+j*.111,.295),(.027,.103,.318),tile if j%2 else tile2,.004)
box('Soft-painted lower plaster seam','01',(-.102,-.081,.512),(.526,.011,.015),wall_patch,.001)
box('Minor plaster repair seam','01',(-.358,-.082,1.156),(.020,.009,.228),wall_patch,.002)
box('Short lane paint reminiscence, no prescription','01',(.355,-.359,.102),(.225,.035,.003),kerb,.0008)
# Bolt heads, angled gusset and physical tube each visibly join neighboring support.
box('Raised surface mounting plate','02',(.097,-.103,1.339),(.181,.053,.264),graphite,.014,2)
for x,z in ((.038,1.255),(.155,1.255),(.038,1.423),(.155,1.423)):
    bolt('Rounded hex on visible fastener', '02',x,-.140,z)
v=[(.067,-.128,1.267),(.067,-.128,1.403),(.067,-.235,1.381),
   (.127,-.128,1.267),(.127,-.128,1.403),(.127,-.235,1.381)]
poly('Thick triangular load brace', '02',v,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],[graphite])
cyl_between('Fixed elbow reach','02',(.095,-.154,1.376),(.183,-.235,1.432),.033,graphite,16)
bead('Rounded junction at bend','02',(.183,-.235,1.432),.034,metal)
cyl_between('Short angled support socket','02',(.183,-.235,1.432),(.206,-.278,1.468),.025,metal,14)
bead('Cast articulation at fixed display angle','02',(.206,-.278,1.468),.033,graphite)
cyl_between('Backplate spindle','02',(.206,-.278,1.468),(.227,-.322,1.49),.024,metal,12)
back=cyl_between('Actual rear attachment disc','02',(.219,-.302,1.488),(.229,-.342,1.492),.081,graphite,20)
# Pose turns the polished front toward the lane and bows forward toward its −Y.
head=empty('MIRROR_STATIC_MOUNT','03',(.222,-.354,1.491),(math.radians(7),0,math.radians(14)))
def around(y,r):
    return [(r*math.cos(math.tau*i/N),y,r*math.sin(math.tau*i/N)) for i in range(N)]
def outline_skin(n,profile,materials):
    vs=[];fs=[];ms=[]
    for y,r,k in profile:vs.extend(around(y,r))
    for i in range(len(profile)):
        j=(i+1)%len(profile)
        for k in range(N):
            v=(k+1)%N;fs.append((i*N+k,j*N+k,j*N+v,i*N+v));ms.append(profile[i][2])
    return poly(n,'03',vs,fs,materials,ms,head,True)
# Closed cross-section (rear face/base to near edge and back).
outline_skin('Rounded daylight-orange bezel and return',
 [(-.051,.250,0),(-.050,.271,0),(-.042,.282,0),(-.019,.288,0),(.009,.283,1),(.026,.265,1),(.027,.243,2),(-.036,.243,2)],
 [rim,rim_shadow,gasket])
outline_skin('Thin rubber crown at lens lip',
 [(-.053,.242,0),(-.055,.246,0),(-.051,.252,0),(-.042,.250,0),(-.041,.243,0)],
 [gasket])
def sag(r):return math.sqrt(SPHERE_RADIUS**2-r*r)-math.sqrt(SPHERE_RADIUS**2-RADIUS**2)
verts=[(0,BACK_EDGE-sag(0),0)];faces=[]
rings=10
for r in range(1,rings+1):
    p=RADIUS*r/rings;verts.extend(around(BACK_EDGE-sag(p),p))
for i in range(N):
    q=(i+1)%N;faces.append((0,1+i,1+q))
for j in range(rings-1):
    p=1+j*N;d=p+N
    for i in range(N):
        q=(i+1)%N;faces.append((p+i,d+i,d+q,p+q))
front=len(verts)
verts.extend(around(.009,RADIUS))
k0=1+(rings-1)*N
for i in range(N):
    q=(i+1)%N;faces.append((k0+i,front+i,front+q,k0+q))
faces.append(tuple(reversed(range(front,front+N))))
glass=poly('CONVEX_LENS_DECORATIVE_CAP','03',verts,faces,[lens],parent=head,smooth=True)
col=glass.data.color_attributes.new(name='LensSheen',type='FLOAT_COLOR',domain='POINT')
# Deliberately abstract color field, like a sheen. No street, vehicle or scene is baked in.
def mix(A,B,u):return tuple(a+(b-a)*max(0,min(1,u)) for a,b in zip(A,B))
low=rgb('60767C');hi=rgb('D4E3E5');line=rgb('EFF3DC');rimblue=rgb('A2CED2')
for index,(x,y,z) in enumerate(verts):
    X,Z=x/RADIUS,z/RADIUS
    q=(Z+.40+.20*X)*.78
    m=mix(low,hi,q)
    band=math.exp(-((Z+.10-.23*X)/.20)**2)*.49
    m=mix(m,line,band)
    m=mix(m,rimblue,.18*max(0,-X+Z)*.48)
    col.data[index].color=(*m,1)
# Small below-lens chevrons are original scenery marks, not signage approval.
box('Weathered little chevron backing','04',(.094,-.102,.861),(.418,.035,.142),graphite,.010,1)
box('Warm inset chevron fascia','04',(.094,-.124,.861),(.393,.015,.117),white,.004)
for j in range(3):
    x=-.005+j*.093;z=.861;y=-.133
    v=[(x-.027,y,z+.039),(x+.011,y,z+.039),(x+.052,y,z),
       (x+.011,y,z-.039),(x-.027,y,z-.039),(x+.013,y,z)]
    poly('One fictional oxide arrow stripe','04',v,[(0,1,2,5),(5,2,3,4)],[stripe])
for x in (-.087,.277):
    cyl_between('Recessed plate rivet','04',(x,-.140,.861),(x,-.131,.861),.007,metal,10)

# Detached studio for stills; the gallery receives no real reflection/environment image.
box('Studio ground, omitted from export','05',(0,0,-.035),(200,200,.063),studio,0)
def point(o,d):o.rotation_euler=(Vector(d)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,loc,pow,size,col,d=(0,-.07,1.0)):
    light=bpy.data.lights.new(n,'AREA');light.energy=pow;light.size=size;light.shape='DISK';light.color=col
    o=bpy.data.objects.new(n,light);C['05'].objects.link(o);o.location=loc;point(o,d)
lamp('Overcast key for rim',(-1.85,-2.38,3.10),138,2.0,(1,.89,.76))
lamp('Pale open-lane fill',(1.56,-1.91,2.23),76,1.54,(.85,.94,1))
lamp('Shoulder separation',(1.214,.91,2.60),101,1.45,(.78,.93,1))
lamp('Broad stylised sheen',(.355,-2.01,2.71),39,1.01,(.83,.97,1),(.222,-.354,1.49))
world=bpy.data.worlds.new('Neutral overcast studio');scene.world=world;world.use_nodes=True
node=world.node_tree.nodes['Background'];node.inputs[0].default_value=(.48,.54,.56,1);node.inputs[1].default_value=.44
cd=bpy.data.cameras.new('Studio camera not part of asset')
cam=bpy.data.objects.new('Studio camera not part of asset',cd);C['05'].objects.link(cam);scene.camera=cam
cam.location=(1.78,-3.38,2.16);point(cam,(.004,-.066,.900))
cd.type='ORTHO';cd.ortho_scale=2.07;cd.lens=51
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=sys.platform=='darwin'
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.12
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='WEBP';scene.render.image_settings.quality=93
scene.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(ID+'.blend')),compress=True)
def render(p):
    scene.render.filepath=str(p);bpy.ops.render.render(write_still=True)
if not args.skip_render:render(out/'previews/studio.webp')
if args.review:
    cam.location=(2.42,-.66,1.91);point(cam,(.095,-.132,1.386));cd.ortho_scale=.880
    scene.render.resolution_x=720;scene.render.resolution_y=580
    render(args.review/'support-detail.webp')
    cam.location=(.77,-2.27,1.91);point(cam,(.192,-.253,1.431));cd.ortho_scale=.792
    render(args.review/'lens-detail.webp')
# Only same-material/static parts batch; preserve lens mesh and editable native scene.
sel=[]
def select(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
for k,coll in sorted(C.items()):
    if k=='05':continue
    parts=defaultdict(list)
    for o in list(coll.objects):
        if o.type=='EMPTY' or o==glass or o==back:
            sel.append(o);continue
        if o.modifiers or o.type!='MESH':
            select(o);bpy.ops.object.convert(target='MESH');o=bpy.context.view_layer.objects.active
        style=tuple(m.name for m in o.data.materials)
        parts[(o.parent.name if o.parent else '',style)].append(o)
    for (parent,style),obs in sorted(parts.items()):
        select(obs[0])
        for o in obs:o.select_set(True)
        h=obs[0]
        if len(obs)>1:bpy.ops.object.join()
        h.name=(parent or coll.name[3:])+' | '+style[0];sel.append(h)
bpy.ops.object.select_all(action='DESELECT')
for o in sel:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(ID+'.glb')),export_format='GLB',use_selection=True,
    export_animations=False,export_cameras=False,export_lights=False,export_extras=False,export_texcoords=False)
