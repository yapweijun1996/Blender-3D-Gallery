"""Original MRT Station Entrance, metres; no structural/load/code certification.
Normal generation replaces source; --export-source preserves source edits.
"""
from pathlib import Path
import bpy,sys,runpy,json,struct
from mathutils import Vector
HERE=Path(__file__).resolve().parent
# Reviewed original procedural helpers copied for a self-contained generator.
def material(name,rgb,roughness=.4,metallic=0,alpha=1):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def linear(v):
        v=v/255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    rgba=(*[linear(v) for v in rgb],alpha);m.diffuse_color=rgba
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=rgba;p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic;p.inputs['Alpha'].default_value=alpha
    if alpha<1:m.blend_method='BLEND';m.use_backface_culling=False;m.show_transparent_back=False
    return m
def box(name,loc,dims,mat,bevel=.001):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:
        b=o.modifiers.new('Editable eased edges','BEVEL');b.width=bevel;b.segments=2
    return o
def cylinder(name,loc,radius,depth,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);return o
def empty(name,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.location=loc;return o
def attach(o,parent):
    bpy.context.view_layer.update();matrix=o.matrix_world.copy();o.parent=parent;o.matrix_world=matrix;return o
def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def studio():
    s=bpy.context.scene
    floor=material('STUDIO floor only',(220,222,216),.95);box('STUDIO_Floor',(0,0,-.03),(2000,2000,.06),floor,0)
    target=(0,0,1.15)
    for name,loc,power,size in [('Key',(-3,-4,6),800,4),('Fill',(4,-2,3),500,4),('Rear',(1,4,5),900,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,target)
    bpy.ops.object.camera_add(location=(3,-6,3.1));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=3.3;point_at(s.camera,target)
    s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.25,.31,.32,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def export(root,destination):
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
    # Blender may emit identical material definitions for flat/bevelled meshes.
    # Collapse only exact duplicates; geometry, component nodes and BIN stay intact.
    data=destination.read_bytes();length=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+length]);unique=[];mapping={}
    for i,mat in enumerate(doc['materials']):
        if mat not in unique:unique.append(mat)
        mapping[i]=unique.index(mat)
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:primitive['material']=mapping[primitive['material']]
    doc['materials']=unique;chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*((-len(chunk))%4);tail=data[20+length:]
    destination.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)


def localbox(name,loc,dims,mat,parent,bevel=.0005):
    o=box(name,loc,dims,mat,bevel);o.parent=parent;return o
def digit(value,x,z,height,mat,parent,prefix):
    patterns={'0':'ab cdef'.replace(' ',''),'1':'bc','2':'abged','3':'abgcd','4':'fgbc','5':'afgcd','6':'afgecd','7':'abc','8':'abcdefg','9':'abfgcd'}
    w=height*.52;t=height*.09
    coords={'a':(0,height/2,w,t),'g':(0,0,w,t),'d':(0,-height/2,w,t),'f':(-w/2,height/4,t,height/2-t),'b':(w/2,height/4,t,height/2-t),'e':(-w/2,-height/4,t,height/2-t),'c':(w/2,-height/4,t,height/2-t)}
    for key in patterns[value]:
        xx,zz,ww,hh=coords[key];localbox(prefix+'_'+key,(x+xx,-.009,z+zz),(ww,.0015,hh),mat,parent,min(.0006,t/5))
def beam(name,a,b,r,mat,parent):
    a,b=Vector(a),Vector(b);o=cylinder(name,(a+b)/2,r,(b-a).length,mat);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();attach(o,parent)


def B(n,p,d,m,parent=None):return attach(box(n,p,d,m,.002),parent or root)
def C(n,p,r,d,m,parent=None):return attach(cylinder(n,p,r,d,m),parent or root)
def P(n,loc=(0,0,0)):return empty(n,root,loc)
def frame(n,z,w,h,m):
 for s in [-1,1]:B(n+'_Stile',(s*w/2,0,z),(.055,.07,h),m)
 for s in [-1,1]:B(n+'_Rail',(0,0,z+s*h/2),(w,.07,.055),m)
def mesh(n,v,f,m):
 import bmesh
 data=bpy.data.meshes.new(n);data.from_pydata(v,[],f);data.update()
 bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
 o=bpy.data.objects.new(n,data);bpy.context.scene.collection.objects.link(o);o.data.materials.append(m);attach(o,root);return o

SLUG='mrt-station-entrance';ROOT='ASSET_MRTStationEntrance'
def build():

 global root
 root=empty(ROOT)
 steel=material('Satin steel',(135,151,153),.4,.65);concrete=material('Warm concrete',(166,163,151),.85)
 wood=material('Tropical timber',(119,72,40),.68);brass=material('Brass fittings',(175,135,65),.4,.6)
 dark=material('Dark rubber',(38,46,48),.8);white=material('Warm white',(225,225,210),.4)
 terra=material('Terracotta',(174,80,49),.75);blue=material('Muted teal',(40,93,103),.5);stone=material('Rural stone',(120,118,106),.95)

 # Generic above-ground station approach canopy; no official network logo.
 B('Landing',(0,0,.65),(4.8,4,1.3),concrete)
 for x in [-2,2]:
  for y in [-1.5,1.5]:B('Canopy_Column',(x,y,2.8),(.16,.16,3.2),steel)
 B('Canopy_Roof',(0,0,4.45),(4.6,3.8,.16),white)
 B('Entry_Fascia',(0,-1.84,4.22),(4.5,.12,.38),blue)
 B('Replaceable_Station_Label',(0,-1.91,4.23),(2.1,.01,.16),white)
 for x in [-1.7,1.7]:
  for y in [-1.4,0,1.4]:B('Rail_Post',(x,y,1.80),(.04,.04,1),steel)
  beam('Handrail',(x,-1.5,2.3),(x,1.5,2.3),.035,steel,root)
  B('Infill',(x,0,1.85),(.025,3,.7),blue)
 for i in range(6):B('Step_'+str(i),(0,-2.15-i*.3,(1.2-i*.2)/2),(3.2,.3,1.2-i*.2),concrete)

 root['units']='metres';root['backlog_id']=341
 # Normalize base contact to zero without flattening component hierarchy.
 bpy.context.view_layer.update()
 pts=[o.matrix_world@Vector(v) for o in root.children_recursive if o.type=='MESH' for v in o.bound_box]
 low=min(v.z for v in pts)
 for o in root.children:o.location.z-=low
 return root
def main():
 if '--export-source' in sys.argv:
  bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
  root=build();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
