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

SLUG='hdb-bin-centre';ROOT='ASSET_HDBBinCentre'
def build():

    shell=material('Warm rendered concrete',(213,211,193),.85);teal=material('Painted teal metal',(50,105,96),.45,.15);dark=material('Dark rubber wheels',(34,39,38),.8);green=material('Green refuse bins',(66,121,64),.6);white=material('Waste pictogram',(231,234,220),.7)
    root=empty(ROOT)
    attach(box('BASE',(0,0,.08),(4.8,3.2,.16),shell,.008),root)
    attach(box('REAR_Wall',(0,1.50,1.42),(4.8,.20,2.52),shell,.006),root)
    for sign in [-1,1]:attach(box('SIDE_Wall_'+str(sign),(sign*2.30,0,1.42),(.20,2.8,2.52),shell,.006),root)
    attach(box('ROOF_Removable',(0,0,2.78),(5.0,3.40,.20),shell,.006),root)
    attach(box('FASCIA',(0,-1.55,2.47),(4.4,.10,.42),teal,.003),root)
    for sign in [-1,1]:
        pivot=empty('HINGE_Door_'+str(sign),root,(sign*2.14,-1.53,.16))
        x=sign*1.07
        for xx in [x-1.02,x+1.02]:attach(box('DOOR_Frame_'+str(sign)+'_'+str(xx),(xx,-1.53,1.17),(.06,.07,2.02),teal,.002),pivot)
        for z in [.20,2.14]:attach(box('DOOR_Rail_'+str(sign)+'_'+str(z),(x,-1.53,z),(1.98,.07,.06),teal,.002),pivot)
        for i in range(12):attach(box('LOUVER_'+str(sign)+'_'+str(i),(x,-1.53,.30+i*.15),(1.98,.07,.075),teal,.001),pivot)
        attach(box('HANDLE_'+str(sign),(sign*.12,-1.59,1.15),(.025,.055,.25),dark,.003),pivot)
        binroot=empty('CONTEXT_Bin_'+str(sign),root)
        attach(box('BIN_Body_'+str(sign),(sign*.8,0,.72),(.64,.70,1.0),green,.025),binroot)
        attach(box('BIN_Lid_'+str(sign),(sign*.8,-.015,1.25),(.70,.76,.06),teal,.01),binroot)
        for xx in [sign*.8-.26,sign*.8+.26]:
            o=cylinder('BIN_Wheel_'+str(xx),(xx,.26,.20),.12,.07,dark);o.rotation_euler[1]=1.57079632679;attach(o,binroot)
    # Original geometric bin icon, no text/font/brand artwork.
    attach(box('ICON_Bin',(0,-1.61,2.45),(.18,.012,.20),white,.005),root)
    attach(box('ICON_Lid',(0,-1.61,2.57),(.23,.012,.025),white,.003),root)
    return root

def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();root['units']='metres';root['backlog_id']=315;root['scope']='Generic HDB-inspired visual module; no estate survey, official brand or engineering/safety certification.'
        studio();s.camera.location=(6, -8, 5);s.camera.data.ortho_scale=6.4;point_at(s.camera,(0, 0, 1.4))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
