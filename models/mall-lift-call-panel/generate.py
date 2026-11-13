"""Original V2.1 P0 item 431. Metres. Static geometry; no elevator logic.
--export-source preserves source edits instead of rebuilding the asset.
"""
from pathlib import Path
import bpy, bmesh, math, json, struct, sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
SLUG='mall-lift-call-panel'; ROOT='ASSET_MallLiftCallPanel'

def material(name,rgb,metallic=0,roughness=.4,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    def linear(v):
        v/=255
        return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    color=(*[linear(v) for v in rgb],1);p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=color;p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness
    if emission:p.inputs['Emission Color'].default_value=color;p.inputs['Emission Strength'].default_value=emission
    m.diffuse_color=color;return m

def mesh(name,verts,faces,mat):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update()
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
    o=bpy.data.objects.new(name,d);bpy.context.scene.collection.objects.link(o);d.materials.append(mat);return o

def empty(name,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;o.location=loc;return o

def cube(name,loc,size,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if bevel:
        m=o.modifiers.new('Small real edge radius','BEVEL');m.width=bevel;m.segments=3
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o

def cylinder(name,loc,r,depth,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=depth,location=loc,rotation=(math.pi/2,0,0))
    o=bpy.context.object;o.name=name;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    if mat:o.data.materials.append(mat)
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o

def annulus(name,z,outer,inner,y0,y1,mat):
    n=48;v=[(r*math.cos(2*math.pi*i/n),y,z+r*math.sin(2*math.pi*i/n)) for r,y in [(outer,y0),(inner,y0),(outer,y1),(inner,y1)] for i in range(n)];f=[]
    for i in range(n):
        j=(i+1)%n
        f.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return mesh(name,v,f,mat)

def extrude(name,outline,y0,y1,mat):
    n=len(outline);v=[(x,y,z) for y in (y0,y1) for x,z in outline]
    return mesh(name,v,[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)

def point_at(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()

def export(root,path):
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
    data=path.read_bytes();n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n]);mats=[];mapping={}
    for i,m in enumerate(doc['materials']):
        if m not in mats:mats.append(m)
        mapping[i]=mats.index(m)
    for m in doc['meshes']:
        for p in m['primitives']:p['material']=mapping[p['material']]
    doc['materials']=mats;chunk=json.dumps(doc,separators=(',',':')).encode();chunk+=b' '*(-len(chunk)%4);tail=data[20+n:]
    path.write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)

def studio():
    s=bpy.context.scene;bg=material('STUDIO soft grey',(215,221,222),roughness=.9)
    cube('STUDIO_Wall',(0,.045,.17),(3,.05,3),bg)
    for name,pos,energy,size in [('Key',(-.3,-.5,.65),18,.45),('Fill',(.4,-.3,.25),8,.35),('Edge',(.2,.1,.6),12,.3)]:
        bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name='STUDIO_'+name;o.data.energy=energy;o.data.size=size;point_at(o,(0,0,.17))
    bpy.ops.object.camera_add(location=(.34,-.7,.43));s.camera=bpy.context.object;s.camera.name='STUDIO_Camera';s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.43;point_at(s.camera,(0,-.01,.17))
    s.world=bpy.data.worlds.new('Studio environment');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.39,.42,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
    s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=False
    s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'

def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    root=empty(ROOT);steel=material('Satin stainless faceplate',(179,189,195),.72,.33);housing=material('Charcoal housing',(43,49,54),.35,.45);rim=material('Polished stainless rims',(174,185,193),.82,.2);cap=material('Dark button faces',(37,45,51),.15,.35);amber=material('Amber static arrow indicators',(255,179,67),0,.35,.7);slot=material('Fastener slot recess',(20,24,27),0,.7)
    # Closed single connected cup shell; wall thickness 1.5 mm, back on mounting plane Y=0.
    outer=[(-.063,.007),(.063,.007),(.063,.333),(-.063,.333)];inner=[(-.0615,.0085),(.0615,.0085),(.0615,.3315),(-.0615,.3315)]
    v=[(x,y,z) for pts,y in [(outer,0),(outer,-.026),(inner,-.0015),(inner,-.026)] for x,z in pts]
    f=[(0,1,2,3),(8,11,10,9)]
    for i in range(4):j=(i+1)%4;f.extend([(i,4+i,4+j,j),(4+i,12+i,12+j,4+j),(8+i,8+j,12+j,12+i)])
    body=mesh('MODULE_Housing',v,f,housing);body.parent=root
    plate=cube('MODULE_MetalFaceplate',(0,-.0275,.17),(.14,.003,.34),steel,.001);plate.parent=root
    for direction,z in [('Up',.225),('Down',.115)]:
        cutter=cylinder('TEMP_aperture',(0,-.0275,z),.025,.02,None)
        bpy.context.view_layer.objects.active=plate;mod=plate.modifiers.new('True button aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
        bezel=annulus('MODULE_Bezel_'+direction,z,.029,.025,-.032,-.029,rim);bezel.parent=root
        pivot=empty('PIVOT_Button_'+direction,root,(0,-.03225,z));pivot['travel_m']=.002;pivot['press_axis']='Blender +Y / glTF -Z';pivot['note']='Source pose only; no runtime interaction or call wiring.'
        button=cylinder('MODULE_Button_'+direction,(0,0,0),.024,.0035,cap);button.parent=pivot
        outline=[(-.009,-.0025),(-.0035,-.0025),(-.0035,-.010),(.0035,-.010),(.0035,-.0025),(.009,-.0025),(0,.010)]
        sign=1 if direction=='Up' else -1
        icon=extrude('MODULE_Arrow_'+direction,[(x,sign*z) for x,z in outline],-.00215,-.00175,amber);icon.parent=pivot
    for ix,x in enumerate([-.049,.049]):
        for iz,z in enumerate([.024,.316]):
            o=cylinder('MODULE_Fastener_'+str(ix)+str(iz),(x,-.0298,z),.003,.0016,rim);o.parent=root
            o=cube('MODULE_FastenerSlot_'+str(ix)+str(iz),(x,-.03065,z),(.0038,.00015,.0007),slot);o.parent=root
    empty('CONNECTOR_WallMount',root,(0,0,.17));empty('CONNECTOR_PanelBottom',root)
    root['units']='metres';root['backlog']='V2.1 P0 item 431';root['scope']='Generic wall lift call panel only, not lift or floor indicator 432. No electrical connection, elevator call logic, tactile or code compliance.'
    root['wall_mount']='CONNECTOR_WallMount at (0,0,0.17); wall plane Blender Y=0; front is -Y; bottom datum Z=0; choose installation height externally.'
    studio();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'),compress=True);return root

if __name__=='__main__':
    for name in ['sources','exports','previews','reports']:(HERE/name).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/f'{SLUG}.blend'));root=bpy.data.objects[ROOT]
    else:root=build()
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:s=bpy.context.scene;s.render.filepath=str(HERE/'previews'/f'{SLUG}.png');bpy.ops.render.render(write_still=True)
