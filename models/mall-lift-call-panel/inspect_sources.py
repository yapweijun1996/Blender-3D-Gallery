"""Reopen real source, exercise independent source poses, edit mesh and re-export a copy."""
from pathlib import Path
import bpy,runpy,json,hashlib,tempfile
HERE=Path(__file__).resolve().parent
source=HERE/'sources/mall-lift-call-panel.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects['ASSET_MallLiftCallPanel'];s=bpy.context.scene
assert s.unit_settings.system=='METRIC' and s.unit_settings.scale_length==1
meshes=[o for o in root.children_recursive if o.type=='MESH'];assert len(meshes)==16
assert all(tuple(o.scale)==(1,1,1) for o in root.children_recursive)
def digest(o):return hashlib.sha256(json.dumps([[list(v.co) for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons]],sort_keys=True).encode()).hexdigest()
original={o.name:digest(o) for o in meshes};poses=[]
for d in ['Up','Down']:
    pivot=bpy.data.objects['PIVOT_Button_'+d];other=bpy.data.objects['PIVOT_Button_'+('Down' if d=='Up' else 'Up')];originalOther=tuple(other.location);home=pivot.location.copy();pivot.location.y+=.002;bpy.context.view_layer.update()
    assert abs(pivot.location.y-home.y-.002)<1e-7 and tuple(other.location)==originalOther
    poses.append({'button':d,'travel_m':.002,'axis':'Blender +Y','otherButtonUnchanged':True});pivot.location=home
bpy.context.view_layer.update()
report={'source_reopened':'PASS','source_sha256':before,'blender_version':bpy.app.version_string,'editable_mesh_parts':len(meshes),'source_units':'metres','independentButtonPoses':poses}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
# Real edit is deliberately scoped: widen Up cap X by 2%, depress only its pivot by 2 mm.
up=bpy.data.objects['MODULE_Button_Up']
for v in up.data.vertices:v.co.x*=1.02
pivot=bpy.data.objects['PIVOT_Button_Up'];pivot.location.y+=.002
changed=[o.name for o in meshes if digest(o)!=original[o.name]];assert changed==['MODULE_Button_Up']
fixture=Path(tempfile.mkdtemp(prefix='mall-lift-call-panel-edit-'));editedSource=fixture/'edited.blend';editedGlb=fixture/'edited.glb';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(editedSource),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(editedSource));assert abs(bpy.data.objects['PIVOT_Button_Up'].location.y-(-.03025))<1e-7
runpy.run_path(str(HERE/'generate.py'))['export'](bpy.data.objects['ASSET_MallLiftCallPanel'],editedGlb)
assert sha(source)==before
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(editedGlb),'fixtureBlend':str(editedSource),'originalSourceSha256':before,'shippedSourceHashUnchanged':True,'changedMesh':changed[0],'unchangedOtherMeshes':15},indent=2)+'\n')
print(json.dumps(report));print('Isolated edited source:',editedSource)
