"""Original perforated rangoli sieve and separate powder study; static heritage exhibit."""
import argparse, math, random, sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='deepavali-rangoli-pattern-sieve'
out=a.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 exhibition platform and independent tilted support')
sieve=collection('02 single true perforated plate and surrounding rim')
study=collection('03 separate same-orientation powder swatch')
studio=collection('04 rendering only; never exported')
def material(name, hx, r, m=0):
    def linear(c):
        s = int(c, 16)/255
        return s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
    col = tuple(linear(hx[i:i+2]) for i in (0,2,4))+(1,)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = col
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = col
    bsdf.inputs['Roughness'].default_value = r
    bsdf.inputs['Metallic'].default_value = m
    return mat

def assign(o,n,c,p,mat=None):
    o.name=n
    if c not in list(o.users_collection):
        c.objects.link(o)
    for old in list(o.users_collection):
        if old != c:
            old.objects.unlink(o)
    o.parent=p
    if mat:
        o.data.materials.append(mat)
    return o

def empty(n,c,p=None,loc=(0,0,0)):
    o=bpy.data.objects.new(n,None)
    c.objects.link(o)
    o.parent=p
    o.location=loc
    o.empty_display_size=.036
    o.rotation_mode='QUATERNION'
    return o

def box(n,c,p,loc,d,mat,b=.003,seg=1):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object
    o.scale=d
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    assign(o,n,c,p,mat)
    o.location=loc
    if b:
        bv=o.modifiers.new('Rounded physical edges','BEVEL')
        bv.width=b
        bv.segments=seg
        wn=o.modifiers.new('Broad flat faces','WEIGHTED_NORMAL')
        wn.keep_sharp=True
    return o

def rod(n,c,p,a,b,r,mat,sides=12):
    a,b=Vector(a),Vector(b)
    d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=r,depth=d.length)
    o=assign(bpy.context.object,n,c,p,mat)
    o.location=(a+b)/2
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    for face in o.data.polygons:
        face.use_smooth=len(face.vertices)==4
    return o

def mesh(n,c,p,v,f,mat):
    data=bpy.data.meshes.new(n)
    data.from_pydata(v,[],f)
    data.update()
    o=bpy.data.objects.new(n,data)
    return assign(o,n,c,p,mat)

def sweep(n,c,p,coords,r,mat,sides=7,closed=False):
    points=[Vector(k) for k in coords]
    v=[]; f=[]; L=len(points)
    for i,q in enumerate(points):
        t=(points[(i+1)%L] if i<L-1 or closed else q)-(points[i-1] if i or closed else q)
        t.normalize()
        u=t.cross(Vector((0,1,0))).normalized()
        if not u.length:
            u=t.cross(Vector((1,0,0))).normalized()
        w=t.cross(u)
        for k in range(sides):
            theta=k*math.tau/sides
            v.append(q+r*(u*math.cos(theta)+w*math.sin(theta)))
    for i in range(L if closed else L-1):
        j=(i+1)%L
        for k in range(sides):
            l=(k+1)%sides
            f.append((i*sides+k,i*sides+l,j*sides+l,j*sides+k))
    if not closed:
        f.extend([tuple(reversed(range(sides))),tuple(range((L-1)*sides,L*sides))])
    o=mesh(n,c,p,v,f,mat)
    for face in o.data.polygons:
        face.use_smooth=len(face.vertices)==4
    return o

def etch(n,c,p,o,text,size,mat):
    data=bpy.data.curves.new(n,'FONT'); data.body=text; data.align_x='CENTER';data.size=size
    ob=bpy.data.objects.new(n,data);assign(ob,n,c,p,mat);ob.location=o
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH')
    return ob


wood=material('Burnished dark walnut display wood','795047',.46)
woodhi=material('Clean striped wood edge','A87055',.47)
garnet=material('Deep plum footboard','4B2C48',.48)
violet=material('Refined glazed aubergine trim','5B3E66',.32,.13)
violet_lo=material('Dark indigo rim behind brass','342F52',.40,.26)
bronze=material('Warm satin brass on perforated faces','D79E51',.34,.57)
boremat=material('Bare cut surfaces within actual holes','C98842',.42,.51)
bronzelite=material('Brushed narrow rim reflection','F1C67B',.30,.61)
bronzedark=material('Subdued warm brass at rim ends','9B6738',.42,.58)
bronzebowl=material('Grained raw brass small sample vessel','AD753D',.38,.58)
slate=material('Fired charcoal powder tile','344B54',.61)
tiletrim=material('Soft steel blue ceramic glazed bevel','49696A',.45,.13)
ochre=material('Coarse marigold study powder','FABB43',.74)
purple=material('Coarse blue-purple study powder','A78ADD',.71)
coral=material('Coarse watermelon study powder','EF7061',.73)
ivory=material('Coarse ivory study powder','FFF1CE',.79)
warmtext=material('Soft warm ivory label letters','FCDEAA',.64)
ground=material('Neutral warm mauve studio background','9D8687',.78)
B=empty('PRESENTATION_BASE',base)
H=empty('PERFORATED_SIEVE_HOLDER',sieve,loc=(-.124,.038,.142))
H.rotation_euler= (0,0,0)
H.rotation_mode='XYZ'
H.rotation_euler.x=math.radians(65)
W=empty('MATCHED_POWDER_SWATCH',study,loc=(.137,-.015,.040))

box('Thin exhibition board low wood body',base,B,(0,.003,.016),(.506,.284,.032),wood,.016,4)
box('Deep plum base underside chamfer',base,B,(0,.004,.0055),(.473,.254,.012),garnet,.007,3)
box('Fine oak front groove',base,B,(0,-.135,.0214),(.460,.006,.004),woodhi,.0019,2)
for side in (-1,1):
    box('Secured short dark foot '+str(side),base,B,(side*.174,.029,.003),(.095,.160,.006),garnet,.004,2)
    box('Front matt floating sign plaque '+str(side),base,B,(side*.129,-.141,.018),(.176,.005,.018),garnet,.006,3)
etch('Plain display label left',base,B,(-.129,-.1442,.016),'PERFORATED SIEVE',.0097,warmtext)
etch('Plain display label right',base,B,(.129,-.1442,.016),'POWDER STUDY',.0097,warmtext)
bpy.context.view_layer.update()
def trans(q):return tuple(H.matrix_world@Vector(q))
# The base cradle and short struts engage the outside of the plate only,
# leaving a bright, genuinely unobstructed inspection path behind the pattern.
for s in (-1,1):
    outer=(s*.064,-.079,-.003)
    p=trans(outer)
    b=(p[0],p[1]+.043,.031)
    rod('Set-in forked support post '+str(s),base,B,b,p,.011,bronzedark,14)
    box('Wood-mounted strut landing '+str(s),base,B,(b[0],b[1],.034),(.041,.043,.013),violet_lo,.006,3)
    rod('External soft cradle tab mount '+str(s),sieve,H,(s*.064,-.077,-.013),(s*.064,-.077,.015),.010,violet_lo,18)
    rod('Visible soft fixing point '+str(s),sieve,H,(s*.064,-.077,.013),(s*.064,-.077,.020),.006,violet,18)
box('Small open presentation rail behind lifted tool',base,B,(-.126,.090,.035),(.173,.032,.014),violet_lo,.006,4)

def ang(n):return n*math.tau
def f_rot(p,t):
    x,y=p
    return (x*math.cos(t)-y*math.sin(t),x*math.sin(t)+y*math.cos(t))
def ellipse(x,y,rx,ry,phi=0,n=14):
    return [(x+u,y+v) for i in range(n) for u,v in [f_rot((rx*math.cos(ang(i/n)),ry*math.sin(ang(i/n))),phi)]]
def path_arc(t0,t1,r,w,n=10):
    a0,a1=math.radians(t0),math.radians(t1)
    ret=[]
    # Both ends rounded with four-segment capsule noses, and all polygons
    # independent. The band itself is an arc with a shallow width variation.
    for j in range(n):
        t=j/(n-1);theta=a0+(a1-a0)*t
        k=r+w*(.80+.20*math.sin(t*math.pi))
        ret.append((k*math.cos(theta),k*math.sin(theta)))
    for j in range(1,8):
        b=math.pi*j/8
        p=(r+w*.80*math.cos(b),w*.80*math.sin(b))
        ret.append(f_rot(p,a1))
    for j in range(n-1,-1,-1):
        t=j/(n-1);theta=a0+(a1-a0)*t
        k=r-w*(.80+.20*math.sin(t*math.pi))
        ret.append((k*math.cos(theta),k*math.sin(theta)))
    for j in range(1,8):
        b=math.pi*(1+j/8)
        p=(r+w*.80*math.cos(b),w*.80*math.sin(b))
        ret.append(f_rot(p,a0))
    return ret
def lozenge(x,y,r,theta):
    return [(x+u,y+v) for q in range(8) for u,v in [f_rot((r*(1.0 if q%2==0 else .75)*math.cos(q*math.pi/4),r*.86*(1.0 if q%2==0 else .75)*math.sin(q*math.pi/4)),theta)]]
# Entire pattern is invented: offset sweep segments, narrow capsules and dots,
# not a copied floor design, idol, script, lotus or prescribed religious motif.
Holes=[]
for k in range(4):
    t=k*math.pi/2
    def add(name,loop,center,color):
        Holes.append((name+'-'+str(k+1),[f_rot(p,t) for p in loop],f_rot(center,t),color))
    add('outer-wave',path_arc(8,56,.079,.0056),f_rot((.079,0),math.radians(32)),ochre)
    add('inner-wave',path_arc(26,72,.056,.0053),f_rot((.056,0),math.radians(48)),coral)
    add('short-capsule',ellipse(.034,.016,.012,.006,-.31),(.034,.016),purple)
    add('cut-lozenge',lozenge(.016,.012,.0050,.35),(.016,.012),ivory)
    add('rim-square',lozenge(.027,.085,.0047,-.12),(.027,.085),ivory)
    add('rim-dot',ellipse(.017,.081,.0052,.0046,.12,12),(.017,.081),purple)
    add('shoulder-dot',ellipse(.086,-.004,.0057,.0044,-.24,12),(.086,-.004),coral)
Holes.append(('center',ellipse(0,0,.0056,.0056,0,16),(0,0),ochre))

def point_in(q,loop):
    x,y=q;r=False
    for i,(u,v) in enumerate(loop):
        k,h=loop[(i+1)%len(loop)]
        if (v>y)!=(h>y) and x<(k-u)*(y-v)/(h-v)+u:r=not r
    return r
def cross2(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def signed(loop):
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(loop,loop[1:]+loop[:1]))
outline=ellipse(0,0,.098,.098,0,72)
loops=[outline]+[q[1] if signed(q[1])<0 else list(reversed(q[1])) for q in Holes]
assert signed(outline)>0 and all(signed(v)<0 for v in loops[1:])
xy=[];edges=[];ranges=[]
for p in loops:
    n=len(xy);N=len(p);xy.extend(p)
    ranges.append((n,N))
    edges.extend((n+i,n+(i+1)%N) for i in range(N))
cdt,_,polys,orig,_,_=delaunay_2d_cdt([Vector(v) for v in xy],edges,[],0,1e-10,True)
assert len(orig)==len(xy), (len(orig),len(xy))
imap=[]
for t in orig:
    assert len(t)==1,t;imap.append(t[0])
faces=[]
for k in polys:
    assert len(k)==3
    a1,b1,c1=(xy[imap[q]] for q in k)
    centroid=tuple((a1[m]+b1[m]+c1[m])/3 for m in (0,1))
    if point_in(centroid,outline) and not any(point_in(centroid,h) for h in loops[1:]):
        q=[imap[u] for u in k]
        faces.append(tuple(q if cross2(a1,b1,c1)>0 else reversed(q)))
# One connected positive-thickness geometric plate, with top/bottom surfaces
# cut out and 29 continuous bare-metal inner walls tessellated explicitly.
N=len(xy);dep=.0034
v=[(x,y,z) for z in (dep/2,-dep/2) for x,y in xy]
f=faces+[tuple(N+q for q in reversed(t)) for t in faces]
for j,C in ranges:
    for i in range(C):
        k=(i+1)%C
        f.append((j+i,j+i+N,j+k+N,j+k))
plate=mesh('PATTERN_SIEVE_TRUE_PERFORATED_PLATE',sieve,H,v,f,bronze)
plate.data.materials.append(boremat)
for q in plate.data.polygons:q.material_index=0 if q.index<2*len(faces) else 1
# The rim has a clear outer and inner edge and never obstructs the pattern.
def revolve(name,group,parent,prof,mat,N=64):
    vs=[];fs=[]
    for r,z in prof:
        vs.extend((r*math.cos(i*math.tau/N),r*math.sin(i*math.tau/N),z) for i in range(N))
    for j in range(len(prof)):
        k=(j+1)%len(prof)
        for i in range(N):
            l=(i+1)%N
            fs.append((j*N+i,j*N+l,k*N+l,k*N+i))
    m=mesh(name,group,parent,vs,fs,mat)
    for p in m.data.polygons:p.use_smooth=True
    return m
revolve('Continuous dark aubergine rim shell',sieve,H,[
 (.096,-.0065),(.103,-.0074),(.111,-.0049),(.113,.0016),(.113,.0102),(.110,.0135),(.101,.0143),(.097,.010),(.097,.004),(.095,-.0007)],violet_lo,72)
revolve('Prominent rolled golden rim bead',sieve,H,[
 (.103,.0132),(.106,.0120),(.110,.0130),(.109,.0150),(.105,.0157),(.103,.0153)],bronzelite,72)
revolve('Secondary etched lower rim line',sieve,H,[
 (.111,-.0027),(.113,-.0034),(.113,-.0008),(.111,-.0001)],bronzedark,72)
for s in (-1,1):
    box('Small opposed patterned hand grip '+str(s),sieve,H,(s*.125,-.004,.004),(.056,.045,.010),violet,.011,4)
    for j in range(-3,4):
        box('Short gold grip grip knurl '+str((s,j)),sieve,H,(s*(.129+.0032*j),-.003,.0098),(.0016,.019,.003),bronzelite,.0009,2)
    rod('Plain visible rim inset pin '+str(s),sieve,H,(s*.105,.003,.012),(s*.105,.003,.016),.004,bronzelite,14)

box('Powder plate angled porcelain stepped bevel',study,W,(0,0,-.007),(.227,.225,.018),tiletrim,.012,5)
box('Dark matte sample tile under separate powder print',study,W,(0,0,.001),(.217,.215,.011),slate,.010,4)
for s in (-1,1):
    box('Quiet brass study tray marker '+str(s),study,W,(0,s*.104,.007),(.075,.0016,.0018),bronzedark,.0006,2)
# Mapped 1-to-1, same-facing pattern and scale, visibly tactile irregular
# powder heights and sparse loose edge grains. No floating broad texture.
rng=random.Random(7313)
pverts={m:[] for m in (ivory,purple,ochre,coral)}
pfaces={m:[] for m in pverts}
height=.00675
for label,loop,c,m in Holes:
    vv,ff=pverts[m],pfaces[m]
    lo=[(x,y,height) for x,y in loop]
    # For an arc, use a per-loop constrained fill before rounding/scattering.
    # A triangle's vertices represent authentic physical support of the print.
    cc,_,ff2,_,_,_=delaunay_2d_cdt([Vector(p) for p in loop],[(i,(i+1)%len(loop)) for i in range(len(loop))],[],0,1e-10,True)
    triangles=[tuple(q) for q in ff2 if point_in((sum(cc[z].x for z in q)/3,sum(cc[z].y for z in q)/3),loop)]
    # Irregular edge bead base w/ raised ridgeline tiny geometry for readability.
    assert len(cc)==len(loop) and triangles
    roof0=len(vv); rr0=len(vv)+len(cc)
    vv.extend((p.x,p.y,height+rng.uniform(.00045,.0016)) for p in cc)
    vv.extend((p.x,p.y,height-.0003) for p in cc)
    inv={ (round(p.x,7),round(p.y,7)):i for i,p in enumerate(cc)}
    for j in range(len(loop)):
        a1=inv[tuple(round(v,7) for v in loop[j])]; b1=inv[tuple(round(v,7) for v in loop[(j+1)%len(loop)])]
        ff.append((roof0+a1,rr0+a1,rr0+b1,roof0+b1))
    for tri in triangles:
        pa,pb,pc=tuple(cc[z] for z in tri)
        order=tri if cross2(pa,pb,pc)>0 else tuple(reversed(tri))
        ff.append(tuple(roof0+z for z in order))
        ff.append(tuple(rr0+z for z in reversed(order)))
        cx=sum(cc[z].x for z in tri)/3;cy=sum(cc[z].y for z in tri)/3
        r=rng.uniform(.00028,.0012)
        vx=len(vv)
        vv.extend(((cx-r,cy,height+.0009),(cx,cy-r,height+.0008),(cx+r,cy,height+.0012),(cx,cy+r,height+.0008),(cx,cy,height+rng.uniform(.0018,.0032))))
        ff.extend(tuple(vx+k for k in q) for q in ((0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)))
    if len(label)>4:
        for j in range(3):
            point=loop[(j*7+3)%len(loop)]
            dx,dy=point[0]-c[0],point[1]-c[1]
            d=math.hypot(dx,dy)
            if d<1e-5:continue
            h=rng.uniform(.0007,.0014)
            qx=point[0]+.00165*dx/d;qy=point[1]+.00165*dy/d
            v0=len(vv);vv.extend(((qx-h,qy,height-.0003),(qx,qy-h,height-.0003),(qx+h,qy,height-.0003),(qx,qy+h,height-.0003),(qx,qy,height+h)))
            ff.extend(tuple(v0+z for z in q) for q in ((0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)))
for m,v in pverts.items():
    mesh('MATCHED_POWDER_TRANSFER_'+m.name,study,W,v,pfaces[m],m)
# A modest, genuine open sampling cup behind the swatch, not necessary for
# function but a visual material cue. It does not touch plate or swatch.
cup=empty('OPEN_SAMPLE_VESSEL',study,loc=(.219,.109,.030))
revolve('Mini open brass specimen cup',study,cup,[
 (.001,.002),(.019,.002),(.024,.008),(.026,.025),(.0245,.028),(.022,.027),(.020,.014),(.008,.010),(.001,.010)],bronzebowl,40)
rod('Preset powder shape in specimen cup',study,cup,(0,0,.010),(0,0,.016),.016,ochre,32)

box('Studio floor only',studio,None,(0,0,-.025),(200,200,.048),ground,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color,aim=(0,0,.09)):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,aim);return o
lamp('Wide warm frontal key',(-.54,-.68,.88),57,.71,(1,.92,.78))
lamp('Soft cool front fill',(.70,-.40,.50),31,.55,(.86,.94,1))
lamp('Warm back rim cold-violet controlled lighting',(.15,.59,.69),52,.58,(1,.93,.86))
world=bpy.data.worlds.new('Warm stable studio');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.61,.57,.64,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.42
lens=bpy.data.cameras.new('Studio optic');cam=bpy.data.objects.new('Studio optic',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=.605
def setcam(pos,target,scale):
    cam.location=pos;look(cam,target);lens.ortho_scale=scale
setcam((.37,-.81,.59),(.003,.000,.088),.610)
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.10
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,sieve,study):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
def still(to,pos,target,scale,res):
    setcam(pos,target,scale);S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',(.37,-.81,.59),(.003,.000,.088),.605,(512,512))
if a.review:
    still(a.review/'plate-face-true-openings.webp',(-.175,-.57,.405),(-.126,.032,.139),.293,(800,760))
    still(a.review/'separate-matching-powder.webp',(.18,-.28,.67),(.136,-.015,.047),.241,(760,760))
    # Opposite normal sees sidewall thickness and real light through the aperture.
    still(a.review/'underside-backed-by-light.webp',(-.105,.53,.112),(-.125,.036,.142),.288,(800,728))
