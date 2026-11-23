"""Reopen the editable source and each exported GLB; measure actual geometry."""
import hashlib
import json
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
SLUG = 'mall-floor-module-2m'
SOURCE = HERE/'sources'/f'{SLUG}.blend'
TOLERANCE = .000002


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    verts = [obj.matrix_world @ v.co for v in mesh.vertices]
    triangles = [list(t.vertices) for t in mesh.loop_triangles]
    bounds = [[round(op(p[i] for p in verts),7) for i in range(3)] for op in (min,max)]
    assert bounds == [[-1.,-1.,0.],[1.,1.,.1]], bounds
    top_area = 0
    for indices in triangles:
        a,b,c = (verts[i] for i in indices)
        if all(abs(v.z - .1) < TOLERANCE for v in (a,b,c)):
            signed_area = ((b-a).cross(c-a)).z / 2
            assert signed_area > 0, 'Flipped or degenerate top triangle'
            top_area += signed_area
    assert abs(top_area - 4.) < .00001, top_area
    bvh = BVHTree.FromPolygons(verts, triangles, all_triangles=True)
    coordinates = sorted({round(-1+i*.05, 6) for i in range(41)} | {
        -.998, -.501, -.5, -.499, -.002, .002, .498, .501, .998
    })
    for x in coordinates:
        for y in coordinates:
            hit,normal,_,_ = bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))
            assert hit is not None and abs(hit.z-.1) < TOLERANCE and normal.z > .9999, (x,y,hit)
    for x,y in [(1.001,0),(-1.001,0),(0,1.001),(0,-1.001)]:
        assert bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))[0] is None
    return {'blenderBoundsMetres':bounds, 'topAreaSquareMetres':round(top_area,7),
            'topRays':len(coordinates)**2, 'outsideMisses':4, 'triangles':len(triangles)}


bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
bpy.context.view_layer.update()
report = {'sourceSHA256':sha(SOURCE),'blender':bpy.app.version_string,'variants':[]}
assets = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert len(assets) == 3
assert all(im.packed_file for im in bpy.data.images if im.source == 'FILE')
for level in range(3):
    obj = bpy.data.objects[f'MODULE_StraightFloor_L{level}']
    assert obj.location.length < .000001 and obj['pitch_m'] == 2. and obj['lod'] == level
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges)
    bm.free()
    report['variants'].append({'level':level,'source':measure(obj)})

for variant in report['variants']:
    level = variant['level']
    name = SLUG + (f'-lod{level}' if level else '') + '.glb'
    path = HERE/'exports'/name
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    bpy.context.view_layer.update()
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(objects)==1
    result = measure(objects[0])
    assert result['triangles'] == variant['source']['triangles']
    textures = [node.image for mat in objects[0].data.materials for node in mat.node_tree.nodes
                if node.type == 'TEX_IMAGE']
    assert len(textures) == 1 and tuple(textures[0].size) == (512,512)
    image = textures[0]
    pixels = np.empty(512*512*4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    # Compare the original finish and the distant baked sRGB appearance away
    # from the atlas padding and the side/bottom swatches.
    mean_rgb = 255 * pixels.reshape(512,512,4)[32:480,32:480,:3].mean(axis=(0,1),dtype=np.float64)
    variant['finishMeanSRGB'] = [round(float(c),3) for c in mean_rgb]
    variant.update({'file':name,'sha256':sha(path),'bytes':path.stat().st_size,'reimport':result})

full,mid,low = (v['finishMeanSRGB'] for v in report['variants'])
assert full == mid
assert max(abs(a-b) for a,b in zip(full,low)) < 3, (full,low)

out = HERE/'reports'/'source-reimport.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
