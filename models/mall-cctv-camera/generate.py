"""Original V2.1 P0 436 CCTV camera visual prop. No capture, network or tracking.
Metres; ceiling mount plane Z=0; front -Y; pan Z, tilt X. Deterministic.
"""
from pathlib import Path
import bpy,bmesh,math,json,struct,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-cctv-camera';ROOT='ASSET_MallCctvCamera'
def material(name,rgb,metallic=0,roughness=.4):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def lin(v):
        v/=255;return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    color=(*[lin(v) for v in rgb],1);p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=color;p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness;m.diffuse_color=color;return m
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;return o
def mesh(name,verts,faces,mat,parent,smooth=False):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.data.materials.append(mat)
    for f in me.polygons:f.use_smooth=smooth
    return o
def lathe(name,profile,mat,parent,segments=32,smooth=True):
    # Closed radial cross-section, no overlapping duplicate seam or zero-area pole.
    verts=[(r*math.cos(i*2*math.pi/segments),r*math.sin(i*2*math.pi/segments),z) for r,z in profile for i in range(segments)]
    faces=[]
    for j in range(len(profile)):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;c=((j+1)%len(profile))*segments+(i+1)%segments;d=((j+1)%len(profile))*segments+i
            faces.append((a,b,c,d))
    return mesh(name,verts,faces,mat,parent,smooth)
def cylinder(name,z,r,depth,mat,parent,segments=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=r,depth=depth,location=(0,0,z));o=bpy.context.object;o.name=name;o.parent=parent;o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4 and segments>8
    return o
def prism(name,points,depth,mat,parent):
    verts=[(x,y,z) for y in [-depth/2,depth/2] for x,z in points];n=len(points)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,verts,faces,mat,parent)
def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def export(root,path):
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
    data=path.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);mats=[];mapping={}
    for i,m in enumerate(doc['materials']):
        if m not in mats:mats.append(m)
        mapping[i]=mats.index(m)
    for me in doc['meshes']:
        for p in me['primitives']:p['material']=mapping[p['material']]
    doc['materials']=mats;chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*(-len(chunk)%4);tail=data[20+n:];path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)

def bevel(o,width=.002):
    bpy.context.view_layer.objects.active=o
    m=o.modifiers.new('Soft original edges','BEVEL');m.width=width;m.segments=3
    bpy.ops.object.modifier_apply(modifier=m.name)
    return o
def disc(name,location,radius,depth,mat,parent,axis='Z',rounded=False):
    o=cylinder(name,0,radius,depth,mat,parent,32);o.location=location
    if axis=='Y':o.rotation_euler.x=math.pi/2
    elif axis=='X':o.rotation_euler.y=math.pi/2
    if rounded:bevel(o,.004)
    return o
def box(name,location,size,mat,parent):
    bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.location=location;o.parent=parent;o.data.materials.append(mat);bevel(o,.002);return o
def studio():
    s=bpy.context.scene
    for name,pos,energy,size in [('Key',(-.30,-.40,-.10),7,.35),('Fill',(.30,-.25,-.12),4,.30),('Rim',(.12,.30,.20),9,.25)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=energy;o.data.size=size;point_at(o,(0,0,-.07))
    bpy.ops.object.camera_add(location=(.25,-.42,-.20));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.22;point_at(s.camera,(0,0,-.073))
    s.world=bpy.data.worlds.new('Studio environment');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.25,.29,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    root=empty(ROOT);pan=empty('PIVOT_Pan',root);pan.location.z=-.025
    tilt=empty('PIVOT_Tilt',pan);tilt.location.z=-.073;tilt.rotation_euler.x=math.radians(20)
    white=material('Matte warm white',(224,226,221),0,.58)
    dark=material('Matte charcoal',(30,34,39),0,.62)
    trim=material('Satin dark trim',(70,76,82),.30,.38)
    lens=material('Opaque dark lens representation',(12,21,28),0,.42)
    lens.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.12
    disc('MODULE_MountingBase',(0,0,-.010),.070,.020,white,root,rounded=True)
    disc('MODULE_BaseGasket',(0,0,-.021),.063,.002,dark,root)
    disc('MODULE_PanCollar',(0,0,-.002),.055,.010,white,pan)
    box('MODULE_YokeBridge',(0,0,-.010),(.090,.018,.010),white,pan)
    for sign,label in [(-1,'Left'),(1,'Right')]:
        box('MODULE_Yoke'+label,(sign*.049,0,-.0415),(.008,.018,.063),white,pan)
        disc('MODULE_TiltAxle'+label,(sign*.048,0,-.073),.009,.012,trim,pan,'X')
    disc('MODULE_Housing',(0,0,0),.042,.066,white,tilt,'Y',True)
    disc('MODULE_Faceplate',(0,-.034,0),.033,.003,dark,tilt,'Y')
    disc('MODULE_LensTrim',(0,-.037,0),.019,.004,trim,tilt,'Y')
    disc('MODULE_LensGasket',(0,-.0395,0),.015,.002,dark,tilt,'Y')
    disc('MODULE_Lens',(0,-.041,0),.012,.002,lens,tilt,'Y')
    empty('CONNECTOR_CeilingMountPlane',root)
    root['units']='metres';root['backlog']='V2.1 P0 item 436'
    root['scope']='Static visible scene prop only. No capture, network, tracking, surveillance functionality or deployment guidance.'
    root['placement']='Mount top at Z=0, body below; glTF Y=0 ceiling plane; front Blender -Y / glTF +Z.'
    root['lens']='Opaque dark material representation only. No physical optics claim.'
    pan['edit_axis']='Blender local Z / glTF local Y; scene pose editing only'
    tilt['edit_axis']='Blender local X / glTF local X; default +20 degrees downward; scene pose editing only'
    studio();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'),compress=True);return root
if __name__=='__main__':
    for name in ['sources','exports','previews','reports']:(HERE/name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'));root=bpy.data.objects[ROOT]
    else:root=build()
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:s=bpy.context.scene;s.render.filepath=str(HERE/'previews'/f'{SLUG}.png');bpy.ops.render.render(write_still=True)
