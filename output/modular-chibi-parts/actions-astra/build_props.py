"""One mesh per prop. All parts are closed, consistently wound solids."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chibi import *
from build_actions import SEAT


class Mesh:
    def __init__(self):
        self.v, self.f, self.ids = [], [], []

    def rings(self, loops, colors, cap_colors):
        n = len(loops[0])
        start = len(self.v)
        self.v.extend(v for ring in loops for v in ring)
        self.f.append(tuple(start+i for i in reversed(range(n))))
        self.ids.append(cap_colors[0])
        for l, color in enumerate(colors):
            i = start+l*n
            for j in range(n):
                k = (j+1)%n
                self.f.append((i+j,i+k,i+n+k,i+n+j))
                self.ids.append(color)
        last = start+(len(loops)-1)*n
        self.f.append(tuple(last+j for j in range(n)))
        self.ids.append(cap_colors[-1])

    def object(self, name, palette):
        data = bpy.data.meshes.new(name)
        data.from_pydata(self.v, [], self.f)
        data.update()
        ob = bpy.data.objects.new(name,data)
        bpy.context.scene.collection.objects.link(ob)
        for label, col in palette:
            mat = bpy.data.materials.new(label)
            mat.diffuse_color=(*col,1)
            mat.use_nodes=True
            bs=mat.node_tree.nodes.get('Principled BSDF')
            bs.inputs['Base Color'].default_value=(*col,1)
            bs.inputs['Roughness'].default_value=.48
            data.materials.append(mat)
        for p, i in zip(data.polygons,self.ids): p.material_index=i
        data.calc_loop_triangles()
        print('ASSET',name,len(data.loop_triangles),flush=True)
        return ob


def rounded(w,d,r,k=4):
    result=[]
    for i,(sx,sy) in enumerate([(1,1),(-1,1),(-1,-1),(1,-1)]):
        for j in range(k+1):
            a=math.pi/2*(i+j/k)
            result.append((sx*(w-r)+r*math.cos(a),sy*(d-r)+r*math.sin(a)))
    return result


def board(mesh, w, d, r, bottom, top, bevel, colors):
    loops=[]
    for z,cut in [(bottom,bevel),(bottom+bevel,0),(top-bevel,0),(top,bevel)]:
        loops.append([(x,y,z) for x,y in rounded(w-cut,d-cut,r-cut)])
    mesh.rings(loops,colors,(colors[0],colors[-1]))


def spindle(mesh,start,end,r0,r1,material):
    a,b=Vector(start),Vector(end)
    axis=(b-a).normalized()
    ly=axis.cross(X).normalized()
    lx=ly.cross(axis).normalized()
    loops=[]
    for t,r in [(0,r0*.83),(.018,r0),(.96,r1),(1,r1*.90)]:
        center=a.lerp(b,t)
        loops.append([center+lx*(r*math.cos(i*math.tau/12))+ly*(r*math.sin(i*math.tau/12)) for i in range(12)])
    # A splayed leg still stands on a horizontal cut.
    if a.z==0:
        loops[0]=[(p.x,p.y,0) for p in loops[0]]
    mesh.rings(loops,[material]*3,[material]*2)


def chair():
    m=Mesh()
    board(m,.160,.103,.027,SEAT-.034,SEAT-.015,.004,[0,0,0])
    board(m,.164,.106,.031,SEAT-.018,SEAT,.005,[2,2,1])
    for sx in [-1,1]:
        for sy in [-1,1]:
            spindle(m,(sx*.145,sy*.090,0),(sx*.125,sy*.067,SEAT-.022),.011,.015,0)
        spindle(m,(sx*.129,.066,SEAT-.026),(sx*.129,.111,.478),.013,.012,0)
    # Curved plywood back: rounded outline in X/Z; the sides sweep toward the sitter.
    loops=[]
    for thick,cut in [(.010,.004),(.006,0),(-.006,0),(-.010,.004)]:
        ring=[]
        for x,z in rounded(.156-cut,.054-cut,.033-cut,5):
            y=.116+.17*z-.022*(x/.156)**2+thick
            ring.append((x,y,.445+z))
        loops.append(ring)
    # The cross-section faces -Y, so progressively decreasing Y is positive extrusion.
    m.rings(loops,[0,0,3],(0,3))
    ob=m.object('Chair',[
        ('Honey birch',(.51,.268,.109)),('Lagoon cushion',(.054,.36,.32)),
        ('Lagoon welt',(.028,.206,.184)),('Celadon back',(.184,.50,.399))])
    ob['seat_height_m']=SEAT
    ob['forward_blender']='-Y'
    export(ob,'chair.glb',export_animations=False)


def cup():
    m=Mesh()
    # A handleless ceramic tasting cup. The straight section is the grip gauge.
    profile=[(.0163,-.044),(.0194,-.042),(.020,-.038),(.020,.029),
             (.0203,.038),(.0217,.045),(.0226,.047),
             (.0226,.049),(.0218,.050),(.0192,.050),(.0187,.048),(.0173,-.037)]
    loops=[[(r*math.cos(i*math.tau/24),r*math.sin(i*math.tau/24),z) for i in range(24)] for r,z in profile]
    m.rings(loops,[0,0,1,1,1,2,2,2,2,3,3],(0,3))
    ob=m.object('Tasting cup',[
        ('Terracotta foot',(.47,.156,.058)),('Clementine glaze',(.74,.225,.065)),
        ('Oat rim',(.91,.72,.46)),('Ivory ceramic',(.91,.82,.63))])
    ob['mount_bone']=N+'RightHand'
    export(ob,'prop.glb',export_animations=False)


if __name__=='__main__':
    fresh()
    chair()
    cup()
