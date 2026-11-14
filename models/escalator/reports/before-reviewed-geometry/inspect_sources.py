"""Read-only source inspection for the ID004 Blender file."""
import bpy, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'sources/escalator.blend'))
root=bpy.data.objects.get('ASSET_EscalatorV1_ID004')
assert root and root.parent is None
assert root.get('asset_id')=='ID004'
assert root.get('mechanism_status','').startswith('NEEDS REVIEW')
names=[o.name for o in root.children_recursive]
required=['LOWER_LANDING_DECK','UPPER_LANDING_DECK','RETURN_ENCLOSURE','MAINTENANCE_PANEL_SEPARATE','HANDRAIL_L','HANDRAIL_R','CONNECTOR_LOWER','CONNECTOR_UPPER']
for name in required: assert name in names, name
(HERE/'reports').mkdir(exist_ok=True)
(HERE/'reports/sources.json').write_text(json.dumps({'root':root.name,'objects':len(names),'required':required},indent=2)+'\n')
print(json.dumps({'status':'PASS','objects':len(names),'root':root.name}))
