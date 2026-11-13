"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='dining-table'
ROOT='ASSET_DiningTable'
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
TARGET=(0, 0, 0.4);SCALE=2.0
def build(root):
 steel,ivory,blue,yellow,rubber,glass,timber,amber=palette()
 box('TOP',(0,0,.735),(1.40,.80,.05),timber,root,.018)
 for x in [-.59,.59]:
  for y in [-.29,.29]:box('LEG',(x,y,.355),(.065,.065,.71),timber,root,.008)
  box('APRON_End',(x,0,.65),(.05,.61,.12),timber,root,.004)
 for y in [-.29,.29]:box('APRON_Side',(0,y,.65),(1.18,.05,.12),timber,root,.004)

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
