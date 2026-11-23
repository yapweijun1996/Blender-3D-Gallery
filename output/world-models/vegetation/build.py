"""Procedural Blender 5.1.2 source for the Singapore street vegetation kit."""
import math
import random
from collections import defaultdict
from hashlib import sha256
from struct import pack
from zlib import crc32
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
TAU = math.tau
UP = Vector((0, 0, 1))
FRONT = Vector((0, -1, 0))  # Blender -Y becomes glTF +Z.

# GLB filenames, LOD0 triangle limits and target Blender XYZ dimensions in metres.
SPECS = {
    "rain_tree": (1800, (18, 15.2, 14)),
    "angsana": (1500, (12.8, 11.7, 15.5)),
    "tembusu": (1500, (10, 9.3, 15)),
    "royal_palm": (1100, (5, 4.8, 17)),
    "coconut_palm": (900, (6.3, 5.6, 12.5)),
    "bottle_palm": (700, (3.6, 3.3, 4.3)),
    "frangipani": (700, (4.5, 3.8, 4.2)),
    "bougainvillea": (600, (2.75, 2.1, 1.42)),
    "heliconia": (500, (1.65, 1.35, 1.8)),
    "ginger": (400, (1.4, 1.15, 1.64)),
    "hedge_2m": (150, (2, .72, .96)),
    "grass_tuft": (80, (.33, .31, .27)),
    "flower_bed": (400, (2, 1, .42)),
    "planter_box": (200, (1.55, .65, .68)),
    "tree_pit": (200, (1.6, 1.6, .09)),
}

GREEN = ("#2b4721", "#365a29", "#426333", "#4b7335", "#536f35", "#638443")
DARK = ("#203a23", "#233f28", "#2b4a2c", "#315432", "#3a5b34")
PALM = ("#295323", "#356b2b", "#477c30", "#528c3c", "#629740", "#739d43")
BARK = ("#51463a", "#625446", "#6d5c49", "#786a55", "#564d3e")
GREY = ("#858178", "#8b877e", "#928d83", "#989186", "#807c72")
SOIL = ("#534333", "#5b4837", "#624c39", "#473c30")
MAGENTA = ("#a61567", "#bb2476", "#c8247c", "#d03589", "#921353")


def rgb(hex_color):
    def linear(value):
        value /= 255
        return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
    return tuple(linear(int(hex_color[i:i + 2], 16)) for i in (1, 3, 5)) + (1,)


def radial(angle):
    return Vector((math.cos(angle), math.sin(angle), 0))


def pick(rng, colors):
    return rng.choice(colors)


class Geometry:
    def __init__(self):
        self.parts = defaultdict(lambda: ([], [], []))

    def add(self, part, material, vertices, faces, colors, smooth=False):
        points, polygons, attributes = self.parts[part]
        offset = len(points)
        points.extend(Vector(v) for v in vertices)
        polygons.extend(tuple(i + offset for i in face) for face in faces)
        if isinstance(colors, str):
            colors = [colors] * len(faces)
        attributes.extend((material, rgb(color), smooth) for color in colors)

    def count(self):
        return sum(len(face) - 2 for _, faces, _ in self.parts.values() for face in faces)

    def fit(self, size):
        points = [v for vertices, _, _ in self.parts.values() for v in vertices]
        low = [min(v[i] for v in points) for i in range(3)]
        high = [max(v[i] for v in points) for i in range(3)]
        # Preserve the planting centre. Asymmetric crowns and leaning trunks can overhang it.
        for v in points:
            for i in range(3):
                v[i] = (v[i] - (low[i] if i == 2 else 0)) * size[i] / (high[i] - low[i])

    def objects(self, lod):
        root = bpy.data.objects.new(lod, None)
        root["lod_level"] = int(lod[-1])
        bpy.context.scene.collection.objects.link(root)
        root.empty_display_size = .15
        for part, (vertices, faces, attributes) in self.parts.items():
            name = f"{lod}_{part}"
            mesh = bpy.data.meshes.new(name)
            mesh.from_pydata(vertices, [], faces)
            mesh.update()
            color_layer = mesh.color_attributes.new(name="Color", type="BYTE_COLOR", domain="CORNER")
            mesh.color_attributes.active_color = color_layer
            slots = {}
            for poly, (material, color, smooth) in zip(mesh.polygons, attributes, strict=True):
                if material not in slots:
                    slots[material] = len(mesh.materials)
                    mesh.materials.append(get_material(material))
                poly.material_index = slots[material]
                poly.use_smooth = smooth
                for loop in poly.loop_indices:
                    color_layer.data[loop].color = color
            obj = bpy.data.objects.new(name, mesh)
            obj.parent = root
            bpy.context.scene.collection.objects.link(obj)


def get_material(name):
    material = bpy.data.materials.get(name)
    if material:
        return material
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.use_backface_culling = False
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = {
        "leaf": .74, "trunk": .93, "metal": .73, "concrete": .91, "stone": .96,
    }[name]
    shader.inputs["Metallic"].default_value = .58 if name == "metal" else 0
    colors = material.node_tree.nodes.new("ShaderNodeVertexColor")
    colors.layer_name = "Color"
    material.node_tree.links.new(colors.outputs["Color"], shader.inputs["Base Color"])
    return material


def tube(g, rng, part, material, path, radii, sides, colors, irregular=.07, caps=True, phase=0):
    path = list(map(Vector, path))
    points = []
    bark = [rng.uniform(1 - irregular, 1 + irregular) for _ in range(sides)]
    for i, (p, radius) in enumerate(zip(path, radii, strict=True)):
        tangent = (path[min(i+1, len(path)-1)] - path[max(0, i-1)]).normalized()
        axis = Vector((1, 0, 0))
        if abs(tangent.dot(axis)) > .88:
            axis = Vector((0, 1, 0))
        x = (axis - tangent * tangent.dot(axis)).normalized()
        y = tangent.cross(x)
        # Extend the full root flare to grade, including the edges of slanted trunks.
        if i == 0 and p.z == 0:
            x, y = Vector((1, 0, 0)), Vector((0, 1, 0))
        for j in range(sides):
            a = TAU*j/sides + phase
            points.append(p + radius*bark[j]*(x*math.cos(a)+y*math.sin(a)))
    faces = []
    for i in range(len(path)-1):
        faces.extend((i*sides+j, i*sides+(j+1)%sides, (i+1)*sides+(j+1)%sides,
                      (i+1)*sides+j) for j in range(sides))
    if caps:
        faces += [tuple(reversed(range(sides))), tuple(range(len(points)-sides, len(points)))]
    shades = [pick(rng, colors) for _ in range(sides)]
    g.add(part, material, points, faces,
          [shades[i % sides] for i in range(len(faces))], smooth=True)


def blade(g, part, material, start, end, width, color, detail=2, roll=0, bend=0):
    """Folded, pointed solid card. Width is the full lamina width."""
    start, end = Vector(start), Vector(end)
    direction = (end-start).normalized()
    cross = direction.cross(UP)
    if cross.length < .01:
        cross = Vector((1, 0, 0))
    cross = cross.normalized()
    cross = cross*math.cos(roll) + direction.cross(cross)*math.sin(roll)
    mid = start.lerp(end, .44) + UP*bend
    a, b = mid-cross*width*.5, mid+cross*width*.5
    if detail == 1:
        g.add(part, material, [start, a, end], [(0, 1, 2)], color)
    elif detail == 2:
        g.add(part, material, [start, a, end, b], [(0, 1, 2), (0, 2, 3)], color)
    else:
        shoulder = start.lerp(end,.32) + UP*bend*.85
        taper = start.lerp(end,.74) + UP*bend*.75
        ridge = mid + direction.cross(cross)*width*.15
        outline = [start,shoulder-cross*width*.44,taper-cross*width*.32,
                   end,taper+cross*width*.32,shoulder+cross*width*.44,ridge]
        g.add(part,material,outline,[(j,(j+1)%6,6) for j in range(6)],color)


def patch(g, rng, part, center, radii, n, color, layered=False, smooth=False, ragged=False):
    """Foliage mass with a serrated outline and inset underside."""
    center = Vector(center)
    rx, ry, rz = radii
    phase = rng.random()*TAU
    count = 2*n-2 if ragged else n
    rim = []
    for i in range(count):
        a = TAU*i/count + phase
        taper = rng.uniform(.76,1.14)
        if ragged and i%2:
            taper *= rng.uniform(.68,.95)
        height = rz*rng.uniform(-.48,.4) if ragged else rz*rng.uniform(-.29,.15)
        rim.append(Vector((rx*math.cos(a)*taper,ry*math.sin(a)*taper,height)))
    top = Vector((rx*rng.uniform(-.19,.19),ry*rng.uniform(-.19,.19),rz))
    bottom = Vector((0,0,-rz*.67))
    if ragged:
        ridge_axis = radial(phase)
        top_a, top_b = top.copy(), top.copy()
        top_a.x += ridge_axis.x*rx*.22
        top_a.y += ridge_axis.y*ry*.22
        top_b.x -= ridge_axis.x*rx*.29
        top_b.y -= ridge_axis.y*ry*.29
        top_b.z *= rng.uniform(.53,.81)
        points = rim+[top_a,top_b,bottom]
        faces = []
        for j in range(count):
            k = (j+1)%count
            # Two raised centres form a crest, giving the clump a broad top.
            ridges = [count if rim[index].dot(ridge_axis) >= 0 else count+1 for index in (j,k)]
            faces.extend([(j,k,ridges[0]),(k,j,count+2)])
            if ridges[0] != ridges[1]:
                faces.append((ridges[0],k,ridges[1]))
        def tint(factor):
            channels = [min(255,round(int(color[i:i+2],16)*factor)) for i in (1,3,5)]
            return "#" + "".join(f"{channel:02x}" for channel in channels)
        colors = [tint(rng.uniform(.87,1.11)) for _ in faces]
    elif layered:
        ridge = [p*.61+Vector((top.x*.4,top.y*.4,rz*rng.uniform(.47,.82))) for p in rim]
        points = rim+ridge+[top,bottom]
        faces = []
        for j in range(n):
            k = (j+1)%n
            faces += [(j,k,n+k),(j,n+k,n+j),(n+j,n+k,2*n),(k,j,2*n+1)]
        colors = color
    else:
        points = rim+[top,bottom]
        faces = [(j,(j+1)%n,n) for j in range(n)]+[((j+1)%n,j,n+1) for j in range(n)]
        colors = color
    g.add(part,"leaf",[p+center for p in points],faces,colors,smooth=layered or smooth)
    return [p+center for p in rim], top+center


def petals(g, rng, part, center, radius, colors, count=5, direction=UP, detailed=True):
    center = Vector(center)
    direction = Vector(direction).normalized()
    x = direction.cross(Vector((0, 1, 0))).normalized()
    y = direction.cross(x)
    points, faces, shades = [center], [], []
    phase = rng.random()*TAU
    for i in range(count):
        angle = phase+TAU*i/count
        out = math.cos(angle)*x+math.sin(angle)*y
        side = direction.cross(out)
        index = len(points)
        points += [center+out*radius*.66-side*radius*.28,
                   center+out*radius+side*radius*.14+direction*radius*.21,
                   center+out*radius*.56+side*radius*.43+direction*radius*.1]
        faces += [(0,index,index+1)]
        if detailed:
            faces.append((0,index+1,index+2))
        shades += [colors[0]] + ([colors[-1]] if detailed else [])
    g.add(part, "leaf", points, faces, shades)


def tree(slug, g, rng, low):
    rain, angsana = slug == "rain_tree", slug == "angsana"
    layout = random.Random(rng.getrandbits(32))
    foliage = GREEN if rain else ("#2d4d20","#375a27","#42672d","#507239","#56783a") if angsana else DARK
    trunk_color = BARK if rain else ("#63594b","#726656","#7a6e5f","#5d5548") if angsana else (
        "#463e32","#5a4a3a","#65523f","#4f483a")
    if rain:
        trunk = [(0,0,0),(-.20,.09,.6),(-.28,.17,1.7),(-.05,.12,3.44),(.47,.24,5.35),(.65,.21,8.04),(.22,-.21,11.12)]
        widths = [1.1,.83,.65,.59,.41,.23,.042]
        branch_count, selected = 6, {0,1,2,4,5}
        cuffs, center_count = 5, 5
    else:
        trunk = [(0,0,0),(-.11,.06,.66),(-.08,.14,2.2),(.14,.24,4.45),(.29,.10,6.5),
                 (.1,.23,8.55),(-.24,.13,11.99)]
        widths = [.98,.69,.52,.44,.34,.24,.084] if angsana else [.93,.61,.48,.41,.34,.24,.1]
        branch_count, selected = (7,{0,2,4,6}) if angsana else (8,{0,1,3,5,7})
        cuffs, center_count = 3, 8 if angsana else 7
    trunk_path = [trunk[i] for i in (0,2,4,6)] if low else trunk
    trunk_radii = [widths[i] for i in (0,2,4,6)] if low else widths
    tube(g,rng,"trunk","trunk",trunk_path,trunk_radii,5 if low else 9,trunk_color,irregular=.1)
    if not low:
        for i in range(5):
            out = radial(TAU*i/5 + rng.uniform(-.23,.23))
            side = UP.cross(out)*rng.uniform(.15,.26)
            p = out*(1.39 if rain else 1.25)
            g.add("trunk","trunk",[p, out*.31-side, out*.3+side, out*.38+UP*rng.uniform(.87,1.5)],
                  [(0,1,3),(2,0,3),(1,2,3)], [trunk_color[0],trunk_color[1],trunk_color[-1]])
    for i in range(branch_count):
        a = TAU*i/branch_count+layout.uniform(-.28,.28)
        out, side = radial(a), radial(a+math.pi/2)
        if rain:
            start_z = (3.19,4.4,3.81,4.69,3.64,4.98)[i]
            reach = layout.uniform(5.95,7.55)
            height = (9.8,11.08,11.8,10.81,9.84,11.31)[i]
            elbow_r, elbow_z = layout.uniform(.40,.58), layout.uniform(.21,.38)
            root_r = (.64,.47,.56,.39,.52,.41)[i]
        elif angsana:
            start_z = (3.65,5.62,4.71,6.1,5.2,6.6,4.72)[i]
            reach, height = layout.uniform(3.65,5.12),layout.uniform(10.18,12.17)
            elbow_r, elbow_z = layout.uniform(.35,.5),layout.uniform(.41,.61)
            root_r = layout.uniform(.32,.48)
        else:
            start_z = 4.95+i*.64
            reach = 5.25-i*.29+layout.uniform(-.37,.37)
            height = 8.03+i*.64+layout.uniform(-.42,.43)
            elbow_r, elbow_z = layout.uniform(.42,.62),layout.uniform(.21,.64)
            root_r = layout.uniform(.29,.42)
        start = UP*start_z+Vector((.11,.12,0))+out*(.13 if rain else .095)
        end = UP*height+out*reach+side*layout.uniform(-.74,.74)
        elbow = UP*(start_z+(height-start_z)*elbow_z)+out*reach*elbow_r+side*layout.uniform(-.62,.62)
        shoulder = UP*(height- (.72 if rain else .39))+out*reach*.76+side*layout.uniform(-.47,.47)
        crown_centers = []
        for j in range(cuffs):
            v = j/(cuffs-1)
            step = layout.uniform(.67,1.25)*(-1 if j%2 else 1)
            if rain:
                p = end+side*step+out*((v-.69)*3.2)
                p.z += layout.uniform(-.65,.42)+(reach-math.hypot(p.x,p.y))*.46
                radii = (layout.uniform(1.74,2.55),layout.uniform(1.55,2.15),layout.uniform(.8,1.31))
            elif angsana:
                p = end + side*step+out*((v-.57)*3.35)
                p.z += layout.uniform(-.43,.37)-(p-end).dot(out)*.74
                radii = (layout.uniform(1.45,2.18),layout.uniform(1.32,1.98),layout.uniform(1.05,1.58))
            else:
                p = end + side*step*.7-out*(v*2.45-.22)
                p.z += layout.uniform(-.35,.48)+v*.65
                radii = (layout.uniform(1.48,1.98),layout.uniform(1.42,1.95),layout.uniform(.9,1.29))
            crown_centers.append((p,radii))
        if low:
            if i not in selected:
                continue
            tube(g,rng,"limbs","trunk",[start,elbow,end],[root_r,root_r*.63,.042],4,trunk_color,caps=False)
            inner, outer = crown_centers[0][0], crown_centers[-1][0]
            p = inner.lerp(outer,.21)
            q = inner.lerp(outer,.77)
            broad = (3.08,2.90,1.43) if rain else (2.32,2.20,1.67) if angsana else (2.35,2.29,1.58)
            patch(g,rng,"crown",p,broad,6,pick(rng,foliage),smooth=True)
            patch(g,rng,"crown",q,(broad[0]*.84,broad[1]*.89,broad[2]*.88),6,pick(rng,foliage),smooth=True)
            continue
        tube(g,rng,"limbs","trunk",[start,start.lerp(elbow,.78),elbow.lerp(shoulder,.24),shoulder,end],
             [root_r,root_r*.78,root_r*.62,root_r*.34,.038],5,trunk_color,caps=False,irregular=.10)
        for j,(p,radii) in enumerate(crown_centers):
            if j in ((0,2) if rain else (0,)):
                twig = p-UP*radii[2]*.49
                fork = elbow.lerp(shoulder,.52 if j==0 else .79)
                tube(g,rng,"limbs","trunk",[fork,fork.lerp(twig,.63)-UP*.35,twig],
                     [.21 if rain else .13,.089,.019],4,trunk_color,caps=False)
            rim,_ = patch(g,rng,"crown",p,radii,7 if rain else 6,pick(rng,foliage),True,ragged=True)
            for k in range(4 if rain or angsana else 3):
                v = rim[(j+k*2)%len(rim)]
                d = (v-p).normalized()
                for side_lean in (-1,1):
                    end_leaf = v+d*rng.uniform(.12,.36)+UP*rng.uniform(-.23,.14)+side*.22*side_lean
                    blade(g,"crown","leaf",v-d*.35,end_leaf,rng.uniform(.16,.28),
                          pick(rng,foliage),1,rng.uniform(-.8,.8),.018)
    for i in range(center_count):
        angle = i*2.39996+.38
        distance = (1.17 if rain else 1.03)*math.sqrt(i)
        z = (12.02 if rain else 13.54 if angsana else 12.89)-distance*(.32 if rain else .36)
        p = UP*(z+layout.uniform(-.56,.48))+radial(angle)*distance
        if not rain and not angsana:
            p += Vector((-.4,.69,0))
        if low and i >= (4 if rain else 4 if angsana else 3):
            continue
        width = 2.64 if low and rain else 2.36 if low else 2.09 if rain else 1.82
        patch(g,rng,"crown",p,(width,width*.88,1.29 if rain else 1.57),
              6 if low or not rain else 7,pick(rng,foliage),not low,smooth=low,ragged=not low)
    # Merge the inner canopy in the principal gaps between the branch fans.
    if rain:
        for x,y,z in ((3.21,3.11,10.83),(-3.42,3.04,11.29),(-3.52,-3.21,10.82),(3.34,-3.33,10.95)):
            patch(g,rng,"crown",(x,y,z),(2.37,2.09,1.02),6 if low else 7,
                  pick(rng,foliage[1:]),smooth=True)
    elif not angsana:
        patch(g,rng,"crown",(.92,.24,10.29),(2.12,1.95,1.12),6,
              pick(rng,foliage),layered=not low,smooth=low,ragged=not low)
        if not low:
            patch(g,rng,"crown",(-1.35,-.37,10.94),(1.87,1.68,1.25),6,
                  pick(rng,foliage),layered=True,ragged=True)


def palm(slug, g, rng, low):
    royal, coconut = slug == "royal_palm", slug == "coconut_palm"
    layout = random.Random(rng.getrandbits(32))
    if royal:
        profile = [(0,.33),(.25,.31),(2,.26),(5.2,.29),(7.4,.33),(10.2,.3),(13,.24),(14.5,.23)]
        crown = [(0,0,14.48),(.015,0,14.78),(.027,0,15.53),(.08,0,15.99)]
        cr = [.23,.25,.19,.13]
        n, length, leaflet_pairs = 13, 3.02, 13
    elif coconut:
        profile = [(0,.35),(.3,.27),(1.65,.19),(3.4,.169),(5.6,.155),(7.7,.149),(9.4,.17),(10.3,.19)]
        crown = [(1.47,-.66,10.15),(1.56,-.7,10.45),(1.65,-.74,10.65)]
        cr = [.19,.24,.16]
        n, length, leaflet_pairs = 11, 3.73, 11
    else:
        profile = [(0,.29),(.17,.34),(.46,.35),(.85,.32),(1.35,.26),(1.95,.19),(2.52,.13)]
        crown = [(0,0,2.5),(0,0,2.67),(.015,0,3.02),(.025,0,3.15)]
        cr = [.132,.149,.112,.083]
        n, length, leaflet_pairs = 6, 2.0, 17
    def center(z):
        if coconut:
            return Vector((1.59*(z/10.3)**1.56, -.69*(z/10.3)**1.8, z))
        return Vector((.02*z/profile[-1][0], .015*math.sin(z), z))
    trunk_color = GREY if not coconut else ("#7d7766", "#8a806c", "#968873", "#a0927e")
    trunk_profile = profile if not low else profile[::2]+([profile[-1]] if len(profile)%2 == 0 else [])
    tube(g,rng,"trunk","trunk",[center(z) for z,_ in trunk_profile],
         [r for _,r in trunk_profile],5 if low else 9,trunk_color,irregular=.028)
    if not low:
        scars = 13 if royal else 15 if coconut else 10
        for i in range(scars):
            z = profile[-1][0]*(.12+.847*i/(scars-1))
            (za,ra),(zb,rb) = next((a,b) for a,b in zip(profile,profile[1:]) if a[0] <= z <= b[0])
            radius = ra+(rb-ra)*(z-za)/(zb-za)
            # Short scar segments preserve the trunk profile and avoid painted bands.
            sides = 5 if royal else 6 if coconut else 7
            points = [center(z)+radial(j*TAU/sides)*radius*(1.06 if j%2 else 1.035)
                      +UP*(.011+radius*.028) for j in range(sides)]
            for j, p in enumerate(points):
                q = points[(j+1)%sides]
                mid = (p+q)*.5-UP*(.012 if royal else .022)
                if (i+j) % (3 if royal else 2) == 0:
                    g.add("trunk","trunk",[p,q,mid],[(0,1,2)],
                          "#746e63" if royal else "#6f6657")
    shaft_parts = [crown[0],crown[-1]] if low else crown
    shaft_r = [cr[0],cr[-1]] if low else cr
    tube(g,rng,"crownshaft","trunk",shaft_parts,shaft_r,5 if low else 8,
         ("#4e752d","#597e35","#648b38","#41652b") if not coconut else ("#665133","#74713d","#78633b"),
         irregular=.024)
    if coconut and not low:
        for i in range(3):
            out = radial(TAU*i/3)
            p = Vector(crown[1])+out*rng.uniform(.17,.31)-UP*rng.uniform(.14,.33)
            tube(g,rng,"fruit","leaf",[p-UP*.12,p,p+UP*.14],[.045,.10,.045],4,
                 ("#657638","#758244","#879448","#586732"),caps=False)
    for i in range(n):
        angle = TAU*i/n + layout.uniform(-.2,.2)
        out, side = radial(angle), radial(angle+math.pi/2)
        base = Vector(crown[-1]).lerp(Vector(crown[-2]), 0.45 + .44*math.cos(i*2.4))
        length_i = length*layout.uniform(.88,1.12)
        lift = layout.uniform(.66,1.23) if not coconut else layout.uniform(.64,1.12)
        drop = layout.uniform(.62,1.78) if royal else layout.uniform(1.21,2.46) if coconut else layout.uniform(.03,.52)
        if i in (2, 7, 11):
            lift += .72
            drop *= .56
            length_i *= .86
        def along(t):
            return base+out*length_i*t+side*length_i*.13*t*t*math.sin(i*1.6)+UP*(lift*math.sin(math.pi*t)-drop*t**2.5)
        shade = pick(rng,PALM[1:])
        if low:
            if i%2 and i != 7 and n > 6:
                continue
            for j in range(4):
                t, next_t = j*.25, (j+1)*.25
                p, q = along(t),along(next_t)
                w, w2 = .31*math.sin(math.pi*t)**.77, .31*math.sin(math.pi*next_t)**.77
                if j in (0,3):
                    tip = p if j == 0 else q
                    wide, spread = (q,w2) if j == 0 else (p,w)
                    g.add("fronds","leaf",[tip,wide+side*spread,wide,wide-side*spread],
                          [(0,1,2),(0,2,3)],shade)
                else:
                    g.add("fronds","leaf",[p+side*w,p-side*w,q-side*w2,q+side*w2],
                          [(0,1,2),(0,2,3)],shade)
                if j in (1,2):
                    for sign in (-1,1):
                        edge = p+side*sign*w
                        blade(g,"fronds","leaf",edge,q+side*sign*(w2+.13)-UP*.13,.15,shade,1)
            continue
        # Flat continuous rachis and individually silhouetted tapered pinnae.
        for j in range(6):
            t, t2 = j/6,(j+1)/6
            p,q = along(t),along(t2)
            w,w2 = (.026*(1-u)+.11*math.sin(math.pi*u)+.006 for u in (t,t2))
            g.add("fronds","leaf",[p-side*w,p+side*w,q+side*w2,q-side*w2],[(0,1,2,3)],
                  "#759447" if not coconut else "#7e8848")
        for j in range(leaflet_pairs):
            t = .13 + .85*j/(leaflet_pairs-1)
            spread = (.66 if royal else .76 if coconut else .57)*math.sin(math.pi*t)**.67+.05
            for sign in (-1,1):
                tt = min(.988,t + (.014 if sign == 1 else -.01))
                p = along(tt)
                q = p+side*(spread*sign)+out*(spread*rng.uniform(.63,1.04))
                q.z -= spread*rng.uniform(.29,.82) if coconut or royal else spread*rng.uniform(.13,.48)
                width = (.235 if royal else .269 if coconut else .151)*math.sin(math.pi*t)**.5+.023
                shade = pick(rng,PALM[1:] if royal else PALM)
                blade(g,"fronds","leaf",p,q,width,shade,2,sign*rng.uniform(.52,1.14),.037)
    spear_start = Vector(crown[-1]) - UP*.18
    blade(g,"fronds","leaf",spear_start,spear_start+UP*(1.16 if royal else .82)+radial(1.8)*.38,
          .11,"#799a47",2,.2)


def frangipani(g, rng, low):
    bark = ("#8d8270","#9a907f","#71695a","#938775")
    trunk = [(0,0,0),(.04,.02,.62),(-.09,.03,1.28)]
    tube(g,rng,"trunk","trunk",trunk[::2] if low else trunk,
         [.195,.12] if low else [.195,.149,.12],5 if low else 8,bark)
    layout = random.Random(7223)
    for i in range(5):
        a = TAU*i/5 + layout.uniform(-.22,.22)
        if low and i==2:
            continue
        out = radial(a)
        start = Vector((-.08,.03,1.03+rng.random()*.22))
        fork = start+out*rng.uniform(.54,.9)+UP*rng.uniform(.44,.8)
        tube(g,rng,"branches","trunk",[start,fork],[.094,.061],4 if low else 5,bark,caps=not low)
        for j in range(1 if low else 2):
            branch_out = radial(a+(-.29 if j==0 else .58))
            tip = fork+branch_out*rng.uniform(.47,.88)+UP*rng.uniform(.4,.9)
            if low:
                tube(g,rng,"branches","trunk",[fork,tip],[.062,.029],3,bark,caps=False)
            else:
                tube(g,rng,"branches","trunk",[fork,fork.lerp(tip,.52)-UP*.07,tip],
                     [.065,.046,.024],4,bark,caps=False)
            leaf_count = 5 if low else 7
            for k in range(leaf_count):
                d = radial(k*TAU/leaf_count+a+rng.uniform(-.18,.18))
                blade(g,"foliage","leaf",tip,tip+d*rng.uniform(.3,.61)+UP*rng.uniform(-.22,.16),
                      rng.uniform(.105,.185),pick(rng,GREEN),2 if low or k else 6,rng.uniform(-.61,.61),.068)
            base = tip + UP*.06
            for k in range(1 if low else 2):
                p = base + radial(k*2.4 + a)*rng.uniform(.045,.128) + UP*rng.uniform(.01,.085)
                blade(g,"blossoms","leaf",tip,p,.017,"#788b4a",1)
                petals(g,rng,"blossoms",p,.112,("#f3d888","#fff8e9"),3 if low else 5,
                       UP+branch_out*.47,detailed=not low)


def bougainvillea(g, rng, low):
    shoots = 5 if low else 9
    trunk = [(0,0,0),(.055,.01,.21),(-.04,.042,.35)]
    tube(g,rng,"stems","trunk",trunk[::2] if low else trunk,
         [.061,.023] if low else [.061,.045,.023],4 if low else 6,BARK)
    for i in range(shoots):
        a = TAU*i/shoots+rng.uniform(-.23,.23)
        out = radial(a)
        p = out*rng.uniform(.39,.77)+UP*rng.uniform(.57,1.05)
        if i in ((3,) if low else (2,6)):
            p *= .72
            p.z -= .094
        stem_base = trunk[1] if i%2 else Vector((0,0,.03))
        twig_start = Vector(stem_base)
        if low:
            tube(g,rng,"stems","trunk",[twig_start,p],[.04,.011],3,BARK,caps=False)
        else:
            tube(g,rng,"stems","trunk",[twig_start,p*.66+UP*.095,p],
                 [.036,.025,.007],4,BARK,caps=False)
        width = rng.uniform(.52,.71) if low else rng.uniform(.38,.55)
        rim,crest = patch(g,rng,"foliage",p,(width,width*.88,.36 if low else .32),5,
                    pick(rng,GREEN),not low,smooth=low)
        blossoms = (1 if i == 0 else 2) if low else 3+(i%3!=0)
        for j in range(blossoms):
            b = crest if j==0 and i%3!=1 else rim[(j*3+i)%len(rim)]
            petals(g,rng,"bracts",b,rng.uniform(.105,.178),
                   (pick(rng,MAGENTA),pick(rng,MAGENTA)),3,UP*.66+(b-p).normalized()*.55,
                   detailed=not low)
            if not low and j%2==0:
                blade(g,"bracts","leaf",b,b+UP*.045+out*.021,.024,"#f8e8c4",1)
        if not low:
            for j in range(1+(i%2==0)):
                q = rim[(i+j*2)%len(rim)]
                direction = (q-p).normalized()
                blade(g,"foliage","leaf",q,q+direction*.17-UP*.08,.11,pick(rng,GREEN),2,.3,.018)


def tropical(slug, g, rng, low):
    heliconia = slug == "heliconia"
    layout = random.Random(rng.getrandbits(32))
    shoots = 5 if low else 8 if heliconia else 6
    for i in range(shoots):
        angle = i*2.39996 + layout.uniform(-.18,.18)
        out = radial(angle)
        start = out*layout.uniform(.02,.24)
        height = layout.uniform(.95,1.38) if heliconia else layout.uniform(.9,1.39)
        top = start + out*layout.uniform(.19,.42)+UP*height
        knee = start.lerp(top,.46)-out*.075
        tube(g,rng,"stems","leaf",[start,top] if low else [start,knee,top],
             [.017,.008] if low else [.026,.019,.008],3 if low else 4,
             ("#627944","#4b6c35","#657f3c"),caps=False)
        leaves = 3
        for j in range(leaves):
            heading = radial(angle+j*2.45+.38)
            t = .34+.61*j/(leaves-1)
            if low:
                p = start.lerp(top,t)
            else:
                p = start.lerp(knee,t/.46) if t < .46 else knee.lerp(top,(t-.46)/.54)
            length = layout.uniform(.43,.7) if heliconia else layout.uniform(.34,.59)
            end = p+heading*length+UP*layout.uniform(.03,.27)
            blade_start = p.lerp(end,.19) if heliconia and not low else p
            if heliconia and not low:
                blade(g,"stems","leaf",p,blade_start,.022,"#708b43",2)
            blade(g,"leaves","leaf",blade_start,end,
                  rng.uniform(.19,.28) if heliconia else rng.uniform(.10,.16),
                  pick(rng,PALM if heliconia else GREEN),6 if not low or (heliconia and j==2) else 2,
                  rng.uniform(-.45,.45),.106 if heliconia else .076)
        if i % (2 if not low else 3) == 0:
            if heliconia:
                tip = top + UP*(.113 if low else .22)
                blade(g,"inflorescences","leaf",top,tip,.033,"#d79537",2,.46)
                for j in range(3 if low else 5):
                    d = out*(-1 if j%2 else 1)
                    p = top+UP*(.052*j)
                    end = p+d*(.24-.027*j)+UP*(.13-.009*j)
                    blade(g,"inflorescences","leaf",p,end,.098-.008*j,
                          ("#e57828","#ec961f","#e88a27","#f1a527","#f5b93e")[j],2 if low else 6,
                          math.pi*.29,.016)
                    if not low:
                        blade(g,"inflorescences","leaf",p.lerp(end,.68),end+UP*.027,.035,"#efca45",2,0,0)
            else:
                p = top + UP*.102
                if low:
                    blade(g,"inflorescences","leaf",top,p+UP*.16,.115,"#b93042",2,.65,.01)
                    blade(g,"inflorescences","leaf",top,p+UP*.16,.115,"#c43a49",2,-.92,.01)
                else:
                    tube(g,rng,"inflorescences","leaf",[top,p,p+UP*.104,p+UP*.187],
                         [.041,.062,.043,.008],5,("#9c2636","#bf3449","#ce3e51","#b32e43"))
                    for j in range(5):
                        heading = radial(angle+j*2.4)
                        base = top+UP*(.041*j)
                        blade(g,"inflorescences","leaf",base,base+heading*(.071-.007*j)+UP*.087,
                              .061,pick(rng,("#c33951","#d84759","#a82a40")),2,j*.36,.01)


def chamfer_rect(width, depth, height, corner):
    x,y = width*.5,depth*.5
    return [(-x+corner,-y,height),(x-corner,-y,height),(x,-y+corner,height),(x,y-corner,height),
            (x-corner,y,height),(-x+corner,y,height),(-x,y-corner,height),(-x,-y+corner,height)]


def section(g, part, material, rings, colors, bottom=True, top=True, close=False):
    n = len(rings[0])
    faces, shades = [], []
    for i in range(len(rings)-1 + int(close)):
        a,b = i, (i+1)%len(rings)
        for j in range(n):
            k = (j+1)%n
            faces.append((a*n+j,a*n+k,b*n+k,b*n+j))
            shades.append(colors[i%len(colors)])
    if bottom:
        faces.append(tuple(reversed(range(n))))
        shades.append(colors[0])
    if top:
        faces.append(tuple((len(rings)-1)*n+j for j in range(n)))
        shades.append(colors[-1])
    g.add(part,material,[p for ring in rings for p in ring],faces,shades)


def block(g, part, material, x0,x1,y0,y1,z0,z1,color):
    def ring(z):
        return [(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)]
    section(g,part,material,[ring(z0),ring(z1)],[color])


def hedge(g, rng, low):
    slices = (-1,1) if low else (-1,-.74,-.49,-.23,0,.25,.51,.76,1)
    profile = ((-.266,.035),(-.357,.37),(-.344,.75),(-.241,.89),
               (.23,.89),(.341,.75),(.36,.37),(.28,.035))
    rings = []
    for i,x in enumerate(slices):
        inset = .008 if i in (0,len(slices)-1) else 0
        ring = []
        for y,z in profile:
            y -= math.copysign(inset,y)
            if not low and i not in (0,len(slices)-1) and z>.1:
                z += rng.uniform(-.036,.036)
                y += rng.uniform(-.013,.013)
            ring.append((x,y,z))
        rings.append(ring)
    points = [v for ring in rings for v in ring]
    faces, colors = [], []
    for i in range(len(rings)-1):
        for j in range(7):
            faces.append((i*8+j,(i+1)*8+j,(i+1)*8+j+1,i*8+j+1))
            palette = ("#3a5a31","#416237","#446535") if j in (0,6) else (
                "#496c3a","#4d713a","#51753e","#54743e")
            colors.append(pick(rng,palette))
    faces += [tuple(range(8)),tuple(reversed(range(len(points)-8,len(points))))]
    colors += [GREEN[2],GREEN[2]]
    g.add("foliage","leaf",points,faces,colors)
    if low:
        for x,y,d in ((-.66,-.246,-1),(0,.01,1),(.66,.237,1)):
            blade(g,"foliage","leaf",(x,y,.884),(x+.096,y+d*.063,.935),
                  .085,"#617d44",1,0,.02)
    else:
        for i in range(13):
            k = min(1+i//2,len(rings)-2)
            side = -1 if i%2 else 1
            if i%3==0:
                vertex = 2 if side==-1 else 5
            elif i%3==1:
                vertex = 3 if side==-1 else 4
            else:
                vertex = 4 if side==-1 else 3
            p = Vector(rings[k][vertex])
            d = Vector((rng.uniform(-.48,.48),side*.73,0)).normalized()
            blade(g,"foliage","leaf",p,p+d*rng.uniform(.075,.122)+UP*.046,
                  .072,"#92543f" if i in (2,7,11) else pick(rng,GREEN[3:]),2,rng.uniform(-.65,.65))


def grass(g, rng, low):
    n = 5 if low else 18
    for i in range(n):
        out = radial(i*2.39996+rng.uniform(-.2,.2))
        base = out*rng.uniform(.0,.045)
        tall = rng.uniform(.09,.25)
        end = base+out*rng.uniform(.054,.154)+UP*tall
        blade(g,"blades","leaf",base,end,rng.uniform(.01,.022),pick(rng,PALM[1:]),
              2 if low or i%2==0 else 6,rng.uniform(-.5,.5),.043)


def flower_bed(g, rng, low):
    section(g,"edging","stone",[
        chamfer_rect(1.98,.98,0,.055),chamfer_rect(2,1,.075,.055),
        chamfer_rect(1.87,.865,.075,.051)],["#9c9586","#afaa9b"],bottom=False,top=False)
    soil = chamfer_rect(1.87,.865,.055,.051)
    g.add("soil","stone",soil,[tuple(range(8))],SOIL[1])
    for i in range(8 if low else 22):
        columns = 4 if low else 8
        x = -.82+1.64*(i%columns)/(columns-1)+rng.uniform(-.062,.062)
        y = -.22+.44*(i//4)+rng.uniform(-.066,.066) if low else -.32+.31*(i//8)+rng.uniform(-.073,.073)
        p = Vector((x,y,.053))
        tip = p+UP*rng.uniform(.16,.34)+radial(i*2.4)*.051
        colors = (("#d88e2b","#f8bf37"),("#c44571","#ec80a7"),("#c74632","#e26c46"),
                  ("#c3baca","#e7dceb"))[i%4]
        if low:
            blade(g,"planting","leaf",p,tip,.027,GREEN[3],1,.3)
            if i not in (1,6):
                leaf = p.lerp(tip,.38)
                blade(g,"planting","leaf",leaf,leaf+radial(i*2.4)*.145+UP*.054,
                      .106,pick(rng,GREEN),1,.32)
            petals(g,rng,"planting",tip,.094,colors,3,UP+radial(i*.8)*.42,detailed=False)
        else:
            blade(g,"planting","leaf",p,tip,.027,GREEN[2],2,.3)
            for j in range(3):
                d = radial(i+2.4*j)
                center = p.lerp(tip,.19+.22*j)
                blade(g,"planting","leaf",center,center+d*rng.uniform(.08,.17)+UP*.033,.074,
                      pick(rng,GREEN),2,.33,.029)
            petals(g,rng,"planting",tip,rng.uniform(.066,.095),colors,5,
                   UP+radial(i*2.4)*.57,detailed=i%2 == 0)
    if not low:
        for x in (-.72,-.24,.24,.72):
            g.add("edging","stone",[(x-.005,-.501,.012),(x+.005,-.501,.012),
                                   (x+.005,-.501,.073),(x-.005,-.501,.073)],[(0,1,2,3)],"#777365")


def planter(g, rng, low):
    def ring(w,d,z,c=.081):
        if low:
            return [(-w/2,-d/2,z),(w/2,-d/2,z),(w/2,d/2,z),(-w/2,d/2,z)]
        return chamfer_rect(w,d,z,c)
    profiles = [(1.35,.48,0),(1.55,.65,.68),(1.41,.51,.68),(1.39,.49,.59)] if low else [
        (1.33,.48,0),(1.4,.5,.06),(1.46,.57,.556),(1.53,.63,.59),
        (1.55,.65,.655),(1.51,.61,.68),(1.38,.49,.68),(1.35,.46,.568)]
    section(g,"shell","concrete",[ring(*profile) for profile in profiles],
            ["#85837b","#a6a39a","#b3afa2","#96948c"] if low else
            ["#807c70","#a09c90","#928c81","#b6b2a6","#bcb7aa","#b2ac9e","#827a6d"],
            bottom=True,top=False)
    soil = ring(*profiles[-1])
    g.add("soil","stone",soil,[tuple(range(len(soil)))],SOIL[1])
    if not low:
        for x in (-.52,.52):
            for side in (-1,1):
                def drain_point(dx,z,lift):
                    return (x+dx,side*(.24+.01*z/.06+lift),z)
                rim = [drain_point(dx,z,.0014) for dx,z in ((-.08,.022),(.08,.022),(.073,.053),(-.073,.053))]
                inset = [drain_point(dx,z,.0006) for dx,z in ((-.064,.029),(.064,.029),(.058,.047),(-.058,.047))]
                g.add("shell","concrete",rim+inset,
                      [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],
                      ["#878275","#756f62","#6b665b","#797468","#514d45"])


def tree_pit(g, rng, low):
    if low:
        exterior = [(-.8,-.8,0),(.8,-.8,0),(.8,.8,0),(-.8,.8,0)]
        inner = [(-.23,-.23,.09),(.23,-.23,.09),(.23,.23,.09),(-.23,.23,.09)]
        flange = [(x,y,.09) for x,y,_ in exterior]
        section(g,"grate","metal",[exterior,flange,inner],["#363a37","#535954"],bottom=False,top=False)
        soil = [(x,y,.012) for x,y,_ in inner]
        g.add("soil","stone",soil,[(0,1,2,3)],"#544638")
        for a in (-.59,.59):
            for h in (-.47,.0,.47):
                g.add("grate","metal",[(h-.14,a-.035,.091),(h+.14,a-.035,.091),
                      (h+.14,a+.035,.091),(h-.14,a+.035,.091)],[(0,1,2,3)],"#2b2e2b")
        return
    outer = chamfer_rect(1.6,1.6,.07,.065)
    edge = chamfer_rect(1.55,1.55,.088,.061)
    frame_inner = chamfer_rect(1.46,1.46,.088,.06)
    section(g,"frame","metal",[chamfer_rect(1.6,1.6,0,.065),outer,edge,frame_inner],
            ["#414844","#555d58","#666b65"],bottom=False,top=False)
    base, top = .034,.085
    inner = [(math.cos(-3*math.pi/4+i*TAU/8)*.287,
              math.sin(-3*math.pi/4+i*TAU/8)*.287,top+.001) for i in range(8)]
    section(g,"grate","metal",[inner,chamfer_rect(.66,.66,top+.001,.075)],
            ["#535953"],bottom=False,top=False)
    # Taper radial bars to the inner collar and clip them to the square frame.
    def ray(angle,z,inner_edge):
        d = radial(angle)
        side = max(abs(d.x),abs(d.y))
        diagonal = abs(d.x)+abs(d.y)
        reach = min(.33/side,.585/diagonal)-.006 if inner_edge else min(.734/side,1.404/diagonal)
        return d*reach+UP*z
    for i in range(32):
        angle = (i+.5)*TAU/32
        half_width = TAU/32*.361
        a,b = angle-half_width,angle+half_width
        points = [ray(a,top,True),ray(a,top,False),ray(b,top,False),ray(b,top,True),
                  ray(a,base,True),ray(a,base,False)]
        g.add("grate","metal",points,[(0,1,2,3),(4,5,1,0)],
              [("#5a615a","#555d55","#626660")[i%3],"#374038"])
    soil = chamfer_rect(1.48,1.48,.005,.051)
    g.add("soil","stone",soil,[tuple(range(8))],SOIL[1])


BUILDERS = {
    "frangipani":frangipani,"bougainvillea":bougainvillea,"hedge_2m":hedge,
    "grass_tuft":grass,"flower_bed":flower_bed,"planter_box":planter,"tree_pit":tree_pit,
}


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    return scene


def build(slug):
    clear_scene()
    budget, size = SPECS[slug]
    counts = []
    for lod in ("lod0", "lod1"):
        low = lod == "lod1"
        rng = random.Random(5319 + sum((i+1)*ord(letter) for i,letter in enumerate(slug)))
        g = Geometry()
        if slug in BUILDERS:
            BUILDERS[slug](g, rng, low)
        elif slug.endswith("_palm"):
            palm(slug, g, rng, low)
        elif slug in {"heliconia", "ginger"}:
            tropical(slug, g, rng, low)
        else:
            tree(slug, g, rng, low)
        g.fit(size)
        counts.append(g.count())
        g.objects(lod)
    print("BUDGET", slug, counts, flush=True)
    if counts[0] > budget or counts[1]*5 > counts[0]:
        raise ValueError(f"{slug}: {counts}, limit {budget} and 20%")
    bpy.ops.export_scene.gltf(filepath=str(ROOT/f"{slug}.glb"), export_format="GLB",
                             export_yup=True, export_animations=False, export_skins=False,
                             export_cameras=False, export_lights=False, export_extras=True,
                             export_texcoords=False, export_vertex_color="ACTIVE")


VIEWS = (
    ("front", (0,-1,.065)), ("right", (1,0,.065)), ("back", (0,1,.065)),
    ("left", (-1,0,.065)), ("top", (0,0,1)), ("three_quarter", (1,-1,.69)),
)


def area(name, target, direction, distance, energy, size, color):
    light = bpy.data.lights.new(name, "AREA")
    light.energy, light.shape, light.size, light.color = energy, "DISK", size, color
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = target + Vector(direction).normalized()*distance
    obj.rotation_euler = (target-obj.location).to_track_quat("-Z", "Y").to_euler()


def render(slug):
    import numpy as np

    glb = ROOT/f"{slug}.glb"
    scene = clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(glb))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.adaptive_threshold = .12
    scene.render.use_persistent_data = True
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.world = bpy.data.worlds.new("Review environment")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.69,.73,.8,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .34
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    width, height = 640, 320
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    camera = bpy.data.objects.new("Review camera", bpy.data.cameras.new("Review camera"))
    bpy.context.scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    scene.camera = camera
    roots = [bpy.data.objects[lod] for lod in ("lod0","lod1")]
    points = [obj.matrix_world @ vertex.co for root in roots for obj in root.children
              for vertex in obj.data.vertices]
    y_min = min(p.y for p in points)
    y_max = max(p.y for p in points)
    x_min = min(p.x for p in points)
    x_max = max(p.x for p in points)
    high = max(p.z for p in points)
    span = max(x_max-x_min,y_max-y_min,high)
    center = Vector(((x_min+x_max)/2,(y_min+y_max)/2,high/2))
    distance = span*3
    camera.data.clip_start = max(.0002,span*.001)
    camera.data.clip_end = distance*5
    area("Key",center,(-2,-4,6),span*2,68*span**2,span*2,(1,.89,.73))
    area("Fill",center,(4,2,3),span*2,39*span**2,span*2,(.73,.84,1))
    area("Rim",center,(-1,4,4),span*2.1,46*span**2,span*1.7,(1,.94,.8))
    gap, canvas_w, canvas_h = 6, width*3+24, height*2+18
    canvas = np.ones((canvas_h,canvas_w,4),dtype=np.float32)
    canvas[:,:,:3] = .105
    frame = ROOT/"review"/"_frame.png"
    for index, (_,direction) in enumerate(VIEWS):
        direction = Vector(direction).normalized()
        rotation = (-direction).to_track_quat("-Z","Y")
        right = rotation @ Vector((1,0,0))
        up = rotation @ UP.cross(Vector((1,0,0)))
        mid_x = (min(p.dot(right) for p in points)+max(p.dot(right) for p in points))/2
        mid_y = (min(p.dot(up) for p in points)+max(p.dot(up) for p in points))/2
        view_center = right*mid_x + up*mid_y + direction*center.dot(direction)
        frame_span = max(max(p.dot(right) for p in points)-min(p.dot(right) for p in points),
                         max(p.dot(up) for p in points)-min(p.dot(up) for p in points))*1.13
        for root,s in zip(roots,(-1,1),strict=True):
            root.location = right*s*frame_span*.5
        camera.location = view_center+direction*distance
        camera.rotation_euler = rotation.to_euler()
        camera.data.ortho_scale = frame_span*2
        scene.render.filepath = str(frame)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(frame), check_existing=False)
        pixels = np.empty(width*height*4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        pixels = pixels.reshape((height,width,4))
        # A thin divider marks the equal-scale LOD0/LOD1 halves.
        pixels[:,width//2-1:width//2+1,:3] = .43
        x = gap + (index%3)*(width+gap)
        y = gap + (1-index//3)*(height+gap)
        canvas[y:y+height,x:x+width] = pixels
        bpy.data.images.remove(image)
    # Source tiles are already display-encoded PNG pixels. Save without a second view transform.
    sheet = bpy.data.images.new("Six view contact sheet", width=canvas_w, height=canvas_h, alpha=False)
    sheet.pixels.foreach_set(canvas.ravel())
    sheet_path = ROOT/"review"/f"{slug}.png"
    sheet.filepath_raw = str(sheet_path)
    sheet.file_format = "PNG"
    sheet.save()
    frame.unlink()
    digest = sha256(glb.read_bytes()).hexdigest()
    metadata = b"tEXtGLB SHA-256\0" + digest.encode("ascii")
    png = sheet_path.read_bytes()
    stamp = pack(">I",len(metadata)-4) + metadata + pack(">I",crc32(metadata))
    sheet_path.write_bytes(png[:-12]+stamp+png[-12:])
    print(f"REVIEW {slug} {digest}", flush=True)


if __name__ == "__main__":
    import sys

    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    mode, *slugs = args or ["all"]
    if mode not in {"build", "render", "all"}:
        raise ValueError("Expected build, render or all, then optional asset names")
    (ROOT/"review").mkdir(exist_ok=True)
    for slug in slugs or SPECS:
        if mode in {"build","all"}:
            build(slug)
        if mode in {"render","all"}:
            render(slug)
