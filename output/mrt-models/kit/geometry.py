"""Geometry extracted from gallery exports and simplified in their local frames."""
from collections import defaultdict
from math import cos, sin, tau
from mathutils import Matrix, Vector

IDENTITY = Matrix.Identity(4)

def bounds(points):
    points = list(points)
    return (Vector([min(v[i] for v in points) for i in range(3)]),
            Vector([max(v[i] for v in points) for i in range(3)]))

def part_name(obj):
    return obj.name.split('.')[0]

class Model:
    def __init__(self):
        self.meshes = defaultdict(lambda: defaultdict(list))
        self.pivots = {'body': Vector((0,0,0))}
        self.moves = {}

    def face(self, points, style, group='body', center=None, normals=None):
        points = list(map(Vector, points))
        face_normal = (points[1]-points[0]).cross(points[2]-points[0]).normalized()
        if center is not None and face_normal.dot(points[0]-center) < 0:
            points.reverse()
            face_normal.negate()
            normals = normals[::-1] if normals else None
        normals = normals or [face_normal]*len(points)
        material, color = style
        target = self.meshes[group][material]
        for index in range(1,len(points)-1):
            a,b,c = (0,index,index+1)
            if (points[b]-points[a]).cross(points[c]-points[a]).length <= 1e-12:
                continue
            target.append(tuple((points[i], normals[i], color) for i in (a,b,c)))

    def box(self, low, high, style, group='body', transform=IDENTITY,
            chamfer=0, axis=2, skip=(), corner_pair=None):
        low, high = Vector(low), Vector(high)
        assert all(a<b for a,b in zip(low,high)), (tuple(low),tuple(high))
        u,v = [i for i in range(3) if i != axis]
        x,X,y,Y = low[u], high[u], low[v], high[v]
        r = min(chamfer,(X-x)*.48,(Y-y)*.48)
        section = ([(x+r,y),(X-r,y),(X,y+r),(X,Y-r),(X-r,Y),(x+r,Y),(x,Y-r),(x,y+r)]
                   if r else [(x,y),(X,y),(X,Y),(x,Y)])
        if r and corner_pair=='low_u':
            section = [(x+r,y),(X,y),(X,Y),(x+r,Y),(x,Y-r),(x,y+r)]
        if r and corner_pair=='high_v':
            section = [(x,y),(X,y),(X,Y-r),(X-r,Y),(x+r,Y),(x,Y-r)]
        rings = []
        for height in (low[axis],high[axis]):
            ring = []
            for a,b in section:
                point = Vector((0,0,0))
                point[u],point[v],point[axis] = a,b,height
                ring.append(transform @ point)
            rings.append(ring)
        bottom,top = rings
        center = transform @ ((low+high)/2)
        for key,points in enumerate(rings):
            if key not in skip:
                self.face(points,style,group,center)
        for i in range(len(section)):
            k = (i+1)%len(section)
            if i+2 not in skip:
                self.face((bottom[i],bottom[k],top[k],top[i]),style,group,center)

    def part(self, obj, style, *, group='body', before=IDENTITY, chamfer=0, axis=2, skip=(), corner_pair=None):
        low,high = bounds(v.co for v in obj.data.vertices)
        self.box(low,high,style,group,before @ obj.matrix_world,chamfer,axis,skip,corner_pair)

    def beveled_faces(self, obj, style, depth, inset, axis, corner=0):
        low,high = bounds(v.co for v in obj.data.vertices)
        u,v = [i for i in range(3) if i != axis]
        rings = []
        for height,margin in [(low[axis],inset),(low[axis]+depth,0),
                              (high[axis]-depth,0),(high[axis],inset)]:
            ring = []
            x,X,y,Y = low[u]+margin,high[u]-margin,low[v]+margin,high[v]-margin
            r = corner
            section = ([(x+r,y),(X-r,y),(X,y+r),(X,Y-r),(X-r,Y),(x+r,Y),(x,Y-r),(x,y+r)]
                       if r else [(x,y),(X,y),(X,Y),(x,Y)])
            for a,b in section:
                point = Vector((0,0,0))
                point[u],point[v],point[axis] = a,b,height
                ring.append(obj.matrix_world @ point)
            rings.append(ring)
        center = obj.matrix_world @ ((low+high)/2)
        self.face(rings[0],style,center=center)
        self.face(rings[-1],style,center=center)
        for a,b in zip(rings,rings[1:]):
            for i in range(len(a)):
                j = (i+1)%len(a)
                self.face((a[i],a[j],b[j],b[i]),style,center=center)

    def rod(self, obj, style, segments, group='body'):
        low,high = bounds(v.co for v in obj.data.vertices)
        radius = (high.x-low.x)/2
        self.lathe(obj.matrix_world,[(low.z,radius),(high.z,radius)],segments,style,group)

    def lathe(self, transform, profile, segments, style, group, closed=False):
        angles = [(cos(tau*i/segments),sin(tau*i/segments)) for i in range(segments)]
        normal_matrix = transform.to_3x3().inverted().transposed()
        rings = [[transform @ Vector((x*r,y*r,h)) for x,y in angles] for h,r in profile]
        for index in range(len(rings) if closed else len(rings)-1):
            a,b = rings[index],rings[(index+1)%len(rings)]
            h1,r1 = profile[index]
            h2,r2 = profile[(index+1)%len(rings)]
            for i in range(segments):
                j = (i+1)%segments
                # Profile tangents give smooth circumferential normals with sharp profile breaks.
                normals = [(normal_matrix @ Vector((angles[k][0]*(h2-h1),
                           angles[k][1]*(h2-h1),r1-r2))).normalized() for k in (i,j,j,i)]
                self.face((a[i],a[j],b[j],b[i]),style,group,normals=normals)
        if not closed:
            for idx in (0,-1):
                center = transform @ Vector((0,0,(profile[0][0]+profile[-1][0])/2))
                self.face(rings[idx],style,group,center)

    def source_mesh(self, obj, style):
        mesh = obj.data
        mesh.calc_loop_triangles()
        transform = obj.matrix_world
        normal_matrix = transform.to_3x3().inverted().transposed()
        for tri in mesh.loop_triangles:
            normals = [(normal_matrix @ mesh.corner_normals[i].vector).normalized() for i in tri.loops]
            self.face([transform @ mesh.vertices[i].co for i in tri.vertices],style,normals=normals)

    def cap_text(self, obj, style, transform=IDENTITY):
        obj.data.calc_loop_triangles()
        matrix = transform @ obj.matrix_world
        for triangle in obj.data.loop_triangles:
            if triangle.normal.z > .999:
                self.face([matrix @ obj.data.vertices[i].co for i in triangle.vertices],style)

    def front_quad(self, x1, x2, y, z1, z2, style, group='body'):
        self.face(((x1,y,z1),(x2,y,z1),(x2,y,z2),(x1,y,z2)),style,group)
