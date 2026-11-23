"""Author the garment silhouettes in the bind frame of the male body."""
import numpy as np
from mathutils.geometry import barycentric_transform

from fitting_geometry import limit_weights, tree
from garments import cut, normals, unit

CENTER = .00191


class Panels:
    def __init__(self):
        self.points, self.faces, self.skin, self.materials = [], [], [], []

    def add(self, points, faces, skin, material):
        self.faces.extend(np.asarray(faces) + len(self.points))
        self.points.extend(points)
        self.skin.extend(skin)
        self.materials.extend(np.broadcast_to(material, (len(faces),)))

    def result(self):
        p, f = np.array(self.points), np.array(self.faces)
        w = limit_weights(np.array(self.skin))
        _, keep, inverse = np.unique(np.round(np.column_stack((p,w)),6),axis=0,
                                      return_index=True,return_inverse=True)
        p, f, w = p[keep],inverse.reshape(-1)[f],w[keep]
        return p, f, w, normals(p, f), np.array(self.materials)


def grid(rows, columns, wrap=False, reverse=False):
    r, c = np.indices((rows-1, columns if wrap else columns-1))
    a = (r*columns+c).ravel()
    b = (r*columns+(c+1)%columns).ravel()
    faces = np.vstack((np.column_stack((a,b,a+columns)),
                       np.column_stack((b,b+columns,a+columns))))
    return faces[:,::-1] if reverse else faces


def largest(p, f, w):
    adjacent = [[] for _ in p]
    for i,j,k in f:
        adjacent[i].extend((j,k))
        adjacent[j].extend((i,k))
        adjacent[k].extend((i,j))
    unseen = set(range(len(p)))
    clusters = []
    while unseen:
        seed = unseen.pop()
        island = [seed]
        pending = [seed]
        while pending:
            for index in adjacent[pending.pop()]:
                if index in unseen:
                    unseen.remove(index)
                    island.append(index)
                    pending.append(index)
        clusters.append(island)
    selected = sorted(max(clusters,key=len))
    remap = np.full(len(p),-1)
    remap[selected] = np.arange(len(selected))
    selected_faces = remap[f]
    return p[selected],selected_faces[(selected_faces>=0).all(axis=1)],w[selected]


def pin(names, profile, count):
    weights = np.zeros((count,len(names)))
    for bone,value in profile.items():
        weights[:,names.index('mixamorig:'+bone)] = value
    return weights


def front_sampler(points, faces, skin):
    surface = tree(points,faces.tolist())
    def sample(x,z):
        hit, _, index, _ = surface.ray_cast((x,-.4,z),(0,1,0),.5)
        if hit is None:
            raise ValueError((x,z))
        u = barycentric_transform(hit,*points[faces[index]],(1,0,0),(0,1,0),(0,0,1))
        return hit.y, np.maximum(0,u) @ skin[faces[index]]
    return sample


def hoodie_details(out, sample, names, style):
    # The hood is folded down. Its inner and outer surfaces follow one curved
    # cross section, with the folded crown behind the neck and tapered ends.
    angle = np.linspace(-1.08,1.08,45) if style>1 else np.linspace(-1.19,1.19,45)
    phase = np.linspace(0,2*np.pi,20,endpoint=False)
    arc = np.cos(angle)
    taper = np.clip(np.sqrt(np.maximum(0.,(1-(angle/1.083)**2)))*1.45,.10,1)
    if style==1:
        taper[:] = 1
    x = CENTER + np.sin(angle)*(.085 + taper*.012*np.cos(phase[:,None]))
    yc = (.037 + .039*arc) if style>1 else -.032+.103*arc
    y = yc + taper*(.010+(.042 if style==1 else .036)*arc)*np.cos(phase[:,None])
    z = .552 + .009*arc + taper*(.012+.029*arc)*np.sin(phase[:,None])
    z -= .017*(1-arc)
    rolled = np.stack((x,y,z),axis=-1).transpose(1,0,2)
    f = grid(len(angle),len(phase),True,True)
    last = (len(angle)-1)*len(phase)
    tips = np.array([(0,k+1,k) for k in range(1,len(phase)-1)]
                    + [(last,last+k,last+k+1) for k in range(1,len(phase)-1)])
    out.add(rolled.reshape(-1,3),np.vstack((f,tips)),
            pin(names,{'Spine2':.88,'Neck':.12},rolled.size//3),0)

    # Sample the already tailored front to keep the raised pocket and its
    # sweeping hand openings flush to the curved garment.
    points, skin = [], []
    for t in np.linspace(0,1,9):
        width = .056 - .019*t + .008*np.sin(np.pi*t)
        for s in np.linspace(-1,1,19):
            x = CENTER + s*width
            z = .431 + .050*t + .004*s*s
            y,w = sample(x,z)
            dome = np.sin(np.pi*t)**.75 * (1-.65*abs(s)**3)
            points.append((x,y-.0009-.010*dome,z))
            skin.append(w)
    out.add(points,grid(9,19,False,False),skin,0)

    for side in (-1,1):
        cord,skin = [],[]
        for t in np.linspace(0,1,13):
            x = CENTER+side*(.039+.011*np.sin(t*np.pi)+.008*t)
            z = .554-.057*t
            y,w = sample(x,z)
            y -= .005+.005*(1-t)
            for a in np.linspace(0,2*np.pi,8,endpoint=False):
                radius = .0022+.0009*(t>.86)
                cord.append((x+radius*np.cos(a),y+radius*np.sin(a),z))
                skin.append(w)
        out.add(cord,grid(13,8,True,True),skin,1)


def sleeve_ends(out, p, f, w, names, cut_span, hoodie, style):
    edges, counts = np.unique(np.sort(np.vstack((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1),
                              axis=0,return_counts=True)
    edges = edges[counts==1]
    for side,bone in ((1,'LeftForeArm'),(-1,'RightForeArm')):
        on_cuff = (side*(p[:,0]-CENTER)>cut_span-.004)
        ring_ids = np.unique(edges[on_cuff[edges].all(axis=1)])
        seam = p[ring_ids]
        z0,y0 = .544,-.023
        angle = np.arctan2(seam[:,2]-z0,seam[:,1]-y0)
        sort = np.argsort(angle)
        angle = angle[sort]
        seam, seam_w = seam[sort],w[ring_ids[sort]]
        # The cut body supplies the transition loop. The cuff itself follows
        # the forearm and keeps a circular opening clear of the palm.
        if not hoodie and style>1:
            profiles = ((cut_span+.006,.045,.042),(.256,.044,.040),(.260,.043,.039),
                        (.274,.043,.039),(.276,.042,.038))
        else:
            profiles = ((cut_span+.008,.047,.044),(.262,.045,.042),(.265,.044,.041),
                        (.279,.044,.040),(.282,.043,.039))
        rings = [seam]
        sw = [seam_w]
        for i,(span,ry,rz) in enumerate(profiles):
            rings.append(np.column_stack((np.full(len(angle),CENTER+side*span),
                                          y0+(ry + (.0009*np.cos(24*angle) if not hoodie and i>=2 else 0))*np.cos(angle),
                                          z0+(rz + (.0009*np.cos(24*angle) if not hoodie and i>=2 else 0))*np.sin(angle))))
            rigid = pin(names,{bone:1.},len(angle))
            blend = (.55,.82,1.,1.,1.)[i]
            sw.append((1-blend)*seam_w+blend*rigid)
        f = grid(len(rings),len(angle),True,side<0)
        band = np.where((f//len(angle)).min(axis=1)>=2,1,0)
        out.add(np.concatenate(rings),f,np.concatenate(sw),band)


def bomber_collar(out, names, style):
    angles = np.linspace(-1.70,1.70,45) if style>1 else np.linspace(-1.86,1.86,45)
    back = np.maximum(0,np.cos(angles))
    rings = []
    for xradius,yradius,z in ((.090,.056,.560),(.080,.050,.577),
                              (.074,.046,.591),(.069,.040,.593),
                              (.066,.037,.586)):
        x = CENTER+xradius*np.sin(angles)
        y = -.012+yradius*np.cos(angles)
        height = z-(.025 if style>1 else .018)*(1-back)
        rings.append(np.column_stack((x,y,height)))
    p = np.concatenate(rings)
    out.add(p,grid(len(rings),len(angles),False,True),
            pin(names,{'Spine2':.90,'Neck':.10},len(p)),1)


def top(item, points, faces, skin, names, style):
    hoodie = item=='top-hoodie'
    # Split the original shell using the waist, wrist and a low collar.
    # Every side panel remains attached to its sleeve across the underarm.
    hem = (.410,.403,.406)[style-1] if hoodie else (.414,.409,.414)[style-1]
    use_cuffs = style>1 or not hoodie
    cuff = .247 if use_cuffs else .308
    x,y,z = points.T
    neck = .582 - .017*np.clip((-y-.032)/.073,0,1)
    mask = np.minimum.reduce((z-hem,cuff-abs(x-CENTER),neck-z))
    if not hoodie:
        opening = np.maximum(abs(x-CENTER)-(.033+.011*np.clip((z-.490)/.095,0,1)),y+.054)
        mask = np.minimum(mask,opening)
    p,f,w = largest(*cut(points,faces,skin,mask))
    x,y,z = p.T
    near_zip = np.minimum(.012-abs(abs(x-CENTER)-(.033+.011*np.clip((z-.490)/.095,0,1))),
                          -.057-y)
    span = abs(x-CENTER)
    sleeve = np.clip((span-.096)/.065,0,1)
    radial_sleeve = unit(np.column_stack((np.zeros(len(p)),y+.021,z-.548)))
    radial_torso = unit(np.column_stack((x-CENTER,y+.038,np.zeros(len(p)))))
    heading = unit(radial_sleeve*sleeve[:,None]+radial_torso*(1-sleeve[:,None]))
    outward = normals(p,f)
    heading = unit(.88*heading+.12*outward)
    ease = (.015-.006*sleeve if use_cuffs else .016+.007*sleeve) + .005*np.exp(-((z-.454)/.031)**2)*(1-sleeve)
    ease += (.002 if style>1 else 0) + (0 if hoodie else .012*(1-sleeve))
    if style>1 or not hoodie:
        ease += .009*np.exp(-((z-hem)/.017)**2)*(1-sleeve)
    # Use a clean rib band silhouette at the two ends of the garment.
    width = .017
    edge = z-hem if use_cuffs else np.minimum(z-hem,cuff-span)
    ease += .0023*np.exp(-((edge-.006)/.005)**2)
    if not hoodie and style>1:
        theta = np.arctan2(y+.038,x-CENTER)
        ribbing = np.sin(np.pi*np.clip(edge/width,0,1))*np.cos(30*theta)
        ease += .00115*ribbing
    underarm = np.exp(-((span-.117)/.033)**2-((z-.503)/.025)**2)
    if not hoodie:
        # Expand the shoulder outward from the original body normals, where
        # a purely horizontal torso offset would move into the sleeve root.
        ease -= .011*underarm
        shoulder = np.exp(-((span-.111)/.061)**2-((z-.552)/.044)**2)
        follow = (.48*underarm if style==1 else np.maximum(.64*underarm,.80*shoulder))[:,None]
        heading = unit(heading*(1-follow)+outward*follow)
        if style>1:
            ease += .005*shoulder*(1-underarm)
    p += heading*ease[:,None]
    p[:,2] -= (.009 if hoodie else .0035)*underarm
    # Continuous bands share their cut vertices with the adjacent main panel.
    trim_start = edge-width
    out = Panels()
    if hoodie:
        out.add(*cut(p,f,w,trim_start),0)
    else:
        core, core_faces, payload = cut(p,f,np.column_stack((w,near_zip)),trim_start)
        out.add(*cut(core,core_faces,payload[:,:-1],-payload[:,-1]),0)
        out.add(*cut(core,core_faces,payload[:,:-1],payload[:,-1]),2)
    out.add(*cut(p,f,w,-trim_start),1)
    if use_cuffs:
        sleeve_ends(out,p,f,w,names,cuff,hoodie,style)
    if hoodie:
        hoodie_details(out,front_sampler(p,f,w),names,style)
    else:
        bomber_collar(out,names,style)
    return out.result()
