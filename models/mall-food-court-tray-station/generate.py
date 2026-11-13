"""V2.1 P0 item 439: original metric tray-return cabinet, Blender 4.0.2.
Self-contained generator. --export-source re-exports the saved source without regeneration.
"""
from pathlib import Path
import math,sys
import bpy,bmesh
from mathutils import Vector
HERE=Path(__file__).resolve().parent
ID='mall-food-court-tray-station'
ROOT='ASSET_MallFoodCourtTrayStation'
GROUPS=['CabinetLeft','CabinetRight','CabinetBack','LowerShelf','UpperShelf','Counter','Feet','SignFrame','SignText','Tray01','Tray02','Tray03','Tray04']
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

def label(name,body,z,size,mat):
 c=bpy.data.curves.new(name,'FONT');c.body=body;c.size=size;c.align_x='CENTER';c.extrude=.0007;c.resolution_u=3;c.offset=.00005  # Avoid bundled Bfont A contour touching at a single edge.
 o=bpy.data.objects.new(name,c);bpy.data.collections['SignText'].objects.link(o);o.location=(0,-.028,z);o.rotation_euler=(math.pi/2,0,0);c.materials.append(mat)
 return o
def tray(name,x,y,z,mat):
 # One closed concave vessel mesh: bottom slab, sloped interior and a flat rim.
 # Bounds .45 x .33 x .03 m, internal floor .402 x .282 m at 6 mm.
 loops=[(.225,.165,0),(.225,.165,.030),(.214,.154,.030),(.201,.141,.006)]
 verts=[(x+u,y+v,z+h) for w,d,h in loops for u,v in [(-w,-d),(w,-d),(w,d),(-w,d)]]
 faces=[(3,2,1,0),(12,13,14,15)]
 for k in range(3):
  for i in range(4):faces.append((k*4+i,k*4+(i+1)%4,(k+1)*4+(i+1)%4,(k+1)*4+i))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);put(o,name+' vessel',mat,name,.001)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 return o
def build():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
 root=bpy.data.collections.new(ROOT);s.collection.children.link(root);root['origin']='floor centre';root['front_axis']='-Y';root['units']='metres';root['scope']='Static illustrative tray return station, not a hygiene or safety certified product'
 for name in GROUPS:
  c=bpy.data.collections.new(name);root.children.link(c);c['replaceable']=True
 teal=material('Teal powder coat',(33,91,96),.12,.45);metal=material('Brushed stainless steel',(169,180,181),.68,.36);rubber=material('Dark levelling feet',(37,43,45),0,.8);ivory=material('Warm white lettering',(246,241,221),0,.5)
 for x,g in [(-.695,'CabinetLeft'),(.695,'CabinetRight')]:
  box(g+' panel',(x,.01,.505),(.03,.60,.81),teal,g,.006)
 box('CabinetBack panel',(0,.295,.505),(1.36,.03,.81),teal,'CabinetBack',.004)
 box('LowerShelf panel',(0,.005,.205),(1.36,.55,.03),metal,'LowerShelf',.003)
 box('UpperShelf panel',(0,.005,.565),(1.36,.55,.03),metal,'UpperShelf',.003)
 # 0.33 m clear between shelves; 0.33 m between upper shelf and counter underside.
 box('Counter panel',(0,0,.93),(1.50,.66,.04),metal,'Counter',.008)
 for x in (-.61,.61):
  for y in (-.21,.22):
   cyl('Foot stem',(x,y,.075),.025,.10,metal,'Feet');cyl('Foot pad',(x,y,.014),.037,.028,rubber,'Feet')
 # Header is a discrete above-counter sign, not a waste drop aperture.
 for x in (-.59,.59):box('Header upright',(x,.04,1.21),(.025,.035,.55),metal,'SignFrame',.003)
 box('Tray return header',(0,0,1.35),(1.30,.05,.28),teal,'SignFrame',.012)
 label('ReturnLabel','TRAY RETURN',1.345,.135,ivory)
 label('ThanksLabel','Thank you',1.255,.055,ivory)
 for i,(x,y,z) in enumerate([(-.34,-.005,.223),(-.34,-.005,.258),(-.34,-.005,.293),(.34,-.005,.583)],1):
  mat=material('Tray %02d warm terracotta'%i,(184,103,69),0,.48);tray('Tray%02d'%i,x,y,z,mat)
 bpy.context.view_layer.update();export_asset()
 world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.30,.34,.38,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6;s.world=world
 for name,pos,power,size in [('Key',(1,-3,4),650,4),('Fill',(-3,-1,2),420,3),('Rear',(1,3,3),650,3)]:
  bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,(0,0,.7))
 bpy.ops.object.camera_add(location=(2,-4,2.5));s.camera=bpy.context.object;s.camera.data.type='ORTHO';s.camera.data.ortho_scale=2.2;point_at(s.camera,(0,0,.76))
 s.render.engine='BLENDER_EEVEE';s.eevee.use_gtao=True;s.eevee.gtao_distance=.25;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.look='AgX - Medium High Contrast'
 bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'),compress=True)
if __name__=='__main__':
 if '--export-source' in sys.argv:
  bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{ID}.blend'));export_asset()
 else:build()
