"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='delivery-van'
ROOT='ASSET_DeliveryVan'
def mat(name,rgb,metal=0,rough=.45):
 m=bpy.data.materials.new(name);m.use_nodes=True
 c=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)+(1,)
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=c;p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;m.diffuse_color=c;return m
def empty(name,loc=(0,0,0),parent=None):
 o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.location=loc;o.parent=parent;return o
def finish(o,name,m,parent,bevel=.002):
 o.name=name;o.data.materials.append(m);o.parent=parent
 if bevel:
  b=o.modifiers.new('Manufactured edge','BEVEL');b.width=bevel;b.segments=2;o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
 return o
def box(name,loc,dims,m,parent,bevel=.002):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,m,parent,bevel)
def rod(name,a,b,r,m,parent):
 a,b=Vector(a),Vector(b);d=b-a;bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r,depth=d.length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,name,m,parent,.001)
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def export(path):
 bpy.ops.object.select_all(action='DESELECT');root=bpy.data.objects[ROOT];root.select_set(True)
 for o in root.children_recursive:o.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=True,export_texcoords=False,export_extras=True,export_cameras=False,export_lights=False)
def studio():
 s=bpy.context.scene;s.world=bpy.data.worlds.new('Slate studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.10,.14,.18,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
 for name,loc,power in [('Key',(-4,-6,7),1300),('Fill',(5,-2,4),900),('Rim',(0,5,6),1500)]:
  bpy.ops.object.light_add(type='AREA',location=Vector(loc)*max(1,SCALE/3));o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power*max(1,(SCALE/3)**2);o.data.size=5*max(1,SCALE/3);aim(o,TARGET)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=SCALE
 s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=512;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def render_views():
 s=bpy.context.scene
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
def disc(name,loc,r,depth,m,parent):
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r,depth=depth,location=loc);return finish(bpy.context.object,name,m,parent,.002)
def digit(number,x,y,z,size,m,parent):
 # Seven-segment numerals as independently editable paint/inlay meshes, no fonts.
 patterns={'0':'abcdef','1':'bc','2':'abged','3':'abgcd','4':'fgbc','5':'afgcd','6':'afgecd','7':'abc','8':'abcdefg','9':'abfgcd'}
 for c in patterns[str(number)]:
  if c in 'agd':
   zz={'a':.85,'g':.45,'d':.05}[c];box('NUM_%s_%s'%(number,c),(x,y,z+zz*size),(.38*size,.008,.07*size),m,parent,.002)
  else:
   xx=.22 if c in 'bc' else -.22;zz=.65 if c in 'bf' else .25;box('NUM_%s_%s'%(number,c),(x+xx*size,y,z+zz*size),(.07*size,.008,.30*size),m,parent,.002)

def label(name,text,loc,size,m,parent):
 bpy.ops.object.text_add(location=loc,rotation=(math.pi/2,0,0));o=bpy.context.object;o.name=name;o.data.body=text;o.data.size=size;o.data.align_x='CENTER';o.data.extrude=.0008;o.data.resolution_u=2;o.data.materials.append(m);o.parent=parent;return o
def swing(o,axis,value):
 o.rotation_euler[axis]=0;o.keyframe_insert(data_path='rotation_euler',frame=1)
 o.rotation_euler[axis]=value;o.keyframe_insert(data_path='rotation_euler',frame=30)
 o.rotation_euler[axis]=0;o.keyframe_insert(data_path='rotation_euler',frame=60)
 bpy.context.scene.frame_set(1)
def slide(o,axis,value):
 v=o.location[axis];o.keyframe_insert(data_path='location',frame=1)
 o.location[axis]=v+value;o.keyframe_insert(data_path='location',frame=30)
 o.location[axis]=v;o.keyframe_insert(data_path='location',frame=60)
 bpy.context.scene.frame_set(1)
def palette():
 return [mat('Steel',(.75,.80,.82),.25),mat('Ivory',(.88,.90,.89)),mat('Transit blue',(.07,.26,.41),.15),mat('Safety yellow',(.99,.72,.16)),mat('Rubber',(.08,.10,.12)),mat('Glazing blue-grey',(.43,.66,.73),.2,.18),mat('Warm timber',(.49,.27,.12)),mat('Display amber',(.98,.62,.12))]

def ellipse(name,loc,rx,ry,h,m,parent):
 o=disc(name,loc,1,h,m,parent);o.scale.x=rx;o.scale.y=ry;bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def combined(name,objects,parent):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;o.parent=parent;return o
def lid_motion(o):
 for f,a in [(1,-1.15),(30,-.03),(60,-1.15)]:
  o.rotation_euler.x=a;o.keyframe_insert(data_path='rotation_euler',frame=f)
 bpy.context.scene.frame_set(1)

def shell(name,loc,dims,m,parent,openings=None):
 # Independent wall/floor/roof meshes, with real facade door apertures.
 x,y,z=loc;w,d,h=dims;t=min(.16,w*.06,d*.06,h*.06);bottom=z-h/2
 box(name+'_Floor',(x,y,bottom+t/2),(w,d,t),m,parent)
 box(name+'_Roof',(x,y,z+h/2-t/2),(w,d,t),m,parent)
 box(name+'_Back',(x,y+d/2-t/2,z),(w,t,h),m,parent)
 for xx in [x-w/2+t/2,x+w/2-t/2]:box(name+'_Side',(xx,y,z),(t,d,h),m,parent)
 openings=openings or [(0,min(1.8,w*.35),min(2.5,h*.75))]
 edge=-w/2
 for cx,ow,oh in sorted(openings):
  left=cx-ow/2;right=cx+ow/2
  if left>edge:box(name+'_FrontPier',(x+(edge+left)/2,y-d/2+t/2,z),(left-edge,t,h),m,parent)
  box(name+'_EntryHeader',(x+cx,y-d/2+t/2,bottom+oh+(h-oh)/2),(ow,t,h-oh),m,parent)
  edge=right
 if edge<w/2:box(name+'_FrontPier',(x+(edge+w/2)/2,y-d/2+t/2,z),(w/2-edge,t,h),m,parent)

def ring(name,loc,major,minor,m,parent):
 bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=8,location=loc,major_radius=major,minor_radius=minor);return finish(bpy.context.object,name,m,parent,0)
def vehicle_glass():
 m=mat('Vehicle glazing',(.55,.76,.82),0,.20);m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.18;m.blend_method='BLEND';return m
def wheelset(root,r,track,axles,steel,rubber,ivory):
 root['wheel_radius_m']=r;root['wheelbase_m']=axles[1]-axles[0];root['wheel_track_m']=track
 root['vehicle']='Original illustrative vehicle, no driving physics or operational certification'
 for side in [-1,1]:
  for y in axles:
   steer=empty(('STEER_Front' if y==axles[0] else 'AXLE_Rear')+('_L' if side<0 else '_R'),(side*track/2,y,r),root)
   roll=empty('ROLL_Wheel',(0,0,0),steer)
   tyre=ring('TYRE',(0,0,0),r-.06,.06,rubber,roll);tyre.scale.z=2;tyre.rotation_euler.y=math.pi/2
   hub=disc('HUB',(0,0,0),r*.58,.15,steel,roll);hub.rotation_euler.y=math.pi/2
   spokes=[]
   for i in range(5):
    a=i*math.tau/5;spokes.append(rod('RIM_Spoke',(.085,0,0),(.085,r*.50*math.cos(a),r*.50*math.sin(a)),.018,ivory,roll))
   combined('RIM_Spokes',spokes,roll);swing(roll,0,math.pi)
   if y==axles[0]:swing(steer,2,.22)
def cabin(root,front,back,roofz,paint,steel,glass,rubber):
 clear=vehicle_glass()
 box('CABIN_Floor',(0,(front+back)/2,.83),(1.8,back-front,.08),rubber,root)
 box('CABIN_Roof',(0,(front+back)/2,roofz),(1.95,back-front,.10),paint,root,.035)
 box('CABIN_Windscreen',(0,front,roofz-.53),(1.82,.035,.90),clear,root)
 box('CABIN_Nose',(0,front-.12,1.13),(2.0,.30,.50),paint,root,.06)
 for side in [-1,1]:
  box('CABIN_Door',(side*.98,(front+back)/2,1.20),(.06,back-front-.10,.65),paint,root,.025)
  box('CABIN_SideGlass',(side*.98,(front+back)/2,roofz-.48),(.025,back-front-.18,.70),clear,root)
  for y in [front,back]:box('CABIN_Pillar',(side*.98,y,(roofz+1.4)/2),(.06,.07,roofz-1.4),paint,root)
  box('CABIN_Mirror',(side*1.13,front+.25,1.8),(.18,.15,.20),paint,root,.02)
 for x in [-.47,.47]:
  box('INTERIOR_Seat',(x,back-.45,1.03),(.54,.55,.18),rubber,root,.04)
  box('INTERIOR_SeatBack',(x,back-.18,1.42),(.54,.14,.68),rubber,root,.035)
 box('INTERIOR_Dashboard',(0,front+.22,1.42),(1.8,.35,.18),rubber,root)
 o=ring('INTERIOR_Steering',(-.47,front+.4,1.55),.16,.018,steel,root);o.rotation_euler.x=math.pi/2
def rear_pair(root,y,height,paint,steel,glass):
 for side in [-1,1]:
  door=empty('MOVABLE_RearLeft' if side<0 else 'MOVABLE_RearRight',(side*1.04,y,.86),root)
  box('REAR_DoorLeaf',(-side*.51,0,height/2),(.94,.04,height),paint,door,.012)
  box('REAR_DoorWindow',(-side*.51,-.023,height*.72),(.60,.012,height*.25),glass,door)
  box('REAR_Handle',(-side*.87,.055,height*.45),(.035,.05,.22),steel,door)
  swing(door,2,-side*1.10)
TARGET=(0,0,1.25);SCALE=7.4
def build(root):
 steel,ivory,blue,yellow,rubber,glass,timber,amber=palette()

 paint=mat('Delivery ivory',(.86,.89,.87),.2,.36);clear=vehicle_glass()
 box('CHASSIS',(0,0,.48),(1.35,4.9,.16),steel,root)
 cabin(root,-2.35,-.62,2.25,paint,steel,glass,rubber)
 box('CARGO_Floor',(0,.9,.81),(1.90,3.0,.08),rubber,root)
 box('CARGO_Roof',(0,.95,2.42),(2.16,3.1,.12),paint,root,.03)
 box('CARGO_LeftWall',(-1.04,.9,1.61),(.08,3.0,1.50),paint,root)
 box('CARGO_Bulkhead',(0,-.58,1.6),(2.08,.08,1.5),paint,root)
 for lo,hi in [(-.60,-.02),(1.40,2.35)]:box('CARGO_RightWall',(1.04,(lo+hi)/2,1.61),(.08,hi-lo,1.50),paint,root)
 box('CARGO_RightHeader',(1.04,.69,2.30),(.08,1.42,.12),paint,root)
 slide_door=empty('MOVABLE_SideSlide',(1.13,.69,1.55),root)
 box('CARGO_SlidingLeaf',(0,0,0),(.045,1.30,1.32),paint,slide_door,.018)
 box('CARGO_SlidingHandle',(.04,-.4,0),(.04,.16,.04),steel,slide_door)
 slide(slide_door,1,.95)
 rear_pair(root,2.48,1.48,paint,steel,glass)
 for y in [-2.58,2.48]:box('BUMPER',(0,y,.68),(2.1,.12,.18),rubber,root,.025)
 for x in [-.72,.72]:
  box('HEADLIGHT',(x,-2.51,1.15),(.32,.04,.20),ivory,root)
  box('TAIL_Light',(x,2.53,.80),(.16,.04,.08),amber,root)
 wheelset(root,.36,1.85,[-1.65,1.55],steel,rubber,ivory)
def main():
 for d in ['sources','exports','previews','reports','metadata']:(HERE/d).mkdir(exist_ok=True)
 if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
  root=empty(ROOT);root['units']='metres';root['front_axis']='Blender -Y / glTF +Z';root['scope']='Illustrative modular prop, not engineering/safety certification'
  build(root);studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 export(HERE/'exports/optimized.glb')
 if '--skip-render' not in sys.argv:render_views()
if __name__=='__main__':main()
