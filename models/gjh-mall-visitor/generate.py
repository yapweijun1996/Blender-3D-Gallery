"""Original reference-led visitor. Blender-only deterministic authoring; collection-local writes."""
from pathlib import Path
import math
import bpy
import bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def mat(name,rgb,rough=.65,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True
 def lin(v):
  v=v/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
 color=(*map(lin,rgb),1);m.diffuse_color=color
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 return m
skin=mat('Warm peach skin',(239,179,126));hair=mat('Swept chestnut hair',(65,43,28));dark=mat('Glasses and eyes',(27,29,25),.45);white=mat('Cream white',(239,237,217));mouth=mat('Warm smile',(164,55,35));green=mat('GJH emerald polo',(10,118,75));navy=mat('Navy denim',(32,58,78));cuff=mat('Denim cuff',(87,112,126));sole=mat('Sneaker sole',(203,209,200));watch=dark

def node(name,loc,parent=None):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.location=loc;o.parent=parent;return o
root=node('GJHMallVisitor',(0,0,0));body=node('Body',(0,0,.70),root)
def mesh(name,verts,faces,material,parent):
 d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.parent=parent;d.materials.append(material)
 for p in d.polygons:p.use_smooth=len(p.vertices)<=4
 return o

def ell(name,loc,scale,material,parent,seg=16,rings=10):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=(0,0,0));o=bpy.context.object;o.name=name;o.parent=parent;o.location=loc;o.scale=scale;o.data.materials.append(material)
 for p in o.data.polygons:p.use_smooth=True
 return o

def loft(name,rows,material,parent,n=20):
 # Rows are height, halfwidth, halfdepth, centreY. Closed smooth contour.
 v=[];f=[]
 for z,w,d,y in rows:
  for i in range(n):
   a=2*math.pi*i/n;v.append((w*math.cos(a),y+d*math.sin(a),z))
 for j in range(len(rows)-1):
  for i in range(n):a=j*n+i;b=j*n+(i+1)%n;f.append((a,b,b+n,a+n))
 f.extend([tuple(reversed(range(n))),tuple((len(rows)-1)*n+i for i in range(n))]);return mesh(name,v,f,material,parent)

def path(name,points,radius,material,parent,sides=6):
 v=[];f=[]
 for j,p in enumerate(points):
  p=Vector(p);direction=Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])
  a=direction.normalized().cross(Vector((0,0,1)))
  if a.length<.01:a=Vector((1,0,0))
  a.normalize();b=direction.normalized().cross(a)
  for i in range(sides):v.append(p+radius*(math.cos(i*math.tau/sides)*a+math.sin(i*math.tau/sides)*b))
 for j in range(len(points)-1):
  for i in range(sides):a=j*sides+i;b=j*sides+(i+1)%sides;f.append((a,b,b+sides,a+sides))
 f.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+i for i in range(sides))]);return mesh(name,v,f,material,parent)

# Rounded mascot proportions: broad friendly face, compact polo and short cuffed legs.
loft('Emerald polo',[(0,.19,.105,0),(.025,.205,.112,0),(.18,.20,.115,0),(.30,.17,.09,0),(.335,.085,.065,0)],green,body,20)
path('Polo lower hem',[(-.19,-.04,.012),(-.14,-.097,.012),(0,-.113,.012),(.14,-.097,.012),(.19,-.04,.012)],.004,green,body)
loft('Visible neck',[(.31,.064,.057,0),(.39,.066,.057,0)],skin,body,16)
for side in(-1,1):
 mesh('Cream pointed collar',[(side*.065,-.06,.34),(side*.105,-.075,.31),(side*.063,-.108,.265),(side*.012,-.089,.32)],[(0,1,2,3)],white,body)
path('Polo placket',[(0,-.114,.22),(0,-.10,.30)],.009,green,body)
for z in(.235,.268):ell('Cream polo button',(0,-.12,z),(.004,.002,.004),white,body,8,4)
# Original concept wordmark is converted to geometry, never an external font/image.
font=bpy.data.curves.new('GJH concept embroidery','FONT');font.body='GJH';font.size=.035;font.extrude=.0004;font.align_x='CENTER'
text=bpy.data.objects.new('GJH concept embroidery',font);scene.collection.objects.link(text);text.parent=body;text.location=(.105,-.109,.245);text.rotation_euler=(math.pi/2,0,0);font.materials.append(white)
bpy.context.view_layer.objects.active=text;text.select_set(True);bpy.ops.object.convert(target='MESH');text.select_set(False)
head=node('Head',(0,0,.35),body)
loft('Rounded face',[(0,.055,.065,-.005),(.025,.118,.101,-.007),(.065,.17,.128,0),(.125,.193,.143,.004),(.205,.197,.151,.006),(.27,.18,.145,.008),(.315,.145,.12,.012),(.345,.085,.08,.013),(.36,.015,.025,.013)],skin,head,24)
for side in(-1,1):
 ell('Rounded ear',(side*.194,.003,.15),(.036,.025,.05),skin,head,12,8)
 # Large black eyes remain clearly visible through open geometric lens rims.
 ell('Expressive black eye',(side*.080,-.143,.192),(.027,.015,.040),dark,head,16,10)
 ell('Eye highlight',(side*.073,-.157,.207),(.008,.002,.010),white,head,10,6)
 ell('Eye small highlight',(side*.088,-.157,.181),(.0035,.001,.0045),white,head,8,4)
 rim=[]
 for i in range(49):
  a=i*math.tau/48;rim.append((side*.081+.067*math.cos(a),-.16+.012*abs(math.cos(a)),.19+.069*math.sin(a)))
 path('Thin open round glasses',rim,.0045,dark,head,6)
 path('Glasses temple',[(side*.148,-.149,.20),(side*.188,-.085,.208),(side*.198,.015,.20)],.0045,dark,head,6)
 path('Friendly curved eyebrow',[(side*.035,-.133,.275),(side*.070,-.145,.286),(side*.105,-.138,.282),(side*.124,-.126,.272)],.009,hair,head,6)
path('Glasses bridge',[(-.014,-.16,.204),(0,-.169,.211),(.014,-.16,.204)],.0045,dark,head,6)
ell('Soft projecting nose',(0,-.146,.143),(.020,.024,.025),skin,head,12,8)
# Open smile, curved lower edge and small tongue; mouth geometry follows face surface.
ell('Happy smile opening',(0,-.126,.085),(.049,.009,.024),dark,head,16,8)
ell('Smile tongue',(0,-.134,.075),(.029,.003,.010),mouth,head,12,6)
path('Smile upper curve',[(-.043,-.132,.096),(0,-.137,.093),(.043,-.132,.096)],.004,skin,head,6)
# Hair extends over back of skull; asymmetrical broad locks sweep to one side.
loft('Rounded back hair',[(.16,.18,.12,.045),(.23,.205,.15,.035),(.30,.195,.16,.025),(.36,.16,.13,.02),(.40,.09,.085,.015),(.416,.008,.012,.005)],hair,head,24)
for name,loc,scale,rot in [
 ('Swept fringe left',(-.11,-.102,.315),(.128,.073,.062),-.35),
 ('Swept fringe centre',(-.045,-.106,.35),(.137,.070,.064),-.30),
 ('Parted right lock',(.12,-.095,.318),(.075,.067,.081),.35),
 ('Top lifted sweep',(-.015,-.015,.405),(.16,.075,.060),-.16),
 ('Back crown',(0,.085,.35),(.17,.085,.075),0)]:
 o=ell(name,loc,scale,hair,head,20,10);o.rotation_euler.y=rot
# Articulated limbs: short polo sleeves, bare forearms, navy denim and white sneakers.
limbs={}
for side,label in[(-1,'Left'),(1,'Right')]:
 arm=node(label+'Shoulder',(side*.173,0,.27),body);arm.rotation_euler.y=-side*.18
 loft(label+'Polo sleeve',[(.065,.015,.016,0),(.05,.045,.047,0),(.02,.062,.064,0),(-.035,.067,.067,0),(-.105,.061,.061,0)],green,arm,16)
 loft(label+'Cream sleeve edging',[(-.095,.062,.062,0),(-.116,.058,.059,0)],white,arm,16)
 loft(label+'Upper arm',[(-.108,.048,.047,0),(-.21,.044,.044,0)],skin,arm,12)
 elbow=node(label+'Elbow',(0,0,-.20),arm)
 ell(label+'Elbow contour',(0,0,0),(.044,.044,.045),skin,elbow,12,8)
 loft(label+'Forearm',[(0,.044,.044,0),(-.13,.038,.038,0)],skin,elbow,12)
 ell(label+'Rounded hand',(0,-.005,-.16),(.043,.035,.060),skin,elbow,12,8)
 ell(label+'Thumb',(-side*.033,-.025,-.143),(.017,.021,.031),skin,elbow,10,6)
 if label=='Right':
  loft('Dark wristwatch band',[(-.098,.041,.042,0),(-.126,.04,.041,0)],dark,elbow,12)
  ell('Watch face',(0,-.043,-.111),(.027,.010,.024),dark,elbow,12,6)
 hip=node(label+'Hip',(side*.097,0,-.015),body)
 loft(label+'Denim thigh',[(.02,.087,.094,0),(-.12,.083,.087,0),(-.24,.072,.075,0)],navy,hip,16)
 knee=node(label+'Knee',(0,0,-.23),hip)
 ell(label+'Denim knee',(0,0,0),(.072,.075,.055),navy,knee,12,8)
 loft(label+'Straight tapered jeans',[(0,.072,.075,0),(-.15,.067,.07,0),(-.25,.063,.066,0)],navy,knee,16)
 loft(label+'Turned denim cuff',[(-.215,.067,.07,0),(-.282,.067,.07,0)],cuff,knee,16)
 foot=node(label+'Foot',(0,-.022,-.306),knee)
 ell(label+'White sneaker sole',(0,-.026,-.024),(.078,.125,.027),white,foot,16,8)
 ell(label+'White sneaker upper',(0,-.025,.008),(.074,.119,.046),white,foot,16,8)
 ell(label+'Sneaker tongue',(0,-.008,.042),(.041,.057,.022),white,foot,12,6)
 for j in range(3):path(label+'Sneaker lace',[(-.041,-.017-j*.019,.056),(.041,-.017-j*.019,.056)],.003,white,foot,5)
 limbs[label]=(arm,elbow,hip,knee,foot)
# Merge authored pieces by articulation node, sharing material slots and reducing draws.
for parent in [body,head]+[j for joints in limbs.values() for j in joints]:
 parts=[o for o in list(scene.objects) if o.parent==parent and o.type=='MESH']
 if not parts:continue
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();parts[0].name=parent.name+' geometry'
# Closed limb lofts use both upward and downward ring orders; normalize winding.
for o in scene.objects:
 if o.type=='MESH':
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
# Normalize measured rest geometry to exactly 1.72m with a floor-centred root.
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(c) for o in scene.objects if o.type=='MESH' for c in o.bound_box]
low=min(p.z for p in points);high=max(p.z for p in points);factor=1.72/(high-low)
body.location.z-=low;root.scale=(factor,factor,factor)
# Smooth in-place cycles using independent node actions grouped by clip-named NLA tracks.
animated=[body]+[joint for joints in limbs.values() for joint in joints]
base={o.name:(o.location.copy(),o.rotation_euler.copy()) for o in animated}
for o in animated:o.animation_data_clear();o.animation_data_create()
for clip,frames,speed in [('idle',240,0),('walk',120,1),('sprint',88,2)]:
 for o in animated:
  for track in o.animation_data.nla_tracks:track.mute=True
  action=bpy.data.actions.new(clip+'_'+o.name);o.animation_data.action=action
  first_pose=None
  for frame in range(1,frames+2,2):
   phase=(frame-1)/frames*math.tau;o.location=base[o.name][0];o.rotation_euler=base[o.name][1]
   if o==body:
    o.location.z+=.003*math.sin(phase) if speed==0 else .012*speed*(1-math.cos(phase*2))
    o.rotation_euler.x=.035*speed
   for label,joints in limbs.items():
    sign=1 if label=='Left' else -1;swing=math.sin(phase)*sign
    if o==joints[0]:o.rotation_euler.x=.035*math.sin(phase) if speed==0 else swing*(.38 if speed==1 else .7)
    if o==joints[1]:o.rotation_euler.x=-.10 if speed==0 else -.22-.25*speed-max(0,swing)*.3
    if o==joints[2]:o.rotation_euler.x=0 if speed==0 else -swing*(.40 if speed==1 else .8)
    if o==joints[3]:o.rotation_euler.x=0 if speed==0 else max(0,-swing)*(.7 if speed==1 else 1.25)
    if o==joints[4]:o.rotation_euler.x=0 if speed==0 else -.12*max(0,swing)
   if first_pose is None:first_pose=(o.location.copy(),o.rotation_euler.copy())
   o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='rotation_euler',frame=frame)
  # Explicit loop end matches the first pose.
  o.location,o.rotation_euler=first_pose
  for data in ('location','rotation_euler'):o.keyframe_insert(data_path=data,frame=frames+1)
  o.animation_data.action=None;t=o.animation_data.nla_tracks.new();t.name=clip;t.strips.new(clip,1,action)
 for o in animated:
  o.location=base[o.name][0];o.rotation_euler=base[o.name][1]
# Bake foot contact at 120 Hz from real posed sneaker vertices.
# Dense contact sampling prevents subframe foot-switch interpolation from floating.
# This keeps at least one sole on the ground throughout each in-place cycle.
feet=[o for o in scene.objects if o.type=='MESH' and o.parent and o.parent.name.endswith('Foot')]
for clip,frames in [('idle',240),('walk',120),('sprint',88)]:
 for o in animated:
  for track in o.animation_data.nla_tracks:track.mute=track.name!=clip
 track=next(t for t in body.animation_data.nla_tracks if t.name==clip)
 action=track.strips[0].action
 track.mute=True;body.animation_data.action=action
 for frame in range(1,frames+2):
  scene.frame_set(frame);bpy.context.view_layer.update()
  floor=min((o.matrix_world@v.co).z for o in feet for v in o.data.vertices)
  body.location.z-=floor/root.scale.z
  body.keyframe_insert(data_path='location',index=2,frame=frame)
 body.animation_data.action=None;track.mute=False
# Sources retain the fully editable hierarchy. Only the visitor exports, studio stays source-only.
for o in animated:
 for t in o.animation_data.nla_tracks:t.mute=t.name!='idle'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:o.select_set(True)
scene.render.fps=120
bpy.ops.export_scene.gltf(filepath=str(ROOT/'exports/gjh-mall-visitor.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_merge_animation='NLA_TRACK',export_force_sampling=True,export_optimize_animation_keep_anim_object=True,export_apply=True,export_cameras=False,export_lights=False)
# Studio lighting with front/side/back and gait evidence.
world=bpy.data.worlds.new('Visitor studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.4,.4,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;scene.world=world
floor=mat('Studio floor',(207,211,205),1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.008));bpy.context.object.data.materials.append(floor)
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for loc,power,size in [((3,-4,5),450,4),((-3,-2,3),300,3),((2,3,4),500,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;aim(o,(0,0,.9))
bpy.ops.object.camera_add(location=(2,-4,2));scene.camera=bpy.context.object;scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=2.04
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=600;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'sources/gjh-mall-visitor.blend'),compress=True)
for view,loc,clip,frame in [('front',(0,-4,1.05),'idle',1),('side',(4,0,1.05),'idle',1),('back',(0,4,1.05),'idle',1),('walk',(2,-4,1.4),'walk',29),('sprint',(2,-4,1.4),'sprint',21),('portrait',(.3,-4,1.5),'idle',1)]:
 for o in animated:
  for t in o.animation_data.nla_tracks:t.mute=t.name!=clip
 scene.frame_set(frame);scene.camera.location=loc;aim(scene.camera,(0,0,1.35) if view=='portrait' else (0,0,.85));scene.camera.data.ortho_scale=.80 if view=='portrait' else 2.04
 scene.render.filepath=str(ROOT/'previews'/f'{view}.png');bpy.ops.render.render(write_still=True)
