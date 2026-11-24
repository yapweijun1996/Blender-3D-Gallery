"""Original static wheel-lift exhibition cutaway, not a real vehicle or operating fixture."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='roadside-wheel-lift-tow-cradle'
out=a.output.resolve()
for k in ('previews','exports'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
body=collection('01 cropped recovery-vehicle body with two cutaway stands')
lift=collection('02 fixed cutaway lift, telescoping shapes, and yoke')
grid=collection('03 paired open-bottom wheel grids')
tire=collection('04 single reference wheel seated in left grid only')
studio=collection('05 studio only, never exported')
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


base=empty('REAR_BODY_DISPLAY',body)
yoke=empty('RECOVERY_LIFT_DISPLAY',lift)
seats=empty('PAIRED_WHEEL_GRID_DISPLAY',grid)
sample=empty('REFERENCE_WHEEL',tire,loc=(-.590,-.734,.504))
coat=material('Deep petrol-blue painted sectional housing','30555C',.37,.18)
coat_l=material('Lighter rolled petrol-blue upper sheet','4F7372',.36,.20)
graph=material('Dark passivated structural steel','29343D',.52,.36)
cav=material('Deep protected recess','202828',.54,.24)
zinc=material('Cool machined axle ZINC','91A39F',.32,.64)
zinc_h=material('Bright pin highlight','E4E7D1',.29,.61)
lift_y=material('Original amber utility-finish cutaway steel','EDA93B',.42,.17)
lift_d=material('Deep ochre powdercoat inner seat blocks','A56B2F',.44,.24)
cream=material('Small neutral label and deck accent','EEE1A9',.47)
orange=material('Amber marker lens, not illuminated','EC8D44',.27)
red=material('Warm red tail lens, not illuminated','AC3E35',.28)
white=material('Pale rear lens, not illuminated','E7DBA9',.27)
rubber=material('Matte sample tread and seat lining','21282A',.69)
soft=material('Satin sidewall rubber','353A3D',.60)
rubhl=material('Fine rubber shoulder and molded ribs','444949',.58)
stage=material('Neutral warm industrial studio','888D83',.75)

# Suggest only the rear of an unbranded service body. Open cut forwards (+Y)
# and neutral display feet make the sectional presentation deliberate.
for s in (-1,1):
    x=s*.590
    box('Rear display floor foot '+str(s),body,base,(x,.520,.032),(.41,.40,.063),graph,.014,3)
    box('Rear display tall foot support '+str(s),body,base,(x,.520,.205),(.193,.214,.348),graph,.018,3)
    box('Chassis rail cropped forward '+str(s),body,base,(s*.530,.381,.390),(.154,.789,.137),graph,.018,4)
    box('Finishing face at cut rail '+str(s),body,base,(s*.530,.780,.388),(.169,.017,.132),zinc,.007,3)
    box('Side body short folded top '+str(s),body,base,(s*.764,.379,.723),(.299,.731,.112),coat,.032,5)
    box('Side-body framed rear compartment '+str(s),body,base,(s*.701,.122,.558),(.395,.237,.337),coat,.035,5)
    box('Inset panel of cropped body '+str(s),body,base,(s*.697,.007,.562),(.293,.018,.240),coat_l,.022,4)
    box('Panel inset latch pocket '+str(s),body,base,(s*.718,-.008,.581),(.091,.023,.032),cav,.011,3)
    rod('Short flush compartment latch '+str(s),body,base,(s*.750,-.022,.583),(s*.686,-.022,.583),.005,zinc,16)
    box('Dark scalloped light plinth '+str(s),body,base,(s*.786,-.023,.463),(.242,.032,.139),graph,.021,5)
    for i,m in enumerate((red,orange,white)):
        x=s*(.717+i*.069)
        box('Rear lamp lens '+str((s,i)),body,base,(x,-.043,.462),(.058,.019,.073),m,.012,4)
        for j in (-1,1):
            box('Rear lamp molded gloss rib '+str((s,i,j)),body,base,(x+.013*j,-.055,.462),(.003,.003,.050),m,.001,2)
    box('Rear lower bumper cropped wing '+str(s),body,base,(s*.623,-.001,.352),(.488,.108,.087),graph,.021,3)
    box('Small amber inset wing marker '+str(s),body,base,(s*.835,-.058,.353),(.081,.015,.043),orange,.008,3)

box('Continuous small deep-blue rear shelf',body,base,(0,.381,.721),(1.587,.743,.104),coat,.029,4)
box('Sectioned physical non-slip loading top',body,base,(0,.380,.774),(1.734,.709,.042),coat_l,.016,4)
box('Satin cut edge beneath shelf',body,base,(0,-.002,.765),(1.662,.057,.045),zinc,.010,3)
for i in range(9):
    box('Original grooved raised deck strip '+str(i),body,base,(.168*(i-4),.367,.799),(.015,.618,.009),graph,.003,3)
box('Central recessed rear tailboard on cutaway body',body,base,(0,.026,.565),(.912,.152,.284),graph,.026,4)
box('Narrow lower plate behind lift aperture',body,base,(0,.012,.452),(.630,.085,.101),coat_l,.012,4)
box('Blank warm rectangular display panel',body,base,(0,-.061,.630),(.415,.020,.116),cav,.014,3)
# Typeface is original text in Blender's built-in font, deliberately no logos.
etch('Unbranded small REAR MODULE display label',body,base,(0,-.074,.632),'REAR MODULE',.033,cream)
etch('Unbranded small WHEEL LIFT display label',body,base,(0,-.074,.607),'W H E E L   L I F T',.018,cream)
for s in (-1,1):
    for j in range(3):
        u=box('Quiet contrasting tailboard caution chevron '+str((s,j)),body,base,
              (s*(.284+j*.047),-.056,.622),(.016,.007,.091),lift_d,.004,3)
        u.rotation_euler.y=s*math.radians(32)

# Steel mechanism contains a true square-tube lip and bores and a visible
# fixed cross pivot, no pin dimensions or controls exposed as instructions.
def tube_around_y(n,c,parent,x,z,w,h,front,back,wall,mat):
    xo=w/2;zo=h/2;xi=xo-wall;zi=zo-wall
    v=[]
    for y,X,Z in ((front,xo,zo),(back,xo,zo),(back,xi,zi),(front,xi,zi)):
        v.extend((x+dx,y,z+dz) for dx,dz in ((-X,-Z),(X,-Z),(X,Z),(-X,Z)))
    faces=[]
    for i in range(4):
        j=(i+1)%4
        for q in range(4):faces.append((4*q+i,4*((q+1)%4)+i,4*((q+1)%4)+j,4*q+j))
    o=mesh(n,c,parent,v,faces,mat)
    o.select_set(True);bpy.context.view_layer.objects.active=o
    # Normals are made consistently outward across outer and internal walls.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    o.select_set(False);return o
for s in (-1,1):
    x=s*.187
    box('Hinge carrier bolt flange '+str(s),lift,yoke,(x,.044,.410),(.102,.231,.199),graph,.017,3)
    box('Rear fork external yellow cheek '+str(s),lift,yoke,(s*.139,-.111,.350),(.063,.191,.125),lift_y,.019,4)
    for z in (.373,.449):
        rod('Visible mount round stud '+str((s,z)),lift,yoke,(x,-.077,z),(x,-.063,z),.019,zinc,16)
rod('Transverse root axle',lift,yoke,(-.203,-.129,.355),(.203,-.129,.355),.037,zinc,28)
for s in (-1,1):
    rod('Transverse root outer keeper '+str(s),lift,yoke,(s*.188,-.129,.355),(s*.210,-.129,.355),.044,graph,24)
    rod('Round cap highlights root joint '+str(s),lift,yoke,(s*.205,-.129,.355),(s*.214,-.129,.355),.024,zinc_h,24)
tube_around_y('True hollow outer telescoping collar',lift,yoke,0,.287,.219,.142,-.375,-.088,.014,lift_y)
tube_around_y('Open dark reinforcing band at collar',lift,yoke,0,.287,.235,.157,-.386,-.342,.012,graph)
box('Steel sliding inner tube with visible four-sided seat',lift,yoke,(0,-.406,.287),(.180,.294,.108),zinc,.012,4)
for s in (-1,1):
    box('Inner tube horizontal wear plate '+str(s),lift,yoke,(s*.089,-.421,.288),(.008,.133,.049),graph,.002,2)
box('Fixed neck between inner tube and rotating-looking yoke',lift,yoke,(0,-.481,.283),(.257,.159,.116),lift_d,.014,4)
rod('Central yoke top-pivot head',lift,yoke,(0,-.450,.322),(0,-.450,.393),.060,zinc,28)
rod('Round machined upper yoke pin',lift,yoke,(0,-.450,.390),(0,-.450,.403),.034,zinc_h,24)
box('Strong one-piece transverse yoke',lift,yoke,(0,-.448,.268),(1.575,.113,.127),lift_y,.017,4)
for s in (-1,1):
    box('Thick stamped yoke end plug '+str(s),lift,yoke,(s*.752,-.448,.269),(.081,.125,.150),lift_d,.012,3)
    box('Dark yoke seat square collar '+str(s),lift,yoke,(s*.572,-.433,.271),(.138,.133,.149),graph,.012,4)
    rod('Round zinc locating head near yoke end '+str(s),lift,yoke,(s*.572,-.433,.342),(s*.572,-.433,.354),.027,zinc,20)

# One visible reference wheel and two paired open wheel pockets. Tire axle
# along X; each pair of crossbars follows a different physically tangent plane.
# This fit is solely of the digital sculpture, not a real support specification.
cy,cz=-.734,.504; radius=.273; st=.530; ct=math.sqrt(1-st*st)
def seat_block(n,x0,x1,side,depth,h,mat,offset=0):
    N=Vector((0,side*st,-ct)); T=Vector((0,ct,side*st))
    polar=math.atan2(-ct,side*st); wheel_pitch=math.tau/64
    support_radius=radius*math.cos(polar-round(polar/wheel_pitch)*wheel_pitch)
    C=Vector((0,cy,cz))+(support_radius+.00004+offset)*N
    pts=[tuple(C+Vector((x,0,0))+j*depth/2*T+k*h*N)
         for x in (x0,x1) for j,k in ((-1,0),(1,0),(1,1),(-1,1))]
    f=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    o=mesh(n,grid,seats,pts,[tuple(reversed(q)) for q in f],mat)
    return o
for s in (-1,1):
    cx=s*.590
    dx=.213
    for side in (-1,1):
        seat_block('Tangent rubber seat insert X%d Y%d'%(s,side),cx-dx+.021,cx+dx-.021,side,.085,.010,rubber)
        seat_block('Beneath rubber solid molded support X%d Y%d'%(s,side),cx-dx,cx+dx,side,.101,.046,lift_y,.010)
    # Continuous outboard L and smaller inboard retention side. No floor under
    # either wheel pocket; the supports are two inclined transverse ledges.
    box('Outer longitudinal wheel-grid arm '+str(s),grid,seats,(cx+s*.205,-.731,.249),(.073,.470,.078),lift_y,.013,4)
    box('Inner short groundless wheel-grid return '+str(s),grid,seats,(cx-s*.202,-.724,.244),(.068,.400,.077),lift_d,.012,4)
    box('Short outer raised L bracket cap '+str(s),grid,seats,(cx+s*.207,-.927,.300),(.075,.086,.058),lift_y,.014,4)
    box('Short inner L bracket cap '+str(s),grid,seats,(cx-s*.199,-.903,.285),(.070,.076,.038),lift_y,.011,3)
    for side in (-1,1):
        y=cy+side*.144
        for dx2 in (-.153,.153):
            rod('Original round wheel ledge outer body rivet '+str((s,side,dx2)),grid,seats,
                (cx+dx2,y,.249),(cx+dx2,y,.259),.012,zinc,16)
    box('Small dark bumper at outer grid return '+str(s),grid,seats,(cx+s*.214,-.970,.252),(.080,.023,.054),rubber,.010,3)
    box('Gold outline return tab on near rail '+str(s),grid,seats,(cx+s*.220,-.820,.287),(.022,.146,.009),lift_d,.004,3)
    # Yellow crossmember visibly connects each pocket to the forward yoke.
    box('Connection foot welded from yoke to wheel-pocket '+str(s),grid,seats,(cx,-.527,.211),(.300,.182,.060),lift_d,.015,3)

def radial_revolve(n,c,parent,prof,mat,N):
    v=[];f=[]
    for u,r in prof:
        for j in range(N):
            ang=j*math.tau/N;v.append((u,r*math.cos(ang),r*math.sin(ang)))
    for k in range(len(prof)):
        h=(k+1)%len(prof)
        for j in range(N):
            t=(j+1)%N
            f.append((k*N+j,k*N+t,h*N+t,h*N+j))
    return mesh(n,c,parent,v,f,mat)
# Keep true sample tire sidewall rounded and center contact crown; tread ribs
# are relief geometry below the centre crown so seating remains measurable.
prof=[(-.112,.174),(-.116,.192),(-.118,.220),(-.107,.247),(-.087,.262),(-.051,.271),
      (-.034,.273),(.034,.273),(.051,.271),(.087,.262),(.107,.247),(.118,.220),
      (.116,.192),(.112,.174),(.091,.166),(-.091,.166)]
to=radial_revolve('One original unbranded reference tire',tire,sample,prof,soft,64)
for f in to.data.polygons:f.use_smooth=True
radial_revolve('One actual multi-lip metal rim dish',tire,sample,
               [(-.092,.185),(-.115,.182),(-.114,.166),(-.095,.153),(-.047,.115),
                (.073,.115),(.095,.153),(.114,.167),(.114,.184),(.078,.186)],zinc,48)
rod('Opaque central reference hub cylinder',tire,sample,(-.112,0,0),(.115,0,0),.082,zinc,32)
for s in (-1,1):
    rod('Shallow center cap '+str(s),tire,sample,(s*.099,0,0),(s*.124,0,0),.054,graph,28)
    rod('Smaller high center disc '+str(s),tire,sample,(s*.121,0,0),(s*.127,0,0),.034,zinc_h,20)
    for i in range(6):
        q=i*math.tau/6
        y,z=.070*math.cos(q),.070*math.sin(q)
        rod('Six plain lug heads '+str((s,i)),tire,sample,(s*.109,y,z),(s*.128,y,z),.008,zinc_h,6)
        ob=box('Six separate sculpted rim spokes '+str((s,i)),tire,sample,(s*.089,.114*math.cos(q),.114*math.sin(q)),(.033,.084,.022),zinc_h,.008,4)
        ob.rotation_euler.x=q
treadv=[];treadf=[]
for i in range(48):
    q=i*math.tau/48
    for side in (-1,1):
        # Thin asymmetrical ribs remain below cylindrical centre-crown support.
        coords=[(.046,.270,q-.033),(.076,.263,q-.022),(.099,.251,q-.040),(.100,.252,q+.012),
                (.079,.264,q+.032),(.050,.270,q+.024)]
        start=len(treadv)
        for base_r in (0,.0018):
            treadv.extend((side*x,(r+base_r)*math.cos(t),(r+base_r)*math.sin(t)) for x,r,t in coords)
        treadf.append(tuple(start+z for z in (5,4,3,2,1,0)))
        treadf.append(tuple(start+6+z for z in range(6)))
        for j in range(6):
            k=(j+1)%6
            treadf.append((start+j,start+k,start+k+6,start+j+6))
mesh('Actual distinct dark shoulder tread reliefs',tire,sample,treadv,treadf,rubber)
for s in (-1,1):
    radial_revolve('Thin molded embossed sidewall rings '+str(s),tire,sample,
       [(s*.1175,.225),(s*.1195,.219),(s*.1180,.212),(s*.1175,.217)],rubhl,48)

box('Studio shadow floor only',studio,None,(0,0,-.028),(200,200,.054),stage,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color,aim=(0,-.18,.3)):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,aim)
lamp('Warm broad recovery-workbench studio key',(-2.5,-3.2,3.22),445,3.0,(1,.92,.84))
lamp('Cool highlight for the actual open support',(2.16,-1.80,2.82),315,2.59,(.80,.96,1))
lamp('Rim light over a rear sectional cut',(.70,1.98,2.92),275,2.2,(1,.92,.75))
world=bpy.data.worlds.new('Neutral warm daylight');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.57,.62,.60,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.49
lens=bpy.data.cameras.new('Studio optic');cam=bpy.data.objects.new('Studio optic',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=2.94
cam.location=(2.95,-3.92,3.23);look(cam,(-.02,-.08,.32))
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.10
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (body,lift,grid,tire):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
def still(to,pos,target,scale,res):
    cam.location=pos;look(cam,target);lens.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',(2.95,-3.92,3.23),(-.02,-.08,.32),2.78,(512,512))
if a.review:
    still(a.review/'two-pockets-wider-context.webp',(1.13,-2.98,4.26),(0,-.305,.352),2.32,(868,680))
    still(a.review/'wheel-contact-and-open-pocket.webp',(-1.43,-2.54,1.33),(-.13,-.691,.362),1.80,(900,660))
    still(a.review/'yoke-bore-and-pins.webp',(1.38,-1.24,1.48),(.042,-.354,.321),1.24,(860,652))
