"""Flat-colour parcel, paper market bag and jam sample on a short return shelf."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from build_props import Mesh
from build import JAR_PICK, JAR_HOME

def panel(m,center,half,z0,z1,cut,mat,top=None):
    x,y=center
    hx,hy=half
    loops=[]
    for z,delta in [(z0,cut),(z0+cut,0),(z1-cut,0),(z1,cut)]:
        a,b=hx-delta,hy-delta
        r=min(max(.0004,cut),a*.2,b*.2)
        outline=[(a,b-r),(a-r,b),(-a+r,b),(-a,b-r),(-a,-b+r),(-a+r,-b),(a-r,-b),(a,-b+r)]
        loops.append([(x+i,y+j,z) for i,j in outline])
    m.rings(loops,[mat]*3,[mat,mat if top is None else top])

def rod(m, path, radius, mat, axis=X, sides=8):
    pts=[Vector(p) for p in path]
    rings=[]
    for i,p in enumerate(pts):
        d=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        u=(axis-d*axis.dot(d)).normalized()
        v=d.cross(u)
        rings.append([p+radius*(u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides)) for k in range(sides)])
    m.rings(rings,[mat]*(len(pts)-1),[mat,mat])

def decal(m,center,points,normal,horizontal,mat,thickness=.0005):
    n=Vector(normal);u=Vector(horizontal);v=n.cross(u)
    c=Vector(center)
    loops=[[c+x*u+y*v+n*d for x,y in points] for d in (0,thickness)]
    m.rings(loops,[mat],[mat,mat])

def circle(r,n=18):
    return [(r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n)) for i in range(n)]

def arrow(m,x,y,z,mat):
    pts=[(-.004,0),(.004,0),(.004,.014),(.009,.014),(0,.026),(-.009,.014),(-.004,.014)]
    decal(m,(x,y,z),pts,-Y,X,mat)

def parcel():
    m=Mesh()
    panel(m,(0,0),(.152,.109),0,.216,.003,0,1)
    # Packing tape over the top seam, returning down both ends.
    panel(m,(0,0),(.021,.108),.2154,.2168,.0003,2)
    for s in (-1,1):
        decal(m,(0,s*.1088,.174),[(-.021,-.041),(.021,-.041),(.021,.042),(-.021,.042)],Y*s,X*(-s),2)
    decal(m,(-.079,-.109,.139),[(-.043,-.025),(.038,-.025),(.043,-.020),(.043,.025),(-.043,.025)],-Y,X,3)
    for i,wd in enumerate((.002,.001,.003,.001,.002,.003,.001)):
        x=-.106+.0055*i
        decal(m,(x,-.10955,.14),[(-wd,-.013),(wd,-.013),(wd,.013),(-wd,.013)],-Y,X,4,.00025)
    for x in (.082,.105):arrow(m,x,-.109,.027,4)
    return m.object('Parcel',[('Kraft',(.54,.269,.115)),('Folded lid',(.66,.361,.171)),('Honey paper tape',(.79,.50,.245)),
                              ('Shipping label',(.93,.82,.62)),('Cocoa ink',(.13,.053,.029))])

BAG_DX=-.0028
BAG_DZ=-.0106
BAG_RADIUS=.010
def market_bag():
    m=Mesh()
    # Nested outlines form an open paper shell, bottom and inset inner walls.
    def ring(w,d,z,fold):
        return [(w,d-.006,z),(w-.006,d,z),(0,d-fold,z-.002),(-w+.006,d,z),(-w,d-.006,z),
                (-w,-d+.006,z),(-w+.006,-d,z),(0,-d+fold,z-.002),(w-.006,-d,z),(w,-d+.006,z)]
    loops=[ring(.028,.070,-.255,.002),ring(.031,.074,-.249,.002),ring(.037,.086,-.136,.011),
           ring(.0375,.086,-.121,.012),ring(.035,.0835,-.121,.012),ring(.029,.071,-.247,.002)]
    m.rings(loops,[2,0,1,2,3],[2,3])
    # The inner handle has a padded grip and reinforced eyelets on the paper.
    for s in (-1,1):
        x=s*.037
        for d in (-1,1):
            if s>0:
                rod(m,[(x,d*.055,-.134),(x*.97,d*.056,-.116),(x*.48,d*.066,-.043),
                       (x*.24,d*.062,-.021),(BAG_DX,d*.054,BAG_DZ)],.0028,2)
            decal(m,(x,d*.055,-.133),circle(.005,10),X*s,Y*s,4)
    rod(m,[(BAG_DX,-.056,BAG_DZ),(BAG_DX,.056,BAG_DZ)],BAG_RADIUS,2,sides=16)
    # The outer cord folds over under its own weight. Each handle stays separate.
    x,z=-.037,-.047
    cord=[(-.037,-.055,-.134),(-.038,-.061,-.100),(x,-.066,z-.025),(x,-.063,z-.007),(x,-.055,z),
          (x,.055,z),(x,.063,z-.007),(x,.066,z-.025),(-.038,.061,-.100),(-.037,.055,-.134)]
    rod(m,cord,.0036,2,sides=10)
    # The two faces carry a citrus emblem visible from either side.
    for s in (-1,1):
        pos=Vector((s*.035,0,-.180))
        normal=Vector((s,0,-.054)).normalized()
        decal(m,pos,circle(.025),normal,Y*s,4)
        decal(m,pos+normal*.001,circle(.018,16),normal,Y*s,5)
        decal(m,pos+normal*.0018+Z*.019,[(0,0),(.006,.006),(.015,.008),(.010,.002)],normal,Y*s,2)
    return m.object('Market bag',[('Sea glass paper',(.091,.46,.387)),('Mint cuff',(.166,.59,.49)),
                                   ('Deep pine cord',(.025,.143,.126)),('Shadow mint lining',(.086,.32,.27)),
                                   ('Oat print',(.96,.79,.54)),('Mandarin print',(.94,.288,.072))])

def preserves():
    m=Mesh()
    # Leave a skin-clearance margin around the measured small-grip gauge.
    profile=[(.019,-.081),(.027,-.078),(.030,-.072),(.030,-.054),(.026,-.049),
             (.0191,-.043),(.0191,.020),(.0193,.021),(.0193,.025),(.018,.028)]
    m.rings([[(x,y,z) for x,y in circle(r,24)] for r,z in profile],
            [0,0,1,0,0,2,3,3,3],[0,3])
    for a in range(0,24,3):
        cx,cy=circle(.011,24)[a]
        decal(m,(cx,cy,.02805),circle(.0024,8),Z,X,4,.0002)
    ob=m.object('Jam jar',[('Berry glass',(.44,.043,.065)),('Preserve label',(.98,.704,.43)),
                           ('Rose label',(.74,.178,.21)),('Cherry lid',(.62,.045,.064)),('Cream dot',(.98,.80,.55))])
    ob.location=JAR_PICK
    return ob

def display():
    m=Mesh()
    x=(JAR_HOME.x+JAR_PICK.x)*.5
    y=(JAR_HOME.y+JAR_PICK.y)*.5
    top=JAR_PICK.z-.081
    panel(m,(x,y),(.052,.088),top-.017,top,.002,0,1)
    # A compact pedestal and foot make the shelf segment freestanding.
    panel(m,(x,y-.052),(.035,.016),.014,top-.013,.003,2)
    panel(m,(x,y-.050),(.057,.041),0,.017,.003,0)
    panel(m,(x,y-.088),(.048,.0013),top-.012,top-.004,.0007,2)
    for off in (-.016,.016):
        panel(m,(x+off,y),(.001,.068),top-.0001,top+.0002,.00007,3)
    return m.object('Display rail',[('Maple edge',(.42,.20,.079)),('Maple shelf',(.66,.396,.190)),
                                     ('Petrol enamel',(.045,.23,.225)),('Brass rail inlay',(.79,.50,.174))])

if __name__=='__main__':
    setup()
    for fn,stem in ((parcel,'box'),(market_bag,'bag')):
        export(fn(),str(HERE/'props'/(stem+'.glb')),export_animations=False)
    jar=preserves();shelf=display()
    bpy.ops.object.select_all(action='DESELECT')
    for o in (jar,shelf):o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(HERE/'props/shelf_item.glb'),export_format='GLB',use_selection=True,export_animations=False)
