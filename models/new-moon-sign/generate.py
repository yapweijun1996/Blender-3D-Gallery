"""Build the wall-mounted New Moon sign. All lengths and bevels are in metres."""
import argparse
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'sources/new-moon-sign.blend'
ROOT = 'ASSET_NewMoonSign'
GROUPS = ('Frame', 'Panel', 'Moon_Logo', 'Letters', 'Light_Strips', 'Mounting')
PHRASE = 'New Moon'
LAMP_X = (-1.0, 0.0, 1.0)
FACE_Y = -.215
TAU = math.tau


def linear(s):
    return s / 12.92 if s <= .04045 else ((s + .055) / 1.055) ** 2.4


def color(hex_rgb):
    return tuple(linear(int(hex_rgb[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1,)


def material(name, hex_rgb, metallic, roughness, glow=None, strength=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    m.diffuse_color = color(hex_rgb)
    for socket, value in [('Base Color', m.diffuse_color), ('Metallic', metallic),
                          ('Roughness', roughness)]:
        p.inputs[socket].default_value = value
    if glow:
        p.inputs['Emission Color'].default_value = color(glow)
        p.inputs['Emission Strength'].default_value = strength
    if name.startswith('Enamel'):
        p.inputs['Specular IOR Level'].default_value = .20
    return m


def palette():
    return dict(green=material('Enamel | bottle green', '102D20', .04, .80),
                brass=material('Brass | satin brushed', 'C09150', 1, .35),
                edge=material('Brass | burnished edges', 'D79D4E', 1, .23),
                bronze=material('Bronze | shadow reveals', '71502F', .90, .39),
                gold=material('Letter | pale gold', 'F6CF86', .88, .26, 'FFCB7C', .23),
                opal=material('Crescent | honey opal', 'E9A849', .35, .29, 'FFB349', .69),
                light=material('Light | warm cream', 'FFF2CE', .05, .27, 'FFDF9F', 4.3),
                backlight=material('Crescent | amber return lens', 'FFD583', .04, .32, 'FFC86B', 7.5),
                steel=material('Steel | blackened', '30312F', .72, .55),
                screw=material('Steel | machined edges', '494944', .85, .39))


def obj(name, data, parent=None):
    o = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    return o


def hierarchy():
    root = obj(ROOT, None)
    root['units'] = 'metres'
    root['wall_mount'] = 'Back plane Y=0; bottom Z=0; front -Y'
    return root, {name: obj(name, None, root) for name in GROUPS}


def geometry(name, verts, faces, parent, mats, slots=None, closed=True):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for mat in mats:
        mesh.materials.append(mat)
    if slots is not None:
        for poly, slot in zip(mesh.polygons, slots, strict=True):
            poly.material_index = slot
    if closed:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()
    mesh.update()
    return obj(name, mesh, parent)


def box(name, parent, mat, center, size, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.object
    o.name = o.data.name = name
    o.parent = parent
    o.data.materials.append(mat)
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new('Rolled edges', 'BEVEL')
        mod.width, mod.segments = bevel, 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for p in o.data.polygons:
            p.use_smooth = True
        mod = o.modifiers.new('Face weighted normals', 'WEIGHTED_NORMAL')
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return o


def strips(a, b):
    return [(a[i - 1], a[i], b[i], b[i - 1]) for i in range(len(a))]


def rim(parent, m, far):
    # Successive mitred rectangular loops describe the entire moulding section.
    stages = [(0, -.213), (0, -.223), (.004, -.228), (.010, -.228),
              (.013, -.225), (.025, -.219), (.029, -.220), (.030, -.214)]
    if far:
        stages = [stages[i] for i in (0, 2, 5, 7)]
    verts, faces, slots = [], [], []
    for inset, y in stages:
        w = 1.512 - inset
        bot, top = .065 + inset, .77 - inset
        verts.extend([(-w,y,bot),(w,y,bot),(w,y,top),(-w,y,top)])
    for i in range(len(stages)):
        j = (i + 1) % len(stages)
        faces.extend(strips(range(4*i, 4*i+4), range(4*j, 4*j+4)))
        slots.extend([1 if i in (1, 4) else 0] * 4)
    geometry('Mitred face moulding', verts, faces, parent, [m['brass'],m['edge']], slots)


# The soffit rises towards the front edge. The three apertures share its tangent plane.
BACK = Vector((0, -.210, .786))
FRONT = Vector((0, -.342, .842))
ALONG = (FRONT - BACK).normalized()
OUT = Vector((0, -ALONG.z, ALONG.y))
MID = (BACK + FRONT) * .5
SOFFIT_HALF = (FRONT - BACK).length / 2


def on_soffit(x, v, out=0):
    return MID + Vector((x, 0, 0)) + ALONG * v + OUT * out


def cornice(parent, lamps, m, far):
    segments = 12 if far else 48
    radius = .046
    # Four quadrants on the inset rectangle line up with the circular lip.
    rect = [(-1,-1),(1,-1),(1,1),(-1,1)]
    outline = []
    for k, a in enumerate(rect):
        b = rect[(k+1) % 4]
        for j in range(segments//4):
            u = j / (segments//4)
            outline.append((a[0]*(1-u)+b[0]*u, a[1]*(1-u)+b[1]*u))
    angles = [math.atan2(v, u) for u, v in outline]
    verts, faces, slots, lookup = [], [], [], {}

    def index(p):
        key = tuple(round(float(n), 6) for n in p)
        if key not in lookup:
            lookup[key] = len(verts)
            verts.append(key)
        return lookup[key]

    def add(polygon, slot=0):
        faces.append(tuple(index(p) for p in polygon))
        slots.append(slot)

    spans = (-1.6, -.5, .5, 1.6)
    section = [(FRONT.y, FRONT.z),(-.346,.846),(-.346,.853),(-.342,.856),
               (-.342,.860),(-.35,.864),(-.35,.894),(-.344,.9),(-.01,.9),
               (-.006,.896),(-.006,.832), (BACK.y,BACK.z)]
    if far:
        section = [section[i] for i in (0, 2, 6, 7, 9, 11)]
    for k, x in enumerate(LAMP_X):
        left, right = spans[k:k+2]
        outer = [on_soffit(left + (u+1)*(right-left)/2, v*SOFFIT_HALF) for u,v in outline]
        throat = [on_soffit(x+radius*math.cos(a), radius*math.sin(a)) for a in angles]
        inner = [p - .012*OUT for p in throat]
        for j in range(segments):
            add((outer[j-1],outer[j],throat[j],throat[j-1]))
            add((throat[j-1],throat[j],inner[j],inner[j-1]), 1)
        add(inner, 1)
        # Segment boundaries coincide with the subdivided perforated soffit.
        nx = segments//4
        for n in range(nx):
            xa = left + n*(right-left)/nx
            xb = left + (n+1)*(right-left)/nx
            for q in range(len(section)-1):
                a,b = section[q:q+2]
                add(((xa,*a),(xb,*a),(xb,*b),(xa,*b)), 1 if q in (2,3) else 0)
        # Each optical insert has a bezel, a recessed baffle and a separate lens.
        profile = [(.051,.0002),(.051,.0020),(.048,.0031),(.044,.0022),
                   (.042,-.001),(.039,-.003),(.0375,-.0065)]
        if far:
            profile = [profile[i] for i in (0, 2, 4, 6)]
        rings = [[on_soffit(x+r*math.cos(a),r*math.sin(a),d) for a in angles] for r,d in profile]
        vs = [v for ring in rings for v in ring]
        fs, ids = [], []
        for q in range(len(rings)-1):
            fs.extend(strips(range(q*segments,(q+1)*segments),range((q+1)*segments,(q+2)*segments)))
            ids.extend([0 if q < 3 else 1] * segments)
        # The open annulus shares no surface with the fully recessed lens.
        geometry(f'Downlight {k+1} | bezel and baffle', vs, fs, lamps,
                           [m['edge'],m['bronze']], ids, closed=False)
        lens = [on_soffit(x+.038*math.cos(a), .038*math.sin(a), -.0067) for a in angles]
        geometry(f'Downlight {k+1} | diffuser', lens, [tuple(range(segments))],
                 lamps, [m['light']], closed=False)
    for x in (spans[0], spans[-1]):
        # Include every soffit boundary vertex along the end cap.
        cap = [(x,*p) for p in section]
        cap.extend(on_soffit(x,(-1+2*j/(segments//4))*SOFFIT_HALF) for j in range(1,segments//4))
        add(cap)
    geometry('Overhanging cornice with three recessed wells', verts, faces, parent,
             [m['brass'],m['bronze']], slots)


def hardware(parent, m, far):
    box('Removable rear steel plate', parent, m['steel'], (0,-.0195,.439),
        (3.112,.013,.794), 0 if far else .004)
    if not far:
        for sign in (-1,1):
            box(f'Rear folded flange | side {sign}',parent,m['steel'],(sign*1.532,-.012,.439),
                (.036,.004,.782),.001)
            box(f'Rear folded flange | rail {sign}',parent,m['steel'],(0,-.012,.439+sign*.381),
                (3.035,.004,.028),.001)
        for i,(x,z) in enumerate([(x,z) for x in (-1.533,1.533) for z in (.118,.436,.754)]
                                 + [(0,.060),(0,.818)],1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.006,depth=.0028,
                        location=(x,-.009,z),rotation=(math.pi/2,0,0))
            screw = bpy.context.object
            screw.name = screw.data.name = f'Back plate rivet {i}'
            screw.parent = parent
            screw.data.materials.append(m['screw'])
    # A keyhole in each stand-off strap opens onto the wall plane.
    for k, (x,z) in enumerate(((-1.18,.734),(1.18,.734),(-1.18,.133),(1.18,.133)),1):
        outline = [(-.032,-.060),(.032,-.060),(.041,-.050),(.041,.052),
                   (.033,.060),(-.033,.060),(-.041,.052),(-.041,-.050)]
        hole = [(-.004,.020),(.004,.020),(.006,.017),(.006,-.002),(.012,-.009),
                (.012,-.017),(.008,-.023),(0,-.026),(-.008,-.023),(-.012,-.017),
                (-.012,-.009),(-.006,-.002),(-.006,.017)]
        # Tessellate the plate with a real opening, then bridge its back and front.
        from mathutils.geometry import tessellate_polygon
        rings = [outline, hole]
        vs2 = [Vector((a,b,0)) for ring in rings for a,b in ring]
        cap = tessellate_polygon([vs2[:len(outline)],vs2[len(outline):]])
        count = len(vs2)
        vs = [(x+p.x,y,z+p.y) for y in (-.0132,0) for p in vs2]
        fs = list(cap) + [tuple(i+count for i in tri) for tri in cap]
        for start,end in ((0,len(outline)),(len(outline),count)):
            fs.extend(strips(range(start,end),range(start+count,end+count)))
        geometry(f'Mount {k} | keyhole strap', vs, fs, parent, [m['screw']])


def enclosure(g, m, far):
    box('Folded enamel cabinet',g['Panel'],m['green'],(0,-.115,.433),
        (3.13,.194,.83), 0 if far else .006)
    box('Inset enamel face',g['Panel'],m['green'],(0,FACE_Y+.004,.419),
        (3.034,.008,.718), 0 if far else .002)
    frame = g['Frame']
    box('Plinth | projecting brass shoe',frame,m['brass'],(0,-.129,.022),
        (3.168,.242,.044), 0 if far else .005)
    box('Plinth | upper lip',frame,m['edge'],(0,-.13,.045),
        (3.153,.233,.009), 0 if far else .002)
    rim(frame,m,far)
    cornice(frame,g['Light_Strips'],m,far)
    hardware(g['Mounting'],m,far)


# Two intersecting circular arcs parameterize the entire inlay, including its ornament.
RADIUS, INNER_RADIUS, SHIFT, TILT = .281, .239, .110, .39
OUT_ANGLE = math.acos((RADIUS**2 + SHIFT**2 - INNER_RADIUS**2)/(2*RADIUS*SHIFT))
IN_ANGLE = math.atan2(RADIUS*math.sin(OUT_ANGLE),RADIUS*math.cos(OUT_ANGLE)-SHIFT)


def moon_point(t, width):
    a = OUT_ANGLE + t*(TAU-2*OUT_ANGLE)
    b = IN_ANGLE + t*(TAU-2*IN_ANGLE)
    x = (1-width)*RADIUS*math.cos(a) + width*(SHIFT+INNER_RADIUS*math.cos(b))
    z = (1-width)*RADIUS*math.sin(a) + width*INNER_RADIUS*math.sin(b)
    return (-.868 + x*math.cos(TILT)-z*math.sin(TILT),
            .419 + x*math.sin(TILT)+z*math.cos(TILT))


def botanical_glass(mat, directory):
    """Draw the enamel cartoon in arc coordinates; line widths are in texture pixels."""
    width, height = 1024, 128
    y,x = np.mgrid[:height,:width]
    band = .45 + .20*np.cos(TAU*y/height) + .11*np.sin(x/69+y/33) + .08*np.sin(x/19-y/25)
    low, high = np.array([156,77,22]), np.array([235,162,59])
    art = low + band[:,:,None]*(high-low)
    ink = np.array([255,230,169])
    gold = np.array([246,181,76])

    def stroke(points, thickness=2.8, tint=ink):
        for p,q in zip(points,points[1:]):
            a,b = np.asarray(p),np.asarray(q)
            d = b-a
            left,top = np.maximum(0,np.floor(np.minimum(a,b)-thickness).astype(int))
            right,bottom = np.minimum((width,height),np.ceil(np.maximum(a,b)+thickness+1).astype(int))
            if left>=right or top>=bottom:
                continue
            yy,xx = np.ogrid[top:bottom,left:right]
            u = np.clip(((xx-a[0])*d[0]+(yy-a[1])*d[1])/max(d@d,1e-8),0,1)
            dist = np.hypot(xx-a[0]-u*d[0], yy-a[1]-u*d[1])
            alpha = np.clip(thickness*.5+.7-dist,0,1)[:,:,None]
            region = art[top:bottom,left:right]
            region += alpha*(tint-region)

    def vine(a,b,c,d):
        s = np.linspace(0,1,19)[:,None]
        return (1-s)**3*a+3*(1-s)**2*s*b+3*(1-s)*s*s*c+s**3*d

    def leaf(base, tip, breadth):
        delta = tip-base
        n = np.array([-delta[1],delta[0]]) / max(np.linalg.norm(delta),1)
        mid = base + delta*.46
        for side in (1,-1):
            stroke(vine(base,mid+side*n*breadth,tip-.22*delta+side*n*breadth,tip),2.5)
        stroke(vine(base,mid+.15*breadth*n,tip-.3*delta,tip),1.65,gold)

    def center(t):
        return 64 + 9*math.sin(t/56) + 7*math.sin(t/32+.7)

    stroke([(x,center(x)) for x in range(0,width+8,4)],3.1)
    for k in range(26):
        origin = 4+k*39 + 6*math.sin(k*2)
        side = 1 if k%2 else -1
        a = np.array([origin,center(origin)])
        d = np.array([origin+40+8*math.cos(k), 64+side*(53+4*math.sin(k*2.1))])
        branch = vine(a,a+(21,-side*6),d+(-19,-side*3),d)
        stroke(branch,2.65)
        for j, q in enumerate((4,9,13)):
            base = branch[q]
            direction = 1 if j%2 else -1
            tip = base + np.array([direction*(16+4*math.cos(k+j)),side*(16+4*math.sin(k+j))])
            leaf(base,tip,5.4+1.1*math.cos(2*k+j))
        # Some terminal shoots curl, others carry an open, five-petal rosette.
        if k%3:
            angles = np.linspace(0,1.68*math.pi,31)
            radii = np.linspace(9.2,1.2,31)
            stroke([d+(9-r*math.cos(t),-side*r*math.sin(t)) for r,t in zip(radii,angles)],2.3)
        else:
            center_flower = d + (2,-side*4)
            for j in range(5):
                ang = j*TAU/5+.4*k
                e = np.array([math.cos(ang),math.sin(ang)])
                leaf(center_flower+2.3*e,center_flower+13.3*e,5.5)
    # Smaller counter-growing sprays fill the gaps between the larger branches.
    for k in range(29):
        ox = k*35.5 + 14
        side = 1 if k%2 else -1
        a = np.array([ox,center(ox)])
        end = a + (-24-4*math.cos(k),side*(30+8*math.sin(k*.9)))
        tendril = vine(a,a+(-12,side*5),end+(10,-side*7),end)
        stroke(tendril,1.8)
        for q in (7,13):
            start = tendril[q]
            leaf(start,start+(-11,side*(12 if q==7 else -7)),4.9)
        curl = np.linspace(0,1.8*math.pi,26)
        stroke([end+(-5+(.9+4.1*(1-v/curl[-1]))*math.cos(v),
                       side*4.5*math.sin(v)) for v in curl],1.8)
    for border in (3.2,height-4.2):
        stroke([(0,border),(width,border)],3.2)
    rgba = np.full((height,width,4),255,np.uint8)
    rgba[:,:,:3] = np.rint(art)
    image = png_image('Crescent botanical enamel',rgba,directory)
    nt = mat.node_tree
    texture = nt.nodes.new('ShaderNodeTexImage')
    texture.image = image
    texture.extension = 'EXTEND'
    bsdf = nt.nodes['Principled BSDF']
    for socket in ('Base Color','Emission Color'):
        nt.links.new(texture.outputs['Color'],bsdf.inputs[socket])
    bsdf.inputs['Emission Strength'].default_value = 2.2


def moon(parent, m, directory):
    steps = 84
    # Wrap a single watertight shell from the rear wall around the rolled rim.
    section = [(0,-.223),(0,-.228),(0,-.246),(.018,-.255),(.049,-.260),(.080,-.258),
               (.088,-.2565),(.910,-.2565),(.922,-.258),(.953,-.260),
               (.984,-.255),(1,-.246),(1,-.228),(1,-.223)]
    slots = [4,2,1,1,1,0,3,0,1,1,1,2,4,4]
    verts, faces, ids, known, coords = [], [], [], {}, {}
    for i in range(steps+1):
        t = i/steps
        for w,y in section:
            x,z = moon_point(t,w)
            # At the tips, each profile collapses onto one front and one back vertex.
            if i in (0,steps) and y < -.223:
                y = -.250
            pt = (round(x,8),y,round(z,8))
            known.setdefault(pt,len(known))
            verts.append(known[pt])
            if w in (.088,.910):
                coords[known[pt]] = (t, (w-.088)/(.910-.088))
    n = len(section)
    for i in range(steps):
        for j in range(n):
            k = (j+1)%n
            face = dict.fromkeys(verts[h] for h in (i*n+j,(i+1)*n+j,(i+1)*n+k,i*n+k))
            if len(face) >= 3:
                faces.append(tuple(face))
                ids.append(slots[j])
    case = geometry('Crescent | luminous botanical enamel and brass', list(known), faces, parent,
                    [m['gold'],m['edge'],m['bronze'],m['opal'],m['backlight']], ids)
    uv = case.data.uv_layers.new(name='Unwrapped crescent')
    for face in case.data.polygons:
        if face.material_index == 3:
            for i in face.loop_indices:
                uv.data[i].uv = coords[case.data.loops[i].vertex_index]
    botanical_glass(m['opal'],directory)
    for i,t in enumerate((.31,.66),1):
        x,z = moon_point(t,.5)
        box(f'Crescent | concealed stand-off {i}',parent,m['bronze'],(x,-.219,z),(.022,.010,.022))


def lettering(parent, m):
    font = bpy.data.fonts.load(str(HERE/'sources/STIXTwoText.ttf'))
    glyphs = []
    for i,ch in enumerate(PHRASE):
        if ch == ' ':
            continue
        data = bpy.data.curves.new('Serif outline','FONT')
        data.body, data.font, data.resolution_u = ch, font, 5
        data.extrude, data.bevel_depth, data.bevel_resolution = .039,.0090,1
        o = obj(f'Letter {i+1:02d} {ch}',data,parent)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.convert(target='MESH')
        o.data.name = o.name
        o['character'] = ch
        o.data.materials.append(m['brass'])
        o.data.materials.append(m['gold'])
        for p in o.data.polygons:
            p.material_index = int(p.normal.z > .998)
        glyphs.append(o)
    # Optical bearings include the space after "New". All glyphs share a baseline.
    gaps = [.011,.004,.096,.010,.010,.012,0]
    widths = [max(v.co.x for v in o.data.vertices)-min(v.co.x for v in o.data.vertices) for o in glyphs]
    sx = (1.81-sum(gaps))/sum(widths)
    sy = .320/max(v.co.y for v in glyphs[0].data.vertices)
    x = -.483
    for o,w,gap in zip(glyphs,widths,gaps):
        left = min(v.co.x for v in o.data.vertices)
        for v in o.data.vertices:
            a,b,c = v.co
            v.co = ((a-left)*sx, -c*.54, b*sy)
        o.location = (x,-.235,.263)
        o.data.update()
        x += w*sx+gap
    parent['inscription'] = PHRASE
    bpy.data.orphans_purge(do_recursive=True)


def png_image(name, rgba, directory, data=False):
    """Write scanlines explicitly so procedural textures require only Blender libraries."""
    h,w,_ = rgba.shape
    def chunk(tag, payload):
        return (struct.pack('>I',len(payload)) + tag + payload
                + struct.pack('>I',zlib.crc32(tag+payload)))
    rows = b''.join(b'\0'+row.tobytes() for row in rgba)
    payload = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))
               + chunk(b'IDAT',zlib.compress(rows,9)) + chunk(b'IEND',b''))
    path = directory/(name+'.png')
    path.write_bytes(payload)
    image = bpy.data.images.load(str(path))
    if data:
        image.colorspace_settings.name = 'Non-Color'
    image.pack()
    image.filepath = '//'+path.name
    return image


def brushed_finish(mat, root, directory):
    y,x = np.mgrid[:128,:64]
    grain = (.35 + .027*np.sin(TAU*(y*29/128+x/64))
             + .021*np.sin(TAU*y*47/128) + .013*np.cos(TAU*(y*9/128-x/64)))
    pixels = np.full((128,64,4),255,np.uint8)
    pixels[:,:,1] = np.rint(grain*255)
    nt = mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = png_image('Satin brass grain',pixels,directory,data=True)
    split = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(tex.outputs['Color'],split.inputs['Color'])
    p = nt.nodes['Principled BSDF']
    nt.links.new(split.outputs['Green'],p.inputs['Roughness'])
    nt.links.new(split.outputs['Blue'],p.inputs['Metallic'])
    bpy.context.view_layer.update()
    for o in root.children_recursive:
        if o.type != 'MESH' or mat not in list(o.data.materials):
            continue
        mesh = o.data
        uv = mesh.uv_layers.active or mesh.uv_layers.new()
        for face in mesh.polygons:
            n = face.normal
            for i in face.loop_indices:
                x,y,z = o.matrix_world @ mesh.vertices[mesh.loops[i].vertex_index].co
                u,v = (y,z) if abs(n.x)>.7 else (x, y if abs(n.z)>.7 else z)
                uv.data[i].uv = (u/.30,v/.085)


# A single orthographic atlas covers both graphic groups. Its empty gutter lets the
# far LOD keep the logo and lettering independently hideable with two coplanar quads.
ATLAS = (-1.18, 1.38, .10, .74)
BREAK_X = -.55


def bake_graphics(groups, directory):
    width,height,ss = 1024,256,2
    xmin,xmax,zmin,zmax = ATLAS
    scale = width*ss/(xmax-xmin)
    h,w = height*ss,width*ss
    depth = np.full((h,w),np.inf)
    pixels = np.zeros((h,w,4),np.uint8)
    # This orthographic colour bake samples the actual silhouette, cap, bevel and wires.
    enamel = bpy.data.images['Crescent botanical enamel.png']
    ew,eh = enamel.size
    linear_rgba = np.empty(ew*eh*4,np.float32)
    enamel.pixels.foreach_get(linear_rgba)
    rgb = linear_rgba.reshape(eh,ew,4)[:,:,:3]
    enamel_srgb = np.rint(255*np.where(rgb < .0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055))
    colors = {'Letter | pale gold':'F4D398','Brass | satin brushed':'AA783B',
              'Crescent | honey opal':'F2C478','Light | warm cream':'FFF4D5',
              'Brass | burnished edges':'D59B52','Bronze | shadow reveals':'775136','Crescent | amber return lens':'FFE0A0'}
    bpy.context.view_layer.update()
    for group in groups:
        for o in sorted(group.children,key=lambda ob: ob.name):
            if 'concealed stand-off' in o.name:
                continue
            mesh = o.data
            mesh.calc_loop_triangles()
            coords = np.array([tuple(o.matrix_world @ v.co) for v in mesh.vertices])
            xx = (coords[:,0]-xmin)*scale
            yy = (zmax-coords[:,2])*scale
            for tri in mesh.loop_triangles:
                if tri.normal.y >= -1e-5:
                    continue
                ind = list(tri.vertices)
                x,y = xx[ind],yy[ind]
                l,r = max(0,math.floor(min(x))), min(w,math.ceil(max(x)))
                t,b = max(0,math.floor(min(y))), min(h,math.ceil(max(y)))
                if l>=r or t>=b:
                    continue
                gy,gx = np.ogrid[t:b,l:r]
                dx,dy = gx+.5-x[0],gy+.5-y[0]
                ax,ay,bx,by = x[1]-x[0],y[1]-y[0],x[2]-x[0],y[2]-y[0]
                det = ax*by-bx*ay
                if abs(det) < 1e-10:
                    continue
                u,v = (dx*by-dy*bx)/det,(ax*dy-ay*dx)/det
                a,b1,c = coords[ind,1]
                d = a+u*(b1-a)+v*(c-a)
                visible = (u>=0)&(v>=0)&(u+v<=1)&(d<=depth[t:b,l:r])
                depth[t:b,l:r][visible] = d[visible]
                mat = mesh.materials[tri.material_index]
                if mat.name == 'Crescent | honey opal':
                    tex = np.array([tuple(mesh.uv_layers.active.data[i].uv) for i in tri.loops])
                    st = tex[0] + u[visible,None]*(tex[1]-tex[0]) + v[visible,None]*(tex[2]-tex[0])
                    indices = np.clip((st*(ew,eh)).astype(int),(0,0),(ew-1,eh-1))
                    patch = pixels[t:b,l:r]
                    patch[visible,:3] = enamel_srgb[indices[:,1],indices[:,0]]
                    patch[visible,3] = 255
                    continue
                rgb = bytes.fromhex(colors[mat.name])
                shade = .94 + .12*tri.normal.z - .06*tri.normal.x
                pixels[t:b,l:r][visible] = [*(min(255,round(ch*shade)) for ch in rgb),255]
    samples = pixels.reshape(height,ss,width,ss,4).astype(np.float32)
    count = np.count_nonzero(samples[:,:,:,:,3],axis=(1,3))
    result = np.empty((height,width,4),np.uint8)
    result[:,:,:3] = np.rint(samples[:,:,:,:,:3].sum(axis=(1,3))/np.maximum(count,1)[:,:,None])
    # A warm gutter keeps minified bilinear edges free from dark fringes.
    result[count==0,:3] = (222,184,118)
    result[:,:,3] = np.rint(255*count/(ss*ss))
    return png_image('New Moon relief bake',result,directory)


def graphics_card(name, parent, mat, left, right):
    xmin,xmax,bottom,top = ATLAS
    o = geometry(name,[(left,FACE_Y-.0006,bottom),(right,FACE_Y-.0006,bottom),
                       (right,FACE_Y-.0006,top),(left,FACE_Y-.0006,top)],
                 [(0,1,2,3)],parent,[mat],closed=False)
    uv = o.data.uv_layers.new()
    for i in range(4):
        x,y,z = o.data.vertices[o.data.loops[i].vertex_index].co
        uv.data[i].uv = ((x-xmin)/(xmax-xmin),(z-bottom)/(top-bottom))


def far_graphics(g, atlas):
    mat = material('Artwork | baked ink and light','FFFFFF',.42,.38,'FFEDC8',.28)
    nt = mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = atlas
    tex.extension = 'CLIP'
    p = nt.nodes['Principled BSDF']
    nt.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    nt.links.new(tex.outputs['Color'],p.inputs['Emission Color'])
    mask = nt.nodes.new('ShaderNodeMath')
    mask.operation = 'GREATER_THAN'
    mask.inputs[1].default_value = .36
    nt.links.new(tex.outputs['Alpha'],mask.inputs[0])
    nt.links.new(mask.outputs[0],p.inputs['Alpha'])
    g['Letters']['inscription'] = PHRASE
    graphics_card('Flat crescent',g['Moon_Logo'],mat,ATLAS[0],BREAK_X)
    graphics_card('Flat inscription',g['Letters'],mat,BREAK_X,ATLAS[1])


def export(root, filename, uv=True):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [root,*root.children_recursive]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=str(HERE/'exports'/filename),export_format='GLB',
        use_selection=True,export_yup=True,export_extras=True,export_texcoords=uv,
        export_cameras=False,export_lights=False,export_animations=False)


TARGET = Vector((0,-.15,.45))
VIEWS = {'hero': ((-1.35,-5.4,-.72),3.48,(1350,540)),
         'front': ((0,-5,0),3.48,(1280,480)),
         'side': ((-5,0,0),1.03,(520,640)),
         '3q': ((2.8,-4.7,.94),3.18,(1280,560)),
         'back': ((0,5,0),3.47,(960,360))}


def aim(o,target):
    o.rotation_euler = (target-o.location).to_track_quat('-Z','Y').to_euler()


def studio():
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new('Softbox studio')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (.82,.85,.89,1)
    bg.inputs['Strength'].default_value = .19
    def area(name,pos,target,power,sizex,sizey,rgb):
        data = bpy.data.lights.new(name,'AREA')
        data.shape,data.size,data.size_y = 'RECTANGLE',sizex,sizey
        data.energy,data.color = power,rgb
        lamp = obj(name,data)
        lamp.location = pos
        aim(lamp,Vector(target))
    area('Studio | long silk',(-1.3,-2.3,3.1),TARGET,125,3.8,.52,(1,.88,.72))
    area('Studio | face bounce',(.90,-2.2,.92),TARGET,52,2.0,.56,(1,.97,.87))
    area('Studio | grazing brass',(-2.6,-1.4,.42),TARGET,45,.44,1.25,(1,.91,.77))
    area('Studio | rear silk',(0,2.9,1.6),TARGET,105,3.6,1.4,(.94,.97,1))
    area('Studio | edge card',(2,-.4,1.8),TARGET,90,1.4,.38,(1,.84,.63))
    for i,x in enumerate(LAMP_X):
        area(f'Studio | lamp spill {i+1}',on_soffit(x,0,.006),(x,-.208,.51),
             1.7,.067,.044,(1,.69,.34))
    cam = obj('Studio | camera',bpy.data.cameras.new('Orthographic product camera'))
    scene.camera = cam
    cam.data.type = 'ORTHO'
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = False
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    # A separate camera-ray background keeps the near-white backdrop independent of reflections.
    nt = scene.world.node_tree
    background = nt.nodes.new('ShaderNodeBackground')
    background.inputs['Color'].default_value = (.94,.96,1,1)
    background.inputs['Strength'].default_value = 5.0
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(nt.nodes.new('ShaderNodeLightPath').outputs['Is Camera Ray'],mix.inputs[0])
    nt.links.new(bg.outputs[0],mix.inputs[1])
    nt.links.new(background.outputs[0],mix.inputs[2])
    nt.links.new(mix.outputs[0],nt.nodes['World Output'].inputs['Surface'])
    scene.view_layers[0].use_pass_emit = True
    comp = bpy.data.node_groups.new('Studio | optical bloom','CompositorNodeTree')
    scene.compositing_node_group = comp
    comp.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    layers = comp.nodes.new('CompositorNodeRLayers')
    glare = comp.nodes.new('CompositorNodeGlare')
    for socket,value in [('Type','Fog Glow'),('Threshold',.6),('Strength',1.1),('Size',.44)]:
        glare.inputs[socket].default_value = value
    comp.links.new(layers.outputs['Emission'],glare.inputs['Image'])
    add = comp.nodes.new('ShaderNodeMixRGB')
    add.blend_type = 'ADD'
    add.inputs[0].default_value = 1
    comp.links.new(layers.outputs['Image'],add.inputs[1])
    comp.links.new(glare.outputs['Glare'],add.inputs[2])
    comp.links.new(add.outputs[0],comp.nodes.new('NodeGroupOutput').inputs[0])
    set_view('hero')


def set_view(name):
    scene = bpy.context.scene
    delta,scale,(w,h) = VIEWS[name]
    scene.camera.location = TARGET+Vector(delta)
    scene.camera.data.ortho_scale = scale
    aim(scene.camera,TARGET)
    scene.render.resolution_x,scene.render.resolution_y = w,h


def render(name,path):
    set_view(name)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def webp(paths, python):
    try:
        from PIL import Image
    except ImportError:
        if python:
            subprocess.run([python,'-B','-c',
                'from PIL import Image;import sys;from pathlib import Path\n'
                'for p in map(Path,sys.argv[1:]): Image.open(p).save(p.with_suffix(".webp"),quality=91,method=6)',
                *map(str,paths)],check=True)
        elif shutil.which('cwebp'):
            for p in paths:
                subprocess.run(['cwebp','-quiet','-q','91','-m','6',str(p),'-o',str(p.with_suffix('.webp'))],check=True)
        else:
            print('WebP skipped: Pillow and cwebp unavailable')
    else:
        for p in paths:
            with Image.open(p) as image:
                image.save(p.with_suffix('.webp'),quality=91,method=6)


def remove_tree(root):
    for o in list(root.children_recursive)[::-1]+[root]:
        bpy.data.objects.remove(o,do_unlink=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-render',action='store_true')
    parser.add_argument('--export-source',action='store_true',help='Use the saved editable near assembly')
    parser.add_argument('--pillow-python',help='External Python with Pillow and WebP support')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    for d in ('sources','previews','exports','reports'):
        (HERE/d).mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=HERE,prefix='.bake-') as temp:
        scratch = Path(temp)
        # Match the rebuild's add-on configuration when reopening the source.
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if args.export_source:
            bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
            root = bpy.data.objects[ROOT]
            g = {o.name:o for o in root.children}
        else:
            bpy.context.preferences.filepaths.save_version = 0
            bpy.context.scene.unit_settings.system = 'METRIC'
            root,g = hierarchy()
            m = palette()
            enclosure(g,m,False)
            moon(g['Moon_Logo'],m,scratch)
            lettering(g['Letters'],m)
            brushed_finish(m['brass'],root,scratch)
            studio()
            bpy.ops.object.select_all(action='DESELECT')
            root.select_set(True)
            bpy.context.view_layer.objects.active = root
            bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),compress=True)
        export(root,'optimized.glb')
        atlas = bake_graphics([g['Letters'],g['Moon_Logo']],scratch)
        remove_tree(root)
        bpy.data.orphans_purge(do_recursive=True)
        # Load the packed bake again after dropping the near assembly's orphan data.
        atlas = bpy.data.images.load(str(scratch/'New Moon relief bake.png'),check_existing=True)
        atlas.pack()
        root,g = hierarchy()
        m = palette()
        enclosure(g,m,True)
        far_graphics(g,atlas)
        export(root,'far-lod.glb')
        if not args.skip_render:
            # Render the exported materials and topology, including the actual far atlas.
            remove_tree(root)
            bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/far-lod.glb'))
            render('front',HERE/'reports/far-front.png')
            remove_tree(bpy.data.objects[ROOT])
            bpy.ops.import_scene.gltf(filepath=str(HERE/'exports/optimized.glb'))
            paths = []
            for name in ('hero','front','side','3q'):
                path = HERE/'previews'/(name+'.png')
                render(name,path)
                paths.append(path)
            render('back',HERE/'reports/back.png')
            webp(paths,args.pillow_python)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
