"""Build and proof-render the Marina Bay game assets with Blender 5.1.2."""
from pathlib import Path
from math import cos, sin, pi, tau, radians, copysign
import hashlib
import json
import random
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
UP = Vector((0, 0, 1))
MATERIALS = {}


def pbr(name, color, roughness=.5, metallic=0, alpha=1, emission=0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, alpha)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    for key, value in {
        "Base Color": (*color, 1), "Metallic": metallic, "Roughness": roughness,
        "Alpha": alpha, "Emission Color": (*color, 1), "Emission Strength": emission,
    }.items():
        shader.inputs[key].default_value = value
    if alpha < 1:
        # The glTF exporter derives alphaMode from the Principled alpha input.
        material.surface_render_method = 'BLENDED'
    MATERIALS[name] = material


class Part:
    """Collect disconnected geometry into one independently addressable mesh."""
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.styles = []

    def patch(self, vertices, faces, material, smooth=False):
        base = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(base + i for i in face) for face in faces)
        self.styles.extend([(material, smooth)] * len(faces))

    def loft(self, rings, material, cap=True, smooth=True):
        count = len(rings[0])
        faces = []
        for index in range(len(rings) - 1):
            base = index * count
            for j in range(count):
                k = (j + 1) % count
                faces.append((base+j, base+k, base+count+k, base+count+j))
        if cap:
            faces += [tuple(reversed(range(count))), tuple(range(len(rings)*count-count, len(rings)*count))]
        self.patch([v for ring in rings for v in ring], faces, material, smooth)

    def tube(self, points, radius, material, sides=6, cap=True):
        points = [Vector(point) for point in points]
        rings = []
        axis = None
        for i, point in enumerate(points):
            tangent = (points[min(i+1,len(points)-1)] - points[max(i-1,0)]).normalized()
            if axis is None:
                axis = tangent.cross(UP if abs(tangent.z) < .88 else Vector((0, 1, 0))).normalized()
            else:
                axis = (axis - tangent * axis.dot(tangent)).normalized()
            other = tangent.cross(axis)
            width = radius[i] if isinstance(radius, (list, tuple)) else radius
            rings.append([point + width*(axis*cos(tau*j/sides) + other*sin(tau*j/sides))
                          for j in range(sides)])
        self.loft(rings, material, cap)

    def finish(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        names = list(dict.fromkeys(name for name, _ in self.styles))
        for name in names:
            mesh.materials.append(MATERIALS[name])
        for poly, (name, smooth) in zip(mesh.polygons, self.styles):
            poly.material_index = names.index(name)
            poly.use_smooth = smooth
        data = bmesh.new()
        data.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(data, faces=list(data.faces))
        data.to_mesh(mesh)
        data.free()
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        return obj


def polar(radius, angle, z, center=(0, 0), aspect=1):
    return (center[0] + radius*cos(angle), center[1] + radius*aspect*sin(angle), z)


def circle(radius, z, sides=32, center=(0, 0), aspect=1):
    return [polar(radius, tau*i/sides, z, center, aspect) for i in range(sides)]


def annulus(part, profile, material, sides=64, center=(0, 0), aspect=1):
    part.loft([circle(radius, height, sides, center, aspect) for radius,height in profile],
              material, cap=False)


def slab(part, points, top, bottom, material):
    part.loft([[(x,y,bottom) for x,y in points], [(x,y,top) for x,y in points]], material, smooth=False)


def museum():
    pbr("roof", (.79,.79,.74), .31)
    pbr("paint", (.91,.89,.81), .39)
    pbr("concrete", (.53,.49,.42), .75)
    pbr("stone", (.31,.32,.29), .77)
    pbr("water", (.045,.14,.115), .15, .38)
    pbr("leaf", (.09,.22,.053), .66)
    pbr("light", (.49,.28,.35), .67)
    pbr("glass", (.15,.29,.32), .17, .24, .66)
    pbr("window", (.072,.151,.170), .26, .27)
    pbr("metal", (.38,.43,.43), .37, .68)
    pbr("wall", (.26,.24,.21), .67)

    basin = Part("Reflecting pond | water lily court")
    annulus(basin, [(52,0),(52,.52),(51.4,.68),(49.9,.68),(49.2,.44),
                    (48.65,.29)], "stone", aspect=.88)
    slab(basin, [(x,y) for x,y,_ in circle(49.1,.3,64,aspect=.88)], .33,.19,"water")
    basin.finish()

    rng = random.Random(812)
    lily = Part("Reflecting pond | lily pads and blossoms")
    for group in range(11):
        a = tau*group/11
        if 3.97 < a < 5.18:
            continue
        x,y,_ = polar(33+5*sin(2*a), a, 0, aspect=.88)
        for i in range(20):
            cx,cy = x+rng.gauss(0,2.4), y+rng.gauss(0,2.1)
            size,theta = rng.uniform(.21,.52),rng.random()*tau
            points = [(cx,cy,.35)] + [polar(size,theta+.2+5.8*j/6,.36,(cx,cy),.77) for j in range(7)]
            lily.patch(points, [(0,j,j+1) for j in range(1,7)], "leaf")
            if i%5 == 0:
                lily.patch([*circle(.16,.38,5,(cx,cy)),(cx,cy,.51)],
                           [(j,(j+1)%5,5) for j in range(5)], "light")
    lily.finish()

    core = Part("Central atrium | oculus and rainwater dish")
    annulus(core, [(5.25,3),(5.25,19.0),(5.9,19.5),(9.0,18.5),(15.5,20.1),
                    (18.8,23.2),(19.2,22),(17.1,17.3),(11.0,11.4),(7.0,4.0)],
            "roof", 44)
    annulus(core, [(5.20,18.6),(5.22,19.03),(5.89,19.54),(6.02,19.46)], "metal", 44)
    annulus(core, [(5.16,3.6),(5.17,4.1),(5.20,18.61)], "wall", 40)
    slab(core, [(x,y) for x,y,_ in circle(5.17,0,40)], 2.8,2.5,"water")
    core.finish()
    structure = Part("Atrium | ten raking supports and diagrid")
    for j in range(10):
        a=tau*j/10
        structure.tube([polar(8.1,a,.22),polar(12.8,a,16.8)], (.63,.50), "metal", 7)
        for offset in (-.32,.32):
            structure.tube([polar(6.2,a+offset,2.3),polar(12.1,a,15.6)],.21,"metal",5)
    structure.finish()

    entry = Part("South entrance | faceted glazed pavilion")
    corners = [(-18,-16,5.1),(-13,-21,7.8),(-4,-24,9.15),
               (5,-24.4,8.4),(14,-21.6,6.5),(18,-17,5.5)]
    foot = [Vector((1.025*x, y-1.25,.71)) for x,y,_ in corners]
    eave = [Vector((x,y,z)) for x,y,z in corners]
    for k in range(len(foot)-1):
        for j in range(4):
            a,b = j/4,(j+1)/4
            left, right = foot[k].lerp(foot[k+1],a),foot[k].lerp(foot[k+1],b)
            upper_l,upper_r = eave[k].lerp(eave[k+1],a),eave[k].lerp(eave[k+1],b)
            if k == 2 and j in (1,2):
                sill_l = left.lerp(upper_l,.38)
                sill_r = right.lerp(upper_r,.38)
                entry.patch([left,right,sill_r,sill_l],[(0,1,2,3)],"window")
                entry.patch([sill_l,sill_r,upper_r,upper_l],[(0,1,2,3)],"glass")
            else:
                entry.patch([left,right,upper_r,upper_l],[(0,1,2,3)],"glass")
            entry.tube([left,upper_l],.061,"metal",4,cap=False)
    entry.tube([foot[-1],eave[-1]],.061,"metal",4,cap=False)
    for t in (0,.25,.50,.75,1):
        entry.tube([a.lerp(b,t) for a,b in zip(foot,eave)],.071,"metal",4)
    ridge = [(-13,-10,5.5),(-4,-10,8.15),(6,-10,7.4),(13,-10,5.6)]
    entry.patch([*eave,*ridge],[(0,1,6),(1,2,7,6),(2,3,8,7),
                                (3,4,9,8),(4,5,9)],"window",False)
    entry.patch([foot[0],eave[0],ridge[0],(-13,-10,.71),foot[-1],eave[-1],
                 ridge[-1],(13,-10,.71)],[(0,1,2,3),(4,5,6,7)],"glass")
    slab(entry, [(-5.8,-43),(7.8,-43),(4.8,-24.7),(-4,-24.7)],.72,.30,"concrete")
    slab(entry,[(-5.5,-40),(7.3,-40),(4.4,-24.9),(-3.6,-24.9)],.74,.70,"stone")
    entry.finish()

    # Finger tips rise toward the north-west. The short south fingers project outward
    # and allow a view into the open central roof from the south promenade.
    fingers = [
        (8,46,38,8.3, .10), (44,54,38,8.7,-.13), (78,58,34.5,8.1,.12),
        (112,60,35.3,8.75,.16), (149,49,38.5,8.2,-.09), (187,36,40,8.65,.15),
        (222,25,42,8.5,-.10), (258,21,38.0,7.4,.12), (291,26,41.9,8.3,-.08),
        (327,34,42.2,8.65,.04),
    ]
    for number,(angle,height,length,width,sweep) in enumerate(fingers,1):
        a = radians(angle)
        part = Part(f"Finger {number:02d} | FRP gallery shell and skylight")
        # Ellipsoid-like longitudinal sweep with a clipped, subtly curved end wall.
        # The tall galleries narrow to a thin upturn and the low ones have broader ends.
        upright = (height-21)/39
        end_width = .77-.23*upright
        end_depth = .40-.17*upright
        stations = [
            (0,0,.50,1.12),(.12,.016,.63,1.37),(.28,.072,.80,1.46),
            (.48,.17,.97,1.36),(.65,.30,1.0,1.19),(.79,.45,.98,.96),
            (.89,.62,.87-.06*upright,.73),(.95,.78,.81-.14*upright,.57),
            (.986,.925,end_width+.035,end_depth*1.18),
            (1,1,end_width,end_depth),
        ]
        rings = []
        for r,z,w,d in stations:
            angle_now = a + sweep*(r*r-.2*r)
            tilt = (height-15.0)/(length-7.4) * (.10+2.4*r*r)
            center = Vector(polar(7.4+(length-7.4)*r,angle_now,15.0+(height-15.0)*z))
            side = Vector((-sin(angle_now),cos(angle_now),0))
            normal = Vector((-cos(angle_now)*tilt,-sin(angle_now)*tilt,1)).normalized()
            ring = []
            for j in range(16):
                theta = tau*j/16
                cross = copysign(abs(cos(theta))**.73,cos(theta))
                depth = copysign(abs(sin(theta))**.77,sin(theta))
                ring.append(center + side*width*w*cross + normal*(4.7*d*depth))
            rings.append(ring)
        lip = rings[-1]
        end_a = a + sweep*.8
        end_tilt = (height-15.0)/(length-7.4)*2.50
        along = Vector((cos(end_a),sin(end_a),end_tilt)).normalized()
        pane_center = sum(lip,Vector())/len(lip)+along*.065
        pane_axis = (lip[0]-lip[8]).normalized()
        pane_up = (lip[4]-lip[12]).normalized()
        half_w = (lip[0]-lip[8]).length*.425
        half_h = (lip[4]-lip[12]).length*.36
        def pane_point(u,v):
            return pane_center + pane_axis*half_w*u + pane_up*half_h*v
        across = [-1,-.66,-.33,0,.33,.66,1]
        glazing = [pane_point(u,v) for v in (-1,1) for u in across]
        dividers = [[pane_point(u,v)+along*.025 for v in (-1,1)] for u in across]
        high = max(v.z for ring in rings for v in ring)
        for v in [*(v for ring in rings for v in ring),*glazing,*(v for bar in dividers for v in bar)]:
            v.z = 15.0+(v.z-15.0)*(height-15.0)/(high-15.0)
        # Keep the glass slightly forward of the clipped FRP face.
        part.loft(rings,"roof",cap=False)
        cap_center = sum(lip,Vector())/16
        part.patch([*lip,cap_center],[(j,(j+1)%16,16) for j in range(16)],"paint")
        part.patch(glazing,[(j,j+1,j+8,j+7) for j in range(6)],"window")
        for bar in dividers[1:-1]:
            part.tube(bar,.045,"metal",3,cap=False)
        part.finish()


def ribbon(part, frame, distances, widths, top, thickness, material):
    part.loft([[frame(s, side * width/2, level) for side,level in
                [(-1,top),(1,top),(1,top-thickness),(-1,top-thickness)]]
               for s,width in zip(distances,widths)],material,smooth=False)


def helix_bridge():
    pbr("concrete", (.37,.35,.31), .75)
    pbr("stone", (.30,.295,.27), .78)
    pbr("wall", (.205,.225,.22), .65)
    pbr("metal", (.41,.465,.48), .32, .72)
    pbr("chrome", (.62,.67,.68), .26, .79)
    pbr("glass", (.37,.55,.59), .28, .24, .54)
    pbr("trim", (.15,.235,.25), .40, .55)
    pbr("light", (.67,.72,.71), .30, .48)

    length, radius = 280, 330
    def frame(s, offset=0, z=0):
        angle = (s-length/2)/radius
        rise = min(s, length-s, 24)/24
        return ((radius-offset)*sin(angle),
                (radius-offset)*(1-cos(angle))+offset,
                3.25+4.5*sin(pi*rise/2)+z)

    # Divide the assembly by its end and main spans so each segment is loadable on its own.
    edges = [0,42.5,107.5,172.5,237.5,280]
    for k,(a,b) in enumerate(zip(edges,edges[1:]),1):
        stations = [a+(b-a)*j/7 for j in range(8)]
        deck = Part(f"Deck span {k:02d} | {'access ramp' if k in (1,5) else 'pedestrian slab'}")
        ribbon(deck,frame,stations,[6]*8,0,.53,"stone")
        for side in (-1,1):
            deck.tube([frame(s,side*2.99,-.27) for s in stations], .095,"metal",4)
        deck.tube([frame(s,0,-.66) for s in stations],.29,"trim",4)
        deck.finish()

    weave_start,weave_stop = 10,270
    def spiral(s,hand,phase):
        t = hand*tau*(s-weave_start)/60 + phase
        diameter = 10.8 if hand==1 else 9.4
        return frame(s,diameter/2*cos(t), 1.90+diameter/2*sin(t))
    for hand,count,label in [(1,6,"Outer"),(-1,5,"Inner")]:
        weave = Part(f"{label} helix | {count} stainless steel tubes")
        stations = [weave_start+(weave_stop-weave_start)*j/66 for j in range(67)]
        for i in range(count):
            weave.tube([spiral(s,hand,tau*i/count+.19*(hand<0)) for s in stations],
                       .1365, "chrome" if hand==1 else "metal",4 if hand==1 else 3)
        weave.finish()

    joints = Part("Helix truss | cross rings and radial ties")
    for j in range(10):
        s = 21+j*26
        hoop = [frame(s,4.77*cos(tau*i/8),1.90+4.77*sin(tau*i/8)) for i in range(9)]
        # Duplicate end rings leave coincident end caps, so only the curved tube wall is used.
        joints.tube(hoop,.093,"metal",4,cap=False)
        for side in (-1,1):
            joints.tube([frame(s,side*2.55,-.43),frame(s+1.4,side*4.35,.42)],.10,"metal",5)
    joints.finish()

    for index,s in enumerate(edges,1):
        cx,cy,_ = frame(s)
        pier = Part(f"Pier {index:02d} | concrete pile cap and steel tripod")
        pier.loft([circle(1.49,0,12,(cx,cy)),circle(1.38,.75,12,(cx,cy))], "concrete")
        for along,side in [(-1.58,0),(.65,-2.35),(.65,2.35)]:
            pier.tube([(cx,cy,.56),frame(max(0,min(length,s+along)),side,-.69)],
                      (.44,.32),"metal",7)
        pier.finish()

    approaches = Part("Approaches | promenade abutments")
    for a,b in [(0,3),(277,280)]:
        approach = [(a,-3.03),(a,3.03),(b,3.03),(b,-3.03)]
        approaches.loft([[(*frame(s,side)[:2],0) for s,side in approach],
                         [frame(s,side,-.515) for s,side in approach]],"concrete",smooth=False)
    approaches.finish()

    pod_stations = (45,108,173,237)
    rails = Part("Deck edges | railings and stainless posts")
    for side in (-1,1):
        ranges = [(0,length)] if side < 0 else list(zip(
            [0,*[s+5 for s in pod_stations]],[*[s-5 for s in pod_stations],length]))
        for a,b in ranges:
            count=max(2,round((b-a)/7.5))
            path=[a+(b-a)*i/count for i in range(count+1)]
            rails.tube([frame(s,side*2.89,1.14) for s in path],.075,"chrome",4)
            rails.patch([frame(s,side*2.89,z) for z in (.21,1.06) for s in path],
                        [(i,i+1,i+count+2,i+count+1) for i in range(count)],"glass")
            for s in path[::2]:
                rails.tube([frame(s,side*2.88,.08),frame(s,side*2.88,1.12)],
                           .048,"metal",4,cap=False)
    rails.finish()

    for k,s in enumerate(pod_stations,1):
        pod = Part(f"Viewing pod {k:02d} | cantilever balcony and shade")
        outline = [(s+5.0*cos(pi*j/14),2.90+5.2*sin(pi*j/14)) for j in range(15)]
        pod.loft([[frame(x,y,z) for x,y in outline] for z in (-.48,0)],
                 "stone",smooth=False)
        pod.tube([frame(x,y,1.15) for x,y in outline],.077,"chrome",5)
        pod.patch([frame(x,y,z) for z in (.18,1.08) for x,y in outline],
                  [(i,i+1,i+16,i+15) for i in range(14)],"glass")
        for x,y in outline[::4]:
            pod.tube([frame(x,y,.04),frame(x,y,1.16)],.065,"metal",4,cap=False)
        for x in (-2.5,2.5):
            pod.tube([frame(s+x,1.48,-1.35),frame(s+x,6.9,-.54)],.16,"metal",5)
        glass = []
        for j in range(9):
            u = -1+j/4
            for v in (0,.5,1):
                glass.append(frame(s+4.5*u,2.55+(2.4-.83*u*u)*v,
                                   3.36+.49*sin(pi*v)-.34*u*u))
        pod.patch(glass,[(3*i+j,3*i+j+3,3*i+j+4,3*i+j+1)
                         for i in range(8) for j in range(2)],"glass",True)
        for j in (0,4,8):
            pod.tube([frame(s+4.5*(-1+j/4),2.26,1.2),glass[j*3],
                      glass[j*3+1],glass[j*3+2]],.082,"metal",4,cap=False)
        pod.tube(glass[2::3],.085,"metal",5)
        pod.finish()

    shades = Part("Walkway canopy | alternating fritted glass and mesh")
    for index,s in enumerate(range(22,267,20)):
        points = [frame(s+long, across, 5.75-.088*across**2)
                  for long in (-3,0,3) for across in (-3.48,-1.74,0,1.74,3.48)]
        shades.patch(points,[(i+j,i+j+5,i+j+6,i+j+1)
                            for i in (0,5) for j in range(4)],
                     "glass" if index%3 else "metal",True)
        for i in (0,10):
            shades.tube(points[i:i+5],.063,"metal",3,cap=False)
        for side in (-1,1):
            shades.tube([frame(s,side*3.48,4.67),frame(s,side*4.52,4.7)],
                        .061,"metal",3,cap=False)
    shades.finish()
    for obj in bpy.context.scene.objects:
        for vertex in obj.data.vertices:
            vertex.co.x *= -1
            vertex.co.y *= -1


def supertree(height, radius, phase, observatory=False):
    pbr("concrete", (.25,.265,.23), .76)
    pbr("trunk", (.146,.20,.105), .94)
    pbr("metal", (.23,.052,.092), .48, .42)
    pbr("paint", (.38,.082,.153), .42, .24)
    pbr("trim", (.22,.40,.037), .53, .26)
    pbr("leaf", (.14,.28,.059), .84)
    pbr("wall", (.052,.13,.051), .92)
    pbr("light", (.50,.34,.27), .39, .35)
    pbr("glass", (.063,.14,.15), .24, .51)
    pbr("stone", (.38,.36,.32), .74)

    trunk_width = 1.85 + height*.042
    deck_level = height-1.5 if observatory else height
    rim_level = deck_level-1.0 if observatory else height-.14

    core = Part("Trunk | concrete shaft and base collar")
    core.loft([circle(r,z,14) for r,z in [(trunk_width*.76,0),
               (trunk_width*.79,.38),(trunk_width*.64,height*.08),
               (trunk_width*.49,height*.61),(trunk_width*.55,rim_level-1)]],"concrete")
    annulus(core, [(trunk_width*.85,.03),(trunk_width*.85,.22),(trunk_width*.74,.31)],
            "stone",18)
    core.finish()

    greens = Part("Vertical gardens | living wall and tropical foliage")
    rng = random.Random(643+height)
    count = 20 if observatory else 28
    levels = [(.015,.87),(.083,.98),(.16,1.045),(.26,1.01),(.37,.95),
              (.47,.92),(.57,.88),(.65,.78),(.72,.57)]
    def living_radius(t):
        for (a,r1),(b,r2) in zip(levels,levels[1:]):
            if t <= b:
                return trunk_width*(r1+(r2-r1)*(t-a)/(b-a))
        return trunk_width*levels[-1][1]
    rings = []
    shift = rng.uniform(0,.13)
    for index,(level,width) in enumerate(levels):
        variation = .01*height if index else .13
        rings.append([polar(trunk_width*width*rng.uniform(.92,1.06),
                            tau*i/count+shift+rng.uniform(-.031,.031),
                            height*level+rng.uniform(-variation,variation)) for i in range(count)])
    for k in range(len(rings)-1):
        for j in range(count):
            n = (j+1)%count
            cell = [rings[k][j],rings[k][n],rings[k+1][n],rings[k+1][j]]
            if (k+j)%2:
                cell = cell[1:]+cell[:1]
            greens.patch(cell[:3],[(0,1,2)],rng.choices(("trunk","wall","leaf"),(6,3,1))[0])
            greens.patch([cell[0],cell[2],cell[3]],[(0,1,2)],rng.choices(("trunk","wall","leaf"),(6,3,1))[0])
    for i in range(218 if observatory else 326):
        a=rng.random()*tau
        t=rng.uniform(.034,.704)
        size = rng.uniform(.32,.73)*(1.13 if observatory else 1)
        center = Vector(polar(living_radius(t)*rng.uniform(.97,1.04),a,t*height))
        out = Vector((cos(a),sin(a),0))
        across = Vector((-sin(a),cos(a),0))
        lean = rng.uniform(-.65,.65)
        greens.patch([center-across*size*.74-UP*size*.26,center+across*size*.73-UP*size*.54,
                      center+across*lean*size+UP*size*.71+out*size*.35,
                      center+out*size*.48],
                     [(0,1,3),(1,2,3)],"leaf" if rng.random()>.20 else "trunk")
    greens.finish()

    ribs = Part("Canopy dish | flared steel ribs and branch forks")
    forks = Part("Canopy dish | perimeter hoops and cross ties")
    n = 12 if height >= 35 else 10
    for i in range(n):
        a = tau*i/n+phase
        profile = [(trunk_width*.87,.45),(trunk_width*.96,height*.12),
                   (trunk_width*.95,height*.37),(trunk_width*.88,height*.56),
                   (trunk_width*1.03,height*.68),(radius*.37,height*.777),
                   (radius*.56,height*.85),(radius*.79,height*.938),
                   (radius*.94,rim_level-1.35),(radius,rim_level)]
        def rib_angle(k):
            return a + .055*sin(k*.57+i*.82)+.045*(k/9)
        points = [polar(r,rib_angle(k),z) for k,(r,z) in enumerate(profile)]
        ribs.tube(points, [.085,.125,.15,.16,.18,.163,.139,.115,.089,.066],
                  "metal",4)
        for side in (-1,1):
            ribs.tube([points[5],polar(radius*.60,a+side*.075,height*.854),
                       polar(radius*.79,a+side*.157,height*.94),
                       polar(radius*.995,a+side*.19,rim_level-.12-(i%3)*.2)],
                      (.108,.094,.072,.049),"paint",3,cap=False)
            if (i+side)%2:
                ribs.tube([points[6],polar(radius*.75,a+side*.17,height*.896),
                           polar(radius*.9,a+side*.25,rim_level-1.22)],
                          (.082,.062,.045),"metal",3,cap=False)
        forks.tube([points[6],polar(radius*.69,a+pi/n,height*.881),
                    polar(radius*.80,a+tau/n,height*.919)],
                   (.072,.064,.056),"paint",3,cap=False)
        forks.tube([points[4],polar(trunk_width*1.18,a+pi/n,height*.715),
                    polar(radius*.37,a+tau/n,height*.777)],
                   .072,"metal",3,cap=False)
    for fraction,z,thickness in [(1,rim_level-.05,.087),(.94,rim_level-1.36,.059),
                                 (.54,height*.846,.072)]:
        path = [polar(radius*fraction*(1+.014*sin(7*a+phase)),a,
                      z+.13*sin(5*a+phase)) for a in [tau*j/24 for j in range(24)]]
        forks.tube(path+[path[0]],thickness,"metal",3,cap=False)
    ribs.finish()
    forks.finish()
    hub=Part("Canopy hub | service ring" if not observatory else "Supertree Observatory | glazed lounge and roof deck")
    hr = trunk_width*(1.22 if not observatory else 1.65)
    ht = rim_level-1.1 if not observatory else height-1.1
    skirt_top = height-4.75 if observatory else ht
    lower_hub = skirt_top-height*(.18 if observatory else .17)
    annulus(hub, [(trunk_width*.50,lower_hub),(trunk_width*.58,lower_hub+height*.055),
                  (hr*.78,skirt_top-height*.053),(hr,skirt_top-.39),
                  (hr,skirt_top),(hr*.84,skirt_top+.07)],"concrete",18)
    for i in range(6):
        a = tau*i/6+phase
        hub.tube([polar(trunk_width*.53,a,lower_hub),
                  polar(hr*.74,a,skirt_top-height*.064),
                  polar(hr*1.002,a,skirt_top-.08)],
                  .075,"trim",3,cap=False)
    if observatory:
        hub.loft([circle(hr*.86,z,24) for z in (height-4.8,height-1.2)],"glass",cap=False)
        for i in range(16):
            a=tau*i/16
            hub.tube([polar(hr*.87,a,height-4.78),polar(hr*.87,a,height-1.16)],
                      .053,"metal",4,cap=False)
        rail = circle(hr*.92,height-.055,24)
        hub.tube(rail+[rail[0]],.055,"paint",4,cap=False)
        for i in range(0,24,2):
            x,y,z=rail[i]
            hub.tube([(x,y,ht),(x,y,z)],.051,"metal",4,cap=False)
        slab(hub,[(x,y) for x,y,_ in circle(hr*.97,0,24)],ht+.16,ht-.24,"stone")
    else:
        # The crown remains open around the compact central service top.
        slab(hub,[(x,y) for x,y,_ in circle(hr*.84,0,24)],ht+.16,ht,"stone")
    hub.finish()
    vertices = [v for obj in bpy.context.scene.objects for v in obj.data.vertices]
    scale_z = height/max(v.co.z for v in vertices)
    for v in vertices:
        v.co.z *= scale_z


def skyway():
    pbr("metal", (.155,.17,.16), .59, .50)
    pbr("trim", (.145,.18,.13), .48, .46)
    pbr("paint", (.72,.404,.047), .46, .45)
    pbr("chrome", (.42,.46,.42), .40, .65)
    radius = 23.5
    def frame(s, offset=0,z=0):
        a=s/radius
        return ((radius-offset)*sin(a),
                (radius-offset)*(1-cos(a))+offset, .27+.19*(s/10)**2+z)
    stations = [-10+2.5*i for i in range(9)]
    deck=Part("Skyway | curved modular steel deck")
    ribbon(deck,frame,stations,[1.65]*len(stations),0,.18,"metal")
    for side in (-1,1):
        deck.tube([frame(s,side*.74,-.19) for s in stations],.08,"trim",4)
    for s in stations[1::2]:
        deck.tube([frame(s,-.87,-.14),frame(s,.87,-.14)], .06,"metal",4)
    deck.finish()
    rails=Part("Skyway | amber handrails and safety mesh")
    for side in (-1,1):
        for h,thickness in [(1.17,.046),(.17,.022)]:
            rails.tube([frame(s,side*.85,h) for s in stations],thickness,"paint",4)
        for s in stations:
            rails.tube([frame(s,side*.79,-.10),frame(s,side*.85,1.17)],
                       .028,"paint",4,cap=False)
        for heights in ([.43]*len(stations),[.80]*len(stations),
                        [.29+.60*(i%2) for i in range(len(stations))]):
            edges = [frame(s,side*.84,h+z)
                     for z in (-.009,.009) for s,h in zip(stations,heights)]
            n = len(stations)
            rails.patch(edges,[(i,i+1,n+i+1,n+i) for i in range(n-1)],"chrome")
    rails.finish()


def center_base():
    vertices = [v for obj in bpy.context.scene.objects if obj.type == 'MESH'
                for v in obj.data.vertices]
    if not vertices:
        raise ValueError("No model geometry")
    low = [min(v.co[i] for v in vertices) for i in range(3)]
    high = [max(v.co[i] for v in vertices) for i in range(3)]
    origin = Vector(((low[0]+high[0])/2,(low[1]+high[1])/2,low[2]))
    for v in vertices:
        v.co -= origin


MODELS = {
    "artscience_museum": museum,
    "helix_bridge": helix_bridge,
    "supertree_tall": lambda: supertree(50,19.1,.14,True),
    "supertree_mid": lambda: supertree(35,15.2,.06),
    "supertree_short": lambda: supertree(25,11.4,.23),
    "skyway_segment": skyway,
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATERIALS.clear()
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1


def area(name, position, target, energy, size, color):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.shape, light.size, light.color = energy, 'DISK', size, color
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (target-obj.location).to_track_quat('-Z','Y').to_euler()


def render_sheet(filename):
    reset()
    bpy.ops.import_scene.gltf(filepath=str(filename))
    scene = bpy.context.scene
    corners = [obj.matrix_world @ Vector(point) for obj in scene.objects
               if obj.type == 'MESH' for point in obj.bound_box]
    low = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    target = (high+low)/2
    span = max(high-low)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.max_bounces = 5
    scene.cycles.samples = 12
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .10
    scene.cycles.use_denoising = True
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    scene.render.resolution_x, scene.render.resolution_y = 528, 352
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    world = bpy.data.worlds.new("Cool daylight")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.61,.72,.89,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .48
    pbr("Studio ground", (.135,.17,.20), .91)
    ground = Part("Studio ground")
    size = span*90
    clearance = .012 if filename.stem == "helix_bridge" else span*.003
    ground.patch([(-size,-size,-clearance),(size,-size,-clearance),
                  (size,size,-clearance),(-size,size,-clearance)],[(0,1,2,3)],"Studio ground")
    ground.finish()
    area("Sun softbox",target+Vector((-.70,-.95,1.30))*span,target,span**2*23,span*.85,(1,.91,.79))
    area("Sky bounce",target+Vector((.9,-.05,.72))*span,target,span**2*5,span*1.2,(.68,.81,1))
    area("Rim",target+Vector((.12,.8,1.0))*span,target,span**2*10,span*.70,(1,.96,.88))
    data = bpy.data.cameras.new("Orthographic review camera")
    camera = bpy.data.objects.new("Orthographic review camera",data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    data.type, data.clip_end = 'ORTHO', span*25
    viewpoints = {
        "front":(0,-1,0), "right":(1,0,0), "rear":(0,1,0),
        "front_three_quarter":(1,-1.55,.77),
        "rear_three_quarter":(-1,1.4,1.01), "top":(0,0,1),
    }
    if filename.stem == "helix_bridge":
        viewpoints["front_three_quarter"] = (-1.95,-1,.83)
        viewpoints["deck_detail"] = (.95,-1.35,.42)
        del viewpoints["rear_three_quarter"]
        viewpoints["top"] = viewpoints.pop("top")
    proof = ROOT/".work"
    proof.mkdir(exist_ok=True)
    aspect = scene.render.resolution_x/scene.render.resolution_y
    panels = []
    for name, direction in viewpoints.items():
        look = Vector(direction).normalized()
        camera.location = target + look*span*3.6
        camera.rotation_euler = (Vector((0,0,-1)).to_track_quat('-Z','Y').to_euler()
                                 if name=="top" else (-look).to_track_quat('-Z','Y').to_euler())
        transform = camera.rotation_euler.to_matrix().transposed()
        projected = [transform @ (point-target) for point in corners]
        extents = [max(v[i] for v in projected)-min(v[i] for v in projected) for i in (0,1)]
        center = Vector(tuple((max(v[i] for v in projected)+min(v[i] for v in projected))/2 for i in (0,1))+(0,))
        camera.location += camera.rotation_euler.to_matrix() @ center
        data.ortho_scale = max(extents[0],extents[1]*aspect)*1.19
        if name == "deck_detail":
            pod = next(obj for obj in scene.objects if obj.name.startswith("Viewing pod 03"))
            focus = sum((pod.matrix_world @ Vector(point) for point in pod.bound_box),Vector())/8
            camera.location = focus + look*span*3.6
            data.ortho_scale = 32
        path = proof/f"{filename.stem}_{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(path),check_existing=False)
        output = np.empty(len(img.pixels), np.float32)
        img.pixels.foreach_get(output)
        panels.append(output.reshape((img.size[1],img.size[0],4)))
        bpy.data.images.remove(img)
        path.unlink()

    h,w = panels[0].shape[:2]
    gap = 5
    sheet = np.full((2*h+gap,3*w+2*gap,4),.043,np.float32)
    sheet[:,:,3]=1
    for i,panel in enumerate(panels):
        x = i%3*(w+gap)
        y = (1-i//3)*(h+gap)
        sheet[y:y+h,x:x+w,:]=panel
    image = bpy.data.images.new("Six-view contact sheet",sheet.shape[1],sheet.shape[0],alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    folder = ROOT/"renders"
    folder.mkdir(exist_ok=True)
    image.filepath_raw = str(folder/f"{filename.stem}_six_views.png")
    image.file_format = 'PNG'
    image.save()
    return {
        "file": f"renders/{filename.stem}_six_views.png",
        "glb_sha256": hashlib.sha256(filename.read_bytes()).hexdigest(),
        "sha256": hashlib.sha256(Path(image.filepath_raw).read_bytes()).hexdigest(),
        "renderer": "Blender 5.1.2 Cycles CPU, 2 threads, 12 samples, denoised",
        "views": list(viewpoints),
    }


def main():
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    render_only = "--render-only" in args
    export_only = "--export-only" in args
    ids = [arg for arg in args if not arg.startswith("--")] or MODELS.keys()
    folder = ROOT/"renders"
    evidence_path = folder/"evidence.json"
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    if bpy.app.version != (5,1,2):
        raise RuntimeError(f"Expected Blender 5.1.2, found {bpy.app.version_string}")
    for name in ids:
        path = ROOT/f"{name}.glb"
        if not render_only:
            reset()
            MODELS[name]()
            center_base()
            bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', export_yup=True,
                                      export_animations=False, export_skins=False,
                                      export_cameras=False, export_lights=False,
                                      export_texcoords=False, export_materials='EXPORT')
        if not export_only:
            evidence[path.name] = render_sheet(path)
            evidence_path.write_text(json.dumps(evidence,indent=2)+"\n")


if __name__ == "__main__":
    main()
