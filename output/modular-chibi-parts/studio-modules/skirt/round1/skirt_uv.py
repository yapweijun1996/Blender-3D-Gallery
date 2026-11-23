"""Project the Studio material charts back onto the fitted panel and belt."""
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from fit_skirt import coords
from skirt_surface import SIDES, barycentric


class StudioCharts:
    def __init__(self, obj):
        mesh = obj.data
        mesh.calc_loop_triangles()
        self.points = coords(obj)
        self.faces = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
        self.uv = np.array([[mesh.uv_layers.active.data[i].uv[:] for i in t.loops]
                            for t in mesh.loop_triangles], dtype=np.float32)
        # glTF splits at UV and normal seams. Reconnect chart faces only where
        # both the spatial edge and the corner UVs match.
        parent = np.arange(len(self.faces), dtype=np.int32)

        def root(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        edge_table = {}
        spatial = np.round(self.points*1e6).astype(np.int32)
        texture = np.round(self.uv*1e6).astype(np.int32)
        for index, (tri, uv) in enumerate(zip(self.faces, texture)):
            keys = [tuple(spatial[v])+tuple(q) for v,q in zip(tri,uv)]
            for a,b in zip(keys, keys[1:]+keys[:1]):
                edge = tuple(sorted((a,b)))
                if edge in edge_table:
                    parent[root(index)] = root(edge_table[edge])
                else:
                    edge_table[edge] = index
        self.labels = np.array([root(i) for i in range(len(self.faces))])
        self.full = BVHTree.FromPolygons(self.points.tolist(), self.faces.tolist(), all_triangles=True)
        self.by_chart = {}
        for chart_id in np.unique(self.labels):
            self.by_chart[int(chart_id)] = np.flatnonzero(self.labels == chart_id)
        self.chart_trees = {}
        self.positions = self.points[self.faces]

    def chart_tree(self, label):
        if label not in self.chart_trees:
            indices = self.by_chart[label]
            polys = self.faces[indices]
            vertices, mapping = np.unique(polys, return_inverse=True)
            tree = BVHTree.FromPolygons(self.points[vertices].tolist(), mapping.reshape(polys.shape).tolist(),
                                        all_triangles=True)
            self.chart_trees[label] = indices, tree
        return self.chart_trees[label]

    def target(self, theta, depth, belt):
        direction = np.array((math.sin(theta),-math.cos(theta),0), dtype=np.float32)
        cos, sin = math.cos(theta), math.sin(theta)
        if belt:
            z = .4325-.017*depth
            cy = -.033
            width, length = .089, .078
        else:
            lower = .278 + .024*sin**2 + .017*max(-cos,0)
            z = .417 + depth*(lower-.417)
            cy = -.029 + .011*depth
            width, length = .092+.057*depth, .079+.043*depth
        expected = ((sin/width)**2+(cos/length)**2)**(-.5)
        center = np.array((.0008,cy,z), dtype=np.float32)
        guess = center + expected*direction
        # Small ray offsets bridge cuts in the segmented source. Prefer the
        # exterior near the expected size and avoid opposite-side hits.
        candidates = []
        for delta in (0,.0008,-.0008,.0017,-.0017,.003,-.003):
            origin = center + direction*.28 + (0,0,delta)
            hit, _, index, _ = self.full.ray_cast(Vector(origin),Vector(-direction),.24)
            if hit:
                cost = abs((np.asarray(hit)-center) @ direction - expected)+2*abs(delta)
                candidates.append((cost, np.asarray(hit,dtype=np.float32), index))
        if candidates:
            cost, point, index = min(candidates,key=lambda x:x[0])
            if cost <= (.025 if belt else .043):
                return point, index
        point, _, index, _ = self.full.find_nearest(guess)
        return np.asarray(point,dtype=np.float32), index

    def uvs_for_face(self, positions, indices):
        labels = set(self.labels[np.asarray(indices)])
        better = None
        for label in labels:
            ids, tree = self.chart_tree(int(label))
            hits = [tree.find_nearest(pos) for pos in positions]
            metric = max(hit[3] for hit in hits) + .35*sum(hit[3] for hit in hits)
            if better is None or metric < better[0]:
                better = metric, np.array([hit[0] for hit in hits],dtype=np.float32), np.array(
                    [ids[hit[2]] for hit in hits],dtype=np.int32)
        distance, xyz, tris = better
        uv = np.einsum("ij,ijk->ik", barycentric(xyz,self.positions[tris]), self.uv[tris])
        return uv, distance


def assign_uv(garment, sources, triangles, depth, theta):
    fabric, belt = (StudioCharts(src) for src in sources)
    fabric_depth = (depth-.10)/.90
    lifted = np.concatenate((fabric_depth, fabric_depth[::-1]))
    strap = np.clip(depth/.115, 0, 1)
    wrapped = np.concatenate((strap, strap[::-1]))
    targets = []
    for chart, d, brass in ((fabric, lifted, False), (belt, wrapped, True)):
        targets.append([chart.target(a, float(np.clip(t,0,1)), brass) for t in d for a in theta])
    primary = garment.data.uv_layers.new(name="Studio UV")
    layer = garment.data.uv_layers.new(name="Studio Source Projection")
    distances = [[],[]]
    for poly, tri in zip(garment.data.polygons, triangles, strict=True):
        row = (poly.index//2)//SIDES
        if row >= 2*len(depth):
            poly.material_index = 1
            ring_count = 2*len(depth)
            quad_id = poly.index//2 - ring_count*SIDES
            section,edge = divmod(quad_id,8)
            for loop,vertex in zip(poly.loop_indices,tri,strict=True):
                if section in (1,3):
                    shell, corner = divmod(int(vertex)-ring_count*SIDES,8)
                    uv = (.30+.011*(edge+int(corner!=edge)), .204+.013*int(shell in (0,1)))
                else:
                    point = garment.data.vertices[vertex].co
                    uv = (.36+point.x*4.3, .23+(point.z-.417)*5.5)
                primary.data[loop].uv = uv
                layer.data[loop].uv = uv
            continue
        count = len(depth)
        other = (row+1)%(2*count)
        mirrored = [r if r < count else 2*count-r-1 for r in (row,other)]
        mat = int(max(mirrored) <= 3)
        poly.material_index = mat
        points, indices = zip(*(targets[mat][index] for index in tri), strict=True)
        chart = belt if mat else fabric
        values, distance = chart.uvs_for_face(np.array(points),indices)
        for loop,uv,vertex in zip(poly.loop_indices,values,tri,strict=True):
            layer.data[loop].uv = uv
            r,a = divmod(int(vertex),SIDES)
            angle = theta[a]
            reverse = r >= count
            level = depth[2*count-r-1 if reverse else r]
            # The original Tripo atlas contains dark baked folds and chart
            # gaps. Sample continuous interior strips so new panels keep
            # their colour while the remodeled geometry defines the folds.
            if mat == 0:
                uv_clean = (.409+.009*math.cos(5*angle+.665),
                            .912-.055*level-(.004 if reverse else 0))
            else:
                uv_clean = (.365+.037*math.cos(angle+.4),
                            .227-.058*(level/.115)-(.009 if reverse else 0))
            primary.data[loop].uv = uv_clean
        distances[mat].append(distance)
    garment.data.uv_layers.active_index = 0
    primary.active_render = True
    return {"source_uv_chart_counts": [len(fabric.by_chart),len(belt.by_chart)],
            "max_uv_chart_projection_distance_m": [max(values) for values in distances],
            "uv_chart_projection_distance_p95_m": [float(np.quantile(values,.95)) for values in distances]}
