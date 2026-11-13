"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='hatchback-car'
ROOT='ASSET_HatchbackCar'
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
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=5;aim(o,TARGET)
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
 return [mat('Steel',(.55,.61,.64),.65),mat('Ivory',(.88,.90,.89)),mat('Transit blue',(.07,.26,.41),.15),mat('Safety yellow',(.99,.72,.16)),mat('Rubber',(.08,.10,.12)),mat('Glazing blue-grey',(.43,.66,.73),.2,.18),mat('Warm timber',(.49,.27,.12)),mat('Display amber',(.98,.62,.12))]

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

def lathe(name,profile,m,parent,offset=(0,0,0)):
 n=32;verts=[];faces=[]
 for r,z in profile:
  for i in range(n):
   a=2*math.pi*i/n;verts.append((r*math.cos(a)+offset[0],r*math.sin(a)+offset[1],z+offset[2]))
 for j in range(len(profile)):
  for i in range(n):
   a=j*n+i;b=j*n+(i+1)%n;c=((j+1)%len(profile))*n+(i+1)%n;d=((j+1)%len(profile))*n+i;faces.append((a,b,c,d))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 import bmesh
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(m);o.parent=parent;return o

def ring(name,loc,major,minor,m,parent):
 bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=8,location=loc,major_radius=major,minor_radius=minor);return finish(bpy.context.object,name,m,parent,0)
def clear_glass():
 m=mat('Clear glass alpha',(.55,.76,.82),0,.20);m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.18;m.blend_method='BLEND';return m
TARGET=(0,0,.8);SCALE=5.5
def profile(name,points,width,m,parent,x=0):
 # Watertight extrusion along X, profile points in YZ.
 n=len(points);verts=[(xx,y,z) for xx in [x-width/2,x+width/2] for y,z in points];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 import bmesh
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);return finish(o,name,m,parent,.006)
def build(root):
 steel,ivory,blue,yellow,rubber,glass,timber,amber=palette();paint=mat('Original teal paint',(.12,.46,.47),.35,.28);clear=clear_glass()
 root['wheel_radius_m']=.31;root['wheelbase_m']=2.48;root['wheel_track_m']=1.58;root['vehicle']='Generic hatchback; illustrative articulation only, no driving physics'
 box('CHASSIS_Centre',(0,0,.37),(1.30,3.40,.12),steel,root,.02)
 box('FLOOR_Cabin',(0,.10,.53),(1.50,2.25,.10),rubber,root,.02)
 # Real openings above each wheel, no solid side slab through the tyres.
 for side in [-1,1]:
  points=[(-2,.84),(2,.84),(2,.43),(1.60,.43),(1.60,.68),(.88,.68),(.88,.43),(-.88,.43),(-.88,.68),(-1.60,.68),(-1.60,.43),(-2,.43)]
  profile('BODY_WheelArchSill',points,.08,paint,root,side*.84)
 box('BODY_Nose',(0,-1.84,.64),(1.70,.32,.42),paint,root,.04)
 box('BODY_Tail',(0,1.84,.64),(1.70,.32,.42),paint,root,.04)
 box('BONNET',(0,-1.20,.85),(1.68,1.52,.08),paint,root,.025)
 box('REAR_Deck',(0,1.90,.86),(1.68,.14,.08),paint,root,.025)
 box('ROOF',(0,.40,1.55),(1.50,1.50,.08),paint,root,.03)
 for side in [-1,1]:
  rod('A_Pillar',(side*.79,-.72,.90),(side*.72,-.35,1.51),.045,paint,root)
  rod('C_Pillar',(side*.79,1.85,.90),(side*.72,1.15,1.51),.055,paint,root)
  profile('REAR_Quarter',[(.68,.86),(1.90,.86),(1.15,1.51),(.68,1.51)],.055,paint,root,side*.79)
  door=empty('MOVABLE_Door_Left' if side<0 else 'MOVABLE_Door_Right',(side*.88,-.68,.85),root)
  profile('DOOR_Lower',[(0,0),(1.32,0),(1.32,.23),(.14,.23)],.045,paint,door)
  profile('DOOR_ClearPane',[(.16,.23),(1.30,.23),(1.30,.65),(.36,.65)],.018,clear,door)
  for a,b in [((.14,.23),(.36,.65)),((.36,.65),(1.32,.65)),((1.32,.65),(1.32,.02))]:rod('DOOR_Frame',(0,*a),(0,*b),.025,steel,door)
  box('DOOR_Handle',(side*.04,1.05,.18),(.05,.19,.045),steel,door,.008)
  rod('MIRROR_Stem',(0,.18,.27),(side*.12,.18,.27),.018,steel,door);box('MIRROR',(side*.15,.19,.29),(.12,.18,.09),paint,door,.02)
  swing(door,2,-side*1.20)
 wind=box('WINDSCREEN',(0,-.535,1.205),(1.42,.025,.714),clear,root,.004);wind.rotation_euler.x=-math.atan2(.37,.61)
 rear=box('HATCH_Glass',(0,1.50,1.205),(1.42,.025,.929),clear,root,.004);rear.rotation_euler.x=math.atan2(.70,.61)
 box('HATCH_Lower',(0,1.90,.97),(1.50,.05,.18),paint,root,.02)
 for x in [-.40,.40]:
  for y in [-.02,.82]:
   box('SEAT_Cushion',(x,y,.70),(.53,.48,.16),rubber,root,.04);back=box('SEAT_Back',(x,y+.22,1.02),(.53,.15,.55),rubber,root,.035);back.rotation_euler.x=.12
 box('DASHBOARD',(0,-.46,.98),(1.44,.22,.17),rubber,root,.03)
 steering=ring('INTERIOR_Steering',(-.40,-.30,1.09),.14,.018,steel,root);steering.rotation_euler.x=math.pi/2
 for side in [-1,1]:
  for y in [-1.24,1.24]:
   steer=empty(('STEER_Front' if y<0 else 'AXLE_Rear')+('_L' if side<0 else '_R'),(side*.79,y,.31),root)
   steer['axle_y_m']=y;steer['wheel_radius_m']=.31
   roll=empty('ROLL_Wheel',(0,0,0),steer)
   tyre=ring('TYRE',(0,0,0),.265,.045,rubber,roll);tyre.scale.z=2;tyre.rotation_euler.y=math.pi/2
   hub=disc('HUB',(0,0,0),.18,.115,steel,roll);hub.rotation_euler.y=math.pi/2
   spokes=[]
   for i in range(5):
    a=i*math.tau/5;spokes.append(rod('RIM_Spoke',(.065,0,0),(.065,.16*math.cos(a),.16*math.sin(a)),.018,ivory,roll))
   combined('RIM_Spokes',spokes,roll)
   swing(roll,0,math.pi)
   if y<0:swing(steer,2,.28)
 for x in [-.59,.59]:
  box('HEADLIGHT',(x,-2.01,.70),(.34,.025,.16),ivory,root,.02);box('TAIL_Light',(x,2.01,.70),(.28,.025,.15),mat('Tail red',(.75,.05,.05)),root,.02)
 box('GRILLE',(0,-2.018,.48),(.68,.025,.10),rubber,root,.01)
 box('PLATE_Front',(0,-2.035,.62),(.44,.012,.10),ivory,root,.003);box('PLATE_Rear',(0,2.035,.62),(.44,.012,.10),ivory,root,.003)

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
