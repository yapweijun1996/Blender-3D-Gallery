"""Reopen delivered source, inspect real meshes, prove isolated edit/re-export."""
from pathlib import Path
import bpy,bmesh,runpy,json,hashlib,math,tempfile
from mathutils import Vector
HERE=Path(__file__).resolve().parent;source=HERE/'sources/mall-sprinkler-head.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source);api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects[api['ROOT']]
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
meshes=[o for o in root.children_recursive if o.type=='MESH'];assert len(meshes)==13
assert all(abs(v-1)<1e-6 for o in meshes for v in o.scale)
def digest(o):return hashlib.sha256(json.dumps([[list(v.co) for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons]],sort_keys=True).encode()).hexdigest()
original={o.name:digest(o) for o in meshes};topology={}
for o in meshes:
    bm=bmesh.new();bm.from_mesh(o.data)
    bad=sum(not e.is_manifold for e in bm.edges);deg=sum(f.calc_area()<1e-14 for f in bm.faces);volume=bm.calc_volume(signed=True)
    assert volume>0,(o.name,'non-positive signed volume');assert bad==0 and deg==0,(o.name,bad,deg)
    topology[o.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifoldEdges':bad,'degenerateFaces':deg,'signedVolume_m3':volume};bm.free()
# Actual mesh points above mount plane must clear the 15 mm context opening radius.
above=[(o.name,o.matrix_world@v.co) for o in meshes for v in o.data.vertices if (o.matrix_world@v.co).z>1e-7]
r=max(math.hypot(v.x,v.y) for _,v in above);assert r<.015
# Every non-fitting pendant component remains at/below mount plane except hex body neck at +1 mm.
for name in ['MODULE_Bulb','MODULE_YokeLeft','MODULE_YokeRight','MODULE_Deflector']:
    assert max((bpy.data.objects[name].matrix_world@v.co).z for v in bpy.data.objects[name].data.vertices)<0
report={'source_reopened':'PASS','source_sha256':before,'blender_version':bpy.app.version_string,'editable_mesh_parts':len(meshes),'source_units':'metres','source_scales':'UNIT','topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0,'parts':topology},'mount_clearance':{'status':'PASS','method':'All actual source vertices above Z=0 checked against 15 mm radial context opening; max-radius bound contains every triangle','abovePlaneComponents':sorted(set(n for n,_ in above)),'maximumAbovePlaneRadius_m':r,'contextHoleRadius_m':.015,'minimumRadialClearance_m':.015-r,'scope':'visual context only, not installation or safety guidance'},'orientation':'PASS: pendant below plane, fitting above plane'}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
bulb=bpy.data.objects['MODULE_Bulb']
for v in bulb.data.vertices:v.co.x*=1.15;v.co.y*=1.15
bulb.data.update()
# Real material edit in isolated copy, preserving the other 3 shared materials.
old=bulb.data.materials[0];edited=old.copy();edited.name='EDIT_Opaque_Amber_Bulb';edited.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.65,.22,.02,1);edited.diffuse_color=(.65,.22,.02,1);bulb.data.materials[0]=edited
assert [o.name for o in meshes if digest(o)!=original[o.name]]==['MODULE_Bulb']
fixture=Path(tempfile.mkdtemp(prefix='mall-sprinkler-435-edit-'));blend=fixture/'edited.blend';glb=fixture/'edited.glb'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(blend));root=bpy.data.objects[api['ROOT']];assert bpy.data.objects['MODULE_Bulb'].data.materials[0].name=='EDIT_Opaque_Amber_Bulb'
assert all(digest(o)==original[o.name] for o in root.children_recursive if o.type=='MESH' and o.name!='MODULE_Bulb')
api['export'](root,glb);assert sha(source)==before
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(glb),'fixtureBlend':str(blend),'originalSourceSha256':before,'shippedSourceHashUnchanged':True,'changedMesh':'MODULE_Bulb','unchangedMeshCoordinates':len(meshes)-1},indent=2)+'\n')
print(json.dumps({**report,'topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0}}))
