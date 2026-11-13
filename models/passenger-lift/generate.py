"""Original illustrative two-stop passenger lift. Metres; not certified equipment.
Door demonstration and travel demonstration are mutually exclusive modes.
Run normal to author source; --export-source exports edited saved source without regeneration.
"""
from pathlib import Path
import bpy, math, sys, json, struct
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='passenger-lift';ROOT='ASSET_PassengerLift'
def material(name,rgb,metal=0,rough=.45,alpha=1):
 m=bpy.data.materials.new(name);m.use_nodes=True
 c=tuple((v/255)/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4 for v in rgb)+(alpha,)
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=c;p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;p.inputs['Alpha'].default_value=alpha;m.diffuse_color=c
 if alpha<1:m.blend_method='BLEND';m.use_backface_culling=False;m.show_transparent_back=False
 return m
def empty(name,parent=None,loc=(0,0,0)):
 o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.location=loc;return o
def box(name,loc,dims,mat,parent,bevel=.002):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.parent=parent;o.location=loc;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
 if bevel:b=o.modifiers.new('Editable eased edges','BEVEL');b.width=bevel;b.segments=2
 return o
def label(name,text,loc,size,mat,parent):
 bpy.ops.object.text_add();o=bpy.context.object;o.name=name;o.parent=parent;o.location=loc;o.rotation_euler=(math.pi/2,0,0);o.data.body=text;o.data.align_x='CENTER';o.data.size=size;o.data.extrude=.0005;o.data.materials.append(mat);return o
def action(o,name,axis,delta):
 original=o.location[axis]
 for frame,d in [(1,0),(25,delta),(49,0)]:o.location[axis]=original+d;o.keyframe_insert(data_path='location',frame=frame)
 o.animation_data.action.name=name
 for f in o.animation_data.action.fcurves:
  for p in f.keyframe_points:p.interpolation='LINEAR'
 o.location[axis]=original

def build():
 root=empty(ROOT);root['backlog_id']=5;root['units']='metres';root['front_axis']='Blender -Y / glTF +Z';root['origin']='Base floor centre';root['scope']='Original cutaway two-stop illustrative passenger lift, NOT operational or certified'
 root['animation_modes']='DOOR_* together at bottom, OR TRAVEL_Cab only; never combine modes'
 steel=material('Brushed steel',(157,171,178),.7,.36);dark=material('Graphite guide frame',(43,59,68),.55,.48);cream=material('Warm landing',(224,221,207),0,.72);blue=material('Cab trim',(36,104,122),.3,.4);glass=material('Cab cutaway glazing',(113,182,191),.05,.3,.23);black=material('Dark display',(24,35,43),0,.45);white=material('Ivory label',(245,244,227),0,.5);yellow=material('Threshold accent',(237,186,62),.2,.48)
 fixed=empty('FIXED_ShaftAndLandings',root)
 box('Shaft_Base',(0,-.40,.05),(3.2,3.2,.10),dark,fixed)
 for x in [-1.4,1.4]:
  for y in [-1.12,1.12]:box('Shaft_Post',(x,y,3.2),(.12,.12,6.2),dark,fixed)
  for z in [.16,3.15,6.25]:box('Shaft_SideBeam',(x,0,z),(.12,2.12,.12),dark,fixed)
  box('Guide_Rail',(x/1.4*1.20,.55,3.20),(.04,.08,6.20),steel,fixed,0)
 for z in [.16,3.15,6.25]:box('Shaft_RearBeam',(0,1.12,z),(2.68,.12,.12),dark,fixed)
 box('Shaft_TopBeam',(0,0,6.40),(2.92,2.36,.18),dark,fixed)
 label('Shaft_Label','LIFT',(0,-1.192,6.20),.22,white,fixed)
 for stop in [0,1]:
  h=3.0*stop;land=empty('LANDING_'+str(stop),fixed, (0,0,h))
  box('Landing_'+str(stop)+'_Floor',(0,-1.50,.25),(2.8,1.0,.10),cream,land)
  box('Landing_'+str(stop)+'_Threshold',(0,-1.00,.31),(1.04,.04,.02),yellow,land,0)
  box('Landing_'+str(stop)+'_Header',(0,-1.075,2.52),(2.26,.20,.16),blue,land)
  for side in [-1,1]:
   word='L' if side<0 else 'R'
   box('Landing_'+str(stop)+'_PocketFront_'+word,(side*.80,-1.16,1.38),(.56,.03,2.12),blue,land)
   box('Landing_'+str(stop)+'_PocketBack_'+word,(side*.80,-1.015,1.38),(.56,.03,2.12),dark,land)
   box('Landing_'+str(stop)+'_OuterJamb_'+word,(side*1.105,-1.075,1.38),(.05,.20,2.12),steel,land)
   door=empty('DOOR_Landing'+str(stop)+word,land,(side*.255,-1.075,.33))
   box('Leaf_Landing'+str(stop)+word,(0,0,1.05),(.50,.04,2.10),steel,door)
   box('Inlay_Landing'+str(stop)+word,(side*.19,-.024,1.08),(.012,.006,1.78),blue,door,0)
   if stop==0:action(door,'DOOR_Cycle_Landing0'+word,0,side*.53)
  box('Landing_'+str(stop)+'_Display',(0,-1.182,2.52),(.32,.018,.11),black,land)
  label('Landing_'+str(stop)+'_FloorLabel',str(stop),(0,-1.194,2.485),.09,white,land)
  box('Landing_'+str(stop)+'_CallPanel',(1.23,-1.195,1.25),(.12,.03,.20),steel,land)
  box('Landing_'+str(stop)+'_CallButton',(1.23,-1.215,1.25),(.055,.012,.055),yellow,land)
 cab=empty('CAB_Carriage',root)
 cab['wall_to_wall_clear_interior_m']=[1.70,1.60,2.30];cab['travel_metres']=3.0
 box('Cab_Floor',(0,-.03,.235),(2.20,1.88,.11),blue,cab)
 box('Cab_FloorFinish',(0,0,.295),(1.70,1.60,.01),cream,cab,0)
 box('Cab_BackWall',(0,.84,1.45),(1.86,.08,2.30),steel,cab)
 for side in [-1,1]:
  word='L' if side<0 else 'R'
  box('Cab_SideWall_'+word,(side*.89,.02,1.45),(.08,1.56,2.30),glass,cab)
  box('Cab_CornerPost_'+word,(side*.89,.80,1.45),(.08,.08,2.30),blue,cab)
  box('Cab_PocketFront_'+word,(side*.795,-.925,1.38),(.55,.025,2.12),blue,cab)
  box('Cab_PocketBack_'+word,(side*.795,-.78,1.38),(.55,.04,2.12),steel,cab)
  box('Cab_GuideShoe_'+word,(side*1.12,.55,1.45),(.08,.12,.24),blue,cab)
  door=empty('DOOR_Cab'+word,cab,(side*.255,-.86,.33))
  box('Leaf_Cab'+word,(0,0,1.05),(.50,.04,2.10),steel,door)
  box('Inlay_Cab'+word,(side*.19,-.024,1.08),(.012,.006,1.78),blue,door,0)
  action(door,'DOOR_Cycle_Cab'+word,0,side*.53)
 box('Cab_Header',(0,-.85,2.50),(2.20,.20,.12),blue,cab)
 box('Cab_Sill',(0,-.85,.315),(2.20,.20,.01),yellow,cab,0)
 box('Cab_Ceiling',(0,-.03,2.64),(2.20,1.88,.08),blue,cab)
 for x in [-.48,.48]:box('Cab_Light',(x,0,2.591),(.30,1.10,.012),white,cab)
 # Handrail/control panel are interior fittings, not wall-to-wall dimensional boundaries.
 box('Cab_Handrail',(0,.72,1.24),(1.30,.045,.045),steel,cab)
 for x in [-.56,.56]:box('Cab_HandrailMount',(x,.76,1.24),(.04,.08,.04),steel,cab)
 box('Cab_ControlPanel',(.824,-.37,1.27),(.035,.18,.36),black,cab)
 for z in [1.18,1.32]:box('Cab_Button',(.802,-.37,z),(.012,.055,.055),yellow,cab)
 action(cab,'TRAVEL_Cab',2,3.0)
 bpy.context.scene.frame_set(1);return root

def export(root,destination):
 bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
 for o in root.children_recursive:o.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=True,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
 data=destination.read_bytes();n=struct.unpack_from('<I',data,12)[0];j=json.loads(data[20:20+n]);unique=[];mapping={}
 for i,m in enumerate(j.get('materials',[])):
  key=json.dumps({k:v for k,v in m.items() if k!='name'},sort_keys=True)
  if key not in mapping:mapping[key]=len(unique);unique.append(m)
  for mesh in j.get('meshes',[]):
   for prim in mesh['primitives']:
    if prim.get('material')==i:prim['_newmaterial']=mapping[key]
 for mesh in j.get('meshes',[]):
  for prim in mesh['primitives']:
   if '_newmaterial' in prim:prim['material']=prim.pop('_newmaterial')
 j['materials']=unique;raw=json.dumps(j,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);tail=data[20+n:];destination.write_bytes(struct.pack('<III',0x46546c67,2,20+len(raw)+len(tail))+struct.pack('<II',len(raw),0x4e4f534a)+raw+tail)

def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def studio():
 s=bpy.context.scene;floor=material('STUDIO floor',(221,223,218),0,.95);box('STUDIO_Floor',(0,0,-.035),(200,200,.06),floor,None,0)
 for name,loc,power,size in [('Key',(-5,-7,10),1400,6),('Fill',(6,-3,5),1000,5),('Rear',(2,5,9),1600,5)]:
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,(0,-.4,3))
 bpy.ops.object.camera_add(location=(8,-12,8));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=8.2;point_at(s.camera,(0,-.4,3))
 s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.31,.32,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'

def main():
 for d in ['sources','exports','previews','reports']:(HERE/d).mkdir(exist_ok=True)
 if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.fps=24;s.frame_start=1;s.frame_end=49;root=build();studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 bpy.context.scene.frame_set(1);export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
