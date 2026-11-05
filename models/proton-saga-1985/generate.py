"""Deterministic, reference-led 1985 Saga exterior study. Blender 5.1.2 + cwebp."""
import bpy
import math
import subprocess
import sys
from pathlib import Path
from mathutils import Vector

OUT = Path(__file__).resolve().parent
QUICK = '--quick' in sys.argv
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
root = bpy.data.objects.new('ASSET_Proton_Saga_1985', None)
bpy.context.collection.objects.link(root)


def material(name, color, metallic=0, roughness=.4, alpha=1):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    for key, value in [('Base Color', (*color, 1)), ('Metallic', metallic), ('Roughness', roughness), ('Alpha', alpha)]:
        shader.inputs[key].default_value = value
    if alpha < 1:
        mat.surface_render_method = 'DITHERED'
        mat.use_transparency_overlap = False
    return mat


paint = material('Silver body enamel', (.48, .505, .52), .65, .29)
black = material('Black molded trim', (.009, .011, .014), 0, .62)
rubber = material('Tire sidewall', (.012, .014, .017), 0, .88)
glass = material('Neutral smoky glazing', (.09, .12, .145), 0, .17, .27)
steel = material('Satin pressed steel', (.30, .325, .345), .78, .34)
chrome = material('Polished narrow trim', (.52, .55, .57), .85, .22)
reflector = material('Aluminized lamp reflector', (.73, .75, .76), .95, .16)
lens = material('Clear headlamp lens', (.72, .8, .83), 0, .13, .15)
lens_rib = material('Fine lens prism', (.53, .60, .64), .25, .25, .22)
red = material('Red rear lens', (.40, .009, .014), .12, .26)
amber = material('Amber corner lens', (.78, .19, .007), .05, .26)
stripe = material('Thin red pinstripe', (.52, .012, .018), .2, .33)
fabric = material('Dark woven seat cloth', (.042, .05, .057), 0, .95)
white = material('Plate lettering', (.8, .83, .84), .1, .4)
navy = material('Heritage shield navy', (.015, .055, .13), .4, .28)
gold = material('Heritage shield gold', (.9, .57, .012), .5, .3)


def mesh(name, vertices, faces, mat, bevel=0, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = root
    obj.data.materials.append(mat)
    for polygon in data.polygons:
        polygon.use_smooth = smooth
    if bevel:
        mod = obj.modifiers.new('Small manufactured edge radius', 'BEVEL')
        mod.width, mod.segments = bevel, 3
        obj.modifiers.new('Panel weighted normals', 'WEIGHTED_NORMAL')
    return obj


def box(name, location, dimensions, mat, bevel=.004):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name, obj.parent = name, root
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Rounded pressed edge', 'BEVEL')
        mod.width, mod.segments = bevel, 3
        obj.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
    return obj


def line(name, points, mat, radius=.002, resolution=1):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions, data.bevel_depth, data.bevel_resolution = '3D', radius, resolution
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = root
    data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    return obj


def cylinder(name, location, radius, depth, mat, vertices=32, rotation=(math.pi/2, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name, obj.parent = name, root
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    mod = obj.modifiers.new('Soft cylindrical edge', 'BEVEL')
    mod.width, mod.segments = .0015, 2
    obj.modifiers.new('Weighted cylinder normals', 'WEIGHTED_NORMAL')
    return obj


def label(name, body, location, size, mat, rotation):
    data = bpy.data.curves.new(name, 'FONT')
    data.body, data.align_x, data.align_y = body, 'CENTER', 'CENTER'
    data.size, data.extrude = size, .00025
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent, obj.location, obj.rotation_euler = root, location, rotation
    data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    return obj


# The lower beltline restores the reference's upright glasshouse and slim bonnet.
# Dimensions are artistic proportions inferred from images, not factory measurements.
stations = [(-2.045,.79,.852),(-1.99,.805,.871),(-1.88,.811,.89),(-1.60,.814,.903),(-1.25,.817,.921),(-.91,.814,.935),(-.66,.81,.935),(.0,.81,.935),(.60,.812,.935),(1.13,.81,.927),(1.30,.808,.925),(1.65,.80,.912),(1.93,.78,.894),(2.045,.739,.88)]
vertices=[]
for x,w,h in stations:
    low=.37 if x < -1.88 or x > 1.93 else .25
    cross=[(-w*.925,low),(-w*.972,.40),(-w,.655),(-w*.995,h-.05),(-w*.95,h),(-w*.76,h+.012),(0,h+.022),(w*.76,h+.012),(w*.95,h),(w*.995,h-.05),(w,.655),(w*.972,.40),(w*.925,low)]
    vertices.extend((x,y,z) for y,z in cross)
count=13
faces=[tuple(reversed(range(count)))]
for i in range(len(stations)-1):
    for j in range(count):
        if -0.92 <= stations[i][0] and stations[i+1][0] <= 1.14 and 4 <= j <= 7:
            continue  # No hidden silver slab behind the windscreen.
        faces.append((i*count+j,i*count+(j+1)%count,(i+1)*count+(j+1)%count,(i+1)*count+j))
faces.append(tuple(range((len(stations)-1)*count,len(stations)*count)))
body=mesh('Sculpted steel body shell',vertices,faces,paint,.008)
# A thin leading bonnet lip shelters the lamp frames without blocking their bowls.
back=vertices[4:9]
front=[(-2.116,y*.79/(.79*.95),z+.003) for x,y,z in back]
mesh('Blended bonnet leading lip',back+front,[(j,j+1,j+6,j+5) for j in range(4)],paint,.001,smooth=True)
for axle in [-1.235,1.145]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=.323, depth=2.1, location=(axle,0,.29), rotation=(math.pi/2,0,0))
    cutter=bpy.context.object
    bpy.context.view_layer.objects.active=body
    mod=body.modifiers.new('Actual wheel opening','BOOLEAN')
    mod.operation,mod.object='DIFFERENCE',cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)

# Shallow crowned roof and thin sheet pillars, without raised chrome tubes.
roof=[]
for i in range(9):
    x=-.49+i*1.34/8
    for j in range(13):
        y=-.624+j*1.248/12
        z=1.373+.022*(1-(y/.64)**2)+.006*math.sin(i*math.pi/8)
        roof.append((x,y,z))
roof_faces=[]
for i in range(8):
    for j in range(12):
        a=i*13+j
        roof_faces.append((a,a+1,a+14,a+13))
roof_obj=mesh('Crowned roof skin',roof,roof_faces,paint,smooth=True)
solid=roof_obj.modifiers.new('Roof sheet thickness','SOLIDIFY');solid.thickness=.015
# Continuous formed header bridges the crowned roof to each screen gasket.
for name,roof_x,glass_x in [('Front roof header',-.49,-.468),('Rear roof header',.85,.835)]:
    header=[]
    for j in range(13):
        y=-.624+j*1.248/12
        z=1.373+.022*(1-(y/.64)**2)
        header.extend([(roof_x,y,z),(glass_x,y*.596/.624,1.346)])
    mesh(name,header,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(12)],paint,smooth=True)
front_glass=[(-.903,-.701,.959),(-.903,.701,.959),(-.468,.596,1.346),(-.468,-.596,1.346)]
rear_glass=[(1.171,.697,.952),(1.171,-.697,.952),(.835,-.594,1.346),(.835,.594,1.346)]
for name,points in [('Front windscreen',front_glass),('Rear screen',rear_glass)]:
    mesh(name,points,[(0,1,2,3)],glass)
    line(name+' thin black gasket',points+[points[0]],black,.007)

for side in [-1,1]:
    def side_point(x,z,offset=0):
        return (x,side*(.754-(z-.95)*.131/.423+offset),z)
    front=[(-.869,.969),(-.449,1.346),(.092,1.346),(.092,.969)]
    rear=[(.159,.969),(.159,1.346),(.772,1.346),(1.102,.969)]
    for name,outline in [('Front door glazing',front),('Rear door glazing',rear)]:
        pts=[side_point(x,z) for x,z in outline]
        mesh(name,pts,[(0,1,2,3)],glass)
        line(name+' black frame',pts+[pts[0]],black,.008)
    # All pillar width comes from sheet surfaces; only narrow seals stand proud.
    pillar_shapes=[('A pillar',[(-.95,.941),(-.51,1.376),(-.45,1.357),(-.889,.948)]),('B pillar',[(.095,.944),(.095,1.367),(.153,1.367),(.153,.944)]),('C pillar',[(1.177,.941),(.876,1.373),(.792,1.367),(1.112,.946)])]
    for name,shape in pillar_shapes:
        mesh(name,[side_point(x,z,.002) for x,z in shape],[(0,1,2,3)],paint)
    line('Rear fixed quarter-light divider',[side_point(.777,.97,.003),side_point(.62,1.345,.003)],black,.006)
    line('Narrow rain gutter',[(-.49,side*.631,1.375),(.85,side*.631,1.375)],chrome,.0025)
    line('Window belt weatherstrip',[(-.927,side*.766,.945),(1.17,side*.766,.945)],black,.006)
    line('Thin bright sill trim',[(-.927,side*.768,.94),(1.17,side*.768,.94)],chrome,.002)
    seam_y=side*.811
    line('Front door shutline',[(-.915,side*.785,.934),(-.79,seam_y,.71),(-.727,side*.788,.344),(.125,side*.788,.344),(.125,seam_y,.70),(.125,side*.785,.936)],black,.0018)
    line('Rear door shutline',[(.125,side*.788,.344),(.81,side*.788,.344),(.973,seam_y,.63),(1.146,side*.785,.934)],black,.0018)
    for x in [-.08,.91]:
        box('Recessed door handle base',(x,side*.811,.862),(.115,.009,.047),black,.006)
        box('Black lift-up handle',(x,side*.821,.874),(.102,.018,.025),black,.005)
        cylinder('Small lock barrel',(x+.036,side*.833,.856),.006,.004,chrome,16)
    line('Door lower pressed crease',[(-.80,side*.798,.325),(.86,side*.798,.325)],paint,.004)
    # Flat black molding follows the body; the small red line is never a raised tube.
    strip=[]
    stripe_points=[]
    for sx,sw,sz in stations:
        strip.extend([(sx,side*(sw+.003),.61),(sx,side*(sw+.003),.648)])
        stripe_points.append((sx,side*(sw+.006),.64))
    mesh('Flat side rubbing molding',strip,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(stations)-1)],black)
    line('Fine side red coachline',stripe_points,stripe,.0025)
    box('Mirror triangular foot',(-.84,side*.791,.988),(.10,.044,.075),black,.007)
    box('Rounded black door mirror',(-.79,side*.869,1.006),(.178,.123,.102),black,.022)
    box('Mirror reflective face',(-.695,side*.872,1.006),(.004,.098,.079),chrome,.01)
    for axle in [-1.235,1.145]:
        arc=[(axle+math.cos(t)*.325,side*.811,.29+math.sin(t)*.325) for t in [i*math.pi/32 for i in range(33)]]
        line('Pressed arch lip',arc,paint,.007)

# The front arms and blades are parked low and nearly parallel to the cowl.
for side in [-1,1]:
    line('Parked wiper arm',[(-.906,side*.34,.969),(-.851,side*.16,1.014)],black,.004)
    line('Parked wiper blade',[(-.853,side*.42,1.009),(-.853,side*.01,1.009)],black,.004)
box('Ventilated cowl',(-.932,0,.946),(.07,1.39,.025),black,.005)
for y in [-.62+i*.04 for i in range(32)]:
    line('Cowl vent',[(-.956,y,.96),(-.917,y,.961)],rubber,.0014)


def wheel_lathe(name, axle, side, profile, mat, segments=64):
    points=[]
    for r,offset in profile:
        for j in range(segments):
            t=j*math.tau/segments
            points.append((axle+math.sin(t)*r,side*(.705+offset),.292+math.cos(t)*r))
    quads=[]
    for ring in range(len(profile)-1):
        for j in range(segments):
            a=ring*segments+j;b=ring*segments+(j+1)%segments
            quads.append((a,b,b+segments,a+segments))
    return mesh(name,points,quads,mat,smooth=True)


for side in [-1,1]:
    for axle in [-1.235,1.145]:
        # A tall rounded sidewall surrounding a small, era-appropriate steel wheel.
        tire_profile=[(.174,-.064),(.198,-.077),(.249,-.081),(.278,-.066),(.29,-.045),(.292,-.014),(.292,.028),(.286,.061),(.269,.079),(.235,.085),(.19,.079),(.174,.068)]
        wheel_lathe('Rounded high-profile tire',axle,side,tire_profile,rubber)
        # Raised fine circumferential rubber ribs replace protruding tread cubes.
        for radial,offset in [(.213,.084),(.253,.080),(.273,.073)]:
            points=[(axle+math.sin(j*math.tau/64)*radial,side*(.705+offset),.292+math.cos(j*math.tau/64)*radial) for j in range(65)]
            line('Fine tire sidewall ridge',points,rubber,.0012)
        for j in range(56):
            t=j*math.tau/56
            points=[]
            for offset,dt in [(-.04,-.008),(0,.008),(.04,.022)]:
                points.append((axle+math.sin(t+dt)*.2924,side*(.705+offset),.292+math.cos(t+dt)*.2924))
            line('Shallow tread groove',points,black,.0009)
        rim=wheel_lathe('Dished stamped steel wheel',axle,side,[(.001,.035),(.09,.035),(.135,.041),(.152,.057),(.167,.067),(.178,.070),(.181,.076),(.175,.081),(.166,.078),(.152,.069),(.13,.056),(.09,.061),(.001,.061)],steel)
        # Open vent holes through the dished annulus, not black disks on a flat cap.
        for j in range(12):
            t=j*math.tau/12
            bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0105,depth=.14,location=(axle+math.sin(t)*.144,side*.767,.292+math.cos(t)*.144),rotation=(math.pi/2,0,0))
            cutter=bpy.context.object;cutter.scale=(.8,1.0,1.0)
            bpy.context.view_layer.objects.active=rim
            mod=rim.modifiers.new('Punched wheel ventilation','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE'
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter,do_unlink=True)
        # A restrained center cap sits inside the tire's widest sidewall.
        wheel_lathe('Shallow steel center cap',axle,side,[(.001,.065),(.067,.065),(.084,.072),(.086,.077),(.079,.084),(.058,.087),(.001,.087)],steel)
        for j in range(4):
            t=j*math.tau/4
            cylinder('Four recessed lug nuts',(axle+math.sin(t)*.064,side*.798,.292+math.cos(t)*.064),.006,.006,chrome,16)
        cylinder('Small wheel center emblem',(axle,side*.794,.292),.018,.003,chrome,24)
        cylinder('Dark brake backing',(axle,side*.733,.292),.166,.01,black,40)


# One continuous wraparound bumper replaces detached square end blocks.
def bumper(name, front):
    xs=[-2.127,-2.127,-2.106,-2.06,-1.98,-1.87]
    ys=[0,.64,.75,.802,.815,.806]
    if not front:xs=[-x for x in xs]
    path=[(x,-y) for x,y in reversed(list(zip(xs[1:],ys[1:])))] + list(zip(xs,ys))
    verts=[]
    for x,y in path:
        # Upper lip projects gently; lower valance recedes like the molded original.
        outward=-1 if front else 1
        verts.extend([(x,y,.622),(x+outward*.012,y,.585),(x,y,.461),(x-outward*.045,y*.987,.397)])
    faces=[]
    for i in range(len(path)-1):
        for j in range(3):faces.append((i*4+j,(i+1)*4+j,(i+1)*4+j+1,i*4+j+1))
    if not front:faces=[tuple(reversed(face)) for face in faces]
    obj=mesh(name,verts,faces,black,.014,smooth=True)
    solid=obj.modifiers.new('Molded bumper thickness','SOLIDIFY');solid.thickness=.025
    line(name+' red insert',[(x+(-.017 if front else .017),y,.596) for x,y in path],stripe,.003)
    return obj
bumper('Front continuous wraparound bumper',True)
bumper('Rear continuous wraparound bumper',False)
box('Front lower valance',(-2.01,0,.363),(.20,1.49,.12),black,.015)
for side in [-1,1]:
    box('Recessed lower cooling slot',(-2.087,side*.405,.422),(.009,.365,.074),rubber,.008)
    for y in [side*.25,side*.45,side*.59]:
        box('Cooling grille vertical bar',(-2.095,y,.422),(.007,.009,.07),black,.001)


# The optical headlamp consists of a concave reflector and bulb under a clear lens.
def reflector_bowl(name, y_center):
    points=[]
    for ring in range(6):
        r=ring/5
        for j in range(40):
            t=j*math.tau/40
            points.append((-2.065-.041*r*r,y_center+math.sin(t)*.139*r,.759+math.cos(t)*.077*r))
    faces=[]
    for ring in range(5):
        for j in range(40):
            a=ring*40+j;b=ring*40+(j+1)%40
            if ring==0:faces.append((a,b,b+40,a+40))
            else:faces.append((a,b,b+40,a+40))
    # First ring is slightly offset to avoid coincident zero-area triangles.
    for j in range(40):
        t=j*math.tau/40;points[j]=(-2.065,y_center+math.sin(t)*.0004,.759+math.cos(t)*.0004)
    return mesh(name,points,faces,reflector,smooth=True)


for side in [-1,1]:
    center=side*.537
    outer=[(-2.117,center-.173,.661),(-2.117,center+.173,.661),(-2.117,center+.173,.857),(-2.117,center-.173,.857)]
    inner=[(-2.119,center-.160,.677),(-2.119,center+.160,.677),(-2.119,center+.160,.841),(-2.119,center-.160,.841)]
    mesh('Thin hollow headlamp gasket',outer+inner,[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)],black)
    back=[(-2.048,y,z) for x,y,z in outer]
    mesh('Open headlamp housing sidewalls',outer+back,[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)],black)
    mesh('Headlamp rear reflector plate',[(-2.056,center-.16,.677),(-2.056,center+.16,.677),(-2.056,center+.16,.841),(-2.056,center-.16,.841)],[(0,1,2,3)],reflector)
    reflector_bowl('Concave parabolic headlamp reflector',center)
    cylinder('Headlamp bulb base',(-2.080,center,.759),.018,.018,chrome,24,(0,math.pi/2,0))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=.017,location=(-2.093,center,.759))
    bulb=bpy.context.object;bulb.name='Visible headlamp bulb';bulb.scale=(.7,1,1);bulb.parent=root;bulb.data.materials.append(white)
    # The lens remains almost clear; fine prisms never obscure the circular bowl.
    mesh('Clear rectangular headlamp lens',[(-2.122,center-.159,.678),(-2.122,center+.159,.678),(-2.122,center+.159,.84),(-2.122,center-.159,.84)],[(0,1,2,3)],lens)
    for j in range(15):
        y=center-.147+j*.021
        line('Fine glass lens vertical prism',[(-2.123,y,.683),(-2.123,y,.835)],lens_rib,.00065)
    for z in [.708,.759,.81]:
        line('Subtle lens cross-prism',[(-2.123,center-.152,z),(-2.123,center+.152,z)],lens_rib,.00045)
    # Corner indicator wraps back onto the tapered wing rather than floating forward.
    coords=[(-2.119,side*.704,.674),(-2.119,side*.787,.674),(-2.042,side*.804,.68),(-2.042,side*.804,.842),(-2.119,side*.787,.844),(-2.119,side*.704,.844)]
    mesh('Wraparound amber front indicator',coords,[tuple(range(6))],amber,.004)
    for j in range(4):
        y=side*(.714+j*.019)
        line('Indicator lens prism',[(-2.122,y,.682),(-2.122,y,.835)],lens_rib,.0007)
    # Flush rear lens housing: amber outer column, red stop/tail and clear reversing cell.
    box('Rear lamp slim dark perimeter',(2.049,side*.571,.759),(.025,.426,.207),black,.008)
    for z in [.709,.802]:
        box('Rear red stop and tail cell',(2.067,side*.539,z),(.019,.273,.084),red,.005)
        box('Rear amber corner cell',(2.064,side*.748,z),(.022,.102,.084),amber,.004)
    box('Rear clear reversing cell',(2.079,side*.448,.803),(.006,.078,.069),lens_rib,.003)
    for j in range(4):
        z=.686+j*.045
        line('Rear lens horizontal rib',[(2.08,side*.407,z),(2.08,side*.674,z)],red,.0009)

# A narrow horizontal grille and a small simplified heritage crest.
box('Recessed grille',(-2.067,0,.76),(.026,.735,.183),black,.006)
for z in [.70,.755,.81]:
    box('Thin bright grille slat',(-2.09,0,z),(.008,.718,.006),chrome,.001)
shield=[(-2.102,-.032,.802),(-2.102,.032,.802),(-2.103,.027,.76),(-2.103,0,.742),(-2.103,-.027,.76)]
mesh('Small heritage shield rim',shield,[tuple(range(5))],chrome)
mesh('Navy shield center',[(x-.001,y*.82,.772+(z-.772)*.82) for x,y,z in shield],[tuple(range(5))],navy)
for j in range(12):
    t=j*math.tau/12
    line('Gold crest sun ray',[(-2.107,math.sin(t)*.009,.777+math.cos(t)*.009),(-2.107,math.sin(t)*.022,.777+math.cos(t)*.022)],gold,.0012)
cylinder('Heritage crest center',(-2.108,0,.777),.009,.001,gold,20,(0,math.pi/2,0))

# Separate bonnet and boot shut lines follow the raised panel shoulders.
for side in [-1,1]:
    line('Bonnet shutline',[(-2.013,side*.686,.863),(-1.876,side*.717,.899),(-1.25,side*.726,.938),(-.927,side*.721,.949)],black,.0017)
line('Boot lid shutline',[(1.18,-.711,.943),(1.85,-.708,.924),(2.01,-.655,.91),(2.01,.655,.91),(1.85,.708,.924),(1.18,.711,.943)],black,.0017)
line('Fuel door',[(1.54,.798,.844),(1.71,.795,.834),(1.71,.804,.702),(1.54,.808,.707),(1.54,.798,.844)],black,.0018)

for x in [-2.152,2.151]:
    rotation=(math.pi/2,0,-math.pi/2) if x<0 else (math.pi/2,0,math.pi/2)
    box('Black display plate',(x,0,.478),(.008,.465,.196),black,.004)
    outline=[(x+(-.006 if x<0 else .006),-.23,.383),(x+(-.006 if x<0 else .006),.23,.383),(x+(-.006 if x<0 else .006),.23,.573),(x+(-.006 if x<0 else .006),-.23,.573),(x+(-.006 if x<0 else .006),-.23,.383)]
    line('Fine plate border',outline,white,.0015)
    outward=x+(-.011 if x<0 else .011)
    label('Display plate name','PROTON',(outward,0,.532),.051,white,rotation)
    label('Display plate model','SAGA',(outward,0,.477),.056,white,rotation)
    label('Display plate year','(1985)',(outward,0,.424),.037,white,rotation)
label('Rear Proton wordmark','PROTON',(2.063,-.525,.879),.025,chrome,(math.pi/2,0,math.pi/2))
label('Rear Saga wordmark','SAGA',(2.063,.56,.879),.025,chrome,(math.pi/2,0,math.pi/2))
cylinder('Boot lock',(2.067,0,.88),.006,.004,chrome,20,(0,math.pi/2,0))

# The restrained interior reads through the glazing without fake opaque slabs.
box('Interior cabin floor',(.12,0,.57),(1.95,1.31,.06),black,.012)
box('Slim dashboard',(-.75,0,.925),(.29,1.32,.105),black,.026)
for side in [-1,1]:
    box('Front seat cushion',(-.13,side*.35,.705),(.44,.45,.12),fabric,.055)
    obj=box('Front seat back',(.045,side*.35,.915),(.13,.45,.43),fabric,.045);obj.rotation_euler.y=-.13
    box('Front head restraint',(.066,side*.35,1.16),(.13,.245,.14),fabric,.035)
    box('Door interior trim',(.09,side*.698,.77),(1.72,.04,.27),black,.02)
box('Rear bench cushion',(.76,0,.7),(.40,1.19,.13),fabric,.035)
box('Rear bench back',(.95,0,.89),(.13,1.19,.38),fabric,.035)
box('Center console',(-.22,0,.72),(.64,.15,.13),black,.015)
# Three-spoke RHD wheel, whose normal points along the car longitudinal axis.
steering=[(-.61,.35+math.sin(j*math.tau/40)*.117,.995+math.cos(j*math.tau/40)*.117) for j in range(41)]
line('Right-hand drive steering rim',steering,black,.009)
for t in [0,2.3,4.0]:
    line('Steering wheel spoke',[(-.61,.35,.995),(-.61,.35+math.sin(t)*.109,.995+math.cos(t)*.109)],black,.006)
box('Steering wheel boss',(-.61,.35,.995),(.033,.058,.047),black,.007)
line('Steering column',[(-.76,.35,.90),(-.61,.35,.995)],black,.019)
box('Underbody shadow pan',(.0,0,.256),(2.9,1.20,.08),black,.01)
cylinder('Exhaust tailpipe',(1.985,-.49,.255),.021,.23,steel,24,(0,math.pi/2,0))
cylinder('Dark exhaust opening',(2.104,-.49,.255),.016,.005,black,24,(0,math.pi/2,0))
line('Roof antenna',[(.66,.11,1.399),(.84,.11,1.66)],black,.002)
cylinder('Antenna mounting foot',(.66,.11,1.399),.012,.012,black,20,(0,0,0))

# Batch evaluated export copies by opaque material, retaining editable source parts.
# Transparent windows stay separate; tiny coplanar prisms batch only within one lamp.
def export_vehicle():
    depsgraph=bpy.context.evaluated_depsgraph_get()
    source_name=root.name
    root.name=source_name+'_SOURCE'
    export_root=bpy.data.objects.new(source_name,None)
    bpy.context.collection.objects.link(export_root)
    groups={}
    temporary=[]
    for original in list(root.children):
        if original.type!='MESH':continue
        evaluated=original.evaluated_get(depsgraph)
        data=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=depsgraph)
        copy=bpy.data.objects.new(original.name+'_EXPORT',data)
        bpy.context.collection.objects.link(copy)
        copy.matrix_world=original.matrix_world.copy()
        copy.parent=export_root
        temporary.append(copy)
        mat=original.data.materials[0]
        alpha=mat.diffuse_color[3]
        if alpha>=1:
            key=('opaque',mat.name)
        elif mat==lens_rib:
            center=sum((copy.matrix_world@Vector(corner) for corner in copy.bound_box),Vector())/8
            if center.x < -1.9:
                key=('lamp-prisms','left' if center.y<0 else 'right')
            else:key=('transparent-pane',original.name)
        else:key=('transparent-pane',original.name)
        groups.setdefault(key,[]).append(copy)
    for key,copies in groups.items():
        if len(copies)<2:continue
        bpy.ops.object.select_all(action='DESELECT')
        for copy in copies:copy.select_set(True)
        bpy.context.view_layer.objects.active=copies[0]
        bpy.ops.object.join()
        copies[0].name='Export '+str(key[1])
    bpy.ops.object.select_all(action='DESELECT')
    export_root.select_set(True)
    for copy in export_root.children:copy.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/'exports/proton-saga-1985.glb'),export_format='GLB',use_selection=True,export_apply=True)
    for copy in list(export_root.children):
        data=copy.data
        bpy.data.objects.remove(copy,do_unlink=True)
        if data.users==0:bpy.data.meshes.remove(data)
    bpy.data.objects.remove(export_root,do_unlink=True)
    root.name=source_name


export_vehicle()

scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.render.engine='CYCLES'
scene.cycles.samples=12 if QUICK else 40
scene.world.color=(.14,.14,.14)
floor=box('STUDIO floor',(0,0,-.025),(300,300,.035),material('Studio charcoal',(.025,.03,.036),.08,.44),0)
floor.parent=None
for location,power,size in [((-3,-4,6),1150,5),((1,4,5),1700,5),((4,-1,4),1400,4),((-5,1,2.6),500,3)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    obj=bpy.context.object;obj.data.energy=power;obj.data.shape='DISK';obj.data.size=size
    obj.rotation_euler=(Vector((0,0,.66))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add()
camera=bpy.context.object;camera.data.type='ORTHO';camera.data.clip_end=1000;scene.camera=camera
scene.render.resolution_x=840 if QUICK else 1400
scene.render.resolution_y=600 if QUICK else 1000
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
views={'preview':(-6,-5.2,2.65),'view-front':(-30,0,3.22),'view-rear':(30,0,3.22),'view-left':(0,-30,3.22),'view-right':(0,30,3.22)}
for name,location in views.items():
    if QUICK and name!='preview':continue
    camera.data.ortho_scale=3.1 if name in ['view-front','view-rear'] else 5.3
    camera.location=location
    camera.rotation_euler=(Vector((0,0,.78))-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    subprocess.run(['cwebp','-quiet','-q','90',str(OUT/(name+'.png')),'-o',str(OUT/(name+'.webp'))],check=True)
    (OUT/(name+'.png')).unlink()
camera.data.ortho_scale=5.3;camera.location=views['preview']
camera.rotation_euler=(Vector((0,0,.78))-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'scene.blend'))
print('COMPLETE',bpy.app.version_string)
