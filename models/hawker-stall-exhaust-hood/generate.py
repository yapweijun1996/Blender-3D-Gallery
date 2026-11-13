"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='hawker-stall-exhaust-hood'
ROOT='ASSET_HawkerStallExhaustHood'
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
 bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_texcoords=False,export_extras=True,export_cameras=False,export_lights=False)
def studio():
 s=bpy.context.scene;s.world=bpy.data.worlds.new('Slate studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.10,.14,.18,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
 for name,loc,power in [('Key',(-4,-6,7),1300),('Fill',(5,-2,4),900),('Rim',(0,5,6),1500)]:
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=5;aim(o,TARGET)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=SCALE
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def render_views():
 s=bpy.context.scene
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5)),('underside',(1.3,-2,-1))]:

  if name=='underside':
   bpy.ops.object.light_add(type='AREA',location=(0,-2,-3));light=bpy.context.object;light.name='STUDIO_Underside';light.data.energy=1000;light.data.size=4;aim(light,TARGET)
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
def disc(name,loc,r,depth,m,parent):
 bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=depth,location=loc);return finish(bpy.context.object,name,m,parent,.002)
def meshpart(name,verts,faces,m,parent):
 import bmesh
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);return finish(o,name,m,parent,0)
def label(body,loc,size,m,parent):
 c=bpy.data.curves.new('Editable queue lettering','FONT');c.body=body;c.align_x='CENTER';c.size=size;c.extrude=.0007;c.resolution_u=3;c.offset=.00005;o=bpy.data.objects.new('EDITABLE_QueueText',c);bpy.context.scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(math.pi/2,0,0);o.parent=parent;c.materials.append(m)
TARGET=(0,0,.40);SCALE=3.2
def build(root):
 steel=mat('Brushed hood steel',(.65,.69,.68),.60,.38);filtermat=mat('Dark filter baffles',(.24,.30,.29),.55,.55)
 box('HOUSING_Top',(0,0,.43),(2.2,.8,.04),steel,root,.006)
 box('HOUSING_Back',(0,.38,.23),(2.2,.04,.40),steel,root,.004)
 for x in [-1.08,1.08]:box('HOUSING_Side',(x,0,.23),(.04,.76,.40),steel,root,.004)
 o=box('HOUSING_SlopedFront',(0,-.33,.23),(2.16,.035,.42),steel,root,.004);o.rotation_euler.x=math.radians(16)
 box('DUCT_Collar',(0,.08,.47),(.53,.48,.05),steel,root,.004)
 box('DUCT_UpperStub',(0,.08,.65),(.45,.40,.31),steel,root,.004)
 for i,x in enumerate([-.78,-.26,.26,.78]):
  g=empty('REMOVABLE_Filter_%02d'%i,(0,0,0),root)
  box('FILTER_Back',(x,0,.045),(.49,.62,.05),filtermat,g,.002)
  for j in range(7):box('FILTER_Baffle',(x,-.27+j*.09,.0125),(.46,.025,.025),steel,g,.001)

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
