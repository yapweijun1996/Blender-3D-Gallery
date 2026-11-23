"""Round-trip validation on evaluated geometry. Every sample includes endpoints or midpoints."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
import csv
from collections import Counter
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(PARTS/'body-fix'))
from bodycheck import Checker
from clearance import arm_contact,knee_contact,SIDES
from validate_actions import triangles
MM=1000
def tree(p,faces):
    return BVHTree.FromPolygons(p.tolist(),faces,all_triangles=True)

def set_time(scene,f):
    scene.frame_set(int(f),subframe=f%1)

def body_checks(frames,demo=False):
    import bodycheck
    if demo:
        sc=setup()
        arm=armature(load(BODY))
        body=bpy.data.objects['Base_Body']
        load(BANK)
    else:
        sc,arm,body,_=bodycheck.load(BANK)
    sc.render.fps=FPS
    ch=Checker(body)
    result={}
    for name in NAMES:
        bind(arm,bpy.data.actions[name])
        rows=[]
        for f in frames:
            set_time(sc,f)
            pts=coords(body)
            pairs,_=ch.overlap(pts)
            regions=Counter(tuple(sorted((ch.regions[i],ch.regions[j]))) for i,j in pairs
                            if any(arm_contact(ch.regions[i],ch.regions[j],s) or knee_contact(ch.regions[i],ch.regions[j],s) for s in SIDES))
            rows.append(dict(frame=f,target_pairs=sum(regions.values()),all_pairs=len(pairs),
                             regions=str(dict(regions)) if regions else ''))
        result[name]=rows
        print('SELF',name,max(r['target_pairs'] for r in rows),max(r['all_pairs'] for r in rows),
              set(r['regions'] for r in rows if r['regions']),flush=True)
    return result

def group_labels(ob):
    return [ob.vertex_groups[max(v.groups,key=lambda g:g.weight).group].name.split(':')[-1] for v in ob.data.vertices]
def apply(p,m):
    a=np.asarray(m)
    return p@a[:3,:3].T+a[:3,3]
def local_coords(ob):
    return np.array([v.co[:] for v in ob.data.vertices],dtype=float)
def winding(point,triangles):
    # Summed oriented solid angle, independent of ray direction and UV splits.
    rays=triangles-point
    length=np.linalg.norm(rays,axis=2)
    a,b,c=rays.transpose(1,0,2)
    denominator=length.prod(1)
    for u,v,w in ((a,b,2),(b,c,0),(c,a,1)):
        denominator+=np.einsum('ij,ij->i',u,v)*length[:,w]
    numerator=np.einsum('ij,ij->i',a,np.cross(b,c))
    return abs(np.arctan2(numerator,denominator).sum()/(2*math.pi))

def shell(points,part):
    vertices=points[np.unique(part)]
    return vertices.min(0),vertices.max(0),vertices[0],points[part]

def encloses(outer,inner):
    # With no surface intersections, an enclosed connected shell must have
    # fully contained bounds. Test the witness against that individual shell.
    return int((inner[0]>=outer[0]).all() and (inner[1]<=outer[1]).all()
               and winding(inner[2],outer[3])>.5)

def components(points,faces):
    # Material splits duplicate exported vertices; only weld for component identification.
    from collections import defaultdict
    touching=defaultdict(list)
    for i,f in enumerate(faces):
        for j in f:touching[tuple(points[j].round(7))].append(i)
    unseen=set(range(len(faces)))
    while unseen:
        stack=[unseen.pop()];part=[]
        while stack:
            i=stack.pop();part.append(faces[i])
            for j in faces[i]:
                for a in touching[tuple(points[j].round(7))]:
                    if a in unseen:unseen.remove(a);stack.append(a)
        yield part

def prop_checks(frames,debug=False,master=False):
    if master:
        bpy.ops.wm.open_mainfile(filepath=str(MASTER),load_ui=False,use_scripts=False)
        sc=bpy.context.scene
        sc.render.fps=FPS
        arm=sc.objects['Armature'];body=sc.objects['Base_Body']
    else:
        sc=setup();arm=armature(load(BODY));body=bpy.data.objects['Base_Body']
    labels=group_labels(body)
    fingers={s:[i for i,l in enumerate(labels) if l.startswith(s+'Hand') and l!=s+'Hand'] for s in SIDES}
    rest=coords(body)
    sole={s:np.flatnonzero((rest[:,2]<.0011)&np.array([n.startswith(s) for n in labels])) for s in SIDES}
    # Keep disconnected body shells separate when testing for full enclosure.
    bf=triangles(body)
    body_parts=[np.array(part) for part in components(rest,bf)]
    load(BANK)
    result={}
    for name in NAMES:
        cfg=json.loads((HERE/'props'/(FILES[name]+'.attachment.json')).read_text())
        objects=load(HERE/cfg['prop'])
        rigid=next(o for o in objects if o.name==cfg['node'])
        static=[o for o in objects if o!=rigid]
        props=[]
        for o in [rigid]+static:
            verts=local_coords(o);faces=triangles(o)
            parts=list(components(verts,faces))
            props.append((o,verts,faces,parts))
        bind(arm,bpy.data.actions[name])
        first=None;rows=[]
        for f in frames:
            set_time(sc,f)
            p=coords(body); bt=tree(p,bf)
            body_shells=[shell(p,part) for part in body_parts]
            if first is None:first=p.copy()
            row=dict(frame=f,floor_mm=MM*p[:,2].min(),
                     sole_drift_mm=max(np.linalg.norm(p[i]-first[i],axis=1).max()*MM for i in sole.values()),
                     seam_mm=np.linalg.norm(p-first,axis=1).max()*MM if f==48 else None)
            for side,ids in sole.items():
                row[side+'_heel_mm']=p[ids[rest[ids,1]>.020],2].min()*MM
                row[side+'_toe_mm']=p[ids[rest[ids,1]<-.050],2].min()*MM
            for o,verts,faces,parts in props:
                m=equipment(name,arm,f,cfg) if o==rigid else o.matrix_world
                q=apply(verts,m)
                pt=tree(q,faces)
                hits=bt.overlap(pt)
                key='item' if o==rigid else 'shelf'
                row[key+'_pairs']=len(hits)
                # Zero intersecting triangle pairs + no enclosed component certifies
                # zero penetration, including edge-only contacts missed by vertex tests.
                enclosed=0
                for part in parts:
                    ps=shell(q,np.array(part))
                    enclosed+=sum(encloses(bs,ps)+encloses(ps,bs) for bs in body_shells)
                row[key+'_enclosed']=enclosed
                if debug and hits:
                    bad=Counter(labels[bf[i][0]] for i,j in hits)
                    material=Counter(o.data.materials[o.data.polygons[o.data.loop_triangles[j].polygon_index].material_index].name for i,j in hits)
                    print('HIT',name,f,key,len(hits),bad.most_common(5),material.most_common(),flush=True)
                if o==rigid and name=='take_item':
                    waiting=apply(verts,equipment(name,arm,f,cfg,first_pick=True))
                    row['first_pick_pairs']=len(tree(waiting,faces).overlap(bt))
                    waiting_shells=[shell(waiting,np.array(part)) for part in parts]
                    row['first_pick_enclosed']=sum(encloses(bs,ws)+encloses(ws,bs)
                                                   for bs in body_shells for ws in waiting_shells)
                if o==rigid:
                    for s in (SIDES if name=='hold_box' else ['Right']):
                        # Every accepted witness is a finger vertex on the actual skin and a prop face.
                        gap,label=min((pt.find_nearest(p[i])[3]*MM,labels[i]) for i in fingers[s])
                        row[s+'_finger_mm']=gap;row[s+'_finger']=label
                        if debug: print('GAP',name,f,s,round(gap,3),label,flush=True)
                    row['prop_floor_mm']=q[:,2].min()*MM
            rows.append(row)
        result[name]=rows
        print('PROP',name, {k:round(float(max(r[k] for r in rows if r[k] is not None)),5)
                           for k in rows[0] if k!='frame' and not k.endswith('finger') and any(r[k] is not None for r in rows)},flush=True)
        for o in objects:bpy.data.objects.remove(o,do_unlink=True)
    return result

def main():
    debug='--probe' in sys.argv
    frames=[0,3,6,10,14,18,22,25,27,29,36,42,48] if debug else [i/2 for i in range(97)]
    for model in ('demo','master'):
        a=body_checks(frames,demo=model=='demo')
        b=prop_checks(frames,debug,master=model=='master')
        if debug:continue
        for n in NAMES:
            rows=[{**x,**y} for x,y in zip(a[n],b[n])]
            filename=n+('_master' if model=='master' else '')+'.csv'
            with (HERE/'checks'/filename).open('w') as fp:
                w=csv.DictWriter(fp,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

if __name__=='__main__':main()
