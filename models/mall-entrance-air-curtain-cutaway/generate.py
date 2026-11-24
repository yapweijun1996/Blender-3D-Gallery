"""Original static shopping-mall doorway air-curtain cutaway, not an HVAC design."""
import argparse,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
p.add_argument('--review',type=Path)
p.add_argument('--skip-render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
slug='mall-entrance-air-curtain-cutaway'
out=a.output.resolve()
for k in ('exports','previews'): (out/k).mkdir(parents=True,exist_ok=True)
if a.review:a.review.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene;S.unit_settings.system='METRIC'
def collection(n):
    c=bpy.data.collections.new(n);S.collection.children.link(c);return c
frame=collection('01 short cropped entrance header and museum stand')
shell=collection('02 stationary cutaway shell and genuine intake and outlet')
cage=collection('03 two stationary hollow cross-flow cages, each sculptural')
studio=collection('04 Studio camera, lights and floor only')
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


F=empty('SAMPLE_ENTRANCE_HEADER',frame)
H=empty('AIR_CURTAIN_SECTIONED_HOUSING',shell)
C=empty('PAIR_OF_STATIC_CROSS_FLOW_BLOWERS',cage)
black=material('Dark slate cutaway seat and blackened steel','283739',.44,.31)
charcoal=material('Smoked forest textured metal','354847',.44,.23)
jadem=material('Petrol green sculpted entrance metal','3F6766',.39,.22)
light=material('Champagne painted ceiling trim','B3AC87',.41,.22)
lit=material('Silvery nickel on trim edges','C5D1BD',.36,.52)
spun=material('Soft satin aluminium housing guide','93BAAE',.43,.40)
oxid=material('Amber exposed cross-flow cage metallic finish','D28C50',.31,.54)
copper=material('Sunlit oxide cup and curved fan blades','E6A366',.39,.46)
graph=material('Muted plenum interior steel','425256',.52,.24)
zinc=material('Brushed restrained nickel axle','BABE9E',.31,.59)
bronze=material('Warm metal face and copper cut-line','AF714F',.41,.44)
floor=material('Mauve-grey soft gallery background','8E9590',.74)
quiet=material('Very subtle cream exhibit type','EFE4B9',.56)

# Display feet and a cropped architectural header. The side posts do not form
# a complete door; around the left grille the profile reads as a finished unit.
for s in (-1,1):
    box('Sample stand low plated wide foot '+str(s),frame,F,(s*.651,.058,.027),(.245,.374,.054),black,.024,4)
    box('Cutaway display support leg '+str(s),frame,F,(s*.711,.095,.168),(.064,.104,.264),charcoal,.012,4)
    box('Open channel outer entrance cheek '+str(s),frame,F,(s*.715,.018,.451),(.081,.335,.328),jadem,.018,4)
    box('Fine brushed side flange '+str(s),frame,F,(s*.758,-.025,.451),(.021,.246,.307),light,.009,3)
    box('Inset display mounting heel '+str(s),frame,F,(s*.706,.099,.283),(.126,.113,.042),black,.009,3)
box('Upper cropped doorway header cap',frame,F,(0,.028,.617),(1.560,.317,.060),light,.018,4)
box('Dark teal join below laminated header cap',frame,F,(0,.037,.582),(1.519,.276,.023),jadem,.006,3)
box('Thin raised cut boundary snapshot',frame,F,(.349,-.132,.586),(.664,.010,.015),bronze,.004,3)
box('Small independent common frame at the rear',frame,F,(0,.172,.467),(1.422,.029,.282),black,.008,3)
for ix in range(8):
    x=.158*(ix-3.5)
    box('Brushed shallow backplate seam rib '+str(ix),frame,F,(x,.190,.472),(.012,.006,.229),jadem,.003,2)

# Geometry is in Blender X-width, -Y front and Z up. Seen +Z front after GLB conversion.
# Two isolated top channels preserve optical access through left slats and an
# exposed native blade cage on the right. Physical slit is open full span below.
box('Long upper intake return just beneath soffit',shell,H,(0,.006,.550),(1.371,.272,.036),jadem,.009,3)
box('Long deep green upper outer lip',shell,H,(0,-.137,.545),(1.365,.040,.046),jadem,.010,4)
box('Left outer fascia beside visible intake grille',shell,H,(-.340,-.155,.573),(.658,.022,.047),black,.009,3)
etch('Left pinned sample sign',shell,H,(-.340,-.168,.572),'AIR CURTAIN',.023,quiet)
etch('Left sample label subtitle',shell,H,(-.340,-.168,.557),'S T A T I C   S E C T I O N',.0091,quiet)
# A new extrusion with no transverse obstruction inside the downward opening.
def yzx(n,c,parent,path,x0,x1,mat):
    verts=[(x,y,z) for x in (x0,x1) for y,z in path]
    N=len(path);faces=[tuple(reversed(range(N))),tuple(range(N,2*N))]
    for i in range(N):
        k=(i+1)%N;faces.append((i,k,k+N,i+N))
    m=mesh(n,c,parent,verts,faces,mat)
    m.select_set(True);bpy.context.view_layer.objects.active=m
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    m.select_set(False);return m
# Swept guide geometry. The upper scroll wraps toward the outlet behind the
# cage; the right section cheek exposes the two contours as a dry sculpture.
back=yzx('Connected rear curved plenum and rear outlet lip',shell,H,[
    (.129,.523),(.103,.518),(.082,.493),(.085,.463),(.090,.433),(.082,.398),
    (.059,.361),(.042,.323),(.040,.274),(.050,.251),(.067,.251),(.066,.312),
    (.085,.348),(.106,.391),(.118,.420),(.136,.473),(.140,.508)],-.666,.666,graph)
front=yzx('Continuous front outlet lip with no texture stand-in',shell,H,[
    (-.152,.324),(-.124,.334),(-.091,.325),(-.060,.313),(-.049,.298),(-.043,.274),(-.049,.251),
    (-.070,.251),(-.071,.278),(-.075,.299),(-.101,.310),(-.134,.310),(-.150,.309)],-.665,.665,jadem)
yzx('Amber edge sweep follows true front nozzle cut wall',shell,H,[
    (-.072,.252),(-.049,.252),(-.049,.246),(-.069,.245)],-.661,.661,bronze)
yzx('Polished rear nozzle boundary edge',shell,H,[(.046,.254),(.067,.254),(.064,.247),(.045,.247)],-.661,.661,lit)
for s in (-1,1):
    x=s*.668
    box('Stationary end border only at outlet extent '+str(s),shell,H,(x,.006,.268),(.028,.147,.045),black,.009,4)

# Primary front grille is actually open at every slat gap. The exposed
# right-hand cage has its entrance face deliberately removed on this display.
for s,x in enumerate((-.656,-.024),1):
    box('Vertical brushed grille end shoe '+str(s),shell,H,(x,-.139,.426),(.031,.047,.214),light,.007,3)
for j in range(11):
    z=.335+j*.0184
    bar=box('Genuinely separated front intake slat '+str(j),shell,H,(-.34,-.143,z),(.608,.038,.0080),spun,.0037,3)
    bar.rotation_euler.x=math.radians(14)
box('Subtle intake black perimeter ledge',shell,H,(-.343,-.146,.322),(.658,.035,.013),charcoal,.005,3)
box('Original amber edge of open cutaway face',shell,H,(.014,-.144,.442),(.022,.052,.202),bronze,.005,3)
box('Exposed tall cross-bearing gallery face',shell,H,(.656,-.126,.451),(.047,.099,.235),light,.011,4)
box('Open charcoal top return above revealed fan',shell,H,(.340,-.040,.535),(.648,.205,.024),graph,.007,3)
box('Minimal small annotation on header underside',shell,H,(.340,-.149,.570),(.445,.014,.033),graph,.005,3)
etch('Second original section identification',shell,H,(.340,-.158,.564),'CROSS-FLOW SECTION',.016,quiet)
for z in (.377,.505):
    for x in (-.666,.659):
        rod('Visible upper brushed mount retaining cap',shell,H,(x,-.163,z),(x,-.154,z),.009,zinc,16)

# Shape of one blower: independent rounded vane cross sections and real bored
# annular end/rib rings, joined by one centered shaft. No simulation or clips.
def ring(n,parent,x0,x1,R,r,mat,seg=52):
    v=[]
    for x,r0 in ((x0,R),(x1,R),(x1,r),(x0,r)):
        v.extend((x,r0*math.cos(i*math.tau/seg),r0*math.sin(i*math.tau/seg)) for i in range(seg))
    f=[]
    for i in range(seg):
        k=(i+1)%seg
        for j in range(4):
            h=(j+1)%4
            f.append((j*seg+i,j*seg+k,h*seg+k,h*seg+i))
    m=mesh(n,cage,parent,v,f,mat)
    for p in m.data.polygons:p.use_smooth=p.index%4 in (0,2)
    return m
def union_vanes(parent,side):
    v=[];faces=[]
    # This coarsened 22-blade shape is intentional and original, not an impeller specification.
    profile=[(.075,-.047),(.080,-.037),(.084,-.016),(.084,.010),(.082,.031),(.078,.037),(.074,.018),(.072,-.002)]
    for i in range(22):
        phi=math.tau*i/22
        loop=[(r*math.cos(phi+b),r*math.sin(phi+b)) for r,b in profile]
        N=len(loop);s0=len(v)
        for x in (-.273,.273):
            v.extend((x,y,z) for y,z in loop)
        faces.extend([tuple(s0+n for n in reversed(range(N))),tuple(s0+n for n in range(N,2*N))])
        faces.extend((s0+i0,s0+(i0+1)%N,s0+N+(i0+1)%N,s0+N+i0) for i0 in range(N))
    ob=mesh('Actual separate curved blade surfaces '+side,cage,parent,v,faces,copper)
    ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)
    for f in ob.data.polygons:
        f.use_smooth=False
for side,x in (('LEFT',-.336),('RIGHT',.336)):
    R=empty('OPEN_BLOWER_CAGE_'+side,cage,C,loc=(x,-.018,.425))
    union_vanes(R,side)
    for a0,a1,n,r,col in [
       (-.284,-.272,'Captured outer annular end ring',.085,oxid),
       (.272,.284,'Matching true bored sleeve end ring',.085,oxid),
       (0,.010,'Sparse center annular support band',.084,zinc)]:
        ring(n+' '+side,R,a0,a1,r,.073,col)
    rod('Light straight original stationary axle '+side,cage,R,(-.308,0,0),(.309,0,0),.008,zinc,24)
    for s in (-1,1):
        r0=s*.279
        q=r0+s*.010
        rod('Static keyed fan hub '+side+str(s),cage,R,(r0,0,0),(q,0,0),.026,graph,22)
        for i in range(5):
            t=i*math.tau/5+.42
            rod('Narrow real connecting spoke near annular end '+side+str((s,i)),cage,R,(r0,.018*math.cos(t),.018*math.sin(t)),
                (r0,.079*math.cos(t),.079*math.sin(t)),.0046,oxid,10)
# Bearing carrier faces remain separate and are joined to the displayed shaft.
for i,x in enumerate((-.638,-.034,.034,.638)):
    box('Inboard or outboard stationary bearing block '+str(i),shell,H,(x,.001,.427),(.028,.088,.105),black,.009,3)
    rod('Visible brushed bearing collar cap '+str(i),shell,H,(x-.013,-.018,.425),(x+.013,-.018,.425),.018,zinc,20)

box('Only Studio neutral shadow floor',studio,None,(0,0,-.027),(200,200,.052),floor,0)
def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
def lamp(n,c,power,size,color,aim=(0,0,.42)):
    m=bpy.data.lights.new(n,'AREA');m.energy=power;m.size=size;m.shape='DISK';m.color=color
    o=bpy.data.objects.new(n,m);studio.objects.link(o);o.location=c;look(o,aim)
lamp('Large soft warm front key',(-1.5,-2.6,2.44),235,2.1,(1,.92,.81))
lamp('Cool open section edge fill',(1.58,-1.63,1.58),180,1.68,(.81,.95,1))
lamp('Rim to differentiate two drum blades',(.83,1.11,1.78),145,1.35,(1,.93,.78))
lamp('Soft nozzle underside searchlight',(.33,-.83,.31),33,.80,(.78,.93,1),(.06,0,.27))
world=bpy.data.worlds.new('Neutral Mall diffuse surroundings');world.use_nodes=True;S.world=world
world.node_tree.nodes['Background'].inputs[0].default_value=(.57,.62,.60,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.42
lens=bpy.data.cameras.new('Studio optics');cam=bpy.data.objects.new('Studio optics',lens);studio.objects.link(cam)
S.camera=cam;lens.type='ORTHO';lens.ortho_scale=1.84
cam.location=(1.00,-2.90,1.37);look(cam,(0,.016,.331))
S.render.engine='CYCLES';S.cycles.samples=48;S.cycles.use_denoising=sys.platform=='darwin'
S.render.threads_mode='FIXED';S.render.threads=5
S.render.resolution_x=S.render.resolution_y=512;S.render.resolution_percentage=100
S.render.image_settings.file_format='WEBP';S.render.image_settings.quality=92
S.view_settings.view_transform='AgX';S.view_settings.exposure=.11
S.render.filepath='//previews/studio.webp'
bpy.ops.object.select_all(action='DESELECT');bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/(slug+'.blend')),compress=True)
for c in (frame,shell,cage):
    for o in c.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'exports'/f'{slug}.glb'),export_format='GLB',use_selection=True,
                         export_texcoords=False,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
def still(to,pos,target,scale,res):
    cam.location=pos;look(cam,target);lens.ortho_scale=scale
    S.render.resolution_x,S.render.resolution_y=res;S.render.filepath=str(to)
    bpy.ops.render.render(write_still=True)
if not a.skip_render:
    still(out/'previews/studio.webp',(1.00,-2.90,1.37),(0,.016,.331),1.84,(512,512))
if a.review:
    still(a.review/'open-section-and-hollow-cage.webp',(.87,-1.43,.62),(.319,-.087,.436),.755,(930,640))
    still(a.review/'real-intake-and-cages.webp',(-.63,-2.20,.79),(-.08,-.079,.451),1.58,(960,620))
    still(a.review/'open-outlet-and-two-metal-lips.webp',(.78,-1.33,.155),(.079,-.030,.289),1.41,(960,600))
