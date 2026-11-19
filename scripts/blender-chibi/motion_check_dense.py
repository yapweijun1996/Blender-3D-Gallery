"""Motion poke-through check for a skinned garment on the master body.
Usage (guarded Blender): -- <master.blend> <motion.glb> <garment.glb> <out_dir>
Prints per clip: max garment vertices inside the posed body and the minimum signed distance.
NOTE: do not change rotation_mode of pose bones, the clips animate quaternions."""
import bpy,math,sys,json
from mathutils.bvhtree import BVHTree
master,motion,garment,out=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=master)
sc=bpy.context.scene;arm=sc.objects['Armature'];body=sc.objects['Base_Body']
before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=garment)
new=[o for o in sc.objects if o not in before]
g=[o for o in new if o.type=='MESH'][0]
g.parent=None
for o in new:
    if o.type=='ARMATURE':bpy.data.objects.remove(o)
for md in list(g.modifiers):g.modifiers.remove(md)
g.name='garment';g.parent=arm
md=g.modifiers.new('Armature','ARMATURE');md.object=arm
before=set(sc.objects);bpy.ops.import_scene.gltf(filepath=motion)
src=[o for o in sc.objects if o.type=='ARMATURE' and o not in (arm,)][-1]
for o in sc.objects:
    if o.type=='MESH' and o not in (body,g):o.hide_viewport=True;o.hide_render=True
src.hide_viewport=True;src.hide_render=True
def measure():
    dg=bpy.context.evaluated_depsgraph_get()
    be=body.evaluated_get(dg);bm=be.to_mesh()
    tree=BVHTree.FromPolygons([be.matrix_world@v.co for v in bm.vertices],[p.vertices[:] for p in bm.polygons])
    ge=g.evaluated_get(dg);gm=ge.to_mesh();inside=0;mn=9
    for v in gm.vertices:
        w=ge.matrix_world@v.co;loc,n,i,d=tree.find_nearest(w)
        s=(w-loc).dot(n);mn=min(mn,s);inside+=(s<0)
    be.to_mesh_clear();ge.to_mesh_clear();return inside,mn
arm.animation_data_create();res={}
sc.frame_set(1);arm.animation_data.action=None;bpy.context.view_layer.update()
res['rest']=measure()
for name in('walk','run','wave','jump','idle','nod','dance'):
    a=bpy.data.actions.get(name)
    if not a:continue
    arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
    f0,f1=a.frame_range;worst=0;mn=9
    for fr in range(int(f0),int(f1)+1):
        sc.frame_set(fr);i,m=measure();worst=max(worst,i);mn=min(mn,m)
    res[name]=(worst,round(mn,4))
for k,v in res.items():print('RESULT',k,'max_verts_inside',v[0] if isinstance(v,tuple) else v,'min_signed_dist',v[1] if isinstance(v,tuple) else '')
sc.render.engine='BLENDER_WORKBENCH';sc.display.shading.light='STUDIO';sc.display.shading.color_type='MATERIAL'
sc.render.resolution_x=sc.render.resolution_y=500
cam=bpy.data.cameras.new('c');co=bpy.data.objects.new('c',cam);sc.collection.objects.link(co);sc.camera=co;cam.type='ORTHO';cam.ortho_scale=1.5
co.location=(0,-6,0.5);co.rotation_euler=(math.radians(90),0,0)
for name in('walk','run','wave','jump'):
    a=bpy.data.actions.get(name)
    if not a:continue
    arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
    f0,f1=a.frame_range;sc.frame_set(int(f0+(f1-f0)*.4));sc.render.filepath=f'{out}/{name}.png';bpy.ops.render.render(write_still=True)
json.dump({k:v for k,v in res.items()},open(f'{out}/motion_check.json','w'))
