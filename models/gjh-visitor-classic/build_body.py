"""Closed base head, projected face art, removable ears and articulated hands."""
import math
import bpy
from mathutils import Vector

SKIN = '#ffcead'
TIP = '#ffc8a9'


def clip(poly, axis, limit, sign):
    result=[]
    for p,q in zip(poly, poly[1:]+poly[:1]):
        a=sign*(p[axis]-limit); b=sign*(q[axis]-limit)
        if a >= -1e-8:
            result.append(p)
        if (a>0) != (b>0) and abs(a-b)>1e-10:
            result.append(p+(q-p)*(a/(a-b)))
    return result


def decal(api, surface, name, slot, box, tile, mirror=False, lift=.00065):
    """Clip to the base topology to keep artwork flush when the head is turned."""
    x0,x1,z0,z1=box
    vs=[]; fs=[]; uvs=[]
    surface.data.calc_loop_triangles()
    for tri in surface.data.loop_triangles:
        if tri.normal.y > -.06:
            continue
        poly=[surface.data.vertices[i].co.copy() for i in tri.vertices]
        for axis,limit,sign in [(0,x0,1),(0,x1,-1),(2,z0,1),(2,z1,-1)]:
            poly=clip(poly,axis,limit,sign)
            if not poly:
                break
        clean=[]
        for p in poly:
            if not clean or (clean[-1]-p).length>1e-6:
                clean.append(p)
        if len(clean)>1 and (clean[0]-clean[-1]).length<1e-6:
            clean.pop()
        if len(clean)<3:
            continue
        offset=len(vs)
        for p in clean:
            u=(p.x-x0)/(x1-x0)
            uvs.append(((tile+(1-u if mirror else u))/6,(p.z-z0)/(z1-z0)))
            vs.append((p.x,p.y-lift,p.z))
        fs.append(tuple(range(offset,len(vs))))
    ob=api.mesh(name,slot,vs,fs,'#ffffff','Head',True)
    ob.data.materials.clear()
    ob.data.materials.append(api.material('Face ink'))
    uv=ob.data.uv_layers.new(name='Face atlas')
    for loop in ob.data.loops:
        uv.data[loop.index].uv=uvs[loop.vertex_index]
    # Match the head's normals across clipped faces to avoid ink changing shade at the patch edge.
    src=surface.data
    nearest=[]
    for v in ob.data.vertices:
        p=v.co.copy(); p.y+=lift
        hit,loc,n,index=surface.closest_point_on_mesh(p)
        if not hit:
            nearest.append((0,-1,0)); continue
        face=src.polygons[index]
        match=min((src.vertices[i] for i in face.vertices),key=lambda vi:(vi.co-p).length)
        nearest.append(tuple(match.normal.lerp(n,.35).normalized()))
    ob.data.normals_split_custom_set_from_vertices(nearest)
    return ob


def build_body(api):
    levels=[
        (.774,0,-.008,.020,.035),(.779,0,-.012,.069,.079),(.792,0,-.008,.122,.121),
        (.812,0,-.002,.163,.151),(.842,0,.001,.201,.180),
        (.899,0,.004,.227,.194),(.964,0,.004,.244,.204),
        (1.043,0,.006,.246,.205),(1.123,0,.009,.232,.192),
        (1.203,0,.009,.177,.147),
        (1.249,0,.006,.028,.027)]
    samples=(8,14,20,24,26,26,24,22,16,12,8)
    if len(samples)!=len(levels):
        raise ValueError('Each head profile ring needs its own resolution')
    verts=[]; rings=[]; faces=[]
    for (z,cx,cy,rx,ry),count in zip(levels,samples):
        ring=[]
        for j in range(count):
            a=math.tau*j/count
            ring.append(len(verts))
            verts.append((cx+rx*math.sin(a),cy-ry*math.cos(a),z))
        rings.append(ring)
    faces.append(tuple(reversed(rings[0])))
    for lo,hi in zip(rings,rings[1:]):
        i=j=0
        while i<len(lo) or j<len(hi):
            a=lo[i%len(lo)];b=hi[j%len(hi)]
            tlo=(i+1)*len(hi);thi=(j+1)*len(lo)
            if tlo==thi:
                faces.append((a,lo[(i+1)%len(lo)],hi[(j+1)%len(hi)],b));i+=1;j+=1
            elif tlo<thi:
                faces.append((a,lo[(i+1)%len(lo)],b));i+=1
            else:
                faces.append((a,hi[(j+1)%len(hi)],b));j+=1
    faces.append(tuple(rings[-1]))
    head=api.mesh('Head • cheek and jaw','Head',verts,faces,SKIN,'Head',True)
    bpy.context.view_layer.update()
    for sign,suffix in [(1,'L'),(-1,'R')]:
        def xbounds(center,half):
            cx=sign*center
            return cx-half,cx+half
        ax,bx=xbounds(.094,.0685)
        decal(api,head,'Eye • '+suffix,'Eye.'+suffix,(ax,bx,.893,1.013),0 if sign==1 else 1,lift=.0012)
        ax,bx=xbounds(.095,.053)
        decal(api,head,'Brow • '+suffix,'Brow.'+suffix,(ax,bx,.987,1.060),2,mirror=sign<0,lift=.0016)
        ax,bx=xbounds(.158,.046)
        decal(api,head,'Blush • '+suffix,'Cheek.'+suffix,(ax,bx,.865,.927),4,lift=.0005)
        # The silhouette ring runs in the image plane so ear lobes stay round in frontal views.
        center=Vector((sign*.229,-.005,.899))
        ear=api.oval('Ear • '+suffix,'Ear.'+suffix,(0,0,0),(.044,.053,.035),TIP,'Head',segments=14,steps=4)
        for vert in ear.data.vertices:
            x,y,z=vert.co
            vert.co=center+Vector((x+sign*.09*y,-z,y))
        ear.data.update()
        bpy.context.view_layer.update()
        ax,bx=xbounds(.243,.024)
        decal(api,ear,'Ear fold • '+suffix,'Ear.'+suffix,(ax,bx,.879,.930),5,mirror=sign<0)
    decal(api,head,'Mouth • happy','Mouth',(-.059,.059,.813,.887),3,lift=.0015)
    api.oval('Nose • button','Nose',(0,-.184,.901),(.014,.014,.011),'#ffd1b1','Head',7,3)
    api.rings('Torso and neck','Body',[(.366,0,.002,.091,.065),
        (.550,0,.002,.118,.084),(.674,0,0,.115,.077),(.711,0,0,.081,.062),
        (.728,0,0,.047,.041),(.793,0,0,.048,.042)],SKIN,
        lambda x,y,z: 'Chest' if z>.60 else 'Spine' if z>.41 else 'Hips',8,True)
    finger_points=[
        ('Thumb',(.210,-.052,.446),(.202,-.064,.424),.0131),
        ('Index',(.217,-.045,.428),(.214,-.051,.402),.0100),
        ('Middle',(.228,-.039,.425),(.226,-.047,.397),.0104),
        ('Ring',(.238,-.031,.427),(.237,-.039,.401),.0100),
        ('Pinky',(.246,-.021,.431),(.245,-.026,.408),.0090)]
    for s,side in [(1,'L'),(-1,'R')]:
        def pos(v):
            return (v[0]*s,v[1],v[2])
        def bone(v):
            return v+'.'+side
        shoulder,elbow,wrist=map(pos,[(.118,0,.709),(.182,-.006,.583),(.222,-.022,.478)])
        api.tapered('Upper arm • '+side,bone('Arm'),shoulder,elbow,.031,.029,SKIN,bone('UpperArm'),sides=5)
        api.tapered('Forearm • '+side,bone('Arm'),elbow,wrist,.029,.025,SKIN,bone('Forearm'),sides=5)
        api.oval('Wrist • '+side,bone('Wrist'),pos((.222,-.022,.477)),(.027,.026,.029),SKIN,bone('Hand'),6,3)
        api.oval('Palm • '+side,bone('Palm'),pos((.229,-.029,.448)),(.032,.029,.041),SKIN,bone('Hand'),8,4)
        for finger,start,end,radius in finger_points:
            a=Vector(pos(start)); b=Vector(pos(end)); mid=(a+b)/2
            obj=api.oval(finger+' • '+side,bone(finger),mid,(radius,radius*.98,(b-a).length*.62),TIP,bone(finger),5,3)
            rot=(a-b).to_track_quat('Z','Y')
            for v in obj.data.vertices:
                v.co=mid+rot@(v.co-mid)
        api.rings('Leg • '+side,bone('Leg'),[
            (.099,s*.099,0,.032,.032),(.208,s*.095,-.002,.043,.039),
            (.234,s*.095,-.002,.043,.041),(.338,s*.092,.001,.046,.044)],
            SKIN,lambda x,y,z: bone('Thigh') if z>=.23 else bone('Shin') if z<=.207 else {bone('Thigh'):.5,bone('Shin'):.5},8,True)
