"""Render the actual 40 mm cylinder at the independently measured fit axis."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
from capture import Hand, Studio, get_points, load_body, select_action, sha

def main():
    audit=WORK/'audit'/'export_checks.json'
    results=json.loads(audit.read_text())
    body_path=WORK/'body_male_v1.glb'
    library=WORK/'hand_gestures_male.glb'
    assert sha(body_path)==results['static']['sha256']
    assert sha(library)==results['library']['sha256']
    body,rig=load_body(body_path)
    select_action(rig,None)
    rest=get_points(body)
    old=set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(library))
    for ob in set(bpy.context.scene.objects)-old:
        ob.hide_render=True
    studio=Studio(12)
    mat=bpy.data.materials.new('QA cylinder')
    mat.use_nodes=True
    node=mat.node_tree.nodes['Principled BSDF']
    node.inputs['Base Color'].default_value=(.052,.32,.38,1)
    node.inputs['Roughness'].default_value=.48
    report={'diameter_mm':40,'body':sha(body_path),'library':sha(library),'audit_sha256':sha(audit),'sides':{}}
    for tag,side,sg in (('L','Left',1),('R','Right',-1)):
        key='hand_grip_small_'+tag
        gauge=results['poses'][key]['cylinder_fit']
        select_action(rig,bpy.data.actions[key])
        pts=get_points(body)
        hand=Hand(body,rig,rest,side,sg)
        subset=[pts[i] for i in hand.ids]
        axis=Vector(gauge['axis_world']).normalized()
        center=Vector(gauge['point_world_mm'])*.001
        dist=[(q-center).dot(axis) for q in subset]
        length=max(dist)-min(dist)+.024
        center+=axis*((max(dist)+min(dist))*.5)
        bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.020,depth=length,location=center)
        ob=bpy.context.object
        ob.name='40 mm grip gauge'
        ob.rotation_euler=axis.to_track_quat('Z','Y').to_euler()
        for face in ob.data.polygons:
            face.use_smooth=len(face.vertices)==4
        ob.data.materials.append(mat)
        bpy.context.view_layer.update()
        shown=subset+[ob.matrix_world@v.co for v in ob.data.vertices]
        frames=[]
        for label,direction in (('palmar',(.31*sg,-.32,-1)),('end',(.29*sg,-1,-.21))):
            path=HERE/f'grip_40mm_{tag}_{label}.png'
            frames.append(studio.frame(path,shown,direction,(sg,0,0),resolution=(520,390)))
        report['sides'][tag]={'gauge':gauge,'render_length_mm':length*1000,'frames':frames}
        bpy.data.objects.remove(ob,do_unlink=True)
    (HERE/'grip_manifest.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
