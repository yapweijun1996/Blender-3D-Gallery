"""Original fictional community beverage-container kiosk, Blender 5.3."""
import argparse
from collections import defaultdict
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ID="community-beverage-container-return-kiosk"
CLIP="BCR_SAMPLE_ACCEPT"
N=24
parser=argparse.ArgumentParser()
parser.add_argument("--output",type=Path,default=Path(__file__).resolve().parent)
parser.add_argument("--review",type=Path)
parser.add_argument("--skip-render",action="store_true")
a=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
R=a.output.resolve()
for d in ('exports','previews'):(R/d).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.render.fps=30
scene.frame_start=0;scene.frame_end=60

C={}
for name in ("01 Enamel cabinet and footing","02 Fixed illustrative can guide","03 Stationary signage and indicator aperture",
             "04 Captive sample cylinder","05 Two-sided status flag","06 Studio not exported"):
    co=bpy.data.collections.new(name);scene.collection.children.link(co);C[name[:2]]=co

def l(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
def mat(name,hex,rough=.5,metal=0,emission=0):
    q=bpy.data.materials.new(name); rgb=[l(int(hex[i:i+2],16)/255) for i in (0,2,4)]
    q.diffuse_color=(*rgb,1);q.use_nodes=True
    p=q.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=q.diffuse_color
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    p.inputs['Emission Color'].default_value=q.diffuse_color;p.inputs['Emission Strength'].default_value=emission
    return q
cream=mat('Soft oat porcelain enclosure','D2C7AB',.52)
teal=mat('Blue-green powder coating','246D6A',.47,.13)
dark_teal=mat('Dark slate teal inset','20474B',.53,.08)
shadow=mat('Deep shaded guide interior','293C41',.61,.08)
iron=mat('Satin warm grey guide steel','838B83',.47,.38)
rubber=mat('Graphite soft edging','364743',.78)
mint=mat('Light mint guide and sign accent','B9D7B4',.48)
white=mat('Warm lettering','F4EAD4',.59)
sun=mat('Warm amber sample stripe','E1A551',.39,.15)
blue=mat('Unbranded ultramarine SAMPLE shell','33779E',.45,.24)
cap=mat('Sample rolled aluminium','B5C3BA',.38,.48)
idle=mat('Muted amber ready tile','B07C38',.48,.08)
accept=mat('Vivid fictional accepted tile','57B957',.46,.06,.21)
accept_tick=mat('Ivory accepted tick','E6F5C9',.45,.02,.12)
foot=mat('Dark ceramic curb plate','66756B',.78)
stage_m=mat('Studio backdrop','52666A',.72)

def into(o,k):
    for c in list(o.users_collection):c.objects.unlink(o)
    C[k].objects.link(o);return o
def empty(name,co,loc):
    o=bpy.data.objects.new(name,None);C[co].objects.link(o);o.location=loc;o.empty_display_size=.028;return o
def box(name,co,loc,dim,m,bevel=.005,segments=1,parent=None,rotation=None):
    bpy.ops.mesh.primitive_cube_add();o=into(bpy.context.object,co);o.name=name;o.dimensions=dim
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.parent=parent;o.location=loc
    if rotation:o.rotation_euler=rotation
    o.data.materials.append(m)
    if bevel:
        b=o.modifiers.new('Soft visible edge','BEVEL');b.width=bevel;b.segments=segments
        w=o.modifiers.new('Plane normals','WEIGHTED_NORMAL');w.keep_sharp=True
    return o
def mesh(n,co,v,f,materials,mi,parent=None,smooth=False):
    data=bpy.data.meshes.new(n);data.from_pydata(v,[],f);data.update()
    ob=bpy.data.objects.new(n,data);C[co].objects.link(ob);ob.parent=parent
    for m in materials:data.materials.append(m)
    for i,p in enumerate(data.polygons):
        p.material_index=mi[i] if mi is not None else 0;p.use_smooth=smooth
    return ob
def label(name,co,text,loc,m,width,size,parent=None):
    t=bpy.data.curves.new(name,'FONT');t.body=text;t.align_x='CENTER';t.size=size;t.resolution_u=2;t.extrude=.00023;t.materials.append(m)
    o=bpy.data.objects.new(name,t);C[co].objects.link(o);o.parent=parent;o.location=loc;o.rotation_euler.x=math.pi/2
    bpy.context.view_layer.update()
    if o.dimensions.x>width:
        f=width/o.dimensions.x;o.scale=(f,f,f)
    return o
def ring_points(y,rx,rz,z0=0):
    out=[]
    for i in range(N):
        t=math.tau*i/N;out.append((math.cos(t)*rx,y,z0+math.sin(t)*rz))
    return out
def ring_faces(f,mi,a,b,index):
    for k in range(N):
        j=(k+1)%N;f.append((a+k,b+k,b+j,a+j));mi.append(index)
def lathe(n,co,profile,materials,parent=None,z0=0,closed_profile=False):
    v=[];f=[];mi=[]
    for y,r,index in profile:v.extend(ring_points(y,r,r,z0))
    for i,(y,r,k) in enumerate(profile[:-1]):ring_faces(f,mi,i*N,(i+1)*N,k)
    top=(len(profile)-1)*N
    if closed_profile:
        ring_faces(f,mi,top,0,profile[-1][2]);f=[tuple(reversed(q)) for q in f]
    else:
        f.extend((tuple(range(N)),tuple(reversed(tuple(range(top,top+N))))))
        mi.extend((profile[0][2],profile[-1][2]))
    return mesh(n,co,v,f,materials,mi,parent,True)
def barmark(name,co,start,end,width,m,parent=None,depth=.003):
    x,y,z=start; X,Y,Z=end; dist=math.hypot(X-x,Z-z); theta=-math.atan2(Z-z,X-x)
    return box(name,co,((x+X)/2,(y+Y)/2,(z+Z)/2),(dist,depth,width),m,.001,1,parent,(0,theta,0))

# A compact slice of fictional neighbourhood common area and a seamless enclosure.
box('Chamfered curb foot','01',(0,-.012,.041),(.985,.820,.082),foot,.019,2)
box('Green machine plinth','01',(0,.012,.111),(.792,.626,.089),teal,.016,2)
box('Oat lower cabinet','01',(0,.020,.516),(.768,.564,.739),cream,.018,2)
box('Rear closed wall above lower cabinet','01',(0,.284,1.151),(.768,.076,.542),cream,.013,2)
for s in (-1,1):
    box('Oat formed upright','01',(s*.355,.023,1.158),(.070,.520,.602),cream,.012,2)
    box('Colour upright edge','01',(s*.374,-.237,1.165),(.035,.055,.59),teal,.010,1)
box('Curved canopy','01',(0,.022,1.486),(.789,.602,.128),teal,.027,3)
box('Canopy trim','01',(0,-.267,1.426),(.695,.038,.023),mint,.006)
box('Lower recessed front plate','01',(0,-.265,.487),(.679,.048,.638),teal,.019,2)
box('Dark washable kick plate','01',(0,-.275,.214),(.672,.046,.165),dark_teal,.014,1)
for i in range(6):
    box('Shallow service-style vent recess','01',(-.222+i*.087,-.301,.222),(.060,.006,.015),rubber,.002)
box('Thin nonstructural orange lower accent','01',(0,-.290,.358),(.627,.007,.017),sun,.002)
# Real opening uses a front single planar square-to-ring beach, then an open cylindrical wall.
v=[];f=[];m=[]
for layer in (0,1):
    for i in range(N):
        t=math.tau*i/N;x,z=math.cos(t),math.sin(t)
        k=.094 if layer else min(.220/max(abs(x),1e-9),.146/max(abs(z),1e-9))
        v.append((k*x,-.274,1.09+k*z))
for i in range(N):
    q=(i+1)%N;f.append((i,q,N+q,N+i));m.append(0)
mesh('Fixed true-hole intake face','02',v,f,[dark_teal],m)
# Front flange, rim and recessed colour bands without a blind front.
lathe('Fully open swept annular inlet','02',
 [(-.276,.116,0),(-.322,.111,0),(-.329,.105,1),(-.329,.090,1),
  (-.316,.081,2),(-.227,.081,2),(.037,.079,2),(.240,.079,2),
  (.240,.086,0),(-.222,.088,0),(-.268,.116,0)],
 [teal,iron,shadow],z0=1.09,closed_profile=True)
box('Recess side extension L','02',(-.237,.012,1.087),(.084,.539,.290),teal,.007)
box('Recess side extension R','02',(.237,.012,1.087),(.084,.539,.290),teal,.007)
box('Closed apron under intake','02',(0,-.213,.926),(.619,.136,.082),teal,.008)
box('Over intake header','02',(0,-.232,1.255),(.619,.108,.066),teal,.007)
box('Guide under horizontal sample path','02',(0,-.020,1.039),(.107,.698,.020),iron,.003)
for side in (-1,1):
    box('Visible supporting lead-in lip','02',(side*.051,-.246,1.044),(.026,.265,.025),iron,.005,1,rotation=(0,side*.16,0))
    box('Amber protective stop edge','02',(side*.060,-.365,1.048),(.027,.045,.035),sun,.005)
box('Leading-edge marker','02',(0,-.372,1.039),(.126,.020,.022),iron,.004)
# Only generic purpose lettering, a simple fictional signal and a separate demo-only label.
box('Purpose panel above the mouth','03',(0,-.267,1.356),(.664,.042,.152),dark_teal,.014)
label('Purpose label','03','CONTAINER RETURN',(0,-.290,1.351),white,.558,.061)
box('Quiet purpose underline','03',(0,-.291,1.336),(.562,.004,.008),mint,.001)
label('Demo-only label','03','DEMO ONLY',(0,-.291,1.304),mint,.325,.040)
for sign in (-1,1):
    box('Fictional flag recessed vertical frame','03',(.263+sign*.074,-.304,1.154),(.022,.093,.102),teal,.006)
    box('Fictional flag recessed horizontal frame','03',(.263,-.304,1.154+sign*.049),(.132,.093,.018),teal,.005)
box('Dark flag backing behind clearance','03',(.263,-.267,1.154),(.136,.024,.090),shadow,.005)
box('Plain SAMPLE plate','03',(0,-.294,.603),(.281,.015,.094),cream,.010)
label('Sample classification label','03','SAMPLE',(0,-.304,.586),dark_teal,.205,.052)
# Three generic stripes are not identifiers, logos, barcodes or printed schemes.
for i in range(3):
    box('Decorative lower enamel line','03',(0,-.293,.509-i*.035),(.275-i*.051,.004,.011),mint if i<2 else sun,.001)

can=empty('BCR_SAMPLE_CAN','04',(0,-.260,1.09))
lathe('Original guided can with band and caps','04',
 [(-.071,.0254,0),(-.068,.032,0),(-.064,.0355,0),(-.059,.0365,1),
  (-.039,.0375,1),(-.016,.0375,2),(.008,.0375,1),(.046,.0375,0),(.059,.0365,0),
  (.065,.0340,0),(.069,.026,0)],
 [cap,blue,sun],can)
# No barcode/QR: face contains only the demonstration word on the physical disk.
box('Round-face visible SAMPLE ink backing','04',(0,-.0718,0),(.046,.002,.014),blue,.002,1,can)
label('Can says SAMPLE','04','SAMPLE',(0,-.0734,-.004),white,.043,.009,can)
flag=empty('BCR_ACCEPT_FLAG','05',(.263,-.343,1.154))
box('Neutral readiness side','05',(0,-.005,0),(.107,.007,.057),idle,.006,1,flag)
box('Bright final accepted side','05',(0,.005,0),(.107,.007,.057),accept,.006,1,flag)
box('Unmistakable readiness dash','05',(0,-.009,0),(.040,.002,.007),white,.001,1,flag)
barmark('Check-mark short stroke','05',(.026,.009,.000),(.004,.009,-.013),.007,accept_tick,flag)
barmark('Check-mark long stroke','05',(.006,.009,-.013),(-.030,.009,.013),.007,accept_tick,flag)
# Flag rotation around Blender +Z is glTF +Y; can moves straight on Blender +Y.
def animate(o,path,index,frames):
    for f,value in frames:
        getattr(o,path)[index]=value;o.keyframe_insert(data_path=path,index=index,frame=f,group='Fictional one sample reveal')
    act=o.animation_data.action;act.name=o.name+' authored transition'
    tr=o.animation_data.nla_tracks.new();tr.name=CLIP
    tr.strips.new('One simulated sample',0,act)
    o.animation_data.action=None
animate(can,'location',1,[(0,-.260),(4,-.260),(12,-.210),(20,-.099),(28,.028),(36,.138),(39,.165),(60,.165)])
animate(flag,'rotation_euler',2,[(0,0),(39,0),(45,.63),(51,math.pi),(60,math.pi)])

# Ready/studio framing and final close detail are actual model geometry, not new assets.
box('Studio floor outside gallery export','06',(0,0,-.036),(200,200,.066),stage_m,0)
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(name,loc,power,size,c,targ=(0,0,.83)):
    q=bpy.data.lights.new(name,'AREA');q.energy=power;q.shape='DISK';q.size=size;q.color=c
    o=bpy.data.objects.new(name,q);C['06'].objects.link(o);o.location=loc;aim(o,targ)
lamp('Overcast warm courtyard key',(-1.6,-2.3,3.15),142,2.06,(1,.9,.80))
lamp('Cool street fill',(1.8,-1.9,2.35),77,1.7,(.81,.94,1))
lamp('Gentle guide light',(.05,-1.75,1.82),46,.84,(.97,1,.86),(0,0,1.085))
lamp('Rear enamel reflection',(1.1,1.34,2.50),94,1.70,(.82,.95,1))
world=bpy.data.worlds.new('Open shade');scene.world=world;world.use_nodes=True
sky=world.node_tree.nodes['Background'];sky.inputs[0].default_value=(.52,.60,.62,1);sky.inputs[1].default_value=.43
cam_data=bpy.data.cameras.new('Studio camera')
cam=bpy.data.objects.new('Studio camera',cam_data);C['06'].objects.link(cam);scene.camera=cam
cam.location=(1.42,-3.3,1.98);aim(cam,(0,-.035,.79))
cam_data.type='ORTHO';cam_data.ortho_scale=1.88;cam_data.lens=45
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=sys.platform=='darwin'
scene.render.threads_mode='FIXED';scene.render.threads=6
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=-.18
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='WEBP';scene.render.image_settings.quality=93
scene.render.filepath='//previews/studio.webp'
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/(ID+'.blend')),compress=True)
def render(out,frame):
    scene.frame_set(frame);scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
if not a.skip_render:render(R/'previews'/'studio.webp',0)
if a.review:
    render(a.review/'accepted.webp',60)
    cam.location=(.77,-2.4,1.57);aim(cam,(.023,-.17,1.132))
    cam_data.ortho_scale=.91
    scene.render.resolution_x=720;scene.render.resolution_y=565
    render(a.review/'path-ready.webp',0)
    render(a.review/'path-accepted.webp',60)
scene.frame_set(0)
# Export only material batches per original assembly while preserving named animatable parents.
parts=[]
def select(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True);bpy.context.view_layer.objects.active=o
for key,collection in sorted(C.items()):
    if key=='06':continue
    buckets=defaultdict(list)
    for ob in list(collection.objects):
        if ob.type=='EMPTY':
            parts.append(ob);continue
        if ob.modifiers or ob.type!='MESH':
            select(ob);bpy.ops.object.convert(target='MESH');ob=bpy.context.view_layer.objects.active
        names=tuple(m.name for m in ob.data.materials)
        buckets[(ob.parent.name if ob.parent else '',names)].append(ob)
    for (parent,names),obs in sorted(buckets.items()):
        select(obs[0])
        for ob in obs:ob.select_set(True)
        if len(obs)>1:bpy.ops.object.join()
        b=obs[0];b.name=(parent or collection.name[3:])+' | '+names[0];parts.append(b)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(R/'exports'/(ID+'.glb')),export_format='GLB',use_selection=True,
  export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,
  export_cameras=False,export_lights=False,export_extras=False,export_texcoords=False)
