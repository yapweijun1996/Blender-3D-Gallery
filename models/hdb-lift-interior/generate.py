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
    s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
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


SLUG='hdb-lift-interior';ROOT='ASSET_HDBLiftInterior'
def build():

    steel=material('Satin cabin wall panels',(167,177,180),.38,.55)
    dark=material('Charcoal floor',(66,74,76),.9)
    ivory=material('Warm white ceiling',(224,225,215),.72)
    rail=material('Polished handrail',(149,159,162),.24,.8)
    light=material('Diffused ceiling luminaire',(248,243,220),.32)
    root=empty(ROOT)
    attach(box('FLOOR',(0,0,.06),(1.8,1.7,.12),dark,.003),root)
    # Independent exterior shell panels; no front wall, so the interior is visible.
    attach(box('WALL_Rear',(0,.82,1.26),(1.8,.06,2.28),steel,.003),root)
    for sign in [-1,1]:
        attach(box('WALL_Side_'+str(sign),(sign*.87,0,1.26),(.06,1.64,2.28),steel,.003),root)
        attach(box('SKIRT_'+str(sign),(sign*.833,0,.20),(.012,1.58,.16),dark,.001),root)
    attach(box('CEILING_Removable',(0,0,2.43),(1.8,1.7,.06),ivory,.002),root)
    for x in [-.45,.45]:attach(box('LIGHT_Diffuser_'+str(x),(x,0,2.393),(.32,1.30,.014),light,.002),root)
    # Two rear rails and their mounts remain independently editable.
    o=cylinder('HANDRAIL_Rear',(0,.72,1.05),.025,1.5,rail);o.rotation_euler[1]=1.57079632679;attach(o,root)
    for x in [-.65,.65]:
        o=cylinder('HANDRAIL_Mount_'+str(x),(x,.765,1.05),.018,.09,rail);o.rotation_euler[0]=1.57079632679;attach(o,root)
    # Generic control strip is a visual prop, not a functional lift controller.
    attach(box('CONTROL_Backplate',(.825,-.44,1.24),(.018,.20,.50),dark,.002),root)
    for i in range(4):
        o=cylinder('CONTROL_Button_'+str(i),(.808,-.44,1.08+i*.10),.023,.012,rail);o.rotation_euler[1]=1.57079632679;attach(o,root)
    empty('CONNECTOR_FrontThreshold',root,(0,-.85,.12));root['interior_width_m']=1.68;root['interior_depth_m']=1.61
    return root

def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();root['units']='metres';root['backlog_id']=303;root['scope']='Generic HDB-inspired visual module, not surveyed construction or safety certification.'
        studio();s.camera.location=(3, -7, 2.8);s.camera.data.ortho_scale=3.5;point_at(s.camera,(0, 0, 1.2))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
