"""Build an editable, lower-triangle modular hairstyle on the visitor rig.

Run in the GJH Reference Visitor scene in Blender. Only the existing Hair mesh
and its topology-reduction modifier are replaced; the object and head binding
remain intact. Blender evaluates the Decimate modifier before the armature.
"""
import bpy
import importlib.util
import inspect
from pathlib import Path

BASE = Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery')
spec = importlib.util.spec_from_file_location('visitor_hair_geometry', BASE / 'models/chibi-visitor-v4/generate.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
scene = bpy.data.scenes['GJH Reference Visitor']
h.SCENE = scene.name
model = next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
hair = next(o for o in model.objects if o.type == 'MESH' and o.name.startswith('Hair'))
material = hair.data.materials[0]

# Preserve the original nape and middle coverage, which seals the scalp behind
# the ears. Vary upper strands individually to avoid a mirrored shingle fan.
original_locks = h.hair_locks
def swept_rear_locks():
    locks = original_locks()
    # (azimuth drift in degrees, endpoint elevation shift, width multiplier).
    # Nape endpoints remain fixed so hair continues to cover the head.
    edits = {
        5: (-7, 3, 1.04), 6: (-10, -2, 1.02), 7: (-7, 7, 1.08),
        8: (7, -3, .95), 9: (9, 5, 1.02), 10: (5, 1, 1.04),
        11: (-7, 5, 1.00), 12: (-11, -5, 1.04), 13: (8, 7, .96),
        14: (7, -4, 1.03), 15: (6, 4, .98),
        16: (-5, 3, 1.02), 17: (7, -2, 1.03), 18: (3, 2, .97),
    }
    for index, (drift, height, widen) in edits.items():
        control, width, radius = locks[index]
        changed = []
        for j, (az, el, scale) in enumerate(control):
            t = j / (len(control) - 1)
            changed.append((az + drift * t, el + height * t, scale))
        locks[index] = (changed, width * widen, radius)
    return locks
h.hair_locks = swept_rear_locks

# Reuse the reviewed eye-safe fringe and keep the shorter side points. Broad,
# low crown shapes replace the antenna-like original; both start inside the cap.
source = inspect.getsource(h.build_hair)
replacements = {
    '(-102, -6, 1.30)': '(-102, -6, 1.15)',
    '(-104, 9, 1.31)': '(-104, 9, 1.15)',
    '(102, -4, 1.29)': '(102, -4, 1.15)',
    '(104, 14, 1.30)': '(104, 14, 1.15)',
    '''([(0.052, -0.004, 0.905), (0.046, -0.008, 0.940), (0.030, -0.011, 0.966), (0.008, -0.012, 0.984),
          (-0.020, -0.012, 0.986)], (0, 0, 1), 0.044, 0.024),''': '',
    'bake_ao(part, HH, lin(HAIR_HEX))': 'bake_ao(part, HH, lin(HAIR_HEX), floor=0.58, power=1.0)',
}
def crown_geometries():
    # Broad, low x/z silhouettes with a real depth; union with the cap below.
    def wedge(outline, front, rear):
        # Taper the depth at both sides: the crest should read as a rounded
        # leaf from profile, rather than the silhouette of an extruded prism.
        n=len(outline)
        anchor_x=sum(x for x,z in outline)/n
        anchor_z=.913
        sections=[(0.0,.04),(.10,.30),(.20,.65),(.30,.87),(.40,.97),
                  (.50,1.0),(.60,.97),(.70,.87),(.80,.65),(.90,.30),(1.0,.04)]
        vertices=[]
        for t,scale in sections:
            y=front+(rear-front)*t
            vertices.extend((anchor_x+(x-anchor_x)*scale,y,
                             anchor_z+(z-anchor_z)*scale) for x,z in outline)
        faces=[tuple(range(n-1,-1,-1)),tuple((len(sections)-1)*n+i for i in range(n))]
        for j in range(len(sections)-1):
            faces.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n))
        return vertices,faces
    return [
        wedge([(-.062,.913),(-.078,.945),(-.115,.973),(-.111,.978),
               (-.094,.978),(-.061,.968),(-.016,.938),(.008,.913)], -.045, .026),
        wedge([(.015,.914),(.025,.941),(.006,.969),(.013,.974),
               (.029,.970),(.064,.947),(.080,.914)], .015, .083),
    ]
h.crown_geometries = crown_geometries
source = source.replace('    part.add(fuse(geoms, 0.0026, 4, 0.2), mt["hair"])',
                        '    geoms.extend(crown_geometries())\n    part.add(fuse(geoms, 0.0026, 4, 0.2), mt["hair"])')
for before, after in replacements.items():
    if before not in source:
        raise RuntimeError('Hair geometry helper changed; cannot safely rebuild')
    source = source.replace(before, after)
exec(compile(source, 'reference_hair_v2', 'exec'), h.__dict__)
part = h.build_hair({'hair': material})
new = part.build(model, hair.parent)
old_mesh = hair.data
hair.data = new.data
bpy.data.objects.remove(new, do_unlink=True)
for group in list(hair.vertex_groups):
    hair.vertex_groups.remove(group)
head_group = hair.vertex_groups.new(name='Head')
head_group.add(list(range(len(hair.data.vertices))), 1.0, 'REPLACE')
for mod in list(hair.modifiers):
    if mod.type == 'DECIMATE':
        hair.modifiers.remove(mod)
reduction = hair.modifiers.new('Hair triangle reduction', 'DECIMATE')
reduction.ratio = 0.14
hair.modifiers.move(len(hair.modifiers) - 1, 0)
hair['partSlot'] = 'Hair'
hair['attachment'] = 'Head'
bpy.context.view_layer.update()
result = {'hair': hair.name, 'source_vertices': len(hair.data.vertices),
          'source_faces': len(hair.data.polygons), 'reduction_ratio': reduction.ratio,
          'head_weight': True, 'old_mesh_preserved': old_mesh.name}
