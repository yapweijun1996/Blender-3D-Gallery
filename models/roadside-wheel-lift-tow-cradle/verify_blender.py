"""Check that the digital reference wheel seats and lift members actually connect."""
import bpy, math, sys, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
params=sys.argv[sys.argv.index('--')+1:]
U=(0,0,1); ST=.530; CT=math.sqrt(1-ST*ST)
def verify(imported):
    graph=bpy.context.evaluated_depsgraph_get()
    O=bpy.data.objects
    def shape(o):
        ev=o.evaluated_get(graph); mesh=ev.to_mesh();m=ev.matrix_world
        v=[m@x.co for x in mesh.vertices];f=[tuple(y.vertices) for y in mesh.polygons]
        ev.to_mesh_clear()
        return v,BVHTree.FromPolygons(v,f,all_triangles=all(len(x)==3 for x in f))
    def part(name):return shape(O[name])
    def boundary(v):
        return [tuple(a(p[k] for p in v) for k in range(3)) for a in (min,max)]
    tire,bvh=part('One original unbranded reference tire')
    cv=O['REFERENCE_WHEEL'].matrix_world.translation
    assert (cv-Vector((-.590,-.734,.504))).length<1e-6
    gaps=[]; rayg=[]; contact_samples=0; area_checks=0
    rubber=O['REFERENCE_WHEEL'].children_recursive
    fixed=[o for k in ('REAR_BODY_DISPLAY','RECOVERY_LIFT_DISPLAY','PAIRED_WHEEL_GRID_DISPLAY')
           for o in O[k].children_recursive if o.type=='MESH']
    FIX={o.name:shape(o) for o in fixed}
    for z in (-1,1):
        N=Vector((0,z*ST,-CT))
        pad=part('Tangent rubber seat insert X-1 Y%d'%z)
        A=min((q-cv).dot(N) for q in pad[0])
        B=max((q-cv).dot(N) for q in tire)
        gap=(A-B)*1000
        assert .038<gap<.042,(z,A,B,gap)
        gaps.append(gap)
        for j in range(-10,11):
            q=cv+Vector((j*.0027,0,0))+.20*N
            _,_,_,tire_dist=bvh.ray_cast(q,N,.40)
            _,norm,_,pad_dist=pad[1].ray_cast(q,N,.40)
            assert tire_dist is not None and pad_dist is not None
            assert norm.dot(N)<-.999,set((z,norm.dot(N)))
            assert 0<pad_dist-tire_dist<.00040,(z,j,(pad_dist-tire_dist)*1000)
            rayg.append((pad_dist-tire_dist)*1000);contact_samples+=1
        for side in (-1,1):
            ledge=part('Beneath rubber solid molded support X%d Y%d'%(side,z))[0]
            for k in ('Outer longitudinal wheel-grid arm ','Inner short groundless wheel-grid return '):
                sup=part(k+str(side))[0]
                L,R=boundary(ledge),boundary(sup)
                hull=tuple(min(L[1][d],R[1][d])-max(L[0][d],R[0][d]) for d in range(3))
                assert all(u>.004 for u in hull),(z,side,k,hull)
                assert part(k+str(side))[1].overlap(part('Beneath rubber solid molded support X%d Y%d'%(side,z))[1]), (z,side,k)
                area_checks+=1
    # Both seats remain open from the front at the center; sample removal does not
    # create a hidden supplied flat floor. Test the static support group alone.
    open_void_checks=0
    physical_grid=[v for k,v in FIX.items() if 'wheel-grid' in k or 'support X' in k or 'seat insert' in k]
    for cx in (-.590,.590):
        for i in range(-3,4):
            for j in range(-2,3):
                q=Vector((cx+.026*i,-.734+.013*j,.43))
                for _,tree in physical_grid:
                    hit=tree.ray_cast(q,Vector((0,0,-1)),.32)[0]
                    assert hit is None,(q,hit)
                open_void_checks+=1
    # No visual part of the staged sample penetrates the cradle, bearing,
    # or recovered body. Broadphase and triangle surfaces are separate gates.
    candidates=0
    for o in rubber:
        if o.type!='MESH':continue
        a,bt=shape(o); box=boundary(a)
        for n,(p,tree) in FIX.items():
            obbox=boundary(p)
            if all(min(box[1][d],obbox[1][d])>=max(box[0][d],obbox[0][d]) for d in range(3)):
                candidates+=1
                assert not bt.overlap(tree),(o.name,n)
    # The lip is a genuine through-bore with a smaller coaxial sliding member.
    body_b=part('True hollow outer telescoping collar')
    inside=body_b[1]; bore=0
    for x in (-.090,-.045,0,.045,.090):
        for z in (.234,.253,.285,.320,.338):
            origin=Vector((x,-.420,z)); q=Vector((0,1,0))
            assert inside.ray_cast(origin,q,.40)[0] is None,(origin,q)
            bore+=1
    for x in (-.106,.106):
        for z in (.231,.282,.340):
            origin=Vector((x,-.420,z));q=Vector((0,1,0))
            pt=inside.ray_cast(origin,q,.4)[0]
            assert pt is not None and abs(pt.y+.375)<1e-6,(origin,pt)
            bore+=1
    rail,_=part('Steel sliding inner tube with visible four-sided seat')
    R=boundary(rail);clear=[min(.0955-abs(p.x),.057-abs(p.z-.287)) for p in rail]
    assert min(clear)>.0029 and R[0][1]<-.45 and R[1][1]>-.27
    pins=[]
    for s in (-1,1):
        ob=O['Round cap highlights root joint '+str(s)]
        p=ob.matrix_world.translation
        assert abs(p.y+.129)<1e-6 and abs(p.z-.355)<1e-6 and abs(p.x-s*.2095)<1e-6
        assert abs((ob.matrix_world.to_3x3()@Vector((0,0,1))).normalized().x)>.999999
        cap,t=part(ob.name)
        cp=Vector((s*.27,-.129,.355));hit=t.ray_cast(cp,Vector((-s,0,0)),.2)[0]
        assert hit is not None and abs(hit.x-s*.214)<1e-6
        pins.append(tuple(p))
    pin,bv=part('Transverse root axle')
    axle=boundary(pin)
    for s in (-1,1):
        sleeve=boundary(part('Transverse root outer keeper '+str(s))[0])
        assert min(axle[1][0],sleeve[1][0])-max(axle[0][0],sleeve[0][0])>.014
        lower=part('Rear fork external yellow cheek '+str(s))[1]
        assert bv.overlap(lower),s
    middle=part('Central yoke top-pivot head')[1]
    for n in ('Round machined upper yoke pin','Fixed neck between inner tube and rotating-looking yoke','Strong one-piece transverse yoke'):
        assert middle.overlap(part(n)[1]),n
    joint_foot=[]
    for s in (-1,1):
        b,c=part('Connection foot welded from yoke to wheel-pocket '+str(s))
        assert c.overlap(part('Dark yoke seat square collar '+str(s))[1])
        assert c.overlap(part('Beneath rubber solid molded support X%d Y1'%s)[1])
        joint_foot.append(s)
    return dict(imported=imported, contactTangentGapsMm=gaps, contactRayGapsMm=(min(rayg),max(rayg)),
      contactRays=contact_samples, openPocketRays=open_void_checks, axleCaps=pins, pairBroadphase=candidates,
      ledgeRailEnvelopeChecks=area_checks, centralPinJoinedSurfaces=3, yokeFootShoulders=joint_foot, boreOpenAndRingRays=bore,
      telescopingInnerLowerClearanceMm=min(clear)*1000)
bpy.ops.wm.open_mainfile(filepath=params[0]);native=verify(False)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=params[1]);imp=verify(True)
print('M34_GEOMETRY='+json.dumps([native,imp]))
