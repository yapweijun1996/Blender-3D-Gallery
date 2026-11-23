"""A static umbrella-draining station. Clean-room Blender 5.3 geometry; metres."""
import math
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

SLUG="mall-wet-umbrella-drip-station"
HERE=Path(__file__).resolve().parent
for sub in ("exports","previews"):
    (HERE/sub).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
parts={}
for label in ("01 Powder coated frame and ventilated side panels",
              "02 Long and compact umbrella guides",
              "03 Liftable drip pan and drainage",
              "04 Sculpted wet umbrellas",
              "05 Bilingual wayfinding and pictogram",
              "06 Studio only"):
    col=bpy.data.collections.new(label)
    scene.collection.children.link(col)
    parts[label[:2]]=col

def material(name,rgb,rough=.48,metal=0):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    m.diffuse_color=(*rgb,1)
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*rgb,1)
    p.inputs["Metallic"].default_value=metal
    p.inputs["Roughness"].default_value=rough
    return m

def attach(o,name,key,mat=None):
    o.name=name
    for col in list(o.users_collection):
        col.objects.unlink(o)
    parts[key].objects.link(o)
    if mat:
        o.data.materials.append(mat)
    return o

def cube(name,center,dims,mat,key,r=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    o=attach(bpy.context.object,name,key,mat)
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if r>=.008:
        m=o.modifiers.new("Folded edge bevel","BEVEL")
        m.width=r
        m.segments=2 if r>=.020 else 1
        m.harden_normals=True
        m=o.modifiers.new("Weighted face normals","WEIGHTED_NORMAL")
        m.keep_sharp=True
    return o

def cyl(name,xyz,r,h,mat,key,n=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=h,location=xyz)
    o=attach(bpy.context.object,name,key,mat)
    for p in o.data.polygons:
        p.use_smooth=len(p.vertices)==4
    return o

def mesh(name,vertices,faces,mat,key,fix=False):
    me=bpy.data.meshes.new(name)
    me.from_pydata(vertices,[],faces)
    me.update()
    if fix:
        bm=bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(me)
        bm.free()
    return attach(bpy.data.objects.new(name,me),name,key,mat)

def tube(name,xyz,r,mat,key,sides=7):
    path=[Vector(p) for p in xyz]
    v=[]
    for k,p in enumerate(path):
        tang=(path[min(k+1,len(path)-1)]-path[max(k-1,0)]).normalized()
        up=Vector((0,1,0)) if abs(tang.y)<.98 else Vector((1,0,0))
        a=tang.cross(up).normalized()
        b=tang.cross(a).normalized()
        for i in range(sides):
            t=math.tau*i/sides
            v.append(p+r*(a*math.cos(t)+b*math.sin(t)))
    f=[tuple(reversed(range(sides)))]
    for k in range(len(path)-1):
        for j in range(sides):
            i=(j+1)%sides
            f.append((k*sides+j,k*sides+i,(k+1)*sides+i,(k+1)*sides+j))
    f.append(tuple(range((len(path)-1)*sides,len(path)*sides)))
    o=mesh(name,v,f,mat,key,True)
    for p in o.data.polygons:
        p.use_smooth=len(p.vertices)==4
    return o

def ring(name,x,y,z,rr,inside,m):
    n=16
    vv=[]
    profile=((rr-.003,-.013),(rr,.007),(rr-.004,.014),
             (inside+.004,.014),(inside,.007),(inside+.004,-.013))
    for rad,h in profile:
        for i in range(n):
            a=i*math.tau/n
            vv.append((x+rad*math.cos(a),y+rad*math.sin(a),z+h))
    ff=[]
    for a in range(len(profile)):
        for j in range(n):
            b=(a+1)%len(profile)
            k=(j+1)%n
            ff.append((a*n+j,a*n+k,b*n+k,b*n+j))
    me=mesh(name,vv,ff,m,"02",True)
    for p in me.data.polygons:
        p.use_smooth=True

jungle=material("Dark laurel powder coat",(.055,.216,.16),.47,.18)
forest=material("Deep spruce welded bar",(.026,.108,.084),.54,.16)
sand=material("Light warm powder-coated vent panels",(.71,.67,.48),.62)
silver=material("Grey stainless drain surfaces",(.394,.478,.442),.42,.39)
rubber=material("Graphite end caps and handles",(.027,.04,.04),.58)
ivory=material("Warm off-white bilingual sign",(.89,.87,.73),.61)
navy=material("Petrol blue folded nylon",(.063,.20,.31),.52)
red=material("Muted terracotta folded nylon",(.55,.129,.084),.53)
sun=material("Mustard folded nylon",(.72,.438,.057),.52)
moss=material("Warm grey sage folded nylon",(.277,.39,.277),.59)
brown=material("Brown cork-look cane handle",(.295,.147,.054),.64)

# Front is Blender −Y, feet at floor. Open ventilated louvers and rear frame.
for x in (-.421,.421):
    for y in (-.226,.216):
        cube("Replaceable rubber foot",(x,y,.023),(.068,.075,.046),rubber,"01",.009)
        top=.690 if y>0 else .575
        cube("Rounded welded vertical upright",(x,y,(top+.040)/2),(.054,.056,top-.040),forest,"01",.011)
    cube("Formed light side-panel perimeter top rail",(x,-.006,.429),(.035,.406,.021),sand,"01",.009)
    cube("Formed light side-panel perimeter bottom rail",(x,-.006,.185),(.035,.408,.020),sand,"01",.007)
    for j in range(7):
        y=-.169+j*.054
        l=cube("Ventilated side-panel folded louver",(x,y,.306),(.031,.027,.231),sand,"01")
        l.rotation_euler.z=.33
    for y in (-.196,.183):
        cube("Narrow end join of the ventilated panel",(x,y,.306),(.034,.025,.253),sand,"01")
for y in (-.218,.211):
    cube("Structural lower side tie",(0,y,.090),(.830,.049,.070),forest,"01",.009)
for x in (-.409,.409):
    cube("Lower pan resting runner",(x,.001,.104),(.048,.414,.028),forest,"01",.007)
cube("Lower rear open drainage splash rail",(0,.216,.206),(.793,.038,.041),jungle,"01",.006)
cube("Upper rear collar-rail perimeter",(0,.200,.697),(.871,.057,.052),jungle,"02",.010)
cube("Upper rear row front collar-rail lip",(0,-.006,.697),(.863,.042,.045),jungle,"02",.009)
cube("Lower front collar rail structural rear lip",(0,-.050,.491),(.866,.046,.052),jungle,"02",.009)
cube("Lower front collar rail structural front lip",(0,-.210,.491),(.872,.044,.051),jungle,"02",.008)
for x in (-.418,.418):
    cube("Long and compact rack side frame tie",(x,-.115,.493),(.060,.256,.049),jungle,"02",.009)
    cube("Upper rack side frame tie",(x,.102,.696),(.060,.175,.057),jungle,"02",.008)

for n,x in enumerate((-.322,-.108,.108,.322)):
    ring("Open rounded long guide %d"%n,x,.097,.700,.090,.070,sand)
    ring("Open rounded compact guide %d"%n,x,-.132,.496,.068,.048,sand)
    for yy,z in ((.022,.699),(.176,.699),(-.071,.494),(-.193,.494)):
        cube("Welded collar hang-tab",(x,yy,z),(.052,.041,.019),silver,"02")
    ring("Slatted tip cradle %d"%n,x,-.132,.324,.057,.035,forest)
    for d in (-.020,.020):
        cube("Compact tip cradle drainage rung",(x+d,-.133,.318),(.014,.089,.017),silver,"02")
    cube("Low compact holder lateral connection",(x,-.132,.307),(.104,.027,.023),forest,"02")
cube("Compact cradle basket front spine",(0,-.176,.315),(.804,.024,.030),jungle,"02",.006)
cube("Compact cradle basket rear spine",(0,-.087,.315),(.804,.025,.027),jungle,"02",.006)

# True angled sheet surface with raised side lips, open cavity and a front pull.
tray=cube("Continuous pitched drip pan bottom",(0,-.006,.121),(.778,.418,.018),silver,"03",.008)
tray.rotation_euler.x=.040
for x in (-.390,.390):
    tray=cube("Lift-out drip pan standing side lip",(x,-.006,.143),(.015,.423,.043),silver,"03",.006)
    tray.rotation_euler.x=.040
cube("Front drip drawer end and spill edge",(0,-.219,.144),(.794,.030,.064),jungle,"03",.009)
cube("Rear drip pan high splash edge",(0,.207,.150),(.792,.023,.041),jungle,"03",.008)
for x in (-.274,-.137,0,.137,.274):
    o=cube("Raised lengthwise drain rib",(x,-.004,.136),(.012,.366,.005),jungle,"03")
    o.rotation_euler.x=.040
tube("Removable-looking drip drawer pull",
     [(-.108,-.237,.155),(-.108,-.260,.155),(-.090,-.272,.155),
      (.090,-.272,.155),(.108,-.26,.155),(.108,-.237,.155)],.010,rubber,"03",8)

# Bunched umbrella covers have real folds, contrasting bands and different handles.
def umbrella(label,x,y,lo,hi,r,tex,handle,sway=.008,phase=0):
    n=16
    profile=[(.000,.19),(.075,.36),(.310,.74),(.590,1.0),(.800,.90),(.950,.58),(1,.25)]
    vv=[]
    for z,scale in profile:
        for j in range(n):
            a=j*math.tau/n+phase
            fold=(1.0 if j%2==0 else .78)+.025*math.sin(3*a+.15)
            rr=r*scale*fold
            vv.append((x+sway*z+rr*math.cos(a),y+rr*math.sin(a),lo+z*(hi-lo)))
    ff=[tuple(reversed(range(n)))]
    for k in range(len(profile)-1):
        for j in range(n):
            p=(j+1)%n
            ff.append((k*n+j,k*n+p,(k+1)*n+p,(k+1)*n+j))
    ff.append(tuple(range((len(profile)-1)*n,len(profile)*n)))
    fabric=mesh(label+" fabric crown with folded ribs",vv,ff,tex,"04",True)
    # Keep the folded silhouette and cap edges, but let the textile gradients
    # flow around its side faces without duplicating their normal vertices.
    for pole in fabric.data.polygons:
        pole.use_smooth=len(pole.vertices)==4
    cyl(label+" grounded ferrule",(x,y,lo-.011),.011,.025,rubber,"04")
    cyl(label+" closed fabric band",(x+.60*sway,y,lo+.610*(hi-lo)),r*.99,.028,rubber,"04",16)
    cyl(label+" small band press button",(x+.60*sway,y-r*.99,lo+.609*(hi-lo)),.005,.006,silver,"04",8)
    x+=sway
    if handle=="short":
        cyl(label+" telescoping closed stem",(x,y,hi+.021),.008,.049,silver,"04")
        cyl(label+" compact grip",(x,y,hi+.069),r*.65,.060,rubber,"04",12)
        tube(label+" short carry loop",[(x+.008,y,hi+.093),(x+.05,y,hi+.081),(x+.057,y,hi+.05),(x+.043,y,hi+.038),(x+.023,y,hi+.058)],.003,rubber,"04",6)
    else:
        cyl(label+" closed shaft",(x,y,hi+.029),.009,.062,silver,"04",10)
        z0=hi+.111
        pts=[(x,y,hi+.048),(x,y,z0)]
        sign=1 if handle=="right" else -1
        for j in range(1,11):
            a=math.pi-j*math.pi/10
            pts.append((x+sign*(.044+.044*math.cos(a)),y,z0+.044*math.sin(a)))
        pts.append((x+sign*.088,y,z0-.028))
        tube(label+" cane J grip",pts,.013,(brown if handle=="right" else rubber),"04",8)

umbrella("A tall blue umbrella",-.319,.098,.152,.809,.044,navy,"right",.008,.13)
umbrella("B tall rust umbrella",-.107,.099,.152,.879,.047,red,"left",-.010,.24)
umbrella("C tall sage umbrella",.316,.096,.151,.825,.040,moss,"left",-.008,.68)
umbrella("D compact mustard umbrella",-.106,-.132,.349,.590,.044,sun,"short",-.011,.39)
umbrella("E compact blue umbrella",.319,-.132,.349,.567,.041,navy,"short",.010,.59)

# Independent bilingual placard; no brand or accessibility/compliance implication.
for x in (-.410,.410):
    cube("Raised rear sign riser",(x,.210,.861),(.051,.049,.334),forest,"05",.008)
cube("Placard backing with soft corners",(0,.204,1.047),(.899,.054,.174),jungle,"05",.024)
cube("Bilingual enamel insert",(0,.174,1.048),(.854,.018,.128),ivory,"05",.013)
cube("Narrow inset sign rule",(.067,.162,1.044),(.558,.004,.002),jungle,"05")
def text(name,value,x,z,size):
    bpy.ops.object.text_add(location=(x,.163,z),rotation=(math.pi/2,0,0))
    o=attach(bpy.context.object,name,"05",forest)
    o.data.body=value
    o.data.align_x="CENTER"
    o.data.align_y="CENTER"
    o.data.size=size
    o.data.resolution_u=2
text("Malay primary guidance","PAYUNG BASAH",.071,1.073,.045)
text("English secondary guidance","WET UMBRELLAS",.071,1.023,.030)
tube("Pictogram umbrella dome and straight edge",
     [(-.362,.161,1.052),(-.347,.161,1.072),(-.325,.161,1.082),(-.303,.161,1.072),
      (-.288,.161,1.052),(-.362,.161,1.052)],.0037,jungle,"05",6)
tube("Pictogram umbrella hook",[(-.325,.161,1.052),(-.325,.161,1.026),(-.322,.161,1.019),(-.313,.161,1.020),(-.310,.161,1.026)],.0037,jungle,"05",6)
for x,z in ((-.352,1.030),(-.337,1.020),(-.294,1.034)):
    tube("Small rain-mark in pictogram",[(x,.161,z+.008),(x-.007,.161,z-.002)],.0026,jungle,"05",5)

def aim(o,target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()
floor=material("Studio neutral clay",(.31,.32,.278),.72)
cube("Studio tiled floor plane",(0,0,-.029),(140,140,.055),floor,"06")
bpy.ops.object.camera_add(location=(1.87,-2.92,1.87))
camera=attach(bpy.context.object,"Front studio camera","06")
aim(camera,(0,-.008,.556))
camera.data.type="ORTHO"
camera.data.ortho_scale=1.56
scene.camera=camera
for n,p,power,color,size in (
    ("Warm diffused key",(1.6,-2.3,3.5),400,(1,.845,.657),2.3),
    ("Cool entrance fill",(-2.9,-1.45,2.25),270,(.76,.89,1),2.5),
    ("Sunlit rear edge",(1.4,1.7,2.7),465,(.91,1,.78),2.05),
):
    bpy.ops.object.light_add(type="AREA",location=p)
    l=attach(bpy.context.object,n,"06")
    l.data.energy=power
    l.data.color=color
    l.data.shape="DISK"
    l.data.size=size
    aim(l,(0,0,.55))
scene.world=bpy.data.worlds.new("Studio ambient")
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes["Background"]
bg.inputs[0].default_value=(.42,.50,.63,1)
bg.inputs[1].default_value=.34
scene.render.engine="CYCLES"
scene.cycles.samples=22
scene.cycles.use_denoising=True
scene.render.resolution_x=720
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX"
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(HERE/"previews"/"studio.png")
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(SLUG+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--drip-review" in sys.argv:
        camera.location=(2.15,-2.41,.97)
        aim(camera,(0,-.015,.324))
        camera.data.ortho_scale=1.20
        scene.render.filepath=str(HERE/"previews"/"drip-review.png")
        bpy.ops.render.render(write_still=True)
selected=[]
# All guides remain separately editable in the saved project. Use three
# repeated cross-sections in the GLB, one shared mesh for each guide profile.
for prefix in ("Open rounded long guide","Open rounded compact guide","Slatted tip cradle"):
    chain=sorted((o for o in parts["02"].objects if o.name.startswith(prefix)),key=lambda o:o.name)
    master=chain[0]
    selected.append(master)
    for n,dx in enumerate((.214,.430,.644),1):
        old=chain[n]
        name=old.name
        bpy.data.objects.remove(old,do_unlink=True)
        link=master.copy()
        link.name=name
        parts["02"].objects.link(link)
        link.location.x+=dx
        selected.append(link)
for key, col in parts.items():
    if key=="06":
        continue
    by=defaultdict(list)
    for ob in list(col.objects):
        if ob in selected:
            continue
        if ob.modifiers or ob.type=="FONT":
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.context.view_layer.objects.active=ob
            bpy.ops.object.convert(target="MESH")
            ob=bpy.context.view_layer.objects.active
        by[ob.data.materials[0].name].append(ob)
    for m,obs in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        active=obs[0]
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active=active
        if len(obs)>1:
            bpy.ops.object.join()
        active.name=col.name[3:]+" | "+m
        selected.append(active)
bpy.ops.object.select_all(action="DESELECT")
for o in selected:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(HERE/"exports"/(SLUG+".glb")),
    export_format="GLB",use_selection=True,export_lights=False,export_cameras=False,
    export_animations=False,export_texcoords=False)
