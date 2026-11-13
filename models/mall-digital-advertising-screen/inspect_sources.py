"""Reopen actual shipped source, check topology and packed image, then make a genuine isolated artwork edit."""
from pathlib import Path
import bpy,bmesh,runpy,json,hashlib,tempfile
HERE=Path(__file__).resolve().parent;source=HERE/'sources/mall-digital-advertising-screen.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(source);api=runpy.run_path(str(HERE/'generate.py'))
bpy.ops.wm.open_mainfile(filepath=str(source));root=bpy.data.objects[api['ROOT']]
assert bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1
meshes=[o for o in root.children_recursive if o.type=='MESH'];assert len(meshes)==17
assert all(abs(v-1)<1e-6 for o in meshes for v in o.scale)
def digest(o):return hashlib.sha256(json.dumps([[list(v.co) for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons],list(o.matrix_local)],default=list,sort_keys=True).encode()).hexdigest()
original={o.name:digest(o) for o in meshes};topology={}
for o in meshes:
    bm=bmesh.new();bm.from_mesh(o.data);bad=sum(not e.is_manifold for e in bm.edges);deg=sum(f.calc_area()<1e-14 for f in bm.faces);vol=bm.calc_volume(signed=True)
    assert vol>0 and bad==0 and deg==0,(o.name,bad,deg,vol)
    topology[o.name]={'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifoldEdges':bad,'degenerateFaces':deg,'signedVolume_m3':vol};bm.free()
bpy.context.view_layer.update()
assert max((o.matrix_world@v.co).y for o in meshes for v in o.data.vertices)<1e-7
img=bpy.data.images['REPLACEABLE_ScreenArtwork'];assert img.packed_file and list(img.size)==[1024,576]
assert len([o for o in bpy.data.scenes['EDITABLE_Artwork'].objects if o.name.startswith('ARTWORK_')])>=10
screen=bpy.data.objects['MODULE_ScreenContent'];assert len(screen.data.uv_layers)==1
report={'source_reopened':'PASS','source_sha256':before,'blender_version':bpy.app.version_string,'editable_mesh_parts':17,'source_units':'metres','source_scales':'UNIT','topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0,'parts':topology},'packed_texture':{'status':'PASS','images':1,'dimensions':[1024,576],'bytes':len(img.packed_file.data)},'artwork_scene':'Editable original Blender text and shape scene retained; not exported','mount':'PASS: all asset vertices on front side of Y=0 wall anchor'}
(HERE/'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
fixture=Path(tempfile.mkdtemp(prefix='mall-digital-screen-437-edit-'));blend=fixture/'edited.blend';glb=fixture/'edited.glb'
# Change actual packed content pixels, not only a name. Swap red and blue channels.
pixels=list(img.pixels[:])
for i in range(0,len(pixels),4):pixels[i],pixels[i+2]=pixels[i+2],pixels[i]
new=bpy.data.images.new('EDIT_RecoloredArtwork',width=1024,height=576);new.pixels[:]=pixels;new.filepath_raw=str(fixture/'edited-artwork.png');new.file_format='PNG';new.save();new.pack()
mat=screen.data.materials[0].copy();mat.name='EDIT_ScreenArtwork';mat.node_tree.nodes['REPLACE_SCREEN_IMAGE'].image=new;mat.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.5;screen.data.materials[0]=mat
assert all(digest(o)==original[o.name] for o in meshes)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True);bpy.ops.wm.open_mainfile(filepath=str(blend))
assert bpy.data.objects['MODULE_ScreenContent'].data.materials[0].name=='EDIT_ScreenArtwork'
assert bpy.data.images['EDIT_RecoloredArtwork'].packed_file
assert all(digest(o)==original[o.name] for o in bpy.data.objects[api['ROOT']].children_recursive if o.type=='MESH')
api['export'](bpy.data.objects[api['ROOT']],glb);assert sha(source)==before
(HERE/'reports/source-edit-fixture.json').write_text(json.dumps({'fixtureGlb':str(glb),'fixtureBlend':str(blend),'originalSourceSha256':before,'shippedSourceHashUnchanged':True,'unchangedMeshesAndTransforms':17},indent=2)+'\n')
print(json.dumps({**report,'topology':{'status':'PASS','nonmanifoldEdges':0,'degenerateFaces':0}}))
