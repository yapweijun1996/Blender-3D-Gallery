"""Geometry shared by the three wall-fixture generate.py entry points."""
import math

import bpy
import bmesh
from mathutils import Vector


TAU = math.tau
SLUGS = {
    "mall-wall-sconce": "ASSET_MallWallSconce",
    "mall-stair-tread-light": "ASSET_MallStairTreadLight",
    "mall-emergency-bulkhead-light": "ASSET_MallEmergencyBulkheadLight",
}
VIEWS = {
    "mall-wall-sconce": (.62, -1.6, .24),
    "mall-stair-tread-light": (-.55, -1.4, .18),
    "mall-emergency-bulkhead-light": (.65, -1.5, .24),
}


def material(name, rgb, metallic=0, roughness=.4, glow=0):
    color = [int(rgb[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in color) + (1,)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = linear
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = linear
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if glow:
        bsdf.inputs["Emission Color"].default_value = linear
        bsdf.inputs["Emission Strength"].default_value = glow
    return mat


def component(name, parent, mat, vertices, faces, *, edge=0, smooth=False, segments=2):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    # Concave profiles and front/back cap winding differ between the wall and axial forms.
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(mat)
    if smooth:
        data.polygons.foreach_set("use_smooth", [True] * len(data.polygons))
        data.set_sharp_from_angle(angle=math.radians(34))
    if edge:
        bevel = obj.modifiers.new("Edge radii", "BEVEL")
        bevel.width = edge
        bevel.segments = segments
        bevel.affect = "EDGES"
        normals = obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
        normals.keep_sharp = True
    return obj


def ring_shape(name, root, mat, rings, *, closed=False, smooth=False, edge=0):
    verts, index, faces = [], [], []
    for row in rings:
        index.append(list(range(len(verts), len(verts) + len(row))))
        verts.extend(row)
    for a, b in zip(index, index[1:] + ([index[0]] if closed else [])):
        for j in range(len(a)):
            k = (j + 1) % len(a)
            faces.append((a[j], a[k], b[k], b[j]))
    if not closed:
        faces += [tuple(reversed(index[0])), tuple(index[-1])]
    return component(name, root, mat, verts, faces, smooth=smooth, edge=edge)


def rounded_loop(w, h, r, steps):
    points = []
    for sx, sz, start in [(1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)]:
        for i in range(steps + 1):
            angle = math.radians(start + 90 * i / steps)
            points.append((sx * (w / 2 - r) + r * math.cos(angle),
                           sz * (h / 2 - r) + r * math.sin(angle)))
    return points


def plate(name, root, mat, specs, steps, *, x=0, z=0, closed=False):
    # A row specifies its face width, height, corner radius and depth in front of the wall.
    return ring_shape(name, root, mat, [
        [(px + x, -depth, pz + z) for px, pz in rounded_loop(w, h, r, steps)]
        for w, h, r, depth in specs], closed=closed)


def turned(name, root, mat, profile, sides, direction="wall", center=(0, 0, 0), flutes=0):
    """Closed axial body. Each ring has independent radius and optional fluting or ellipticity."""
    cx, cy, cz = center
    rings = []
    for row in profile:
        radius, along = row[:2]
        depth_or_z = row[2] if len(row) > 2 else radius
        relief = row[3] if len(row) > 3 else 0
        points = []
        for j in range(sides):
            a = TAU * j / sides
            ridge = relief * (.5 + .5 * math.cos(flutes * a))
            x = cx + (radius + ridge) * math.cos(a)
            radial = (depth_or_z + ridge) * math.sin(a)
            if direction == "wall":
                points.append((x, cy - along, cz + radial))
            else:
                points.append((x, cy + radial, cz + along))
        rings.append(points)
    return ring_shape(name, root, mat, rings, smooth=True)


def vertical_cap(name, root, mat, profile, segments, cy):
    return turned(name, root, mat, profile, segments, "vertical", (0, cy, 0))


def tube(name, root, mat, path, radius, guide, sides):
    points = [Vector(v) for v in path]
    guide = Vector(guide)
    rings = []
    for i, pos in enumerate(points):
        tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
        side = tangent.cross(guide).normalized()
        up = side.cross(tangent).normalized()
        rings.append([tuple(pos + radius * (side * math.cos(TAU*j/sides) + up * math.sin(TAU*j/sides)))
                      for j in range(sides)])
    return ring_shape(name, root, mat, rings, smooth=True)


def wall_screw(name, root, metal, insert, x, z, d, radius, low):
    sides = 12 if low else 24
    turned(name + "_Crown", root, metal, [
        (.92 * radius, d), (radius, d + .00055), (.9 * radius, d + .0013)
    ], sides, center=(x, 0, z))
    if not low:
        # A shallow dark inset on the head denotes the service slot at native scale.
        slot = plate(name + "_Slot", root, insert, [
            (radius * 1.1, radius * .23, radius*.06, d + .00129),
            (radius * 1.06, radius * .20, radius*.06, d + .00140)
        ], 2, x=x, z=z)
        for v in slot.data.vertices:
            dx, dz = v.co.x - x, v.co.z - z
            v.co.x, v.co.z = x + .866*dx - .5*dz, z + .5*dx + .866*dz


def sconce(root, low):
    brass = material("Satin honey bronze", "AE8151", .68, .31)
    dark = material("Patinated peacock enamel", "285453", .32, .31)
    amber = material("Warm ribbed opal", "FFE4AF", .04, .36, .30)
    shade = material("Dark saddle lining", "3F3930", .16, .45)
    n = 32 if low else 96
    # The stepped backplate and opposing axial collars support the fluted glass at both ends.
    plate("Escutcheon | bronze perimeter", root, brass, [
        (.103,.337,.025,0),(.108,.342,.028,.002),(.108,.342,.028,.010),
        (.104,.338,.026,.012)], 3 if low else 7)
    plate("Escutcheon | enamel face", root, dark, [
        (.098,.331,.024,.011),(.098,.331,.024,.016),(.094,.326,.022,.018)], 3 if low else 6)
    cy = -.086
    for z, label in [(-.118, "Lower"), (.118,"Upper")]:
        plate(label+" | corbel", root, dark, [
            (.055,.040,.009,.017),(.048,.034,.008,.037),(.030,.026,.007,.055),
            (.028,.025,.006,.084)], 3 if low else 5, z=z)
        turned(label+" | saddle washer", root, brass, [(.017,.017),(.017,.024)], 24,
               center=(0,0,z))
    glass_profile = [
        (.026,-.158,.025,0),(.029,-.149,.028,.0005),(.034,-.118,.033,.0018),
        (.041,-.054,.039,.0025),(.043,0,.041,.0026),(.041,.054,.039,.0025),
        (.034,.118,.033,.0018),(.029,.149,.028,.0005),(.026,.158,.025,0)]
    turned("Shade | pressed longitudinal flutes", root, amber, glass_profile, n, "vertical",
           (0,cy,0), 8 if low else 24)
    for sign, label in [(-1,"Lower"),(1,"Upper")]:
        vertical_cap(label+" | globe seat",root,shade,[(.028,sign*.147),(.0315,sign*.150),
            (.0305,sign*.156)], n//2,cy)
        vertical_cap(label+" | spun ferrule",root,brass,[(.032,sign*.149),(.033,sign*.153),
            (.032,sign*.159),(.026,sign*.163),(.018,sign*.167)],n//2,cy)
        vertical_cap(label+" | stepped finial",root,dark,[(.0185,sign*.164),(.020,sign*.168),
            (.019,sign*.172),(.011,sign*.177),(.009,sign*.181)],n//2,cy)
    # Two narrow side bows meet the bronze collars without obscuring the primary opal silhouette.
    for sign, label in [(-1,"Left"),(1,"Right")]:
        path = []
        count = 10 if low else 25
        for i in range(count+1):
            t = i/count
            path.append((sign*(.026 + .026*math.sin(math.pi*t)),cy-.0008,
                         -.152+.304*t))
        tube(label+" | bronze guard bow",root,brass,path,.0027,(0,1,0),6 if low else 10)
    for z, label in [(-.147,"Lower"),(.147,"Upper")]:
        wall_screw(label+" | mounting screw",root,brass,shade,0,z,.0175,.0042,low)


def tread(root, low):
    graphite = material("Graphite cast aluminium", "3B4242", .42, .38)
    trim = material("Satin nickel flange", "A6A49B", .70, .32)
    dark = material("EPDM and optical shadow", "222829", .05, .65)
    opal = material("Warm setback diffuser", "FFE7BC", .03, .39, .50)
    steps = 3 if low else 7
    plate("Recess can | rear enclosure",root,graphite,[
        (.215,.044,.005,-.044),(.227,.055,.008,-.042),(.231,.058,.009,.001)],steps)
    plate("Gasket | flange bedding",root,dark,[
        (.264,.079,.009,0),(.264,.079,.009,.0024)],steps)
    # The machined perimeter is a true opening; the diffuser sits behind the projecting blades.
    plate("Flange | trim and inner reveal",root,trim,[
        (.271,.084,.009,.0018),(.274,.087,.010,.0035),(.274,.087,.010,.0065),
        (.270,.083,.009,.008),(.224,.048,.004,.008),(.220,.045,.003,.006),
        (.220,.045,.003,.0018)],steps,closed=True)
    plate("Reveal | graphite bezel",root,graphite,[
        (.225,.049,.004,.003),(.225,.049,.004,.0068),(.217,.043,.003,.0068),
        (.213,.039,.002,.0048),(.213,.039,.002,.002)],steps,closed=True)
    plate("Lens | frosted inset",root,opal,[
        (.218,.043,.003,.0022),(.218,.043,.003,.0036)],steps)
    for i,z in enumerate([-.013,-.002,.009]):
        # Each closed, folded extrusion shields the lens at a high viewing angle.
        yz=[(-.0038,z+.0028),(-.007,z+.0028),(-.0149,z-.0024),
            (-.0143,z-.0040),(-.0126,z-.0042),(-.004,z+.0010)]
        ring_shape("Baffle | blade "+str(i+1),root,graphite,[[(x,y,h) for y,h in yz]
            for x in [-.107,.107]],edge=.00040)
    for x,label in [(-.124,"Left"),(.124,"Right")]:
        wall_screw(label+" | service screw",root,trim,dark,x,0,.0078,.0042,low)
    if not low:
        for i in range(6):
            x=-.079+i*.0316
            plate("Rear | cast fin "+str(i+1),root,graphite,[
                (.004,.039,.001,-.046),(.005,.040,.001,-.043)],2,x=x)
    plate("Rear | cable port",root,dark,[(.027,.019,.004,-.049),(.030,.021,.004,-.043)],2 if low else 4)


def bulkhead(root, low):
    enamel = material("Marine teal cast enamel", "496461", .31, .36)
    rim = material("Burnished nickel hardware", "A9A89B", .65, .39)
    black = material("Weatherseal charcoal", "2B3030", .03, .67)
    lens = material("Prismatic ivory diffuser", "FFE6B2", .02, .38, .28)
    green = material("Green charge indicator", "83BD72", .0, .30, .38)
    steps = 32 if low else 72
    # A mounting ear at each pole bears a fastener; the rear casting can sit against a wall.
    for z,label in [(-.148,"Lower"),(.148,"Upper")]:
        plate(label+" | cast mounting lug",root,enamel,[
            (.040,.045,.012,0),(.045,.047,.013,.004),(.043,.045,.013,.017)], 3 if low else 6,z=z)
        wall_screw(label+" | anchor",root,rim,black,0,z*1.07,.0168,.005,low)
    turned("Housing | oval die casting",root,enamel,[(.089,0,.132),(.096,.003,.141),
        (.100,.009,.146),(.102,.024,.148),(.102,.031,.148),(.098,.035,.145)],steps)
    turned("Seal | raised dark gasket",root,black,[(.098,.031,.144),(.101,.033,.1465),
        (.100,.038,.146),(.097,.040,.143)],steps)
    # A collar covers the outer glass edge and leaves a narrow dark seam around the entire perimeter.
    collar=[]
    for rx,d,rz in [(.098,.037,.143),(.099,.040,.145),(.097,.044,.143),(.089,.046,.134),
                    (.086,.045,.130),(.086,.040,.130)]:
        collar.append([(rx*math.cos(TAU*i/steps),-d,rz*math.sin(TAU*i/steps)) for i in range(steps)])
    ring_shape("Lip | rolled enclosure collar",root,enamel,collar,closed=True,smooth=True)
    profile=[(.090,.037,.134),(.087,.046,.131),(.082,.052,.124),(.077,.060,.116),
             (.068,.069,.103),(.053,.078,.080),(.034,.084,.052),(.014,.087,.021)]
    turned("Globe | pressed oval diffuser",root,lens,profile,steps)
    if not low:
        # Parallel moulded ridges follow the glass arch over its central face.
        for i in [-3,-2,-1,0,1,2,3]:
            x=.013*i
            path=[]
            extent=.125*math.sqrt(1-(x/.088)**2)
            for j in range(17):
                z=extent*(-.89+1.78*j/16)
                d=.038+.049*math.sqrt(max(0,1-(x/.088)**2-(z/.133)**2))
                path.append((x,-d,z))
            tube("Globe | prism rib "+str(i+4),root,lens,path,.00135,(1,0,0),6)
    for i,z in enumerate([-.089,-.045,0,.045,.089]):
        q=math.sqrt(1-(z/.144)**2)
        path=[]
        count=12 if low else 22
        for j in range(count+1):
            angle=math.pi*j/count
            path.append((.095*q*math.cos(angle),-(.042+.056*q*math.sin(angle)),z))
        tube("Guard | arched crossbar "+str(i+1),root,enamel,path,.004,(0,0,1),6 if low else 10)
    path=[]
    count=18 if low else 34
    for i in range(count+1):
        a=math.pi*i/count
        path.append((0,-(.043+.0568*math.sin(a)),.140*math.cos(a)))
    tube("Guard | longitudinal spine",root,enamel,path,.0042,(1,0,0),6 if low else 10)
    for sign,label in [(-1,"Left"),(1,"Right")]:
        plate(label+" | captive clasp",root,rim,[(.013,.032,.004,.028),(.013,.032,.004,.041),
            (.010,.030,.003,.044)],3,x=sign*.097)
    turned("Status | rubber bezel",root,black,[(.0064,.0445),(.0057,.049)],18,center=(.051,0,-.115))
    turned("Status | green pilot",root,green,[(.0046,.0485),(.0045,.050),(.0036,.051)],16,
           center=(.051,0,-.115))


def build(slug, low=False):
    root = bpy.data.objects.new(SLUGS[slug], None)
    bpy.context.collection.objects.link(root)
    root.empty_display_size = .02
    root["mount"] = "Wall or riser face at Blender Y=0, front toward -Y"
    builders = {"mall-wall-sconce":sconce, "mall-stair-tread-light":tread,
                "mall-emergency-bulkhead-light":bulkhead}
    builders[slug](root,low)
    return root
