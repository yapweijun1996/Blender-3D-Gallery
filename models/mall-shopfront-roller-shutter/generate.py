"""Original mall shutter in metres. --export-source preserves saved edits."""
from pathlib import Path
import bpy,sys,math,json,struct
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG="mall-shopfront-roller-shutter"; ROOT="ASSET_MallShopfrontRollerShutter"
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
    target=(0,0,1.6)
    for name,loc,power,size in [('Key',(-3,-4,6),800,4),('Fill',(4,-2,3),500,4),('Rear',(1,4,5),900,3)]:
        bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=power;o.data.size=size;point_at(o,target)
    bpy.ops.object.camera_add(location=(3,-6,3.1));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=4.4;point_at(s.camera,target)
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
# Geometric pose helper, not a motor/physics/controller simulation.
R=.27; K=-.024/(2*math.pi); TANGENT_Z=3.
def arc(theta):
    def f(r):return .5*(r*math.sqrt(r*r+K*K)+K*K*math.asinh(r/abs(K)))/K
    return f(R+K*theta)-f(R)
def path(z):
    if z<=TANGENT_Z:return -.03,z,0.
    low,high=0.,16.
    for _ in range(48):
        theta=(low+high)/2
        if arc(theta)<z-TANGENT_Z:low=theta
        else:high=theta
    t=(low+high)/2;r=R+K*t
    return .24-r*math.cos(t),3+r*math.sin(t),-math.atan2(r*math.sin(t)-K*math.cos(t),r*math.cos(t)+K*math.sin(t))
def pose(lift):
    assert 0<=lift<=2.6
    for i in range(28):
        o=bpy.data.objects[f'SLAT_{i+1:02d}'];y,z,angle=path(.13+i*.1+lift)
        o.rotation_mode='XYZ';o.location=(0,y,z);o.rotation_euler=(angle,0,0)
    for name,z in [('BOTTOM_Rail',.04),('BOTTOM_Seal',.005)]:
        bpy.data.objects[name].location.z=z+lift
    bpy.context.view_layer.update()
def main():
    for folder in ('sources','exports','previews','reports'):(HERE/folder).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        steel=material('Satin galvanized shutter slats',(178,185,183),.38,.65)
        frame=material('Charcoal powder coated housing',(57,70,74),.42,.35)
        hardware=material('Steel roller and bottom rail',(112,126,128),.32,.7)
        rubber=material('Dark rubber floor seal',(31,35,34),.85,0)
        root=empty(ROOT);fixed=empty('FRAME_Fixed',root);curtain=empty('CURTAIN_EditableSlats',root);roller=empty('ROLLER_Assembly',root)
        # U-section guides: webs outside the curtain; front/rear lips capture ends with clearance.
        for side,sign in [('Left',-1),('Right',1)]:
            for label,loc,dims in [('Web',(sign*1.55,-.03,1.35),(.06,.15,2.7)),('FrontLip',(sign*1.52,-.0925,1.35),(.12,.025,2.7)),('RearLip',(sign*1.52,.0325,1.35),(.12,.025,2.7))]:
                attach(box('TRACK_'+side+'_'+label,loc,dims,frame,.0015),fixed)
        # Three removable hood sheets plus separate end plates. Open underside.
        for label,loc,dims in [('Front',(0,-.151,3.01),(3.26,.018,.62)),('Rear',(0,.521,3.01),(3.26,.018,.62)),('Top',(0,.185,3.329),(3.26,.69,.018)),('Left',(-1.639,.185,3.01),(.018,.69,.62)),('Right',(1.639,.185,3.01),(.018,.69,.62))]:
            attach(box('HOOD_'+label,loc,dims,frame,.0015),fixed)
        drum=cylinder('ROLLER_Drum',(0,.24,3.),.22,3.12,hardware);drum.rotation_euler.y=math.pi/2;attach(drum,roller)
        for side,sign in [('Left',-1),('Right',1)]:
            axle=cylinder('ROLLER_Axle_'+side,(sign*1.59,.24,3),.035,.06,hardware);axle.rotation_euler.y=math.pi/2;attach(axle,roller)
        for i in range(28):
            o=box(f'SLAT_{i+1:02d}',(0,-.03,.13+i*.1),(3.,.012,.096),steel,.0015);attach(o,curtain);o['index_from_bottom']=i+1
        attach(box('BOTTOM_Rail',(0,-.03,.04),(3.,.045,.07),hardware,.002),curtain)
        attach(box('BOTTOM_Seal',(0,-.03,.005),(3.,.04,.01),rubber,.001),curtain)
        root['units']='metres';root['origin']='floor midpoint'
        root['pose_instructions']='Use generate.py pose(lift) from 0 to 2.6 metres. 28 separate slats follow a geometric spiral winding path; roller and bottom rail remain independent. No physics or motor controls.'
        root['scope']='Generic visual concept. Not a safety, security, structural, fire or installation specification. Static closed gallery export; no runtime click interaction.'
        studio();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
