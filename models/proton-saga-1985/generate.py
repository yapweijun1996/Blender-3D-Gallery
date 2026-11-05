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
glass = material('Neutral smoky glazing', (.055, .066, .073), 0, .12, .24)
steel = material('Satin pressed steel', (.39, .41, .42), .78, .28)
chrome = material('Polished narrow trim', (.52, .55, .57), .85, .22)
reflector = material('Aluminized lamp reflector', (.73, .75, .76), .95, .16)
lens = material('Clear headlamp lens', (.72, .8, .83), 0, .13, .15)
lens_rib = material('Fine lens prism', (.53, .60, .64), .25, .25, .22)
red = material('Red rear lens', (.19, .0025, .005), .08, .22)
amber = material('Amber corner lens', (.54, .105, .002), .05, .22)
stripe = material('Thin red pinstripe', (.52, .012, .018), .2, .33)
fabric = material('Dark woven seat cloth', (.042, .05, .057), 0, .95)
white = material('Plate lettering', (.8, .83, .84), .1, .4)
navy = material('Heritage shield navy', (.015, .055, .13), .4, .28)
gold = material('Heritage shield gold', (.9, .57, .012), .5, .3)
# Colored lens plastic retains saturated pigment under the large studio softboxes.
for colored_lens in [red,amber]:
    colored_lens.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.25


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


# Cross sections preserve the original proportions while forming a gently crowned
# bonnet, shoulder roll and lower door tumble-in rather than one flat side slab.
# Dimensions remain visual approximations, not factory measurements.
stations = [(-2.045,.79,.852),(-1.99,.805,.866),(-1.88,.811,.883),(-1.60,.814,.9),(-1.25,.817,.918),(-.91,.814,.935),(-.66,.81,.935),(.0,.81,.935),(.60,.812,.935),(1.13,.81,.927),(1.30,.808,.925),(1.65,.80,.912),(1.93,.79,.894),(2.045,.778,.88)]


def body_section(x, width, height):
    low = .37 if x < -1.88 or x > 1.93 else .25
    left = [(-width*.925,low),(-width*.947,max(low+.004,.30)),
            (-width*.974,max(low+.02,.41)),(-width*.995,.54),
            (-width,.65),(-width*.997,.75),(-width*.987,height-.065),
            (-width*.967,height-.023),(-width*.941,height),
            (-width*.72,height+.016)]
    return left + [(0,height+.026)] + [(-y,z) for y,z in reversed(left)]


def shell_width(x, z):
    """Sample the actual piecewise panel surface so trim cannot bury or float."""
    for i in range(len(stations)-1):
        a,b=stations[i:i+2]
        if x <= b[0]:
            t=max(0,min(1,(x-a[0])/(b[0]-a[0])))
            ca,cb=body_section(*a),body_section(*b)
            section=[(ya+(yb-ya)*t,za+(zb-za)*t) for (ya,za),(yb,zb) in zip(ca,cb)][:9]
            for j in range(len(section)-1):
                ya,za=section[j];yb,zb=section[j+1]
                if z<=zb:
                    u=max(0,min(1,(z-za)/max(.00001,zb-za)))
                    return -(ya+(yb-ya)*u)
            return -section[-1][0]
    return shell_width(stations[-1][0]-.00001,z)


def panel_path(name, outline, side, mat=black, radius=.0017, offset=.0015):
    points=[]
    for (xa,za),(xb,zb) in zip(outline,outline[1:]):
        steps=max(2,math.ceil(math.hypot(xb-xa,zb-za)/.025))
        for j in range(steps):
            t=j/steps;x=xa+(xb-xa)*t;z=za+(zb-za)*t
            points.append((x,side*(shell_width(x,z)+offset),z))
    x,z=outline[-1];points.append((x,side*(shell_width(x,z)+offset),z))
    return line(name,points,mat,radius)


vertices=[]
for station in stations:
    vertices.extend((station[0],y,z) for y,z in body_section(*station))
count=21
faces=[tuple(reversed(range(count)))]
underside_faces=[]
for i in range(len(stations)-1):
    for j in range(count):
        if -.92<=stations[i][0] and stations[i+1][0]<=1.14 and 8<=j<=11:
            continue
        if j==count-1:underside_faces.append(len(faces))
        faces.append((i*count+j,i*count+(j+1)%count,(i+1)*count+(j+1)%count,(i+1)*count+j))
faces.append(tuple(range((len(stations)-1)*count,len(stations)*count)))
body=mesh('Formed steel body shell',vertices,[tuple(reversed(face)) for face in faces],paint,.004,smooth=True)
# The connected lower apron/underbody is coated black; silver side panels remain.
body.data.materials.append(black)
for index in underside_faces:body.data.polygons[index].material_index=1
back=vertices[8:13]
front=[(-2.116,y*.79/(.79*.941),z+.003) for x,y,z in back]
mesh('Blended bonnet leading lip',back+front,[(j,j+1,j+6,j+5) for j in range(4)],paint,.001,smooth=True)
for axle in [-1.235,1.145]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=80,radius=.323,depth=2.1,location=(axle,0,.29),rotation=(math.pi/2,0,0))
    cutter=bpy.context.object
    bpy.context.view_layer.objects.active=body
    mod=body.modifiers.new('Actual wheel opening','BOOLEAN')
    mod.operation,mod.object='DIFFERENCE',cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)


def rounded_outline(points, radius=.015, steps=5):
    result=[]
    points=[Vector(point) for point in points]
    for i,corner in enumerate(points):
        previous=points[i-1];following=points[(i+1)%len(points)]
        incoming=corner+(previous-corner).normalized()*radius
        outgoing=corner+(following-corner).normalized()*radius
        for j in range(steps+1):
            t=j/steps
            result.append(tuple((1-t)**2*incoming+2*t*(1-t)*corner+t*t*outgoing))
    return result


def glazing(name, points, outward, bow=.008, corner=.014):
    """A lightly bowed pane and rounded gasket, with a filled metal reveal."""
    normal=Vector(outward).normalized()
    edge_a=Vector(points[1])-Vector(points[0])
    edge_b=Vector(points[2])-Vector(points[0])
    if edge_a.cross(edge_b).dot(normal)<0:
        points=list(reversed(points))
    boundary=rounded_outline(points,corner)
    center=sum((Vector(p) for p in boundary),Vector())/len(boundary)
    vertices=[tuple(center+normal*bow)]
    rings=5;n=len(boundary)
    for ring in range(1,rings+1):
        t=ring/rings
        vertices.extend(tuple(center+(Vector(p)-center)*t+normal*bow*(1-t*t)) for p in boundary)
    faces=[(0,1+j,1+(j+1)%n) for j in range(n)]
    for ring in range(rings-1):
        for j in range(n):
            a=1+ring*n+j;b=1+ring*n+(j+1)%n
            faces.append((a,a+n,b+n,b))
    pane=mesh(name,vertices,faces,glass,smooth=True)
    assert all(polygon.normal.dot(normal)>.1 for polygon in pane.data.polygons), name+' has reversed glazing faces'
    line(name+' fitted rubber gasket',boundary+[boundary[0]],black,.0055)
    outer=[tuple(center+(Vector(p)-center)*1.035-normal*.001) for p in boundary]
    mesh(name+' sheet metal reveal',boundary+outer,[(j,j+n,(j+1)%n+n,(j+1)%n) for j in range(n)],paint,smooth=True)

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
        roof_faces.append((a,a+13,a+14,a+1))
roof_obj=mesh('Crowned roof skin',roof,roof_faces,paint,smooth=True)
solid=roof_obj.modifiers.new('Roof sheet thickness','SOLIDIFY');solid.thickness=.008
# Continuous formed header bridges the crowned roof to each screen gasket.
for name,roof_x,glass_x in [('Front roof header',-.49,-.505),('Rear roof header',.85,.865)]:
    header=[]
    for j in range(13):
        y=-.624+j*1.248/12
        z=1.373+.022*(1-(y/.64)**2)
        header.extend([(roof_x,y,z),(glass_x,y*.596/.624,1.357)])
    faces=[(j*2,j*2+1,j*2+3,j*2+2) for j in range(12)]
    if name.startswith('Front'):faces=[tuple(reversed(face)) for face in faces]
    mesh(name,header,faces,paint,smooth=True)
front_glass=[(-.903,-.701,.959),(-.903,.701,.959),(-.505,.596,1.357),(-.505,-.596,1.357)]
rear_glass=[(1.171,.697,.952),(1.171,-.697,.952),(.865,-.594,1.357),(.865,.594,1.357)]
for name,points in [('Front windscreen',front_glass),('Rear screen',rear_glass)]:
    glazing(name,points,(-1,0,.7) if name=='Front windscreen' else (1,0,.7),bow=.01,corner=.021)

for side in [-1,1]:
    def side_point(x,z,offset=0):
        return (x,side*(.754-(z-.95)*.131/.423+offset),z)
    front=[(-.869,.969),(-.449,1.346),(.092,1.346),(.092,.969)]
    rear=[(.159,.969),(.159,1.346),(.772,1.346),(1.102,.969)]
    for name,outline in [('Front door glazing',front),('Rear door glazing',rear)]:
        pts=[side_point(x,z) for x,z in outline]
        glazing(name,pts,(0,side,.15),bow=.006,corner=.012)
    # All pillar width comes from sheet surfaces; only narrow seals stand proud.
    pillar_shapes=[('A pillar',[(-.95,.941),(-.51,1.376),(-.45,1.357),(-.889,.948)]),('B pillar',[(.095,.944),(.095,1.367),(.153,1.367),(.153,.944)]),('C pillar',[(1.177,.941),(.876,1.373),(.792,1.367),(1.112,.946)])]
    for name,shape in pillar_shapes:
        mesh(name,[side_point(x,z,.002) for x,z in shape],[(0,1,2,3)],paint)
    line('Rear fixed quarter-light divider',[side_point(.879,.97,.003),side_point(.696,1.345,.003)],black,.005)
    line('Narrow rain gutter',[(-.49,side*.631,1.375),(.85,side*.631,1.375)],chrome,.0025)
    line('Window belt weatherstrip',[(-.927,side*.766,.945),(1.17,side*.766,.945)],black,.006)
    line('Thin bright sill trim',[(-.927,side*.768,.94),(1.17,side*.768,.94)],chrome,.002)
    # Continuous reveals bridge the screen edges to the door-side pillars.
    mesh('Joined front screen pillar reveal',[
        (-.95,side*.757,.941),(-.51,side*.624,1.376),
        (-.505,side*.596,1.357),(-.903,side*.701,.959)],[(0,1,2,3)],paint,smooth=True)
    mesh('Joined rear screen pillar reveal',[
        (1.177,side*.757,.941),(.876,side*.624,1.373),
        (.865,side*.594,1.357),(1.171,side*.697,.952)],[(0,1,2,3)],paint,smooth=True)
    mesh('Formed window lower sill',[
        (-.927,side*.766,.94),(1.17,side*.766,.94),
        (1.102,side*.748,.969),(-.869,side*.748,.969)],[(0,1,2,3)],paint,smooth=True)
    panel_path('Front door continuous shutline',[(-.915,.934),(-.80,.77),(-.755,.60),(-.727,.344),(.125,.344),(.125,.936)],side)
    panel_path('Rear door continuous shutline',[(.125,.344),(.765,.344),(.81,.44),(.865,.55),(.973,.63),(1.146,.929)],side)
    for x in [-.08,.91]:
        handle_y=shell_width(x,.862)
        box('Recessed door handle base',(x,side*(handle_y+.005),.862),(.115,.009,.043),black,.006)
        box('Black lift-up handle',(x,side*(handle_y+.015),.874),(.102,.018,.024),black,.005)
        cylinder('Small lock barrel',(x+.036,side*(handle_y+.026),.856),.006,.004,chrome,16)
    panel_path('Door lower pressed crease',[(-.78,.318),(.77,.318)],side,paint,.0035,.001)
    strip=[];stripe_points=[]
    for sx,sw,sz in stations:
        strip.extend([(sx,side*(shell_width(sx,.61)+.002),.61),(sx,side*(shell_width(sx,.648)+.002),.648)])
        stripe_points.append((sx,side*(shell_width(sx,.64)+.004),.64))
    mesh('Flat side rubbing molding',strip,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(stations)-1)],black)
    line('Fine side red coachline',stripe_points,stripe,.0025)
    box('Mirror triangular foot',(-.84,side*.791,.988),(.10,.044,.075),black,.007)
    box('Rounded black door mirror',(-.79,side*.869,1.006),(.178,.123,.102),black,.022)
    box('Mirror reflective face',(-.695,side*.872,1.006),(.004,.098,.079),chrome,.01)
    for axle in [-1.235,1.145]:
        lip=[]
        for j in range(49):
            t=j*math.pi/48
            for r in [.324,.339]:
                x=axle+math.cos(t)*r;z=.29+math.sin(t)*r
                lip.append((x,side*(shell_width(x,z)+.0015),z))
        mesh('Rolled wheel opening flange',lip,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(48)],paint,smooth=True)

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
    if side<0:quads=[tuple(reversed(face)) for face in quads]
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
        rim=wheel_lathe('Dished stamped steel wheel',axle,side,[(.001,.031),(.09,.031),(.125,.035),(.149,.050),(.167,.065),(.178,.070),(.181,.076),(.175,.081),(.167,.078),(.15,.062),(.125,.047),(.09,.052),(.001,.052)],steel)
        # Tangential oval slots pierce the pressed annulus, with a visible dark back.
        for j in range(12):
            t=j*math.tau/12;cut=[]
            for offset in [-.07,.15]:
                for k in range(24):
                    angle=k*math.tau/24
                    tangent=math.cos(angle)*.0155;radial=.147+math.sin(angle)*.0075
                    cut.append((axle+math.sin(t)*radial+math.cos(t)*tangent,side*(.705+offset),.292+math.cos(t)*radial-math.sin(t)*tangent))
            faces=[tuple(reversed(range(24))),tuple(range(24,48))]
            faces.extend((k,(k+1)%24,(k+1)%24+24,k+24) for k in range(24))
            if side>0:faces=[tuple(reversed(face)) for face in faces]
            cutter=mesh('Temporary oval wheel punch',cut,faces,black)
            bpy.context.view_layer.objects.active=rim
            mod=rim.modifiers.new('Punched oval wheel ventilation','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE'
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter,do_unlink=True)
        wheel_lathe('Shallow stamped steel center cap',axle,side,[(.001,.052),(.068,.052),(.084,.058),(.086,.063),(.079,.069),(.058,.071),(.001,.071)],steel)
        for j in range(4):
            t=j*math.tau/4
            cylinder('Four recessed lug nuts',(axle+math.sin(t)*.062,side*.782,.292+math.cos(t)*.062),.006,.006,chrome,16)
        cylinder('Small wheel center emblem',(axle,side*.779,.292),.018,.003,chrome,24)
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
        lower=.35+.045*(abs(y)/.815)**4 if front else .397
        verts.extend([(x,y,.622),(x+outward*.012,y,.585),(x,y,.469),(x-outward*.045,y*.987,lower)])
    faces=[]
    for i in range(len(path)-1):
        for j in range(3):faces.append((i*4+j,(i+1)*4+j,(i+1)*4+j+1,i*4+j+1))
    if not front:faces=[tuple(reversed(face)) for face in faces]
    obj=mesh(name,verts,faces,black,.014,smooth=True)
    solid=obj.modifiers.new('Molded bumper thickness','SOLIDIFY');solid.thickness=.025
    line(name+' red insert',[(x+(-.017 if front else .017),y,.596) for x,y in path],stripe,.003)
    return obj
front_bumper=bumper('Front continuous wraparound bumper',True)
bumper('Rear continuous wraparound bumper',False)
# Cut real intake apertures through the same molded front apron; no extra plank.
for modifier in list(front_bumper.modifiers):
    bpy.context.view_layer.objects.active=front_bumper
    bpy.ops.object.modifier_apply(modifier=modifier.name)
for side in [-1,1]:
    cutter=box('Temporary bumper intake cutter',(-2.105,side*.436,.414),(.20,.358,.073),black,.009)
    bpy.context.view_layer.objects.active=cutter
    bpy.ops.object.modifier_apply(modifier=cutter.modifiers[0].name)
    bpy.context.view_layer.objects.active=front_bumper
    mod=front_bumper.modifiers.new('Recessed lower cooling opening','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    box('Dark intake interior',(-2.052,side*.436,.414),(.012,.359,.075),rubber,.006)
    for y in [side*.34,side*.46,side*.58]:
        box('Cooling grille recessed vertical bar',(-2.086,y,.414),(.009,.009,.069),black,.001)


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
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=.010,location=(-2.093,center,.759))
    bulb=bpy.context.object;bulb.name='Visible headlamp bulb';bulb.scale=(.7,1,1);bulb.parent=root;bulb.data.materials.append(chrome)
    # The lens remains almost clear; fine prisms never obscure the circular bowl.
    mesh('Clear rectangular headlamp lens',[(-2.122,center-.159,.678),(-2.122,center+.159,.678),(-2.122,center+.159,.84),(-2.122,center-.159,.84)],[(0,1,2,3)],lens)
    for j in range(25):
        y=center-.147+j*.01225
        line('Fine glass lens vertical prism',[(-2.123,y,.683),(-2.123,y,.835)],lens_rib,.00085)
    for z in [.696,.722,.748,.774,.8,.826]:
        line('Subtle lens cross-prism',[(-2.123,center-.152,z),(-2.123,center+.152,z)],lens_rib,.0006)
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
    box('Rear clear reversing cell',(2.079,side*.448,.803),(.006,.078,.069),white,.003)
    line('Rear lamp center separator',[(2.083,side*.369,.755),(2.083,side*.785,.755)],black,.002)
    for j in range(16):
        y=side*(.410+j*.017)
        line('Rear lens fine vertical flute',[(2.079,y,.672),(2.079,y,.746)],red,.0008)
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
panel_path('Fuel door',[(1.54,.844),(1.71,.834),(1.71,.702),(1.54,.707),(1.54,.844)],1)

# The rear plate belongs to the recessed black panel between the tail lamps.
box('Recessed rear registration panel',(2.06,0,.752),(.028,.733,.213),black,.006)
for x,height in [(-2.152,.478),(2.082,.752)]:
    rotation=(math.pi/2,0,-math.pi/2) if x<0 else (math.pi/2,0,math.pi/2)
    box('Black display plate',(x,0,height),(.008,.465,.196),black,.004)
    outside=x+(-.006 if x<0 else .006)
    outline=[(outside,-.23,height-.095),(outside,.23,height-.095),(outside,.23,height+.095),(outside,-.23,height+.095),(outside,-.23,height-.095)]
    line('Fine plate border',outline,white,.0015)
    outward=x+(-.011 if x<0 else .011)
    label('Display plate name','PROTON',(outward,0,height+.054),.051,white,rotation)
    label('Display plate model','SAGA',(outward,0,height-.001),.056,white,rotation)
    label('Display plate year','(1985)',(outward,0,height-.054),.037,white,rotation)
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
