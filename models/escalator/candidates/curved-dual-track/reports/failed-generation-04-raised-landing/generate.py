"""Original deterministic metric architectural prop. Blender 4.0.2. No external assets."""
from pathlib import Path
import bpy, math, sys, json
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='escalator-circulation'
ROOT='ASSET_EscalatorV1_ID004'
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
  factor=max(1,SCALE/3);bpy.ops.object.light_add(type='AREA',location=Vector(TARGET)+Vector(loc)*factor);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power*factor*factor;o.data.size=5*factor;aim(o,TARGET)
 bpy.ops.object.camera_add();s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=SCALE
 s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=512;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def render_views():
 s=bpy.context.scene
 for name,delta in [('hero',(1.3,-2,1)),('front',(0,-3,.15)),('rear',(1.4,2,1)),('side',(3,-.3,.5))]:
  s.camera.location=Vector(TARGET)+Vector(delta)*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(name+'.png'));bpy.ops.render.render(write_still=True)
def disc(name,loc,r,depth,m,parent):
 bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r,depth=depth,location=loc);return finish(bpy.context.object,name,m,parent,0)
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
def profile(name,points,width,m,parent,x=0):
 # Watertight extrusion along X, profile points in YZ.
 n=len(points);verts=[(xx,y,z) for xx in [x-width/2,x+width/2] for y,z in points];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 import bmesh
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);return finish(o,name,m,parent,.006)


import importlib.util
ks=importlib.util.spec_from_file_location('escalator_kin',HERE/'kinematics.py');kin=importlib.util.module_from_spec(ks);ks.loader.exec_module(kin)
POSE,L,N,PITCH,FLAT=kin.make_track(.75,-1);PIVOT=(.36,-.2);PERIOD=L/.5
UPPER=[POSE(i*L/6000) for i in range(6000) if POSE(i*L/6000)[3] in ['lower_flat','lower_transition','incline','upper_transition','upper_flat']]
END=max(p[0] for p in UPPER);CENTER=END/2
TARGET=(0,0,1.0);SCALE=13.5

def mesh_object(name,verts,faces,m,parent):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 import bmesh
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(m);o.parent=parent;return o

def prism(name,poly,width,m,parent,x=0):
 n=len(poly);verts=[(xx,y,z) for xx in [x-width/2,x+width/2] for y,z in poly];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)];return mesh_object(name,verts,faces,m,parent)

def tube(name,points,m,parent,r=.014):
 n=len(points);verts=[];faces=[]
 for i,p in enumerate(points):
  tangent=(Vector(points[(i+1)%n])-Vector(points[(i-1)%n])).normalized();normal=Vector((0,-tangent.z,tangent.y)).normalized()
  for j in range(8):
   a=2*math.pi*j/8;verts.append(tuple(Vector(p)+Vector((r*math.cos(a),0,0))+normal*r*math.sin(a)))
 for i in range(n):
  for j in range(8):faces.append((i*8+j,i*8+(j+1)%8,((i+1)%n)*8+(j+1)%8,((i+1)%n)*8+j))
 return mesh_object(name,verts,faces,m,parent)

def key_motion(o,phase,duration,pathfn,kind):
 frames=round(duration*24);o.rotation_mode='QUATERNION'
 from mathutils import Quaternion
 # Explicit24Hz samples; positions/orientations never scale or disappear.
 for f in range(frames+1):
  u=f/frames;point=pathfn(u,phase);o.location=point[:3];o.rotation_quaternion=Quaternion((1,0,0),point[3]);o.keyframe_insert(data_path='location',frame=f+1);o.keyframe_insert(data_path='rotation_quaternion',frame=f+1)
 o.animation_data.action.name=kind+'_'+o.name
 for fc in o.animation_data.action.fcurves:
  for k in fc.keyframe_points:k.interpolation='LINEAR'
 o['period_seconds']=frames/24;o['intended_speed_m_s']=.5;o['phase_m']=phase
 return frames

def rail_path():
 pts=[(p[0]-.36-CENTER,p[1]+.9) for p in UPPER[::30]]
 # Add exact flat endpoints. Rounded end returns are separate from the step turnaround.
 pts[0]=(-.36-CENTER,.9);pts.append((END-.36-CENTER,3.9));a,b=pts[0],pts[-1];r=.25
 for i in range(1,25):
  t=math.pi*i/24;pts.append((b[0]+r*math.sin(t),b[1]-r+r*math.cos(t)))
 top=list(pts[:len(UPPER[::30])+1])
 pts.extend([(y,z-.5) for y,z in reversed(top[:-1])])
 for i in range(1,24):
  t=math.pi+math.pi*i/24;pts.append((a[0]+r*math.sin(t),a[1]-r+r*math.cos(t)))
 lengths=[0.]
 for i in range(len(pts)):lengths.append(lengths[-1]+math.dist(pts[i],pts[(i+1)%len(pts)]))
 def at(s):
  import bisect
  s%=lengths[-1];i=min(len(pts)-1,bisect.bisect_right(lengths,s)-1);t=(s-lengths[i])/(lengths[i+1]-lengths[i]);a,b=pts[i],pts[(i+1)%len(pts)];return (a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),math.atan2(b[1]-a[1],b[0]-a[0]))
 return pts,lengths[-1],at

def build(root):
 steel,ivory,blue,yellow,rubber,glass,timber,amber=palette();clear=clear_glass()
 full=kin.profile(PITCH);body=[(y-.36,z+.2) for y,z in full if z<=-.02]
 # Exact finite curved body below tread grooves, with rigid support retained.
 topy=PITCH-math.sqrt(PITCH*PITCH-.02*.02)+.004
 body=[(topy-.36,.18),(.396-.36,.18),(.396-.36,0)]+[(y-.36,z+.2) for y,z in full[3:] if z<-.02]
 for i in range(N):
  moving=empty('STEP_%02d'%i,(0,0,0),root);moving['rigid_full_profile']=True
  parts=[prism('CURVED_RISER_AND_SUPPORT',body,1.0,steel,moving)]
  for j in range(25):parts.append(box('TREAD_Rib',(-.48+j*.04,(.004+.396)/2-.36,.19),(.023,.392,.02),steel,moving,0))
  combined('STEP_BODY_%02d'%i,parts,moving)
  wheels=[]
  for x in [-.58,.58]:
   o=disc('CHAIN_Wheel',(x,0,0),.035,.018,rubber,moving);o.rotation_euler.y=math.pi/2;wheels.append(o)
  for x in [-.68,.68]:
   o=disc('GUIDE_Wheel',(x,-.32,.03),.035,.018,rubber,moving);o.rotation_euler.y=math.pi/2;wheels.append(o)
  combined('STEP_WHEELS_%02d'%i,wheels,moving)
  def step_at(u,phase):
   y,z,a,_=POSE(u*L+phase);return (0,y-CENTER,z-.2,a)
  key_motion(moving,i*PITCH,PERIOD,step_at,'StepCirculation')
 # Original faceted roller swept-envelope rail profiles, independently editable closed meshes.
 rails=json.loads((HERE/'rail-profiles.json').read_text())
 for side,x,name in [('L',-.58,'CHAIN'),('R',.58,'CHAIN'),('L',-.68,'GUIDE'),('R',.68,'GUIDE')]:
  rail=rails[name];inside=rail['inner'];outside=rail['outer'];verts=[];faces=[];count=len(inside)
  for a,b in zip(inside,outside):verts.extend([(x-.012,a[0],a[1]),(x+.012,a[0],a[1]),(x+.012,b[0],b[1]),(x-.012,b[0],b[1])])
  for i in range(count):
   for j in range(4):faces.append((i*4+j,i*4+(j+1)%4,((i+1)%count)*4+(j+1)%4,((i+1)%count)*4+j))
  mesh_object('TRACK_'+name+'_'+side,verts,faces,steel,root)
 top=[(p[0]-.36-CENTER,p[1]) for p in UPPER[::30]];top[0]=(-.36-CENTER,0);top.append((END-.36-CENTER,3))
 for side,x in [('L',-.55),('R',.55)]:
  prism('GUARD_'+side,[(y,z+.10) for y,z in top]+[(y,z+.84) for y,z in reversed(top)],.02,clear,root,x)
  prism('SKIRT_'+side,[(y,z-.25) for y,z in top]+[(y,z+.08) for y,z in reversed(top)],.035,steel,root,x)
 # Side truss panels and floor enclose return run; no solid block through moving steps.
 envelope=[(-1.2-CENTER,0)]+top+[(END+1.2-CENTER,3)]
 for side,x in [('L',-.76),('R',.76)]:prism('TRUSS_'+side,[(y,z-2.3) for y,z in envelope]+[(y,z-.06) for y,z in reversed(envelope)],.035,steel,root,x)
 prism('TRUSS_Bottom',[(y,z-2.34) for y,z in envelope]+[(y,z-2.3) for y,z in reversed(envelope)],1.55,steel,root)
 for label,y,z in [('Lower',-1.2,0),('Upper',END+1.2,3)]:box('TRUSS_End_'+label,(0,y-CENTER,z-1.18),(1.55,.04,2.25),steel,root,0)
 for label,y,z in [('Lower',-.3,0),('Upper',END+.3,3)]:
  box('LANDING_'+label,(0,y-CENTER,z+.03),(1.55,1.8,.05),ivory,root,.002)
  parts=[];tip=.65 if label=='Lower' else END-.65
  for j in range(24):parts.append(box('tooth',(-.46+j*.04,tip-CENTER,z+.004),(.011,.12,.032),yellow,root,0))
  combined('COMB_'+label,parts,root)
 points,railL,railAt=rail_path()
 # Parameterize the actual offset seam path by its own arc length, not belt-centre length.
 seam_points=[]
 for i,(y,z) in enumerate(points):
  prev=points[(i-1)%len(points)];nxt=points[(i+1)%len(points)];a=math.atan2(nxt[1]-prev[1],nxt[0]-prev[0]);seam_points.append((y-.038*math.sin(a),z+.038*math.cos(a)))
 seam_lengths=[0.]
 for i in range(len(seam_points)):seam_lengths.append(seam_lengths[-1]+math.dist(seam_points[i],seam_points[(i+1)%len(seam_points)]))
 seamL=seam_lengths[-1]
 for side,x in [('L',-.55),('R',.55)]:
  tube('HANDRAIL_'+side,[(x,y,z) for y,z in points],rubber,root,.04)
  seam=empty('HANDRAIL_MaterialSeam_'+side,(0,0,0),root)
  box('BELT_Seam',(0,0,0),(.085,.025,.018),steel,seam,.001)
  def seam_at(u,phase,x=x):
   import bisect
   distance=(u*seamL+phase)%seamL;i=min(len(seam_points)-1,bisect.bisect_right(seam_lengths,distance)-1);t=(distance-seam_lengths[i])/(seam_lengths[i+1]-seam_lengths[i]);a,b=seam_points[i],seam_points[(i+1)%len(seam_points)];return(x,a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]),math.atan2(b[1]-a[1],b[0]-a[0]))
  key_motion(seam,0,seamL/.5,seam_at,'HandrailTravel')
 root['handrail_seam_surface_path_length_m']=seamL
 root['units']='metres';root['rise_m']=3.;root['chain_path_length_m']=L;root['step_count']=N;root['nominal_linear_speed_m_s']=.5;root['handrail_path_length_m']=railL
 root['scope']='Original kinematic visual mechanism; not engineering/safety certification, no operational UI. Uniform rubber belt transport indicated by a physical seam, no conveyor texture.'
 bpy.context.scene.frame_set(1)

def main():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.render.fps=24
 root=empty(ROOT);build(root);s.frame_end=round(PERIOD*24)+1;studio();s.frame_set(1)
 bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True);export(HERE/'exports/optimized.glb');render_views()
 # Actual full-geometry intermediate poses; no removal of steps or risers.
 for f,label in [(round(PERIOD*24*.25),'quarter'),(round(PERIOD*24*.5),'half'),(round(PERIOD*24*.75),'three-quarter')]:
  s.frame_set(f);s.camera.location=Vector(TARGET)+Vector((1.3,-2,1))*SCALE;aim(s.camera,TARGET);s.render.filepath=str(HERE/'previews'/(label+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
