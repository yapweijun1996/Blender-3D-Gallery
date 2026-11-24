"""Butterworth Ferry Ticket Clerk: a rigged SG/MY vinyl figure with a painted expression atlas.
Rebuild: blender -b --factory-startup --python generate.py
All shapes, colours and markings are procedural. No external assets.
"""
SLUG, TITLE, ROLE = 'sgmy-chibi-butterworth-ferry-ticket-clerk', 'Butterworth Ferry Ticket Clerk', 'A nostalgic Butterworth quay clerk with a ticket rack and notched ferry stubs.'
FIGURE_SCALE = 1.57
HZ, HR, HX, HD = .753, .199, .215, .169
EARS, FRECKLES, MOUSTACHE, STUDENT = True, False, False, False
SHORTS, SANDALS = False, False
BROW, MOUTH, SMILE = .001, .041, .025
BROW_COLOR = None
HAND, SLEEVE, BOOT_HEIGHT = None, .53, .084
EYE_X, EYE_Z, EYE_SIZE = .087, -.041, (.043,.049)
SKIN, EAR_SHADE, BLUSH = ('#CA8F6C', '#A56659', '#BB726B')
HAIR, IRIS = '#A39B8F', '#69452F'
TOP, CUFF, PANTS, SHOE = '#8AABA0', '#D7DEBD', '#4A5968', '#5F4B42'
SOLE, SHOE_TRIM = '#453A40', CUFF
TOP_NAME, TOP_MATERIAL = 'Tunic', 'Tailored Cotton'
CAM_X, CAM_Z, CAM_SCALE = .76, 1.54, 1.22
CAM_TARGET_X, CAM_TARGET_Z = .028, .50

def spun(p, x, y, profile, color, n=40, power=1.):
    lathe(p,[(x,y,z,a,b) for z,a,b in profile],color,n=n,power=power)


def disk(p,at,r,thickness,color):
    x,y,z=at
    tube(p,(x,y+thickness/2,z),(x,y-thickness/2,z),r,r,color,n=48,roundness=.14)


def hand_pose(left,right):
    return {'L':[(.119,.001,.504),*left], 'R':[(-.119,.001,.504),*right]}

FIGURE_SCALE=1.70
SKIN, EAR_SHADE, BLUSH='#AD7659','#925D50','#B57367'
HAIR, IRIS='#50403D','#644535'
MOUSTACHE=True
TOP,CUFF,PANTS='#ABC1BC','#EAE2C9','#374C59'
SHOE,SHOE_TRIM,SOLE='#594E41','#80664A','#3B3937'
TOP_NAME='Quayside Service Shirt'
CAM_X=.59
ARMS=hand_pose([(.211,.002,.406),(.204,-.107,.451),(.196,-.135,.473)],[(-.196,.010,.387),(-.143,-.111,.336),(-.117,-.139,.335)])

def outfit(shirt,hips,arms):
    hair_cap(.76,-.19,-.56,.07,trim_at=.83)
    cap=accessory('Butterworth Quay Cap','Head')
    spun(cap,0,.004,[(.832,.202,.153),(.843,.210,.161),(.870,.209,.160),(.879,.204,.154)],'#374B54')
    orb(cap,(0,-.118,.843),(.177,.111,.012),'#384449',n=40)
    spun(cap,0,.004,[(.868,.207,.159),(.887,.229,.177),(.905,.234,.180),(.940,.202,.157),(.959,.153,.118),(.969,.105,.080),(.972,0,0)],'#E8D9B5')
    # Original bow-on ferry device, repeated on tickets and the enamel cap badge.
    def ferry(p,x,y,z,r):
        def xy(u,v):return (x+u*r,y,z+v*r)
        patch(p,[xy(-.83,-.10),xy(.83,-.10),xy(.51,-.55),xy(-.41,-.55)],'#42646A',depth=r*.07)
        box(p,xy(.04,.12),(r*1.24,r*.12,r*.31),r*.04,'#42646A')
        for j in range(3):box(p,(x+(j-1)*r*.31,y-r*.09,z+r*.12),(r*.15,r*.05,r*.13),r*.02,'#F3D698')
    disk(cap,(0,-.174,.897),.027,.008,'#C69C65');disk(cap,(0,-.181,.897),.022,.007,'#FADEA0');ferry(cap,0,-.187,.896,.020)
    collar(shirt,'#586F70');button_row(shirt,[(0,-.084,.464),(0,-.089,.435)],'#CEAE7E')
    stripe(shirt,[(.077,.052,.538),(.083,-.008,.550),(.080,-.070,.515),(.053,-.081,.478),(-.012,-.094,.399),(-.067,-.106,.340)],.010,'#835E48')
    rack=accessory('Leather Ticket Rack','Chest');x,y,z=-.049,-.118,.345
    box(rack,(x,y,z),(.174,.049,.093),.009,'#815740');box(rack,(x,y-.028,z-.004),(.163,.012,.055),.005,'#996B4C')
    for j,col in enumerate(['#E0A66B','#AFC5AA','#E6C78D','#C89EAA']):
        a=x+(j-1.5)*.037;box(rack,(a,y-.017,z+.044),(.033,.024,.043),.002,col);box(rack,(a,y-.031,z+.047),(.022,.002,.003),.0007,'#705A4C')
    for s in [-1,1]:bead(rack,(x+s*.072,y-.035,z-.020),.004,'#DCB67D')
    stub=accessory('Perforated Ferry Stubs','Hand.L');x,y,z=.194,-.155,.494
    box(stub,(x+.018,y+.007,z+.013),(.063,.009,.096),.004,'#D29C78',angle=.27)
    box(stub,(x-.011,y,z),(.080,.009,.106),.004,'#ECD6A4');ferry(stub,x-.010,y-.006,z+.016,.033)
    for j in range(6):box(stub,(x-.042+j*.012,y-.006,z-.019),(.006,.002,.0025),.0008,'#966953')
    for j in range(2):box(stub,(x-.013,y-.006,z-.029-j*.008),(.042-j*.016,.0018,.0035),.001,'#9E7761')


def compact_png(path):
    """Median-cut the rendered sRGB pixels. Keep the portrait standalone and small."""
    import struct, zlib
    if path.stat().st_size <= 245000:
        return
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = 'Non-Color'
    w, h = image.size
    pixels = np.empty(w*h*4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    rgb = np.rint(255*pixels.reshape(h,w,4)[::-1,:,:3]).astype(np.int32)
    bpy.data.images.remove(image)
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
    # Prefer true colour: soft gradations in skin and glossy hair outlive a palette.
    for step in (1,2,3,4):
        a = np.clip(np.rint(rgb/step)*step,0,255).astype(np.int16)
        left = np.zeros_like(a); left[:,1:] = a[:,:-1]
        up = np.zeros_like(a); up[1:] = a[:-1]
        predictors = [a,a-left,a-up,a-(up+left)//2]
        rows = np.argmin([np.minimum(p%256,(-p)%256).sum(axis=(1,2)) for p in predictors],axis=0)
        scan = b''.join(bytes([i])+predictors[i][j].astype('u1').tobytes() for j,i in enumerate(rows))
        data = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'sRGB',b'\0')+chunk(b'IDAT',zlib.compress(scan,9))+chunk(b'IEND',b'')
        if len(data)<=245000:
            path.write_bytes(data); return
    ids = (rgb[:,:,0] >> 2)*4096 + (rgb[:,:,1] >> 2)*64 + (rgb[:,:,2] >> 2)
    keys, inverse, count = np.unique(ids.ravel(), return_inverse=True, return_counts=True)
    mean = np.array([np.bincount(inverse, weights=c.ravel()) / count for c in rgb.transpose(2,0,1)]).T
    bins = [np.arange(len(keys))]; scores = [1.]
    for _ in range(min(255,len(keys)-1)):
        i = int(np.argmax(scores)); ix = bins.pop(i); scores.pop(i)
        axis = np.argmax(np.ptp(mean[ix],axis=0)*[.9,1,.78]); ix = ix[np.argsort(mean[ix,axis])]
        weights = count[ix].cumsum(); cut = min(len(ix)-1,weights.searchsorted(weights[-1]*.5)+1)
        for segment in (ix[:cut],ix[cut:]):
            bins.append(segment); scores.append(np.ptp(mean[segment],axis=0).max()*count[segment].sum()**.36 if len(segment)>1 else -1.)
    table=np.empty(len(keys),dtype='u1'); palette=[]
    for i,ix in enumerate(bins):
        table[ix]=i; palette.extend(np.rint(np.average(mean[ix],axis=0,weights=count[ix])).astype('u1'))
    scan=table[inverse].reshape(h,w)
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,3,0,0,0))+chunk(b'sRGB',b'\0')+chunk(b'PLTE',bytes(palette))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in scan),9))+chunk(b'IEND',b''))


def bead(p,at,r,color):
    orb(p,at,(r,r,r),color,n=12,rows=7)


def shoe_details(p, side, s, xf):
    # Painted outsole foxing and a simple instep strap on the soft vinyl shoe.
    stroke(p,[xf((x,y,z)) for x,y,z in [(-.047,-.055,.023),(-.032,-.076,.022),(0,-.084,.022),
            (.032,-.076,.022),(.047,-.055,.023)]],.0027,SHOE_TRIM,n=10)
    stroke(p,[xf((x,y,z)) for x,y,z in [(-.040,-.040,.047),(-.023,-.043,.055),
            (.014,-.044,.056),(.039,-.040,.049)]],.006,SHOE_TRIM,depth=.003,n=10)


def hair_cap(front, side, rear, sweep, locks=7, bulk=.018, accents=(), trim_at=None):
    p = Part('Hair',material('Moulded Hair',.34),'Head')
    hair_shell(p,HAIR,front=front,side=side,rear=rear,sweep=sweep,locks=locks,bulk=bulk,trim_at=trim_at)
    fringe(p,HAIR,accents)
    return p


def button_row(part, points, color):
    for x,y,z in points:
        orb(part,(x,y,z),(.006,.004,.006),color,n=12,rows=6)


def patch(part,path,color,depth=.003):
    """Closed, lined appliqué or thin panel; front edge winds towards -Y."""
    pts=list(path); n=len(pts)
    if sum(pts[i][0]*pts[(i+1)%n][2]-pts[(i+1)%n][0]*pts[i][2] for i in range(n))<0:pts.reverse()
    v=pts+[(x,y+depth,z) for x,y,z in pts]
    part.add(v,[tuple(range(n)),tuple(reversed(range(n,2*n)))]+[(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)],color,smooth=False)


def accessory(name,bone,finish=.44):
    return Part(name,material(name+' Finish',finish),bone)


def stripe(part,points,w,color):
    stroke(part,points,w,color,depth=w*.60,n=8)


def collar(part,color):
    for s in [-1,1]:
        patch(part,[(s*x,y,z) for x,y,z in [(.012,-.082,.488),(.005,-.077,.510),(.054,-.049,.546),(.085,-.058,.527),(.064,-.080,.488)]],color)


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
        mesh.from_pydata([Vector(v)*FIGURE_SCALE for v in self.v], [], self.f)
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
        paint(soft((dist-1)*3), BROW_COLOR or HAIR)
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
    n, rows = 64, 44
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
    n,rings = 40,7
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


def hair_shell(part,color,front=.28,side=-.40,rear=-.65,sweep=.04,locks=7,bulk=.018,
               edge_wave=1., trim_at=None):
    # Locks are broad, rounded lobes of a continuous cap. No pointed tips.
    n, rings = 64, 14
    V, F, UV = [], [], []
    for i in range(rings):
        q = i/rings
        for j in range(n):
            t = 2*pi*j/n
            ct = cos(t)
            edge = side+(front-side)*max(0,ct)**1.45+(rear-side)*max(0,-ct)**1.4
            wave = .5+.5*cos(locks*t + 1.4*sin(t)+2.0*q)
            edge += sweep*sin(2*t)-edge_wave*(.15 if ct>0 else .035)*wave**1.5
            a = edge+(pi/2-edge)*q
            z = HZ+(HR+bulk*.66)*sin(a)
            z += bulk*(.53+.45*wave)*cos(a)**2*g((q-.42)/.48)
            r = profile(HZ+HR*sin(a))
            rel = bulk*(.79+.55*wave)*cos(a)
            x = (HX*r+rel)*signed_power(sin(t),.91)
            y = -(HD*r+rel)*signed_power(ct,.91)
            if trim_at is not None:
                # Flatten the covered crown without narrowing the visible sideburns.
                q_trim = max(0.,min(1.,(z-trim_at)/.025))
                scale = 1-.16*q_trim*q_trim*(3-2*q_trim)
                x,y = x*scale,y*scale
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
        e.head,e.tail = Vector(a)*FIGURE_SCALE,Vector(b)*FIGURE_SCALE
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
                   (0,0,length*.83,.044 if SLEEVE >= .85 else .048,.046),
                   (0,0,length,.039 if SLEEVE >= .85 else .044,.040 if SLEEVE >= .85 else .044),
                   (0,0,length,0,0)],TOP,n=26,xf=lambda p: shoulder+axis_sleeve@Vector(p))
        if SLEEVE < .85:
            tube(arm,sewn.lerp(a,.11),sewn.lerp(b,.045),.0475,.0475,CUFF)
            tube(arm,sewn.lerp(a,.16),b,.036,.035,SKIN)
        elbow = .039 if SLEEVE >= .85 else .035
        orb(arm,b,(elbow,elbow,elbow),SKIN if SLEEVE<.85 else TOP,n=20,rows=10,bone=fa)
        tube(arm,b,c+(d-c)*.14,elbow,.026,SKIN if SLEEVE<.85 else TOP,bone=fa)
        if SLEEVE >= .85:
            tube(arm,b.lerp(c,.82),c,.031,.029,CUFF,n=18,bone=fa)
        hand = c.lerp(d,.56)
        axis = d-c
        tube(arm,c-axis*.11,d,.028,.030,HAND or SKIN,n=24,roundness=.76,bone=ha)
        orb(arm,hand+Vector((-s*.021,-.013,.006)),(.015,.020,.023),HAND or SKIN,n=16,rows=10,angle=s*.26,bone=ha)
        limb_parts[side] = arm
        leg = Part('Leg.'+side,fabric,'Thigh.'+side)
        if STUDENT:
            tube(leg,(s*.083,0,.112),(s*.074,0,.255),.039,.047,SKIN,n=24,bone='Shin.'+side)
            tube(leg,(s*.091,.011,.052),(s*.082,.002,.130),.039,.043,IVORY,n=24,bone='Shin.'+side)
            tube(leg,(s*.082,.002,.119),(s*.082,.001,.132),.043,.043,WHITE,bone='Shin.'+side)
        elif SHORTS:
            tube(leg,(s*.091,.011,.048),(s*.080,.002,.178),.035,.045,SKIN,n=24,bone='Shin.'+side)
            lathe(leg,[(s*.083,0,.139,0,0),(s*.083,0,.139,.050,.049),
                       (s*.083,0,.145,.056,.053),(s*.081,0,.156,.057,.055),
                       (s*.074,0,.211,.058,.057),(s*.068,.003,.258,.060,.055),
                       (s*.066,0,.277,0,0)],PANTS,n=30,power=.83)
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
                    (0,.031,BOOT_HEIGHT-.003,.048,.047),(0,.040,BOOT_HEIGHT,.034,.034),(0,.040,BOOT_HEIGHT,0,0)],
              SKIN if SANDALS else SHOE,n=36,power=.79,xf=xf)
        if SANDALS:
            stroke(shoe,[xf(p) for p in [(-.057,-.045,.033),(-.047,-.046,.054),(-.029,-.047,.065),(0,-.047,.069),
                                         (.029,-.047,.065),(.047,-.045,.054),(.057,-.040,.034)]],.013,SHOE,depth=.006,normal=(0,1,0),n=12)
            stroke(shoe,[xf(p) for p in [(-.062,.011,.033),(-.056,.008,.058),(-.040,.004,.078),(0,.001,.086),
                                         (.040,.004,.078),(.056,.008,.058),(.062,.011,.033)]],.013,SHOE,depth=.005,normal=(0,1,0),n=12)
            box(shoe,xf((s*.041,.003,.079)),(.019,.024,.011),.003,SHOE_TRIM,angle=s*.32)
        else:
            shoe_details(shoe,side,s,xf)
    return hips,limb_parts


def set_expressions(head,eyes):
    head.shape_key_add(name='neutral',from_mix=False)
    for name in ('smile','surprised'):
        key = head.shape_key_add(name=name,from_mix=False)
        key.value = 0.
        for i,vertex in enumerate(head.data.vertices):
            x,y,z = vertex.co/FIGURE_SCALE
            if y >= -.05:
                continue
            z0 = HZ-(.136 if not MOUSTACHE else .153)
            mouth = g((x/(MOUTH*1.52)))*g((z-z0)/.041)
            cheeks = g((abs(x)-.114)/.049)*g((z-(HZ-.108))/.025)
            brow = g((abs(x)-EYE_X)/.067)*g((z-(HZ+.071))/.022)
            if name == 'smile':
                key.data[i].co = Vector((x+x*.29*mouth,y-.005*cheeks,z+.011*cheeks+.009*mouth))*FIGURE_SCALE
            else:
                key.data[i].co = Vector((x-x*.50*mouth,y-.013*mouth,z+(z-z0)*.59*mouth+.022*brow))*FIGURE_SCALE
    eyes.shape_key_add(name='open',from_mix=False)
    blink = eyes.shape_key_add(name='blink',from_mix=False)
    blink.value = 0.
    for v in blink.data:
        v.co.y += .048*FIGURE_SCALE


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
    scene.cycles.samples = int(os.environ.get('CHIBI_SAMPLES','15'))
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.resolution_x,scene.render.resolution_y = 800,900
    scene.render.resolution_percentage = int(os.environ.get('CHIBI_RENDER_PERCENT','75'))
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
    camdata.type,camdata.ortho_scale = 'ORTHO',CAM_SCALE*FIGURE_SCALE
    views = {'hero':(CAM_X,-3.8,CAM_Z),'front':(0,-4,.52),'back':(0,4,.52),
             'side':(4,0,.52),'reverse':(-2.2,-3.8,1.1),'rear':(2.2,3.8,1.1)}
    for name in os.environ.get('CHIBI_VIEWS','hero').split(','):
        cam.location = views[name]
        cam.rotation_euler = (Vector((CAM_TARGET_X,0,CAM_TARGET_Z))*FIGURE_SCALE-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath = str(OUT/('preview.png' if name=='hero' else 'inspection-'+name+'.png'))
        bpy.ops.render.render(write_still=True)
        compact_png(Path(scene.render.filepath))


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
    rig['Facing'] = 'glTF +Z forward; +Y up'
    rig['origin_note'] = 'At ground level midway between the soles; metres'
    rig['Theme'] = 'Singapore / Malaysia street life'
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
