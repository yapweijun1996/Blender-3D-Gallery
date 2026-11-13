"""Original visual mall column, metres; no structural/load/code certification.
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
    s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
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


SLUG='hdb-staircase';ROOT='ASSET_HDBStaircase'
RISE=1.5;COUNT=9;TREAD=.28;WIDTH=1.2;GAP=.20
def beam(name,a,b,r,mat,parent):
    a,b=Vector(a),Vector(b);o=cylinder(name,(a+b)/2,r,(b-a).length,mat);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();attach(o,parent)
def step(name,x,ya,yb,top,low_a,low_b,mat,parent):
    lo=x-WIDTH/2;hi=x+WIDTH/2
    v=[(lo,ya,top),(lo,yb,top),(lo,yb,low_b),(lo,ya,low_a),(hi,ya,top),(hi,yb,top),(hi,yb,low_b),(hi,ya,low_a)]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o);o.data.materials.append(mat);attach(o,parent)
    # Recalculate normals for the reversed second-flight profile.
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    return o
def build():
    concrete=material('Warm off-white precast concrete',(209,205,187),.85)
    tread=material('Charcoal anti-slip nosings',(85,90,86),.9)
    rail=material('Painted muted teal handrails',(56,105,104),.4,.15)
    root=empty(ROOT); stairs=empty('STAIRS_EditableFlights',root);rails=empty('RAILS_EditableMembers',root)
    for flight,x in [(0,-.7),(1,.7)]:
        for i in range(COUNT):
            y=-1.26+(i+.5)*TREAD if flight==0 else 1.26-(i+.5)*TREAD
            z=(i+1)*RISE/COUNT+flight*RISE
            # Solid concrete rectangular stepped blocks, no concealed geometry duplication.
            step('STEP_%d_%02d'%(flight,i+1),x,y-TREAD/2 if flight==0 else y+TREAD/2,y+TREAD/2 if flight==0 else y-TREAD/2,z,max(0,z-RISE/COUNT-.15),max(0,z-.15),concrete,stairs)
            edge=y-TREAD/2+.018 if flight==0 else y+TREAD/2-.018
            attach(box('NOSING_%d_%02d'%(flight,i+1),(x,edge,z+.002),(WIDTH-.04,.035,.004),tread,0),stairs)
        # continuous sloping support stringers on each flight
        for side in [-1,1]:
            xx=x+side*.56
            a=(xx,-1.26,.055) if flight==0 else (xx,1.26,RISE)
            b=(xx,1.26,RISE) if flight==0 else (xx,-1.26,2*RISE)
            # Closed wedge steps form a continuous solid waist, no separate rods.
            for i in range(COUNT):
                y=-1.26+(i+.5)*TREAD if flight==0 else 1.26-(i+.5)*TREAD
                z=(i+1)*RISE/COUNT+flight*RISE
                beam('BALUSTER_%d_%d_%d'%(flight,side,i),(xx,y,z),(xx,y,z+.95),.016,rail,rails)
            ya=-1.26+.5*TREAD if flight==0 else 1.26-.5*TREAD
            yb=1.26-.5*TREAD if flight==0 else -1.26+.5*TREAD
            za=RISE/COUNT+flight*RISE+.95;zb=(flight+1)*RISE+.95
            beam('HANDRAIL_%d_%d'%(flight,side),(xx,ya,za),(xx,yb,zb),.025,rail,rails)
    attach(box('LANDING_HalfStorey',(0,1.86,RISE-.10),(2.6,1.2,.20),concrete,.003),stairs)
    # Rear landing guard joins both outer stair rails; interior landing stays walkable.
    for xx in [-1.26,-.84,-.42,0,.42,.84,1.26]:
        beam('LANDING_GuardPost_'+str(xx),(xx,2.42,RISE),(xx,2.42,RISE+.95),.016,rail,rails)
    beam('LANDING_RearHandrail',(-1.26,2.42,RISE+.95),(1.26,2.42,RISE+.95),.025,rail,rails)
    for xx in [-1.26,1.26]:
        for yy in [1.5,1.96]:
            beam('LANDING_SidePost_'+str(xx)+'_'+str(yy),(xx,yy,RISE),(xx,yy,RISE+.95),.016,rail,rails)
        beam('LANDING_SideRail_'+str(xx),(xx,1.12,RISE+.95),(xx,2.42,RISE+.95),.025,rail,rails)
    empty('CONNECTOR_LowerFloor',root,(-.7,-1.26,0))
    empty('CONNECTOR_UpperFloor',root,(.7,-1.26,3))
    root['backlog_id']=301;root['units']='metres';root['storey_rise_m']=3.0;root['riser_count']=18;root['tread_depth_m']=TREAD
    root['scope']='Generic HDB-inspired visual staircase, not a surveyed estate, compliant escape stair or structural design.'
    return root
def main():
    if '--export-source' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
        root=build();studio();s.camera.location=(6,-8,6);s.camera.data.ortho_scale=6.3;point_at(s.camera,(0,.45,1.8))
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
    export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
