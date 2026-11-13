"""Original visual HDB Car Park Ramp, metres; no structural/load/code certification.
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


def beam(name,a,b,r,mat,parent):
    a,b=Vector(a),Vector(b);o=cylinder(name,(a+b)/2,r,(b-a).length,mat);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();attach(o,parent)
def lathe(name,profile,mat,parent,N=48,spout=False):
    import math,bmesh
    verts=[]
    for r,z in profile:
        for i in range(N):
            a=i*2*math.pi/N;delta=.016*max(0,-math.cos(a))**16 if spout and z>.205 else 0
            verts.append(((r+delta)*math.cos(a),(r+delta)*math.sin(a),z))
    faces=[]
    for j in range(len(profile)-1):
        for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
    faces.append(tuple(reversed(range(N))));faces.append(tuple((len(profile)-1)*N+i for i in range(N)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(mat);attach(o,parent)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for poly in mesh.polygons:poly.use_smooth=len(poly.vertices)==4
    return o
def ring(name,loc,radius,tube,mat,parent):
    bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=8,major_radius=radius,minor_radius=tube,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);attach(o,parent);return o
def rounded_path(prefix,points,r,mat,parent):
    for i in range(len(points)-1):beam(prefix+'_Segment_'+str(i),points[i],points[i+1],r,mat,parent)
    for i,p in enumerate(points):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=r,location=p);o=bpy.context.object;o.name=prefix+'_Joint_'+str(i);o.data.materials.append(mat);attach(o,parent)

def wedge(name,halfwidth,y0,y1,z0,z1,thickness,mat,parent):
    import bmesh
    verts=[(-halfwidth,y0,z0), (halfwidth,y0,z0),(halfwidth,y1,z1),(-halfwidth,y1,z1),(-halfwidth,y0,z0+thickness),(halfwidth,y0,z0+thickness),(halfwidth,y1,z1+thickness),(-halfwidth,y1,z1+thickness)]
    faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(mat);attach(o,parent)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();return o
def arrow(name,x,y,z,size,mat,parent):
    # Original vertical-panel arrow: up arrow with separate shaft and triangular head.
    attach(box(name+'_Shaft',(x,y,z-size*.15),(size*.16,.012,size*.5),mat,0),parent)
    verts=[(x-size*.3,y,z+size*.05),(x+size*.3,y,z+size*.05),(x,y,z+size*.42)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],[(0,1,2),(2,1,0)]);mesh.update();o=bpy.data.objects.new(name+'_Head',mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(mat);attach(o,parent)
def parking_lines(root,mat,yellow):
    for i,x in enumerate([-1.35,-.45,.45,1.35]):attach(box('MARK_BayLine_'+str(i),(x,0,.123),(.07,2.2,.006),mat,0),root)
    for i,x in enumerate([-.9,0,.9]):
        attach(box('STOP_'+str(i),(x,.8,.18),(.6,.13,.12),yellow,.02),root)
    attach(box('MARK_Front',(0,-1.07,.123),(2.75,.06,.006),mat,0),root)

SLUG='hdb-car-park-ramp';ROOT='ASSET_HDBCarParkRamp'
def build():

    root=empty(ROOT);concrete=material('Ramp concrete',(154,158,152),.9);road=material('Ramp wearing course',(66,72,71),.9);yellow=material('Edge caution paint',(219,180,54),.8);white=material('Centre marking',(228,230,216),.85)
    wedge('STRUCTURE_Ramp',2.8,-5,5,0,1.2,.18,concrete,root)
    wedge('SURFACE_Road',2.52,-5,5,.18,1.38,.025,road,root)
    for side in [-1,1]:
        o=wedge('PARAPET_'+str(side),.13,-5,5,.18,1.38,.75,concrete,root);o.location.x=side*2.67
        o=wedge('MARK_Edge_'+str(side),.05,-4.95,4.95,.207,1.395,.005,yellow,root);o.location.x=side*2.38
    for i in range(8):
        y=-4.4+i*1.2;wedge('MARK_Dash_'+str(i),.045,y,y+.55,.208+(y+5)*.12,.208+(y+.55+5)*.12,.005,white,root)
    empty('CONNECTOR_Lower',root,(0,-5,.205));empty('CONNECTOR_Upper',root,(0,5,1.405))
    root['grade_note']='Illustrative 1.2m rise over10m run; not an approved accessibility or vehicle-design standard.'
    return root

def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();root['units']='metres';root['backlog_id']=388
        studio();
        for light in [o for o in s.objects if o.type=='LIGHT']:light.location*=max(1,14/3);light.data.energy*=max(1,14/3)**2;light.data.size*=max(1,14/3)
        s.camera.location=(13, -17, 12);s.camera.data.ortho_scale=14;point_at(s.camera,(0, 0, 1.1))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
