"""Replace the shorts boxes with a tapered waist and two soft cargo legs."""
import bpy, math
scene=bpy.data.scenes['GJH Reference Visitor']
model=next(c for c in scene.collection.children if c.name.startswith('GJH Visitor Model'))
root=next(o for o in model.objects if o.name=='GJH_Visitor')
for obj in list(model.objects):
    if obj.name.startswith(('Shorts waist','Shorts leg','Shorts tailored')):
        bpy.data.objects.remove(obj,do_unlink=True)
verts=[];faces=[]
def loft(rings,n=24):
    start=len(verts)
    for z,rx,ry,cx in rings:
        for i in range(n):
            a=2*math.pi*i/n
            def rounded(v):return math.copysign(abs(v)**.8,v)
            verts.append((cx+rx*rounded(math.cos(a)),ry*rounded(math.sin(a)),z))
    for j in range(len(rings)-1):
        for i in range(n):
            a=start+j*n+i;b=start+j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    faces.append(tuple(start+i for i in reversed(range(n))))
    end=start+(len(rings)-1)*n
    faces.append(tuple(end+i for i in range(n)))
loft([(.265,.116,.079,0),(.285,.115,.079,0),(.315,.105,.077,0)])
for s in (-1,1):
    loft([(.207,.061,.078,s*.063),(.212,.064,.080,s*.063),(.258,.062,.079,s*.063),(.278,.058,.077,s*.063)])
me=bpy.data.meshes.new('Tailored shorts');me.from_pydata(verts,[],faces);me.update()
obj=bpy.data.objects.new('Shorts tailored',me);model.objects.link(obj);obj.parent=root
obj.data.materials.append(next(m for m in bpy.data.materials if m.name.startswith('Cargo Pocket')))
for p in me.polygons:p.use_smooth=True
rig=next((o for o in model.objects if o.type=='ARMATURE'),None)
if rig:
    vg=obj.vertex_groups.new(name='Root');vg.add(list(range(len(me.vertices))),1.,'REPLACE');mod=obj.modifiers.new('Visitor armature','ARMATURE');mod.object=rig
