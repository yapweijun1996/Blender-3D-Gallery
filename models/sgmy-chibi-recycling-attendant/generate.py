"""SG/MY vinyl figures: recycling attendant (original design).
Rebuild with blender -b --python generate.py (Blender 5.2.3 LTS).
Original procedural wardrobe and props over the round-1 SG/MY character rig.
No external assets, imagery or fonts. The portrait studio is preview-only.
"""
SLUG = 'sgmy-chibi-recycling-attendant'
EARS, FRECKLES, MOUSTACHE, STUDENT = True, False, False, False
BROW, MOUTH, SMILE = .001, .044, .026
HAND, SLEEVE, BOOT_HEIGHT = None, .44, .084
CAM_X, CAM_Z, CAM_SCALE = 1.51, 1.51, 1.24
CAM_TARGET_X, CAM_TARGET_Z = 0, .515
TITLE = 'Estate Recycling Attendant'
ROLE = 'Singapore housing estate recycling attendant with a plastics caddy'
HZ, HR, HX, HD = .751,.186,.213,.166
SKIN, EAR_SHADE, BLUSH = '#B8795D', '#935341', '#C3675E'
HAIR, IRIS = '#3E332E', '#8A6956'
EYE_X, EYE_Z, EYE_SIZE = .084,-.041,(.047,.052)
BROW, MOUTH, SMILE = -.004,.043,.022
TOP_NAME, TOP_MATERIAL = 'Estate Polo', 'Lagoon Work Polo'
TOP, CUFF, PANTS = '#318A7E', '#3A6968', '#374C54'
SHOE, SOLE, SHOE_TRIM = '#526865', '#283F45', '#B8C78F'
HAND, BOOT_HEIGHT = '#E8DAC1',.104
CAM_X, CAM_TARGET_X = 1.65,.038
ARMS = {
    'L': ((.119,0,.503),(.196,-.026,.359),(.227,-.040,.276),(.252,-.053,.244)),
    'R': ((-.119,0,.503),(-.172,.010,.372),(-.184,-.010,.266),(-.179,-.023,.221)),
}


def outfit(shirt,hips,arms):
    mint, pine, lagoon, berry = '#CBDF9A','#2A6461','#498684','#AE6678'
    hair_cap(.34,-.57,-.88,.050,locks=6,bulk=.015,trim_at=.832)
    hat = Part('Sun Bucket Hat',material('Lagoon Canvas',.58),'Head')
    xf=lambda p:(p[0],p[1]+.006,p[2]-.041*p[0]+.068*p[1])
    lathe(hat,[(0,0,.859,0,0),(0,0,.858,.190,.146),(0,0,.867,.203,.162),(0,0,.902,.196,.159),
              (0,.006,.949,.177,.135),(0,.010,.975,.165,.126),(0,.010,.979,.154,.114),(0,.010,.979,0,0)],lagoon,n=56,xf=xf)
    # A floppy brim with a narrow binding rather than a cap visor.
    lathe(hat,[(0,-.008,.825,.205,.174),(0,-.012,.817,.243,.222),(0,-.012,.824,.246,.226),
              (0,-.012,.833,.242,.223),(0,-.008,.865,.205,.174),(0,-.008,.871,.198,.168)],pine,n=56,xf=xf)
    lathe(hat,[(0,0,.870,.203,.163),(0,0,.880,.202,.164),(0,0,.892,.199,.161)],mint,n=56,xf=xf)
    for i in range(5):
        a=(i-2)*.68
        orb(hat,xf((.194*sin(a),-.158*cos(a),.905)),(.006,.004,.005),pine,n=12,rows=6)

    collar(shirt,mint,pine)
    stroke(shirt,[(-.054,-.063,.533),(-.040,-.084,.525),(.002,-.094,.514),(.047,-.075,.525),
                  (.062,-.062,.537)],.012,berry,depth=.006)
    orb(shirt,(-.051,-.081,.523),(.016,.009,.013),berry,n=16,rows=8)
    plaque(shirt,'KITAR',.079,.430,.068,IVORY,pine,y=-.086,height=.029)
    sleeve_trim(arms,mint,frac=.32)
    pants_pocket(hips,-.112,-.030,.239,'#475C61',pine)

    binpart = Part('Recycling Caddy',material('Moss Plastic, Bottles and Paper',.46),'Hand.L')
    x,y,z = .277,-.062,.204
    lathe(binpart,[(x,y,z-.122,0,0),(x,y,z-.122,.067,.052),(x,y,z-.113,.075,.058),(x,y,z-.040,.087,.063),
                   (x,y,z-.033,.091,.069),(x,y,z-.023,.092,.070),(x,y,z-.019,.090,.069),
                   (x,y,z-.020,.081,.060),(x,y,z-.032,.080,.058),(x,y,z-.110,.064,.048),
                   (x,y,z-.110,0,0)],'#7B9B67',n=42,power=.68)
    lathe(binpart,[(x,y,z-.040,.089,.066),(x,y,z-.034,.094,.071),(x,y,z-.022,.094,.072)],pine,n=42,power=.68)
    for dx in (-.065,-.043,.043,.065):
        stroke(binpart,[(x+dx*.87,y-.051,z-.108),(x+dx*.96,y-.062,z-.071),(x+dx,y-.065,z-.040)],.0048,'#A5B885',n=8)
    stroke(binpart,[(x+.077,y+.014,z-.026),(x+.065,y+.006,z+.028),(x+.032,y-.004,z+.067),
                    (x-.024,y-.009,z+.067),(x-.064,y-.012,z+.033),(x-.080,y-.019,z-.027)],.0066,'#424C54',n=12)
    for side in (-1,1):
        orb(binpart,(x+side*.091,y,z-.037),(.008,.012,.010),pine,n=14,rows=6)
    box(binpart,(x,y-.065,z-.073),(.060,.006,.039),.008,IVORY)
    label(binpart,'PLASTIK',(x,y-.070,z-.073),.050,pine)
    for dx,dy,dz,col,cap,angle in ((-.033,.008,.027,'#78B5B3','#56658F',.21),(.038,-.010,.009,'#B2C589','#647F64',-.23)):
        c = Vector((x+dx,y+dy,z-.098+dz))
        r = Matrix.Rotation(angle,3,'Y')
        xf=lambda p:c+r@Vector(p)
        lathe(binpart,[(0,0,0,0,0),(0,0,0,.018,.018),(0,0,.008,.021,.021),(0,0,.052,.021,.021),
                      (0,0,.064,.017,.017),(0,0,.074,.010,.010),(0,0,.084,.010,.010),(0,0,.084,0,0)],col,n=22,xf=xf)
        tube(binpart,xf((0,0,.075)),xf((0,0,.089)),.011,.011,cap,n=16)
    box(binpart,(x+.007,y+.029,z-.039),(.067,.019,.093),.006,'#F1C487',angle=.25,side_angle=.21)
    label(shirt,'KITAR SEMULA',(0,.091,.439),.131,mint,side_angle=pi)


# Tailoring and accessory helpers. Colours are sRGB; all measurements are metres.
def round_motif(part, center, radius, color, sides=28, tube_radius=.003):
    x,y,z = center
    points = [(x+radius*cos(2*pi*i/sides),y,z+radius*sin(2*pi*i/sides)) for i in range(sides+1)]
    stroke(part,points,tube_radius,color,n=8)


def plaque(part, name, x, z, width, base, text, y=-.095, height=.031):
    box(part,(x,y,z),(width,.010,height),.005,base)
    label(part,name,(x,y-.0052,z),width*.82,text)


def pants_pocket(part, x, y, z, color, trim):
    box(part,(x,y,z),(.055,.030,.073),.010,color,angle=.06)
    stroke(part,[(x-.024,y-.015,z+.020),(x,y-.017,z+.020),(x+.023,y-.015,z+.020)],.0025,trim,n=8)


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


def sleeve_trim(arms, color, frac=.30):
    for side, arm in arms.items():
        a,b = map(Vector,ARMS[side][:2])
        origin = a.lerp(b,frac)
        axis = (b-a).to_track_quat('Z','Y')
        lathe(arm,[(0,0,-.006,.049,.049),(0,0,-.002,.051,.051),(0,0,.003,.050,.050),
                   (0,0,.006,.048,.048)],color,n=24,xf=lambda p: origin+axis@Vector(p))


def apron_band(part, color, bottom=.216, middle=.306, width=.147):
    lathe(part,[(0,-.005,bottom,0,0),(0,-.006,bottom,width-.013,.083),
                (0,-.010,bottom+.009,width,.091),(0,-.008,middle-.022,width-.008,.099),
                (0,-.004,middle,width-.010,.099),(0,-.004,middle+.009,width-.019,.093),
                (0,0,middle+.010,0,0)],color,n=44,power=.75)


def tray(part, x,y,z, radius, base, rim):
    lathe(part,[(x,y,z+d,r,r*.78) for d,r in [(0,0),(0,radius*.80),(.004,radius*.90),
          (.017,radius),(.021,radius),(.023,radius*.96),(.019,radius*.92),(.008,radius*.86),(.008,0)]],
          base,n=48)
    lathe(part,[(x,y,z+d,r,r*.78) for d,r in [(.018,radius),(.021,radius*1.007),(.023,radius*.973)]],rim,n=48)


def strap(part, a,b, width, color, depth=.005):
    a,b = Vector(a),Vector(b)
    stroke(part,(a,a.lerp(b,.09),a.lerp(b,.91),b),width,color,depth=depth,n=12)


def pocket_welt(part,x,y,z,width,color):
    stroke(part,[(x-width*.50,y,z-.003),(x-width*.43,y-.002,z),(x+width*.40,y-.002,z),
                 (x+width*.50,y,z+.001)],.004,color,n=8)


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
    n, rows = 76, 54
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
    n, rings = 72, 17
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
    camdata.type,camdata.ortho_scale = 'ORTHO',CAM_SCALE
    views = {'hero':(CAM_X,-3.8,CAM_Z),'front':(0,-4,.52),'back':(0,4,.52),
             'side':(4,0,.52),'reverse':(-2.2,-3.8,1.1),'rear':(2.2,3.8,1.1)}
    for name in os.environ.get('CHIBI_VIEWS','hero').split(','):
        cam.location = views[name]
        cam.rotation_euler = (Vector((CAM_TARGET_X,0,CAM_TARGET_Z))-cam.location).to_track_quat('-Z','Y').to_euler()
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
