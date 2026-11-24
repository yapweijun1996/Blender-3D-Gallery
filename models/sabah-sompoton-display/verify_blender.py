"""Observe actual open/closed tube ends, mouth neck and chamber in the native and GLB meshes."""
import bpy,math,json,sys
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='sabah-sompoton-display'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
root=Path(args[0]) if args else Path(__file__).resolve().parent
results={}
for kind in ['native','reimport']:
    if kind=='native':bpy.ops.wm.open_mainfile(filepath=str(root/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(root/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    def listof(p):return [o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(p)]
    def one(p):
        m=listof(p);assert len(m)==1,(kind,p,[o.name for o in m]);return m[0]
    dg=bpy.context.evaluated_depsgraph_get()
    def geo(ob):
        e=ob.evaluated_get(dg);m=e.to_mesh()
        vs=[e.matrix_world@v.co for v in m.vertices]
        fc=[tuple(p.vertices) for p in m.polygons]
        e.to_mesh_clear()
        return vs,fc
    def geometry_db(o):
        v,f=geo(o); assert v and f
        return BVHTree.FromPolygons(v,f),v,f
    def read_hit(b,pt,di,d=5.):
        return b.ray_cast(Vector(pt),Vector(di),d)
    def manifold(v,f):
        # Source and import can split material vertices; weld by piecewise model-space coordinates for observation only.
        vi=[tuple(round(x,6) for x in q) for q in v]
        count=Counter(tuple(sorted([vi[p],vi[t]])) for row in f for p,t in zip(row,row[1:]+row[:1]) if vi[p]!=vi[t])
        return dict(total=len(count),one=sum(x==1 for x in count.values()),other=sum(x>2 for x in count.values()))
    db,gv,gf=geometry_db(one('Hollow organic gourd shell'))
    bottleM=manifold(gv,gf)
    assert bottleM['one']==bottleM['other']==0,(kind,bottleM)
    # The mouth is not a black cap. A slight pitch follows the formed neck.
    near=(-.252,-.023,.246);deep=(-.210,-.017,.226)
    direction=(Vector(deep)-Vector(near)).normalized()
    mouthClear=0
    for y in (-.0023,0,.0023):
        for z in (-.0023,0,.0023):
            hit,*_=read_hit(db,(near[0],near[1]+y,near[2]+z),direction,.046)
            assert hit is None,(kind,y,z,hit)
            mouthClear+=1
    # Near mouth skin has rings on either side of the central hole.
    for t in (-1,1):
        p,n,*_=read_hit(db,(-.255,-.021+t*.0109,.241),(1,0,0),.043)
        assert p and -0.24<p.x<-.226,(kind,p)
    # Actual chamber opening under both modeled rows, with retained closed lower interior skin.
    ch=[];neck=[]
    for x in (.000,.034,.068,.102):
        for y in (-.016,.016):
            p,n,*_=read_hit(db,(x,y,.315),(0,0,-1),.35)
            assert p and .057<p.z<.115 and n.z>.55,(kind,p,n,x,y)
            ch.append(p.z)
    # Hollow from tip to chamber corroborated by probing physical bounds of neck sections.
    for x,y,z in [(-.219,-.018,.232),(-.180,-.009,.203),(-.133,-.003,.175),(-.086,0,.163),(-.018,0,.157)]:
        hi,n,*_=read_hit(db,(x,y,z),(0,0,1),.12)
        lo,m,*_=read_hit(db,(x,y,z),(0,0,-1),.10)
        assert hi and lo and n.z<-.63 and m.z>.58,(kind,x,hi,lo,n,m)
        neck.append(hi.z-lo.z)
    chamberSeatRays=0
    padContact=[]
    for x in (-.061,.058):
        for y in (-.037,.037):
            p,n,*_=read_hit(db,(x,y,.055),(0,0,1),.071)
            pd=next(o for o in listof('Felt pinched-contact cradle pad') if abs(o.matrix_world.translation.x-x)<.005 and abs(o.matrix_world.translation.y-y)<.005)
            pt,*_=read_hit(geometry_db(pd)[0],(x,y,.099),(0,0,-1),.045)
            assert p and pt and -.001<(pt.z-p.z)<.002,(kind,x,y,p,pt)
            padContact.append(pt.z-p.z)
            chamberSeatRays+=1
    # No support vertex breaks into the actual inner gourd cavity.
    interiorMargins=[]
    for obj in listof('Bent display hardware')+listof('Felt pinched-contact'):
        for v in geo(obj)[0]:
            surf,n,*_=read_hit(db,(v.x,v.y,.154),(0,0,-1),.14)
            assert surf and n.z>.25,(kind,obj.name,v,surf,n)
            interiorMargins.append(surf.z-v.z)
    assert min(interiorMargins)>.00020,(kind,min(interiorMargins))
    tubes={}
    for row in ('SHORT','LONG'):
        for i,x in enumerate((.000,.034,.068,.102)):
            name=f'{row}_RAFT_{i+1}'
            tube=one(f'Hollow bamboo stalk {name}')
            b,v,f=geometry_db(tube)
            topo=manifold(v,f)
            assert topo['one']==topo['other']==0,(kind,name,topo)
            y=-.016 if row=='SHORT' else .016
            ht=max(q.z for q in v);lo=min(q.z for q in v)
            depth=[]
            for dx,dy in [(0,0),(.003,0),(-.003,0),(0,.003),(0,-.003),(.004,.004),(-.004,.004)]:
                hit,n,*_=read_hit(b,(x+dx,y+dy,ht+.015),(0,0,-1),.64)
                assert hit and n.z>.32,(kind,name,hit,n)
                depth.append(ht-hit.z)
            if row=='SHORT':
                assert .327<min(depth)<.343 and max(depth)<.35
            elif i in (0,2):
                assert .010<min(depth) and max(depth)<.016
            else:
                assert .00050<min(depth)<.00210 and max(depth)<.0021
            # Rim/wall directional samples, lower piece remains closed.
            bottom,n,*_=read_hit(b,(x,y,lo-.016),(0,0,1),.04)
            assert bottom and n.z<-.85 and abs(bottom.z-lo)<.0002
            r0=0.013 if i!=1 else .0129
            endhits=0
            for t in range(16):
                theta=t*math.tau/16
                xx=x+r0*math.cos(theta);yy=y+r0*math.sin(theta)
                hit,n,*_=read_hit(b,(xx,yy,ht+.01),(0,0,-1),.025)
                assert hit and ht-hit.z<.0012,(kind,name,t,hit)
                endhits+=1
            tubes[name]=dict(totalM=ht-lo,topHeightM=ht,centerAndOffAxisProbes=len(depth),observedPocketDepthM=[min(depth),max(depth)],rimProbes=endhits)
    s=[tubes[f'SHORT_RAFT_{i+1}']['topHeightM'] for i in range(4)]
    l=[tubes[f'LONG_RAFT_{i+1}']['topHeightM'] for i in range(4)]
    assert max(s)-min(s)<.00012
    assert abs(l[0]-l[2])<.00012 and l[0]-l[1]>.085 and l[1]-l[3]>.057
    results[kind]=dict(mouthAxialClearProbes=mouthClear,chamberEntryRays=len(ch),hollowDepthObservationsM=neck,
                       pinchedStandSupportRays=chamberSeatRays,padContactM=padContact,allSupportVerticesChecked=len(interiorMargins),minimumSupportToCavityM=min(interiorMargins),gourdWatertightMesh=bottleM,tubes=tubes)
print(json.dumps(results,indent=2))
