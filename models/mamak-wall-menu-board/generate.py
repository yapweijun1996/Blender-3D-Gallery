"""Original visual Mamak Wall Menu Board, metres; no structural/load/code certification.
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

SLUG='mamak-wall-menu-board';ROOT='ASSET_MamakWallMenuBoard'
def build():

    wood=material('Dark warm frame',(95,69,42),.78);board=material('Deep green menu face',(28,62,51),.92);white=material('Ivory pixel lettering',(230,228,202),.8);gold=material('Blank price label plates',(187,169,106),.7);root=empty(ROOT)
    attach(box('BOARD_Back',(0,0,.35),(1.0,.035,.70),wood,.006),root)
    attach(box('BOARD_Face',(0,-.023,.35),(.92,.012,.62),board,.003),root)
    # Hand-defined original 5x7 bitmap glyphs, no external font or artwork.
    glyph={'M':['10001','11011','10101','10001','10001','10001','10001'],'E':['11111','10000','10000','11110','10000','10000','11111'],'N':['10001','11001','11001','10101','10011','10011','10001'],'U':['10001','10001','10001','10001','10001','10001','01110'],'T':['11111','00100','00100','00100','00100','00100','00100'],'H':['10001','10001','10001','11111','10001','10001','10001'],'C':['01111','10000','10000','10000','10000','10000','01111'],'R':['11110','10001','10001','11110','10100','10010','10001'],'Y':['10001','10001','01010','00100','00100','00100','00100'],'O':['01110','10001','10001','10001','10001','10001','01110'],'I':['11111','00100','00100','00100','00100','00100','11111'],'S':['01111','10000','10000','01110','00001','00001','11110'],'A':['01110','10001','10001','11111','10001','10001','10001']}
    def word(text,x,z,pixel):
        verts=[];faces=[]
        for ci,ch in enumerate(text):
            for row,line in enumerate(glyph[ch]):
                for col,on in enumerate(line):
                    if on=='1':
                        xx=x+(ci*6+col)*pixel;zz=z-row*pixel;idx=len(verts);a=pixel*.86
                        verts.extend([(xx,-.030,zz),(xx+a,-.030,zz),(xx+a,-.030,zz+a),(xx,-.030,zz+a)]);faces.append((idx,idx+1,idx+2,idx+3))
        mesh=bpy.data.meshes.new('Letters_'+text);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('LABEL_'+text,mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(white);attach(o,root)
    word('MENU',-.19,.60,.016)
    for text,z in [('TEH',.45),('CURRY',.34),('ROTI',.23),('SATAY',.12)]:
        word(text,-.40,z,.010);attach(box('PRICE_Replaceable_'+text,(.30,-.032,z-.018),(.20,.008,.055),gold,.002),root)
    root['placeholder_content']='Generic TEH / CURRY / ROTI / SATAY labels; blank price panels. No advertised prices or actual business claim.'
    return root

def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();root['units']='metres';root['backlog_id']=378
        studio();s.camera.location=(1.4, -2.1, 1.15);s.camera.data.ortho_scale=1.35;point_at(s.camera,(0, 0, 0.35))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
