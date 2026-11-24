"""Verification of actual visible weave, through throat and display supports in Blender and GLB."""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='woven-bubu-fish-trap-display'
path=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).resolve().parent
out={}
for lane in ['native','GLB']:
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(path/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    def many(s):return sorted((o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(s)),key=lambda o:o.name)
    def one(s):
        a=many(s);assert len(a)==1,(lane,s,a);return a[0]
    def geo(o):
        e=o.evaluated_get(dg);m=e.to_mesh();v=[e.matrix_world@q.co for q in m.vertices];f=[tuple(q.vertices) for q in m.polygons];e.to_mesh_clear();return v,f
    def tree(o):return BVHTree.FromPolygons(*geo(o))
    def mix(owners):
        vv=[];ff=[]
        for o in owners:
            v,f=geo(o);j=len(vv);vv+=v;ff.extend(tuple(i+j for i in p) for p in f)
        return BVHTree.FromPolygons(vv,ff)
    body=[];allobj=[]
    def ray(t,p,d,length):return t.ray_cast(Vector(p),Vector(d),length)[0]
    def rad(t,x,a,r,dir=1,tol=.42):
        p=(x,r*math.sin(a),.410+r*math.cos(a));d=(0,dir*math.sin(a),dir*math.cos(a))
        h=ray(t,p,d,tol)
        if h:return math.hypot(h.y,h.z-.410)
        return None
    fins=0
    for tag,n,course,edge,stride in [('Outer',34,21,-.549,.057),('Inset',26,7,-.536,.039)]:
        strips=many(tag+' longitudinal strip')
        bands=many(tag+' closed transverse weft')
        assert len(strips)==n and len(bands)==course,(lane,tag,len(strips),len(bands))
        st=list(map(tree,strips)); bt=list(map(tree,bands)); gaps=[]
        for i,warp in enumerate(st):
            a=i*math.tau/n
            for j,weft in enumerate(bt):
                assert not warp.overlap(weft),(lane,tag,i,j,'intersection')
                x=edge+j*stride
                high,low=(warp,weft) if (i+j)%2==0 else (weft,warp)
                hi, lo=rad(high,x,a,0),rad(low,x,a,.34,-1)
                assert hi and lo and .0031<(hi-lo)<.0098,(lane,tag,i,j,hi,lo)
                gaps.append(hi-lo)
            fins+=1
        t=mix(strips+bands)
        empty=0
        for j in range(1,course-1,3):
            for i in range(0,n,3):
                a=(i+.5)*math.tau/n
                assert rad(t,edge+(j+.5)*stride,a,0,1,.34) is None,(lane,tag,i,j,'fake open weave')
                empty+=1
        body.append({'weft':course,'longitudinal':n,'actual_separated_crossings':len(gaps),'gap_mm':[min(gaps)*1000,max(gaps)*1000],
                     'real_open_cells_probed':empty})
        allobj.append(strips+bands)
    outer=mix(allobj[0]);inner=mix(allobj[1])
    assert not outer.overlap(inner),(lane,'inner clipped exterior')
    mouthA=tree(one('Original narrow rounded entrance face lip'))
    collar=tree(one('Inset attached wide entrance collar'))
    rim=tree(one('Inner throat physical open edge binder'))
    outerBand=tree(one('Actual dark rear mouth wrap'))
    assert mouthA.overlap(collar) and outerBand.overlap(mix(many('Outer longitudinal strip')))
    assert collar.overlap(mix(many('Inset longitudinal strip'))) and rim.overlap(mix(many('Inset longitudinal strip')))
    axisRays=0
    for rr in [0,.029,.051,.071]:
        for j in range(12):
            a=j*math.tau/12
            at=(-.72,rr*math.sin(a),.410+rr*math.cos(a))
            for t in [inner,mouthA,collar,rim]:
                assert ray(t,at,(1,0,0),.53) is None,(lane,'narrowing not through',rr,j)
            axisRays+=1
    for j in range(12):
        a=j*math.tau/12;rr=.080
        h=ray(rim,(-.72,rr*math.sin(a),.410+rr*math.cos(a)),(1,0,0),.53)
        assert h and -.263<h.x<-.228,(lane,'throat rim absent',j,h)
    seats=[]
    pads=sorted(many('Distinct concave exhibit cradle saddle'),key=lambda p:min(v.x for v in geo(p)[0]))
    posts=sorted(many('Short contemporary upright under saddle'),key=lambda p:p.location.x)
    assert len(pads)==len(posts)==2
    for cx,p,post in zip([-.321,.363],pads,posts):
        s=tree(p)
        assert s.overlap(tree(post)),(lane,'stand floats',p.name)
        distances=[]
        for i in range(13,22):
            a=i*math.tau/34
            shell,pad=rad(outer,cx,a,.34,-1),rad(s,cx,a,0)
            if shell and pad:distances.append(pad-shell)
        assert len(distances)>=7,(lane,cx,len(distances))
        assert min(distances)>-.0018 and min(abs(x) for x in distances)<.00055,(lane,cx,distances)
        seats.append(dict(minimum_signed_gap_mm=min(distances)*1000,closest_surface_mm=min(abs(x) for x in distances)*1000,
                          physical_contact_probes=len(distances)))
    out[lane]=dict(woven=body,clear_inward_funnel_rays=axisRays,actual_annular_edge_rays=12,
                   inner_and_outer_mouth_contacts=True,independent_cradles=seats)
print(json.dumps(out,indent=2))
