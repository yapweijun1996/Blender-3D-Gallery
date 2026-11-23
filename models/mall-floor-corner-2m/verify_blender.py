"""Reopen the editable source and each exported GLB; measure actual geometry."""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
SLUG = 'mall-floor-corner-2m'
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



GOLD_X = 'Brushed champagne right'
GOLD_Z = 'Brushed champagne front'
GREEN = 'Cut eucalyptus terrazzo'
WIDTHS = (.025, .053, .103, .117)


def check_inlay(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    verts = [obj.matrix_world @ v.co for v in mesh.vertices]
    areas = defaultdict(float)
    edges = defaultdict(set)
    for tri in mesh.loop_triangles:
        mat = mesh.materials[tri.material_index].name
        a,b,c = [verts[i] for i in tri.vertices]
        if mat not in (GOLD_X,GOLD_Z,GREEN): continue
        assert all(abs(v.z-.1)<TOLERANCE for v in (a,b,c))
        areas[mat] += (b-a).cross(c-a).z / 2
        for left,right in ((a,b),(b,c),(c,a)):
            if abs(left.x+left.y)<TOLERANCE and abs(right.x+right.y)<TOLERANCE:
                points=tuple(sorted((round(left.x,6),round(right.x,6))))
                edges[points].add(mat)
    lo,hi,li,he=WIDTHS
    expected_gold=(2-lo)**2-(2-hi)**2+(2-li)**2-(2-he)**2
    expected_green=(2-hi)**2-(2-li)**2
    for mat in (GOLD_X,GOLD_Z): assert abs(areas[mat]-expected_gold/2)<1e-5,(mat,areas)
    assert abs(areas[GREEN]-expected_green)<1e-5,areas
    pair_edges=[(a,b) for (a,b),materials in edges.items() if materials=={GOLD_X,GOLD_Z}]
    common=sum((b-a)*math.sqrt(2) for a,b in pair_edges)
    assert abs(common-math.sqrt(2)*(hi-lo+he-li))<1e-5,(common,pair_edges)
    assert all((1-hi-1e-6<=a<b<=1-lo+1e-6) or (1-he-1e-6<=a<b<=1-li+1e-6) for a,b in pair_edges)
    t = [list(tri.vertices) for tri in mesh.loop_triangles]
    bvh=BVHTree.FromPolygons(verts,t,all_triangles=True)
    total=0
    for along in (-.83,-.37,.12,.68):
        for d,role in [(lo-.0005,'stone'),(lo+.0005,'gold'),(hi-.0005,'gold'),(hi+.0005,'green'),
                       (li-.0005,'green'),(li+.0005,'gold'),(he-.0005,'gold'),(he+.0005,'stone')]:
            for x,y,axis in ((1-d,along,GOLD_X),(along,d-1,GOLD_Z)):
                hit,normal,index,_=bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))
                name=mesh.materials[mesh.loop_triangles[index].material_index].name
                expected=axis if role=='gold' else GREEN if role=='green' else 'Honed ivory terrazzo, seed 421'
                assert hit and abs(hit.z-.1)<TOLERANCE and name==expected,(x,y,name,expected)
                total+=1
    return {'metalDiagonalsBlenderX':sorted(pair_edges),'metalMitreLengthM':round(common,7),
            'areaM2':{k:round(v,7) for k,v in areas.items()},'boundaryMaterialRays':total}


def check_baked(obj):
    mat=obj.data.materials[0]
    images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
    color=next(im for im in images if im.name.startswith('Corner finished surface'))
    orm=next(im for im in images if im.name.startswith('Corner material response'))
    def unpack(im):
        assert tuple(im.size)==(512,512)
        values=np.empty(512*512*4,np.float32)
        im.pixels.foreach_get(values)
        return 255*values.reshape(512,512,4)[:,:,:3]
    colors,response=unpack(color),unpack(orm)
    mesh=obj.data
    mesh.calc_loop_triangles()
    verts=[obj.matrix_world @ v.co for v in mesh.vertices]
    bvh=BVHTree.FromPolygons(verts,[list(t.vertices) for t in mesh.loop_triangles],all_triangles=True)
    samples=defaultdict(list)
    for along in (-.84,-.68,-.35,-.13,.12,.34,.66,.82):
        for d,role in [(.012,'ivory'),(.039,'outer'),(.078,'green'),(.110,'inner'),(.142,'ivory')]:
            for x,y,arm in ((1-d,along,'right'),(along,d-1,'front')):
                hit,normal,index,_=bvh.ray_cast(Vector((x,y,1)),Vector((0,0,-1)))
                tri=mesh.loop_triangles[index]
                a,b,c=(verts[i] for i in tri.vertices)
                u=(hit-a).cross(c-a).z / (b-a).cross(c-a).z
                v=(b-a).cross(hit-a).z / (b-a).cross(c-a).z
                ua,ub,uc=[mesh.uv_layers.active.data[i].uv.copy() for i in tri.loops]
                tc=ua*(1-u-v)+ub*u+uc*v
                ix,iy=int(tc.x*512),int(tc.y*512)
                gold=role in ('outer','inner')
                expected=(181,153,103) if arm=='right' else (170,139,92)
                measured=colors[iy,ix]
                if gold: assert np.max(abs(measured-expected))<22,(x,y,measured,expected)
                elif role=='green': assert measured[1]>measured[0] and measured.mean()<168,(x,y,measured)
                else: assert measured.mean()>168,(x,y,measured)
                m=response[iy,ix,2]/255
                assert (.47<m<.85 if gold else m<.13),(x,y,m)
                samples[role+' '+arm].append([*measured.tolist(),float(m)])
    return {'surfaceMaterialSamples':sum(map(len,samples.values())),
            'meanSRGBAndMetallic': {k:np.mean(v,axis=0).round(3).tolist() for k,v in samples.items()}}


bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
bpy.context.view_layer.update()
report = {'sourceSHA256':sha(SOURCE),'blender':bpy.app.version_string,'variants':[]}
assets = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert len(assets) == 3
assert all(im.packed_file for im in bpy.data.images if im.source == 'FILE')
for level in range(3):
    obj = bpy.data.objects[f'MODULE_CornerFloor_L{level}']
    assert obj.location.length < .000001 and obj['pitch_m'] == 2. and obj['lod'] == level
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges)
    bm.free()
    checks = check_inlay(obj) if level < 2 else check_baked(obj)
    report['variants'].append({'level':level,'source':measure(obj), 'sourceBorder':checks})

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
    variant['exportBorder'] = check_inlay(objects[0]) if level<2 else check_baked(objects[0])
    variant.update({'file':name,'sha256':sha(path),'bytes':path.stat().st_size,'reimport':result})

out = HERE/'reports'/'source-reimport.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
