"""Original Malaysian pasar dacing illustration with an editable native balance clip."""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
parser.add_argument('--review', type=Path)
parser.add_argument('--skip-render', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug = 'pasar-dacing-steelyard-scale'
clip = 'DACING_FIND_BALANCE'
out = args.output.resolve()
for d in ['exports', 'previews']:
    (out/d).mkdir(parents=True, exist_ok=True)
if args.review:
    args.review.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.fps = 30
scene.frame_start, scene.frame_end = 0, 66

def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c

base = collection('01 fixed wooden display and steel fulcrum')
moving = collection('02 authored beam and gravity-aligned hanging loads')
studio = collection('03 studio, not exported')

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

oil = material('Oiled medium meranti tones', '835931', .62)
grain = material('Dark edge-grain tone', '664226', .70)
iron = material('Dark painted green iron stand', '304F46', .46, .24)
blue = material('Patinated charcoal hardware', '293736', .48, .42)
steel = material('Burnished axial pins and cable ferrules', '89928C', .40, .60)
gold = material('Satin old yellow brass', 'C5A05C', .38, .53)
edge = material('Deep brass groove and ferrules', '82603C', .46, .42)
dark = material('Dark incised tick inlay', '45341E', .66)
white = material('Warm unnumbered plaque lettering', 'E3D1A3', .55)
lime = material('Sample green-gold mango skin', 'A7A64F', .52)
green = material('Sample green mango skin', '6F853D', .52)
ochre = material('Sample orange-gold mango skin', 'D4A34D', .55)
ground = material('Studio only matte bone concrete', 'A0A68F', .76)

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

def eye(n,c,p,center,R,r,mat):
    x,y,z=center
    return sweep(n,c,p,[(x+R*math.cos(a*math.tau/16),y,z+R*math.sin(a*math.tau/16)) for a in range(16)],r,mat,closed=True)

def lathe(n,c,p,profile,mat,sides):
    v=[(r*math.cos(i*math.tau/sides),r*math.sin(i*math.tau/sides),z)
       for r,z in profile for i in range(sides)]
    f=[tuple(reversed(range(sides)))]
    for k in range(len(profile)-1):
        for i in range(sides):
            j=(i+1)%sides
            f.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    f.append(tuple(range(len(v)-sides,len(v))))
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

root=empty('ASSET_PasarDacingSteelyardScale',base)
H=.846
PX=-.198
starting=.126
ending=.361
box('Inset plinth shadow line',base,root,(.059,.004,.017),(.937,.414,.034),grain,.015,3)
box('Solid oiled display base',base,root,(.059,.004,.047),(.919,.398,.044),oil,.008,3)
for ox in (-.304,.418):
    for y in (-.140,.148):
        box('Recessed dark support pad',base,root,(ox,y,.003),(.083,.058,.006),blue,.002)
box('Understated plate backing',base,root,(.153,-.197,.049),(.275,.006,.035),blue,.002)
etch('DACING plaque; decorative, not calibrated',base,root,(.153,-.2004,.042),'DACING  /  PASAR',.0165,white)
for x in (.027,.279):
    rod('Plaque pin',base,root,(x,-.2003,.050),(x,-.2021,.050),.0025,gold,8)
box('Bolted rear foot',base,root,(.031,.126,.079),(.171,.104,.029),iron,.006,2)
box('Rear support upright',base,root,(.031,.142,.536),(.048,.044,.921),iron,.006,2)
box('Upper mounting gusset shelf',base,root,(.031,.077,.985),(.063,.185,.036),iron,.006,2)
for x in (-.030,.092):
    rod('Foot anchor hex',base,root,(x,.109,.094),(x,.109,.101),.009,steel,6)
for x in (.010,.055):
    rod('Yoke mount hex fastener',base,root,(x,.000,1.002),(x,.000,1.009),.006,steel,6)
# The fork clears the beam along Y. Its axial pin is the stationary fulcrum.
for y in (-.046,.046):
    box('Clevis side hanger',base,root,(0,y,.907),(.020,.015,.159),iron,.005,2)
    rod('Fulcrum outer bushing',base,root,(0,y-.009,H),(0,y+.009,H),.021,blue,14)
rod('DACING_FIXED_FULCRUM_PIN',base,root,(0,-.061,H),(0,.061,H),.011,steel,16)
for y in (-.063,.063):
    rod('Visible axial pivot pin collar',base,root,(0,y-.003,H),(0,y+.003,H),.016,steel,12)

beam=empty('DACING_BEAM',moving,root,(0,0,H))
box('Long asymmetrical steelyard beam',moving,beam,(.108,0,0),(.665,.050,.031),gold,.004,2)
box('Inlaid front face for illustrative ticks',moving,beam,(.232,-.0257,0),(.378,.0022,.022),edge,.001)
for i in range(23):
    x=.064+i*.0157
    span=.014 if i%5==0 else .0088 if i%2==0 else .0058
    box('Unitless ruled tick',moving,beam,(x,-.0272,.0073-span/2),(.0017,.0007,span),white,0)
# The fitted cheek rides the stationary pin; the load joint is through a separate transverse pin.
rod('Beam fulcrum cheek',moving,beam,(0,-.021,0),(0,.021,0),.023,gold,18)
rod('Short-arm load axle',moving,beam,(PX,-.034,-.007),(PX,.034,-.007),.0068,steel,14)
for y in (-.032,.032):
    rod('Short-arm load axle shoulder',moving,beam,(PX,y-.003,-.007),(PX,y+.003,-.007),.011,gold,12)
box('Outer travel stop',moving,beam,(.438,0,0),(.014,.057,.038),blue,.003)
w=empty('DACING_COUNTERWEIGHT',moving,beam,(starting,0,0))
# Four faces make a real open saddle sleeve, around rather than through the beam.
for z in (-.0208,.0208):
    box('Open sliding collar upper/lower lip',moving,w,(0,0,z),(.038,.070,.006),blue,.002)
for y in (-.0314,.0314):
    box('Open sliding collar side wall',moving,w,(0,y,0),(.038,.006,.038),blue,.002)
box('Bright moving collar witness notch',moving,w,(0,-.035,0),(.002,.001,.014),white,0)
# Hanger starts at the counterweight pivot; inverse rotation keeps it vertical.
poise=empty('DACING_POISE_SWIVEL',moving,w,(0,0,-.031))
rod('Collar lower hanging pivot',moving,w,(0,-.029,-.031),(0,.029,-.031),.0057,steel,12)
eye('Counterweight closed hanger',moving,poise,(0,0,-.009),.009,.0028,steel)
lathe('Dark antique drop counterweight',moving,poise,[(.024,-.122),(.033,-.118),(.038,-.095),(.031,-.071),(.018,-.054),(.011,-.022),(.011,-.015)],blue,16)
for z,r in [(-.112,.033),(-.070,.029)]:
    rod('Slim brass ring on poise',(moving),poise,(0,0,z-.002),(0,0,z+.002),r,gold,16)
# Short side sample assembly follows the beam end while staying upright in world space.
pan=empty('DACING_PAN_SWIVEL',moving,beam,(PX,0,-.007))
for y in (-.026,.026):
    eye('Closed load shackle side eye',moving,pan,(0,y,0),.011,.0032,steel)
    rod('Shackle leg',moving,pan,(0,y,-.011),(0,y,-.045),.0039,steel,10)
rod('Load shackle lower crosspin',moving,pan,(0,-.032,-.045),(0,.032,-.045),.0057,steel,12)
eye('Tripod sling upper eye',moving,pan,(0,0,-.061),.014,.0033,steel)
trayTop=-.297
lathe('Spun brass hanging produce pan',moving,pan,[(.104,-.322),(.120,-.317),(.141,-.305),(.151,-.288),(.157,-.281),(.157,-.275),(.152,-.271),(.147,-.273),(.144,-.283),(.135,-.298),(.115,-.304)],gold,36)
for k in range(3):
    theta=math.radians(30)+math.tau*k/3
    x,y=.146*math.cos(theta),.146*math.sin(theta)
    rod('Rigid-looking fine tension cable',moving,pan,(0,0,-.073),(x,y,-.267),.0027,steel,8)
    rod('Crimped cable lower sleeve',moving,pan,(x*.93,y*.93,-.253),(x,y,-.267),.0043,edge,10)
    rod('Riveted pan strap attachment',moving,pan,(x,y,-.289),(x,y,-.262),.0065,gold,12)
    rod('Pan strap rivet cap',moving,pan,(x,y,-.291),(x,y,-.288),.0085,edge,12)
# Low resolution sculpted fruit meshes, all fixed to the sample group/pan.
load=empty('DACING_SAMPLE_MANGOES',moving,pan,(0,0,-.303))
def mango(n,x,y,heading,size,mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14,ring_count=9,radius=1)
    o=assign(bpy.context.object,n,moving,load,mat)
    for group in o.data.vertices:
        a,b,c=group.co[:]
        group.co=((a*.068*(1-.10*a)*size),
                  (b*.037*(1-.22*a)*size),
                  ((c*.0275*(1-.10*a)+.008*a*a)*size))
    for f in o.data.polygons:
        f.use_smooth=True
    o.location=(x,y,.025*size+.002)
    o.rotation_euler.z=heading
    end=Vector(o.location)+Vector((math.cos(heading)*-.063*size,math.sin(heading)*-.063*size,.004*size))
    rod('Subtle mango stem',moving,load,end,end+Vector((-.006*size,0,.005*size)),.0024,grain,8)
mango('Green-gold sample mango',-.054,-.039,-.43,1.03,lime)
mango('Amber sample mango',.034,-.050,.52,.91,ochre)
mango('Muted green sample mango',.025,.051,.14,.97,green)

def progress(frame):
    t=min(1,max(0,(frame-3)/52))
    return t*t*(3-2*t)

def set_pose(frame):
    t=progress(frame)
    angle=math.radians(-9)*(1-t)
    beam.rotation_quaternion=Quaternion((0,1,0),angle)
    w.location=(starting+(ending-starting)*t,0,0)
    for gravity in (pan,poise):
        gravity.rotation_quaternion=Quaternion((0,1,0),-angle)

animated=((beam,'rotation_quaternion'),(w,'location'),(pan,'rotation_quaternion'),(poise,'rotation_quaternion'))
for f in range(67):
    set_pose(f)
    for o,prop in animated:
        o.keyframe_insert(data_path=prop, frame=f)
for o,prop in animated:
    action=o.animation_data.action
    action.name=o.name+' original balance illustration'
    track=o.animation_data.nla_tracks.new()
    track.name=clip
    track.strips.new('Balance demonstration without assay or measurement',0,action)
    o.animation_data.action=None
scene.frame_set(0)
box('Studio shadow surface',studio,None,(0,0,-.025),(200,200,.048),ground,0)
def look(o,t):
    o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,(0,0,.64))
lamp('Broad warm market-like key',(-1.87,-2.25,2.54),205,2.18,(1,.91,.78))
lamp('Reflective white frontal fill',(1.6,-1.7,1.42),100,1.5,(.86,.96,1))
lamp('Edge and spring brass reflection',(.36,1.42,2.28),193,1.84,(.90,.98,1))
world=bpy.data.worlds.new('Neutral warm daylight')
world.use_nodes=True;scene.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.62,.66,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.46
lens=bpy.data.cameras.new('Asset studio');cam=bpy.data.objects.new('Asset studio',lens);studio.objects.link(cam)
scene.camera=cam;lens.type='ORTHO';lens.ortho_scale=1.31
cam.location=(.80,-3.2,1.43);look(cam,(.064,0,.513))
scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=sys.platform=='darwin'
scene.render.threads_mode='FIXED';scene.render.threads=5
scene.render.resolution_x=scene.render.resolution_y=512
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='WEBP';scene.render.image_settings.quality=92
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.16
scene.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)

def still(to,frame,pos,target,ortho,res):
    scene.frame_set(frame);cam.location=pos;look(cam,target)
    lens.ortho_scale=ortho
    scene.render.resolution_x,scene.render.resolution_y=res
    scene.render.filepath=str(to);bpy.ops.render.render(write_still=True)
if not args.skip_render:
    still(out/'previews/studio.webp',0,(.8,-3.2,1.43),(.064,0,.513),1.31,(512,512))
if args.review:
    for f,title in [(0,'ready'),(31,'transition'),(66,'balanced')]:
        still(args.review/(title+'.webp'),f,(.26,-2.69,1.42),(.073,0,.68),.89,(808,530))
    still(args.review/'fulcrum.webp',52,(-.80,-2.55,1.38),(.055,0,.85),.72,(774,470))
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for c in (base,moving):
    for o in c.objects:
        o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,export_texcoords=False,
                         export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_cameras=False,
                         export_lights=False,export_extras=False)
