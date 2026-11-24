"""Checks the explicitly nonoperational display, not a real tool or process."""
import sys,json,bpy,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='five-foot-way-ice-ball-shaver-exhibit'
path=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else Path(__file__).resolve().parent
stats={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(path/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(path/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
    def pick(n): return [o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(n)]
    def one(n):
        a=pick(n);assert len(a)==1,(lane,n,[o.name for o in a]);return a[0]
    def m(o):
        e=o.evaluated_get(dg); me=e.to_mesh()
        out=([e.matrix_world@v.co for v in me.vertices],[tuple(f.vertices) for f in me.polygons]);e.to_mesh_clear();return out
    def bv(o):return BVHTree.FromPolygons(*m(o))
    def mix(items):
        v=[];f=[]
        for o in items:
            a,b=m(o);k=len(v);v+=a;f.extend(tuple(k+x for x in face) for face in b)
        return BVHTree.FromPolygons(v,f)
    def zrange(o):
        v,_=m(o);return min(q.z for q in v),max(q.z for q in v)
    def ray(tree,x,y,z=.27,dist=.24):
        return tree.ray_cast(Vector((x,y,z)),Vector((0,0,-1)),dist)[0]
    top=one('Continuous bench deck');tray=one('Closed thin enamel catch bowl'); floor=one('Modern dark exhibit plinth')
    ice=one('Frosty sculpted demonstration ice block')
    verts,faces=m(top);p=[tuple(round(x,6) for x in v) for v in verts]
    e=collections.Counter(tuple(sorted((p[i],p[f[(j+1)%len(f)]]))) for f in faces for j,i in enumerate(f) if p[i]!=p[f[(j+1)%len(f)]])
    assert len(e)>100 and set(e.values())=={2},(lane,collections.Counter(e.values()))
    tt=bv(top); cc=bv(tray)
    whole=mix([o for n in ('ORIGINAL_WOODEN_SHAVER_EXHIBIT','EMPTY_BOWL_AND_SEPARATE_STAGED_ICE')
               for o in bpy.data.objects[n].children_recursive if o.type=='MESH'])
    trueSlotChecks=0
    for x in (-.048,-.024,0,.024,.048):
        for dy in (-.015,-.006,0,.010,.015):
            y=-.103+dy
            assert ray(tt,x,y,dist=.12) is None,(lane,x,y)
            h=ray(whole,x,y)
            expected=ray(cc,x,y)
            assert h and expected and abs(h.z-expected.z)<2e-6 and .048999<h.z<.051,(lane,x,y,h)
            trueSlotChecks+=1
    for x,y in ((-.129,-.103),(.124,-.103),(.014,-.168),(-.023,-.040)):
        a=ray(tt,x,y);assert a and abs(a.z-.2165)<2e-6
    assert abs(zrange(tray)[0]-zrange(floor)[1])<2e-6,(lane,zrange(tray),zrange(floor))
    assert abs(zrange(ice)[0]-zrange(top)[1])<2e-6,(lane,zrange(ice),zrange(top))
    assert zrange(top)[0]-zrange(tray)[1]>.07
    legs=pick('Seated tapered square timber leg')
    assert len(legs)==4
    for leg in legs:
        low,high=zrange(leg)
        assert low<zrange(floor)[1]+.0001 and high>zrange(top)[0]+.007
    assert not any('blade' in o.name.lower() or o.animation_data for o in bpy.data.objects)
    stats[lane]={'openSlotToEmptyBowlRays':trueSlotChecks,'closedContinuousDeckEdges':len(e),'bowlAndInsetIceAreSeated':True,'fourDeckSupports':len(legs),'operativeParts':0}
print('M52_PHYSICAL='+json.dumps(stats,separators=(',',':')))
