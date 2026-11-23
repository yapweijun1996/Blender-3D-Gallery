"""Fit a fixed right-hand attachment, allowing progressively larger adjustments."""
import argparse
from parcel import *


def exp_rotation(v):
    angle = np.linalg.norm(v)
    return np.asarray(Quaternion(v, angle).to_matrix()) if angle else np.eye(3)


def quat_values(q):
    return [q.x, q.y, q.z, q.w]


class Fit:
    def __init__(self, joint_suffix, frames):
        self.r = r = ParcelReplay()
        self.orig = bpy_pose(original_socket())
        self.prop, _ = r.prop(CLIP)
        main = next(closed_components(self.prop.points, self.prop.faces))
        self.center = np.array([0., 0., 108.])
        xyz = self.prop.points[np.asarray(main)]*1000-self.center
        faces = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
        faces /= np.linalg.norm(faces,axis=1)[:,None]
        support = (xyz[:,0]*faces).sum(1)
        if np.median(support) < 0:
            faces, support = -faces, -support
        planes = np.unique(np.column_stack((faces,support)).round(5),axis=0)
        self.normal, self.offset = planes[:,:3].T, planes[:,3]
        suffixes = [joint_suffix] * 4 if len(joint_suffix)==1 else list(joint_suffix)
        self.names = [side+'Hand'+digit+suffix for (side,digit),suffix in zip(r.pads,suffixes)]
        self.times = np.linspace(0, r.end_time, frames)
        points, skeleton = [], []
        for t in self.times:
            p, hand = r.time(float(t))
            inv = (hand @ self.orig).inverted()
            points.append(transform(p,inv)*1000-self.center)
            skeleton.append([np.asarray(inv @ r.arm.matrix_world @ r.arm.pose.bones[N+name].matrix)
                             for name in self.names])
        raw = np.array(points)
        self.head = raw[:,r.labels=='Head',:]
        self.world = raw
        self.all_ids = np.arange(len(r.rest))
        pad_ids = [np.unique(f) for f in r.pads.values()]
        near = (np.abs(raw) < np.array([200,165,159])).all(-1).any(0)
        self.ids = np.union1d(np.flatnonzero(near),np.concatenate(pad_ids))
        self.points = raw[:,self.ids,:]
        self.pad_indices = [np.searchsorted(self.ids,ids) for ids in pad_ids]
        self.skeleton = np.array(skeleton)
        self.fingers = []
        for k,name in enumerate(self.names):
            all_ids, weights = self.affected(name)
            indices = np.searchsorted(self.ids,all_ids)
            match = (indices<len(self.ids)) & (self.ids[np.minimum(indices,len(self.ids)-1)]==all_ids)
            indices, weights = indices[match], weights[match]
            rest = np.column_stack([r.rest[self.ids[indices]],np.ones(len(indices))])
            local = np.empty((len(self.times),len(indices),3))
            # LBS contributions in the rotated joint frame, accounting for
            # each original descendant's skin weight and bind transform.
            for j,t in enumerate(self.times):
                r.time(float(t))
                base = r.arm.pose.bones[N+name]
                accum = np.zeros((len(indices),3))
                for add in [base,*base.children_recursive]:
                    w = r.weights.get(add.name.removeprefix(N))
                    if w is None:
                        continue
                    from_mesh = base.matrix.inverted() @ add.matrix @ add.bone.matrix_local.inverted()
                    accum += (rest @ np.asarray(from_mesh).T)[:,:3]*w[self.ids[indices],None]
                local[j] = accum*1000
            self.fingers.append((indices,local))
        self.wall = .3
        self.target = 1.24
        self.contact_weight = 6.
        self.skin_weight = 4.
        self.active = None
        self.flat = 0.
        self.phase = np.column_stack([np.sin(h*np.pi*self.times) for h in (1,2)] +
                                     [np.cos(h*np.pi*self.times)-1 for h in (1,2)])

    def affected(self, name):
        bone = self.r.arm.pose.bones[N+name]
        weights = sum(self.r.weights.get(b.name.removeprefix(N),0.) for b in [bone,*bone.children_recursive])
        ids = np.flatnonzero(weights > 0)
        return ids, weights[ids]

    def parts(self,x):
        return x[:3], exp_rotation(x[3:6]/100), np.exp(x[6:9]/100) if len(x)>=9 else np.ones(3)

    def predicted(self,x):
        points = self.points.copy()
        if len(x)>9:
            for k,(ids,base) in enumerate(self.fingers):
                v = x[9+3*k:12+3*k]/100
                if k>=2 and len(x)>21:
                    motion = x[21+(k-2)*12:21+(k-1)*12].reshape(4,3)/100
                    rot = np.array([exp_rotation(v + step) for step in self.phase @ motion])
                    effect = (rot-np.eye(3)).transpose(0,2,1)
                else:
                    effect = (exp_rotation(v)-np.eye(3)).T
                world = self.skeleton[:,k,:3,:3]
                points[:,ids,:] += (base @ effect) @ world.transpose(0,2,1)
        return points

    def signed(self, points, tr, rot, scale):
        u = (points-tr) @ rot
        normals = self.normal / scale[:,None]
        # Maximum signed plane distance is exact inward depth in a convex solid.
        d = ((u @ normals-self.offset)/np.linalg.norm(normals,axis=0)).max(-1)
        return d

    def residual(self,x,full=False):
        tr,rot,scale = self.parts(x)
        p = self.predicted(x)
        if full or self.active is None:
            d = self.signed(p,tr,rot,scale)
            clearance = self.signed(self.head,tr,rot,scale)
        else:
            ids, head_ids = self.active
            d = self.signed(np.take_along_axis(p,ids[...,None],axis=1),tr,rot,scale)
            clearance = self.signed(np.take_along_axis(self.head,head_ids[...,None],axis=1),tr,rot,scale)
        gaps = []
        for i in self.pad_indices:
            pad = p[:,i,:]
            # At a corner, distance to the rectangular envelope also bounds
            # the gap from below, unlike taking a single supporting plane.
            u = (pad-tr) @ rot
            ext = np.maximum(abs(u)-scale*np.array([152.,109.,108.]),0.)
            d_pad = self.signed(pad,tr,rot,scale)
            d_pad = np.where((ext>0).any(-1), np.maximum(d_pad,np.linalg.norm(ext,axis=-1)),d_pad)
            if self.flat and len(gaps)==3:
                half = scale*np.array([152.,109.,108.])
                dx = abs(u[...,0]-half[0])
                dy = np.maximum(abs(u[...,1])-half[1]+self.flat,0.)
                dz = np.maximum(abs(u[...,2])-half[2]+self.flat,0.)
                d_pad = np.sqrt(dx*dx+dy*dy+dz*dz)
            gaps.append(d_pad.min(1))
        gaps = np.stack(gaps,axis=1)
        near_head = clearance.min(1)
        if full:
            return gaps.max(0), -d.min(), near_head.min(), gaps.min(0)
        contact = np.maximum(gaps-self.target,0.)
        skin = np.maximum(-d-self.wall,0.)
        worst = np.sort(skin,axis=1)[:,-12:]
        head = np.maximum(11.-near_head,0.)
        rest = x.copy()
        rest[:6] *= .008
        rest[6:9] *= .025
        rest[9:21] *= .06
        rest[21:] *= .11
        return np.concatenate([contact.ravel()*self.contact_weight, worst.ravel()*self.skin_weight,head*3,rest])

    def choose_active(self,x):
        tr,rot,scale = self.parts(x)
        skin = self.signed(self.predicted(x),tr,rot,scale)
        head = self.signed(self.head,tr,rot,scale)
        self.active = (np.argpartition(skin,192,axis=1)[:,:192],
                       np.argpartition(head,48,axis=1)[:,:48])

    def record(self,x):
        tr,rot,scale = self.parts(x)
        matrix = Matrix(rot.tolist()).to_4x4()
        matrix.translation = Vector((self.center + tr - rot@(scale*self.center))/1000)
        pose = json_pose(self.orig@matrix)
        pose['scale'] = np.abs(np.asarray(C.to_3x3()).T @ scale).tolist()
        pose.update(usesLeftHand=True, leftHandSupport={'bone': N+'LeftHand', 'pads': ['Thumb','Index']})
        if len(x)>9:
            static = pose['fingerRotationDeltas'] = {}
            tracks = {}
            for k,name in enumerate(self.names):
                vec = x[9+3*k:12+3*k]/100
                bridge = self.r.bridge(name)

                def as_gltf(vector):
                    angle = np.linalg.norm(vector)
                    q = Quaternion(vector, angle) if angle else Quaternion()
                    return quat_values(bridge.inverted() @ q @ bridge)

                if k>=2 and len(x)>21:
                    motion = x[21+(k-2)*12:21+(k-1)*12].reshape(4,3)/100
                    ticks = np.linspace(0,self.r.end_time,round(self.r.end_time*48)+1)
                    phase = np.column_stack([np.sin(h*np.pi*ticks) for h in (1,2)] +
                                            [np.cos(h*np.pi*ticks)-1 for h in (1,2)])
                    tracks[N+name] = [as_gltf(vector) for vector in vec + phase @ motion]
                elif np.linalg.norm(vec)>=.001:
                    static[N+name] = as_gltf(vec)
            if tracks:
                pose['fingerRotationTracks'] = dict(sampleRateHz=48, interpolation='slerp',
                                                   jointQuaternions=tracks)
        cfg = dict(body=BODY_NAME,bone=N+'RightHand',unit='metres',quaternionOrder='xyzw',
                   coordinates='glTF Y-up', sockets={CLIP:pose})
        SOCKET_FILE.write_text(json.dumps(cfg,indent=2)+'\n')


def least_squares(fit,initial,iterations):
    x = initial.copy()
    damping = .1
    diff = .035
    eye = np.eye(len(x))
    for i in range(iterations):
        fit.choose_active(x)
        r = fit.residual(x)
        jac = np.column_stack([(fit.residual(x+e*diff)-r)/diff for e in eye])
        jac[:,fit.fixed] = 0.
        lhs = jac.T@jac
        rhs = -jac.T@r
        score = r@r
        accepted = False
        for _ in range(13):
            change = np.linalg.solve(lhs+damping*eye,rhs)
            work = x + change
            work[:3] = np.clip(work[:3],-65,65)
            work[3:6] = np.clip(work[3:6],-60,60)
            work[6:9] = np.clip(work[6:9],-12,12)
            work[9:21] = np.clip(work[9:21],-45,45)
            work[21:] = np.clip(work[21:],-20,20)
            active = fit.active
            fit.active = None
            vals = fit.residual(work)
            fit.active = active
            if vals@vals < score:
                x = work
                damping = max(.0001,damping*.45)
                accepted = True
                break
            damping *= 4
        if i%10==0:
            print(i,round(float(score),3),fit.residual(x,True),flush=True)
        if not accepted or np.linalg.norm(change)<.008:
            break
    return x


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suffix', default='1')
    parser.add_argument('--frames', type=int, default=13)
    parser.add_argument('--mode', type=int, choices=(6,9,21,45), default=21)
    parser.add_argument('--iters', type=int, default=85)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--target', type=float, default=1.24)
    parser.add_argument('--wall', type=float, default=.3)
    parser.add_argument('--weight', type=float, default=6.)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--file', default='solution')
    parser.add_argument('--start', default='solution')
    parser.add_argument('--flat', type=float, default=0.)
    parser.add_argument('--emit', action='store_true')
    parser.add_argument('--fix-digit', type=int, action='append', default=[])
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    fit = Fit(args.suffix,args.frames)
    fit.target, fit.wall, fit.contact_weight = args.target, args.wall, args.weight
    fit.flat = args.flat
    fit.fixed = [9+3*k+j for k in args.fix_digit for j in range(3)]
    x = np.zeros(args.mode)
    if args.resume:
        prev = np.load(HERE/(args.start+'.npy'))
        x[:min(len(prev),len(x))] = prev[:len(x)]
    if args.seed is not None:
        rng = np.random.default_rng(args.seed)
        x += rng.normal(0.,6.,len(x))
    x[fit.fixed] = 0.
    if not args.emit:
        x = least_squares(fit,x,args.iters)
        np.save(HERE/(args.file+'.npy'),x)
    fit.record(x)
    print('RESULT',x.tolist(),fit.residual(x,True),flush=True)


if __name__=='__main__':
    main()
