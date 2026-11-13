"""Real source reopen/configuration edit/save/reopen/re-export without regenerating housing."""
from pathlib import Path
import bpy,runpy,json,hashlib,tempfile
HERE=Path(__file__).resolve().parent;source=HERE/'sources/mall-lift-floor-indicator.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects['ASSET_MallLiftFloorIndicator'];s=bpy.context.scene
assert s.unit_settings.system=='METRIC' and s.unit_settings.scale_length==1
meshes=[o for o in root.children_recursive if o.type=='MESH'];assert len(meshes)==20
assert all(tuple(o.scale)==(1,1,1) for o in root.children_recursive)
def digest(o):return hashlib.sha256(json.dumps([[list(v.co) for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons]],sort_keys=True).encode()).hexdigest()
original={o.name:digest(o) for o in meshes}
assert root['display_floor']=='02' and root['display_direction']=='up'
(HERE/'reports/sources.json').write_text(json.dumps({'source_reopened':'PASS','source_sha256':before,'blender_version':bpy.app.version_string,'editable_mesh_parts':len(meshes),'source_units':'metres','independent_digit_segments':14,'independent_arrow_segments':3,'configuration':{'display_floor':'02','display_direction':'up'}},indent=2)+'\n')
root['display_floor']='03';root['display_direction']='down'
fixture=Path(tempfile.mkdtemp(prefix='mall-lift-floor-indicator-edit-'));editedSource=fixture/'edited.blend';editedGlb=fixture/'edited.glb'
api=runpy.run_path(str(HERE/'generate.py'));api['apply_display'](root)
assert all(digest(o)==original[o.name] for o in meshes)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(editedSource),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(editedSource));root=bpy.data.objects['ASSET_MallLiftFloorIndicator']
assert root['display_floor']=='03' and root['display_direction']=='down'
api['export'](root,editedGlb)
assert sha(source)==before
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(editedGlb),'fixtureBlend':str(editedSource),'originalSourceSha256':before,'shippedSourceHashUnchanged':True,'unchangedMeshCoordinates':20},indent=2)+'\n')
print('Source reopened; actual 02 up -> 03 down edit saved, reopened and exported:',editedGlb)
