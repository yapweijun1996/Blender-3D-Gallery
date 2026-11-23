"""Build the two texture-free Merlion Park game assets in Blender 5.1.2."""
from math import cos, pi, sin, sqrt
from pathlib import Path
import sys

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
TAU = 2 * pi

# Author dimensions as right, bayward, up. Blender maps -Y to +Z in glTF.
def xyz(point):
    x, forward, height = point
    return (x, -forward, height)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2


PALETTE = {
    'paint': ((.87, .855, .817), .37, 0),
    'stone': ((.267, .251, .222), .82, 0),
    'concrete': ((.49, .472, .441), .82, 0),
    'trim': ((.043, .109, .260), .35, 0),
    'water': ((.61, .82, .86), .27, 0),
    'plate': ((.029, .025, .022), .50, 0),
    'metal': ((.145, .16, .164), .42, .65),
    'chrome': ((.49, .53, .55), .31, .72),
    'wall': ((.339, .332, .304), .87, 0),
    'roof': ((.239, .241, .219), .68, 0),
    'leaf': ((.119, .204, .046), .81, 0),
    'trunk': ((.194, .143, .091), .9, 0),
    'light': ((.72, .70, .60), .36, 0),
    'lamp_emissive': ((.92, .86, .67), .33, 0),
}


def material(name):
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    color, roughness, metallic = PALETTE[name]
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1)
    result.use_nodes = True
    shader = result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    if name == 'lamp_emissive':
        shader.inputs['Emission Color'].default_value = (*color, 1)
        shader.inputs['Emission Strength'].default_value = .35
    return result


class Part:
    def __init__(self, name, scale=1, offset=(0, 0, 0), reverse=False):
        self.name = name
        self.scale = scale
        self.offset = offset
        self.reverse = reverse
        self.vertices = []
        self.faces = []
        self.styles = []

    def add(self, vertices, faces, style, smooth=False):
        base = len(self.vertices)
        for x, forward, height in vertices:
            if self.reverse:
                x, forward = -x, -forward
            self.vertices.append(xyz(tuple(
                component * self.scale + shift
                for component, shift in zip((x, forward, height), self.offset)
            )))
        self.faces.extend(tuple(base + i for i in face) for face in faces)
        self.styles.extend((style, smooth) for _ in faces)

    def finish(self, pivot=(0, 0, 0)):
        mesh = bpy.data.meshes.new(self.name)
        origin = Vector(xyz(pivot))
        mesh.from_pydata([Vector(point) - origin for point in self.vertices], [], self.faces)
        mesh.update()
        slots = list(dict.fromkeys(style for style, _ in self.styles))
        for name in slots:
            mesh.materials.append(material(name))
        for face, (style, smooth) in zip(mesh.polygons, self.styles, strict=True):
            face.material_index = slots.index(style)
            face.use_smooth = smooth
        obj = bpy.data.objects.new(self.name, mesh)
        obj.location = origin
        bpy.context.collection.objects.link(obj)
        return obj


def ring_faces(count, sides, close=True):
    faces = [
        (row*sides+i, row*sides+(i+1)%sides, (row+1)*sides+(i+1)%sides, (row+1)*sides+i)
        for row in range(count-1) for i in range(sides)
    ]
    if close:
        faces += [tuple(reversed(range(sides))),
                  tuple((count-1)*sides+i for i in range(sides))]
    return faces


def prism(part, outline, bottom, top, style):
    # Normalize the outline to counterclockwise in Blender XY.
    area = sum(x * g - y * f for (x, f), (y, g) in
               zip(outline, outline[1:] + outline[:1]))
    if area > 0:
        outline = list(reversed(outline))
    part.add([(x, f, h) for h in (bottom, top) for x, f in outline],
             ring_faces(2, len(outline)), style)


def box(part, x, forward, height, width, depth, tall, style, angle=0):
    outline = [(x + a*cos(angle) - b*sin(angle), forward + a*sin(angle) + b*cos(angle))
               for a, b in [(-width/2, -depth/2), (-width/2, depth/2),
                            (width/2, depth/2), (width/2, -depth/2)]]
    prism(part, outline, height, height+tall, style)


def disc_profile(part, x, forward, levels, sides, style, smooth=True):
    vertices = [
        (x + rx*cos(-TAU*i/sides), forward + rf*sin(-TAU*i/sides), h)
        for h, rx, rf in levels for i in range(sides)
    ]
    part.add(vertices, ring_faces(len(levels), sides), style, smooth)


def capsule(part, center, scales, style, sides=14, rings=8, axes=None):
    if axes is None:
        axes = ((1, 0, 0), (0, -1, 0), (0, 0, 1))
    u, v, w = map(Vector, axes)
    center = Vector(center)
    a, b, c = scales
    vertices = [center-w*c]
    for j in range(1, rings):
        polar = pi*j/rings
        for i in range(sides):
            angle = TAU*i/sides
            vertices.append(center + u*(a*cos(angle)*sin(polar))
                            + v*(b*sin(angle)*sin(polar)) - w*(c*cos(polar)))
    vertices.append(center+w*c)
    faces = [(0, 1+(i+1)%sides, 1+i) for i in range(sides)]
    faces += [tuple(1+i for i in face) for face in ring_faces(rings-1, sides, False)]
    last = 1+(rings-2)*sides
    faces += [(last+i, last+(i+1)%sides, len(vertices)-1) for i in range(sides)]
    part.add(vertices, faces, style, True)


def curve_points(points, divisions):
    points = [Vector(point) for point in points]
    result = []
    for i, (b, c) in enumerate(zip(points, points[1:])):
        a = points[max(0, i-1)]
        d = points[min(len(points)-1, i+2)]
        for j in range(divisions):
            t = j / divisions
            result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return result + [points[-1]]


def sweep(part, points, widths, style, sides=8, depths=None, reference=(1, 0, 0), cap=True):
    points = list(map(Vector, points))
    if depths is None:
        depths = widths
    vertices = []
    for pos, (p, width, depth) in enumerate(zip(points, widths, depths, strict=True)):
        direction = (points[min(len(points)-1, pos+1)]-points[max(0, pos-1)]).normalized()
        side = Vector(reference)
        side = (side - direction*side.dot(direction)).normalized()
        normal = side.cross(direction).normalized()
        for i in range(sides):
            theta = TAU*i/sides
            vertices.append(p + side*(width*cos(theta)) + normal*(depth*sin(theta)))
    part.add(vertices, ring_faces(len(points), sides, cap), style, True)


def beam(part, start, end, radius, style, sides=6):
    direction = (Vector(end) - Vector(start)).normalized()
    reference = (0, 0, 1) if abs(direction.z) < .9 else (1, 0, 0)
    sweep(part, [start, end], [radius, radius], style, sides, reference=reference)


def band(part, path, low, high, width, style):
    path = list(map(Vector, path))
    left, right = [], []
    for i, point in enumerate(path):
        tangent = (path[min(i+1, len(path)-1)] - path[max(0, i-1)]).normalized()
        lateral = Vector((-tangent.y, tangent.x))*width/2
        left.append(tuple(point+lateral))
        right.append(tuple(point-lateral))
    prism(part, left + right[::-1], low, high, style)


def interpolate(profile, h):
    for (a, *start), (b, *end) in zip(profile, profile[1:]):
        if h <= b:
            t = max(0, (h-a)/(b-a))
            return tuple(v + (w-v)*t for v, w in zip(start, end))
    return profile[-1][1:]


BODY = [
    (.77, 1.03, .84, -.25), (1.1, 1.22, .97, -.25),
    (1.7, 1.32, .99, -.26), (2.4, 1.34, 1.00, -.28),
    (3.1, 1.32, 1.05, -.31), (3.8, 1.26, 1.12, -.27),
    (4.7, 1.17, 1.09, -.21), (5.5, 1.03, 1.03, -.12), (6.33, .90, .85, -.12),
]


def body_point(h, angle, relief=0):
    rx, rf, center = interpolate(BODY, h)
    return ((rx+relief)*sin(angle), center+(rf+relief)*cos(angle), h)


def fan_scale(part, surface, h, theta, spacing, length, ribs):
    # Each scallop is a real shell-shaped relief with a raised and fluted free edge.
    vertices = [surface(h + length*.26, theta, -.016)]
    for underside in (False, True):
        for i in range(ribs):
            u = 2*i/(ribs-1)-1
            height = h - length * (.30 + .51*sqrt(max(0, 1-u*u)))
            relief = -.019 if underside else (.108 if i%2 == 0 else .074)
            vertices.append(surface(height, theta+u*spacing*.55, relief))
    faces = [(0, 1+i, 2+i) for i in range(ribs-1)]
    faces += [(2+i, 1+i, 1+ribs+i, 2+ribs+i) for i in range(ribs-1)]
    part.add(vertices, faces, 'paint')


def fish(part, small):
    part.add([body_point(h, TAU*i/28) for h, *_ in BODY for i in range(28)],
             ring_faces(len(BODY), 28), 'paint', True)
    rows, columns, ribs = (7, 10, 3) if small else (11, 17, 5)
    pitch = 4.65/rows
    for row in range(rows):
        h = 1.04 + row*pitch
        for col in range(columns):
            theta = TAU*(col+.5*(row%2))/columns
            front = cos(theta)
            if front > .77 and 1.95 < h < 4.95:
                continue
            fan_scale(part, body_point, h, theta, TAU/columns, pitch*1.40, ribs)


def fins(part, small):
    # The front edge of the tail curls back into the trunk, leaving a real opening.
    control = [(0, .22, 1.05), (0, 1.02, 1.12), (0, 1.37, 1.43),
               (0, 1.48, 1.91), (0, 1.42, 2.31), (0, 1.16, 2.53),
               (0, .86, 2.54), (0, .43, 2.79), (0, .26, 3.33)]
    path = curve_points(control, 1 if small else 2)
    widths = [.85 - .38*sin(pi*i/(len(path)-1)) for i in range(len(path))]
    thickness = [.165 + .075*sin(pi*i/(len(path)-1)) for i in range(len(path))]
    sweep(part, path, widths, 'paint', 8 if small else 12, thickness)
    if not small:
        def tail_surface(t, angle, relief):
            index = min(len(path)-2, max(0, int(t)))
            fraction = min(1, max(0, t-index))
            p = path[index].lerp(path[index+1], fraction)
            direction = (path[index+1]-path[index]).normalized()
            normal = Vector((1, 0, 0)).cross(direction)
            return p+Vector((1,0,0))*((widths[index]+relief)*sin(angle))+normal*((thickness[index]+relief)*cos(angle))
        for i in (4, 7, 10):
            for col in range(7):
                fan_scale(part, tail_surface, i, TAU*(col+.5*(i%3))/7, TAU/7, 2.86, 4)

    # The two-lobed breast fin is a fluted web, with a forward-rolled crest.
    rings = [
        (2.25, .31, .76, .065), (2.75, .50, .80, .115),
        (3.15, .65, .88, .14), (3.75, .69, .97, .16),
        (4.25, .70, 1.10, .22), (4.69, .66, 1.37, .26),
        (4.92, .58, 1.56, .235), (5.03, .45, 1.54, .144),
        (5.08, .34, 1.39, .048),
    ]
    if small:
        rings = rings[::2]
    columns = 12 if small else 20
    vertices = []
    for h, width, f, depth in rings:
        crest = max(0, (h-3.8)/1.28)
        for j in range(columns):
            angle = TAU*j/columns
            u = sin(angle)
            front = max(0,cos(angle))
            channel = (.018 + .029*crest)*cos(u*4*TAU)
            vertices.append((u*width, f + (depth+channel*front)*cos(angle)-.46*u*u,
                             h+crest*(.21*sin(abs(u)*pi)-.38*abs(u))))
    part.add(vertices, ring_faces(len(rings), columns), 'paint', True)


def mane(part, small):
    # A continuous carved mantle with broad tapered flutes, wrapping from cheek to nape.
    strands, samples, height_segments = (8, 2, 8) if small else (14, 3, 10)
    across = strands*samples
    vertices = []
    # Positions at the crown, cheeks, side of the jaw, mid-mane and cut hem.
    profile = [
        (0, 8.6, .10, .18, .12, .02),
        (.07, 8.54, .48, .54, .11, .88),
        (.18, 8.26, .84, .90, -.02, 1.34),
        (.34, 7.65, 1.09, 1.05, -.24, 1.29),
        (.53, 6.73, 1.16, 1.14, -.25, .94),
        (.72, 5.81, 1.18, 1.19, -.22, .58),
        (.87, 5.11, 1.23, 1.25, -.20, .44),
        (1, 4.52, 1.30, 1.31, -.22, .39),
    ]
    for j in range(height_segments+1):
        t = j/height_segments
        h, rx, rf, center, opening = interpolate(profile, t)
        for i in range(across+1):
            u = i/across
            theta = opening+(TAU-2*opening)*u
            groove = (1-cos(TAU*i/samples))*.5
            relief = (.046+.078*t)*groove*sin(pi*t/2)**.6
            hem = .76*(sin(4.0*theta)**2) + .44*sin(theta)**2
            hem += (-.10+.14*groove)*sin(2.1*theta)**2
            # Front layers end in diagonal edges, then flare into the short central fall.
            hv = h + (t**4)*hem
            vertices.append(((rx+relief)*sin(theta), center+(rf+relief)*cos(theta), hv))
    row = across+1
    faces = [(j*row+i, (j+1)*row+i, (j+1)*row+i+1, j*row+i+1)
             for j in range(height_segments) for i in range(across)]
    # A turned-under stone hem makes its distinct silhouette visible from low angles.
    start = len(vertices)
    for x, f, h in vertices[-row:]:
        vertices.append((x*.83, f*.82, h-.045))
    faces += [(start+i, start+i+1, start-row+i+1, start-row+i) for i in range(across)]
    crown = len(vertices)
    vertices.append((0, .12, 8.6))
    faces.extend((crown,i,i+1) for i in range(across))
    faces.append((crown,across,0))
    for side in (0, across):
        start = len(vertices)
        for j in range(height_segments+1):
            x, f, h = vertices[j*row+side]
            vertices.append((x*.75, f+.13, h-.055))
        for j in range(height_segments):
            quad = (j*row+side, (j+1)*row+side, start+j+1, start+j)
            faces.append(quad if side else quad[::-1])
    part.add(vertices, faces, 'paint', True)


def face(part, small):
    # Fuse overlapping volumes into one lion head, with the lower jaw held open.
    skull = Part('sculpt_core')
    coarse = 12 if small else 20
    capsule(skull, (0, .32, 7.41), (.99, .88, 1.16), 'paint', coarse, 12)
    capsule(skull, (0, .98, 7.42), (.82, .61, .90), 'paint', coarse, 10)
    capsule(skull, (0, .60, 6.15), (.68, .58, .48), 'paint', coarse, 8)
    for side in (-1, 1):
        capsule(skull, (side*.54, .66, 6.46), (.35, .46, .43), 'paint', coarse, 8)
        capsule(skull, (side*.47, .99, 7.06), (.46, .59, .57), 'paint', coarse, 8)
        capsule(skull, (side*.32, 1.43, 7.06), (.39, .56, .33), 'paint', coarse, 8)
    capsule(skull, (0, 1.09, 6.31), (.61, .72, .27), 'paint', coarse, 8)
    capsule(skull, (0, 1.57, 7.31), (.32, .40, .20), 'paint', coarse, 8)
    obj = skull.finish()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.data.remesh_voxel_size = .074 if small else .052
    bpy.ops.object.voxel_remesh()
    mod = obj.modifiers.new('Relax voxel seams', 'SMOOTH')
    mod.factor = .9
    mod.iterations = 5
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mod = obj.modifiers.new('Low-poly stone carving', 'DECIMATE')
    obj.data.calc_loop_triangles()
    mod.ratio = (355 if small else 890)/len(obj.data.loop_triangles)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    part.add([(v.co.x, -v.co.y, v.co.z) for v in obj.data.vertices],
             [tuple(p.vertices) for p in obj.data.polygons], 'paint', True)
    bpy.data.objects.remove(obj, do_unlink=True)

    capsule(part, (0, 1.01, 6.60), (.52, .33, .38), 'plate', 10, 6)
    for side in (-1, 1):
        # Small stone ears, slanted eyes, nostrils, and three whisker incisions.
        capsule(part, (side*.70, .36, 8.17), (.245, .22, .32), 'paint', 10, 6)
        capsule(part, (side*.70, .541, 8.19), (.143, .064, .207), 'paint', 8, 5)
        normal = Vector((side*.71, .70, 0))
        horizontal = Vector((.70, -side*.71, 0))
        axes = (horizontal, -normal, (0, 0, 1))
        center = Vector((side*.758, 1.135, 7.68))
        capsule(part, center, (.245, .11, .102), 'paint', 12, 7, axes)
        capsule(part, center + normal*.101, (.073, .024, .076), 'plate', 10, 6, axes)
        for upper in (True, False):
            points = [
                center + horizontal*(p*.25) + normal*(.055+.066*(1-p*p))
                + Vector((0,0, (.103 if upper else -.076)*(1-p*p)-side*p*.061))
                for p in (-1, -.73, -.43, 0, .43, .73, 1)
            ]
            widths = [(.023+(.05 if upper else .025)*(1-(2*i/6-1)**2)) for i in range(7)]
            sweep(part, points, widths, 'paint', 5, reference=(0,1,0))
        capsule(part, (side*.188, 1.905, 7.30), (.119, .040, .071), 'stone', 9, 5)
        for i in range(3 if not small else 2):
            line = [(side*.529, 1.846, 7.059+i*.080),
                    (side*.66, 1.749, 7.073+i*.068),
                    (side*.741, 1.64, 7.112+i*.047)]
            sweep(part, line, [.011, .021, .011], 'paint', 5, reference=(0,0,1))
        sweep(part, [(side*.43, 1.55, 6.87), (side*.43, 1.59, 6.75),
                     (side*.40, 1.60, 6.62)], [.09, .062, .008], 'paint', 7)
        sweep(part, [(side*.365, 1.49, 6.47), (side*.36, 1.51, 6.57)],
              [.078, .009], 'paint', 7)
    for i in range(-2, 3):
        box(part, i*.116, 1.69, 6.738+abs(i)*.012, .107, .105, .112, 'paint')
    beam(part, (0, 1.17, 6.62), (0, 1.86, 6.63), .102, 'metal', 10)


def stadium(rx, rf, sides):
    return [(rx*sin(TAU*i/sides), rf*cos(TAU*i/sides)) for i in range(sides)]


def statue_base(part, small):
    sides = 20 if small else 30
    if small:
        disc_profile(part, 0, 0, [(0, 2.80, 3.00), (.45, 2.80, 3.00),
                                  (.64, 2.89, 3.12)], 20, 'stone', False)
        disc_profile(part, 0, 0, [(.63, 2.65, 2.89), (.645, 2.65, 2.89)], 20, 'water')
    else:
        prism(part, stadium(2.07, 3.36, sides), 0, .19, 'stone')
        prism(part, stadium(2.13, 3.43, sides), .19, .245, 'concrete')
        prism(part, stadium(2.06, 3.35, sides), .245, .335, 'plate')
    # Parallel blue and pale stone bands run down the same double wave surface.
    rows, columns = (4, 6) if small else (10, 12)
    vertices = []
    for j in range(rows+1):
        angle = pi*j/rows
        f = (2.72 if small else 3.11)*cos(angle)
        w = .025 + (1.81 if small else 1.90)*sin(angle)**.70
        for i in range(columns+1):
            x = (2*i/columns-1)*w
            edge = max(.04, 1-(abs(x)/w)**4)
            swells = .71 + .26*cos(2.45*f+.73*x) + .16*sin(1.16*f-.38*x)
            base = .655 if small else .318
            vertices.append((x, f, base + edge*swells*(.42 if small else 1)*sin(angle)**.54))
    for i in range(columns):
        faces = [
            (j*(columns+1)+i, (j+1)*(columns+1)+i,
             (j+1)*(columns+1)+i+1, j*(columns+1)+i+1)
            for j in range(rows)
        ]
        # Each call only adds vertices owned by its strip.
        indices = sorted({index for f in faces for index in f})
        mapping = {value: index for index, value in enumerate(indices)}
        part.add([vertices[index] for index in indices],
                 [tuple(mapping[i] for i in reversed(face)) for face in faces],
                 'trim' if i%4 in (0, 3) else ('stone' if i%4 == 1 else 'concrete'), True)


def reduce_mesh(obj, target):
    obj.data.calc_loop_triangles()
    if len(obj.data.loop_triangles) <= target:
        return
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new('Game triangle budget', 'DECIMATE')
    modifier.ratio = target/len(obj.data.loop_triangles)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.validate(verbose=False)
    obj.data.update()


def create_statue():
    for small in (False, True):
        scale = 2 / 8.6 if small else 1
        offset = (-2.6, -14.3, 0) if small else (0, 0, 0)
        def section(name):
            return Part(('cub_' if small else '') + name, scale, offset, small)
        if small:
            cub = Part('merlion_cub', scale, offset, True)
            for sculpt in (fish, fins, mane, face):
                sculpt(cub, True)
            obj = cub.finish(offset)
            reduce_mesh(obj, 1130)
            # The decimator may collapse the crown's highest vertex.
            top = max(vertex.co.z for vertex in obj.data.vertices)
            height_factor = 2.0 / top
            for vertex in obj.data.vertices:
                vertex.co.z *= height_factor
            obj.data.update()
        else:
            for name, sculpt in [('scaled_fish_body', fish), ('curled_tail_and_fins', fins),
                                 ('lion_mane', mane), ('lion_head', face)]:
                part = section(name)
                sculpt(part, False)
                obj = part.finish()
                if name == 'lion_head':
                    reduce_mesh(obj, 1930)
        base = section('basin_and_waves' if small else 'stone_plinth_and_wave_mosaic')
        statue_base(base, small)
        base.finish(offset)
    jet = Part('water_jet')
    points, widths = [], []
    for i in range(26):
        t = i/25
        points.append((.023*t*sin(t*22), 1.85+10.6*t, 6.63+1.13*t-7.47*t*t))
        widths.append(.086 + .074*t + .016*sin(i*1.87)*t)
    sweep(jet, points, widths, 'water', 7)
    for k in range(3):
        start = 8+k*5
        spray = [(x+.13*sin(k*4)*t, f, h-.105*t*t)
                 for i, (x,f,h) in enumerate(points[start:], start)
                 if (i-start)%4 == 0 for t in [(i-start)/(25-start)]]
        sweep(jet, spray, [.020+.008*(i%2) for i in range(len(spray))], 'water', 4)
    jet.finish((0, 1.85, 6.63))


PLAZA = [(-30,-20), (16,-20), (26,-15), (30,-8), (30,-4),
         (20,-4), (19.1,-2.6), (2,-2.6), (-5,-3.2), (-15,-3.3),
         (-22,-5.5), (-29,-3.5), (-30,-4)]
PIER = [(12.5,-2.6), (18.5,-2.6), (18.5,18.60), (17.1,20.0),
        (-3.0,20.0), (-4.0,19.0), (-4.0,10.8), (-2.95,9.8),
        (11.85,9.8), (12.5,9.1)]


def paving(part, outline, height, pitch, width, style):
    # Line/polygon clipping works for the irregular quay as well as the L-shaped pier.
    for axis in (0, 1):
        limits = [p[axis] for p in outline]
        index = int(min(limits)/pitch)
        while index*pitch < max(limits):
            value = index*pitch+.014
            index += 1
            crossings = []
            for a,b in zip(outline, outline[1:]+outline[:1]):
                if min(a[axis], b[axis]) <= value < max(a[axis], b[axis]):
                    other = 1-axis
                    t = (value-a[axis])/(b[axis]-a[axis])
                    crossings.append(a[other]*(1-t)+b[other]*t)
            crossings.sort()
            strips = []
            for start, end in zip(crossings[::2], crossings[1::2]):
                if end-start < .12:
                    continue
                if axis == 0:
                    rect = [(value-width/2, start+.035), (value+width/2, start+.035),
                            (value+width/2, end-.035), (value-width/2, end-.035)]
                else:
                    rect = [(start+.035, value-width/2), (end-.035, value-width/2),
                            (end-.035, value+width/2), (start+.035, value+width/2)]
                strips.extend(rect)
            part.add([(x,f,height+axis*.0008) for x,f in strips],
                     [(i+3,i+2,i+1,i) for i in range(0,len(strips),4)], style)


def rail(part, path, h, spacing=2.0):
    for z, width in [(h+.26, .025), (h+.46,.025), (h+.66,.025), (h+.86,.025), (h+1.05,.064)]:
        band(part, path, z, z+width, width, 'chrome')
    for i, (a,b) in enumerate(zip(path,path[1:])):
        a, b = Vector(a), Vector(b)
        count = max(1, int((b-a).length/spacing+.5))
        for j in range(count + (i == len(path)-2)):
            x, f = a.lerp(b, j/count)
            box(part, x, f, h, .087, .093, 1.09, 'metal')


def park():
    quay = Part('waterfront_plaza')
    prism(quay, PLAZA, 0, 1.98, 'wall')
    prism(quay, PLAZA, 1.98, 2.34, 'concrete')
    quay.finish()

    joints = Part('granite_paving_and_inlays')
    paving(joints, PLAZA, 2.341, 1.20, .014, 'stone')
    paving(joints, PIER, 2.341, .95, .011, 'stone')
    for f in (-15.16, -11.49, -7.57):
        end = 17.7 if f < -12 else 22.7 if f < -9 else 28.7
        rect = [(-29.97,f-.077), (end,f-.077), (end,f+.077), (-29.97,f+.077)]
        joints.add([(x,y,2.343) for x,y in rect], [(3,2,1,0)], 'stone')
    joints.finish()

    edge = Part('stepped_granite_seawall')
    waterfront = [(-29,-3.5), (-22,-5.5), (-15,-3.3), (-5,-3.2),
                  (2,-2.6), (12.45,-2.6)]
    for i in range(8):
        depth = .51*i
        back = [(x, f + depth) for x,f in waterfront]
        front = [(x, f + depth+.51) for x,f in waterfront]
        top = 2.26 - .272*i
        prism(edge, back+front[::-1], 0, top, 'stone' if i == 7 else 'concrete')
        for point_a, point_b in zip(front, front[1:]):
            x, f = point_a
            y, g = point_b
            edge.add([(x,f+.002,top-.081), (y,g+.002,top-.081),
                      (y,g+.002,top-.039), (x,f+.002,top-.039)],[(3,2,1,0)],'stone')
        for a,b in zip(front, front[1:]):
            a,b = Vector(a), Vector(b)
            count = max(1, int((b-a).length/2.15))
            for j in range(1,count,2):
                x,f = a.lerp(b, (j-.24*(i%2))/count)
                edge.add([(x-.009,f-.31,top+.001), (x+.009,f-.31,top+.001),
                          (x+.009,f-.035,top+.001), (x-.009,f-.035,top+.001)],[(3,2,1,0)],'stone')
    edge.finish()

    landing = Part('semicircular_waterfront_platform')
    center_x, center_f = -5.0, -3.0
    arc = [(center_x+2.62*cos(pi*i/18),center_f+3.65*sin(pi*i/18)) for i in range(19)]
    outline = arc + [(center_x-2.62, center_f-4.05), (center_x+2.62, center_f-4.05)]
    prism(landing, outline, 0, 2.13, 'wall')
    prism(landing, outline, 2.13, 2.336, 'stone')
    for i in range(7):
        z = .18 + .278*i
        border = [(center_x+(x-center_x)*1.0015, center_f+(f-center_f)*1.0015) for x,f in arc]
        vertices = [(x,f,h) for h in (z,z+.023) for x,f in border]
        n = len(border)
        landing.add(vertices, [(j,j+1,j+1+n,j+n) for j in range(n-1)],'stone')
    landing.finish()
    parapet = Part('curved_stone_parapet')
    back_curve = [(center_x+2.80*cos(pi+i*pi/20),center_f+3.84*sin(pi+i*pi/20))
                  for i in range(21)]
    band(parapet, back_curve, 2.34, 2.83, .31, 'stone')
    band(parapet, back_curve, 2.83, 2.93, .39, 'concrete')
    for path in ([(-29.65,-4),(-29.65,-19.7)], [(29.7,-4.15),(29.7,-7.86),(25.7,-14.75)]):
        band(parapet, path, 2.34, 2.90, .34, 'stone')
        band(parapet, path, 2.90, 2.99, .47, 'concrete')
    parapet.finish()

    pier = Part('precast_pier_and_viewing_deck')
    prism(pier, [(x*.992, f*.995) for x,f in PIER], 1.54, 2.15, 'concrete')
    prism(pier, PIER, 2.15, 2.34, 'wall')
    for x,f in [(13.5,3.0),(17.1,3.0),(13.5,7.8),(17.1,7.8),
                (14,12),(17,17), (9,11),(9,18), (4,11),(4,18), (-1.6,18)]:
        disc_profile(pier,x,f,[(0,.40,.40),(1.25,.40,.40),(1.62,.62,.62)], 6, 'wall')
    pier.finish()
    railing = Part('stainless_steel_deck_rails')
    rail_path = PIER[1:]+PIER[:1]
    inner = [(x + (.11 if x<0 else -.10), f + (-.10 if f>17 else .095)) for x,f in rail_path]
    rail(railing, inner, 2.34, 2.30)
    railing.finish()

    benches = Part('promenade_benches')
    for x, f, angle in [(-20,-6.25,0),(-11,-6.55,0),(2,-6.4,0), (9,-6.2,0),
                         (-2.2,18.4,0),(5.7,18.4,0)]:
        for lateral in (-.70,.70):
            box(benches,x+lateral*cos(angle),f+lateral*sin(angle),2.34,.26,.48,.38,'stone',angle)
        for i in range(4):
            across = (i-1.5)*.126
            box(benches,x-across*sin(angle),f+across*cos(angle),2.71,1.92,.111,.086,
                'trunk',angle)
    benches.finish()

    lamps = Part('promenade_lamp_posts')
    for x, f, dark in [(-25,-7.5,False),(-2,-9.8,False),
                       (15.8,-8.2,False),(17.4,6.3,True),
                       (-3.05,18.9,True)]:
        style = 'metal' if dark else 'chrome'
        h = 2.34
        disc_profile(lamps,x,f,[(h,.185,.185),(h+.10,.185,.185),(h+.13,.095,.095),
                                (h+3.50,.061,.061),(h+3.83,.052,.052)],6,style)
        if dark:
            for z in (h+3.29,h+3.75):
                beam(lamps,(x-.22,f-.04,z),(x+.22,f+.04,z+.045), .075,'metal',5)
                box(lamps,x-.22,f-.046,z,.10,.115,.067,'lamp_emissive')
        else:
            disc_profile(lamps,x,f,[(h+3.51,.14,.14),(h+3.57,.29,.29),
                                    (h+3.64,.13,.13)],6,'lamp_emissive')
            disc_profile(lamps,x,f,[(h+3.64,.28,.28),(h+3.69,.28,.28),
                                    (h+3.78,.080,.080)],6,'chrome')
    lamps.finish()

    trees = Part('shade_trees_and_planters')
    for i, (x,f) in enumerate([(-23,-13.8),(-12.2,-13.9),
                               (-2.6,-12.2),(9.5,-12.25)]):
        h = 2.34
        box(trees,x,f,h,2.20,2.20,.14,'stone',pi/20)
        box(trees,x,f,h+.14,1.94,1.94,.02,'plate',pi/20)
        sweep(trees,[(x,f,h+.14),(x-.09,f+.06,h+1.5),(x+.13,f-.12,h+3.35)],
              [.15,.117,.082],'trunk',6)
        for j in range(3):
            a = 2.37*j + i*.82
            end = (x+1.31*cos(a),f+1.36*sin(a),h+3.31+.33*j)
            beam(trees,(x,f,h+1.8+.27*j),end,.073,'trunk',5)
            capsule(trees,end,(1.15+.16*(j%2), 1.12,.53), 'leaf',6,3)
        capsule(trees,(x+.05,f-.05,h+4.60),(1.49,1.38,.68),'leaf',7,3)
    trees.finish()


def export(name, builder):
    reset()
    builder()
    scene = bpy.context.scene
    triangles = 0
    for obj in scene.objects:
        obj.data.calc_loop_triangles()
        count = len(obj.data.loop_triangles)
        triangles += count
        print(f'{obj.name}: {count}', flush=True)
    print(f'{name}: {triangles} source triangles', flush=True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUT / f'{name}.glb'),
        export_format='GLB',
        export_yup=True,
        export_normals=True,
        export_texcoords=False,
        export_animations=False,
        export_skins=False,
        export_cameras=False,
        export_lights=False,
    )


if __name__ == '__main__':
    if bpy.app.version[:3] != (5, 1, 2):
        raise RuntimeError(f'Expected Blender 5.1.2. Found {bpy.app.version_string}.')
    builders = {'merlion': create_statue, 'merlion_park': park}
    requested = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for name in requested or builders:
        export(name, builders[name])
