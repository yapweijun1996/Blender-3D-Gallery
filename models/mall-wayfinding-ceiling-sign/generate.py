"""V2.1 P0 438. Original suspended double-sided North Walk sign, Blender 4.0.2.
Run -- --export-source to export the saved source without regeneration.
"""
from pathlib import Path
import math,sys
import bpy,bmesh
from mathutils import Vector, Matrix
HERE=Path(__file__).resolve().parent
ID='mall-wayfinding-ceiling-sign'
ROOT='ASSET_MallWayfindingCeilingSign'
GROUPS=['Housing','HangerLeft','HangerRight']+[s+t for s in ('Front','Rear') for t in ('Face','Text','Icons','Arrows')]
def material(name,rgb,metallic=0,roughness=.5):
 m=bpy.data.materials.new(name);m.use_nodes=True
 def linear(v):
  v/=255
  return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
 rgba=tuple(linear(v) for v in rgb)+(1,)
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=rgba;p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic;m.diffuse_color=rgba
 return m
def put(o,name,mat,group,bevel=0):
 o.name=name;o.data.materials.append(mat)
 if o.type=='MESH':o.data.use_auto_smooth=True
 if group:
  for c in list(o.users_collection):c.objects.unlink(o)
  bpy.data.collections[group].objects.link(o)
 if bevel:
  b=o.modifiers.new('Soft manufactured edge','BEVEL');b.width=bevel;b.segments=2
  o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
 return o
def box(name,loc,dims,mat,group,bevel=.002):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 return put(o,name,mat,group,bevel)
def cyl(name,loc,r,depth,mat,group):
 bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=depth,location=loc)
 return put(bpy.context.object,name,mat,group,.001)
def text(name,body,x,z,size,mat,group,align='LEFT'):
 c=bpy.data.curves.new(name,'FONT');c.body=body;c.size=size;c.align_x=align;c.extrude=.0006;c.resolution_u=3
 o=bpy.data.objects.new(name,c);bpy.data.collections[group].objects.link(o);o.location=(x,-.077,z);o.rotation_euler=(math.pi/2,0,0);c.materials.append(mat)
 return o
def arrow(name,direction,x,z,mat,group,scale=1):
 points=[(-.047,-.013),(.007,-.013),(.007,-.039),(.052,0),(.007,.039),(.007,.013),(-.047,.013)]
 a={'right':0,'left':math.pi,'up':math.pi/2,'down':-math.pi/2}[direction]
 coords=[(scale*(u*math.cos(a)-v*math.sin(a)),scale*(u*math.sin(a)+v*math.cos(a))) for u,v in points]
 vertices=[(x+u,y,z+v) for y in (-.077,-.080) for u,v in coords];n=len(coords)
 faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);put(o,name,mat,group)
 bpy.context.view_layer.objects.active=o;bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 return o
def icon(kind,x,z,mat,group):
 def b(s,dx,dz,w,h):return box(kind+s,(x+dx,-.079,z+dz),(w,.004,h),mat,group,.0008)
 if kind=='Shops':
  b('_bag',0,-.015,.072,.063);b('_handle_left',-.021,.031,.009,.03);b('_handle_right',.021,.031,.009,.03);b('_handle_top',0,.044,.047,.009)
 elif kind=='Food':
  b('_fork_stem',-.026,-.016,.010,.065);b('_fork_cross',-.026,.018,.038,.010)
  for q in (-.041,-.026,-.011):b('_fork_tine',q,.036,.009,.035)
  b('_spoon_stem',.025,-.02,.01,.060);b('_spoon_bowl',.025,.027,.032,.045)
 else:
  b('_lift_top',0,.047,.09,.008);b('_lift_left',-.041,0,.008,.09);b('_lift_right',.041,0,.008,.09);b('_lift_bottom',0,-.047,.09,.008);b('_door_seam',0,-.01,.004,.062)
  arrow('Lift icon up','up',x-.018,z+.013,mat,group,.28);arrow('Lift icon down','down',x+.018,z+.013,mat,group,.28)
def point_at(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
def evaluated_mesh(o,dg):
 # Blender FONT evaluation has coincident boundary vertices. Weld the evaluated
 # export copy, leaving the original FONT fully editable in the saved source.
 mesh=bpy.data.meshes.new_from_object(o.evaluated_get(dg),depsgraph=dg)
 bm=bmesh.new();bm.from_mesh(mesh)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-6)
 # Dissolve degenerate collinear cap diagonals emitted by bundled Bfont.
 bad=[f for f in bm.faces if f.calc_area()<1e-14]
 if bad:
  edges=list({max(f.edges,key=lambda e:e.calc_length()) for f in bad})
  bmesh.ops.dissolve_edges(bm,edges=edges,use_verts=False,use_face_split=False)
 bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='EAR_CLIP')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
 return mesh
def export_asset(path=None):
 scene=bpy.context.scene;root=bpy.data.objects.new(ROOT,None);scene.collection.objects.link(root);parts=[root];dg=bpy.context.evaluated_depsgraph_get()
 for name in GROUPS:
  copies=[]
  for orig in bpy.data.collections[name].objects:
   if orig.type not in ('MESH','FONT','CURVE'):continue
   mesh=evaluated_mesh(orig,dg);o=bpy.data.objects.new(orig.name+' export',mesh);scene.collection.objects.link(o);o.matrix_world=orig.matrix_world.copy();copies.append(o)
  bpy.ops.object.select_all(action='DESELECT')
  for o in copies:o.select_set(True)
  bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;o.parent=root;o['source_collection']=name;parts.append(o)
 for name,x in [('ANCHOR_CeilingLeft',-.7),('ANCHOR_CeilingRight',.7)]:
  o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.location=(x,0,0);o.parent=root;parts.append(o)
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=root
 bpy.ops.export_scene.gltf(filepath=str(path or HERE/'exports/optimized.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_texcoords=False,export_extras=True,export_cameras=False,export_lights=False)
 for o in reversed(parts):bpy.data.objects.remove(o,do_unlink=True)
def build():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
 root=bpy.data.collections.new(ROOT);s.collection.children.link(root);root['origin']='ceiling mount plane centre';root['front_axis']='-Y';root['units']='metres'
 for name in GROUPS:
  c=bpy.data.collections.new(name);root.children.link(c);c['replaceable']=True
 ink=material('Midnight blue powder coat',(24,44,61));ivory=material('Porcelain wayfinding white',(237,231,212));orange=material('Burnt orange accent',(213,101,47));metal=material('Satin aluminium',(156,172,181),.72,.32)
 box('Housing continuous core',(0,0,-.71),(2.10,.12,.46),ink,'Housing',.014)
 box('Top aluminium cap',(0,0,-.486),(2.08,.132,.018),metal,'Housing',.006)
 box('Bottom aluminium cap',(0,0,-.934),(2.08,.132,.012),metal,'Housing',.004)
 for x,g in [(-.7,'HangerLeft'),(.7,'HangerRight')]:
  box(g+' ceiling plate',(x,0,-.01),(.16,.12,.02),metal,g,.005)
  cyl(g+' drop rod',(x,0,-.257),.011,.478,metal,g)
  cyl(g+' upper collar',(x,0,-.037),.022,.035,ink,g)
  cyl(g+' lower collar',(x,0,-.468),.022,.035,ink,g)
  for dx in (-.055,.055):cyl(g+' fixing cap',(x+dx,0,-.022),.009,.008,ink,g)
 for side in ('Front','Rear'):
  box(side+' removable face',(0,-.066,-.71),(2.02,.016,.398),ink,side+'Face',.008)
  box(side+' orange locator',(0,-.076,-.616),(1.90,.003,.011),orange,side+'Face',.001)
  for x in (-.335,.335):box(side+' divider',(x,-.076,-.765),(.004,.003,.21),metal,side+'Face',.001)
  text(side+'_Zone','NORTH WALK',-.95,-.585,.067,ivory,side+'Text')
  text(side+'_Level','LEVEL 02',.95,-.585,.057,ivory,side+'Text','RIGHT')
  for i,(label,direction) in enumerate([('Shops','up'),('Food','left'),('Lifts','right')]):
   x=(-.67,0,.67)[i];direction=({'left':'right','right':'left'}.get(direction,direction) if side=='Rear' else direction)
   text(side+'_'+label+'_Label',label.upper(),x-.125,-.782,.096,ivory,side+'Text')
   icon(label,x-.237,-.75,ivory,side+'Icons')
   a=arrow(side+'_'+label+'_Arrow',direction,x+.257,-.75,ivory,side+'Arrows');a['direction']=direction
  if side=='Rear':
   # A proper 180-degree rotation, NEVER a negative scale or mirrored glyph.
   rot=Matrix.Rotation(math.pi,4,'Z')
   for suffix in ('Face','Text','Icons','Arrows'):
    for o in bpy.data.collections[side+suffix].objects:o.matrix_world=rot@o.matrix_world
 bpy.context.view_layer.update();export_asset()
 world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.30,.34,.38,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6;s.world=world
 for name,pos,power,size in [('Key',(1,-3,2),600,4),('Fill',(-3,-1,.5),350,3),('Rear',(1,3,1),500,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,(0,0,-.55))
 bpy.ops.object.camera_add(location=(1.3,-4,1));s.camera=bpy.context.object;s.camera.data.type='ORTHO';s.camera.data.ortho_scale=2.65;point_at(s.camera,(0,0,-.47))
 s.render.engine='BLENDER_EEVEE';s.eevee.use_gtao=True;s.eevee.gtao_distance=.3;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.look='AgX - Medium High Contrast'
 bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'),compress=True)
if __name__=='__main__':
 if '--export-source' in sys.argv:
  bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'));export_asset()
 else:build()
