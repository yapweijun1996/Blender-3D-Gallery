import bpy
from mathutils.bvhtree import BVHTree
s=bpy.context.scene
flap=bpy.data.objects['Flap']
letter_parts=[bpy.data.objects[n] for n in ('LetterPaper','LetterBorder','LetterBorder.001','LetterStar')]
def tree(obj, dg):
    evaluated=obj.evaluated_get(dg)
    mesh=evaluated.to_mesh()
    vertices=[evaluated.matrix_world @ v.co for v in mesh.vertices]
    faces=[list(p.vertices) for p in mesh.polygons]
    result=BVHTree.FromPolygons(vertices,faces)
    evaluated.to_mesh_clear()
    return result
for tick in range(223):
    frame = 1 + tick // 2
    subframe = (tick % 2) * 0.5
    s.frame_set(frame, subframe=subframe)
    dg=bpy.context.evaluated_depsgraph_get()
    f=tree(flap,dg)
    for obj in letter_parts:
        hits=f.overlap(tree(obj,dg))
        if hits: raise RuntimeError(f'Intersection at frame {frame + subframe}: Flap and {obj.name}: {len(hits)}')
print('PASS: no flap/letter surface intersections in 223 half-frame samples')
