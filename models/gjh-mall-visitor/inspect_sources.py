"""Reopen only this collection's authored source and verify the editable animation hierarchy."""
from pathlib import Path
import json
import hashlib
import bpy
root=Path(__file__).resolve().parent
source=root/'sources/gjh-mall-visitor.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
visitor=bpy.data.objects.get('GJHMallVisitor')
assert visitor and visitor.type=='EMPTY'
names=['Body','Head','LeftShoulder','RightShoulder','LeftElbow','RightElbow','LeftHip','RightHip','LeftKnee','RightKnee','LeftFoot','RightFoot']
for name in names:assert bpy.data.objects.get(name),name
tracks={o.name:[t.name for t in o.animation_data.nla_tracks] for o in bpy.data.objects if o.animation_data and o.animation_data.nla_tracks}
assert tracks and all(sorted(names)==['idle','sprint','walk'] for names in tracks.values())
assert bpy.context.scene.unit_settings.scale_length==1
report={'source_reopened':'PASS','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'editable_meshes':sum(o.type=='MESH' and o.parent is not None for o in bpy.data.objects),'animation_tracks':tracks,'generator_sha256':hashlib.sha256((root/'generate.py').read_bytes()).hexdigest()}
(root/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
