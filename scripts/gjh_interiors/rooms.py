"""Seventeen room-specific compositions. Coordinates are metres in the installed slot."""
from math import cos, pi, radians, sin, tau

from mesh import CRAFT, PRINT, PULSE, SCROLL, Room, library_profile, logo

GOLD, BONE, INK = "d7a95b", "f6ecd2", "203545"
MINT, RED, SEA = "70cdb9", "c34339", "357675"
GLOBE = ((.10,0),(.72,.15),(1,.46),(.81,.78),(.25,1))
CAN = ((.92,0),(1,.09),(1,.24),(1,.78),(.97,1))
BOTTLE = ((.94,0),(1,.21),(1,.60),(.47,.77),(.47,.87),(.51,1))
LIBRARY = {
    "lantern": ("chinese-lantern/exports/chinese-lantern.glb","Sphere.001",5),
    "plate": ("mamak-stainless-steel-plate/exports/mamak-stainless-steel-plate.glb","PLATE_ShallowBowl",5)
}


def stock(room, shape, colours, locations, radius, height, depth=1, sides=8):
    master = Room(room.slot)
    master.lathe(0,0,0,radius,height,shape,colours,sides,depth=depth)
    room.stock(master.batches[CRAFT],locations)


def leaf(room,x,z,size,angle,c):
    outline=((0,-.55),(.21,-.22),(.22,.08),(.10,.36),(0,.52),(-.16,.26),(-.22,-.08),(-.16,-.36))
    pts=[(x+size*(a*cos(angle)+b*sin(angle)),room.floor,z+size*(b*cos(angle)-a*sin(angle)))
         for a,b in outline]
    room.face(pts[::-1],c)
    room.ribbon([(x-size*.35*sin(angle),room.floor+.002,z-size*.35*cos(angle)),
                 (x+size*.37*sin(angle),room.floor+.002,z+size*.37*cos(angle))],size*.034,GOLD,PRINT,True)


def lantern(r,x,y,z,rad,h,c,profile,ceiling,sides=10):
    r.line((x,ceiling,z),(x,y+h,z),.022,GOLD)
    r.lathe(x,y,z,rad,h,profile,[c],sides,PRINT)
    for level in (0,.96):
        r.lathe(x,y+h*level,z,rad*.36,.045,((1,0),(1,1)),[GOLD],8)
    r.line((x,y,z),(x,y-.21,z),.044,GOLD)


def placard(r,x,y,z,w,colour):
    r.box(x,y,z,w+.08,w*.5+.065,.05,colour)
    r.badge(x,y,z+.03,w)


def new_moon(r,profiles):
    for i,(x,z) in enumerate(((-3.25,-2.4),(-2.55,-2.6),(2.86,-2.7))):
        lantern(r,x,3.27+.28*(i%2),z,.32+.07*(i%2),.69,"efb94f",profiles["lantern"],5.65)
    # Two arcs with common tips give a genuine tapered crescent inlay.
    for i in range(24):
        def point(k,inner):
            a=pi*.16+pi*1.63*k/24
            inset=.38*sin(pi*k/24) if inner else 0
            return ((.97-inset)*cos(a),r.floor,2.1+(.97-inset)*sin(a))
        pts=[point(i,False),point(i+1,False),point(i+1,True),point(i,True)]
        r.face(list(dict.fromkeys(pts))[::-1],"efb94f",PRINT)
    for i,x in enumerate((-3.62,-1.2,1.2,3.62)):
        r.tag(x,1.65,-2.952,.32,i)


def mili(r,profiles):
    # Copper fascia and tile lettering sit clear of the hood's foremost lip.
    r.box(0,2.76,1.207,2.51,.57,.035,"bd7750")
    r.badge(0,2.78,1.229,.98,.42)
    for x in (-.94,-.75,.75,.94):
        r.box(x,2.75,1.233,.042,.37,.012,GOLD)
    r.box(0,2.45,1.19,2.5,.037,.048,BONE,PRINT)
    r.box(0,4.68,.36,.48,1.96,.49,"b7805c")
    for x in (-2.95,2.95):
        for h in (1.79,2.38):
            r.box(x,h,-4.02,1.47,.07,.40,"895c43")
            r.tag(x+.4,h,-3.811,.28)
    loc=[(x+(k-1.5)*.29,y,-4.02,1+.08*(k%2)) for x in (-2.95,2.95)
         for y in (1.826,2.416) for k in range(4)]
    stock(r,BOTTLE,["973d28",BONE,"ab4b30","853f2e",GOLD],loc,.085,.34,sides=6)
    r.lathe(.48,1.228,1.39,.26,.044,profiles["plate"],["dfd6b3"],12)
    for i in range(3):
        r.lathe(.36+i*.11,1.269,1.40,.063,.073,GLOBE,["dc9552"],6)
    for k in range(3): leaf(r,-1.51+.16*k,2.04+k*.37,.47,.65,MINT)


def gogo(r,_):
    for j in range(2):
        pts=[(-3.6+i*.68,5.04-.51*sin(i*pi/9),-.28-j*2.76) for i in range(10)]
        for a,b in zip(pts,pts[1:]): r.line(a,b,.024,"7d8566")
        for i,(x,y,z) in enumerate(pts[1::2]):
            c=("feb46c","70cdb9","efade6")[i%3]
            r.box(x,y-.27,z,.18,.33,.09,c,PRINT)
            r.lathe(x,y-.12,z,.09,.08,((1,0),(.55,1)),[c],8,PRINT,depth=.5)
            r.box(x,y-.48,z,.044,.12,.035,GOLD)
    for i,(x,z) in enumerate(((-3.26,1.91),(-3.03,2.08),(-3.42,2.02))):
        y=2.75+i*.23
        r.line((-3.12,1.20,2.10),(x,y,z),.018,BONE)
        r.lathe(x,y,z,.16,.40,GLOBE,[("efade6","70cdb9","feb46c")[i]],8)
    r.panel(-2.26,.91,2.626,1.0,.40,logo(3),yaw=radians(12))
    for rad in (1.16,1.44):
        r.ring(.24,r.floor,1.23,rad,rad*.82,.065,MINT,PULSE,True,start=-.14,end=pi*1.3)


def borsch(r,_):
    loc=[((i-2)*.29,h+.045,-5.08,1+.08*((i+j)%3))
         for j,h in enumerate((.61,1.34,2.07,2.8)) for i in range(5)]
    stock(r,BOTTLE,["69794b",BONE,"9784a7","79608e","68547d"],loc,.087,.36,sides=6)
    for i in range(4): r.tag(.45,.61+.73*i,-4.89,.30,i)
    for i in range(5): leaf(r,(-1)**i*.57,1.14+i*.54,.83,(-1)**i*.62,"89aa79")
    for i in range(3):
        x=-2.25+i*1.95
        r.ring(x,3.97,-1.6,.55,.21,.055,"c5dc77",PRINT,True)
    placard(r,2.7,2.13,-4.97,.94,"765285")


def herbal(r,profiles):
    for x in (-2.36,2.36):
        for j,z in enumerate((.58,-2.39)):
            lantern(r,x,3.11+.15*j,z,.27,.55,"e64b37",profiles["lantern"],4.08)
    placard(r,0,2.59,-3.828,1.55,GOLD)
    for x,z in ((-1.04,1.68),(1.02,2.47),(-.72,3.38)):
        for dx,dz,rx,rz in ((-.22,0,.23,.16),(0,-.08,.25,.20),(.24,0,.20,.14)):
            r.ring(x+dx,r.floor,z+dz,rx,rz,.044,GOLD,PRINT,True,pi,2*pi,10)
        r.ribbon([(x-.44,r.floor,z),(x-.23,r.floor,z+.12),(x+.30,r.floor,z+.12)],
                 .041,GOLD,PRINT,True)


def wheel(r,_):
    x,y,z=1.95,2.16,-3.79
    for radius in (.57,.66): r.ring(x,y,z,radius,radius,.09,"c4894a",CRAFT)
    for i in range(8):
        a=i*pi/4
        r.line((x,y,z),(x+.84*cos(a),y+.84*sin(a),z),.069,GOLD)
    r.box(x,y,z+.04,.20,.20,.10,"9c633c")
    for i in range(3):
        x=-1.75+i*.28
        r.lathe(x,.715,-4.06,.14,.42,((.63,0),(1,.26),(.86,.78),(.42,.9),(.58,1)),
                ["a98659","c4a376","977247",BONE],7)
    # Banded sheaves lean against the drying bench; three cut ends per bundle.
    for i in range(3):
        x=-1.62+i*.19
        for j in range(3):
            r.line((x+(j-1)*.041,1.41,-4.05),(x+.18+(j-1)*.047,1.93,-4.04),.039,"e7c58b")
        r.box(x+.09,1.67,-4.04,.16,.068,.074,"ad6242")
    for x,z in ((-.9,1.65),(.69,2.63)):
        r.ribbon([(x-.34,r.floor,z+.58),(x+.3,r.floor,z-.54)],.041,GOLD,PRINT,True)
        for i in range(3):
            leaf(r,x-.14+i*.1,z+.22-i*.22,.34,-.83,"d3a04f")
    for x in (-1.85,1.85):
        r.box(x,3.94,0,.14,.09,4.3,"b98b55")
        r.box(x,3.88,-.24,.05,.025,3.57,GOLD,PRINT)
    r.tag(-1.74,.52,-3.81,.32)


def dragon(r,profiles):
    x,z=1.84,-3.79
    r.box(x,2.06,z,1.90,2.00,.065,"672d2c")
    spine=[(-.66,-.55),(-.34,-.38),(.23,-.42),(.49,-.24),(.42,-.03),(.12,.07),
           (-.22,.09),(-.41,.28),(-.30,.46),(.01,.50),(.27,.43),(.51,.52),(.69,.50)]
    def trace(path,w,c):
        r.ribbon([(x+a,2.04+b,z+.046) for a,b in path],w,c)
    trace(spine,.094,"efb94f")
    trace([(.28,.44),(.22,.69),(.11,.79)],.055,"feb46c")
    trace([(.35,.48),(.45,.73),(.59,.78)],.044,"feb46c")
    trace([(.46,.38),(.65,.32),(.75,.42)],.035,"efb94f")
    # A flared muzzle, mane, dorsal scales, foreleg and swept whiskers
    # keep the gold relief legible when the horns occupy only a few pixels.
    def silhouette(points,c):
        r.face([(x+a,2.04+b,z+.055) for a,b in points],c,PRINT)
    silhouette([(.19,.43),(.05,.62),(.27,.59),(.28,.69),(.40,.60),(.52,.62),
                (.59,.54),(.76,.55),(.80,.45),(.56,.40),(.45,.33),(.29,.38)],"efb94f")
    silhouette([(.47,.53),(.54,.55),(.51,.48)],"e64b37")
    trace([(.63,.46),(.78,.38),(.84,.29)],.025,"feb46c")
    trace([(.13,.08),(.26,-.07),(.22,-.18),(.35,-.16)],.048,"efb94f")
    trace([(-.20,.08),(-.35,-.04),(-.48,-.02)],.049,"efb94f")
    for dx,dy in ((-.18,.13),(.02,.13),(.20,.09),(.34,.04),(.42,-.09)):
        silhouette([(dx,dy),(dx-.055,dy+.14),(dx+.093,dy+.018)],"feb46c")
    for side in (-1,1):
        for i in range(3):
            lantern(r,side*(2.51+.08*i),3.27+.07*(i%2),1.5-i*1.38,.16,.33,"e64b37",profiles["lantern"],4.05,7)
    for i in range(3): r.ring(-1.1+i*.78,r.floor,2.25,.38,.38,.045,GOLD,PRINT,True)
    r.tag(-.52,.73,.009,.32)


def skippy(r,_):
    x,z=-2.96,-1.83
    r.lathe(x,1.085,z,.44,1.24,((.83,0),(1,.09),(1,.75),(.84,.84),(.98,.85),(.98,1)),
            ["965c35","c18a57","a96b3d","446797","1c5079"],14)
    r.badge(x,1.72,z+.432,.65,.31)
    r.box(-.58,1.271,-.253,1.34,.834,.014,"294e80")
    r.panel(-.58,1.271,-.241,1.29,.71,(129,129,190,158),PULSE)
    for i in range(5):
        x=(-1)**i*.23+.72;z=.58+i*.61
        # Two lobes with a narrow waist, one continuous stamped outline.
        pts=[]
        for k in range(25):
            a=k*tau/24
            pts.append((x+.17*cos(a)*(1-.45*cos(2*a)),r.floor,z+.24*sin(a)))
        r.ribbon(pts,.037,"cf9d58",PRINT,True)
    for x in (-2.54,2.54):
        r.ring(x,3.91,.72,.53,.53,.059,"efb94f",PRINT,True)
    r.tag(-3.02,1.045,-1.26,.26)


def spam(r,_):
    # The rear ledges and the 12-degree conveyor have different coordinate frames.
    loc=[((i-(6-2*j)/2)*.28,.899+j*.52,-4.00,1)
         for j in range(3) for i in range(7-2*j)]
    a=radians(12)
    for i in range(4):
        dx=-.83+i*.48
        loc.append((-.72+dx*cos(a),1.684,-1.10-dx*sin(a),1.15))
    stock(r,CAN,[GOLD,"254d83","3e6e9d",GOLD],loc,.116,.27,.76,sides=8)
    r.box(-.62,1.40,-.633,2.43,.19,.06,"d1a753",yaw=a)
    r.panel(-.61,1.40,-.593,.82,.17,logo(9),yaw=a)
    placard(r,0,2.83,-3.99,2.08,"1d4072")
    for x in (-1.2,1.2):
        for z in (1.71,2.58,3.45):
            r.ribbon([(x-.23,r.floor,z+.11),(x,r.floor,z-.11),(x+.23,r.floor,z+.11)],.048,GOLD,PRINT,True)
    for x in (-1.98,1.98): r.box(x,3.98,-1.39,.12,.07,2.41,GOLD,PRINT)
    r.tag(.60,1.95,-3.819,.28,1)


def coast(r,_):
    r.lathe(-.45,1.175,-1.31,.345,.65,[(max(.035,sin(k*pi/8)),(1-cos(k*pi/8))/2) for k in range(9)],
            ["d8edf4"],18,PRINT)
    for j in range(3):
        r.ring(-.38,r.floor,1.12+j*.46,1.02+j*.26,.36,.042,"70cdb9",PRINT,True,.10,pi-.10)
    for i,(x,z) in enumerate(((-2.4,-.93),(-2.02,-1.1),(-2.65,-1.23))):
        y=3.2+i*.15
        r.line((x,4.05,z),(x,y+.27,z),.018,GOLD)
        r.lathe(x,y,z,.14,.28,GLOBE,["d8edf4"],8,PRINT)
    for i in range(5):
        x=1.92+(i%3)*.38;y=1.46+(i//3)*.62
        for j in range(5):
            a=(j-2)*.31
            r.line((x,y,-3.74),(x+.20*sin(a),y+.25*cos(a),-3.74),.049,"d3b49d")
    r.tag(-1.13,1.12,-1.04,.28)


def deli(r,_):
    # Dress the existing packing bench with a chilled, brass-framed service rack.
    x,y,z=-.56,1.46,-.57
    r.box(x,y,z,2.17,.115,.52,"985841")
    for end in (-1,1):
        r.line((x+end*1.02,y,z+.20),(x+end*1.02,y+.51,z+.20),.045,GOLD)
        r.line((x+end*1.02,y+.51,z+.20),(x+end*1.02,y+.61,z-.29),.045,GOLD)
    r.box(x,y+.54,z+.19,2.12,.085,.06,"698065")
    for i in range(3):
        px=x+(i-1)*.64
        r.box(px,y+.074,z,.55,.034,.40,BONE)
        for j in range(3):
            r.lathe(px+(j-1)*.13,y+.094,z,.11,.16-.025*j,GLOBE,
                    [["a74b41","ca8270","b06350"][i]],8,depth=.93)
        r.tag(px,y-.015,z+.268,.33,i)
    placard(r,1.68,2.63,-3.76,1.38,"596b4b")
    for i in range(7):
        for j in range(2):
            if (i+j)%2==0:
                x=(i-3)*.36;z=2.2+j*.36
                r.face([(x-.18,r.floor,z-.18),(x-.18,r.floor,z+.18),(x+.18,r.floor,z+.18),(x+.18,r.floor,z-.18)],"c17b68")
    for i in range(7):
        r.box(1.86+(i-3)*.23,3.71,-2.91,.23,.1,.98,("b9584d",BONE)[i%2])


def herbarium(r,_):
    for i,(x,y,z) in enumerate(((-2.92,1.09,-1.72),(1.28,.085,-3.72),(1.72,.085,-3.78))):
        r.lathe(x,y,z,.18,.33,((.73,0),(1,.93),(1,1)),["d3c5aa",BONE],8)
        for j in range(7):
            a=j*2.4+i
            bx,bz=x+.31*cos(a),z+.31*sin(a)
            base=(x,y+.29,z); tip=(bx,y+.60+.07*(j%3),bz)
            wing=(x+.19*cos(a)-.095*sin(a),y+.51,z+.19*sin(a)+.095*cos(a))
            other=(x+.19*cos(a)+.095*sin(a),y+.50,z+.19*sin(a)-.095*cos(a))
            r.face([base,wing,tip,other],("5a9577","86aa79")[j%2])
            r.face([other,tip,wing,base],"688b6e")
    placard(r,.78,2.81,-3.91,1.50,"b76462")
    for i in range(4): leaf(r,1.12+.16*(i%2),1.23+i*.48,.51,(-1)**i*.76,"79aa90")
    for x,z in ((-2.2,-.51),(2.13,.73)):
        r.ring(x,3.96,z,.69,.35,.061,"cbefed",PRINT,True)
    r.tag(-2.90,1.025,-1.35,.31,1)


def listening(r,_):
    angle=radians(8)
    r.panel(-.64-.084*sin(angle),.43+2.428,-1.05-.084*cos(angle),
            1.005,.27,(0,205,256,228),SCROLL,yaw=angle)
    r.box(1.75,2.98,-3.91,2.05,.42,.08,INK)
    r.panel(1.75,2.98,-3.865,1.94,.33,(0,205,256,228),SCROLL)
    # Three contrasting earcups on the exposed right-hand return.
    for i,x in enumerate((.85,1.73,2.61)):
        r.box(x,2.12,-3.89,.77,.97,.08,"394f5d")
        r.ring(x,2.11,-3.832,.24,.32,.052,BONE,CRAFT,start=0,end=pi,n=14)
        for side in (-1,1):
            r.box(x+side*.236,2.04,-3.815,.131,.26,.14,"789caa")
        r.tag(x,1.78,-3.84,.29,i)
    for side in (-1,1):
        pts=[(side*1.53,r.floor,3.52),(side*1.53,r.floor,1.72),(side*2.05,r.floor,1.18),
             (side*2.05,r.floor,-.37)]
        r.ribbon(pts,.07,"8ad9ff",PRINT,True)
        r.ribbon([(x+side*.16,y,z) for x,y,z in pts],.029,BONE,PRINT,True)
        r.box(side*1.87,3.94,-.64,.065,.045,3.42,"8ad9ff",PRINT)


def living(r,_):
    aurora=(0,162,256,199)
    r.panel(-.62,2.084,-3.833,3.43,1.92,aurora,SCROLL)
    r.panel(2.63,.947,-3.518,.82,.88,aurora,SCROLL)
    # Red architectural lightbox and a low, continuous reveal around the lounge.
    r.box(2.44,2.82,-4.13,1.14,.75,.09,"aa344a")
    r.panel(2.44,2.82,-4.076,.96,.52,logo(14))
    r.ribbon([(-1.71,r.floor,1.29),(-1.71,r.floor,2.00),(.92,r.floor,2.00),
              (1.43,r.floor,1.51)],.059,"efade6",PRINT,True)
    for x in (-2.22,2.22):
        r.ring(x,3.94,-1.43,.39,.39,.048,"efade6",PRINT,True)
    r.tag(1.25,1.285,-3.93,.28)


def recital(r,_):
    angle=radians(-22)
    # Align the ivory tips with the measured key fronts on both piano exports.
    for i in range(32):
        u=(i-15.5)*.043;v=.617
        x=-1.05+u*cos(angle)+v*sin(angle);z=-1.02-u*sin(angle)+v*cos(angle)
        r.face([(x+u*cos(angle)+v*sin(angle),.973,z-u*sin(angle)+v*cos(angle))
                for u,v in ((-.018,-.029),(-.018,.029),(.018,.029),(.018,-.029))],"fff3c8",PRINT)
    x,z=-2.98,-1.80
    r.box(x,1.105,z,.66,.065,1.22,"655145")
    for i in range(3):
        pz=z+(i-1)*.37
        r.box(x,1.175,pz,.26,.09,.29,"b6a887")
        r.box(x,1.253,pz,.115,.08,.23,"574746")
        r.lathe(x,1.29,pz,.082,.042,((1,0),(1,1)),[GOLD],10)
        r.lathe(x,1.331,pz,.066,.008,((1,0),(1,1)),[INK],10)
        r.line((x,1.342,pz),(x+.034,1.342,pz-.014),.011,BONE)
        r.tag(x+.341,1.105,pz,.24,i,yaw=pi/2)
    for i in range(3):
        x,z=-.7+i*.54,2.29+i*.08
        r.ring(x,r.floor,z,.12,.087,.044,GOLD,PRINT,True,n=12)
        r.ribbon([(x+.11,r.floor,z),(x+.11,r.floor,z-.39),(x+.23,r.floor,z-.32)],.033,GOLD,PRINT,True)
    for x in (-1.17,1.17): r.box(x,3.989,-.86,.065,.056,2.84,BONE,PRINT)


def power(r,_):
    # Standee and demo meter share the right-hand permanent workbench.
    x,z=1.74,-.49
    r.lathe(x,1.122,z,.35,1.34,((.94,0),(1,.04),(1,.20),(1,.72),(1,.84),(.97,.98),(.87,1)),
            [INK,"5b773c","9abf38","5d983d",INK,"b7b9a9"],12)
    r.lathe(x,2.462,z,.13,.11,((1,0),(.94,1)),["cad0bd"],10)
    r.badge(x,1.86,z+.354,.53,.31)
    r.panel(2.63,1.423,-3.598,.53,.30,(0,205,256,228),PULSE)
    for i in range(3):
        x,z=-1.05+i*.88,1.60+.25*(i%2)
        outline=[(.09,-.55),(-.28,.09),(-.015,.075),(-.11,.53),(.31,-.14),(.02,-.105)]
        r.face([(x+a,r.floor,z+b) for a,b in outline],"c5dc77",PULSE)
    for i in range(4): r.box(-2.51+i*.33,3.95,-1.43,.21,.058,.69,"c5dc77",PRINT)
    r.tag(x+1.13,1.10,-.13,.27)


def telephone(r,_):
    # Handset rests in a two-ear cradle on the existing writing desk.
    x,y,z=-2.96,1.09,-1.80
    r.box(x,y+.11,z,.68,.22,.93,"424c50")
    r.box(x,y+.24,z-.13,.55,.07,.51,"81918b")
    for row in range(3):
        for col in range(3):
            r.box(x+(col-1)*.12,y+.267,z+.11+row*.10,.091,.04,.073,BONE)
    r.box(x,y+.41,z-.22,.56,.13,.14,"cf8964")
    for side in (-1,1):
        r.box(x+side*.264,y+.34,z-.22,.16,.18,.21,"ba775c")
    for i in range(3):
        radius=.30+i*.19
        r.ring(-.55,1.83,-2.21,radius,radius,.061,"feb46c",PULSE,
               start=pi*.17,end=pi*.83,n=16)
        r.ring(.5,r.floor,1.31,radius+.27,radius+.27,.038,GOLD,PRINT,
               floor=True,start=pi*.13,end=pi*.87,n=16)
    for i in range(3): r.box(1.8+i*.24,3.94,.8,.09,.06,.46+i*.33,"feb46c",PRINT)
    r.tag(x,1.21,z+.48,.31)


# Replace the eye-level facings on the left rear shelf. The runtime studio
# retains the shelf and its ticket rail. Each category has its own silhouette.
FEATURE_SHELVES = {
    # centre X, container profile, three bands, radius, height, depth scale, sides
    5:(-2.10,((.88,0),(1,.74),(.77,.85),(.83,1)),("964938","d4ac66","6b4137"),.107,.31,.86,6),
    6:(-2.04,((.80,0),(1,.44),(.86,.57),(1,1)),("dcc091","ab6a44","edce91"),.110,.38,.78,6),
    7:(-1.93,((1,0),(1,.83),(1.03,1)),("a33e37","dea95d"),.119,.25,.95,6),
    8:(-1.96,((.91,0),(1,.64),(.80,.77),(.95,1)),("b0774e","d6a572","3d6c9d"),.117,.31,.91,8),
    10:(-2.10,((.87,0),(1,.21),(1,.92),(.95,1)),("94ae9b","538d83","d2b28f"),.119,.28,.79,6),
    11:(-1.83,((1,0),(1,.76),(.92,.86),(.95,1)),("a75445","e8c6a4","577758"),.121,.29,.76,8),
    12:(-2.20,((.98,0),(1,.63),(.58,.74),(.58,1)),("91b29a","d8e4ca","9b849f"),.085,.36,.84,6),
    17:(-3.06,((1,0),(1,.62),(.96,.67),(.93,1)),("846c5d","c9cbbe","656d71"),.075,.24,.77,4),
}


def shelf_facings(r):
    x,shape,colours,rad,h,depth,n = FEATURE_SHELVES[r.slot]
    z = -5.08 if r.slot == 5 else -3.84 if r.slot == 17 else -4.08
    locations = [(x+(i-1.5)*.23,2.115,z,.98+.07*(i%2)) for i in range(4)]
    stock(r,shape,colours,locations,rad,h,depth,n)
    r.tag(x+.21,2.065,z+.213,.27,r.slot%3)


DESIGNS = (new_moon,mili,gogo,borsch,herbal,wheel,dragon,skippy,spam,coast,
           deli,herbarium,listening,living,recital,power,telephone)


def build(slot,models):
    profiles={key:library_profile(models/path,mesh,samples) for key,(path,mesh,samples) in LIBRARY.items()
              if key == "plate" and slot == 2 or key == "lantern" and slot in (1,5,7)}
    room=Room(slot)
    DESIGNS[slot-1](room,profiles)
    if slot in FEATURE_SHELVES:
        shelf_facings(room)
    return room
