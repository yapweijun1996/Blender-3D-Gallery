"""Original female-office-worker pilot: editable rigid articulation, not a skin or IK rig."""
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
 navy=mat('Workwear navy',(.025,.055,.085));teal=mat('Occupation uniform',(0.23, 0.12, 0.19));yellow=mat('Reflective lime',(.75,.82,.12));skin=mat('Warm skin',(.53,.29,.16));white=mat('Off white',(.82,.86,.83));black=mat('Boot rubber',(.018,.024,.03));steel=mat('Broom aluminium',(.35,.42,.46),.32);glove=mat('Protective gloves',(.78,.68,.18));bristle=mat('Broom bristles',(.13,.07,.18))
 pelvis=joint('Pelvis',(0,0,.91),root);torso=joint('Torso',(0,0,1.15),pelvis)
 box('PelvisWorkTrousers',(0,0,.91),(.34,.24,.22),navy,pelvis,.04)
 box('UniformTorso',(0,0,1.18),(.41,.26,.43),teal,torso,.055)
 box('EditPocket',(-.11,-.15,1.23),(.12,.025,.10),navy,torso,.006)
 box('BlousePanel',(0,-.15,1.25),(.22,.022,.28),white,torso,.005)
 for x in [-.17,.17]:box('TailoredVestPanel'+str(x),(x,-.15,1.18),(.09,.025,.39),teal,torso,.006)
 box('VestHem',(0,0,.99),(.42,.28,.055),teal,torso,.008)
 rod('Neck',(0,0,1.36),(0,0,1.46),.055,skin,torso)
 head=joint('HeadJoint',(0,0,1.48),torso);sphere('Head',(0,0,1.565),(.13,.115,.155),skin,head)
 sphere('HairCrown',(0,.02,1.69),(.135,.12,.06),navy,head)
 sphere('HairBun',(0,.135,1.67),(.075,.065,.075),navy,head)
 for sign in [-1,1]:
  sphere('EyeWhite_'+str(sign),(sign*.045,-.108,1.59),(.024,.012,.021),white,head);sphere('EyePupil_'+str(sign),(sign*.045,-.119,1.59),(.009,.006,.011),black,head)
 sphere('Nose',(0,-.12,1.55),(.021,.028,.025),skin,head)
 rod('SmileLeft',(-.036,-.109,1.511),(0,-.119,1.503),.005,black,head);rod('SmileRight',(0,-.119,1.503),(.036,-.109,1.511),.005,black,head)
 legs=[];joints=[root,pelvis,torso,head]
 for side,x in [('Left',-.115),('Right',.115)]:
  hip=joint(side+'Hip',(x,0,.92),pelvis);knee=joint(side+'Knee',(x,0,.53),hip);foot=joint(side+'Foot',(x,-.04,.12),knee)
  rod(side+'TrouserUpper',(x,0,.90),(x,0,.52),.088,navy,hip);sphere(side+'KneeCap',(x,0,.53),(.084,.085,.086),navy,knee);rod(side+'TrouserLower',(x,0,.53),(x,0,.16),.073,navy,knee)
  box(side+'Boot',(x,-.065,.065),(.17,.29,.13),black,foot,0);box(side+'BootUpper',(x,.015,.15),(.15,.17,.15),black,foot,.018)
  legs.append(foot);joints += [hip,knee,foot]
 left=joint('LeftShoulder',(-.245,0,1.36),torso);le=joint('LeftElbow',(-.28,0,1.09),left);lh=joint('LeftHand',(-.28,-.02,.87),le)
 rod('LeftSleeve',(-.24,0,1.36),(-.28,0,1.09),.073,teal,left);rod('LeftForearm',(-.28,0,1.09),(-.28,-.02,.88),.055,teal,le);sphere('LeftGlove',(-.28,-.02,.86),(.061,.055,.085),glove,lh)
 right=joint('RightShoulder',(.245,0,1.36),torso);re=joint('RightElbow',(.36,-.04,1.08),right);grip=Vector((.47,-.18,.83));rh=joint('RightHand',grip,re)
 rod('RightSleeve',(.245,0,1.36),(.36,-.04,1.08),.073,teal,right);sphere('RightElbowCap',(.36,-.04,1.08),(.068,.065,.07),teal,re);rod('RightForearm',(.36,-.04,1.08),grip,.055,teal,re)
 sphere('RightGlove',grip,(.065,.062,.075),glove,rh);sphere('GripThumb',grip+Vector((-.04,-.025,.02)),(.03,.032,.04),glove,rh)
 handmark=joint('HandGrip',grip,rh);tool=joint('OccupationTool',grip,rh);toolmark=joint('ToolGrip',grip,tool)
 box('ToolGripGeometry',grip,(.035,.045,.10),black,tool,.004)
 box('PlanClipboard',grip+Vector((.055,-.025,.09)),(.26,.03,.30),navy,tool,.004)
 box('PlanSheet',grip+Vector((.055,-.043,.09)),(.235,.006,.265),white,tool,.001)
 for x in [-.02,.07]:box('PlanVertical'+str(x),grip+Vector((x,-.048,.09)),(.008,.004,.18),teal,tool,0)
 for z in [.02,.14]:box('PlanHorizontal'+str(z),grip+Vector((.055,-.048,z)),(.18,.004,.008),teal,tool,0)
 joints += [left,le,lh,right,re,rh,tool]
 rest={o.name:(o.location.copy(),o.rotation_euler.copy()) for o in joints}
 for o in joints:o.animation_data_create()
 for clip in ['Idle','ReviewPlans']:
  for o in joints:
   for t in o.animation_data.nla_tracks:t.mute=True
   act=bpy.data.actions.new(clip+'_'+o.name);o.animation_data.action=act
   for frame in range(0,61,3):
    o.location=rest[o.name][0];o.rotation_euler=rest[o.name][1];phase=2*math.pi*frame/60
    if clip=='Idle':
     if o==head:o.rotation_euler.z=.07*math.sin(phase)
     if o==left:o.rotation_euler.x=.04*math.sin(phase)
    else:
     if o==right:o.rotation_euler.z=0.3*math.sin(phase)
     if o==head:o.rotation_euler.z=.045*math.sin(phase)
    o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='rotation_euler',frame=frame)
   for fc in act.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'
   o.animation_data.action=None;t=o.animation_data.nla_tracks.new();t.name=clip;t.strips.new(clip,0,act)
 select_clip('Idle',0)
 export(H/'exports/female-office-worker.glb')
 world=bpy.data.worlds.new('StudioWorld');s.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.15,.19,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5
 target=(.35,-.12,.92)
 for n,loc,e in [('Key',(-3,-4,5),500),('Fill',(3,-2,3),350),('Rim',(1,3,4),600)]:
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+n;o.data.energy=e;o.data.size=3;aim(o,target)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=2.7
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
 for name,delta,clip,frame in [('hero',(1.6,-3,1),'Idle',0),('front',(0,-3,.2),'Idle',0),('rear',(1.4,3,.6),'Idle',0),('side',(3,-.2,.3),'Idle',0),('action-a',(1.6,-3,1),'ReviewPlans',15),('action-b',(1.6,-3,1),'ReviewPlans',45),('idle-action',(1.6,-3,1),'Idle',15)]:
  select_clip(clip,frame);s.camera.location=Vector(target)+Vector(delta);aim(s.camera,target);s.render.filepath=str(H/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
 select_clip('Idle',0);bpy.ops.wm.save_as_mainfile(filepath=str(H/'sources/female-office-worker.blend'))
