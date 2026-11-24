"""Original Singapore-inspired stair display with a physical continuous bicycle wheel trough."""
import argparse
import math
import random
from pathlib import Path
import sys
import bpy
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='stair-side-bicycle-wheeling-channel'
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

stairs=collection('01 cut stair flight and distinct landings')
channel=collection('02 one-piece physical trough and editable saddles')
handrail=collection('03 separate pedestrian handrail')
marks=collection('04 original explanatory marks')
studio=collection('05 studio camera/light, omitted from export')
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

foundation=material('Dusty deep warm substrate', '716D5B', .90)
plinth=material('Muted forest-green exhibit base', '41554C', .74)
concrete=material('Warm light cast concrete stairs', 'ACA697', .79)
cut=material('Pale warm sliced concrete face', 'B8AD92', .83)
lower=material('Gray pavement at lower approach', '838D84', .83)
top=material('Gray light landing slabs', 'B4AEA0', .81)
seam=material('Dark stone joint line', '737D70', .85)
nosings=material('Warm unnumbered contrast strip', 'CFB275', .69)
rail=material('Quiet deep green handrail finish', '365852', .44, .28)
metal=material('Dull stainless fixings', '78827F', .46, .47)
blue=material('Desaturated cobalt wheeling trough exterior', '3B7691', .46, .36)
blue_f=material('Satin slightly lighter continuous contact bed', '5E95A5', .52, .24)
blue_edge=material('Lifted edge high point in warm blue', '679EAF', .40, .32)
blue_bottom=material('Deep blue steel pan underside', '365F73', .48, .35)
white=material('Pale warm exhibit mark paint', 'E3D9B9', .67)
asphalt=material('Studio-only matte sage shadow surface', '8D9F92', .82)
aggregate=[material('Exposed mineral fleck A','D3C4A2',.90),material('Exposed mineral fleck B','837F72',.92)]
root=empty('ASSET_StairSideBicycleWheelingChannel',stairs)

def block(n,c,x0,x1,y0,y1,z0,z1,mat,b=.004,sg=1):
    return box(n,c,root,((x0+x1)*.5,(y0+y1)*.5,(z0+z1)*.5),(x1-x0,y1-y0,z1-z0),mat,b,sg)

def solid(n,c,v,f,materials,mi=None):
    ob=mesh(n,c,root,v,f,materials[0])
    for m in materials[1:]:
        ob.data.materials.append(m)
    if mi is not None:
        for j,k in zip(ob.data.polygons,mi):
            j.material_index=k
    return ob

def section_body(n,c,x0,x1,y0,y1,base,za,zb,mat):
    v=[(x0,y0,base),(x1,y0,base),(x1,y1,base),(x0,y1,base),
      (x0,y0,za),(x1,y0,zb),(x1,y1,zb),(x0,y1,za)]
    f=[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    return solid(n,c,v,f,[mat])

block('Cutaway exhibit base',stairs,-1.487,1.355,-.711,.673,.009,.092,plinth,.023,3)
for x in (-1.275,1.139):
    for y in (-.522,.463):
        box('Dark exhibit base floor pad',stairs,root,(x,y,.006),(.132,.107,.012),foundation,.005)
# Two cropped landings and one independently inspectable stair flight.
base_z=.143
rise=.116
upper=base_z+6*rise
block('Lower cropped loading landing slab',stairs,-1.438,-1.145,-.644,.591,.091,base_z,lower,0)
block('Approach paving beside lower transition',stairs,-1.147,-.926,-.323,.576,.092,base_z,lower,.006,2)
section_body('Sloped core below abruptly cut stair side',stairs,-.917,.728,-.336,.573,.092,.118,.769,cut)
block('Long pier below rear upper landing',stairs,.715,1.304,-.334,.579,.093,.804,cut,.009,2)
block('Upper landing slab behind clear channel',stairs,.670,1.306,-.336,.584,.789,upper,top,.004,2)
block('Narrow upper handover closeout slab',stairs,.985,1.305,-.639,-.334,.789,upper,top,0)
block('Upper landing closeout pier',stairs,.985,1.305,-.636,-.337,.091,.799,cut,.008,2)
for i in range(6):
    lo=-.932+i*.267
    height=base_z+(i+1)*rise
    bottom=base_z+i*rise-.021
    block('Editable concrete stair tread',stairs,lo,lo+.269,-.326,.565,bottom,height,concrete,.006,2)
    block('Held amber tread nosing accent',stairs,lo+.010,lo+.046,-.302,.520,height-.0007,height+.0011,nosings,.0016,2)
# Separate turn of two slim mounted handrails keeps the wheel surface visible.
def unitrail(n,zoff,r):
    pts=[(-1.298,.469,base_z+zoff),(-1.033,.469,base_z+zoff),
          (-.989,.469,base_z+zoff+.024),(-.868,.469,base_z+zoff+.106),
          (.638,.469,upper+zoff-.007),(.718,.469,upper+zoff), (1.235,.469,upper+zoff)]
    sweep(n,handrail,root,pts,r,rail,10)
unitrail('Continuous separate upper pedestrian rail',.700,.022)
unitrail('Lower quiet separate rail member',.415,.015)
for x,z in [(-1.303,base_z),(-.758,base_z+.116),(-.216,base_z+.348),(.339,base_z+.580),(.976,upper),(1.226,upper)]:
    box('Rail base plate bolted to walkable surface',handrail,root,(x,.469,z+.008),(.081,.080,.017),metal,.005,2)
    rod('Independently editable rail upright',handrail,root,(x,.469,z+.010),(x,.469,z+.692),.018,rail,12)
    for y in (.440,.497):
        rod('Round rail plate stud',handrail,root,(x,y,z+.016),(x,y,z+.023),.0047,metal,8)

# Continuous narrow hollow-looking U-section, made from a closed bent-sheet solid.
# Analytic variable approach shoulders and tangent blend are original display geometry.
CY=-.492
X0=-1.145
X1=.985
START=-1.072
END=.758
blend=.125
total=END-START
def level(x):
    u=min(total,max(0,x-START))
    if u<blend:
        area=u*u/(2*blend)
    elif u>total-blend:
        area=total-blend-(total-u)**2/(2*blend)
    else:
        area=u-blend/2
    return base_z+6*rise*area/(total-blend)
def smooth(v):
    v=min(1,max(0,v))
    return v*v*(3-2*v)
def flange(x):
    q=smooth(min((x-X0)/.250,(X1-x)/.272))
    w=.085-.022*q
    h=.005+.035*q
    return w,h

def profile(x):
    w,h=flange(x);z=level(x)
    # Cross section from internal floor to rounded inner wall, rolled edge and exterior underside.
    shape=[(-w+.017,0), (w-.017,0), (w-.012,.004), (w-.006,h*.69),
      (w-.002,h*.94), (w+.003,h), (w+.009,h*.92), (w+.012,h*.71),
      (w+.010,h*.31),(w+.005,-.006),(w-.012,-.011),
      (-w+.012,-.011),(-w-.005,-.006),(-w-.010,h*.31),(-w-.012,h*.71),
      (-w-.009,h*.92),(-w-.003,h),(-w+.002,h*.94),(-w+.006,h*.69),(-w+.012,.004)]
    return [(x,CY+y,z+zz) for y,zz in shape]
xpts=sorted(set([X0+(X1-X0)*i/88 for i in range(89)]
                +[START,START+blend,END-blend,END,-.887,-.410,.064,.529,.718]))
N=len(xpts);K=len(profile(X0))
v=[pt for x in xpts for pt in profile(x)]
f=[];mi=[]
for i in range(N-1):
    for j in range(K):
        a0=i*K+j;a1=i*K+(j+1)%K
        f.append((a0,(i+1)*K+j,(i+1)*K+(j+1)%K,a1))
        mi.append(1 if j in (0,1,K-1) else 2 if j in (3,4,5,K-7,K-6,K-5,K-4) else 3 if j in (9,10,11) else 0)
f.extend([tuple(range(K)),tuple(reversed(range((N-1)*K,N*K)))]);mi.extend([0,0])
trough=solid('CONTINUOUS_WHEEL_TROUGH',channel,v,f,[blue,blue_f,blue_edge,blue_bottom],mi)

# Pads sit against the true ramp sheet underside at both ends of each bracket.
for j,x in enumerate((-.925,-.578,-.210,.166,.525,.842)):
    z=level(x)
    block('Discrete concrete side seat',channel,x-.079,x+.079,CY-.084,CY+.084,.091,max(.105,z-.066),cut,.007,2)
    bracket=section_body('Welded blue wedge saddle supporting channel',channel,x-.052,x+.052,CY-.060,CY+.060,max(.099,z-.073),level(x-.052)-.0105,level(x+.052)-.0105,blue_bottom)
    for y in (CY-.073,CY+.073):
        x0,x1=x-.046,x+.046
        Z1=max(.109,z-.057)
        block('Small side bearing tab fastened to seat',channel,x0,x1,y-.016,y+.016,max(.101,z-.069),Z1,metal,.003,2)
        rod('Ball-shaped bracket bolt head',channel,root,(x,y,Z1),(x,y,Z1+.006),.007,metal,8)
# Small original bicycle pictogram uses physical paint lines (no claim to be an official sign).
def paint(name,points,r=.006,close=False):
    return sweep(name,marks,root,points,r,white,6,closed=close)
def circle(x,y,r):
    return [(x+r*math.cos(math.tau*i/24),y+r*math.sin(math.tau*i/24),base_z+.0012) for i in range(24)]
for xx in (-1.364,-1.249):
    paint('Original exhibit pictogram wheel outline',circle(xx,-.119,.043),.004,True)
pz=base_z+.0012
for a1,b1 in [((-1.363,-.118),(-1.322,-.086)),((-1.322,-.086),(-1.289,-.132)),
    ((-1.289,-.132),(-1.363,-.118)),((-1.289,-.132),(-1.271,-.082)),((-1.271,-.082),(-1.249,-.118)),
    ((-1.270,-.082),(-1.271,-.071)),((-1.326,-.081),(-1.311,-.081))]:
    paint('Original exhibit pictogram frame',[(a1[0],a1[1],pz),(b1[0],b1[1],pz)],.0043)
block('Original explanatory cutaway display plaque',marks,-.873,-.236,-.712,-.702,.022,.074,rail,.004)
etch('Fictional wheel-channel display wording',marks,root,(-.555,-.713,.034),'WHEELING CHANNEL',.026,white)
# Sparse mineral flecks on the section side, no texture image or added path obstacles.
rng=random.Random(440)
verts=[]; faces=[]; im=[]
for _ in range(132):
    x=rng.uniform(-.849,.666);z=rng.uniform(.121,.758)
    est=.118+(.769-.118)*(x+.917)/(.728+.917)
    if z>=est-.013:
        continue
    y=-.338-rng.uniform(.0005,.004)
    rr=rng.uniform(.003,.009); n=rng.choice((3,4,5)); off=len(verts)
    t=rng.uniform(0,math.tau)
    for k in range(n):
        a1=t+k*math.tau/n
        verts.append((x+rr*math.cos(a1),y,z+.78*rr*math.sin(a1)))
    faces.append(tuple(range(off,off+n)));im.append(rng.randrange(2))
solid('Small native concrete section aggregate paint flecks',stairs,verts,faces,aggregate,im)

box('Studio shadow surface',studio,None,(0,0,-.025),(200,200,.048),asphalt,0)
def look(o,t):
    o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,(0,0,.68))
lamp('Warm broad shaded daylight key',(-2.46,-3.78,4.32),448,3.44,(1,.92,.79))
lamp('Soft trough fill to preserve lip legibility',(2.9,-3.2,2.20),203,2.44,(.89,.98,1))
lamp('Daylight rail separation',(1.46,2.4,4.21),258,2.51,(.89,.96,1))
world=bpy.data.worlds.new('Neutral warm sky');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.58,.65,.63,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.47
lens=bpy.data.cameras.new('Model studio');cam=bpy.data.objects.new('Model studio',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=3.40
cam.location=(1.64,-6.8,3.91);look(cam,(-.006,-.053,.657))
S.render.engine='CYCLES';S.cycles.samples=40;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.11
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (stairs,channel,handrail,marks):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
def still(to,pos,target,scale,res):
    cam.location=pos;look(cam,target);lens.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',(1.64,-6.8,3.91),(-.006,-.053,.657),3.40,(512,512))
if a.review:
    still(a.review/'low-landing-and-rolled-channel.webp',(-2.79,-2.58,1.94),(-.984,-.323,.377),1.46,(840,600))
    still(a.review/'high-landing-and-saddle.webp',(2.71,-2.37,2.77),(.765,-.283,.795),1.40,(840,600))
    still(a.review/'top-continuous-section.webp',(-1.41,-1.88,6.75),(-.043,-.409,.521),3.12,(920,560))
