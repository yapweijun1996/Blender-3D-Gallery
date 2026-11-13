from pathlib import Path
import bpy,json,runpy,hashlib,os
R=Path(__file__).resolve().parents[1]
for spec in json.loads((R/'scripts/batchservices02.json').read_text()):
 if os.environ.get('BATCH_ASSET_ID') and str(spec['id'])!=os.environ['BATCH_ASSET_ID']:continue
 p=R/'models'/spec['slug'];src=p/'sources'/(spec['slug']+'.blend');sha=hashlib.sha256(src.read_bytes()).hexdigest()
 bpy.ops.wm.open_mainfile(filepath=str(src));root=bpy.data.objects[spec['root']]
 assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
 nodes=list(root.children_recursive);meshes=[o for o in nodes if o.type=='MESH'];assert meshes
 report={'source_sha256':sha,'units':'metres','scale_length':1,'meshes':len(meshes),'objects':[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None} for o in nodes]}
 target=meshes[0];before=list(target.location);target.location.x+=.123
 mat=target.data.materials[0];rough=mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'];old=float(rough.default_value);new=.27 if old>.5 else .73;rough.default_value=new
 report['edit_proof']={'node':target.name,'before':before,'after':list(target.location),'delta_x':.123,'output':'reports/source-edit.glb','saved_copy':'reports/source-edit.blend','material':mat.name,'roughness_before':old,'roughness_after':new}
 copy=p/'reports/source-edit.blend';bpy.ops.wm.save_as_mainfile(filepath=str(copy),compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(copy));root=bpy.data.objects[spec['root']]
 assert abs(bpy.data.objects[report['edit_proof']['node']].location.x-before[0]-.123)<1e-5
 assert abs(bpy.data.materials[report['edit_proof']['material']].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value-new)<1e-5
 h=runpy.run_path(str(p/'generate.py'));h['export'](root,p/'reports/source-edit.glb')
 assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
 report['edit_proof']['copy_sha256']=hashlib.sha256(copy.read_bytes()).hexdigest()
 (p/'reports/source.json').write_text(json.dumps(report,indent=2)+'\n');print('SOURCE_PASS',spec['id'],spec['slug'])
