"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='singapore-traffic-signal-pole'
ROOT='ASSET_SingaporeTrafficSignalPole'
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
 import bmesh
 root=bpy.data.objects[ROOT];copies=[];dg=bpy.context.evaluated_depsgraph_get()
 for orig in list(root.children_recursive):
  if orig.type!='FONT':continue
  mesh=bpy.data.meshes.new_from_object(orig.evaluated_get(dg),depsgraph=dg);bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6)
  bad=[f for f in bm.faces if f.calc_area()<1e-14]
  if bad:bmesh.ops.dissolve_edges(bm,edges=list({max(f.edges,key=lambda e:e.calc_length()) for f in bad}),use_verts=False,use_face_split=False)
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  o=bpy.data.objects.new(orig.name+'_Export',mesh);bpy.context.scene.collection.objects.link(o);o.parent=orig.parent;o.matrix_world=orig.matrix_world.copy();copies.append(o)
 bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
 for o in root.children_recursive:
  if o.type!='FONT':o.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_texcoords=False,export_extras=True,export_cameras=False,export_lights=False)
 for o in copies:bpy.data.objects.remove(o,do_unlink=True)
def studio():
 s=bpy.context.scene;s.world=bpy.data.worlds.new('Slate studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.10,.14,.18,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
 for name,loc,power in [('Key',(-4,-6,7),1300),('Fill',(5,-2,4),900),('Rim',(0,5,6),1500)]:
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=5;aim(o,TARGET)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=SCALE
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def render_views():
 s=bpy.context.scene
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
def disc(name,loc,r,depth,m,parent):
 bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=depth,location=loc);return finish(bpy.context.object,name,m,parent,.002)
def meshpart(name,verts,faces,m,parent):
 import bmesh
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);return finish(o,name,m,parent,0)
def label(body,loc,size,m,parent):
 c=bpy.data.curves.new('Editable original lettering','FONT');c.body=body;c.align_x='CENTER';c.size=size;c.extrude=.0007;c.resolution_u=3;c.offset=.00005;o=bpy.data.objects.new('EDITABLE_Lettering',c);bpy.context.scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(math.pi/2,0,0);o.parent=parent;c.materials.append(m)

def wheel(name,loc,r,m,parent):
 o=disc(name,loc,r,.07,m,parent);o.rotation_euler=(math.pi/2,0,0);return o
def signal_head(name,x,z,back,root,black,red,amber,green):
 box(name+'_Backplate',(x,-.08,z),(.46,.07,1.18),back,root,.06)
 box(name+'_Housing',(x,-.14,z),(.34,.18,1.04),black,root,.035)
 for i,colour in enumerate([red,amber,green]):
  zz=z+.32-i*.32;o=disc(name+'_Lens_'+str(i),(x,-.24,zz),.115,.025,colour,root);o.rotation_euler=(math.pi/2,0,0)
  box(name+'_VisorTop',(x,-.29,zz+.12),(.25,.16,.025),black,root,.008)
  for xx in [-.12,.12]:box(name+'_VisorSide',(x+xx,-.28,zz+.035),(.018,.14,.17),black,root,.006)
TARGET=(0, 0, 1.7);SCALE=4.6
def build(root):

 black=mat('Charcoal pole and housing',(.10,.13,.12),.1,.6);white=mat('Pale pole base',(.83,.85,.81),0,.6);red=mat('Static red lens',(.65,.06,.035),0,.35);amber=mat('Unlit amber lens',(.25,.13,.02),0,.5);green=mat('Unlit green lens',(.025,.17,.08),0,.5)
 box('BASE_Footing',(0,0,.06),(.32,.32,.12),white,root,.012)
 rod('POLE_Main',(0,0,.12),(0,0,3.05),.065,black,root)
 rod('POLE_PaleLower',(0,0,.12),(0,0,.90),.067,white,root)
 signal_head('VEHICLE',0,3.0,black,root,black,red,amber,green)
 box('BUTTON_Housing',(0,-.09,1.05),(.15,.09,.24),black,root,.018)
 o=disc('BUTTON_Pedestrian',(0,-.14,1.05),.04,.018,white,root);o.rotation_euler=(math.pi/2,0,0)
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
