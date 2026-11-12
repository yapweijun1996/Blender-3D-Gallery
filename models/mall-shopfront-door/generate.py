"""Original hinged double shopfront door, metres, Blender +Z / glTF +Y.
Normal generation replaces source. --export-source preserves manual source edits.
"""
from pathlib import Path
import bpy,sys,math,json,struct
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-shopfront-door'; ROOT='ASSET_MallShopfrontDoor'
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
    matrix=o.matrix_world.copy();o.parent=parent;o.matrix_world=matrix;return o
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
def main():
    for folder in ('sources','exports','previews','reports'):(HERE/folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        metal=material('Satin charcoal aluminium',(65,77,79),.32,.55)
        steel=material('Brushed stainless pull hardware',(184,191,188),.3,.7)
        glass=material('GLASS pale aqua alpha 0.22',(155,202,197),.16,0,.22)
        stripe=material('Frosted visibility band',(220,229,222),.65,0,.7)
        root=empty(ROOT);fixed=empty('FRAME_Fixed',root)
        for side,x in [('Left',-1.01),('Right',1.01)]:attach(box('FRAME_Jamb_'+side,(x,0,1.16),(.08,.12,2.32),metal,.002),fixed)
        attach(box('FRAME_Header',(0,0,2.36),(2.1,.12,.08),metal,.002),fixed)
        for side,sign in [('Left',-1),('Right',1)]:
            pivot=empty('HINGE_'+side,root,(sign*.95,-.04,0));bpy.context.view_layer.update()
            pivot['open_angle_degrees']=sign*90;pivot['axis']='Blender local Z / glTF local Y';pivot['closed_angle_degrees']=0
            centre=sign*.478
            for label,x in [('HingeStile',sign*.93),('MeetingStile',sign*.026)]:attach(box('LEAF_'+side+'_'+label,(x,-.04,1.159),(.04,.04,2.282),metal),pivot)
            attach(box('LEAF_'+side+'_BottomRail',(centre,-.04,.068),(.864,.04,.1),metal),pivot)
            attach(box('LEAF_'+side+'_TopRail',(centre,-.04,2.27),(.864,.04,.06),metal),pivot)
            attach(box('GLASS_'+side,(centre,-.04,1.179),(.864,.01,2.122),glass,0),pivot)
            for face,y in [('Front',-.046),('Back',-.034)]:attach(box('BAND_'+side+'_'+face,(centre,y,1.36),(.82,.001,.055),stripe,0),pivot)
            for face,y in [('Front',-.111),('Back',.031)]:
                attach(cylinder('HANDLE_'+side+'_'+face,(sign*.13,y,1.10),.012,.60,steel),pivot)
                for z in [.84,1.36]:attach(box('BRACKET_'+side+'_'+face+'_'+str(z),(sign*.13,(y-.04)/2,z),(.022,.071,.022),steel,.002),pivot)
            # Barrels are fixed frame components. Leaves rotate on the same named axis.
            for z in [.32,2.04]:attach(cylinder('HINGE_Barrel_'+side+'_'+str(z),(sign*.95,-.04,z),.014,.10,steel),fixed)
        root['units']='metres';root['origin']='floor midpoint of frame';root['opening']='Frame aperture 1.94 m wide x 2.32 m high; paired leaves rotate outward 0 to 90 degrees at HINGE_Left/Right.'
        root['scope']='Static gallery GLB with editable transform pivots. No runtime door click controls or animation clips; no safety/accessibility/fire/security certification.'
        studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
