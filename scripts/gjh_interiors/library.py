"""Retopology inputs from the gallery's editable native parts. Never save into a source file."""
from hashlib import sha256
from math import cos, sin, tau
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def physical(point):
    return (point.x,-point.y,point.z)


class Parts:
    def __init__(self, fixture):
        self.f = fixture
        spec = fixture.spec
        repo = Path(__file__).resolve().parents[2]
        original = repo/spec["source_blend"]
        for path,key in ((original,"blend_sha256"),(repo/spec["anchor"]["source"],"source_sha256")):
            if sha256(path.read_bytes()).hexdigest()!=spec[key]:
                raise ValueError(f"Source differs from reviewed input: {path}")
        bpy.ops.wm.open_mainfile(filepath=str(original),load_ui=False,use_scripts=False)
        scene = bpy.context.scene
        scene.frame_set(scene.frame_start)
        root, = [o for o in scene.objects if o.name.startswith("ASSET_") and o.parent is None]
        self.objects = sorted((o for o in root.children_recursive
                               if o.type=="MESH" and not o.name.lower().startswith("collider")),
                              key=lambda o:o.name)
        coords = [o.matrix_world @ v.co for o in self.objects for v in o.data.vertices]
        fixture.source_bounds = (list(map(min,zip(*coords))),list(map(max,zip(*coords))))

    @staticmethod
    def bounds(obj):
        pts = [physical(obj.matrix_world @ v.co) for v in obj.data.vertices]
        return list(map(min,zip(*pts))), list(map(max,zip(*pts)))

    def copy(self, obj, color, pattern=0, bevel=0, simplify=0):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        if simplify:
            bmesh.ops.dissolve_limit(bm,angle_limit=simplify,verts=list(bm.verts),edges=list(bm.edges))
        bm.verts.index_update()
        self.f.solid([physical(obj.matrix_world @ v.co) for v in bm.verts],
                     [[v.index for v in face.verts] for face in bm.faces],color,pattern,bevel)
        bm.free()

    def box(self,obj,color,pattern=0,bevel=0):
        lo,hi = self.bounds(obj)
        self.f.box([(l+h)/2 for l,h in zip(lo,hi)],[h-l for l,h in zip(lo,hi)],
                   color,pattern,bevel)

    def cylinder(self,obj,color,sides,axis=2):
        lo,hi = self.bounds(obj)
        axes = [k for k in range(3) if k!=axis]
        mid = [(h+l)/2 for l,h in zip(lo,hi)]
        rings = []
        for plane in (lo[axis],hi[axis]):
            ring = []
            for i in range(sides):
                pt = mid.copy()
                pt[axis] = plane
                for k,offset in zip(axes,(cos(tau*i/sides),sin(tau*i/sides))):
                    pt[k] += offset*(hi[k]-lo[k])/2
                ring.append(pt)
            rings.append(ring)
        self.f.rings(rings,color,smooth=True)


def derive(f, retopology):
    source = Parts(f)
    retopology(f,source)
    # Only plain geometric arrays cross this boundary. The derivative scene
    # receives no source animation, drivers, embedded scripts or studio objects.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
