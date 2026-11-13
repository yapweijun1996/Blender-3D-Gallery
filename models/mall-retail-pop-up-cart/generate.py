"""V2.1 P0 item 440: original metric mobile retail cart, Blender 4.0.2.
Self-contained generator. --export-source re-exports the saved source without regeneration.
"""
from pathlib import Path
import math,sys
import bpy,bmesh
from mathutils import Vector
HERE=Path(__file__).resolve().parent
ID='mall-retail-pop-up-cart'
ROOT='ASSET_MallRetailPopUpCart'
GROUPS=['Frame','FrontPanel','SidePanels','Counter','Shelf','WheelFL','WheelFR','WheelRL','WheelRR','CanopyPosts','Canopy','SignPanel','SignText']
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
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=root
 bpy.ops.export_scene.gltf(filepath=str(path or HERE/'exports/optimized.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_texcoords=False,export_extras=True,export_cameras=False,export_lights=False)
 for o in reversed(parts):bpy.data.objects.remove(o,do_unlink=True)

def build():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
 root=bpy.data.collections.new(ROOT);s.collection.children.link(root);root['origin']='floor centre';root['front_axis']='-Y';root['units']='metres'
 for name in GROUPS:
  c=bpy.data.collections.new(name);root.children.link(c);c['replaceable']=True
 teal=material('Jade enamel',(31,100,95),.1,.42);wood=material('Honey timber',(176,127,75),0,.48);metal=material('Champagne metal',(181,156,102),.65,.36);rubber=material('Caster rubber',(39,44,48),0,.78);ivory=material('Warm canvas',(239,226,201),0,.8)
 # Four distinct caster modules. Cylinder axle runs X, tyre touches ground.
 for x,side in [(-.59,'L'),(.59,'R')]:
  for y,end in [(-.24,'F'),(.24,'R')]:
   g='Wheel'+end+side
   o=cyl('Rubber wheel',(x,y,.075),.075,.045,rubber,g);o.rotation_euler[1]=math.pi/2
   o=cyl('Wheel hub',(x,y,.075),.027,.052,metal,g);o.rotation_euler[1]=math.pi/2
   for dx in (-.035,.035):box('Caster fork',(x+dx,y,.12),(.012,.045,.105),metal,g)
   cyl('Swivel stem',(x,y,.175),.018,.045,metal,g)
 box('Base plinth',(0,0,.21),(1.34,.64,.06),teal,'Frame',.006)
 for x in (-.64,.64):
  for y in (-.29,.29):box('Counter frame',(x,y,.565),(.035,.035,.65),metal,'Frame')
 box('Front fascia',(0,-.305,.565),(1.25,.025,.65),teal,'FrontPanel',.005)
 for x in (-.635,.635):box('Side fascia',(x,0,.565),(.025,.58,.65),teal,'SidePanels',.005)
 # Rear stays open to reveal the shelf and replaceable stock area.
 box('Storage shelf',(0,.01,.48),(1.24,.56,.026),wood,'Shelf',.004)
 box('Countertop',(0,0,.92),(1.5,.78,.05),wood,'Counter',.012)
 for x in (-.68,.68):
  for y in (-.28,.28):box('Canopy post',(x,y,1.45),(.03,.03,1.05),metal,'CanopyPosts',.003)
 # Slightly pitched fabric panels, independent from four frame posts.
 for y,ang in [(-.225,.09),(.225,-.09)]:
  o=box('Canvas canopy',(0,y,2.015),(1.65,.46,.025),ivory,'Canopy',.004);o.rotation_euler[0]=ang
 box('Front valance',(0,-.455,1.95),(1.65,.022,.13),teal,'Canopy',.003)
 box('Rear valance',(0,.455,1.95),(1.65,.022,.13),teal,'Canopy',.003)
 box('Replaceable sign',(0,-.326,.635),(.88,.026,.23),ivory,'SignPanel',.014)
 c=bpy.data.curves.new('Editable pop-up name','FONT');c.body='LOCAL FINDS';c.size=.12;c.align_x='CENTER';c.extrude=.0007;c.resolution_u=3;c.offset=.00005
 o=bpy.data.objects.new('ShopLabel',c);bpy.data.collections['SignText'].objects.link(o);o.location=(0,-.341,.60);o.rotation_euler=(math.pi/2,0,0);c.materials.append(teal)
 bpy.context.view_layer.update();export_asset()
 world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.30,.34,.38,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6;s.world=world
 for name,pos,power,size in [('Key',(1,-3,4),650,4),('Fill',(-3,-1,2),420,3),('Rear',(1,3,3),650,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,(0,0,1))
 bpy.ops.object.camera_add(location=(3,-5,3));s.camera=bpy.context.object;s.camera.data.type='ORTHO';s.camera.data.ortho_scale=2.8;point_at(s.camera,(0,0,1.02))
 s.render.engine='BLENDER_EEVEE';s.eevee.use_gtao=True;s.eevee.gtao_distance=.25;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.look='AgX - Medium High Contrast'
 bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'),compress=True)
if __name__=='__main__':
 if '--export-source' in sys.argv:
  bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'));export_asset()
 else:build()
