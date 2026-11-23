"""Build one candidate and replay the exported GLB on its source skeleton."""
import sys

from asset_io import HERE, MOTION, bpy, json, np, write_json
from bake import bake
from body_audit import load_body_motion, set_frame, use_action
from fit_module import read_module
from fitting_geometry import arrays, limit_weights, weights
from garments import PALETTES, build, underarm_ease
from gate_module import BODY, companions, measure
from refine import refine


def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color,1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color,1)
    shader.inputs['Roughness'].default_value = roughness
    return mat


def export(item, name, arm, p, f, w, m, names):
    mesh = bpy.data.meshes.new(item)
    mesh.from_pydata(p.tolist(),[],f.tolist())
    mesh.update()
    obj = bpy.data.objects.new(item, mesh)
    bpy.context.collection.objects.link(obj)
    for label,color,roughness in zip(('Fabric or leather','Cuffs and hems','Detail'),
                                    PALETTES[item],(.78,.85,.66)):
        mesh.materials.append(material(label,color,roughness))
    for polygon,index in zip(mesh.polygons,m):
        polygon.use_smooth = True
        polygon.material_index = int(index)
    # Write vertex groups without setting custom normals on the new mesh.
    for i,bone in enumerate(names):
        group = obj.vertex_groups.new(name=bone)
        for vertex in np.flatnonzero(w[:,i]):
            group.add([int(vertex)],float(w[vertex,i]),'REPLACE')
    obj.modifiers.new('Male skeleton','ARMATURE').object = arm
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = HERE/f'{name}.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                              export_animations=False,export_skins=True,export_yup=True)
    bpy.data.objects.remove(obj,do_unlink=True)
    return path


def run(item, first=1):
    scene, arm, master, actions = load_body_motion(MOTION)
    use_action(arm,None)
    set_frame(scene,0)
    body = read_module(BODY,arm)
    layers = {path.name: read_module(path,arm) for path in companions(item)}
    layer_data = {filename:(obj,arrays(obj)[1].tolist()) for filename,obj in layers.items()}
    b, bf = arrays(body)
    names = [bone.name for bone in arm.data.bones]
    skin = weights(body,names)
    cache = HERE/'qa'/f'{item}-r{first}.npz'
    previous_gate = HERE/'qa'/f'{item}-r{first-1}.gate.json'
    previous_report = json.loads(previous_gate.read_text()) if previous_gate.exists() else None
    previous = HERE/'qa'/f'{item}-r{first-1}.npz'
    layer_conflict = previous_report and any(any(row['layer_peaks'].values())
                                            for row in previous_report['clips'].values())
    fresh = (item=='top-hoodie' or not previous.exists() or bool(layer_conflict)
             or (item.startswith('bottom') and first==3))
    if fresh:
        points,faces,w,axis,mat = build(item,b,bf,skin,names,first)
    else:
        with np.load(previous) as saved:
            points,faces,w,axis,mat = (saved[k] for k in ('points','faces','weights','axis','materials'))
        w = limit_weights(w)
    assert (np.count_nonzero(w,axis=1)<=4).all() and np.allclose(w.sum(axis=1),1)
    if item=='top-jacket' and first>1:
        underarm = any(.075<abs(frame['worst_position_m'][0])<.142 and .473<frame['worst_position_m'][2]<.536
                       for group in previous_report['clips'].values() for frame in group['frames']
                       if 'worst_position_m' in frame) if previous_report else False
        if underarm:
            underarm_ease(points,first)
    if item=='shoes-boots' and first==3 and previous_report:
        # Keep cuff height while relieving the fore-ankle crease found in run.
        x,y,z = points.T
        quarter = np.exp(-((abs(x)-.091)/.034)**2-((y+.073)/.022)**2-((z-.075)/.017)**2)
        points[:,1] -= .004*quarter
    limit = 3500 if item=='shoes-boots' else 6000
    assert len(faces) <= limit, (item,len(faces),limit)
    points, evidence = bake(points,faces,w,axis,item,scene,arm,body,bf,actions,layer_data,fresh,first)
    evidence['fresh_cut'] = fresh
    points = refine(points,faces,w,axis,item,scene,arm,body,bf,actions,layer_data,evidence,previous_report)
    use_action(arm,None)
    set_frame(scene,0)
    name = f'{item}-r{first}'
    path = export(item,name,arm,points,faces,w,mat,names)
    np.savez_compressed(cache,points=points,faces=faces,weights=w,axis=axis,materials=mat)
    report, obj = measure(path,scene,arm,master,body,actions,layers)
    report['round'] = first
    report['bake'] = evidence
    write_json(HERE/'qa'/f'{name}.gate.json',report)
    print('ROUND',name,report['samples'],max(r['peak_inside'] for r in report['clips'].values()),
          max(r['peak_pairs'] for r in report['clips'].values()),
          min(r['min_signed_m'] for r in report['clips'].values()),
          {k:max(r['layer_peaks'][k] for r in report['clips'].values()) for k in layers},flush=True)


if __name__=='__main__':
    item,round_no = sys.argv[sys.argv.index('--')+1:]
    run(item,int(round_no))
