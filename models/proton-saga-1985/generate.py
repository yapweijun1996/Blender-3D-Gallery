"""Original procedural simplified 1985 Proton Saga exterior study."""
import bpy,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(n,c,metal=0,rough=.4):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*c,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough;return m
paint=mat('Heritage crimson',(.42,.025,.035),.45,.29);black=mat('Rubber',(.018,.022,.027),0,.65);glass=mat('Blue glazing',(.035,.085,.12),.45,.19);silver=mat('Wheel alloy',(.55,.59,.62),.8,.3);chrome=mat('Polished trim',(.7,.74,.76),.9,.2);head=mat('Headlamps',(.8,.85,.77),.2,.23);red=mat('Red lamps',(.5,.012,.015),.15,.24);amber=mat('Indicators',(.95,.29,.015),.1,.25)
root=bpy.data.objects.new('ASSET_Proton_Saga_1985',None);bpy.context.collection.objects.link(root)
def box(n,loc,dims,m,b=.012):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=n;o.data.materials.append(m);o.parent=root;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if b:
  mod=o.modifiers.new('Rounded edges','BEVEL');mod.width=b;mod.segments=3;o.modifiers.new('Normals','WEIGHTED_NORMAL')
 return o
def mesh(n,v,f,m):
 d=bpy.data.meshes.new(n);d.from_pydata(v,[],f);d.update();o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);o.parent=root;d.materials.append(m);return o
def panel(n,v,m):return mesh(n,v,[tuple(range(len(v)))],m)
def line(n,pts,m,r=.005):
 d=bpy.data.curves.new(n,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=2;s=d.splines.new('POLY');s.points.add(len(pts)-1)
 for p,v in zip(s.points,pts):p.co=(*v,1)
 o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);o.parent=root;d.materials.append(m);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');return o
def cyl(n,loc,r,depth,m):
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=depth,location=loc,rotation=(math.pi/2,0,0));o=bpy.context.object;o.name=n;o.parent=root;o.data.materials.append(m)
 for p in o.data.polygons:p.use_smooth=True
 mod=o.modifiers.new('Rounded rim','BEVEL');mod.width=.009;mod.segments=3;o.modifiers.new('Normals','WEIGHTED_NORMAL');return o
# Front toward -X. Approximate meter-scale proportions, not a measured replica.
body=box('Steel body',(0,0,.70),(4.22,1.62,.72),paint,.05)
for x in [-1.26,1.20]:
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.365,depth=2.1,location=(x,0,.34),rotation=(math.pi/2,0,0));cut=bpy.context.object;bpy.context.view_layer.objects.active=body;mod=body.modifiers.new('Wheel opening','BOOLEAN');mod.object=cut;mod.operation='DIFFERENCE';bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
v=[(-.95,-.77,1.035),(-.95,.77,1.035),(.99,.77,1.035),(.99,-.77,1.035),(-.43,-.625,1.43),(-.43,.625,1.43),(.55,.625,1.43),(.55,-.625,1.43)]
mesh('Cabin',v,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],paint)
panel('Windshield',[(-.941,-.714,1.069),(-.941,.714,1.069),(-.445,.591,1.405),(-.445,-.591,1.405)],glass)
panel('Rear glass',[(.978,.708,1.07),(.978,-.708,1.07),(.566,-.588,1.402),(.566,.588,1.402)],glass)
for s in [-1,1]:
 def y(z):return s*(.77-(z-1.035)*(.145/.395)+.005)
 for n,c in [('Front glass',[(-.875,1.075),(-.417,1.399),(-.025,1.399),(-.025,1.075)]),('Rear glass',[(.035,1.075),(.035,1.399),(.523,1.399),(.925,1.075)])]:
  pts=[(x,y(z),z) for x,z in c];panel(n,pts,glass);line('Gasket',pts+[pts[0]],black,.009)
 line('Beltline',[(-.95,s*.799,1.035),(.99,s*.799,1.035)],chrome,.009)
 line('Door split',[(.005,s*.818,1.03),(.005,s*.821,.48)],black,.003)
 line('Front door seam',[(-.94,s*.816,1.02),(-.86,s*.823,.84),(-.78,s*.823,.48),(0,s*.823,.48)],black,.003)
 line('Rear door seam',[(.01,s*.823,.48),(.81,s*.823,.48),(.97,s*.817,.84),(.97,s*.807,1.02)],black,.003)
 box('Protection strip',(.05,s*.824,.65),(2,.022,.035),black,.004)
 for x in [-.16,.75]:
  box('Handle recess',(x,s*.825,.96),(.145,.014,.045),black,.009);box('Handle',(x,s*.839,.974),(.11,.02,.016),chrome,.005)
 box('Mirror stalk',(-.74,s*.857,1.075),(.065,.16,.045),black);box('Mirror housing',(-.72,s*.95,1.115),(.19,.13,.115),black,.025);box('Mirror lens',(-.617,s*.951,1.12),(.006,.104,.076),silver,.004)
 for x in [-1.26,1.20]:
  cyl('Tire',(x,s*.743,.335),.313,.20,black);cyl('Wheel rim',(x,s*.851,.335),.225,.025,silver);cyl('Hubcap',(x,s*.872,.335),.122,.02,chrome)
  for a in range(8):
   t=a*math.tau/8;cyl('Wheel vent',(x+math.sin(t)*.169,s*.87,.335+math.cos(t)*.169),.025,.008,black)
  for a in range(4):
   t=a*math.tau/4;cyl('Lug',(x+math.sin(t)*.073,s*.89,.335+math.cos(t)*.073),.012,.01,black)
for x in [-2.12,2.12]:box('Bumper',(x,0,.49),(.13,1.69,.16),black,.035)
box('Grille',(-2.119,0,.859),(.026,.83,.23),black)
for z in [.81,.907]:box('Twin grille bar',(-2.14,0,z),(.025,.78,.022),chrome,.003)
for s in [-1,1]:
 box('Lamp bezel',(-2.112,s*.592,.862),(.045,.353,.237),black);box('Rectangular headlight',(-2.14,s*.56,.869),(.025,.26,.184),head,.007);box('Front indicator',(-2.139,s*.736,.869),(.026,.076,.184),amber,.005)
 for j in range(5):box('Lamp prism',(-2.156,s*.56+(j-2)*.044,.869),(.004,.003,.16),silver,.001)
 box('Rear bezel',(2.116,s*.579,.852),(.035,.42,.22),black);box('Rear red lamp',(2.14,s*.52,.85),(.025,.268,.17),red,.005);box('Rear indicator',(2.14,s*.706,.85),(.025,.093,.17),amber,.005);box('Reverse lamp',(2.157,s*.438,.85),(.008,.08,.082),head,.003)
 line('Hood seam',[(-2.06,s*.66,1.065),(-1,s*.71,1.065)],black,.003);line('Wiper',[(-.91,s*.32,1.09),(-.74,s*.12,1.205)],black,.007)
line('Trunk seam',[(1.04,-.7,1.065),(1.94,-.7,1.065),(1.94,.7,1.065),(1.04,.7,1.065)],black,.003)
box('Underfloor',(0,0,.33),(2.7,1.23,.09),black)
for x in [-2.198,2.198]:box('Plate',(x,0,.48),(.012,.42,.105),black,.004)
bpy.ops.object.select_all(action='DESELECT')
for o in root.children:o.select_set(True)
root.select_set(True);bpy.ops.export_scene.gltf(filepath=str(P/'exports/proton-saga-1985.glb'),export_format='GLB',use_selection=True,export_apply=True)
floor=box('Studio',(0,0,-.045),(200,200,.06),mat('Slate',(.075,.09,.105)),0);floor.parent=None
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.engine='CYCLES';scene.cycles.samples=32;scene.world.color=(.3,.3,.3)
for loc,power,size in [((-3,-4,7),1700,5),((2,4,5),2200,4),((4,-1,3),1000,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(Vector((0,0,.5))-l.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(-6.2,-5.7,3.5));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.69))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=5.65;scene.camera=cam
scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(P/'preview.png')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'scene.blend'));bpy.ops.render.render(write_still=True);print('COMPLETE',bpy.app.version_string)
