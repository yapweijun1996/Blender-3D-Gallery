"""Build the paired Esplanade exterior GLBs and render the exported meshes."""
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / ".review"
TAU = math.tau

# Design coordinates are east-southeast / north-northeast. Turn the finished
# site toward the southwest bay approach and center it on the shared site.
TURN = math.radians(35)
SITE_CENTER = Vector((0, 0, 0))  # computed from the terrace bounds
PALETTE = {
    "paint": ((.79, .77, .68), 0, .56),
    "glass": ((.145, .242, .249), .28, .23),
    "window": ((.092, .154, .158), .25, .26),
    "wall": ((.48, .365, .28), 0, .76),
    "roof": ((.29, .312, .315), .23, .56),
    "concrete": ((.48, .457, .40), 0, .84),
    "metal": ((.68, .63, .54), .73, .37),
    "chrome": ((.55, .59, .59), .83, .28),
    "trim": ((.116, .132, .124), .46, .46),
    "stone": ((.64, .554, .457), 0, .78),
    "water": ((.095, .224, .222), .28, .18),
    "leaf": ((.088, .172, .053), 0, .83),
    "trunk": ((.166, .105, .06), 0, .87),
    "light": ((.93, .77, .46), 0, .4),
    "lamp_emissive": ((.95, .74, .4), 0, .29),
    "rubber": ((.024, .025, .024), 0, .82),
    "plate": ((.328, .284, .212), .32, .54),
}
MAT = {}
SHADES = {
    # Center, azimuth, major/minor span, nominal crown, grid resolution and skew.
    "Concert_Hall": ((-43, -64), 39, 83.6, 63, 33.6, 31, 4),
    "Theatre": ((-33, 38), -51, 73, 83.8, 35.0, 32, 42),
}


def world(p):
    x, y, z = p
    c, s = math.cos(TURN), math.sin(TURN)
    return (c * x - s * y - SITE_CENTER.x, s * x + c * y - SITE_CENTER.y, z)


def make_materials():
    for name, (rgb, metal, roughness) in PALETTE.items():
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*rgb, 1)
        mat.use_backface_culling = name not in {"metal", "glass", "window", "paint", "chrome"}
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (*rgb, 1)
        shader.inputs["Metallic"].default_value = metal
        shader.inputs["Roughness"].default_value = roughness
        MAT[name] = mat


def ccw(points):
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
    return points if area > 0 else list(reversed(points))


class Batch:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.materials = []

    def face(self, points, mat):
        start = len(self.vertices)
        self.vertices.extend(points)
        self.faces.append(tuple(range(start, len(self.vertices))))
        self.materials.append(mat)

    def prism(self, outline, low, high, side, top=None):
        outline = ccw(outline)
        bottom = [(x, y, low) for x, y in outline]
        upper = [(x, y, high) for x, y in outline]
        for i, a in enumerate(bottom):
            j = (i + 1) % len(bottom)
            self.face([a, bottom[j], upper[j], upper[i]], side)
        for tri in tessellate_polygon([[Vector(p) for p in upper]]):
            self.face([upper[i] for i in tri], top or side)
            self.face([bottom[i] for i in reversed(tri)], side)

    def box(self, x, y, z, width, depth, height, mat):
        w, d = width / 2, depth / 2
        self.prism([(x-w, y-d), (x+w, y-d), (x+w, y+d), (x-w, y+d)], z, z+height, mat)

    def beam(self, start, end, width, mat, depth=None, sides=4):
        a, b = Vector(start), Vector(end)
        axis = (b - a).normalized()
        reference = Vector((0, 0, 1)) if abs(axis.z) < .9 else Vector((1, 0, 0))
        u = axis.cross(reference).normalized()
        v = axis.cross(u)
        if sides == 4:
            offsets = [u * (width/2 * x) + v * ((depth or width)/2 * y)
                       for x, y in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        else:
            offsets = [(u*math.cos(i*TAU/sides) + v*math.sin(i*TAU/sides))*width/2
                       for i in range(sides)]
        for i, p in enumerate(offsets):
            q = offsets[(i+1) % sides]
            self.face([a+p, a+q, b+q, b+p], mat)
        self.face([a+p for p in reversed(offsets)], mat)
        self.face([b+p for p in offsets], mat)

    def build(self, part):
        if not self.faces:
            return
        mesh = bpy.data.meshes.new(part)
        mesh.from_pydata([world(p) for p in self.vertices], [], self.faces)
        mesh.update()
        slots = list(dict.fromkeys(self.materials))
        for name in slots:
            mesh.materials.append(MAT[name])
        indices = {name: i for i, name in enumerate(slots)}
        for polygon, name in zip(mesh.polygons, self.materials):
            polygon.material_index = indices[name]
        obj = bpy.data.objects.new(part, mesh)
        bpy.context.collection.objects.link(obj)
        return obj


def ellipse(x, y, rx, ry, steps=24, angle=0):
    c, s = math.cos(angle), math.sin(angle)
    return [(x + c*rx*math.cos(t) - s*ry*math.sin(t),
             y + s*rx*math.cos(t) + c*ry*math.sin(t))
            for t in (i*TAU/steps for i in range(steps))]


def shade_point(spec, u, v):
    (cx, cy), angle, length, width, top, _, skew = spec
    a, g = math.radians(angle), math.radians(skew)
    r2 = u*u + v*v
    m = 2 / (1 + r2)
    h = max(0, (1 - r2) / (1 + r2))
    sx = (u*math.cos(g) - v*math.sin(g)) * m
    sy = (u*math.sin(g) + v*math.cos(g)) * m
    # One end of each envelope is fuller. The rising eave follows the foyer.
    x = sx * length/2 + 2.8 * h
    y = sy * width/2 * (1 + .16*sx) - 2.2 * h
    spring = 9.9 + 2.70*sx + 1.15*sy + .8*sy*sy
    z = spring*(1-h) + top*h**.91
    return Vector((cx+x*math.cos(a)-y*math.sin(a), cy+x*math.sin(a)+y*math.cos(a), z))


def clipped_grid(count):
    # Clip Cartesian cells to a regular polygon on the stereographic disk.
    # Two constant grid directions preserve the diagonal rows on the roof.
    disk = [Vector((math.cos(i*TAU/144), math.sin(i*TAU/144))) for i in range(144)]
    edges = [(a, b-a) for a, b in zip(disk, disk[1:] + disk[:1])]
    for iy in range(count):
        for ix in range(count):
            u, v = ix*2/count-1, iy*2/count-1
            step = 2/count
            quad = [Vector(p) for p in ((u, v), (u+step, v), (u+step, v+step), (u, v+step))]
            radii = [p.length_squared for p in quad]
            if min(radii) > (1 + step*1.43)**2:
                continue
            if max(radii) > .999:
                for a, edge in edges:
                    if not quad:
                        break
                    output = []
                    for p, q in zip(quad, quad[1:] + quad[:1]):
                        dp, dq = edge.cross(p-a), edge.cross(q-a)
                        inside_p, inside_q = dp >= -5e-8, dq >= -5e-8
                        if inside_p:
                            output.append(p)
                        if inside_p != inside_q:
                            t = max(0.0, min(1.0, dp/(dp-dq)))
                            if 1e-5 < t < 1 - 1e-5:
                                output.append(p.lerp(q, t))
                    quad = output
            if len(quad) >= 3:
                yield quad


def ring_surface(batch, outline, upper, lower, material):
    for a, b in zip(outline, outline[1:] + outline[:1]):
        batch.face([(a[0], a[1], lower), (b[0], b[1], lower),
                    (b[0], b[1], upper), (a[0], a[1], upper)], material)


def build_domes():
    for hall, spec in SHADES.items():
        shades, glass, grid, eaves = Batch(), Batch(), Batch(), Batch()
        seen = set()
        for polygon in clipped_grid(spec[5]):
            points = [shade_point(spec, *p) for p in polygon]
            for i in range(1, len(points)-1):
                tri = [points[0], points[i], points[i+1]]
                a, b, c = tri
                cross = (b-a).cross(c-a)
                if cross.length < .002:
                    continue
                n = cross.normalized()
                glass.face(tri, "glass")
                center = (a+b+c)/3
                if cross.length > .37:
                    sun = Vector((-.67, -.62, .43))
                    strongest = max(range(3), key=lambda j: tri[j].dot(sun))
                    tip = tri[strongest]
                    left, right = tri[(strongest+1)%3], tri[(strongest+2)%3]
                    foot = tip.lerp(center, .12) + n*.14
                    wing_l = left.lerp(center, .14) + n*.38
                    wing_r = right.lerp(center, .14) + n*.38
                    fold = wing_l.lerp(wing_r, .43).lerp(foot, .18)
                    rise = min(1.2, math.sqrt(cross.length)*.49) * (.86 + .18*abs(n.dot(sun)))
                    peak = fold + n*rise + sun*.19
                    shades.face([foot, wing_l, peak], "metal")
                    shades.face([foot, peak, wing_r], "metal")
            for a, b in zip(points, points[1:] + points[:1]):
                key = tuple(sorted(tuple(round(float(x), 3) for x in p) for p in (a, b)))
                if key in seen or (a-b).length < .15:
                    continue
                seen.add(key)
                center = Vector((*spec[0], 8))
                ab = (b-a).normalized()
                normal = ((a+b)/2-center).normalized()
                across = normal.cross(ab).normalized()*.045
                lift = normal*.058
                grid.face([a+across+lift, a-across+lift, b-across+lift, b+across+lift], "trim")
        rim = [shade_point(spec, math.cos(i*TAU/72), math.sin(i*TAU/72)) for i in range(72)]
        for a, b in zip(rim, rim[1:]+rim[:1]):
            eaves.face([a-Vector((0,0,.48)), b-Vector((0,0,.48)), b, a], "chrome")
        glass.build(hall + "_Dome_Glazing")
        grid.build(hall + "_Dome_Steel_Grid")
        shades.build(hall + "_Folded_Aluminium_Sunshades")
        eaves.build(hall + "_Dome_Eave")

# Survey-scale envelopes traced in plan from the site outline and mapped venues.
PLAZA = [
    (-113, -66), (-110, -89), (-98, -108), (-84, -119), (-67, -123),
    (-37, -123), (-12, -120), (19, -116), (51, -112), (73, -106),
    (92, -96), (106, -87), (122, -75), (137, -59), (138, -34),
    (129, 10), (121, 29), (91, 40), (73, 51), (46, 59), (10, 69),
    (-24, 96), (-56, 100), (-80, 87), (-93, 61), (-106, 31), (-111, 11),
    (-111, -19), (-115, -43),
]
BAY_EDGE = PLAZA[1:15]
MALL = [
    (-16, -59), (-6, -68), (5, -85), (15, -82), (23, -74),
    (28, -63), (27, -52), (38, -48), (45, -38),
    (37, -36), (32, -30), (32, -23), (37, -17), (44, -14),
    (51, -16), (56, -22), (56, -30), (52, -35), (63, -43),
    (85, -37), (82, -17), (76, 9), (70, 25), (60, 42),
    (46, 51), (30, 53), (13, 48), (4, 54), (-5, 49),
    (-2, 28), (9, 19), (11, 9), (6, -2), (-10, -18),
]
ANNEXE = [(86,-37), (94,-45), (103,-48), (112,-43), (115,-34),
          (129,-27), (117,20), (94,14), (105,-33), (101,-39),
          (96,-37), (82,16), (74,14)]


def band(batch, a, b, low, high, mat, offset=0):
    a, b = Vector(a), Vector(b)
    delta = b-a
    outward = Vector((delta.y, -delta.x)).normalized() * offset
    a += outward
    b += outward
    batch.face([(a.x,a.y,low), (b.x,b.y,low), (b.x,b.y,high), (a.x,a.y,high)], mat)


def ribbon(batch, a, b, width, mat, normal=(0, 0, 1)):
    a, b = Vector(a), Vector(b)
    span = (b-a).cross(Vector(normal)).normalized() * width/2
    batch.face([a-span, a+span, b+span, b-span], mat)


def facade(batch, outline, low, high, interval, mat, recessed=False):
    outline = ccw(outline)
    for k, start in enumerate(outline):
        a, b = Vector(start), Vector(outline[(k+1)%len(outline)])
        length = (b-a).length
        divisions = max(1, round(length/interval))
        along = (b-a).normalized()
        for i in range(divisions):
            p, q = a.lerp(b, i/divisions), a.lerp(b, (i+1)/divisions)
            gap = min(.24 if recessed else .125, (q-p).length*.15)
            band(batch, p+along*gap, q-along*gap*.65, low+.08, high-.09, mat, .085)
        band(batch, a, b, high-.12, high, "chrome", .13)


def hall_foyers():
    for hall, spec in SHADES.items():
        podium, facade_mesh = Batch(), Batch()
        cx, cy = spec[0]
        perimeter = [shade_point(spec, math.cos(i*TAU/36), math.sin(i*TAU/36))
                     for i in range(36)]
        outline = [(p.x, p.y) for p in perimeter]
        podium.prism(outline, .32, 1.15, "stone")
        ring_surface(podium, outline, 7.16, 1.15, "trim")
        # A recessed auditorium outer volume sits inside the surrounding foyer.
        inner = [(cx+(p.x-cx)*.73, cy+(p.y-cy)*.66) for p in perimeter[::2]]
        podium.prism(inner, 4.75, 7.31, "wall", "roof")
        floor = [(cx+(p.x-cx)*1.022, cy+(p.y-cy)*1.022) for p in perimeter]
        podium.prism(floor, 4.43, 4.76, "stone")
        for i, a in enumerate(perimeter):
            b = perimeter[(i+1)%len(perimeter)]
            l, r = Vector(a.xy), Vector(b.xy)
            d = (r-l).normalized()
            out = Vector((d.y,-d.x))
            l += out*.05
            r += out*.05
            for low, high in ((1.2,4.42), (4.78,6.95)):
                d1 = d*.12
                band(facade_mesh, l+d1, r-d1, low+.06, high-.04, "glass", .042)
                band(facade_mesh, l, r, high-.14, high-.04, "chrome", .08)
            offset = Vector((out.x,out.y,0))
            lower_a = Vector((l.x,l.y,7.05))
            lower_b = Vector((r.x,r.y,7.05))
            upper_a, upper_b = a-Vector((0,0,.43)), b-Vector((0,0,.43))
            facade_mesh.face([lower_a,lower_b,upper_b,upper_a], "glass")
            facade_mesh.face([lower_a+offset*.065, lower_a+Vector((d.x,d.y,0))*.16+offset*.065,
                              upper_a+Vector((d.x,d.y,0))*.16+offset*.065, upper_a+offset*.065], "chrome")
            if i % 4 == 0:
                root = l+out*.27
                podium.beam((*root, .64), (*root, 6.98), .72, "stone", .56)
        podium.build(hall + "_Podium_and_Stone_Bands")
        facade_mesh.build(hall + "_Curved_Glass_Foyer")


def build_mall():
    mall, skin, terrace, annex = Batch(), Batch(), Batch(), Batch()
    mall.prism(MALL, .32, 10.8, "wall", "concrete")
    facade(skin, MALL, 1.03, 4.29, 3.25, "window", True)
    facade(skin, MALL, 4.89, 8.03, 4.2, "glass")
    facade(skin, MALL, 8.35, 10.21, 4.5, "window")
    outline = ccw(MALL)
    for a, b in zip(outline, outline[1:]+outline[:1]):
        for low, high, mat, width in ((.63,1.02,"stone",.20), (4.33,4.78,"stone",.28),
                                      (8.08,8.29,"stone",.25), (10.37,10.9,"stone",.31),
                                      (10.9,11.67,"stone",.21)):
            band(mall, a, b, low, high, mat, width)
    # Arced waterfront club room and the terraced levels it overlooks.
    pavilion = ellipse(12,-62,12,24,28,math.radians(-19))
    mall.prism(pavilion, 10.72, 13.34, "window", "roof")
    facade(skin, pavilion, 10.82, 13.19, 2.4, "glass")
    mall.prism(ellipse(12,-62,12.45,24.38,28,math.radians(-19)),13.22,13.64,"metal","roof")

    # Sheltered retail bays and the west-facing return around the courtyard.
    awning = [(33,-40),(29,-31),(29,-21),(35,-15),(44,-12),(53,-13),
              (59,-20),(59,-30),(54,-36),(53,-33),(56,-29),(56,-20),
              (52,-16),(44,-15),(38,-17),(33,-23),(33,-31),(37,-39)]
    terrace.prism(awning,3.72,4.02,"chrome","roof")
    for x, y in [(30,-34),(29,-26),(31,-20),(38,-14),(48,-13),(56,-17),(59,-23),(57,-32)]:
        terrace.beam((x,y,.35),(x,y,3.74), .20, "chrome", sides=6)
    for x, y, rx, ry, angle in [(22,-35,3,10,-.45),(15,8,2,6,-.05),
                                 (35,32,4,10,-.3),(56,10,2.25,12,-.27),(64,-19,2.35,11,-.28)]:
        planter(terrace,x,y,rx,ry,10.81,angle,8)
    for x, y, angle in [(33,-52,-.21),(61,-34,-.25),(42,47,.23)]:
        hood = ellipse(x,y,2.8,5.0,8,angle)
        terrace.prism(hood,10.81,13.22,"window","roof")
        facade(terrace,hood,11.3,13.0,2.5,"glass")
    annex.prism(ANNEXE, .35, 7.4, "wall", "roof")
    facade(annex, ANNEXE, 1.02, 4.0, 3.3, "window")
    facade(annex, ANNEXE, 4.76, 6.8, 4.2, "glass")
    annex.prism([(102,-38),(113,-35),(124,-24),(116,13),(98,10)],7.39,9.25,"wall","roof")
    mall.build("Esplanade_Mall_Stone_Terraces")
    skin.build("Esplanade_Mall_Shopfronts_and_West_Frontage")
    terrace.build("Esplanade_Mall_Roof_Garden_and_Arcade")
    annex.build("Esplanade_Annexe_Studio")


def planter(batch, x, y, width, length, z, angle=0, steps=12):
    outer = ellipse(x, y, width, length, steps, angle)
    inner = ellipse(x, y, max(.4,width-.24), max(.4,length-.24), steps, angle)
    batch.prism(outer, z, z+.48, "stone")
    batch.prism(inner, z+.48, z+.52, "leaf")


def build_concourse():
    glass, steel, entry = Batch(), Batch(), Batch()

    def section(t, v):
        x = -81 + 110*t
        center = -10 + 3*t
        span = 16.3 - 5.4*t
        z = 8.1 + (6.0-1.5*t)*max(0,1-v*v)**.86
        return Vector((x, center+v*span, z))

    nu, nv = 15, 8
    for i in range(nu):
        for j in range(nv):
            t, v = i/nu, j*2/nv-1
            r, w = (i+1)/nu, (j+1)*2/nv-1
            a,b,c,d = section(t,v),section(r,v),section(r,w),section(t,w)
            glass.face([a,b,c], "glass")
            glass.face([a,c,d], "glass")
            up = Vector((0,0,.065))
            ribbon(steel, a+up,b+up,.115,"chrome")
            if (i+j)%2==0:
                ribbon(steel, a+up,c+up,.08,"trim")
            ribbon(steel, a+up,d+up,.14 if i%4==0 else .075,"chrome")
            if i==nu-1:
                ribbon(steel,b+up,c+up,.15,"chrome")
    front = [section(0, i*2/nv-1) for i in range(nv+1)]
    for j in range(nv):
        a,b = front[j:j+2]
        glass.face([(a.x,a.y,.83), a, b, (b.x,b.y,.83)], "glass")
        steel.beam((a.x-.09,a.y,.76),a-Vector((.09,0,0)),.14,"chrome")
    for i in range(nu):
        for v in (-1, 1):
            a, b = section(i/nu,v),section((i+1)/nu,v)
            if v > 0:
                a, b = b, a
            lo, hi = Vector(a.xy),Vector(b.xy)
            band(glass, lo, hi, .79, 8.11, "window")
            mid = lo.lerp(hi,.5)
            along = (hi-lo).normalized()
            for left, right in ((lo,mid),(mid,hi)):
                left, right = left+along*.15,right-along*.12
                band(glass,left,right,1.0,4.16,"glass",.075)
                band(glass,left,right,4.33,7.99,"glass",.075)
            band(steel,lo,hi,4.13,4.28,"chrome",.10)
    for z in (2.88, 5.95, 8.15):
        steel.beam((-81.15,front[0].y,z),(-81.15,front[-1].y,z),.14,"chrome")
    entry.prism([(-84,-23),(-84,3),(-91,3),(-92,.5),(-92,-21),(-89,-24)],4.95,5.32,"chrome","glass")
    # The low bridge-side landing widens to a fan of shallow approach steps.
    for i in range(3):
        west = -94.6+i*.68
        south, north = -23.8+i*.43,4.3-i*.36
        entry.prism([(west,south+.66), (west+1.7,south), (-81.18,south+.35),
                     (-81.18,north-.31), (west+1.7,north), (west,north-.63)],
                    .338+i*.16, .498+i*.16, "stone", "concrete")
    for y in (-21,-15,-9,-3,1):
        entry.beam((-90,y,.46),(-90,y,4.95), .31, "chrome", sides=6)
    for i in range(8):

        q = -23+i*3.75
        band(entry, (-81.18,q+1.275), (-81.18,q-1.275), .82,3.00,"trim")
        band(entry, (-81.23,q+1.12), (-81.23,q-1.12), .91,2.89,"window")
    glass.build("Concourse_Arched_Glass_and_Curtain_Wall")
    steel.build("Concourse_Steel_Ribs_and_Mullions")
    entry.build("Esplanade_Bridge_Entry_Canopy_and_Doors")


def build_terrace():
    paving, edge, garden, canopy = Batch(), Batch(), Batch(), Batch()
    paving.prism(PLAZA, 0, .34, "concrete")
    # The promenade follows the sea wall with a contrasting stone paving band.
    inside = [(x*.96, y*.96+6) for x,y in BAY_EDGE]
    edge.prism(BAY_EDGE+list(reversed(inside)), .341, .50,"stone","stone")
    for a,b in zip(BAY_EDGE, BAY_EDGE[1:]):
        a,b = Vector(a),Vector(b)
        n = max(1,round((b-a).length/4.2))
        for i in range(n):
            p = a.lerp(b,i/n)*.998
            ribbon(edge, (*p,.49),(*p,1.65),.13,"chrome", (b.y-a.y,a.x-b.x,0))
        for z in (.85,1.54):
            a1,b1 = a*.998,b*.998
            ribbon(edge, (*a1,z),(*b1,z),.11,"chrome", (b.y-a.y,a.x-b.x,0))
    for x,y,rx,ry,ang in [(-100,-28,5.1,12,.27),(-97,7,4.6,11,-.20),
                         (-97,35,2.9,9,-.25),(-106,-51,3,7,.24),
                         (81,-58,9,6,.22),(94,-68,10,6.5,.29),
                         (117,-58,9,6.5,.5),(-13,-107,13,2.2,0)]:
        planter(garden,x,y,rx,ry,.343,ang,8)
    for x,y,w,d in [(-98,-10,4.8,14.7),(-104,15,3.2,10.2)]:
        garden.box(x,y,.342,w,d,.21,"stone")
        garden.box(x,y,.552,w-.26,d-.27,.025,"water")
    for x,y in [(-99,-30),(-97,5),(-97,35),(-105,-53),(83,-57),(96,-67),(116,-59)]:
        garden.beam((x,y,.48),(x+.26,y+.25,4.9),.38,"trunk",sides=6)
        for i in range(3):
            theta = i*TAU/3+ .1*x
            tx, ty = x+math.cos(theta)*2.15,y+math.sin(theta)*2.15

            crown = ellipse(tx,ty,2.65,2.1,5,theta)
            for j,p in enumerate(crown):
                q = crown[(j+1)%len(crown)]
                garden.face([(*p,5.28),(*q,5.28),(tx+.45,ty-.19,7.04)],"leaf")
                garden.face([(*q,5.28),(*p,5.28),(tx-.28,ty+.37,4.35)],"leaf")

    # The waterfront kiosk canopy runs between the bridge and the outdoor stage.
    for i in range(20):
        x = -75 + i*5.3
        roof_y = -113+.00064*(x+36)**2
        next_x = x+5.3
        next_y = -113+.00064*(next_x+36)**2
        canopy.face([(x,roof_y-2.6,3.96),(next_x,next_y-2.6,3.96),
                     (next_x,next_y,4.64),(x,roof_y,4.64)], "glass")
        canopy.face([(x,roof_y,4.64),(next_x,next_y,4.64),
                     (next_x,next_y+2.6,3.91),(x,roof_y+2.6,3.91)], "glass")
        ribbon(canopy,(x,roof_y-2.6,4.0),(x,roof_y,4.68),.125,"chrome")
        ribbon(canopy,(x,roof_y,4.68),(x,roof_y+2.6,3.95),.125,"chrome")
        if i%2==0:
            canopy.beam((x,roof_y+.92,.35),(x,roof_y+.92,4.35),.21,"chrome",sides=6)
    for x,y in [(-57,-109),(-23,-109),(14,-107)]:
        canopy.box(x,y,.35,4.2,2.8,2.94,"wall")
        canopy.box(x,y-1.42,.98,3.48,.13,1.72,"window")
        canopy.box(x,y,3.25,4.55,3.18,.22,"roof")
    paving.build("Waterfront_Terrace_and_Forecourt_Paving")
    edge.build("Waterfront_Seawall_Coping_and_Railings")
    garden.build("Forecourt_Garden_and_Reflecting_Pools")
    canopy.build("Waterfront_Canopy_and_Kiosks")


def build_outdoor_theatre():
    seats, stage, sail = Batch(), Batch(), Batch()
    x, y = 62, -92

    def arc(r):
        return [(x+r*math.sin(t)+.10*r, y+1.09*r*math.cos(t))
                for t in [(-.99+j*2.0/12) for j in range(13)]]

    for i in range(7):
        outer, inner = arc(21-i*1.7), arc(19.3-i*1.7)
        z = .57+(6-i)*.36
        for j in range(len(outer)-1):
            p, q = outer[j], outer[j+1]
            r, s = inner[j], inner[j+1]
            seats.face([(*r,z),(*s,z),(*q,z),(*p,z)],"concrete")
            band(seats,r,s,max(.34,z-.36),z,"stone")
        for j in (0,-1):
            band(seats,outer[j],inner[j],.34,z,"wall")
    stage.prism(ellipse(x,y-2,17,8,24,.13),.34,1.25,"stone","trim")
    stage.prism(ellipse(x,y-6,14,3,24,.16),.35,3.42,"wall","stone")
    for xoff in (-12,12):
        stage.beam((x+xoff,y-6,1.22),(x+xoff,y-5.5,8.3),.50,"chrome",sides=6)

    def canopy(u,v):
        return (x+u*(16-3*v),y-9+15*v+1.2*u*u+1.1*u,
                5.3+2.5*(1-u*u)+4.2*v-.65*v*v+1.25*u*v)

    for i in range(16):
        u, q = i/8-1,(i+1)/8-1
        for j in range(5):
            v,w = j/5,(j+1)/5
            sail.face([canopy(u,v),canopy(q,v),canopy(q,w),canopy(u,w)],"paint")
        for eave in (0,1):
            p,r = Vector(canopy(u,eave)),Vector(canopy(q,eave))
            ribbon(sail,p+Vector((0,0,.06)),r+Vector((0,0,.06)),.18,"chrome")
    for u in (-.92,.92):
        p = canopy(u,.88)
        sail.beam((p[0]-u*2.1,p[1]-5.9,1.3),p,.32,"chrome",sides=6)
    seats.build("DBS_Outdoor_Theatre_Tiered_Seating")
    stage.build("DBS_Outdoor_Theatre_Stage")
    sail.build("DBS_Outdoor_Theatre_Swept_Canopy")


def build_base():
    hall_foyers()
    build_mall()
    build_concourse()
    build_terrace()
    build_outdoor_theatre()


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    MAT.clear()
    make_materials()


VIEWS = {
    "bay": (0,-1,.17),
    "bridge": (-.95,-1,.63),
    "waterfront": (1,-.7,.49),
    "north": (-.72,1,.46),
    "east": (1,.75,.32),
    "plan": (0,0,1),
}


def render_glbs(label, paths, names=VIEWS):
    clear_scene()
    for path in paths:
        bpy.ops.import_scene.gltf(filepath=str(path))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_x = 780
    scene.render.resolution_y = 490
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"

    coordinates = [obj.matrix_world @ v.co for obj in scene.objects if obj.type=="MESH"
                   for v in obj.data.vertices]
    bounds = [(min(v[i] for v in coordinates),max(v[i] for v in coordinates)) for i in range(3)]
    target = Vector(tuple((a+b)/2 for a,b in bounds))
    radius = max((p-target).length for p in coordinates)
    world = bpy.data.worlds.new("Daylight")
    world.node_tree.nodes["Background"].inputs[0].default_value = (.57,.67,.82,1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .52
    scene.world = world
    sun = bpy.data.lights.new("Sun","SUN")
    sun.energy = 2.7
    sun.angle = math.radians(6)
    sun.color = (1,.925,.81)
    sunlight = bpy.data.objects.new("Sun",sun)
    scene.collection.objects.link(sunlight)
    sunlight.rotation_euler = Vector((.45,.59,-.62)).to_track_quat("-Z","Y").to_euler()
    data = bpy.data.cameras.new("Review")
    data.type = "ORTHO"
    data.clip_end = 2000
    camera = bpy.data.objects.new("Review",data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    path = REVIEW / label
    path.mkdir(parents=True,exist_ok=True)
    for name in names:
        direction = Vector(VIEWS[name]).normalized()
        rotation = direction.to_track_quat("Z","Y")
        right, up = rotation @ Vector((1,0,0)), rotation @ Vector((0,1,0))
        if name=="plan":
            right,up = Vector((1,0,0)),Vector((0,1,0))
            rotation = Quaternion((1,0,0,0))
        horizontal = [(p-target).dot(right) for p in coordinates]
        vertical = [(p-target).dot(up) for p in coordinates]
        width = max(horizontal)-min(horizontal)
        height = max(vertical)-min(vertical)
        data.ortho_scale = 1.17*max(width, height*780/490)
        aim = target+right*((max(horizontal)+min(horizontal))/2)+up*((max(vertical)+min(vertical))/2)
        camera.location = aim+direction*(radius*3+42)
        camera.rotation_euler = rotation.to_euler()
        scene.render.filepath = str(path / f"{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    if bpy.app.version[:3] != (5,1,2):
        raise RuntimeError(f"Blender 5.1.2 required, found {bpy.app.version_string}")
    xy = [world((*p,0)) for p in PLAZA]
    SITE_CENTER.x += (min(p[0] for p in xy)+max(p[0] for p in xy))/2
    SITE_CENTER.y += (min(p[1] for p in xy)+max(p[1] for p in xy))/2

    arguments = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    mode = arguments[0] if arguments else "all"
    paths = {key: ROOT / f"esplanade_{key}.glb" for key in ("domes","base")}
    model_names = arguments[1:] or list(paths)
    builders = {"domes": (build_domes, 18000), "base": (build_base, 9000)}
    if mode in {"export", "all"}:
        for key in model_names:
            build, budget = builders[key]
            clear_scene()
            build()
            count = 0
            for obj in bpy.context.scene.objects:
                obj.data.calc_loop_triangles()
                count += len(obj.data.loop_triangles)
                print(f"  {obj.name}: {len(obj.data.loop_triangles)}",flush=True)
            print(f"{key}: {count} triangles",flush=True)
            if count>budget:
                raise RuntimeError(f"{key} exceeds triangle budget: {count}")
            bpy.ops.export_scene.gltf(filepath=str(paths[key]),export_format="GLB",
                                      export_yup=True,export_cameras=False,export_lights=False,
                                      export_animations=False,export_skins=False,
                                      export_texcoords=False,export_tangents=False)
    if mode in {"render","all"}:
        for key in model_names:
            render_glbs(key,[paths[key]])
        render_glbs("assembled",list(paths.values()),("bay","bridge"))


if __name__ == "__main__":
    main()
