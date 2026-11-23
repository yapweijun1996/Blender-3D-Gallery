"""Build one candidate and replay the exported GLB on its source skeleton."""
import sys

from asset_io import HERE, MOTION, bpy, json, np, write_json
from bake import bake
from body_audit import load_body_motion, set_frame, use_action
from fit_module import read_module
from fitting_geometry import arrays, limit_weights, weights
from garments import PALETTES
from gate_module import BODY, companions, measure
from refine import refine, restore_rest_clearance
from tailoring import top
from swept_skirt import build_skirt
from shorts import build_shorts
from settle import settle


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
    for label,color,roughness in zip(('Wall','Trim','Detail'),
                                    PALETTES[item][:(2 if item=='top-hoodie' else 3)],(.78,.85,.66)):
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


def run(item, first=1, mode="author"):
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
    evidence = {}
    if mode=='settle':
        if previous_report is None:
            raise ValueError('The preceding round must have a full gate.')
        with np.load(previous) as saved:
            points,faces,w,axis,mat = (saved[k] for k in ('points','faces','weights','axis','materials'))
        w = limit_weights(w)
        guide = None
        if item.startswith('top'):
            initial, indices, initial_weights, *_ = top(item,b,bf,skin,names,first-1)
            if np.array_equal(indices,faces) and np.allclose(initial_weights,w):
                if item=='top-hoodie':
                    cowl = np.isclose(w[:,names.index('mixamorig:Neck')],.12)
                    initial[cowl] = points[cowl]
                guide = initial
        elif item=='bottom-shorts':
            guide = points.copy()
            x,y,z = points.T
            inseam = np.exp(-((abs(x)-.034)/.029)**2-((y+.112)/.028)**2-((z-.296)/.033)**2)
            guide[:,1] -= .0045*inseam
            guide[:,2] += .0030*inseam
            back = np.clip((y-.005)/.055,0,1) * np.clip((z-.341)/.032,0,1)
            guide[:,1] += .004*back
            guide[:,2] += .007*back
        points,w,evidence['settle'] = settle(
            points,faces,w,item,scene,arm,body,bf,actions,layer_data,previous_report,guide,(b,bf,skin))
    elif item=='bottom-skirt':
        (points,faces,w,axis,mat),evidence = build_skirt(scene,arm,body,b,bf,actions,names,first)
    else:
        if item.startswith('top'):
            points,faces,w,axis,mat = top(item,b,bf,skin,names,first)
        else:
            points,faces,w,axis,mat = build_shorts(b,bf,skin,names,first)
        points, evidence = bake(points,faces,w,axis,item,scene,arm,body,bf,actions,layer_data)
        points = refine(points,faces,w,axis,item,scene,arm,body,bf,actions,layer_data,evidence,previous_report)
        if item in ('top-jacket','bottom-shorts'):
            points,evidence['rest_relief'] = restore_rest_clearance(points,faces,b,bf)
    assert len(faces) <= 6000, (item,len(faces))
    assert (np.count_nonzero(w,axis=1)<=4).all() and np.allclose(w.sum(axis=1),1)
    use_action(arm,None)
    set_frame(scene,0)
    name = f'{item}-r{first}'
    path = export(item,name,arm,points,faces,w,mat,names)
    np.savez_compressed(cache,points=points,faces=faces,weights=w,axis=axis,materials=mat)
    from render_item import render
    render(path, name, item)
    scene, arm, master, actions = load_body_motion(MOTION)
    body = read_module(BODY,arm)
    layers = {ref.name:read_module(ref,arm) for ref in companions(item)}
    report, _ = measure(path,scene,arm,master,body,actions,layers)
    report['round'] = first
    gate_path = HERE/'qa'/f'{name}.gate.json'
    write_json(gate_path,report)
    report['bake'] = evidence
    write_json(gate_path,report)
    print('ROUND',name,report['samples'],max(r['peak_inside'] for r in report['clips'].values()),
          max(r['peak_pairs'] for r in report['clips'].values()),
          min(r['min_signed_m'] for r in report['clips'].values()),
          {k:max(r['layer_peaks'][k] for r in report['clips'].values()) for k in layers},flush=True)


if __name__=='__main__':
    item,round_no,*mode = sys.argv[sys.argv.index('--')+1:]
    run(item,int(round_no),*mode)
