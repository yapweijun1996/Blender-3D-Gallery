"""Original escalator landing module, metres; no structural/load/code certification.
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
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True,export_texcoords=True,export_cameras=False,export_lights=False)
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


SLUG='mall-escalator-landing';ROOT='ASSET_MallEscalatorLanding'
def extruded_profile(name,profile,a,b,mat,axis):
    # CCW profile in its 2D plane; cap direction is corrected with bmesh.
    import bmesh
    def point(p,t):return (p[0],t,p[1]) if axis=='y' else (p[0],p[1],t)
    n=len(profile);v=[point(p,t) for t in (a,b) for p in profile]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);mesh.materials.append(mat);return o

def plate(name,y0,y1,mat):
    # One closed corrugated plate, not dozens of overlapping rib boxes.
    top=[(-.538,.027)]
    for i in range(25):
        x=-.48+i*.04;top.extend([(x-.009,.027),(x-.009,.030),(x+.009,.030),(x+.009,.027)])
    top.append((.538,.027));profile=[(-.538,.012),(.538,.012)]+list(reversed(top))
    return extruded_profile(name,profile,y0,y1,mat,'y')

def main():
    for d in ('sources','exports','previews','reports'):(HERE/d).mkdir(exist_ok=True)
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=empty(ROOT)
        plate_mat=material('Satin aluminium access plates',(166,179,182),.34,.68)
        trim=material('Brushed stainless side trims',(103,119,124),.30,.72)
        tray=material('Charcoal recessed support tray',(31,39,42),.65,.15)
        comb=material('Cast aluminium comb transition',(139,151,155),.40,.55)
        yellow=material('Safety yellow visual marker',(235,178,39),.45,.1)
        attach(box('MODULE_SupportTray',(0,-.04,.006),(1.08,1.12,.012),tray,0),root)
        for name,x in [('Left',-.57),('Right',.57)]:attach(box('MODULE_SideTrim_'+name,(x,0,.015),(.06,1.2,.03),trim,.0005),root)
        attach(box('MODULE_FloorThreshold',(0,-.57,.021),(1.08,.06,.018),trim,.0005),root)
        attach(plate('MODULE_AccessPlate_Front',-.538,-.061,plate_mat),root)
        attach(plate('MODULE_AccessPlate_Rear',-.059,.418,plate_mat),root)
        # Coarse original comb silhouette. Not a manufacturer tooth/step interface.
        profile=[(-.54,.420),(.54,.420),(.54,.520)]
        for i in range(26,-1,-1):
            x=-.52+i*.04;profile.extend([(x+.011,.520),(x+.011,.600),(x-.011,.600),(x-.011,.520)])
        profile.append((-.54,.520))
        attach(extruded_profile('MODULE_CombTransition',profile,.012,.029,comb,'z'),root)
        attach(box('MODULE_YellowMarker',(0,.444,.0295),(1.076,.024,.001),yellow,0),root)
        for name,loc in [('FloorSide',(0,-.6,.03)),('FutureEscalator',(0,.6,.03)),('Underside',(0,0,0)),('LeftEdge',(-.6,0,.03)),('RightEdge',(.6,0,.03))]:empty('CONNECTOR_'+name,root,loc)
        root['units']='metres';root['backlog']='V2.1 P0 item 429';root['floor_surface_height_m']=.03
        root['origin']='Module underside centre. Blender -Y faces mall floor, +Y faces future escalator; glTF +Z faces floor.'
        root['scope']='Static landing threshold/access plate visual module only. No moving transport, manufacturer, safety, slip-resistance or code certification.'
        root['assembly']='Actual 421 floor root at glTF (0,0,1.2): matching 1.2 m width and 30 mm top. Future interface at glTF Z=-0.6 is provisional and NOT tested against an escalator.'
        studio();s.camera.location=(2.3,-3,3.2);s.camera.data.ortho_scale=1.85;point_at(s.camera,(0,0,.015));s.cycles.samples=32
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports/optimized.glb')
    if '--skip-render' not in sys.argv:
        bpy.context.scene.render.filepath=str(HERE/'previews'/(SLUG+'.png'));bpy.ops.render.render(write_still=True)
if __name__=='__main__':main()
