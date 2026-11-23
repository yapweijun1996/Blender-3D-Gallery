"""Ninja face, wrapped headband and tied hair. Coordinates are in metres."""
from math import cos, sin, sqrt, pi
import bpy
from mathutils import Vector
from kit import ell, mat, tube


def mesh(name, vertices, faces, material):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.materials.append(material)
    data.update()
    for poly in data.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj["bone"] = "Head"
    return obj


def rings_mesh(name, rings, material, invert=False):
    count = len(rings[0])
    vertices = [v for ring in rings for v in ring]
    faces = []
    for i in range(len(rings) - 1):
        for j in range(count):
            a = i*count + j
            b = i*count + (j+1) % count
            faces.append((a, b, b+count, a+count))
    faces.append(tuple(reversed(range(count))))
    faces.append(tuple(range(len(vertices)-count, len(vertices))))
    if invert:
        faces = [f[::-1] for f in faces]
    return mesh(name, vertices, faces, material)


def radii(z):
    t = max(-.99999, min(.99999, (z-.7445)/.2295))
    r = sqrt(1-t*t)
    return (.263*r*(1+.025*t), .217*r, .008*t)


def face_y(x, z):
    rx, ry, cy = radii(z)
    return cy - ry*sqrt(max(.025, 1-(x/rx)**2))


def skin_shell(material):
    zs = [.5151 + .4588*(.5-.5*cos(pi*i/26)) for i in range(27)]
    rings = []
    for z in zs:
        rx, ry, cy = radii(z)
        rings.append([(rx*sin(2*pi*j/64), cy-ry*cos(2*pi*j/64), z) for j in range(64)])
    return rings_mesh("Head • soft cheek volume", rings, material)


def sticker(name, cx, cz, w, h, offset, material, bend=0, tilt=0, n=28):
    # Project each point onto the curved face, allowing silhouettes to turn with the head.
    vertices = []
    for i in range(4):
        radial = (i+1)/4
        for j in range(n):
            a = 2*pi*j/n
            u, v = radial*cos(a), radial*sin(a)
            x, z = cx+w*u, cz+h*v+bend*u*u+tilt*u
            vertices.append((x, face_y(x,z)-offset, z))
    center = len(vertices)
    vertices.append((cx,face_y(cx,cz)-offset,cz))
    faces = [(center,j,(j+1)%n) for j in range(n)]
    for i in range(3):
        for j in range(n):
            a,b = i*n+j,i*n+(j+1)%n
            faces.append((a,a+n,b+n,b))
    return mesh(name, vertices, faces, material)


def stroke(name, coords, material, radius, offset, taper=None):
    points = [(x,face_y(x,z)-offset,z) for x,z in coords]
    return tube(name, points, radius, material, taper)


def soft_lock(name, points, widths, depths, material, broad=(1,0,0)):
    # Elliptic sections normal to the flow create a closed volume bounded by blunt ends.
    # Intermediate sections round off the turn at each sculpted guide point.
    def smooth_samples(values):
        samples = []
        for i in range(len(values)-1):
            a,b,c,d = (values[max(0,i-1)],values[i],values[i+1],values[min(len(values)-1,i+2)])
            for t in (0,.5):
                samples.append((2*b+(c-a)*t+(2*a-5*b+4*c-d)*t*t+(3*b-a-3*c+d)*t*t*t)*.5)
        return samples+[values[-1]]
    points = smooth_samples([Vector(p) for p in points])
    widths = smooth_samples(widths)
    depths = smooth_samples(depths)
    rings = []
    guide = Vector(broad)
    for i, pos in enumerate(points):
        p = Vector(pos)
        tangent = (Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
        side = (guide-tangent*guide.dot(tangent)).normalized()
        far = tangent.cross(side).normalized()
        rings.append([tuple(p+side*widths[i]*cos(2*pi*j/16)+far*depths[i]*sin(2*pi*j/16)) for j in range(16)])
    return rings_mesh(name,rings,material)


def headwear(hair, band, orange, gold, green):
    cap_rings = []
    for u in (0,.025,.07,.16,.28,.42,.55,.68,.80,.9,.97,.999):
        ring = []
        for j in range(72):
            a=2*pi*j/72
            bottom_z=.592+.260*(max(0,(cos(a)+.48)/1.48)**1.75)
            z=bottom_z+(.993-bottom_z)*u
            t=(z-.75)/.244
            r=sqrt(max(.0001,1-t*t))
            cone=1-.045*(1-min(1,u/.06))
            ring.append((.274*r*sin(a)*cone,.018-.228*r*cos(a)*cone,z))
        cap_rings.append(ring)
    rings_mesh("Hair • nape and crown",cap_rings,hair)

    band_rings=[]
    for f, extra in ((0,.003),(.05,.010),(.20,.013),(.72,.013),(.95,.009),(1,.003)):
        row=[]
        for j in range(72):
            a=2*pi*j/72
            z=.774+f*.064+.018*cos(a)-.009*sin(a)
            rx,ry,cy=radii(z)
            x=(rx+extra+.008)*sin(a)
            y=cy-(ry+extra+.015)*cos(a)
            # The rear scalp is offset toward the nape relative to the face.
            # Fit the cloth to the outer ellipsoid, with a rolled margin at its edges.
            scalp_r=sqrt(1-((z-.75)/.244)**2)
            scalp_x=.274*scalp_r+extra+.004
            scalp_y=.228*scalp_r+extra+.004
            ratio=sqrt((x/scalp_x)**2+((y-.018)/scalp_y)**2)
            scale=max(1.,1./ratio)
            row.append((x*scale,.018+(y-.018)*scale,z))
        band_rings.append(row)
    rings_mesh("Headband • woven jade wrap",band_rings,band)

    # The fringe is split at the right temple, leaving a clear patch for the badge.
    locks = [
        ("Fringe • long sweep",[(.128,-.135,.930),(.086,-.172,.923),(.030,-.202,.895),(-.054,-.220,.871),(-.125,-.210,.844),(-.156,-.191,.832)], [.012,.047,.057,.048,.027,.003], [.007,.021,.024,.024,.018,.003]),
        ("Fringe • swept crown",[(.100,-.100,.955),(.032,-.155,.950),(-.062,-.177,.929),(-.130,-.179,.894),(-.192,-.151,.858),(-.216,-.127,.841)], [.009,.045,.049,.046,.026,.004], [.006,.023,.026,.025,.017,.004]),
        ("Fringe • part",[(.109,-.131,.938),(.144,-.159,.913),(.172,-.169,.876),(.200,-.160,.849),(.216,-.145,.835)], [.005,.030,.037,.022,.003], [.004,.018,.020,.018,.003]),
    ]
    for name,points,w,d in locks:
        soft_lock(name,points,w,d,hair,broad=(0,0,1))
    for side in (-1,1):
        soft_lock("Hair • temple lock "+str(side),[(side*.217,-.100,.842),(side*.232,-.113,.813),(side*.244,-.119,.767),(side*.242,-.117,.724),(side*.232,-.104,.692)],
                  [.004,.025,.030,.021,.004],[.004,.023,.026,.021,.004],hair,broad=(0,1,0))

    # A compact tied ponytail flares outward behind the head, overlapping the scalp.
    ell("Bun • vermilion tie",(.074,.169,.930),(.074,.067,.056),orange,24,12)
    ell("Hair • tied bun",(.100,.209,.980),(.107,.094,.101),hair,32,18)
    soft_lock("Bun • rolled end",[(.117,.202,1.034),(.158,.229,1.025),(.191,.236,.985),(.191,.217,.935),(.178,.197,.907)],
              [.006,.038,.038,.024,.004],[.004,.026,.026,.021,.004],hair,broad=(0,1,0))
    ell("Headband • back knot",(-.065,.245,.785),(.043,.031,.027),band,20,10)
    soft_lock("Headband • long ribbon",[(-.065,.245,.785),(-.108,.249,.770),(-.163,.254,.728),(-.194,.271,.657),(-.218,.278,.610)],
              [.004,.022,.027,.025,.014],[.003,.006,.006,.005,.003],band,broad=(1,0,0))
    soft_lock("Headband • short ribbon",[(-.065,.246,.785),(-.089,.257,.773),(-.114,.283,.736),(-.116,.308,.690)],
              [.004,.021,.025,.016],[.003,.006,.006,.003],band,broad=(1,0,0))
    # A tangerine persimmon mark with a two-lobed calyx uses the same curved base as the wrap.
    badge_x,badge_z = .017,.819
    sticker("Badge • fruit",badge_x,badge_z,.018,.015,.034,orange,bend=.002)
    sticker("Badge • calyx left",badge_x-.006,badge_z+.013,.010,.004,.036,green,tilt=-.003)
    sticker("Badge • calyx right",badge_x+.006,badge_z+.014,.010,.004,.036,green,tilt=.004)
    sticker("Badge • glint",badge_x-.005,badge_z+.002,.0023,.003,.037,gold)


def add_expression(obj, key_name, transform):
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    key = obj.shape_key_add(name=key_name, from_mix=False)
    key.value = 0.0
    for point in key.data:
        x,y,z = point.co
        new_x,new_z,behind = transform(x,z)
        point.co = (new_x,face_y(new_x,new_z) + (y-face_y(x,z)) + behind,new_z)


def expressions(parts):
    for obj in parts:
        name=obj.name
        if name.startswith(("Eye.", "Lash.")):
            side = 1 if ".L" in name else -1
            eye_x=side*.104
            def blink(x,z):
                t=(x-eye_x)/.055
                arc=.700+.009*(1-min(1,t*t))+.004*t*side
                if name.startswith("Lash."):
                    return x,arc+(z-.740)*.08,.030
                return x,arc+(z-.699)*.025,.030
            def surprised_eye(x,z):
                return eye_x+(x-eye_x)*1.06,.700+(z-.699)*1.15,0
            add_expression(obj,"blink",blink)
            add_expression(obj,"surprised",surprised_eye)
        elif name.startswith("Closed lash."):
            add_expression(obj,"blink",lambda x,z:(x,z,-.023))
        elif name.startswith("Brow."):
            side=1 if ".L" in name else -1
            eye_x=side*.104
            add_expression(obj,"surprised",lambda x,z:(x,z+.017-.12*side*(x-eye_x),0))
            add_expression(obj,"smile",lambda x,z:(x,z+.004+.10*side*(x-eye_x),0))
        elif name.startswith("Cheek.") or name.startswith("Freckle."):
            add_expression(obj,"smile",lambda x,z:(x*.983,z+.010,0))
        elif name.startswith("Mouth "):
            # The painted opening can widen into a grin or round into an O.
            def mouth(x,z,expression):
                u=x/.032
                v=(z-.606-.008*u*u-.002*u)/.0033
                if expression == "smile":
                    return .044*u,.608+.012*u*u+.008*v+.002*u,0
                return .014*u,.608+.015*v,0
            add_expression(obj,"smile",lambda x,z:mouth(x,z,"smile"))
            add_expression(obj,"surprised",lambda x,z:mouth(x,z,"surprised"))


def build_head():
    existing = set(bpy.data.objects)
    skin=mat("Apricot skin","#E8A277",.51)
    hair=mat("Aubergine hair","#352939",.37)
    ink=mat("Plum ink","#302435",.31)
    amber=mat("Amber iris","#AA663C",.27)
    brass=mat("Golden amber","#E9AD5D",.36)
    white=mat("Rice ivory","#FFF2D9",.38)
    blush=mat("Peach blush","#DF8C79",.58)
    band=mat("Deep teal","#32756E",.56)
    orange=mat("Persimmon","#DE7042",.48)
    leaf=mat("Leaf jade","#95B68C",.54)
    skin_shell(skin)
    for s in (-1,1):
        side="L" if s==1 else "R"
        ell("Ear."+side,(s*.249,-.001,.684),(.044,.043,.054),skin,22,12)
        ell("Ear."+side+" • concha",(s*.277,-.021,.685),(.016,.022,.027),blush,20,12)
        x,z=s*.104,.699
        sticker("Eye."+side+" • outer rim",x,z,.055,.055,.0037,ink,tilt=s*.004)
        sticker("Eye."+side+" • sclera",x,z-.001,.050,.049,.0061,white,tilt=s*.004)
        sticker("Eye."+side+" • iris",x-s*.003,z-.0007,.038,.047,.0084,amber)
        sticker("Eye."+side+" • pupil",x-s*.003,z+.006,.027,.035,.0103,ink)
        sticker("Eye."+side+" • amber fleck",x+.009,z-.030,.010,.004,.0119,brass,tilt=.002)
        sticker("Eye."+side+" • large catchlight",x-.013,z+.019,.011,.0125,.0139,white)
        sticker("Eye."+side+" • small catchlight",x+.014,z+.003,.004,.004,.0139,white)
        stroke("Lash."+side,[(x+s*u,z+v) for u,v in [(-.046,.020),(-.031,.041),(-.009,.052),(.011,.053),(.033,.045),(.047,.034),(.061,.037)]],
               ink,.0052,.012,[.24,.70,1,1.15,1.1,.8,.12])
        stroke("Closed lash."+side,[(x+s*u,z+v) for u,v in [(-.045,.001),(-.031,.005),(-.013,.009),(.009,.010),(.029,.007),(.043,.003),(.052,.005)]],
               ink,.0048,-.014,[.2,.7,.93,1,.9,.65,.2])
        stroke("Brow."+side,[(x+s*u,z+v) for u,v in [(-.038,.072),(-.022,.078),(0,.084),(.022,.086),(.041,.083)]],
               hair,.0074,.0039,[.47,.9,1,.8,.17])
        sticker("Cheek."+side,x+s*.041,.632,.033,.010,.0039,blush,tilt=s*.004)
        for i,(dx,dz) in enumerate([(-.007,-.001),(.002,.002),(.009,.0005)]):
            sticker("Freckle."+side+str(i),x+s*(.042+dx),.631+dz,.0020,.0018,.0051,amber,n=12)
    ell("Nose • soft button",(0,-.207,.658),(.017,.014,.014),skin,24,12)
    sticker("Mouth • quiet smile",0,.606,.032,.0033,.0038,ink,bend=.008,tilt=.002)
    headwear(hair,band,orange,brass,leaf)
    created=set(bpy.data.objects)-existing
    for obj in created:
        obj["bone"]="Head"
    expressions(created)
