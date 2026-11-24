"""Read-only Blender native and GLB readback of the illustrative transit tray motion."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='transit-two-tier-bicycle-tray'
path=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).resolve().parent
out={}
for lane in ('native','GLB'):
    if lane=='native':
        bpy.ops.wm.open_mainfile(filepath=str(path/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps=30
        bpy.ops.import_scene.gltf(filepath=str(path/'exports'/(slug+'.glb')))
    scene=bpy.context.scene;scene.render.fps=30
    src=bpy.data.objects.get('BIKE_UPPER_CARRIAGE');ch=bpy.data.objects.get('BIKE_UPPER_TRAY_PIVOT')
    assert ch and src and ch.parent==src,(lane,'wrong hierarchy')
    def over(o,prefix): return o.name.startswith(prefix)
    def many(prefix):return sorted((o for o in scene.objects if o.type=='MESH' and over(o,prefix)),key=lambda o:o.name)
    def one(prefix):
        t=many(prefix);assert len(t)==1,(lane,prefix,[q.name for q in t]);return t[0]
    def local_data(o):
        e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
        vv=[q.co.copy() for q in m.vertices];ff=[tuple(q.vertices) for q in m.polygons];e.to_mesh_clear();return (vv,ff)
    def global_v(o):
        return [o.matrix_world@v for v in raw[o][0]]
    def leaf(o,s):
        cur=o
        while cur:
            if cur==s:return True
            cur=cur.parent
        return False
    allmesh=[o for o in scene.objects if o.type=='MESH' and leaf(o,bpy.data.objects['TRANSIT_TWO_TIER_BICYCLE_TRAY_EXHIBIT'])]
    raw={o:local_data(o) for o in allmesh}
    def tree(o):return BVHTree.FromPolygons(global_v(o),raw[o][1])
    def mix(os):
        vv=[];ff=[]
        for o in os:
            vs=global_v(o);n=len(vv);vv+=vs;ff.extend([tuple(n+k for k in f) for f in raw[o][1]])
        return BVHTree.FromPolygons(vv,ff)
    def range_(o,k):
        p=global_v(o);return [min(q[k] for q in p),max(q[k] for q in p)]
    static=[o for o in allmesh if not leaf(o,src)]
    mov=[o for o in allmesh if leaf(o,src)]
    assert len(static)>30 and len(mov)>20
    fixed=mix(static)
    stationaryMatrices={o:tuple(q for row in o.matrix_world for q in row) for o in static}
    tray=[o for o in mov if leaf(o,ch)]
    lower=[o for o in static if o.name.startswith(('Lower ','Stationary lower','Parked lower','Visible underside lower'))]
    lowerT=mix(lower)
    span=[];bboxclear=[];clear=[];travel=[];rot=[];tip=[];swept=[]
    axle=one('One fixed continuous hinge axle')
    moving_knuckles=many('Moving tray bored inner hinge')
    fixed_knuckles=many('Fixed carriage bored outer hinge')
    assert len(moving_knuckles)==3 and len(fixed_knuckles)==2
    times=[i/60 for i in range(145)]
    for i,t in enumerate(times):
        fr=math.floor(30*t+1e-9)
        scene.frame_set(fr,subframe=max(0,30*t-fr));bpy.context.view_layer.update()
        center=ch.matrix_world.translation
        pos=src.matrix_world.translation
        assert abs(center.x-pos.x)<1e-6 and abs(center.y-pos.y)<1e-6 and abs(center.z-pos.z)<1e-6
        axis=ch.matrix_world.to_3x3()@Vector((0,-1,0))
        theta=math.degrees(math.atan2(-axis.z,-axis.y))
        assert abs(pos.x)<1e-5 and abs(pos.z-1.427)<1e-5
        slide=.240-pos.y
        if t<=1.2+1e-9:assert abs(theta)<.0001,(lane,t,theta)
        if t>=1.2-1e-9:assert abs(slide-.64)<.00002,(lane,t,slide)
        if t>=2.1-1e-9:assert abs(theta-38)<.0002,(lane,t,theta)
        if travel:assert slide>=travel[-1]-1e-6 and theta>=rot[-1]-1e-5,(lane,t,slide,theta)
        travel.append(slide);rot.append(theta)
        assert all(tuple(q for row in o.matrix_world for q in row)==m for o,m in stationaryMatrices.items()),(lane,'static transformed',t)
        for side in ['LEFT','RIGHT']:
            runner=one('Sensing-free long captured slider runner '+side)
            top=one('FIXED_GUIDE_'+side+'_CAPTURE_TOP')
            bottom=one('FIXED_GUIDE_'+side+'_CAPTURE_BOTTOM')
            web=one('FIXED_GUIDE_'+side+'_OUTER_WEB')
            r0,r1=range_(runner,1);g0,g1=range_(top,1)
            overlap=min(r1,g1)-max(r0,g0)
            span.append(overlap);assert overlap>.68,(lane,side,t,overlap)
            a=range_(top,2)[0]-range_(runner,2)[1]
            b=range_(runner,2)[0]-range_(bottom,2)[1]
            c=(range_(web,0)[0]-range_(runner,0)[1]) if side=='RIGHT' else (range_(runner,0)[0]-range_(web,0)[1])
            assert min(a,b,c)>.009,(lane,side,t,a,b,c)
            clear.extend([a,b,c])
        tt=mix(tray); whole=mix(mov)
        overlap=whole.overlap(fixed)
        assert not overlap,(lane,'moving-to-fixed intersection',t,len(overlap))
        assert not tt.overlap(lowerT),(lane,'tray/lower interpenetration',t)
        height=min(v.z for o in tray for v in global_v(o))
        maxLower=max(v.z for o in lower for v in global_v(o))
        gap=height-maxLower;bboxclear.append(gap)
        assert gap>.25,(lane,t,height,maxLower,gap)
        handle=one('Clear painted upper motion handle')
        tip.append(min(v.z for v in global_v(handle)))
        if i in (0,72,99,126,144):
            axv=tree(axle)
            for o in moving_knuckles+fixed_knuckles:
                bo=tree(o)
                assert not bo.overlap(axv),(lane,t,o.name,'hinge bore obstructed')
                x0,x1=range_(o,0);xx=(x0+x1)/2
                maxRad=0
                for k in range(12):
                    a=k*2*math.pi/12
                    start=Vector((xx,center.y,center.z));v=Vector((0,math.cos(a),math.sin(a)))
                    ra=bo.ray_cast(start,v,.026)[0];rb=axv.ray_cast(start,v,.020)[0]
                    assert ra and rb and .0019<(ra-rb).length<.0028,(lane,t,o.name,ra,rb)
                    maxRad=max(maxRad,(ra-rb).length)
                swept.append(maxRad)
    assert abs(travel[0])<.00001 and abs(rot[0])<.00001
    assert abs(travel[36]-.32)<.00001 and abs(rot[99]-19)<.0002
    out[lane]=dict(samples=len(times),phase_checks=[[t,travel[i],rot[i],tip[i]] for i,t in enumerate(times) if i in (0,36,72,99,126,144)],
                   min_actual_bilateral_guide_engagement_m=min(span),min_rail_surface_clearance_mm=min(clear)*1000,
                   min_upper_to_lower_bound_m=min(bboxclear),exact_bvh_intersection_count=0,actual_axial_bore_rays=len(swept)*12,
                   max_hinge_surface_clearance_mm=max(swept)*1000)
print(json.dumps(out,indent=2))
