"""Tailor a crotch bridge and two flared legs from the male body surface."""
import numpy as np

from fitting_geometry import laplacian, weld_graph
from garments import cut, normals, unit
from tailoring import CENTER, Panels, largest


def build_shorts(points, faces, skin, names, style):
    x,y,z = points.T
    span = abs(x-CENTER)
    # The side seam reaches mid-thigh. The inseam rises through the area
    # where the two thigh sweeps approach during the seated clips.
    inside = np.clip((.059-span)/.052,0,1)
    hem = (.274,.275,.280)[style-1] + (.034,.043,.046)[style-1]*inside**1.6
    if style>1:
        front = np.clip((-.065-y)/.045,0,1)
        inner_front = np.exp(-((span-.044)/.040)**2)
        hem += (.016 if style==2 else .020)*front*inner_front
    waist = (.383,.379,.376)[style-1] - .004*np.exp(-((y+.107)/.028)**2)
    p,f,payload = largest(*cut(points,faces,np.column_stack((skin,z-hem,waist-z)),
                               np.minimum(z-hem,waist-z)))
    w = payload[:,:-2]
    lower,upper = payload[:,-2:].T
    graph = weld_graph(p,f)
    n = unit(.48*normals(p,f)+.52*laplacian(normals(p,f),graph))
    x,y,z = p.T
    span = abs(x-CENTER)
    medial = np.clip((.062-span)/.052,0,1)*np.clip((.332-z)/.023,0,1)
    outer_flare = np.clip((span-.055)/.059,0,1) * np.exp(-(lower/.024)**2)
    cuff_lip = .0013*np.exp(-((lower-.0045)/.0038)**2)*(1-medial)
    waistband_lip = .0011*np.exp(-((upper-.003)/.0038)**2)
    ease = .0037-.0012*medial + (.008+.001*(style-1))*outer_flare + cuff_lip + waistband_lip
    if style>1:
        y_front = np.clip((-.065-y)/.045,0,1)
        ease += (.006 if style==2 else .008)*y_front*np.exp(-((z-.307)/.026)**2)
        # Below the seat, the hem follows the same thigh that it surrounds.
        # A tapered transition leaves the central crotch bridge flexible.
        cuff = .34*np.clip((.329-z)/.052,0,1)*np.clip((span-.020)/.035,0,1)
        w *= 1-cuff[:,None]
        increased = np.where(x>CENTER,names.index('mixamorig:LeftUpLeg'),
                              names.index('mixamorig:RightUpLeg'))
        w[np.arange(len(w)),increased] += cuff
    p += n*ease[:,None]
    panels = Panels()
    band = np.minimum(lower-.011,upper-.010)
    panels.add(*cut(p,f,w,band),0)
    panels.add(*cut(p,f,w,-band),1)
    return panels.result()
