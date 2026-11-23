"""Read back the final GLBs and compare welded topology and UV orientation."""
import hashlib
import json
from pathlib import Path
import sys

from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from build_npc import SOURCE, WORK, load_mesh, read_mesh, topology
from decimate import uv_area


def audit(path, shoe):
    garment, arm = load_mesh(path)
    points, _, faces, _ = read_mesh(garment, arm)
    uv = [uv_area(f.uv) for f in faces if f.uv]
    result = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'topology': topology(faces),
              'triangles': len(faces), 'uv_triangles': len(uv),
              'collapsed_uv_triangles': sum(abs(a) <= 1e-10 for a in uv)}
    if shoe:
        lining = [f.vertices for f in faces if f.material == 3]
        outer = [f.vertices for f in faces if f.material != 3]
        a, b = (BVHTree.FromPolygons(points.tolist(), group, all_triangles=True)
                for group in (lining, outer))
        result['lining_against_shell_pairs'] = sum(not set(lining[i]) & set(outer[j])
                                                 for i,j in a.overlap(b))
    return result


if __name__ == '__main__':
    results = {}
    for name in sys.argv[sys.argv.index('--')+1:]:
        shoe = name == 'shoes-sneakers'
        before = audit(SOURCE/(name+'.glb'), shoe)
        after = audit(HERE/('npc-'+name+'.glb'), shoe)
        assert before['topology'] == after['topology'], (name, before, after)
        assert bool(before['uv_triangles']) == bool(after['uv_triangles'])
        if shoe:
            assert before['lining_against_shell_pairs'] == after['lining_against_shell_pairs'] == 0
        results[name] = dict(before=before, after=after)
    (WORK/'geometry.json').write_text(json.dumps(results,indent=2)+'\n')
