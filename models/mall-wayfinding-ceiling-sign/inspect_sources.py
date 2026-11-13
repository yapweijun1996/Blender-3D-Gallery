"""Inspect the delivered source and exercise a real label/arrow edit on a saved copy."""
from pathlib import Path
import bpy,bmesh,runpy,json,hashlib,tempfile,math
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;api=runpy.run_path(str(HERE/'generate.py'));source=HERE/'sources/mall-wayfinding-ceiling-sign.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();originalSha=sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.collections[api['ROOT']];bpy.context.view_layer.update()
assert set(api['GROUPS'])==set(c.name for c in root.children)
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
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
   rear=c.name.startswith('Rear');normal=o.matrix_world.to_3x3()@Vector((0,0,1));assert normal.y>.999 if rear else normal.y<-.999
   local=[Matrix.Rotation(math.pi,4,'Z')@p if rear else p for p in points]
   lo=[min(p[i] for p in local) for i in range(3)];hi=[max(p[i] for p in local) for i in range(3)]
   if '_Label' in o.name:
    col={'Shops':-.67,'Food':0,'Lifts':.67}[o.name.split('_')[1]]
    assert lo[0]>=col-.13 and hi[0]<=col+.195 and lo[2]>=-.80 and hi[2]<=-.69,(o.name,lo,hi)
   else:assert lo[0]>=-.96 and hi[0]<=.96 and lo[2]>=-.60 and hi[2]<=-.51,(o.name,lo,hi)
   textfit[o.name]={'body':o.data.body,'localMin':lo,'localMax':hi,'normal':list(normal),'determinant':o.matrix_world.determinant()}
   assert o.matrix_world.determinant()>.999
  bm.free();bpy.data.meshes.remove(m)
assert max(p.z for p in allpoints)<1e-7 and abs(min(p.z for p in allpoints)+.94)<1e-6
report={'source_reopened':'PASS','source_sha256':originalSha,'blender_version':bpy.app.version_string,'source_units':'metres','source_scales':'UNIT','independentModules':api['GROUPS'],'editableTextObjects':len(textfit),'textFit':{'status':'PASS','labels':textfit},'topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0,'parts':topology},'orientation':'PASS: front -Y, rear +Y; rotation determinants +1; no mirrored scales','mount':'PASS: ceiling plane Z=0, all geometry below; no floor stand','sourceBounds':{'min':[min(p[i] for p in allpoints) for i in range(3)],'max':[max(p[i] for p in allpoints) for i in range(3)]}}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
fixture=Path(tempfile.mkdtemp(prefix='mall-ceiling-sign-438-edit-'));blend=fixture/'edited.blend';glb=fixture/'edited.glb'
bpy.data.objects['Front_Shops_Label'].data.body='STORES'
o=bpy.data.objects['Front_Food_Arrow'];pivot=Vector((.257,0,-.75));rot=Matrix.Rotation(math.pi,4,'Y')
for v in o.data.vertices:
 p=v.co.copy();p.y=0;q=rot@(p-pivot)+pivot;v.co.x=q.x;v.co.z=q.z
o['direction']='right'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True);bpy.ops.wm.open_mainfile(filepath=str(blend))
assert bpy.data.objects['Front_Shops_Label'].data.body=='STORES' and bpy.data.objects['Front_Food_Arrow']['direction']=='right'
api['export_asset'](glb);assert sha(source)==originalSha
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(glb),'fixtureBlend':str(blend),'originalSourceSha256':originalSha,'shippedSourceHashUnchanged':True,'edits':['Front_Shops_Label: SHOPS to STORES','Front_Food_Arrow: left to right']},indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('topology','textFit')}))
