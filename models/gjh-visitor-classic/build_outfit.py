"""Build the Classic visitor's palette-colored modular wardrobe in model space."""
from math import cos, sin, pi


def build_outfit(api):
    bone = 'Chest'
    hoodie, bag, shorts = 'Hoodie', 'Backpack', 'Shorts'
    cloth, cloth_light, lavender = '#EEE8FA', '#F8F2FE', '#DDD1EC'
    iris, plum, crocus, violet = '#8852D4', '#60319E', '#AA73F1', '#7540B7'
    charcoal, piping, flap = '#393541', '#4D4656', '#514A58'
    sole, white = '#F4EBF1', '#FFF9FA'
    gold = '#EFC589'

    def submit(name, slot, vertices, faces, colors, binding, smooth=False):
        weights = [binding(*v) for v in vertices] if callable(binding) else binding
        return api.mesh(name, slot, vertices, faces, colors, weights, smooth)

    surfaces = {}

    def surface(name, u, v, axis, outer):
        # Project trim onto the triangulated garment, keeping narrow details visible in profile.
        axis_u, axis_v = {1:(0,2),2:(0,1),0:(1,2)}[axis]
        hits=[]
        points, faces = surfaces[name]
        for polygon in faces:
            for i in range(1,len(polygon)-1):
                a,b,c=(points[k] for k in (polygon[0],polygon[i],polygon[i+1]))
                du1,dv1=b[axis_u]-a[axis_u],b[axis_v]-a[axis_v]
                du2,dv2=c[axis_u]-a[axis_u],c[axis_v]-a[axis_v]
                determinant=du1*dv2-du2*dv1
                if abs(determinant)<1e-12:
                    continue
                uu,vv=u-a[axis_u],v-a[axis_v]
                w1=(uu*dv2-vv*du2)/determinant
                w2=(du1*vv-dv1*uu)/determinant
                if min(w1,w2,1-w1-w2)>=-1e-6:
                    hits.append(a[axis]+w1*(b[axis]-a[axis])+w2*(c[axis]-a[axis]))
        if not hits:
            raise ValueError(f"Graphic misses {name} at {(u,v)}")
        return outer(hits)

    def loft(name, slot, rows, sides, shades, binding, *, shaped=None, smooth=True, caps=True):
        vertices, faces, colors = [], [], []
        for level, (z, x, y, rx, ry, exponent) in enumerate(rows):
            for i in range(sides):
                angle = i * 2*pi/sides
                dx, dy = sin(angle), -cos(angle)
                dx = rx * (1 if dx >= 0 else -1) * abs(dx)**exponent
                dy = ry * (1 if dy >= 0 else -1) * abs(dy)**exponent
                pos = (x+dx, y+dy, z)
                if shaped:
                    pos = shaped(level, pos, angle, dx, dy)
                vertices.append(pos)
        if isinstance(shades, str):
            shades = [shades] * (len(rows)-1)
        for row, shade in enumerate(shades):
            for i in range(sides):
                j = (i+1) % sides
                faces.append((row*sides+i, row*sides+j, (row+1)*sides+j, (row+1)*sides+i))
                colors.append(shade)
        if caps:
            faces += [tuple(reversed(range(sides))), tuple(range((len(rows)-1)*sides,len(rows)*sides))]
            colors.extend([shades[0],shades[-1]])
        surfaces[name] = vertices, faces
        return submit(name, slot, vertices, faces, colors, binding, smooth)

    def patch(name, slot, outline, color, binding, rear=False):
        indexes = tuple(range(len(outline)))
        if rear:
            indexes = indexes[::-1]
        return submit(name, slot, outline, [indexes], color, binding)

    def band(name, slot, pairs, color, binding, rear=False):
        vs = [v for pair in pairs for v in pair]
        fs = [(i*2, i*2+1, i*2+3, i*2+2) for i in range(len(pairs)-1)]
        if rear:
            fs = [f[::-1] for f in fs]
        return submit(name, slot, vs, fs, color, binding)

    def tube(name, slot, path, radius, color, binding):
        # Four-sided tape cord. The tip and eyelet hide the ends.
        vs, fs = [], []
        for x,y,z in path:
            for ox,oy in [(radius,0),(0,radius),(-radius,0),(0,-radius)]:
                vs.append((x+ox,y+oy,z))
        for level in range(len(path)-1):
            for i in range(4):
                j = (i+1)%4
                fs.append((level*4+i,(level+1)*4+i,(level+1)*4+j,level*4+j))
        return submit(name,slot,vs,fs,color,binding)

    def blend(a, b, t):
        t = max(0,min(1,t))
        if t<=0: return a
        if t>=1: return b
        return {a:1-t,b:t}

    def torso(x,y,z):
        return blend('Spine','Chest',(z-.436)/.177)

    # Bell-shaped fleece with a pale ribbed hem. Superellipses give the front graphics a shallow surface.
    loft('Classic fleece',hoodie,[
        (.409,0,0,.153,.094,.84),
        (.442,0,-.002,.166,.101,.84),(.466,0,-.002,.173,.105,.83),
        (.581,0,0,.143,.093,.86),(.680,0,.001,.136,.083,.88),
        (.719,0,.004,.108,.068,.92)],12,
        [cloth_light,'#E8DDF5',cloth,cloth,cloth],torso)
    # Kangaroo pocket, with a seam following each angled hand opening.
    def fleece_face(x,z,offset):
        return (x,surface('Classic fleece',x,z,1,min)-offset,z)
    pocket_rows=[(.458,.107),(.479,.080),(.522,.060)]
    vs=[]
    for z,width in pocket_rows:
        for frac in (-1,-.5,0,.5,1):
            vs.append(fleece_face(width*frac,z,.0035+.002*(1-abs(frac))))
    fs=[(i,i+1,i+6,i+5) for i in (0,1,2,3,5,6,7,8)]
    submit('Kangaroo pocket',hoodie,vs,fs,'#F4EDF9',torso,True)
    for sign, side in [(1,'L'),(-1,'R')]:
        outline=[(sign*.059,.521),(sign*.062,.521),(sign*.084,.479),(sign*.080,.477)]
        patch('Pocket welt '+side,hoodie,[fleece_face(x,z,.0036) for x,z in outline],
              '#D6C7E8',torso,rear=sign==1)

    # Hood rim flares outward at the shoulder and scoops low behind the neck.
    rows=[(.675,0,.024,.071,.050,1),(.708,0,.021,.145,.105,.96),
          (.747,0,.012,.143,.098,.97),(.759,0,.007,.108,.068,1),
          (.744,0,.008,.081,.060,1)]
    def hood_cut(level, pos, angle, dx, dy):
        x,y,z=pos
        back=(1-cos(angle))*.5
        front=(1+cos(angle))*.5
        notch=max(0,cos(angle))**10
        droop=(.063,.050,.026,.018,.012)[level]*back**1.55
        roll=(.0,.003,.015,.021,.016)[level] * (.48+.52*abs(sin(angle)))
        return x,y,z-droop-.016*front-.025*notch+roll
    loft('Hood folded over shoulders',hoodie,rows,12,
         [plum,iris,crocus,'#8F53D2'],bone,shaped=hood_cut,caps=False)
    # Local emblem coordinates are measured on the garment surface.
    def logo(name,slot,cx,z0,w,h,surface,ink,inside,binding,rear=False):
        def at(x,z,depth=0):
            xx,zz=cx+x*w,z0+z*h
            return (xx,surface(xx,zz)+(depth if rear else -depth),zz)
        outline=[(-.50,0),(.50,0),(.41,.65),(-.41,.65)]
        if inside:
            inner=[(-.376,.095),(.376,.095),(.31,.545),(-.31,.545)]
            vs=[at(*p) for p in outline+inner]
            fs=[(i,(i+1)%4,4+(i+1)%4,4+i) for i in range(4)]
            if rear:fs=[f[::-1] for f in fs]
            submit(name+' body',slot,vs,fs,ink,binding)
        else:
            def fill(label,lower,upper,base,top,depth,color):
                vs=[at(x,z,depth) for z,half in ((base,lower),(top,upper)) for x in (-half,0,half)]
                faces=[(0,1,4,3),(1,2,5,4)]
                submit(name+label,slot,vs,faces,color,binding)
            fill(' body',.50,.41,0,.65,0,ink)
            fill(' square label',.175,.175,.17,.44,.0012,white)
            heart=[(-.098,.347),(-.057,.374),(0,.343),(.052,.374),(.098,.347),
                   (.085,.306),(0,.236),(-.085,.306)]
            patch(name+' heart',slot,[at(x,z,.0019) for x,z in heart],crocus,binding)
        pts=[]
        for i in range(9):
            a=pi*i/8
            pts.append((at(.245*cos(a),.565+.40*sin(a),.0003),
                        at(.16*cos(a),.565+.292*sin(a),.0005)))
        band(name+' handle',slot,pts,ink,binding,rear=not rear)
        if inside:
            pts=[(at(-.17,.33,.0005),at(-.155,.36,.0005)),
                 (at(-.02,.23,.0005),at(-.02,.28,.0005)),
                 (at(.16,.36,.0005),at(.18,.33,.0005))]
            band(name+' smile',slot,pts,ink,binding,rear)

    def chest_front(x,z):
        return surface('Classic fleece',x,z,1,min)-.002
    logo('Shopping tote chest print',hoodie,0,.551,.083,.083,chest_front,violet,False,torso)
    for sign, side in [(1,'L'),(-1,'R')]:
        tube('Braided drawcord '+side,hoodie,
             [(sign*.045,-.078,.725),(sign*.046,-.088,.687),(sign*.048,-.095,.638)],
             .0048,iris,bone)
        tube('Drawcord aglet '+side,hoodie,[(sign*.048,-.095,.641),(sign*.048,-.095,.630)],.0048,gold,bone)

        def arm_weight(x,y,z,s=side):
            return blend('Forearm.'+s,'UpperArm.'+s,(z-.559)/.055)
        sleeve_rows=[(.477,sign*.222,-.020,.053,.052,.92),
                     (.485,sign*.220,-.019,.060,.056,.91),
                     (.514,sign*.207,-.015,.064,.060,.92),
                     (.526,sign*.202,-.014,.064,.060,.92),
                     (.563,sign*.186,-.008,.056,.055,.96),
                     
                     (.693,sign*.128,.001,.050,.054,.96),
                     (.710,sign*.113,.002,.034,.042,.98)]
        def cross_sleeve(level,pos,angle,dx,dy,s=sign):
            x,y,z=pos
            return x,y,z+s*dx*.44
        loft('Puff sleeve and violet cuff '+side,hoodie,sleeve_rows,8,
             [plum,iris,crocus,cloth,cloth,cloth],arm_weight,shaped=cross_sleeve)
        # Shoulder straps descend along the lateral surface from back to front.
        route=[(.092,.101,.484,.010),(.102,.091,.611,.015),
               (.105,.052,.698,.016),(.101,.004,.729,.015),
               (.092,None,.704,.016),(.094,None,.672,.017),
               (.100,None,.617,.016),(.106,None,.565,.015),
               (.117,None,.519,.013),(.129,None,.483,.013),
               (.145,None,.461,.010)]
        pairs=[]
        for cx,y,z,half in route:
            edge=[]
            for x in (sign*cx-half,sign*cx+half):
                # The inner strap edge lies further forward on the curved chest.
                # Project both independently so bending the shoulder cannot expose a broken ribbon.
                yy=y if y is not None else surface('Classic fleece',x,z,1,min)-.006
                edge.append((x,yy,z))
            pairs.append(edge)
        band('Padded shoulder strap '+side,bag,pairs,'#45394F',torso,rear=True)
        # A small pin on the upper left front.
        if side=='L':
            patch('Apricot visitor pin',hoodie,[(.072,-.082,.635),(.083,-.079,.632),(.09,-.078,.641),
                (.087,-.079,.650),(.076,-.083,.652),(.069,-.084,.645)],'#F39D78',torso)
            patch('Pin highlight',hoodie,[(.076,-.085,.638),(.082,-.082,.641),(.081,-.083,.646)],'#FFF0CD',torso)

    # Backpack volumes use softer shoulders than the squared cargo pockets.
    loft('Backpack shell',bag,[(.429,0,.121,.075,.028,.63),(.455,0,.125,.107,.054,.55),(.580,0,.120,.109,.056,.59),(.632,0,.110,.096,.046,.67),
         (.658,0,.101,.063,.027,.82)],8,
         ['#433A4E','#493F53','#493F53','#51465C'],torso)
    loft('Front zip pocket',bag,[(.449,0,.168,.064,.011,.54),(.461,0,.169,.083,.022,.55),
         (.540,0,.165,.085,.027,.54),(.558,0,.159,.067,.021,.62)],8,
         ['#4D4255','#504657','#67596D'],torso)
    # Keep logo centered on the front-most area of the zip pocket.
    def back_surface(x,z):
        return surface('Front zip pocket',x,z,1,max)+.0018
    logo('Backpack shopping emblem',bag,0,.474,.071,.067,back_surface,'#F5E9FF',True,torso,True)

    def legs_bind(x,y,z,s):
        return blend('Thigh.'+s,'Hips',(z-.319)/.066)
    def trouser_leg(name,slot,side,lower_rows,seat,waist,shades,binding,hem_drape=0):
        sign=1 if side=='L' else -1
        verts=[]; faces=[]; paint=[]; weights=[]
        def point(x,y,z,w=None):
            p=(sign*x,y,z)
            verts.append(p)
            weights.append(w or binding(*p))
        for k,(z,cx,cy,rx,ry) in enumerate(lower_rows):
            for i in range(8):
                a=i*pi/4
                y=cy-ry*cos(a)
                # A broad back on the final thigh loop supports a cloth seat in the deep bend.
                if k==len(lower_rows)-1 and i in (4,5):
                    y=.079
                elif slot==shorts and k==2 and i==4:
                    y-=.00165
                point(cx+rx*sin(a),y,z-(hem_drape*cos(a) if k<3 else 0))
        # Both inside seams meet at the same weighted pelvis vertices. The notch folds
        # into the crotch, with only the outer arc continuing up to the waistband.
        cut=[(.076,-.083,.347),(.133,-.065,.35),(.163,.002,.35),(.133,.068,.35),
             (.076,.08285,.347),(0,.08225,.339),(0,.002,seat),(0,-.079,.336)]
        for i,(x,y,z) in enumerate(cut):
            if i==4:
                bound='Thigh.'+side
            elif i==5:
                bound={'Thigh.L':.5,'Thigh.R':.5}
            else:
                bound='Hips' if i>=6 else binding(sign*x,y,z)
            point(x,y,z,bound)
        for layer,shade in enumerate(shades):
            for i in range(8):
                j=(i+1)%8
                faces.append((8*layer+i,8*layer+j,8*layer+8+j,8*layer+8+i))
                paint.append(shade)
        seam_base=len(verts)-8
        arc=(7,0,1,2,3,4,5)
        prior=[seam_base+i for i in arc]
        for z,rx,ry,shade in waist:
            base=len(verts)
            for i in range(7):
                theta=i*pi/6
                point(rx*sin(theta),.002-ry*cos(theta),z,'Hips')
            current=[base+i for i in range(7)]
            for i in range(6):
                faces.append((prior[i],prior[i+1],current[i+1],current[i]))
                paint.append(shade)
            prior=current
        if sign<0:
            faces=[f[::-1] for f in faces]
        return submit(name,slot,verts,faces,paint,weights,True)

    for sign, side in [(1,'L'),(-1,'R')]:
        leg=lambda x,y,z,s=side:legs_bind(x,y,z,s)
        trouser_leg('Cargo shorts leg '+side,shorts,side,[
             (.262,.091,0,.054,.052),(.245,.091,0,.081,.074),
             (.255,.091,0,.086,.079),(.292,.089,.001,.084,.081)],
             .294,[(.389,.151,.089,charcoal),(.428,.139,.085,piping)],
             ['#28252F','#393440',charcoal,charcoal],leg,hem_drape=.013)
        def pouch_shape(level,pos,angle,dx,dy,s=sign):
            x,y,z=pos
            return x,y+s*dx*.55,z
        loft('Cargo bellows pocket '+side,shorts,[(.272,sign*.150,-.025,.015,.034,.52),
             (.320,sign*.151,-.023,.017,.038,.52),
             (.330,sign*.149,-.022,.020,.039,.52),(.339,sign*.147,-.020,.019,.034,.53)],6,
             ['#48424F',flap,piping],leg,shaped=pouch_shape)
    patch('Violet side label',hoodie,[(.102,-.084,.412),(.126,-.075,.412),(.126,-.076,.435),(.101,-.085,.435)],
          plum,torso)

    for sign,side in [(1,'L'),(-1,'R')]:
        x=sign*.099
        foot='Foot.'+side
        shoe='Shoe.'+side
        shin='Shin.'+side
        loft('Folded sock '+side,'Sock.'+side,[(.087,x,.004,.054,.050,.91),
             (.156,x,.005,.058,.053,.91),
             (.166,x,.005,.056,.051,.91)],8,[white,'#EAE0F2'],shin)
        # The asymmetric foot last has a wide, blunt toe and a narrow raised heel.
        footrows=[(.000,x,-.027,.091,.122,.73),(.009,x,-.028,.097,.126,.73),
                  (.036,x,-.029,.099,.127,.72),(.044,x,-.029,.095,.125,.73),
                  (.067,x,-.024,.089,.117,.80),(.091,x,-.012,.077,.092,.85),
                  (.118,x,.014,.058,.065,.89)]
        def last_shape(level,pos,a,dx,dy):
            xx,yy,zz=pos
            rear=(1-cos(a))*.5
            return x+dx*(1-.19*rear),yy,zz+(.000,.0,.000,.002,.010,.015,.012)[level]*rear
        loft('Court trainer '+side,shoe,footrows,10,
             ['#E8D9E3',sole,white,white,iris,'#7444BC'],foot,shaped=last_shape)
        # White leather toe guard wraps three frontal facets and follows the foot last.
        def sneaker_y(a,level):
            z,cx,cy,rx,ry,e=footrows[level]
            si,co=sin(a),cos(a)
            dx=rx*(1 if si>=0 else -1)*abs(si)**e
            dy=-ry*(1 if co>=0 else -1)*abs(co)**e
            px,py,pz=last_shape(level,(cx+dx,cy+dy,z),a,dx,dy)
            return px,py-.0015,pz+.0008
        pairs=[(sneaker_y(i*pi/12,4),sneaker_y(i*pi/12,5)) for i in range(-3,4)]
        band('Leather toe cap '+side,shoe,pairs,'#FEF6F8',foot,rear=True)
        # The padded violet tongue rises in front of the sock above the white laces.
        tongue=[]
        for yy,zz,w in [(-.099,.091,.027),(-.069,.114,.030),(-.050,.143,.030),(-.046,.151,.023)]:
            tongue.extend([(x-w,yy+.003,zz-.001),(x,yy-.001,zz+.001),(x+w,yy+.003,zz-.001)])
        tongue_faces=[(k,k+1,k+4,k+3) for k in (0,1,3,4,6,7)]
        submit('Padded sneaker tongue '+side,shoe,tongue,tongue_faces,
               [iris,iris,'#965BD8','#965BD8',crocus,crocus],foot,True)
        for j in range(2):
            yy=-.089+j*.023
            pairs=[]
            for off in (-.041,-.019,0,.019,.041):
                y=yy+.006*(off/.041)**2+.001*(off/.041)
                pair=[]
                for edge in (y+.0045,y-.0045):
                    top=surface('Court trainer '+side,x+off,edge,2,max)
                    pair.append((x+off,edge,top+.0025))
                pairs.append(pair)
            band('Flat lace '+side+str(j+1),shoe,pairs,white,foot)
        coords=[(-.058,.056),(-.042,.079),(-.018,.070),
                (.022,.089),(.012,.069),(-.014,.052)]
        outside=max if sign>0 else min
        stripe=[(surface('Court trainer '+side,y,z,0,outside)+sign*.002,y,z) for y,z in coords]
        patch('Gold quarter flash '+side,shoe,stripe,gold,foot,rear=sign>0)

    # Sports cap is a full alternative accessory with a contrasting crown insert and bill.
    hat='Hat'
    loft('Blue cap crown',hat,[(1.139,0,.005,.277,.236,.97),(1.151,0,.005,.287,.246,.97),
         (1.190,0,.005,.285,.244,.98),(1.246,0,.015,.255,.220,.99),
         (1.288,0,.023,.188,.165,1),(1.318,0,.030,.095,.080,1),
         (1.324,0,.032,.012,.010,1)],12,
         ['#283D78','#5579BA','#F0EDF5','#F6F3F4','#E6E3EF','#D8D9E9'],'Head')
    # A curved bill fits against the crown rather than slicing through the eyes.
    bill=[]
    for i in range(9):
        t=(i-4)/4
        a=t*1.2
        inner=(.267*sin(a),-.232*cos(a),1.153-.015*t*t)
        outer=(.286*sin(a),-.353+.230*abs(t)**1.75,1.139-.018*t*t)
        bill.append((inner,outer))
    band('Curved cap bill',hat,bill,'#5482C5','Head')
    jeans='Jeans'
    for sign,side in [(1,'L'),(-1,'R')]:
        def denim(x,y,z,s=side):
            # The tucked cuff follows the ankle collar through extreme calf rotation.
            if z<=.208:return blend('Foot.'+s,'Shin.'+s,(z-.175)/.035)
            if z>.31:return legs_bind(x,y,z,s)
            return blend('Shin.'+s,'Thigh.'+s,(z-.192)/.055)
        trouser_leg('Indigo jeans '+side,jeans,side,[
             (.121,.098,.005,.046,.038),(.109,.098,.005,.051,.041),
             (.131,.098,.006,.057,.042),(.173,.098,.008,.062,.045),
             (.208,.095,.001,.068,.061),
             (.232,.094,-.002,.070,.064),(.281,.091,0,.076,.074)],
             .295,[(.390,.146,.084,'#53698E'),(.423,.139,.080,'#4A6085')],
             ['#475E83','#7890B1','#4E6289','#4E6289','#52698D','#536A92','#52678F'],denim)
