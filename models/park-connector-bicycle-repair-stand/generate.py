import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
for sub in ("exports", "previews"):
    (ROOT / sub).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
parts = {}
for key, name in {
    "base":"01 Shared pavement footprint and feet",
    "support":"02 Padded bicycle support arms",
    "tools":"03 Four captive tools and tethers",
    "pump":"04 Hand pump with dial and hose",
    "sign":"05 Generic pictogram and faceplate",
    "studio":"06 Studio only",
}.items():
    c=bpy.data.collections.new(name)
    scene.collection.children.link(c)
    parts[key]=c


def material(name, color, rough=.45, metal=0, glow=0, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, alpha)
    s = m.node_tree.nodes.get("Principled BSDF")
    s.inputs["Base Color"].default_value = (*color, 1)
    s.inputs["Metallic"].default_value = metal
    s.inputs["Roughness"].default_value = rough
    s.inputs["Alpha"].default_value = alpha
    s.inputs["Emission Color"].default_value = (*color, 1)
    s.inputs["Emission Strength"].default_value = glow
    if alpha < 1:
        m.surface_render_method = "BLENDED"
    return m


def attach(o, name, group, mat=None):
    o.name = name
    for coll in list(o.users_collection):
        coll.objects.unlink(o)
    parts[group].objects.link(o)
    if mat:
        o.data.materials.append(mat)
    return o


def cube(name, pos, size, mat, group="case", radius=.008):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    o = attach(bpy.context.object,name,group,mat)
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if radius > .006:
        bevel = o.modifiers.new("Powder-coated edge radius","BEVEL")
        bevel.width = radius
        bevel.segments = 2 if radius >= .025 else 1
        bevel.harden_normals = True
        normal = o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL")
        normal.keep_sharp = True
    return o


def cylinder(name,pos,radius,depth,mat,group,side=False,n=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=radius,depth=depth,location=pos)
    o = attach(bpy.context.object,name,group,mat)
    if side:
        o.rotation_euler.x = math.pi/2
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices)==4
    return o


def profile(name, points, left, thickness, mat, group, radius=.006):
    """Extrude a CCW X,Z polygon along Y (cabinet panels and signs)."""
    n=len(points)
    verts=[(x,y,z) for y in (left,left+thickness) for x,z in points]
    faces=[tuple(range(n)),tuple(reversed(range(n,n*2)))]
    faces.extend((i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh)
    parts[group].objects.link(o);o.data.materials.append(mat)
    if radius:
        bevel=o.modifiers.new("Soft molded edge","BEVEL")
        bevel.width=radius;bevel.segments=3;bevel.harden_normals=True
        o.modifiers.new("Weighted facets","WEIGHTED_NORMAL")
    return o




green=material("Weatherproof deep green enamel",(.057,.239,.175),.48,.2)
sage=material("Sage powder-coated cover plate",(.24,.40,.29),.47,.1)
chalk=material("Ivory placard and gauge enamel",(.86,.81,.63),.53)
coal=material("Textured rubber and shadow",(.024,.041,.049),.70)
iron=material("Asphalt dark mounting plates",(.055,.075,.081),.66,.23)
orange=material("Signal orange rubber caps",(.83,.254,.050),.52)
silver=material("Brushed stainless tooling",(.53,.57,.58),.34,.63)
dust=material("Cool granite footprint",(.28,.31,.29),.80)
lighter=material("Quartz inlaid pad perimeter",(.40,.43,.38),.72)
amber=material("Readable tether insulating sleeve",(.60,.235,.082),.61)
red=material("Rust-orange gauge pointer",(.83,.123,.060),.48)
glass=material("Dial translucent protective lens",(.76,.92,.98),.17,0,0,.075)


def mesh_object(name,verts,faces,mat,group,soft=False):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);parts[group].objects.link(o);o.data.materials.append(mat)
    if soft:
        for p in mesh.polygons:p.use_smooth=True
    return o


def beam(name,a,b,w,mat,group,radius=.008):
    p,q=Vector(a),Vector(b);d=q-p
    o=cube(name,(p+q)*.5,(w,w,d.length+.002),mat,group,radius)
    o.rotation_mode="QUATERNION";o.rotation_quaternion=d.to_track_quat("Z","Y")
    return o


def tube(name,points,r,mat,group,sides=8):
    points=[Vector(k) for k in points];n=len(points)
    verts=[];faces=[]
    for i,p in enumerate(points):
        t=(points[i+1] if i<n-1 else p)-(points[i-1] if i else p);t.normalize()
        u=Vector((1,0,0)) if abs(t.x)<.93 else Vector((0,0,1))
        u=(u-t*u.dot(t)).normalized();v=t.cross(u)
        for j in range(sides):
            k=j*math.tau/sides
            verts.append(tuple(p+r*(u*math.cos(k)+v*math.sin(k))))
    for i in range(n-1):
        for j in range(sides):
            k=(j+1)%sides
            faces.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
    faces.extend((tuple(reversed(range(sides))),tuple(range((n-1)*sides,n*sides))))
    return mesh_object(name,verts,faces,mat,group,True)


def rod(name,a,b,r,mat,group,n=12):
    p,q=Vector(a),Vector(b);d=q-p
    o=cylinder(name,(p+q)*.5,r,d.length,mat,group,n=n)
    o.rotation_euler=d.to_track_quat("Z","Y").to_euler()
    return o


def cycle_ring(name,x,y,z,r,t,mat,group):
    q=lambda i:(x+r*math.cos(i*math.tau/24),y,z+r*math.sin(i*math.tau/24))
    tube(name,[q(i) for i in range(24)]+[q(0)],t,mat,group,6)


def label(name,body,pos,size,mat):
    bpy.ops.object.text_add(location=pos,rotation=(math.pi/2,0,0))
    o=attach(bpy.context.object,name,"sign",mat)
    o.data.body=body;o.data.align_x="CENTER";o.data.align_y="CENTER";o.data.size=size
    o.data.resolution_u=2;o.data.space_character=1.02


# A compact ground pad with flush mounts, not a parking rack or reported location.
cube("Chamfered reusable granite footprint",(-.006,.052,.037),(1.102,.686,.074),dust,"base",.019)
cube("Light footplate front inlay",(-.006,-.281,.047),(1.035,.024,.021),lighter,"base",.004)
for x,y,w,l in ((-.221,.101,.302,.254),(.353,.102,.224,.220)):
    cube("Independent mast mounting plate",(x,y,.083),(w,l,.026),iron,"base",.009)
    for dx,dy in ((-1,-1),(1,-1),(1,1),(-1,1)):
        cylinder("Visible hex anchor bolt",(x+dx*w*.35,y+dy*l*.33,.102),.013,.017,silver,"base",n=6)
cube("Deep rectangular service mast",(-.222,.111,.722),(.141,.147,1.249),green,"support",.027)
cube("Mast lower steel bumper sleeve",(-.222,.111,.218),(.158,.159,.286),sage,"support",.015)
cube("Mast outer rear inspection plate",(-.216,.192,.777),(.119,.017,.341),sage,"support",.010)
cube("Cross arm mounting saddle",(-.222,.050,1.131),(.502,.102,.113),green,"support",.017)
cube("Visible cross-arm mounting bracket",(-.222,-.010,1.133),(.439,.031,.088),sage,"support",.008)
for x in (-.361,-.071):
    arm=[(x,.021,1.138),(x,-.111,1.139),(x,-.269,1.140),(x,-.342,1.166)]
    tube("Upturned bicycle support cantilever",arm,.023,silver,"support",12)
    tube("Replaceable soft contact cradle",[(x,-.111,1.139),(x,-.169,1.139),(x,-.238,1.141),
                                          (x,-.284,1.145),(x,-.311,1.154)],.034,coal,"support",12)
    for y in (-.148,-.183,-.218,-.251):
        rod("Molded padded support grip rib",(x,y,1.141),(x,y-.005,1.141),.036,coal,"support",12)
    rod("Orange rounded upturned arm tip",(x,-.326,1.157),(x,-.352,1.170),.026,orange,"support",12)
    beam("Welded arm under-brace",(x,.009,1.062),(x,-.134,1.131),.036,green,"support",.008)


# Captive tools hang in separate channels from real curved tethers.
cube("Accessory tether backing panel",(-.229,.051,.803),(.534,.033,.442),green,"tools",.020)
cube("Inset dark tool shadow panel",(-.229,.030,.791),(.482,.014,.386),iron,"tools",.011)
cube("Tool bracket horizontal weather hood",(-.229,.001,1.012),(.539,.095,.040),sage,"tools",.012)
for i,x in enumerate((-.417,-.287,-.157,-.030)):
    cylinder("Stainless captive tether port",(x,-.013,.975),.018,.019,silver,"tools",side=True,n=12)
    z=.780-i*.018
    point=[(x,-.021,.972),(x+.012,-.039,.929),(x-.010,-.119,.904),
           (x-.016,-.155,.854),(x-.003,-.167,z+.035),(x,-.164,z+.004)]
    tube("Captured orange-coated hanging tether",point,.007,amber,"tools",8)
    cylinder("Captive crimp collar",(x,-.164,z+.003),.014,.026,silver,"tools",n=9)
    cylinder("Tool-end attachment pin",(x,-.170,z-.010),.009,.015,silver,"tools",n=8)
    if i==0:
        # Negative space in the jaws is a real cut in the profile, not a decal.
        local=[(-.019,-.151),(.019,-.151),(.017,-.073),(.033,-.049),(.034,-.006),
               (.019,.011),(.015,-.019),(-.012,-.025),(-.018,.009),(-.033,-.006),(-.032,-.050),(-.018,-.075)]
        profile("Captive open-ended wrench with jaw relief",[(x+a,z+b) for a,b in local],-.182,.023,silver,"tools",.003)
        cube("Wrench moulded comfort grip",(x,-.172,z-.101),(.046,.028,.063),orange,"tools",.006)
    elif i==1:
        tube("Captive L-shaped hex tool",
             [(x,-.175,z-.025),(x,-.175,z-.141),(x+.016,-.175,z-.156),(x+.058,-.175,z-.156)],.009,silver,"tools",6)
    elif i==2:
        cylinder("Captive screwdriver thick handle",(x,-.171,z-.055),.027,.103,orange,"tools",n=12)
        cylinder("Screwdriver shaft without active surfaces",(x,-.171,z-.144),.009,.088,silver,"tools",n=10)
        cylinder("Stainless screwdriver driver end",(x,-.171,z-.190),.011,.014,silver,"tools",n=8)
        for a in range(6):
            xx=x+.027*math.cos(a*math.tau/6);yy=-.171+.027*math.sin(a*math.tau/6)
            rod("Moulded screwdriver grip spline",(xx,yy,z-.025),(xx,yy,z-.081),.005,orange,"tools",7)
    else:
        trace=[(x-.010,-.174,z-.016),(x-.014,-.174,z-.098),(x-.005,-.173,z-.156),
               (x+.010,-.179,z-.169),(x+.032,-.187,z-.167)]
        tube("Captive wedge tyre lever",trace,.014,orange,"tools",8)
        cube("Tyre lever flattened pry lip",(x+.032,-.188,z-.166),(.035,.026,.013),orange,"tools",.007)


# Separate hand pump with actual plunger, protective dial and docked valve hose.
px,py=.353,.111
cube("Pump tall casing upright",(px,py,.516),(.149,.155,.829),green,"pump",.020)
cube("Pump barrel shroud access face",(px,py-.083,.551),(.114,.018,.573),sage,"pump",.010)
cylinder("Brushed round plunger guide",(px,py,.952),.042,.119,silver,"pump",n=14)
cylinder("Exposed plunger rod",(px,py,1.082),.017,.220,silver,"pump",n=12)
cube("Shared pump T-handle fitting",(px,py,1.202),(.093,.056,.064),green,"pump",.011)
rod("Pump handle internal metal bar",(px-.079,py,1.210),(px+.079,py,1.210),.017,silver,"pump",14)
for sign in (-1,1):
    rod("Pump handle textured rubber grip",(px+sign*.045,py,1.210),
        (px+sign*.132,py,1.210),.030,coal,"pump",14)
    rod("Pump grip end cap",(px+sign*.131,py,1.210),
        (px+sign*.142,py,1.210),.031,orange,"pump",14)
cube("Pump front rounded gauge support",(px,-.018,.862),(.139,.094,.172),iron,"pump",.020)
cylinder("Pressure dial brushed bezel",(px,-.074,.870),.065,.031,silver,"pump",side=True,n=28)
cylinder("Ivory unnumbered gauge face",(px,-.092,.870),.055,.008,chalk,"pump",side=True,n=28)
for i in range(9):
    a=math.radians(217-i*29)
    inner=.034 if i%2 else .029
    rod("Readout engraved radial tick",(px+inner*math.cos(a),-.097,.870+inner*math.sin(a)),
        (px+.048*math.cos(a),-.097,.870+.048*math.sin(a)),.0022,coal,"pump",6)
rod("Orange gauge pointer",(px,-.104,.870),(px+.021,-.104,.907),.0038,red,"pump",8)
cylinder("Pointer pivot cap",(px,-.105,.870),.007,.004,red,"pump",side=True,n=10)
cylinder("Clear gauge cover",(px,-.113,.870),.053,.007,glass,"pump",side=True,n=24)
path=[(.428,.120,.373),(.489,.096,.357),(.544,.024,.270),(.544,-.077,.174),(.514,-.169,.148),
      (.443,-.240,.180),(.435,-.248,.300),(.465,-.205,.408),(.482,-.103,.483),(.460,-.055,.537)]
tube("Continuous reinforced pump hose",path,.015,coal,"pump",9)
rod("Hose casing first union",(.420,.124,.373),(.451,.113,.366),.022,silver,"pump",12)
rod("Hose valve head angled",(.460,-.055,.537),(.437,-.021,.575),.027,silver,"pump",14)
rod("Valve fitting rubber tip",(.436,-.019,.577),(.423,-.002,.597),.021,orange,"pump",12)
cube("Dock for captive air nozzle",(.425,.013,.587),(.067,.077,.083),green,"pump",.013)
cube("Pump low tread base upper ledge",(.351,.014,.135),(.211,.249,.042),iron,"pump",.012)
for x in (.284,.333,.382,.431):
    cube("Pump tread stippled slot",(x,-.050,.158),(.014,.114,.010),silver,"pump",.003)


# Generic two-wheel outline, no transport operator mark or functionality claim.
cube("Upright sign support channel",(-.222,.105,1.405),(.077,.063,.244),green,"sign",.010)
cube("Rounded station pictogram plaque",(-.221,.113,1.438),(.395,.063,.231),green,"sign",.018)
cube("Warm readable artwork backing",(-.221,.076,1.444),(.359,.014,.192),chalk,"sign",.012)
for x in (-.299,-.142):
    cycle_ring("Bicycle pictogram open wheel",x,.065,1.466,.034,.0041,green,"sign")
for i,(a,b) in enumerate((((-.301,1.466),(-.259,1.513)),((-.259,1.513),(-.223,1.470)),((-.223,1.470),(-.301,1.466)),
                          ((-.223,1.470),(-.181,1.510)),((-.181,1.510),(-.259,1.513)),((-.181,1.510),(-.142,1.466)),
                          ((-.186,1.510),(-.196,1.535)),((-.196,1.535),(-.165,1.534)),((-.279,1.520),(-.243,1.520)))):
    rod("Bicycle pictogram frame",(a[0],.065,a[1]),(b[0],.065,b[1]),.0044,green,"sign",7)
label("Generic station title","CYCLE CARE",(-.221,.066,1.394),.035,green)
cube("Slim orange placard bottom stripe",(-.222,.066,1.356),(.312,.008,.014),orange,"sign",.003)
def aim(o, target):
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


cube("Studio floor",(0,0,-.029),(200,200,.045),material("Studio charcoal",(.042,.052,.053),.66),"studio")
bpy.ops.object.camera_add(location=(1.82,-4.45,2.32))
camera=attach(bpy.context.object,"Frontal three-quarter studio camera","studio")
aim(camera,(0,-.01,.77))
camera.data.type="ORTHO";camera.data.ortho_scale=1.92
scene.camera=camera
for name,pos,energy,color,size in (
    ("Warm key",(2.9,-3.7,5.1),264,(1,.89,.73),2.45),
    ("Cool window fill",(-3.5,-4.0,2.7),175,(.70,.87,1),2.2),
    ("Top perimeter rim",(3,2.7,4.2),275,(.77,.93,1),2.5),
):
    bpy.ops.object.light_add(type="AREA",location=pos)
    o=attach(bpy.context.object,name,"studio")
    o.data.energy=energy;o.data.color=color;o.data.shape="DISK";o.data.size=size
    aim(o,(0,0,.94))
scene.world=bpy.data.worlds.new("Ambient studio")
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.32,.38,.47,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.32
scene.render.engine="CYCLES"
scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(ROOT/"previews"/"studio.png")
scene.view_settings.view_transform="AgX"

# Every authoring part remains separate and editable in the saved project.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"park-connector-bicycle-repair-stand.blend"))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)

# Batch exported meshes by functional group and material. Keep glass separate
# so an engine can sort its transparency independently of the cabinet.
model_objects=[]
for name, coll in parts.items():
    if name=="studio":
        continue
    by=defaultdict(list)
    for o in list(coll.objects):
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active=o
        if o.type=="FONT" or o.modifiers:
            bpy.ops.object.convert(target="MESH")
            o=bpy.context.view_layer.objects.active
        by[o.data.materials[0].name].append(o)
    for mat, objects in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects:
            o.select_set(True)
        active=objects[0]
        bpy.context.view_layer.objects.active=active
        if len(objects)>1:
            bpy.ops.object.join()
        active.name=coll.name[3:]+" | "+mat
        model_objects.append(active)
bpy.ops.object.select_all(action="DESELECT")
for o in model_objects:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/"park-connector-bicycle-repair-stand.glb"),
                         export_format="GLB",use_selection=True,export_animations=False,
                         export_cameras=False,export_lights=False,export_texcoords=False)
