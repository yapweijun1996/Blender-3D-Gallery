"""Original static funicular line-sheave exhibit, not a surveyed or operating railway."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='funicular-cable-guide-roller-section'
out=a.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 shortened inclined roadbed and exhibition origin')
rail=collection('02 twin separate rail profiles and physical end faces')
roll=collection('03 three static continuous rounded cable-guide sheaves')
rope=collection('04 one original static exposed haul-rope sample')
studio=collection('05 studio only, excluded from export')
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


frame=empty('HILL_TRACK_SECTION_BED',base)
incl=empty('INCLINED_SECTION_ORIGIN',base,loc=(0,0,.306))
incl.rotation_mode='XYZ';incl.rotation_euler.x=math.radians(13)
R=empty('TWIN_RAIL_TRACK_PAIR',rail,incl)
G=empty('CENTER_LINE_SHEAVE_ASSEMBLIES',roll,incl)
C=empty('CONTINUOUS_HAUL_ROPE_LINE',rope,incl)
steel=material('Neutral dark treated rail steel','536365',.52,.46)
nickel=material('Polished slate silver rail head and axle','A6B8AE',.31,.66)
railweb=material('Warm subdued weather tint on rail webs','74645C',.52,.43)
graph=material('Iron-grey foot and support metal','37484B',.46,.43)
petr=material('Muted petrol mineral coating on forks','426C6A',.45,.35)
petrhi=material('Cool highlight over concave machined guide wheel','66918C',.37,.45)
rub=material('Dark satin lining of carved round cable groove','343C3D',.47,.17)
bronze=material('Warm ochre clipped sectional accent','B48452',.44,.43)
copper=material('Subdued warm exposed core faces','C48E60',.49,.29)
rope_light=material('Satin twisted-looking haul rope envelope','AFC1B9',.40,.58)
rope_dark=material('Deep grooves between cable strands','7B8980',.49,.42)
slate=material('Stone gray original sectional concrete heel','777D76',.72)
slateh=material('Pale cut slab exposed top','9C9F87',.67)
aggregate=material('Muted darker inset concrete surface detail','77796A',.79)
accent=material('Small neutral lettering','E9D3A3',.59)
stage=material('Mauve warm neutral editorial floor','949587',.76)

# Sloping exhibit wedge is not an actual infrastructure footprint. Lower floor
# stays level, while its clipped mineral upper section follows the track slope.
def multis(n,c,p,v,f,mats,ids):
    m=mesh(n,c,p,v,f,mats[0])
    for material in mats[1:]:m.data.materials.append(material)
    for pol,i in zip(m.data.polygons,ids):pol.material_index=i
    return m
def side_extrude(n,c,parent,shape,x0,x1,mats,faceidx=None):
    v=[(x,y,z) for x in (x0,x1) for y,z in shape];N=len(shape)
    f=[tuple(reversed(range(N))),tuple(range(N,N*2))]
    for k in range(N):
        j=(k+1)%N;f.append((k,j,j+N,k+N))
    o=multis(n,c,parent,v,f,mats,faceidx or [0]*len(f))
    o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');o.select_set(False)
    return o
bpy.context.view_layer.update()
def tracktop(y):
    return .306+(math.sin(math.radians(13))*y-.006)/math.cos(math.radians(13))
side_extrude('Short solid slope sample heel',base,frame,[
    (-.895,.028),(.875,.028),(.875,tracktop(.875)),(-.895,tracktop(-.895))
    ],-.624,.624,[slate,slateh],[0,0,0,0,1,0])
box('Clean low grayed exhibit plinth',base,frame,(0,-.006,.028),(1.315,1.867,.057),graph,.029,4)
for i in range(2):
    for s in (-1,1):
        x=s*.632
        for k in range(6):
            y=-.68+.238*k+.021*math.sin(k*2.17+s*1.3)
            z=.060+i*.060+.025*math.sin(k*1.6)
            if z<tracktop(y)-.018:
                box('Physical sparse stone cutface inset '+str((i,s,k)),base,frame,(s*.624,y,z),(.010,.070+.014*(k%3),.013),aggregate,.004,3)
side_extrude('Inset bronze line in original low cut face',base,frame,[(-.901,.042),(-.892,.042),(-.892,.057),(-.901,.057)],-.583,.583,[bronze])
# Context sleepers and fasteners remain below the uninterrupted cable route.
for i,y in enumerate((-.760,-.514,-.244,.062,.331,.592,.806)):
    box('Genuine transverse grey bearer '+str(i),base,incl,(0,y,.020),(1.132,.147,.063),slateh,.013,4)
    for s in (-1,1):
        x=s*.472
        box('Seat rail fishplate base '+str((s,i)),rail,R,(x,y,.060),(.192,.117,.030),graph,.007,3)
        for a1 in (-1,1):
            zp=.086
            box('Small angled original rail clip '+str((s,i,a1)),rail,R,(x+a1*.058,y,zp),(.045,.051,.029),bronze,.006,4)
            rod('Real seat bolt running into clip '+str((s,i,a1)),rail,R,(x+a1*.070,y,.067),(x+a1*.070,y,.101),.0125,nickel,10)
# Profile along actual inclined Y, not a painted edge. Head and lower base
# firmly integral; continuous unbroken profile follows this short vignette.
outline=[(-.078,.063),(.078,.063),(.078,.084),(.049,.101),(.031,.111),
 (.030,.303),(.046,.322),(.052,.350),(.049,.379),(.042,.395),
 (-.042,.395),(-.049,.379),(-.052,.350),(-.046,.322),(-.030,.303),
 (-.031,.111),(-.049,.101),(-.078,.084)]
def rail_profile(label,x):
    n=len(outline)
    verts=[(x+u,y,z) for y in (-.878,.878) for u,z in outline]
    faces=[tuple(range(n)),tuple(reversed(range(n,n*2)))]
    ids=[2,2]
    for i,(u,z) in enumerate(outline):
        j=(i+1)%n
        faces.append((i,i+n,j+n,j))
        ids.append(0 if min(z,outline[j][1])>=.348 else 1)
    return multis(label,rail,R,verts,faces,[nickel,steel,railweb],ids)
rail_profile('Continuous left section rail head web and foot',-.472)
rail_profile('Continuous right section rail head web and foot',.472)

# Slope-local geometry. The round steel rope runs along Y continuously.
# Constant X across the three transversal axles is terrain-independent.
ZAX=.216
Rin=.112
Rope=.0228
Chd=.00031
RopeZ=ZAX+Rin+Rope+Chd
Ys=(-.605,0,.605)
def sheave(n,parent,Y):
    # The radius sweeps from flange through a smooth positive concavity.
    # Never infer these exhibit proportions as equipment dimensions.
    notch=[(Rope*math.sin(k*math.pi/180),
            Rin+Rope*(1-math.cos(k*math.pi/180))) for k in (-69,*range(-66,67,6),69)]
    prof=[(-.066,.060),(-.064,.125),(-.053,.144),(-.041,.147),(-.034,.142),
          (-.029,.136),(-.0245,.132)]+notch+[(.0245,.132),(.029,.136),(.034,.142),(.041,.147),(.053,.144),(.064,.125),(.066,.060),(.061,.024),(-.061,.024)]
    N=56;v=[];f=[];m=[]
    for x,r in prof:
        for k in range(N):
            alpha=k*math.tau/N;v.append((x,Y+r*math.cos(alpha),ZAX+r*math.sin(alpha)))
    for j in range(len(prof)):
        h=(j+1)%len(prof); u,w=prof[j],prof[h]
        for k in range(N):
            v0=(k+1)%N
            f.append((j*N+k,j*N+v0,h*N+v0,h*N+k))
            m.append(2 if abs(u[0])<.0246 and abs(w[0])<.0246 else 1 if max(u[1],w[1])>.137 else 0)
    g=multis(n,roll,parent,v,f,[petr,petrhi,rub],m)
    for q in g.data.polygons:q.use_smooth=True
    return g
for j,Y in enumerate(Ys,1):
    side=empty('GUIDE_STATION_'+str(j),roll,G)
    sheave('CONCAVE_GUIDE_ROLLER_'+str(j),side,Y)
    box('Actual central mounting sleeper bridge '+str(j),roll,side,(0,Y,.018),(.306,.215,.052),graph,.016,4)
    for s in (-1,1):
        p=s*.110
        box('Short raised pedestal joined to bridge and fork '+str((j,s)),roll,side,(p,Y,.060),(.078,.134,.057),petr,.006,3)
        box('Seat base of installed guide fork '+str((j,s)),roll,side,(p,Y,.100),(.084,.174,.034),petr,.008,4)
        box('Sculpted upright rectangular bearing cheek '+str((j,s)),roll,side,(p,Y,.162),(.070,.118,.122),petr,.011,4)
        yz=[(Y-.063,.091),(Y+.064,.091),(Y+.049,.146),(Y+.026,.209),
            (Y-.025,.209),(Y-.043,.146)]
        side_extrude('Gently shaped gold structural gusset '+str((j,s)),roll,side,yz,p-.020,p+.020,[bronze])
        rod('Surface kingpin anticorrosion collar '+str((j,s)),roll,side,
           (s*.0675,Y,ZAX),(s*.091,Y,ZAX),.032,nickel,24)
        rod('Outer machined retaining seat '+str((j,s)),roll,side,
           (s*.121,Y,ZAX),(s*.149,Y,ZAX),.035,petrhi,24)
        rod('Original hex anti-rotation hub cap '+str((j,s)),roll,side,
           (s*.146,Y,ZAX),(s*.160,Y,ZAX),.023,nickel,12)
        for yy in (-.064,.064):
            rod('Exposed fixed bridge foot screw '+str((j,s,yy)),roll,side,
               (p,Y+yy,.111),(p,Y+yy,.126),.012,nickel,10)
    rod('One physically sustained transverse axle '+str(j),roll,side,(-.150,Y,ZAX),(.150,Y,ZAX),.0232,nickel,30)

# Ribbon-like lengthwise group-free geometry hints at a wire rope but neither
# asserts a strand specification nor uses an external material map.
v=[];f=[];m=[]
N=36;NY=132
for i in range(NY+1):
    y=-.893+1.786*i/NY
    for k in range(N):
        angle=k*math.tau/N
        ph=6*(angle+math.pi/2)+math.tau*y/.121
        r=Rope-.00070*(1-math.cos(ph))*.5
        v.append((r*math.cos(angle),y,RopeZ+r*math.sin(angle)))
for i in range(NY):
    for k in range(N):
        j=(k+1)%N
        f.append((i*N+k,(i+1)*N+k,(i+1)*N+j,i*N+j))
        c=(k+.5)*math.tau/N;y=-.893+1.786*(i+.5)/NY
        m.append(1 if math.cos(6*(c+math.pi/2)+math.tau*y/.121)<-.68 else 0)
f += [tuple(range(N)),tuple(reversed(range(N*NY,N*(NY+1))))];m += [2,2]
rr=multis('One unbroken sculpted centre haul rope',rope,C,v,f,[rope_light,rope_dark,copper],m)
for q in rr.data.polygons:q.use_smooth=(len(q.vertices)==4)
# Only neutral labels, no location or system implied.
box('Inset non-institutional exhibit label back',base,frame,(0,-.906,.043),(.441,.018,.032),graph,.009,3)
etch('Plain miniature exhibit label',base,frame,(0,-.917,.036),'FUNicular  /  LINE SHEAVE'.upper(),.015,accent)

box('Studio only flat shadow surface',studio,None,(0,0,-.027),(200,200,.052),stage,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color,aim=(0,0,.44)):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,aim)
lamp('Warm diffuse key along the centre rope',(-1.42,-2.12,2.69),365,1.95,(1,.92,.80))
lamp('Cool steel and near concavity fill',(1.56,-1.02,1.48),253,1.48,(.81,.95,1))
lamp('High warm edge over slope',(.45,1.33,2.53),235,1.42,(1,.93,.78))
world=bpy.data.worlds.new('Quiet industrial overcast daylight');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.59,.64,.60,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.48
lens=bpy.data.cameras.new('Studio camera');cam=bpy.data.objects.new('Studio camera',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=2.53
cam.location=(1.61,-2.88,2.51);look(cam,(0,0,.365))
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.10
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,rail,roll,rope):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
def still(to,pos,target,scale,res):
    cam.location=pos;look(cam,target);lens.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',(1.61,-2.88,2.51),(0,0,.365),2.46,(512,512))
if a.review:
    still(a.review/'transverse-axle-and-cable-groove.webp',(.35,-.875,1.19),(.002,-.554,.507),.60,(960,670))
    still(a.review/'continuous-centre-and-two-rails.webp',(-.74,-1.63,2.97),(0,-.01,.433),2.13,(960,680))
    still(a.review/'side-rail-pair-and-slope.webp',(2.95,-.90,1.27),(0,-.04,.387),2.38,(940,610))
