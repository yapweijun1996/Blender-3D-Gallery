"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='kopitiam-toast-display'
ROOT='ASSET_KopitiamToastDisplay'
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
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
def disc(name,loc,r,depth,m,parent):
 bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=depth,location=loc);return finish(bpy.context.object,name,m,parent,.002)
def meshpart(name,verts,faces,m,parent):
 import bmesh
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);return finish(o,name,m,parent,0)
def label(body,loc,size,m,parent):
 c=bpy.data.curves.new('Editable queue lettering','FONT');c.body=body;c.align_x='CENTER';c.size=size;c.extrude=.0007;c.resolution_u=3;c.offset=.00005;o=bpy.data.objects.new('EDITABLE_QueueText',c);bpy.context.scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(math.pi/2,0,0);o.parent=parent;c.materials.append(m)

def lathe(name,profile,m,parent,n=48,loc=(0,0,0)):
 verts=[(loc[0]+r*math.cos(2*math.pi*i/n),loc[1]+r*math.sin(2*math.pi*i/n),loc[2]+z) for r,z in profile for i in range(n)]
 faces=[]
 for j in range(len(profile)):
  k=(j+1)%len(profile)
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,k*n+(i+1)%n,k*n+i))
 return meshpart(name,verts,faces,m,parent)
def tube(name,points,r,m,parent,n=12):
 verts=[]
 for j,p in enumerate(points):
  tangent=Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])
  q=tangent.to_track_quat('Z','Y')
  for i in range(n):verts.append(Vector(p)+q@Vector((r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),0)))
 faces=[tuple(range(n-1,-1,-1)),tuple((len(points)-1)*n+i for i in range(n))]
 for j in range(len(points)-1):
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 return meshpart(name,verts,faces,m,parent)
TARGET=(0, 0, 0.21);SCALE=0.9
def build(root):

 wood=mat('Warm display timber',(.39,.19,.08),0,.6);cream=mat('Bread crumb',(.84,.62,.30),0,.8);crust=mat('Toast crust',(.49,.25,.08),0,.8);steel=mat('Tray stainless',(.68,.72,.70),.5,.4)
 box('DISPLAY_Base',(0,0,.018),(.58,.34,.036),wood,root,.007)
 for z in [.065,.245]:box('SHELF_Tray',(0,0,z),(.52,.29,.018),steel,root,.003)
 for x in [-.275,.275]:
  for y in [-.145,.145]:box('FRAME_Post',(x,y,.22),(.025,.025,.40),wood,root)
 box('DISPLAY_Header',(0,.13,.42),(.58,.04,.075),wood,root,.004)
 for z in [.098,.278]:
  for x in [-.165,0,.165]:
   box('TOAST_Crust',(x,0,z),(.13,.12,.045),crust,root,.015)
   box('TOAST_Crumb',(x,-.001,z+.023),(.107,.097,.003),cream,root,.01)
   for j in range(3):box('TOAST_GrillMark',(x-.03+j*.03,0,z+.025),(.003,.065,.001),crust,root,.0004)
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
