"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='tool-cabinet'
ROOT='ASSET_ToolCabinet'
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
  bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.location*=(2.7/4);o.data.energy=power*(2.7/4)**2;o.data.size=2.7;aim(o,TARGET)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=SCALE
 s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def render_views():
 s=bpy.context.scene
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.50)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)

def beam(name,a,b,width,depth,m,parent):
 a,b=Vector(a),Vector(b);d=b-a;o=box(name,(a+b)/2,(width,depth,d.length),m,parent,0);o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return o
def text(name,value,loc,size,m,parent):
 bpy.ops.object.text_add(location=loc,rotation=(math.pi/2,0,0));o=bpy.context.object;o.data.body=value;o.data.align_x='CENTER';o.data.size=size;o.data.extrude=.001
 bpy.ops.object.convert(target='MESH');return finish(bpy.context.object,name,m,parent,0)
def frame(root,w,h,m):
 box('DOOR_Sill',(0,0,.04),(w,.24,.08),m,root,.004)
 for x in [-w/2+.08,w/2-.08]:box('DOOR_Jamb',(x,0,h/2),(.16,.20,h),m,root,.004)
 box('DOOR_Header',(0,0,h-.08),(w-.32,.20,.16),m,root,.004)
def shutterframe(root,w,h,m):
 box('FRAME_Sill',(0,0,.06),(w,.23,.12),m,root,.004)
 for x in [-w/2+.05,w/2-.05]:box('FRAME_Jamb',(x,0,h/2),(.10,.15,h),m,root,.003)
 box('FRAME_Head',(0,0,h-.05),(w-.2,.15,.1),m,root,.003)
def doorleaf(leaf,side,sgn,w,h,wood,dark,brass):
 box(side+'_Core',(sgn*w/2,0,h/2),(w,.06,h),dark,leaf,.003)
 for x in [sgn*.045,sgn*(w-.045)]:box(side+'_Stile',(x,-.045,h/2),(.09,.035,h),wood,leaf,.003)
 for z in [.05,h*.48,h-.05]:box(side+'_Rail',(sgn*w/2,-.045,z),(w-.18,.035,.1),wood,leaf,.003)
 for z,hh in [(h*.25,h*.36),(h*.75,h*.34)]:
  box(side+'_RaisedPanel',(sgn*w/2,-.045,z),(w-.25,.028,hh),wood,leaf,.008)
 rod(side+'_Pull',(sgn*(w-.13),-.10,h*.45),(sgn*(w-.13),-.10,h*.55),.014,brass,leaf)
def animate(leaf,side,angle):
 for f,a in [(0,0),(30,angle),(60,0)]:
  leaf.rotation_euler.z=math.radians(a);leaf.keyframe_insert(data_path='rotation_euler',frame=f)
 leaf.animation_data.action.name='OpenClose_'+side
 for fc in leaf.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
 bpy.context.scene.render.fps=30;bpy.context.scene.frame_start=0;bpy.context.scene.frame_end=60;bpy.context.scene.frame_set(0)
def archcap(name,x,length,radius,m,parent):
 verts=[]
 for xx in [x-length/2,x+length/2]:
  for radius2 in [radius,radius-.035]:
   for i in range(13):
    a=i*math.pi/12;verts.append((xx,radius2*math.cos(a),.14+radius2*math.sin(a)))
 faces=[]
 for i in range(12):
  faces.extend([(i,i+1,26+i+1,26+i),(13+i,39+i,40+i,14+i),(i,13+i,14+i,i+1),(26+i,27+i,40+i,39+i)])
 faces.extend([(0,26,39,13),(12,25,51,38)])
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);finish(o,name,m,parent,0)

TARGET=(0, 0, 0.95);SCALE=2.7

def cylinder(name,loc,radius,depth,m,parent):
 bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=radius,depth=depth,location=loc);return finish(bpy.context.object,name,m,parent,.001)
def ico(name,loc,scale,m,parent,sub=1):
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc);o=bpy.context.object;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,m,parent,0)
def cone(name,a,b,r,m,parent):
 a,b=Vector(a),Vector(b);d=b-a;bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=r,radius2=0,depth=d.length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,name,m,parent,0)
def ring(name,loc,radius,thickness,m,parent):
 bpy.ops.mesh.primitive_torus_add(major_segments=24,minor_segments=6,location=loc,major_radius=radius,minor_radius=thickness);return finish(bpy.context.object,name,m,parent,0)
def leaf(name,start,end,width,m,parent):
 start,end=Vector(start),Vector(end);axis=end-start;across=Vector((-axis.y,axis.x,0))
 if across.length<.001:across=Vector((1,0,0))
 across.normalize();verts=[]
 # Closed thin folded leaf mesh; three axial rings preserve a curved spine.
 for t,w in [(0,.006),(.25,width*.75),(.55,width),(.80,width*.65),(1,.001)]:
  c=start+axis*t+Vector((0,0,axis.length*.15*math.sin(math.pi*t)))
  verts.extend([c-across*w,c+Vector((0,0,.01)),c+across*w,c-Vector((0,0,.004))])
 faces=[]
 for j in range(4):
  for k in range(4):faces.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
 faces.extend([(3,2,1,0),(16,17,18,19)])
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 import bmesh
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);finish(o,name,m,parent,0)
def flower(name,loc,size,petal,centre,parent,count):
 c=Vector(loc)
 for i in range(count):
  a=i*math.tau/count;pos=c+Vector((size*.55*math.cos(a),-size*.12,size*.55*math.sin(a)))
  o=ico(name+'_Petal',pos,(size*.48,size*.16,size*.66),petal,parent,2);o.rotation_euler.y=-a
 ico(name+'_Centre',c+Vector((0,-size*.22,0)),(size*.22,size*.22,size*.22),centre,parent,1)
 rod(name+'_Stamen',c+Vector((0,-size*.1,0)),c+Vector((0,-size*.8,.03)),size*.035,centre,parent)
def prism(name,points,z0,z1,m,parent):
 n=len(points);verts=[(x,y,z) for z in [z0,z1] for x,y in points];faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
 faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);finish(o,name,m,parent,0)
def lantern(name,loc,radius,height,shade,gold,parent):
 c=Vector(loc);ico(name+'_Shade',c,(radius,radius,height/2),shade,parent,2)
 for sign in [-1,1]:cylinder(name+'_Cap',c+Vector((0,0,sign*height/2)),radius*.42,.035,gold,parent)
 for i in range(8):
  a=i*math.tau/8
  rod(name+'_Rib',c+Vector((radius*.30*math.cos(a),radius*.30*math.sin(a),-height*.48)),c+Vector((radius*.92*math.cos(a),radius*.92*math.sin(a),0)),.006,gold,parent)
  rod(name+'_Rib',c+Vector((radius*.92*math.cos(a),radius*.92*math.sin(a),0)),c+Vector((radius*.30*math.cos(a),radius*.30*math.sin(a),height*.48)),.006,gold,parent)
 rod(name+'_Tassel',c+Vector((0,0,-height/2)),c+Vector((0,0,-height/2-.20)),.018,gold,parent)

def build(root):

 blue=mat('Industrial blue enamel',(.17,.36,.49),.35);steel=mat('Galvanized shelves',(.58,.63,.63),.65);dark=mat('Black handles',(.16,.19,.20))
 box('CABINET_Base',(0,0,.06),(1.20,.62,.12),blue,root,.008)
 box('CABINET_Back',(0,.29,.98),(1.2,.04,1.72),blue,root,.004)
 for x in [-.58,.58]:box('CABINET_Side',(x,0,.98),(.04,.54,1.72),blue,root,.004)
 box('CABINET_Top',(0,0,1.86),(1.2,.62,.04),blue,root,.004)
 for i,z in enumerate([.35,.82,1.30]):box('CABINET_Shelf_'+str(i),(0,0,z),(1.10,.53,.025),steel,root,.002)
 for side,x,sgn in [('Left',-.55,1),('Right',.55,-1)]:
  leaf=empty('MOVABLE_'+side+'Leaf',(x,-.33,.14),root)
  box(side+'_Door',(sgn*.27,0,.83),(.54,.035,1.66),blue,leaf,.004)
  box(side+'_Handle',(sgn*.46,-.045,.84),(.025,.055,.19),dark,leaf,.004)
  for j in range(4):box(side+'_Vent_'+str(j),(sgn*.27,-.021,1.40+j*.035),(.36,.008,.012),dark,leaf,0)
  animate(leaf,side,sgn*85)

def main():
 if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')))
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
  root=empty(ROOT);root['units']='metres';root['front_axis']='Blender -Y / glTF +Z';root['backlog_id']=156;root['scope']='Original illustrative heritage module, not surveyed or certified'
  build(root);studio();s.camera.location=Vector(TARGET)+Vector((1.3,-2,1))*SCALE;aim(s.camera,TARGET);bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 export(HERE/'exports/optimized.glb')
if __name__=='__main__':main()
