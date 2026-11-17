import bpy,sys,math,os
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=sys.argv[-1])
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');m=next(o for o in bpy.context.scene.objects if o.type=='MESH')
def smooth(a,b,v):
 t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)
groups=list(m.vertex_groups); targets={g.name:g.index for g in groups}; bins={g.index:{} for g in groups}; affected=[]
for v in m.data.vertices:
 x,y,z=v.co; body=(1-smooth(.075,.14,abs(x)))*smooth(.24,.28,z)*(1-smooth(.405,.445,z))
 arm=smooth(.12,.16,abs(x))*smooth(.19,.22,z)*(1-smooth(.405,.445,z))
 mask=max(body,arm)
 if mask<.01:continue
 affected.append(v.index); d={g.group:g.weight*(1-mask) for g in v.groups}
 mid=smooth(.29,.36,z); side='L_' if x>0 else 'R_'
 bw=body*(1-arm); aw=arm; total=max(bw+aw,1e-8)
 for name,w in [('Spine01',bw*(1-mid)/total),('Spine02',bw*mid/total),(side+'Hand',aw*(1-smooth(.255,.285,z))/total),(side+'Forearm',aw*smooth(.255,.285,z)*(1-smooth(.315,.35,z))/total),(side+'Upperarm',aw*smooth(.315,.35,z)/total)]:
  d[targets[name]]=d.get(targets[name],0)+mask*w
 for gi,w in d.items():
  q=round(w*100)
  if q: bins[gi].setdefault(q,[]).append(v.index)
print('affected',len(affected),flush=True)
for g in groups:
 g.remove(affected)
 for q,indices in bins[g.index].items():g.add(indices,q/100,'REPLACE')

# Keep the imported Tripo Actions as editable NLA tracks and export all clips.
scene=bpy.context.scene;scene.frame_set(1)
for image in bpy.data.images:
 if image.source == 'FILE' and not image.packed_file:
  image.pack()
out=os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,'chibi-boy-rig.blend'),compress=True)
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);m.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.gltf(filepath=os.path.join(out,'chibi-boy-animated.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_tangents=True)
print('ACTIONS',[(a.name,tuple(a.frame_range)) for a in bpy.data.actions])
