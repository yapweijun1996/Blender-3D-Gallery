"""SG/MY vinyl figures: Singapore neighbourhood patrol officer (fictional uniform).
Rebuild with blender -b --python generate.py (Blender 5.2.3 LTS).
The uniform, insignia and character are original, with no external assets.
"""
SLUG = 'sgmy-chibi-police-officer'
TITLE = 'Neighbourhood Patrol Officer'
ROLE = 'Singapore-inspired neighbourhood police officer in a fictional navy uniform'
HZ, HR, HX, HD = .786, .201, .208, .174
SKIN, EAR_SHADE, BLUSH = '#C58259', '#A9574F', '#CF635C'
HAIR, IRIS = '#2F2731', '#805449'
EYE_X, EYE_Z, EYE_SIZE = .083, -.037, (.047,.052)
BROW, MOUTH, SMILE = .003, .038, .021
FRECKLES, MOUSTACHE, EARS, STUDENT = False, False, True, False
TOP_NAME, TOP_MATERIAL = 'Patrol Shirt', 'Ink Navy Uniform'
TOP, CUFF, HAND, SLEEVE = '#254264', '#1C304F', SKIN, .53
PANTS, SOLE, SHOE = '#232F44', '#202232', '#2E3346'
CAM_X = 1.34
CAM_Z = 1.22
ARMS = {
    'L': ((.123,.008,.523),(.178,.020,.391),(.171,-.018,.276),(.159,-.031,.235)),
    'R': ((-.121,-.004,.526),(-.193,-.014,.385),(-.151,-.102,.344),(-.105,-.119,.348)),
}


def shoe_details(p, side, s, xf):
    for y,z in [(-.054,.053),(-.035,.060),(-.016,.067)]:
        stroke(p,[xf((-.032,y+.010,z-.008)),xf((0,y,z)),xf((.032,y+.010,z-.008))],.0041,'#48516A')
    for x in (-.052,.052):
        box(p,xf((x,-.014,.011)),(.019,.123,.013),.004,'#333747')


def outfit(shirt,hips,arms):
    hair = Part('Hair',material('Espresso Hair',.34),'Head')
    hair_shell(hair,HAIR,front=.59,side=-.26,rear=-.60,sweep=.042,locks=7,bulk=.012)
    # Compress the upper locks into the cap instead of letting them pierce the band.
    for i,(x,y,z) in enumerate(hair.v):
        t = min(1.,max(0.,(z-HZ-.078)/.022))
        fit = 1-.13*t*t*(3-2*t)
        hair.v[i] = (x*fit,y*fit,z)
    orb(hair,(.042,.162,HZ-.079),(.081,.067,.069),HAIR,n=32,rows=20)
    for off in (-.038,0,.038):
        pts = [(.042+off*.9+.046*cos(a),.187+.026*sin(a),HZ-.094+.051*sin(a)) for a in [i*pi/15 for i in range(16)]]
        stroke(hair,pts,.014,'#40303B',depth=.011,normal=(0,0,1))
    cap = Part('Peaked Patrol Cap',material('Navy Cap Twill',.52),'Head')
    h = HZ+.091
    lathe(cap,[(0,0,h-.024,0,0),(0,0,h-.023,.195,.168),(0,0,h-.018,.213,.180),
               (0,.001,h-.002,.215,.181),(0,.005,h+.040,.202,.174),
               (0,.006,h+.045,.168,.143),(0,.006,h+.047,0,0)],'#263B54',n=56)
    lathe(cap,[(0,.006,h+.025,0,0),(0,.006,h+.026,.175,.142),(0,.003,h+.032,.205,.166),
               (0,.001,h+.057,.215,.178),(0,.007,h+.088,.199,.167),(0,.016,h+.122,.153,.140),
               (0,.024,h+.134,.072,.072),(0,.024,h+.136,0,0)],'#294266',n=52,power=.94)
    lathe(cap,[(0,-.115,h-.024,0,0),(0,-.125,h-.023,.116,.086),(0,-.131,h-.018,.180,.098),
               (0,-.128,h-.012,.183,.099),(0,-.128,h-.005,.171,.093),(0,-.119,h+.003,.124,.079),
               (0,-.089,h+.005,0,0)],'#22242E',n=52,power=.9)
    gold = '#D8A86A'
    box(cap,(0,-.174,h+.040),(.048,.012,.047),.010,'#101F37')
    box(cap,(0,-.182,h+.046),(.032,.009,.023),.004,gold)
    box(cap,(0,-.182,h+.033),(.018,.009,.018),.003,gold,angle=pi/4)
    stroke(cap,[(-.008,-.188,h+.053),(0,-.190,h+.043),(.008,-.188,h+.053)],.0028,'#754F48')

    collar(shirt,'#395E7B','#213750')
    for s in (-1,1):
        box(shirt,(s*.075,-.078,.428),(.080,.019,.061),.008,'#284A6B',side_angle=s*.17)
        box(shirt,(s*.075,-.092,.449),(.082,.012,.021),.004,'#3B6280',side_angle=s*.17)
        orb(shirt,(s*.073,-.100,.440),(.005,.003,.005),gold,n=12,rows=8)
        arm = arms['L' if s>0 else 'R']
        upper = 'UpperArm.'+('L' if s>0 else 'R')
        box(arm,(s*.130,-.002,.545),(.073,.057,.014),.005,'#1D2E4A',angle=s*.42,bone=upper)
        for i in range(2):
            box(arm,(s*(.124+i*.012),-.004,.554-i*.004),(.005,.037,.003),.001,'#8AA8B1',angle=s*.42,bone=upper)
        box(shirt,(0,-.086,.333+.039*(s+1)),(.005,.007,.059),.002,'#2D4C68')
    box(shirt,(.066,-.090,.478),(.095,.013,.025),.005,'#142843',side_angle=.15)
    label(shirt,'POLICE',(.066,-.097,.478),.079,'#E3E1C9',side_angle=.15)
    box(shirt,(-.074,-.090,.479),(.050,.014,.024),.004,'#9F514E',side_angle=-.16)
    box(shirt,(-.074,-.098,.474),(.049,.004,.009),.002,'#F3D6BE',side_angle=-.16)
    label(shirt,'S G',(-.074,-.101,.485),.022,IVORY,side_angle=-.16)
    box(shirt,(0,.081,.463),(.159,.013,.044),.008,'#1C304C',side_angle=pi)
    label(shirt,'PATROL',(0,.090,.463),.128,'#B8C6BD',side_angle=pi)

    utility = Part('Utility Belt',material('Utility Nylon',.61),'Hips')
    lathe(utility,[(0,0,.252,.135,.091),(0,0,.255,.142,.096),(0,0,.279,.143,.098),
                   (0,0,.284,.141,.096),(0,0,.284,.129,.079),(0,0,.252,.129,.079)],'#1E2639',n=56,power=.76)
    box(utility,(0,-.101,.267),(.057,.020,.034),.006,'#456275')
    box(utility,(0,-.112,.268),(.033,.006,.019),.004,'#253747')
    box(utility,(.117,.035,.267),(.050,.056,.066),.008,'#28344A',side_angle=-.15)
    box(utility,(.126,.041,.287),(.053,.055,.022),.004,'#3D4E61',side_angle=-.15)
    radio = Part('Shoulder Radio',material('Radio Polymer',.42),'Chest')
    box(radio,(-.120,-.053,.494),(.047,.028,.062),.007,'#1B2335',side_angle=-.34,angle=-.21)
    tube(radio,(-.134,-.051,.519),(-.140,-.048,.554),.0048,.0039,'#1B2335',n=12)
    for i in range(3):
        box(radio,(-.120,-.069,.480+i*.009),(.023,.004,.003),.001,'#63788D',side_angle=-.34,angle=-.18)
    orb(radio,(-.109,-.072,.513),(.005,.003,.004),'#EDB862',n=12,rows=8)

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
    scene.render.resolution_percentage = int(os.environ.get('CHIBI_RENDER_PERCENT','85'))
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
    area('Large key',(-2.7,-3.6,4.5),(0,0,.58),420,3.0,(1,.88,.77))
    area('Cool fill',(2.2,-2.5,2.6),(0,0,.6),175,2.8,(.73,.85,1.))
    area('Crown rim',(-1.2,1.8,3.3),(0,0,.63),320,2.1,(1,.80,.89))
    area('Eye bounce',(.15,-3,1.3),(0,0,.67),38,3,(1,.97,.94))
    camdata = bpy.data.cameras.new('Portrait')
    cam = bpy.data.objects.new('Portrait',camdata)
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    camdata.type,camdata.ortho_scale = 'ORTHO',1.24
    views = {'hero':(CAM_X,-3.8,CAM_Z),'front':(0,-4,.52),'back':(0,4,.52),
             'side':(4,0,.52),'reverse':(-2.2,-3.8,1.1),'rear':(2.2,3.8,1.1)}
    for name in os.environ.get('CHIBI_VIEWS','hero').split(','):
        cam.location = views[name]
        cam.rotation_euler = (Vector((0,0,.515))-cam.location).to_track_quat('-Z','Y').to_euler()
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
    rig['Facing'] = 'glTF +Z; +Y up; origin between soles'
    rig['Provenance'] = 'Original Blender procedural sculpture; no external inputs'
    rig['Rig'] = 'Rigid weighted vinyl figure, 16 bones, rest pose only'
    head = build_head()
    eyes = build_eyes()
    shirt = torso()
    hips, arms = standard_clothes()
    outfit(shirt,hips,arms)
    objs = {part.name:part.bake(rig) for part in parts}
    set_expressions(objs[head.name],objs[eyes.name])
    for obj, extra in ((objs['Head'],'neutral basis, smile, surprised'),(objs['Eyes'],'open basis, blink')):
        obj['Expression Keys'] = extra
    OUT.mkdir(parents=True,exist_ok=True)
    if not os.environ.get('CHIBI_SKIP_EXPORT'):
        bpy.ops.export_scene.gltf(filepath=str(OUT/(SLUG+'.glb')),export_format='GLB',
            export_yup=True,export_animations=False,export_extras=True,
            export_morph_normal=True,export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=7,export_draco_position_quantization=15,
            export_draco_normal_quantization=11,export_draco_texcoord_quantization=13,
            export_draco_color_quantization=10,export_draco_generic_quantization=10)
    if not os.environ.get('CHIBI_SKIP_PREVIEW'):
        preview()


if __name__ == '__main__':
    build()
