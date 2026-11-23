"""Build the two Gardens by the Bay conservatories with Blender 5.1.2."""
from dataclasses import dataclass
from hashlib import sha256
from math import cos, pi, sin
from pathlib import Path
import json
import random
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
TAU = 2 * pi
UP = Vector((0, 0, 1))


@dataclass(frozen=True)
class Dome:
    file: str
    length: float
    depth: float
    height: float
    bays: int
    rows: int
    arches: int
    shoulder: float
    skew: float
    cloud: bool = False


DOMES = (
    Dome("flower_dome", 130, 100, 38, 34, 20, 11, .65, .11),
    Dome("cloud_forest", 100, 80, 58, 36, 22, 10, .58, -.10, True),
)

MATERIALS = {
    # RGB values are linear glTF/Blender factors.
    "paint": ((.78, .82, .80), .31, .06, 1),
    "glass": ((.27, .52, .56), .21, .28, .34),
    "window": ((.23, .43, .52), .23, .24, .29),
    "wall": ((.28, .29, .25), .76, 0, 1),
    "roof": ((.48, .53, .51), .41, .10, 1),
    "concrete": ((.44, .43, .37), .85, 0, 1),
    "metal": ((.19, .30, .30), .43, .42, 1),
    "trim": ((.35, .48, .46), .36, .20, 1),
    "stone": ((.34, .32, .27), .90, 0, 1),
    "water": ((.24, .48, .48), .24, .14, 1),
    "leaf": ((.29, .45, .17), .86, 0, 1),
    "trunk": ((.23, .15, .09), .89, 0, 1),
}


VERTEX_TINTS = {"glass", "leaf", "water"}


def pbr(name, color, roughness, metallic=0, alpha=1):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    if name in VERTEX_TINTS:
        vertex_color = mat.node_tree.nodes.new('ShaderNodeVertexColor')
        vertex_color.layer_name = "Tint"
        mat.node_tree.links.new(vertex_color.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Alpha"].default_value = alpha
    mat.diffuse_color = (*color, alpha)
    mat.use_backface_culling = alpha < 1
    if alpha < 1:
        mat.surface_render_method = 'BLENDED'
    return mat


class Part:
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.styles = []

    def face(self, indices, material, smooth=False, tint=None):
        self.faces.append(tuple(indices))
        self.styles.append((material, smooth, tint))

    def patch(self, points, faces, material, smooth=False, tint=None):
        offset = len(self.vertices)
        self.vertices.extend(points)
        for face in faces:
            self.face((offset + i for i in face), material, smooth, tint)

    def skin(self, rings, materials, closed=True, caps=False, smooth=False):
        count = len(rings[0])
        offset = len(self.vertices)
        self.vertices.extend(point for ring in rings for point in ring)
        for row in range(len(rings) - 1):
            for col in range(count if closed else count - 1):
                a = offset + row * count + col
                b = offset + row * count + (col + 1) % count
                self.face((a, b, b + count, a + count), materials[row], smooth)
        if caps:
            self.face(range(offset + count - 1, offset - 1, -1), materials[0])
            end = offset + (len(rings) - 1) * count
            self.face(range(end, end + count), materials[-1])

    def beam(self, points, width, depth, material, reference=UP, sizes=None,
             sides=4, caps=True, smooth=False):
        rings = []
        for i, point in enumerate(points):
            direction = (points[min(i + 1, len(points) - 1)]
                         - points[max(i - 1, 0)]).normalized()
            ref = Vector((0, 1, 0)) if abs(direction.dot(reference)) > .985 else reference
            across = ref.cross(direction).normalized()
            normal = direction.cross(across).normalized()
            factor = sizes[i] if sizes else 1
            if sides == 4:
                profile = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
            else:
                profile = [(cos(TAU * j / sides), sin(TAU * j / sides)) for j in range(sides)]
            rings.append([point + factor * (across * sx * width/2 + normal * sy * depth/2)
                          for sx, sy in profile])
        self.skin(rings, [material] * (len(rings) - 1), caps=caps, smooth=smooth)

    def finish(self, sharp=False):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        materials = list(dict.fromkeys(name for name, _, _ in self.styles))
        for name in materials:
            mesh.materials.append(pbr(name, *MATERIALS[name]))
        colors = (mesh.color_attributes.new(name="Tint", type='FLOAT_COLOR', domain='CORNER')
                  if VERTEX_TINTS.intersection(materials) else None)
        for polygon, (name, smooth, tint) in zip(mesh.polygons, self.styles):
            polygon.material_index = materials.index(name)
            polygon.use_smooth = smooth
            if colors:
                rgb = (tint or MATERIALS[name][0]) if name in VERTEX_TINTS else (1, 1, 1)
                for index in polygon.loop_indices:
                    colors.data[index].color = (*rgb, 1)
        if sharp:
            mesh.set_sharp_from_angle(angle=.63)
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        return obj


class Shell:
    def __init__(self, dome):
        self.dome = dome
        self.a = dome.length / 2 - .64
        self.b = dome.depth / 2 - .60
        self.floor = 1.35 if dome.cloud else 1.16
        self.h = dome.height - self.floor - (1.18 if dome.cloud else 1.04)
        self.entry_center = 14 if dome.cloud else -15
        self.entry_width = 11.2 if dome.cloud else 15.5
        self.peak = max(self.height_factor(pi * j / 100, pi * k / 100)
                        for j in range(101) for k in range(101))

    def height_factor(self, u, v):
        return (max(0, sin(u)) ** (.84 if self.dome.cloud else .93)
                * max(0, sin(v)) ** (1.18 if self.dome.cloud else 1.06)
                * (1 + self.dome.shoulder * cos(v))
                * (1 + self.dome.skew * cos(u)))

    def point(self, u, v):
        r = max(0, sin(u))
        bow = 1 - cos(v) ** 2
        return Vector((self.a * cos(u) + .035 * self.a * sin(u)**2 * bow,
                       -self.b * r**.76 * cos(v),
                       self.floor + self.h * self.height_factor(u, v) / self.peak))

    def normal(self, u, v):
        eps = .0002
        u = min(max(u, eps), pi - eps)
        along = self.point(u + eps, v) - self.point(u - eps, v)
        around = self.point(u, min(v + eps, pi)) - self.point(u, max(v - eps, 0))
        return around.cross(along).normalized()

    def in_entry(self, x):
        return abs(x - self.entry_center) < self.entry_width * .51

    def build_glazing(self):
        n, m = self.dome.bays, self.dome.rows
        shell = Part("Glass gridshell panels")
        seams = Part("Diagonal glazing mullions")
        glazing_random = random.Random(119 if self.dome.cloud else 86)
        shell.vertices = [self.point(0, 0), self.point(pi, 0)]
        grid = []
        edges = set()

        for row in range(m + 1):
            curb_row = .066 if self.dome.cloud else .080
            v = 0 if row == 0 else curb_row + (row - 1) * (pi - curb_row) / (m - 1)
            line = [(0, shell.vertices[0], self.normal(.035, v))]
            for col in range(1, n):
                # Staggered nodes produce a continuous diamond lattice.
                shift = .41 * (row % 2) * sin(pi * col / n)**.42
                u = pi * (col + shift) / n
                u += .115 * sin(2*v - .36) * sin(u)
                point = self.point(u, v)
                line.append((len(shell.vertices), point, self.normal(u, v)))
                shell.vertices.append(point)
            line.append((1, shell.vertices[1], self.normal(pi - .035, v)))
            grid.append(line)

        def seam(first, second, width, material):
            i, a, normal_a = first
            j, b, normal_b = second
            key = (min(i, j), max(i, j))
            if i == j or key in edges:
                return
            edges.add(key)
            tangent = (b - a).normalized()
            side_a = normal_a.cross(tangent).normalized() * width / 2
            side_b = normal_b.cross(tangent).normalized() * width / 2
            start, end = a + normal_a * .047, b + normal_b * .047
            seams.patch([start - side_a, end - side_b, end + side_b, start + side_a],
                        [(0, 1, 2, 3)], material)

        for row, (a, b) in enumerate(zip(grid, grid[1:])):
            for col in range(n):
                p, q, r, s = a[col], a[col + 1], b[col], b[col + 1]
                if row == 0 and self.in_entry((p[1].x + q[1].x)/2):
                    continue
                triangles = ((p, r, q), (q, r, s)) if row % 2 == 0 else ((p, r, s), (p, s, q))
                for tri in triangles:
                    ids = [point[0] for point in tri]
                    if len(set(ids)) == 3:
                        chance = .31 + .13 * cos(row * .40)
                        tint = glazing_random.choice([
                            (.19,.43,.51), (.24,.49,.48), (.34,.54,.57), (.25,.48,.54),
                        ])
                        name = "window" if glazing_random.random() < chance else "glass"
                        shell.face(ids, name, True, tint)
                seam(p, r, .115, "metal")
                seam(q, r, .105, "metal") if row % 2 == 0 else seam(p, s, .105, "metal")
                pitch = 4 if self.dome.cloud else 3
                if row in (1, m - 1) or (row % pitch == 0 and (row > 0 or not self.dome.cloud)):
                    seam(p, q, .079, "trim")
            seam(a[-2], b[-1], .115, "metal")
        shell.finish()
        seams.finish()

    def build_steel(self):
        spine = Part("Primary steel spine")
        ribs = Part("Radial outer steel arches")
        ties = Part("Arch standoffs and feet")
        start = .57 if self.dome.cloud else .56
        stations = [pi * i / 38 for i in range(39)]
        spine_points = []
        for u in stations:
            v = start + .05 * cos(u)
            p = self.point(u, v)
            p.z += .24 + .60 * sin(u)**.9
            spine_points.append(p)
        spine.beam(spine_points, .80 if self.dome.cloud else .85, 1.35, "paint", Vector((0,-.85,.53)),
                   sizes=[.62 + .38 * sin(u)**.65 for u in stations], smooth=True)

        for index in range(self.dome.arches):
            f = (index + 1) / (self.dome.arches + 1)
            root = pi * (.135 + .735 * f)
            heel = pi * (.005 + .985 * f) - .048 * sin(2*pi*f)
            steps = 20 if self.dome.cloud else 18
            points = []
            for step in range(steps + 1):
                t = step / steps
                u = (1 - t)*root + t*heel + .041*sin(pi*t)*sin(2*pi*f)
                v = start + .05*cos(root)
                v += (pi - v) * t
                surface = self.point(u, v)
                offset = .56 + (.95 if self.dome.cloud else .85)*sin(pi*t)**1.2
                outer = surface + self.normal(u, v) * offset * sin(pi * (t*.93 + .049))**.38
                if step == steps:
                    outer.y -= .19
                    outer.z = .62
                points.append(outer)
                if step in (3, 7, 11, steps - 2):
                    ties.beam([surface - self.normal(u, v)*.08, outer], .135, .135, "metal", caps=False)
            ribs.beam(points, .96 if self.dome.cloud else .91, 1.22 if self.dome.cloud else 1.05,
                      "paint", sizes=[.68 + .43 * sin(pi*i/steps)**.7 + .24*(i/steps)**8
                                      for i in range(steps + 1)], smooth=True)
        spine.finish(sharp=True)
        ribs.finish(sharp=True)
        ties.finish()

    def build_base(self):
        ring = Part("Low stone plinth and curb")
        floor = Part("Conservatory floor")
        count = 52 if self.dome.cloud else 56
        profile = [(-.10, 0), (.60, 0), (.60, .29), (.42, .35),
                   (.42, self.floor - .21), (.50, self.floor - .14), (.50, self.floor),
                   (-.14, self.floor)]
        rings = []
        for offset, height in profile:
            rings.append([self.perimeter(i*TAU/count, offset, height) for i in range(count)])
        ring.vertices = [point for band in rings for point in band]
        for lower, a in enumerate(rings[:-1]):
            material = "concrete" if lower in (0, 1, 4, 5) else "stone"
            for j in range(count):
                k = (j + 1) % count
                if a[j].y < 0 and self.in_entry((a[j].x + a[k].x)/2):
                    continue
                ring.face((lower*count+j, lower*count+k,
                           (lower+1)*count+k, (lower+1)*count+j), material)
        ring.finish()
        floor.patch([self.perimeter(i*TAU/count, -.20, .16) for i in range(count)],
                    [tuple(range(count))], "concrete")
        floor.finish()

    def perimeter(self, angle, offset, height):
        return Vector(((self.a + offset) * cos(angle),
                       (self.b + offset) * sin(angle) * abs(sin(angle))**(-.24)
                       if abs(sin(angle)) > 1e-10 else 0, height))

    def build_entrance(self):
        portal = Part("Front entrance glazing and mullions")
        canopy = Part("Front entrance canopy and columns")
        size = self.entry_width
        center = self.entry_center
        # The canopy sits in the recess of the oval footprint along visitor approach.
        front = self.dome.depth / 2 - .04
        face = self.b * sin(np.arccos(center / self.a))**.76
        start = face - (3.6 if self.dome.cloud else 4.9)
        height = 3.20 if self.dome.cloud else 3.60
        count = 9 if self.dome.cloud else 12
        for i in range(count):
            left, right = [center + (f/count - .5)*size for f in (i, i + 1)]
            y = -start - .27
            portal.patch([(left,y,.17),(right,y,.17),(right,y,height),(left,y,height)],
                         [(0,1,2,3)], "window")
            portal.beam([Vector((left,y-.06,.12)), Vector((left,y-.06,height))],
                        .10,.105,"metal")
        portal.beam([Vector((center-size/2,-start-.35,2.58)),
                     Vector((center+size/2,-start-.35,2.58))], .09,.15,"trim")
        portal.beam([Vector((center+size/2,-start-.34,.1)),
                     Vector((center+size/2,-start-.34,height))], .105,.105,"metal")
        rings = []
        for i in range(11):
            f = (i / 10 - .5) * 2
            x = center + f*(size/2+.70)
            y = -front + .53*f*f
            top = height + .22*(1 - f*f)
            rings.append([Vector((x,y,top)), Vector((x,-start+1.5,top+.45)),
                          Vector((x,-start+1.5,top+.68)), Vector((x,y,top+.26))])
        canopy.skin(rings, ["roof"] * 10, caps=True)
        canopy.beam([r[0]+Vector((0,.015,.11)) for r in rings], .11,.135,"trim")
        for f in (-.40, -.13, .14, .40):
            x = center + f*size
            canopy.beam([Vector((x,-front+.68,0)), Vector((x-.17,-front+.90,height+.16))],
                        .23,.23,"paint", sides=5)
        canopy.finish()
        portal.finish()


def organic_disk(part, x, y, z, radius_x, radius_y, material, phase=0, sides=14, tint=None):
    points = [(x,y,z)] + [(x+cos(a)*radius_x*(1+.08*sin(3*a+phase)),
                            y+sin(a)*radius_y*(1+.08*sin(3*a+phase)),z)
                           for a in [TAU*j/sides for j in range(sides)]]
    part.patch(points, [(0,j+1,(j+1)%sides+1) for j in range(sides)], material, tint=tint)


def vegetation_clump(part, x, y, z, sx, sy, sz, rng):
    tint = rng.choice([(.11,.22,.063),(.19,.31,.085),(.16,.29,.089),
                       (.26,.37,.10),(.13,.27,.12),(.21,.34,.13)])
    # A displaced hexagonal shoulder keeps shadows legible at kilometre-scale LOD.
    points = [(x+.15*sx, y-.11*sy, z+sz), (x,y,z-.26*sz)]
    for i in range(6):
        theta = TAU*i/6
        radius = rng.uniform(.73,1.19)
        points.append((x+sx*cos(theta)*radius,y+sy*sin(theta)*radius,z+rng.uniform(0,.30)*sz))
    faces = []
    for j in range(6):
        a, b = j+2, (j+1)%6+2
        faces.extend(((0,a,b),(1,b,a)))
    part.patch(points, faces, "leaf", tint=tint)


def flower_garden():
    beds = Part("Flower Field and terraced planting")
    trees = Part("Olive grove and garden trees")
    rng = random.Random(2319)
    organic_disk(beds, -2, 5, .22, 27, 18, "stone", 2, 24)
    flower_colors = [(.53,.18,.27),(.41,.29,.12),(.35,.17,.40),(.29,.37,.14)]
    for index in range(8):
        x = (index - 3.5) * 5.2
        organic_disk(beds, x, 3 + 3*cos(index*.45), .28, 2.4, 7.5 + sin(index)*2,
                     "leaf", index, 10, flower_colors[index % 4])
    for x,y,rx,ry in [(-36,5,13,19), (32,4,15,20), (12,23,21,9), (-12,-22,25,9), (34,-20,9,9)]:
        organic_disk(beds, x,y,.31+abs(x)*.001,rx,ry,"leaf",x,18,
                     (.17,.26,.11) if x < 0 else (.22,.32,.13))
        for j in range(4):
            t = TAU*j/4 + .9
            px, py = x+.69*rx*cos(t),y+.59*ry*sin(t)
            height = rng.uniform(1.8, 5.2)
            trees.beam([Vector((px,py,.30)),Vector((px+.19,py+.13,height*.79))],
                       .35,.35,"trunk",sides=3)
            for k in range(2):
                radius = rng.uniform(1.1, 2.2)
                vegetation_clump(trees,px+rng.uniform(-.9,.9),py+rng.uniform(-.9,.9),
                                 height*.78,radius,radius*.86,height*.30,rng)
    beds.finish()
    trees.finish()


def cloud_mountain():
    rng = random.Random(450)
    mountain = Part("Cloud Mountain")
    cascade = Part("Indoor waterfall and plunge pool")
    walks = Part("Cloud Walk and Tree Top Walk")
    garden = Part("Foothills planting")
    cx, cy = -5.0, 0.8
    levels = [(0.17,19.5,13.6), (2.9,20.0,13.8), (5.8,18.0,12.5),
              (8.7,17.0,11.2), (12.2,15.9,10.35), (15.6,13.4,9.0),
              (19.0,13.2,8.75), (22.4,11.5,8.8), (25.8,10.4,7.7),
              (28.9,8.5,6.9), (32.9,6.65,5.9), (34.6,5.4,4.75)]
    rings = []
    n = 23
    for index,(height,rx,ry) in enumerate(levels):
        ring = []
        for j in range(n):
            a = TAU*j/n
            ridge = 1 + .14*sin(3*a+index*.33) + .09*cos(5*a-index*.32)
            y_shift = -2.8*sin(height*pi/75) + 1.3*sin(height*.28)
            z = height + (0 if index == 0 else rng.uniform(-.70, .37))
            ring.append(Vector((cx + 3.5*sin(height/34) + rx*cos(a)*ridge,
                                cy + y_shift + ry*sin(a)*ridge, z)))
        rings.append(ring)
    mountain.vertices.extend(point for ring in rings for point in ring)
    for i in range(len(rings)-1):
        for j in range(n):
            a, b = i*n+j, i*n+(j+1)%n
            # Green ledges wind around a visibly broken dark-grey rock core.
            probability = (.82 if i in (1,3,4,6,8,9,10) else .37)
            tint = rng.choice([(.15,.26,.085),(.18,.29,.085),(.17,.32,.12),
                               (.20,.30,.07),(.12,.23,.075)])
            for face in ((a,b,b+n),(a,b+n,a+n)):
                mountain.face(face, "leaf" if rng.random() < probability else "stone", tint=tint)
    peak = len(mountain.vertices)
    mountain.vertices.append(Vector((cx+3.1,cy-2.0,35)))
    for j in range(n):
        mountain.face(((len(rings)-1)*n+j,(len(rings)-1)*n+(j+1)%n,peak), "leaf")
    for index in range(1,len(rings)-1):
        for j in rng.sample(range(n), 7):
            x,y,z = rings[index][j]
            vegetation_clump(mountain,x,y,z,rng.uniform(.65,1.55),rng.uniform(.75,1.50),
                             rng.uniform(.48,1.85),rng)
    mountain.finish()

    # Anchor the narrow white curtain to the forward ledges of the mountain.
    falls = [ring[18] for ring in rings]
    tints = [(.58,.72,.71),(.70,.81,.80),(.46,.64,.64),(.79,.85,.83)]
    for i in range(7):
        k = (i-3)*.40
        sheet = []
        for j, (x,y,z) in enumerate(falls):
            width = 1.48-.061*j
            x += k*width + .21*sin(j*.90+i*.36)
            y -= .38 + .10*abs(k)
            sheet.extend(((x-.19*width,y,z), (x+.19*width,y,z)))
        cascade.patch(sheet, [(j,j+1,j+3,j+2) for j in range(0,len(sheet)-2,2)],
                      "water", tint=tints[i % 4])
    organic_disk(cascade,falls[0].x,falls[0].y-1.0,.255,5.2,3.42,"water",1,20)
    cascade.finish()

    for number,(start,end,height,rx,ry) in enumerate([
            (-.40,3.63,24,20.2,13.0), (.95,5.08,11.4,24.3,16.9)]):
        points = []
        for j in range(21):
            f = j/20
            t = start + (end-start)*f
            flare = 1 - .51*abs((f-.50)*2)**2.1 + .20*sin(TAU*f)
            points.append(Vector((cx+rx*flare*cos(t),cy+ry*flare*sin(t),
                                  height-3.8*f + 1.5*sin(pi*f+number))))
        walks.beam(points, 2.05,.42,"concrete")
        for side in (-1,1):
            rails = []
            for j,point in enumerate(points):
                direction = points[min(j+1,20)]-points[max(j-1,0)]
                offset = UP.cross(direction).normalized()*side*.98
                rails.append(point+offset)
            walks.skin([[p+UP*.23,p+UP*1.04] for p in rails], ["trim"]*20, closed=False)
            for j in range(20):
                a, b = rails[j], rails[j+1]
                walks.patch([a+UP*1.04,b+UP*1.04,b+UP*1.18,a+UP*1.18],
                            [(0,1,2,3)], "paint")
    walks.finish()

    for x,y,rx,ry in [(-26,-7,9,12),(21,7,11,14),(-13,17,16,7),(-1,-22,19,5)]:
        organic_disk(garden,x,y,.23,rx,ry,"leaf",x,13,(.12,.23,.071))
        for j in range(5):
            angle = TAU*j/5 + .17
            px,py = x+.72*rx*cos(angle),y+.74*ry*sin(angle)
            vegetation_clump(garden,px,py,.62,rng.uniform(1.7,3.1),rng.uniform(1.4,2.8),
                             rng.uniform(1.25,3.25),rng)
    garden.finish()


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1


def build(dome):
    reset()
    shell = Shell(dome)
    shell.build_glazing()
    shell.build_steel()
    shell.build_base()
    shell.build_entrance()
    if dome.cloud:
        cloud_mountain()
    else:
        flower_garden()

    # Normalize the outer envelope after accounting for structural steel and curb profiles.
    objs = list(bpy.context.scene.objects)
    width = max(abs(v.co.x) for o in objs for v in o.data.vertices)
    depth = max(abs(v.co.y) for o in objs for v in o.data.vertices)
    tall = max(v.co.z for o in objs for v in o.data.vertices if o.name != "Cloud Mountain")
    for o in objs:
        # Keep the landscape and the waterfall independent of the shell's height adjustment.
        adjust_height = o.name not in {
            "Cloud Mountain", "Indoor waterfall and plunge pool", "Cloud Walk and Tree Top Walk",
            "Foothills planting", "Flower Field and terraced planting", "Olive grove and garden trees",
        }
        for v in o.data.vertices:
            v.co.x *= dome.length/(2*width)
            v.co.y *= dome.depth/(2*depth)
            v.co.z = max(0, v.co.z * (dome.height/tall if adjust_height else 1))
        o.data.update()
    path = ROOT/f"{dome.file}.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', export_yup=True,
                              export_animations=False, export_skins=False, export_cameras=False,
                              export_lights=False, export_texcoords=False)
    return path


def area(name, position, target, power, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size, data.color = power, 'DISK', size, color
    lamp = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(lamp)
    lamp.location = position
    lamp.rotation_euler = (target-position).to_track_quat('-Z','Y').to_euler()


def render_sheet(path):
    reset()
    bpy.ops.import_scene.gltf(filepath=str(path))
    scene = bpy.context.scene
    corners = [o.matrix_world @ vertex.co for o in scene.objects
               if o.type == 'MESH' for vertex in o.data.vertices]
    low = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    target = (high+low)/2
    span = max(high-low)

    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 18
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 8
    scene.render.threads_mode, scene.render.threads = 'FIXED', 2
    scene.render.resolution_x, scene.render.resolution_y = 660, 420
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new("Marina daylight")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (.63,.74,.92,1)
    background.inputs["Strength"].default_value = .54

    bpy.ops.mesh.primitive_plane_add(size=span*40, location=(0,0,-.035))
    bpy.context.object.data.materials.append(pbr("Review ground", (.16,.19,.196), .92))
    area("Warm key", target+Vector((-.76,-.78,1.46))*span, target,
         span**2*22, span*.77, (1,.94,.84))
    area("Blue fill", target+Vector((1.02,-.14,.86))*span, target,
         span**2*7, span*1.02, (.74,.88,1))
    area("Rim", target+Vector((.15,.88,1.30))*span, target,
         span**2*12, span*.88, (1,.96,.88))
    data = bpy.data.cameras.new("Review camera")
    camera = bpy.data.objects.new("Review camera", data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    data.type, data.clip_end = 'ORTHO', span*25

    viewpoints = {
        "front": (0,-1,0), "right": (1,0,0), "rear": (0,1,0),
        "front_three_quarter": (.91,-1.4,.69), "rear_three_quarter": (-.93,1.3,.82),
        "top": (0,0,1),
    }
    aspect = scene.render.resolution_x/scene.render.resolution_y
    panels = []
    panel_path = ROOT/".render-panel.png"
    for name, direction in viewpoints.items():
        look = Vector(direction).normalized()
        camera.rotation_euler = ((0,0,0) if name == "top"
                                 else (-look).to_track_quat('-Z','Y').to_euler())
        rotation = camera.rotation_euler.to_matrix()
        projected = [rotation.transposed() @ (point-target) for point in corners]
        lower = [min(v[i] for v in projected) for i in (0,1)]
        upper = [max(v[i] for v in projected) for i in (0,1)]
        center = Vector(((lower[0]+upper[0])/2,(lower[1]+upper[1])/2,0))
        camera.location = target + look*span*3.6 + rotation@center
        data.ortho_scale = max(upper[0]-lower[0], (upper[1]-lower[1])*aspect)*1.15
        scene.render.filepath = str(panel_path)
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(str(panel_path), check_existing=False)
        pixels = np.empty(len(img.pixels), dtype=np.float32)
        img.pixels.foreach_get(pixels)
        panels.append(pixels.reshape(img.size[1], img.size[0], 4))
        bpy.data.images.remove(img)
        panel_path.unlink()

    height, width = panels[0].shape[:2]
    gap = 7
    sheet = np.full((2*height+gap,3*width+2*gap,4), .06, np.float32)
    sheet[:,:,3] = 1
    for i, panel in enumerate(panels):
        x, y = i%3*(width+gap), (1-i//3)*(height+gap)
        sheet[y:y+height,x:x+width,:] = panel
    image = bpy.data.images.new("Six-view contact sheet", sheet.shape[1], sheet.shape[0], alpha=False)
    image.pixels.foreach_set(sheet.ravel())
    image.filepath_raw = str(ROOT/f"{path.stem}_six_views.png")
    image.file_format = 'PNG'
    image.save()
    return {
        "file": Path(image.filepath_raw).name,
        "sha256": sha256(Path(image.filepath_raw).read_bytes()).hexdigest(),
        "glb_sha256": sha256(path.read_bytes()).hexdigest(),
        "renderer": "Blender 5.1.2 Cycles CPU, 2 threads, 18 samples",
        "views": list(viewpoints),
    }


def main():
    assert bpy.app.version == (5,1,2), bpy.app.version_string
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    mode = args[0] if args else "all"
    assert mode in {"all", "build", "render"}, mode
    if mode in {"all", "build"}:
        for dome in DOMES:
            build(dome)
    if mode in {"all", "render"}:
        evidence = {dome.file: render_sheet(ROOT/f"{dome.file}.glb") for dome in DOMES}
        (ROOT/".render-evidence.json").write_text(json.dumps(evidence, indent=2)+"\n")


if __name__ == "__main__":
    main()
