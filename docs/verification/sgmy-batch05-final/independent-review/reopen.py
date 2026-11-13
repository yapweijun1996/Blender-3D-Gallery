import bpy,json,hashlib,math
from pathlib import Path
ids=['hdb-drop-off-porch', 'hawker-stall-roller-shutter', 'hawker-stall-exhaust-hood', 'hawker-stall-stainless-counter', 'hawker-stall-queue-sign', 'hawker-stall-number-plate', 'hawker-centre-ceiling-fan', 'hawker-centre-table-number', 'hawker-centre-tray-rack', 'kopitiam-coffee-sock']
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
