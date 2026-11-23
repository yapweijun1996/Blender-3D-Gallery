"""Fitted wrap jacket, sash, cloth accessories, and tabi for the Persimmon Ninja."""

from math import cos, pi, sin

import bpy
from mathutils import Vector

from kit import ell, loft, mat, tube


def bind(obj, bone):
    obj["bone"] = bone
    return obj


def ring_mesh(name, rings, material, bone):
    """Close a sequence of equally sized, consistently wound cross sections."""
    count = len(rings[0])
    faces = [tuple(reversed(range(count)))]
    for level in range(len(rings) - 1):
        start = level * count
        for i in range(count):
            j = (i + 1) % count
            faces.append((start + i, start + j, start + count + j, start + count + i))
    faces.append(tuple(range((len(rings) - 1) * count, len(rings) * count)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([v for ring in rings for v in ring], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for face in mesh.polygons[1:-1]:
        face.use_smooth = True
    return bind(obj, bone)


def sleeve(name, a, b, sections, material, bone, segments=20):
    """Cross sections follow the limb axis so the cuff openings stay square to it."""
    start, end = Vector(a), Vector(b)
    axis = (end - start).normalized()
    across = Vector((0, 1, 0)).cross(axis).normalized()
    deep = axis.cross(across)
    rings = []
    for t, rx, ry in sections:
        center = start.lerp(end, t)
        rings.append([center + across * (rx * cos(2*pi*i/segments)) +
                      deep * (ry * sin(2*pi*i/segments)) for i in range(segments)])
    return ring_mesh(name, rings, material, bone)


def ribbon(name, nodes, material, bone="Torso"):
    """Nodes give the center, half-width, and half-thickness of the folded cloth."""
    points = [Vector(n[:3]) for n in nodes]
    rings = []
    for i, point in enumerate(points):
        tangent = (points[min(len(nodes) - 1, i + 1)] - points[max(0, i - 1)]).normalized()
        lateral = Vector((0, 1, 0)).cross(tangent).normalized()
        normal = tangent.cross(lateral)
        width, thick = nodes[i][3:]
        rings.append([point + lateral * (width*cos(j*pi/4)) + normal*(thick*sin(j*pi/4))
                      for j in range(8)])
    return ring_mesh(name, rings, material, bone)


def oval(name, loc, scale, material, bone, segments=16, rings=8):
    return bind(ell(name, loc, scale, material, segments, rings), bone)


def shell(name, rows, material, bone, segments=28):
    return bind(loft(name, rows, material, segments), bone)


def line(name, points, radius, material, bone):
    return bind(tube(name, points, radius, material), bone)


def build_body():
    midnight = mat("Midnight", "#27304B", .62)
    indigo = mat("Indigo", "#44547D", .59)
    jade = mat("Deep teal", "#32756E", .56)
    orange = mat("Persimmon", "#DE7042", .48)
    cream = mat("Linen", "#E8D9BD", .62)
    honey = mat("Golden amber", "#E9AD5D", .36)
    skin = mat("Apricot skin", "#E8A277", .51)

    shell("Jacket • brushed indigo", [
        (.232,0,.003,.095,.057), (.238,0,.002,.110,.067),
        (.249,0,.002,.116,.071), (.276,0,.002,.109,.068),
        (.300,0,.000,.102,.064), (.332,0,0,.094,.061), (.372,0,0,.099,.068),
        (.409,0,0,.108,.073), (.435,0,.002,.110,.072),
        (.453,0,.004,.099,.065), (.470,0,.004,.081,.055),
        (.488,0,.005,.051,.040), (.494,0,.005,.034,.029)
    ], indigo, "Torso", 36)
    oval("Nape", (0,.002,.496),(.045,.041,.051),skin,"Torso")
    shell("Jacket • bound hem", [
        (.236,0,.002,.106,.064),(.240,0,.002,.112,.069),
        (.246,0,.002,.116,.072),(.249,0,.002,.1155,.0715)
    ], midnight, "Torso", 32)

    # The two lapels climb opposite shoulders and cross behind the ribbed sash.
    ribbon("Jacket • underlap", [
        (-.049,-.027,.476,.011,.003),(-.052,-.049,.458,.014,.004),
        (-.037,-.066,.435,.015,.004),(-.014,-.073,.408,.014,.003),
        (.012,-.070,.386,.011,.003)], midnight)
    ribbon("Jacket • long overlap",[
        (.054,-.019,.476,.012,.003),(.057,-.047,.456,.015,.004),
        (.043,-.066,.434,.016,.004),(.022,-.074,.412,.017,.004),
        (-.006,-.073,.383,.017,.004),(-.033,-.064,.358,.017,.004),
        (-.059,-.050,.335,.018,.004),(-.067,-.045,.322,.018,.003)
    ],midnight)
    line("Jacket • woven edge",[(.061,-.049,.453),(.052,-.067,.436),
         (.031,-.077,.412),(.004,-.077,.383),(-.028,-.070,.355),(-.05,-.060,.336)],
         .0023,cream,"Torso")

    # Scarf is cut on the bias. The top edge rolls around the neck.
    shell("Scarf • folded collar", [
        (.462,0,-.001,.053,.045),(.467,-.002,-.003,.073,.052),
        (.476,-.003,-.003,.076,.056),(.484,0,-.002,.071,.054),
        (.497,.001,0,.067,.051),(.503,.001,0,.062,.048),
        (.508,.001,0,.047,.037)
    ],orange,"Torso",32)
    ribbon("Scarf • long windward tail",[
        (-.047,.033,.483,.023,.005),(-.083,.047,.469,.025,.005),
        (-.121,.055,.444,.024,.005),(-.159,.049,.430,.021,.004),
        (-.193,.044,.436,.021,.004),(-.226,.036,.458,.020,.0035),
        (-.255,.032,.465,.013,.0025),(-.271,.033,.460,.001,.001)
    ],orange)
    ribbon("Scarf • lower tail",[
        (-.045,.034,.476,.018,.004),(-.076,.055,.448,.018,.004),
        (-.10,.069,.419,.016,.0035),(-.137,.079,.399,.016,.0035),
        (-.157,.077,.394,.009,.002),(-.166,.075,.398,.001,.001)
    ],orange)
    oval("Scarf • side knot",(-.061,.032,.476),(.030,.021,.020),orange,"Torso")

    shell("Obi • cinch", [
        (.298,0,0,.097,.059),(.302,0,0,.104,.067),(.308,0,0,.105,.068),
        (.327,0,0,.101,.067),(.339,0,0,.100,.066),(.343,0,0,.096,.063)
    ],jade,"Torso",36)
    for name,z,rx,ry in (("lower",.306,.105,.068),("upper",.336,.1005,.066)):
        shell("Obi • "+name+" piping",[
            (z-.002,0,0,rx-.001,ry-.001),(z,0,0,rx+.001,ry+.001),
            (z+.0022,0,0,rx-.0005,ry-.0005)
        ],jade,"Torso",32)
    ribbon("Obi • front tie end",[
        (-.062,-.055,.318,.014,.0035),(-.071,-.059,.294,.014,.004),
        (-.065,-.069,.271,.013,.003),(-.056,-.067,.258,.008,.002),
        (-.052,-.066,.257,.001,.001)], jade)
    ribbon("Obi • tucked tie",[
        (-.066,-.054,.318,.012,.004),(-.086,-.046,.302,.014,.004),
        (-.096,-.040,.280,.011,.003),(-.095,-.041,.272,.001,.001)], jade)
    oval("Obi • knot",(-.065,-.054,.319),(.022,.013,.016),jade,"Torso")

    # A stitched utility pouch hangs from the back hip, clear of the swinging forearm.
    shell("Pouch • cloth body",[
        (.239,.094,.044,.022,.018),(.243,.096,.045,.030,.023),
        (.254,.097,.046,.034,.026),(.284,.096,.045,.033,.024),
        (.301,.093,.043,.028,.022)
    ],midnight,"Pelvis",20)
    shell("Pouch • flap",[
        (.277,.096,.046,.031,.025),(.284,.097,.047,.035,.0265),
        (.296,.095,.047,.034,.026),(.302,.092,.045,.028,.022)
    ],jade,"Pelvis",20)
    oval("Pouch • snap",(.102,.072,.286),(.006,.003,.006),honey,"Pelvis",12,6)
    oval("Trousers • seat",(0,.003,.245),(.099,.060,.060),midnight,"Pelvis")

    for side,s in (("L",1),("R",-1)):
        arm,forearm="UpperArm."+side,"Forearm."+side
        shoulder=(s*.101,.000,.445)
        elbow=(s*(.150 if s==1 else .151),-.005 if s==1 else 0,.372 if s==1 else .371)
        wrist=(s*(.181 if s==1 else .190),-.036 if s==1 else -.054,.318 if s==1 else .362)
        sleeve("Sleeve • "+side,shoulder,elbow,[
            (-.14,.012,.017),(-.04,.031,.032),(.17,.042,.044),(.39,.046,.045),
            (.67,.045,.045),(.92,.042,.041),(1.04,.035,.034)
        ],indigo,arm,24)
        sleeve("Sleeve welt • "+side,shoulder,elbow,[
            (.83,.044,.044),(.87,.045,.045),(.98,.043,.042),(1.0,.041,.040)
        ],midnight,arm,22)
        sleeve("Wrist guard • "+side,elbow,wrist,[
            (-.10,.028,.030),(.06,.033,.033),(.31,.032,.032),
            (.63,.029,.031),(.90,.025,.028),(1.07,.023,.026)
        ],midnight,forearm)
        for idx,(t,r) in enumerate(((.28,.032),(.53,.031),(.78,.028))):
            sleeve(f"Guard binding {idx+1} • "+side,elbow,wrist,[
                (t-.04,r,r+.001),(t-.025,r+.002,r+.003),
                (t+.023,r+.002,r+.003),(t+.04,r,r+.001)
            ],jade,forearm,16)
        palm=Vector(wrist)+(Vector(wrist)-Vector(elbow)).normalized()*.022
        oval("Mitten • "+side,palm,(.026,.026,.031),midnight,forearm)
        thumb=palm+Vector((-s*.018,-.010,.009))
        oval("Mitten thumb • "+side,thumb,(.014,.015,.020),midnight,forearm)

        thigh,shin,foot="Thigh."+side,"Shin."+side,"Foot."+side
        hip=(s*.067,0,.25)
        knee=(s*.082,-.020 if s==1 else .012,.15)
        ankle=(s*.093,-.025 if s==1 else .016,.070)
        sleeve("Trousers • "+side,hip,knee,[
            (-.24,.031,.037),(-.10,.047,.047),(.15,.050,.050),
            (.47,.051,.048),(.69,.047,.044),(.83,.039,.037),
            (.98,.032,.032),(1.06,.030,.031)
        ],midnight,thigh,24)
        sleeve("Greave • "+side,knee,ankle,[
            (-.08,.030,.031),(.12,.035,.034),(.36,.034,.034),
            (.63,.030,.031),(1.07,.027,.028)
        ],jade,shin)
        for i,(t,r) in enumerate(((.12,.035),(.39,.034),(.66,.0305))):
            sleeve(f"Puttee turn {i+1} • "+side,knee,ankle,[
                (t-.045,r-.0005,r-.0005),(t-.023,r+.0012,r+.0012),
                (t+.025,r+.001,r+.001),(t+.042,r-.0007,r-.0007)
            ],cream,shin,18)
        ax,ay,_=ankle
        # The left toe is the inner toe of the shoe on each foot.
        shell("Tabi • sole "+side,[
            (.000,ax,ay-.015,.037,.063),(.004,ax,ay-.019,.044,.071),
            (.011,ax,ay-.019,.045,.072),(.016,ax,ay-.017,.044,.071),
            (.019,ax,ay-.016,.042,.066)
        ],midnight,foot)
        shell("Tabi • foxing "+side,[
            (.011,ax,ay-.019,.044,.071),(.014,ax,ay-.019,.045,.072),
            (.020,ax,ay-.017,.044,.071),(.022,ax,ay-.015,.042,.067)
        ],jade,foot)
        shell("Tabi • upper "+side,[
            (.017,ax,ay-.017,.0435,.068),(.024,ax,ay-.017,.044,.069),
            (.031,ax,ay-.016,.044,.066),(.039,ax,ay-.013,.042,.061),
            (.049,ax,ay-.005,.037,.049),(.061,ax,ay+.001,.033,.039),
            (.075,ax,ay+.001,.031,.035),(.085,ax,ay,.028,.031)
        ],midnight,foot)
        line("Tabi • split toe seam "+side,[
            (ax-s*.014,ay-.077,.025),(ax-s*.013,ay-.070,.034),
            (ax-s*.010,ay-.058,.041),(ax-s*.008,ay-.049,.044)
        ],.0017,jade,foot)
