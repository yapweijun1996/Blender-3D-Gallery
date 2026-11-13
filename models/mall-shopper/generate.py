"""Original mall-shopper pilot: editable rigid articulation, not a skin or IK rig."""
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
 for p in ['sources','exports','previews','reports']: (H/p).mkdir(parents=True,exist_ok=True)
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.fps=30;s.frame_start=0;s.frame_end=60
 root=empty(ROOT);bpy.context.view_layer.update()
 navy=mat('Workwear navy',(.025,.055,.085));teal=mat('Occupation uniform',(.15,.32,.55));yellow=mat('Reflective lime',(.75,.82,.12));skin=mat('Warm skin',(.53,.29,.16));white=mat('Off white',(.82,.86,.83));black=mat('Boot rubber',(.018,.024,.03));steel=mat('Broom aluminium',(.35,.42,.46),.32);glove=mat('Protective gloves',(.78,.68,.18));bristle=mat('Broom bristles',(.13,.07,.18))
 pelvis=joint('Pelvis',(0,0,.91),root);torso=joint('Torso',(0,0,1.15),pelvis)
 box('PelvisWorkTrousers',(0,0,.91),(.34,.24,.22),navy,pelvis,.04)
 box('UniformTorso',(0,0,1.18),(.44,.27,.42),teal,torso,.055)
 box('EditPocket',(-.11,-.15,1.22),(.12,.025,.10),navy,torso,.006)
 box('JacketZip',(0,-.15,1.20),(.015,.023,.35),white,torso,.002)
 box('JacketHem',(0,-.01,.99),(.45,.29,.045),navy,torso,.005)
 rod('Neck',(0,0,1.36),(0,0,1.46),.055,skin,torso)
 head=joint('HeadJoint',(0,0,1.48),torso);sphere('Head',(0,0,1.565),(.13,.115,.155),skin,head)
 sphere('HairCrown',(0,.02,1.69),(.135,.115,.055),navy,head)
 box('HairBack',(0,.10,1.58),(.22,.07,.21),navy,head,.025)
 for sign in [-1,1]:
  sphere('EyeWhite_'+str(sign),(sign*.045,-.108,1.59),(.024,.012,.021),white,head);sphere('EyePupil_'+str(sign),(sign*.045,-.119,1.59),(.009,.006,.011),black,head)
 sphere('Nose',(0,-.12,1.55),(.021,.028,.025),skin,head)
 rod('SmileLeft',(-.036,-.109,1.511),(0,-.119,1.503),.005,black,head);rod('SmileRight',(0,-.119,1.503),(.036,-.109,1.511),.005,black,head)
 legs=[];joints=[root,pelvis,torso,head]
 for side,x in [('Left',-.115),('Right',.115)]:
  hip=joint(side+'Hip',(x,0,.92),pelvis);knee=joint(side+'Knee',(x,0,.52),hip);foot=joint(side+'Foot',(x,0,.12),knee)
  rod(side+'TrouserUpper',(x,0,.90),(x,0,.52),.088,navy,hip);sphere(side+'KneeCap',(x,0,.52),(.084,.085,.086),navy,knee);rod(side+'TrouserLower',(x,0,.52),(x,0,.16),.073,navy,knee)
  box(side+'Boot',(x,-.065,.065),(.18,.31,.13),white,foot,0);box(side+'BootUpper',(x,.015,.15),(.15,.17,.15),black,foot,.018)
  legs.append(foot);joints += [hip,knee,foot]
 left=joint('LeftShoulder',(-.245,0,1.36),torso);le=joint('LeftElbow',(-.28,0,1.09),left);lh=joint('LeftHand',(-.28,-.02,.87),le)
 rod('LeftSleeve',(-.24,0,1.36),(-.28,0,1.09),.073,teal,left);rod('LeftForearm',(-.28,0,1.09),(-.28,-.02,.88),.055,teal,le);sphere('LeftGlove',(-.28,-.02,.86),(.061,.055,.085),glove,lh)
 right=joint('RightShoulder',(.245,0,1.36),torso);re=joint('RightElbow',(.36,-.04,1.08),right);grip=Vector((.47,-.18,.83));rh=joint('RightHand',grip,re)
 rod('RightSleeve',(.245,0,1.36),(.36,-.04,1.08),.073,teal,right);sphere('RightElbowCap',(.36,-.04,1.08),(.068,.065,.07),teal,re);rod('RightForearm',(.36,-.04,1.08),grip,.055,teal,re)
 sphere('RightGlove',grip,(.065,.062,.075),glove,rh);sphere('GripThumb',grip+Vector((-.04,-.025,.02)),(.03,.032,.04),glove,rh)
 handmark=joint('HandGrip',grip,rh);tool=joint('OccupationTool',grip,rh);toolmark=joint('ToolGrip',grip,tool)
 box('ToolGripGeometry',grip,(.035,.045,.10),navy,tool,.004)
 bag=mat('Unbranded paper bag',(.52,.31,.16))
 box('ShoppingBag',grip+Vector((.045,0,-.25)),(.26,.16,.29),bag,tool,.006)
 for x in [-.06,.15]:rod('BagHandleSide'+str(x),grip+Vector((x,0,-.105)),grip+Vector((x,0,.02)),.009,navy,tool)
 rod('BagHandleGrip',grip+Vector((-.06,0,.02)),grip+Vector((.15,0,.02)),.012,navy,tool)
 box('BagFold',grip+Vector((.045,0,-.105)),(.27,.17,.018),bag,tool,.002)
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
       lift=.12*math.sin(math.pi*u)**2
       foreaft=-.10*math.sin(2*math.pi*u)
       distance=math.hypot(.8-lift,foreaft)
       bend=math.acos(min(1,max(-1,distance/.8)))
       hip=math.atan2(foreaft,.8-lift)-bend;knee=2*bend;ankle=-(hip+knee)
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
 export(H/'exports/mall-shopper.glb')
 world=bpy.data.worlds.new('StudioWorld');s.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.19,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5
 target=(.15,-.10,.88)
 for n,loc,e in [('Key',(-3,-4,5),500),('Fill',(3,-2,3),350),('Rim',(1,3,4),600)]:
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+n;o.data.energy=e;o.data.size=3;aim(o,target)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=2.7
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
 for name,delta,clip,frame in [('hero',(1.6,-3,1),'Idle',0),('front',(0,-3,.2),'Idle',0),('rear',(1.4,3,.6),'Idle',0),('side',(3,-.2,.3),'Idle',0),('action-a',(1.6,-3,1),'WalkInPlace',15),('action-b',(1.6,-3,1),'WalkInPlace',45),('idle-action',(1.6,-3,1),'Idle',15)]:
  select_clip(clip,frame);s.camera.location=Vector(target)+Vector(delta);aim(s.camera,target);s.render.filepath=str(H/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
 select_clip('Idle',0);bpy.ops.wm.save_as_mainfile(filepath=str(H/'sources/mall-shopper.blend'))
