"""Measure genuine captured hinge/tray clearance in source Blender and GLB reimport."""
import bpy, math, sys, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=sys.argv[sys.argv.index('--')+1:]
def verify(imported=False):
    sc=bpy.context.scene
    hinge=bpy.data.objects['CHANGING_DECK_HINGE']
    fixed=bpy.data.objects['CHANGING_STATION_HOUSING']
    room=bpy.data.objects['FAMILY_ROOM_DISPLAY_CONTEXT']
    action=hinge.animation_data.action
    motion=action
    if motion is None:
        track=hinge.animation_data.nla_tracks[0]
        motion=track.strips[0].action
    assert 'CHANGING_STATION_UNFOLD' in motion.name,motion.name
    def get_meshes(root):return [x for x in root.children_recursive if x.type=='MESH']
    moves=get_meshes(hinge); sta=get_meshes(fixed); walls=get_meshes(room)
    assert len(moves)>=18 and len(sta)>=20 and len(walls)>=27,(len(moves),len(sta),len(walls))
    start,end=tuple(motion.frame_range)
    assert abs((end-start)/sc.render.fps-2.2)<.001,(start,end,sc.render.fps)
    def evaluation(f):
        n=math.floor(f);sc.frame_set(n,subframe=f-n)
        dg=bpy.context.evaluated_depsgraph_get()
        return dg
    def arr(o,dg):
        eo=o.evaluated_get(dg); mesh=eo.to_mesh();T=eo.matrix_world
        v=[tuple(T@x.co) for x in mesh.vertices]
        F=[tuple(x.vertices) for x in mesh.polygons]
        eo.to_mesh_clear()
        return v,F
    def bounds(v):return [(min(x[d] for x in v),max(x[d] for x in v)) for d in range(3)]
    def BBinter(a,b):
        return all(max(a[d][0],b[d][0])<=min(a[d][1],b[d][1]) for d in range(3))
    def solid(o,dg):
        v,f=arr(o,dg)
        return o.name,bounds(v),BVHTree.FromPolygons(v,f,all_triangles=all(len(x)==3 for x in f),epsilon=0)
    dg=evaluation(start)
    F=[solid(o,dg) for o in sta+walls]
    mats=[[list(r) for r in o.evaluated_get(dg).matrix_world] for o in sta+walls]
    piv=hinge.evaluated_get(dg).matrix_world.translation
    for actual,want in zip(piv,(0,-.124,.851)):assert abs(actual-want)<.000001,(piv,want)
    movement=[]; count=0; startQ=None; endQ=None
    orient=hinge.rotation_mode
    for k in range(133):
        frac=k/132;dg=evaluation(start+(end-start)*frac)
        h=hinge.evaluated_get(dg).matrix_world
        np=h.translation
        assert (np-piv).length<.000001,(piv,np)
        axis=(h.to_3x3()@Vector((1,0,0))).normalized()
        assert (axis-Vector((1,0,0))).length<.00001,axis
        level=(h.to_3x3()@Vector((0,-1,0))).normalized()
        angle=math.degrees(math.atan2(level.z,-level.y))
        movement.append(angle)
        for i,o in enumerate(sta+walls):
            w=[[float(z) for z in r] for r in o.evaluated_get(dg).matrix_world]
            assert all(abs(x-y)<.000001 for a,b in zip(w,mats[i]) for x,y in zip(a,b)),o.name
        for s in moves:
            n,B,T=solid(s,dg)
            for name,bb,tree in F:
                if BBinter(B,bb):
                    count+=1
                    assert not T.overlap(tree),(k,angle,n,name)
    assert abs(movement[0]-90)<.001
    assert abs(movement[-1])<.001
    assert all(y-x<.001 for x,y in zip(movement,movement[1:]))
    assert all(abs(x)<.001 for x in movement[-17:]),movement[-17:]
    dg=evaluation(end)
    def exact(n):return next(x for x in (moves+sta+walls) if x.name==n)
    fits=[]
    for side in (-1,1):
        a=arr(exact('Moving open-limit contact lug '+str(side)),dg)[0]
        b=arr(exact('Stationary continuous bearing stop shoulder '+str(side)),dg)[0]
        A,B=bounds(a),bounds(b)
        gap=A[2][0]-B[2][1]
        assert .0002<gap<.0004,(A,B,gap)
        assert all(min(A[d][1],B[d][1])-max(A[d][0],B[d][0])>.010 for d in (0,1))
        fits.append(gap*1000)
    axle=exact('Stationary continuous captured steel axle')
    sleeve=exact('One moving central hinge sleeve')
    v,fa=arr(sleeve,dg)
    rmin=min(math.hypot(y-piv.y,z-piv.z) for x,y,z in v)
    v2,fb=arr(axle,dg)
    rmax=max(math.hypot(y-piv.y,z-piv.z) for x,y,z in v2)
    radialClear=(rmin*math.cos(math.pi/28)-rmax)
    assert .0008<radialClear<.0010,radialClear
    return dict(imported=imported,keys=133,pairBroadphase=count,movingObjects=len(moves),fixedObjects=len(sta)+len(walls),angles={str(k):movement[k] for k in (0,33,66,99,116,132)},openStopGapMm=fits,radialBoreClearanceLowerBoundMm=radialClear*1000,clipSeconds=(end-start)/sc.render.fps)
bpy.ops.wm.open_mainfile(filepath=p[0]); native=verify()
rt=bpy.context.scene.render.fps
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=rt
bpy.ops.import_scene.gltf(filepath=p[1]); imp=verify(True)
print('M33_GEOMETRY='+json.dumps([native,imp]))
