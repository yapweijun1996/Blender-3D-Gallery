"""Compute the radial sweep of the male legs in the pelvis bind frame."""
import numpy as np


def edges(faces):
    return np.unique(np.sort(np.vstack((faces[:,[0,1]],faces[:,[1,2]],
                                        faces[:,[2,0]])),axis=1),axis=0)


class SkirtEnvelope:
    def __init__(self, points, body_faces, body_points, arm):
        self.rings = points.reshape(-1,64,3)
        self.center = np.array((.0019,-.0248))
        self.levels = self.rings[:,0,2]
        # Extra levels cover the span between authored rings.
        self.planes = np.linspace(self.levels[0],self.levels[-1],2*len(self.levels)-1)
        self.side = np.zeros((len(self.planes),self.rings.shape[1]))
        lower = body_faces[body_points[body_faces,2].max(axis=1)<.448]
        self.edges = edges(lower)
        self.hips = [bone.name for bone in arm.pose.bones].index('mixamorig:Hips')

    def sample(self, body_points, matrices, seam_points=None, seam_edges=None):
        inverse = np.linalg.inv(matrices[self.hips])
        self.section(body_points, self.edges, inverse)
        if seam_points is not None:
            self.section(seam_points, seam_edges, inverse)

    def section(self, points, edge_list, inverse):
        p = points @ inverse[:3,:3].T + inverse[:3,3]
        a,b = p[edge_list[:,0]],p[edge_list[:,1]]
        lo = np.minimum(a[:,2],b[:,2])
        hi = np.maximum(a[:,2],b[:,2])
        # Use all body edge intersections with every horizontal sample plane.
        level, edge = np.nonzero((self.planes[:,None]>=lo)&(self.planes[:,None]<hi))
        t = (self.planes[level]-a[edge,2])/(b[edge,2]-a[edge,2])
        xy = a[edge,:2]+t[:,None]*(b[edge,:2]-a[edge,:2])-self.center
        theta = np.arctan2(xy[:,1],xy[:,0])*(64/(2*np.pi))
        # Both neighboring vertices must cover the crossing or a triangle
        # between angular samples can cut a curved boundary.
        left = np.floor(theta).astype(int)
        radius = np.linalg.norm(xy,axis=1)
        np.maximum.at(self.side,(level,left%64),radius)
        np.maximum.at(self.side,(level,(left+1)%64),radius)

    def clamp(self, points, slim):
        at_vertices = self.side[::2].copy()
        np.maximum(at_vertices[1:],self.side[1::2],out=at_vertices[1:])
        np.maximum(at_vertices[:-1],self.side[1::2],out=at_vertices[:-1])
        needed = (at_vertices if slim else np.maximum.accumulate(at_vertices,axis=0))+.004
        # Raise low neighbors while keeping the maximum sweep in each sector.
        for _ in range(6):
            diffused = .5*needed+.25*(np.roll(needed,1,axis=1)+np.roll(needed,-1,axis=1))
            needed = np.maximum(needed,diffused)
        fit = points.reshape(self.rings.shape)
        radial = fit[:,:,:2]-self.center
        radii = np.linalg.norm(radial,axis=2)
        fit[:,:,:2] += radial * np.maximum(0,(needed-radii)/radii)[:,:,None]
        return fit.reshape(-1,3)
