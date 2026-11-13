"""Original elderly-walker pilot: editable rigid articulation, not a skin or IK rig."""
from pathlib import Path
import bpy,math,json
from mathutils import Vector
H=Path(__file__).resolve().parent
ROOT='CharacterRoot'
def mat(n,c,rough=.55):
 m=bpy.data.materials.new(n);m.use_nodes=True;p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=rough;m.diffuse_color=(*c,1);return m
def empty(n,p=(0,0,0),parent=None):
 o=bpy.data.objects.new(n,None);bpy.context.collection.objects.link(o);o.location=p
 if parent:o.parent=parent;o.matrix_parent_inverse=parent.matrix_world.inverted()
 bpy.context.view_layer.update();return o
def bind(o,n,m,parent):
 o.name=n;o.data.materials.append(m);bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=parent;o.matrix_world=world;bpy.context.view_layer.update();return o
def box(n,p,d,m,parent,b=.01):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.dimensions=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if b:q=o.modifiers.new('Soft manufactured edges','BEVEL');q.width=b;q.segments=2;o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
 return bind(o,n,m,parent)
def rod(n,a,b,r,m,parent):
 a,b=Vector(a),Vector(b);v=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=r,depth=v.length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();return bind(o,n,m,parent)
def sphere(n,p,s,m,parent):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=p);o=bpy.context.object;o.scale=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return bind(o,n,m,parent)
def joint(n,p,parent):
 bpy.context.view_layer.update();o=empty(n,p);w=o.matrix_world.copy();o.parent=parent;o.matrix_world=w;bpy.context.view_layer.update();return o
def export(path):
 bpy.ops.object.select_all(action='DESELECT');root=bpy.data.objects[ROOT]
 for o in [root,*root.children_recursive]:o.select_set(True)
 opts=dict(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=True,export_cameras=False,export_lights=False,export_extras=True)
 props=bpy.ops.export_scene.gltf.get_rna_type().properties
 for k,v in {'export_nla_strips':True,'export_force_sampling':True,'export_optimize_animation_size':False,'export_optimize_animation_keep_anim_object':True,'export_animation_mode':'NLA_TRACKS','export_merge_animation':'NLA_TRACK','export_anim_slide_to_zero':True}.items():
  if k in props:
   if props[k].type!='ENUM' or v in props[k].enum_items.keys():opts[k]=v
 bpy.ops.export_scene.gltf(**opts)
def select_clip(clip,frame):
 for o in bpy.data.objects:
  if o.animation_data:
   o.animation_data.action=None
   for t in o.animation_data.nla_tracks:t.mute=t.name!=clip
 bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
if __name__=='__main__':
 for p in ['sources','exports','previews','reports']:(H/p).mkdir(parents=True,exist_ok=True)
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.fps=30;s.frame_start=0;s.frame_end=60
 root=empty(ROOT);root['fictional_original']=True
 navy=mat('Soft navy fabric',(.035,.08,.14));teal=mat('Clothing green',(.15,.31,.20));yellow=mat('Warm yellow fabric',(.78,.53,.08));skin=mat('Original warm skin',(.53,.29,.16));white=mat('Off white',(.82,.86,.83));black=mat('Shoe sole',(.025,.035,.04));steel=mat('Small prop metal',(.35,.42,.46));grey=mat('Silver grey hair',(.38,.40,.38))
 hipZ=.84;kneeZ=.47;ankleZ=.10;legX=.11;soleH=.11;shoeW=.19;shoeD=.29
 torsoZ=1.075;shoulderZ=1.29;headZ=1.47
 pelvis=joint('Pelvis',(0,0,.83),root);torso=joint('Torso',(0,0,torsoZ),pelvis)
 box('ComfortTrousersHip',(0,0,.83),(.35,.25,.21),navy,pelvis,.035)
 box('CardiganTorso',(0,0,1.075),(.43,.28,.38),teal,torso,.045)
 box('CardiganHem',(0,0,.91),(.44,.29,.06),teal,torso,.012)
 box('InnerShirt',(0,-.15,1.10),(.16,.025,.30),white,torso,.006)
 for x in [-.10,.10]:box('CardiganOpening'+str(x),(x,-.15,1.10),(.045,.03,.33),teal,torso,.004)
 for z in [.99,1.08,1.17]:sphere('CardiganButton'+str(z),(.085,-.17,z),(.012,.008,.012),navy,torso)
 box('EditPocket',(-.14,-.15,1.02),(.12,.03,.10),teal,torso,.006)
 rod('Neck',(0,0,1.25),(0,0,1.36),.055,skin,torso)
 head=joint('HeadJoint',(0,0,1.37),torso);sphere('Head',(0,0,headZ),(.135,.12,.15),skin,head)
 sphere('SilverHairCrown',(0,.025,1.59),(.13,.11,.052),grey,head)
 for sign in [-1,1]:
  sphere('SideHair'+str(sign),(sign*.115,.025,1.50),(.030,.09,.095),grey,head)
  rod('Brow'+str(sign),(sign*.065,-.11,1.535),(sign*.025,-.12,1.54),.006,grey,head)
 grip=Vector((.38,-.15,.82));elbow=Vector((.30,-.025,1.06));leftelbow=Vector((-.29,0,1.04));leftgrip=Vector((-.29,-.025,.83))
 width=.43;armR=.065;handR=.060;faceEye=1.495;noseZ=1.45;smileZ=1.408
 for sign in [-1,1]:
  sphere('EyeWhite_'+str(sign),(sign*.047,-(.137 if headZ<1.3 else .113),faceEye),(.026,.012,.023),white,head)
  sphere('EyePupil_'+str(sign),(sign*.047,-(.148 if headZ<1.3 else .124),faceEye),(.010,.006,.012),black,head)
 sphere('Nose',(0,-(.145 if headZ<1.3 else .125),noseZ),(.021,.025,.024),skin,head)
 rod('SmileLeft',(-.034,-(.133 if headZ<1.3 else .112),smileZ),(0,-(.145 if headZ<1.3 else .124),smileZ-.007),.0045,black,head)
 rod('SmileRight',(0,-(.145 if headZ<1.3 else .124),smileZ-.007),(.034,-(.133 if headZ<1.3 else .112),smileZ),.0045,black,head)
 legs=[];joints=[root,pelvis,torso,head]
 for side,x in [('Left',-legX),('Right',legX)]:
  hip=joint(side+'Hip',(x,0,hipZ),pelvis);knee=joint(side+'Knee',(x,0,kneeZ),hip);foot=joint(side+'Foot',(x,0,ankleZ),knee)
  rod(side+'UpperLeg',(x,0,hipZ-.02),(x,0,kneeZ),.075 if hipZ>.7 else .060,navy,hip)
  sphere(side+'KneeCap',(x,0,kneeZ),(.072,.075,.070) if hipZ>.7 else (.055,.058,.058),navy if hipZ>.7 else skin,knee)
  rod(side+'LowerLeg',(x,0,kneeZ),(x,0,ankleZ+.04),.066 if hipZ>.7 else .046,navy if hipZ>.7 else skin,knee)
  box(side+'Boot',(x,-.04,soleH/2),(shoeW,shoeD,soleH),white,foot,0)
  box(side+'ComfortUpper',(x,.01,ankleZ+.03),(shoeW*.86,shoeD*.60,soleH),teal,foot,.012)
  box(side+'ShoeVelcro',(x,-.025,ankleZ+.075),(shoeW*.84,.035,.016),white,foot,.003)
  legs.append(foot);joints += [hip,knee,foot]
 left=joint('LeftShoulder',(-width*.56,0,shoulderZ),torso);le=joint('LeftElbow',leftelbow,left);lh=joint('LeftHand',leftgrip,le)
 rod('LeftSleeve',(-width*.56,0,shoulderZ),leftelbow,armR,teal if hipZ>.7 else yellow,left);rod('LeftForearm',leftelbow,leftgrip,armR*.75,teal if hipZ>.7 else yellow,le);sphere('LeftGlove',leftgrip,(handR,handR*.9,handR*1.15),skin,lh)
 right=joint('RightShoulder',(width*.56,0,shoulderZ),torso);re=joint('RightElbow',elbow,right);rh=joint('RightHand',grip,re)
 rod('RightSleeve',(width*.56,0,shoulderZ),elbow,armR,teal if hipZ>.7 else yellow,right);rod('RightForearm',elbow,grip,armR*.75,teal if hipZ>.7 else yellow,re);sphere('RightGlove',grip,(handR,handR*.9,handR*1.15),skin,rh)
 handmark=joint('HandGrip',grip,rh);tool=joint('OccupationTool',grip,rh);toolmark=joint('ToolGrip',grip,tool)
 box('ToolGripGeometry',grip,(.035,.040,.075),navy,tool,.003)
 box('PocketBook',grip+Vector((.015,-.025,-.07)),(.12,.05,.18),teal,tool,.006)
 box('BookPages',grip+Vector((.015,-.055,-.07)),(.10,.012,.15),white,tool,.002)
 joints += [left,le,lh,right,re,rh,tool]
 rest={o.name:(o.location.copy(),o.rotation_euler.copy()) for o in joints}
 for o in joints:o.animation_data_create()
 for clip in ['Idle','WalkInPlace']:
  for o in joints:
   for t in o.animation_data.nla_tracks:t.mute=True
   act=bpy.data.actions.new(clip+'_'+o.name);o.animation_data.action=act
   for frame in range(0,61):
    o.location=rest[o.name][0];o.rotation_euler=rest[o.name][1];phase=2*math.pi*frame/60
    if clip=='Idle':
     if o==head:o.rotation_euler.z=.07*math.sin(phase)
     if o==left:o.rotation_euler.x=.04*math.sin(phase)
    else:
     t=frame/30
     # A stance foot is fixed for a full half-cycle. The other foot swings and returns.
     for side in ['Left','Right']:
      swing=(side=='Right' and t<=1) or (side=='Left' and t>=1)
      u=t if side=='Right' else t-1
      if swing and 0<=u<=1:
       lift=0.07*math.sin(math.pi*u)**2
       foreaft=-0.07*math.sin(2*math.pi*u)
       distance=math.hypot(0.74-lift,foreaft)
       bend=math.acos(min(1,max(-1,distance/0.74)))
       hip=math.atan2(foreaft,0.74-lift)-bend;knee=2*bend;ankle=-(hip+knee)
       if o.name==side+'Hip':o.rotation_euler.x=hip
       if o.name==side+'Knee':o.rotation_euler.x=knee
       if o.name==side+'Foot':o.rotation_euler.x=ankle
     if o==left:o.rotation_euler.x=.12*math.sin(phase)
     if o==right:o.rotation_euler.x=-.10*math.sin(phase)
     if o==head:o.rotation_euler.z=.025*math.sin(phase)
    o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='rotation_euler',frame=frame)
   for fc in act.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'
   o.animation_data.action=None;t=o.animation_data.nla_tracks.new();t.name=clip;t.strips.new(clip,0,act)
 select_clip('Idle',0)
 export(H/'exports/elderly-walker.glb')
 world=bpy.data.worlds.new('StudioWorld');s.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.19,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5
 target=(.10,-.06,0.83)
 for n,loc,e in [('Key',(-3,-4,5),500),('Fill',(3,-2,3),350),('Rim',(1,3,4),600)]:
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+n;o.data.energy=e;o.data.size=3;aim(o,target)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=2.25
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
 for name,delta,clip,frame in [('hero',(1.6,-3,1),'Idle',0),('front',(0,-3,.2),'Idle',0),('rear',(1.4,3,.6),'Idle',0),('side',(3,-.2,.3),'Idle',0),('action-a',(1.6,-3,1),'WalkInPlace',15),('action-b',(1.6,-3,1),'WalkInPlace',45),('idle-action',(1.6,-3,1),'Idle',15)]:
  select_clip(clip,frame);s.camera.location=Vector(target)+Vector(delta);aim(s.camera,target);s.render.filepath=str(H/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
 select_clip('Idle',0);bpy.ops.wm.save_as_mainfile(filepath=str(H/'sources/elderly-walker.blend'))
