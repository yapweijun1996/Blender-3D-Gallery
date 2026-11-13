from pathlib import Path
import bpy,json,hashlib
root=Path(__file__).resolve().parent; reports=[]
for suffix,name in [('post','ASSET_MallGlassPost'),('1m','ASSET_MallGlass1m'),('2m','ASSET_MallGlass2m')]:
    slug='mall-glass-railing-'+suffix; path=root/'sources'/(slug+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path)); asset=bpy.data.objects[name]
    assert tuple(asset.location)==(0,0,0)
    assert bpy.context.scene.unit_settings.scale_length==1
    assert len(asset.children)>=16
    panels=[o for o in asset.children if o.name.startswith('GLASS editable')]
    if suffix!='post':
        assert len(panels)==1
        mat=panels[0].data.materials[0]; shader=mat.node_tree.nodes.get('Principled BSDF')
        assert abs(shader.inputs['Alpha'].default_value-.28)<1e-6 and mat.blend_method=='BLEND'
    reports.append(dict(id=slug,source_reopened='PASS',editable_parts=len(asset.children),glass_panels=len(panels),
      modules=sorted({o['module'] for o in asset.children}),blender_version=bpy.app.version_string,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(root/'reports/sources.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
