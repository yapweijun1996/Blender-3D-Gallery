import bpy
from mathutils.bvhtree import BVHTree
s=bpy.context.scene
flap_parts=[bpy.data.objects[n] for n in ('Flap','FlapTrim')]
back=bpy.data.objects['Back']
letter_parts=[bpy.data.objects[n] for n in ('LetterPaper','LetterBorder','LetterBorder.001')]
bow=bpy.data.objects['RibbonBow']
pocket_band=bpy.data.objects['RibbonPocketBand']
pocket_parts=[bpy.data.objects[n] for n in ('PocketLeft','PocketRight','PocketBottom','PocketTrim')]
seal_parts=[part for part in bpy.data.objects['Seal'].children_recursive if part.type in ('MESH','CURVE')]
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
    parts=[back, *flap_parts, *pocket_parts, *letter_parts]
    if tick == 0:
        parts.extend(seal_parts)
    obstacles=[(obj, tree(obj,dg)) for obj in parts]
    ribbon_trees={ribbon:tree(ribbon,dg) for ribbon in [bow,pocket_band]}
    for ribbon, ribbon_tree in ribbon_trees.items():
        for obj, obstacle in obstacles:
            if ribbon_tree.overlap(obstacle):
                raise RuntimeError(f'{ribbon.name} touches {obj.name} at frame {frame + subframe}')
    if ribbon_trees[bow].overlap(ribbon_trees[pocket_band]):
        raise RuntimeError(f'Bow crosses the pocket ribbon at frame {frame + subframe}')
print(f'PASS: hinge joined and no flap/letter surface intersections in {samples} half-frame samples')
print(f'PASS: ribbon clears the shell, flap and letter in {samples} half-frame samples')
bpy.context.scene.frame_set(s.frame_end)
dg=bpy.context.evaluated_depsgraph_get()
letter_paper=letter_parts[0].evaluated_get(dg)
assert min((letter_paper.matrix_world @ v.co).z for v in letter_paper.data.vertices) > 1.05
print('PASS: the letter fully clears the mouth at the end of the lift')
