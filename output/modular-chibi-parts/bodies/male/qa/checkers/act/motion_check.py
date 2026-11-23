"""Measure a skinned garment against the posed master. Run with guarded Blender.

-- <master.blend> <motion.glb> <garment.glb> <out_dir> [additional_actions.glb]
The local actions.glb supplies sit_idle and hold_item when checking the legacy library.
"""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from chibi import *
from mathutils.bvhtree import BVHTree

LEGACY = ()
ADDED = ('sit_down','sit_idle','stand_up','hold_item')


def garment_check(triangles=False):
    master,motion,module,out,*extra = sys.argv[sys.argv.index('--')+1:]
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=master,load_ui=False,use_scripts=False)
    scene=bpy.context.scene
    arm,body=scene.objects['Armature'],scene.objects['Base_Body']
    added=load(Path(module))
    garment, = [o for o in added if o.type=='MESH' and len(o.vertex_groups)]
    world=garment.matrix_world.copy()
    garment.parent=arm
    garment.matrix_world=world
    for m in list(garment.modifiers): garment.modifiers.remove(m)
    mod=garment.modifiers.new('Armature','ARMATURE')
    mod.object=arm
    for o in added-{garment}: bpy.data.objects.remove(o,do_unlink=True)
    bind(arm,None)
    def measure():
        pts=coords(body)
        tree=BVHTree.FromPolygons(pts.tolist(),body_tri,all_triangles=True)
        gp=coords(garment)
        mn=math.inf
        inside=0
        for pos in gp:
            point,normal,_,_=tree.find_nearest(pos)
            distance=(Vector(pos)-point).dot(normal)
            inside+=int(distance<0)
            mn=min(mn,distance)
        if triangles:
            gt=BVHTree.FromPolygons(gp.tolist(),garment_tri,all_triangles=True)
            return len(tree.overlap(gt)),mn,float(gp[:,2].min())
        return inside,mn,float(gp[:,2].min())
    def faces(o):
        o.data.calc_loop_triangles()
        return [tuple(f.vertices) for f in o.data.loop_triangles]
    body_tri,garment_tri=faces(body),faces(garment)
    res={'rest':measure()[:2]}
    detail={}
    new_path=Path(extra[0]) if extra else OUT/'actions.glb'
    inputs={Path(motion).resolve():LEGACY}
    inputs[new_path.resolve()]=inputs.get(new_path.resolve(),())+ADDED
    for path,clips in inputs.items():
        if path==new_path.resolve():
            scene.render.fps=FPS
            scene.render.fps_base=1
        prior=set(bpy.data.actions)
        extras=load(path)
        actions=set(bpy.data.actions)-prior
        for o in extras:
            o.hide_render=True
            o.hide_viewport=True
        for name in clips:
            act=next((a for a in actions if a.name==name or a.name.startswith(name+'.')),None)
            if not act:
                if name in ADDED: raise KeyError(name)
                continue
            bind(arm,act)
            first,last=act.frame_range
            results=[]
            for f in sorted({float(first),float(last),*(n/2 for n in range(math.ceil(2*first-1e-5),math.floor(2*last+1e-5)+1))}):
                scene.frame_set(math.floor(f),subframe=f%1)
                count,dist,floor=measure()
                results.append(dict(frame=f,count=count,min_signed_m=dist,garment_min_z_m=floor))
            detail[name]=results
            res[name]=(max(r['count'] for r in results),min(r['min_signed_m'] for r in results))
    stem='motion_check_tri' if triangles else 'motion_check'
    for name,value in res.items(): print('RESULT',name,*value,flush=True)
    (out/(stem+'.json')).write_text(json.dumps(res,indent=2)+'\n')
    (out/(stem+'_frames.json')).write_text(json.dumps(detail,indent=2)+'\n')

if __name__=='__main__':
    garment_check()
