"""Original V2.1 P0 435 pendant sprinkler visual prop, not functional equipment.
Metres; mount plane Z=0, pendant downward -Z. No external inputs or random seed.
"""
from pathlib import Path
import bpy,bmesh,math,json,struct,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-sprinkler-head';ROOT='ASSET_MallSprinklerHead'
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
def studio():
    s=bpy.context.scene
    for name,pos,energy,size in [('Key',(-.16,-.20,-.06),8,.16),('Fill',(.16,-.13,-.09),5,.16),('Rim',(.04,.17,.08),9,.13)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=energy;o.data.size=size;point_at(o,(0,0,-.02))
    bpy.ops.object.camera_add(location=(.10,-.20,-.10));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.10;point_at(s.camera,(0,0,-.017))
    s.world=bpy.data.worlds.new('Studio environment');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.22,.25,.29,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.7
    s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    root=empty(ROOT)
    brass=material('Warm satin brass',(171,133,68),.65,.32)
    chrome=material('Satin nickel finish',(183,191,196),.72,.3)
    ivory=material('Ivory coated ceiling trim',(232,231,219),.12,.36)
    red=material('Opaque glossy red bulb representation',(173,24,32),0,.18)
    # Non-functional annular ridge representation of a threaded fitting, not a thread specification.
    profile=[(.004,.001),(.009,.001)]
    for i in range(5):
        z=.002+i*.003
        profile.extend([(.009,z),(.0105,z+.0007),(.0105,z+.0013),(.009,z+.002)])
    profile.extend([(.009,.019),(.004,.019)])
    lathe('MODULE_ThreadedFitting',profile,brass,root)
    body=cylinder('MODULE_HexBody',-.004,.014,.010,brass,root,6);body.rotation_euler.z=math.pi/6
    lathe('MODULE_CeilingTrim',[(.015,0),(.031,0),(.033,-.0015),(.033,-.003),(.030,-.004),(.015,-.004)],ivory,root)
    cylinder('MODULE_BodyCollar',-.010,.010,.004,chrome,root)
    arm=[(.0075,-.011),(.011,-.011),(.014,-.019),(.013,-.036),(.008,-.044),(.005,-.042),(.009,-.034),(.010,-.020)]
    prism('MODULE_YokeRight',arm,.004,brass,root)
    prism('MODULE_YokeLeft',[(-x,z) for x,z in reversed(arm)],.004,brass,root)
    prism('MODULE_YokeBridge',[(-.007,-.041),(.007,-.041),(.007,-.045),(-.007,-.045)],.004,brass,root)
    cylinder('MODULE_BulbUpperSeat',-.0135,.0035,.003,chrome,root,16)
    cylinder('MODULE_BulbLowerSeat',-.040,.0035,.004,chrome,root,16)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1,location=(0,0,-.0265))
    bulb=bpy.context.object;bulb.name='MODULE_Bulb';bulb.scale=(.0027,.0027,.012);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bulb.parent=root;bulb.data.materials.append(red)
    for f in bulb.data.polygons:f.use_smooth=True
    cylinder('MODULE_DeflectorStem',-.0465,.0028,.005,chrome,root,16)
    # 12 original blunt teeth, closed solid profile; visual deflector only.
    pts=[((.0155 if i%4 in (0,1) else .0125)*math.cos(2*math.pi*i/48),(.0155 if i%4 in (0,1) else .0125)*math.sin(2*math.pi*i/48)) for i in range(48)]
    verts=[(x,y,z) for z in [-.051,-.049] for x,y in pts];n=len(pts)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh('MODULE_Deflector',verts,faces,chrome,root)
    cylinder('MODULE_DeflectorButton',-.0515,.004,.001,brass,root,16)
    empty('CONNECTOR_CeilingMountPlane',root)
    root['units']='metres';root['backlog']='V2.1 P0 item 435'
    root['scope']='Visual prop only; no temperature rating, flow, fire protection, installation or certification claims. No activation or simulation.'
    root['placement']='Mount-plane origin Z=0; fitting above plane; pendant hangs along -Z. glTF +Y is up, pendant hangs -Y.'
    root['bulb']='Opaque glossy red representation. No physical glass, refraction or temperature encoding.'
    studio();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'),compress=True);return root
if __name__=='__main__':
    for name in ['sources','exports','previews','reports']:(HERE/name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'));root=bpy.data.objects[ROOT]
    else:root=build()
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:s=bpy.context.scene;s.render.filepath=str(HERE/'previews'/f'{SLUG}.png');bpy.ops.render.render(write_still=True)
