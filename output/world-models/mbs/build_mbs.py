"""Generate Marina Bay Sands in metres with Blender 5.1.2."""
import math
import random
import sys
from array import array
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PALETTE = {
    "paint": (.66, .69, .70, .20, .43),
    "glass": (.20, .33, .39, .26, .21),
    "window": (.24, .35, .41, .19, .29),
    "wall": (.47, .46, .43, .08, .53),
    "roof": (.43, .48, .49, .42, .36),
    "concrete": (.44, .43, .39, .02, .68),
    "metal": (.42, .48, .51, .67, .29),
    "chrome": (.62, .70, .74, .78, .19),
    "trim": (.75, .77, .75, .35, .39),
    "stone": (.52, .46, .38, .02, .63),
    "water": (.021, .205, .24, .20, .22),
    "leaf": (.115, .24, .064, .0, .8),
    "trunk": (.23, .14, .079, .0, .78),
    "light": (.88, .82, .60, .10, .36),
    "lamp_emissive": (.86, .64, .32, .03, .35),
    "rubber": (.055, .065, .070, .01, .79),
    "plate": (.27, .29, .30, .42, .43),
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2


def materials():
    for name, (r, g, b, metallic, roughness) in PALETTE.items():
        material = bpy.data.materials.new(name)
        material.diffuse_color = (r, g, b, 1)
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = material.diffuse_color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if name == "lamp_emissive":
            bsdf.inputs["Emission Color"].default_value = material.diffuse_color
            bsdf.inputs["Emission Strength"].default_value = .4


class Part:
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.materials = []
        self.face_materials = []
        self.uvs = []

    def add(self, vertices, faces, material, uvs=None):
        start = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(start + i for i in face) for face in faces)
        if material not in self.materials:
            self.materials.append(material)
        self.face_materials.extend([self.materials.index(material)] * len(faces))
        self.uvs.extend(uvs if uvs is not None else [None] * len(faces))

    def face(self, points, material, uv=None):
        self.add(points, [tuple(range(len(points)))], material, [uv])

    def prism(self, footprint, low, high, material, top_material=None):
        count = len(footprint)
        signed = sum(x * footprint[(i+1) % count][1] -
                     y * footprint[(i+1) % count][0]
                     for i, (x, y) in enumerate(footprint))
        if signed < 0:
            footprint = footprint[::-1]
        vertices = [(x, y, z) for z in (low, high) for x, y in footprint]
        faces = [tuple(reversed(range(count)))]
        for j in range(count):
            k = (j + 1) % count
            faces.append((j, k, k + count, j + count))
        self.add(vertices, faces, material)
        self.face(vertices[count:], top_material or material)

    def box(self, x, y, z, dx, dy, dz, material):
        self.prism([(x-dx/2, y-dy/2), (x+dx/2, y-dy/2),
                    (x+dx/2, y+dy/2), (x-dx/2, y+dy/2)], z, z+dz, material)

    def beam(self, start, end, width, material, sides=4, end_width=None):
        a, b = Vector(start), Vector(end)
        axis = (b-a).normalized()
        reference = Vector((0, 0, 1)) if abs(axis.z) < .9 else Vector((1, 0, 0))
        right = axis.cross(reference).normalized()
        up = axis.cross(right)
        vertices = []
        for center, diam in ((a, width), (b, end_width or width)):
            for i in range(sides):
                angle = 2*math.pi*(i+.5)/sides
                vertices.append(tuple(center+diam/2*(right*math.cos(angle)+up*math.sin(angle))))
        faces = [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
        for i in range(sides):
            j = (i+1) % sides
            faces.append((i, j, j+sides, i+sides))
        self.add(vertices, faces, material)

    def finish(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        for name in self.materials:
            mesh.materials.append(bpy.data.materials[name])
        layer = mesh.uv_layers.new(name="Facade") if any(self.uvs) else None
        for poly, mat, uv in zip(mesh.polygons, self.face_materials, self.uvs):
            poly.material_index = mat
            if uv is not None:
                for index, coords in zip(poly.loop_indices, uv):
                    layer.data[index].uv = coords
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        return obj


def lerp(a, b, t):
    return a+(b-a)*t


def smoothstep(t):
    t = min(1, max(0, t))
    return t*t*(3-2*t)


def oval(x, y, rx, ry, sides=16):
    return [(x+rx*math.cos(2*math.pi*i/sides), y+ry*math.sin(2*math.pi*i/sides))
            for i in range(sides)]


def tree(part, x, y, z, height, radius, seed, palm=False, lobes=2):
    phase = seed*1.83
    part.beam((x, y, z), (x+.12*radius, y, z+height*.75), .20*radius, "trunk", 5)
    if palm:
        for i in range(7):
            angle = phase + i*2*math.pi/7
            def point(along, cross, h):
                return (x+radius*(along*math.cos(angle)-cross*math.sin(angle)),
                        y+radius*(along*math.sin(angle)+cross*math.cos(angle)), z+height*h)
            part.face([point(0,0,.74), point(.52,-.20,.95),
                       point(1.35,0,.67), point(.54,.20,.95)], "leaf")
            part.face([point(0,0,.74), point(.54,.20,.95),
                       point(1.35,0,.67), point(.52,-.20,.95)], "leaf")
    else:
        for lobe in range(lobes):
            a = phase + lobe*math.pi
            cx, cy = x+radius*.30*math.cos(a), y+radius*.30*math.sin(a)
            points = [(cx,cy,z+height*(.96+.08*lobe)), (cx,cy,z+height*.48)]
            points += [(cx+radius*.78*math.cos(a+i*math.pi/3),
                        cy+radius*.78*math.sin(a+i*math.pi/3),z+height*(.73+.025*(i%2)))
                       for i in range(6)]
            faces = [(0,2+i,2+(i+1)%6) for i in range(6)]
            faces += [(1,2+(i+1)%6,2+i) for i in range(6)]
            part.add(points, faces, "leaf")


def facade_atlas():
    size = 1024
    columns, floors = 26, 55
    rng = random.Random(7341)
    shades = [[rng.uniform(-.045, .045) for _ in range(columns)] for _ in range(floors)]
    pixels = array("f")
    for iy in range(size):
        floor = (iy+.5)*floors/size
        row = int(floor)
        v = floor-row
        for ix in range(size):
            bay = (ix+.5)*columns/size
            col = int(bay)
            u = bay-col
            delta = shades[row][col]
            if v < .085:
                rgb = (.67, .71, .72)
            elif v < .16:
                rgb = (.34, .40, .43)
            elif u < .12:
                rgb = (.62, .67, .68) if u < .069 else (.34, .40, .43)
            elif .465 < u < .50:
                rgb = (.44, .50, .52)
            else:
                curtain = (u > .66 and delta > .009)*.103
                reflected = .036*math.sin(col*.86-row*.36)+.018*math.cos(col*1.42+row*.24)
                rgb = (.33+delta+curtain+reflected, .45+delta+curtain+reflected,
                       .50+delta+curtain+reflected)
            pixels.extend(rgb)
            pixels.append(1)
    image = bpy.data.images.new("Curtain wall", width=size, height=size, alpha=False)
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(ROOT / ".curtain-wall.jpg")
    image.file_format = "JPEG"
    image.save()
    image = bpy.data.images.load(image.filepath_raw, check_existing=False)
    image.pack()
    material = bpy.data.materials["window"]
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.extension = "EXTEND"
    material.node_tree.links.new(texture.outputs["Color"],
                                 material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])


def tower(index, mid, width, splay, merge, bow):
    levels = sorted(set([0, 9, 21, 35, 50, 65, 81, 103, 142, 170, 193, merge]))
    divisions = 10

    def point(z, u, garden, back):
        t = z/193
        x = mid + (u-.5)*(width - (6 if garden else 3)*t)
        x += (4.8 if garden else -4.1) * (1-t)**2 + (u-.5)*(2.1 if back else -1.4)
        y = bow + 2.6*(2*u-1)**2 + 3.4*(u-.5)
        if garden:
            spread = splay*(1-min(z/merge, 1))**1.26
            y += 16.2 + spread - (12.6 if not back else 0)
        else:
            y += (-13.8 if not back else 4.8) + (0.5 if back else 3.6)*(1-t)**2
        return x, y, z

    for garden in (False, True):
        wing = Part(f"Tower_{index:02d}_{'Garden' if garden else 'Bay'}_Wing")
        for back in (False, True):
            for low, high in zip(levels, levels[1:]):
                for i in range(divisions):
                    u0, u1 = i/divisions, (i+1)/divisions
                    face = [point(low,u0,garden,back), point(low,u1,garden,back),
                            point(high,u1,garden,back), point(high,u0,garden,back)]
                    uv = [(u0,low/193),(u1,low/193),(u1,high/193),(u0,high/193)]
                    if (index + garden + back) % 2:
                        uv = [(1-u,v) for u,v in uv]
                    if back:
                        face.reverse()
                        uv.reverse()
                    wing.face(face,"window",uv)
        for u in (0, 1):
            for low, high in zip(levels, levels[1:]):
                for v0, v1, mat in [(0,.24,"trim"),(.24,.37,"wall"),(.37,.66,"glass"),(.66,1,"trim")]:
                    def jamb(z,v):
                        a, b = point(z,u,garden,False), point(z,u,garden,True)
                        return tuple(lerp(i,j,v) for i,j in zip(a,b))
                    faces = [jamb(low,v0),jamb(low,v1),jamb(high,v1),jamb(high,v0)]
                    wing.face(faces if u == 1 else faces[::-1],mat)
        for z in (0,193):
            for i in range(divisions):
                u0,u1 = i/divisions,(i+1)/divisions
                face = [point(z,u0,garden,False),point(z,u1,garden,False),
                        point(z,u1,garden,True),point(z,u0,garden,True)]
                wing.face(face if z else face[::-1],"wall")
        wing.finish()

    fins = Part(f"Tower_{index:02d}_Curtain_Wall_Glass_Fins")
    for i in range(12):
        u = (i+.5)/12

        def profile(z):
            drift = (u-.5)*.018*(1-z/193)
            x,y,_ = point(z,u+drift,False,False)
            projection = 1.04 - .55*math.exp(-((z-105)/38)**2)
            return (x,y+.05,z),(x,y-projection,z)

        for bottom,high in zip(levels,levels[1:]):
            inner_low,tip_low=profile(max(bottom,4.25))
            inner_high,tip_high=profile(high)
            fins.face([inner_low,tip_low,tip_high,inner_high],"glass")
            x0,y0,z0=tip_low
            x1,y1,z1=tip_high
            fins.face([(x0-.048,y0,z0),(x0+.048,y0,z0),
                       (x1+.048,y1,z1),(x1-.048,y1,z1)],"metal")
    fins.finish()

    atrium = Part(f"Tower_{index:02d}_Atrium_and_Terraces")
    for u in (0, 1):
        for low, high in zip([0,9,19,31,45,60],[9,19,31,45,60,merge*.91]):
            a,b=point(low,u,False,True),point(low,u,True,False)
            c,d=point(high,u,True,False),point(high,u,False,True)
            if b[1]-a[1] < 1:
                continue
            for i in range(7):
                s,t=i/7,(i+1)/7
                def blend(p,q,r):
                    return tuple(lerp(h,j,r) for h,j in zip(p,q))
                quad=[blend(a,b,s),blend(a,b,t),blend(d,c,t),blend(d,c,s)]
                atrium.face(quad if u else quad[::-1],"glass")
                p0,p1=quad[0],quad[3]
                atrium.face([p0,(p0[0],p0[1]+.31,p0[2]),
                             (p1[0],p1[1]+.31,p1[2]),p1] if u else
                            [p1,(p1[0],p1[1]+.31,p1[2]),
                             (p0[0],p0[1]+.31,p0[2]),p0],"metal")
    for n in range(3,23):
        z = n*3.51
        depth = lerp(3.5,1.1,n/23)
        for i in range(6):
            u0,u1 = lerp(.025,.975,i/6),lerp(.025,.975,(i+1)/6)
            a,b=point(z,u0,True,True),point(z,u1,True,True)
            c,d=(b[0],b[1]+depth,z),(a[0],a[1]+depth,z)
            atrium.face([a,b,c,d],"leaf" if (i+n)%5 else "stone")
            atrium.face([d,c,(c[0],c[1],z-.37),(d[0],d[1],z-.37)],"trim")
            atrium.face([(d[0],d[1],z+.63),(c[0],c[1],z+.63),c,d],"glass")
    atrium.finish()


def skypark():
    stations = [
        (-170,-1.6,.55,1.15),(-169,-1.6,4.2,1.40),(-166,-1.4,7.9,2.25),
        (-161,-1.1,11.3,3.2),(-154,-.7,14.3,4.45),(-144,-.1,16.9,5.55),
        (-131,.45,18.5,6.15),(-114,.9,19,6.55),(-96,1.1,18.8,6.55),
        (-74,.85,18.0,5.5),(-51,.5,17.1,5.15),(-28,.28,16.45,5.4),
        (-5,.15,16.25,5.3),(19,.0,16.0,5.05),(43,-.25,16.2,5.15),
        (66,-.15,16.35,5.0),(91,.20,16.3,5.05),(113,.8,16.4,5.35),
        (137,1.5,16.1,5.1),(151,1.9,15.6,4.8),(160,2.1,14.3,4.2),
        (165,2.3,11.5,3.3),(168,2.55,8.4,2.4),(169.4,2.7,4.65,1.65),
        (170,2.8,1.0,1.2),
    ]
    profile = [(-1,0),(-1,-.18),(-.982,-.34),(-.92,-.56),(-.75,-.80),
               (-.43,-.95),(0,-1),(.43,-.95),(.75,-.8),(.92,-.56),
               (.982,-.34),(1,-.18),(1,0)]
    hull = Part("SkyPark_Silver_Hull")
    vertices = [(x,c+w*u,199.6+d*v) for x,c,w,d in stations for u,v in profile]
    n = len(profile)
    for i in range(len(stations)-1):
        for j in range(n-1):
            a,b=i*n+j,(i+1)*n+j
            material = "trim" if j in (0,n-2) else ("roof" if j in (4,5,6,7) else "paint")
            hull.add([vertices[k] for k in (a,a+1,b+1,b)], [(0,1,2,3)], material)
    hull.face(vertices[:n][::-1], "paint")
    hull.face(vertices[-n:], "paint")
    hull.finish()

    surface=Part("SkyPark_Deck_and_Guardrails")
    outline = [(x,c-w) for x,c,w,d in stations]+[(x,c+w) for x,c,w,d in stations[::-1]]
    surface.prism(outline,199.57,200,"stone")
    for i, (a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
        x,y=a
        for z, dz, mat in [(200,.94,"glass"),(200.94,.12,"trim")]:
            surface.face([(x,y,z),(b[0],b[1],z),(b[0],b[1],z+dz),(x,y,z+dz)],mat)
        if i%2 == 0:
            surface.beam((x,y,199.96),(x,y,201.1),.21,"metal")
    surface.finish()

    bearings=Part("SkyPark_Tower_Bearings")
    for x,w,y in [(-70,62,.2),(30,62,0),(128,59,1.1)]:
        bearings.prism([(x-w/2,y-12),(x+w/2,y-12),(x+w/2-2,y+13),(x-w/2+2,y+13)],
                       192.88,194.75,"metal")
        for dx in (-.36,-.18,.18,.36):
            for dy in (-8,8):
                bearings.beam((x+w*dx,y+dy*.7,192.9),(x+w*(dx+.05),y+dy,195.7),1.0,"trim")
    bearings.finish()

    pool=Part("SkyPark_150m_Infinity_Pool")
    pool_points=[(-88,-14.9),(-85,-15.7),(-24,-14.9),(24,-14.8),(59,-14.9),(62,-14.1),
                 (62,-6.2),(58,-5.75),(26,-5.8),(-21,-5.95),(-84,-6.7),(-88,-7.6)]
    pool_points=[(x+52,y) for x,y in pool_points]
    pool.prism(pool_points,200.03,200.56,"trim")
    water=[(lerp(x,39,.006),lerp(y,-10.5,.12)) for x,y in pool_points]
    pool.prism(water,200.56,200.61,"water")
    for x,y in [(-62,-6.75),(-9,-6.07),(36,-5.99)]:
        pool.box(x+52,y-.57,200.61,.7,1.22,.12,"trim")
    pool.finish()

    garden=Part("SkyPark_Gardens")
    rng=random.Random(5141)
    for left,right in [(-127,-100),(-88,-35),(-27,32),(38,72),(84,123),(128,152)]:
        beds=[(left,8),(left+3,6.65),(right-2,7.25),(right,8.5),
              (right-1.5,12.65),(left+3,13.0),(left,11.8)]
        garden.prism(beds,200.015,200.31,"stone","leaf")
    for i,x in enumerate([-137,-121,-98,-80,-64,-46,-26,-6,14,34,55,72,88,101,115,133,150]):
        y = 10.4 if i%3 else 8.25
        garden.prism(oval(x,y,7.3 if i%3 else 5.2,3.7,10),200,200.52,"stone","leaf")
        garden.prism(oval(x+4.3,y+.9,2.5,1.4,6),200.51,201.12,"leaf")
        tree(garden,x,y,200.52,rng.uniform(4.0,6.3),rng.uniform(1.5,2.65),i,i%4==2)
        if i%3:
            tree(garden,x-3.3,y+.7,200.50,rng.uniform(3,4.4),1.5,i+32,lobes=1)
    for i,x in enumerate(range(-31,114,6)):
        garden.box(x,-2.8,200,.95,2.2,.25,"trim")
        if i%4==1:
            tree(garden,x,-.45,200,3.1,1.15,i+90,True)
    garden.finish()

    leisure=Part("SkyPark_Observation_Deck_and_Restaurants")
    leisure.prism([(-168,-3.6),(-167,-5.4),(-161,-9),(-151,-11.7),
                   (-143,-11.8),(-139,-8.9),(-139,7),(-145,10.9),
                   (-155,9.4),(-165,5.1),(-168,1.6)],200,200.08,"stone","plate")
    for x,y,w,h in [(-112,2,15,6.4),(-91,5,11,8.7),(139,3,14,9.6)]:
        leisure.box(x,y,200,w,9,h,"paint")
        leisure.box(x,y-4.57,200.8,w*.86,.15,min(3,h*.58),"glass")
        leisure.box(x,y,200+h,w+.6,9.6,.27,"trim")
    for x,y in [(-130,1),(-123,9),(78,3),(92,4),(157,3)]:
        leisure.prism(oval(x,y,4.5,3.2,14),202.9,203.43,"paint")
        for p,q in [(-2,-1.4),(2,1.4),(-2,1.4),(2,-1.4)]:
            leisure.beam((x+p,y+q,200),(x+p,y+q,203),.24,"metal")
    leisure.finish()


def make_towers():
    facade_atlas()
    tower(1,128,66,41.2,106,1.5)
    tower(2,30,65,21.2,100,.2)
    tower(3,-70,66.5,11.2,90,.4)
    lobby=Part("Hotel_Link_Atria")
    for x,z,w in [(-20,24,39),(79,25.5,39)]:
        lobby.box(x,2,0,w,24,z,"glass")
        lobby.box(x,2,z,w,25,1.2,"roof")
        for i in range(1,11):
            xx=x+w*(i/11-.5)
            for y in (-10.1,14.1):
                lobby.face([(xx-.16,y,0),(xx+.16,y,0),(xx+.16,y,z),(xx-.16,y,z)]
                           [::1 if y<0 else -1],"trim")
        for floor in (4.1,8.2,12.3,16.4,20.5):
            lobby.box(x,2,floor,w+.2,24.3,.23,"metal")
    lobby.finish()
    skypark()


def podium_shell(name, x0, x1, center, depth, base, crown, slices):
    # Each roof is a skewed barrel with standing seams and a clear waterfront clerestory.
    body=Part(name)
    rib=Part(name+"_Seams")

    def station(u,v):
        x = lerp(x0,x1,u) + (v-.5)*7 + 4*math.sin(v*math.pi)*(.6-u)
        y = center+(v-.5)*depth+5*math.sin(math.pi*u)
        ridge = .39 if crown < 30 else .44
        if v <= ridge:
            arch = .33 + .67*(v/ridge)**1.24
        else:
            # Long silver roof sheets roll away from the denser bay-side ridge.
            arch = .17 + .83*math.cos(math.pi*.5*(v-ridge)/(1-ridge))
        z = base+crown*arch*(.83+.17*math.sin(math.pi*u))
        return x,y,z

    cols, rows=slices, 10
    for i in range(cols):
        u0,u1=i/cols,(i+1)/cols
        for j in range(rows):
            a,b=j/rows,(j+1)/rows
            body.face([station(u0,a),station(u1,a),station(u1,b),station(u0,b)],
                      "trim" if j>=4 else "roof")
        for v in (0,1):
            a,b=station(u0,v),station(u1,v)
            floor=4.4 if v==0 else 2.8
            for factor0, factor1, mat in [(0,.13,"concrete"),(.13,.75,"glass"),(.75,.80,"metal"),(.80,1,"window")]:
                def wall(p,t):
                    return (*p[:2],lerp(floor,p[2],t))
                quad=[wall(a,factor0),wall(b,factor0),wall(b,factor1),wall(a,factor1)]
                body.face(quad if v==0 else quad[::-1],mat)
            rib.face([a,(a[0]+.29,a[1],a[2]),(a[0]+.29,a[1],floor),(*a[:2],floor)]
                     [:: -1 if v==0 else 1],"trim")
        for j in range(rows):
            p,q=station(u0,j/rows),station(u0,(j+1)/rows)
            width=.27 if j<4 else .91
            rib.face([(p[0]-width,p[1],p[2]+.15),(p[0]+width,p[1],p[2]+.15),
                      (q[0]+width,q[1],q[2]+.15),(q[0]-width,q[1],q[2]+.15)],"trim")
    for u in (0,1):
        for j in range(rows):
            p,q=station(u,j/rows),station(u,(j+1)/rows)
            body.face([(*p[:2],1.55),(*q[:2],1.55),q,p][::1 if u else -1],
                      "glass" if j<5 else "wall")
            rib.face([(p[0]+(.11 if u else -.11),p[1]-.20,p[2]),
                      (p[0]+(.11 if u else -.11),p[1]+.20,p[2]),
                      (p[0]+(.11 if u else -.11),p[1]+.20,2),
                      (p[0]+(.11 if u else -.11),p[1]-.20,2)]
                     [:: -1 if u else 1],"metal")
    body.finish()
    rib.finish()


def shoppes_canopy():
    glass=Part("The_Shoppes_Curved_Glass_Shell")
    frames=Part("The_Shoppes_Steel_Arches_and_Masts")
    sections=51
    across=6

    def point(u,v):
        x=lerp(-189,278,u)+(v-.5)*(8*math.cos(math.pi*u)+4)
        y=-112+28*v+15*(2*u-1)**2 - 13*math.exp(-((u-.67)/.15)**2)
        z=13.0+8.25*math.sin(math.pi*(v*.89+.05)) + 5.7*math.exp(-((u-.58)/.055)**2)
        z -= 2.3*math.exp(-(u/.05)**2)
        return x,y,z

    for i in range(sections):
        u0,u1=i/sections,(i+1)/sections
        for j in range(across):
            v0,v1=j/across,(j+1)/across
            face=[point(u0,v0),point(u1,v0),point(u1,v1),point(u0,v1)]
            glass.face(face,"glass" if j in (0,1,3,4,5) else "window")
            p,q=face[0],face[3]
            width=.47 if i%4==0 else .22
            frames.face([(p[0]-width,p[1],p[2]+.10),(p[0]+width,p[1],p[2]+.1),
                         (q[0]+width,q[1],q[2]+.1),(q[0]-width,q[1],q[2]+.1)],"trim")
            p,q=face[:2]
            frames.face([(p[0],p[1]-.16,p[2]+.11),(q[0],q[1]-.16,q[2]+.11),
                         (q[0],q[1]+.16,q[2]+.11),(p[0],p[1]+.16,p[2]+.11)],"metal")
        a,b=point(u0,0),point(u1,0)
        landing = .505 < u0 < .66
        sill = 4.55 if landing else 3.4
        lintel = 8.1 if landing else 6.85
        pane = "window" if i%7 else "glass"
        glass.face([(*a[:2],lintel),(*b[:2],lintel),b,a],pane)
        glass.face([(*a[:2],lintel-.30),(*b[:2],lintel-.30),
                    (*b[:2],lintel),(*a[:2],lintel)],"trim")
        ax,bx=a[0],b[0]
        ay,by=a[1]+.62,b[1]+.62
        glass.face([(ax,ay,sill),(bx,by,sill),(bx,by,lintel-.28),(ax,ay,lintel-.28)],
                   "glass" if landing else "window")
        if landing:
            frames.face([(ax-.14,ay-.02,sill),(ax+.14,ay-.02,sill),
                         (ax+.14,ay-.02,lintel),(ax-.14,ay-.02,lintel)],"trim")
        if i%3==0:
            frames.beam((*a[:2],1.9),a,.50,"trim")
        if i%5==0:
            m=point(u0,.89)
            top=(m[0],m[1]+1,m[2]+7.6)
            frames.beam((m[0],m[1]+1,2.1),top,.60,"trim",5)
            for u,v in [(u0,.17),(min(1,u0+.028),.91),(max(0,u0-.028),.92)]:
                frames.beam(top,point(u,v),.22,"metal",3)
    glass.finish()
    frames.finish()


def waterfront():
    ground=Part("Bayfront_Promenade_and_Podium_Base")
    land=[(-197,-56),(-194,-97),(-188,-112),(-172,-124),(-149,-128),(-119,-129),
          (-88,-137),(-46,-142),(-12,-147),(20,-148),(49,-146),(76,-144),
          (104,-142),(143,-137),(187,-130),(212,-122),(246,-115),(279,-110),
          (290,-99),(290,-22),(10,-22),(-38,-20),(-38,-5),(-104,-5),
          (-104,-22),(-172,-23)]
    ground.prism(land,0,1.7,"concrete","stone")
    rim=[(-194,-106),(-188,-112),(-172,-124),(-149,-128),(-119,-129),(-88,-137),
         (-46,-142),(-12,-147),(20,-148),(49,-146),(76,-144),(104,-142),(143,-137),
         (187,-130),(212,-122),(246,-115),(279,-110),(290,-99)]
    for i,(a,b) in enumerate(zip(rim,rim[1:])):
        xa,ya=a
        xb,yb=b
        ground.face([(xa,ya-.05,.28),(xb,yb-.05,.28),(xb,yb-.05,1.11),(xa,ya-.05,1.11)],"wall")
        ground.face([(xa,ya,1.72),(xb,yb,1.72),(xb,yb+3.1,1.72),(xa,ya+3.1,1.72)],"plate")
        if i not in (8,9,10,11):
            ground.beam((xa,ya+.6,2.75),(xb,yb+.6,2.75),.13,"metal",3)
            length=math.hypot(xb-xa,yb-ya)
            count=max(1,round(length/7))
            for j in range(count):
                t=j/count
                x,y=lerp(xa,xb,t),lerp(ya,yb,t)+.6
                ground.beam((x,y,1.69),(x,y,2.76),.16,"metal",3)
    ground.finish()

    retail=Part("Retail_Stone_Platform_and_Glazed_Frontage")
    for x0,x1,bay in [(-184,-52,-91),(-52,45,-97),(115,280,-95)]:
        zone=[(x0,bay+5),(x0+7,bay),(x1-6,bay-5),(x1,bay-2),
              (x1,-41),(x0,-41)]
        retail.prism(zone,1.72,5.08,"concrete","stone")
        retail.prism([(x,y+1.5 if y < -50 else y) for x,y in zone],5.08,11.2,"glass")
        for i in range(10):
            t=(i+.48)/10
            x=lerp(x0+7,x1-6,t)
            y=lerp(bay,bay-5,t)+1.32
            retail.face([(x-.27,y,5.08),(x+.27,y,5.08),(x+.27,y,11.08),(x-.27,y,11.08)],"trim")
    retail.finish()

    plaza=Part("Event_Plaza_Stepped_Terraces")
    for i in range(13):
        t=i/12
        xp=lerp(51,47,t)
        xq=lerp(126,131,t)
        y=lerp(-147.8,-124.7,t)
        footprint=[(xp,y+7.5),(xp+7,y+3.0),(xp+15,y+.52),
                   (xp+27,y-.65),(xp+43,y-.42),(xq-14,y+.4),(xq-6,y+2.7),
                   (xq,y+6.3),(xq-2,-98),(xp+3,-98)]
        z=1.70+i*.232
        if i==0:
            # The first landing forms a projecting, rounded amphitheatre edge.
            plaza.prism(footprint,0,1.73,"concrete","stone")
        else:
            plaza.prism(footprint,z-.232,z,"stone" if i%3 else "wall")
    for i in range(1,9):
        x=48+i*9
        plaza.face([(x,-122,4.492),(x+.10,-122,4.492),
                    (x+.10,-98.3,4.492),(x,-98.3,4.492)],"trim")
    plaza.finish()

    trees=Part("Waterfront_Planting_and_Promenade_Lights")
    rng=random.Random(281)
    for i,x in enumerate(range(-173,273,17)):
        if 44 < x < 128:
            continue
        y=-119-13*math.exp(-((x-18)/100)**2)+.000095*(x+15)**2
        trees.prism(oval(x,y,3.25,2.35,8),1.71,2.12,"wall","leaf")
        tree(trees,x,y,2.12,rng.uniform(4.7,7.7),rng.uniform(2.2,3.35),i,i%5==2,lobes=1)
        if i%2:
            trees.beam((x+5,y-2.1,1.73),(x+5,y-2.1,5.35),.17,"metal")
            trees.box(x+5,y-2.6,5.18,.28,1.07,.19,"lamp_emissive")
    trees.finish()


def crystal_pavilion():
    building=Part("North_Crystal_Pavilion")
    frame=Part("North_Crystal_Pavilion_Diagrid")
    x,y=-18,-164
    ring=[(-18,2),(-15,-11),(-4,-17),(9,-15),(18,-6),(17,6),(8,12),(-7,11)]
    footprint=[(x+.88*u,y+.88*v) for u,v in ring]
    building.prism(footprint,0,1.8,"concrete")
    ridges=[(-18,1,7),(-16,-10,10),(-4,-18,5.7),(10,-15,7.0),
            (19,-6,11.2),(17,7,8.2),(10,12,14),(-7,11,9.7)]
    bottom=[(a,b,1.8) for a,b in footprint]
    roof=[(x+a,y+b,z) for a,b,z in ridges]
    crest=[(x-6.4,y+8.9,14.9),(x+6.3,y-10.2,12.05)]
    for i in range(len(roof)):
        top=crest[1 if i<4 else 0]
        j=(i+1)%len(roof)
        building.face([bottom[i],bottom[j],roof[j]],"glass" if i%3 else "window")
        building.face([bottom[i],roof[j],roof[i]],"window" if i%3 else "glass")
        building.face([roof[i],roof[j],top],"glass" if i in (0,2,3,5,7) else "metal")
        frame.beam(roof[i],roof[j],.25,"trim")
        frame.beam(roof[i],top,.24,"trim")
        frame.beam(bottom[i],roof[i],.3,"trim")
        frame.beam(bottom[i],roof[j],.25,"metal")
        for k in range(1,6):
            t=k/6
            def blend(p,q,u):
                return tuple(lerp(a,b,u) for a,b in zip(p,q))
            frame.beam(blend(bottom[i],bottom[j],t),blend(roof[i],roof[j],t),.126,"metal",3)
            a,b=blend(roof[i],top,t),blend(roof[j],top,t)
            frame.beam(a,b,.13,"trim",3)
    building.face([roof[0],crest[1],crest[0]],"glass")
    building.face([roof[4],crest[0],crest[1]],"metal")
    frame.beam(*crest,.29,"trim")
    building.finish()
    frame.finish()

    bridge=Part("Crystal_Pavilion_Boardwalk")
    bridge.prism([(-26,-155),(-16,-154),(-16,-142),(-26,-143)],1.22,1.78,"stone")
    for xx in (-26,-16):
        bridge.beam((xx,-154,2.85),(xx,-143,2.85),.19,"metal")
        for yy in (-153,-150,-147,-144):
            bridge.beam((xx,yy,1.76),(xx,yy,2.85),.17,"metal")
    bridge.finish()


def porte_cochere():
    arrival=Part("Bayfront_Avenue_Porte_Cochere")
    glazing=Part("Bayfront_Avenue_Glazed_Entrance")
    x=-70
    # Clear span keeps the three curbside arrival lanes open.
    arrival.prism([(x-31,-36),(x+32,-36),(x+30,-10),(x-33,-10)],1.71,1.84,"rubber")
    for y in (-32,-25,-18):
        for i in range(8):
            arrival.box(x-30+i*7.4,y,1.85,3.5,.16,.028,"trim")
    for i in range(13):
        xa=x-30+i*4.6
        xb=xa+4.6
        def roof_point(xx,v):
            angle=(xx-x+30)/(13*4.6)
            return (xx-(v-.5)*2.4,lerp(-36,-9,v),8.3+2.7*math.sin(math.pi*v*.91)+.6*math.sin(angle*math.pi))
        for j in range(6):
            p,q,r,s=roof_point(xa,j/6),roof_point(xb,j/6),roof_point(xb,(j+1)/6),roof_point(xa,(j+1)/6)
            arrival.face([p,q,r,s],"glass" if i%4!=0 else "roof")
            arrival.face([(p[0]-.2,p[1],p[2]+.10),(p[0]+.2,p[1],p[2]+.10),
                          (s[0]+.2,s[1],s[2]+.10),(s[0]-.2,s[1],s[2]+.10)],"metal")
        if i%2==0:
            for v in (.10,.84):
                q=roof_point(xa,v)
                arrival.beam((q[0]+.6,q[1],1.7),q,.83,"paint",6)
    glazing.prism([(x-31,-11),(x+29,-11),(x+27,-5),(x-33,-5)],1.72,8.0,"glass")
    for i in range(20):
        xx=x-30+i*2.97
        glazing.face([(xx-.115,-11.08,1.74),(xx+.115,-11.08,1.74),
                      (xx+.115,-11.08,8.02),(xx-.115,-11.08,8.02)],"metal")
        if i%4 in (1,2):
            glazing.box(xx+.7,-11.12,1.74,1.24,.12,3.12,"window")
    glazing.box(x-1,-11.2,4.89,60,.26,.25,"trim")
    arrival.finish()
    glazing.finish()


def make_podium():
    waterfront()
    podium_shell("Sands_Theatres_Barrel_Roof",-181,-62,-60,67,11,25.2,12)
    podium_shell("Casino_Barrel_Roof",-48,67,-60,75,12,29.1,13)
    podium_shell("South_Shoppes_Expo_Barrel_Roof",85,274,-57,86,14,36.2,18)
    shoppes_canopy()
    crystal_pavilion()
    porte_cochere()


def center_ground():
    objects = list(bpy.context.scene.objects)
    footprint = [v.co for obj in objects for v in obj.data.vertices if abs(v.co.z)<.00001]
    origin = Vector(((min(v.x for v in footprint)+max(v.x for v in footprint))/2,
                     (min(v.y for v in footprint)+max(v.y for v in footprint))/2,0))
    for obj in objects:
        for vertex in obj.data.vertices:
            vertex.co -= origin
    print(f"SITE_ORIGIN {tuple(origin)}", flush=True)


def export(stem, builder):
    reset()
    materials()
    builder()
    center_ground()
    bpy.ops.export_scene.gltf(filepath=str(ROOT/f"{stem}.glb"), export_format="GLB",
                              export_yup=True, export_cameras=False, export_lights=False,
                              export_animations=False, export_skins=False, export_extras=False,
                              export_image_format="AUTO")
    (ROOT/".curtain-wall.jpg").unlink(missing_ok=True)


if __name__ == "__main__":
    assert bpy.app.version == (5, 1, 2), bpy.app.version_string
    builders={"mbs_towers": make_towers, "mbs_podium": make_podium}
    stems=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else builders
    for stem in stems:
        export(stem, builders[stem])
