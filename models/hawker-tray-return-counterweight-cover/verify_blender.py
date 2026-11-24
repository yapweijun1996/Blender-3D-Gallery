"""Observe the saved native motion and reimport the shipped GLB without changing either."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
p=Path(__file__).resolve().parent
slug='hawker-tray-return-counterweight-cover'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
asset=Path(args[0]).resolve() if args else p
source=asset/(slug+'.blend'); glb=asset/'exports'/(slug+'.glb')
results={}
for variant in ['native','glb']:
    if variant=='native':bpy.ops.wm.open_mainfile(filepath=str(source))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(glb))
    sc=bpy.context.scene; sc.render.fps=30;sc.render.fps_base=1
    def named(prefix,typ=None):
        return [m for m in sc.objects if m.name.startswith(prefix) and (not typ or m.type==typ)]
    def exact(name):
        o=sc.objects.get(name)
        assert o is not None,name
        return o
    def one(prefix):
        found=named(prefix,'MESH');assert len(found)==1,(prefix,[m.name for m in found]);return found[0]
    def verts(o):
        dg=bpy.context.evaluated_depsgraph_get();ob=o.evaluated_get(dg);m=ob.to_mesh()
        pts=[ob.matrix_world@v.co for v in m.vertices]
        ob.to_mesh_clear();return pts
    def extent(o):
        v=verts(o)
        return [(min(p[k] for p in v),max(p[k] for p in v)) for k in (0,1,2)]
    def wpos(o):return o.matrix_world.translation
    cv=exact('TRAY_RETURN_COVER')
    cw=exact('TRAY_RETURN_COUNTERWEIGHT')
    pa=exact('TRAY_RETURN_TOP_PULLEY')
    cs=[exact('TRAY_RETURN_COVER_CABLE'),exact('TRAY_RETURN_WEIGHT_CABLE')]
    tray=exact('FIXED_ILLUSTRATIVE_SAMPLE_TRAY')
    arc=one('FIXED_CONTIGUOUS_TANGENT_HALF_TURN')
    cables=[one('Parallel straight cable to cover'),one('Parallel straight cable to counterweight')]
    ferrules=[one('Front cable ferrule'),one('Rear cable ferrule')]
    curve_center=Vector((.623,-.214,1.704))
    sc.frame_set(0);bpy.context.view_layer.update()
    arc_pts=verts(arc)
    front=[x for x in arc_pts if (x-Vector((.623,-.269,1.704))).length<.005]
    aft=[x for x in arc_pts if (x-Vector((.623,-.159,1.704))).length<.005]
    assert len(front)>=10 and len(aft)>=10
    # Centerline of the actual meshed groove/line along 49 arc neighborhoods.
    arc_samples=0
    for k in range(49):
        ang=math.pi-k*math.pi/48
        centre=curve_center+Vector((0,.055*math.cos(ang),.055*math.sin(ang)))
        assert min((q-centre).length for q in arc_pts)<.004501
        arc_samples+=1
    # Endpoint world planes from cable geometry vs its actual ferrules, not labels.
    anchors=[wpos(x).copy() for x in cs]
    static=[tray,arc,pa.parent]
    fixed=[n.matrix_world.copy() for n in static]
    maxerr=dict(cable_length=0.,moving_anchors=0.,upper_anchors=0.,stationary=0.,opposite_travel=0.)
    lengths=[];poses=[];last=-1.
    for f2 in range(133):
        sc.frame_set(f2//2,subframe=(f2%2)/2);bpy.context.view_layer.update()
        up=wpos(cv).z-.941;dn=1.407-wpos(cw).z
        assert up>=last-2e-6,(variant,f2,up,last);last=up
        maxerr['opposite_travel']=max(maxerr['opposite_travel'],abs(up-dn))
        z=[extent(o)[2] for o in cables]
        l=sum(hi-lo for lo,hi in z);lengths.append(l)
        e=[extent(o) for o in ferrules]
        for i in range(2):
            maxerr['moving_anchors']=max(maxerr['moving_anchors'],abs(z[i][0]-e[i][2][1]))
            maxerr['upper_anchors']=max(maxerr['upper_anchors'],abs(z[i][1]-anchors[i].z),(wpos(cs[i])-anchors[i]).length)
            chk=extent(cables[i]);pt=wpos(cs[i])
            assert abs((chk[0][0]+chk[0][1])/2-pt.x)<2e-6
            assert abs((chk[1][0]+chk[1][1])/2-pt.y)<2e-6
        for o,m in zip(static,fixed):
            maxerr['stationary']=max(maxerr['stationary'],max(abs(o.matrix_world[i][j]-m[i][j]) for i in range(4) for j in range(4)))
        if f2 in (0,60,112,132):poses.append(dict(t=f2/60,coverZ=wpos(cv).z,weightZ=wpos(cw).z,front=z[0][1]-z[0][0],rear=z[1][1]-z[1][0]))
    maxerr['cable_length']=max(lengths)-min(lengths)
    assert max(maxerr.values())<2e-6,(variant,maxerr)
    assert abs(poses[0]['coverZ']-.941)<2e-6 and abs(poses[-1]['coverZ']-1.276)<2e-6
    assert abs(poses[0]['weightZ']-1.407)<2e-6 and abs(poses[-1]['weightZ']-1.072)<2e-6
    assert all(abs(poses[-1][k]-poses[-2][k])<2e-6 for k in ('coverZ','weightZ','front','rear'))
    results[variant]=dict(arc_mesh_neighborhoods=arc_samples,interpolated_sample_count=133,maximum_error_m=maxerr,
                          nominal_visible_straight_total_m=lengths[0],poses=poses)
print(json.dumps(results,indent=2))
