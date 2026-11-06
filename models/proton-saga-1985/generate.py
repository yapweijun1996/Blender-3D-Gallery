"""Reference-led 1985 Saga panel reconstruction. Blender 5.1.2 + cwebp."""
import bpy
import math
import subprocess
import shutil
import sys
import json
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path(__file__).resolve().parent
TEXTURES = OUT/'textures'
TEXTURES.mkdir(exist_ok=True)
front_reference=TEXTURES/'heritage-front-reference.png'
if not front_reference.exists():
    shutil.copy2('/Users/yapweijun/Downloads/1985 Proton Saga Heritage Showcase.png',front_reference)
rear_reference=TEXTURES/'heritage-multiview-reference.png'
if not rear_reference.exists():
    shutil.copy2('/Users/yapweijun/Downloads/Proton Saga 1985 Heritage Showcase.png',rear_reference)
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


paint = material('Silver metallic body', (.36, .385, .41), .72, .26)
black = material('Black molded trim', (.004, .005, .006), 0, .68)
black.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.15
rubber = material('Tire sidewall', (.012, .014, .017), 0, .88)
glass = material('Neutral smoky glazing', (.022, .028, .034), 0, .10, .36)
glass.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.10
steel = material('Satin pressed steel', (.39, .41, .42), .78, .28)
wheel_steel = material('Silver pressed wheel rim', (.56, .58, .60), .72, .30)
wheel_cap = material('Silver domed wheel cover', (.62, .64, .66), .70, .27)
chrome = material('Polished narrow trim', (.52, .55, .57), .85, .22)
reflector = material('Aluminized lamp reflector', (.31, .33, .34), .55, .48)
reflector_light = material('Reflector fine facets', (.42, .44, .45), .50, .42)
reflector_dark = material('Reflector shaded facets', (.16, .18, .19), .42, .54)
optical_gradient = material('Continuously shaded optical reflector', (.37, .39, .40), .40, .28)
vertex_color = optical_gradient.node_tree.nodes.new('ShaderNodeVertexColor')
vertex_color.layer_name = 'ReflectorTone'
optical_gradient.node_tree.links.new(vertex_color.outputs['Color'], optical_gradient.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
lens = material('Fluted headlamp glass', (.72, .75, .77), .02, .09, .06)
lens_rib = material('Fine lens prism', (.40, .43, .44), .15, .35, .35)
red = material('Red rear lens', (.19, .002, .004), .16, .21)
amber = material('Amber corner lens', (.40, .064, .001), .12, .27)
amber_prism = material('Amber lens internal facets', (.30, .065, .004), .12, .36)
stripe = material('Thin red pinstripe', (.52, .012, .018), .2, .33)
fabric = material('Dark woven seat cloth', (.042, .05, .057), 0, .95)
white = material('Plate lettering', (.8, .83, .84), .1, .4)
navy = material('Heritage shield navy', (.015, .055, .13), .4, .28)
gold = material('Heritage shield gold', (.9, .57, .012), .5, .3)
# The model uses image-based lens appearance from the reference supplied for
# this task. The UVs select only each headlamp; the original image is embedded
# and its provenance must accompany any future redistribution.
reference_image=bpy.data.images.load(str(front_reference),check_existing=True)
reference_image.pack()
reference_lens=material('Reference-derived glass headlamp', (1,1,1), .04, .28)
image_node=reference_lens.node_tree.nodes.new('ShaderNodeTexImage')
image_node.image=reference_image
reference_lens.node_tree.links.new(image_node.outputs['Color'],reference_lens.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
rear_reference_image=bpy.data.images.load(str(rear_reference),check_existing=True)
rear_reference_image.pack()
rear_reference_lens=material('Reference-derived rear lens', (1,1,1), .03, .32)
rear_image_node=rear_reference_lens.node_tree.nodes.new('ShaderNodeTexImage')
rear_image_node.image=rear_reference_image
rear_reference_lens.node_tree.links.new(rear_image_node.outputs['Color'],rear_reference_lens.node_tree.nodes['Principled BSDF'].inputs['Base Color'])


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


def line(name, points, mat, radius=.002, resolution=0):
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
    data.resolution_u = 3
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


reverse_lens = material('Clear reversing lens', (.53,.57,.59), .25, .22)
fabric_seam = material('Upholstery seam',(.027,.031,.035),0,.95)
defroster = material('Heated glass copper',(.035,.013,.005),.1,.9)
underseal = material('Deep matte underseal',(.002,.0025,.003),0,1)
underseal.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=0
plate_black = material('Registration plate black ink',(.0015,.0017,.002),0,.5)
plate_black.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.1

# Reference landmarks are an artistic fit to the approved four-view image set.
# X points rearward, Y right, Z up; no factory dimensions are implied.
AXLES = (-1.31, 1.17)
WHEEL_Z = .359
ARCH_RX, ARCH_RZ = .323, .322
BODY_LOWERING = .075
WHEEL_RADIUS_SCALE = .90
BODY_ENDS = (-2.065, 2.065)


def interp(knots, x):
    for (xa, ya), (xb, yb) in zip(knots, knots[1:]):
        if x <= xb:
            t = max(0, min(1, (x-xa)/(xb-xa)))
            return ya+(yb-ya)*t
    return knots[-1][1]


def crown_height(x):
    return interp([(-2.065,.87),(-1.98,.895),(-1.65,.945),(-1.15,.981),
                   (-.87,.988),(.6,.988),(1.43,.988),(1.85,.974),(2.065,.956)], x)


def arch_bottom(x):
    # End panels meet the bottom of the bumper; the wheel openings alone cut
    # farther into the lower sheet metal. This avoids loose triangular slivers.
    if x < AXLES[0]-ARCH_RX:base=.400
    elif x > AXLES[1]+ARCH_RX:base=.380
    else:base=.248
    for axle in AXLES:
        distance=abs(x-axle)
        if distance<ARCH_RX:
            base=max(base,WHEEL_Z+ARCH_RZ*math.sqrt(max(0,1-(distance/ARCH_RX)**2)))
    return base


def side_width(x, z):
    height = crown_height(x)
    width = interp([(.245,.749),(.29,.773),(.46,.796),(.575,.807),(.64,.811),
                    (.76,.805),(height-.065,.792),(height-.025,.776),(height,.750)], z)
    # Broader pressed metal flares blend into each wing instead of an added ring.
    for axle in AXLES:
        radial = math.sqrt(((x-axle)/ARCH_RX)**2+((z-WHEEL_Z)/ARCH_RZ)**2)
        width += .016*math.exp(-((radial-1.09)/.17)**2)
    end=max(0,(abs(x)-1.82)/.245)**2
    upper=max(0,min(1,(z-height+.09)/.09))
    # The nose and tail shoulders meet the outer lamp corners; cabin belt width
    # must not inadvertently narrow the bonnet and leave the indicators exposed.
    width += end*(-.008+.032*upper*upper*(3-2*upper))
    return width


def side_point(x,z,side,offset=0):
    return (x,side*(side_width(x,z)+offset),z)


def surface_path(name, outline, side, mat=black, radius=.0017, offset=.0015):
    points=[]
    for (xa,za),(xb,zb) in zip(outline,outline[1:]):
        steps=max(2,math.ceil(math.hypot(xb-xa,zb-za)/.028))
        for j in range(steps):
            t=j/steps
            points.append(side_point(xa+(xb-xa)*t,za+(zb-za)*t,side,offset))
    points.append(side_point(*outline[-1],side,offset))
    return line(name,points,mat,radius)


def rounded_outline(points, radius=.014, steps=5):
    result=[]
    points=[Vector(point) for point in points]
    for i,corner in enumerate(points):
        previous=points[i-1];following=points[(i+1)%len(points)]
        r=min(radius,(previous-corner).length*.35,(following-corner).length*.35)
        incoming=corner+(previous-corner).normalized()*r
        outgoing=corner+(following-corner).normalized()*r
        for j in range(steps+1):
            t=j/steps
            result.append(tuple((1-t)**2*incoming+2*t*(1-t)*corner+t*t*outgoing))
    return result


def surface_disk(name, boundary, normal, mat, bow=0, rings=4):
    normal=Vector(normal).normalized()
    pts=[Vector(p) for p in boundary]
    if (pts[1]-pts[0]).cross(pts[2]-pts[1]).dot(normal)<0:
        pts.reverse()
    center=sum(pts,Vector())/len(pts)
    verts=[tuple(center+normal*bow)]
    n=len(pts)
    for i in range(1,rings+1):
        t=i/rings
        verts.extend(tuple(center+(p-center)*t+normal*bow*(1-t*t)) for p in pts)
    faces=[(0,1+j,1+(j+1)%n) for j in range(n)]
    for i in range(rings-1):
        for j in range(n):
            a=1+i*n+j;b=1+i*n+(j+1)%n
            faces.append((a,a+n,b+n,b))
    return mesh(name,verts,faces,mat,smooth=True)


def glazing(name, outline, normal, corner=.018, bow=.007):
    boundary=rounded_outline(outline,corner)
    pane=surface_disk(name,boundary,normal,glass,bow)
    outward=Vector(normal).normalized()
    assert all(p.normal.dot(outward)>.05 for p in pane.data.polygons), name
    line(name+' rubber channel',boundary+[boundary[0]],black,.0045)
    # The bright edge is a small separate bead; it never substitutes for a pillar.
    center=sum((Vector(p) for p in boundary),Vector())/len(boundary)
    bright=[tuple(center+(Vector(p)-center)*1.018-outward*.001) for p in boundary]
    line(name+' narrow metal surround',bright+[bright[0]],chrome,.0014)
    return pane


# Build the wings and individual door skins as separate fitted panels. Shared
# surface equations keep the adjacent panels aligned; small physical gaps form
# the shut lines instead of painting door outlines on one uninterrupted slab.
def front_shut(z):
    return interp([(.24,-.77),(.49,-.81),(.70,-.83),(.89,-.86),(.988,-.89)],z)


def rear_shut(z):
    return interp([(.24,.847),(.31,.847),(.43,.91),(.53,.96),(.61,1.12),(.68,1.31),(.82,1.355),(.985,1.375)],z)


def clip_polygon(poly, signed_distance):
    clipped=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da,db=signed_distance(a),signed_distance(b)
        if da>=0:clipped.append(a)
        if (da>=0)!=(db>=0):
            clipped.append(a+(b-a)*(da/(da-db)))
    return clipped


stations=set(-2.065+i*4.13/120 for i in range(121))
for axle in AXLES:
    stations.update(axle+ARCH_RX*math.cos(j*math.pi/48) for j in range(49))
    stations.update([axle-ARCH_RX-.001,axle+ARCH_RX+.001])
stations=sorted(stations)
for side in [-1,1]:
    grid=[];levels=12
    for x in stations:
        lower=arch_bottom(x);upper=crown_height(x)
        grid.append([Vector(side_point(x,lower+(upper-lower)*j/(levels-1),side)) for j in range(levels)])
    # Signed distances are positive inside each panel. Gaps expose black recesses.
    gap=.0010
    definitions=[('Front wing', [lambda p:front_shut(p.z)-p.x-gap]),
                 ('Front door', [lambda p:p.x-front_shut(p.z)-gap,lambda p:.25-p.x-gap]),
                 ('Rear door', [lambda p:p.x-.25-gap,lambda p:rear_shut(p.z)-p.x-gap]),
                 ('Rear quarter', [lambda p:p.x-rear_shut(p.z)-gap])]
    for panel_name,limits in definitions:
        vertices=[];faces=[];lookup={}
        def vertex_index(v):
            key=tuple(round(n,8) for n in v)
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(tuple(v))
            return lookup[key]
        for i in range(len(stations)-1):
            for j in range(levels-1):
                polygon=[grid[i][j],grid[i+1][j],grid[i+1][j+1],grid[i][j+1]]
                for limit in limits:
                    polygon=clip_polygon(polygon,limit)
                    if len(polygon)<3:break
                if len(polygon)>=3:
                    face=tuple(vertex_index(v) for v in polygon)
                    faces.append(face if side<0 else tuple(reversed(face)))
        prefix=('Left ' if side<0 else 'Right ')+panel_name
        mesh(prefix+' panel',vertices,faces,paint,smooth=True)
        # Add only the visible turned edges, instead of duplicating an entire
        # hidden inner skin for each door and wing in the interactive GLB.
        edges={}
        for face in faces:
            for a,b in zip(face,face[1:]+face[:1]):
                key=tuple(sorted((a,b)))
                if key in edges:edges[key]=None
                else:edges[key]=(a,b)
        edge_vertices=[];edge_faces=[]
        for edge in edges.values():
            if edge is None:continue
            a,b=edge;p=Vector(vertices[a]);q=Vector(vertices[b])
            inward=Vector((0,-side*.004,0));i=len(edge_vertices)
            edge_vertices.extend([tuple(p),tuple(q),tuple(q+inward),tuple(p+inward)])
            edge_faces.append((i,i+1,i+2,i+3))
        if edge_faces:mesh(prefix+' folded edge',edge_vertices,edge_faces,paint)
    # Return the lips into the wheel wells so openings have real thickness.
    for axle in AXLES:
        vertices=[]
        for j in range(97):
            t=j*math.pi/96
            x=axle+ARCH_RX*math.cos(t);z=WHEEL_Z+ARCH_RZ*math.sin(t)
            w=side_width(x,z)
            vertices.extend([(x,side*w,z),(x,side*(w-.010),z-.003),(x,side*.665,z-.006)])
        faces=[]
        for j in range(96):
            for k in range(2):
                a=j*3+k;faces.append((a,a+3,a+4,a+1))
        arch=mesh('Folded wheel arch return',vertices,faces,black,smooth=True)
        arch.data.materials.append(paint)
        for face in arch.data.polygons:
            if face.index%2==0:face.material_index=1
    box('Pressed rocker sill',(-.03,side*.765,.263),(1.82,.038,.052),paint,.014)
    box('Black sill lower seam',(-.03,side*.748,.232),(1.9,.032,.02),black,.007)


def deck(name, start, end):
    verts=[];nx=29;ny=19
    for i in range(nx):
        x=start+(end-start)*i/(nx-1)
        h=crown_height(x)
        for j in range(ny):
            u=-1+2*j/(ny-1)
            # Soft crown and subtle paired pressed creases form a continuous hood.
            z=h+.020*(1-u*u)
            if start<0:
                z+=.004*math.exp(-((abs(u)-.79)/.05)**2)*math.sin(i*math.pi/(nx-1))
            verts.append((x,u*side_width(x,h),z))
    faces=[]
    for i in range(nx-1):
        for j in range(ny-1):
            a=i*ny+j;faces.append((a,a+ny,a+ny+1,a+1))
    obj=mesh(name,verts,faces,paint,smooth=True)
    solid=obj.modifiers.new('Folded panel thickness','SOLIDIFY');solid.thickness=.006
    return obj


deck('Crowned bonnet',-2.065,-.865)
deck('Crowned boot lid',1.43,2.065)
for side in [-1,1]:
    line('Bonnet panel shutline',[(x,side*.690,crown_height(x)+.004) for x in [-2.055,-1.99,-1.8,-1.5,-1.2,-.87]],black,.0015)
    line('Boot panel shutline',[(x,side*.69,crown_height(x)+.004) for x in [1.44,1.6,1.8,2.05]],black,.0015)
box('Front panel behind grille',(-2.027,0,.748),(.045,1.54,.23),black,.008)
box('Rear body face',(2.04,0,.814),(.047,1.51,.286),paint,.018)
box('Dark chassis tray',(0,0,.242),(2.55,1.28,.035),underseal,.012)
for end,lower in [(-2.065,.856),(2.065,.947)]:
    verts=[]
    for j in range(41):
        u=-1+2*j/40;y=u*side_width(end,crown_height(end))
        z=crown_height(end)+.020*(1-u*u)
        verts.extend([(end,y,z),(end+(-.009 if end<0 else .009),y,lower)])
    mesh('Folded bonnet front edge' if end<0 else 'Folded boot rear edge',verts,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(40)],paint,smooth=True)

# Crowned roof, formed screen reveals and thin door frames all meet at shared
# landmarks. The former wide rectangular roof bars are intentionally removed.
roof=[];nx=19;ny=21
for i in range(nx):
    x=-.345+1.385*i/(nx-1)
    for j in range(ny):
        u=-1+2*j/(ny-1)
        z=1.446+.022*(1-u*u)+.006*math.sin(i*math.pi/(nx-1))
        roof.append((x,u*.625,z))
roof_faces=[(i*ny+j,(i+1)*ny+j,(i+1)*ny+j+1,i*ny+j+1) for i in range(nx-1) for j in range(ny-1)]
obj=mesh('Continuous crowned roof',roof,roof_faces,paint,smooth=True)
solid=obj.modifiers.new('Roof skin thickness','SOLIDIFY');solid.thickness=.009

front_screen=[(-.855,-.716,1.004),(-.855,.716,1.004),(-.333,.602,1.431),(-.333,-.602,1.431)]
rear_screen=[(1.432,.713,1.004),(1.432,-.713,1.004),(1.032,-.601,1.431),(1.032,.601,1.431)]
glazing('Front windscreen',front_screen,(-.65,0,.8),.028,.012)
glazing('Rear screen',rear_screen,(.75,0,.7),.028,.010)
for name,rx,gx in [('Front roof edge',-.345,-.333),('Rear roof edge',1.04,1.032)]:
    points=[]
    for j in range(33):
        u=-1+2*j/32
        points.extend([(rx,u*.625,1.446+.022*(1-u*u)),(gx,u*.602,1.431)])
    mesh(name,points,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(32)],paint,smooth=True)


def cabin_point(x,z,side,offset=0):
    return (x,side*(.755-(z-.988)*.130/.458+offset),z)


for side in [-1,1]:
    front=[(-.805,1.008),(-.297,1.424),(.225,1.424),(.225,1.008)]
    rear=[(.284,1.008),(.284,1.424),(.825,1.424),(.850,1.008)]
    quarter=[(.875,1.008),(.848,1.424),(.895,1.424),(1.300,1.008)]
    for name,outline in [('Front door window',front),('Rear door window',rear),('Fixed rear quarterlight',quarter)]:
        glazing(name,[cabin_point(x,z,side) for x,z in outline],(0,side,.28),.012,.005)
    pillars=[('Slender A pillar',[(-.86,.989),(-.355,1.448),(-.302,1.433),(-.815,.995)]),
             ('Painted B pillar',[(.235,.986),(.235,1.447),(.274,1.447),(.274,.986)]),
             ('Formed C pillar',[(1.438,.985),(1.052,1.448),(.902,1.435),(1.315,.989)])]
    for name,outline in pillars:
        points=[cabin_point(x,z,side,.002) for x,z in outline]
        normal=(Vector(points[1])-Vector(points[0])).cross(Vector(points[2])-Vector(points[0]))
        face=(0,1,2,3) if normal.y*side>0 else (3,2,1,0)
        obj=mesh(name,points,[face],paint,.003,smooth=True)
        obj.data.materials.append(black)
        solid=obj.modifiers.new('Pillar section thickness','SOLIDIFY');solid.thickness=.018
        solid.material_offset=1;solid.material_offset_rim=1
    for name,points in [
        ('Front pillar reveal',[cabin_point(-.86,.989,side),cabin_point(-.355,1.448,side),(-.333,side*.602,1.431),(-.855,side*.716,1.004)]),
        ('Rear pillar reveal',[cabin_point(1.438,.985,side),cabin_point(1.052,1.448,side),(1.032,side*.601,1.431),(1.432,side*.713,1.004)])]:
        outward=Vector((-1 if name.startswith('Front') else 1,side,.2))
        normal=(Vector(points[1])-Vector(points[0])).cross(Vector(points[2])-Vector(points[0]))
        face=(0,1,2,3) if normal.dot(outward)>0 else (3,2,1,0)
        obj=mesh(name,points,[face],paint,smooth=True)
        obj.data.materials.append(black)
        solid=obj.modifiers.new('Reveal interior lining','SOLIDIFY');solid.thickness=.008
        solid.material_offset=1;solid.material_offset_rim=1
    # Roof rail and lower window ledge close the narrow gaps around the glass.
    mesh('Roof rail', [cabin_point(-.34,1.443,side),cabin_point(1.04,1.443,side),cabin_point(1.01,1.43,side),cabin_point(-.32,1.43,side)],[(0,1,2,3)],paint,smooth=True)
    mesh('Window belt ledge',[side_point(-.91,.988,side),side_point(1.438,.988,side),cabin_point(1.35,1.006,side),cabin_point(-.805,1.006,side)],[(0,1,2,3)],paint,smooth=True)
    line('Rain gutter bead',[(-.345,side*.628,1.445),(-.1,side*.629,1.45),(.7,side*.629,1.45),(1.04,side*.628,1.445)],chrome,.0023)
    line('Lower window weatherstrip',[cabin_point(-.84,1.000,side,.004),cabin_point(1.38,1.000,side,.004)],black,.005)
    surface_path('Front door shutline',[(-.89,.984),(-.86,.89),(-.83,.70),(-.81,.49),(-.77,.31),(.25,.31),(.25,.985)],side)
    # The door seam ends on the wheel opening; it cannot continue across air.
    surface_path('Rear door shutline',[(.25,.31),(.847,.31)],side)
    surface_path('Rear door upper shutline',[(1.31,arch_bottom(1.31)+.004),(1.355,.82),(1.375,.985)],side)
    surface_path('Door lower pressed contour',[(-.77,.322),(.85,.322)],side,paint,.0022,.002)
    for index,x in enumerate([.09,1.06]):
        y=side_width(x,.907)
        box('Door handle recess',(x,side*(y+.002),.907),(.165,.009,.064),black,.014)
        box('Black lift handle',(x,side*(y+.014),.919),(.152,.024,.036),black,.009)
        if index==0:
            cylinder('Front door lock',(x+.055,side*(y+.018),.851),.009,.005,chrome,24)
            cylinder('Lock key slot',(x+.055,side*(y+.021),.851),.004,.005,black,12)
    for xa,xb in [(-2.055,-.86),(-.845,.238),(.263,1.31),(1.33,2.055)]:
        points=[]
        for j in range(31):
            x=xa+(xb-xa)*j/30
            points.extend([side_point(x,.587,side,.005),side_point(x,.641,side,.005)])
        faces=[]
        for j in range(30):
            xm=xa+(xb-xa)*(j+.5)/30
            if arch_bottom(xm)<.582:faces.append((j*2,j*2+2,j*2+3,j*2+1))
        obj=mesh('Individual rubber side molding',points,faces,black,.002,smooth=True)
        solid=obj.modifiers.new('Molding depth','SOLIDIFY');solid.thickness=.007
        run=[]
        for j in range(121):
            x=xa+(xb-xa)*j/120
            if arch_bottom(x)<.582:run.append((x,.624))
            elif run:
                if len(run)>1:surface_path('Red side molding insert',run,side,stripe,.0025,.013)
                run=[]
        if len(run)>1:surface_path('Red side molding insert',run,side,stripe,.0025,.013)
    # The bumper end wraps across the small panel area immediately ahead of
    # the wheel opening, avoiding an exposed painted wedge below the moulding.
    start,end=-1.645,-1.595
    vertices=[];faces=[];count=32
    for j in range(count+1):
        x=start+(end-start)*j/count
        bottom=arch_bottom(x)
        vertices.extend([side_point(x,bottom,side,.009),side_point(x,max(bottom,.624),side,.009)])
    for j in range(count):
        x=start+(end-start)*(j+.5)/count
        if arch_bottom(x)<.624:
            face=(j*2,j*2+2,j*2+3,j*2+1)
            faces.append(face if side<0 else tuple(reversed(face)))
    if faces:mesh('Moulded front bumper arch transition',vertices,faces,black,smooth=True)
    # A tapered housing with a small fitted sail panel replaces the old cube.
    mount=[cabin_point(-.82,1.006,side,.002),cabin_point(-.66,1.006,side,.002),cabin_point(-.67,1.128,side,.002)]
    mesh('Mirror sail panel',mount,[(0,1,2)],black,.006)
    housing=[(-.83,side*.787,1.015),(-.64,side*.787,1.015),(-.63,side*.958,1.025),(-.82,side*.946,1.025),
             (-.82,side*.791,1.119),(-.66,side*.791,1.126),(-.64,side*.948,1.118),(-.81,side*.94,1.118)]
    mesh('Tapered black door mirror',housing,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)],black,.013,smooth=True)
    mesh('Inset mirror glass',[(-.625,side*.81,1.033),(-.625,side*.935,1.036),(-.635,side*.936,1.106),(-.65,side*.81,1.113)],[(0,1,2,3)],chrome,.004)
    box('Amber wing repeater',(-1.01,side*(side_width(-1.01,.728)+.006),.728),(.063,.012,.025),amber,.006)
    for axle in AXLES:
        box('Flexible black mud flap',(axle+.367,side*.758,.306),(.016,.14,.22),black,.015)

# An inset rounded filler door lives only on the physical right rear quarter.
fuel=rounded_outline([(1.56,.77),(1.56,.925),(1.75,.925),(1.75,.77)],.022)
surface_path('Rounded fuel flap',fuel+[fuel[0]],1,black,.0018,.001)

# Both wipers park below the primary view through the windscreen.
box('Cowl vent recess',(-.871,0,.99),(.063,1.37,.015),black,.007)
for j in range(40):
    y=-.65+j*1.3/39
    line('Cowl vent slot',[(-.903,y,.999),(-.85,y,1.001)],black,.0015)
for y in [-.42,.23]:
    line('Wiper articulated arm',[(-.854,y,1.012),(-.807,y+.19,1.054),(-.799,y+.33,1.058)],black,.0038)
    line('Wiper blade',[(-.805,y+.04,1.052),(-.798,y+.49,1.060)],black,.0048)
    cylinder('Wiper pivot',(-.854,y,1.01),.009,.009,black,16,(0,0,0))
for side in [-1,1]:
    box('Bonnet washer nozzle',(-1.02,side*.45,.994),(.015,.011,.009),black,.003)


def lathe(name, axle, side, profile, mat, segments=64):
    verts=[]
    for r,offset in profile:
        for j in range(segments):
            t=j*math.tau/segments
            verts.append((axle+math.sin(t)*r,side*(.709+offset),WHEEL_Z+math.cos(t)*r))
    faces=[]
    for i in range(len(profile)-1):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments
            face=(a,b,b+segments,a+segments)
            faces.append(face if side>0 else tuple(reversed(face)))
    return mesh(name,verts,faces,mat,smooth=True)


# Opaque inner wheelhouses are part of the vehicle, not part of the floor.
# They prevent the opposite wheel or studio background showing through the
# narrow clearance between each tire and its opening.
for side in [-1,1]:
    for axle in AXLES:
        radius=ARCH_RX+.012
        vertices=[(axle,side*.635,WHEEL_Z)]
        for j in range(96):
            angle=math.tau*j/96
            x=axle+radius*math.sin(angle)
            z=max(.10,WHEEL_Z+radius*math.cos(angle))
            vertices.append((x,side*.635,z))
        faces=[]
        for j in range(96):
            face=(0,1+j,1+(j+1)%96)
            faces.append(face if side<0 else tuple(reversed(face)))
        mesh('Dark recessed wheelhouse liner',vertices,faces,underseal)


for side in [-1,1]:
    for axle in AXLES:
        before_wheel=set(root.children)
        tire=[(.188,-.066),(.219,-.080),(.277,-.083),(.302,-.067),(.313,-.042),(.315,-.02),(.315,.025),(.309,.060),(.291,.080),(.259,.09),(.215,.088),(.188,.073)]
        lathe('High profile radial tire',axle,side,tire,rubber,56)
        for radius,offset in [(.204,.083),(.273,.086),(.296,.075)]:
            lathe('Tire molded circumferential rib',axle,side,[(radius-.001,offset),(radius,offset+.0008),(radius+.001,offset)],rubber,64)
        for j in range(44):
            t=j*math.tau/44
            for band in [-1,1]:
                points=[]
                for offset,dt in [(band*.008,-.014),(band*.036,.005),(band*.060,.021)]:
                    radius=.315 if abs(offset)<.04 else .310
                    points.append((axle+math.sin(t+dt)*radius,side*(.709+offset),WHEEL_Z+math.cos(t+dt)*radius))
                line('Tire tread channel',points,black,.0013)
        rim=lathe('Pressed steel wheel with punched vents',axle,side,[(.001,.037),(.102,.037),(.131,.044),(.158,.057),(.181,.068),(.190,.075),(.191,.082),(.187,.086),(.178,.084),(.155,.073),(.125,.058),(.001,.058)],wheel_steel,64)
        for j in range(12):
            t=j*math.tau/12;verts=[]
            for offset in [-.04,.15]:
                for k in range(20):
                    a=k*math.tau/20
                    tang=.019*math.cos(a);rad=.160+.008*math.sin(a)
                    verts.append((axle+math.sin(t)*rad+math.cos(t)*tang,side*(.709+offset),WHEEL_Z+math.cos(t)*rad-math.sin(t)*tang))
            faces=[tuple(reversed(range(20))),tuple(range(20,40))]+[(k,(k+1)%20,(k+1)%20+20,k+20) for k in range(20)]
            if side>0:faces=[tuple(reversed(f)) for f in faces]
            cutter=mesh('Temporary wheel slot punch',verts,faces,black)
            bpy.context.view_layer.objects.active=rim
            mod=rim.modifiers.new('Pressed oval ventilation','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE'
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter,do_unlink=True)
        # The pressed rim retains real apertures and a separate domed cover.
        cover=lathe('Shallow silver wheel cover',axle,side,[(.001,.059),(.10,.059),(.127,.064),(.132,.069),(.131,.074),(.123,.079),(.108,.081),(.075,.087),(.001,.091)],wheel_cap,48)
        # The rim apertures and domed center use actual geometry and metal.
        lathe('Wheel cover narrow rolled edge',axle,side,[(.123,.080),(.126,.083),(.128,.081)],chrome,64)
        cylinder('Small wheel cover center',(axle,side*.806,WHEEL_Z),.026,.004,steel,32)
        cylinder('Dark brake backing',(axle,side*.736,WHEEL_Z),.180,.012,black,24)
        t=.78
        cylinder('Rubber tire valve',(axle+math.sin(t)*.177,side*.799,WHEEL_Z+math.cos(t)*.177),.004,.012,black,12)
        # Reference silhouette calls for a smaller tire while retaining sidewall
        # depth. Transform every rim, tread and valve around the same wheel hub.
        wheel_scale=(Matrix.Translation((axle,0,WHEEL_Z)) @
                     Matrix.Diagonal((WHEEL_RADIUS_SCALE,1,WHEEL_RADIUS_SCALE,1)) @
                     Matrix.Translation((-axle,0,-WHEEL_Z)))
        for part in set(root.children)-before_wheel:
            part.matrix_world=wheel_scale @ part.matrix_world



def bumper(name, front):
    sign=-1 if front else 1
    curve=[(2.13,0),(2.128,.46),(2.117,.69),(2.091,.775),(2.045,.811),(1.97,.824),(1.64 if front else 1.55,.816)]
    path=[(sign*x,-y) for x,y in reversed(curve[1:])]+[(sign*x,y) for x,y in curve]
    profile=[(.654,-.012),(.642,.002),(.615,.014),(.53,.009),(.48,0),(.400,-.010)]
    if not front:profile=[(.654,-.012),(.642,.002),(.615,.012),(.535,.012),(.46,-.005),(.38,-.008)]
    verts=[]
    for x,y in path:
        for z,offset in profile:
            verts.append((x+sign*offset,y*(1-.014*(.654-z)/.32),z))
    n=len(profile)
    faces=[]
    for i in range(len(path)-1):
        for j in range(n-1):
            a=i*n+j;face=(a,a+n,a+n+1,a+1)
            faces.append(face if front else tuple(reversed(face)))
    # Molded side ends return inward to meet the body and hide the hollow shell.
    for end in [0,len(path)-1]:
        outer=[end*n+j for j in range(n)]
        inner=[]
        for k in outer:
            x,y,z=verts[k];inner.append(len(verts));verts.append((x,y*.86,z))
        for j in range(n-1):
            face=(outer[j],outer[j+1],inner[j+1],inner[j])
            faces.append(face if end==0 else tuple(reversed(face)))
    obj=mesh(name,verts,faces,black,.008,smooth=True)
    solid=obj.modifiers.new('Molded bumper wall','SOLIDIFY');solid.thickness=.022
    line(name+' red inlay',[(x+sign*.016,y,.624) for x,y in path],stripe,.0027)
    line(name+' top rubber bead',[(x+sign*.001,y,.646) for x,y in path],black,.004)
    return obj


front_bumper=bumper('Molded front bumper and apron',True)
bumper('Molded rear bumper and apron',False)
bpy.context.view_layer.objects.active=front_bumper
for mod in list(front_bumper.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
for side in [-1,1]:
    cutter=box('Temporary lower intake',(-2.1,side*.425,.462),(.24,.39,.087),black,.014)
    bpy.context.view_layer.objects.active=cutter
    bpy.ops.object.modifier_apply(modifier=cutter.modifiers[0].name)
    bpy.context.view_layer.objects.active=front_bumper
    mod=front_bumper.modifiers.new('Cooling aperture','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    box('Intake shadow recess',(-2.03,side*.425,.462),(.018,.39,.087),rubber,.009)
    for y in [side*.31,side*.43,side*.55]:box('Intake vertical vane',(-2.078,y,.462),(.022,.005,.080),black,.001)
    box('Intake horizontal vane',(-2.08,side*.425,.462),(.024,.386,.005),black,.001)

# Shaped light faces are near-flush with the body, with a recessed reflector and
# a fine fluted outer lens. Lamp boundaries follow a slight trapezoid.
def front_x(y):return -2.078+.025*(abs(y)/.81)**3


for side in [-1,1]:
    yc=side*.535
    yz=[(yc-.169,.665),(yc+.169,.665),(yc+.154,.858),(yc-.154,.858)]
    border=rounded_outline([(front_x(y),y,z) for y,z in yz],.009)
    center=Vector((-2.07,yc,.760))
    outer=[tuple(center+(Vector(p)-center)*1.037) for p in border]
    n=len(border)
    mesh('Thin headlamp perimeter',outer+border,[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)],black,smooth=True)
    box('Recessed headlamp back',(-2.018,yc,.760),(.025,.329,.19),reflector,.012)
    # An irregular pressed rectangular reflector: micro-facets vary angle
    # without drawing any circular outline over the rectangular lens.
    verts=[];columns=30;rows=16
    for j in range(rows+1):
        z=.676+j*.168/rows
        for k in range(columns+1):
            y=yc-.153+k*.306/columns
            u=abs((k-columns/2)/(columns/2));v=abs((j-rows/2)/(rows/2))
            x=-2.060-.009*(1-u*u)*(1-v*v)+.00018*math.sin(k*.7+j*.55)
            verts.append((x,y,z))
    faces=[]
    for j in range(rows):
        for k in range(columns):
            a=j*(columns+1)+k;faces.append((a,a+1,a+columns+2,a+columns+1))
    optics=mesh('Pressed rectangular lamp reflector facets',verts,faces,optical_gradient,smooth=True)
    colors=optics.data.color_attributes.new(name='ReflectorTone',type='FLOAT_COLOR',domain='POINT')
    for j in range(rows+1):
        for k in range(columns+1):
            u=(k-columns/2)/(columns/2);v=(j-rows/2)/(rows/2)
            center=math.exp(-((u/.60)**2+(v/.70)**2)*1.6)
            highlight=math.exp(-(((u+.28)/.23)**2+((v-.16)/.30)**2)*1.4)
            value=max(.05,min(.9,.43-.21*center+.21*highlight))
            colors.data[j*(columns+1)+k].color=(value,value*1.015,value*1.025,1)
    cylinder('Recessed optical bulb detail',(-2.068,yc,.760),.007,.003,reflector_dark,16,(0,math.pi/2,0))
    lamp_surface=surface_disk('Image-mapped glass headlamp',border,(-1,0,0),reference_lens,.002,4)
    lamp_uv=lamp_surface.data.uv_layers.new(name='UVMap')
    # The near (physical left) and far headlamps are independently sampled.
    # Coordinates are pixels in the unedited, user-provided 1672x941 image.
    if side<0: left_px,right_px,top_left,top_right,bottom_left,bottom_right=(702,889,508,511,596,602)
    else: left_px,right_px,top_left,top_right,bottom_left,bottom_right=(108,279,497,502,587,592)
    iw,ih=reference_image.size
    for polygon in lamp_surface.data.polygons:
        for li in polygon.loop_indices:
            vertex=lamp_surface.data.vertices[lamp_surface.data.loops[li].vertex_index].co
            across=max(0,min(1,(yc+.169-vertex.y)/.338))
            up=max(0,min(1,(vertex.z-.665)/.193))
            px=left_px+(right_px-left_px)*across
            top=top_left+(top_right-top_left)*across
            bottom=bottom_left+(bottom_right-bottom_left)*across
            lamp_uv.data[li].uv=(px/iw,1-(bottom+(top-bottom)*up)/ih)

    # A shallow clear cover and a fine rim give the reference-mapped reflector
    # physical highlights when the vehicle is turned in the 3D viewer.
    cover_border=[(x-.0015,y,z) for x,y,z in border]
    surface_disk('Clear molded headlamp cover',cover_border,(-1,0,0),lens,.003,4)
    line('Headlamp narrow silver rim',cover_border+[cover_border[0]],chrome,.0009)

    for j in range(43):
        y=yc-.150+j*.300/42
        line('Headlight vertical optical flute',[(front_x(y)-.003,y,.673),(front_x(y)-.003,y,.849)],lens_rib,.00036)
    for j in range(4):
        z=.690+j*.045
        line('Headlight horizontal optical flute',[(front_x(yc)-.003,yc-.15,z),(front_x(yc)-.003,yc+.15,z)],lens_rib,.00025)
    indicator=[(-2.084,side*.709,.668),side_point(-2.084,.668,side,.014),side_point(-2.084,.857,side,.014),(-2.084,side*.699,.859)]
    corner=mesh('Front amber corner lens',indicator,[(0,1,2,3)],reference_lens,.002,smooth=True)
    corner_uv=corner.data.uv_layers.new(name='UVMap')
    if side<0:left_px,right_px,top,bottom=(890,952,510,603)
    else:left_px,right_px,top,bottom=(80,113,496,589)
    iw,ih=reference_image.size
    for polygon in corner.data.polygons:
        for li in polygon.loop_indices:
            vertex=corner.data.vertices[corner.data.loops[li].vertex_index].co
            outer=max(0,min(1,(abs(vertex.y)-.699)/.115))
            across=outer if side<0 else 1-outer
            up=max(0,min(1,(vertex.z-.668)/.191))
            corner_uv.data[li].uv=((left_px+(right_px-left_px)*across)/iw,1-(bottom+(top-bottom)*up)/ih)

    indicator_side=[side_point(-2.084+i*.119/6,.668+j*.189/6,side,.014) for i in range(7) for j in range(7)]
    mesh('Contoured amber corner return',indicator_side,[(i*7+j,(i+1)*7+j,(i+1)*7+j+1,i*7+j+1) for i in range(6) for j in range(6)],amber,smooth=True)
    # The reference indicator has fine lens ribs rather than a dark grille.
    for j in range(15):
        y=side*(.706+j*.0057)
        line('Amber front vertical flute',[(-2.089,y,.68),(-2.089,y,.844)],amber_prism,.00028)
    for j in range(3):
        z=.704+j*.055
        line('Amber lens horizontal prism',[(-2.089,side*.716,z),(-2.089,side*.786,z)],amber_prism,.00022)
    # Four columns: red / clear / red / outer amber, divided into two rows.
    box('Rear lamp recessed gasket',(2.071,side*.581,.759),(.022,.456,.207),black,.008)
    for col,y in enumerate([.412,.516,.620,.742]):
        for row,z in enumerate([.712,.809]):
            mat=amber if col==3 else reverse_lens if col==1 and row==1 else red
            width=.125 if col==3 else .102
            cell=box('Segmented rear optical cell',(2.085,side*y,z),(.017,width,.093),mat,.002)
            cell.data.materials.append(rear_reference_lens)
            while cell.data.uv_layers:
                cell.data.uv_layers.remove(cell.data.uv_layers[0])
            cell_uv=cell.data.uv_layers.new(name='UVMap')
            if side<0:left_px,right_px,top,bottom=(824,891,288,330)
            else:left_px,right_px,top,bottom=(1048,1134,290,333)
            iw,ih=rear_reference_image.size
            for polygon in cell.data.polygons:
                if polygon.normal.x>.9:polygon.material_index=1
                for li in polygon.loop_indices:
                    vertex=cell.data.vertices[cell.data.loops[li].vertex_index].co
                    yy=vertex.y+side*y;zz=vertex.z+z
                    outer=max(0,min(1,(abs(yy)-.363)/.448))
                    across=(1-outer) if side<0 else outer
                    up=max(0,min(1,(zz-.668)/.185))
                    cell_uv.data[li].uv=((left_px+(right_px-left_px)*across)/iw,1-(bottom+(top-bottom)*up)/ih)

    mesh('Rear lamp amber corner return',[(2.08,side*.809,.67),(2.08,side*.809,.85),side_point(1.997,.85,side,.006),side_point(1.997,.67,side,.006)],[(0,1,2,3)],amber,.003)

box('Deep black front grille',(-2.035,0,.761),(.035,.73,.189),black,.008)
for z in [.687,.758,.829]:
    box('Grille black horizontal rail',(-2.067,0,z),(.02,.729,.015),black,.003)
    box('Grille narrow bright leading edge',(-2.078,0,z+.004),(.003,.723,.004),chrome,.0008)
for y in [-.30,-.15,0,.15,.30]:box('Grille recessed vertical support',(-2.045,y,.756),(.008,.007,.172),black,.001)

shield=[(-2.089,-.050,.815),(-2.089,.050,.815),(-2.090,.042,.754),(-2.091,0,.711),(-2.090,-.042,.754)]
mesh('Heritage shield silver edge',shield,[tuple(range(5))],chrome)
mesh('Heritage shield navy enamel',[(x-.002,y*.84,.763+(z-.763)*.84) for x,y,z in shield],[tuple(range(5))],navy)
star=[]
for j in range(32):
    t=j*math.tau/32;r=.032 if j%2==0 else .012
    star.append((-2.094,math.sin(t)*r,.766+math.cos(t)*r))
mesh('Heritage sun emblem',star,[tuple(range(32))],gold)

box('Recessed rear plate panel',(2.068,0,.760),(.033,.705,.207),black,.008)
for x,height in [(-2.15,.497),(2.10,.759)]:
    rot=(math.pi/2,0,-math.pi/2) if x<0 else (math.pi/2,0,math.pi/2)
    box('Black heritage registration plate',(x,0,height),(.009,.48,.212),plate_black,.009)
    face=x+(-.006 if x<0 else .006)
    outline=rounded_outline([(face,-.237,height-.103),(face,.237,height-.103),(face,.237,height+.103),(face,-.237,height+.103)],.012)
    line('White registration plate border',outline+[outline[0]],white,.0017)
    for text,z,size in [('PROTON',.061,.051),('SAGA',-.002,.061),('(1985)',-.064,.039)]:
        label('Registration plate '+text,text,(face+(-.003 if x<0 else .003),0,height+z),size,white,rot)
label('Rear proton script','proton',(2.069,-.52,.912),.046,black,(math.pi/2,0,math.pi/2))
label('Rear SAGA lettering','SAGA',(2.069,.57,.912),.036,chrome,(math.pi/2,0,math.pi/2))
cylinder('Boot key surround',(2.074,0,.915),.013,.006,chrome,24,(0,math.pi/2,0))
cylinder('Boot key center',(2.079,0,.915),.008,.006,black,20,(0,math.pi/2,0))

# Visible cabin details are modeled rather than painted onto opaque window cards.
box('Cabin floor',(.2,0,.53),(2.3,1.35,.055),black,.018)
box('Dark inner roof lining',(.35,0,1.433),(1.30,1.19,.013),fabric,.008)
box('Sculpted padded dashboard',(-.72,0,.947),(.34,1.35,.10),black,.038)
box('Instrument binnacle',(-.68,.36,1.003),(.18,.38,.068),black,.027)
box('Dashboard center stack',(-.65,0,.845),(.13,.25,.19),black,.019)
for side in [-1,1]:
    box('Front seat cushion',(-.08,side*.34,.687),(.48,.45,.13),fabric,.065)
    back=box('Front seat upholstered back',(.09,side*.34,.875),(.14,.445,.35),fabric,.065)
    back.rotation_euler.y=-.12
    box('Front head restraint',(.10,side*.34,1.15),(.13,.26,.18),fabric,.045)
    for dy in [-.16,.16]:
        bolster=box('Front seat side bolster',(.055,side*.34+dy,.875),(.17,.07,.29),fabric,.034)
        bolster.rotation_euler.y=-.12
    for dy in [-.10,0,.10]:line('Seat upholstery stitch',[(-.004,side*.34+dy,.76),(-.03,side*.34+dy,1.06)],fabric_seam,.0012)
    box('Inner door upholstery',(.22,side*.716,.797),(1.94,.04,.28),fabric,.022)
    box('Door armrest',(.12,side*.678,.823),(.35,.075,.052),black,.014)
    line('Visible front seat belt',[(.24,side*.68,1.28),(.2,side*.56,.75)],black,.009)
box('Rear seat cushion',(1.0,0,.68),(.43,1.23,.13),fabric,.05)
rearback=box('Rear seat upholstered back',(1.21,0,.90),(.14,1.23,.40),fabric,.052)
rearback.rotation_euler.y=-.1
box('Rear parcel shelf',(1.35,0,.992),(.27,1.32,.025),fabric,.009)
box('Rear center brake lamp housing',(1.31,0,1.04),(.12,.19,.066),black,.014)
box('Rear center brake lamp lens',(1.376,0,1.044),(.006,.158,.035),red,.004)
box('Rearview mirror',(-.42,0,1.344),(.045,.21,.064),black,.013)
line('Rearview mirror stalk',[(-.43,0,1.412),(-.42,0,1.365)],black,.008)
for side in [-1,1]:box('Folded sun visor',(-.36,side*.36,1.393),(.045,.37,.07),fabric,.011)
box('Center console',(-.18,0,.697),(.65,.16,.13),black,.02)
line('Gear lever',[(-.29,0,.75),(-.25,0,.84)],black,.012)
steering=[(-.56,.35+math.sin(j*math.tau/64)*.132,1.016+math.cos(j*math.tau/64)*.132) for j in range(65)]
line('RHD steering wheel',steering,black,.012)
for t in [math.pi/2,-math.pi/2,math.pi]:line('Steering spoke',[(-.56,.35,1.016),(-.56,.35+math.sin(t)*.121,1.016+math.cos(t)*.121)],black,.011)
box('Steering hub',(-.56,.35,1.016),(.041,.1,.058),black,.014)
line('Steering column',[(-.74,.35,.91),(-.56,.35,1.016)],black,.02)
for j in range(9):
    t=.12+j*.085;x=1.432+(1.032-1.432)*t;z=1.004+(1.431-1.004)*t
    width=.713+(.601-.713)*t
    line('Rear glass heating element',[(x+.002,-width*.95,z),(x+.002,width*.95,z)],defroster,.0004)
line('Short roof antenna',[(-.29,0,1.48),(.05,0,1.82)],black,.0017)
box('Antenna mounting foot',(-.29,0,1.478),(.065,.026,.022),black,.01)
line('Underbody exhaust pipe',[(1.42,-.35,.34),(1.68,-.35,.34),(1.86,-.35,.38)],underseal,.018)
cylinder('Exhaust outlet',(1.99,-.35,.39),.025,.12,steel,32,(0,math.pi/2,0))
cylinder('Exhaust dark bore',(2.052,-.35,.39),.021,.006,black,32,(0,math.pi/2,0))

# The front and rear reference views have a narrower roof than the original
# study. Deform all cabin pieces together so adjoining glass, pillars and trim
# retain the same joins; taper from the beltline to avoid changing body width.
# The rear roof edge also moves slightly forward to shorten the roof profile.
def smooth_unit(value):
    value=max(0,min(1,value))
    return value*value*(3-2*value)


bpy.context.view_layer.update()
for part in root.children:
    if part.type!='MESH':continue
    world=part.matrix_world.copy()
    inverse=world.inverted_safe()
    for vertex in part.data.vertices:
        point=world @ vertex.co
        height=smooth_unit((point.z-.988)/.458)
        rear=smooth_unit((point.x-.24)/.80)
        point.x -= .052*height*rear
        point.y *= 1-.10*height
        vertex.co=inverse @ point
    part.data.update()

# Shift the complete upper structure relative to the contact patch. Wheel hubs
# and openings were modeled on the same pre-shift center, so they remain aligned.
for part in root.children:
    part.location.z -= BODY_LOWERING

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
        # Evaluated bevel UVs can vary by a float ULP across Blender processes.
        # Quantize only exported UVs; 1e-6 is below 0.002 reference-image pixels.
        for uv_layer in data.uv_layers:
            for item in uv_layer.data:
                item.uv=(round(item.uv.x,6),round(item.uv.y,6))
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
    bpy.ops.export_scene.gltf(filepath=str(OUT/'exports/proton-saga-1985.glb'),export_format='GLB',use_selection=True,export_apply=True,export_image_format='JPEG',export_jpeg_quality=94)
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
scene.cycles.samples=12 if QUICK else 48
scene.cycles.use_denoising=True
scene.world.color=(.10,.10,.10)
scene.world.use_nodes=True
# Blender bundles this studio HDRI with an accompanying CC0 license. It is
# packed into the editable scene and is used for lighting only, not in the GLB.
world_nodes=scene.world.node_tree.nodes;world_links=scene.world.node_tree.links
world_nodes.clear()
world_output=world_nodes.new('ShaderNodeOutputWorld')
background=world_nodes.new('ShaderNodeBackground')
background.inputs['Color'].default_value=(.014,.018,.023,1)
background.inputs['Strength'].default_value=.3
studio_background=world_nodes.new('ShaderNodeBackground')
studio_background.inputs['Strength'].default_value=.45
env=world_nodes.new('ShaderNodeTexEnvironment')
env.image=bpy.data.images.load('/Applications/Blender.app/Contents/Resources/5.1/datafiles/studiolights/world/studio.exr',check_existing=True)
env.image.pack()
world_links.new(env.outputs['Color'],studio_background.inputs['Color'])
light_path=world_nodes.new('ShaderNodeLightPath')
mix=world_nodes.new('ShaderNodeMixShader')
world_links.new(light_path.outputs['Is Camera Ray'],mix.inputs[0])
world_links.new(studio_background.outputs[0],mix.inputs[1]);world_links.new(background.outputs[0],mix.inputs[2])
world_links.new(mix.outputs[0],world_output.inputs['Surface'])
# A radial cyclorama supplies a real continuous studio background to every camera.
# A horizontal plane alone exposes a distant edge in the low perspective views.
studio_material=material('Studio charcoal concrete',(.008,.009,.011),.08,.55)
# Procedural micro-bump belongs only to the presentation floor, never the GLB.
floor_nodes=studio_material.node_tree.nodes;floor_links=studio_material.node_tree.links
noise=floor_nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=150
noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7
bump=floor_nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.001
floor_links.new(noise.outputs['Fac'],bump.inputs['Height'])
floor_links.new(bump.outputs['Normal'],floor_nodes['Principled BSDF'].inputs['Normal'])
profile=[(35,-.004),(40,.1),(43,.8),(45,2.5),(46,5),(46,12),(46,25)]
segments=128;verts=[(0,0,-.004)]
for radius,z in profile:
    verts.extend((radius*math.cos(j*math.tau/segments),radius*math.sin(j*math.tau/segments),z) for j in range(segments))
faces=[(0,1+j,1+(j+1)%segments) for j in range(segments)]
for i in range(len(profile)-1):
    for j in range(segments):
        a=1+i*segments+j;b=1+i*segments+(j+1)%segments
        faces.append((a,a+segments,b+segments,b))
floor=mesh('STUDIO seamless cyclorama',verts,faces,studio_material,smooth=True)
floor.parent=None
for location,power,size in [((-3,-4,6),750,5),((1,4,5),950,5),((4,-1,4),800,4),((-5,1,2.6),260,3)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    obj=bpy.context.object;obj.data.energy=power;obj.data.shape='DISK';obj.data.size=size
    obj.rotation_euler=(Vector((0,0,.7))-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add()
camera=bpy.context.object;camera.data.clip_end=1000;scene.camera=camera
scene.render.resolution_x=960 if QUICK else 1536
scene.render.resolution_y=640 if QUICK else 1024
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
views={'preview':(-9,-4,1.95),'view-rear-3q':(9,4,1.95),'view-front':(-9.5,0,1.12),'view-rear':(9.5,0,1.12),'view-left':(0,-30,2.4),'view-right':(0,30,2.4)}
selected=None
if '--views' in sys.argv:
    selected=sys.argv[sys.argv.index('--views')+1].split(',')
for name,location in views.items():
    if selected and name not in selected:continue
    camera.data.type='ORTHO' if name in ['view-left','view-right'] else 'PERSP'
    camera.data.lens=75 if name=='view-rear-3q' else 94
    camera.data.ortho_scale=3.0 if name in ['view-front','view-rear'] else 4.85
    camera.location=location
    target=Vector((0,.35,.78)) if name=='preview' else Vector((0,0,.86))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    subprocess.run(['/opt/homebrew/bin/cwebp','-quiet','-q','92',str(OUT/(name+'.png')),'-o',str(OUT/(name+'.webp'))],check=True)
    (OUT/(name+'.png')).unlink()
camera.data.type='PERSP';camera.data.lens=94;camera.location=views['preview']
camera.rotation_euler=(Vector((0,.35,.78))-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'scene.blend'))
print('COMPLETE',bpy.app.version_string)
