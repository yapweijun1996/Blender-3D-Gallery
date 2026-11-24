"""Original static Malaysian pasar malam round pan and cooling display."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='pasar-malam-apam-balik-pan-station'
out=a.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
import random
base=collection('01 countertop stand, dark teal frame and iron cradles')
pans=collection('02 independent genuine concave pan profiles and removable dome')
serve=collection('03 elevated open cooling grid and one original folded sample')
studio=collection('04 studio only, excluded from export')
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


ice=material('Brushed neutral stainless', 'A3B3AD', .38, .55)
light=material('Neutral polished highlights', 'CBD2C2', .30, .51)
black=material('Blue black iron base', '323C38', .59, .45)
teal=material('Aged petrol enamel', '336F67', .47, .27)
teall=material('Slightly brighter section edges', '659189', .45, .26)
iron=material('Seasoned cool dark cast-pan wall', '484841', .57, .44)
hot=material('Used cast-iron basin base', '4F4A41', .70, .57)
burn=material('Warm softened patina band', '5C5040', .64, .56)
used=material('Muted bronze second pan', '786446', .55, .58)
usedb=material('Warm basin inner ring', '856D4B', .57, .59)
smoke=material('Weathered radial inner band','6F5B43',.55,.51)
domeMat=material('Warm satin thin formed display dome', 'B6AC8F', .45, .51)
wood=material('Toasted red wooden grip', '6C3D2E', .66)
woodL=material('Midgrain shaped handle', '8C5539', .61)
label=material('Cream panel lettering', 'F3E5C3', .61)
rub=material('Dark counter feet', '313B37', .79)
brass=material('Deep aged brass edge and pointer', 'A48255', .44, .45)
toast=material('Vertex-coloured original baked surface and pale cut edge', 'FFFFFF', .80)
toast_attr=toast.node_tree.nodes.new('ShaderNodeVertexColor')
toast_attr.layer_name='Original Bake Colour'
toast.node_tree.links.new(toast_attr.outputs['Color'],toast.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
pore=material('Dark toasted surface pore accents','73431F',.87)
poreLight=material('Muted caramel flecks of baked surface','98562D',.86)
inside=material('Open cut-edge soft airy interior', 'DEAD66', .82)
deepfill=material('Subdued crease in folded sample', '855436', .76)
paper=material('Muted neutral liner ends', 'ABA17E', .83)
floor=material('Soft pale studio surface', 'C5C5B4', .87)
R=empty('APAM_BALIK_PAN_STATION_EXHIBIT',base)
T=empty('STATIC_COUNTER_STAND',base,R)
PC=empty('TWO_INDEPENDENT_ROUND_APAM_PANS',pans,R)
F=empty('STATIC_COOLING_DISPLAY',serve,R)

def hollow(s,c,p,prof,mats,face_material,count=60,cap=(False,False),reverse=False):
    v=[(r*math.cos(i*math.tau/count),r*math.sin(i*math.tau/count),z) for r,z in prof for i in range(count)]
    faces=[]; ids=[]
    for j in range(len(prof)-1):
        for i in range(count):
            ii=(i+1)%count
            faces.append((j*count+i,j*count+ii,(j+1)*count+ii,(j+1)*count+i))
            ids.append(face_material[j])
    if cap[0]: faces.append(tuple(reversed(range(count))));ids.append(face_material[0])
    if cap[1]: faces.append(tuple(range((len(prof)-1)*count,len(prof)*count)));ids.append(face_material[-1])
    if not any(cap):
        for i in range(count):
            ii=(i+1)%count; k=(len(prof)-1)*count
            faces.append((k+i,k+ii,ii,i));ids.append(face_material[-1])
    ob=mesh(s,c,p,v,[tuple(reversed(f)) for f in faces] if reverse else faces,mats[0])
    for m in mats[1:]:ob.data.materials.append(m)
    for face,mid in zip(ob.data.polygons,ids):
        face.material_index=mid
        face.use_smooth=len(face.vertices)==4
    return ob

box('Beveled upper worktop skin',base,T,(0,0,.544),(1.416,.702,.040),ice,.014,3)
box('Rounded front folded stainless edge',base,T,(0,-.346,.527),(1.393,.034,.052),light,.011,3)
box('Raised back lip, stops short of removable dome recess',base,T,(0,.335,.579),(1.386,.036,.085),ice,.013,3)
box('Dark roughened canopy-free skirt',base,T,(0,-.294,.462),(1.294,.088,.121),teal,.012,3)
box('Sand-toned enamel panel with teeth folded into front skirt',base,T,(-.192,-.348,.459),(.555,.026,.081),teall,.009,2)
etch('Original baked enamel title, no real seller name',base,T,(-.192,-.362,.445),'APAM BALIK',.053,label)
for x in (-.660,.660):
    for y in (-.254,.257):
        box('Splayed-look square tube work stand foot',base,T,(x,y,.244),(.050,.050,.451),teal,.008,2)
        box('Fitted rubber foot over each steel tube',base,T,(x,y,.022),(.063,.062,.043),rub,.008,2)
    box('Side frame crosspiece fastened into legs',base,T,(x,.006,.210),(.041,.496,.048),teal,.008,2)
    box('Steel skirt side edging',base,T,(x,.014,.457),(.044,.611,.109),teall,.011,2)
for y in (-.225,.226):
    box('Shelving horizontal edge crossbar',base,T,(0,y,.157),(1.321,.035,.040),teal,.008,2)
box('Open lower utility shelf',base,T,(0,0,.174),(1.322,.478,.030),ice,.011,3)
for x in (-.53,.53):
    for z in (.477,.510):
        rod('Folded fascia raised stud stays metallic',base,T,(x,-.332,z),(x,-.347,z),.0058,light,12)
for x in (.468,.558):
    box('Small brushed design accent in front skirt',base,T,(x,-.340,.452),(.065,.018,.018),brass,.006,2)
# Each station: original annular seated base and independent pan with an open concavity.
pan_z=.593
for side,x in [('LEFT',-.448),('RIGHT',-.025)]:
    support=empty('PAN_'+side+'_PHYSICAL_REST_RING',pans,PC,(x,-.078,.563))
    standProf=[(.102,0),(.146,0),(.150,.006),(.149,.020),(.141,.024),(.116,.024),(.111,.020),(.112,.014),(.103,.010)]
    hollow('Short passive annular iron trivet '+side,pans,support,standProf,[black,iron,light],[0,0,1,1,1,0,0,0,0],48)
    pan=empty('APAM_OPEN_PAN_'+side,pans,PC,(x,-.078,pan_z))
    # Bottom is a thick closed disk; inside rises to a radiused rolled lip.
    shape=[(.008,-.006),(.089,-.006),(.126,-.006),(.143,.006),(.153,.019),
           (.158,.036),(.157,.041),(.151,.043),(.145,.041),(.142,.034),
           (.139,.022),(.131,.011),(.119,.004),(.099,.001),(.077,0),(.045,0),(.008,0)]
    if side=='LEFT':
        mats=[iron,hot,burn,light]; colors=[0,0,0,0,0,0,2,2,0,2,2,1,2,1,1,1]
    else:
        mats=[burn,used,usedb,smoke]; colors=[0,0,0,0,3,1,2,2,1,2,1,3,1,3,1,1]
    hollow('Walled concave radial pan basin '+side,pans,pan,shape,mats,colors,64,(True,True))
    # Original arched steel and wooden grip fastens through two integral side ears.
    ang=math.radians(-108 if side=='LEFT' else -79)
    U=Vector((math.cos(ang),math.sin(ang),0));V=Vector((-U.y,U.x,0))
    def local(t,l,z):return tuple((U*t+V*l+Vector((0,0,z))))
    for s in (-1,1):
        rod('Grip steel prong '+side,pans,pan,local(.146,s*.023,.022),local(.196,s*.023,.019),.0058,black,10)
        rod('Pan side grip visible fixing '+side,pans,pan,local(.149,s*.022,.019),local(.153,s*.022,.027),.005,light,12)
    rod('Shaped red hardwood pan grip '+side,pans,pan,local(.199,-.041,.019),local(.199,.041,.019),.016,wood,16)
    for s in [-1,1]:
        rod('Warm wrapped grip bands '+side,pans,pan,local(.199,.028*s-.004,.019),local(.199,.028*s+.004,.019),.0162,woodL,14)
# Independent closed-metal lid shell parked diagonally in the stand, not part of pans.
D=empty('REMOVABLE_DOMED_LID',pans,PC,(.073,.221,.718))
D.rotation_mode='XYZ';D.rotation_euler.x=math.radians(66)
lidProf=[(.006,.108),(.034,.105),(.069,.094),(.104,.073),(.134,.046),(.152,.020),
         (.158,.007),(.157,.002),(.151,0),(.148,.006),(.148,.014),(.128,.044),(.098,.066),
         (.064,.086),(.032,.098),(.006,.101)]
# Profile travels outward along the outside, then inward from the rim along the inside.
hollow('True hollow thin removable domed lid',pans,D,lidProf,[domeMat,light,burn],[0,0,0,0,0,0,1,1,1,2,2,2,2,2,2],56,(True,True),reverse=True)
rod('Stainless top knob seat',pans,D,(0,0,.102),(0,0,.123),.025,light,20)
hollow('Lathed round turned hardwood dome knob',pans,D,[(.018,.121),(.021,.128),(.018,.141),(.027,.155),(.029,.163),(.021,.169),(.005,.170)],[wood,woodL],[0,0,1,0,1,1],24,(True,True))
# Parked holder has two actual soft-looking cradles reaching the installed arc.
Rx=66*math.pi/180
for x in [-.094,.094]:
    rad=.151
    localy=-math.sqrt(rad*rad-x*x)
    q=Vector((.073+x,.221+math.cos(Rx)*localy,.718+math.sin(Rx)*localy))
    rod('Stainless removable-dome supporting stem',pans,PC,(q.x,q.y,.559),(q.x,q.y,q.z-.007),.012,ice,14)
    for yy in (-.012,.012):
        rod('Formed padded contact on dome stand',pans,PC,(q.x-.012,q.y+yy,q.z-.008),(q.x+.012,q.y+yy,q.z+.009),.006,black,10)
    box('Lid stand weighted foot plate on brushed table',pans,PC,(q.x,q.y,.571),(.036,.060,.012),ice,.003,2)
# Raised open stainless rack with actual clear openings, not a printed pattern.
S0=empty('OPEN_WIRE_COOLING_RACK',serve,F,(.408,-.055,.634))
rackz=0
for x in (-.152,.152):
    for y in (-.199,.192):
        rod('Cooling rack corner foot',serve,S0,(x,y,-.070),(x,y,-.010),.011,black,13)
        rod('Cooling rack foot cap',serve,S0,(x,y,-.069),(x,y,-.060),.015,rub,14)
    rod('Long stainless cooling frame',serve,S0,(x,-.201,-.008),(x,.195,-.008),.0058,light,13)
for y in (-.197,.192):
    rod('Open cooling frame short span',serve,S0,(-.157,y,-.008),(.157,y,-.008),.006,light,14)
for i in range(16):
    y=-.175+.023*i
    rod('Independent cooling rack wire',serve,S0,(-.151,y,0),(.151,y,0),.0032,ice,9)
for x in (-.078,.079):
    rod('Rack spacing support lower longitudinal wire',serve,S0,(x,-.194,-.005),(x,.191,-.005),.0031,light,10)
# One folded sample: actual upper/lower shaped shell and a small visible dark crease.
# No albedo images: toast and cut edge color follows original geometry and small topology.
P=empty('ONE_FIXED_ORIGINAL_FOLDED_APAM_SAMPLE',serve,F,(.411,-.134,.6371))
P.rotation_mode='XYZ';P.rotation_euler.z=math.radians(-15)
rng=random.Random(513)
def sample_half(n,z0,z1,r,nudge=0):
    # full boundary runs along irregular arc and closes along a shallow wavy fold spine
    outline=[(r*math.cos(math.pi*k/34),r*math.sin(math.pi*k/34)) for k in range(35)]
    outline.extend([(-r+2*r*k/10, -.0020*math.sin(math.pi*k/10)) for k in range(1,10)])
    levels=[(.98,z0),(1,z0+.003),(1,z1-.003),(.965,z1),
            (.83,z1+.00030),(.70,z1+.00064),(.565,z1+.00105),(.43,z1+.00145),
            (.29,z1+.00198),(.15,z1+.00265)]
    lin=lambda c: (c/255)/12.92 if c/255<.04045 else ((c/255+.055)/1.055)**2.4
    def colors(stain,cut):
        orig=(151,78,33) if not cut else (193,144,73)
        return tuple(lin(max(0,min(255,k*stain))) for k in orig)+(1,)
    v=[];faces=[]; tint=[]
    for ring,(scale,z) in enumerate(levels):
        for j,(x,y) in enumerate(outline):
            q=1+.009*math.sin(2.9*j+nudge)+.009*math.sin(.55*j-nudge)
            xx=x*scale*q; yy=(y-.047)*scale*q+.047
            should = .0014*math.sin(j*.9+nudge) if ring<4 else .00050*math.sin(j*.55+ring*.68+nudge)*scale
            v.append((xx,yy,z+(0 if ring==0 else should)))
            edge=1 if ring>=4 else (.69,.77,.87,.90)[ring]
            stain=edge*(.99+.095*math.sin(46*xx+15*yy)+.065*math.cos(69*yy-29*xx)+.027*math.sin(154*xx+113*yy))
            tint.append(colors(stain,ring<3 and j>=35))
    L=len(outline)
    faces.append(tuple(reversed(range(L))))
    for j in range(len(levels)-1):
        for k in range(L):
            l=(k+1)%L
            faces.append((j*L+k,j*L+l,(j+1)*L+l,(j+1)*L+k))
    center=len(v);v.append((0,.050,z1+.0042));tint.append(colors(.99,False))
    for k in range(L):faces.append((center,(len(levels)-1)*L+k,(len(levels)-1)*L+(k+1)%L))
    o=mesh(n,serve,P,v,faces,toast)
    attr=o.data.color_attributes.new(name='Original Bake Colour',type='FLOAT_COLOR',domain='POINT')
    for color,value in zip(attr.data,tint):color.color=value
    for poly in o.data.polygons:poly.use_smooth=True
    return o
sample_half('Pancake true baked lower folded shell',0,.014,.125,1)
top=sample_half('Pancake upper turned-over shell and irregular edge',.016,.030,.122,3)
pts=[(-.112+.224*k/16,.008+.003*math.sin(k*.8),.0156+.0007*math.sin(k*.4)) for k in range(17)]
sweep('Dark edible-looking folded seam, no recipe data',serve,P,pts,.0038,deepfill,8)
# Pore-shaped original browned marks follow the actual shell; no raster images.
surface_rng=random.Random(514)
bm=BVHTree.FromPolygons([v.co.copy() for v in top.data.vertices],[tuple(f.vertices) for f in top.data.polygons])
pv=[];pf=[];pi=[]
for i in range(172):
    while True:
        x,y=surface_rng.uniform(-.112,.112),surface_rng.uniform(.010,.114)
        if x*x+y*y<.112*.112:break
    d=surface_rng.uniform(.00062,.00176);w=d*surface_rng.uniform(.7,1.17); turn=surface_rng.uniform(0,math.pi)
    samples=[(x+d*math.cos(k*math.pi/3+turn),y+w*math.sin(k*math.pi/3+turn)) for k in range(6)]
    topPts=[bm.ray_cast(Vector((xx,yy,.05)),Vector((0,0,-1)))[0] for xx,yy in samples]
    if not all(p is not None for p in topPts):continue
    fst=len(pv);pv.extend((v.x,v.y,v.z+.00017) for v in topPts)
    pf.append(tuple(range(fst,fst+6)));pi.append(1 if (i%4) else 0)
dots=mesh('Original scattered cast-patina pores only on the folded crust',serve,P,pv,pf,pore)
dots.data.materials.append(poreLight)
for face,mid in zip(dots.data.polygons,pi):face.material_index=mid
# Raised small amber crumbs are decoration on the original open cutting/fold line, not a process.
for i in range(18):
    xx=-.104+i*.012+(.002*rng.random());yy=.004+.005*rng.random()
    point=(xx,yy,.017+.0013*rng.random())
    rod('Subtle warm fold cross-section fleck',serve,P,(point[0],point[1],point[2]-.001),(point[0]+.0006,point[1]-.0004,point[2]+.0012),.0013,inside,7)
# Utensil with visibly separate offset blade/neck, ground plane/contact.
U=empty('STATIC_OFFSET_TURNER_SAMPLE',serve,F,(-.111,.220,.5635))
U.rotation_mode='XYZ';U.rotation_euler.z=math.radians(19)
box('Thin rounded original stainless turner blade',serve,U,(-.075,0,.004),(.128,.058,.007),light,.003,3)
rod('Offset turner formed neck',serve,U,(-.016,0,.006),(.044,0,.023),.005,ice,12)
rod('Offset turner oiled timber grip',serve,U,(.039,0,.022),(.128,0,.022),.010,wood,16)
for j in (.048,.119):
    rod('Turner small brass bolster',serve,U,(j-.003,0,.022),(j+.003,0,.022),.0106,brass,12)
box('Studio only matte stage',studio,None,(0,0,-.026),(200,200,.052),floor,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,pos,w,s,col,aim=(0,-.06,.54)):
    d=bpy.data.lights.new(n,'AREA');d.energy=w;d.size=s;d.shape='DISK';d.color=col
    o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=pos;look(o,aim)
lamp('Broad key emphasizes distinct dark pan cavity',(-2.5,-2.5,2.95),410,3.12,(1,.91,.79))
lamp('Cool soft contrast for stainless edges',(2.1,-1.7,2.27),265,2.42,(.80,.92,1))
lamp('Rim light across baked sample',(1.2,1.5,2.9),220,2.44,(1,.93,.81))
world=bpy.data.worlds.new('Neutral workshop daylight');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.53,.55,.55,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.51
cd=bpy.data.cameras.new('Studio orthographic camera');cam=bpy.data.objects.new('Studio orthographic camera',cd);studio.objects.link(cam);S.camera=cam
hero=(2.19,-4.11,2.59);target=(0,-.011,.445)
cd.type='ORTHO';cd.ortho_scale=1.94;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=220;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=58
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_percentage=100;S.render.resolution_x=S.render.resolution_y=512
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.1
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,pans,serve):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(slug+'.glb')),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,
                         export_lights=False,export_extras=False)
def still(to,pos,tgt,scale,wh):
    cam.location=pos;look(cam,tgt);cd.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:still(out/'previews/studio.webp',hero,target,1.94,(512,512))
if a.review:
    S.cycles.samples=100
    still(a.review/'twin-pan-cavities.webp',(-1.32,-2.40,3.25),(-.237,-.094,.614),.85,(680,640))
    still(a.review/'open-lid-underside.webp',(2.39,-1.91,1.50),(.039,.20,.749),.481,(645,600))
    still(a.review/'folded-sample-wire-rack.webp',(1.30,-2.27,2.26),(.407,-.068,.641),.496,(660,615))
