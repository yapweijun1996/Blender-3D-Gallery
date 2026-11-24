"""Original static Singapore provision shop pulley-tin exhibit; no financial simulation."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
opts=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='provision-shop-pulley-tin-display'
out=opts.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if opts.review:opts.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
base=collection('01 independent retail exhibit ground')
last=collection('02 display arm, fixed pulley and continuous cord')
loose=collection('03 two suspended open tin assemblies')
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
pine=material('Oiled sectioned shop timber','78513C',.66)
grain=material('Long quiet end-grain lines','896149',.70)
slate=material('Graphite museum support and plinth','283740',.55,.28)
strip=material('Satin exhibit engraving','D1CFBD',.47,.2)
metal=material('Pewter bright worn tin roll','9EA6A0',.44,.50)
inside=material('Soft contrasting uncoated tin interior','B1AB97',.57,.40)
dark=material('Oxidized black steel','354141',.53,.50)
shine=material('Rubbed guide groove','7C8580',.42,.58)
amber=material('Stove red old enamel','96594D',.56,.20)
blue=material('Washed slate teal old enamel','527A77',.54,.20)
ribA=material('Paler old red enamel roll','AD735B',.55,.28)
ribB=material('Paler teal enamel roll','678E85',.55,.28)
cotton=material('Warm visible cotton cord','D6B899',.82)
cotton2=material('Twisted cord lighter helix','DECAA9',.79)
capmat=material('Worn bronze plain eyelet','927760',.50,.52)
studioMat=material('Studio matte','384851',.82)

def sweep(name,c,p,coords,r,mat,sides=8):
    pts=[Vector(i) for i in coords];v=[];f=[]
    for j,o in enumerate(pts):
        t=(pts[min(j+1,len(pts)-1)]-pts[max(j-1,0)]).normalized()
        u=t.cross(Vector((0,1,0))).normalized()
        if not u.length:u=t.cross(Vector((1,0,0))).normalized()
        w=t.cross(u)
        for i in range(sides):
            a=math.tau*i/sides
            v.append(o+r*(u*math.cos(a)+w*math.sin(a)))
        if j:
            for i in range(sides):
                k=(i+1)%sides
                f.append(((j-1)*sides+i,(j-1)*sides+k,j*sides+k,j*sides+i))
    f.extend([tuple(reversed(range(sides))),tuple(range(len(v)-sides,len(v)))])
    o=mesh(name,c,p,v,f,mat)
    for f0 in o.data.polygons:f0.use_smooth=len(f0.vertices)==4
    return o

def spin_loft(name,c,p,loc,axial_axis,profile,mats,count=40,norm=True,closed=False,sealed=False):
    v=[];f=[];iidx=[]
    for rr,zz,m in profile:
        for j in range(count):
            a=math.tau*j/count
            x=rr*math.cos(a);y=rr*math.sin(a)
            v.append((loc[0]+x,loc[1]+y,loc[2]+zz) if axial_axis=='Z' else (loc[0]+x,loc[1]+zz,loc[2]+y))
    for j,(_,_,m) in enumerate(profile if closed else profile[:-1]):
        k=(j+1)%len(profile)
        for i in range(count):
            n=(i+1)%count
            q=(j*count+i,j*count+n,k*count+n,k*count+i)
            if (axial_axis=='Y')==norm:q=q[::-1]
            f.append(q);iidx.append(m)
    if sealed:
        assert axial_axis=='Z' and norm and not closed
        for j,sig in ((0,-1),(len(profile)-1,1)):
            ci=len(v);v.append((loc[0],loc[1],loc[2]+profile[j][1]))
            for k in range(count):
                a=j*count+k;b=j*count+(k+1)%count
                f.append((ci,b,a) if sig<0 else (ci,a,b));iidx.append(profile[j][2])
    return multi(name,c,p,v,f,mats,iidx,True)

ped=empty('ABSTRACT_MUSEUM_PLINTH',base)
beam=empty('OVERHEAD_TIMBER_AND_ONE_AUTHORED_PULLEY',last)
vess=empty('PAIR_OPEN_EMPTY_PROVISION_TINS',loose)
box('Separately styled exhibition riser',base,ped,(0,0,.042),(1.09,.84,.084),slate,.026,3)
box('Silver edge of exhibition riser',base,ped,(0,0,.085),(1.04,.79,.008),strip,.004,2)
box('Quiet exhibition top field',base,ped,(0,0,.097),(1.01,.756,.022),slate,.010,3)
etch('Original display label',base,ped,(0,-.421,.026),'PROVISION SHOP   /   PULLEY TINS',.031,strip)
# Distinct present-day support is off the artisan object, behind its motion plane.
box('Independent museum steel upright',base,ped,(.399,.305,.780),(.061,.061,1.348),slate,.008,2)
box('Visible upright plated floor shoe',base,ped,(.399,.305,.114),(.150,.115,.026),slate,.007,2)
for x in (.35,.448):
    for y in (.273,.337):
        rod('Exhibit support seated floor bolt',base,ped,(x,y,.123),(x,y,.136),.010,metal,6)
box('Independent exhibit back crossbar',base,ped,(.005,.305,1.436),(.852,.063,.072),slate,.009,2)
for x in (-.249,.240):
    box('Small visible reversible support from stand to wood',base,ped,(x,.182,1.424),(.066,.240,.063),slate,.009,2)
    rod('Reversible timber support head',base,ped,(x,.079,1.412),(x,.079,1.461),.013,metal,12)
box('Cropped overhead old timber',last,beam,(0,0,1.438),(.871,.190,.108),pine,.010,2)
# Small toned grain ribbons are physically flush on the warm timbers.
import random
R=random.Random(569)
for side in (-1,1):
    v=[];f=[]
    for i in range(24):
        z=1.402+i*.00293; a=R.uniform(-.422,.21);e=min(.425,a+R.uniform(.14,.43))
        off=R.uniform(.0006,.00126);j=len(v)
        v.extend([(a,side*.0952,z),((a+e)/2,side*.0952,z+off),(e,side*.0952,z+off*.67),
               ((a+e)/2,side*.0952,z+off+.00036)])
        f.append((j,j+1,j+2,j+3) if side<0 else (j+3,j+2,j+1,j))
    mesh('Timber tonal grain face '+str(side),last,beam,v,f,grain)

# One fixed grooved pulley; stationary rope path rises, follows its upper arc,
# and descends to the opposing bail. Neutral styling is not a historical replica.
RIM=.178; AXZ=1.152; PLANE=-.012
CEN=(0,PLANE,AXZ)
for y in (PLANE-.064,PLANE+.064):
    box('Actual mounting cheek',last,beam,(0,y,1.280),(.118,.024,.309),dark,.011,2)
    box('Visible bracket pad seated in timber',last,beam,(0,y,1.393),(.163,.052,.033),dark,.006,2)
    for x in (-.054,.054):
        rod('Bracket screw into timber',last,beam,(x,y,1.373),(x,y,1.407),.010,metal,6)
rod('Continuous pulley shaft through both cheeks',last,beam,(0,PLANE-.089,AXZ),(0,PLANE+.089,AXZ),.022,metal,18)
for s in (-1,1):
    rod('Axle end cap seated',last,beam,(0,PLANE+s*.074,AXZ),(0,PLANE+s*.086,AXZ),.034,capmat,12)
spin_loft('Single sheave with real recessed cord groove',last,beam,CEN,'Y',
          [(.020,-.033,0),(.165,-.033,0),(.184,-.028,0),(.190,-.019,0),(.186,-.012,0),
           (.177,-.007,1),(.171,-.0037,1),(.171,.0037,1),(.177,.007,1),(.186,.012,0),(.190,.019,0),
           (.184,.028,0),(.165,.033,0),(.020,.033,0)],
          [dark,shine],48,closed=True)
# A ring of small plain fastener accents, geometrically flush to the wheel.
for a in [math.tau*i/8 for i in range(8)]:
    for s in (-1,1):
        x=.132*math.cos(a);z=AXZ+.132*math.sin(a)
        rod('Plain wheel plate cap',last,beam,(x,PLANE+s*.0326,z),(x,PLANE+s*.0335,z),.009,capmat,8)

# Actual closed-path bail ear has an open axial hole; its overlap with the outside
# of the vessel seals the manufacturing seam but never enters the interior.
def ear(name,c,p,cx,z):
    return spin_loft(name,c,p,(cx,PLANE,z),'Y',
       [(.010,-.012,0),(.025,-.012,0),(.028,-.008,0),(.028,.008,0),(.025,.012,0),(.010,.012,0)],
       [capmat],28,closed=True)
ropeends={}
for sign,z,fill,rib in [(-1,.720,blue,ribB),(1,.430,amber,ribA)]:
    x=sign*RIM
    root=empty(('HIGH' if sign<0 else 'LOW')+'_EMPTY_TIN',loose,vess)
    # Shallow formed bottom radius, open actual side/bottom shell. External
    # circumferential rolls break the cylinder with old plain enamel coloring.
    prof=[(.001,.001,1),(.094,.001,1),(.110,.003,1),(.117,.010,1),(.118,.016,1),
          (.115,.018,0),(.113,.034,0),(.113,.055,0),(.115,.058,2),(.115,.063,2),
          (.113,.066,0),(.113,.124,0),(.115,.127,2),(.115,.131,2),(.113,.136,0),
          (.113,.172,0),(.115,.174,2),(.118,.180,1),(.120,.186,1),(.118,.193,1),
          (.111,.194,1),(.108,.189,1),(.1065,.180,3),(.1065,.020,3),(.100,.012,3),(.001,.012,3)]
    tin=spin_loft('Bored empty rolled enamel tub '+str(sign),loose,root,(x,PLANE,z),'Z',prof,[fill,metal,rib,inside],48,sealed=True)
    for dd in (-1,1):
        ear('True bored eye secured outside tin '+str(dd),loose,root,x+dd*.137,z+.160)
        rod('Mated ear shelf rivet',loose,root,(x+dd*.111,PLANE-.007,z+.143),(x+dd*.124,PLANE-.007,z+.143),.006,metal,10)
    # Bail has a real cut-through ear attachment at both ends and forms a clean
    # 3D arch from the seated hooks on the forward side.
    k=.137
    arch=[(x-k,PLANE-.016,z+.160),(x-k,PLANE-.024,z+.160),(x-k-.014,PLANE-.024,z+.168),
          (x-k-.014,PLANE,z+.175),(x-k,PLANE,z+.186)]
    def bridge(t):
        return (x-k*math.cos(t),PLANE,z+.186+.109*math.sin(t))
    arch+= [bridge(q*math.pi/27) for q in range(1,28)]
    arch.extend([(x+k+.014,PLANE,z+.175),(x+k+.014,PLANE-.024,z+.168),
            (x+k,PLANE-.024,z+.160),(x+k,PLANE-.016,z+.160)])
    arch=[(x-k,PLANE+.010,z+.160)]+arch+[(x+k,PLANE+.010,z+.160)]
    sweep('Continuous ear-to-ear formed bail '+str(sign),loose,root,arch,.0048,metal,9)
    ropeends[sign]=(x,PLANE,z+.295)
    # Auditable eye connection: compact visible wrap at bail crown and matching
    # central thread segment. The entire artifact represents no storage use.
    wrap=[]
    for i in range(37):
        t=math.tau*i/36
        wrap.append((x+.00450*math.sin(4*t),PLANE+.0105*math.cos(t),z+.302+.0105*math.sin(t)))
    sweep('Seated cord lashing at bail crown '+str(sign),loose,root,wrap,.0040,cotton2,7)
# Warm off-white illumination of a real continuous representative cotton line.
path=[ropeends[-1],(-RIM,PLANE,AXZ)]
path.extend((RIM*math.cos(q*math.pi/48),PLANE,AXZ+RIM*math.sin(q*math.pi/48)) for q in range(47,-1,-1))
path.append(ropeends[1])
sweep('Single continuous cord over groove between vessels',last,beam,path,.0069,cotton,10)
box("Studio matte shadow only excluded",studio,None,(0,0,-.027),(100,100,.053),studioMat,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,where,w,sz,col,aim=(0,0,.79)):
    l=bpy.data.lights.new(n,'AREA');l.energy=w;l.size=sz;l.shape='DISK';l.color=col
    o=bpy.data.objects.new(n,l);studio.objects.link(o);o.location=where;look(o,aim)
light('Warm key highlights steel wheels and cut concrete',(-2.75,-3.1,3.66),510,2.35,(1,.91,.80))
light('Cool quiet fill shapes model plinth',(2.9,-2.13,2.74),360,2.0,(.83,.94,1))
light('Upper reflected rim on upper steel bracket',(.91,2.3,2.75),285,1.70,(1,.92,.78))
world=bpy.data.worlds.new('Warm natural exhibit fill');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.54,.55,.52,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.38
cd=bpy.data.cameras.new('Editorial cutaway camera');cam=bpy.data.objects.new('Editorial cutaway camera',cd);studio.objects.link(cam);S.camera=cam
hero=(1.45,-2.45,1.84);target=(0,.011,.766)
cd.type='ORTHO';cd.ortho_scale=1.77;cam.location=hero;look(cam,target)
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
if not opts.skip_render:still(out/'previews/studio.webp',hero,target,1.77,(512,512))

if opts.review:
    S.cycles.samples=116
    still(opts.review/'bearing-visible-rope-over-real-groove.webp',(1.04,-1.67,1.83),(0,PLANE,1.206),.73,(690,620))
    still(opts.review/'high-tin-open-rim-and-bail-close.webp',(.58,-1.24,1.36),(-.17,-.02,.944),.60,(690,630))
    still(opts.review/'low-tin-opposed-bail-through-eyes.webp',(-.63,-1.20,1.00),(.156,-.02,.606),.57,(690,630))
