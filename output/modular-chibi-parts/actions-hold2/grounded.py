"""Replay both shod rigs at the supplied wardrobe placement, including the shelf assembly."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from audit import tree, triangles, set_time, apply, local_coords, group_labels
from module_checks import MODULES

def run():
    result={n:{} for n in NAMES}
    config=placement();lift=config['sneaker_v3_root_lift_m']
    for model in ('master','demo'):
        if model=='master':
            bpy.ops.wm.open_mainfile(filepath=str(MASTER),load_ui=False,use_scripts=False)
            sc=bpy.context.scene;sc.render.fps=FPS
            arm=sc.objects['Armature'];body=sc.objects['Base_Body']
        else:
            sc=setup();arm=armature(load(BODY));body=bpy.data.objects['Base_Body']
        load(BANK)
        shoe=dress(arm,MODULES['sneakers'])
        rest=coords(shoe);labels=group_labels(shoe)
        support={}
        for side in ('Right','Left'):
            low=np.flatnonzero(np.array([l.startswith(side) for l in labels])&(rest[:,2]<-.0057))
            support[side+' heel']=low[rest[low,1]>.02]
            support[side+' forefoot']=low[rest[low,1]<-.05]
        assert all(len(i)>0 for i in support.values())
        sole=np.unique(np.concatenate(list(support.values())))
        arm.location.z+=lift
        bpy.context.view_layer.update()
        bf,sf=triangles(body),triangles(shoe)
        for n in NAMES:
            cfg=json.loads((HERE/'props'/(FILES[n]+'.attachment.json')).read_text())
            objects=load(HERE/cfg['prop'])
            prop=next(o for o in objects if o.name==cfg['node'])
            shelf=next((o for o in objects if o!=prop),None)
            if shelf:
                place_shelf(shelf,config,lift)
                bpy.context.view_layer.update()
                shelf_pts=coords(shelf);shelf_bvh=tree(shelf_pts,triangles(shelf))
            verts=local_coords(prop);faces=triangles(prop)
            bind(arm,bpy.data.actions[n])
            mn=1e6;hi=-1e6;drift=0;hits=0;foot_ref=None;deck_gap=0
            for tick in range(97):
                f=tick/2;set_time(sc,f)
                sp=coords(shoe)
                if foot_ref is None:foot_ref=sp[sole].copy()
                mn=min(mn,float(sp[:,2].min()*1000))
                hi=max(hi,max(float(sp[i,2].min()*1000) for i in support.values()))
                drift=max(drift,float(np.linalg.norm(sp[sole]-foot_ref,axis=1).max()*1000))
                sb=tree(sp,sf);bb=tree(coords(body),bf)
                pp=apply(verts,equipment(n,arm,f,cfg,lift))
                pb=tree(pp,faces)
                hits=max(hits,len(pb.overlap(sb)),len(pb.overlap(bb)),len(bb.overlap(sb)))
                if shelf:
                    waiting=apply(verts,equipment(n,arm,f,cfg,lift,first_pick=True))
                    wb=tree(waiting,faces)
                    hits=max(hits,len(shelf_bvh.overlap(sb)),len(shelf_bvh.overlap(bb)),
                             len(wb.overlap(sb)),len(wb.overlap(bb)))
                    if f<=GRIP or f==48:
                        deck_gap=max(deck_gap,abs(float(pp[:,2].min())-config['shelf_deck_z_m']-lift)*1000)
            result[n][model]=dict(samples=97,character_lift_mm=lift*1000,shoe_floor_min_mm=mn,
                                  heel_forefoot_max_height_mm=hi,sole_drift_mm=drift,
                                  max_shoe_body_or_prop_and_shelf_pairs=hits,shelf_contact_error_mm=deck_gap,
                                  shelf_foot_z_mm=float(shelf_pts[:,2].min())*1000 if shelf else None,
                                  pass_gate=mn>=-1 and hi<1 and drift<.001 and hits==0 and deck_gap<.01)
            print('GROUND',n,model,result[n][model],flush=True)
            for o in objects:bpy.data.objects.remove(o,do_unlink=True)
    (HERE/'checks/grounded.json').write_text(json.dumps(result,indent=2)+'\n')
    assert all(row['pass_gate'] for clip in result.values() for row in clip.values())

if __name__=='__main__':run()
