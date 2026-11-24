"""Independent actual mesh evidence for a static display; not loom-building guidance."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ID='sarawak-iban-backstrap-loom-display'
arg=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=Path(arg[0]) if arg else Path(__file__).resolve().parent
results={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(p/(ID+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(p/'exports'/(ID+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    def many(prefix):
        return sorted([o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(prefix)],key=lambda o:o.name)
    def one(prefix):
        c=many(prefix);assert len(c)==1,(prefix,[n.name for n in c]);return c[0]
    def geom(o):
        t=o.evaluated_get(dg);m=t.to_mesh()
        vv=[t.matrix_world@v.co for v in m.vertices];ff=[tuple(f.vertices) for f in m.polygons]
        t.to_mesh_clear();return vv,ff
    def mesh(o):
        v,f=geom(o);return BVHTree.FromPolygons(v,f)
    def ray(b,where,d,lim=.027):
        return b.ray_cast(Vector(where),Vector(d),lim)[0]
    def down(b,x,y,z=.37):
        q=ray(b,(x,y,z),(0,0,-1),.085);assert q,(lane,x,y);return q.z
    def up(b,x,y,z=.322):
        q=ray(b,(x,y,z),(0,0,1),.055);assert q,(lane,x,y);return q.z
    warp=many('Continuous warp thread')
    weft=many('Alternating solid weft course')
    assert len(warp)==36 and len(weft)==21
    warpB=[mesh(o) for o in warp];weftB=[mesh(o) for o in weft]
    x=[-.221+(i+.5)*(.442/36) for i in range(36)]
    y=[-.321+j*.0105 for j in range(21)]
    gaps=[]
    for i,a in enumerate(warpB):
        for j,b in enumerate(weftB):
            assert not a.overlap(b),(lane,'cross-clipping',i,j)
            yy=y[j]
            top,low=(a,b) if (i+j)%2==0 else (b,a)
            gap=up(top,x[i],yy)-down(low,x[i],yy)
            assert .00160 < gap < .0028,(lane,'cross-gap',i,j,gap)
            gaps.append(gap)
    banks=[one('Wood breast beam'),one('Wood warp beam'),one('First slender'),one('Second slender')]
    rb=[mesh(o) for o in banks]
    # A separate cylindrical wood beam goes through each actual continuous
    # yarn wrap or passes between rows. Measured rays cannot pass through both
    # yarn and wood at their closest tangent trajectory.
    close=[]
    for i,a in enumerate(warpB):
        for k,b in enumerate(rb):
            assert not a.overlap(b),(lane,'warp-wood penetration',i,k)
        for j,py in [(0,-.368),(1,.368),(2,.169),(3,.220)]:
            upper=True if j<2 else (i+j)%2==0
            if upper:
                gap=up(a,x[i],py,.325 if j<2 else .349)-down(rb[j],x[i],py,.39)
            else:
                q=ray(rb[j],(x[i],py,.320),(0,0,1),.035); assert q
                zz=ray(a,(x[i],py,.343),(0,0,-1),.04); assert zz
                gap=q.z-zz.z
            assert -.00005 < gap < .0024,(lane,'seated over/under beam',i,j,gap)
            close.append(gap)
    hl=many('Closed cord loop');assert len(hl)==18
    heddle=mesh(one('Raised hardwood heddle rod'))
    heddleClear=[]
    for j,o in enumerate(hl):
        curve=mesh(o); i=j*2
        wt=warpB[i]
        # Verify the top arc rides over the wooden rod and the bottom arc
        # encloses the selected high warp instead of passing through it.
        axis=x[i]
        hi=ray(curve,(axis,.033,.416),(0,0,1),.014)
        wh=ray(heddle,(axis,.033,.434),(0,0,-1),.035)
        lo=ray(curve,(axis,.033,.369),(0,0,1),.013)
        wb=ray(wt,(axis,.033,.369),(0,0,1),.02)
        assert hi and wh and lo and wb,(lane,'missing loop closure',i)
        assert hi.z>wh.z and lo.z<wb.z,(lane,i,[v.z for v in (hi,wh,lo,wb)])
        assert not curve.overlap(wt) and not curve.overlap(heddle),(lane,'heddle interpenetration',i)
        heddleClear.append(hi.z-wh.z)
    strap=one('Wide curved open backstrap')
    strapBV=mesh(strap)
    rest=mesh(one('Independent lower padded display strap rest'))
    center=[]
    for j in [-.580,-.560,-.533]:
        a=ray(strapBV,(0,j,.150),(0,0,1),.030)
        b=ray(rest,(0,j,.185),(0,0,-1),.060)
        assert a and b,(lane,j)
        center.append(a.z-b.z)
    assert abs(min(center))<.00008,(lane,"belt must physically seat on display pad",center)
    cords=many('Continuous bound strap tie');assert len(cords)==2
    fasteners=[]
    for o in cords:
        xx=sum(v.x for v in geom(o)[0])/len(geom(o)[0])
        bv=mesh(o)
        assert not bv.overlap(rb[0]),(lane,'strap cord through wood',o.name)
        # The throat is around the real breast beam, and the cord follows the
        # tongue thick enough to share the resting belt edge as a fitted tie.
        axis=math.copysign(.261,xx)
        top=ray(bv,(axis,-.368,.355),(0,0,-1),.035)
        low=ray(bv,(axis,-.368,.261),(0,0,1),.035)
        assert top and low and top.z>.333 and low.z<.279,(lane,'real strap beam wrap',o.name)
        gap=min(strapBV.find_nearest(v)[3] for v in geom(o)[0])
        assert gap < .002,(lane,'separate floating strap tie',o.name,gap)
        fasteners.append({'strap_vertex_contact_distance_mm':gap*1000,'physical_beam_wrap_extents_m':[low.z,top.z]})
    results[lane]={'continuous_warp':len(warp),'individual_weft':len(weft),'alternating_intersections':len(gaps),
                   'loom_crossing_gap_mm':[min(gaps)*1000,max(gaps)*1000],
                   'seated_nonpenetrating_beam_clearance_mm':[min(close)*1000,max(close)*1000],
                   'wood_over_under_clearance_probes':len(close),'closed_heddles':len(hl),
                   'heddle_rim_clearance_mm':[min(heddleClear)*1000,max(heddleClear)*1000],
                   'belt_to_pad_signed_mm':[v*1000 for v in center],
                   'attached_ties':fasteners}
print(json.dumps(results,indent=2))
