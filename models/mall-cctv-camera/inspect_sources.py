"""Reopen actual source, check manifold geometry, continuous pose clearance, edit/re-export."""
from pathlib import Path
import bpy,bmesh,runpy,json,hashlib,math,tempfile
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;source=HERE/'sources/mall-cctv-camera.blend'
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
pan=bpy.data.objects['PIVOT_Pan'];tilt=bpy.data.objects['PIVOT_Tilt'];head=[o for o in tilt.children_recursive if o.type=='MESH']
bpy.context.view_layer.update()
# Exact source mesh vertices in tilt-local coordinates give a conservative continuous swept cylinder.
points=[o.matrix_local@v.co for o in head for v in o.data.vertices]
rho=max(math.hypot(v.y,v.z) for v in points);halfwidth=max(abs(v.x) for v in points)
bridge=bpy.data.objects['MODULE_YokeBridge']
bridge_bottom=min((bridge.matrix_world@v.co).z for v in bridge.data.vertices)
axis_z=tilt.matrix_world.translation.z
top_gap=bridge_bottom-(axis_z+rho);side_gap=.045-halfwidth
assert top_gap>.001 and side_gap>.002,(rho,top_gap,side_gap)
assert max((o.matrix_world@v.co).z for o in meshes for v in o.data.vertices)<1e-7
def tree(o):return BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons],all_triangles=False)
samples=[]
for p in [0,40,90,180,270]:
    pan.rotation_euler.z=math.radians(p)
    for t in [-30,0,20,45]:
        tilt.rotation_euler.x=math.radians(t);bpy.context.view_layer.update()
        overlaps=[]
        for moving in head:
            for name in ['MODULE_YokeBridge','MODULE_YokeLeft','MODULE_YokeRight','MODULE_MountingBase','MODULE_BaseGasket','MODULE_PanCollar']:
                fixed=bpy.data.objects[name]
                if tree(moving).overlap(tree(fixed)):overlaps.append([moving.name,name])
        assert not overlaps,(p,t,overlaps)
        samples.append({'pan_deg':p,'tilt_deg':t,'triangleOverlapPairs':0})
pan.rotation_euler.z=0;tilt.rotation_euler.x=math.radians(20);bpy.context.view_layer.update()
report={'source_reopened':'PASS','source_sha256':before,'blender_version':bpy.app.version_string,'editable_mesh_parts':len(meshes),'source_units':'metres','source_scales':'UNIT','topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0,'parts':topology},'articulation':{'status':'PASS','method':'Actual source vertices bound a continuous tilt swept cylinder; separate BVH triangle checks at 20 pan/tilt poses. Intentional axle-to-housing mating contact excluded. No mechanical or installation claim.','tilt_axis_Blender':'X','pan_axis_Blender':'Z','axis_z_m':axis_z,'swept_head_radius_m':rho,'head_half_width_m':halfwidth,'minimum_yoke_side_gap_m':side_gap,'minimum_bridge_gap_m':top_gap,'samples':samples},'mount':'PASS: all asset vertices at/below Z=0, source anchor exactly zero'}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
lens=bpy.data.objects['MODULE_Lens']
for v in lens.data.vertices:v.co.x*=1.1;v.co.y*=1.1
lens.data.update();old=lens.data.materials[0];edited=old.copy();edited.name='EDIT_Opaque_Blue_Lens';edited.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.02,.06,.1,1);edited.diffuse_color=(.02,.06,.1,1);lens.data.materials[0]=edited
pan.rotation_euler.z=math.radians(40);tilt.rotation_euler.x=math.radians(45)
assert [o.name for o in meshes if digest(o)!=original[o.name]]==['MODULE_Lens']
fixture=Path(tempfile.mkdtemp(prefix='mall-cctv-436-edit-'));blend=fixture/'edited.blend';glb=fixture/'edited.glb'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(blend));root=bpy.data.objects[api['ROOT']];assert bpy.data.objects['MODULE_Lens'].data.materials[0].name=='EDIT_Opaque_Blue_Lens'
assert all(digest(o)==original[o.name] for o in root.children_recursive if o.type=='MESH' and o.name!='MODULE_Lens')
assert abs(bpy.data.objects['PIVOT_Pan'].rotation_euler.z-math.radians(40))<1e-6
assert abs(bpy.data.objects['PIVOT_Tilt'].rotation_euler.x-math.radians(45))<1e-6
api['export'](root,glb);assert sha(source)==before
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(glb),'fixtureBlend':str(blend),'originalSourceSha256':before,'shippedSourceHashUnchanged':True,'changedMesh':'MODULE_Lens','unchangedMeshCoordinates':len(meshes)-1},indent=2)+'\n')
print(json.dumps({**report,'topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0}}))
