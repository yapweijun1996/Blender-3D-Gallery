"""Original deterministic 1985 Saga heritage model; proportions approximate."""
import bpy,math,subprocess
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(n,c,metal=0,rough=.4,alpha=1):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,alpha);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*c,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;b.inputs['Alpha'].default_value=alpha
 if n in ['Satin black','Smoky glazing']:b.inputs['Specular IOR Level'].default_value=.12
 if alpha<1:m.surface_render_method='DITHERED';m.use_transparency_overlap=False
 return m
paint=mat('Silver metallic',(.48,.51,.53),.72,.26);black=mat('Satin black',(.004,.005,.006),0,.68);rubber=mat('Tire rubber',(.006,.007,.008),0,.9);glass=mat('Smoky glazing',(.018,.032,.045),0,.33,.68);steel=mat('Pressed steel',(.32,.35,.37),.85,.32);chrome=mat('Bright trim',(.62,.66,.69),.9,.19);head=mat('Headlamp glass',(.68,.76,.79),.25,.19);reflect=mat('Reflector',(.78,.8,.79),.9,.16);red=mat('Ruby lens',(.38,.008,.014),.18,.24);amber=mat('Amber lens',(.94,.23,.008),.18,.23);stripe=mat('Red coachline',(.56,.015,.022),.3,.3);fabric=mat('Charcoal cloth',(.07,.08,.085),0,.9);white=mat('Plate letters',(.8,.83,.81),.1,.4)
root=bpy.data.objects.new('ASSET_Proton_Saga_1985',None);bpy.context.collection.objects.link(root)
def box(n,loc,dims,m,b=.008):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=n;o.parent=root;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 if b:
  q=o.modifiers.new('Manufactured radii','BEVEL');q.width=b;q.segments=2;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def mesh(n,v,f,m,b=0):
 d=bpy.data.meshes.new(n);d.from_pydata(v,[],f);d.update();o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);o.parent=root;d.materials.append(m)
 if b:
  q=o.modifiers.new('Edge radii','BEVEL');q.width=b;q.segments=2;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def panel(n,v,m):return mesh(n,v,[tuple(range(len(v)))],m)
def line(n,pts,m,r=.004):
 d=bpy.data.curves.new(n,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=1;s=d.splines.new('POLY');s.points.add(len(pts)-1)
 for p,v in zip(s.points,pts):p.co=(*v,1)
 o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);o.parent=root;d.materials.append(m);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');return o
def cyl(n,loc,r,depth,m,verts=32,rot=(math.pi/2,0,0)):
 bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rot);o=bpy.context.object;o.name=n;o.parent=root;o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 q=o.modifiers.new('Rim edge','BEVEL');q.width=.004;q.segments=2;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
def torus(n,loc,major,minor,m,rot=(math.pi/2,0,0)):
 bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=10,location=loc,rotation=rot,major_radius=major,minor_radius=minor);o=bpy.context.object;o.name=n;o.parent=root;o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 return o
def text(n,body,loc,size,m,rot):
 d=bpy.data.curves.new(n,'FONT');d.body=body;d.align_x='CENTER';d.align_y='CENTER';d.size=size;d.extrude=.0005;o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);o.parent=root;o.location=loc;o.rotation_euler=rot;d.materials.append(m);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');return o
# Profiled lower body, front=-X. Actual dimensions remain approximate.
st=[(-2.08,.755,.875),(-1.88,.805,.93),(-.97,.815,1.005),(.98,.815,1.005),(1.9,.79,.97),(2.08,.755,.925)];v=[]
for x,w,z in st:v.extend([(x,-w*.94,.34),(x,-w,.78),(x,-w*.98,z),(x,w*.98,z),(x,w,.78),(x,w*.94,.34)])
f=[tuple(reversed(range(6)))]
for i in range(len(st)-1):
 for j in range(6):
  if not (i==2 and j==2):f.append((i*6+j,i*6+(j+1)%6,(i+1)*6+(j+1)%6,(i+1)*6+j))
f.append(tuple(range((len(st)-1)*6,len(st)*6)));body=mesh('Profiled pressed body',v,f,paint,.012)
for x in [-1.27,1.19]:
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.342,depth=2.2,location=(x,0,.32),rotation=(math.pi/2,0,0));cut=bpy.context.object;bpy.context.view_layer.objects.active=body;q=body.modifiers.new('Open wheel arch','BOOLEAN');q.object=cut;q.operation='DIFFERENCE';bpy.ops.object.modifier_apply(modifier=q.name);bpy.data.objects.remove(cut,do_unlink=True)
box('Roof panel',(.12,0,1.366),(1.23,1.245,.058),paint,.025)
for n,pts in [('Windscreen',[(-.98,-.729,1.006),(-.98,.729,1.006),(-.451,.599,1.343),(-.451,-.599,1.343)]),('Rear screen',[(1.095,.727,1.012),(1.095,-.727,1.012),(.714,-.595,1.343),(.714,.595,1.343)])]:panel(n,pts,glass);line(n+' seal',pts+[pts[0]],black,.012)
for s in [-1,1]:
 def yy(z):return s*(.755-(z-1.005)*.155/.36)
 for n,c in [('Front side glass',[(-.91,1.035),(-.421,1.328),(.045,1.328),(.045,1.035)]),('Rear side glass',[(.098,1.035),(.098,1.328),(.673,1.328),(1.018,1.035)])]:
  pts=[(x,yy(z),z) for x,z in c];panel(n,pts,glass);line(n+' seal',pts+[pts[0]],black,.018)
 line('A pillar',[(-1.003,s*.761,1.004),(-.474,s*.616,1.364)],paint,.026);line('C pillar',[(1.138,s*.765,1.006),(.742,s*.612,1.365)],paint,.042);line('B pillar',[(.071,s*.758,1.015),(.071,s*.611,1.353)],black,.019)
 line('Rain gutter',[(-.473,s*.632,1.37),(.738,s*.632,1.37)],chrome,.004);line('Window sill trim',[(-.98,s*.773,1.008),(1.13,s*.773,1.008)],chrome,.007)
 line('Front door seam',[(-.974,s*.791,.994),(-.83,s*.817,.78),(-.76,s*.795,.41),(.06,s*.795,.41),(.06,s*.817,.78),(.06,s*.79,.995)],black,.0025);line('Rear door seam',[(.06,s*.795,.41),(.84,s*.795,.41),(1.055,s*.817,.78),(1.075,s*.79,.994)],black,.0025)
 for x in [-.11,.87]:box('Handle recess',(x,s*.817,.927),(.125,.012,.047),black,.007);box('Lift handle',(x,s*.83,.94),(.103,.021,.025),black,.006)
 line('Side rubbing strip',[(-1.96,s*.811,.679),(1.97,s*.805,.679)],black,.018);line('Red side pinstripe',[(-1.96,s*.831,.688),(1.97,s*.825,.688)],stripe,.0038);line('Sill crease',[(-.85,s*.797,.388),(.88,s*.797,.388)],chrome,.004)
 box('Mirror pedestal',(-.86,s*.806,1.026),(.09,.08,.08),black,.009);box('Mirror housing',(-.83,s*.916,1.064),(.198,.13,.12),black,.022);box('Mirror glass',(-.725,s*.919,1.064),(.005,.101,.083),chrome,.005)
 for x in [-1.27,1.19]:
  torus('Rounded tire',(x,s*.727,.313),.248,.065,rubber);cyl('Tire sidewall',(x,s*.748,.313),.289,.15,rubber);cyl('Steel rim',(x,s*.835,.313),.212,.028,steel);torus('Rolled rim lip',(x,s*.853,.313),.199,.008,chrome);cyl('Pressed wheel center',(x,s*.86,.313),.153,.021,steel);cyl('Dished hubcap',(x,s*.878,.313),.113,.023,chrome)
  for a in range(12):
   t=a*math.tau/12;cyl('Wheel vent',(x+math.sin(t)*.171,s*.857,.313+math.cos(t)*.171),.018,.004,black,16)
  for a in range(4):
   t=a*math.tau/4;cyl('Wheel lug',(x+math.sin(t)*.075,s*.893,.313+math.cos(t)*.075),.01,.009,steel,12)
  for a in range(36):
   t=a*math.tau/36;o=box('Tread block',(x+math.sin(t)*.31,s*.727,.313+math.cos(t)*.31),(.012,.105,.004),black,.001);o.rotation_euler.y=t
box('Interior floor',(.12,0,.67),(1.95,1.32,.07),black);box('Dashboard',(-.77,0,.98),(.34,1.33,.13),black,.025)
for s in [-1,1]:
 box('Front cushion',(-.16,s*.36,.79),(.44,.46,.1),fabric,.04);o=box('Seat back',(.01,s*.36,1.005),(.11,.46,.43),fabric,.035);o.rotation_euler.y=-.12;box('Headrest',(.04,s*.36,1.245),(.12,.25,.13),fabric,.025)
box('Rear bench',(.73,0,.79),(.4,1.22,.13),fabric,.035);box('Rear seat back',(.91,0,1.01),(.12,1.22,.38),fabric,.035);box('Console',(-.3,0,.82),(.65,.15,.13),black,.02)
torus('Right hand drive steering',(-.63,.37,1.06),.12,.012,black,(0,math.pi/2,0));line('Steering column',[(-.68,.37,.98),(-.61,.37,1.06)],black,.025);line('Steering spoke',[(-.63,.255,1.06),(-.63,.485,1.06)],black,.009)
for x in [-2.09,2.09]:
 box('Wraparound bumper',(x,0,.525),(.17,1.69,.225),black,.025);line('Bumper red coachline',[(x+(-.09 if x<0 else .09),-.79,.616),(x+(-.09 if x<0 else .09),.79,.616)],stripe,.0045)
 for s in [-1,1]:box('Bumper return',(x+(.10 if x<0 else -.10),s*.805,.525),(.20,.045,.17),black,.018)
box('Front valance',(-1.99,0,.379),(.18,1.48,.13),black,.012)
for s in [-1,1]:
 box('Lower intake',(-2.091,s*.46,.397),(.008,.38,.065),rubber,.007);box('Headlamp surround',(-2.096,s*.555,.785),(.045,.365,.208),black,.009);box('Headlamp reflector',(-2.122,s*.542,.788),(.025,.271,.164),reflect,.012);box('Headlamp lens',(-2.14,s*.542,.788),(.009,.267,.156),head,.008)
 for j in range(9):box('Lens fluting',(-2.147,s*.542+(j-4)*.028,.788),(.003,.002,.142),chrome,.0005)
 box('Amber corner lamp',(-2.126,s*.745,.788),(.032,.095,.163),amber,.008);box('Rear lamp gasket',(2.086,s*.551,.783),(.025,.471,.221),black,.005)
 for z in [.735,.83]:box('Rear red lens',(2.107,s*.518,z),(.022,.272,.083),red,.004);box('Rear amber lens',(2.109,s*.721,z),(.025,.104,.083),amber,.004)
 box('Reverse lens',(2.123,s*.442,.83),(.008,.08,.064),head,.003)
 for z in [.713,.76,.81,.857]:line('Tail lens flute',[(2.126,s*.389,z),(2.126,s*.65,z)],red,.0015)
 line('Bonnet seam',[(-2.03,s*.65,.892),(-1.89,s*.714,.944),(-1.0,s*.743,1.016)],black,.0025);line('Wiper arm',[(-.96,s*.32,1.025),(-.88,s*.12,1.078)],black,.006);line('Wiper blade',[(-.90,s*.16,1.068),(-.77,s*.42,1.151)],black,.006)
line('Boot seam',[(1.11,-.7,1.016),(1.91,-.697,.978),(2.015,-.65,.947),(2.015,.65,.947),(1.91,.697,.978),(1.11,.7,1.016)],black,.0025);line('Fuel filler',[(1.58,.802,.876),(1.75,.799,.87),(1.75,.81,.735),(1.58,.813,.741),(1.58,.802,.876)],black,.0025)
box('Black grille',(-2.102,0,.785),(.035,.72,.19),black,.005)
for z in [.747,.8,.848]:box('Horizontal grille bar',(-2.146,0,z),(.012,.70,.01),chrome,.002)
mesh('Original shield badge',[(-2.157,-.035,.832),(-2.157,.035,.832),(-2.158,.027,.781),(-2.158,0,.757),(-2.158,-.027,.781)],[(0,1,2,3,4)],chrome)
for x in [-2.192,2.192]:
 box('Plate border',(x,0,.49),(.01,.47,.177),chrome,.006);box('Registration plate',(x+(-.007 if x<0 else .007),0,.49),(.01,.453,.16),black,.004);rot=(math.pi/2,0,-math.pi/2) if x<0 else (math.pi/2,0,math.pi/2);text('Display plate text','SAGA 1985',(x+(-.014 if x<0 else .014),0,.493),.056,white,rot)
text('Rear model lettering','SAGA',(2.105,.55,.938),.045,chrome,(math.pi/2,0,math.pi/2));cyl('Exhaust',(1.98,-.5,.287),.027,.27,steel,24,(0,math.pi/2,0));cyl('Exhaust opening',(2.121,-.5,.287),.021,.008,black,24,(0,math.pi/2,0));box('Underbody',(0,0,.30),(2.85,1.18,.10),black,.012);line('Antenna',[(.53,.12,1.398),(.73,.12,1.66)],black,.0028);cyl('Antenna base',(.53,.12,1.398),.018,.016,black,20,(0,0,0))
bpy.ops.object.select_all(action='DESELECT')
for o in root.children:o.select_set(True)
root.select_set(True);bpy.ops.export_scene.gltf(filepath=str(P/'exports/proton-saga-1985.glb'),export_format='GLB',use_selection=True,export_apply=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.engine='CYCLES';scene.cycles.samples=24;scene.world.color=(.18,.18,.18)
floor=box('STUDIO charcoal',(0,0,-.027),(200,200,.045),mat('Studio charcoal',(.025,.031,.038),.15,.32),0);floor.parent=None
for loc,power,size in [((-3,-4,6),1100,5),((1,4,5),1500,4),((4,-1,4),1200,3),((-5,1,2.5),500,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.65))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=5.5;scene.camera=cam;scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
views={'preview':(-6,-5.2,2.7),'view-front':(-30,0,3.22),'view-rear':(30,0,3.22),'view-left':(0,-30,3.22),'view-right':(0,30,3.22)}
for name,loc in views.items():
 cam.data.ortho_scale=3.1 if name in ['view-front','view-rear'] else 5.5;cam.data.clip_end=1000;cam.location=loc;cam.rotation_euler=(Vector((0,0,.78))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True);subprocess.run(['cwebp','-quiet','-q','90',str(P/(name+'.png')),'-o',str(P/(name+'.webp'))],check=True);(P/(name+'.png')).unlink()
cam.data.ortho_scale=5.5;cam.location=views['preview'];cam.rotation_euler=(Vector((0,0,.78))-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'scene.blend'));print('COMPLETE',bpy.app.version_string)
