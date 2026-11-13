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
    s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
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

SLUG='hawker-centre-tray-rack';ROOT='ASSET_HawkerCentreTrayRack'
def build():

    import bmesh
    steel=material('Satin stainless rack',(155,168,171),.38,.7);rubber=material('Dark caster rubber',(35,42,40),.8);terra=material('Reused tray terracotta',(184,103,69),.48)
    root=empty(ROOT)
    for x in [-.26,.26]:
        for y in [-.30,.30]:
            attach(box('POST_'+str(x)+'_'+str(y),(x,y,.87),(.025,.025,1.36),steel,.002),root)
            o=cylinder('CASTER_'+str(x)+'_'+str(y),(x,y,.05),.05,.035,rubber);o.rotation_euler[1]=1.57079632679;attach(o,root)
            attach(box('CASTER_Fork_'+str(x)+'_'+str(y),(x,y,.13),(.045,.045,.08),steel,.002),root)
    for z in [.22,1.54]:
        for y in [-.30,.30]:attach(box('CROSSBAR_'+str(z)+'_'+str(y),(0,y,z),(.50,.025,.025),steel,.001),root)
    for i in range(10):
        z=.31+i*.12
        for sign in [-1,1]:
            attach(box('RAIL_Horizontal_'+str(i)+'_'+str(sign),(sign*.218,0,z),(.045,.60,.012),steel,.001),root)
            attach(box('RAIL_Upstand_'+str(i)+'_'+str(sign),(sign*.245,0,z+.015),(.012,.60,.035),steel,.001),root)
    # Reuse the reviewed original 439 tray profile, not another new asset type.
    loops=[(.225,.165,0),(.225,.165,.030),(.214,.154,.030),(.201,.141,.006)]
    verts=[(u,v,.796+h) for w,d,h in loops for u,v in [(-w,-d),(w,-d),(w,d),(-w,d)]]
    faces=[(3,2,1,0),(12,13,14,15)]
    for k in range(3):
        for i in range(4):faces.append((k*4+i,k*4+(i+1)%4,(k+1)*4+(i+1)%4,(k+1)*4+i))
    mesh=bpy.data.meshes.new('Reused439Tray');mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('CONTEXT_Tray_Reuse439',mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(terra);attach(o,root)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    o['provenance']='Original tray profile reused from models/mall-food-court-tray-station/generate.py, backlog439; contextual, not a new counted type.'
    return root

def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();root['units']='metres';root['backlog_id']=368
        studio();s.camera.location=(2, -3, 2.2);s.camera.data.ortho_scale=2.1;point_at(s.camera,(0, 0, 0.82))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
