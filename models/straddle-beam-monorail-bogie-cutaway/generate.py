"""Original static straddle-beam monorail bogie cutaway; fictional geometry, no fleet or engineering claims."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='straddle-beam-monorail-bogie-cutaway'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 independent retail exhibit ground')
last=collection('02 single guideway beam section')
loose=collection('03 original static saddle bogie')
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

def etch(n,c,p,o,text,size,mat):
    data=bpy.data.curves.new(n,'FONT'); data.body=text; data.align_x='CENTER';data.size=size
    ob=bpy.data.objects.new(n,data);assign(ob,n,c,p,mat);ob.location=o
    ob.rotation_euler.x=math.pi/2
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.convert(target='MESH')
    return ob


def multi(n,c,r,v,f,m,ids,smooth=False):
    o=mesh(n,c,r,v,f,m[0])
    for mat in m[1:]:o.data.materials.append(mat)
    for p,k in zip(o.data.polygons,ids):p.material_index=k;p.use_smooth=smooth and len(p.vertices)==4
    return o
slate=material('Blue graphite exhibit pedestal','263743',.48,.28)
trim=material('Silver engraved model legend','CDDADE',.42,.35)
cl=material('Cast cement, warm ash','B1ADA2',.84)
section=material('Saw-cut aggregate face','B5A995',.88)
grainA=material('Cut light mineral flecks','D0C8BC',.84)
grainB=material('Cut iron-rich mineral flecks','817971',.86)
runway=material('Top running face pressure-polished concrete','C5C5BC',.76)
guideway=material('Side guide face pressure-polished concrete','A6ACAD',.74)
lowerface=material("Lower stabilizer face polished concrete","99A2A4",.73)
saddle=material('Petrol enamel saddle fabrication','397477',.42,.26)
dark=material('Graphite joint dark steel','34424A',.49,.39)
steel=material('Cool brushed hub and fasteners','8B9BA1',.36,.58)
soft=material('Carbon tyre edge compound','242E33',.65)
rubber=material('Dark tread rubber','303B42',.73)
recess=material('Recessed moulded tread lines','1D262B',.71)
topcolor=material('Load identification ochre','D79B48',.42,.24)
sidcolor=material('Guide identification blue','78ADB4',.38,.24)
stbcolor=material('Stabilizer marker muted vermilion','C77F68',.42,.29)
studioMat=material('Studio matte','334651',.82)

ped=empty('EXHIBIT_BASE',base)
track=empty('SINGLE_STRADDLE_BEAM',last)
bogie=empty('SCHEMATIC_SADDLE_BOGIE',loose)
box('Independent exhibition plinth',base,ped,(0,0,.064),(1.64,2.69,.128),slate,.035,3)
box('Top floating silver reveal in exhibition plinth',base,ped,(0,0,.135),(1.56,2.59,.018),trim,.006,2)
box('Top exhibition inset',base,ped,(0,0,.151),(1.52,2.55,.025),slate,.012,2)
etch('Exhibit legend in stud-mounted front strip',base,ped,(0,-1.346,.056),'STRADDLE BEAM   /   BOGIE SECTION',.049,trim)
for x in (-.48,.48):
    for y in (-.91,.91):
        rod('Inset plinth cap',base,ped,(x,y,.163),(x,y,.166),.014,steel,12)

# Fictional exhibit dimensions in local coordinates, not field specifications.
# Concrete core, independently highlighted running surfaces, and exposed near section.
box('Beam concrete core',last,track,(0,0,.521),(.652,2.31,.649),cl,0)
box('Flat TOP load running surface',last,track,(0,0,.837),(.700,2.31,.026),runway,0)
for s in (-1,1):
    box(f'Bevel shoulder surface {s}',last,track,(s*.331,0,.790),(.033,2.31,.068),cl,0)
    box(f'Flat SIDE guide running surface {s}',last,track,(s*.338,0,.689),(.024,2.31,.139),guideway,0)
    box(f'Recessed middle side concrete {s}',last,track,(s*.332,0,.530),(.012,2.31,.179),cl,0)
    box(f'Flat SIDE stabilizer running surface {s}',last,track,(s*.338,0,.371),(.024,2.31,.139),lowerface,0)
    box(f'Lower concrete beam foot cheek {s}',last,track,(s*.326,0,.253),(.018,2.31,.098),cl,0)
box('Independent display beam bearer',last,track,(0,0,.182),(.722,2.344,.035),section,.004,1)
# Mottled color is authored in actual flush planar polygon patches, not floating pebbles.
import random
rng=random.Random(419)
verts=[]; faces=[]; shades=[]
for k in range(230):
    xx=rng.uniform(-.302,.302);zz=rng.uniform(.246,.801)
    n=rng.choice((3,4,5,6));rr=rng.uniform(.002,.011)
    i=len(verts)
    for q in range(n):
        a=math.tau*q/n; rv=rr*rng.uniform(.67,1.12)
        verts.append((xx+rv*math.cos(a),-1.1552,zz+rv*math.sin(a)))
    faces.append(tuple(range(i,i+n)));shades.append(rng.randrange(2))
multi('Exposed saw cut mineral grains',last,track,verts,faces,[grainA,grainB],shades)
for x in (-.196,.196):
    for z in (.287,.772):
        rod('Embedded exhibited bar end',last,track,(x,-1.1551,z),(x,-1.157,z),.012,steel,14)

def tyre(n,parent,o,axis,rad,width):
    # Concentric closed tyre loft. Cardinal points at target contact have explicit vertices.
    # Full-diameter flat band across shoulder retained; grooves indent only inboard.
    rows=[(-.50,-.054,soft),(-.495,-.026,soft),(-.411,0,rubber),
        (-.249,0,rubber),(-.218,-.008,recess),(-.167,-.008,recess),(-.136,0,rubber),
        (.136,0,rubber),(.167,-.008,recess),(.218,-.008,recess),(.249,0,rubber),
        (.411,0,rubber),(.495,-.026,soft),(.50,-.054,soft),(.50,-.084,soft),(-.50,-.084,soft)]
    if axis=='Z':
        rows=[(-.50,-.044,soft),(-.40,0,rubber),(-.08,0,rubber),(-.06,-.005,recess),
              (.07,-.005,recess),(.09,0,rubber),(.40,0,rubber),(.50,-.044,soft),(.50,-.084,soft),(-.50,-.084,soft)]
    N=36 if rad>.19 else 20
    v=[]; f=[];m=[]
    for a,dr,mt in rows:
        rr=rad+dr*(1 if rad>.19 else .56)
        for k in range(N):
            q=math.tau*k/N;ct=math.cos(q);sn=math.sin(q)
            ax=a*width;u=rr*ct;w=rr*sn
            v.append((o[0]+ax,o[1]+u,o[2]+w) if axis=='X' else (o[0]+u,o[1]+w,o[2]+ax))
    for j,(_,_,mt) in enumerate(rows):
        jj=(j+1)%len(rows)
        for k in range(N):
            kk=(k+1)%N
            f.append((j*N+k,j*N+kk,jj*N+kk,jj*N+k))
            m.append([soft,rubber,recess].index(mt))
    ob=multi(n,loose,parent,v,f,[soft,rubber,recess],m,True)
    return ob

def axle_x(n,p,y,z,a,b,r,mat,ns=16):
    return rod(n,loose,p,(a,y,z),(b,y,z),r,mat,ns)
def axle_z(n,p,x,y,a,b,r,mat,ns=16):
    return rod(n,loose,p,(x,y,a),(x,y,b),r,mat,ns)

# The two uncut transverse bridges join both side members, not cosmetic floating trim.
for y in (-.415,.415):
    p=empty(f'TOP_LOAD_AXLE_{y:+.3f}',loose,bogie)
    box(f'Saddle cross brace {y:+.3f}',loose,bogie,(0,y,1.407),(1.30,.166,.105),saddle,.020,2)
    tyre(f'TOP_LOAD_TYRE_{y:+.3f}',p,(0,y,1.085),'X',.235,.206)
    for s in (-1,1):
        axle_x(f'Wheel rim {y:+.3f}/{s}',p,y,1.085,s*.093,s*.111,.156,steel,32)
        axle_x(f'Ochre load hub {y:+.3f}/{s}',p,y,1.085,s*.112,s*.128,.118,topcolor,24)
        axle_x(f'Load inner hub {y:+.3f}/{s}',p,y,1.085,s*.127,s*.161,.066,dark,20)
        axle_x(f'Continuous load spindle toward frame {y:+.3f}/{s}',p,y,1.085,s*.147,s*.654,.041,steel,20)
        axle_x(f'Load bearing housing {y:+.3f}/{s}',p,y,1.085,s*.532,s*.626,.082,dark,20)
        for q in range(6):
            q0=q*math.tau/6
            axle_x('Wheel fastener seated',p,y+.088*math.cos(q0),1.085+.088*math.sin(q0),s*.127,s*.139,.010,steel,6)
        box(f'Load spindle visible pendant seat {y:+.3f}/{s}',loose,bogie,(s*.592,y,1.220),(.135,.185,.322),saddle,.018,2)
        axle_x(f'Exposed pendant bearing cap {y:+.3f}/{s}',p,y,1.085,s*.629,s*.677,.068,steel,24)
    # Pair of raised mount pads ends. There is no modeled carriage body or load.
    for x in (-.312,.312):
        axle_z('Cross brace upper seated mounting collar',bogie,x,y,1.451,1.496,.080,dark,20)
        axle_z('Sectioned upper suspension attachment cap',bogie,x,y,1.479,1.506,.064,steel,20)

for s in (-1,1):
    p=empty('SADDLE_SIDE_'+str(s),loose,bogie)
    box('Continuous outer saddle header',loose,p,(s*.59,0,1.310),(.135,1.989,.13),saddle,.018,2)
    box('Lower bogie outer longitudinal side sills',loose,p,(s*.593,0,.551),(.112,1.944,.123),saddle,.019,2)
    for y in (-.755,.755):
        box('Continuous side cheek leg between header and sill',loose,p,(s*.598,y,.905),(.135,.190,.907),saddle,.020,2)
        box('Leg face raiser',loose,p,(s*.665,y,.972),(.018,.132,.431),dark,.013,2)
        for z in (.795,1.124):
            axle_x('Outer leg exposed bolt',p,y,z,s*.659,s*.684,.022,steel,6)
        for i,(name,xc,z,rad,w,mark) in enumerate((
                    ('SIDE_GUIDE',.474,.689,.124,.084,sidcolor),
                    ('LOWER_STABILIZER',.442,.371,.092,.069,stbcolor))):
            tirex=s*xc
            # Separate vertical kingpin, horizontal tyre, contiguous support tab and leg.
            pp=empty(f'{name}_MOUNT_{s}_{y:+.3f}',loose,p)
            zz=z+(.100 if i==0 else .096)
            box(f'{name} hub tab seat',loose,pp,(s*(xc+.592)/2,y,zz),
                ((.592-xc)+.098,.150,.064),saddle,.011,2)
            axle_z(f'{name} exposed seated kingpin',pp,tirex,y,z-(w*.50+.017),zz+.045,.027,steel,16)
            axle_z(f'{name} retaining boss',pp,tirex,y,zz+.028,zz+.045,.047,dark,18)
            tyre(f'{name}_TYRE_{s}_{y:+.3f}',pp,(tirex,y,z),'Z',rad,w)
            axle_z(f'{name} tinted hub',pp,tirex,y,z+w*.32,z+w*.68,rad-.043,mark,24)
            axle_z(f'{name} lower back hub',pp,tirex,y,z-w*.64,z-w*.24,rad-.043,steel,24)
            axle_z(f'{name} marking screw',pp,tirex,y,z+w*.67,z+w*.81,.018,steel,8)
        # Extra fixture tabs and fasteners against the cheek; no synthetic power drive.
        box('Sill reinforcement by each roller post',loose,p,(s*.608,y,.553),(.136,.197,.117),saddle,.018,2)
        for z in (.517,.585):
            axle_x('Visible hex at roller support post',p,y,z,s*.656,s*.680,.018,steel,6)

# Legend plate on the near cross brace, not covering either contact.
box('Mounted plain exhibit tag',loose,bogie,(0,-.508,1.412),(.343,.022,.069),dark,.006,2)
etch('Private plain component legend',loose,bogie,(0,-.520,1.401),'EXHIBIT  /  SECTION',.028,trim)
box("Studio matte shadow only excluded",studio,None,(0,0,-.027),(100,100,.053),studioMat,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.79)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights steel wheels and cut concrete',(-2.75,-3.1,3.66),675,2.48,(1,.91,.80))
light('Cool quiet fill shapes model plinth',(2.9,-2.13,2.74),475,2.3,(.83,.94,1))
light('Upper reflected rim on upper steel bracket',(.91,2.3,2.75),355,1.85,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(2.48,-3.67,2.39);target=(0,-.018,.710)
cd.type='ORTHO';cd.ortho_scale=2.99;cam.location=hero;look(cam,target)
S.render.engine='CYCLES';S.cycles.samples=190;S.cycles.use_denoising=False
S.cycles.adaptive_threshold=.012;S.cycles.adaptive_min_samples=38
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
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,2.99,(512,512))
if opts.review:
    S.cycles.samples=124
    still(opts.review/'top-load-contact-and-seat.webp',(1.49,-2.30,1.75),(0,-.095,1.075),1.73,(690,585))
    still(opts.review/'side-guide-and-stabilizer-on-two-side-faces.webp',(1.81,-1.43,1.023),(.423,-.511,.566),1.28,(680,650))
    still(opts.review/'cross-sectional-opposing-tyres.webp',(.55,-3,1.41),(0,-.38,.773),1.79,(690,640))
