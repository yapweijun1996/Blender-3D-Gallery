"""Original fictional two-tier bicycle tray exhibit; no operational guidance or claim."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='transit-two-tier-bicycle-tray'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 independent lower bay and stand')
last=collection('02 static elevated captured guides')
loose=collection('03 carriage and articulated empty tray')
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
from mathutils import Quaternion
z0=1.427
start=.240
travel=.640
angle=math.radians(38)
railx=.238
gZ=1.401
grange=(-.295,1.100)
floor=vmat('Tropical station paving, original aggregate hue',.83)
blue=material('Industrial muted cool teal fixed frame','397B7E',.57,.36)
blueDark=material('Deep cadet stationary guide outer shell','355359',.53,.44)
steel=material('Brushed metal slider faces','9DAEA8',.45,.68)
lead=material('Slightly aged satin stainless trough body','9CA39A',.46,.62)
dark=material('Deep graphite lower wheel bay contrasted from upper','414B4B',.62,.44)
wear=material('Nylon sleeve and guide pad','51473A',.79,.05)
yellow=material('Muted orange-yellow upper pull handle and stops','E5A940',.58,.06)
yellowDark=material('Noncommercial lower markers and grips','A08652',.72)
ivory=material('Paving line and editorial lettering','E5DFC0',.67)
rubber=material('Original overmolded dark molded grips','364044',.68)
R=empty('TRANSIT_TWO_TIER_BICYCLE_TRAY_EXHIBIT',base)
F=empty('STATIONARY_LOWER_BAY_AND_FIXED_FRAME',base,R)
G=empty('CAPTURED_FIXED_LEFT_AND_RIGHT_GUIDES',last,R)
M=empty('BIKE_UPPER_CARRIAGE',loose,R,(0,start,z0))
P=empty('BIKE_UPPER_TRAY_PIVOT',loose,M,(0,0,0))
def deck(name,c,p,y0,y1,w,zTop,zBot,mat,bevel=.006):
    return box(name,c,p,(0,(y0+y1)/2,(zTop+zBot)/2),(w,y1-y0,zTop-zBot),mat,bevel,2)
def sidewall(name,c,p,pts,x0,x1,mat):
    # XY plate extruded normal to local X: ordered along the near profile.
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1]))
    if area<0:pts=list(reversed(pts))
    V=[(x,y,z) for x in (x0,x1) for y,z in pts];k=len(pts)
    f=[tuple(reversed(range(k))),tuple(range(k,k*2))]
    f.extend((i,(i+1)%k,(i+1)%k+k,i+k) for i in range(k))
    return mesh(name,c,p,V,f,mat)
def annular_knuckle(name,parent,xa,xb,r0,r1,mat):
    V=[];f=[];n=28
    for x,r in [(xa,r0),(xa,r1),(xb,r1),(xb,r0)]:
        for j in range(n):
            t=j*math.tau/n;V.append((x,math.cos(t)*r,math.sin(t)*r))
    for i in range(4):
        for j in range(n):
            k=(j+1)%n;a=i*n;b=((i+1)%4)*n
            f.append((a+j,b+j,b+k,a+k))
    o=mesh(name,loose,parent,V,f,mat)
    for k,q in enumerate(o.data.polygons):q.use_smooth=k//n in (1,3)
    return o
def capsule(name,p,x,z,y0,y1,w,h,m,bv=.004):
    return box(name,loose,p,(x,(y0+y1)/2,z),(w,y1-y0,h),m,bv,2)
pl=box('Fictional grey transit paver section',base,F,(0,-.310,.033),(1.18,2.990,.066),floor,.019,3)
bpy.context.view_layer.update();bpy.context.view_layer.objects.active=pl
for mod in list(pl.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
apply_color(pl,lambda v:(124+7*math.sin(v.x*11+v.y*21),133+4*math.cos(v.x*39-v.y*12),125+4*math.cos(v.x*17+v.y*37)))
for s in (-1,1):
    for y in [-1.21,-.48,.25,.98]:
        box('Inlaid simplified parking boundary guide, not regulatory',base,F,(s*.449,y,.0668),(.019,.525,.0022),ivory,.001)
    x=s*.340
    box('Rear frame bolted footing',base,F,(x,.970,.083),(.181,.204,.032),blueDark,.009,2)
    box('Vertical fixed rack support',base,F,(x,.970,.716),(.088,.101,1.268),blue,.012,2)
    box('Cantilever shoulder fixed bracket',base,F,(x,.834,1.323),(.115,.395,.091),blue,.009,2)
    rod('Diagonal rear fixed shoulder brace',base,F,(x,.937,.987),(x,.695,1.304),.026,blueDark,12)
    for dx,dy in [(-.055,-.050),(.055,-.050),(-.055,.050),(.055,.050)]:
        rod('Small rear bolt socket cap',base,F,(x+dx,.97+dy,.088),(x+dx,.97+dy,.108),.014,steel,6)
box('Fixed rear raised beam beneath guide pair',base,F,(0,.872,1.334),(.779,.154,.077),blue,.011,2)
# Stable empty lower channel, different color, visually independent.
deck('Stationary lower bike trough floor',base,F,-.91,.873,.207,.093,.071,dark,.009)
for x in [-.095,.095]:
    b=box('Lower fixed separate rounded side wall',base,F,(x,-.010,.105),(.026,1.790,.055),dark,.008,2)
for y in [-.705,.650]:
    box('Visible underside lower short fixed footing',base,F,(0,y,.071),(.249,.100,.019),blueDark,.004,2)
pts=[(-.105,.602,.105),(-.105,.645,.254),(-.077,.693,.318),(0,.708,.324),(.077,.693,.318),(.105,.645,.254),(.105,.602,.105)]
sweep('Parked lower curved wheel catch, no bicycle',base,F,pts,.014,steel,12)
box('Lower inactive end bumper',base,F,(0,.793,.100),(.157,.040,.063),rubber,.008,2)
# Twin true C-shaped guide sleeves. The upper, lower and outside webs are
# independent pieces; amber pads identify restrained motion without a brand cue.
A,B=grange
for s,word in [(-1,'LEFT'),(1,'RIGHT')]:
    x=s*railx
    for z,nom in [(gZ+.040,'CAPTURE_TOP'),(gZ-.040,'CAPTURE_BOTTOM')]:
        box('FIXED_GUIDE_'+word+'_'+nom,last,G,(x,(A+B)/2,z),(.080,B-A,.014),blueDark,.004,2)
    box('FIXED_GUIDE_'+word+'_OUTER_WEB',last,G,(x+s*.039,(A+B)/2,gZ),(.015,B-A,.092),blue,.005,2)
    box('Fixed visible steel maker-neutral sleeve nose',last,G,(x+s*.038,A+.017,gZ),(.021,.050,.093),steel,.005,2)
    box('Short contrasting guide end-stop detail',last,G,(x+s*.038,B-.024,gZ),(.020,.043,.085),yellowDark,.006,2)
    box('Sensing-free long captured slider runner '+word,loose,M,(x,.398,-.026),(.041,.796,.041),steel,.005,3)
    box('Flush guide wear stripe on retained slider '+word,loose,M,(x,.437,-.0047),(.031,.707,.0025),wear,.0008)
    box('Forward carriage fork side pillar '+word,loose,M,(s*.155,.040,-.002),(.053,.101,.051),blue,.006,2)
    odd=(s*.179,s*.121); xa,xb=sorted(odd)
    annular_knuckle('Fixed carriage bored outer hinge knuckle '+word,M,xa,xb,.0169,.033,blueDark)
    rod('Fixed hinge axle end retaining cap '+word,loose,M,(s*.185,0,0),(s*.190,0,0),.020,steel,16)
box('Clear central bridge behind the pivot on slider carriage',loose,M,(0,.100,-.023),(.482,.045,.050),blue,.006,2)
for s in [-1,1]:
    box('Nose fork connecting end to paired running beam',loose,M,(s*.197,.071,-.026),(.095,.047,.046),blue,.004,2)
rod('One fixed continuous hinge axle across carriage and tray',loose,M,(-.188,0,0),(.188,0,0),.0145,steel,22)
# Two-channel upper tray assembly with real tire saddle and separate folded rails.
for xa,xb in [(-.108,-.062),(-.023,.023),(.062,.108)]:
    annular_knuckle('Moving tray bored inner hinge knuckle',P,xa,xb,.0169,.033,lead)
    box('Tray body coupled to its inner hinge flanges',loose,P,((xa+xb)/2,-.023,.024),(xb-xa,.067,.037),lead,.004,2)
deck('Upper tray actual continuous wheel trough bed',loose,P,-1.153,.033,.176,.059,.037,lead,.007)
for s in [-1,1]:
    x=s*.082
    # The folded bottom and raised edge are independently modeled in the empty channel.
    capsule('Upper tray interior through-running folded flange',P,x,.072,-1.13,.025,.020,.031,lead,.004)
    capsule('Upper tray underside stiffening channel',P,x,.028,-1.119,.030,.022,.019,blue,.005)
    wall=[(-.986,.072),(-.962,.112),(-.880,.142),(-.770,.117),(-.728,.087),(-.775,.071)]
    sidewall('Raised rear wheel saddle with actual open bed',loose,P,wall,min(s*.072,s*.103),max(s*.072,s*.103),yellow)
    wall=[(-.318,.072),(-.293,.094),(-.224,.104),(-.180,.076),(-.220,.067)]
    sidewall('Shallow near-hinge wheel shoulder aligned with tray',loose,P,wall,min(s*.080,s*.114),max(s*.080,s*.114),lead)
for y in [-.998,-.670,-.130]:
    capsule('Shallow transverse capture saddle floor strip',P,0,.064,y-.014,y+.014,.150,.012,wear,.004)
# Rounded orange exhibition handle make slope/extension easy to see.
hs=[(-.100,-1.09,.076),(-.137,-1.156,.060),(-.137,-1.201,.045),(-.110,-1.230,.040),(.110,-1.230,.040),(.137,-1.201,.045),(.137,-1.156,.060),(.100,-1.09,.076)]
sweep('Clear painted upper motion handle',loose,P,hs,.014,yellow,12)
rod('Centered dark grip on painted rail counterpart',loose,P,(-.073,-1.231,.040),(.073,-1.231,.040),.0185,rubber,16)

# A single strictly two-track authored pose clip. No stay frames have spare motion.
clip='TWO_TIER_TRAY_SLIDE_TIP'
S.render.fps=30;S.render.fps_base=1.0;S.frame_start=0;S.frame_end=72
S.timeline_markers.new('Parked state',frame=0)
S.timeline_markers.new('Slides level before pivot',frame=36)
S.timeline_markers.new('Lowered empty tray hold',frame=63)
def easing(x):
    a=max(0,min(1,x));return a*a*(3-2*a)
channels=[(M,'location'),(P,'rotation_quaternion')]
for fr in range(73):
    f=fr/30
    q=easing(f/1.2);r=easing((f-1.2)/.9)
    M.location=(0,start-travel*q,z0)
    P.rotation_quaternion=Quaternion((1,0,0),angle*r)
    for owner,prop in channels:owner.keyframe_insert(data_path=prop,frame=fr)
for owner,prop in channels:
    act=owner.animation_data.action
    act.name=owner.name+' sampled authored motion'
    fs=act.layers[0].strips[0].channelbag(owner.animation_data.action_slot).fcurves if hasattr(act,'layers') else act.fcurves
    for curve in fs:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    track=owner.animation_data.nla_tracks.new();track.name=clip
    track.strips.new('Illustrative model motion only',0,act)
    owner.animation_data.action=None
S.frame_set(0)
box('Studio matte shadow only excluded',studio,None,(0,0,-.027),(100,100,.053),blueDark,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,-.15,.76)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights metal tray and fixed guides',(-3,-4.1,4.3),635,2.8,(1,.91,.80))
light('Cool quiet fill shapes old station paving',(3.45,-2.23,3.44),500,2.9,(.83,.94,1))
light('Upper reflected rim on highlights raised upper tray',(1.9,3.1,3.25),435,2.4,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(3.48,-4.27,3.04);target=(.0,-.31,.64)
cd.type='ORTHO';cd.ortho_scale=3.32;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=192;S.cycles.use_denoising=False
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
                         export_texcoords=False,export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_cameras=False,
                         export_lights=False,export_extras=False)
def still(to,f,pos,tgt,scale,wh):
    S.frame_set(f);cam.location=pos;look(cam,tgt);cd.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not opts.skip_render:still(out/'previews/studio.webp',0,hero,target,3.32,(512,512))
if opts.review:
    S.cycles.samples=128
    for n,f in [('extended-horizontal',36),('lowered-angled',72)]:
        still(opts.review/(n+'.webp'),f,hero,target,3.32,(650,650))
    still(opts.review/'lowered-pivot-and-retained-guides.webp',72,(1.82,-1.23,2.12),(.04,-.10,1.40),1.06,(640,600))
    still(opts.review/'low-side-sweep-clearance.webp',72,(3.80,-.97,1.21),(.03,-.25,.756),2.96,(675,580))
