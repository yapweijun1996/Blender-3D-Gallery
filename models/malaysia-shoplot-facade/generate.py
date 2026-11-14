"""Original reusable civic prop or architectural shell, metres; no structural/load/code certification.
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
    s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=False;s.render.resolution_x=s.render.resolution_y=768;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
def export(root,destination):
    bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for o in root.children_recursive:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(destination),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=True,export_extras=True,export_texcoords=False,export_cameras=False,export_lights=False)
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


def build():
 import hashlib
 spec=json.loads((HERE/'backlog.json').read_text());parent=runpy.run_path(str(HERE/'provenance/parent-generator.py'))
 if spec['id']==175:
  old=parent['empty'](parent['ROOT']);parent['build'](old)
 else:old=parent['build']()
 bpy.context.view_layer.update()
 keep=set()
 for obj in old.children_recursive:
  if any(obj.name.startswith(p) for p in spec['prefixes']) or obj.name in spec.get('exact_names',[]):keep.add(obj);keep.update(obj.children_recursive)
 assert keep and all(o.type in ['EMPTY','MESH'] for o in keep)
 meshes=[o for o in keep if o.type=='MESH'];deps=bpy.context.evaluated_depsgraph_get();pts=[]
 for o in meshes:
  e=o.evaluated_get(deps);pts.extend(e.matrix_world@v.co for v in e.data.vertices)
 lo=Vector([min(p[i] for p in pts) for i in range(3)]);hi=Vector([max(p[i] for p in pts) for i in range(3)])
 shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z));records=[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None} for o in sorted(keep,key=lambda o:o.name)]
 tops=[o for o in keep if o.parent not in keep]
 new=empty(ROOT)
 for o in tops:
  matrix=o.matrix_world.copy();o.parent=new;o.matrix_world=matrix;o.matrix_world.translation+=shift
 for o in list(bpy.context.scene.objects):
  if o!=new and o not in keep:bpy.data.objects.remove(o,do_unlink=True)
 new['units']='metres';new['backlog_id']=spec['id'];new['kind']='DERIVED EXTRACTION';new['parent_asset']=spec['parent'];new['count_policy']='Independent derivative packaging; novel model count pending owner policy'
 report={'kind':'DERIVED EXTRACTION','parent_asset':spec['parent'],'parent_generator_sha256':hashlib.sha256((HERE/'provenance/parent-generator.py').read_bytes()).hexdigest(),'source_origin_shift_blender':list(shift),'source_bounds_before':{'min':list(lo),'max':list(hi)},'kept_objects':records,'geometry_edits':'NONE: subset selection and one rigid origin translation only','count_policy':'NOT counted as new design; owner counting decision pending'}
 (HERE/'reports/extraction.json').write_text(json.dumps(report,indent=2)+'\n');return new

SLUG='malaysia-shoplot-facade';ROOT='ASSET_MalaysiaShoplotFacade'
def main():
 if '--export-source' in sys.argv:
  bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')));root=bpy.data.objects[ROOT]
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
  root=build();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'sources'/(SLUG+'.blend')),compress=True)
 export(root,HERE/'exports'/(SLUG+'.glb'))
if __name__=='__main__':main()
