import bpy, json
from pathlib import Path
root=Path(__file__).resolve().parent
results=[]
for suffix, name in [('post','ASSET_MallQueuePost'),('short','ASSET_MallQueueShort'),('long','ASSET_MallQueueLong')]:
    slug='mall-queue-'+suffix
    bpy.ops.wm.open_mainfile(filepath=str(root/'sources'/(slug+'.blend')))
    obj=bpy.data.objects.get(name)
    assert obj and len(obj.children)>=10
    assert tuple(obj.location)==(0,0,0)
    assert bpy.context.scene.unit_settings.scale_length==1
    modules=sorted({child['module'] for child in obj.children})
    assert len(modules)==(1 if suffix=='post' else 3)
    results.append({'id':slug,'source_reopened':'PASS','editable_parts':len(obj.children),'modules':modules,'blender_version':bpy.app.version_string})
(root/'reports'/'sources.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
