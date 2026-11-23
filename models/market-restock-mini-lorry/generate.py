"""Original compact market restock lorry, metres. Run Blender background."""
import math
import sys
from collections import defaultdict
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
SLUG = "market-restock-mini-lorry"
for folder in ("exports", "previews"):
    (ROOT / folder).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
groups = {}
for key, name in (
    ("cab", "01 Teal cab and welded doorway"),
    ("windows", "02 Safety-glass panes"),
    ("interior", "03 Cab interior"),
    ("chassis", "04 Chassis and suspension"),
    ("wheels", "05 Wheels and hubs"),
    ("bed", "06 Open dropside bed and tie-down points"),
    ("cargo", "07 Reusable crate load and straps"),
    ("studio", "08 Studio only"),
):
    groups[key] = bpy.data.collections.new(name)
    scene.collection.children.link(groups[key])

def mat(name, c, rough=.42, metal=0, alpha=1):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*c, alpha)
    s = m.node_tree.nodes.get("Principled BSDF")
    s.inputs["Base Color"].default_value = (*c, 1)
    s.inputs["Roughness"].default_value = rough
    s.inputs["Metallic"].default_value = metal
    s.inputs["Alpha"].default_value = alpha
    if alpha < 1:
        m.surface_render_method = "BLENDED"
    return m

def attach(o, name, group, material=None):
    o.name = name
    for old in list(o.users_collection):
        old.objects.unlink(o)
    groups[group].objects.link(o)
    if material:
        o.data.materials.append(material)
    return o

def bevel(o, width, seg=1):
    if width:
        m = o.modifiers.new("Formed edge radius", "BEVEL")
        m.width, m.segments, m.harden_normals = width, seg, True
        n = o.modifiers.new("Weighted form normals", "WEIGHTED_NORMAL")
        n.keep_sharp = True
    return o

def box(name, pos, size, material, group, radius=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    o = attach(bpy.context.object, name, group, material)
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return bevel(o, radius, 2 if radius >= .028 else 1)

def mesh(name, verts, faces, material, group):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return attach(bpy.data.objects.new(name, me), name, group, material)

def cylinder(name, pos, r, depth, material, group, axis="z", n=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=depth, location=pos)
    o = attach(bpy.context.object, name, group, material)
    if axis == "x":
        o.rotation_euler.y = math.pi/2
    if axis == "y":
        o.rotation_euler.x = math.pi/2
    for p in o.data.polygons:
        p.use_smooth = len(p.vertices)==4
    return o

def bar(name, a, b, w, h, material, group, radius=0):
    va, vb = Vector(a), Vector(b)
    o = box(name, (va+vb)/2, (w,h,(vb-va).length), material, group, radius)
    o.rotation_euler = (vb-va).to_track_quat("Z","Y").to_euler()
    return o

def pane(name, corners, material, group):
    o=mesh(name,corners,[(0,1,2,3)],material,group)
    return o

def aim(o,target):
    o.rotation_euler = (Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()

teal = mat("Marine blue-green painted steel",(.045,.30,.32),.43,.19)
mist = mat("Porcelain cream cap paint",(.72,.78,.70),.41,.13)
dark = mat("Anthracite composite guards",(.028,.041,.046),.61)
black = mat("Rubber tyres and isolators",(.023,.027,.026),.78)
metal = mat("Brushed grey utility hardware",(.40,.44,.43),.43,.44)
hub = mat("Dull silver wheel hubs",(.45,.51,.50),.35,.55)
glass = mat("Cool smoky laminated glazing",(.33,.55,.63),.15,0,.43)
seat = mat("Graphite woven seat material",(.078,.115,.118),.81)
bed = mat("Textured dark cargo deck",(.115,.14,.136),.75)
wood = mat("Worn light alloy rail inserts",(.40,.45,.39),.56,.23)
red = mat("Muted red rear optic",(.59,.036,.026),.28)
amber = mat("Amber corners and restraint webbing",(.91,.37,.039),.46)
ivory = mat("Diffuse ivory headlight reflector",(.88,.92,.80),.31,.17)
cream = mat("Cream neutral chevron",(.88,.835,.63),.57)
crate_a = mat("Reusable ochre HDPE crate",(.75,.43,.085),.56)
crate_b = mat("Reusable jade HDPE crate",(.095,.36,.26),.63)

# Compact 2.28 m wheelbase, orthogonal axes and ground pivot, -Y front.
axles = (-1.23,1.05)
wheel_z = .302
for x in (-.40,.40):
    box("Separate continuous frame stringer",(x,.05,.482),(.092,3.80,.126),dark,"chassis",.011)
for y in (-1.84,-.72,.23,1.48,1.98):
    box("Welded frame crossmember",(0,y,.493),(1.03,.107,.078),dark,"chassis",.008)
for y in axles:
    cylinder("Transverse axle tube",(0,y,.300),.038,1.36,metal,"chassis","x")
    for x in (-.48,.48):
        box("Longitudinal laminated spring pack",(x,y,.374),(.117,.605,.028),metal,"chassis",.007)
        box("Spring saddle bracket",(x,y,.334),(.161,.126,.084),dark,"chassis",.008)

def tyre(name,x,y):
    profile=[(-.097,.207),(-.102,.250),(-.087,.282),(-.059,.299),(-.034,.302),
             (.034,.302),(.059,.299),(.087,.282),(.102,.250),(.097,.207)]
    verts=[]; faces=[]; n=24
    for lx,r in profile:
        for j in range(n):
            a=j*math.tau/n
            verts.append((x+lx,y+r*math.cos(a),wheel_z+r*math.sin(a)))
    for i in range(len(profile)):
        for j in range(n):
            k=(i+1)%len(profile); m=(j+1)%n
            faces.append((i*n+j,i*n+m,k*n+m,k*n+j))
    o=mesh(name,verts,faces,black,"wheels")
    # Closed surface; align actual normals after constructing profile.
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in o.data.polygons: p.use_smooth=True

for side in (-1,1):
    ss="Right" if side<0 else "Left"
    for i,y in enumerate(axles):
        x=side*.702
        key=("Front " if i==0 else "Rear ")+ss
        tyre(key+" formed rubber tyre",x,y)
        cylinder(key+" inset steel rim",(x,y,wheel_z),.207,.172,hub,"wheels","x",20)
        cylinder(key+" dark stamped wheel center",(x+side*.089,y,wheel_z),.153,.011,dark,"wheels","x",20)
        cylinder(key+" pressed hub cover",(x+side*.101,y,wheel_z),.112,.030,hub,"wheels","x",16)
        for j in range(5):
            a=j*math.tau/5
            cylinder(key+" utility wheel stud",(x+side*.119,y+.074*math.cos(a),wheel_z+.074*math.sin(a)),.013,.009,metal,"wheels","x",6)
        # Five-sided geometric flare clears tyre. Low skirts and separate rear mud flaps.
        points=[(y-.372,.339),(y-.351,.488),(y-.246,.615),(y-.12,.663),
                (y+.12,.663),(y+.246,.615),(y+.351,.488),(y+.372,.339)]
        # Continuous folded arch ribbon; no intersecting box parts or faceted gaps.
        av = [(side*.808+dx,py,pz+dz) for py,pz in points
              for dx,dz in ((-.052,-.026),(.052,-.026),(.052,.026),(-.052,.026))]
        af = [(0,1,2,3)]
        for a in range(len(points)-1):
            for j in range(4):
                k=(j+1)%4
                af.append((4*a+j,4*a+k,4*(a+1)+k,4*(a+1)+j))
        end=(len(points)-1)*4
        af.append((end+3,end+2,end+1,end))
        arch=mesh(key+" continuous wheel arch",av,af,dark,"chassis")
        bm=bmesh.new()
        bm.from_mesh(arch.data)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(arch.data)
        bm.free()
        if i==1:
            box(key+" flexible mud flap",(side*.70,y+.363,.309),(.233,.038,.270),black,"chassis",.006)

box("Cab floor",(0,-1.366,.553),(1.364,1.425,.105),dark,"interior",.020)
box("Lower cab bulkhead",(0,-.704,.950),(1.414,.076,.774),teal,"cab",.024)
box("Upper cab rear bulkhead",(0,-.683,1.594),(1.391,.073,.563),teal,"cab",.018)
box("Cab nose full-width front mask",(0,-2.030,.916),(1.482,.166,.668),teal,"cab",.056)
box("Grey front impact bumper",(0,-2.104,.566),(1.582,.173,.171),dark,"cab",.035)
box("Inset center air intake",(0,-2.116,.885),(.716,.026,.162),dark,"cab",.017)
for z in (.84,.878,.916):
    box("Horizontal inset grille bar",(0,-2.133,z),(.656,.012,.012),metal,"cab",.002)
box("Lower center air intake",(0,-2.194,.590),(.610,.018,.054),black,"cab",.012)

for s in (-1,1):
    # Straight window lip over deep door shell and authentic wheel opening.
    box("Upper pressed cab door panel",(s*.718,-1.374,1.074),(.094,1.236,.377),teal,"cab",.020)
    box("Front door lower geometry ahead of wheel",(s*.724,-1.822,.870),(.084,.333,.326),teal,"cab",.016)
    box("Behind front wheel lower cab skirt",(s*.716,-.822,.700),(.087,.186,.361),teal,"cab",.012)
    box("Rear gap door gasket",(s*.766,-.855,1.086),(.008,.017,.339),dark,"cab",.002)
    box("Pressed door swage",(s*.768,-1.353,1.026),(.006,1.050,.022),mist,"cab",.004)
    box("Recessed flush door handle",(s*.771,-.945,1.176),(.023,.138,.029),dark,"cab",.006)
    box("Non-skid external cab step",(s*.760,-.788,.475),(.146,.248,.048),metal,"chassis",.010)
    for j in range(4):
        box("Step traction groove",(s*.774,-.866+j*.048,.501),(.083,.012,.007),dark,"chassis")
    box("Headlight bevel housing",(s*.562,-2.113,1.006),(.297,.081,.211),dark,"cab",.027)
    box("Rectangular upper clear headlamp",(s*.554,-2.157,1.040),(.231,.024,.094),ivory,"cab",.011)
    box("Amber corner optic",(s*.554,-2.157,.971),(.232,.023,.038),amber,"cab",.006)
    # Sloped A-post; upper frame, backlight border and 2-sided glazing.
    bar("Windscreen structural A post",(s*.711,-2.011,1.233),(s*.656,-1.851,1.879),.063,.060,teal,"cab",.009)
    bar("Rear cab corner pillar",(s*.733,-.704,1.239),(s*.665,-.714,1.864),.062,.059,teal,"cab",.009)
    bar("Side upper window beam",(s*.650,-1.848,1.863),(s*.665,-.712,1.863),.064,.080,mist,"cab",.010)
    bar("Side center glazing post",(s*.724,-1.048,1.254),(s*.671,-1.031,1.860),.030,.036,teal,"cab",.004)
    pane("Broad side door glass",[(s*.719,-1.985,1.266),(s*.715,-1.072,1.266),
         (s*.664,-1.056,1.830),(s*.661,-1.824,1.834)],glass,"windows")
    pane("Narrow rear quarter glass",[(s*.715,-1.027,1.266),(s*.722,-.731,1.266),
         (s*.669,-.737,1.831),(s*.670,-1.006,1.831)],glass,"windows")
    bar("Outboard mirror bracket",(s*.721,-1.920,1.329),(s*.920,-1.959,1.472),.028,.027,dark,"cab")
    box("Outer black mirror pod",(s*.924,-1.948,1.531),(.139,.091,.232),dark,"cab",.025)
    box("Folded mirror backing glass",(s*.925,-1.896,1.530),(.106,.014,.184),metal,"cab",.010)
    box("Separate dark fabric seat base",(s*.385,-1.165,.716),(.350,.354,.122),seat,"interior",.022)
    lean=box("Separate dark fabric seat back",(s*.385,-.980,.964),(.349,.092,.440),seat,"interior",.020)
    lean.rotation_euler.x=-.12
    box("Separate headrest",(s*.385,-.946,1.205),(.177,.103,.134),seat,"interior",.012)
pane("Wide sloped two-part laminated windscreen",[(-.680,-2.038,1.265),(.680,-2.038,1.265),
    (.620,-1.874,1.820),(-.620,-1.874,1.820)],glass,"windows")
box("Wide roof with rain edge",(0,-1.278,1.896),(1.399,1.295,.134),mist,"cab",.055)
box("Dark windscreen lower scuttle",(0,-2.035,1.257),(1.359,.102,.074),dark,"cab",.012)
box("Recessed simple dashboard",(0,-1.765,1.147),(1.275,.320,.141),dark,"interior",.027)
for x in (-.313,.297):
    bar("Parked windscreen wiper arm",(x,-2.032,1.294),(x+.239,-1.998,1.378),.012,.015,black,"cab")
    bar("Windscreen wiper blade",(x+.091,-2.010,1.359),(x+.359,-1.982,1.426),.017,.010,black,"cab")
bpy.ops.mesh.primitive_torus_add(major_segments=16,minor_segments=6,major_radius=.135,minor_radius=.016,location=(-.399,-1.523,1.180),rotation=(.76,0,0))
attach(bpy.context.object,"Right-hand steering rim","interior",dark)
bar("Steering column",(-.399,-1.75,.938),(-.399,-1.526,1.180),.036,.038,metal,"interior")

# Open dropside bed: short waist-height platform, visibly no cargo roof.
box("Dropped flanged cargo platform",(0,.720,.698),(1.636,2.727,.111),dark,"bed",.016)
box("Deck inner wear surface",(0,.713,.762),(1.520,2.542,.036),bed,"bed",.006)
for x in [-.64,-.48,-.32,-.16,0,.16,.32,.48,.64]:
    box("Longitudinal pressed deck line",(x,.713,.782),(.020,2.510,.006),wood,"bed")
for x in (-.792,.792):
    box("Shallow opening dropside panel",(x,.734,.919),(.049,2.658,.288),mist,"bed",.012)
    box("Long formed dropside crown",(x,.731,1.063),(.073,2.673,.042),teal,"bed",.008)
    box("Continuous external hinge beam",(x,.738,.786),(.078,2.646,.044),teal,"bed",.008)
    for y in (-.491,.385,1.260,1.957):
        box("Pressed external dropside stiffener",(x+math.copysign(.025,x),y,.916),(.017,.062,.212),wood,"bed",.006)
        cylinder("Functional form dropside hinge pin",(x+math.copysign(.032,x),y,.789),.024,.119,metal,"bed","y")
    for y in (-.384,1.823):
        box("Folded rectangular side latch plate",(x+math.copysign(.035,x),y,.986),(.022,.094,.083),teal,"bed",.006)
        box("Latch release finger",(x+math.copysign(.054,x),y+.025,.995),(.026,.108,.024),metal,"bed",.004)
box("Cab-side reinforced low headboard",(0,-.558,.940),(1.482,.063,.330),mist,"bed",.013)
box("Cab protector headboard rail",(0,-.569,1.143),(1.546,.074,.065),teal,"bed",.009)
for x in (-.708,.708):
    box("Raised cab protector stub",(x,-.569,1.030),(.064,.077,.279),teal,"bed",.007)
box("Shallow independent rear tailgate",(0,2.014,.937),(1.513,.068,.313),mist,"bed",.016)
box("Rear dropside crown",(0,2.052,1.070),(1.530,.042,.045),teal,"bed",.008)
box("Rear chassis bumper",(0,2.047,.518),(1.456,.133,.127),dark,"chassis",.022)
for x in (-.602,.602):
    box("Rear combination lamp housing",(x,2.120,.564),(.212,.055,.118),dark,"chassis",.015)
    box("Tail and stop lens",(x-.025,2.151,.568),(.110,.015,.064),red,"chassis",.008)
    box("Rear amber direction lens",(x+.058,2.151,.568),(.046,.015,.063),amber,"chassis",.008)
    box("Neutral rear reflective insert",(x,2.067,.812),(.122,.010,.027),cream,"bed")
# Neutral abstract rectangular utility color strip, no text, brand or plate.
for x in (-.142,0,.142):
    v=box("Small unbranded tailgate trim stripe",(x,2.052,.925),(.085,.010,.025),teal,"bed")
    v.rotation_euler.y=.20

# Four independently editable open-topped reuse crates with actual negative slat space.
def crate(x,y,z,material,label):
    group="cargo"
    w,d,h=.579,.459,.272
    box(label+" solid stack base",(x,y,z+.022),(w,d,.044),material,group,.009)
    for side in (-1,1):
        yy=y+side*d/2
        box(label+" long wall continuous rim",(x,yy,z+h-.024),(w+.021,.035,.043),material,group,.007)
        for ix in (-.208,-.106,0,.106,.208):
            box(label+" long louvered wall rib",(x+ix,yy,z+.111),(.024,.025,.156),material,group)
        for zz in (.078,.125):
            box(label+" long lower ventilation runner",(x,yy,z+zz),(w,.022,.016),material,group)
        xx=x+side*w/2
        box(label+" end wall top handle rim",(xx,y,z+h-.024),(.038,d,.043),material,group,.006)
        for iy in (-.159,-.095,.095,.159):
            box(label+" short wall ventilation rib",(xx,y+iy,z+.128),(.026,.027,.206),material,group)
        box(label+" open handhold lower rail",(xx,y,z+.132),(.026,d,.027),material,group)
        for yy in (-d/2,d/2):
            box(label+" stackable corner",(xx,y+yy,z+.140),(.046,.045,.252),material,group,.005)
    for off in (-.166,.166):
        box(label+" stacking foot",(x+off,y,z+.008),(.079,d+.022,.021),material,group)

for x,y,z,c,n in ((-.348,-.105,.783,crate_a,"A lower"),(.335,-.105,.783,crate_b,"B lower"),
                  (-.348,-.105,1.037,crate_b,"A stacked"),(.335,-.105,1.037,crate_a,"B stacked"),
                  (-.348,.907,.783,crate_b,"C lower"),(.335,.907,.783,crate_a,"D lower")):
    crate(x,y,z,c,n)

for y,z in ((-.121,1.311),(.912,1.058)):
    # Straps stop against inside tie points instead of hanging through the bed.
    bar("Wide horizontal amber load restraint",(-.646,y,z),(.625,y,z),.039,.011,amber,"cargo")
    for side in (-1,1):
        a=(side*(.646 if side<0 else .625),y,z)
        b=(side*.733,y,.825)
        bar("Downward angled load restraint",a,b,.040,.012,amber,"cargo")
        cylinder("Inside deck tie point pin",(side*.737,y,.833),.025,.044,metal,"bed","y")
    box("Metal strap lock on usable upper run",(0,y,z+.017),(.106,.066,.032),dark,"cargo",.008)
    box("Recessed metal ratchet lever",(0,y,z+.044),(.072,.055,.018),metal,"cargo",.003)

floor=mat("Studio warm greige floor",(.23,.249,.228),.74)
box("Studio floor",(0,0,-.047),(150,150,.070),floor,"studio")
bpy.ops.object.camera_add(location=(6.55,-5.55,4.8))
c=attach(bpy.context.object,"Front three-quarter camera","studio")
aim(c,(0,.035,.87))
c.data.type="ORTHO"
c.data.ortho_scale=5.30
scene.camera=c
for n,p,power,color,size in (
    ("Large warm soft key",(2.1,-5.0,6.2),900,(1,.87,.72),5.0),
    ("Large cool flank fill",(-4.4,-1.7,4.4),680,(.72,.88,1),4.0),
    ("Soft cream rear rim",(3.8,4.5,5.75),1030,(1,.94,.76),4.4),
):
    bpy.ops.object.light_add(type="AREA",location=p)
    o=attach(bpy.context.object,n,"studio")
    o.data.energy,o.data.color,o.data.shape,o.data.size=power,color,"DISK",size
    aim(o,(0,0,.8))
scene.world=bpy.data.worlds.new("Muted studio ambient")
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value=(.47,.56,.65,1)
bg.inputs[1].default_value=.45
scene.render.engine="CYCLES"
scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=720
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX"
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(ROOT/"previews"/"studio.png")
# Save every authored building block, then batch exported GLB meshes by editable
# assembly/material. Studio floor/lights are not exported.
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(SLUG+".blend")))
if "--skip-render" not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if "--rear-review" in sys.argv:
        c.location=(6.25,5.7,4.6)
        aim(c,(0,.18,.86))
        scene.render.filepath=str(ROOT/"previews"/"rear-review.png")
        bpy.ops.render.render(write_still=True)
# Share the same exact slatted crate mesh by color, without baking away the
# independently modeled crates, slats and straps in the editable .blend.
selected=[]
cargo_specs = {
    crate_a.name: [("A lower ",0,0,0),("B stacked ",.683,0,.254),("D lower ",.683,1.012,0)],
    crate_b.name: [("B lower ",0,0,0),("A stacked ",-.683,0,.254),("C lower ",-.683,1.012,0)],
}
for material, specs in cargo_specs.items():
    take = [obj for obj in groups["cargo"].objects if obj.name.startswith(specs[0][0])]
    for prefix, *_ in specs[1:]:
        for obj in [o for o in groups["cargo"].objects if o.name.startswith(prefix)]:
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in take:
        obj.select_set(True)
        if obj.modifiers:
            bpy.context.view_layer.objects.active=obj
            bpy.ops.object.convert(target="MESH")
            bpy.ops.object.select_all(action="DESELECT")
    for obj in take: obj.select_set(True)
    base = take[0]
    bpy.context.view_layer.objects.active=base
    bpy.ops.object.join()
    base.name="Slatted crate "+specs[0][0].strip()
    selected.append(base)
    for name, dx, dy, dz in specs[1:]:
        o=base.copy()
        o.name="Slatted crate "+name.strip()
        groups["cargo"].objects.link(o)
        o.location += Vector((dx,dy,dz))
        selected.append(o)
# Linked wheel submeshes retain separate objects and transforms without
# repeating the same tyre, hub and fastener geometry four times in the GLB.
wheel_groups = defaultdict(list)
for obj in list(groups["wheels"].objects):
    if obj.name.startswith("Front Left "):
        wheel_groups[obj.data.materials[0].name].append(obj)
    else:
        bpy.data.objects.remove(obj, do_unlink=True)
wheel_label = ("Front Left", "Front Right", "Rear Left", "Rear Right")
locations = ((.702,-1.23),(-.702,-1.23),(.702,1.05),(-.702,1.05))
for material, objects in sorted(wheel_groups.items()):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects: obj.select_set(True)
    whole=objects[0]
    bpy.context.view_layer.objects.active=whole
    if len(objects)>1:
        bpy.ops.object.join()
    whole.name=wheel_label[0]+" | "+material
    selected.append(whole)
    world=whole.matrix_world.copy()
    for label, (x,y) in zip(wheel_label[1:],locations[1:]):
        obj=whole.copy()
        obj.name=label+" | "+material
        groups["wheels"].objects.link(obj)
        spin=Matrix.Rotation(math.pi if x<0 else 0,4,"Z")
        obj.matrix_world=Matrix.Translation((x,y,wheel_z)) @ spin @ Matrix.Translation((-.702,1.23,-wheel_z)) @ world
        selected.append(obj)
for key, group in groups.items():
    if key=="studio":
        continue
    by=defaultdict(list)
    for o in list(group.objects):
        if o in selected:
            continue
        if o.modifiers:
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target="MESH")
            o=bpy.context.view_layer.objects.active
        by[o.data.materials[0].name].append(o)
    for material, objects in sorted(by.items()):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objects: o.select_set(True)
        active=objects[0]
        bpy.context.view_layer.objects.active=active
        if len(objects)>1:
            bpy.ops.object.join()
        active.name=group.name[3:]+" | "+material
        selected.append(active)
bpy.ops.object.select_all(action="DESELECT")
for o in selected: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/"exports"/(SLUG+".glb")),
    export_format="GLB",use_selection=True,export_animations=False,
    export_cameras=False,export_lights=False,export_texcoords=False)
