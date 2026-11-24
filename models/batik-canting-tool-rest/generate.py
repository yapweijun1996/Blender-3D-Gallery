"""Original Malaysia-inspired canting display: open copper bowl, continuous fine spout and a small cloth study."""
import argparse
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='batik-canting-tool-rest'
out=a.output.resolve()
for k in ('previews','exports'):
    (out/k).mkdir(parents=True,exist_ok=True)
if a.review:
    a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene
S.unit_settings.system='METRIC'

def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c

stand=collection('01 separate board and padded cradle')
tool=collection('02 canting body with a genuinely connected hollow spout')
swatch=collection('03 original folded cloth study, not a cultural stencil')
studio=collection('04 studio excluded')
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

board=material('Oiled dark meranti coloured display wood','795841',.63)
edge=material('Quiet earthen wood grain end','634A39',.72)
green=material('Warm slate tea green holder padding','486B61',.61,.10)
sheet=material('Dark green ash stone shallow insert','566F66',.72)
feet=material('Dark woven presentation base accents','50483B',.78)
body_c=material('Hand-beaten warm satin copper reservoir','B76E50',.39,.63)
inside_c=material('Slightly darker copper cavity and lumen','A56547',.45,.54)
rim_c=material('Soft lighter polished copper lip','D99366',.40,.59)
joint=material('Darker brass tang and copper neck seam','9E6F4A',.45,.48)
handle_m=material('Warm dark turned wooden handle','76543D',.59)
handle_a=material('Subtle grain and burnished wooden ring','5D4031',.52)
indigo=material('Deep teal-indigo original cloth','355D69',.84)
indigo_edge=material('Light teal underside of turned cloth corner','51717A',.79)
indigo_shadow=material('Dark indigo selvage shadow','2F4950',.84)
ivory=material('Warm straw resist-like pattern colour','D8BD86',.76)
leaf=material('Muted amber flower accent on study swatch','AE7954',.74)
fade=material('Desaturated warm sage motif accent','8C9B77',.83)
plaque=material('Original cream exhibit title','DBCCA2',.68)
ground=material('Studio sage matte shadow surface','83968C',.81)
root=empty('ASSET_BatikCantingToolRest',stand)

def block(n,c,x0,x1,y0,y1,z0,z1,mat,b=0,seg=1):
    return box(n,c,root,((x0+x1)*.5,(y0+y1)*.5,(z0+z1)*.5),(x1-x0,y1-y0,z1-z0),mat,b,seg)
def faces_materials(n,c,v,f,materials,mi):
    o=mesh(n,c,root,v,f,materials[0])
    for m in materials[1:]:o.data.materials.append(m)
    for face,i in zip(o.data.polygons,mi):face.material_index=i
    return o

block('Thin layered original presentation plank',stand,-.228,.217,-.115,.116,.008,.041,board,.009,3)
block('Dark end grain shadow line',stand,-.224,.213,-.111,.111,.006,.015,edge,.006,2)
for x in (-.184,.166):
    for y in (-.082,.082):
        box('Setback display foot',stand,root,(x,y,.005),(.041,.034,.010),feet,.004,2)
block('Individual shallowed stone insert under tip',stand,.042,.115,-.057,.009,.040,.045,sheet,.009,3)
block('Inner shadow of the dry drip insert',stand,.049,.108,-.052,.003,.044,.046,green,.006,3)
block('Original exhibit name plate',stand,-.119,.041,-.117,-.111,.016,.033,green,.003,2)
etch('Canting engraved exhibit plate',stand,root,(-.039,-.118,.021),'CANTING  /  BATIK LUKIS',.0084,plaque)
for x in (-.110,.032):
    rod('Mounting plate pin',stand,root,(x,-.118,.025),(x,-.119,.025),.0015,joint,9)

# An intentionally offset wooden handle and two independent cradle supports.
def wood_shell(n,xr,materials,indices):
    N=24;V=[]
    for x,y,z,radius in xr:
        for i in range(N):
            t=math.tau*i/N
            V.append((x,y+radius*math.cos(t),z+radius*math.sin(t)))
    F=[];MI=[]
    for k in range(len(xr)-1):
        for j in range(N):
            o=(j+1)%N
            F.append((k*N+j,k*N+o,(k+1)*N+o,(k+1)*N+j))
            MI.append(indices[k])
    F.extend([tuple(reversed(range(N))),tuple(range((len(xr)-1)*N,len(xr)*N))]);MI.extend([0,0])
    ob=faces_materials(n,tool,V,F,materials,MI)
    for f in ob.data.polygons:
        f.use_smooth=len(f.vertices)==4
    return ob
hY=-.016
hZ=.101
wood_shell('Offset turned wooden canting handle',[
   (-.179,hY-.007,hZ-.004,.0038),(-.176,hY-.007,hZ-.004,.0072),
   (-.169,hY-.006,hZ-.004,.0094),(-.155,hY-.005,hZ-.003,.0107),
   (-.131,hY-.002,hZ-.001,.0115),(-.110,hY,hZ,.0115),(-.090,hY+.001,hZ+.001,.0107),
   (-.071,hY+.002,hZ+.002,.0092),(-.058,hY+.003,hZ+.003,.0080),
   (-.045,hY+.004,hZ+.003,.0072),(-.030,hY+.005,hZ+.003,.0065)
  ],[handle_m,handle_a],[1,0,0,0,0,0,0,0,1,0])
wood_shell('Copper offset handle ferrule with shoulder',[
    (-.055,-.012,.104,.0072),(-.052,-.012,.104,.0090),(-.034,-.011,.104,.0085),
    (-.024,-.010,.103,.0065),(-.0218,-.010,.100,.0055)], [joint,rim_c],[1,0,0,1])
sweep('Short bent metal tang seated on external weld saddle',tool,root,
     [(-.038,-.012,.105),(-.030,-.011,.101),(-.0275,-.009,.096)],.0032,body_c,14)
# The holder touches the wood underside, not the canting mouth or spout.
block('Handle rest pedestal',stand,-.126,-.095,-.043,.011,.041,.083,sheet,.004,2)
block('Flat padded handle saddle seat',stand,-.124,-.097,-.034,.001,.081,.08965,green,.0025,2)
for y in (-.031,-.001):
    rod('Short rounded U cradle shoulder',stand,root,(-.125,y,.090),(-.096,y,.090),.0043,green,14)
block('Low reservoir support block',stand,-.009,.017,-.018,.018,.041,.058,sheet,.003,2)
block('Thin padded bowl heel cutout',stand,-.007,.015,-.013,.013,.057,.0613,green,.0018,2)

# One connected copper shell, with no disk obstructing the bowl-to-spout path.
N=48; Cx=.006; Cy=0.0
profile=[
    (.011,.009,.061),(.018,.013,.066),(.023,.017,.074),(.027,.0209,.083),(.0280,.0218,.091),
    (.0284,.0220,.101),(.030,.0227,.115),(.0315,.0235,.127),(.0315,.0235,.129),
    (.0299,.0224,.1302),(.0285,.0210,.128),(.0286,.0212,.125),(.0279,.0208,.115),
    (.0265,.0201,.101),(.0262,.0199,.091),(.0251,.0194,.084),(.0206,.0155,.077),
    (.0155,.0125,.071),(.0095,.008,.069),
]
rad=[-math.pi+math.tau*j/N for j in range(N)]
V=[(Cx+rx*math.cos(t),Cy+ry*math.sin(t),z) for rx,ry,z in profile for t in rad]
F=[];MI=[]
J0,J1=22,26
for k in range(len(profile)-1):
    for j in range(N):
        if k in (4,13) and J0<=j<J1:continue
        jj=(j+1)%N
        F.append((k*N+j,k*N+jj,(k+1)*N+jj,(k+1)*N+j))
        MI.append(2 if 7<=k<=10 else 1 if k>=11 else 0)
F.extend([tuple(reversed(range(N))),tuple(range((len(profile)-1)*N,len(profile)*N))]);MI.extend([0,1])
def loop(low,high):
    return [low*N+i for i in range(J0,J1+1)]+[high*N+i for i in range(J1,J0-1,-1)]
L=loop(4,5)
I=loop(14,13)
angles=[math.atan2((V[j][2]-.096)/.005,V[j][1]/.0057) for j in L]
K=len(angles)
def point(t):
    return Vector((.039+.058*t,-.0044*t*t,.096-.031*t*t))
def tangent(t):
    return Vector((.058,-.0088*t,-.062*t)).normalized()
def lumen(t):
    return .00440-.00325*t**.77
def exterior(t):
    return lumen(t)+(.0024-.00165*t)
def add_swept_ring(t,rad):
    p=point(t);T=tangent(t)
    Y=(Vector((0,1,0))-T*T.y).normalized()
    Z=T.cross(Y).normalized()
    indices=[]
    for ang in angles:
        indices.append(len(V))
        V.append(tuple(p+Y*math.cos(ang)*rad+Z*math.sin(ang)*rad))
    return indices
def join_ring(lo,hi,m,flip=False):
    for j in range(K):
        n=(j+1)%K
        q=(lo[j],lo[n],hi[n],hi[j])
        F.append(q[::-1] if flip else q)
        MI.append(m)
ts=[i/28 for i in range(29)]
for t in ts:
    Q=add_swept_ring(t,exterior(t))
    R=add_swept_ring(t,lumen(t))
    join_ring(L,Q,3 if t<.09 else (2 if t>.90 else 0))
    join_ring(I,R,1,True)
    L,I=Q,R
join_ring(L,I,2)
vessel=faces_materials('CANTING_CONNECTED_COPPER_BOWL_AND_SPOUT',tool,V,F,[body_c,inside_c,rim_c,joint],MI)
for f in vessel.data.polygons:
    f.use_smooth=len(f.vertices)==4
# External handle saddle follows the actual left outer mesh contours. One shallow inset
# fully within the copper wall joins the separate solid without reaching the cavity.
pad_ids=[4*N+j for j in range(2,6)]+[5*N+j for j in range(2,6)]
sp=[(V[i][0]+d,V[i][1],V[i][2]) for d in (-.0045,.00055) for i in pad_ids]
sf=[]
for j in range(3):
    sf.extend([(j,j+1,j+5,j+4),(j+12,j+13,j+9,j+8)])
loop_ids=[0,1,2,3,7,6,5,4]
for j,e in enumerate(loop_ids):
    f=loop_ids[(j+1)%len(loop_ids)]
    sf.append((f,e,e+8,f+8))
faces_materials('Exterior copper tang weld saddle',tool,sp,sf,[joint,rim_c],[0]*6+[1]*8)


# A small cloth study with one turned corner, independently editable. All painted-looking
# strokes below are original shallow geometry, never a photo or recreated historic motif.
xmin,xmax=.070,.182
ymin,ymax=.023,.092
def height(x,y):
    return .043+.002*math.sin((x-xmin)*41+(y-ymin)*23)+.009*max(0,((x-.150)+(y-.064))/.060)**2
NX,NY=18,12
v=[]
for j in range(NY+1):
    for i in range(NX+1):
        fx=i/NX;fy=j/NY
        x=xmin+(xmax-xmin)*fx+.0012*math.sin(j*.51)*math.sin(fx*math.pi)
        y=ymin+(ymax-ymin)*fy+.0011*math.sin(i*.56)*math.sin(fy*math.pi)
        v.append((x,y,height(x,y)))
f=[];mi=[]
for j in range(NY):
    for i in range(NX):
        u=j*(NX+1)+i
        f.append((u,u+1,u+NX+2,u+NX+1))
        mi.append(1 if i>=15 and j>=9 else 0)
ob=faces_materials('Small folded indigo swatch',swatch,v,f,[indigo,indigo_edge],mi)
sol=ob.modifiers.new('Tangible cloth thickness','SOLIDIFY');sol.thickness=.00165;sol.offset=-1
def stroke(n,path,r,m,closed=False):
    xyz=[(x,y,height(x,y)+.00091) for x,y in path]
    return sweep(n,swatch,root,xyz,r,m,6,closed=closed)
for side in (-1,1):
    y=(ymin+.0032 if side<0 else ymax-.0032)
    stroke('Subtle selvedge accent',[(xmin+.003+(xmax-xmin-.006)*k/18,y+.0004*math.sin(k*.76)) for k in range(19)],.0010,ivory)
for side in (-1,1):
    x=(xmin+.0032 if side<0 else xmax-.0032)
    stroke('Subtle selvedge accent',[(x+.0004*math.sin(k*.66),ymin+.003+(ymax-ymin-.006)*k/15) for k in range(16)],.0010,fade)
for j,(x,y,l,tilt) in enumerate(((.086,.039,.023,.63),(.107,.041,.027,.91),(.133,.041,.028,.78),(.156,.044,.019,.94))):
    dx=math.cos(tilt);dy=math.sin(tilt)
    px,py=-dy,dx
    stem=[]
    for i in range(10):
        t=i/9
        stem.append((x+l*t*dx+.0018*math.sin(t*math.pi),y+l*t*dy))
    stroke('Original branching stem on cloth',stem,.00112,ivory)
    for ix,t in enumerate((.30,.52,.77)):
        ox=x+l*t*dx+.0018*math.sin(t*math.pi);oy=y+l*t*dy
        for s in (-1,1):
            scale=.0048-.0011*ix
            pts=[]
            for k in range(15):
                a1=k*math.tau/15
                u=math.sin(a1)*scale*.66
                v=(1-math.cos(a1))*scale
                pts.append((ox+u*dx+s*v*px,oy+u*dy+s*v*py))
            stroke('Invented petal outline on swatch',pts,.00063,ivory if (j+ix)%2 else fade,True)
    x1,y1=stem[-1]
    for k in range(4):
        t=k*math.tau/4
        cx=x1+.0027*math.cos(t);cy=y1+.0027*math.sin(t)
        stroke('Small original petal dot loops',[(cx+.00134*math.cos(math.tau*m/10),cy+.00134*math.sin(math.tau*m/10)) for m in range(10)],.00061,leaf,True)

box('Studio shadow surface',studio,None,(0,0,-.025),(200,200,.048),ground,0)
def look(o,t):
    o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,(0,0,.070))
lamp('Soft golden craft-table key',(-.577,-.880,1.17),70,.94,(1,.92,.80))
lamp('Low cool spout detail fill',(.82,-.515,.64),49,.655,(.86,.97,1))
lamp('Warm rim separation',(.27,.58,1.08),55,.72,(1,.94,.87))
world=bpy.data.worlds.new('Soft windows and neutral daylight');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.58,.65,.62,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.47
lens=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=.55
cam.location=(.39,-1.22,.89);look(cam,(-.006,.003,.061))
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512
S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.09
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (stand,tool,swatch):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)

def still(to,pos,target,scale,res):
    cam.location=pos;look(cam,target);lens.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',(.39,-1.22,.89),(-.006,.003,.061),.55,(512,512))
if a.review:
    still(a.review/'reservoir-cavity-and-joint.webp',(.202,-.148,.60),(.013,.000,.099),.125,(872,630))
    lens.clip_start=.0007
    still(a.review/'curved-hollow-tip.webp',(.245,-.029,.052),(.089,-.0039,.071),.055,(770,544))
    still(a.review/'swatch-and-separate-rest.webp',(.323,-.341,.75),(.082,.033,.061),.305,(808,620))
