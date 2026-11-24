"""Read-only native and Blender GLB reimport geometry checks for this static exhibit."""
import bpy,json,sys,math
from pathlib import Path
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree
slug='carpark-suspended-height-clearance-bar'
arg=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=Path(arg[0]) if arg else Path(__file__).resolve().parent
result={}
for lane in ('native','GLB'):
    if lane=='native':bpy.ops.wm.open_mainfile(filepath=str(p/(slug+'.blend')))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(p/'exports'/(slug+'.glb')))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    def one(prefix):
        found=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(prefix)]
        assert len(found)==1,(lane,prefix,[o.name for o in found]);return found[0]
    def geo(o):
        e=o.evaluated_get(dg);m=e.to_mesh()
        v=[e.matrix_world@q.co for q in m.vertices];f=[tuple(face.vertices) for face in m.polygons];e.to_mesh_clear()
        return v,f
    def bv(g):return BVHTree.FromPolygons(*g)
    def bounds(v,axis):return [min(q[axis] for q in v),max(q[axis] for q in v)]
    def qbound(g,axis):return bounds(g[0],axis)
    def tread(g):
        v,f=g;V=[tuple(round(a,5) for a in q) for q in v]; ee=Counter()
        for face in f:
            for a,b in zip(face,face[1:]+face[:1]):ee[tuple(sorted((V[a],V[b])))]+=1
        assert all(k==2 for k in ee.values()),(lane,'ring surface not closed',Counter(ee.values()))
    def ray(b,xyz,d,far):return b.ray_cast(Vector(xyz),Vector(d),far)[0]
    def along(b,axis,ran):
        a=ray(b,(*axis,ran[0]),(0,0,1),ran[1]-ran[0]);c=ray(b,(*axis,ran[1]),(0,0,-1),ran[1]-ran[0])
        assert a and c,(lane,'missing joined part',axis,ran,a,c)
        return [a.z,c.z]
    spans=[];chains=[];through=0
    for word,s in [('LEFT',-1),('RIGHT',1)]:
        x=s*1.135;y=-.467
        objs=[geo(one(f'{word}_{i}_CLOSED_')) for i in range(6)]
        trees=[bv(g) for g in objs]
        centers=[]
        for i,g in enumerate(objs):
            z=qbound(g,2); cz=(z[0]+z[1])/2;centers.append(cz)
            tread(g)
            distinct=qbound(g,i%2); thin=qbound(g,1-i%2)
            assert distinct[1]-distinct[0]>.100 and thin[1]-thin[0]<.026,(lane,i,distinct,thin)
            for off in [-.012,0,.012]:
                if i%2==0:
                    a=(x+off,y-.135,cz);d=(0,1,0)
                else:
                    a=(x-.135,y+off,cz);d=(1,0,0)
                assert ray(trees[i],a,d,.27) is None,(lane,'opening filled',word,i,off)
                through+=1
        mm=[];diskIntersection=[]
        for i in range(5):
            a,b=trees[i],trees[i+1]
            assert not a.overlap(b),(lane,'adjacent steel overlap',word,i)
            nearest=min(
                min(b.find_nearest(v)[3] for v in objs[i][0]),
                min(a.find_nearest(v)[3] for v in objs[i+1][0]))
            assert .000001<nearest<.0018,(lane,'too loose / intersecting link',word,i,nearest)
            mm.append(nearest*1000)
            # A closed neighbor enters through the first ring interior at
            # exactly one pole of its own centerline; the other pole lies
            # outside the first ring's enclosure (actual mesh extents).
            z0,z1=qbound(objs[i+1],2);cz=centers[i];inside=z0+.012;outside=z1-.012
            assert cz < inside < cz+.054 and outside > cz+.077,(lane,word,i,inside,cz,outside)
            # A ray along the current ring's opening actually strikes its
            # neighbor at the inside pole (not the open ring itself).
            if i%2==0: u=(x,y-.16,inside); v=(0,1,0)
            else: u=(x-.16,y,inside); v=(1,0,0)
            assert ray(a,u,v,.32) is None and ray(b,u,v,.32) is not None,(lane,'not interlinked',word,i)
            diskIntersection.append(i)
        anchor=[
           along(bv(geo(one('Real overhead concrete anchorage lintel'))),(x,y),(2.20,2.67)),
           along(bv(geo(one('Roof bolted anchor plate '+word))),(x,y),(2.26,2.35)),
           along(bv(geo(one('Anchor eye stem anchored to roof plate '+word))),(x,y),(2.24,2.36)),
           along(trees[5],(x,y),(2.273,2.35))]
        bar=[
           along(bv(geo(one('Closed suspended warning bar core'))),(x,y),(1.43,1.66)),
           along(bv(geo(one('Bar bolted eye seat plate '+word))),(x,y),(1.57,1.67)),
           along(bv(geo(one('Bar eye stem anchored to seat and warning core '+word))),(x,y),(1.57,1.67)),
           along(trees[0],(x,y),(1.607,1.655))]
        contacts=lambda parts:[min(a[1],b[1])-max(a[0],b[0]) for a,b in zip(parts,parts[1:])]
        ar,br=contacts(anchor),contacts(bar)
        assert all(.0032<z<.035 for z in ar+br),(lane,word,ar,br,anchor,bar)
        spans.append(centers)
        chains.append({'side':word,'links_including_eyes':len(objs),'proven_disk_interlocks':len(diskIntersection),
                        'no_overlap_adjacent_mesh_nearest_mm':[min(mm),max(mm)],
                        'roof_to_eye_overlaps_mm':[x*1000 for x in ar],
                        'beam_to_eye_overlaps_mm':[x*1000 for x in br]})
    assert max(abs(a-b) for a,b in zip(*spans))<.000012,(lane,spans)
    result[lane]={'chains':chains,'true_through_opening_rays':through}
print(json.dumps(result,indent=2))
