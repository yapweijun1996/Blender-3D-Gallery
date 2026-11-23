"""Generate Kit A in Blender. Geometry functions take metre coordinates in glTF space."""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PAINT = (0.79, 0.84, 0.89)
GLASS = (0.025, 0.082, 0.12)
TIRE = (0.018, 0.023, 0.029)
TRIM = (0.046, 0.065, 0.081)
METAL = (0.41, 0.49, 0.56)
LIGHT = (0.91, 0.94, 0.96)
RED = (0.79, 0.025, 0.047)
AMBER = (1, 0.53, 0.045)
GREEN = (0.025, 0.37, 0.25)
parts = []
materials = {}


def material(name, color=None):
    colors = dict(paint=PAINT, glass=GLASS, tire=TIRE, trim=TRIM, metal=METAL,
                  light=LIGHT, concrete=(0.31, 0.33, 0.34), roof=(0.23, 0.34, 0.37))
    base = colors[name] if name in ("paint", "tire", "concrete") else (1, 1, 1)
    color = color or colors[name]
    multiplier = tuple(c / b for c, b in zip(color, base))
    # Flat color variants share one named PBR material via COLOR_0.
    if name not in materials:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*base, 1)
        bsdf.inputs["Roughness"].default_value = dict(glass=.23, paint=.32, tire=.84, light=.34).get(name, .48)
        bsdf.inputs["Metallic"].default_value = dict(metal=.60, paint=.20).get(name, 0)
        materials[name] = mat
    return materials[name], multiplier


def xyz(point):
    x, y, z = point
    return x, -z, y


def mesh(name, points, faces, finish, color=None, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata([xyz(p) for p in points], [], faces)
    data.update()
    mat, color = material(finish, color)
    data.materials.append(mat)
    layer = data.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')
    for entry in layer.data:
        entry.color = (*color, 1)
    data.color_attributes.active_color = layer
    for face in data.polygons:
        face.use_smooth = smooth
    return data


def add(name, points, faces, finish, color=None, smooth=False):
    data = mesh(name, points, faces, finish, color, smooth)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    parts.append(obj)
    return obj


def panel(name, points, finish, color=None):
    return add(name, points, [(0, 1, 2, 3)], finish, color)


def loft(name, rings, finish, color=None, smooth=False, caps=True):
    count = len(rings[0])
    faces = [tuple(reversed(range(count)))] if caps else []
    for row in range(len(rings) - 1):
        for i in range(count):
            a, b = row * count + i, row * count + (i+1) % count
            faces.append((a, b, b + count, a + count))
    if caps:
        faces.append(tuple(range((len(rings)-1)*count, len(rings)*count)))
    obj = add(name, [p for ring in rings for p in ring], faces, finish, color, smooth)
    if caps and smooth:
        obj.data.polygons[0].use_smooth = False
        obj.data.polygons[-1].use_smooth = False
    return obj


def outline(half_w, low, high, bevel):
    return [(-half_w+bevel, low), (half_w-bevel, low), (half_w, low+bevel),
            (half_w, high-bevel), (half_w-bevel, high), (-half_w+bevel, high),
            (-half_w, high-bevel), (-half_w, low+bevel)]


def box(name, center, size, finish, color=None, radius=0):
    x, y, z = center
    w, h, d = (n/2 for n in size)
    if not radius:
        rings = [[(x+dx, y+dy, z+dz) for dx,dy in ((-w,-h),(w,-h),(w,h),(-w,h))]
                 for dz in (-d,d)]
    else:
        r = min(radius, w*.45, h*.45, d*.45)
        rings = [[(x+dx,y+dy,z+dz) for dx,dy in outline(width,-height,height,bevel)]
                 for width,height,bevel,dz in
                 ((w-r,h-r,r*.3,-d), (w,h,r,-d+r), (w,h,r,d-r), (w-r,h-r,r*.3,d))]
    return loft(name, rings, finish, color)


def tube(name, centers, radii, sides, finish, color=None, axis_hint=None, caps=True, smooth=True):
    rings = []
    for i, (center, radius) in enumerate(zip(centers, radii)):
        tangent = (Vector(centers[min(i+1,len(centers)-1)]) - Vector(centers[max(i-1,0)])).normalized()
        guide = Vector(axis_hint or ((0,0,1) if abs(tangent.z)<.85 else (1,0,0)))
        u = (guide - tangent * guide.dot(tangent)).normalized()
        v = tangent.cross(u)
        rings.append([tuple(Vector(center) + radius*(math.cos(j*math.tau/sides)*u +
                      math.sin(j*math.tau/sides)*v)) for j in range(sides)])
    return loft(name, rings, finish, color, smooth, caps)


def cylinder(name, a, b, radius, sides, finish, color=None, caps=True):
    return tube(name, (a,b), (radius,radius), sides, finish, color, caps=caps)


def wheel(x, y, z, r, width, sides=12, detailed=True, rim="metal"):
    # A rolled rubber shoulder catches light without an added tread mesh.
    spans = (-.5, -.33, .33, .5)
    tube("Tyre", [(x+width*t,y,z) for t in spans], [r*v for v in (.86,1,1,.86)], sides, "tire", axis_hint=(0,1,0))
    for s in ([-1,1] if abs(x)<.01 else [1 if x>0 else -1]):
        start = x+s*(width*.495)
        face = x+s*(width*.507)
        cylinder("Rim", (start,y,z),(face,y,z),r*.66,sides if detailed else 8,rim,(.41,.49,.56),caps=True)
        hub = x+s*(width*.525)
        if detailed:
            for j in range(5):
                angle = math.tau*j/5
                points = [(hub, y+r*f*math.cos(angle+off), z+r*f*math.sin(angle+off))
                          for f,off in ((.24,-.36),(.58,-.20),(.58,.20),(.24,.36))]
                panel("Spoke inset",points,"trim")
            cylinder("Hub", (face,y,z),(hub+s*.002,y,z),r*.19,8,rim,(.66,.70,.74))


def mix(a,b,t):
    return tuple(x+(y-x)*t for x,y in zip(a,b))


def patch(name, quad, finish, u0=0, u1=1, v0=0, v1=1, color=None):
    a,b,c,d = quad
    def at(u,v):
        return mix(mix(a,b,u),mix(d,c,u),v)
    panel(name,[at(u0,v0),at(u1,v0),at(u1,v1),at(u0,v1)],finish,color)


def autobody(name, stations, finish="paint", bevel=.08):
    # Each station has its own sill height, allowing actual wheel cutouts.
    rings = []
    for z, bottom, belt, w in stations:
        shoulder = min(bevel, (belt-bottom)*.3)
        rings.append([(x,y,z) for x,y in outline(w,bottom,belt,shoulder)])
    return loft(name,rings,finish)


def car(sedan):
    length, width = (4.6, 1.8) if sedan else (4, 1.75)
    nose, w = length/2, width/2
    front, rear = nose-.78, -nose+.76
    r = .318 if sedan else .306
    axle_x = (w-.113)/1.0015
    for x in (-axle_x,axle_x):
        for z in (rear,front):
            wheel(x,r,z,r,.222,14)
    box("Underfloor", (0,.265,0), (1.20,.23,length-.38), "trim", radius=.065)

    stations = [(-nose,.35,.71,w-.15),(-nose+.14,.23,.77,w-.06),
                (rear-.47,.26,.81,w-.02), (rear+.48,.23,.82,w-.025),
                (0,.23,.82,w-.035), (front-.48,.23,.81,w-.025),
                (front+.48,.25,.72,w-.025),(nose-.14,.26,.67,w-.06),(nose,.34,.62,w-.16)]
    for axle in (rear,front):
        for offset in (-.40,-.35,-.27,-.15,0,.15,.27,.35,.40):
            bottom = r+math.sqrt(max(0,.368**2-offset**2)) if abs(offset)<.368 else .265
            stations.append((axle+offset,bottom,.81 if axle==rear else .81-.095*(offset+.40)/.80,w))
    stations.sort()
    autobody("Sculpted body and fender openings",stations,bevel=.078)

    roof = 1.37 if sedan else 1.45
    base_back = -nose+(.62 if sedan else .16)
    top_back = -nose+(1.30 if sedan else .44)
    base_front, top_front = nose-.71, nose-1.49
    # Cabin corners are clipped in plan, and the windscreen and hatch lean into the roof.
    def cabin_ring(side, y, back, fore):
        corner = .095
        return [(-side+corner,y,back),(side-corner,y,back),(side,y,back+corner),
                (side,y,fore-corner),(side-corner,y,fore),(-side+corner,y,fore),
                (-side,y,fore-corner),(-side,y,back+corner)]
    lower = cabin_ring(w-.11,.718,base_back,base_front)
    upper = cabin_ring(w-.255,roof-.075,top_back,top_front)
    crown = cabin_ring(w-.30,roof,top_back+.067,top_front-.067)
    loft("Cabin and roof", [lower,upper,crown],"paint")
    for i in (0,2,4,6):
        j=(i+1)%8
        quad = [lower[i],lower[j],upper[j],upper[i]]
        normal = (Vector(quad[1])-Vector(quad[0])).cross(Vector(quad[3])-Vector(quad[0])).normalized()
        quad = [tuple(Vector(p)-.009*normal) for p in quad]
        if i in (0,4):
            patch("Windscreen" if i==4 else "Rear glass", quad,"glass",.045,.955,.115,.95)
        else:
            for a,b in ((.03,.18),(.21,.51),(.555,.97)) if i==2 else ((.03,.445),(.49,.79),(.82,.97)):
                patch("Side glazing",quad,"glass",a,b,.142,.94)

    for s in (-1,1):
        # Rear combination lamps and swept front lighting use outlines instead of rectangular boxes.
        panel("Smoked headlight housing", [(s*x,y,nose+.002) for x,y in
              ((.381,.508),(w-.153,.508),(w-.151,.576),(.45,.595))],"trim")
        panel("Daytime running light", [(s*x,y,nose+.004) for x,y in
              ((.425,.557),(w-.178,.540),(w-.175,.562),(.45,.578))],"light")
        panel("Headlamp reflector", [(s*x,y,nose+.004) for x,y in
              ((.448,.521),(w-.20,.521),(w-.205,.538),(.46,.547))],"light",(.61,.78,.94))
        panel("Tail lamp", [(s*x,y,z) for x,y,z in
              ((.43,.540,-nose-.001),(w-.163,.540,-nose-.001),
               (w-.150,.663,-nose-.002),(.49,.643,-nose-.002))],"light",RED)
        panel("Rear light return", [(s*x,y,z) for x,y,z in
              ((w-.163,.54,-nose-.001),(w-.071,.559,-nose+.138),
               (w-.071,.697,-nose+.136),(w-.150,.663,-nose-.002))],"light",RED)
        for z in (-.66,.14,.66):
            x = s*(w-.020)
            panel("Door shut line",[(x,.397,z),(x,.397,z+.012),(x,.771,z+.075),(x,.771,z+.063)],"trim")
        x = s*(w-.022)
        panel("Door sill crease",[(x,.389,-.66),(x,.389,.672),(x,.402,.67),(x,.402,-.66)],"trim")
        for z in (-.55,.30):
            box("Door handle",(s*(w-.022),.748,z),(.025,.035,.15),"trim",radius=.008)
        box("Mirror stalk",(s*(w-.11),.935,base_front-.21),(.18,.038,.055),"trim")
        box("Mirror housing",(s*(w-.09),.975,base_front-.23),(.18,.10,.21),"paint",radius=.029)
        panel("Mirror glass",[(s*x,y,base_front-.336) for x,y in
              ((w-.156,.95),(w-.026,.95),(w-.028,1.001),(w-.151,1.001))],"glass")
    panel("Upper grille", [(-.38,.51,nose+.001),(.38,.51,nose+.001),(.33,.569,nose+.001),(-.33,.569,nose+.001)],"trim")
    panel("Lower bumper intake",[(-.56,.395,nose+.001),(.56,.395,nose+.001),(.48,.469,nose+.001),(-.48,.469,nose+.001)],"trim")
    panel("Rear bumper insert",[(-.55,.388,-nose-.001),(.55,.388,-nose-.001),(.51,.45,-nose-.001),(-.51,.45,-nose-.001)],"trim")
    panel("Rear plate",[(-.14,.478,-nose-.002),(.14,.478,-nose-.002),(.14,.545,-nose-.002),(-.14,.545,-nose-.002)],"light",(.78,.78,.72))
    if sedan:
        box("Taxi roof sign",(0,1.406,.14),(.49,.088,.245),"light",AMBER,.026)
        panel("Taxi sign front face",[(-.187,1.386,.264),(.187,1.386,.264),(.170,1.433,.264),(-.17,1.433,.264)],"light",(.96,.79,.30))
        for s in (-1,1):
            for i in range(8):
                z = -.49 + i*.137
                x = s*(w-.012)
                panel("Taxi side band",[(x,.55,z),(x,.55,z+.122),(x,.643,z+.147),(x,.643,z+.025)],
                      "trim",(.038,.27,.48) if i%2==0 else (.067,.45,.68))


def bus():
    w, end = 1.25, 5.50
    for z in (-3.34, 3.48):
        for x in (-1.085, 1.085):
            wheel(x,.50,z,.50,.292,16,rim="trim")
    box("Bus chassis",(0,.46,0),(1.57,.49,10.50),"trim",radius=.10)
    stations = [(-end+.004,.57,2.93,1.07),(-end+.23,.47,3.07,1.225),
                (-4.96,.49,3.11,w),(-1.6,.49,3.11,w),(1.65,.49,3.11,w),
                (4.99,.49,3.11,w),(end-.24,.49,3.08,1.22),(end-.004,.62,2.94,1.07)]
    for axle in (-3.34,3.48):
        for offset in (-.61,-.54,-.39,-.22,0,.22,.39,.54,.61):
            stations.append((axle+offset,max(.49,.49+math.sqrt(max(0,.55**2-offset**2))),3.11,w))
    autobody("Low-floor coach body",sorted(stations),bevel=.155)
    box("Roof equipment",(0,3.107,-.72),(1.78,.186,2.68),"paint",radius=.075)
    for k in range(5):
        box("Roof grille slat",(0,3.194,-1.64+k*.13),(1.16,.012,.049),"trim")
    for s in (-1,1):
        def side(label,z0,z1,y0,y1,finish,color=None,depth=0):
            x = s*(1.252+depth)
            panel(label,[(x,y0,z0),(x,y0,z1),(x,y1,z1),(x,y1,z0)],finish,color)
        side("Continuous window surround",-4.94,4.98,1.48,2.81,"trim")
        for z0,z1 in ((-4.89,-3.76),(-3.69,-2.28),(-2.22,-.79),(-.72,.71),
                      (.77,2.15),(2.22,3.62),(3.68,4.92)):
            if s < 0 or (z0 not in (-.72,3.68)):
                side("Passenger window",z0,z1,1.62,2.76,"glass",depth=.002)
        if s > 0:  # Left side when looking in the direction of travel (+Z).
            for z0,z1 in ((-.72,.71),(3.68,4.92)):
                side("Full-height door frame",z0-.045,z1+.035,.63,2.81,"trim",depth=.003)
                mid = (z0+z1)/2
                for a,b in ((z0,mid-.035),(mid+.035,z1)):
                    side("Door glass",a,b,.83,2.72,"glass",depth=.004)
        for a,b in ((-4.96,-4.02),(-2.65,-.80),(.80,2.83),(4.12,4.95)):
            if s>0 and a==4.12:
                continue
            side("Lower service livery",a,b,.70,.84,"trim",GREEN)
        for z in (-4.72,2.87):
            side("Amber position marker",z,z+.15,.90,.99,"light",AMBER)
        box("Mirror stalk",(s*1.135,2.06,5.24),(.18,.052,.060),"trim")
        box("Bus mirror",(s*1.184,1.96,5.23),(.132,.33,.135),"trim",radius=.031)
        panel("Mirror reflective face",[(s*x,y,5.161) for x,y in
              ((1.143,1.84),(1.224,1.84),(1.224,2.074),(1.143,2.074))],"glass")
        for z in (-1,1):
            nose=z*5.50
            panel("Combination lamp backing",[(s*x,y,nose) for x,y in
                  ((.665,.753),(1.012,.753),(1.012,1.058),(.742,1.018))],"trim")
            panel("Front corner lamp" if z>0 else "Rear cluster",
                  [(s*x,y,nose+.002*z) for x,y in ((.71,.79),(.982,.79),(.982,1.022),(.776,.979))],
                  "light", LIGHT if z>0 else RED)
            panel("Corner indicator",[(s*x,y,nose+.003*z) for x,y in
                  ((.904,.823),(.967,.823),(.967,.970),(.904,.955))],"light",AMBER)
    panel("Front windscreen",[(-.975,1.19,end),(.975,1.19,end),(.93,2.48,end),(-.93,2.48,end)],"glass")
    panel("Destination display",[(-.92,2.53,end),(.92,2.53,end),(.90,2.86,end),(-.90,2.86,end)],"trim")
    for i,width in enumerate((.14,.22,.17,.18,.18,.21,.11)):
        x=-.78+i*.228
        panel("Amber display segments",[(x,2.645,end+.001),(x+width,2.645,end+.001),
                                        (x+width,2.741,end+.001),(x,2.741,end+.001)],"light",AMBER)
    for s in (-1,1):
        panel("Windscreen wiper",[(s*.20,1.23,end+.001),(s*.23,1.23,end+.001),
                                 (s*.49,1.51,end+.001),(s*.46,1.51,end+.001)],"trim")
    panel("Rear saloon glazing",[(-.92,1.77,-end),(.92,1.77,-end),(.92,2.74,-end),(-.92,2.74,-end)],"glass")
    for z in (-end,end):
        panel("Lower bumper surround",[(-.94,.66,z),(.94,.66,z),(.88,.74,z),(-.88,.74,z)],"trim")
    for i in range(5):
        y=1.06+i*.086
        panel("Rear ventilation slit",[(-.69,y,-end),(.69,y,-end),(.69,y+.031,-end),(-.69,y+.031,-end)],"trim")


def motorbike():
    for z in (-.72,.72):
        wheel(0,.23,z,.23,.118,12,False)
    autobody("Rear scooter fairing",[(-.94,.43,.54,.115),(-.82,.32,.65,.195),
                                    (-.55,.27,.727,.214),(-.29,.25,.686,.174),(.02,.237,.38,.137)],
             bevel=.078)
    autobody("Rider floorboard",[(-.48,.235,.31,.15),(-.26,.20,.291,.194),
                                (.31,.20,.291,.181),(.51,.265,.33,.139)],"trim",.027)
    loft("Tapered saddle", [[(x,y,z) for x,y in outline(w,b,t,.028)] for z,w,b,t in
          ((-.77,.112,.622,.715),(-.63,.179,.653,.776),(-.40,.161,.635,.749),(-.16,.112,.618,.697))],"trim")
    for s in (-1,1):
        cylinder("Front fork",(s*.069,.23,.72),(s*.072,.79,.46),.036,6,"metal")
    panel("Tail light surround",[(-.101,.473,-.942),(.101,.473,-.942),
                                  (.089,.531,-.942),(-.089,.531,-.942)],"trim")
    panel("Tail light lens",[(-.083,.483,-.945),(.083,.483,-.945),
                              (.076,.520,-.945),(-.076,.520,-.945)],"light",RED)
    autobody("Front leg shield",[(.25,.245,.57,.125),(.35,.30,.84,.201),
                                  (.48,.42,.894,.185),(.58,.56,.849,.126)],bevel=.068)
    # The painted guard follows the curvature of the front tyre.
    autobody("Front mudguard",[(.49,.32,.40,.08),(.57,.387,.457,.104),(.72,.426,.504,.114),
                                (.84,.385,.461,.105),(.92,.324,.392,.086)],bevel=.029)
    tube("Handlebar",[(-.315,.935,.31),(-.17,.928,.406),(0,.91,.45),(.17,.928,.406),(.315,.935,.31)],
         [.023]*5,6,"metal")
    for s in (-1,1):
        cylinder("Grip",(s*.228,.93,.374),(s*.315,.935,.31),.031,6,"trim")
        cylinder("Mirror stem",(s*.203,.93,.378),(s*.289,1.10,.357),.011,5,"metal")
        loft("Chamfered mirror", [[(s*.303+x,1.116+y,z) for x,y in outline(.071,-.032,.032,.012)]
                                 for z in (.327,.380)],"trim")
        panel("Mirror face",[(s*.303+x,1.116+y,.326) for x,y in
              ((-.054,-.021),(.054,-.021),(.054,.021),(-.054,.021))],"glass")
    panel("Headlamp surround",[(-.106,.735,.582),(.106,.735,.582),(.067,.819,.582),(-.067,.819,.582)],"trim")
    panel("Headlamp lens",[(-.084,.750,.585),(.084,.750,.585),(.053,.802,.585),(-.053,.802,.585)],"light")
    panel("Instrument pod",[(-.071,.895,.303),(.071,.895,.303),(.098,.932,.456),(-.098,.932,.456)],"glass")


def street_lamp():
    centers = [(0,.10,0),(0,.88,0),(0,6.90,0),(.032,7.66,0),(.166,8.19,0),
               (.418,8.56,0),(.778,8.785,0),(1.26,8.884,0),(1.73,8.911,0),(2.26,8.891,0)]
    tube("Tapered curved outreach",centers,[.118,.107,.077,.069,.064,.061,.056,.05,.047,.041],10,"metal",axis_hint=(0,0,1))
    cylinder("Flanged service foot",(0,0,0),(0,.12,0),.231,10,"metal")
    cylinder("Lower pole sleeve",(0,.12,0),(0,.81,0),.142,10,"metal")
    box("Luminaire housing",(2.139,8.90,0),(.722,.20,.301),"metal",radius=.067)
    box("Recessed lamp lens",(2.173,8.803,0),(.53,.023,.211),"light")


def traffic_light():
    cylinder("Pole foot",(0,0,0),(0,.105,0),.235,8,"metal")
    tube("Raised signal mast",[(0,.10,0),(0,3.16,0),(0,4.91,0)],[.103,.088,.068],8,"metal")
    cylinder("Mount arm",(0,4.22,-.074),(.875,4.22,-.074),.062,8,"metal")
    for x,y in ((0,4.35),(.875,3.98)):
        box("Signal head",(x,y,.105),(.42,1.30,.25),"trim")
        for dy,color in ((.39,RED),(0,AMBER),(-.39,GREEN)):
            center = y+dy
            cylinder("Signal lens",(x,center,.232),(x,center,.250),.123,8,"light",color)
            rings=[]
            for z, fall in ((.228,0),(.377,.040)):
                points = []
                for j in range(6):
                    angle=math.pi*j/5
                    points.append((x+.145*math.cos(angle),center+.149*math.sin(angle)-fall,z))
                rings.append(points)
            # Open-ended visors allow the lens to remain visible from the approach.
            add("Signal sun visor",rings[0]+rings[1],[(j,j+1,j+7,j+6) for j in range(5)],"trim",smooth=True)


def sign_gantry():
    for x in (-6.73,6.73):
        box("Concrete footing",(x,.22,0),(.54,.44,.64),"concrete")
        box("Wide flange post",(x,3.58,0),(.27,6.88,.27),"metal")
        for z in (-.159,.159):
            box("Post flange",(x,3.58,z),(.43,6.88,.057),"metal")
    for y in (6.645,7.365):
        box("Truss chord",(0,y,-.041),(13.60,.29,.32),"metal")
    for x in (-6.55,-4.30,-2.15,0,2.15,4.30,6.55):
        box("Truss upright",(x,7.0,-.04),(.10,.70,.15),"metal")
    for i in range(6):
        x=-6.50+i*2.17
        a,b=(6.76,7.25) if i%2==0 else (7.25,6.76)
        cylinder("Diagonal brace",(x,a,-.04),(x+2.15,b,-.04),.048,4,"metal")
    for x in (-3.33,3.33):
        box("Sign backing",(x,6.99,.184),(4.65,.94,.11),"metal",radius=.036)
        box("Blank green panel",(x,6.99,.247),(4.54,.837,.026),"trim",(.016,.195,.075))
        for offset in (-1.66,1.66):
            box("Back bracket",(x+offset,6.99,.112),(.117,.98,.105),"metal")


def bus_stop():
    for x in (-1.45,1.45):
        for z in (-.67,.61):
            box("Bolt-down foot",(x,.028,z),(.229,.056,.209),"metal")
            box("Shelter post",(x,1.25,z),(.118,2.43,.113),"metal")
    roof_rings=[]
    for x in (-1.75,1.75):
        roof_rings.append([(x,y,z) for z,y in
            ((-.82,2.43),(-.80,2.52),(-.55,2.60),(-.11,2.66),(.34,2.65),
             (.72,2.58),(.90,2.51),(.91,2.44),(.74,2.48),(.34,2.55),
             (-.11,2.56),(-.55,2.50))])
    loft("Curved canopy",roof_rings,"roof")
    for x in (-1.46,0,1.46):
        box("Glazing frame upright",(x,1.30,-.676),(.060,1.97,.069),"metal")
    for y in (.36,2.24):
        box("Glazing frame rail",(0,y,-.676),(2.94,.063,.083),"metal")
    for x in (-.74,.74):
        box("Blue-grey rear panel",(x,1.44,-.679),(1.39,1.535,.045),"glass",(.094,.218,.257))
        box("Rear kick plate",(x,.47,-.674),(1.40,.28,.058),"trim")
        panel("Glazing safety band",[(x-.683,1.51,-.654),(x+.683,1.51,-.654),
                                     (x+.683,1.56,-.654),(x-.683,1.56,-.654)],"metal")
    for x in (-.91,.91):
        box("Bench pedestal",(x,.23,-.15),(.095,.46,.138),"metal")
        box("Bench underframe",(x,.422,-.15),(.102,.071,.41),"metal")
    for z in (-.33,-.21,-.09,.03):
        box("Seat slat",(0,.48,z),(2.31,.055,.108),"roof",(.45,.25,.109),.012)
    for y in (.75,.86):
        box("Backrest slat",(0,y,-.37),(2.31,.082,.063),"roof",(.45,.25,.109),.012)
    for x in (-.91,.91):
        box("Backrest bracket",(x,.66,-.40),(.064,.47,.068),"metal")
    cylinder("Stop flag pole",(1.56,0,1.01),(1.56,2.88,1.01),.039,8,"metal")
    box("Stop flag",(1.53,2.713,1.027),(.39,.34,.079),"trim",GREEN,.025)
    panel("Stop flag header",[(1.372,2.77,1.069),(1.688,2.77,1.069),
                             (1.688,2.83,1.069),(1.372,2.83,1.069)],"light")


def guardrail():
    for z in (-1,1):
        box("Driven guardrail post",(-.10,.38,z),(.115,.76,.103),"metal")
        box("Stand-off block",(-.006,.64,z),(.147,.184,.141),"metal")
    # Both end profiles are identical and terminate at z = +/-2, ready for repetition.
    cross = [( .008,.58),(.059,.598),(.105,.631),(.105,.670),(.048,.712),
             (.048,.752),(.105,.796),(.105,.838),(.059,.875),(.008,.891)]
    profile = cross + [(x-.012,y) for x,y in reversed(cross)]
    loft("Roll-formed W-beam",[[(x,y,z) for x,y in profile] for z in (-2,2)],"metal")
    for z in (-1,1):
        cylinder("Rail bolt",(.050,.733,z),(.060,.733,z),.022,6,"metal",(.65,.70,.72))


def road_cone():
    loft("Weighted square base", [[(x,y,z) for x,z in outline(w,-w,w,.029)]
                                      for w,y in ((.18,0),(.157,.056))],"tire")
    # Shared radii at stripe boundaries give a continuous tapered road cone.
    bands = ((.051,.141),(.255,.074),(.413,.035),(.467,.022))
    for index,finish in enumerate(("trim","light","trim")):
        (y0,r0),(y1,r1) = bands[index:index+2]
        tube("Reflective band" if index==1 else "Orange cone casing",
             [(0,y0,0),(0,y1,0)],[r0,r1],12,finish,
             LIGHT if index==1 else (1,.21,.026),axis_hint=(1,0,0),caps=False)
    # Close the top without a second bottom inside the weighted foot.
    points=[(.022*math.cos(j*math.tau/12),.467,-.022*math.sin(j*math.tau/12)) for j in range(12)]
    add("Cone tip",points,[tuple(range(12))],"trim",(1,.21,.026))


MODELS = {
    "car_hatchback": lambda: car(False), "car_sedan": lambda: car(True), "bus": bus,
    "motorbike": motorbike, "street_lamp": street_lamp, "traffic_light": traffic_light,
    "sign_gantry": sign_gantry, "bus_stop": bus_stop, "guardrail": guardrail, "road_cone": road_cone,
}
# X width, Y height, Z length. Unspecified axes keep their original measurements.
FIXED_SIZE = {
    "car_hatchback": (1.75,1.45,4), "car_sedan":(1.8,1.45,4.6), "bus":(2.5,3.2,11),
    "motorbike":(None,None,1.9), "street_lamp":(None,9,None), "traffic_light":(None,5,None),
    "sign_gantry":(14,None,None), "bus_stop":(3.5,None,None), "guardrail":(None,None,4),
}
# A street lamp and a signal mast pivot about the foot of the principal post.
BASE_OFFSETS = {"street_lamp":(0,0), "traffic_light":(0,0), "bus_stop":(0,-.03),
                "guardrail":(-.10,0)}


def finish(name):
    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    model = bpy.context.object
    model.name = name
    bm = bmesh.new()
    bm.from_mesh(model.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.00001)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(model.data)
    bm.free()
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0

    vertices = model.data.vertices
    points = [(p.co.x,p.co.z,-p.co.y) for p in vertices]
    lo = [min(v[i] for v in points) for i in range(3)]
    hi = [max(v[i] for v in points) for i in range(3)]
    cx,cz = BASE_OFFSETS.get(name,((lo[0]+hi[0])/2,(lo[2]+hi[2])/2))
    center = (cx,lo[1],cz)
    target = FIXED_SIZE.get(name,(None,None,None))
    factors = [t/(b-a) if t else 1 for a,b,t in zip(lo,hi,target)]
    for vert,point in zip(vertices,points):
        vert.co = xyz([(p-c)*f for p,c,f in zip(point,center,factors)])
    model.data.update()
    bpy.ops.export_scene.gltf(filepath=str(ROOT / f"{name}.glb"), export_format='GLB',
                              export_yup=True, export_apply=True, export_vertex_color='ACTIVE',
                              export_animations=False, export_cameras=False, export_lights=False)


def main():
    bpy.context.preferences.filepaths.temporary_directory = str(ROOT)
    requested = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    for name in requested or MODELS:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.temporary_directory = str(ROOT)
        materials.clear()
        parts.clear()
        MODELS[name]()
        finish(name)


if __name__ == "__main__":
    main()
