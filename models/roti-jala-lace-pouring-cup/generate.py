"""Original Malaysian roti jala utensil and no-cook lace sample display."""
import argparse
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='roti-jala-lace-pouring-cup'
out=a.output.resolve()
for d in ('exports','previews'):
    (out/d).mkdir(parents=True,exist_ok=True)
if a.review:
    a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene
S.unit_settings.system='METRIC'

def collection(n):
    c=bpy.data.collections.new(n); S.collection.children.link(c); return c

base=collection('01 presentation tray and open cradle')
tool=collection('02 editable cup wall, five bores and insulated-looking pull handle')
food=collection('03 original actual open lace crêpe meshes')
studio=collection('04 studio, not exported')
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

def eye(n,c,p,center,R,r,mat):
    x,y,z=center
    return sweep(n,c,p,[(x+R*math.cos(a*math.tau/16),y,z+R*math.sin(a*math.tau/16)) for a in range(16)],r,mat,closed=True)

def lathe(n,c,p,profile,mat,sides):
    v=[(r*math.cos(i*math.tau/sides),r*math.sin(i*math.tau/sides),z)
       for r,z in profile for i in range(sides)]
    f=[tuple(reversed(range(sides)))]
    for k in range(len(profile)-1):
        for i in range(sides):
            j=(i+1)%sides
            f.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    f.append(tuple(range(len(v)-sides,len(v))))
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

pl=material('Warm dark olive hardwood display', '615143', .68)
trim=material('Moderately brushed slate tray steel', '8A9590', .46, .44)
teal=material('Dark petrol slate tray insert', '475D56', .7)
slate=material('Dark green enamel cradle', '395F57', .44, .13)
olive=material('Dark timber grain accent', '4C4032', .72)
brass=material('Vintage brass nozzle satin', 'AF884D', .43, .54)
warm=material('Light warm brass lip', 'DBBB79', .39, .45)
amber=material('Warm aged mustard cup coating', 'D39147', .50, .23)
edge=material('Dark amber neck joins', '8C5C31', .56, .27)
handle=material('Deep brown composite grip', '583A2A', .66)
plate=material('Warm ivory glazed dish', 'D8D1B8', .39)
stripe=material('Muted sage porcelain band', '819B84', .52)
gold=material('Golden lace sample', 'DAAA54', .66)
light=material('Lighter crepe rib', 'E3B75F', .72)
dark=material('Gently toasted applique strokes', 'B8833C', .71)
label=material('Cream display lettering', 'EEE1B2', .65)
floor=material('Studio dark sage surface', '879B8F', .84)

root=empty('ASSET_RotiJalaLacePouringCup',base)
box('Low presentation board',base,root,(0,0,.018),(.751,.420,.036),pl,.019,3)
for x in (-.294,.296):
    for y in (-.154,.153):
        box('Recessed rubber support pad',base,root,(x,y,.004),(.076,.069,.008),olive,.004)
box('Inset compact demonstration tray',base,root,(0,.010,.036),(.698,.364,.016),teal,.017,3)
for y in (-.173,.193):
    box('Brushed rolled lengthwise tray edge',base,root,(0,y,.046),(.696,.015,.022),trim,.006,2)
for x in (-.345,.345):
    box('Short raised brushed metal tray edge',base,root,(x,.010,.046),(.016,.357,.022),trim,.006,2)
box('Fictional presentation plate, independent of utensil',base,root,(-.145,-.210,.020),(.248,.005,.026),slate,.002)
etch('Roti jala display title',base,root,(-.145,-.213,.015),'ROTI JALA  /  ACUAN',.0134,label)

# The cup is tilted in a nonfunctional, open viewing cradle, not held as if in use.
cup=empty('ROTI_JALA_CUP_LOCAL',tool,root,(-.204,.041,.158))
cup.rotation_mode='XYZ'
cup.rotation_euler=(0,-.413,0)
# Rigid braces flank the underside, leaving all five actual tips and the front opening visible.
bpy.context.view_layer.update()
for ys,fy in ((-1,-.021),(1,.103)):
    for xs,fx in ((-1,-.282),(1,-.131)):
        box('Cradle foot',base,root,(fx,fy,.048),(.046,.032,.008),slate,.003)
        y=ys*.047
        # Two supports per side, with the leg fixed to the actual cup cradle strap.
        points=[cup.matrix_world @ Vector((xs*.057,y,.010)),
                cup.matrix_world @ Vector((xs*.062,y,.023)),
                cup.matrix_world @ Vector((xs*.070,y,.051))]
        rod('Green angled cradle leg',base,root,(fx,fy,.049),points[0],.0084,slate,12)
        sweep('Open rubber-tipped side cradle contact',base,root,points,.0084,slate,9)
rod('Rear stabilizing open rail',base,root,(-.263,.117,.066),(-.140,.117,.066),.0075,slate)
# Repeat rolled wall with five holes, each with its own continuous tangible bore.
C=[(0,0),(.031,0),(-.031,0),(0,.031),(0,-.031)]
OUTER=36
HOLE=16
HR=.0060
OR=.066
IR=.059

def disk_loop(r,N,x=0,y=0):
    return [(x+r*math.cos(math.tau*i/N),y+r*math.sin(math.tau*i/N)) for i in range(N)]

def signed(f,xy):
    return sum(xy[i][0]*xy[j][1]-xy[j][0]*xy[i][1] for i,j in zip(f,f[1:]+f[:1]))

def cap_with_holes(orad):
    rings=[disk_loop(orad,OUTER)]+[disk_loop(HR,HOLE,*xy) for xy in C]
    initial=[xy for ring in rings for xy in ring]
    ed=[];k=0
    for ring in rings:
        n=len(ring);ed.extend((k+i,k+(i+1)%n) for i in range(n));k+=n
    points,_,faces,origin,_,_=delaunay_2d_cdt([Vector(xy) for xy in initial],ed,[],0,3e-8,True)
    assert len(points)==len(initial) and all(len(owners)==1 for owners in origin)
    order=[owners[0] for owners in origin]; tri=[]
    for f0 in faces:
        F=[order[i] for i in f0]
        x=sum(initial[i][0] for i in F)/len(F)
        y=sum(initial[i][1] for i in F)/len(F)
        if any(math.hypot(x-a,y-b)<HR*math.cos(math.pi/HOLE) for a,b in C):
            continue
        assert len(F)==3
        tri.append(F if signed(F,initial)>0 else F[::-1])
    return initial,tri

def mats(o,materials,idx):
    for m in materials[1:]:
        o.data.materials.append(m)
    for pp,k in zip(o.data.polygons,idx):
        pp.material_index=k
    return o

body=[(OR,.004),(.075,.019),(.078,.047),(.084,.105),(.086,.117),(.086,.122),(.083,.126),
      (.080,.125),(.078,.120),(.078,.112),(.075,.103),(.071,.048),(.065,.028),(IR,.014)]
V=[(x,y,z) for r,z in body for x,y in disk_loop(r,OUTER)]
F=[]; MI=[]
for k in range(len(body)-1):
    for i in range(OUTER):
        j=(i+1)%OUTER
        F.append((k*OUTER+i,k*OUTER+j,(k+1)*OUTER+j,(k+1)*OUTER+i))
        MI.append(1 if 4<=k<=8 else 0 if k<=3 else 2)
M=mesh('CUP_ROLLED_BODY',tool,cup,V,F,amber)
mats(M,[amber,warm,brass],MI)
for f in M.data.polygons:
    f.use_smooth=True

def mesh_cap(name,rad,z,flip):
    v,f=cap_with_holes(rad)
    return mesh(name,tool,cup,[(x,y,z) for x,y in v],[t[::-1] if flip else t for t in f],brass)
mesh_cap('CUP_FLOOR_TOP_FIVE_CUTS',IR,.014,False)
mesh_cap('CUP_FLOOR_UNDER_FIVE_CUTS',OR,.004,True)
for j,(x,y) in enumerate(C):
    v=[(xx,yy,z) for z in (.004,.014) for xx,yy in disk_loop(HR,HOLE,x,y)]
    fs=[(i,HOLE+i,HOLE+(i+1)%HOLE,(i+1)%HOLE) for i in range(HOLE)]
    o=mesh(f'CUP_DRILLED_THROAT_{j+1}',tool,cup,v,fs,brass)
    for f in o.data.polygons:
        f.use_smooth=True
    profile=[(.0090,.004),(.0092,-.000),(.0083,-.006),(.0067,-.021),(.0061,-.029),
             (.0045,-.029),(.0044,-.026),(.0048,-.015),(.0058,-.005),(HR,.004)]
    verts=[(xx,yy,z) for r,z in profile for xx,yy in disk_loop(r,HOLE,x,y)]
    fs=[];si=[]
    for k in range(len(profile)):
        l=(k+1)%len(profile)
        for i in range(HOLE):
            e=(i+1)%HOLE
            fs.append((k*HOLE+i,l*HOLE+i,l*HOLE+e,k*HOLE+e))
            si.append(2 if k in (1,2) else 1 if k in (4,) else 0)
    o=mesh(f'CUP_HOLLOW_NOZZLE_{j+1}',tool,cup,verts,fs,brass)
    mats(o,[brass,warm,edge],si)
    for f in o.data.polygons:
        f.use_smooth=True
# Thick fixed D-shaped side handle seated on two visible tangs and dark overgrip.
path=[(-.074,0,.103),(-.090,0,.103),(-.114,0,.100),(-.135,0,.087),(-.145,0,.069),
      (-.144,0,.054),(-.135,0,.041),(-.121,0,.037),(-.098,0,.043),(-.073,0,.052)]
sweep('Curved joined metal handle',tool,cup,path,.0077,brass,10)
sweep('Independent bowed dark grip',tool,cup,path[2:8],.0092,handle,9)
for z in (.103,.052):
    rod('Raised round handle tang fastener',tool,cup,(-.070,-.002,z),(-.086,-.002,z),.010,warm,12)

# Serving reference dish with a tiny distinct rolled foot, far from all tool outlets.
dish=empty('ROTI_JALA_SAMPLE_DISH',food,root,(.176,.011,0))
lathe('Warm cream shallow edged porcelain',food,dish,[(.060,.043),(.083,.045),(.104,.050),(.135,.058),
    (.143,.065),(.145,.071),(.143,.075),(.138,.077),(.133,.074),(.127,.068),(.115,.059),(.088,.057)],plate,44)
lathe('Separate ceramic foot on tray',food,dish,[(.055,.043),(.066,.044),(.066,.050),(.056,.052)],stripe,28)
# The net is real fibre-size geometry. Slight curves, material and radius variation avoid a wire grid.
def strand(n,pts,r,colour):
    return sweep(n,food,dish,pts,r,colour,6)
R=.119
for family in (0,1):
    for k in range(-6,7):
        shift=k*.018
        xx=math.sqrt(R*R-shift*shift)*.981
        pts=[]
        for j in range(0,15):
            x=-xx+2*xx*j/14
            y=shift+.0028*math.sin(j*.65+k*.72)+.0010*math.sin(j*.92-family)
            z=.0615+.0011*math.sin(j*.7+2*k)+.0005*family
            pts.append((x,y,z) if family==0 else (y,x,z))
        strand('Physical roti jala crossing ribbon',pts,.0034+.00045*(abs(k)%3),light if (k+family)%5==0 else gold)
for n in range(3):
    dia=math.tau*n/3
    pts=[]
    for i in range(41):
        t=math.tau*i/41
        rad=.118+.0014*math.cos(t*11+dia)+.0012*math.sin(t*5-dia)
        pts.append((rad*math.cos(t),rad*math.sin(t),.0622+n*.0009))
    sweep('Irregular circular net rim ribbon',food,dish,pts,.0031,gold if n!=1 else dark,6,closed=True)
# Optional utensil, not an active cooking setup.
sp=empty('Small retained serving utensil',food,root,(.277,-.146,.054))
sp.rotation_mode='XYZ';sp.rotation_euler.z=-.16
box('Slender brushed spoon handle',food,sp,(-.029,0,.003),(.099,.013,.006),trim,.0025,2)
bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=1)
spoon=assign(bpy.context.object,'Quiet flattened spoon end',food,sp,trim)
spoon.location=(.025,0,.003)
spoon.scale=(.024,.015,.0033)
for f in spoon.data.polygons:f.use_smooth=True

box('Studio shadow surface',studio,None,(0,0,-.025),(200,200,.048),floor,0)
def look(o,t):
    o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,(0,0,.14))
lamp('Broad soft warm food editorial key',(-.9,-1.16,1.8),142,1.36,(1,.92,.78))
lamp('White shop front reflected fill',(1.15,-.83,.8),72,1.02,(.88,.98,1))
lamp('Bright separation along rim',(.08,.78,1.72),110,1.03,(.88,.96,1))
world=bpy.data.worlds.new('Warm open daylight');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.58,.65,.64,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.45
lens=bpy.data.cameras.new('Hero studio');cam=bpy.data.objects.new('Hero studio',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=.905
cam.location=(.92,-2.32,1.31);look(cam,(-.004,.006,.124))
S.render.engine='CYCLES';S.cycles.samples=40;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512
S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.08
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (base,tool,food):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)

def still(to,pos,target,scale,res):
    cam.location=pos;look(cam,target);lens.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to);bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',(.92,-2.32,1.31),(-.004,.006,.124),.905,(512,512))
if a.review:
    still(a.review/'cup-and-five-tip-assembly.webp',(.85,-1.9,.81),(-.197,.036,.184),.403,(760,560))
    still(a.review/'lace-open-net-detail.webp',(.301,-.73,3.10),(.177,.012,.060),.322,(700,580))
    still(a.review/'cradle-and-open-mouth.webp',(-.8,.448,2.18),(-.202,.054,.220),.426,(760,580))
