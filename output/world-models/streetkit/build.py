"""Build and photograph the Singapore street kit with Blender 5.1.2."""
import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PALETTE = {
    'silver': ('metal', '939e9c'), 'galv': ('metal', 'a5afae'),
    'steel': ('metal', '5d6a6a'), 'iron': ('metal', '394244'),
    'chrome': ('chrome', 'ccd2d2'), 'green': ('paint', '08764d'),
    'blue': ('paint', '005caa'), 'white': ('paint', 'f5f4eb'),
    'red': ('paint', 'c8212b'), 'yellow': ('paint', 'f5bc23'),
    'black': ('paint', '202326'), 'orange': ('paint', 'ed601e'),
    'violet': ('paint', '6c307a'), 'teal': ('paint', '187b76'),
    'roof': ('roof', 'a5babe'), 'roof_edge': ('roof', 'd0dbda'),
    'glass': ('glass', 'b7d9d5'), 'window': ('window', '151a1c'),
    'concrete': ('concrete', 'a6a6a0'), 'dark_concrete': ('concrete', '777a76'),
    'grey': ('trim', '5a665f'), 'charcoal': ('trim', '262e30'),
    'beige': ('wall', 'b4bdac'), 'olive': ('wall', '627368'),
    'rubber': ('rubber', '242c2c'), 'plate': ('plate', 'eff0df'),
    'tile': ('stone', 'dfa925'), 'tile_ridge': ('stone', 'ecb438'), 'amber_lens': ('light', 'bf741d'),
    'red_lens': ('light', 'aa292a'), 'green_lens': ('light', '247858'),
    'signal_red': ('light', 'f9504d'), 'signal_green': ('light', '43dc99'),
    'countdown_red': ('lamp_emissive', 'ff5650'), 'emitter': ('lamp_emissive', 'fff2cf'),
    'recycling': ('paint', '087fc1'), 'leaf_green': ('paint', '3f622f'),
    'lush': ('paint', '8ac442'), 'rainforest': ('paint', '084e51'), 'seat': ('trim', 'a17e59'),
}
PARTS = defaultdict(lambda: ([], [], [], []))


def geo(part, verts, faces, tone, smooth=False):
    vertices, polygons, tones, smoothing = PARTS[part]
    start = len(vertices)
    vertices.extend(verts)
    polygons.extend(tuple(start + i for i in face) for face in faces)
    tones.extend([tone] * len(faces))
    smoothing.extend([smooth] * len(faces))


def profile(part, points, y, depth, tone):
    """Extrude an x/z profile. A zero-depth profile has its normal towards the street."""
    points = list(points)
    area = sum(x * z2 - x2 * z for (x, z), (x2, z2)
               in zip(points, points[1:] + points[:1]))
    if area < 0:
        points.reverse()
    n = len(points)
    front = [(x, y - depth / 2, z) for x, z in points]
    if not depth:
        geo(part, front, [tuple(range(n))], tone)
        return
    back = [(x, y + depth / 2, z) for x, z in points]
    faces = [tuple(range(n)), tuple(reversed(range(n, n * 2)))]
    faces += [(j, i, i+n, j+n) for i in range(n) for j in [(i+1) % n]]
    geo(part, front + back, faces, tone)


def box(part, x, y, z, w, d, h, tone):
    profile(part, [(x-w/2, z-h/2), (x+w/2, z-h/2),
                   (x+w/2, z+h/2), (x-w/2, z+h/2)], y, d, tone)


def plate(part, x, y, z, w, h, r, depth, tone):
    points = [(x-w/2+r,z-h/2), (x+w/2-r,z-h/2), (x+w/2,z-h/2+r),
              (x+w/2,z+h/2-r), (x+w/2-r,z+h/2), (x-w/2+r,z+h/2),
              (x-w/2,z+h/2-r), (x-w/2,z-h/2+r)]
    profile(part, points, y, depth, tone)


def flat(part, points, z, tone):
    points = list(points)
    area = sum(x * y2 - x2 * y for (x, y), (x2, y2)
               in zip(points, points[1:] + points[:1]))
    if area < 0:
        points.reverse()
    geo(part, [(x,y,z) for x,y in points], [tuple(range(len(points)))], tone)


def rail(part, a, b, w, d, tone):
    start, end = Vector(a), Vector(b)
    direction = (end - start).normalized()
    u = direction.cross(Vector((0, 1, 0))).normalized()
    if u.length < .5:
        u = direction.cross(Vector((1, 0, 0))).normalized()
    v = direction.cross(u)
    offsets = [-u*w/2-v*d/2, u*w/2-v*d/2, u*w/2+v*d/2, -u*w/2+v*d/2]
    rings(part, [[tuple(p + q) for q in offsets] for p in (start, end)], tone)


def rings(part, sections, tone, cap=True, smooth=False):
    n = len(sections[0])
    faces = []
    if cap:
        faces.append(tuple(reversed(range(n))))
    for k in range(len(sections)-1):
        a = k*n
        for i in range(n):
            j = (i+1) % n
            faces.append((a+i,a+j,a+n+j,a+n+i))
    if cap:
        a = (len(sections)-1)*n
        faces.append(tuple(range(a,a+n)))
    if smooth and cap:
        geo(part, sum(sections, []), faces, tone)
        _, _, _, flags = PARTS[part]
        flags[-len(faces)+1:-1] = [True] * (len(faces)-2)
    else:
        geo(part, sum(sections, []), faces, tone, smooth)


def turn(part, x, y, levels, tone, n=12):
    rings(part, [[(x+r*math.cos(i*math.tau/n), y+r*math.sin(i*math.tau/n), z)
                  for i in range(n)] for z,r in levels], tone, smooth=True)


def tube(part, path, radii, tone, n=8, cap=True):
    path = [Vector(p) for p in path]
    sections = []
    for k, (p, radius) in enumerate(zip(path, radii)):
        tangent = (path[min(k+1,len(path)-1)] - path[max(k-1,0)]).normalized()
        reference = Vector((1,0,0)) if abs(tangent.x) < .85 else Vector((0,1,0))
        u = tangent.cross(reference).normalized()
        v = tangent.cross(u)
        sections.append([tuple(p+radius*(u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n)))
                         for i in range(n)])
    rings(part, sections, tone, cap, smooth=True)


def disk(part, x, y, z, r, tone, n=20, depth=0, height_ratio=1):
    points = [(x+r*math.cos(i*math.tau/n),
               z+r*height_ratio*math.sin(i*math.tau/n)) for i in range(n)]
    profile(part, points, y, depth, tone)


def stripe(part, a, b, width, tone, z=0):
    x,y = a
    X,Y = b
    length = math.hypot(X-x,Y-y)
    u,v = -(Y-y)*width/(2*length),(X-x)*width/(2*length)
    flat(part, [(x+u,y+v),(x-u,y-v),(X-u,Y-v),(X+u,Y+v)], z, tone)


def face_arrow(part, x, y, z, length, angle, tone='white'):
    points = [(-.105,-.5),(.105,-.5),(.105,.11),(.27,.11),(0,.5),(-.27,.11),(-.105,.11)]
    c,s = math.cos(angle),math.sin(angle)
    profile(part, [(x+length*(u*c-v*s),z+length*(u*s+v*c)) for u,v in points], y, 0, tone)


def button_plate(part, x, y, z):
    plate(part,x,y,z,.115,.18,.013,.055,'yellow')
    disk(part,x,y-.029,z-.019,.027,'chrome',10,.018)
    disk(part,x,y-.039,z-.019,.018,'black',10)
    face_arrow(part,x,y-.029,z+.043,.05,0,'black')


# Seven-segment strokes keep markings editable as flat geometry.
DIGITS = ('abcdef','bc','abdeg','abcdg','bcfg','acdfg','acdefg','abc','abcdefg','abcdfg')
SEGMENTS = {
    'a': ((.18,1),(.82,1)), 'b': ((.91,.9),(.91,.57)), 'c': ((.91,.43),(.91,.10)),
    'd': ((.82,0),(.18,0)), 'e': ((.09,.1),(.09,.43)), 'f': ((.09,.57),(.09,.9)),
    'g': ((.18,.5),(.82,.5)),
}


def face_stroke(part, x1, z1, x2, z2, y, width, tone):
    length = math.hypot(x2-x1,z2-z1)
    dx,dz = -(z2-z1)*width/(2*length),(x2-x1)*width/(2*length)
    profile(part,[(x1+dx,z1+dz),(x1-dx,z1-dz),(x2-dx,z2-dz),(x2+dx,z2+dz)],y,0,tone)


def digits(part, label, x, y, z, w, h, tone):
    for i, ch in enumerate(label):
        ox = x+(i-(len(label)-1)/2)*w*1.24-w/2
        for seg in DIGITS[int(ch)]:
            (a,b),(c,d) = SEGMENTS[seg]
            face_stroke(part,ox+a*w,z+(b-.5)*h,ox+c*w,z+(d-.5)*h,y,h*.093,tone)


def road_light():
    tube('tapered_pole_and_arm',[(0,0,0),(0,0,.18),(0,0,.21),(0,0,8.65),
                  (0,-.037,9.12),(0,-.162,9.49),(0,-.43,9.749),(0,-.78,9.908),
                  (0,-1.20,9.953),(0,-1.53,9.952)],
         [.14,.14,.109,.066,.063,.059,.055,.052,.047,.044],'galv',12)
    plate('access_cover',0,-.104,.56,.092,.29,.013,.015,'steel')
    # The cast head flares out from the spigot and carries its lens underneath.
    outline = [(-.055,-1.31),(.055,-1.31),(.119,-1.49),(.159,-1.78),
               (.145,-2.01),(.088,-2.12),(-.088,-2.12),(-.145,-2.01),
               (-.159,-1.78),(-.119,-1.49)]
    rings('cobra_housing',[
        [(x*.94,y,9.895) for x,y in outline],
        [(x,y,9.943) for x,y in outline],
        [(x*.78,y+.011,10.025 if y> -1.72 else 10.05) for x,y in outline],
        [(x*.60,y+.025,10.036 if y> -1.72 else 10.067) for x,y in outline],
    ],'silver')
    points = [(-.093,-1.60),(.093,-1.60),(.124,-1.78),(.11,-1.98),(.065,-2.055),(-.065,-2.055),(-.11,-1.98),(-.124,-1.78)]
    flat('lamp_lens',points[::-1],9.894,'emitter')
    # The exposed lens is on the underside.
    p = PARTS['lamp_lens'][1]
    p[-1] = p[-1][::-1]


def gantry_sign():
    for x, name in [(-8,'left_support'),(8,'right_support')]:
        box(name,x,0,.13,.85,.95,.26,'concrete')
        box(name,x,0,.286,.64,.68,.052,'steel')
        box(name,x,0,3.48,.41,.48,6.42,'galv')
        box(name,x,0,6.46,.53,.58,.12,'steel')
    for y in (-.31,.31):
        for z in (5.62,6.52):
            box('span_truss',0,y,z,16.35,.13,.15,'galv')
        for i in range(9):
            x = -8+i*2
            box('span_truss',x,y,6.07,.08,.08,.86,'silver')
            if i < 8:
                z1,z2 = (5.65,6.49) if i%2==0 else (6.49,5.65)
                rail('span_truss',(x,y,z1),(x+2,y,z2),.084,.075,'silver')
    for x in (-8,-4,0,4,8):
        for z in (5.64,6.5):
            box('cross_bracing',x,0,z,.09,.63,.078,'steel')
    for x in (-3.75,3.75):
        box('panel_hangers',x,-.405,6.06,.13,.2,1.48,'steel')
    plate('green_direction_panel',0,-.53,6.05,9.7,1.86,.11,.12,'steel')
    plate('green_direction_panel',0,-.595,6.05,9.64,1.8,.098,.008,'white')
    plate('green_direction_panel',0,-.602,6.05,9.51,1.67,.067,.006,'green')
    for z in (5.48,6.62):
        box('panel_stiffeners',0,-.46,z,9.5,.055,.075,'galv')
    for x in (-3.54,-1.18,1.18,3.54):
        face_arrow('lane_arrows',x,-.607,5.51,.49,math.pi)
    face_stroke('lane_arrows',-4.63,5.88,4.63,5.88,-.607,.032,'white')
    face_stroke('lane_arrows',0,5.90,0,6.84,-.607,.032,'white')
    for name,(verts,_,_,_) in PARTS.items():
        if name not in ('left_support','right_support'):
            verts[:] = [(x,y,z+.58) for x,y,z in verts]


def sign_post(part, x, y, height, r=.038):
    turn(part,x,y,[(0,r*1.19),(.095,r*1.19),(.12,r),(height,r)],'galv',8)


def direction_sign():
    for x,n in [(-.9,'post_left'),(.9,'post_right')]:
        sign_post(n,x,0,3.22,.047)
    plate('direction_board',0,-.067,2.67,2.55,1.04,.037,.045,'steel')
    plate('direction_board',0,-.091,2.67,2.52,1.01,.029,0,'white')
    plate('direction_board',0,-.094,2.67,2.46,.95,.019,0,'green')
    box('blue_expressway_inset',-.45,-.097,2.902,1.10,.004,.31,'blue')
    profile('direction_board',[(-1.21,2.638),(1.21,2.638),(1.21,2.651),(-1.21,2.651)],
            -.099,0,'white')
    face_arrow('direction_board',.969,-.101,2.902,.35,-math.pi/4)
    face_arrow('direction_board',.969,-.101,2.411,.34,0)
    label('direction_board','PIE',-.62,-.102,2.91,.172,'white')
    label('direction_board','JURONG',-.49,-.10,2.412,.195,'white')
    for a,b,c,d in [(-.18,2.81,-.09,3.007),(.045,2.81,-.046,3.007),
                    (-.171,2.92,.037,2.92),(-.176,2.925,-.176,2.956),
                    (.042,2.925,.042,2.956)]:
        face_stroke('blue_expressway_inset',a,b,c,d,-.102,.017,'white')


def speed_sign():
    sign_post('post',0,0,2.76)
    disk('round_speed_face',0,-.064,2.47,.32,'steel',18,.035)
    disk('round_speed_face',0,-.083,2.47,.312,'red',18)
    disk('round_speed_face',0,-.085,2.47,.259,'white',18)
    speed_glyphs = [
        [(-.77,.95),(-.1,.95),(-.1,.67),(-.56,.67),(-.59,.43),(-.39,.48),
         (-.21,.42),(-.11,.27),(-.09,-.12),(-.19,-.43),(-.42,-.54),
         (-.69,-.46),(-.83,-.24),(-.67,-.03),(-.55,-.19),(-.38,-.23),
         (-.28,-.12),(-.28,.08),(-.41,.17),(-.62,.12),(-.81,.25)],
    ]
    for points in speed_glyphs:
        profile('round_speed_face',[(x*.185,2.442+z*.19) for x,z in points],-.087,0,'black')
    outer = [(.025,.55),(.12,.85),(.35,.97),(.56,.85),(.66,.55),(.66,-.12),(.56,-.43),(.35,-.54),(.12,-.43),(.025,-.12)]
    inner = [(.22,.55),(.25,.67),(.35,.71),(.45,.67),(.48,.55),(.48,-.12),(.45,-.24),(.35,-.28),(.25,-.24),(.22,-.12)]
    for i in range(len(outer)):
        j = (i+1)%len(outer)
        profile('round_speed_face',[(x*.185,2.442+z*.19) for x,z in [outer[i],outer[j],inner[j],inner[i]]],-.087,0,'black')


def keep_left():
    sign_post('post',0,0,1.65,.032)
    disk('keep_left_face',0,-.054,1.39,.255,'steel',15,.03)
    disk('keep_left_face',0,-.071,1.39,.249,'white',15)
    disk('keep_left_face',0,-.073,1.39,.238,'blue',15)
    face_arrow('keep_left_face',0,-.075,1.39,.37,math.pi*.75)

GLYPHS = {
    'A': [((0,0),(.25,1),(.5,0)),((.12,.42),(.38,.42))],
    'B': [((0,0),(0,1),(.33,1),(.49,.85),(.49,.65),(.35,.51),(0,.51)),
          ((.35,.51),(.51,.37),(.51,.14),(.35,0),(0,0))],
    'E': [((.48,1),(0,1),(0,0),(.48,0)),((0,.52),(.41,.52))],
    'G': [((.5,.84),(.36,1),(.13,1),(0,.84),(0,.16),(.13,0),(.37,0),(.5,.15),(.5,.46),(.30,.46))],
    ' ': [],
    'K': [((0,0),(0,1)),((.48,1),(0,.48),(.48,0))],
    'L': [((0,1),(0,0),(.48,0))],
    'I': [((.25,0),(.25,1))],
    'J': [((.47,1),(.47,.15),(.34,0),(.14,0),(0,.15))],
    'N': [((0,0),(0,1),(.5,0),(.5,1))],
    'O': [((.12,0),(0,.15),(0,.85),(.12,1),(.39,1),(.51,.85),(.51,.15),(.39,0),(.12,0))],
    'P': [((0,0),(0,1),(.36,1),(.5,.85),(.5,.65),(.36,.5),(0,.5))],
    'R': [((0,0),(0,1),(.36,1),(.5,.85),(.5,.65),(.36,.5),(0,.5)),((.27,.5),(.53,0))],
    'S': [((.49,.88),(.37,1),(.12,1),(0,.87),(0,.65),(.12,.53),(.37,.47),(.49,.35),(.49,.13),(.37,0),(.12,0),(0,.12))],
    'T': [((0,1),(.52,1)),((.26,1),(.26,0))],
    'U': [((0,1),(0,.15),(.13,0),(.37,0),(.5,.15),(.5,1))],
    'V': [((0,1),(.25,0),(.5,1))],
    'W': [((0,1),(.1,0),(.28,.73),(.45,0),(.55,1))],
    '1': [((.25,0),(.25,1),(.10,.81))],
}


def label(part, word, x, y, z, height, tone):
    for i, ch in enumerate(word):
        origin = x+(i-(len(word)-1)/2)*height*.72-height*.25
        for path in GLYPHS.get(ch, []):
            for (a,b),(c,d) in zip(path,path[1:]):
                face_stroke(part,origin+a*height,z+(b-.5)*height,
                            origin+c*height,z+(d-.5)*height,y,height*.09,tone)


def signal_hood(part, x, y, z, r, projection):
    # A three-quarter visor is open along the underside for drainage.
    angles = [math.radians(-27+i*234/7) for i in range(8)]
    verts = []
    for y0, scale in [(y,1),(y-projection,.96)]:
        for a in angles:
            length = (0.48+.52*max(0,math.sin(a))) if y0 != y else 0
            verts.append((x+r*scale*math.cos(a),y-projection*length,z+r*scale*math.sin(a)))
    faces = [(i,i+1,i+9,i+8) for i in range(7)]
    # Closed, thin hood wall gives the inner and outer surfaces consistent normals.
    inner = [(x+(X-x)*.9,Y,z+(Z-z)*.9) for X,Y,Z in verts]
    faces += [tuple(j+16 for j in reversed(f)) for f in faces[:]]
    faces += [(i+8,i+9,i+25,i+24) for i in range(7)]
    faces += [(i+1,i,i+16,i+17) for i in range(7)]
    faces += [(0,8,24,16),(15,7,23,31)]
    geo(part,verts+inner,faces,'charcoal')


def pedestrian_icon(part, x, y, z, walking, tone):
    disk(part,x+.004,y,z+.047,.014,tone,8)
    if walking:
        for a,b,c,d,w in [(-.006,.029,-.012,-.015,.019),(-.006,.020,-.04,-.003,.009),
                          (.002,.021,.036,.002,.009),(-.013,-.012,-.038,-.051,.011),
                          (-.012,-.012,.028,-.051,.011)]:
            face_stroke(part,x+a,z+b,x+c,z+d,y,w,tone)
    else:
        for a,b,c,d,w in [(0,.026,0,-.013,.024),(-.013,.02,-.022,-.013,.009),
                          (.013,.02,.022,-.013,.009),(-.009,-.01,-.012,-.047,.009),
                          (.009,-.01,.012,-.047,.009)]:
            face_stroke(part,x+a,z+b,x+c,z+d,y,w,tone)


def ped_signal():
    turn('signal_post',0,0,[(0,.083),(.1,.083),(.13,.062),(3.02,.052)],'galv',10)
    box('signal_bracket',0,-.1,2.57,.095,.18,.18,'steel')
    plate('pedestrian_head',0,-.195,2.65,.217,.423,.027,.155,'charcoal')
    for z, walking in [(2.75,False),(2.55,True)]:
        disk('pedestrian_head',0,-.278,z,.078,'window',12)
        signal_hood('pedestrian_head',0,-.273,z,.085,.11)
        pedestrian_icon('pedestrian_head',0,-.28,z,walking,'signal_green' if walking else 'red_lens')
    box('countdown_mount',.15,-.056,2.64,.36,.075,.065,'steel')
    plate('countdown_box',.246,-.192,2.65,.238,.243,.025,.14,'charcoal')
    plate('countdown_box',.246,-.265,2.65,.185,.146,.013,.006,'window')
    digits('countdown_box','12',.246,-.27,2.65,.05,.095,'countdown_red')
    button_plate('push_button',0,-.081,1.08)


def mast_signal():
    turn('mast_post',0,0,[(0,.34),(.12,.34),(.154,.23),(1,.19),(6.16,.12)],'galv',10)
    box('service_cover',0,-.185,.67,.16,.044,.38,'steel')
    # Use coherent cross sections around the bends in the tapered mast arm.
    points = [(0,0,5.39),(.31,0,5.79),(.91,0,6.0),(1.8,0,6.025),(4.8,0,5.985),(8.38,0,5.91)]
    sections = []
    for i, ((x,y,z),r) in enumerate(zip(points,[.155,.142,.127,.113,.085,.058])):
        before,after = points[max(0,i-1)],points[min(len(points)-1,i+1)]
        theta = math.atan2(after[2]-before[2],after[0]-before[0])
        sections.append([(x-r*math.sin(theta)*math.sin(j*math.tau/8),
                          y+r*math.cos(j*math.tau/8),
                          z+r*math.cos(theta)*math.sin(j*math.tau/8)) for j in range(8)])
    rings('cantilever_arm',sections,'galv',smooth=True)
    for i,x in enumerate((2.13,5.17,7.95),1):
        p = f'vehicle_head_{i}'
        box(p,x,0,5.78,.10,.09,.46,'steel')
        plate(p,x,-.128,5.42,.32,.88,.058,.19,'charcoal')
        plate(p,x,-.226,5.42,.285,.837,.044,0,'black')
        for z, tone in [(5.695,'signal_red'),(5.42,'amber_lens'),(5.145,'green_lens')]:
            disk(p,x,-.229,z,.112,tone,12)
            # A short integrated hood uses a single sheet with a double-sided material.
            angles = [math.radians(-25+j*230/7) for j in range(8)]
            verts = [(x+.121*math.cos(a),-.225,z+.121*math.sin(a)) for a in angles]
            verts += [(x+.117*math.cos(a),-.225-(.085+.16*max(0,math.sin(a))),
                       z+.117*math.sin(a)) for a in angles]
            geo(p,verts,[(j,j+1,j+9,j+8) for j in range(7)],'charcoal')


def canopy(part, left, right, y0, y1, spring, rise, steps, thickness, tone):
    shape = []
    for i in range(steps+1):
        t = i/steps
        shape.append((y0+(y1-y0)*t,spring+rise*(1-(2*t-1)**2)))
    perimeter = [(y,z-thickness) for y,z in shape] + shape[::-1]
    rings(part,[[(x,y,z) for y,z in perimeter] for x in (left,right)],tone)


def canopy_frame(part, x, y0, y1, spring, rise, steps, width, tone):
    sections = []
    for i in range(steps+1):
        t = i/steps
        y = y0+(y1-y0)*t
        z = spring+rise*(1-(2*t-1)**2)
        sections.append([(x-width/2,y,z+.009),(x+width/2,y,z+.009),
                         (x+width/2,y,z-.058),(x-width/2,y,z-.058)])
    rings(part,sections,tone)


def bus_shelter_sbs():
    canopy('curved_canopy',-3.45,3.45,-1.21,1.15,2.52,.32,12,.065,'roof')
    canopy_frame('roof_end_caps',-3.42,-1.21,1.15,2.52,.32,6,.06,'roof_edge')
    canopy_frame('roof_end_caps',3.42,-1.21,1.15,2.52,.32,6,.06,'roof_edge')
    for y in (-1.18,1.12):
        box('fascias',0,y,2.486,6.9,.095,.16,'steel')
    for x in (-2.83,0,2.83):
        turn('rear_columns',x,.87,[(0,.107),(.08,.107),(.12,.068),(2.63,.068)],'galv',8)
        canopy_frame('cantilever_ribs',x,-1.17,1.11,2.463,.32,5,.092,'silver')
        rail('cantilever_brackets',(x,.87,2.05),(x,.23,2.66),.068,.058,'silver')
    for x in (-1.42,1.42):
        box('windbreak_glazing',x,.908,1.34,2.67,.019,1.56,'glass')
        for z in (.545,2.13):
            box('windbreak_frames',x,.908,z,2.82,.062,.056,'silver')
        for z in (1.025,1.064):
            face_stroke('visibility_bands',x-1.33,z,x+1.33,z,.897,.017,'white')
    for x in (-1.83,-.22):
        box('bench_legs',x,.37,.23,.09,.44,.46,'steel')
    for j in range(5):
        box('bench_slats',-1.03,.157+j*.092,.474,2.23,.078,.053,'seat')
    for x in (-2.15,.09):
        box('bench_slats',x,.34,.46,.032,.468,.055,'steel')
    for x in (-1.88,-.21):
        rail('bench_back', (x,.58,.46),(x,.635,.89),.055,.058,'silver')
    for z in (.75,.85):
        box('bench_back',-1.03,.645,z,2.22,.044,.077,'seat')
    plate('route_information',1.83,.847,1.62,1.36,.87,.024,.085,'charcoal')
    plate('route_information',1.83,.799,1.62,1.28,.79,.012,.008,'white')
    box('route_information',1.83,.793,1.91,1.28,.007,.18,'green')
    label('route_information','BUS STOP',1.77,.788,1.91,.067,'white')
    for row, service in enumerate(('99','185','198')):
        z = 1.735-row*.18
        profile('route_information',[(1.255,z-.0635),(1.525,z-.0635),
                                     (1.525,z+.0635),(1.255,z+.0635)],.787,0,'red')
        digits('route_information',service,1.39,.785,z,.043,.068,'white')
        face_stroke('route_information',1.60,z+.036,2.425,z+.036,.792,.02,'grey')
        face_stroke('route_information',1.60,z-.01,2.255,z-.01,.792,.014,'silver')
        face_stroke('route_information',1.60,z-.049,2.363,z-.049,.792,.013,'silver')
    label('route_information','SBS',1.19,.792,1.286,.061,'violet')
    face_stroke('route_information',1.115,1.244,1.268,1.244,.792,.008,'orange')
    plate('stop_address_plate',0,-1.233,2.483,1.48,.151,.019,.012,'rainforest')
    label('stop_address_plate','JURONG WEST AVE 1',-.143,-1.241,2.484,.066,'white')
    label('stop_address_plate','B',.444,-1.241,2.484,.073,'white')
    digits('stop_address_plate','07',.532,-1.241,2.484,.041,.073,'white')
    box('canopy_luminaire',-.71,.08,2.698,1.1,.075,.052,'emitter')
    box('canopy_luminaire',.71,.08,2.698,1.1,.075,.052,'emitter')


def bus_stop_flag():
    turn('bus_stop_post',0,0,[(0,.064),(3.08,.064)],'galv',8)
    part = 'bus_stop_flag'
    plate(part,0,-.084,2.90,.586,.44,.057,.031,'rainforest')
    profile(part,[(-.257,3.008),(.257,3.008),(.257,3.066),(.224,3.094),
                  (-.224,3.094),(-.257,3.066)],-.102,0,'white')
    plate(part,-.075,-.104,3.047,.123,.07,.013,0,'blue')
    box(part,-.075,-.105,3.057,.084,.004,.029,'white')
    for x in (-.112,-.038):
        profile(part,[(x-.01,3.005),(x+.01,3.005),(x+.01,3.022),(x-.01,3.022)],-.106,0,'blue')
    profile(part,[(-.281,2.873),(.281,2.873),(.281,2.998),(-.281,2.998)],-.102,0,'lush')
    digits(part,'28401',0,-.105,2.935,.065,.068,'white')
    label(part,'BLK',-.104,-.104,2.797,.062,'white')
    digits(part,'502',.089,-.104,2.797,.040,.062,'white')
    box('services_panel',0,-.088,2.51,.553,.033,.295,'galv')
    for i,(num,tone) in enumerate([('99','green'),('185','green'),('198','green')]):
        x = (i-1)*.177
        profile('services_panel',[(x-.082,2.405),(x+.082,2.405),(x+.082,2.619),
                                 (x-.082,2.619)],-.106,0,tone)
        digits('services_panel',num,x,-.109,2.512,.038,.067,'white')


def kerb_drain():
    # Standard chamfered upstand, with the throat set back from the road face.
    cross = [(-.145,0),(.145,0),(.145,.165),(-.103,.165),(-.128,.14),(-.145,.109)]
    for left,right in [(-2,-.39),(.39,2)]:
        rings('chamfered_kerb',[[(x,y,z) for y,z in cross] for x in (left,right)],'concrete')
    cap = [(-.145,.111),(.145,.111),(.145,.165),(-.103,.165),(-.128,.14)]
    rings('inlet_lintel',[[(x,y,z) for y,z in cap] for x in (-.39,.39)],'concrete')
    box('inlet_channel',0,0,.014,.78,.29,.028,'dark_concrete')
    box('inlet_recess',0,.068,.076,.78,.14,.08,'iron')
    for x in (-.34,.34):
        box('inlet_frame',x,-.106,.07,.048,.071,.1,'iron')
    for z in (.042,.103):
        box('inlet_frame',0,-.103,z,.724,.068,.021,'iron')
    for x in (-.25,-.15,-.05,.05,.15,.25):
        box('inlet_bars',x,-.109,.073,.024,.053,.059,'iron')
    for x in (-1.2,1.2):
        profile('kerb_joints',[(x-.004,.003),(x+.004,.003),(x+.004,.104),(x-.004,.104)],-.146,0,'dark_concrete')
        flat('kerb_joints',[(x-.004,-.103),(x+.004,-.103),(x+.004,.145),(x-.004,.145)],.1655,'dark_concrete')


def drain_grate():
    # Rectangular cast-iron frame with open transverse slots.
    outer = [(-.30,-.203),(.30,-.203),(.325,-.179),(.325,.179),(.30,.203),
             (-.30,.203),(-.325,.179),(-.325,-.179)]
    inner = [(-.276,-.154),(.276,-.154),(.281,-.135),(.281,.135),(.276,.154),
             (-.276,.154),(-.281,.135),(-.281,-.135)]
    verts = [(x,y,z) for points,z in [(outer,0),(outer,.036),(inner,.036),(inner,.004)]
             for x,y in points]
    faces = []
    for i in range(8):
        j = (i+1)%8
        faces += [(i,j,j+8,i+8),(i+8,j+8,j+16,i+16),(i+16,j+16,j+24,i+24)]
    geo('cast_frame',verts,faces,'iron')
    for x in (-.224,-.134,-.045,.045,.134,.224):
        width = .044
        verts = [(x-width/2,-.156,.006),(x-width/2,-.156,.032),
                 (x+width/2,-.156,.032),(x+width/2,-.156,.006)]
        verts += [(X,.156,Z) for X,_,Z in verts]
        geo('slot_crossbars',verts,[(0,1,5,4),(1,2,6,5),(2,3,7,6)],'steel')


def manhole():
    n = 16
    contour = [(math.cos(i*math.tau/n),math.sin(i*math.tau/n)) for i in range(n)]
    sections = [[(x*r,y*r,z) for x,y in contour] for r,z in [(.35,0),(.333,.036)]]
    rings('cast_cover',sections,'iron',cap=False)
    flat('cast_cover',[(x,y) for x,y,_ in sections[-1]],.036,'iron')
    for x,y in [(-.131,-.141),(.018,-.141),(.128,-.054),(-.069,0),
                (.064,.088),(-.124,.143),(.024,.143)]:
        stripe('cast_treads',(x-.052,y-.023),(x+.052,y+.023),.032,'steel',.037)


def guard_rail_3m():
    for x in (-1.425,0,1.425):
        box('anchor_plates',x,0,.009,.15,.15,.018,'steel')
        box('posts',x,0,.603,.054,.054,1.194,'leaf_green')
    for bay in (-.7125,.7125):
        for z in (.175,1.145):
            box('horizontal_rails',bay,0,z,1.38,.038,.054,'leaf_green')
        for i in range(11):
            x = bay+(i-5)*.117
            rings('vertical_pickets',
                  [[(x+dx,dy,z) for dx,dy in [(-.009,-.009),(.009,-.009),(.009,.009),(-.009,.009)]]
                   for z in (.177,1.144)],'leaf_green',cap=False)
    profile('identification_plate',[(.036,1.131),(.089,1.131),(.089,1.159),(.036,1.159)],
            -.020,0,'chrome')


def bollard():
    turn('steel_post',0,0,[(0,.083),(.77,.083),(.785,.079)],'steel',10)
    turn('reflective_collar',0,0,[(.676,.084),(.744,.084)],'yellow',10)


def bins():
    x = -.33
    turn('blue_recycling_body',x,0,[(0,.207),(.05,.247),(.79,.258),(.845,.236)],'recycling',10)
    n = 12
    cap = [[(x+r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for i in range(n)]
           for z,r in [(.845,.252),(.927,.265),(.975,.241),(1.005,.155)]]
    rings('blue_recycling_lid',cap,'recycling',smooth=True)
    _,faces,tones,smooth = PARTS['blue_recycling_lid']
    # Open two forward-facing facets and bridge their boundary into a dark recessed chute.
    for i in (10,9):
        del faces[i],tones[i],smooth[i]
    opening = cap[0][8:11]+cap[1][8:11][::-1]
    inner = [(X,-.148,Z) for X,_,Z in opening]
    rings('recycling_intake',[opening,inner],'recycling',cap=False)
    # The six-point boundary has collinear points in the chute plane.
    profile('recycling_intake',[(inner[0][0],.845),(inner[2][0],.845),
                                (inner[3][0],.927),(inner[5][0],.927)],
            -.149,0,'rubber')
    plate('recycling_label',x,-.254,.603,.194,.172,.017,.006,'white')
    pts = [(0,.075),(-.066,-.035),(.066,-.035)]
    for i,(a,b) in enumerate(zip(pts,pts[1:]+pts[:1])):
        dx,dz = b[0]-a[0],b[1]-a[1]
        face_arrow('recycling_label',x+(a[0]+b[0])*.43,-.259,.60+(a[1]+b[1])*.43,
                   .071,math.atan2(-dx,dz),'green')
    x = .35
    turn('litter_bin_shell',x,0,[(0,.18),(.048,.22),(.70,.242),(.78,.248)],'grey',10)
    # A hood is lifted above the liner, leaving two actual open sides.
    turn('litter_bin_hood',x,0,[(.925,.249),(.989,.239),(1.017,.192)],'charcoal',10)
    for y in (-.058,.058):
        for dx in (-.19,.19):
            box('litter_bin_hood',x+dx,y,.845,.064,.071,.17,'grey')
    turn('litter_bin_liner',x,0,[(.755,.215),(.791,.222)],'rubber',8)
    plate('litter_access_door',x,-.223,.395,.212,.474,.028,.014,'charcoal')
    disk('litter_access_door',x+.066,-.232,.546,.013,'chrome',8)


def hydrant():
    # Conventional red pillar with a bonnet and two opposed, capped outlets.
    turn('pillar',0,0,[(0,.146),(.068,.146),(.095,.093),(.59,.086)],'red',8)
    turn('bonnet',0,0,[(.57,.11),(.633,.114),(.704,.085)],'red',7)
    turn('operating_nut',0,0,[(.698,.033),(.739,.033)],'iron',5)
    for side in (-1,1):
        a,b = side*.066,side*.151
        p = 'outlet_left' if side < 0 else 'outlet_right'
        tube(p,[(a,0,.472),(b,0,.472),(side*.163,0,.472)],[.057,.061,.052],'red',6)
    disk('inspection_badge',0,-.091,.333,.034,'plate',8)
    disk('inspection_badge',0,-.092,.333,.024,'red',8)


def covered_walkway():
    canopy('curved_roof',-3,3,-1.23,1.23,2.585,.37,14,.062,'roof')
    for x in (-2.962,0,2.962):
        canopy_frame('curved_ribs',x,-1.23,1.23,2.537,.37,10,.076,'roof_edge')
    for y in (-1.208,1.208):
        box('edge_gutters',0,y,2.537,6,.112,.135,'steel')
    for y in (-.72,.72):
        box('longitudinal_purlins',0,y,2.765,6,.087,.096,'galv')
    for x in (-2.68,2.68):
        for y in (-.99,.99):
            n = 'front_columns' if y < 0 else 'rear_columns'
            box(n,x,y,.03,.216,.201,.06,'steel')
            box(n,x,y,1.297,.115,.115,2.48,'galv')
            rail('knee_braces',(x,y,2.23),(x,y*.58,2.766),.065,.065,'silver')
        rail('downpipes',(x,1.084,.12),(x,1.084,2.54),.052,.055,'roof_edge')
    for x in (-1.48,1.48):
        box('ceiling_lights',x,.09,2.832,1.27,.093,.047,'emitter')


def kiosk_substation():
    # Compact roadside electricity service cabinet on a shallow concrete plinth.
    box('plinth',0,0,.066,.75,.442,.132,'concrete')
    plate('powder_coated_cabinet',0,.006,.603,.65,.94,.029,.362,'olive')
    plate('rain_hood',0,-.007,1.079,.702,.096,.014,.417,'beige')
    plate('service_door',0,-.184,.594,.597,.836,.017,.031,'beige')
    for z in (.33,.86):
        box('hinges',-.277,-.209,z,.054,.026,.079,'galv')
    plate('lock',.211,-.207,.581,.045,.093,.006,.016,'charcoal')
    disk('lock',.211,-.217,.594,.012,'chrome',8)
    for i in range(7):
        z = .295+i*.024
        box('vent_louvres',0,-.203,z,.373,.014,.012,'olive')
    box('hazard_label',.01,-.202,.763,.16,.006,.14,'plate')
    profile('hazard_label',[(-.05,.722),(.072,.722),(.011,.815)],-.207,0,'yellow')
    profile('hazard_label',[(.013,.799),(-.012,.758),(.008,.758),(.001,.729),
                            (.035,.77),(.015,.77)],-.209,0,'black')
    plate('cabinet_id',0,-.202,.895,.136,.047,.005,.007,'grey')
    digits('cabinet_id','03',0,-.207,.895,.026,.032,'white')


def tactile_strip():
    # Seven 300 mm directional tiles alternate with 300 mm flush paving gaps.
    box('paving_bed',0,0,.0175,4,.30,.035,'concrete')
    for i in range(7):
        x = (i-3)*.60
        flat('tile_faces',[(x-.15,-.15),(x+.15,-.15),(x+.15,.15),(x-.15,.15)],
             .0352,'tile')
        for y in (-.1125,-.0375,.0375,.1125):
            v = [(x-.112,y-.0125,.0402),(x+.112,y-.0125,.0402),
                 (x+.112,y+.0125,.0402),(x-.112,y+.0125,.0402),
                 (x-.126,y,.0352)]
            geo('directional_ribs',v,[(0,1,2,3),(4,0,3)],'tile_ridge')


def clip_marking(points, normal, edge):
    clipped = []
    for a,b in zip(points,points[1:]+points[:1]):
        d0,d1 = a.dot(normal)-edge,b.dot(normal)-edge
        if d0 >= 0:
            clipped.append(a)
        if (d0 < 0) != (d1 < 0):
            clipped.append(a.lerp(b,d0/(d0-d1)))
    return clipped


def bus_word(part, center_x, center_y):
    # A 2.4 by 2.7 m block stencil follows the lane direction, including the open letter counters.
    glyphs = [
        [(0,0,.15,2.7),(.15,0,.59,.3),(.15,1.2,.59,1.5),(.15,2.4,.59,2.7),
         (.59,.3,.70,1.2),(.59,1.5,.70,2.4)],
        [(0,.3,.15,2.7),(.15,0,.55,.3),(.55,.3,.70,2.7),(0,0,.15,.3),(.55,0,.70,.3)],
        [(0,0,.70,.3),(.55,.3,.70,1.2),(0,1.2,.70,1.5),
         (0,1.5,.15,2.4),(0,2.4,.70,2.7)],
    ]
    for i, strokes in enumerate(glyphs):
        x = center_x+1.2-i*.85
        y = center_y+1.35
        for x0,y0,x1,y1 in strokes:
            flat(part,[(x-x0,y-y0),(x-x1,y-y0),(x-x1,y-y1),(x-x0,y-y1)],0,'yellow')


def road_markings():
    # Travel direction is Blender -Y, or glTF +Z when placed on the road.
    for i in range(12):
        x = -9.1+i*.56
        flat('zebra',[(x-.14,-6.2),(x+.14,-6.2),(x+.14,-2.7),(x-.14,-2.7)],0,'white')
    # The border and X are connected coplanar polygons, with no overlapping paint.
    x0,x1,y0,y1 = -.95,7.05,-5.7,.3
    w = .45
    outer = [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    inner = [(x0+w,y0+w),(x1-w,y0+w),(x1-w,y1-w),(x0+w,y1-w)]
    for i in range(4):
        j = (i+1)%4
        flat('yellow_box',[outer[i],outer[j],inner[j],inner[i]],0,'yellow')
    # Trim both diagonals into the inside rim and divide the crossing at the first stripe.
    lo,hi = Vector(inner[0]),Vector(inner[2])
    n = Vector((-(hi.y-lo.y),hi.x-lo.x)).normalized()
    half_width = .10
    midpoint = (lo+hi)/2
    for start,end,second in [(lo,hi,False),(Vector(inner[1]),Vector(inner[3]),True)]:
        delta = (end-start).normalized()
        side = Vector((-delta.y,delta.x))*half_width
        polygon = [start-delta+side,start-delta-side,end+delta-side,end+delta+side]
        for normal, edge in [(Vector((1,0)),lo.x),(Vector((-1,0)),-hi.x),
                             (Vector((0,1)),lo.y),(Vector((0,-1)),-hi.y)]:
            polygon = clip_marking(polygon,normal,edge)
        pieces = [polygon]
        if second:
            pieces = [clip_marking(polygon,n,n.dot(midpoint)+half_width),
                      clip_marking(polygon,-n,-n.dot(midpoint)+half_width)]
        for piece in pieces:
            flat('yellow_box',piece,0,'yellow')
    stripe('bus_lane',(-9.25,.72),(-9.25,9.05),.30,'yellow')
    stripe('bus_lane',(-9.10,1.35),(-7.90,1.35),.20,'yellow')
    bus_word('bus_lane',-7.44,4.23)
    stripe('stop_line',(-7.32,1.15),(-3.83,1.15),.30,'white')
    tail,tip = 7.52,3.54
    outline = [(-.105,tail),(.105,tail),(.105,tip+.96),(.38,tip+.96),(0,tip),(-.38,tip+.96),(-.105,tip+.96)]
    flat('arrow_straight',[(x-4.13,y) for x,y in outline],0,'white')
    turn = [(-.102,tail),(.102,tail),(.102,5.3),(.145,4.95),(.43,4.68),(.71,4.63),
            (.84,4.63),(.84,4.91),(1.61,4.52),(.84,4.10),(.84,4.37),
            (.43,4.37),(.032,4.64),(-.102,4.97)]
    flat('arrow_left',[(x+3.1,y) for x,y in turn],0,'white')
    flat('arrow_right',[(x*-1+.05,y) for x,y in turn],0,'white')


BUDGETS = {
    'road_light':700, 'gantry_sign':900, 'direction_sign':300, 'speed_sign':200,
    'keep_left':150, 'ped_signal':450, 'mast_signal':900, 'bus_shelter_sbs':1400,
    'bus_stop_flag':300, 'kerb_drain':350, 'drain_grate':100, 'manhole':60,
    'guard_rail_3m':300, 'bollard':100, 'bins':500, 'hydrant':200,
    'covered_walkway':900, 'kiosk_substation':500, 'tactile_strip':120, 'road_markings':800,
}

MATERIALS = {
    'paint': (0,.55), 'metal': (.68,.39), 'chrome': (.86,.26),
    'roof': (.39,.4), 'glass': (0,.16), 'window': (.14,.31),
    'concrete': (0,.85), 'trim': (.12,.63), 'wall': (.13,.58),
    'rubber': (0,.87), 'plate': (.14,.48), 'stone': (0,.77),
    'light': (0,.34), 'lamp_emissive': (0,.29),
}


def make_material(name, model):
    material = bpy.data.materials.get(name)
    if material:
        return material
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value, shader.inputs['Roughness'].default_value = MATERIALS[name]
    if name == 'metal' and model in ('drain_grate','manhole','kerb_drain'):
        shader.inputs['Metallic'].default_value = .4
        shader.inputs['Roughness'].default_value = .76
    colors = material.node_tree.nodes.new('ShaderNodeVertexColor')
    colors.layer_name = 'Finish'
    material.node_tree.links.new(colors.outputs['Color'],shader.inputs['Base Color'])
    if name == 'glass':
        shader.inputs['Alpha'].default_value = .22
        material.surface_render_method = 'BLENDED'
    if name == 'lamp_emissive':
        shader.inputs['Emission Color'].default_value = (
            (1,.045,.023,1) if model == 'ped_signal' else (.94,.82,.58,1))
        shader.inputs['Emission Strength'].default_value = 1.0
    return material


def bounds(vertices):
    return [Vector(f(v[i] for v in vertices) for i in range(3)) for f in (min,max)]


def make_objects(model):
    PARTS.clear()
    globals()[model]()
    offset = Vector((0,0,0))
    # Layout samples are centered as a group with individually centered marking pivots.
    if model == 'road_markings':
        low,high = bounds([v for verts,_,_,_ in PARTS.values() for v in verts])
        offset = (low+high)/2
        offset.z = 0
    objects = []
    for name,(verts,faces,tones,smooth) in PARTS.items():
        low,high = bounds(verts)
        pivot = (low+high)/2
        pivot.z = low.z
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([Vector(v)-pivot for v in verts],[],faces)
        mesh.update()
        obj = bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = pivot-offset
        color = mesh.color_attributes.new(name='Finish',type='BYTE_COLOR',domain='CORNER')
        categories = list(dict.fromkeys(PALETTE[t][0] for t in tones))
        for category in categories:
            mesh.materials.append(make_material(category,model))
        for polygon,tone,soft in zip(mesh.polygons,tones,smooth):
            mat,hex_color = PALETTE[tone]
            polygon.material_index = categories.index(mat)
            polygon.use_smooth = soft
            rgba = [int(hex_color[i:i+2],16)/255 for i in (0,2,4)] + [1]
            for corner in polygon.loop_indices:
                color.data[corner].color_srgb = rgba
        objects.append(obj)
    bpy.context.view_layer.update()
    return objects


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for group in (bpy.data.meshes,bpy.data.materials,bpy.data.cameras,bpy.data.lights):
        for data in list(group):
            if data.users == 0:
                group.remove(data)


def export(model):
    bpy.ops.export_scene.gltf(filepath=str(ROOT/f'{model}.glb'),export_format='GLB',
                             export_yup=True,export_animations=False,export_skins=False,
                             export_cameras=False,export_lights=False,export_texcoords=False,
                             export_vertex_color='ACTIVE',export_apply=True,
                             export_unused_images=False)


def orthographic_views(model, span, height):
    low_profile = height < span*.24 and model not in ('covered_walkway','gantry_sign')
    tilt = 1.35 if model == 'road_markings' else (.36 if low_profile else .08)
    oblique = (.76,-1,.67 if not low_profile else 1.05)
    if model == 'road_light':
        oblique = (.74,-1,-.20)
    return [(0,-1,tilt),(1,0,tilt),(0,1,tilt),(-1,0,tilt),(0,-.0001,1),oblique]


def studio(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x,scene.render.resolution_y = 1188,596
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    world = scene.world or bpy.data.worlds.new('Studio')
    scene.world = world
    world.use_nodes = True
    nodes,links = world.node_tree.nodes,world.node_tree.links
    nodes.clear()
    ambient = nodes.new('ShaderNodeBackground')
    ambient.inputs[0].default_value = (.49,.54,.59,1)
    ambient.inputs[1].default_value = .47
    backdrop = nodes.new('ShaderNodeBackground')
    backdrop.inputs[0].default_value = (.042,.054,.070,1)
    mix = nodes.new('ShaderNodeMixShader')
    light_path = nodes.new('ShaderNodeLightPath')
    output = nodes.new('ShaderNodeOutputWorld')
    links.new(light_path.outputs['Is Camera Ray'],mix.inputs[0])
    links.new(ambient.outputs[0],mix.inputs[1])
    links.new(backdrop.outputs[0],mix.inputs[2])
    links.new(mix.outputs[0],output.inputs[0])
    for name,d,p,c in [('Key',(-.55,.9,1),1.68,(1,.94,.86)),
                       ('Fill',(.82,.13,1),.62,(.8,.91,1)),
                       ('Rim',(.15,.68,-1),1.08,(.93,.97,1))]:
        data = bpy.data.lights.new(name,'SUN')
        data.energy,data.color,data.angle = p,c,.24
        obj = bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(obj)
        obj.rotation_euler = (-Vector(d)).to_track_quat('-Z','Y').to_euler()
    data = bpy.data.cameras.new('Six-view orthographic')
    camera = bpy.data.objects.new(data.name,data)
    bpy.context.collection.objects.link(camera)
    data.type = 'ORTHO'
    data.ortho_scale = 3.0
    camera.location = (0,0,10)
    scene.camera = camera
    return scene


def photograph(model):
    from mathutils import Matrix

    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'{model}.glb'))
    originals = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    vertices = [obj.matrix_world @ v.co for obj in originals for v in obj.data.vertices]
    low,high = bounds(vertices)
    center = (low+high)/2
    extent = high-low
    views = orthographic_views(model,max(extent),extent.z)
    # Each linked instance applies the transform of its orthographic view.
    # A single studio render captures all six tiles with identical lighting.
    for i,view in enumerate(views):
        rotation = (-Vector(view)).to_track_quat('-Z','Y').to_matrix().transposed()
        rotated = [rotation@(v-center) for v in vertices]
        lo,hi = bounds(rotated)
        width,height = (hi-lo).xy
        scale = .82/max(width,height*396/298)
        tile = Vector((i%3-1,(.5-i//3)*298/396,0))
        framing = (lo+hi)/2
        transform = (Matrix.Translation(tile-scale*framing)
                     @ Matrix.Scale(scale,4)
                     @ rotation.to_4x4()
                     @ Matrix.Translation(-center))
        for obj in originals:
            copy = bpy.data.objects.new(obj.name,obj.data)
            bpy.context.collection.objects.link(copy)
            copy.matrix_world = transform @ obj.matrix_world
    for obj in originals:
        bpy.data.objects.remove(obj,do_unlink=True)
    scene = studio(bpy.context.scene)
    directory = ROOT/'reviews'
    directory.mkdir(exist_ok=True)
    scene.render.filepath = str(directory/f'{model}.png')
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage',choices=('export','review','all'),default='all')
    parser.add_argument('models',nargs='*',metavar='MODEL')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if unknown := sorted(set(args.models)-BUDGETS.keys()):
        parser.error('unknown model(s): '+', '.join(unknown))
    assert bpy.app.version == (5,1,2), bpy.app.version_string
    render_scene = bpy.context.scene
    render_scene.unit_settings.system = 'METRIC'
    render_scene.unit_settings.scale_length = 1.0
    for model in args.models or BUDGETS:
        print(f'STREETKIT {args.stage} {model}',flush=True)
        clear_scene()
        if args.stage in ('export','all'):
            objects = make_objects(model)
            count = 0
            for obj in objects:
                obj.data.calc_loop_triangles()
                count += len(obj.data.loop_triangles)
            print(f'STREETKIT TRIANGLES {model} {count}/{BUDGETS[model]}',flush=True)
            if count > BUDGETS[model]:
                raise ValueError(f'{model} needs {count} triangles, budget {BUDGETS[model]}')
            export(model)
            clear_scene()
        if args.stage in ('review','all'):
            photograph(model)


if __name__ == '__main__':
    main()
