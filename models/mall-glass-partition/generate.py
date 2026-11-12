"""Original static full-height glazed partition, metres, Blender +Z / glTF +Y.
Normal generation replaces source. --export-source preserves manual source edits.
"""
from pathlib import Path
import bpy,sys,math,json,struct
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-glass-partition'; ROOT='ASSET_MallGlassPartition'
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
def main():
    for folder in ('sources','exports','previews','reports'):(HERE/folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        metal=material('Satin charcoal aluminium',(65,77,79),.32,.55)
        glass=material('GLASS pale aqua alpha 0.22',(155,202,197),.16,0,.22)
        stripe=material('Frosted visibility band',(220,229,222),.65,0,.7)
        root=empty(ROOT);frame=empty('FRAME_TracksAndMullions',root);panes=empty('PANES_StaticGlazing',root)
        for side,x in [('Left',-.57),('Right',.57)]:
            post=attach(box('POST_'+side,(x,0,1.2),(.06,.06,2.4),metal,.001),root)
            post['joint_policy']='Keep one shared square post at coincident connectors; remove incoming POST_Left.'
            connector=empty('CONNECTOR_'+side,root,(x,0,0));connector['height_m']=2.4;connector['joint_angles_degrees']='0, 90, -90';connector['post_node']='POST_'+side
        for name,z in [('FloorTrack',.03),('CeilingTrack',2.37)]:attach(box('FRAME_'+name,(0,0,z),(1.08,.06,.06),metal),frame)
        attach(box('MULLION_Centre',(0,0,1.2),(.03,.045,2.28),metal),frame)
        for side,x in [('Left',-.2775),('Right',.2775)]:
            attach(box('TRANSOM_'+side,(x,0,1.85),(.525,.045,.03),metal),frame)
            for label,z,height in [('Lower',.9475,1.775),('Upper',2.1025,.475)]:
                attach(box('GLASS_'+side+'_'+label,(x,0,z),(.525,.01,height),glass,0),panes)
            for face,y in [('Front',-.006),('Back',.006)]:attach(box('BAND_'+side+'_'+face,(x,y,1.32),(.485,.001,.055),stripe,0),panes)
        root['units']='metres';root['origin']='floor midpoint of standalone bay';root['pitch_m']=1.14
        root['scope']='Static full-height mall partition, not a door or guardrail. No safety, structural or installation certification.'
        root['assembly']='Connect at x=-0.57/+0.57 m. Incoming bay shares preceding POST_Right; remove its POST_Left. Square posts support 0 or +/-90 degree joins.'
        studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
