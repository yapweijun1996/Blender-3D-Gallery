"""Add an independently skinned torso underneath the default hoodie."""
import bpy,math
sc=bpy.data.scenes['GJH Reference Visitor'];model=next(c for c in sc.collection.children if c.name.startswith('GJH Visitor Model'));root=next(o for o in model.objects if o.name=='GJH_Visitor');rig=next(o for o in model.objects if o.type=='ARMATURE')
if any(o.get('partSlot')=='Body' for o in model.objects):raise RuntimeError('Body slot already exists')
skin=next(o.data.materials[0] for o in model.objects if o.type=='MESH' and o.name.startswith('Arm tube.'))
rings=[(.304,.075,.060),(.335,.088,.068),(.39,.090,.071),(.46,.084,.065),(.50,.076,.058),(.53,.058,.047),(.55,.045,.040)]
verts=[];faces=[];n=24
for z,rx,ry in rings:
 for k in range(n):
  a=math.tau*k/n;verts.append((rx*math.cos(a),.005+ry*math.sin(a),z))
for j in range(len(rings)-1):
 for k in range(n):
  a=j*n+k;b=j*n+(k+1)%n;faces.append((a,b,b+n,a+n))
faces.append(tuple(reversed(range(n))));faces.append(tuple((len(rings)-1)*n+k for k in range(n)))
mesh=bpy.data.meshes.new('Body core');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(skin)
o=bpy.data.objects.new('Body',mesh);model.objects.link(o);o.parent=root;o['partSlot']='Body';o['attachment']='Spine'
for f in mesh.polygons:f.use_smooth=True
vg=o.vertex_groups.new(name='Spine');vg.add(list(range(len(mesh.vertices))),1.,'REPLACE');mod=o.modifiers.new('Visitor armature','ARMATURE');mod.object=rig
result={'created':o.name,'slot':'Body','vertices':len(mesh.vertices)}
