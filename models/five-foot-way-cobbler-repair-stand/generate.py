"""Original static five-foot-way cobbler stand, not a named artifact or tool instruction."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='five-foot-way-cobbler-repair-stand'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 original short five-foot-way context and worn workbench')
last=collection('02 separately fitted cast shoe form and wooden fixed stand')
loose=collection('03 one loose shoe sole with actual tread and a parked small mallet')
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
wood=vmat('Worn oiled timber and restrained grown-in grain',.63)
lastTint=vmat('Dark browned cast iron with subtle use patina',.57,.61)
lastFace=vmat('Blued planished contact crown',.43,.68)
tileBase=material('Warm aged pavement borders','908D76',.77)
tileA=material('Muted red clay five-foot-way field','A48472',.76)
tileB=material('Faded bone old floor-tile tone','B7AD91',.77)
tileC=material('Dusty deep sage original tile contrast','57726C',.74)
mortar=material('Old recessed stone joint','686F66',.83)
wall=material('Original neutral old plaster crop','C7BF9F',.82)
iron=material('Weathered oxide-brown heavy iron','4D4E44',.62,.5)
heelIron=material('Slight sheen on forged iron shoulder','7C7765',.43,.58)
shadows=material('Dark recess around actual square foot socket','292F2C',.68,.36)
nickel=material('Small aged fastener ends','9B917C',.51,.55)
bronze=material('Original thin burnt brass label border','9F8458',.47,.47)
leather1=material('Oxblood brown shoe sole outer band','6F4734',.74)
leather2=material('Open grain cue on cut midsole boundary','B88D65',.76)
tread=material('Dark planted tread relief above leather field','303B36',.72)
recess=material('Dusty graphite sole under tread','49524A',.72)
mallet=material('Round warm auburn soft mallet head','8D6046',.63)
cap=material('Wicker dull warm handle finish','A9825D',.68)
stone=material('Pale shadow surface for studio only','C6C8B8',.85)
paint=material('Deep muted green original identification band','41675E',.68)
letter=material('Small warm cream clear exhibit type','DECCAA',.67)
R=empty('FIVE_FOOT_WAY_COBBLER_EXHIBIT',base)
T=empty('LOW_SINGAPORE_STYLE_TREAD_AND_BENCH',base,R)
M=empty('CAST_SHOE_LAST_MODULE',last,R,(-.129,-.051,0))
S0=empty('LOOSE_SHOE_FORM_SOLE',loose,R,(.181,-.065,.356))
S0.rotation_mode='XYZ';S0.rotation_euler.z=math.radians(-22)
H=empty('ROUNDED_PARKED_MALLET',loose,R,(.201,.090,.35595))
H.rotation_mode='XYZ';H.rotation_euler.z=math.radians(17)
# Short old walkway section, original arrangement not a recognizable site.
box('Shallow cropped pavement structural base',base,T,(0,0,.023),(.958,.642,.046),tileBase,.011,3)
box('Flat continuous underlying old mortar bed',base,T,(0,0,.048),(.932,.626,.014),mortar,.005,2)
palette=[tileA,tileB,tileB,tileA,tileC,tileA,tileB]
for row in range(6):
    for col in range(9):
        xx=-.415+.104*col;yy=-.259+.104*row
        c=palette[(row*3+col*2)%len(palette)] if row in (0,5) else (tileB if (row+col)%4 else tileA)
        box('Separately shaded old paving tile',base,T,(xx,yy,.056),(.101,.101,.010),c,.0016,2)
# A tiny plaster return plus two glazed tiled faces say old walkway, not shop replica.
box('Short plaster edge indicating shophouse frontage only',base,T,(-.286,.279,.132),(.326,.082,.149),wall,.009,3)
box('Muted teal old base tile line',base,T,(-.286,.222,.091),(.326,.026,.058),tileC,.005,2)
for x in (-.407,-.332,-.257,-.182):
    box('Original narrow small glazed tile along the return',base,T,(x,.205,.093),(.067,.015,.045),tileC,.004,2)
# Low wooden workbench with separate planks, open underframing and small mitered edges.
for j,y in enumerate((-.142,.0,.142)):
    colored_board('Independent worn flat workbench plank',base,T,(0,y,.336),(.764,.137,.040),wood,(108+j*7,76+j*4,54+j*3))
for x in (-.323,.323):
    for y in (-.152,.152):
        ob=colored_board('Splayed-look aged timber workbench leg',base,T,(x,y,.19075),(.068,.064,.2605),wood,(103,72,48))
        box('Low dark foot cap seated on tiles',base,T,(x,y,.064),(.072,.068,.009),iron,.004,2)
    colored_board('Independently joined side timber spreader',base,T,(x,0,.136),(.048,.346,.054),wood,(83,61,45))
for y in (-.164,.164):
    colored_board('Long wooden apron below worn bench surface',base,T,(0,y,.294),(.704,.030,.050),wood,(89,61,44))
for x in (-.309,.309):
    for y in (-.146,.147):
        rod('Old exposed wood peg turned flush',base,T,(x,y,.354),(x,y,.357),.0074,heelIron,12)
box('Small dusty green exhibit identification plate',base,T,(-.078,-.192,.303),(.242,.016,.038),paint,.004,2)
box('Refined retained metal line label lower edge',base,T,(-.078,-.201,.287),(.224,.004,.002),bronze,.001,2)
etch('Original exhibit lettering no seller',base,T,(-.078,-.201,.297),'SHOE  REPAIR',.019,letter)
# Stable bolted mount. Socket is made of real wall rings, no black fake opening.
support_x=-.095
colored_board('Sanded hardwood last mount foot block',last,M,(support_x,0,.384),(.158,.158,.056),wood,(88,61,46))
ironfoot=box('Independent cast iron footprint flange',last,M,(support_x,0,.417),(.125,.113,.015),iron,.010,3)
for dx in (-.045,.045):
    for yy in (-.035,.035):
        rod('Old square-shaped base bolt',last,M,(support_x+dx,yy,.422),(support_x+dx,yy,.430),.0075,nickel,8)
def sx(v,z):
    w=v/2
    return [(-w,-w,z),(w,-w,z),(w,w,z),(-w,w,z)]
def flare_post(n,root,x,section,mat):
    arr=[(u+x,v,z) for w,h in section for u,v,z in sx(w,h)]
    f=[(3,2,1,0)]+[(j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k) for j in range(len(section)-1) for k in range(4)]
    f.append(tuple(range(len(arr)-4,len(arr))))
    return mesh(n,last,root,arr,f,mat)
flare_post('Tapered mounted iron stem fixed into footprint flange',M,support_x,[(.074,.424),(.071,.432),(.052,.461),(.039,.483),(.037,.505)],iron)
# Hollow independent square saddle retains its open rim around the narrower stem.
rr=[]
for w,z in [(.064,.486),(.059,.498),(.056,.523),(.040,.525),(.040,.490)]:
    rr.append([(a+support_x,b,h) for a,b,h in sx(w,z)])
rrv=[v for r in rr for v in r]
ff=[]
for j in range(len(rr)):
    n=(j+1)%len(rr)
    ff.extend((j*4+k,j*4+(k+1)%4,n*4+(k+1)%4,n*4+k) for k in range(4))
saddle=mesh('True open square saddle socket and detent shoulder',last,M,rrv,ff,heelIron)
topPost=box('Continuous heel tenon visible within actual socket',last,M,(support_x,0,.518),(.036,.036,.043),shadows,.002,2)
rod('Rounded cap to held shoulder on mount side',last,M,(support_x+.021,.017,.502),(support_x+.030,.017,.502),.0074,nickel,12)
# An original shoe-shaped cast last. Hand-authored asymmetric loft with a visibly
# broad curved toe and pinched arch, not a rectangle or an unmolded foot scan.
sections=[
 (-.152,.005,.009,.539,.559),(-.145,.001,.024,.528,.569),(-.131,-.001,.034,.526,.574),
 (-.106,-.004,.035,.527,.573),(-.082,-.008,.030,.537,.570),(-.055,-.009,.028,.547,.566),
 (-.023,-.006,.033,.547,.566),(.010,.000,.044,.538,.568),(.042,.006,.049,.531,.570),
 (.074,.010,.047,.535,.571),(.103,.013,.037,.542,.573),(.126,.014,.022,.550,.573),(.136,.014,.008,.558,.570)
]
nSeg=48
tv=[];tf=[];mi=[]
for j,(cx,cy,w,bot,top) in enumerate(sections):
    cz=(bot+top)/2;h=(top-bot)/2
    for i in range(nSeg):
        theta=math.tau*i/nSeg
        ss=math.sin(theta);cc=math.cos(theta)
        zz=cz+h*(abs(ss)**.57)*(1 if ss>=0 else -1)
        yy=cy+w*(abs(cc)**.79)*(1 if cc>=0 else -1)+.004*ss*math.sin(cx*15)
        tv.append((cx,yy,zz))
    if j:
        for i in range(nSeg):
            a=(j-1)*nSeg+i;b=(j-1)*nSeg+(i+1)%nSeg
            tf.append((a,b,b+nSeg,a+nSeg))
            mi.append(1 if 4<i<21 else 0)
tf.extend([tuple(reversed(range(nSeg))),tuple(range(len(tv)-nSeg,len(tv)))]);mi.extend([0,0])
cast=multi('Sculpted closed asymmetric toe heel cast shoe last',last,M,tv,tf,[lastTint,lastFace],mi,True)
apply_color(cast,lambda q:(81+(16 if q.z>.56 else 0)+9*math.sin(29*q.x+47*q.y)+5*math.sin(172*q.y+37*q.x),76+(15 if q.z>.56 else 0)+11*math.sin(35*q.x-28*q.y),66+(11 if q.z>.56 else 0)+7*math.cos(44*q.x+38*q.y)))
# Relief sole is a separate open-air shoe shape with raised physical tread groups.
sole_outline=[(-.132,0),(-.129,-.023),(-.115,-.038),(-.090,-.041),(-.063,-.037),(-.040,-.025),(-.019,-.028),(.011,-.038),(.046,-.046),
 (.078,-.044),(.104,-.036),(.125,-.024),(.137,-.011),(.139,.007),(.132,.024),(.115,.041),(.089,.051),(.059,.054),(.033,.048),
 (.012,.040),(-.015,.032),(-.038,.029),(-.063,.034),(-.094,.037),(-.118,.031),(-.132,.019)]
def expand_ring(n,c,r,ring,z0,z1,mat):
    m=len(ring);v=[(x,y,z) for z in (z0,z1) for x,y in ring]
    fs=[tuple(reversed(range(m))),tuple(range(m,m*2))]
    fs.extend((i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m))
    o=mesh(n,c,r,v,fs,mat)
    return o
expand_ring('Full distinct shoe sole sidewall and low outsole',loose,S0,sole_outline,0,.009,leather1)
expand_ring('Separate real contrasting heel-top midsole lip',loose,S0,[(x*.984,y*.981) for x,y in sole_outline],.009,.0115,leather2)
expand_ring('Dark full continuous recessed tread field',loose,S0,[(x*.94,y*.94) for x,y in sole_outline],.0115,.014,recess)
# independent short tread panels leave verifiable physical gaps.
for j in range(8):
    x=.010+.0142*j
    w=[.027,.033,.035,.038,.039,.035,.029,.021][j]
    for s in (-1,1):
        y=s*.007
        t=[(x-.005,y),(x+.004,y+s*.002),(x+.004,y+s*w),(x-.006,y+s*(w-.004))]
        if s<0:t=list(reversed(t))
        expand_ring('Actual raised forefoot tread segment',loose,S0,t,.014,.0174,tread)
for j in range(4):
    x=-.117+j*.013
    for s in (-1,1):
        points=[(x-.004,s*.006),(x+.005,s*.007),(x+.003,s*.025),(x-.005,s*.021)]
        if s<0:points=list(reversed(points))
        expand_ring('Actual raised heel tread segment',loose,S0,points,.014,.0171,tread)
# Rounded parked leatherworking mallet with no configured use or strike action.
for xx,r0,r1 in [(-.020,.019,.024),(.0,.024,.024),(.022,.024,.018)]:
    rod('Mallet round older smooth head section',loose,H,(xx-.011,0,.025),(xx+.011,0,.025),(r0+r1)/2,mallet,20)
rod('Mallet low aged retaining center collar',loose,H,(-.008,0,.024),(.011,0,.024),.0245,cap,20)
rod('Slightly tapered timber mallet handle',loose,H,(0,.005,.024),(0,-.121,.014),.0091,cap,18)
rod('Mallet broad rounded tail supports the parked end',loose,H,(0,-.120,.010),(0,-.130,.010),.0101,mallet,16)
box('Studio matte shadow only excluded',studio,None,(0,0,-.027),(100,100,.053),stone,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.29)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights sculpted iron surface',(-1.54,-1.68,1.72),135,1.42,(1,.91,.80))
light('Cool quiet fill shapes old tiled perimeter',(1.29,-1.31,1.54),98,1.30,(.83,.94,1))
light('Upper reflected rim on cast shoe last',(.66,.95,1.65),78,.94,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(.98,-1.66,1.28);target=(.008,-.010,.260)
cd.type='ORTHO';cd.ortho_scale=1.23;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=189;S.cycles.use_denoising=False
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
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,1.23,(512,512))
if opts.review:
    S.cycles.samples=76
    still(opts.review/'shoe-last-and-mounted-socket.webp',(.79,-1.13,.73),(-.21,-.052,.480),.480,(655,604))
    still(opts.review/'actual-sole-tread-and-mallet.webp',(.81,-1.08,1.23),(.205,-.033,.372),.420,(640,610))
    still(opts.review/'footway-and-stand-reverse.webp',(-.82,.92,1.13),(-.120,.004,.272),.945,(635,594))
