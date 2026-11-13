"""Reopen the delivered source, inspect evaluated geometry, and save real mesh/material/text edits."""
from pathlib import Path
import bpy,bmesh,runpy,json,hashlib,tempfile
from mathutils import Vector
HERE=Path(__file__).resolve().parent;api=runpy.run_path(str(HERE/'generate.py'));source=HERE/'sources/mall-food-court-tray-station.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();originalSha=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.collections[api['ROOT']];bpy.context.view_layer.update()
assert set(api['GROUPS'])==set(c.name for c in root.children)
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
assert not [im for im in bpy.data.images if im.source=='FILE' and not im.packed_file]
dg=bpy.context.evaluated_depsgraph_get();topology={};textfit={};allpoints=[]
for c in root.children:
 for o in c.objects:
  assert all(abs(v-1)<1e-6 for v in o.scale),(o.name,list(o.scale))
  m=api['evaluated_mesh'](o,dg);bm=bmesh.new();bm.from_mesh(m)
  bad=sum(not e.is_manifold for e in bm.edges);deg=sum(f.calc_area()<1e-14 for f in bm.faces);vol=bm.calc_volume(signed=True)
  assert bad==0 and deg==0 and vol>0,(o.name,bad,deg,vol)
  topology[o.name]={'nonmanifoldEdges':bad,'degenerateFaces':deg,'signedVolume_m3':vol}
  points=[o.matrix_world@v.co for v in m.vertices];allpoints+=points
  if o.type=='FONT':
   normal=o.matrix_world.to_3x3()@Vector((0,0,1));assert normal.y<-.999
   lo=[min(p[i] for p in points) for i in range(3)];hi=[max(p[i] for p in points) for i in range(3)]
   assert lo[0]>-.60 and hi[0]<.60 and lo[2]>1.22 and hi[2]<1.47,(o.name,lo,hi)
   textfit[o.name]={'body':o.data.body,'min':lo,'max':hi,'normal':list(normal),'determinant':o.matrix_world.determinant()}
  bm.free();bpy.data.meshes.remove(m)
report={'source_reopened':'PASS','source_sha256':originalSha,'blender_version':bpy.app.version_string,'source_units':'metres','source_scales':'UNIT','selfContained':True,'independentModules':api['GROUPS'],'editableTextObjects':len(textfit),'textFit':{'status':'PASS','labels':textfit},'topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0,'parts':topology},'sourceBounds':{'min':[min(p[i] for p in allpoints) for i in range(3)],'max':[max(p[i] for p in allpoints) for i in range(3)]}}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
fixture=Path(tempfile.mkdtemp(prefix='mall-tray-station-439-edit-'));blend=fixture/'edited.blend';glb=fixture/'edited.glb'
bpy.data.objects['ReturnLabel'].data.body='RETURN TRAYS'
# A real mesh vertex edit, not just a transform or a regenerated preset.
for vert in bpy.data.collections['Counter'].objects[0].data.vertices:vert.co.x*=1.04
mat=bpy.data.materials['Tray 04 warm terracotta'];mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.07,.24,.31,1);mat.diffuse_color=(.07,.24,.31,1)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True);bpy.ops.wm.open_mainfile(filepath=str(blend))
assert bpy.data.objects['ReturnLabel'].data.body=='RETURN TRAYS'
assert max(v.co.x for v in bpy.data.collections['Counter'].objects[0].data.vertices)>.779
assert abs(bpy.data.materials['Tray 04 warm terracotta'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value[0]-.07)<1e-6
api['export_asset'](glb);assert sha(source)==originalSha
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(glb),'fixtureBlend':str(blend),'originalSourceSha256':originalSha,'shippedSourceHashUnchanged':True,'edits':['Counter: mesh vertices widened 4%','Tray04: material changed terracotta to teal blue','ReturnLabel: TRAY RETURN to RETURN TRAYS']},indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('topology','textFit')}))
