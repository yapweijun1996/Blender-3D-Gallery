"""Original Penang-inspired roasting furniture exhibit, no recipe or replica."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='penang-heritage-kopi-roasting-station'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 brick roasting workshop exhibit')
last=collection('02 recessed pot saddle and parked wooden paddles')
loose=collection('03 separate pulley and rope display')
studio=collection('04 studio only; excluded from export')
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

def sweep(n,c,p,coords,r,mat,sides=7,closed=False,fixed_axis=(0,1,0)):
    points=[Vector(k) for k in coords]
    v=[]; f=[]; L=len(points)
    for i,q in enumerate(points):
        t=(points[(i+1)%L] if i<L-1 or closed else q)-(points[i-1] if i or closed else q)
        t.normalize()
        u=t.cross(Vector(fixed_axis)).normalized()
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


def linear(x):
    x=max(0,min(255,x))/255
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4
def vmat(n,rough,metal=0):
    m=material(n,'FFFFFF',rough,metal)
    v=m.node_tree.nodes.new('ShaderNodeVertexColor');v.layer_name='Procedural surface grain'
    m.node_tree.links.new(v.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return m
def apply_color(o,fn):
    c=o.data.color_attributes.new(name='Procedural surface grain',type='FLOAT_COLOR',domain='POINT')
    for v,x in zip(o.data.vertices,c.data):x.color=tuple(linear(k) for k in fn(v.co))+(1,)
def multi(n,c,r,v,f,m,ids,smooth=False):
    o=mesh(n,c,r,v,f,m[0])
    for mat in m[1:]:o.data.materials.append(mat)
    for p,k in zip(o.data.polygons,ids):p.material_index=k;p.use_smooth=smooth and len(p.vertices)==4
    return o
def colored_board(n,c,r,p,d,mat,hue):
    o=box(n,c,r,p,d,mat,.0068,3)
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=o
    for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    apply_color(o,lambda v: tuple(k*(1+.065*math.sin(v.y*99+v.x*9)+.045*math.sin(v.y*186+v.z*5)+.042*math.cos(v.x*21+v.y*50)) for k in hue))
    return o
plinth=vmat('Sculptural warm grey old cement exhibit surface',.84)
plaster=vmat('Natural neutral warm mortar banding',.85)
brick=vmat('Quiet rust and umber baked bricks',.83)
iron=vmat('Seasoned matte cast iron',.61,.47)
ironRim=vmat('Worn iron bearing surface',.48,.64)
wood=vmat('Tropical old hardwood with original tonal flecks',.65)
warmWood=vmat('Warm oiled hardwood paddle',.58)
bronze=material('Quiet burnt bronze non-branded fittings','80664A',.55,.56)
hardware=material('Dull dark iron fittings on independent stand','535855',.55,.66)
leather=material('Rope polishing brass pin tips','A48A5A',.56,.62)
rope=material('Natural muted hemp exhibit cord','AE9772',.84)
plate=material('Slate exhibit label and muted framing','334947',.64)
offWhite=material('Warm biscuit text','EFE1BD',.68)
beansM=material('Unglossed dark coffee beans sample','4D2922',.82)
beansAlt=material('Quiet chestnut variation on sample','6C4030',.82)
worldPlate=material('Background matte warmth only','787765',.88)
R=empty('PENANG_ORIGINAL_KOPI_ROASTING_STATION_EXHIBIT',base)
B=empty('ROASTING_POT_STOVE_AND_OPEN_MASONRY_SECTION',base,R)
P=empty('INDEPENDENT_PAUSED_POT_AND_PADDLE_TOOLS',last,R)
D=empty('SEPARATE_DISPLAY_PULLEY_NOT_CONNECTED_TO_STOVE',loose,R)
def colorgrain(o, rgb, f=1):
    apply_color(o,lambda v:tuple(k*(1+f*(.056*math.sin(v.x*91+v.y*64+v.z*51)+.027*math.cos(v.x*163-v.y*47+v.z*147)+.018*math.sin(v.y*179))) for k in rgb))
    return o
def block(n,c,p,loc,d,mat,rgb,bev=.007,f=1):
    o=box(n,c,p,loc,d,mat,bev,2)
    bpy.context.view_layer.update();bpy.context.view_layer.objects.active=o
    for m in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    return colorgrain(o,rgb,f)
def annulus(n,c,p,xy,profile,mat,tint=None,N=64,want_closed=True):
    x,y=xy
    vv=[];ff=[]
    for rr,zz in profile:
        for j in range(N):
            t=j*math.tau/N; vv.append((x+rr*math.cos(t),y+rr*math.sin(t),zz))
    L=len(profile)
    for i in range(L if want_closed else L-1):
        a=i*N;b=((i+1)%L)*N
        for j in range(N):
            jj=(j+1)%N;ff.append((a+j,a+jj,b+jj,b+j))
    if not want_closed:
        ff.extend((tuple(reversed(range(N))),tuple(range((L-1)*N,L*N))))
    o=mesh(n,c,p,vv,ff,mat)
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    if tint:colorgrain(o,tint)
    return o
def sector(n,c,p,xy,z0,z1,ri,ro,a,b,mat,tint):
    x,y=xy;nseg=5
    vv=[]
    for r,z in [(ro,z0),(ro,z1),(ri,z1),(ri,z0)]:
        for i in range(nseg):
            th=a+(b-a)*i/(nseg-1);vv.append((x+r*math.cos(th),y+r*math.sin(th),z))
    faces=[]
    for q in range(4):
        for j in range(nseg-1):
            a=q*nseg+j;b=((q+1)%4)*nseg+j
            faces.append((a,a+1,b+1,b))
    faces+=[tuple(i*nseg for i in range(4)),tuple(reversed([i*nseg+nseg-1 for i in range(4)]))]
    o=mesh(n,c,p,vv,faces,mat);colorgrain(o,tint)
    return o
cx,cy=-.23,.038
block('Aged grey concrete cutaway exhibit plinth',base,B,(0,-.030,.034),(1.80,1.14,.068),plinth,[115,118,99],.020)
block('Shallow low old workshop seating pad for masonry',base,B,(cx,cy,.078),(.947,.850,.024),plaster,[141,128,102],.021)
for j in range(9):
    z=.090+j*.052; r=.356; count=12
    for i in range(count):
        center=i*math.tau/count+(math.pi/count if j%2 else 0)
        off=abs((center+math.pi/2+math.pi)%math.tau-math.pi)
        if j<5 and off<(.57 if j<4 else .38):continue
        color=(126+(i*13+j*7)%24,78+(i*8+j*17)%27,53+(i*9+j*12)%16)
        sector(f'Individual original curved brick joint {j} {i}',base,B,(cx,cy),z,z+.0522,.280,r,center-.261,center+.261,brick,color)
    # Only uninterrupted structural band preserves the opening below; separate broad seat.
    if j>=5:
        annulus('Quiet continuous mortar bed under each upper course',base,B,(cx,cy),[(.281,z-.003),(.353,z-.003),(.353,z+.001),(.281,z+.001)],plaster,[129,118,92],36)
# Flat front shelf and low rear shadow leave this a real open vault rather than a black decal.
block('Low ash opening threshold plinth, no active heat',base,B,(cx,-.276,.097),(.369,.173,.020),plaster,[127,114,86],.009)
annulus('Independent forged ring seated on brick',base,B,(cx,cy),
  [(.279,.533),(.359,.533),(.359,.550),(.346,.563),(.280,.563)],ironRim,[76,72,62],64)
# One coherent finite-thickness pot with bowl bottom and open mouth.
potProf=[(.040,.183),(.117,.188),(.180,.227),(.222,.285),(.253,.354),(.277,.445),(.295,.545),
         (.323,.578),(.326,.595),(.318,.608),(.304,.604),(.296,.594),(.296,.580),(.276,.557),
         (.257,.457),(.232,.371),(.201,.309),(.167,.262),(.118,.233),(.040,.223)]
annulus('Genuinely hollow thick cast roast pot with real inner wall',last,P,(cx,cy),potProf,iron,[74,67,54],80,False)
annulus('Cast pot seating collar and bearing ledge',last,P,(cx,cy),
  [(.277,.552),(.314,.552),(.322,.558),(.319,.568),(.296,.57),(.278,.565)],ironRim,[94,85,67],80)
for side in (-1,1):
    ob=box('Independent pot rim handle loading shoe',last,P,(cx+side*.314,cy,.587),(.027,.098,.033),ironRim,.006,2)
    points=[(cx+side*(.321+.071*math.sin(t*math.pi/12)),cy+.047*math.cos(t*math.pi/12),.589+.016*math.sin(t*math.pi/12)) for t in range(13)]
    sweep('Solid returned forged pot grip',last,P,points,.010,hardware,10)
# Dark static beans as a thin recognizable material sample, not a roasting simulation.
v=[];f=[];matids=[]
for k in range(71):
    theta=k*math.pi*(3-math.sqrt(5));r=.155*math.sqrt((k+.5)/71)
    x=cx+r*math.cos(theta);y=cy+r*math.sin(theta)
    z=.244+1.20*r*r
    dx=.0135+.003*math.sin(k*6.87);dy=.0075+.0018*math.sin(k*7.31);h=.0077
    n=len(v);turn=.87*k;cc=math.cos(turn);ss=math.sin(turn)
    for band,(radius,height) in enumerate([(0.73,-.66),(1,0),(.79,.68)]):
        for j in range(10):
            t=j*math.tau/10;X=math.cos(t)*dx*radius;Y=math.sin(t)*dy*radius
            groove=.0022 if band==2 and abs(math.sin(t))<.40 else 0
            v.append((x+cc*X-ss*Y,y+ss*X+cc*Y,z+height*h-groove))
    for i in range(2):
        for j in range(10):
            b=(j+1)%10
            f.append((n+i*10+j,n+i*10+b,n+(i+1)*10+b,n+(i+1)*10+j));matids.append(k%3==0)
    f.extend([tuple(n+j for j in range(9,-1,-1)),tuple(n+20+j for j in range(10))]); matids.extend([k%3==0,k%3==0])
multi('Small original static unheated roast-bean display',last,P,v,f,[beansM,beansAlt],matids,True)

# Independently parked paddle heads and handles on a separate small wall rack.
for side in (-1,1):
    x=.338+side*.075
    block('Raised separate paddle-rest end block',last,P,(x,.280,.145),(.064,.125,.162),wood,[120,82,49],.008)
block('Low unconnected paddles rack crossbar',last,P,(.338,.279,.216),(.259,.095,.061),wood,[139,100,62],.008)
for side in [-1,1]:
    block('Rear upright attached to same paddle rack',last,P,(.338+side*.088,.312,.212),(.037,.057,.299),wood,[118,82,53],.005)
block('Second timber saddle on paddle rack',last,P,(.338,.2877,.368),(.235,.072,.049),wood,[120,81,51],.007)
for side,ht in [(-1,.73),(1,.63)]:
    x=.338+side*.070
    po=[(x-.027,.240,.230),(x+.027,.240,.230),(x+.034,.244,.373),(x+.020,.260,.423),
        (x+.012,.277,.457),(x-.012,.277,.457),(x-.020,.260,.423),(x-.034,.244,.373)]
    # Each paddle is an actual finite-thickness standalone wooden tool.
    ov=[(a,b+o,c+.0156) for o in [-.005,.009] for a,b,c in po];N=len(po)
    faces=[tuple(range(N)),tuple(reversed(range(N,2*N)))]
    faces.extend((k,k+N,(k+1)%N+N,(k+1)%N) for k in range(N))
    ob=mesh('Paired rounded parked hardwood paddle blade',last,P,ov,faces,warmWood);colorgrain(ob,[186,134,75])
    o=rod('Separate long wooden parked paddle shaft',last,P,(x,.272,.4496),(x,.352,ht+.0156),.010,warmWood,12);colorgrain(o,[160,109,60])
# Separate end-cheek supporting a static single spool and real wrap; there is no link to the pot.
pulX=.649;pulY=.305;pulZ=.930;cordZ=.935;groove=.047
block('Separate support exhibit foot for pulley stand',loose,D,(pulX,.318,.101),(.285,.272,.070),wood,[111,78,47],.011)
for s in (-1,1):
    x=pulX+s*.084
    block('Independent short upright on pulley exhibit support',loose,D,(x,.384,.530),(.065,.062,.838),wood,[140,96,51],.009)
    block('Independent axle-clevis jaw projecting from stand',loose,D,(x,.344,.929),(.051,.136,.089),hardware,[72,74,64],.004)
block('Hardwood saddle spans the separate pulley display',loose,D,(pulX,.382,.890),(.232,.065,.061),wood,[137,94,49],.008)
# Axle is X; repeated ring profile handles actual rim transitions and groove.
def pulley(n,x0,y0,z0,pr,mat,tint):
    # Construct in local XZ annulus, then swizzle axial orientation into X.
    o=annulus(n,loose,D,(0,0),pr,mat,tint,48)
    for v in o.data.vertices:
        x,y,z=v.co;v.co=(x0+z,y0+x,z0+y)
    return o
pulley('Deep open rope groove integral to separate spool',pulX,pulY,pulZ,
       [(.014,-.029),(.062,-.029),(.065,-.022),(.056,-.017),(.047,-.004),
        (.047,.004),(.056,.017),(.065,.022),(.062,.029),(.014,.029)],ironRim,[99,95,82])
rod('Continuous axle through spool and matching stand cheeks',loose,D,(pulX-.117,pulY,pulZ),(pulX+.117,pulY,pulZ),.015,hardware,18)
for s in (-1,1):
    x=pulX+s*.115
    rod('Separate retaining bronze axle cap',loose,D,(x-.009,pulY,pulZ),(x+.009,pulY,pulZ),.023,bronze,16)
rr=.05192
cordPts=[(pulX,.205,.149),(pulX,.231,.301),(pulX,pulY-rr,.381),(pulX,pulY-rr,.694),(pulX,pulY-rr,pulZ)]
for q in range(1,25):
    t=math.pi*(1-q/24)
    cordPts.append((pulX,pulY+rr*math.cos(t),pulZ+rr*math.sin(t)))
cordPts+= [(pulX,pulY+rr,.687),(pulX,pulY+rr,.547),(pulX,.366,.457),(pulX,.371,.420)]
sweep('One genuine stationary rope passing around independent exhibit pulley',loose,D,cordPts,.0047,rope,10,fixed_axis=(1,0,0))
# Separate front end rests against this idle prop cleat; rear tail hangs beside the rack.
box('Small independent cord parking cleat on separate stand',loose,D,(pulX,.205,.143),(.068,.036,.026),bronze,.005,2)
box('Original workshop exhibit caption plate',base,B,(.22,-.596,.055),(.506,.025,.041),plate,.003,2)
etch('Generic Penang-inspired display caption',base,B,(.22,-.610,.053),'PENANG  /  KOPI WORKSHOP',.022,offWhite)
box('Studio matte shadow only excluded',studio,None,(0,0,-.027),(100,100,.053),worldPlate,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.49)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights iron rim and warm segmented brick',(-2.0,-2.7,3.3),520,2.4,(1,.91,.80))
light('Cool quiet fill shapes old small workshop',(2.4,-1.9,2.14),290,1.83,(.83,.94,1))
light('Upper reflected rim on pot and timber',(.92,1.36,2.3),270,1.48,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(2.09,-3.36,2.56);target=(.0,-.03,.41)
cd.type='ORTHO';cd.ortho_scale=2.24;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=205;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=52
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_percentage=100;S.render.resolution_x=S.render.resolution_y=512
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=93
S.view_settings.view_transform='AgX';S.view_settings.exposure=.05
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,last,loose):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/(slug+'.glb')),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,
                         export_lights=False,export_extras=False)
def still(to,pos,tgt,scale,wh):
    cam.location=pos;look(cam,tgt);cd.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=wh;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,2.24,(512,512))
if opts.review:
    S.cycles.samples=126
    still(opts.review/'real-pot-cavity-and-open-masonry.webp',(.33,-.92,1.68),(-.230,.035,.375),1.12,(640,620))
    still(opts.review/'pulleys-and-parked-rope.webp',(.48,-1.44,1.36),(.650,.300,.790),.62,(630,620))
    still(opts.review/'pot-seat-and-independent-paddles.webp',(1.1,-.81,.93),(.13,.16,.457),.95,(660,620))
