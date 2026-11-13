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
    s.render.engine='CYCLES';s.cycles.samples=64;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
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

h={'studio':studio,'point_at':point_at,'export':export}
SLUG='mall-structural-column';ROOT='ASSET_MallStructuralColumn'
HEIGHT=3.0;WIDTH=.50;CLADDING_THICKNESS=.02;BASE_WIDTH=.60
BASE_HEIGHT=.20;CAP_HEIGHT=.16;REVEAL_HEIGHT=.02;MID_JOINT=.008
def main():
    for d in ('sources','exports','previews','reports'):(HERE/d).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        stone=material('Honed warm ivory cladding',(214,210,194),.58)
        metal=material('Satin charcoal base and reveals',(65,77,79),.32,.55)
        coremat=material('Neutral column core',(157,159,150),.82)
        root=empty(ROOT);clad=empty('CLADDING_IndependentPanels',root)
        bottom=BASE_HEIGHT+REVEAL_HEIGHT;top=HEIGHT-CAP_HEIGHT-REVEAL_HEIGHT;mid=(bottom+top)/2
        attach(box('BASE_Plinth',(0,0,BASE_HEIGHT/2),(BASE_WIDTH,BASE_WIDTH,BASE_HEIGHT),metal,.003),root)
        attach(box('REVEAL_Base',(0,0,BASE_HEIGHT+REVEAL_HEIGHT/2),(WIDTH-.02,WIDTH-.02,REVEAL_HEIGHT),metal,.001),root)
        attach(box('CORE_SquareShaft',(0,0,(bottom+top)/2),(WIDTH-.06,WIDTH-.06,top-bottom),coremat,.001),root)
        for label,lo,hi in [('Lower',bottom,mid-MID_JOINT/2),('Upper',mid+MID_JOINT/2,top)]:
            for side,loc,dims in [
                ('Front',(0,-(WIDTH-CLADDING_THICKNESS)/2,(lo+hi)/2),(WIDTH,CLADDING_THICKNESS,hi-lo)),
                ('Back',(0,(WIDTH-CLADDING_THICKNESS)/2,(lo+hi)/2),(WIDTH,CLADDING_THICKNESS,hi-lo)),
                ('Left',(-(WIDTH-CLADDING_THICKNESS)/2,0,(lo+hi)/2),(CLADDING_THICKNESS,WIDTH-2*CLADDING_THICKNESS,hi-lo)),
                ('Right',((WIDTH-CLADDING_THICKNESS)/2,0,(lo+hi)/2),(CLADDING_THICKNESS,WIDTH-2*CLADDING_THICKNESS,hi-lo))]:
                attach(box('CLADDING_'+side+'_'+label,loc,dims,stone,.001),clad)
        attach(box('REVEAL_Cap',(0,0,top+REVEAL_HEIGHT/2),(WIDTH-.02,WIDTH-.02,REVEAL_HEIGHT),metal,.001),root)
        attach(box('CAP_Square',(0,0,HEIGHT-CAP_HEIGHT/2),(BASE_WIDTH,BASE_WIDTH,CAP_HEIGHT),stone,.003),root)
        empty('CONNECTOR_Floor',root);empty('CONNECTOR_Ceiling',root,(0,0,HEIGHT))
        root['units']='metres';root['height_m']=HEIGHT;root['shaft_width_m']=WIDTH;root['base_width_m']=BASE_WIDTH
        root['origin']='bottom centre, Blender Z=0 / glTF Y=0'
        root['scope']='Visual architecture asset only. No structural load, safety, engineering or code certification.'
        root['placement']='Place at floor finished height. Reserve one 1.2 m ceiling bay; do not intersect intact ceiling panels.'
        h['studio']();s.camera.location=(3,-6,3);s.camera.data.ortho_scale=3.65;h['point_at'](s.camera,(0,0,1.5))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    h['export'](root,HERE/'exports'/(SLUG+'.glb'))
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
