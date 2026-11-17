"""Indigo wind-swept crop. Each visible lock has an editable Bezier spine."""
from math import cos, pi, sin
import bpy
from mathutils import Vector
from mathutils.geometry import interpolate_bezier
from forms import material, mesh


# Hairline and nape follow the independently authored head's axial sections.
SCALP = [
    (.315, .166, .201, .133), (.35,.240,.249,.197), (.39,.293,.265,.237),
    (.43, .345, .262, .278), (.54, .397, .303, .319),
    (.64, .414, .323, .329), (.72, .420, .326, .329),
    (.80, .408, .315, .318), (.88, .363, .287, .299),
    (.94, .302, .242, .253), (.98, .224, .184, .200),
    (1.015, .123, .114, .122), (1.031, .024, .023, .024),
]


def scalp_point(z, angle):
    for a, b in zip(SCALP, SCALP[1:]):
        if z <= b[0]:
            t = max(0, (z - a[0]) / (b[0] - a[0]))
            x, front, rear = [v + (w-v)*t for v, w in zip(a[1:], b[1:])]
            sx, cy = sin(angle), cos(angle)
            power = 2 / 2.3
            return Vector((x * abs(sx)**power * (1 if sx >= 0 else -1),
                           -(front if cy >= 0 else rear) * abs(cy)**power * (1 if cy >= 0 else -1), z))
    return Vector((0, 0, z))


def undercut(mat):
    n, levels = 72, 22
    verts, faces = [], []
    for row in range(levels):
        for j in range(n):
            a = 2*pi*j/n
            front = (1+cos(a))*.5
            hairline = .340 + .460*front**.97 + .018*sin(2*a)
            z = hairline + (SCALP[-1][0]-hairline)*row/(levels-1)
            point = scalp_point(z, a)
            if row == 0:
                point.x *= .988
                point.y *= .988
            verts.append(point)
            if row:
                k, m = (row-1)*n+j, (row-1)*n+(j+1)%n
                faces.append((k,m,m+n,k+n))
    faces.extend([tuple(reversed(range(n))), tuple(range((levels-1)*n, levels*n))])
    return mesh("Hair foundation | sculpted undercut", verts, faces, mat)


# Each profile runs from the broad attached root to the isolated tip. Front is -Y.
# A flattened cross-section gives the clumps a crest and two broad planes.
LOCKS = [
    ("01 | Forelock", "Ink", .108,.042, [(-.18,-.23,.915),(-.20,-.321,.875),(-.17,-.341,.797),(-.10,-.327,.735)]),
    ("02 | Split fringe", "Marine", .086,.036, [(-.30,-.17,.909),(-.32,-.258,.852),(-.304,-.275,.766),(-.26,-.260,.692)]),
    ("03 | Left temple", "Deep", .080,.036, [(-.33,-.13,.88),(-.391,-.179,.754),(-.399,-.174,.659),(-.365,-.167,.590)]),
    ("04 | Windswept forecrest","Ocean", .112,.051, [(-.26,-.217,.814),(-.177,-.274,.940),(-.008,-.220,1.080),(.199,-.052,1.225)]),
    ("05 | Crown sail","Blue", .126,.053, [(-.18,-.10,.881),(-.104,-.123,1.039),(.038,-.064,1.164),(.108,.145,1.294)]),
    ("06 | Far crest","Marine",.126,.061, [(-.329,-.081,.812),(-.337,-.068,.955),(-.303,.038,1.090),(-.215,.143,1.190)]),
    ("07 | Far wing","Ocean",.092,.053, [(-.323,.014,.746),(-.419,.050,.868),(-.462,.100,.953),(-.482,.200,1.036)]),
    ("08 | Near crest","Marine",.110,.043, [(-.155,-.226,.881),(.056,-.276,.931),(.223,-.195,1.039),(.383,.034,1.162)]),
    ("09 | Near temple sweep","Blue",.082,.034, [(.077,-.244,.852),(.228,-.236,.891),(.366,-.142,.958),(.467,.088,1.054)]),
    ("10 | Near blade","Ocean",.085,.041, [(.210,-.176,.801),(.351,-.122,.838),(.420,-.015,.897),(.484,.212,.997)]),
    ("11 | Rear crown","Marine",.135,.055, [(-.181,.060,.925),(-.119,.172,1.053),(.012,.258,1.126),(.151,.365,1.179)]),
]
COLOURS = {"Deep":"#223c60", "Ink":"#29486d", "Marine":"#345a83", "Ocean":"#3b6996", "Blue":"#4c7ea9"}


CROWN = [(.0, 0, 0), (.14,.019,.003), (.34,.042,.012), (.56,.061,.034),
         (.75,.057,.045), (.91,.036,.040), (1,.022,.032)]


def crown_point(t, a):
    for left, right in zip(CROWN, CROWN[1:]):
        if t <= right[0]:
            w = (t-left[0])/(right[0]-left[0])
            lift = left[1] + w*(right[1]-left[1])
            lean = left[2] + w*(right[2]-left[2])
            break
    z0 = .690+.137*(1+cos(a))*.5
    p = scalp_point(z0+(1.031-z0)*t,a)
    groove = (.012*cos(7*a+t*2.8)+.006*sin(4*a+t*4))*sin(pi*t)
    p.x += (lift*.55+groove)*sin(a)+lean
    p.y += -(lift*.62+groove)*cos(a)+lean*.65
    p.z += lift * (.68+.32*cos(a))
    return p


def crown_mass():
    # The rear guides share this surface to keep their upper course visible.
    verts, faces = [], []
    n = 72
    for i,(t, _, _) in enumerate(CROWN):
        for j in range(n):
            a = 2*pi*j/n
            verts.append(crown_point(t,a))
            if i:
                k,m=(i-1)*n+j,(i-1)*n+(j+1)%n
                faces.append((k,m,m+n,k+n))
    faces.extend([tuple(reversed(range(n))), tuple(range(len(verts)-n,len(verts)))])
    obj=mesh("Hair | swept crown foundation",verts,faces,material("Hair | crown","#305579",.64))
    mod=obj.modifiers.new("Crown transitions",'SUBSURF')
    mod.levels=mod.render_levels=1


def nape_locks():
    # These clumps flow from the crown, across the band and underneath the occiput.
    # The changing width and tip angle keep the back from becoming a row of scallops.
    layout=[(74,.56,.090), (94,.455,.100), (116,.391,.108), (138,.354,.110),
            (161,.335,.116), (185,.360,.124), (209,.343,.120), (230,.385,.102),
            (251,.435,.100), (270,.485,.094), (286,.552,.080)]
    for k,(degrees,end,width) in enumerate(layout):
        controls=[]
        twist = 10*sin(1.7*k)
        for t, offset, lift in [(.93,-54,.000),(.72,-42,.014),(.47,-31,.019),
                                (.22,-21,.019),(.04,-14,.023)]:
            a=(degrees+offset+twist*t)*pi/180
            p=crown_point(t,a)
            controls.append(tuple(p + Vector((sin(a)*lift,-cos(a)*lift,0))))
        for z, offset, lift in [(.643,-7,.024),((end+.59)*.5,1,.018),(end,7,.009)]:
            a=(degrees+offset)*pi/180
            p=scalp_point(z,a)
            p+=Vector((sin(a)*lift,-cos(a)*lift,0))
            controls.append(tuple(p))
        yield (f"{k+12:02d} | nape sweep",("Ink","Marine","Ocean","Marine")[k%4],width,.033,controls)


def make_spine(collection, title, colour, width, depth, controls):
    data = bpy.data.curves.new(title, 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(controls)-1)
    for point, co in zip(spline.bezier_points, controls):
        point.co = co
        point.handle_left_type = point.handle_right_type = 'AUTO'
    guide = bpy.data.objects.new("Guide " + title, data)
    collection.objects.link(guide)
    guide["colour"] = colour
    guide["width"], guide["depth"] = width, depth
    guide.hide_render = True
    return guide


def section_scale(f):
    keys = [(0,.48), (.15,.97), (.31,1.0), (.58,.79), (.77,.48), (.92,.20), (1,0.)]
    for (a, av), (b, bv) in zip(keys, keys[1:]):
        if f <= b:
            return av + (bv-av)*(f-a)/(b-a)
    return 0.


def rebuild_lock(guide):
    title = guide.name.removeprefix("Guide ")
    objname = "Lock " + title
    old = bpy.data.objects.get(objname)
    if old:
        if old.get("spine") != guide.name:
            raise RuntimeError("Unexpected lock name collision: " + objname)
        old_data = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if not old_data.users:
            bpy.data.meshes.remove(old_data)
    pts = guide.data.splines[0].bezier_points
    path = []
    for a,b in zip(pts, list(pts)[1:]):
        segment = interpolate_bezier(a.co, a.handle_right, b.handle_left, b.co, 4)
        path.extend(segment if not path else segment[1:])
    # Keep the flattened section against the curved skull even where the quiff rises above it.
    # Orient each ring continuously so the tapered planes cannot flip at a turning point.
    verts, faces = [], []
    prior = None
    section = [(1,0),(.81,.52),(.33,.95),(-.08,1.08),(-.67,.66),(-1,0),(-.62,-.56),(.23,-.70),(.76,-.40)]
    sides = len(section)
    for i, p in enumerate(path[:-1]):
        f = i/(len(path)-1)
        tangent = (path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        radial = Vector((p.x*.82, p.y*1.38, (p.z-.64)*.66)).normalized()
        wide = radial.cross(tangent)
        if wide.length < .12 and prior is not None:
            wide = prior - tangent*prior.dot(tangent)
        wide.normalize()
        if prior is not None and prior.dot(wide) < 0:
            wide.negate()
        outward = tangent.cross(wide).normalized()
        prior = wide
        scale = section_scale(f)
        for j,(w,h) in enumerate(section):
            verts.append(p + wide*w*guide["width"]*scale + outward*h*guide["depth"]*scale)
            if i:
                k,m = (i-1)*sides+j, (i-1)*sides+(j+1)%sides
                faces.append((k,m,m+sides,k+sides))
    verts.append(path[-1])
    row = len(verts)-1-sides
    for j in range(sides):
        faces.append((row+j, row+(j+1)%sides,len(verts)-1))
    faces.append(tuple(reversed(range(sides))))
    mat = material("Hair | "+guide["colour"], COLOURS[guide["colour"]], .61)
    result = mesh(objname, verts, faces, mat)
    result["spine"] = guide.name
    dst = guide.get("destination")
    if dst and dst in bpy.data.collections:
        target = bpy.data.collections[dst]
        for owner in list(result.users_collection):
            owner.objects.unlink(result)
        target.objects.link(result)
    mod = result.modifiers.new("Round the modelled crest", 'SUBSURF')
    mod.levels = mod.render_levels = 1
    return result


def build_hair():
    undercut(material("Hair | foundation","#213c58",.65))
    crown_mass()
    guides = bpy.data.collections.new("Indigo | editable hair spines")
    bpy.context.scene.collection.children.link(guides)
    for title, colour, width, depth, controls in [*LOCKS, *nape_locks()]:
        guide = make_spine(guides, title, colour, width, depth, controls)
        rebuild_lock(guide)
    guides.hide_viewport = True
    guides.hide_render = True
