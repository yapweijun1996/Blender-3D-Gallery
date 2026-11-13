from pathlib import Path
import bpy,json,runpy,hashlib,os
R=Path(__file__).resolve().parents[1]
for spec in json.loads((R/'scripts/batch325341.json').read_text()):
 if os.environ.get('BATCH_ASSET_ID') and str(spec['id'])!=os.environ['BATCH_ASSET_ID']:continue
 p=R/'models'/spec['slug'];src=p/'sources'/(spec['slug']+'.blend')
 bpy.ops.wm.open_mainfile(filepath=str(src));root=bpy.data.objects[spec['root']]
 assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
 nodes=list(root.children_recursive);meshes=[o for o in nodes if o.type=='MESH'];assert meshes
 report={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'units':'metres','scale_length':1,'meshes':len(meshes),'objects':[{'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None} for o in nodes]}
 # Edit a copied in-memory source component, export it, never mutate canonical source.
 target=meshes[0];before=list(target.location);target.location.x+=.123
 h=runpy.run_path(str(p/'generate.py'));h['export'](root,p/'reports/source-edit.glb')
 report['edit_proof']={'node':target.name,'before':before,'after':list(target.location),'delta_x':.123,'output':'reports/source-edit.glb'}
 assert hashlib.sha256(src.read_bytes()).hexdigest()==report['source_sha256']
 (p/'reports/source.json').write_text(json.dumps(report,indent=2)+'\n')
 print('SOURCE_PASS',spec['id'],spec['slug'])
