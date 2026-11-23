"""Build deterministic Kit B meshes with Blender's Z up and -Y as the front."""
import argparse
from math import cos, pi, sin, tau
from pathlib import Path
import random
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent

# sRGB hex values are converted to linear for Principled BSDF and glTF.
COLORS = {
    'wall': ('E2D8C7', .78, 0), 'window': ('345D70', .29, .26),
    'roof': ('766C61', .82, 0), 'concrete': ('AAADA8', .83, 0),
    'trim': ('E9E5D7', .68, 0), 'metal': ('75939F', .36, .5),
    'paint': ('F1EDE0', .56, 0), 'leaf': ('588150', .86, 0),
    'trunk': ('796858', .94, 0), 'light': ('D46F4D', .49, 0),
}


def material(name, override):
    hex_color, roughness, metallic = COLORS[name]
    hex_color = override.get(name, hex_color)
    rgb = [int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    rgb = [v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*rgb, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return mat


class Geometry:
    def __init__(self):
        self.points = []
        self.faces = []
        self.materials = []
        self.smooth = []

    def add(self, vertices, faces, mat, smooth=False):
        offset = len(self.points)
        self.points.extend(vertices)
        self.faces.extend(tuple(offset + i for i in f) for f in faces)
        self.materials.extend([mat] * len(faces))
        self.smooth.extend([smooth] * len(faces))

    def quad(self, corners, mat):
        self.add(corners, [(0, 1, 2, 3)], mat)

    def rings(self, loops, mat, smooth=False, cap=True):
        sides = len(loops[0])
        faces = []
        for level in range(len(loops) - 1):
            a = level * sides
            b = a + sides
            for i in range(sides):
                j = (i + 1) % sides
                faces.append((a+i, a+j, b+j, b+i))
        if cap:
            faces.extend([tuple(reversed(range(sides))),
                          tuple(range((len(loops)-1)*sides, len(loops)*sides))])
        self.add([p for loop in loops for p in loop], faces, mat, smooth)
        if cap:
            self.smooth[-2:] = [False, False]

    def prism(self, outline, bottom, top, mat):
        self.rings([[(x, y, z) for x, y in outline] for z in (bottom, top)], mat)

    def box(self, x, y, w, d, z0, z1, mat, cut=0):
        self.prism(outline(x, y, w, d, cut), z0, z1, mat)

    def cylinder(self, x, y, z0, z1, r, mat, n=10):
        self.rings([[(x+r*cos(tau*i/n), y+r*sin(tau*i/n), z)
                     for i in range(n)] for z in (z0, z1)], mat, True)

    def tube(self, path, sides, mat, vertical_base=False):
        loops = []
        for i, (x, y, z, radius) in enumerate(path):
            tangent = Vector(path[min(i+1, len(path)-1)][:3]) - Vector(path[max(i-1, 0)][:3])
            u = Vector((0, 1, 0)).cross(tangent).normalized()
            v = tangent.normalized().cross(u)
            if i == 0 and vertical_base:
                u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
            loops.append([Vector((x, y, z)) + radius*(u*cos(tau*j/sides)+v*sin(tau*j/sides))
                          for j in range(sides)])
        self.rings(loops, mat, True)

    def ellipsoid(self, center, scale, mat, sides=10, bands=5, seed=0, noise=.12, lobes=0, stagger=True):
        rng = random.Random(seed)
        x, y, z = center
        rx, ry, rz = scale
        vertices = [(x, y, z-rz)]
        for level in range(1, bands):
            angle = -pi/2 + pi*level/bands
            for i in range(sides):
                azimuth = tau*(i + ((level % 2)*.5 if stagger else 0))/sides
                puff = 1 + rng.uniform(-noise, noise)
                puff += lobes*(.68*cos(5*azimuth + .8*sin(2*angle)) + .32*sin(3*azimuth-4*angle))
                vertices.append((x + rx*cos(angle)*cos(azimuth)*puff,
                                 y + ry*cos(angle)*sin(azimuth)*puff,
                                 z + rz*sin(angle)*puff))
        vertices.append((x, y, z+rz))
        faces = []
        for i in range(sides):
            j = (i+1) % sides
            faces.append((0, 1+j, 1+i))
            for level in range(bands-2):
                base = 1 + level*sides
                faces.extend([(base+i, base+j, base+j+sides),
                              (base+i, base+j+sides, base+i+sides)])
            start = 1 + (bands-2)*sides
            faces.append((start+i, start+j, len(vertices)-1))
        self.add(vertices, faces, mat, True)

    def object(self, name, palette, pivot=(0, 0, 0)):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([Vector(p)-Vector(pivot) for p in self.points], [], self.faces)
        unique = list(dict.fromkeys(self.materials))
        for key in unique:
            mesh.materials.append(palette.setdefault(key, bpy.data.materials.get(key))
                                  or material(key, palette['overrides']))
            palette[key] = mesh.materials[-1]
        for face, key, smooth in zip(mesh.polygons, self.materials, self.smooth):
            face.material_index = unique.index(key)
            face.use_smooth = smooth
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        # Open façade inserts keep their authored winding after closed shells are corrected.
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = pivot
        return obj


def outline(x, y, w, d, cut=0):
    l, r, f, b = x-w/2, x+w/2, y-d/2, y+d/2
    if cut == 0:
        return [(l, f), (r, f), (r, b), (l, b)]
    return [(l+cut, f), (r-cut, f), (r, f+cut), (r, b-cut),
            (r-cut, b), (l+cut, b), (l, b-cut), (l, f+cut)]


def face_panel(g, side, center, plane, width, bottom, top, mat='window'):
    a, b = center-width/2, center+width/2
    if side == 'front':
        corners = [(a, plane, bottom), (b, plane, bottom), (b, plane, top), (a, plane, top)]
    elif side == 'back':
        corners = [(b, plane, bottom), (a, plane, bottom), (a, plane, top), (b, plane, top)]
    elif side == 'left':
        corners = [(plane, b, bottom), (plane, a, bottom), (plane, a, top), (plane, b, top)]
    else:
        corners = [(plane, a, bottom), (plane, b, bottom), (plane, b, top), (plane, a, top)]
    g.quad(corners, mat)


def facade_band(g, x, y, w, d, z0, z1, mat='window', cut=.4):
    loop = outline(x, y, w, d, cut)
    g.rings([[(a, b, z) for a, b in loop] for z in (z0, z1)], mat, cap=False)


def raintree(g):
    g.tube([(0,0,0,1.02),(-.15,0,1.15,.73),(-.36,.15,4.3,.61),
            (-.6,.3,6.2,.48),(-1.4,.55,8.1,.26),(-2.8,.65,10,.13)], 9, 'trunk', True)
    g.tube([(-.35,.15,4.2,.56),(.65,-.35,6.1,.46),(2.6,-.35,8.25,.31),
            (4.5,-.8,10.5,.13)], 8, 'trunk')
    g.tube([(-.6,.3,6.15,.39),(-2.6,-.55,7.9,.29),(-4.8,-.85,10.3,.12)], 7, 'trunk')
    g.tube([(-.6,.5,6.9,.33),(-.25,2.12,8.75,.23),(.9,3.6,10.5,.11)], 7, 'trunk')
    for i, (center, scale) in enumerate([
        ((-.3,.0,11.7),(5.2,4.7,2.3)), ((-4.3,-.9,10.9),(3.7,3.5,1.95)),
        ((4.3,-.5,11.05),(3.7,3.4,1.9)), ((1,3.55,10.95),(4.0,2.8,1.83)),
        ((-2.7,2.8,11.0),(3.75,2.8,1.7)), ((1.5,-3.15,11.0),(3.9,2.9,1.62)),
        ((-2.35,-3.25,10.75),(3.45,2.5,1.55)),
    ]):
        g.ellipsoid(center, scale, 'leaf', 11, 5, 11+i, .085)


def palm(g):
    g.tube([(0,0,0,.33),(.01,.0,.36,.30),(.06,.02,2.7,.225),
            (.078,.022,3.58,.216),(.083,.025,3.65,.226),(.085,.025,3.71,.213),
            (.116,.075,5.68,.19),(.12,.078,5.75,.199),(.124,.08,5.81,.188),
            (.183,.095,7.73,.177),(.186,.096,7.80,.187),(.19,.098,7.86,.175),
            (.25,.11,9.3,.17),(.27,.10,10.14,.23)], 9, 'trunk', True)
    g.tube([(.27,.10,9.72,.245),(.27,.09,10.48,.32),(.27,.09,11.02,.19)], 8, 'leaf')
    for i in range(9):
        angle = tau*i/9 + .15*sin(i*2.1)
        across = Vector((-sin(angle), cos(angle), 0))
        out = Vector((cos(angle), sin(angle), 0))
        run = 2.65 + .34*cos(i*2.4)
        lift = .35*sin(i*2.7)
        sections = [(0,10.46,.055),(.13,11.02+lift,.18),(.25,11.30+lift,.31),
                    (.42,11.43+lift,.40),(.56,11.29+lift,.33),(.69,10.98+lift,.31),
                    (.83,10.48+lift,.22),(.93,9.93+lift,.116),(1,9.30+lift,.012)]
        vertices = []
        for j, (distance, z, width) in enumerate(sections):
            c = Vector((.27,.09,z)) + out*(distance*run) + across*(.065*j)
            for offset in (-1, 0, 1):
                p = c + across*(width*offset)
                p.z -= abs(offset)*width*.44
                vertices.append(p)
        faces = []
        for j in range(len(sections)-1):
            a = 3*j
            faces.extend([(a,a+3,a+4,a+1),(a+1,a+4,a+5,a+2)])
        g.add(vertices, faces, 'leaf', True)


def street_tree(g):
    g.tube([(0,0,0,.29),(.02,.01,.5,.24),(.17,.04,3.0,.17),(.02,.04,4.8,.10)], 8, 'trunk', True)
    g.tube([(.15,.05,2.65,.15),(-.55,-.12,3.65,.105),(-1.12,-.25,4.8,.05)], 6, 'trunk')
    g.tube([(.15,.05,3.0,.15),(.76,.31,3.94,.09),(1.24,.66,5.14,.06)], 6, 'trunk')
    g.ellipsoid((-.09,.10,5.61),(2.51,2.41,2.39), 'leaf', 16, 9, 16, .014, .078, stagger=False)


def hedge(g):
    # Identical end profiles let instances meet at a 4 m repeat interval.
    profile = [(-.30,0),(.30,0),(.4,.15),(.4,.72),(.29,.94),
               (.12,1),(-.12,1),(-.31,.92),(-.4,.71),(-.4,.15)]
    loops = []
    for i, (y, lift, width) in enumerate([(-2,0,1),(-1.32,-.025,.98),(-.52,0,1),
                                          (.35,-.026,.99),(1.15,-.006,.98),(2,0,1)]):
        loops.append([(x*width, y, z+lift*min(1, z*3)) for x, z in profile])
    g.rings(loops, 'leaf', True)


def hdb(g):
    g.box(0,0,69.2,13.5,0,.3,'concrete',.55)
    g.box(0,0,69.3,12.66,3.5,36.65,'wall',.4)
    g.box(0,0,70,14,3.43,3.84,'concrete',.5)
    for y in (-4.9,0,4.9):
        positions = (-32,-21,-10,0,10,21,32) if y else (-30,-10,10,30)
        for x in positions:
            g.box(x,y,1.2,1.05,.25,3.49,'concrete')
    for x in (-22,21):
        g.box(x,1.85,3.35,3.1,.24,3.57,'wall')
    for floor in range(11):
        base = 3.88 + 2.95*floor
        for side, sign in [('front',-1),('back',1)]:
            for bay in range(14):
                x = (bay-6.5)*4.78
                face_panel(g,side,x,sign*6.347,3.0,base+.74,base+2.29)
                if bay % 3 != 1:
                    if side == 'front':
                        g.quad([(x-1.71,-6.97,base+.67),(x+1.71,-6.97,base+.67),
                                (x+1.71,-6.30,base+.67),(x-1.71,-6.30,base+.67)],'concrete')
                    face_panel(g,side,x,sign*(6.969 if side=='front' else 6.385),3.34,
                               base+.67,base+(1.36 if side=='front' else 1.15),'trim')
        for side, sign in [('left',-1),('right',1)]:
            for y in (-3.78,3.78):
                face_panel(g,side,y,sign*34.665,2.65,base+.79,base+2.18)
    for side, sign in [('front',-1),('back',1)]:
        for x in (-33.8,-19.1,0,19.1,33.8):
            face_panel(g,side,x,sign*6.36,.54,3.86,36.38,'trim')
    g.box(0,0,70,14,36.28,36.63,'roof',.5)
    for side in (-1,1):
        g.box(0,side*6.72,69.25,.48,36.57,37.42,'wall')
        g.box(side*34.62,0,.59,13.68,36.57,37.42,'wall')
    g.box(6.8,.8,8.5,5.4,36.59,37.92,'concrete',.28)
    g.box(6.8,.8,8.9,5.8,37.92,38,'roof',.28)


def glass_tower(g):
    g.box(0,0,30,30,0,2,'concrete',2.4)
    g.box(0,0,27.98,27.98,2,110,'window',2.1)
    facade_band(g,0,0,28.4,28.4,2,8.4,'metal',2.12)
    for floor in range(1, 34):
        z = 7.05 + 3.02*floor
        facade_band(g,0,0,28.25,28.25,z,z+.36,'metal',2.12)
    for side in ('front','back','left','right'):
        sign = -1 if side in ('front','left') else 1
        for offset in (-10.8,-7.2,-3.6,0,3.6,7.2,10.8):
            face_panel(g,side,offset,sign*14.15,.202,8.45,109.85,'metal')
    g.box(0,0,28.65,28.65,109.75,111.25,'metal',2.3)
    g.box(0,0,23.2,23.2,111.25,118.7,'window',2.1)
    g.box(0,0,24.4,24.4,118.35,120,'metal',2.2)
    for side in ('front','back','left','right'):
        sign = -1 if side in ('front','left') else 1
        for pos in (-9,-6,-3,0,3,6,9):
            face_panel(g,side,pos,sign*11.69,.35,111.3,118.36,'metal')


def arch(g, x, y, width, bottom, spring, rise, trim=.15, fill='window'):
    inner = [(x-width/2,y,bottom), (x+width/2,y,bottom)]
    outer = [(x-width/2-trim,y-.015,bottom), (x+width/2+trim,y-.015,bottom)]
    for i in range(7):
        a = i*pi/6
        inner.append((x+width/2*cos(a),y,spring+rise*sin(a)))
        outer.append((x+(width/2+trim)*cos(a),y-.015,spring+(rise+trim)*sin(a)))
    if fill:
        g.add(inner, [range(len(inner))], fill)
    edges = [(i,i+1) for i in range(1,len(inner)-1)] + [(len(inner)-1,0)]
    g.add(outer+inner, [(a,b,len(inner)+b,len(inner)+a) for a,b in edges], 'trim')


def shophouse(g):
    centers = [-7.30,0,7.30]
    g.box(0,0,22,8,0,.19,'concrete',.08)
    for i,x in enumerate(centers):
        g.box(x,.94,7.26,5.20,.18,3.45,'wall')
        g.box(x,0,7.30,7.63,3.4,9.95,['wall','paint','concrete'][i])
        g.box(x,-3.48,7.32,.92,3.37,3.62,'trim')
        g.box(x,-3.79,7.27,.32,6.60,6.78,'trim')
        g.box(x,0,7.28,7.78,9.75,10.0,'trim')
        for dx in (-2.24,0,2.24):
            arch(g,x+dx,-3.827,1.58,7.16,8.53,.75)
            arch(g,x+dx,-3.829,1.54,4.03,5.31,.67)
            for bottom in (4.05,7.18):
                for sign in (-1,1):
                    face_panel(g,'front',x+dx+sign*.40,-3.849,.64,bottom,bottom+1.15,'metal')
                    for j in range(3):
                        face_panel(g,'front',x+dx+sign*.40,-3.851,.57,bottom+.21+j*.30,
                                   bottom+.24+j*.30,'window')
            face_panel(g,'front',x+dx,-1.671,1.6,.37,2.67,'window')
            face_panel(g,'back',x+dx,3.822,1.34,4.25,5.7,'window')
            face_panel(g,'back',x+dx,3.822,1.34,7.18,8.67,'window')
        for dx in (-3.35,3.35):
            face_panel(g,'front',x+dx,-3.845,.22,3.66,9.64,'trim')
        # The masonry above the arcade openings joins the beam and column capitals.
        supports = [-10.56,-3.65,3.65,10.56]
        left,right = supports[i:i+2]
        middle = (left+right)/2
        radius = (right-left)/2-.24
        arch(g,middle,-3.687,2*radius,.46,2.12,1.08,.098,fill=None)
        curve = [(middle+(radius+.065)*cos(j*pi/10),-3.674,2.12+1.136*sin(j*pi/10))
                 for j in range(11)]
        for a,b in zip(curve,curve[1:]):
            g.quad([b,a,(a[0],a[1],3.45),(b[0],b[1],3.45)], 'wall')
        for dx in (-1.48,1.48):
            face_panel(g,'back',x+dx,3.553,1.13,.41,2.41,'window')
        profile = [(-3.95,9.90),(3.95,9.90),(3.95,10.04),(2.02,10.87),(.15,11.85),
                   (0,11.92),(-.15,11.85),(-2.02,10.87),(-3.95,10.04)]
        g.rings([[(edge,y,z) for y,z in profile] for edge in (x-3.63,x+3.63)],'roof')
        for sign in (-1,1):
            for pos in (.95,1.76,2.52,3.27,3.8):
                z = 11.85-(pos-.15)*(.524 if pos < 2.02 else .452)
                if pos >= 2.02:
                    z = 10.87-(pos-2.02)*(.83/1.93)
                g.quad([(x-3.57,sign*(pos-.035),z+.018),(x+3.57,sign*(pos-.035),z+.018),
                        (x+3.57,sign*(pos+.032),z-.016),(x-3.57,sign*(pos+.032),z-.016)] if sign>0 else
                       [(x+3.57,sign*(pos-.035),z+.018),(x-3.57,sign*(pos-.035),z+.018),
                        (x-3.57,sign*(pos+.032),z-.016),(x+3.57,sign*(pos+.032),z-.016)],'light')
        g.box(x,0,7.26,.20,11.84,12,'roof',.05)
    for x in (-10.56,-3.65,3.65,10.56):
        g.box(x,-3.58,.60,.65,.16,.48,'trim',.08)
        g.box(x,-3.58,.42,.51,.47,3.39,'paint')
        g.box(x,-3.58,.62,.68,2.87,3.39,'trim',.08)


def condo(g):
    g.box(0,0,40,25,0,.55,'concrete',2)
    g.box(0,0,39.4,24.4,.55,5.7,'wall',1.8)
    g.box(0,0,39.8,24.8,5.38,6.4,'trim',1.9)
    facade_band(g,0,0,39.49,24.49,1.15,4.85,'window',1.8)
    for x in range(-15,16,5):
        g.box(x,-12.15,.86,.62,.55,5.55,'concrete')
    for x,y,top in [(-9,-2.9,55),(9,3,47)]:
        g.box(x,y,15.4,13.1,6.35,top-2.1,'wall',.8)
        g.box(x,y,15.6,13.3,top-2.1,top-1.35,'trim',.83)
        g.box(x+.8,y+.55,8.3,7.5,top-1.4,top,'roof',.65)
        for storey in range(round((top-9)/3.05)):
            z = 6.78+3.05*storey
            facade_band(g,x,y,15.47,13.17,z+.24,z+2.29,'window',.8)
            # Continuous slabs wrap the end of each tower on opposite corners.
            x_offset = -1.17 if x < 0 else 1.17
            if storey < 13 or x < 0:
                long_end = x + x_offset
                g.box(long_end,y-.39,13.2,13.65,z,z+.26,'trim')
                for side, sign in [('front',-1),('back',1)]:
                    face_panel(g,side,long_end,y+sign*6.68-.38,12.8,z+.24,z+.61,'metal')
        for side, sign in [('front',-1),('back',1)]:
            for offset in (-4.9,0,4.9):
                face_panel(g,side,x+offset,y+sign*6.605,.46,6.44,top-2.08,'wall')
    g.box(0,-10.65,12,1.6,3.94,4.2,'metal',.23)


def lowrise(g):
    g.box(0,0,30,12,0,.23,'concrete',.24)
    g.box(0,.235,29.7,11.47,.2,12.8,'wall',.21)
    g.box(0,.1,29.92,11.8,12.65,13.08,'roof',.28)
    for sign in (-1,1):
        g.box(0,.10+sign*5.73,29.45,.32,12.91,13.67,'wall')
        g.box(sign*14.73,.135,.4,11.73,12.91,13.67,'wall')
    for i in range(6):
        x = (i-2.5)*4.83
        face_panel(g,'front',x,-5.534,4.14,.35,3.71)
        g.box(x-2.34,-5.34,.31,.53,.24,4.0,'concrete')
        for z in (5.0,8.93):
            for offset in (-1.07,1.07):
                face_panel(g,'front',x+offset,-5.526,1.68,z,z+1.95)
                face_panel(g,'back',x+offset,5.999,1.68,z,z+1.95)
                face_panel(g,'front',x+offset,-5.531,.09,z,z+1.95,'trim')
    for z in (4.24,8.32,12.35):
        g.box(0,-5.43,29.66,.38,z,z+.21,'trim')
    g.rings([[(-14.87,y,z),(14.87,y,z),(14.87,y+.16,z+.075),(-14.87,y+.16,z+.075)]
             for y,z in [(-5.25,4.18),(-6,3.79)]],'metal')
    for side, sign in [('left',-1),('right',1)]:
        for z in (5,8.93):
            for y in (-2.8,.2,3.2):
                face_panel(g,side,y,sign*14.856,1.42,z,z+1.95)
    g.box(8,2,3.3,3.3,12.99,13.35,'concrete')
    g.cylinder(8,2,13.33,14.8,1.26,'metal',12)
    g.cylinder(8,2,14.8,15,1.11,'roof',12)


def mbs(g):
    g.box(0,0,276,90,0,4,'concrete',10)
    g.box(0,1.9,258,80,4,12,'wall',9)
    facade_band(g,0,1.9,258.2,80.2,5,10,'window',9.02)
    g.box(0,1.9,262,82,11.75,14.5,'concrete',9.5)
    g.box(0,-30,202,23.5,14.28,17.4,'wall',4.4)

    def tower_profile(level):
        t = level/190
        return -5 + 17*(1-t)**2 - 7*t, 47-21*t + 4*t*t

    for x in (-88,0,88):
        levels = [11,31,57,82,106,132,157,178,190]
        loops = []
        for z in levels:
            y, depth = tower_profile(z)
            loops.append([(a,b,z) for a,b in outline(x,y,56,depth,3.15)])
        g.rings(loops, 'window')
        for stage in range(len(levels)-1):
            z0,z1 = levels[stage:stage+2]
            y0,d0 = tower_profile(z0)
            y1,d1 = tower_profile(z1)
            for sign in (-1,1):
                for pos in (-25.4,-16.7,-.9,.9,16.7,25.4):
                    width = 1.55 if abs(pos)>23 else .72
                    g.quad([(x+pos+sign*width/2,y0+sign*(d0/2+.09),z0),
                            (x+pos-sign*width/2,y0+sign*(d0/2+.09),z0),
                            (x+pos-sign*width/2,y1+sign*(d1/2+.09),z1),
                            (x+pos+sign*width/2,y1+sign*(d1/2+.09),z1)], 'wall')
            for sign in (-1,1):
                for fraction in (-.24,.24):
                    px = x+sign*28.09
                    a = y0 + d0*fraction
                    b = y1 + d1*fraction
                    g.quad([(px,a-sign*.62,z0),(px,a+sign*.62,z0),
                            (px,b+sign*.62,z1),(px,b-sign*.62,z1)], 'wall')
        for level in range(15,187,5):
            # Interpolate the same loft breakpoints so the thin floor bands sit on its skin.
            j = next(j for j in range(len(levels)-1) if levels[j] <= level < levels[j+1])
            a,b = levels[j:j+2]
            ya,da = tower_profile(a)
            yb,db = tower_profile(b)
            f = (level-a)/(b-a)
            y,d = ya+(yb-ya)*f, da+(db-da)*f
            for sign in (-1,1):
                side = 'front' if sign < 0 else 'back'
                face_panel(g,side,x,y+sign*(d/2+.055),49.7,level,level+.27,'metal')

    hull = [(-144,-10),(-138,-23),(-122,-33),(-94,-37),(82,-37),(134,-34),
            (163,-29),(181,-21),(188,-13),(181,-5),(163,1),(134,7),
            (82,10),(-92,9),(-123,5),(-139,-1)]
    def hull_loop(scale_x, scale_y, z):
        return [(24+(x-24)*scale_x,-13+(y+13)*scale_y,z) for x,y in hull]
    g.rings([hull_loop(.88,.64,186.8),hull_loop(.98,.91,191.6),
             hull_loop(1,1,194.35)],'metal')
    g.rings([hull_loop(.991,.97,194.28),hull_loop(.985,.94,195.65)],'wall')
    g.box(-23,-25,131,7.4,195.63,195.9,'window',.5)
    for x in (-105,-68,10,61,111):
        g.box(x,-7,17,6.1,195.6,197.6,'concrete',1.2)
        g.box(x,-7,18.2,6.8,197.45,198.2,'metal',1.35)


def checkpoint(g):
    # Blender -Y maps to game +Z. The roads are open along that axis.
    g.box(0,0,39.94,15.8,6.35,7.08,'paint',1.55)
    g.box(0,0,39.65,15.55,7.08,7.38,'concrete',1.44)
    facade_band(g,0,0,40,15.85,6.53,6.98,'trim',1.55)
    facade_band(g,0,0,39.72,15.62,7.04,7.15,'metal',1.45)
    for x in (-16.8,-8.4,0,8.4,16.8):
        g.box(x,0,1.55,15.45,0,.23,'concrete',.28)
        for y in (-5.5,5.5):
            g.box(x,y,.69,.93,.21,6.39,'concrete',.10)
            g.box(x,y,1.02,1.24,5.94,6.42,'paint',.13)
    for index, x in enumerate((-16.8,-8.4,0,8.4),1):
        g.box(x,.4,1.52,3.15,.23,2.92,'paint',.19)
        facade_band(g,x,.4,1.54,3.17,1.30,2.54,'window',.19)
        facade_band(g,x,.4,1.57,3.20,.56,.74,'trim',.20)
        g.box(x,.4,1.66,3.32,2.87,3.03,'trim',.23)
        px,py,pz = x+.63,-2.83,1.08
        g.box(px,py,.27,.36,.21,pz+.08,'metal',.035)
        arm = Geometry()
        arm.box(px+3.38,py,6.9,.145,pz-.052,pz+.052,'paint')
        arm.box(px,py,.28,.25,pz-.117,pz+.117,'paint',.032)
        for step in range(5):
            xx = px+.64+step*1.29
            arm.box(xx,py,.43,.152,pz-.054,pz+.054,'light')
        yield f'barrier_{index}',arm,(px,py,pz)
    for x in (-12.6,-4.2,4.2,12.6):
        for y in (-7.2,7.2):
            g.box(x,y,1.32,.32,5.87,6.35,'metal',.065)
            face_panel(g,'front' if y<0 else 'back',x,y+(-.164 if y<0 else .164),.44,6.01,6.19,'light')


def southkey(g):
    g.box(0,0,198,112,0,1.1,'concrete',10)
    g.box(0,0,196,109,1.1,21.7,'wall',9.5)
    g.box(0,0,197.4,110.3,20.9,23.5,'trim',10)
    g.box(-6,-25.5,154,56,23.45,27,'concrete',6.2)
    for z0,z1 in [(3.5,5.7),(9.4,11.7),(15.95,18.42)]:
        facade_band(g,0,0,196.16,109.16,z0,z1,'metal',9.52)
    g.box(-13,-50.2,55,10,1.04,18.78,'window',2.7)
    g.box(-13,-50.28,56.7,10.72,7.4,8.53,'trim',2.7)
    g.box(-13,-50.28,57.2,10.84,18.6,20.24,'wall',2.7)
    for x in (-36,-29,-22,-15,-8,-1,6,13):
        face_panel(g,'front',x,-55.29,.5,1.09,18.55,'metal')
    for x in (-80,-67,-54,22,35,48,61,74,87):
        face_panel(g,'front',x,-54.67,5.6,3.88,17.82,'window')
    for x,y,w,d,h,style in [(-66,17,29,33,116,0),(-27,19,30,34,150,1),
                             (22,10,33,33,132,2),(63,-1,31,32,90,3)]:
        bottom = 23.36
        top = h-(4 if style != 2 else 11)
        g.box(x,y,w,d,bottom,top,'window',1.23)
        for i in range(int((top-bottom)/3.6)):
            z = bottom+1.64+i*3.6
            if z+.37 < top:
                facade_band(g,x,y,w+.08,d+.08,z,z+.37,'metal' if style in (1,2) else 'trim',1.24)
        for side in ('front','back','left','right'):
            sign = -1 if side in ('front','left') else 1
            axis,plane,radius = (x,y,d/2) if side in ('front','back') else (y,x,w/2)
            for unit in (-.34,-.12,.12,.34):
                face_panel(g,side,axis+unit*(w if side in ('front','back') else d),
                           plane+sign*(radius+.06),.72,bottom+.07,top-.10,'wall')
        if style == 0:
            g.box(x,y,w+.6,d+.6,top,top+.93,'trim',1.32)
            g.box(x,y,w-3,d-3,top+.9,h,'metal',1.32)
            for sign in (-1,1):
                side = 'front' if sign < 0 else 'back'
                for offset in (-10,-6,-2,2,6,10):
                    face_panel(g,side,x+offset,y+sign*((d-3)/2+.08),1.0,top+1,h-.24,'wall')
        elif style == 1:
            lower = [(a,b,top) for a,b in outline(x,y,w,d,1.23)]
            upper = [(a,b,h-3.35*(a-(x-1.65)+(w-1.4)/2)/(w-1.4))
                     for a,b in outline(x-1.65,y,w-1.4,d-2.4,1.23)]
            g.rings([lower,upper],'metal')
        elif style == 2:
            g.box(x-3,y,w-6.5,d,top,h-5,'wall',1.3)
            g.box(x-5,y+1,w-12,d-5,h-5,h,'window',1.25)
        else:
            g.box(x,y,w+1.25,d+1.25,top,h-2.33,'wall',1.65)
            g.box(x+4.2,y+3.1,w-15,d-15,h-2.33,h,'trim',1.23)
            g.box(x-8.4,y-5.8,7,10,h-2.33,h-.8,'metal',.64)


ASSETS = {
    'tree_raintree': (raintree, 900, {'leaf':'648456','trunk':'716353'}, {0:16, 2:14}),
    'tree_palm': (palm, 600, {'leaf':'638E46','trunk':'A59583'}, {2:12}),
    'tree_street': (street_tree, 400, {'leaf':'5B854F','trunk':'826A55'}, {0:5,1:5,2:8}),
    'shrub_hedge': (hedge, 120, {'leaf':'557C45'}, {}),
    'building_hdb': (hdb, 1800, {'wall':'DFD7C5','window':'4F6C73','trim':'D0A479'}, {}),
    'building_tower_glass': (glass_tower, 900, {'window':'3D758C','metal':'86A5AC'}, {}),
    'building_shophouse': (shophouse, 1800, {'wall':'DB9D87','paint':'F4E8CB','trim':'EDE6C9',
                                              'metal':'628984','roof':'9D573F','light':'B8785B'}, {}),
    'building_condo': (condo, 1600, {'wall':'D2C9B6','window':'467183','trim':'F4EBDD'}, {}),
    'building_lowrise': (lowrise, 900, {'wall':'DAB98A','metal':'5B8380','window':'494E50'}, {}),
    'landmark_mbs': (mbs, 3500, {'wall':'DEDAD0','window':'557B89','metal':'9EA9A8'}, {}),
    'landmark_checkpoint': (checkpoint, 2800, {'trim':'24689C','paint':'F1F1EA','light':'D03432'}, {}),
    'landmark_southkey': (southkey, 3000, {'wall':'C9BFAE','window':'4F7385','trim':'DED6C8'}, {}),
}


def build(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.unit_settings.system = 'METRIC'
    factory, max_triangles, overrides, targets = ASSETS[name]
    g = Geometry()
    extras = list(factory(g) or [])
    for axis,size in targets.items():
        values = [p[axis] for p in g.points]
        scale = size / (max(values)-min(values))
        g.points = [tuple(coordinate*scale if i==axis else coordinate for i,coordinate in enumerate(p))
                    for p in g.points]
    palette = {'overrides':overrides}
    objects = [g.object(name,palette)]
    for part,data,pivot in extras:
        objects.append(data.object(part,palette,pivot))
    counts = []
    for obj in objects:
        obj.data.calc_loop_triangles()
        counts.append(len(obj.data.loop_triangles))
    if sum(counts) > max_triangles:
        raise ValueError(f'{name}: {sum(counts)} triangles exceeds {max_triangles}')
    bpy.ops.export_scene.gltf(
        filepath=str(ROOT/f'{name}.glb'), export_format='GLB', export_yup=True,
        export_apply=True, export_texcoords=False, export_normals=True, export_tangents=False,
        export_animations=False, export_skins=False, export_cameras=False, export_lights=False,
    )
    print(f'BUILT {name}: {sum(counts)} triangles', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('models', nargs='*')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for name in args.models or ASSETS:
        build(name)
