"""Slot-local (+Y up, +Z out) modelling tools for the GJH room dressing."""
from collections import defaultdict
from functools import lru_cache
from math import cos, sin, tau
import json
import struct

import bpy
from mathutils import Vector


from palette import SWATCHES

CRAFT, PRINT, PULSE, SCROLL = "Enamel", "Printed opal", "Pulse", "Scroll"


def linear(hexcode):
    rgb = tuple(int(hexcode[i:i+2], 16)/255 for i in (0, 2, 4))
    return [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb]+[1]


def swatch(hexcode):
    def distance(code):
        return sum((int(code[i:i+2], 16)-int(hexcode[i:i+2], 16))**2 for i in (0, 2, 4))
    index = min(range(len(SWATCHES)), key=lambda i: distance(SWATCHES[i]))
    x,y = 72+16*(index%4),133+10*(index//4)
    return (x,y,x+1,y+1)


def logo(slot):
    i = slot-1
    return (64*(i%4)+1, 32*(i//4)+1, 64*(i%4)+63, 32*(i//4)+31)


def ticket(i):
    x = (i%3)*64
    return (x+1, 235, x+62, 254)


@lru_cache(maxsize=4)
def library_profile(path, mesh_name, samples):
    """Resample the original gallery lathe at authored heights, in mesh-local metres."""
    raw = path.read_bytes()
    length = struct.unpack_from("<I",raw,12)[0]
    doc = json.loads(raw[20:20+length])
    mesh = next(m for m in doc["meshes"] if m["name"] == mesh_name)
    ac = doc["accessors"][mesh["primitives"][0]["attributes"]["POSITION"]]
    view = doc["bufferViews"][ac["bufferView"]]
    start = 28+length+view.get("byteOffset",0)+ac.get("byteOffset",0)
    rings = defaultdict(list)
    for i in range(ac["count"]):
        x,y,z = struct.unpack_from("<3f", raw, start+i*view.get("byteStride",12))
        rings[round(y,5)].append((x*x+z*z)**.5)
    heights = sorted(rings)
    peak = max(max(r) for r in rings.values())
    return [(max(.025,max(rings[y])/peak),(y-heights[0])/(heights[-1]-heights[0]))
            for y in dict.fromkeys(heights[round(k*(len(heights)-1)/(samples-1))] for k in range(samples))]


class Mesh:
    def __init__(self):
        self.points, self.faces, self.colours, self.uvs = [], [], [], []

    def face(self, points, colour, rect=None):
        base = len(self.points)
        self.points.extend((x,-z,y) for x,y,z in points)
        self.faces.append(tuple(range(base,base+len(points))))
        self.colours.extend([colour]*len(points))
        l,t,r,b = rect or (0,0,1,1)
        uv = [(l,b),(r,b),(r,t),(l,t)] if rect and len(points)==4 else [(l,t)]*len(points)
        self.uvs.extend((u/256,1-v/256) for u,v in uv)

    def object(self, name, mat, painted):
        data = bpy.data.meshes.new(name)
        data.from_pydata(self.points, [], self.faces)
        data.materials.append(mat)
        if painted:
            colours = data.color_attributes.new(name="Pigment",type="FLOAT_COLOR",domain="POINT")
            colours.data.foreach_set("color",[v for hexcode in self.colours for v in linear(hexcode)])
        else:
            uv = data.uv_layers.new(name="Print")
            uv.data.foreach_set("uv",[v for loop in data.loops for v in self.uvs[loop.vertex_index]])
        obj = bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(obj)
        return obj


class Room:
    def __init__(self, slot):
        self.slot = slot
        self.floor = .032 if slot <= 3 else .091
        self.batches = defaultdict(Mesh)
        self.instances = []

    def face(self, points, c, finish=CRAFT, rect=None):
        self.batches[finish].face(points,c,rect or (swatch(c) if finish!=CRAFT else None))

    def box(self, x,y,z,w,h,d,c,finish=CRAFT,yaw=0):
        def pt(i,j,k):
            u,v = i*w/2,k*d/2
            return (x+u*cos(yaw)+v*sin(yaw), y+j*h/2, z-u*sin(yaw)+v*cos(yaw))
        for face in (((-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)),
                     ((1,-1,-1),(-1,-1,-1),(-1,1,-1),(1,1,-1)),
                     ((-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1)),
                     ((1,-1,1),(1,-1,-1),(1,1,-1),(1,1,1)),
                     ((-1,1,1),(1,1,1),(1,1,-1),(-1,1,-1)),
                     ((-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1))):
            self.face([pt(*p) for p in face],c,finish)

    def panel(self,x,y,z,w,h,rect,finish=PRINT,yaw=0):
        self.face([(x+i*w*cos(yaw),y+j*h,z-i*w*sin(yaw))
                   for i,j in ((-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5))],
                  "ffffff",finish,rect)

    def lathe(self,x,y,z,r,h,profile,colors,n=8,finish=CRAFT,depth=1):
        rings = [[(x+r*radius*cos(i*tau/n),y+h*height,z+r*depth*radius*sin(i*tau/n))
                  for i in range(n)] for radius,height in profile]
        for k,(lo,hi) in enumerate(zip(rings,rings[1:])):
            for i in range(n):
                j=(i+1)%n
                self.face([lo[j],lo[i],hi[i],hi[j]],colors[k%len(colors)],finish)
        self.face(rings[0],colors[0],finish)
        self.face(rings[-1][::-1],colors[-1],finish)

    def line(self,a,b,width,c,finish=CRAFT):
        # Four-sided brass rods and fabric piping. Pick a stable cross-section
        # even for cables running vertically.
        a,b=Vector(a),Vector(b)
        direction=(b-a).normalized()
        normal=direction.cross(Vector((0,1,0) if abs(direction.y)<.9 else (1,0,0))).normalized()*width*.5
        side=direction.cross(normal)
        offsets=(normal+side,-normal+side,-normal-side,normal-side)
        for i,p in enumerate(offsets):
            q=offsets[(i+1)%4]
            self.face([a+p,a+q,b+q,b+p],c,finish)

    def ribbon(self,path,width,c,finish=PRINT,floor=False):
        """Flat joined strokes in the X/Y wall or X/Z floor plane."""
        edges=[]
        for i,point in enumerate(path):
            a,b=path[max(0,i-1)],path[min(len(path)-1,i+1)]
            axis=2 if floor else 1
            dx,dy=b[0]-a[0],b[axis]-a[axis]
            length=(dx*dx+dy*dy)**.5 or 1
            off=(-dy/length*width/2,dx/length*width/2)
            pair=[]
            for sign in (-1,1):
                p=list(point);p[0]+=sign*off[0];p[axis]+=sign*off[1]
                pair.append(p)
            edges.append(pair)
        for (a,b),(c1,d) in zip(edges,edges[1:]):
            points=[a,c1,d,b]
            self.face(points[::-1] if floor else points,c,finish)

    def ring(self,x,y,z,rx,ry,w,c,finish=PRINT,floor=False,start=0,end=tau,n=24):
        pts=[(x+rx*cos(t), y if floor else y+ry*sin(t), z+ry*sin(t) if floor else z)
             for t in [start+(end-start)*i/n for i in range(n+1)]]
        self.ribbon(pts,w,c,finish,floor)

    def badge(self,x,y,z,w,h=None,yaw=0):
        self.panel(x,y,z,w,h or w*.48,logo(self.slot),yaw=yaw)

    def tag(self,x,y,z,w=.31,i=0,yaw=0):
        self.panel(x,y,z,w,w*.32,ticket(i),yaw=yaw)

    def stock(self, prototype, locations):
        self.instances.append((prototype,locations))
