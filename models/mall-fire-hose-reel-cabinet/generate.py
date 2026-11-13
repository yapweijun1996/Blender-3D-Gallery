"""Original V2.1 P0 434 visual fire-hose cabinet. No operation/safety claims.
Metres, front -Y, up +Z; source door pose only. --export-source preserves meshes.
"""
from pathlib import Path
import bpy, math, json, struct, sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-fire-hose-reel-cabinet';ROOT='ASSET_MallFireHoseReelCabinet'
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
        m=o.modifiers.new('Subtle manufactured edge','BEVEL');m.width=bevel;m.segments=1 if bevel<=.001 else 3;bpy.ops.object.modifier_apply(modifier=m.name)
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


def tube(name,points,radius,mat,parent,sides=8,closed=False):
    verts=[];faces=[]
    pts=[Vector(p) for p in points]
    for i,p in enumerate(pts):
        tangent=(pts[(i+1)%len(pts)]-pts[(i-1)%len(pts)]).normalized() if closed else (pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        u=tangent.cross(Vector((0,1,0))).normalized();v=tangent.cross(u).normalized()
        for j in range(sides):verts.append(p+radius*(u*math.cos(j*2*math.pi/sides)+v*math.sin(j*2*math.pi/sides)))
    for i in range(len(pts) if closed else len(pts)-1):
        for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,b,(b+sides)%len(verts),(a+sides)%len(verts)))
    if not closed:faces.append(tuple(reversed(range(sides))));faces.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.data.materials.append(mat)
    for face in mesh.polygons:face.use_smooth=len(face.vertices)==4
    return o
def disc(name,loc,r,depth,mat,parent):
    o=cylinder(name,loc,r,depth,mat,parent);o.rotation_euler.x=math.pi/2;return o
def apply_pose(root):
    angle=float(root['door_angle_degrees'])
    if not 0<=angle<=105:raise ValueError('Source pose range is 0..105 degrees')
    bpy.data.objects['PIVOT_CabinetDoor'].rotation_euler.z=-math.radians(angle)
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
    s=bpy.context.scene
    for name,pos,energy,size in [('Key',(-3,-4,5),550,3),('Fill',(3,-2,2),280,3),('Rim',(1,2,3),400,2)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=energy;o.data.size=size;point_at(o,(0,0,.4))
    bpy.ops.object.camera_add(location=(2,-5,2));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=1.52;point_at(s.camera,(-.22,-.32,.41))
    s.world=bpy.data.worlds.new('Studio environment');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.24,.27,.3,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
    s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    root=empty(ROOT)
    red=material('Vermilion powder coated steel',(182,38,30),.18,.42)
    inner=material('Warm grey inner lining',(186,184,172),.12,.52)
    hose=material('Charcoal rubber hose',(34,37,36),0,.62)
    steel=material('Satin hardware',(179,186,184),.7,.28)
    brass=material('Warm brass nozzle',(161,123,57),.65,.31)
    white=material('Original ivory label strokes',(244,239,213),0,.5)
    cube('ENCLOSURE_Back',(0,.004,.41),(.72,.012,.82),red,root,.002)
    cube('ENCLOSURE_InnerLining',(0,-.005,.41),(.687,.006,.787),inner,root,.001)
    for side,x in [('Left',-.354),('Right',.354)]:cube('ENCLOSURE_'+side,(x,-.11,.41),(.012,.23,.82),red,root,.002)
    for side,z in [('Bottom',.006),('Top',.814)]:cube('ENCLOSURE_'+side,(0,-.11,z),(.696,.23,.012),red,root,.002)
    # Plain geometric wall-mounting tabs, not an installation specification.
    for i,(x,z) in enumerate([(-.25,.12),(.25,.12),(-.25,.7),(.25,.7)]):
        cube('HARDWARE_RearTab'+str(i),(x,.016,z),(.07,.012,.09),steel,root,.003)
        disc('HARDWARE_Fastener'+str(i),(x,-.013,z),.009,.009,steel,root)
    pivot=empty('PIVOT_CabinetDoor',root,(-.365,-.257,0))
    door=cube('MODULE_MetalDoor',(0,-.25,.41),(.704,.016,.796),red,root,.003);attach_keep_world(door,pivot)
    for i,z in enumerate([.16,.66]):
        cylinder('HARDWARE_HingeBarrel'+str(i),(-.365,-.257,z),.01,.07,steel,root)
        plate=cube('HARDWARE_DoorHingePlate'+str(i),(-.336,-.254,z),(.04,.008,.056),steel,root,.002);attach_keep_world(plate,pivot)
    handle=cube('HARDWARE_DoorPull',(.283,-.277,.4),(.018,.038,.105),steel,root,.006);attach_keep_world(handle,pivot)
    latch=disc('HARDWARE_Latch',(.283,-.262,.32),.016,.006,steel,root);attach_keep_world(latch,pivot)
    # A compact original two-line FIRE / HOSE label, assembled from geometric strokes.
    segments={'F':[(0,0,0,1),(0,1,.6,1),(0,.5,.5,.5)],'I':[(.3,0,.3,1)],'R':[(0,0,0,1),(0,1,.6,1),(.6,1,.6,.5),(0,.5,.6,.5),(.3,.5,.6,0)],'E':[(0,0,0,1),(0,1,.6,1),(0,.5,.5,.5),(0,0,.6,0)],'H':[(0,0,0,1),(.6,0,.6,1),(0,.5,.6,.5)],'O':[(0,0,0,1),(0,1,.6,1),(.6,1,.6,0),(0,0,.6,0)],'S':[(0,1,.6,1),(0,1,0,.5),(0,.5,.6,.5),(.6,.5,.6,0),(0,0,.6,0)]}
    for row,word in enumerate(['FIRE','HOSE']):
        for index,char in enumerate(word):
            for j,(x1,z1,x2,z2) in enumerate(segments[char]):
                a=Vector((-.155+index*.082+x1*.075,-.259,.5-row*.13+z1*.09));b=Vector((-.155+index*.082+x2*.075,-.259,.5-row*.13+z2*.09));d=b-a
                o=cube(f'LABEL_{row}_{index}_{char}_{j}',(a+b)/2,(.009,.002,d.length+.005),white,root,.0008);o.rotation_euler.y=math.atan2(d.x,d.z);attach_keep_world(o,pivot)
    reel=empty('MODULE_Reel',root,(-.025,0,.47))
    disc('REEL_BackPlate',(0,-.066,0),.28,.012,red,reel)
    disc('REEL_Axle',(0,-.093,0),.047,.115,steel,reel)
    # Simplified single continuous planar spiral: 7 turns; 24 mm hose, 27 mm pitch.
    pts=[]
    for i in range(449):
        t=i/448;angle=-math.pi/2+t*7*2*math.pi;r=.06+.189*t
        pts.append((r*math.cos(angle),-.125,r*math.sin(angle)))
    tube('MODULE_CoiledHose',pts,.012,hose,reel)
    for i in range(3):
        a=i*2*math.pi/3
        o=cube('REEL_FrontSpoke'+str(i),(.15*math.cos(a),-.161,.15*math.sin(a)),(.253,.018,.025),red,reel,.003);o.rotation_euler.y=-a
    tube('REEL_FrontRim',[(.279*math.cos(i*2*math.pi/128),-.161,.279*math.sin(i*2*math.pi/128)) for i in range(128)],.009,red,reel,closed=True)
    disc('REEL_FrontHub',(0,-.177,0),.055,.026,red,reel)
    disc('REEL_HubFastener',(0,-.194,0),.014,.008,steel,reel)
    # Short displayed tail and clipped nozzle, no plumbing or operating mechanism.
    tail=[(-.025,-.125,.221),(-.026,-.125,.177),(-.01,-.125,.137),(.04,-.125,.112),(.13,-.125,.105),(.21,-.125,.117),(.255,-.125,.155),(.267,-.125,.203)]
    tube('MODULE_HoseTail',tail,.012,hose,root)
    cylinder('MODULE_NozzleBody',(.267,-.125,.255),.018,.115,brass,root)
    cylinder('MODULE_NozzleTip',(.267,-.125,.321),.012,.025,steel,root)
    cylinder('MODULE_NozzleGrip',(.267,-.125,.242),.021,.045,hose,root)
    cube('HARDWARE_NozzleClip',(.267,-.083,.26),(.055,.07,.019),steel,root,.003)
    empty('CONNECTOR_WallBottomCentre',root)
    root['door_angle_degrees']=105.0;root['units']='metres';root['backlog']='V2.1 P0 item 434'
    root['scope']='Visual module only. No installation, fire-system operation, certification, pressure, flow or safety claims. No runtime door controls.'
    root['placement']='Origin at cabinet bottom rear centre. Front -Y. Door pose is authoring-only.'
    apply_pose(root);studio();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'),compress=True);return root
if __name__=='__main__':
    for name in ['sources','exports','previews','reports']:(HERE/name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'));root=bpy.data.objects[ROOT]
    else:root=build()
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:s=bpy.context.scene;s.render.filepath=str(HERE/'previews'/f'{SLUG}.png');bpy.ops.render.render(write_still=True)
