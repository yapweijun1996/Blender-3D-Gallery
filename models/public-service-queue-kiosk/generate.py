"""Original visual mall column, metres; no structural/load/code certification.
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
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=True,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
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

def ring(n,outer,inner,z0,z1,m):
 import math
 v=[]
 for z in [z0,z1]:
  for r in [outer,inner]:
   for k in range(32):v.append((r*math.cos(k*math.tau/32),r*math.sin(k*math.tau/32),z))
 f=[]
 for k in range(32):
  j=(k+1)%32;f.extend([(k,j,64+j,64+k),(32+k,96+k,96+j,32+j),(64+k,64+j,96+j,96+k),(k,32+k,32+j,j)])
 return mesh(n,v,f,m)
def counter(w,d,h,body,top):
 B('Counter_Base',(0,0,.055),(w-.10,d-.1,.11),dark)
 B('Counter_Body',(0,0,h/2),(w-.04,d-.04,h-.08),body)
 B('Worktop',(0,0,h-.025),(w,d,.05),top)
def terminal(x,y,z,case,screen):
 B('Terminal_Foot',(x,y,z+.015),(.27,.19,.03),case)
 B('Terminal_Stem',(x,y,z+.13),(.04,.04,.23),case)
 B('Screen_Housing',(x,y,z+.26),(.34,.055,.22),case)
 B('Screen',(x,y-.032,z+.26),(.29,.012,.17),screen)
def kiosk(w,d,h,body,trim,screen):
 B('Foot',(0,0,.03),(w,d,.06),trim)
 B('Pedestal',(0,.04,.52),(w*.65,d*.7,.98),body)
 B('Head',(0,0,h-.25),(w-.05,d,.5),trim)
 B('Display',(0,-d/2-.006,h-.20),(w-.13,.012,.28),screen)
 for i in range(3):B('Interface_Line',(0,-d/2-.014,h-.15-i*.08),(w*.50,.004,.018),white)

SLUG='public-service-queue-kiosk';ROOT='ASSET_PublicServiceQueueKiosk'
def build():

 global root,dark,white
 root=empty(ROOT)
 steel=material('Satin steel',(135,151,153),.4,.65);concrete=material('Warm concrete',(166,163,151),.85)
 wood=material('Tropical timber',(119,72,40),.68);brass=material('Brass fittings',(175,135,65),.4,.6)
 dark=material('Dark rubber',(38,46,48),.8);white=material('Warm white',(225,225,210),.4)
 terra=material('Terracotta',(174,80,49),.75);blue=material('Muted teal',(40,93,103),.5);stone=material('Rural stone',(120,118,106),.95)

 glass=material('Frosted blue glazing',(151,193,197),.24,.05,.58)

 kiosk(.65,.50,1.55,white,blue,dark)
 B('Speaker',(.21,-.258,1.13),(.12,.016,.045),steel)
 B('Ticket_Slot',(0,-.262,1.10),(.20,.02,.025),dark)
 ticket=P('MOVABLE_Ticket',(0,-.28,1.10));localbox('Paper',(0,0,0),(.16,.08,.003),white,ticket)
 B('Wheelchair_Clearance_Marker',(0,-.143,.38),(.15,.015,.15),blue)


 bpy.ops.object.text_add(location=(0,-0.256,1.51),rotation=(1.5707963267948966,0,0));o=bpy.context.object;o.name='Editable_Label_QUEUE'
 o.data.body='QUEUE';o.data.align_x='CENTER';o.data.align_y='CENTER';o.data.size=0.05;o.data.extrude=.0005;o.data.materials.append(dark);bpy.ops.object.convert(target='MESH');attach(bpy.context.object,root)
 root['units']='metres';root['backlog_id']=447
 return root
def animate():
 s=bpy.context.scene;s.render.fps=24;s.frame_start=1;s.frame_end=49
 for name,prop,axis,delta in [('MOVABLE_Ticket', 'location', 1, -0.16)]:
  o=bpy.data.objects[name];initial=list(getattr(o,prop))
  for frame,amount in [(1,0),(25,1),(49,0)]:
   value=initial.copy();value[axis]+=delta*amount;setattr(o,prop,value);o.keyframe_insert(data_path=prop,frame=frame)
  o.animation_data.action.name='Demonstrate_'+name
  for fc in o.animation_data.action.fcurves:
   for key in fc.keyframe_points:key.interpolation='LINEAR'
 s.frame_set(1)
def main():
 if '--export-source' in sys.argv:
  bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
  root=build();animate();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
