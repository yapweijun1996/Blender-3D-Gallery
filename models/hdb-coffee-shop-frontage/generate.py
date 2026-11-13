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

SLUG='hdb-coffee-shop-frontage';ROOT='ASSET_HDBCoffeeShopFrontage'
def build():

    cream=material('Cream frontage plaster',(226,215,187),.8);green=material('Kopitiam green trim',(49,112,91),.45,.1);metal=material('Stainless counter',(163,175,176),.35,.7);dark=material('Dark support and cup',(55,66,58),.5);white=material('Pale canvas awning',(239,235,212),.85);root=empty(ROOT)
    attach(box('FLOOR_Sill',(0,0,.05),(6,.70,.10),cream,.004),root)
    for x in [-2.9,.9,2.9]:attach(box('PIER_'+str(x),(x,0,1.45),(.20,.30,2.80),cream,.004),root)
    attach(box('FASCIA_Support',(0,0,2.98),(6,.25,.48),green,.003),root)
    attach(box('FASCIA_ReplaceableFace',(0,-.14,2.98),(5.7,.025,.34),white,.002),root)
    attach(box('COUNTER_Front',(-1.0,-.02,.56),(3.6,.15,.92),green,.005),root)
    attach(box('COUNTER_Top',(-1.0,-.15,1.05),(3.75,.75,.08),metal,.008),root)
    for x in [-2.75,.75]:attach(box('COUNTER_Side_'+str(x),(x,.10,.56),(.10,.42,.92),cream,.003),root)
    # 1.8 m clear right-hand entrance is left physically open.
    awning=box('AWNING_Editable',(0,-.85,2.63),(6.2,1.8,.055),white,.002);awning.rotation_euler[0]=.10;attach(awning,root)
    attach(box('AWNING_Valance',(0,-1.74,2.49),(6.2,.05,.18),green,.002),root)
    for x in [-2.8,2.8]:beam('AWNING_Bracket_'+str(x),(x,0,2.1),(x,-1.6,2.50),.023,green,root)
    # Cup icon and handle built entirely from primitive meshes, no external brand/font.
    attach(box('ICON_CupBody',(0,-.162,2.98),(.25,.016,.18),dark,.016),root)
    bpy.ops.mesh.primitive_torus_add(major_segments=20,minor_segments=6,location=(.16,-.162,2.98),major_radius=.065,minor_radius=.012,rotation=(1.57079632679,0,0));o=bpy.context.object;o.name='ICON_CupHandle';o.data.materials.append(dark);attach(o,root)
    attach(box('ICON_Saucer',(0,-.162,2.87),(.38,.016,.025),dark,.006),root)
    return root

def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();root['units']='metres';root['backlog_id']=318;root['scope']='Generic HDB-inspired visual module; no estate survey, official brand or engineering/safety certification.'
        studio();s.camera.location=(7, -10, 4.8);s.camera.data.ortho_scale=7.3;point_at(s.camera,(0, -0.4, 1.6))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
