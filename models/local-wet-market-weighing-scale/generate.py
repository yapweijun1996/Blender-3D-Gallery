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
 B('Display',(0,-d/2-.006,h-.24),(w-.13,.012,.32),screen)
 for i in range(3):B('Interface_Line',(0,-d/2-.014,h-.15-i*.08),(w*.50,.004,.018),white)


import math
from mathutils.geometry import tessellate_polygon
def sphere(n,p,d,m):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=p);o=bpy.context.object;o.name=n;o.scale=d;o.data.materials.append(m);attach(o,root);return o
def cone(n,p,v,r,h,m):
 v=Vector(v).normalized();bpy.ops.mesh.primitive_cone_add(vertices=8,radius1=r,radius2=0,depth=h,location=Vector(p)+v*h/2);o=bpy.context.object;o.name=n;o.rotation_euler=v.to_track_quat('Z','Y').to_euler();o.data.materials.append(m);attach(o,root);return o
def flame(n,p,r,h,m):
 return mesh(n,[(p[0]+r*math.cos(i*math.tau/8),p[1]+r*math.sin(i*math.tau/8),p[2]+h*.3) for i in range(8)]+[(p[0],p[1],p[2]),(p[0]+r*.15,p[1],p[2]+h)],[(i,(i+1)%8,9) for i in range(8)]+[(i,8,(i+1)%8) for i in range(8)],m)
def ring(n,outer,inner,z0,z1,m,scale_y=1):
 v=[(r*math.cos(k*math.tau/32),scale_y*r*math.sin(k*math.tau/32),z) for z in [z0,z1] for r in [outer,inner] for k in range(32)];f=[]
 for k in range(32):
  j=(k+1)%32;f.extend([(k,j,64+j,64+k),(32+k,96+k,96+j,32+j),(64+k,64+j,96+j,96+k),(k,32+k,32+j,j)])
 return mesh(n,v,f,m)
def prism(n,points,a,b,m,horizontal=False):
 vec=[Vector((x,y,0)) for x,y in points];tri=tessellate_polygon([vec]);indices={tuple(v):i for i,v in enumerate(vec)};faces=[tuple(v if isinstance(v,int) else indices[tuple(v)] for v in t) for t in tri];N=len(points)
 verts=[(x,y,z) if horizontal else (x,z,y) for z in [a,b] for x,y in points]
 faces=faces+[tuple(i+N for i in t[::-1]) for t in faces]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
 return mesh(n,verts,faces,m)
def star(n,p,R,r,points,m):
 shape=[(p[0]+(R if i%2==0 else r)*math.cos(math.pi/2-i*math.pi/points),p[1]+(R if i%2==0 else r)*math.sin(math.pi/2-i*math.pi/points)) for i in range(points*2)]
 for side,a,b in [('Front',-.006,-.004),('Back',.004,.006)]:o=prism(n+'_'+side,shape,a,b,m);o['points']=points
 def_unused=0

def crescent(n,p,R,r,d,m):
 x=(R*R-r*r+d*d)/(2*d);z=math.sqrt(R*R-x*x);theta=math.atan2(z,x);phi=math.atan2(z,x-d)
 shape=[(p[0]+R*math.cos(theta+(math.tau-2*theta)*i/48),p[1]+R*math.sin(theta+(math.tau-2*theta)*i/48)) for i in range(49)]
 shape += [(p[0]+d+r*math.cos(-phi-(math.tau-2*phi)*i/48),p[1]+r*math.sin(-phi-(math.tau-2*phi)*i/48)) for i in range(1,48)]
 for side,a,b in [('Front',-.006,-.004),('Back',.004,.006)]:prism(n+'_'+side,shape,a,b,m)
def flag_background(w,h,bands):
 for i,(m,lo,hi) in enumerate(bands):attach(box('Flag_Band_'+str(i),(0,0,(lo+hi)/2),(w,.004,hi-lo),m,0),root)
def flag_mount(w):
 o=C('Mount_Rail',(0,0,1.08),.012,w+.1,steel);o.rotation_euler[1]=math.pi/2
 for x in [-w/2+.05,w/2-.05]:B('Suspension_Tab',(x,0,1.035),(.025,.06,.07),steel)
def label(word,p,size,m):
 bpy.ops.object.text_add(location=p,rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='Editable_Label_'+word.replace(' ','_');o.data.body=word;o.data.align_x='CENTER';o.data.align_y='CENTER';o.data.size=size;o.data.extrude=.0005;o.data.materials.append(m);bpy.ops.object.convert(target='MESH');attach(bpy.context.object,root)
def canopy(n,w,d,z,peak,m):
 o=mesh(n,[(-w,-d,z),(w,-d,z),(w,d,z),(-w,d,z),(0,0,peak)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(0,3,2,1)],m);return o
def lantern(n,p,r,h,m):
 sphere(n+'_Body',p,(r,r,h),m)
 for j in range(8):
  a=j*math.tau/8
  pts=[(p[0]+r*1.012*math.sin(math.pi*k/8)*math.cos(a),p[1]+r*1.012*math.sin(math.pi*k/8)*math.sin(a),p[2]+h*math.cos(math.pi*k/8)) for k in range(1,8)]
  for k in range(6):beam(n+'_Rib',pts[k],pts[k+1],.006,gold,root)
 for z in [p[2]-h,p[2]+h]:C(n+'_Cap',(p[0],p[1],z),.07,.025,gold)

SLUG='local-wet-market-weighing-scale';ROOT='ASSET_LocalWetMarketWeighingScale'
def build():

 global root,dark,white,gold,steel
 root=empty(ROOT)
 steel=material('Satin metal',(150,163,169),.48,.35);concrete=material('Warm concrete',(168,164,151),.85)
 wood=material('Tropical timber',(128,81,47),.68);gold=material('Warm yellow',(255,204,0),.5,.08)
 dark=material('Charcoal',(38,46,48),.8);white=material('White',(255,255,255),.6)
 terra=material('Terracotta',(174,80,49),.75);blue=material('Muted teal',(40,93,103),.6);green=material('Palm green',(61,113,54),.7)
 red=material('Festive red',(204,0,1),.65);pink=material('Festive magenta',(179,44,105),.6);orange=material('Marigold',(235,143,25),.6);navy=material('Flag navy',(1,0,102),.7)

 B('Base',(0,0,.035),(.32,.28,.07),green);B('Housing',(0,.015,.165),(.23,.23,.26),green)
 o=C('Dial',(0,-.112,.25),.115,.015,white);o.rotation_euler[0]=math.pi/2
 for i in range(13):
  a=-math.pi*.75+i*math.pi*1.5/12;beam('Dial_Tick',(.088*math.sin(a),-.1215,.25+.088*math.cos(a)),(.102*math.sin(a),-.1215,.25+.102*math.cos(a)),.0025,dark,root)
 needle=P('MOVABLE_Needle',(0,-.129,.25));localbox('Pointer',(0,0,.043),(.006,.004,.086),red,needle)
 C('Spring_Column',(0,0,.35),.025,.12,steel);pan=P('MOVABLE_Pan',(0,0,.42));localbox('Platform',(0,0,0),(.38,.30,.02),steel,pan)
 for y in [-.145,.145]:localbox('Pan_Lip',(0,y,.02),(.38,.01,.04),steel,pan)
 for x in [-.185,.185]:localbox('Pan_Lip',(x,0,.02),(.01,.28,.04),steel,pan)


 o=C('Pointer_Axle',(0,-.126,.25),.008,.016,steel);o.rotation_euler[0]=math.pi/2
 root['units']='metres';root['backlog_id']=497
 return root
def animate():
 s=bpy.context.scene;s.render.fps=24;s.frame_start=1;s.frame_end=49
 for name,prop,axis,delta in [('MOVABLE_Needle', 'rotation_euler', 1, 2.1), ('MOVABLE_Pan', 'location', 2, -0.015)]:
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
