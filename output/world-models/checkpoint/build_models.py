"""Generate the checkpoint game meshes in glTF world coordinates and render the exported GLBs."""
from hashlib import sha256
from math import cos, pi, sin
from pathlib import Path
import json
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PITCH = 4.8
LANE_CENTER = -.75
BOOM_PIVOT = (.86, 1.02, 2.65)

# Base colors are in linear RGB. Variant signal colors use glTF vertex colors.
COMMON = {
    "paint": ((.59, .035, .024), .46, .0),
    "glass": ((.065, .29, .31), .20, .12),
    "window": ((.075, .20, .24), .24, .10),
    "wall": ((.70, .72, .69), .58, .0),
    "roof": ((.29, .38, .43), .46, .28),
    "concrete": ((.36, .365, .33), .83, .0),
    "metal": ((.32, .37, .39), .39, .58),
    "chrome": ((.65, .70, .72), .26, .76),
    "trim": ((.072, .102, .112), .46, .25),
    "stone": ((.065, .073, .075), .90, .0),
    "light": ((.85, .87, .78), .35, .04),
    "lamp_emissive": ((1, 1, 1), .42, .0),
    "rubber": ((.027, .029, .03), .78, .0),
    "plate": ((.94, .55, .045), .59, .0),
}
SIGNAL_COLORS = {"green": (.05, .95, .17, 1), "red": (1, .045, .018, 1),
                 "amber": (1, .38, .035, 1)}


def blender(point):
    x, y, z = point
    return (x, -z, y)


def pbr(name, color, roughness, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return mat


def palette(kind):
    specs = COMMON.copy()
    if kind == "canopy":
        specs["roof"] = ((.12, .26, .35), .43, .28)
        specs["plate"] = ((.083, .18, .24), .52, .0)
    if kind == "building":
        specs["roof"] = ((.50, .57, .60), .42, .20)
        specs["window"] = ((.080, .23, .26), .23, .15)
        specs["leaf"] = ((.085, .17, .056), .86, .0)
    mats = {key: pbr(key, *value) for key, value in specs.items()}
    if kind == "lane":
        glass = mats["glass"]
        glass.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = .39
    # glTF has no vertex-color input for emission. Add a dim common emissive
    # component while vertex colors supply the individual signal face colors.
    signal = mats["lamp_emissive"]
    shader = signal.node_tree.nodes["Principled BSDF"]
    shader.inputs["Emission Color"].default_value = (.09, .075, .065, 1)
    shader.inputs["Emission Strength"].default_value = .36
    vertex_color = signal.node_tree.nodes.new("ShaderNodeVertexColor")
    vertex_color.layer_name = "signal_color"
    signal.node_tree.links.new(vertex_color.outputs["Color"], shader.inputs["Base Color"])
    return mats


class Part:
    def __init__(self, name, origin=(0, 0, 0)):
        self.name, self.origin = name, origin
        self.vertices, self.faces, self.materials, self.colors = [], [], [], []

    def add(self, vertices, faces, mat, tint=None):
        start = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(start+i for i in face) for face in faces)
        if isinstance(mat, str):
            self.materials.extend([mat]*len(faces))
        else:
            self.materials.extend(mat)
        self.colors.extend([tint]*len(faces))

    def loft(self, rings, mat):
        """Stack closed XZ rings ordered counterclockwise as coordinates on paper."""
        n = len(rings[0])
        faces = [tuple(range(n))]
        for row in range(len(rings)-1):
            for i in range(n):
                a, b = row*n+i, row*n+(i+1)%n
                faces.append((a, a+n, b+n, b))
        start = (len(rings)-1)*n
        faces.append(tuple(reversed(range(start, start+n))))
        self.add([vertex for ring in rings for vertex in ring], faces, mat)

    def box(self, center, size, mat, tint=None):
        x, y, z = center
        a, b, c = (d/2 for d in size)
        vertices = [(x+sx*a, y+sy*b, z+sz*c)
                    for sy in (-1, 1) for sx, sz in ((-1,-1),(1,-1),(1,1),(-1,1))]
        self.add(vertices, [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),
                            (2,6,7,3),(3,7,4,0)], mat, tint)

    def cylinder(self, a, b, radius, mat, sides=10, end_radius=None, tint=None):
        a, b = Vector(a), Vector(b)
        axis = (b-a).normalized()
        u = axis.cross(Vector((0,1,0)) if abs(axis.y) < .95 else Vector((1,0,0))).normalized()
        v = axis.cross(u)
        rim = [u*cos(2*pi*i/sides)+v*sin(2*pi*i/sides) for i in range(sides)]
        vertices = [a+radius*r for r in rim] + [b+(end_radius or radius)*r for r in rim]
        faces = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
        faces.extend((i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides))
        self.add(vertices, faces, mat, tint)

    def bar(self, a, b, width, depth, mat, up=(0,0,1), tint=None):
        a, b = Vector(a), Vector(b)
        axis = (b-a).normalized()
        u = axis.cross(Vector(up)).normalized()*width/2
        v = axis.cross(u).normalized()*depth/2
        rim = [-u-v,u-v,u+v,-u+v]
        self.add([a+r for r in rim]+[b+r for r in rim],
                 [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),
                  (2,3,7,6),(3,0,4,7)], mat, tint)

    def face(self, vertices, mat, tint=None):
        self.add(vertices, [tuple(range(len(vertices)))], mat, tint)

    def panel(self, center, size, mat, axis, facing):
        x,y,z = center
        a,b = (length/2 for length in size)
        if axis == "z":
            points = [(x+i*a,y+j*b,z) for i,j in ((-1,-1),(1,-1),(1,1),(-1,1))]
        else:
            points = [(x,y+j*b,z+i*a) for i,j in ((1,-1),(-1,-1),(-1,1),(1,1))]
        self.face(points if facing > 0 else points[::-1],mat)

    def build(self, materials):
        pivot = Vector(self.origin)
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata([blender(Vector(v)-pivot) for v in self.vertices], [], self.faces)
        slots = list(dict.fromkeys(self.materials))
        for name in slots:
            mesh.materials.append(materials[name])
        for poly, mat in zip(mesh.polygons, self.materials):
            poly.material_index = slots.index(mat)
        if any(self.colors):
            colors = mesh.color_attributes.new(name="signal_color", type="FLOAT_COLOR", domain="CORNER")
            for poly, color in zip(mesh.polygons, self.colors):
                for loop in poly.loop_indices:
                    colors.data[loop].color = color or (1,1,1,1)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = blender(pivot)
        return obj


def chamfer_ring(x0, x1, z0, z1, y, cut):
    return [(x0+cut,y,z0),(x1-cut,y,z0),(x1,y,z0+cut),(x1,y,z1-cut),
            (x1-cut,y,z1),(x0+cut,y,z1),(x0,y,z1-cut),(x0,y,z0+cut)]


def lane():
    road, markings, island = (Part(n) for n in ("lane_deck", "road_markings", "booth_island"))
    road.box((0,.009,0),(4.8,.018,9), "stone")
    # Flat lane markings sit just clear of the drivable surface.
    for z in (-3.62,-1.50,.65,2.77,4.17):
        markings.box((-2.36,.019,z),(.08,.002,.67 if z < 4 else .5),"light")
    markings.box((-.75,.019,2.24),(3.12,.002,.18),"light")
    markings.box((-.75,.019,-3.02),(.112,.002,.74),"light")
    markings.face([(-1.03,.020,-2.72),(-.75,.020,-2.30),(-.47,.020,-2.72)],"light")

    def island_ring(y, inset):
        return [(x,y,z) for x,z in ((1.18+inset,-4.29+inset),(2.14-inset,-4.29+inset),
               (2.399-inset,-3.66+inset),(2.399-inset,3.62-inset),(2.14-inset,4.25-inset),
               (1.19+inset,4.25-inset),(.90+inset,3.62-inset),(.90+inset,-3.66+inset))]
    island.loft([island_ring(.018,0),island_ring(.131,0),island_ring(.182,.043)],
                ["concrete"]+["concrete"]*8+["wall"]*8+["concrete"])
    for z in (-3.36,-2.91,1.52,1.97,3.31,3.68):
        island.box((.921,.082,z),(.022,.104,.28),"rubber")
    for z in (-2.02,2.03):
        island.box((1.93,.185,z),(.42,.008,.28),"metal")
        for n in range(5):
            island.box((1.93,.19,z-.104+n*.052),(.37,.002,.016),"trim")

    booth, frames, glazing, interior = (Part(n) for n in
        ("booth_shell", "booth_frames", "booth_glazing", "booth_counter"))
    x, z, floor = 1.65, -.48, .182
    booth.box((x,floor+.06,z),(1.2,.12,2),"trim")
    for bx in (1.073,2.227):
        booth.box((bx,floor+.52,z),(.046,.83,1.91),"metal")
        booth.box((bx,floor+2.31,z),(.046,.235,1.91),"wall")
    for bz in (z-.973, z+.973):
        booth.box((x,floor+.52,bz),(1.12,.83,.052),"metal")
        booth.box((x,floor+2.31,bz),(1.12,.235,.052),"wall")
    booth.loft([chamfer_ring(1.05,2.25,z-1,z+1,floor+2.428,.047),
                chamfer_ring(1.05,2.25,z-1,z+1,floor+2.53,.047),
                chamfer_ring(1.075,2.225,z-.975,z+.975,floor+2.6,.039)],"roof")
    for bx in (1.079,2.221):
        for bz in (z-.95,z+.95):
            frames.box((bx,floor+1.25,bz),(.058,2.28,.066),"trim")
        for h in (.94,2.195):
            frames.box((bx,floor+h,z),(.057,.053,1.85),"trim")
        for bz in (z+.08,z-.47):
            frames.box((bx,floor+1.57,bz),(.049,1.24,.037),"trim")
        for za, zb in ((z-.92,z-.49),(z-.45,z+.06),(z+.10,z+.92)):
            if bx < x and za < z < zb:
                # The slider is shown partially open at the driver's window.
                zb -= .25
            glazing.box((bx,floor+1.566,(za+zb)/2),(.012,1.17,zb-za),"glass")
        booth.box((bx,floor+.80,z),(.008,.039,1.80),"wall")
    for bz in (z-.962,z+.962):
        for h in (.94,2.195):
            frames.box((x,floor+h,bz),(1.106,.05,.045),"trim")
        frames.box((x,floor+1.57,bz),(.037,1.24,.044),"trim")
        for bx in (x-.275,x+.275):
            glazing.box((bx,floor+1.57,bz),(.50,1.17,.012),"glass")
    # Rear door has a separate surround and latch. Add a shallow driver's sill.
    frames.box((1.27,floor+.94,z+1.002),(.041,1.75,.017),"trim")
    frames.box((2.02,floor+.94,z+1.002),(.041,1.75,.017),"trim")
    frames.box((1.65,floor+1.815,z+1.002),(.79,.052,.017),"trim")
    frames.box((1.96,floor+1.02,z+1.024),(.10,.034,.028),"chrome")
    frames.box((1.004,floor+.95,z-.07),(.18,.058,.77),"chrome")
    interior.box((1.52,floor+.897,z-.11),(.75,.050,1.14),"wall")
    interior.box((1.39,floor+.47,z-.48),(.36,.84,.36),"trim")
    interior.box((1.54,floor+1.10,z+.17),(.066,.30,.40),"trim")
    interior.box((1.576,floor+1.10,z+.17),(.012,.252,.35),"window")
    interior.box((1.55,floor+.957,z+.17),(.21,.04,.31),"metal")
    interior.box((1.83,floor+.47,z+.34),(.41,.067,.37),"rubber")
    interior.box((2.01,floor+.696,z+.34),(.066,.40,.37),"rubber")
    interior.cylinder((1.83,floor+.05,z+.34),(1.83,floor+.45,z+.34),.043,"metal",8)

    kiosk = Part("inspection_kiosk")
    kiosk.box((1.65,.224,-2.16),(.49,.082,.39),"metal")
    kiosk.loft([chamfer_ring(1.44,1.86,-2.31,-2.01,.265,.035),
                chamfer_ring(1.44,1.86,-2.31,-2.01,1.26,.035),
                chamfer_ring(1.48,1.84,-2.29,-2.03,1.47,.029)],"wall")
    kiosk.box((1.426,1.14,-2.16),(.07,.43,.285),"trim")
    kiosk.box((1.385,1.207,-2.16),(.013,.185,.203),"window")
    kiosk.box((1.384,1.015,-2.17),(.013,.050,.128),"rubber")
    kiosk.box((1.384,1.01,-2.08),(.013,.022,.021),"lamp_emissive",SIGNAL_COLORS["green"])
    kiosk.box((1.66,1.47,-2.16),(.38,.048,.30),"roof")
    kiosk.box((1.65,.46,-2.318),(.29,.35,.016),"metal")

    bollards = Part("bollards")
    for bx, bz in ((1.39,-3.57),(1.98,-3.57),(1.36,1.27),(1.99,3.35),(1.38,3.35)):
        bollards.cylinder((bx,floor,bz),(bx,floor+.033,bz),.110,"metal")
        for ya,yb,material in ((.033,.225,"plate"),(.225,.33,"rubber"),(.33,.54,"plate"),
                               (.54,.65,"rubber"),(.65,.833,"plate")):
            bollards.cylinder((bx,floor+ya,bz),(bx,floor+yb,bz),.068,material)
        bollards.cylinder((bx,floor+.833,bz),(bx,floor+.86,bz),.068,"plate",end_radius=.053)

    housing, boom = Part("boom_housing"), Part("boom_arm", BOOM_PIVOT)
    housing.box((1.18,.217,2.65),(.43,.070,.51),"metal")
    housing.loft([chamfer_ring(.99,1.37,2.43,2.87,.25,.035),
                  chamfer_ring(.99,1.37,2.43,2.87,1.208,.035),
                  chamfer_ring(1.015,1.345,2.455,2.845,1.275,.035)],"paint")
    housing.box((1.183,1.253,2.65),(.31,.026,.34),"trim")
    housing.box((1.182,.64,2.874),(.29,.66,.014),"wall")
    housing.box((1.27,.72,2.888),(.048,.075,.015),"trim")
    housing.cylinder((.812,1.02,2.65),(1.019,1.02,2.65),.093,"metal",12)
    housing.cylinder((.86,1.02,2.56),(.86,1.02,2.718),.059,"trim",10)
    # One continuous arm with alternating material segments. Its root is the pin.
    x0, y, z = BOOM_PIVOT
    for i in range(8):
        x1, x2 = x0-i*.4, x0-(i+1)*.4
        ring = lambda x: [(x,y-.052,z-.029),(x,y+.052,z-.029),
                          (x,y+.052,z+.029),(x,y-.052,z+.029)]
        faces = [(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
        if i == 0:
            faces.append((0,1,2,3))
        if i == 7:
            faces.append((4,7,6,5))
        boom.add(ring(x1)+ring(x2),faces,"wall" if i%2 else "paint")
    return [road,markings,island,booth,frames,glazing,interior,kiosk,bollards,housing,boom]


def sign_digit(part, number, x, y, z, front):
    segments = ("abcdef", "cf", "acdeg", "acdfg", "bcfg", "abdfg", "abdefg")
    offsets = {"a":(0,.205,1), "g":(0,0,1), "d":(0,-.205,1),
               "b":(-.097,.105,0), "c":(.097,.105,0),
               "e":(-.097,-.105,0), "f":(.097,-.105,0)}
    for segment in segments[number]:
        dx,dy,horizontal = offsets[segment]
        size = (.150,.037,.01) if horizontal else (.037,.151,.01)
        u,v = size[0]/2, size[1]/2
        dx *= front
        corners = [(x+dx+i*u,y+dy+j*v,z) for i,j in ((-1,-1),(1,-1),(1,1),(-1,1))]
        part.face(corners if front > 0 else corners[::-1],"light")


def canopy():
    roof, structure, trusses, gantry, fixtures = (Part(n) for n in
        ("canopy_roof", "portal_columns", "portal_trusses", "lane_gantry", "soffit_fixtures"))

    def crown(z):
        return 8 - .02845*z*z

    def roof_ring(x0, x1, z0, z1, y0, y1):
        return [(x0,y0,z0),(x1,y0,z0),(x1,y1,z1),(x0,y1,z1)]

    edges = np.linspace(-6.8,6.8,9)
    for a,b in zip(edges,edges[1:]):
        ya,yb = crown(a),crown(b)
        roof.loft([roof_ring(-15,15,a,b,ya-.14,yb-.14),
                   roof_ring(-15,15,a,b,ya,yb)],"roof")
    for x in np.linspace(-14.6,14.6,19):
        for a,b in zip(edges,edges[1:]):
            roof.face([(x-.012,min(8,crown(a)+.005),a),(x-.012,min(8,crown(b)+.004),b),
                       (x+.012,min(8,crown(b)+.004),b),(x+.012,min(8,crown(a)+.005),a)],"metal")
    for x in (-14.96,14.96):
        for a,b in zip(edges,edges[1:]):
            roof.bar((x,crown(a)-.13,a),(x,crown(b)-.13,b),.075,.29,"wall",up=(0,1,0))
    for z in (-6.71,6.71):
        roof.box((0,crown(6.8)-.12,z),(30,.24,.18),"wall")
        roof.box((0,crown(6.8)-.285,z),(29.9,.097,.16),"metal")
    # Four long side-supported trusses with a clear span over all six lanes.
    for z in (-5.45,-1.85,1.85,5.45):
        y_top = crown(z)-.20
        y_bottom = 5.32
        for x in (-14.70,14.70):
            structure.loft([chamfer_ring(x-.30,x+.30,z-.54,z+.54,0,.105),
                            chamfer_ring(x-.30,x+.30,z-.54,z+.54,.22,.105),
                            chamfer_ring(x-.277,x+.277,z-.45,z+.45,.32,.09)],"concrete")
            structure.box((x,2.85,z),(.49,5.06,.55),"wall")
            structure.box((x,5.43,z),(.58,.20,.74),"metal")
            if abs(z) == 5.45:
                structure.cylinder((x,.31,z+.36),(x,5.71,z+.36),.052,"metal",8)
        trusses.box((0,y_top,z),(29.57,.15,.22),"metal")
        trusses.box((0,y_bottom,z),(29.57,.19,.26),"metal")
        for i in range(9):
            x=-14.70+i*(29.4/8)
            trusses.box((x,(y_top+y_bottom)/2,z),(.125,y_top-y_bottom,.135),"metal")
            if i < 8:
                end=x+29.4/8
                a=(x,y_bottom if i%2 else y_top,z)
                b=(end,y_top if i%2 else y_bottom,z)
                trusses.bar(a,b,.105,.115,"metal")
    for z in np.linspace(-6.24,6.24,9):
        trusses.box((0,crown(z)-.207,z),(29.40,.125,.085),"metal")

    gantry.box((0,5.11,5.67),(29.28,.26,.29),"trim")
    gantry.box((0,5.27,5.67),(29.28,.057,.24),"metal")
    for x in (-14.54,14.54):
        gantry.box((x,5.30,5.53),(.15,.20,.39),"metal")

    lane_parts=[]
    for i in range(6):
        x = (i-2.5)*PITCH+LANE_CENTER
        number = i+1
        sign=Part(f"lane_{number:02d}_number")
        control=Part(f"lane_{number:02d}_control")
        traffic=Part(f"lane_{number:02d}_traffic_light")
        sign.box((x-.37,4.81,5.67),(.49,.62,.105),"trim")
        control.box((x+.36,4.82,5.67),(.79,.65,.145),"trim")
        traffic.box((x+1.20,4.79,5.67),(.27,.58,.20),"trim")
        state = "red" if number in (3,6) else "green"
        for front in (-1,1):
            sign.box((x-.37,4.81,5.67+front*.057),(.43,.56,.013),"plate")
            sign_digit(sign,number,x-.37,4.81,5.67+front*.068,front)
            cz=5.67+front*.084
            control.box((x+.36,4.82,cz),(.67,.55,.023),"rubber")
            control.box((x+.36,5.112,cz+front*.069),(.73,.036,.15),"trim")
            z=cz+front*.013
            c=x+.36
            color=SIGNAL_COLORS[state]
            if state == "green":
                points=[(-.065,.17),(.065,.17),(.065,-.017),(.195,-.017),
                        (0,-.203),(-.195,-.017),(-.065,-.017)]
                control.face([(c+u,4.82+v,z) for u,v in (points if front < 0 else reversed(points))],
                             "lamp_emissive",color)
            else:
                a,b = .165,.054
                points=[(-a,-a+b),(-a+b,-a),(0,-b),(a-b,-a),(a,-a+b),(b,0),
                        (a,a-b),(a-b,a),(0,b),(-a+b,a),(-a,a-b),(-b,0)]
                control.face([(c+u,4.82+v,z) for u,v in (points if front > 0 else reversed(points))],
                             "lamp_emissive",color)
            for index, lens in enumerate(("red","amber","green")):
                ly=4.97-index*.154
                live = lens == state
                for radius, depth, material in ((.060,.109,"metal"),
                                                (.046,.113,"lamp_emissive" if live else "window")):
                    points = [(x+1.20+radius*cos(2*pi*k/8),
                               ly+front*radius*sin(2*pi*k/8),5.67+front*depth) for k in range(8)]
                    traffic.face(points,material,SIGNAL_COLORS[lens] if material == "lamp_emissive" else None)
        lane_parts.extend((sign,control,traffic))
        for z in (-3.25,2.65):
            fixtures.box((x,crown(z)-.42,z),(1.43,.16,.29),"metal")
            fixtures.box((x,crown(z)-.51,z),(1.32,.028,.21),"light")
    return [roof,structure,trusses,gantry,fixtures,*lane_parts]


def building():
    podium, paving, wing_left, wing_right, rear = (Part(n) for n in
        ("building_podium", "entrance_paving", "west_wing", "east_wing", "rear_elevation"))
    curtain, curtain_frames, entrances, visor = (Part(n) for n in
        ("curved_glass_facade", "curtainwall_mullions", "entrance_doors", "projecting_entrance_roof"))
    upper, upper_windows, main_roof, plant = (Part(n) for n in
        ("upper_hall", "upper_hall_glazing", "main_roof", "roof_services"))

    def arc(x):
        return 8.74 - .0072*x*x

    def footprint(xs, front_offset, back, y, fn=arc):
        return [(xs[0],y,back),(xs[-1],y,back)] + [(x,y,fn(x)+front_offset) for x in reversed(xs)]

    def layer(part, xs, offset, back, bottom, top, mat, fn=arc):
        part.loft([footprint(xs,offset,back,bottom,fn),footprint(xs,offset,back,top,fn)],mat)

    xs=list(np.linspace(-22.8,22.8,21))
    podium.box((0,.215,-1.12),(60,.43,21.56),"concrete")
    podium.box((0,.12,-12.21),(54,.24,.38),"concrete")
    layer(paving,xs,2.30,3.2,0,.25,"concrete")
    layer(paving,xs,1.68,3.2,.25,.43,"wall")
    paving.box((0,.095,12.2),(10.60,.19,.40),"concrete")
    paving.box((0,.165,11.898),(10.60,.33,.224),"concrete")
    paving.box((0,.215,11.668),(10.60,.43,.241),"wall")
    paving.box((0,.215,10.982),(10.60,.43,1.146),"wall")
    for x in (-21.7,-16.3,16.3,21.7):
        z=arc(x)+.78
        paving.cylinder((x,.43,z),(x,4.65,z),.21,"wall",12)
        paving.cylinder((x,.43,z),(x,.63,z),.242,"concrete",12)
        paving.cylinder((x,4.56,z),(x,4.71,z),.258,"metal",12)

    for part, s in ((wing_left,-1),(wing_right,1)):
        part.box((s*25.92,2.89,-1.44),(6.62,4.92,17.84),"wall")
        part.box((s*26.25,5.52,-1.25),(7.50,.39,18.72),"wall")
        part.box((s*26.25,5.76,-1.25),(7.40,.15,18.53),"roof")
        part.box((s*21.45,5.45,-1.49),(3.45,.20,14.57),"wall")
        part.box((s*21.45,5.582,-1.49),(3.47,.070,14.62),"roof")
        part.box((s*26.25,1.30,7.527),(6.12,1.71,.078),"concrete")
        for j in range(4):
            x=s*(23.16+j*1.51)
            part.panel((x,3.58,7.54),(1.39,1.33),"window","z",1)
            part.box((x,2.88,7.559),(1.47,.093,.16),"metal")
            part.panel((x,3.57,7.549),(.045,1.30),"trim","z",1)
        for j in range(7):
            z=-8.7+j*2.21
            part.panel((s*29.257,3.62,z),(1.79,1.37),"window","x",s)
            part.panel((s*29.272,3.62,z),(.064,1.43),"trim","x",s)
            part.box((s*29.28,2.89,z),(.18,.095,1.89),"metal")
            part.panel((s*29.237,.74,z),(1.40,.51),"concrete","x",s)

    rear.box((0,2.55,-6.66),(46,4.24,9.6),"wall")
    rear.box((0,3.20,-11.495),(52,.25,.18),"metal")
    rear.box((0,4.56,-11.47),(54,.57,.20),"wall")
    rear.box((0,5.02,-10.97),(53,.37,1.38),"roof")
    for i in range(22):
        x=-25.2+i*2.4
        rear.panel((x,3.91,-11.582),(2.13,1.10),"window","z",-1)
        rear.panel((x,3.93,-11.598),(.045,1.07),"metal","z",-1)
        if i%4 == 1:
            rear.box((x,1.48,-11.518),(1.26,2.10,.094),"metal")
            rear.box((x+.45,1.33,-11.578),(.081,.29,.041),"trim")
        else:
            rear.box((x,1.45,-11.537),(1.49,.79,.074),"concrete")

    layer(curtain,xs,-.055,4.35,.43,.64,"trim")
    # Segmented curtain glazing follows the bow. Two horizontal glass registers
    # sit behind continuous spandrel bands and individual narrow mullions.
    for i,(a,b) in enumerate(zip(xs,xs[1:])):
        za,zb=arc(a),arc(b)
        entry = 8 <= i <= 11
        for bottom,top in ((2.86,4.63),) if entry else ((.64,2.30),(2.49,4.63)):
            curtain.face([(a,bottom,za),(b,bottom,zb),(b,top,zb),(a,top,za)],
                         "window" if i%5 == 1 else "glass")
        for y,h in ((.64,.12),(2.41,.19),(4.62,.12)):
            if entry and y<4:
                continue
            curtain_frames.bar((a,y,za+.02),(b,y,zb+.02),h,.104,"metal",up=(0,0,1))
    for i,x in enumerate(xs):
        bottom = 2.85 if 8 < i < 12 else .47
        curtain_frames.box((x,(bottom+4.70)/2,arc(x)+.013),(.080,4.70-bottom,.106),"metal")
        if i < 20 and not 8 <= i <= 11:
            a,b=x,xs[i+1]
            mid=(a+b)/2
            curtain_frames.panel((mid,2.59,(arc(a)+arc(b))/2+.025),(.039,4.06),"trim","z",1)
    for i in range(8,12):
        a,b=xs[i],xs[i+1]
        x=(a+b)/2
        z=(arc(a)+arc(b))/2+.045
        entrances.box((x,1.63,z-.15),(b-a,2.40,.24),"trim")
        entrances.box((x,1.67,z),(b-a-.17,2.03,.046),"window")
        entrances.box((x,2.78,z+.028),(b-a-.06,.18,.13),"metal")
        entrances.box((x,1.65,z+.043),(.064,2.14,.070),"metal")
        for dx in (-.27,.27):
            entrances.box((x+dx,1.43,z+.089),(.25,.044,.050),"chrome")
    layer(visor,xs,1.65,3.4,4.67,4.82,"trim")
    layer(visor,xs,1.92,3.15,4.82,5.57,"wall")
    layer(visor,xs,1.94,3.08,5.57,5.69,"roof")
    # Recessed planting beds behind the curved fascia frame the clerestory.
    for x in (-18.4,-12.5,12.5,18.4):
        z=arc(x)+.75
        visor.box((x,5.80,z),(3.30,.22,.58),"wall")
        visor.box((x,5.916,z),(3.16,.030,.45),"stone")
        for i in range(4):
            bx=x+(i-1.5)*.75
            y=5.92+.035*(i%2)
            visor.loft([chamfer_ring(bx-.30,bx+.30,z-.22,z+.22,5.922,.080),
                        chamfer_ring(bx-.20,bx+.20,z-.14,z+.14,y+.24,.052)],"leaf")
    for a,b in zip(xs,xs[1:]):
        for y,mat in ((4.94,"metal"),(5.45,"wall")):
            za,zb=arc(a)+1.932,arc(b)+1.932
            visor.face([(a,y-.016,za),(b,y-.016,zb),(b,y+.016,zb),(a,y+.016,za)],mat)

    def hall_front(x):
        return 6.38 - .0039*x*x

    ux=list(np.linspace(-19.9,19.9,19))
    layer(upper,ux,0,-8.6,4.26,6.25,"wall",hall_front)
    layer(upper,ux,-.19,-8.6,6.25,8.73,"wall",hall_front)
    layer(upper,ux,.04,-8.66,7.18,7.45,"wall",hall_front)
    layer(upper,ux,.09,-8.77,8.49,8.78,"wall",hall_front)
    for i,(a,b) in enumerate(zip(ux,ux[1:])):
        za,zb=hall_front(a)+.035,hall_front(b)+.035
        for lower,higher in ((6.28,7.18),(7.45,8.48)):
            upper_windows.face([(a,lower,za),(b,lower,zb),(b,higher,zb),(a,higher,za)],
                               "glass" if i%4 != 0 else "window")
        upper_windows.box((a,7.40,za+.03),(.057,2.23,.064),"trim")
    upper_windows.box((ux[-1],7.4,hall_front(ux[-1])+.065),(.057,2.23,.064),"trim")
    for side in (-1,1):
        for i in range(7):
            z = -7.54+i*1.82
            for y in (6.72,7.98):
                upper_windows.panel((side*19.943,y,z),(1.55,.89),"window","x",side)
                upper_windows.panel((side*19.957,y,z),(.046,.92),"trim","x",side)
    for i in range(18):
        x=-18.7+i*2.2
        for y in (6.68,7.98):
            upper_windows.panel((x,y,-8.669),(1.92,.91),"window","z",-1)
    layer(main_roof,ux,.58,-9.05,8.72,8.89,"trim",hall_front)
    layer(main_roof,ux,.71,-9.22,8.89,9.16,"wall",hall_front)
    layer(main_roof,ux,.62,-9.14,9.16,9.25,"roof",hall_front)
    for i in range(15):
        x=-18.5+i*2.64
        z=hall_front(x)+.26
        main_roof.face([(x-.018,9.255,-8.85),(x-.018,9.255,z),
                        (x+.018,9.255,z),(x+.018,9.255,-8.85)],"metal")
    for x,z,w,d in ((-9,-4.72,7.0,3.6),(8,-4.52,5.4,3.1)):
        plant.box((x,9.63,z),(w,.76,d),"wall")
        plant.box((x,10.06,z),(w+.18,.11,d+.18),"roof")
        plant.box((x,9.65,z-d/2-.015),(w-.52,.52,.07),"trim")
        for n in range(6):
            plant.panel((x,9.43+n*.087,z-d/2-.061),(w-.60,.027),"metal","z",-1)
    return [podium,paving,wing_left,wing_right,rear,curtain,curtain_frames,entrances,visor,
            upper,upper_windows,main_roof,plant]


MODELS = {"checkpoint_lane": lane, "checkpoint_canopy": canopy, "checkpoint_building": building}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    units = bpy.context.scene.unit_settings
    units.system, units.scale_length, units.length_unit = "METRIC", 1.0, "METERS"
    bpy.context.preferences.filepaths.temporary_directory = str(ROOT)


def export(name):
    reset()
    parts = MODELS[name]()
    materials = palette(name.removeprefix("checkpoint_"))
    for part in parts:
        part.build(materials)
    bpy.ops.export_scene.gltf(
        filepath=str(ROOT/f"{name}.glb"), export_format="GLB", export_yup=True,
        export_animations=False, export_skins=False, export_cameras=False, export_lights=False,
        export_texcoords=False, export_vertex_color="MATERIAL",
    )


def area(name, location, target, power, size, color):
    data = bpy.data.lights.new(name,"AREA")
    data.energy, data.shape, data.size, data.color = power,"DISK",size,color
    light = bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (target-location).to_track_quat("-Z","Y").to_euler()


VIEWS = {
    "front": (0,-1,0), "right": (1,0,0), "rear": (0,1,0),
    "front_three_quarter": (.85,-1.45,.66), "rear_three_quarter": (-.94,1.3,.80),
    "top": (0,0,1),
}


def render(name):
    reset()
    glb = ROOT/f"{name}.glb"
    bpy.ops.import_scene.gltf(filepath=str(glb))
    scene = bpy.context.scene
    corners = [obj.matrix_world@v.co for obj in scene.objects if obj.type=="MESH" for v in obj.data.vertices]
    low = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    target,span = (high+low)/2,max(high-low)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.render.threads_mode,scene.render.threads = "FIXED",2
    scene.render.resolution_x,scene.render.resolution_y = 620,370
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("Cloudy Singapore daylight")
    scene.world.use_nodes = True
    world = scene.world.node_tree.nodes["Background"]
    world.inputs["Color"].default_value = (.75,.85,1,1)
    world.inputs["Strength"].default_value = .61
    bpy.ops.mesh.primitive_plane_add(size=span*40,location=(0,0,-.04))
    bpy.context.object.data.materials.append(pbr("Review_ground",(.145,.16,.172),.91))
    area("Key",target+Vector((-.8,-.75,1.4))*span,target,span**2*18,span*.79,(1,.94,.85))
    area("Fill",target+Vector((.95,-.26,.85))*span,target,span**2*11,span*.9,(.80,.91,1))
    area("Rear",target+Vector((.15,1,1.4))*span,target,span**2*12,span*.92,(1,.95,.88))
    data = bpy.data.cameras.new("Review")
    cam = bpy.data.objects.new("Review",data)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    data.type,data.clip_end = "ORTHO",span*25
    w,h = scene.render.resolution_x,scene.render.resolution_y
    gap = 8
    sheet = np.full((2*h+gap,3*w+2*gap,4),.065,np.float32)
    sheet[:,:,3] = 1
    panel = ROOT/".render-panel.png"
    for index,(view,direction) in enumerate(VIEWS.items()):
        look = Vector(direction).normalized()
        cam.rotation_euler = (0,0,0) if view=="top" else (-look).to_track_quat("-Z","Y").to_euler()
        rotation = cam.rotation_euler.to_matrix()
        projected = [rotation.transposed()@(point-target) for point in corners]
        lo = [min(v[i] for v in projected) for i in (0,1)]
        hi = [max(v[i] for v in projected) for i in (0,1)]
        center = Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0))
        cam.location = target+look*span*3.6+rotation@center
        data.ortho_scale = max(hi[0]-lo[0],(hi[1]-lo[1])*w/h)*1.13
        scene.render.filepath = str(panel)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(panel),check_existing=False)
        values = np.empty(w*h*4,np.float32)
        img.pixels.foreach_get(values)
        y,x = (1-index//3)*(h+gap),(index%3)*(w+gap)
        sheet[y:y+h,x:x+w,:] = values.reshape(h,w,4)
        bpy.data.images.remove(img)
    panel.unlink()
    image = bpy.data.images.new("Six-view contact sheet",sheet.shape[1],sheet.shape[0],alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    path = ROOT/f"{name}_six_views.png"
    image.filepath_raw = str(path)
    image.file_format = "PNG"
    image.save()
    return {"file":path.name,"sha256":sha256(path.read_bytes()).hexdigest(),
            "glb_sha256":sha256(glb.read_bytes()).hexdigest(),"views":list(VIEWS),
            "renderer":"Blender 5.1.2 Cycles CPU","threads":2,"samples":16}


def main():
    assert bpy.app.version == (5,1,2), bpy.app.version_string
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    mode = args[0] if args else "all"
    names = args[1:] or list(MODELS)
    assert mode in ("build","render","all"),mode
    if mode in ("build","all"):
        for name in names:
            export(name)
    if mode in ("render","all"):
        path = ROOT/".render-evidence.json"
        capture = json.loads(path.read_text()) if path.exists() else {}
        capture.update({name:render(name) for name in names})
        path.write_text(json.dumps(capture,indent=2)+"\n")


if __name__ == "__main__":
    main()
