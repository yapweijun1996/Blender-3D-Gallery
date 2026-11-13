"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='malaysia-car-porch-roof'
ROOT='ASSET_MalaysiaCarPorchRoof'
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
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.location*=(8.0/4);o.data.energy=power*(8.0/4)**2;o.data.size=8.0;aim(o,TARGET)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=SCALE
 s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def render_views():
 s=bpy.context.scene
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
TARGET=(0, 0, 1.45);SCALE=8.0
def build(root):
 steel=mat('Painted steel supports',(.31,.38,.38),.55);roof=mat('Warm zinc roof',(.58,.63,.62),.5);concrete=mat('Footing pads',(.70,.71,.66),0,.85);trim=mat('Roof fascia',(.80,.76,.64),.4)
 for x in [-2.45,2.45]:
  for y in [-1.95,1.95]:
   box('FOOTING',(x,y,.05),(.34,.34,.10),concrete,root,.01);h=2.67+y*.04;box('COLUMN',(x,y,.10+h/2),(.11,.11,h),steel,root,.003)
  o=box('BEAM_Side',(x,0,2.82),(.12,4.50,.16),steel,root,.003);o.rotation_euler.x=.04
 for y in [-2.12,0,2.12]:box('BEAM_Cross',(0,y,2.90+y*.04),(5.25,.10,.14),steel,root,.003)
 for i in range(20):
  x=-2.755+i*.29;o=box('ROOF_Sheet_'+str(i),(x,0,3.01),(.29,4.80,.028),roof,root,.001);o.rotation_euler.x=.04
  o=box('ROOF_Rib_'+str(i),(x,0,3.035),(.025,4.80,.04),roof,root,.001);o.rotation_euler.x=.04
 for x in [-2.90,2.90]:
  o=box('FASCIA_Side',(x,0,3.00),(.06,4.90,.14),trim,root,.003);o.rotation_euler.x=.04
 for y in [-2.42,2.42]:box('FASCIA_End',(0,y,3.00+y*.04),(5.86,.06,.14),trim,root,.003)
 rod('DOWNPIPE',(2.45,-2.00,.10),(2.45,-2.00,2.87),.04,steel,root)

def main():
 if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
  root=empty(ROOT);root['units']='metres';root['front_axis']='Blender -Y / glTF +Z';root['backlog_id']=323;root['scope']='Illustrative modular asset; no official certification or runtime logic'
  build(root);studio();s.camera.location=Vector(TARGET)+Vector((1.3,-2,1))*SCALE;aim(s.camera,TARGET);bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 export(HERE/'exports/optimized.glb')
if __name__=='__main__':main()
