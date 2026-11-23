"""Measure the master body, floor, chair and grip on every integer and half frame."""
import json
import sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate_actions import mount, penetration, solids, triangles
from props_check import exterior,authored_grip
sys.path.insert(0,str(chibi.HANDS))
from hand_common import rest_data
from hand_check import hand_geometry
from hand_surface import patches, nearest

def deep_record(pairs, depths, checker):
    if not len(pairs):
        return {"depth_mm":0.0}
    i = int(np.argmax(depths))
    a,b = pairs[i]
    return {"depth_mm":round(float(depths[i]),6), "triangles":[a,b],
            "regions":[checker.regions[a],checker.regions[b]]}

def self_hits(checker, points):
    pairs, _ = checker.overlap(points)
    a,b = np.array(pairs, dtype=int).reshape(-1,2).T
    depths = pair_depth(points[checker.indices[a]],points[checker.indices[b]]) if pairs else []
    hits, hit_depths, groups = [], [], Counter()
    for (i,j),d in zip(pairs,depths):
        ri,rj=checker.regions[i],checker.regions[j]
        if target(ri,rj):
            groups[' / '.join(sorted([ri,rj]))]+=1
            hits.append((i,j))
            hit_depths.append(d)
    return {"all_pairs":len(pairs), "target_pairs":len(hits),"target_regions":dict(sorted(groups.items())),
            "target_triangle_pairs":hits, "deepest_target":deep_record(hits,hit_depths,checker),
            "deepest_all":deep_record(pairs,depths,checker)}

def summary(rows):
    groups = Counter()
    for row in rows:
        groups.update(row["target_regions"])
    def worst(key):
        r=max(rows,key=lambda r:r[key]["depth_mm"])
        return {"frame":r["frame"],**r[key]}
    return {"samples":len(rows),
            "target_integer":sum(r["target_pairs"] for r in rows if r["frame"].is_integer()),
            "target_half":sum(r["target_pairs"] for r in rows if not r["frame"].is_integer()),
            "target_total":sum(r["target_pairs"] for r in rows),
            "all_integer":sum(r["all_pairs"] for r in rows if r["frame"].is_integer()),
            "all_half":sum(r["all_pairs"] for r in rows if not r["frame"].is_integer()),
            "target_by_region":dict(groups),"deepest_target":worst("deepest_target"),"deepest_all":worst("deepest_all")}

def audit(state):
    path = SOURCE if state=="before" else FIXED
    scene,arm,body,actions=load(path)
    checker=Checker(body)
    rest=posed(body)
    chair,=chibi.load(ASSETS/'chair.glb')
    cup,=chibi.load(ASSETS/'prop.glb')
    cp,ct=posed(chair),triangles(chair)
    pp,pt=posed(cup),triangles(cup)
    parts=solids(cp,ct)
    ctree=BVHTree.FromPolygons(cp.tolist(),ct,all_triangles=True)
    sole={s:np.flatnonzero((sg*rest[:,0]>0)&(rest[:,2]<.0011)) for s,sg in zip(SIDES,(1,-1))}
    tips,*_=rest_data(body,arm,'Right')
    pads=patches(body,arm,'Right',tips,hand_geometry(body,'Right',-1,tips))
    ptris=[tuple(i+len(rest) for i in tr) for tr in pt]
    socket=mount()
    report={"blender":bpy.app.version_string,"fps":FPS,"master_sha256":sha(MASTER),"action_sha256":sha(path),
            "attachment_sha256":sha(ASSETS/'attachment.json'),**checker.stats,
            "sole_vertex_indices":{k:v.tolist() for k,v in sole.items()},"clips":{}}
    for name,last in CLIPS.items():
        chibi.bind(arm,actions[name])
        assert tuple(actions[name].frame_range)==(0,last)
        rows=[]
        for tick in range(2*last+1):
            f=tick/2
            at(scene,f)
            p=posed(body)
            bt=BVHTree.FromPolygons(p.tolist(),checker.faces,all_triangles=True)
            hip=arm.matrix_world@bone(arm,'Hips').head
            row={"frame":f,**self_hits(checker,p),"hips_mm":(np.array(hip)*1000).tolist(),
                 "foot_min_z_mm":{s:float(p[idx,2].min()*1000) for s,idx in checker.feet.items()},
                 "sole_xy_mm":{s:(p[idx,:2]*1000).round(7).tolist() for s,idx in sole.items()}}
            if name=="hold_item":
                m=np.array(arm.matrix_world@bone(arm,'RightHand').matrix@socket)
                pos=pp@m[:3,:3].T+m[:3,3]
                prop_tree=BVHTree.FromPolygons(pos.tolist(),pt,all_triangles=True)
                row["cup_body_pairs"]=len(bt.overlap(prop_tree))
                combined=np.concatenate((p,pos))
                row["pad_gap_mm"]={d:nearest(combined,pads[d],ptris)["distance_mm"] for d in ('Thumb','Index')}
                row["cup_up"]=m[:3,2].tolist()
                row["cup_origin_mm"]=(m[:3,3]*1000).tolist()
            else:
                count,_,depth=penetration(p,parts)
                row["chair_vertices_inside"]=count
                row["chair_depth_mm"]=depth
                row["chair_body_pairs"]=len(ctree.overlap(bt))
                row["all_chair_components_proven_exterior"]=row["chair_body_pairs"]==0 and exterior(parts,bt)
                row["chair_verts_inside_body"]=0 if row["all_chair_components_proven_exterior"] else None
                support=(rest[:,2]>.21)&(rest[:,2]<.41)&(abs(p[:,0])<.142)&(abs(p[:,0])>.008)&(abs(p[:,1]-hip.y)<.054)&(abs(p[:,1])<.098)
                row["seat_gap_mm"]={s:float((p[sel,2].min()-chair['seat_height_m'])*1000) if np.any(sel) else None
                                    for s,sel in [(s,support&(sg*p[:,0]>0)) for s,sg in zip(SIDES,(1,-1))]}
            rows.append(row)
        report["clips"][name]={"summary":summary(rows),"samples":rows}
        print(name,report["clips"][name]["summary"],flush=True)
    report["authored_grip"]=authored_grip(path)
    (OUT/f"body_selfcheck_{state}.json").write_text(json.dumps(report,separators=(',',':'))+'\n')

if __name__=="__main__":
    audit(sys.argv[sys.argv.index('--')+1])
