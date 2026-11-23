"""Replace the reference visitor's hair, preserving its rig and object identity.

Run inside the connected Blender on the editable visitor scene. The component
uses the original v4 geometry helpers; it does not touch any other model part.
"""
import bpy
import importlib.util
from mathutils import Vector
from pathlib import Path

base = Path('/Users/yapweijun/Documents/GitHub/Blender-3D-Gallery')
helper = base / 'models/chibi-visitor-v4/generate.py'
spec = importlib.util.spec_from_file_location('visitor_v4_hair_helpers', helper)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
scene = bpy.data.scenes['GJH Reference Visitor']
model = next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
old = next(o for o in model.objects if o.type == 'MESH' and o.name.startswith('Hair'))
root = old.parent
mat = old.data.materials[0]
part = h.Part('Hair redesign')
# Use one continuous sculpted shell. The inherited skull has a squarer lower
# section than a sphere, so the nape follows a matching superellipse.
original_shell = h.hshell
def fitted_shell(az, el, radius):
    if el >= 0:
        return original_shell(az, el, radius)
    a, e = h.m.radians(az), h.m.radians(el)
    horizontal = h.sp(h.m.cos(e), 2 / 2.65)
    vertical = h.sp(h.m.sin(e), 2 / 2.65)
    return h.HH + Vector((horizontal*h.m.sin(a)*1.035,
                          -horizontal*h.m.cos(a)*1.05,
                          vertical*.99))*radius
h.hshell = fitted_shell
nv, nr = 80, 24
cap = h.g_cap(.192, nv=nv, nr=nr, solid=True)
geoms=[cap]
# A handful of irregular shallow radial locks; remesh merges them into the
# shell so the surface stays continuous instead of leaving dark seams.
back_locks=[
 ([(150,74,.97),(143,51,.99),(136,24,1.0),(130,0,1.0),(126,-22,.99)],.125),
 ([(163,78,.97),(160,52,.99),(155,20,1.0),(151,-4,1.0),(148,-26,.99)],.135),
 ([(177,80,.97),(177,52,1.0),(176,21,1.0),(173,-4,1.0),(169,-31,.99)],.145),
 ([(192,78,.97),(196,50,1.0),(198,18,1.0),(200,-6,1.0),(202,-27,.99)],.140),
 ([(207,76,.97),(216,48,.99),(221,19,1.0),(224,-4,1.0),(225,-22,.99)],.130),
 ([(220,73,.97),(234,47,.99),(240,16,1.0),(242,-2,1.0),(239,-17,.99)],.120),
]
for ctrl,width in back_locks:
    geoms.append(h.g_lock(ctrl,width,.192,seg=16,thick=.013,groove=0,root=.7,taper=2.1,tip=.03,end=.85))
# The original v4 fringe provides the expressive eye-safe asymmetric sweep.
h.hshell=original_shell
front = [([(25, 52, 0.97), (60, 74, 1.0), (120, 78, 1.0), (165, 62, 1.01)], 0.125, 0.198, 2.6), ([(10, 56, 0.97), (-40, 76, 1.0), (-110, 78, 1.0), (-160, 62, 1.01)], 0.125, 0.198, 2.6), ([(-10, 66, 1.0), (-45, 58, 1.06), (-75, 44, 1.1), (-90, 30, 1.08)], 0.11, 0.198, 2.2), ([(-82, 30, 0.99), (-78, 8, 1.0), (-70, -8, 1.0), (-64, -19, 1.0)], 0.07, 0.194, 2.6), ([(84, 30, 0.99), (80, 8, 1.0), (72, -8, 1.0), (64, -18, 1.0)], 0.07, 0.194, 2.6), ([(-40, 40, 0.97), (-66, 22, 1.0), (-78, 4, 1.01), (-74, -12, 1.03)], 0.115, 0.196, 2.0), ([(50, 40, 0.97), (70, 22, 1.0), (80, 4, 1.01), (76, -12, 1.03)], 0.115, 0.196, 2.0), ([(14, 50, 0.97), (-30, 44, 1.0), (-66, 26, 1.02), (-90, 4, 1.08), (-102, -6, 1.3)], 0.13, 0.198, 1.6), ([(8, 60, 0.97), (-35, 56, 1.0), (-68, 36, 1.01), (-92, 17, 1.05), (-104, 9, 1.31)], 0.135, 0.2, 1.6), ([(42, 48, 0.97), (66, 38, 1.0), (86, 20, 1.02), (92, 4, 1.08), (102, -4, 1.29)], 0.13, 0.198, 1.6), ([(40, 58, 0.97), (64, 52, 1.0), (82, 35, 1.01), (92, 21, 1.05), (104, 14, 1.3)], 0.135, 0.2, 1.6), ([(22, 50, 0.97), (-4, 40, 1.0), (-26, 22, 1.0), (-38, -4, 1.0)], 0.14, 0.2, 2.0), ([(28, 48, 0.98), (14, 36, 1.0), (-2, 18, 1.005), (-10, -8, 1.0)], 0.125, 0.202, 2.0), ([(31, 44, 0.99), (24, 30, 1.0), (12, 13, 1.01), (4, -5, 1.005)], 0.095, 0.204, 2.0), ([(33, 46, 0.98), (40, 32, 1.0), (42, 14, 1.0), (37, -8, 1.0)], 0.11, 0.202, 2.0)]
for ctrl,width,radius,taper in front:
    geoms.append(h.g_lock(ctrl,width,radius,thick=.022 if taper == 1.6 else None,taper=taper,root=.72,tip=.06,groove=0,end=.65 if taper == 1.6 else .8))
# Two low broad crown sweeps intersect the cap deeply; they read as hair
# planes flowing out of the crown instead of three separate antennae.
for ctrl,width,thick in [
    ([(.030,.020,.903),(.018,.016,.922),(-.010,.008,.940),(-.047,.002,.944)],.080,.010),
    ([(-.015,.047,.902),(-.040,.040,.920),(-.069,.030,.929),(-.095,.026,.928)],.068,.009),
]:
    points=h.path3(ctrl,12)
    geoms.append(h.g_leaf(points,[Vector((0,0,1))]*len(points),width,thick,groove=0,root=1.0,tip=.025,taper=1.8,end=.8))
# Union the fringe and crown into the cap. Intersection boundaries cannot
# become black cracks because the mesh is remeshed into a single surface.
h.SCENE=scene.name
part.add(h.fuse(geoms,voxel=.0022,smooth=2,ratio=.30),mat)
# The existing hair material reads vertex colour. Preserve its chestnut palette
# and the local shadowing in creases without adding external textures.
h.bake_ao(part,h.HH,h.lin(h.HAIR_HEX),samples=12,reach=.025,floor=.78,power=0.8)
new=part.build(model,root)
old_mesh=old.data
old.data=new.data
bpy.data.objects.remove(new,do_unlink=True)
for g in list(old.vertex_groups):old.vertex_groups.remove(g)
head=old.vertex_groups.new(name='Head');head.add(list(range(len(old.data.vertices))),1.0,'REPLACE')
for mod in list(old.modifiers):
    if mod.type=='DECIMATE':old.modifiers.remove(mod)
# Preserve the inherited armature modifier and existing object transform.
bpy.context.view_layer.update()
result={'hair':old.name,'vertices':len(old.data.vertices),'faces':len(old.data.polygons),'old_mesh_preserved':old_mesh.name,'head_weight':True}
