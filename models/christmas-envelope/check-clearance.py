import bpy
from mathutils.bvhtree import BVHTree
s=bpy.context.scene
flap_parts=[bpy.data.objects[n] for n in ('Flap','FlapTrim')]
back=bpy.data.objects['Back']
letter_parts=[bpy.data.objects[n] for n in ('LetterPaper','LetterBorder','LetterBorder.001','LetterStar')]
def tree(obj, dg):
    evaluated=obj.evaluated_get(dg)
    mesh=evaluated.to_mesh()
    vertices=[evaluated.matrix_world @ v.co for v in mesh.vertices]
    faces=[list(p.vertices) for p in mesh.polygons]
    result=BVHTree.FromPolygons(vertices,faces)
    evaluated.to_mesh_clear()
    return result
samples=(s.frame_end-s.frame_start)*2+1
for tick in range(samples):
    frame = s.frame_start + tick // 2
    subframe = (tick % 2) * 0.5
    s.frame_set(frame, subframe=subframe)
    dg=bpy.context.evaluated_depsgraph_get()
    flap_trees=[tree(obj,dg) for obj in flap_parts]
    if not flap_trees[0].overlap(tree(back,dg)):
        raise RuntimeError(f'Hinge detached at frame {frame + subframe}')
    for obj in letter_parts:
        letter_tree=tree(obj,dg)
        for part, flap_tree in zip(flap_parts, flap_trees):
            hits=flap_tree.overlap(letter_tree)
            if hits: raise RuntimeError(f'Intersection at frame {frame + subframe}: {part.name} and {obj.name}: {len(hits)}')
print(f'PASS: hinge joined and no flap/letter surface intersections in {samples} half-frame samples')
