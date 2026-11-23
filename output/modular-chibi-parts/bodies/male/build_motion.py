"""Retarget glTF channels by bind-relative transform and repackage without a mesh."""
from copy import deepcopy
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector
from asset_io import *


def rotation(values):
    return Quaternion((values[3],*values[:3])).normalized()


def xyzw(q):
    return q.x,q.y,q.z,q.w


def rest(asset):
    transforms = [Matrix.LocRotScale(Vector(n.get('translation',(0,0,0))),
                                     rotation(n.get('rotation',(0,0,0,1))),
                                     Vector(n.get('scale',(1,1,1)))) for n in asset.nodes]
    world = {}
    def resolve(i):
        if i not in world:
            world[i] = resolve(asset.parents[i]) @ transforms[i] if i in asset.parents else transforms[i]
        return world[i]
    for i in range(len(asset.nodes)):
        resolve(i)
    return [m.decompose() for m in transforms], world


def skeleton_doc(asset):
    # The Studio export uses separate, identity-transform scene roots for the
    # mesh and skeleton. Drop the former, preserving the target joint indices.
    doc = {'asset':{'version':'2.0','generator':'Male chibi bind-relative retarget'},
           'scene':0,'scenes':deepcopy(asset.doc['scenes']),'nodes':deepcopy(asset.nodes),'animations':[]}
    assert len(doc['scenes']) == 1
    mesh, = [i for i,n in enumerate(doc['nodes']) if 'mesh' in n]
    assert mesh == len(doc['nodes'])-1
    doc['nodes'].pop()
    doc['scenes'][0]['nodes'].remove(mesh)
    return doc


def append_action(out,target,rig,clip,times,arrays):
    shared = out.accessor(times,'SCALAR',bounds=True)
    short = out.accessor(times[[0,-1]],'SCALAR',bounds=True)
    action = dict(name=clip,samplers=[],channels=[])
    for j,name in enumerate(rig.names):
        idx = target.ids['mixamorig:'+name]
        for kind,p,form in zip(('translation','rotation','scale'),arrays,('VEC3','VEC4','VEC3')):
            data = np.array(p[:,j],dtype=np.float32)
            if kind=='rotation':
                for i in range(1,len(data)):
                    if np.dot(data[i-1],data[i])<0:
                        data[i] *= -1
            stable = np.max(abs(data-data[0])) < 2.e-7
            value = out.accessor(data[[0,-1]] if stable else data,form)
            action['channels'].append(dict(target=dict(node=idx,path=kind),sampler=len(action['samplers'])))
            action['samplers'].append(dict(input=short if stable else shared,output=value,interpolation='LINEAR'))
    out.doc['animations'].append(action)


def retarget(destination):
    target = GLB(HERE/'body_male.glb')
    dest, dw = rest(target)
    out = Writer(skeleton_doc(target))
    out.doc["skins"] = deepcopy(target.doc["skins"])
    for skin in out.doc["skins"]:
        matrices = target.accessor(skin["inverseBindMatrices"])
        skin["inverseBindMatrices"] = out.accessor(matrices, "MAT4")
    durations = {}
    for path in BANKS:
        source = GLB(path)
        src, sw = rest(source)
        assert set(source.ids)==set(target.ids)
        timings = {}
        for anim in source.doc['animations']:
            converted = {'name':anim['name'],'samplers':[],'channels':[]}
            durations[anim['name']] = 0.
            for ch in anim['channels']:
                idx = ch['target']['node']
                name = source.nodes[idx].get('name')
                if name not in target.ids:
                    continue
                dst = target.ids[name]
                prop = ch['target']['path']
                sampler = anim['samplers'][ch['sampler']]
                shape = 'VEC4' if prop=='rotation' else 'VEC3'
                values = source.accessor(sampler['output'])
                time_id = sampler['input']
                if time_id not in timings:
                    raw_time = source.accessor(time_id)
                    timings[time_id] = out.accessor(raw_time,'SCALAR',bounds=True)
                durations[anim['name']] = max(durations[anim['name']],float(source.accessor(time_id).max()))
                assert sampler.get('interpolation','LINEAR') in ('LINEAR','STEP')
                s_loc,s_rot,s_scale = src[idx]
                d_loc,d_rot,d_scale = dest[dst]
                if prop=='translation':
                    # Transfer the displacement in world metres, retaining each
                    # target rest pivot, including Hips origin and floor scale.
                    basis = dw[target.parents[dst]].to_3x3().inverted() @ sw[source.parents[idx]].to_3x3()
                    values = (values-np.asarray(s_loc)) @ np.asarray(basis).T + np.asarray(d_loc)
                elif prop=='rotation':
                    convert = dw[dst].to_quaternion().inverted() @ sw[idx].to_quaternion()
                    left = d_rot @ convert @ s_rot.inverted()
                    right = convert.inverted()
                    values = [xyzw((left @ rotation(row) @ right).normalized()) for row in values]
                elif prop=='scale':
                    values = values / np.asarray(s_scale) * np.asarray(d_scale)
                else:
                    raise ValueError(prop)
                re_sampler = {'input':timings[time_id],'output':out.accessor(values,shape),
                              'interpolation':sampler.get('interpolation','LINEAR')}
                converted['channels'].append({'sampler':len(converted['samplers']),
                                              'target':{'node':dst,'path':prop}})
                converted['samplers'].append(re_sampler)
            assert len(converted['channels']) >= 65
            out.doc['animations'].append(converted)
            print('RETARGET',anim['name'],durations[anim['name']],len(converted['channels']),flush=True)
    assert set(durations)==set(CLIPS)
    out.doc['animations'].sort(key=lambda a:CLIPS.index(a['name']))
    out.write(destination)
    write_json(HERE/'qa/clip_durations.json', durations)


if __name__=='__main__':
    retarget(HERE/'.runtime/motion_relative.glb')
