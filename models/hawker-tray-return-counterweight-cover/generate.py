"""Original hawker tray-return cover cutaway with single fictional motion."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector, Quaternion
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='hawker-tray-return-counterweight-cover'
out=a.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
S.render.fps=30
S.frame_start,S.frame_end=0,66
base=collection('01 independent steel cabinet and fixed sample tray')
guide=collection('02 front cover, fixed rails and rounded frame')
drive=collection('03 exposed counterweight and constant-length transmission')
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


steel=material('Fine satin stainless steel', 'A1AEA8', .38, .63)
silver=material('Brighter rounded lips', 'C6CEC2', .32, .52)
dark=material('Recessed charcoal-blue steel', '344449', .47, .45)
teal=material('Deep blue-green powder coat', '286664', .47, .20)
edg=material('Light blue-green gallery trims', '538782', .37, .24)
cream=material('Cream silkscreen', 'F2E7CF', .63)
clay=material('Terra-cotta sample tray', 'B56044', .55)
claylit=material('Sample tray rounded rim', 'CB8160', .52)
gold=material('Ochre cutaway counterweight', 'BF9143', .40, .34)
goldlit=material('Ochre moving grip end caps', 'DCAC59', .34, .31)
rubber=material('Dark rubber rail insert', '283437', .73)
cord=material('Pale woven steel cable', 'C6C2A9', .42, .36)
ground=material('Warm pale neutral studio only', 'C8C8B7', .84)

root=empty('HAWKER_TRAY_RETURN_FIXTURE',base)
r=empty('FIXED_CABINET',base,root)
frame=empty('FIXED_COVER_FRAME',guide,root)
dr=empty('FIXED_EXHIBIT_DRIVE',drive,root)
# Low open-backed base and floor shelf. Fasteners/rendered detail are local geometry.
for x in (-.48,.48):
    for y in (-.24,.18):
        box('Square foot post',base,r,(x,y,.367),(.060,.060,.717),steel,.006,2)
        box('Rubber contact foot',base,r,(x,y,.020),(.083,.076,.036),rubber,.005,2)
for z in (.20,.699):
    box('Rounded stainless lower and upper shelf',base,r,(0,-.018,z),(1.094,.515,.044),steel,.011,3)
    box('Shelf front half-round edging',base,r,(0,-.279,z+.001),(1.073,.030,.039),silver,.012,3)
    box('Shallow rear shelf upstand',base,r,(0,.222,z+.052),(1.051,.025,.086),steel,.010,2)
box('Full receiving deck',base,r,(0,-.033,.865),(1.117,.639,.086),steel,.024,3)
box('Layered dark counter fascia',base,r,(0,-.343,.857),(1.058,.034,.044),dark,.009,2)
box('Recessed removable-looking rear insert',base,r,(-.016,.237,1.118),(1.007,.041,.444),dark,.012,2)
for y in (-.178,.056):
    box('Per-tube lower leg joining rail',base,r,(0,y,.097),(1.014,.035,.048),dark,.007,2)
for x in (-.53,.53):
    for z in (.73,.82):
        rod('Corner shelf screw',base,r,(x,-.352,z),(x,-.359,z),.006,steel,12)
# Standalone removable-looking sample tray, genuinely open and empty.
tray=empty('FIXED_ILLUSTRATIVE_SAMPLE_TRAY',base,r,(.016,-.049,.9115))
box('Sample tray inner floor',base,tray,(0,0,.005),(.489,.263,.017),clay,.012,3)
for x in (-.252,.252):
    box('Sample tray side with open center',base,tray,(x,0,.028),(.027,.276,.050),claylit,.013,3)
for y in (-.133,.133):
    box('Sample tray rim',base,tray,(0,y,.028),(.485,.027,.050),claylit,.013,3)
etch('Example labeling on sample tray front',base,tray,(0,-.147,.021),'SAMPLE',.015,cream)
# In this section display both actual front rails, while simplifying rear framing.
for x in (-.509,.509):
    box('Structural vertical front post',guide,frame,(x,-.212,1.252),(.059,.124,.730),teal,.008,2)
    sign=1 if x<0 else -1
    xface=x+sign*.038
    # Two independent lips with an actual open U slot between them; radius only on exposed edges.
    for yy in (-.245,-.185):
        box('Radiused inside guide lip',guide,frame,(xface,yy,1.2645),(.030,.017,.677),silver,.004,2)
    box('Recessed guide web between lips',guide,frame,(x+sign*.021,-.215,1.2645),(.014,.065,.677),steel,.003,2)
    for zz in (.982,1.514):
        rod('Guide insert bolt',guide,frame,(xface,-.255,zz),(xface,-.261,zz),.0054,dark,9)
box('High header separates top mechanisms from panel',guide,frame,(0,-.192,1.672),(1.064,.152,.135),teal,.012,3)
box('Header facing plate',guide,frame,(0,-.273,1.674),(1.009,.026,.090),edg,.009,2)
etch('Original neutral section lettering',guide,frame,(-.02,-.287,1.656),'TRAY RETURN',.047,cream)
for x in (-.471,.440):
    rod('Header stainless rivet',guide,frame,(x,-.287,1.673),(x,-.293,1.673),.0066,steel,12)
for x in (-.505,.505):
    box('Portal back brace',guide,frame,(x,.167,1.223),(.040,.041,.650),teal,.006,2)
box('Upper connector behind portal',guide,frame,(0,.167,1.506),(1.055,.043,.053),teal,.010,2)
box('Staged tray stop at rear',guide,frame,(0,.194,.956),(1.039,.041,.105),steel,.009,2)
# Front moving solid cover, stepped face, flanged edges and real guide shoes.
C=empty('TRAY_RETURN_COVER',guide,root,(0,0,.941))
box('Solid stainless slide cover',guide,C,(0,-.215,.169),(.925,.027,.338),steel,.010,3)
box('Satin center cover field inset',guide,C,(0,-.231,.170),(.872,.010,.286),silver,.015,3)
for z in (.016,.322):
    box('Cover rigid leading and top edges',guide,C,(0,-.218,z),(.940,.031,.025),steel,.006,2)
for x in (-.470,.470):
    for z in (.033,.302):
        box('Dark captured moving guide shoe',guide,C,(x,-.215,z),(.019,.037,.044),rubber,.003,2)
for z in (.045,.278):
    box('Shallow cover stiffening crease shadow',guide,C,(0,-.239,z),(.790,.006,.006),dark,.002,2)
# Raised pull bar; not a display button. Independent parts and lip shadow.
for x in (-.144,.144):
    box('Handle bridge from steel face',guide,C,(x,-.255,.104),(.024,.047,.022),dark,.005,2)
rod('Dull ochre finger rail',guide,C,(-.155,-.279,.104),(.155,-.279,.104),.0125,gold,20)
for x in (-.156,.156):
    rod('Rounded ochre handrail end',guide,C,(x-.009,-.279,.104),(x+.009,-.279,.104),.0138,goldlit,16)

# Front y=-.269 and rear y=-.159 are the two physical tangent positions.
# Exposed line is a fixed top half-turn plus straight spans from fixed tangencies
# to the moving brackets. Never detach or alter total centerline length.
x,y,z,R=.623,-.214,1.704,.055
yA,yB=y-R,y+R
travel=.335
portal_y=-.019
box('Corner mechanism side return bracket',drive,dr,(.592,portal_y,1.342),(.195,.050,.763),teal,.011,3)
box('Rear mechanism fold only, deliberately sectioned front side',drive,dr,(.708,-.130,1.317),(.030,.244,.688),edg,.009,2)
box('Low support pad attached to guide rods',drive,dr,(.612,-.155,.937),(.166,.207,.035),teal,.008,2)
box('Upper support pad outboard of pulley arc',drive,dr,(.711,-.155,1.750),(.076,.207,.035),teal,.008,2)
box('Upper side return physically joins frame and pad',drive,dr,(.708,-.103,1.702),(.038,.041,.115),edg,.006,2)
for xx in (.574,.672):
    rod('Exposed round counterweight guide rod',drive,dr,(xx,yB,.925),(xx,yB,1.650),.0062,silver,14)
    for zz in (.925,1.650):
        rod('Guide rod captive collar',drive,dr,(xx,yB,zz-.014),(xx,yB,zz+.013),.0103,dark,14)
W=empty('TRAY_RETURN_COUNTERWEIGHT',drive,root,(x,yB,1.407))
box('Dark chamfered counterweight core',drive,W,(0,0,0),(.082,.064,.128),dark,.011,3)
box('Ochre exposed front face of moving counterweight',drive,W,(0,-.034,0),(.074,.013,.119),gold,.008,2)
for px in (-.049,.049):
    # Slotted follower surrounds guide by two flanges with separate topology.
    for py in (-.011,.011):
        box('Counterweight captive guide lips',drive,W,(px,py,0),(.026,.009,.091),gold,.002,2)
    box('Counterweight shoe back tie',drive,W,(px+(1 if px>0 else -1)*.012,0,0),(.008,.031,.085),dark,.002,2)
box('Counterweight fixed-length link',drive,W,(0,0,.077),(.021,.024,.033),silver,.003,2)
rod('Rear cable ferrule pins counterweight eye',drive,W,(0,0,.089),(0,0,.099),.008,goldlit,14)
box('Cover side returned link in front of stationary guide',drive,C,(.535,-.287,.286),(.198,.016,.027),dark,.004,2)
box('Cover link bridge anchored within moving fascia',drive,C,(.441,-.253,.286),(.021,.079,.023),steel,.004,2)
box('Rotating-free end joint connects returned link to bracket',drive,C,(x,-.279,.291),(.025,.035,.028),steel,.004,2)
box('Cover front cable collar block',drive,C,(x,yA,.326),(.034,.023,.023),silver,.003,2)
box('Cover formed riser connects line to guide shoe',drive,C,(x,yA,.301),(.028,.023,.049),steel,.004,2)
rod('Front cable ferrule pins cover eye',drive,C,(x,yA,.328),(x,yA,.344),.008,goldlit,14)
# Grooved pulley: real concentric annular section, central bore and axial steel pin.
P=empty('TRAY_RETURN_TOP_PULLEY',drive,root,(x,y,z))
profile=[(-.034,.018),(-.034,.071),(-.027,.076),(-.017,.076),(-.015,.061),(-.008,.052),(0,.050),(.008,.052),(.015,.061),(.017,.076),(.027,.076),(.034,.071),(.034,.018)]
n=40
vv=[(px,r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n)) for px,r in profile for i in range(n)]
ff=[(j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i) for j in range(len(profile)) for i in range(n)]
wheel=mesh('Flanged pulley with physical groove and center bore',drive,P,vv,ff,dark)
wheel.data.materials.append(silver);wheel.data.materials.append(steel)
for i,f in enumerate(wheel.data.polygons):
    layer=i//n; f.material_index=1 if layer in (1,2,9,10) else (2 if layer in (0,11,12) else 0)
    f.use_smooth=layer not in (0,11)
rod('Static through axle in cutaway',drive,dr,(.555,y,z),(.692,y,z),.018,steel,20)
for xx in (.559,.689):
    rod('Static axle retention washer',drive,dr,(xx-.006,y,z),(xx+.006,y,z),.028,steel,20)
rod('Ochre moving pulley witness on near flange',drive,P,(.034,.035,.032),(.040,.035,.032),.0105,goldlit,14)
rod('Rear cover frame tie pin',drive,dr,(.670,y+.092,z),(.706,y+.092,z),.017,silver,16)
rod('Exposed pulley shaft supporting cheek',drive,dr,(.679,y,z),(.679,y+.092,z),.024,edg,11)
# Visible cable actually follows the pulley groove. The two straight spans
# stay pinned to the tangent high endpoints; only their axial lengths vary.
rr=.0045
arc=[(x,y+R*math.cos(math.pi-i*math.pi/48),z+R*math.sin(math.pi-i*math.pi/48)) for i in range(49)]
sweep('FIXED_CONTIGUOUS_TANGENT_HALF_TURN',drive,dr,arc,rr,cord,10)
A=empty('TRAY_RETURN_COVER_CABLE',drive,root,(x,yA,z))
B=empty('TRAY_RETURN_WEIGHT_CABLE',drive,root,(x,yB,z))
AL=z-(.941+.344)
BL=z-(1.407+.099)
rod('Parallel straight cable to cover',drive,A,(0,0,0),(0,0,-1),rr,cord,10)
rod('Parallel straight cable to counterweight',drive,B,(0,0,0),(0,0,-1),rr,cord,10)
box('Side inspection base tag block',drive,dr,(.619,-.270,.875),(.152,.055,.071),dark,.010,2)
etch('Side inspection original cutaway tag',drive,dr,(.620,-.299,.869),'CUTAWAY',.018,cream)
box('Studio floor only',studio,None,(0,0,-.026),(200,200,.051),ground,0)
# Held calm endpoints and monotonic open eased progress, sampled on every frame.
clip='TRAY_RETURN_COVER_LIFT'
channels=((C,'location'),(W,'location'),(P,'rotation_quaternion'),(A,'scale'),(B,'scale'))
def pose(f):
    t=max(0,min(1,(f-4)/52)); d=travel*t*t*(3-2*t)
    C.location.z=.941+d
    W.location.z=1.407-d
    # At the front tangent (y=-R), negative X rotation moves top line upward.
    P.rotation_quaternion=Quaternion((1,0,0),-d/R)
    A.scale.z=AL-d
    B.scale.z=BL+d
for f in range(67):
    pose(f)
    for obj,prop in channels:obj.keyframe_insert(data_path=prop,frame=f)
for obj,prop in channels:
    act=obj.animation_data.action
    act.name=obj.name+' captured synchronized illustrative motion'
    fs=act.layers[0].strips[0].channelbag(obj.animation_data.action_slot).fcurves if hasattr(act,'layers') else act.fcurves
    for curve in fs:
        for sample in curve.keyframe_points:sample.interpolation='LINEAR'
    tr=obj.animation_data.nla_tracks.new()
    tr.name=clip
    tr.strips.new('Local illustration, no real operation',0,act)
    obj.animation_data.action=None
S.frame_set(0)
def look(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,at,power,size,col,tgt=(0,-.09,.95)):
    d=bpy.data.lights.new(n,'AREA');d.energy=power;d.size=size;d.shape='DISK';d.color=col
    o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=at;look(o,tgt)
lamp('Warm broad stainless key',(-3.2,-3.25,3.68),460,3.55,(1,.91,.79))
lamp('Cool fill for narrow guides',(3.0,-2.0,2.7),375,2.65,(.79,.92,1))
lamp('Upper edge sheen',(1.23,1.45,3.17),280,2.20,(1,.90,.76))
world=bpy.data.worlds.new('Soft gallery studio');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.53,.58,.59,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.48
ls=bpy.data.cameras.new('Editorial orthographic');cam=bpy.data.objects.new('Editorial orthographic',ls);studio.objects.link(cam);S.camera=cam
ls.type='ORTHO';ls.ortho_scale=2.12;cam.location=(2.42,-4.85,2.84);look(cam,(.075,-.028,.886))
S.render.engine='CYCLES';S.cycles.samples=224;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=72
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=93
S.view_settings.view_transform='AgX';S.view_settings.exposure=.12
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for coll in (base,guide,drive):
    for ob in coll.objects:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(slug+'.glb')),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=True,export_animation_mode='NLA_TRACKS',
                         export_force_sampling=True,export_cameras=False,export_lights=False,export_extras=False)
def still(to,f,pos,tgt,scale,wh):
    S.frame_set(f);cam.location=pos;look(cam,tgt);ls.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
hero=(2.42,-4.85,2.84);target=(.075,-.028,.886)
if not a.skip_render:still(out/'previews/studio.webp',0,hero,target,2.12,(512,512))
if a.review:
    S.cycles.samples=48
    for name,f in [('closed',0),('mid',30),('open',66)]:still(a.review/(name+'.webp'),f,hero,target,2.16,(773,773))
    still(a.review/'side-transmission.webp',30,(4.8,-2.40,2.20),(.591,-.212,1.375),1.04,(660,800))
    still(a.review/'side-tangent.webp',41,(4.1,-.86,2.06),(.638,-.218,1.666),.230,(720,680))
