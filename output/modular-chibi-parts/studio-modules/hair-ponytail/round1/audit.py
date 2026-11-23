"""Audit decoded GLB topology, skin, texture and fitting scene."""
from pathlib import Path
import sys,hashlib,json,collections
import bpy,bmesh,numpy as np
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(HERE))
from fit_hair import bob,GLB,MASTER,make_tree
def digest(f):return hashlib.sha256(f.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(MASTER),use_scripts=False)
expected=bpy.data.objects['Armature']
bpy.ops.import_scene.gltf(filepath=str(GLB));o=bpy.data.objects['Hair_High_Ponytail']
rig=o.parent
assert set(expected.data.bones.keys())==set(rig.data.bones.keys())
doc,buf=bob.read_glb(GLB);prim,=doc['meshes'][0]['primitives'];skin,=doc['skins']
# Inverse bind matrices and hierarchy must agree with a verified sibling on the same master.
ref=HERE.parents[1]/'hair-sidepart/round3/hair_sidepart_v3.glb'
rd,rb=bob.read_glb(ref)
def hierarchy(doc):
    return [(doc['nodes'][i]['name'],[doc['nodes'][c]['name'] for c in doc['nodes'][i].get('children',[])]) for i in doc['skins'][0]['joints']]
attrs=prim['attributes']
weights=bob.accessor(doc,buf,attrs['WEIGHTS_0']);joints=bob.accessor(doc,buf,attrs['JOINTS_0'])
names=[doc['nodes'][i]['name'] for i in skin['joints']]
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.normal_update();bm.faces.ensure_lookup_table()
tree=BVHTree.FromBMesh(bm)
pairs=[(i,j) for i,j in tree.overlap(tree) if i<j and set(bm.faces[i].verts).isdisjoint(bm.faces[j].verts)]
wrong=[(list(e.verts[0].co),list(e.verts[1].co),len(e.link_faces)) for e in bm.edges if not e.is_manifold]
print('BAD',wrong[:9], 'SELF',[(i,j,list(bm.faces[i].calc_center_median()),list(bm.faces[j].calc_center_median())) for i,j in pairs[:8]],flush=True)
skin_tree=make_tree(bpy.data.objects['Base_Body'])
def clearance(v):
    p=v.co;q,n,_,_=skin_tree.find_nearest(p)
    return (p-q).dot(n)
near=sorted((clearance(v),tuple(v.co)) for v in bm.verts)
print('CLEAR',near[:8],flush=True)
info=dict(asset_sha256=digest(GLB),bytes=GLB.stat().st_size,triangles=doc['accessors'][prim['indices']]['count']//3,
mesh_count=len(doc['meshes']),primitives=len(doc['meshes'][0]['primitives']),materials=len(doc['materials']),has_uv='TEXCOORD_0' in attrs,
textures=[list(n.image.size) for n in o.active_material.node_tree.nodes if n.type=='TEX_IMAGE'],
joints=len(names),weighted_bones=[names[i] for i in np.unique(joints[weights>0])],max_influences=int((weights>0).sum(1).max()),
weight_sum_error=float(np.max(np.abs(weights.sum(1)-1))),hierarchy_matches=hierarchy(doc)==hierarchy(rd),
max_inverse_bind_difference=float(np.max(np.abs(bob.accessor(doc,buf,skin['inverseBindMatrices'])-bob.accessor(rd,rb,rd['skins'][0]['inverseBindMatrices'])))),
rest_vertex_clearance_m=near[0][0],rest_inside_vertices=sum(v[0]<0 for v in near),components=len(bob.connected_faces(bm)),bad_edges=len(wrong),
inconsistent_edges=sum(not e.is_contiguous for e in bm.edges),nonadjacent_self_intersections=len(pairs),volume_m3=bm.calc_volume(signed=True),
min_triangle_area=min(f.calc_area() for f in bm.faces))
exported_positions=[o.matrix_world@v.co for v in bm.verts]
pos=bob.accessor(doc,buf,attrs['POSITION']);norm=bob.accessor(doc,buf,attrs['NORMAL'])
seen={};max_delta=0.
for p,n in zip(pos,norm):
    usual=seen.setdefault(tuple(p),n);max_delta=max(max_delta,float(np.linalg.norm(n-usual)))
info['max_normal_delta_at_uv_seams']=max_delta
bm.free()
bpy.ops.wm.open_mainfile(filepath=str(GLB.with_suffix('.blend')),use_scripts=False)
edit=bpy.data.objects['Hair_High_Ponytail']
info['editable_reopened']=edit.parent.type=='ARMATURE' and all(p.use_smooth for p in edit.data.polygons) and all(n.image.packed_file for n in edit.active_material.node_tree.nodes if n.type=='TEX_IMAGE')
edit.data.calc_loop_triangles()
from mathutils.kdtree import KDTree
kt=KDTree(len(edit.data.vertices))
for v in edit.data.vertices:kt.insert(edit.matrix_world@v.co,v.index)
kt.balance()
info['max_editable_to_export_position_error_m']=max(kt.find(p)[2] for p in exported_positions)
info['editable_vertices']=len(edit.data.vertices)
info['export_welded_vertices']=len(exported_positions)
assert info['editable_vertices']==info['export_welded_vertices'] and len(edit.data.loop_triangles)==info['triangles']
assert info['max_editable_to_export_position_error_m']<1e-6
(HERE/'geometry_check.json').write_text(json.dumps(info,indent=2)+'\n');print(info,flush=True)

