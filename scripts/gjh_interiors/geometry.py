"""Closed solids in fixture coordinates (right, forward, up), assembled by removable part."""
from collections import defaultdict
from math import cos, sin, tau

import bmesh
import bpy
from mathutils import Matrix, Vector


class Fixture:
    def __init__(self, spec, tier):
        self.spec = spec
        self.tier = tier
        self.level = ("Low", "Balanced", "Detailed").index(tier)
        self.parts = defaultdict(lambda: [[], [], [], []])
        self.group = "Structure"
        self.pose = None
        self.source_bounds = None
        self.segments = (8, 16, 28)[self.level]

    def solid(self, points, faces, swatch, pattern=0, bevel=0, smooth=False, projection=None):
        # Reorient each connected shell before deriving planar UVs. Authoring axes
        # flip handedness when the forward coordinate becomes Blender -Y.
        bm = bmesh.new()
        vs = [bm.verts.new((x, -d, z)) for x,d,z in points]
        for face in faces:
            bm.faces.new([vs[i] for i in face])
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        if bevel and self.level:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel,
                            segments=self.level, affect="EDGES", clamp_overlap=True)
        bm.normal_update()
        bm.verts.index_update()
        lo = [min(v.co[a] for v in bm.verts) for a in range(3)]
        hi = [max(v.co[a] for v in bm.verts) for a in range(3)]
        verts, polys, uvs, normals = self.parts[self.group]
        start = len(verts)
        mirrored = False
        if self.pose:
            origin = Vector(self.pose(0,0,0))
            basis = [Vector(self.pose(*axis))-origin for axis in ((1,0,0),(0,1,0),(0,0,1))]
            mirrored = Matrix(basis).determinant() < 0
        for v in bm.verts:
            x,y,z = v.co
            if self.pose:
                x,d,z = self.pose(x,-y,z)
                y = -d
            verts.append((x,y,z))
        for face in bm.faces:
            corners = list(face.verts)
            if mirrored:
                corners.reverse()
            polys.append([start+v.index for v in corners])
            axis = max(range(3),key=lambda a:abs(face.normal[a]))
            u,v = projection or ((1,2),(0,2),(0,1))[axis]
            # Two texels of gutter keep minified faces inside the intended cell.
            color = swatch(face.calc_center_median()) if callable(swatch) else swatch
            uv = []
            for point in corners:
                a,b = [(point.co[k]-lo[k])/max(1e-10,hi[k]-lo[k]) for k in (u,v)]
                uv.append(((color+.035+.93*a)/4,(pattern+.035+.93*b)/4))
            uvs.append(uv)
            normals.append(smooth and len(face.verts)==4)
        bm.free()

    def box(self, centre, size, swatch, pattern=0, bevel=0):
        x,d,z = centre
        w,t,h = (v/2 for v in size)
        self.solid([(x+i*w,d+j*t,z+k*h) for k in (-1,1) for i,j in
                    ((-1,-1),(1,-1),(1,1),(-1,1))],
                   [(0,1,2,3),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],
                   swatch,pattern,bevel)

    def profile(self, outline, depth, thickness, swatch, pattern=0, bevel=0):
        """Extrude a front elevation outline in depth."""
        n = len(outline)
        points = [(x,d,z) for d in (depth-thickness/2,depth+thickness/2) for x,z in outline]
        faces = [tuple(range(n)),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        self.solid(points,faces,swatch,pattern,bevel)

    def tube(self, start, end, radius, swatch, sides=None, pattern=0):
        a,b = Vector(start),Vector(end)
        axis = (b-a).normalized()
        ref = Vector((0,0,1)) if abs(axis.z)<.9 else Vector((1,0,0))
        x = axis.cross(ref).normalized()*radius
        y = axis.cross(x)
        n = sides or self.segments
        pts = [p+x*cos(tau*i/n)+y*sin(tau*i/n) for p in (a,b) for i in range(n)]
        faces = [tuple(range(n)),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        self.solid(pts,faces,swatch,pattern,smooth=True)

    def rings(self, rings, swatch, pattern=0, smooth=False, loop=False, projection=None):
        """Loft matching closed cross-sections, optionally returning to the first ring."""
        n = len(rings[0])
        faces = [] if loop else [tuple(range(n)),tuple(range(n*(len(rings)-1),n*len(rings)))]
        for k in range(len(rings) if loop else len(rings)-1):
            j = (k+1)%len(rings)
            faces.extend((k*n+i,k*n+(i+1)%n,j*n+(i+1)%n,j*n+i) for i in range(n))
        self.solid([v for ring in rings for v in ring],faces,swatch,pattern,smooth=smooth,projection=projection)

    def lathe(self, centre, profile, swatch, sides=None, pattern=0):
        x,d = centre
        n = sides or self.segments
        self.rings([[(x+r*cos(tau*i/n),d+s*sin(tau*i/n),z) for i in range(n)]
                    for r,s,z in profile],swatch,pattern,True)

    def finish(self, material):
        coords = [p for verts,_,_,_ in self.parts.values() for p in verts]
        low = list(map(min,zip(*coords)))
        high = list(map(max,zip(*coords)))
        if self.source_bounds:
            low, high = self.source_bounds
        w,h,d = self.spec["anchor"]["envelope_whd_m"]
        # Import/author in local coordinates. The programme positions a bottom-
        # centred pivot, including overhead pieces, in its pre-yaw envelope.
        middle = [(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]]
        scale = [extent/(hi-lo) for extent,lo,hi in zip((w,d,h),low,high)]
        if self.spec["slot"] in {"S03","S07","S08","S13","S15"}:
            scale = [min(scale)]*3
        elif self.spec["slot"] == "S14":
            scale[0] = scale[2] = min(scale[0],scale[2])
        root = bpy.data.objects.new("ASSET_"+self.spec["slug"].replace("-","_"),None)
        bpy.context.scene.collection.objects.link(root)
        for group,(verts,faces,uvs,smooth) in self.parts.items():
            mesh = bpy.data.meshes.new(group)
            mesh.from_pydata([tuple((p[k]-middle[k])*scale[k] for k in range(3)) for p in verts],[],faces)
            mesh.materials.append(material)
            mesh.update()
            uv = mesh.uv_layers.new(name="Swatches")
            for face,coords,shade in zip(mesh.polygons,uvs,smooth):
                face.use_smooth = shade
                for index,coord in zip(face.loop_indices,coords):
                    uv.data[index].uv = coord
            if self.spec["slot"] == "S16":
                # Multiply the white swatch by a linear tint to reproduce the
                # programme lime on the lanyard without another material/pass.
                colors = mesh.color_attributes.new(name="Parts tint",type="FLOAT_COLOR",domain="POINT")
                def linear(b):
                    s = b/255
                    return s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
                palette = self.spec["palette"]
                base, lime = [bytes.fromhex(palette[i]["hex"][1:]) for i in (0,2)]
                tint = tuple(linear(a)/linear(b) for a,b in zip(lime,base))+(1,)
                for value in colors.data:
                    value.color = tint if group=="Lime lanyard" else (1,1,1,1)
            obj = bpy.data.objects.new(group,mesh)
            bpy.context.scene.collection.objects.link(obj)
            obj.parent = root
        return root
