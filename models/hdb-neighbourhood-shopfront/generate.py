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


def beam(name,a,b,r,mat,parent):
    a,b=Vector(a),Vector(b);o=cylinder(name,(a+b)/2,r,(b-a).length,mat);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();attach(o,parent)

SLUG='hdb-neighbourhood-shopfront';ROOT='ASSET_HDBNeighbourhoodShopfront'
def build():

    frame=material('Muted blue-green shop frames',(54,107,103),.4,.1);wall=material('Cream perimeter piers',(222,214,193),.8);glass=material('Clear blue display glazing',(160,207,215),.18,.05,.28);sign=material('Blank replaceable sign face',(224,230,212),.72);dark=material('Black door handle',(44,50,49),.5);root=empty(ROOT)
    attach(box('THRESHOLD',(0,0,.04),(4.0,.50,.08),wall,.004),root)
    for x in [-1.9,1.9]:attach(box('PIER_'+str(x),(x,0,1.50),(.20,.32,2.92),wall,.004),root)
    attach(box('SIGN_Backboard',(0,0,2.93),(3.6,.20,.50),frame,.003),root)
    attach(box('SIGN_ReplaceableFace',(0,-.112,2.93),(3.4,.018,.36),sign,.002),root)
    for x in [-1.72,.45,1.72]:attach(box('FRAME_Jamb_'+str(x),(x,-.02,1.38),(.055,.08,2.60),frame,.001),root)
    for z in [.12,2.65]:attach(box('FRAME_Rail_'+str(z),(-.635,-.02,z),(2.12,.08,.055),frame,.001),root)
    attach(box('DISPLAY_Glass',(-.635,-.02,1.385),(2.12,.008,2.475),glass,0),root)
    leaf=empty('HINGE_Entrance',root,(1.69,-.02,.08))
    for x in [.52,1.67]:attach(box('DOOR_Stile_'+str(x),(x,-.02,1.38),(.055,.055,2.60),frame,.001),leaf)
    for z in [.12,2.65]:attach(box('DOOR_Rail_'+str(z),(1.095,-.02,z),(1.10,.055,.055),frame,.001),leaf)
    attach(box('DOOR_Glass',(1.095,-.02,1.385),(1.10,.008,2.475),glass,0),leaf)
    attach(box('DOOR_Handle',(.61,-.08,1.3),(.025,.05,.36),dark,.003),leaf)
    attach(box('CANOPY',(0,-.65,2.65),(4.15,1.5,.10),frame,.004),root)
    for x in [-1.8,1.8]:beam('CANOPY_Bracket_'+str(x),(x,-.02,2.30),(x,-1.1,2.60),.018,dark,root)
    return root

def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();root['units']='metres';root['backlog_id']=317;root['scope']='Generic HDB-inspired visual module; no estate survey, official brand or engineering/safety certification.'
        studio();s.camera.location=(5, -8, 4);s.camera.data.ortho_scale=5.5;point_at(s.camera,(0, -0.25, 1.6))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
