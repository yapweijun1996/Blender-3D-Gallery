"""Cut the male body surface and give each garment its own silhouette."""
import numpy as np
from mathutils.geometry import barycentric_transform
from fitting_geometry import laplacian, limit_weights, tree, weld_graph


PALETTES = {
    'top-hoodie': ((.035,.24,.21), (.016,.104,.086), (.105,.40,.29)),
    'top-jacket': ((.24,.078,.033), (.088,.027,.014), (.51,.23,.075)),
    'bottom-shorts': ((.035,.087,.17), (.015,.039,.081), (.10,.20,.30)),
    'bottom-skirt': ((.17,.052,.15), (.072,.025,.066), (.28,.075,.21)),
    'shoes-boots': ((.095,.044,.024), (.026,.020,.017), (.23,.104,.044)),
}


def unit(vector):
    return vector / np.maximum(np.linalg.norm(vector, axis=1, keepdims=True), 1.e-10)


def cut(points, faces, skin, mask):
    """Clip the triangulated body against an interpolated vertex mask."""
    vertices, indices, weights, cache = [], [], [], {}
    for face in faces:
        if mask[face].max() < 0:
            continue
        polygon = []
        for a, b in zip(face, np.roll(face, -1)):
            edges = []
            if mask[a] >= 0:
                edges.append((a, a))
            if (mask[a] >= 0) != (mask[b] >= 0):
                edges.append(tuple(sorted((a, b))))
            for key in edges:
                if key not in cache:
                    i, j = key
                    t = 0. if i == j else mask[i] / (mask[i] - mask[j])
                    cache[key] = len(vertices)
                    vertices.append(points[i] + t * (points[j] - points[i]))
                    weights.append(skin[i] + t * (skin[j] - skin[i]))
                polygon.append(cache[key])
        indices.extend((polygon[0], polygon[i], polygon[i+1]) for i in range(1, len(polygon)-1))
    p, first, inverse = np.unique(np.round(vertices, 7), axis=0, return_index=True, return_inverse=True)
    f = inverse[np.array(indices)]
    keep = np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]], p[f[:,2]]-p[f[:,0]]),axis=1) > 1.e-10
    f = f[keep]
    used, remap = np.unique(f,return_inverse=True)
    return p[used], remap.reshape(-1,3), np.array(weights)[first[used]]


def normals(p, f):
    n = np.zeros_like(p)
    vectors = np.cross(p[f[:,1]]-p[f[:,0]], p[f[:,2]]-p[f[:,0]])
    for i in range(3):
        np.add.at(n, f[:,i], vectors)
    return unit(n)


def skirt_surface(points, faces, skin, names, style):
    """Sweep loft rings from the fused outer thigh/hip cross-sections."""
    body = tree(points, faces.tolist())
    center = np.array([.0019, -.0248])
    directions = np.array([(np.cos(t), np.sin(t), 0.) for t in np.arange(64)*2*np.pi/64])
    levels = np.linspace((.410,.391,.387)[style-1], .302 if style==3 else .285, 15)
    hips = names.index('mixamorig:Hips')
    back = np.maximum(directions[:,1],0)
    front = np.maximum(-directions[:,1],0)
    radii, weights, origins = [], [], []
    for z in levels:
        origin = np.r_[center, z]
        origins.append(origin)
        ring, row = [], []
        for heading in directions:
            hit, _, face, _ = body.ray_cast(origin + .40*heading, -heading, .40)
            if hit is None:
                hit, _, face, _ = body.find_nearest(origin + .04*heading)
            ring.append(max(.02, np.dot(np.array(hit)-origin, heading)))
            a,b,c = points[faces[face]]
            ratio = barycentric_transform(hit, a,b,c, (1,0,0), (0,1,0), (0,0,1))
            row.append(np.maximum(0,ratio) @ skin[faces[face]])
        radii.append(ring)
        weights.append(row)
    radii = np.asarray(radii)
    for _ in range(5):
        radii = .50*radii + .25*(np.roll(radii,1,axis=1)+np.roll(radii,-1,axis=1))
    flare = ((levels[0]-levels)/(levels[0]-levels[-1]))[:,None]
    fitted = np.maximum.accumulate(radii,axis=0)
    profile = (.010+.092*front+.032*back) if style==3 else (.040+.080*front+.022*back)
    radii = fitted + .003 + flare * profile
    p = (np.array(origins)[:,None,:] + radii[:,:,None]*directions[None,:,:]).reshape(-1,3)
    w = np.asarray(weights)
    # The shared skirt surface follows the waist. Carrying both opposing leg
    # rotations at the hem would collapse its opening in a stride.
    retention = (np.maximum(0,1-flare*5)*.30)[:,:,None]
    w *= retention
    w[:,:,hips] += (1-retention)[:,:,0]
    f = []
    for r in range(len(levels)-1):
        for k in range(len(directions)):
            a = r*64+k
            b = r*64+(k+1)%64
            f.extend(((a,a+64,b),(b,a+64,b+64)))
    f = np.array(f)
    mat = np.where(p[f,2].mean(axis=1)>levels[0]-.014,1,0)
    w = w.reshape(-1,skin.shape[1])
    w = limit_weights(.985*w + .015*laplacian(w,weld_graph(p,f)))
    return p,f,w,np.tile(directions,(len(levels),1)),mat


def underarm_ease(points, style):
    """Lower the shape under the sleeve root and taper into the side panel."""
    x,y,z = points.T
    distance = ((abs(x)-.103)/.024)**2 + ((z-.503)/.025)**2 + ((y+.018)/.064)**2
    ease = np.exp(-distance)
    points[:,2] -= ease*(.009 if style==2 else .015)
    points[:,0] += np.sign(x)*ease*.005



def build(item, points, faces, skin, names, style=1):
    if item == 'bottom-skirt':
        return skirt_surface(points, faces, skin, names, style)
    x,y,z = points.T
    span = np.abs(x)
    if item.startswith('top'):
        hem = .430 if item == 'top-hoodie' else .425
        cuff = (.265 if style==1 else .219) if item == 'top-hoodie' else (.226,.212,.195)[style-1]
        if style > 1:
            hem += .006
        neckline = .578 - .022*np.clip((-y-.034)/.068,0,1)
        collar = neckline-z
        if item == 'top-hoodie':
            hood = np.minimum(z-.556, y+np.interp(z,[.556,.626,.74,.89,.98],
                                                 [-.001,.024,.076,.111,.12]))
            collar = np.maximum(collar, hood)
        mask = np.minimum.reduce((z-hem, cuff-span, collar))
        if item == 'top-jacket':
            opening = np.maximum(span-(.025+.012*np.clip((z-.50)/.09,0,1)), y+.057)
            mask = np.minimum(mask,opening)
    elif item == 'bottom-shorts':
        waist = (.410,.394,.383)[style-1]
        hem = .265+.007*(style-1)
        if style==3:
            # A curved inseam clears the high-contact inner thigh while
            # keeping the outer leg at mid-thigh length.
            hem += .041*np.clip((.053-span)/.046,0,1)**1.3
        mask = np.minimum(waist-z, z-hem)
    else:
        mask = (.112-.007*(style-1))-z
    p,f,w = cut(points,faces,skin,mask)
    graph = weld_graph(p,f)
    n = normals(p,f)
    n = unit(.60*n+.40*laplacian(n,graph))
    if item.startswith('top') and (style>1 or item=='top-jacket'):
        # Forearms have a nearly horizontal principal axis. The body normal
        # can tilt along that axis at a cut edge or in the elbow crease.
        span = abs(p[:,0])
        radial = unit(np.column_stack((np.zeros(len(p)),p[:,1]+.021,p[:,2]-.545)))
        blend = np.clip((span-.095)/.056,0,1) * (p[:,2]<.601)
        n = unit(n*(1-blend[:,None])+radial*blend[:,None])
    cx,cy,cz = p[f].mean(axis=1).T
    if item.startswith('top'):
        rest = .0055 if item=='top-jacket' else .008
        extra = np.full(len(p),rest)
        if style>1 or item=='top-jacket':
            extra += .005*np.clip((abs(p[:,0])-.090)/.067,0,1)*(p[:,2]<.601)
        if item == 'top-hoodie':
            extra += .009*np.clip((p[:,2]-.594)/.085,0,1)
            pocket = ((cz>.455)&(cz<.492)&(np.abs(cx)<.063)&(cy<-.065))
            trim = (np.abs(cx)>cuff-.014)|(cz<hem+.011)|((cz>.62)&(cy<-.062))
            mat = np.where(trim,1,np.where(pocket,2,0))
        else:
            trim = (np.abs(cx)>cuff-.013)|(cz<hem+.008)
            placket = (np.abs(cx)<.038)&(cy<-.055)
            mat = np.where(trim,1,np.where(placket,2,0))
    elif item == 'bottom-shorts':
        extra = .003 + .0015*np.clip((.32-p[:,2])/.05,0,1)
        if style==3:
            medial = np.clip((.047-abs(p[:,0]))/.042,0,1)
            front = np.clip((-.045-p[:,1])/.042,0,1)
            thigh = np.clip((.355-p[:,2])/.047,0,1)
            extra += .007*front*thigh*(1-medial)
        mat = np.where((cz>waist-.010)|(cz<.276+.007*(style-1)),1,0)
    else:
        # A wider toe box and a level sole cover the body-derived instep and toes.
        extra = .0035 + .003*np.clip((-.083-p[:,1])/.065,0,1)
        sole = np.clip((.015-p[:,2])/.018,0,1)
        extra += .003*sole
        mat = np.where(cz<.013,1,np.where(cz>.089-.007*(style-1),2,0))
    p += n*extra[:,None]
    if item=='shoes-boots':
        p[:,2] = np.minimum(p[:,2], np.where(sole>.75, -.008, np.inf))
    return p, f, limit_weights(.985*w+.015*laplacian(w,graph)), n, mat
