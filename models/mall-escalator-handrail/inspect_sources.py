"""Reopen source; test manifold editable parts; edit an isolated copy, never delivery."""
from pathlib import Path
import bpy, bmesh, json, hashlib, sys, shutil
HERE = Path(__file__).resolve().parent
source = HERE / 'sources/mall-escalator-handrail.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
root = bpy.data.objects['ASSET_MallEscalatorHandrail']
assert tuple(root.location) == (0, 0, 0)
assert bpy.context.scene.unit_settings.scale_length == 1
meshes = [o for o in root.children_recursive if o.type == 'MESH']
assert len(meshes) == 8
checks = []
for o in meshes:
    bm = bmesh.new(); bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges), o.name
    volume = bm.calc_volume(); assert volume > 0, o.name
    euler = len(bm.verts) - len(bm.edges) + len(bm.faces)
    assert euler == (0 if 'ContinuousRubberBelt' in o.name else 2), o.name
    unseen = set(bm.verts); components = 0
    while unseen:
        components += 1; queue = [unseen.pop()]
        while queue:
            v = queue.pop()
            for edge in v.link_edges:
                other = edge.other_vert(v)
                if other in unseen: unseen.remove(other); queue.append(other)
    assert components == 1, o.name
    checks.append({'name':o.name,'closed_manifold':True,'components':components,'euler':euler,'volume_m3':volume})
    bm.free()
assert all(o.library is None for o in root.children_recursive)
assert len([o for o in root.children if o.name.startswith('CONNECTOR_')]) == 5
report = {'source_reopened':'PASS','editable_mesh_parts':8,'closed_manifold_meshes':8,'topology':checks,'external_links':0,'units':'metres','blender_version':bpy.app.version_string,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(HERE / 'reports/sources.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
if '--' in sys.argv:
    out = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
    assert out != HERE and not out.exists()
    (out / 'sources').mkdir(parents=True)
    shutil.copy(HERE / 'generate.py',out / 'generate.py')
    for v in bpy.data.objects['MODULE_ContinuousRubberBelt'].data.vertices: v.co.y *= 1.125
    bpy.data.materials['Black elastomer handrail belt'].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .62
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'sources/mall-escalator-handrail.blend'),compress=True)
