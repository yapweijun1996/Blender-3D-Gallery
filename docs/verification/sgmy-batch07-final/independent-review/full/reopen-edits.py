from pathlib import Path
import bpy,runpy,hashlib,inspect,json
rows=[]
for p in sorted(Path('fixtures/models').iterdir()):
 api=runpy.run_path(str(p/'generate.py'));bstyle=(p/'inspect_sources.py').exists()
 blend=p/('reports/source-edit/'+p.name+'-edited.blend' if bstyle else 'reports/source-edit.blend');prior=p/('reports/source-edit/edited.glb' if bstyle else 'reports/source-edit.glb')
 bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
 out=Path('review-results/full')/(p.name+'-reopened-edit.glb')
 if bstyle:api['export'](out.resolve())
 else:api['export'](bpy.data.objects[api['ROOT']],out.resolve())
 a=hashlib.sha256(prior.read_bytes()).hexdigest();b=hashlib.sha256(out.read_bytes()).hexdigest();assert a==b,(p.name,a,b)
 rows.append({'asset':p.name,'savedEditedBlendReopened':True,'reexportByteIdentical':True,'sha256':a})
Path('review-results/full/reopened-edit-proof.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
