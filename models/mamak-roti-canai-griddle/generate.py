"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mamak-roti-canai-griddle'
ROOT='ASSET_MamakRotiCanaiGriddle'
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
TARGET=(0, 0, 0.47);SCALE=1.8
def build(root):

 steel=mat('Satin stainless chassis',(.65,.70,.70),.65,.4);iron=mat('Seasoned griddle plate',(.12,.14,.14),.6,.5);black=mat('Control grip',(.055,.06,.06),0,.6);brass=mat('Burner control pointer',(.7,.5,.22),.4,.5)
 box('CHASSIS_Body',(0,0,.75),(.98,.68,.22),steel,root,.012)
 box('GRIDDLE_CookingPlate',(0,0,.875),(1.02,.72,.03),iron,root,.008)
 for x in [-.43,.43]:
  for y in [-.27,.27]:
   box('LEG_SquareTube',(x,y,.33),(.045,.045,.62),steel,root,.003);disc('FOOT_Leveler',(x,y,.015),.034,.03,black,root)
 box('SHELF_Lower',(0,0,.23),(.90,.58,.025),steel,root)
 for x in [-.23,.23]:
  knob=disc('CONTROL_Knob',(x,-.358,.76),.035,.028,black,root);knob.rotation_euler=(math.pi/2,0,0)
  box('CONTROL_Pointer',(x,-.374,.775),(.005,.004,.023),brass,root,.001)
 box('BACK_Splash',(0,.35,.945),(1.02,.02,.14),steel,root)
 for x in [-.5,.5]:box('SIDE_Splash',(x,.02,.92),(.02,.65,.09),steel,root)
 box('DRAWER_Grease',(0,-.354,.66),(.28,.025,.035),steel,root,.004)
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
