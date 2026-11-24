"""Read-only geometric check of this fictional contact exhibit, in native and reimport."""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='straddle-beam-monorail-bogie-cutaway'
path=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).resolve().parent
out={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(path/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    leaves={}
    for root in ('SINGLE_STRADDLE_BEAM','SCHEMATIC_SADDLE_BOGIE','EXHIBIT_BASE'):
        leaves[root]=[o for o in bpy.data.objects[root].children_recursive if o.type=='MESH']
    def pick(prefix,l):
        return [o for o in l if o.name.startswith(prefix)]
    def one(prefix,l):
        a=pick(prefix,l);assert len(a)==1,(lane,prefix,[(o.name,o.type) for o in a]);return a[0]
    vdata={}
    for o in sum(leaves.values(),[]):
        e=o.evaluated_get(dg);m=e.to_mesh()
        vdata[o.name]=([e.matrix_world@q.co for q in m.vertices],[tuple(q.vertices) for q in m.polygons]);e.to_mesh_clear()
    def geom(o):return vdata[o.name]
    def bvh(o):return BVHTree.FromPolygons(*geom(o))
    def hit(t,p,d,span):
        q,n,_,_=t.ray_cast(Vector(p),Vector(d),span)
        assert q is not None,(lane,p,d,span)
        return q,n
    def b(o,k):
        v,_=geom(o);return (min(x[k] for x in v),max(x[k] for x in v))
    t=leaves['SINGLE_STRADDLE_BEAM']; v=leaves['SCHEMATIC_SADDLE_BOGIE']
    top=one('Flat TOP load running surface',t);tt=bvh(top)
    tires=[]; details={}; joins={}; normals=[]
    for tag,surface,ax,count in [
        ('TOP_LOAD_TYRE','Flat TOP load running surface',2,2),
        ('SIDE_GUIDE_TYRE','Flat SIDE guide running surface',0,4),
        ('LOWER_STABILIZER_TYRE','Flat SIDE stabilizer running surface',0,4)]:
        wheels=pick(tag,v);assert len(wheels)==count,(lane,tag,[q.name for q in wheels]);tires+=wheels
        values=[]
        for w in wheels:
            c=[(b(w,i)[0]+b(w,i)[1])/2 for i in range(3)];ss=1 if ax==2 or c[0]>0 else -1
            face=top if ax==2 else one(surface+' '+str(ss),t)
            tree=bvh(face); wheel=bvh(w); outdir=[0,0,0];outdir[ax]=ss
            face_at=b(face,ax)[1 if ss>0 else 0]
            tread_at=b(w,ax)[0 if ss>0 else 1]
            assert abs(tread_at-face_at)<2e-6,(lane,tag,w.name,face_at,tread_at)
            # Axial samples intentionally within the unbroken central tread of each tyre.
            sample_ax=0 if ax==2 else 2
            for shoulder in ((-.007,0,.007) if ax==2 else (-.015,.013,.020)):
                a=c.copy();a[ax]=face_at+ss*.009;a[sample_ax]+=shoulder
                q,n=hit(tree,a,[-j for j in outdir],.011)
                assert abs(q[ax]-face_at)<2e-6 and n[ax]*ss>.99,(lane,tag,q,n)
                a[ax]=face_at-ss*.008
                q2,n2=hit(wheel,a,outdir,.012)
                assert abs(q2[ax]-q[ax])<2e-6 and n2[ax]*ss<-.97,(lane,tag,q,q2,n2)
                values.append(abs(q2[ax]-q[ax])*1000)
            normals.append((tag,ss,ax))
            # Tyre touching only its nominated beam face: no interior vertices
            # past the surface; other axis must clear it.
            if ax==0:
                assert b(w,2)[1]<.815 and b(w,2)[0]>.235,(lane,w.name,b(w,2))
            else:
                assert b(w,0)[0]>-.35 and b(w,0)[1]<.35
        details[tag]={'count':len(wheels),'max_abs_tangent_gap_mm':max(values),'rays':len(values)}
    assert len(tires)==10
    for prefix in ('SIDE_GUIDE','LOWER_STABILIZER'):
        tabs=pick(prefix+' hub tab seat',v);pins=pick(prefix+' exposed seated kingpin',v)
        legs=pick('Continuous side cheek leg',v);rings=pick(prefix+' tinted hub',v);back=pick(prefix+' lower back hub',v)
        assert len(tabs)==len(pins)==len(legs)==len(rings)==len(back)==4
        lateral=pick(prefix+'_TYRE',v)
        margins=[]
        centro=lambda o,k:sum(b(o,k))/2
        for pin in pins:
            def mate(os):
                a=[o for o in os if abs(centro(o,1)-centro(pin,1))<.002 and centro(o,0)*centro(pin,0)>0]
                assert len(a)==1,(lane,pin.name,[o.name for o in a])
                return a[0]
            tab,leg,rim,rear,tyre=map(mate,(tabs,legs,rings,back,lateral))
            # Exact part groups all share same longitudinal station; structural
            # parts remain physically joined while tread is clear of its tab.
            sb=[b(tab,i) for i in range(3)]
            def bbshare(o,p):return min(min(b(o,k)[1],b(p,k)[1])-max(b(o,k)[0],b(p,k)[0]) for k in range(3))
            for o,p in ((tab,leg),(tab,pin),(pin,rim),(pin,rear),(rim,tyre),(rear,tyre)):
                assert bbshare(o,p)>.001,(lane,o.name,p.name,bbshare(o,p))
            assert b(tab,2)[0]-b(tyre,2)[1]>.02,(lane,tab.name)
            # A radial cross-section of either coloured rim meets the actual annulus.
            for part in (rim,rear):
                assert bvh(part).overlap(bvh(tyre)),(lane,'unseated side rim',part.name)
            margins.append((b(tab,2)[0]-b(tyre,2)[1])*1000)
        joins[prefix]={'four_continuous_pin_tab_cheek_mounts':True,'min_clearance_mm':min(margins)}
    braces=pick('Saddle cross brace',v); headers=pick('Continuous outer saddle header',v)
    assert len(braces)==len(headers)==2
    assert len(pick('Continuous load spindle toward frame',v))==len(pick('Load spindle visible pendant seat',v))==4
    overlaps=[]; clearances=[]
    for bridge in braces:
        clear=min(b(bridge,2)[0]-b(w,2)[1] for w in pick('TOP_LOAD_TYRE',v));assert clear>.03
        clearances.append(clear*1000)
        for head in headers:
            ds=[min(b(bridge,k)[1],b(head,k)[1])-max(b(bridge,k)[0],b(head,k)[0]) for k in range(3)]
            assert min(ds)>.012,(lane,bridge.name,head.name,ds)
            overlaps.append(min(ds)*1000)
    for rod in pick('Continuous load spindle toward frame',v):
        s=-1 if b(rod,0)[0]<0 else 1
        cx=(b(rod,1)[0]+b(rod,1)[1])*.5
        z=1.085
        for prefix,x in [('Load inner hub',s*.151),('Load bearing housing',s*.59),('Load spindle visible pendant seat',s*.59)]:
            a=[o for o in pick(prefix,v) if all(b(o,k)[0]-1e-6<=q<=b(o,k)[1]+1e-6 for k,q in enumerate((x,cx,z)))]
            assert len(a)==1 and b(rod,0)[0]<=x<=b(rod,0)[1],(lane,rod.name,prefix,a)
    # Elevated hardware sits on the exhibit's central beam only through tyres.
    for ob in v:
        if ob in tires:continue
        bb=[b(ob,k) for k in range(3)]
        assert bb[2][0]>.850001 or bb[0][0]>.350001 or bb[0][1]<-.350001,(lane,'unintended beam intrusion',ob.name,bb)
    out[lane]={'touches':details,'normals':normals,'minimum_cross_brace_to_top_tyre_clearance_mm':min(clearances),
        'minimum_terrace_to_side_header_join_mm':min(overlaps),'independent_lower_arms':joins,
        'static_exhibit':not any(o.animation_data for o in bpy.data.objects),'non_tyre_beam_intrusions':0}
print('M49_PHYSICAL='+json.dumps(out,separators=(',',':')))
