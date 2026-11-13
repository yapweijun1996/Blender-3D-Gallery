"""Original V2.1 P0 433 visual asset. No standards/certification claim.
Source root door_angle_degrees (0..100) and push_bar_depression_m (0...018)
are authoring poses only. --export-source preserves edited meshes.
"""
from pathlib import Path
import bpy,bmesh,math,json,struct,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-emergency-exit-door'; ROOT='ASSET_MallEmergencyExitDoor'
def material(name,rgb,metallic=0,roughness=.4):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def lin(v):
        v/=255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    color=(*[lin(v) for v in rgb],1);p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=color;p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness;m.diffuse_color=color;return m

def empty(name,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.location=loc;return o

def cube(name,loc,size,mat,parent=None,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:
        m=o.modifiers.new('Subtle manufactured edge','BEVEL');m.width=bevel;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
    o.parent=parent;return o

def cylinder(name,loc,r,depth,mat,parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);o.parent=parent
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o

def attach_keep_world(o,parent):
    bpy.context.view_layer.update();matrix=o.matrix_world.copy();o.parent=parent;o.matrix_world=matrix

def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def beam(name,a,b,width,depth,mat,parent=None):
    a,b=Vector(a),Vector(b);o=cube(name,(a+b)/2,((b-a).length,width,depth),mat,parent,.002);o.rotation_euler.z=math.atan2(b.y-a.y,b.x-a.x);return o

def apply_pose(root):
    angle=float(root['door_angle_degrees']);press=float(root['push_bar_depression_m'])
    if not 0<=angle<=100 or not 0<=press<=.018:raise ValueError('Authoring pose range: angle 0..100 degrees; depression 0...018 m')
    hinge=bpy.data.objects['PIVOT_DoorHinge'];hinge.rotation_euler.z=-math.radians(angle)
    bpy.data.objects['PIVOT_PushBar'].location.y=press
    bpy.context.view_layer.update()
    a=bpy.data.objects['CONNECTOR_CloserLeafPivot'].matrix_world.translation.copy();b=bpy.data.objects['CONNECTOR_CloserFramePivot'].matrix_world.translation.copy()
    d=(b-a).length;L=.28
    if not 0<d<2*L:raise ValueError('Closer linkage out of range')
    mid=(a+b)/2;v=(b-a)/d;perp=Vector((v.y,-v.x,0));elbow=mid+perp*math.sqrt(L*L-d*d/4)
    for name,p,q,z in [('MODULE_CloserArmLeaf',a,elbow,2.078),('MODULE_CloserArmFrame',elbow,b,2.091)]:
        o=bpy.data.objects[name];o.location=(p+q)/2;o.location.z=z;o.rotation_euler.z=math.atan2(q.y-p.y,q.x-p.x)
    bpy.data.objects['MODULE_CloserElbowPin'].location=(elbow.x,elbow.y,2.0845)
    bpy.context.view_layer.update()

def export(root,path):
    apply_pose(root);bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
    data=path.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);mats=[];mapping={}
    for i,m in enumerate(doc['materials']):
        if m not in mats:mats.append(m)
        mapping[i]=mats.index(m)
    for m in doc['meshes']:
        for p in m['primitives']:p['material']=mapping[p['material']]
    doc['materials']=mats;chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*(-len(chunk)%4);tail=data[20+n:];path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)

def studio():
    s=bpy.context.scene;bg=material('STUDIO warm stone',(208,208,197),roughness=.85);cube('STUDIO_Floor',(0,0,-.04),(200,200,.08),bg)
    for name,pos,energy,size in [('Key',(-3,-4,5),650,3),('Fill',(3,-2,3),360,3),('Rim',(1,2,4),550,2)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=energy;o.data.size=size;point_at(o,(0,0,1))
    bpy.ops.object.camera_add(location=(3,-6,3));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=2.7;point_at(s.camera,(0,-.03,1.08))
    s.world=bpy.data.worlds.new('Studio environment');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.39,.42,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    root=empty(ROOT);frame=material('Warm grey powder coated frame',(132,141,138),.25,.45);red=material('Muted oxide red door',(157,55,43),.18,.44);steel=material('Brushed stainless hardware',(182,193,195),.72,.29);dark=material('Charcoal hardware caps',(37,44,43),.12,.4);green=material('Original green EXIT plaque',(26,107,73),.05,.45);white=material('Original ivory EXIT strokes',(245,243,224),0,.5)
    for name,x in [('Left',-.515),('Right',.515)]:cube('FRAME_'+name+'Jamb',(x,0,1.05),(.07,.14,2.1),frame,root,.002)
    cube('FRAME_Head',(0,0,2.14),(1.1,.14,.08),frame,root,.002)
    hinge=empty('PIVOT_DoorHinge',root,(-.48,-.05,0));leaf=cube('MODULE_DoorLeaf',(0,0,1.0535),(.95,.05,2.083),red,root,.002);attach_keep_world(leaf,hinge)
    for i,z in enumerate([.22,1.05,1.88]):
        cube('HINGE_FixedPlate'+str(i),(-.505,-.074,z),(.048,.008,.10),steel,root,.002)
        barrel=cylinder('HINGE_Barrel'+str(i),(-.48,-.05,z),.013,.105,steel,root)
        plate=cube('HINGE_LeafPlate'+str(i),(-.447,-.032,z),(.055,.009,.09),steel,root,.002);attach_keep_world(plate,hinge)
    kick=cube('MODULE_KickPlate',(0,-.027,.18),(.89,.004,.28),steel,root,.002);attach_keep_world(kick,hinge)
    for side,x in [('Left',-.36),('Right',.36)]:
        box=cube('MODULE_PushBarMount'+side,(x,-.066,1.03),(.09,.082,.105),dark,root,.009);attach_keep_world(box,hinge)
    push=empty('PIVOT_PushBar',hinge)
    bar=cube('MODULE_HorizontalPushBar',(0,-.128,1.03),(.79,.035,.05),steel,root,.012);attach_keep_world(bar,push)
    rear=cube('MODULE_RearPullHandle',(.35,.063,1.03),(.035,.07,.20),steel,root,.01);attach_keep_world(rear,hinge)
    plaque=cube('MODULE_ExitPlaque',(0,-.028,1.67),(.36,.006,.13),green,root,.007);attach_keep_world(plaque,hinge)
    # Original simple rectilinear letter strokes, not a font or standard sign mark.
    letters={'E':[(0,0,0,1),(0,1,.6,1),(0,.5,.5,.5),(0,0,.6,0)],'X':[(0,0,.6,1),(0,1,.6,0)],'I':[(.3,0,.3,1)],'T':[(0,1,.6,1),(.3,0,.3,1)]}
    for index,char in enumerate('EXIT'):
        for j,(x1,z1,x2,z2) in enumerate(letters[char]):
            a=Vector((-.136+index*.073+x1*.07,-.032,1.63+z1*.08));b=Vector((-.136+index*.073+x2*.07,-.032,1.63+z2*.08));d=b-a
            o=cube(f'LABEL_EXIT_{char}_{j}',(a+b)/2,(.008,.002,d.length+.006),white,root,.001);o.rotation_euler.y=math.atan2(d.x,d.z);attach_keep_world(o,hinge)
    body=cube('MODULE_CloserBody',(-.23,-.059,2.029),(.19,.068,.06),steel,root,.008);attach_keep_world(body,hinge)
    pin=cylinder('MODULE_CloserLeafPin',(-.23,-.075,2.068),.013,.023,dark,root);attach_keep_world(pin,hinge)
    a=empty('CONNECTOR_CloserLeafPivot',root,(-.23,-.075,2.078));attach_keep_world(a,hinge)
    empty('CONNECTOR_CloserFramePivot',root,(-.1,-.095,2.078))
    cube('MODULE_CloserFrameBracket',(-.1,-.083,2.128),(.072,.026,.034),steel,root,.002)
    cylinder('MODULE_CloserFramePin',(-.1,-.095,2.106),.012,.065,steel,root)
    for n in ['Leaf','Frame']:cube('MODULE_CloserArm'+n,(0,0,2.078),(.28,.018,.01),steel,root,.003)
    cylinder('MODULE_CloserElbowPin',(0,0,2.0845),.013,.026,dark,root)
    empty('CONNECTOR_FloorCentre',root);empty('CONNECTOR_WallOpeningCentre',root,(0,0,1.05))
    root['door_angle_degrees']=0.0;root['push_bar_depression_m']=0.0;root['units']='metres';root['backlog']='V2.1 P0 item 433'
    root['scope']='Visual asset only. No certification, fire resistance, building-code or evacuation-safety claims. No runtime door UI.'
    root['mounting']='Floor z=0, opening x=-.48...48 z=0..2.10; frame depth .14; front -Y. Source opening 0..100 degrees into front clearance zone.'
    apply_pose(root);studio();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'),compress=True);return root

if __name__=='__main__':
    for name in ['sources','exports','previews','reports']:(HERE/name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'));root=bpy.data.objects[ROOT]
    else:root=build()
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:s=bpy.context.scene;s.render.filepath=str(HERE/'previews'/f'{SLUG}.png');bpy.ops.render.render(write_still=True)
