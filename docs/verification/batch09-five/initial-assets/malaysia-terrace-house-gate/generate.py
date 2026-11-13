"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='malaysia-terrace-house-gate'
ROOT='ASSET_MalaysiaTerraceHouseGate'
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
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.location*=(5.4/4);o.data.energy=power*(5.4/4)**2;o.data.size=5.4;aim(o,TARGET)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=SCALE
 s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def render_views():
 s=bpy.context.scene
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
TARGET=(0, 0, 0.95);SCALE=5.4
def build(root):
 concrete=mat('Cream masonry piers',(.79,.77,.65),0,.85);steel=mat('Charcoal gate steel',(.19,.24,.25),.55);bronze=mat('Brushed warm accent',(.65,.47,.27),.55);silver=mat('Hinge hardware',(.57,.62,.62),.75)
 for x in [-1.95,1.95]:
  box('PIER',(x,0,.95),(.30,.38,1.90),concrete,root,.018);box('PIER_Cap',(x,0,1.92),(.36,.44,.08),concrete,root,.012)
 for side,origin,sgn in [('Left',-1.77,1),('Right',1.77,-1)]:
  leaf=empty('MOVABLE_'+side+'Leaf',(origin,0,0),root);leaf['hinge_axis']='local Z';leaf['example_open_degrees']=sgn*65
  for x in [sgn*.03,sgn*1.72]:box(side+'_Stile',(x,0,.90),(.06,.07,1.66),steel,leaf,.004)
  for z in [.10,1.70]:box(side+'_Rail',(sgn*.875,0,z),(1.69,.07,.07),steel,leaf,.004)
  for i in range(12):box(side+'_Slat_'+str(i),(sgn*(.13+i*.135),0,.90),(.065,.045,1.52),steel,leaf,.002)
  for z in [.38,1.4]:box(side+'_Accent',(sgn*.875,-.042,z),(1.62,.025,.045),bronze,leaf,.002)
  box(side+'_Lock',(sgn*1.63,-.065,.92),(.12,.055,.16),silver,leaf,.008)
  for z in [.30,1.46]:rod(side+'_Hinge',(origin,0,z-.065),(origin,0,z+.065),.027,silver,root)

def main():
 if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
  root=empty(ROOT);root['units']='metres';root['front_axis']='Blender -Y / glTF +Z';root['backlog_id']=321;root['scope']='Illustrative modular asset; no official certification or runtime logic'
  build(root);studio();s.camera.location=Vector(TARGET)+Vector((1.3,-2,1))*SCALE;aim(s.camera,TARGET);bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 export(HERE/'exports/optimized.glb')
if __name__=='__main__':main()
