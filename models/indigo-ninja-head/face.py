"""Editable facial planes, painted features and cloth for the Indigo Ninja bust.

Blender metres, +Z up, character faces -Y. The X-positive brow leads the pose.
The skin and facial artwork share one surface function, including the nose,
cheeks and eyelids, so the face remains fitted when viewed in profile.
"""
from math import cos, exp, pi, sin, sqrt

from forms import ellipsoid, material, mesh, tube


# Height, half-width, front depth and back depth of each sculpting section.
PROFILE = (
    (.290, .024, .092, .050), (.302, .116, .169, .096),
    (.326, .196, .217, .151), (.363, .252, .248, .202),
    (.420, .307, .273, .249), (.482, .352, .287, .275),
    (.548, .382, .300, .294), (.610, .396, .307, .308),
    (.640, .398, .309, .312), (.720, .405, .305, .313),
    (.800, .388, .291, .293), (.880, .337, .258, .273),
    (.940, .254, .197, .213), (.974, .145, .115, .130),
    (.987, .062, .049, .052), (.990, .009, .008, .009),
)


def _profile(z):
    if z <= PROFILE[0][0]:
        return PROFILE[0][1:]
    for i, (upper, *_) in enumerate(PROFILE[1:], 1):
        if z <= upper:
            a, b = PROFILE[i-1], PROFILE[i]
            prev, following = PROFILE[max(i-2, 0)], PROFILE[min(i+1, len(PROFILE)-1)]
            length = b[0]-a[0]
            t = (z-a[0])/length
            w = t*t*(3-2*t)
            return tuple(a[k]*(1-w) + b[k]*w + length*(
                t*(1-t)**2*(b[k]-prev[k])/(b[0]-prev[0])
                - t*t*(1-t)*(following[k]-a[k])/(following[0]-a[0])) for k in (1, 2, 3))
    return PROFILE[-1][1:]


def _bump(x, z, xc, zc, width, height):
    return exp(-((x-xc)/width)**2-((z-zc)/height)**2)


def _relief(x, z):
    # Sculpt the nose, muzzle and chin in the skin itself; avoid seams at the bridge.
    cheek = .016*_bump(abs(x), z, .205, .49, .122, .068)
    socket = .010*_bump(abs(x), z, .158, .625, .1, .057)
    brow = .008*_bump(abs(x), z, .156, .704, .093, .039)
    bridge = .029*_bump(x, z, 0, .549, .038, .082)
    nose = .036*_bump(x, z, 0, .515, .048, .040)
    wing = .009*_bump(abs(x), z, .032, .503, .027, .019)
    muzzle = .026*_bump(x, z, .013, .419, .106, .065)
    mouth_top, mouth_bottom = _lip_lines(x)
    upper_lip = .014*_bump(x, z, .015, mouth_top+.004, .071, .010)
    lower_lip = .024*_bump(x, z, .014, mouth_bottom-.005, .073, .013)
    chin = .027*_bump(x, z, .002, .356, .106, .036)
    return cheek - socket + brow + bridge + nose + wing + muzzle + upper_lip + lower_lip + chin


MOUTH_SPAN = (-.065, .124)


def _lip_lines(x):
    t = max(0.0, min(1.0, (x-MOUTH_SPAN[0]) / (MOUTH_SPAN[1]-MOUTH_SPAN[0])))
    arc = sin(t*pi)
    top = .416 + .035*t*t - .011*arc
    return top, top - .014*arc**1.35



def _front(x, z):
    width, depth, _ = _profile(z)
    return -depth*max(0, 1-abs(x/width)**2.3)**(1/2.3) - _relief(x, z)


def _head(skin):
    verts, faces = [], []
    segments = 112
    heights = [a[0] + (b[0]-a[0])*j/5 for a,b in zip(PROFILE, PROFILE[1:]) for j in range(5)]
    heights.append(PROFILE[-1][0])
    # The profile needs additional rows across the two small lip ridges.
    heights = sorted(set(heights + [.393 + i*.004 for i in range(16)]))
    for z in heights:
        width, front, rear = _profile(z)
        for j in range(segments):
            angle = 2*pi*j/segments
            c, s = cos(angle), sin(angle)
            x = width * (1 if c >= 0 else -1) * abs(c)**(2/2.3)
            y = (rear if s >= 0 else -front)*abs(s)**(2/2.3)
            if s < 0:
                y -= _relief(x, z)*min(1, -s*3)
            verts.append((x,y,z))
    for i in range(len(heights)-1):
        for j in range(segments):
            a, b = i*segments+j, i*segments+(j+1)%segments
            faces.append((a,b,b+segments,a+segments))
    faces.extend((tuple(reversed(range(segments))), tuple(range(len(verts)-segments,len(verts)))))
    return mesh('Skin | cheek planes and sculpted nose', verts, faces, skin)


def _ear(side, skin, shadow, warmth):
    label = 'L' if side > 0 else 'R'
    centre = (.395*side, -.013, .579)
    def point(u,v,h):
        return (centre[0]+side*(.78*u+.626*h), centre[1]+.626*u-.78*h, centre[2]+v+.1*u)
    verts, faces = [], []
    n = 44
    # Start at the back of the pinna, roll forward around the helix and into its bowl.
    bands = ((.02,-.026),(.62,-.022),(.96,-.010),(1,.004),(.95,.020),(.75,.030),(.56,.022),(.38,.009),(.02,.008))
    for scale,h in bands:
        for i in range(n):
            a = 2*pi*i/n
            verts.append(point(.057*scale*cos(a)*(1+.14*sin(a)), .075*scale*sin(a), h))
    for j in range(len(bands)-1):
        for i in range(n):
            a,b=j*n+i,j*n+(i+1)%n
            face=(a,b,b+n,a+n)
            faces.append(face if side > 0 else tuple(reversed(face)))
    faces.extend((tuple(reversed(range(n))),tuple(range(len(verts)-n,len(verts)))))
    obj = mesh('Ear '+label+' | helix', verts, faces, skin)
    obj.data.materials.append(warmth)
    for polygon in obj.data.polygons[6*n:8*n]:
        polygon.material_index=1
    curl = [(-.002,.030,.024),(.011,.035,.025),(.020,.025,.026),(.018,.012,.026),(.008,.006,.024),(.003,-.005,.019)]
    tube('Ear '+label+' | inner fold', [point(*p) for p in curl], [.001,.0035,.0045,.004,.003,.001], shadow, sides=8)


def _strip(name,x0,x1,limits,surface,mat,steps=34,rows=4):
    """A curved filled patch sampled between two boundaries on the same skin."""
    verts, faces, prev = [], [], None
    for j in range(steps+1):
        x = x0+(x1-x0)*j/steps
        low,high=limits(x)
        if high <= low+.00004:
            z = (high+low)/2
            row = [len(verts)]
            verts.append((x,surface(x,z),z))
        else:
            row=[]
            for k in range(rows+1):
                z=low+(high-low)*k/rows
                row.append(len(verts)); verts.append((x,surface(x,z),z))
        if prev is not None:
            if len(prev)==1 and len(row)>1:
                faces.extend((prev[0],row[k],row[k+1]) for k in range(rows))
            elif len(row)==1 and len(prev)>1:
                faces.extend((prev[k],row[0],prev[k+1]) for k in range(rows))
            elif len(row)>1:
                faces.extend((prev[k],row[k],row[k+1],prev[k+1]) for k in range(rows))
        prev=row
    return mesh(name, verts, faces, mat)


def _eye(side,m):
    label = 'L' if side>0 else 'R'
    prefix = 'Eye '+label+' | '
    cx=side*.163
    cz=.619 if side>0 else .615
    half=.111
    top=.034 if side>0 else .023
    bottom=.035 if side>0 else .031
    def bounds(x):
        t=max(-1,min(1,(x-cx)*side/half))
        arc=max(0,1-t*t)**.78
        mid=cz+(.018 if side>0 else .023)*t+.001*arc
        return mid-bottom*arc*(1-.07*t), mid+top*arc*(1+.12*t)
    def depth(x,z):
        dome=max(0,1-((x-cx)/half)**2-((z-cz)/.063)**2)
        return _front(x,z)-.004-.019*dome
    def shifted(d): return lambda x,z:depth(x,z)-d
    _strip(prefix+'ivory', cx-half,cx+half,bounds,shifted(0),m['white'])
    # Shift both irises toward +X, leaving a larger wedge of sclera at the left.
    ix=cx+.055
    iz=cz+.004
    def disk(title,dx,dz,rx,rz,mat,offset):
        def clipped(x):
            delta=rz*sqrt(max(0,1-((x-dx)/rx)**2))
            lo,hi=bounds(x)
            return max(lo,dz-delta), min(hi,dz+delta)
        _strip(prefix+title,dx-rx,dx+rx,clipped,shifted(offset),mat,steps=36,rows=5)
    disk('umber iris rim',ix,iz,.042,.053,m['ink'],.0011)
    disk('amber iris',ix,iz,.037,.048,m['amber'],.0021)
    disk('honey lower iris',ix,iz-.021,.029,.022,m['honey'],.0030)
    disk('deep pupil',ix,iz+.003,.021,.032,m['pupil'],.0039)
    disk('main catchlight',ix-.011,iz+.008,.009,.0085,m['glint'],.0047)
    disk('small catchlight',ix+.016,iz-.020,.0035,.0033,m['glint'],.0047)
    def line(x):
        t=(x-cx)*side/half
        l,u=bounds(x)
        h=.002+(.009 if side>0 else .011)*(1-max(-1,min(1,t))**2)+.004*(t+1)/2
        return u-.0015,u+h
    _strip(prefix+'inked upper lid',cx-half,cx+half,line,shifted(.006),m['ink'],steps=34,rows=2)
    line_x=cx+side*half
    line_z=bounds(line_x)[1]
    outer_pts=[(line_x-side*.015,line_z+.014),(line_x-side*.006,line_z+.010),(line_x+side*.005,line_z+.008),(line_x+side*.018,line_z+.014)]
    tube(prefix+'outer lash flick',[(x,depth(x,z)-.006,z) for x,z in outer_pts],[.002,.004,.003,.0004],m['ink'],sides=7)
    # The outer third has a thin rim; the lower waterline stays lighter toward the nose.
    points=[]; widths=[]
    for i in range(23):
        t=-.77+1.765*i/22
        x=cx+side*half*t
        z=bounds(x)[0]-.0006
        points.append((x,depth(x,z)-.0019,z)); widths.append(.0007+.0025*(i/22)**1.55)
    tube(prefix+'lower lid',points,widths,m['line'],sides=8)
    # A tapered, angular brow. One brow arches, and the other stays lowered.
    centre=cx+side*.002; bw=.101
    def brow(x):
        t=max(0,min(1,.5+.5*side*(x-centre)/bw))
        arch=sin(pi*t)**.83
        base=(.673 if side>0 else .652)+(.045 if side>0 else .042)*t+(.019 if side>0 else .003)*arch
        width=.017*(max(0,sin(pi*t))**.48)*(1-.19*t)
        return base,base+width
    _strip('Brow '+label+' | tapered arch',centre-bw,centre+bw,brow,lambda x,z:_front(x,z)-.004,m['ink'],steps=27,rows=2)


def _expression(m):
    # A low crescent grin, fuller at the confident, raised corner.
    xa,xb=MOUTH_SPAN
    def mouth(x):
        top,bottom=_lip_lines(x)
        return bottom,top
    _strip('Smile | opening',xa,xb,mouth,lambda x,z:_front(x,z)-.0035,m['mouth'],steps=46)
    def tooth(x):
        t=(x+.037)/.121
        top=_lip_lines(x)[0]-.0015
        return top-.004*max(0,sin(pi*t))**.9,top
    _strip('Smile | upper teeth sliver',-.037,.084,tooth,lambda x,z:_front(x,z)-.005,m['tooth'],30,2)
    def lip(x):
        t=(x+.037)/.126
        line=_lip_lines(x)[1]-.002
        return line-.005*max(0,sin(pi*t)),line
    _strip('Smile | lower lip highlight',-.037,.089,lip,lambda x,z:_front(x,z)-.0035,m['lip'],28,2)
    for side in [-1,1]:
        points=[]
        for j in range(9):
            t=j/8; x=side*(.021+.018*t); z=.501+.0025*sin(pi*t)-.0015*t
            points.append((x,_front(x,z)-.0017,z))
        tube('Nostril '+str(side),points,[.0007+.0009*sin(pi*i/8) for i in range(9)],m['lip'],sides=7)


def _collar(m):
    ellipsoid('Neck', (0,.018,.278),(.119,.110,.119),m['skin'],segments=32,rings=16)
    # A single continuous surface turns back on itself at each fold. The seam
    # shares vertices around the full circumference, including behind the neck.
    n = 96
    rows = [
        # X/Y radius, height, fraction of the diagonal drape, X shift, material above row.
        (.250,.146,.000,0,0,'cloth'), (.258,.150,.007,0,0,'cloth'),
        (.258,.151,.024,0,0,'cloth'), (.222,.140,.054,.08,0,'cloth'),
        (.215,.139,.064,.12,0,'scarf'), (.228,.149,.068,.15,0,'scarf'),
        (.244,.158,.091,.20,-.002,'scarf'), (.238,.158,.117,.53,-.002,'scarf'),
        (.218,.147,.141,1,-.002,'scarf'), (.229,.153,.143,1,-.002,'edge'),
        (.233,.156,.150,1,-.002,'edge'), (.231,.156,.158,1,-.003,'edge'),
        (.213,.152,.184,.86,-.003,'edge'), (.183,.140,.218,.69,-.002,'edge'),
        (.164,.131,.253,.66,.002,'edge'), (.152,.123,.266,.65,.002,'edge'),
        (.137,.109,.263,.65,.002,'edge'), (.108,.090,.251,.60,.002,'edge'),
    ]
    def point(row, angle, offset=0):
        rx,ry,height,weight,shift,_=row
        drape=.040*cos(angle+.05)+.010*sin(2*angle+.6)
        return ((rx+offset)*cos(angle)+shift, .020+(ry+offset)*sin(angle), height+weight*drape)
    verts=[point(row,2*pi*i/n) for row in rows for i in range(n)]
    faces=[]
    for j in range(len(rows)-1):
        for i in range(n):
            a,b=j*n+i,j*n+(i+1)%n
            faces.append((a,b,b+n,a+n))
    faces.extend((tuple(reversed(range(n))),tuple(range(len(verts)-n,len(verts)))))
    garment=mesh('Scarf | wrapped cloth and standing collar',verts,faces,m['cloth'])
    garment.data.materials.append(m['scarf'])
    garment.data.materials.append(m['edge'])
    for j,row in enumerate(rows[:-1]):
        index=('cloth','scarf','edge').index(row[-1])
        for polygon in garment.data.polygons[j*n:(j+1)*n]:
            polygon.material_index=index
    garment.data.polygons[-1].material_index=2
    for j in range(20):
        angle=2*pi*j/20
        pts=[point(rows[11],angle+k*.040,.0013) for k in range(5)]
        tube('Scarf | stitch '+str(j+1),pts,[.0008,.00155,.0017,.00155,.0008],m['seam'],sides=6)


def build_face():
    colors={
        'skin':('#E8A677',.59), 'ear':('#D58768',.67), 'earfold':('#C07860',.66),
        'white':('#FFF0D8',.36),'ink':('#25192C',.52),'line':('#643F44',.54),
        'amber':('#C77729',.36),'honey':('#F4A83D',.37),'pupil':('#272033',.31),
        'glint':('#FFF8DD',.26),'mouth':('#702F41',.62),'tooth':('#FFF0DC',.48),
        'lip':('#C67966',.57),'cloth':('#262A40',.76),'scarf':('#8E3340',.73),
        'edge':('#B54B4E',.69),'seam':('#E7A96C',.65),
    }
    m={key:material('Figure | '+key,*value) for key,value in colors.items()}
    _collar(m)
    _head(m['skin'])
    for side in (-1,1):
        _ear(side,m['skin'],m['earfold'],m['ear'])
        _eye(side,m)
    _expression(m)
