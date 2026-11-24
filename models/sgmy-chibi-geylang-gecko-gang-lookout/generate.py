"""Original SG/MY chibi figure. Rebuild: blender -b --python generate.py.
Coordinates use metres; the feet and rig root are at the ground origin.
Blender -Y is forward; glTF +Z is forward. No third-party inputs.
The GLB is a static rest pose with a rigid-weighted skeleton and face keys.
"""
SLUG = 'sgmy-chibi-geylang-gecko-gang-lookout'
TITLE = 'Geylang Gecko Gang Lookout'
ROLE = 'A fictional street rival in a gecko jacket with a sling bag'
STYLE = 'gecko'
HZ, HR, HX, HD = .766, .202, .222, .171
SKIN, EAR_SHADE, BLUSH = '#B78162', '#96604F', '#CF7971'
HAIR, IRIS = '#27212B', '#79533F'
EYE_X, EYE_Z, EYE_SIZE = .086, -.044, (.049,.055)
BROW, MOUTH, SMILE = .001, .044, .032
FRECKLES, MOUSTACHE, EARS, STUDENT = False, False, True, False
TOP_NAME, TOP_MATERIAL = 'Garment', 'Garment Fabric'
TOP, CUFF, HAND, SLEEVE = '#39565B', '#294248', SKIN, .95
PANTS, SOLE, SHOE = '#333541', '#302E32', '#3D363B'
CAM_X, CAM_Z = 1.51, 1.51
ARMS = {
    'L': ((.120,0,.514),(.191,-.028,.376),(.180,-.119,.341),(.181,-.166,.335)),
    'R': ((-.120,0,.514),(-.176,.010,.390),(-.176,-.024,.277),(-.174,-.034,.232)),
}

def shoe_details(p, side, s, xf):
    stroke(p, [xf((s*x,y,z)) for x,y,z in [(-.034,-.058,.046),(0,-.066,.052),(.035,-.051,.046)]], .004, '#D5C5B2')


def outfit(shirt, hips, arms):
    hair = Part('Hair', material('Hair', .38), 'Head')
    hair_shell(hair, HAIR, front=.35, side=-.38, rear=-.70, sweep=.035, locks=8, bulk=.017)
    detail = Part('Clothing Details', material('Clothing Details', .55), 'Chest')
    collar(detail, CUFF, TOP)
    for z in (.39,.435,.48):
        orb(detail, (0,-.094,z), (.005,.004,.005), '#E7D7BC', n=12, rows=6)
    if STYLE == 'auntie':
        # A silver bun and frog closures distinguish the tai chi uniform.
        orb(hair,(0,.115,.837),(.095,.070,.083),HAIR)
        for z in (.38,.42,.46):
            stroke(detail,[(-.045,-.096,z),(.042,-.096,z)],.004,'#D8D0A8')
            orb(detail,(.046,-.095,z),(.009,.006,.009),'#D8D0A8')
        stroke(detail,[(-.105,-.088,.285),(.105,-.088,.285)],.004,'#B8D4B8')
    elif STYLE == 'teacher':
        for s in (-1,1):
            pts=[(s*.086+.058*cos(a),head_front(s*.086+.058*cos(a),HZ-.045+.067*sin(a))-.014,HZ-.045+.067*sin(a)) for a in [2*pi*i/36 for i in range(37)]]
            stroke(hair,pts,.0035,'#41302B')
        stroke(hair,[(-.028,-.178,HZ-.044),(.028,-.178,HZ-.044)],.004,'#41302B')
        book=Part('Workbook',material('Workbook',.62),'Hand.L')
        box(book,(.186,-.171,.338),(.115,.031,.153),.008,'#E9BA64',angle=-.12)
        box(book,(.186,-.191,.338),(.090,.005,.124),.004,'#FFF0CF',angle=-.12)
        for z in (.31,.33,.35,.37): stroke(book,[(.158,-.196,z),(.216,-.196,z)],.002,'#66858B')
    elif STYLE == 'commuter':
        # Long tunic hem, floral embroidery and woven handbag.
        lathe(detail,[(0,0,.192,.143,.085),(0,0,.205,.145,.092),(0,0,.282,.142,.095)],TOP,n=40,power=.75)
        for x in (-.09,0,.09):
            for z in (.23,.27,.31):
                orb(detail,(x,-.096,z),(.009,.004,.009),'#E8BBBE',n=12,rows=6)
        bag=Part('Woven Handbag',material('Woven Handbag',.68),'Hand.L')
        box(bag,(.184,-.17,.285),(.12,.055,.105),.014,'#C89C61')
        for x in (.14,.16,.18,.20,.22): stroke(bag,[(x,-.202,.24),(x,-.202,.325)],.003,'#EDD09B')
        stroke(bag,[(.14,-.17,.326),(.145,-.17,.37),(.21,-.17,.37),(.225,-.17,.326)],.006,'#A97C4D')
    elif STYLE == 'sari':
        orb(hair,(0,.13,.78),(.10,.06,.11),HAIR)
        for i in range(9):
            a=pi*i/8
            orb(hair,(.09*cos(a),.102,.80+.065*sin(a)),(.018,.015,.018),'#FFF0D5',n=14,rows=8)
        stroke(detail,[(-.12,-.077,.52),(-.07,-.102,.45),(.03,-.104,.37),(.13,-.08,.29)],.043,'#D69D47',depth=.009)
        stroke(detail,[(-.12,-.087,.52),(-.07,-.11,.45),(.03,-.11,.37),(.13,-.09,.29)],.006,'#F3CE81')
        lathe(detail,[(0,0,.14,.12,.075),(0,0,.16,.14,.09),(0,0,.275,.14,.09)],TOP,n=40,power=.8)
        stroke(detail,[(-.12,-.077,.16),(0,-.095,.16),(.12,-.077,.16)],.005,'#EAC77D')
        orb(hair,(0,head_front(0,HZ+.06)-.012,HZ+.06),(.009,.004,.009),'#B64247')
    elif STYLE == 'soldier':
        hat=Part('Field Cap',material('Field Cap',.65),'Head')
        lathe(hat,[(0,0,HZ+.13,.18,.14),(0,0,HZ+.18,.16,.13),(0,0,HZ+.205,.11,.10),(0,0,HZ+.21,0,0)],'#53624B',n=40)
        box(hat,(0,-.16,HZ+.13),(.24,.12,.015),.018,'#4B5B46')
        for x,z in [(-.075,.40),(.072,.44),(-.025,.32),(.07,.30)]:
            orb(detail,(x,-.093,z),(.025,.006,.013),'#475B48',n=14,rows=8,angle=.4)
        for s in (-1,1): box(detail,(s*.078,-.092,.395),(.067,.015,.057),.007,'#596B51')
        stroke(detail,[(-.13,-.03,.51),(-.08,-.10,.45),(.08,-.10,.32)],.018,'#475340')
    elif STYLE == 'durian':
        for x in (-.09,-.03,.03,.09):
            for z in (.31,.37,.43,.49):
                stroke(detail,[(x-.015,-.096,z-.015),(x+.015,-.097,z+.015)],.006,'#789E72')
                stroke(detail,[(x+.015,-.097,z-.015),(x-.015,-.096,z+.015)],.004,'#F4D38D')
        fruit=Part('Durian',material('Durian Husk',.72),'Hand.L')
        orb(fruit,(.18,-.16,.36),(.083,.068,.085),'#8F9B48',n=20,rows=12)
        for i in range(40):
            a=i*2.399; z=-.72+1.44*((i%10)/9); r=(1-z*z)**.5
            p=Vector((.18+.083*r*cos(a),-.16+.068*r*sin(a),.36+.085*z))
            v=Vector((r*cos(a),r*sin(a),z))
            tube(fruit,p,p+.022*v,.010,0,'#BBC267',n=7)
        tube(fruit,(.18,-.16,.44),(.19,-.16,.475),.008,.006,'#6D5037')
    elif STYLE == 'student':
        hijab=Part('Plum Hijab',material('Hijab Cloth',.75),'Head')
        lathe(hijab,[(0,0,.525,.105,.09),(0,0,.55,.17,.11),(0,0,.63,.20,.13),(0,.01,.70,.218,.15)],'#76566E',n=48,power=.9)
        stroke(hijab,[(-.16,-.11,.64),(0,-.17,.58),(.16,-.11,.64)],.018,'#9A738D')
        books=Part('Books',material('Book Covers',.6),'Hand.L')
        for i,col in enumerate(('#D8AE65','#6F9A98','#D3CFBC')):
            box(books,(.18,-.16,.29+i*.028),(.15,.09,.023),.004,col,angle=-.08)
    elif STYLE == 'grandfather':
        orb(hair,(0,.1,.81),(.13,.06,.1),HAIR)
        box(detail,(0,-.098,.365),(.21,.022,.23),.015,'#6D5847')
        for z in (.29,.33,.37,.41,.45):
            for x in (-.075,-.025,.025,.075):
                stroke(detail,[(x-.014,-.112,z),(x,-.114,z+.013),(x+.014,-.112,z)],.004,'#D6AF6A')
        cane=Part('Walking Stick',material('Rattan',.52),'Hand.R')
        tube(cane,(-.177,-.034,.01),(-.177,-.034,.27),.008,.009,'#8B6444',n=14)
        stroke(cane,[(-.177,-.034,.27),(-.178,-.034,.30),(-.15,-.034,.31)],.009,'#8B6444')
    elif STYLE == 'gecko':
        stroke(detail,[(0,-.098,.48),(0,-.098,.29)],.004,'#223A40')
        for s in (-1,1): stroke(detail,[(s*.10,-.088,.30),(s*.10,-.09,.39)],.006,'#486B70')
        stroke(detail,[(-.11,-.11,.48),(.12,-.11,.28)],.019,'#D49C56')
        box(detail,(.075,-.134,.31),(.10,.045,.075),.012,'#B8874E')
        # A small fictional gecko mark, never a real gang or brand.
        stroke(detail,[(-.06,-.117,.40),(-.04,-.12,.42),(-.03,-.12,.45)],.006,'#8BC9AE')
        for z in (.41,.43): stroke(detail,[(-.065,-.117,z),(-.025,-.117,z+.01)],.004,'#8BC9AE')
    elif STYLE == 'hornbill':
        stroke(hair,[(-.20,-.10,HZ+.095),(0,-.18,HZ+.095),(.20,-.10,HZ+.095)],.016,'#D95F49')
        box(detail,(0,-.098,.37),(.21,.025,.22),.015,'#6F3632')
        orb(detail,(.055,-.115,.43),(.030,.005,.022),'#E7BD79')
        stroke(detail,[(.045,-.12,.43),(.075,-.12,.45),(.10,-.12,.44)],.006,'#F1D38A')
        stroke(detail,[(-.10,-.114,.29),(.10,-.114,.29)],.006,'#DEA66C')

# Common construction for the SG/MY vinyl figures. Every vertex is authored in
# metres in rest pose: Blender -Y is forward, Z is up, soles touch Z=0.
import math
import os
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

pi = math.pi
sin, cos, sqrt = math.sin, math.cos, math.sqrt
OUT = Path(os.environ.get('CHIBI_OUTPUT', Path(__file__).resolve().parent))
FLOOR = '#D3CFDF'
IVORY = '#FFF0D6'
INK = '#202132'
WHITE = '#FFF9ED'


def srgb(hex_color):
    return tuple(int(hex_color.lstrip('#')[i:i+2], 16) / 255 for i in (0, 2, 4))


def rgba(hex_color):
    return tuple(c / 12.92 if c < .04045 else ((c+.055)/1.055)**2.4
                 for c in srgb(hex_color)) + (1.,)


def material(name, roughness, base=None, spec=.36):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Specular IOR Level'].default_value = spec
    if base:
        shader.inputs['Base Color'].default_value = rgba(base)
    else:
        color = mat.node_tree.nodes.new('ShaderNodeVertexColor')
        color.layer_name = 'Palette'
        mat.node_tree.links.new(color.outputs['Color'], shader.inputs['Base Color'])
    return mat


class Part:
    """One material primitive and UV layer per part; components carry bone IDs."""
    def __init__(self, name, mat, bone):
        self.name, self.mat, self.bone = name, mat, bone
        self.v, self.f, self.uv, self.colors, self.bones = [], [], [], [], []
        self.smooth = []
        parts.append(self)

    def add(self, verts, faces, color, uv=None, smooth=True, bone=None):
        offset = len(self.v)
        self.v.extend(verts)
        self.f.extend(tuple(offset+i for i in f) for f in faces)
        if uv is None:
            uv = [((verts[i][0]+.45)/.9, verts[i][2]/1.15) for f in faces for i in f]
        self.uv.extend(uv)
        self.colors.extend([rgba(color)] * len(verts))
        self.bones.extend([bone or self.bone] * len(verts))
        self.smooth.extend([smooth] * len(faces) if isinstance(smooth, bool) else smooth)

    def bake(self, rig):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.v, [], self.f)
        mesh.update()
        mesh.materials.append(self.mat)
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        uv = mesh.uv_layers.new(name='UV')
        uv.data.foreach_set('uv', [c for pair in self.uv for c in pair])
        if self.name not in {'Head', 'Eyes'}:
            col = mesh.color_attributes.new(name='Palette', type='FLOAT_COLOR', domain='POINT')
            col.data.foreach_set('color', [c for pair in self.colors for c in pair])
        mesh.polygons.foreach_set('use_smooth', self.smooth)
        for name in dict.fromkeys(self.bones):
            group = obj.vertex_groups.new(name=name)
            group.add([i for i, b in enumerate(self.bones) if b == name], 1., 'REPLACE')
        deform = obj.modifiers.new('Character Skin', 'ARMATURE')
        deform.object = rig
        # Deliberately unparented skinned nodes, per section 12 of the chibi standard.
        return obj


def signed_power(value, p):
    return math.copysign(abs(value)**p, value)


def lathe(part, rings, color, n=32, power=1., xf=None, bone=None):
    """Bottom-to-top rings of (cx, cy, z, horizontal radius, depth radius)."""
    pts, faces, uv, ids = [], [], [], []
    for x, y, z, a, b in rings:
        ring = [len(pts)]
        if a == 0:
            pts.append((x, y, z))
        else:
            ring = []
            for j in range(n):
                ang = 2*pi*j/n - pi/2
                ring.append(len(pts))
                pts.append((x+a*signed_power(cos(ang),power), y+b*signed_power(sin(ang),power),z))
        ids.append(ring)
    for i, (low, high) in enumerate(zip(ids, ids[1:])):
        a, b = i/(len(ids)-1), (i+1)/(len(ids)-1)
        for j in range(n):
            k = (j+1)%n
            u, w = j/n, (j+1)/n
            if len(low) == 1:
                faces.append((low[0], high[k], high[j]))
                uv.extend((((u+w)/2,a),(w,b),(u,b)))
            elif len(high) == 1:
                faces.append((low[j], low[k], high[0]))
                uv.extend(((u,a),(w,a),((u+w)/2,b)))
            else:
                faces.append((low[j], low[k], high[k], high[j]))
                uv.extend(((u,a),(w,a),(w,b),(u,b)))
    part.add([xf(p) for p in pts] if xf else pts, faces, color, uv, bone=bone)


def orb(part, center, radii, color, n=20, rows=10, angle=0., bone=None):
    x,y,z = center
    a,b,c = radii
    axis = Matrix.Rotation(angle, 3, 'Y')
    rings = [(0.,0.,-c,0.,0.)]
    rings += [(0.,0.,c*sin(t),a*cos(t),b*cos(t))
              for t in [(i/rows-.5)*pi for i in range(1, rows)]]
    rings += [(0.,0.,c,0.,0.)]
    lathe(part, rings, color, n=n, xf=lambda p: Vector((x,y,z))+axis@Vector(p), bone=bone)


def tube(part, start, end, r1, r2, color, n=20, roundness=.26, bone=None):
    a, d = Vector(start), Vector(end)-Vector(start)
    L = d.length
    rotation = d.to_track_quat('Z','Y')
    f = min(L*.31, min(r1,r2)*roundness)
    rings = [(0,0,0,0,0), (0,0,0,r1*.70,r1*.70), (0,0,f*.33,r1*.93,r1*.93),
             (0,0,f,r1,r1), (0,0,L*.5,(r1+r2)*.5,(r1+r2)*.5),
             (0,0,L-f,r2,r2),(0,0,L-f*.33,r2*.93,r2*.93),
             (0,0,L,r2*.70,r2*.70),(0,0,L,0,0)]
    lathe(part, rings, color, n=n, xf=lambda p: a+rotation@Vector(p), bone=bone)


def box(part, center, dims, radius, color, angle=0., side_angle=0., bone=None):
    """Real three-segment radius bevels on small hard goods and stitched tabs."""
    x,y,z = (d/2 for d in dims)
    verts = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces = [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    tmp = bpy.data.meshes.new('Rounded blank')
    tmp.from_pydata(verts, [], faces)
    tmp.update()
    obj = bpy.data.objects.new('Rounded blank',tmp)
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers.new('Edge radius','BEVEL')
    mod.width, mod.segments = radius, 3
    norm = obj.modifiers.new('Face normals', 'WEIGHTED_NORMAL')
    norm.keep_sharp = True
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    R = Matrix.Rotation(side_angle,3,'Z') @ Matrix.Rotation(angle,3,'Y')
    v = [Vector(center)+R@p.co for p in mesh.vertices]
    f = [tuple(p.vertices) for p in mesh.polygons]
    uv = []
    for p in mesh.polygons:
        dominant = max(range(3), key=lambda i: abs(p.normal[i]))
        u,w = [i for i in range(3) if i != dominant]
        for index in p.vertices:
            point = mesh.vertices[index].co
            uv.append((.5+point[u]/dims[u], .5+point[w]/dims[w]))
    # The middle of each box face stays flat; small bevel faces shade smoothly.
    part.add(v,f,color,uv,smooth=[p.area < max(dims)**2*.019 for p in mesh.polygons],bone=bone)
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(tmp)


def stroke(part, points, width, color, depth=None, normal=(0, -1, 0), n=10, bone=None):
    """Sewn piping / swept ribbon, with rounded ends and an elliptical section."""
    P = list(map(Vector, points))
    N = Vector(normal)
    V, F, UV = [], [], []
    for i,p in enumerate(P):
        t = (P[min(i+1,len(P)-1)]-P[max(0,i-1)]).normalized()
        u = N.cross(t).normalized()
        v = t.cross(u).normalized()
        taper = .48 if i in (0,len(P)-1) else 1.
        for j in range(n):
            th = 2*pi*j/n
            V.append(p+taper*(u*width*cos(th)+v*(depth or width)*sin(th)))
    V.extend((P[0],P[-1]))
    for i in range(len(P)-1):
        for j in range(n):
            k = (j+1)%n
            F.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
            UV.extend(((j/n,i/(len(P)-1)),((j+1)/n,i/(len(P)-1)),
                       ((j+1)/n,(i+1)/(len(P)-1)),(j/n,(i+1)/(len(P)-1))))
    for j in range(n):
        k = (j+1)%n
        F.extend(((len(V)-2,k,j),((len(P)-1)*n+j,(len(P)-1)*n+k,len(V)-1)))
        UV.extend(((.5,0),((j+1)/n,.01),(j/n,.01),(j/n,.99),((j+1)/n,.99),(.5,1)))
    part.add(V,F,color,UV,bone=bone)


def label(part, text, center, width, color, side_angle=0, tilt=0, bone=None):
    """Blender's built-in Bfont, turned into solid, UV-mapped marks."""
    data = bpy.data.curves.new('Lettering', type='FONT')
    data.body, data.align_x, data.align_y = text, 'CENTER', 'CENTER'
    data.size, data.space_character, data.extrude = 1., 1.10, .012
    obj = bpy.data.objects.new('Lettering',data)
    bpy.context.collection.objects.link(obj)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    xs = [v.co.x for v in mesh.vertices]
    scale = width/(max(xs)-min(xs))
    R = Matrix.Rotation(side_angle,3,'Z') @ Matrix.Rotation(tilt,3,'Y')
    verts = [Vector(center)+R@Vector((v.co.x*scale,-v.co.z*scale,v.co.y*scale)) for v in mesh.vertices]
    part.add(verts,[tuple(p.vertices) for p in mesh.polygons],color,smooth=False,
             uv=[(mesh.vertices[i].co.x*scale/width+.5, mesh.vertices[i].co.y*scale/width+.5)
                 for p in mesh.polygons for i in p.vertices],bone=bone)
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.curves.remove(data)


def g(x):
    return math.exp(-x*x)


def profile(z):
    h = min(1., abs((z-HZ)/HR))
    return (max(0.,1.-h*h)**.39) * (1.-.07*(z-HZ)/HR)


def nose_relief(x,z):
    return .020*g(x/.025)*g((z-(HZ-.071))/.020)+.007*g(x/.018)*g((z-(HZ-.035))/.048)


def head_front(x,z):
    r = profile(z)
    xx = min(.9999, abs(x)/max(r*HX,.0001))
    contour = (1-xx**(2/.91))**(.91/2)
    return -HD*r*contour*1.025 - nose_relief(x,z)


def head_image():
    # Orthographic facial paint in the upper UV island; the back uses the lower strip.
    N = 1024
    U,V = np.meshgrid((np.arange(N,dtype=np.float32)+.5)/N,(np.arange(N,dtype=np.float32)+.5)/N)
    X, Z = (U-.5)*.52, (V-.715)*.90
    img = np.ones((N,N,4),np.float32)
    img[:,:,:3] = srgb(SKIN)

    def paint(mask, color, island=None):
        mask = (mask*((V>.46) if island is None else island))[:,:,None]
        img[:,:,:3] *= 1-mask
        img[:,:,:3] += mask*np.array(srgb(color),np.float32)

    def soft(dist, strength=1):
        return np.clip(.5-dist*1.5,0,1)*strength

    for s in (-1,1):
        x = X*s-EYE_X
        paint(.48*np.exp(-((x-.025)/.043)**2-((Z+.105)/.021)**2), BLUSH)
        xb = x/.049
        brow = -.039 + .100 + BROW * s + .013*(1-xb**2)-.006*xb
        dist = np.sqrt((np.maximum(abs(x)-.037,0)/.0045)**2 + ((Z-brow)/.0052)**2)
        paint(soft((dist-1)*3), HAIR)
        # A short closed lash line appears only when the eye mesh is retracted.
        closed = EYE_Z - .005 - .008*(1-(x/.041)**2)
        dist = np.sqrt((np.maximum(abs(x)-.036,0)/.002)**2 + ((Z-closed)/.0023)**2)
        paint(soft((dist-1)*2), HAIR)
        if FRECKLES:
            for i in range(4):
                dist = np.sqrt(((x-.002-i*.010)/.0022)**2+((Z+.100+.007*sin(i*1.8+s))/.0021)**2)
                paint(soft((dist-1)*2,.69),'#9D5847')
    if MOUSTACHE:
        for s in (-1,1):
            d = np.sqrt(((X*s-.018)/.021)**2 + ((Z+.118-.22*(.018-X*s))/.0085)**2)
            paint(soft((d-1)*4), HAIR)
    mouth_z = -.129 if not MOUSTACHE else -.143
    # A continuous crescent with a lip accent, teeth and a coloured tongue.
    u = X/MOUTH
    arc = np.sqrt(np.clip(1-u*u,0,1))
    top = mouth_z-.008*(1-u*u)
    bottom = mouth_z-SMILE*arc
    paint(soft(np.maximum.reduce((abs(u)*MOUTH-MOUTH,Z-top,bottom-Z))*950), '#602D35')
    enamel = np.maximum.reduce((abs(u)*MOUTH-MOUTH*.94,Z-top+.0007,top-.006*arc-Z,bottom-Z))
    paint(soft(enamel*1100), '#FFF2DC')
    lip = np.sqrt((X/(MOUTH*.68))**2+((Z-(mouth_z-SMILE*1.03))/.010)**2)
    paint(soft(np.maximum((lip-1)*3,(bottom-Z)*1700)), '#D77875')
    # Both glossy eye plates sample this same texture, with padding outside each UV disk.
    for side in (-1,1):
        ex,ey = (U-(.50+side*.23))/.163,(V-.265)/.152
        tile = (abs(ex)<1.09)&(abs(ey)<1.09)
        def ellipse(cx,cy,rx,ry):
            return soft((np.sqrt(((ex-cx)/rx)**2+((ey-cy)/ry)**2)-1)*130)
        paint(np.ones_like(V),HAIR,tile)
        paint(ellipse(.0,-.049,.952,.951),'#FFF6E9',tile)
        ix = -.075*side
        paint(ellipse(ix,-.034,.743,.861),'#37282F',tile)
        paint(ellipse(ix,-.034,.670,.792),IRIS,tile)
        paint(.47*ellipse(ix,.025,.632,.687)*np.clip((ey+.23)*1.4,0,1),'#37282F',tile)
        paint(ellipse(ix-.015,.056,.470,.613),'#241923',tile)
        paint(ellipse(ix-.208,.361,.163,.194),'#FFFAEE',tile)
        paint(ellipse(ix+.276,-.291,.088,.081),'#FFEFDB',tile)
    image = bpy.data.images.new('Face Paint',N,N,alpha=False,float_buffer=False)
    image.colorspace_settings.name = 'sRGB'
    image.pixels.foreach_set(img.ravel())
    image.pack()
    return image


def build_head():
    mat = material('Painted Face',.44,SKIN,spec=.25)
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = head_image()
    mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    head = Part('Head',mat,'Head')
    n, rows = 88, 60
    rings = [(0,0,HZ-HR,0,0)]
    for i in range(1,rows):
        z = HZ+HR*sin((i/rows-.5)*pi)
        r = profile(z)
        rings.append((0,0,z,HX*r,HD*r))
    rings += [(0,0,HZ+HR,0,0)]
    def form(p):
        x,y,z = p
        return x, y*(1.025 if y<0 else .975)-(nose_relief(x,z) if y<0 else 0), z
    lathe(head,rings,SKIN,n=n,power=.91,xf=form)
    # Isolate the painted face from both cheeks and rear; the rear still has real UVs.
    offset = 0
    for f in head.f:
        front = sum(head.v[i][1] for i in f) < -.0001
        for j,i in enumerate(f):
            x,y,z = head.v[i]
            u,v = head.uv[offset+j]
            head.uv[offset+j] = (x/.52+.5,(z-HZ)/.90+.715) if front else (u,.024+.066*v)
        offset += len(f)
    if EARS:
        ears = Part('Ears',resin,'Head')
        for s in (-1,1):
            orb(ears,(s*HX*.975,-.004,HZ-.052),(.032,.026,.046),SKIN,angle=s*.18)
            orb(ears,(s*HX*1.035,-.025,HZ-.052),(.015,.006,.026),EAR_SHADE,angle=s*.18)
    return head


def build_eyes():
    mat = material('Gloss Eyes',.31,WHITE,spec=.17)
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images['Face Paint']
    mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    eyes = Part('Eyes',mat,'Head')
    n,rings = 48,8
    for side in (-1,1):
        x,z = side*EYE_X,HZ+EYE_Z
        rx,rz = EYE_SIZE
        tilt = -side*.09
        u0 = .50+side*.23
        V, F, UV = [(x,head_front(x,z)-.010,z)], [], [(u0,.265)]
        for ri in range(1,rings+1):
            q = ri/rings
            for j in range(n):
                a = 2*pi*j/n
                u,v = q*cos(a),q*sin(a)
                dx,dz = u*rx,v*rz
                X,Z = x+dx*cos(tilt)+dz*sin(tilt), z-dx*sin(tilt)+dz*cos(tilt)
                V.append((X,head_front(X,Z)-.0018-.0082*(1-q*q),Z))
                UV.append((u0+u*.163,.265+v*.152))
        for j in range(n):
            k = (j+1)%n
            F.append((0,1+j,1+k))
            for ri in range(rings-1):
                i = 1+ri*n
                F.append((i+j,i+n+j,i+n+k,i+k))
        eyes.add(V,F,WHITE,[UV[i] for f in F for i in f])
    return eyes


def hair_shell(part,color,front=.28,side=-.40,rear=-.65,sweep=.04,locks=7,bulk=.018):
    # Locks are broad, rounded lobes of a continuous cap. No pointed tips.
    n, rings = 84, 17
    V, F, UV = [], [], []
    for i in range(rings):
        q = i/rings
        for j in range(n):
            t = 2*pi*j/n
            ct = cos(t)
            edge = side+(front-side)*max(0,ct)**1.45+(rear-side)*max(0,-ct)**1.4
            wave = .5+.5*cos(locks*t + 1.4*sin(t)+2.0*q)
            edge += sweep*sin(2*t)-(.15 if ct>0 else .035)*wave**1.5
            a = edge+(pi/2-edge)*q
            z = HZ+(HR+bulk*.66)*sin(a)
            z += bulk*(.53+.45*wave)*cos(a)**2*g((q-.42)/.48)
            r = profile(HZ+HR*sin(a))
            rel = bulk*(.79+.55*wave)*cos(a)
            x = (HX*r+rel)*signed_power(sin(t),.91)
            y = -(HD*r+rel)*signed_power(ct,.91)
            V.append((x,y,z))
    V += [(0,0,HZ+HR+bulk*.66),(0,0,HZ-.023)]
    for j in range(n):
        k = (j+1)%n
        for i in range(rings-1):
            F.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
            UV.extend(((j/n,i/rings),((j+1)/n,i/rings),((j+1)/n,(i+1)/rings),(j/n,(i+1)/rings)))
        F.append(((rings-1)*n+j,(rings-1)*n+k,len(V)-2))
        UV.extend(((j/n,1-1/rings),((j+1)/n,1-1/rings),((j+.5)/n,1)))
        F.append((k,j,len(V)-1))
        UV.extend((((j+1)/n,0),(j/n,0),((j+.5)/n,.01)))
    part.add(V,F,color,UV)


def fringe(part,color,arcs):
    for x0,z0,x1,z1,w in arcs:
        pts = []
        for i in range(10):
            t = i/9
            x = x0+(x1-x0)*t + sin(pi*t)*.016
            z = HZ+z0+(z1-z0)*t
            y = head_front(x,z)-.012-.009*sin(pi*t)
            pts.append((x,y,z))
        stroke(part,pts,w,color,depth=.022,n=16)


def make_rig():
    arm = bpy.data.armatures.new(TITLE+' Skeleton')
    rig = bpy.data.objects.new(TITLE,arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.show_in_front = True
    bpy.ops.object.mode_set(mode='EDIT')
    def bone(name, a,b,parent=None):
        e = arm.edit_bones.new(name)
        e.head,e.tail = a,b
        if parent:
            e.parent = arm.edit_bones[parent]
    bone('Root',(0,0,0),(0,0,.145))
    bone('Hips',(0,0,.24),(0,0,.34),'Root')
    bone('Chest',(0,0,.34),(0,0,HZ-.20),'Hips')
    bone('Head',(0,0,HZ-.20),(0,0,HZ+.14),'Chest')
    for side,s in [('L',1),('R',-1)]:
        a,b,c,d = ARMS[side]
        bone('UpperArm.'+side,a,b,'Chest')
        bone('Forearm.'+side,b,c,'UpperArm.'+side)
        bone('Hand.'+side,c,d,'Forearm.'+side)
        a,b,c = (s*.071,0,.269),(s*.079,0,.159),(s*.093,.012,.064)
        bone('Thigh.'+side,a,b,'Hips')
        bone('Shin.'+side,b,c,'Thigh.'+side)
        bone('Foot.'+side,c,(s*.096,-.099,.043),'Shin.'+side)
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def torso():
    top = HZ-HR+.007
    p = Part(TOP_NAME,cloth,'Chest')
    lathe(p,[(0,0,.251,0,0),(0,0,.245,.105,.062),(0,0,.258,.131,.083),
             (0,0,.293,.138,.091),(0,0,.382,.132,.091),(0,0,.456,.139,.079),
             (0,0,.493,.136,.076),(0,0,min(top-.052,.54),.130,.070),
             (0,0,top-.022,.092,.062),(0,0,top-.016,.047,.044),(0,0,top-.016,0,0)],TOP,
          n=56,power=.78)
    tube(p,(0,0,top-.039),(0,0,top+.028),.064,.067,SKIN,n=32)
    return p


def standard_clothes():
    hips = Part('Waist',fabric,'Hips')
    lathe(hips,[(0,0,.207,0,0),(0,0,.216,.101,.051),(0,0,.231,.125,.064),
                (0,0,.256,.127,.077),(0,0,.294,.111,.073),(0,0,.31,0,0)],PANTS,n=40,power=.86)
    limb_parts = {}
    for side,s in [('L',1),('R',-1)]:
        a,b,c,d = list(map(Vector,ARMS[side]))
        ua,fa,ha = 'UpperArm.'+side,'Forearm.'+side,'Hand.'+side
        arm = Part('Arm.'+side,cloth,ua)
        sewn = a.lerp(b,SLEEVE)
        shoulder = a.lerp(b,-.27)
        axis_sleeve = sewn-shoulder
        length = axis_sleeve.length
        axis_sleeve = axis_sleeve.to_track_quat('Z','Y')
        lathe(arm,[(0,0,0,0,0),(0,0,length*.13,.029,.034),
                   (0,0,length*.28,.044,.047),(0,0,length*.45,.050,.052),
                   (0,0,length*.83,.048,.048),(0,0,length,.044,.044),
                   (0,0,length,0,0)],TOP,n=26,xf=lambda p: shoulder+axis_sleeve@Vector(p))
        tube(arm,sewn.lerp(a,.11),sewn.lerp(b,.045),.0475,.0475,CUFF)
        if SLEEVE < .85:
            tube(arm,sewn.lerp(a,.16),b,.036,.035,SKIN)
        orb(arm,b,(.035,.035,.035),SKIN if SLEEVE<.85 else TOP,n=20,rows=10,bone=fa)
        tube(arm,b,c+(d-c)*.14,.034,.026,SKIN if SLEEVE<.85 else TOP,bone=fa)
        hand = c.lerp(d,.56)
        axis = d-c
        tube(arm,c-axis*.11,d,.028,.030,HAND,n=24,roundness=.76,bone=ha)
        orb(arm,hand+Vector((-s*.021,-.013,.006)),(.015,.020,.023),HAND,n=16,rows=10,angle=s*.26,bone=ha)
        limb_parts[side] = arm
        leg = Part('Leg.'+side,fabric,'Thigh.'+side)
        if STUDENT:
            tube(leg,(s*.083,0,.112),(s*.074,0,.255),.039,.047,SKIN,n=24,bone='Shin.'+side)
            tube(leg,(s*.091,.011,.052),(s*.082,.002,.130),.039,.043,IVORY,n=24,bone='Shin.'+side)
            tube(leg,(s*.082,.002,.119),(s*.082,.001,.132),.043,.043,WHITE,bone='Shin.'+side)
        else:
            lathe(leg,[(s*.093,.012,.055,0,0),(s*.092,.010,.057,.038,.038),
                       (s*.091,.010,.065,.046,.045),(s*.087,.006,.098,.047,.046),
                       (s*.081,.001,.145,.050,.050),(s*.079,0,.163,.050,.051),
                       (s*.073,.001,.215,.055,.056),(s*.067,.003,.261,.059,.055),
                       (s*.064,.005,.278,0,0)],PANTS,n=32,power=.89)
            leg.bones = ['Shin.'+side if p[2]<.163 else 'Thigh.'+side for p in leg.v]
        shoe = Part('Shoe.'+side,rubber,'Foot.'+side)
        R = Matrix.Rotation(s*.11,3,'Z')
        xf = lambda p: Vector((s*.092,-.044,0))+R@Vector(p)
        lathe(shoe,[(0,0,0,0,0),(0,0,0,.045,.075),(0,0,.005,.060,.087),
                    (0,0,.013,.064,.090),(0,0,.026,.061,.087),(0,0,.030,.050,.073),(0,0,.030,0,0)],
              SOLE,n=36,power=.73,xf=xf)
        lathe(shoe,[(0,0,.021,0,0),(0,0,.022,.060,.085),(0,0,.033,.061,.086),
                    (-s*.001,.001,.051,.059,.078),(0,.016,.068,.053,.061),
                    (0,.031,.081,.048,.047),(0,.040,.084,.034,.034),(0,.040,.084,0,0)],
              SHOE,n=36,power=.79,xf=xf)
        shoe_details(shoe,side,s,xf)
    return hips,limb_parts


def collar(part,light,dark):
    h = HZ-HR
    # The collar stand blends into two broad, rounded fall pieces.
    lathe(part,[(0,0,h-.045,.079,.066),(0,0,h-.031,.079,.067),
                (0,0,h-.008,.060,.059),(0,0,h-.005,.058,.057)],dark,n=40)
    for s in (-1,1):
        stroke(part,[(s*.066,-.042,h-.020),(s*.066,-.065,h-.036),
                     (s*.044,-.081,h-.058),(s*.025,-.088,h-.075)],.018,light,depth=.006)
    box(part,(0,-.085,h-.111),(.013,.007,.062),.003,dark)


def set_expressions(head,eyes):
    head.shape_key_add(name='neutral',from_mix=False)
    for name in ('smile','surprised'):
        key = head.shape_key_add(name=name,from_mix=False)
        key.value = 0.
        for i,vertex in enumerate(head.data.vertices):
            x,y,z = vertex.co
            if y >= -.05:
                continue
            z0 = HZ-(.136 if not MOUSTACHE else .153)
            mouth = g((x/(MOUTH*1.52)))*g((z-z0)/.041)
            cheeks = g((abs(x)-.114)/.049)*g((z-(HZ-.108))/.025)
            brow = g((abs(x)-EYE_X)/.067)*g((z-(HZ+.071))/.022)
            if name == 'smile':
                key.data[i].co = (x+x*.29*mouth,y-.005*cheeks,z+.011*cheeks+.009*mouth)
            else:
                key.data[i].co = (x-x*.50*mouth,y-.013*mouth,z+(z-z0)*.59*mouth+.022*brow)
    eyes.shape_key_add(name='open',from_mix=False)
    blink = eyes.shape_key_add(name='blink',from_mix=False)
    blink.value = 0.
    for v in blink.data:
        v.co.y += .048


def area(name,location,direction,power,size,color):
    data = bpy.data.lights.new(name,'AREA')
    data.energy,data.shape,data.size,data.color = power,'DISK',size,color
    obj = bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(direction)-obj.location).to_track_quat('-Z','Y').to_euler()


def preview():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = int(os.environ.get('CHIBI_SAMPLES','17'))
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.resolution_x,scene.render.resolution_y = 800,900
    scene.render.resolution_percentage = int(os.environ.get('CHIBI_RENDER_PERCENT','55'))
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    world = bpy.data.worlds.new('Lavender Studio')
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (.68,.70,.82,1)
    bg.inputs['Strength'].default_value = .42
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.001))
    bpy.context.object.data.materials.append(material('Lavender Floor',.83,FLOOR))
    area('Large key',(-2.7,-3.6,4.5),(0,0,.58),945,4.5,(1,.88,.77))
    area('Cool fill',(2.2,-2.5,2.6),(0,0,.6),394,4.2,(.73,.85,1.))
    area('Crown rim',(-1.2,1.8,3.3),(0,0,.63),720,3.15,(1,.80,.89))
    area('Eye bounce',(.15,-3,1.3),(0,0,.67),86,4.5,(1,.97,.94))
    camdata = bpy.data.cameras.new('Portrait')
    cam = bpy.data.objects.new('Portrait',camdata)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    camdata.type,camdata.ortho_scale = 'ORTHO',1.86
    views = {'hero':(CAM_X,-3.8,CAM_Z),'front':(0,-4,.52),'back':(0,4,.52),
             'side':(4,0,.52),'reverse':(-2.2,-3.8,1.1),'rear':(2.2,3.8,1.1)}
    for name in os.environ.get('CHIBI_VIEWS','hero').split(','):
        cam.location = Vector(views[name])*1.5
        cam.rotation_euler = (Vector((0,0,.7725))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath = str(OUT/('preview.png' if name=='hero' else 'inspection-'+name+'.png'))
        bpy.ops.render.render(write_still=True)


def build():
    global parts,resin,cloth,fabric,rubber
    bpy.ops.wm.read_factory_settings(use_empty=True)
    unit = bpy.context.scene.unit_settings
    unit.system,unit.scale_length = 'METRIC',1.
    parts = []
    resin = material('Soft Vinyl',.40)
    cloth = material(TOP_MATERIAL,.55)
    fabric = material('Woven Trousers',.62)
    rubber = material('Moulded Footwear',.44)
    rig = make_rig()
    rig['Asset ID'] = SLUG
    rig['Purpose'] = ROLE
    rig['Facing'] = 'glTF +Z; +Y up'
    rig['origin_note'] = 'Ground level between the soles'
    rig['Provenance'] = 'Original Blender procedural sculpture; no external inputs'
    rig['Rig'] = 'Rigid weighted vinyl figure, 16 bones, rest pose only'
    head = build_head()
    eyes = build_eyes()
    shirt = torso()
    hips, arms = standard_clothes()
    outfit(shirt,hips,arms)
    objs = {part.name:part.bake(rig) for part in parts}
    set_expressions(objs[head.name],objs[eyes.name])
    for obj in objs.values():
        obj.data.transform(Matrix.Scale(1.5, 4), shape_keys=True)
    rig.data.transform(Matrix.Scale(1.5, 4))
    for obj, extra in ((objs['Head'],'neutral basis, smile, surprised'),(objs['Eyes'],'open basis, blink')):
        obj['Expression Keys'] = extra
    OUT.mkdir(parents=True,exist_ok=True)
    if not os.environ.get('CHIBI_SKIP_EXPORT'):
        bpy.ops.export_scene.gltf(filepath=str(OUT/'model.glb'),export_format='GLB',
            export_yup=True,export_animations=False,export_extras=True,
            export_morph_normal=True,export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=7,export_draco_position_quantization=15,
            export_draco_normal_quantization=11,export_draco_texcoord_quantization=13,
            export_draco_color_quantization=10,export_draco_generic_quantization=10)
    if not os.environ.get('CHIBI_SKIP_PREVIEW'):
        preview()


if __name__ == '__main__':
    build()
