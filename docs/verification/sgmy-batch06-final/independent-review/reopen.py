import bpy,json,hashlib,math
from pathlib import Path
ids=['kopitiam-kettle', 'kopitiam-saucer-and-cup', 'kopitiam-condiment-tray', 'kopitiam-toast-display', 'mamak-roti-canai-griddle', 'mamak-teh-tarik-jug', 'mamak-curry-pot', 'mamak-stainless-steel-plate', 'mamak-wall-menu-board', 'satay-skewer-display']
rows=[]
for slug in ids:
 p=Path('models')/slug; source=next((p/'sources').glob('*.blend'));before=hashlib.sha256(source.read_bytes()).hexdigest()
 bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
 assert bpy.context.scene.unit_settings.scale_length==1
 meshes=[o for o in bpy.data.objects if o.type=='MESH' and (o.name.startswith('MODULE_') or not o.name.lower().startswith(('studio','ground')))]
 assert meshes and all(all(math.isfinite(c) for c in v.co) for o in meshes for v in o.data.vertices)
 assert not any(o.library for o in bpy.data.objects)
 assert before==hashlib.sha256(source.read_bytes()).hexdigest()
 rows.append({'asset':slug,'sourceSha256':before,'metricScale':1,'meshObjects':len(meshes),'finiteMeshCoordinates':True,'externalObjectLibraries':False,'sourceUnchanged':True})
Path('review-results/reopen.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows))
