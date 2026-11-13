"""Original V2.1 P0 437 landscape digital panel. Static artwork, no connected functionality."""
from pathlib import Path
import bpy,bmesh,math,json,struct,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-digital-advertising-screen';ROOT='ASSET_MallDigitalAdvertisingScreen'
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
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=True,export_cameras=False,export_lights=False)
    data=path.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);mats=[];mapping={}
    for i,m in enumerate(doc['materials']):
        if m not in mats:mats.append(m)
        mapping[i]=mats.index(m)
    for me in doc['meshes']:
        for p in me['primitives']:p['material']=mapping[p['material']]
    doc['materials']=mats
    textures=[];texture_map={}
    for i,t in enumerate(doc.get('textures',[])):
        if t not in textures:textures.append(t)
        texture_map[i]=textures.index(t)
    for m in mats:
        if 'emissiveTexture' in m:m['emissiveTexture']['index']=texture_map[m['emissiveTexture']['index']]
        pbr=m.get('pbrMetallicRoughness',{})
        if 'baseColorTexture' in pbr:pbr['baseColorTexture']['index']=texture_map[pbr['baseColorTexture']['index']]
    if textures:doc['textures']=textures
    chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*(-len(chunk)%4);tail=data[20+n:];path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)

def bevel(o,width=.002,segments=3):
    bpy.context.view_layer.objects.active=o
    m=o.modifiers.new('Soft original edges','BEVEL');m.width=width;m.segments=segments
    bpy.ops.object.modifier_apply(modifier=m.name)
    return o
def disc(name,location,radius,depth,mat,parent,axis='Z',rounded=False):
    o=cylinder(name,0,radius,depth,mat,parent,32);o.location=location
    if axis=='Y':o.rotation_euler.x=math.pi/2
    elif axis=='X':o.rotation_euler.y=math.pi/2
    if rounded:bevel(o,.004)
    return o
def box(name,location,size,mat,parent,segments=3):
    bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.location=location;o.parent=parent;o.data.materials.append(mat);bevel(o,min(.002,min(size)*.25),segments);return o
def artwork():
    # Original vector-style composition. Bfont is Blender-bundled; no external art/font files.
    s=bpy.data.scenes.new('EDITABLE_Artwork');bpy.context.window.scene=s
    s.render.engine='CYCLES';s.cycles.samples=1;s.cycles.use_denoising=False
    s.render.resolution_x=1024;s.render.resolution_y=576;s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.view_settings.view_transform='Standard'
    s.world=bpy.data.worlds.new('Artwork world')
    def ink(name,rgb):
        m=material(name,rgb);p=m.node_tree.nodes['Principled BSDF']
        out=m.node_tree.nodes['Material Output'];e=m.node_tree.nodes.new('ShaderNodeEmission');e.inputs['Color'].default_value=m.diffuse_color;e.inputs['Strength'].default_value=1;m.node_tree.links.new(e.outputs[0],out.inputs[0]);return m
    navy=ink('Art navy',(17,34,49));cream=ink('Art cream',(248,240,220));orange=ink('Art orange',(240,145,89));mint=ink('Art mint',(144,197,178))
    def rect(n,x,y,w,h,mat,z=0):return box('ARTWORK_'+n,(x,y,z),(w,h,.01),mat,None)
    def text(n,body,x,y,size,mat):
        c=bpy.data.curves.new(n,'FONT');c.body=body;c.size=size;c.space_character=1.15;c.align_y='BOTTOM_BASELINE'
        o=bpy.data.objects.new('ARTWORK_'+n,c);s.collection.objects.link(o);o.location=(x,y,.04);c.materials.append(mat)
    rect('Background',0,0,16,9,navy)
    text('Eyebrow','W E E K E N D',-6.8,3.05,.36,mint)
    text('Title1','FRESH',-6.9,.70,1.55,cream);text('Title2','FINDS',-6.9,-.90,1.55,cream)
    rect('Rule',-3.7,-1.65,6.15,.035,mint,.03)
    text('Footer','DESIGN / FOOD / CULTURE',-6.8,-2.4,.27,cream)
    text('Caption','A LITTLE SOMETHING DIFFERENT',-6.8,-3.15,.20,mint)
    # Layered abstract arch and offset discs on the right, not an official brand/campaign.
    rect('MintPanel',4.5,-.35,4.3,5.0,mint,.01)
    bpy.ops.mesh.primitive_circle_add(vertices=64,radius=2.15,fill_type='NGON',location=(4.5,2.15,.02));bpy.context.object.name='ARTWORK_Arch';bpy.context.object.data.materials.append(mint)
    rect('OrangePanel',5.25,-1.30,2.8,4.1,orange,.04)
    bpy.ops.mesh.primitive_circle_add(vertices=64,radius=1.4,fill_type='NGON',location=(5.25,.75,.05));bpy.context.object.name='ARTWORK_OrangeArch';bpy.context.object.data.materials.append(orange)
    bpy.ops.mesh.primitive_circle_add(vertices=64,radius=.8,fill_type='NGON',location=(2.55,-2.60,.06));bpy.context.object.name='ARTWORK_CreamDisc';bpy.context.object.data.materials.append(cream)
    bpy.ops.object.camera_add(location=(0,0,10));s.camera=bpy.context.object;s.camera.name='ARTWORK_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=16
    s.render.filepath=str(HERE/'sources/screen-artwork.png');bpy.ops.render.render(write_still=True)
    return s
def studio():
    s=bpy.context.scene
    for name,pos,energy,size in [('Key',(-2,-3,3),160,3),('Fill',(2,-2,1),90,2),('Rim',(1,2,2),220,2)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=energy;o.data.size=size;point_at(o,(0,-.04,0))
    bpy.ops.object.camera_add(location=(1.4,-3,.8));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=1.62;point_at(s.camera,(0,-.04,0))
    s.world=bpy.data.worlds.new('Studio environment');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.19,.22,.26,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.name='MODEL_DigitalPanel'
    artwork();bpy.context.window.scene=s;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    root=empty(ROOT);empty('CONNECTOR_WallMountPlane',root)
    charcoal=material('Charcoal anodized bezel',(30,35,39),.45,.36)
    rear=material('Satin graphite housing',(55,62,67),.25,.52)
    dark=material('Vent recess and screen edge',(10,14,17),0,.65)
    steel=material('Mounting rail satin metal',(109,116,121),.7,.36)
    box('MODULE_RearHousing',(0,-.042,0),(1.25,.05,.725),rear,root)
    # Four separate bezel bars. Front is -Y; wall-plane anchor is rear Y=0.
    for n,x,z,w,h in [('Top',0,.3575,1.28,.04),('Bottom',0,-.3575,1.28,.04),('Left',-.62,0,.04,.675),('Right',.62,0,.04,.675)]:
        box('MODULE_Bezel'+n,(x,-.071,z),(w,.028,h),charcoal,root)
    screenmat=material('Screen original replaceable artwork',(255,255,255),0,.8)
    bsdf=screenmat.node_tree.nodes['Principled BSDF'];bsdf.inputs['Specular IOR Level'].default_value=0
    image=bpy.data.images.load(str(HERE/'sources/screen-artwork.png'));image.name='REPLACEABLE_ScreenArtwork';image.pack()
    tex=screenmat.node_tree.nodes.new('ShaderNodeTexImage');tex.name='REPLACE_SCREEN_IMAGE';tex.image=image
    screenmat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);screenmat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Emission Color']);bsdf.inputs['Emission Strength'].default_value=.75
    # Closed thin screen slab, custom UVs with left-to-right artwork on the front.
    screen=box('MODULE_ScreenContent',(0,-.0795,0),(1.20,.003,.675),screenmat,root)
    uv=screen.data.uv_layers.active or screen.data.uv_layers.new(name='ScreenUV')
    for poly in screen.data.polygons:
        for li in poly.loop_indices:
            v=screen.data.vertices[screen.data.loops[li].vertex_index].co
            uv.data[li].uv=(v.x/1.20+.5,v.z/.675+.5)
    screen['edit']='Replace packed REPLACEABLE_ScreenArtwork or edit ARTWORK scene and render 1024 x 576 PNG; reload/repack image. Housing independent.'
    for x,label in [(-.40,'Left'),(.40,'Right')]:
        box('MODULE_MountRail'+label,(x,-.009,0),(.055,.018,.46),steel,root)
        for z,suffix in [(-.18,'Bottom'),(.18,'Top')]:
            d=disc('MODULE_MountFastener'+label+suffix,(x,-.0009,z),.008,.0018,dark,root,'Y')
    box('MODULE_RearServicePanel',(0,-.014,0),(.52,.006,.34),charcoal,root)
    # Visible modeled ventilation grille ribs over a recessed dark channel.
    for z,label in [(.28,'Upper'),(-.28,'Lower')]:
        box('MODULE_VentRecess'+label,(0,-.0155,z),(.90,.003,.055),dark,root)
        pieces=[]
        for i in range(29):
            pieces.append(box('VentRib',(-.435+i*.03,-.011,z),(.012,.006,.055),rear,root,segments=1))
        bpy.ops.object.select_all(action='DESELECT')
        for o in pieces:o.select_set(True)
        bpy.context.view_layer.objects.active=pieces[0];bpy.ops.object.join();pieces[0].name='MODULE_VentGrille'+label
    root['units']='metres';root['backlog']='V2.1 P0 item 437'
    root['scope']='Static emissive digital advertising screen visual prop. No video, live CMS, touch, network or electrical functionality.'
    root['placement']='Rear wall plane Y=0; front -Y; GLB rear Z=0 and front +Z. Panel centre anchor, not floor origin.'
    studio();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'),compress=True);return root
if __name__=='__main__':
    for n in ['sources','exports','previews','reports']:(HERE/n).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'));root=bpy.data.objects[ROOT]
    else:root=build()
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:s=bpy.context.scene;s.render.filepath=str(HERE/'previews'/f'{SLUG}.png');bpy.ops.render.render(write_still=True)
