"""Build the editable Indigo head, export the selected portrait and render its hero camera."""
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from face import build_face
from forms import material, mesh
from hair import build_hair, scalp_point
from export_source import export_portrait


def regroup(objects, collection):
    for obj in objects:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)


def collection(scene, name):
    result = bpy.data.collections.new(name)
    scene.collection.children.link(result)
    return result


def headband():
    cloth = material("Band | deep petrol canvas", "#234359", .78)
    metal = material("Clasp | champagne brass", "#EFBB70", .36)
    enamel = material("Clasp | midnight enamel", "#254555", .39)
    rows, count = 6, 96
    verts, faces = [], []
    for row in range(rows):
        t = row/(rows-1)
        for j in range(count):
            a = 2*math.pi*j/count
            front = (1+math.cos(a))/2
            z = .62+.142*front+.015*math.sin(a)+t*.071
            point = scalp_point(z,a)
            rim = 1.008+.009*math.sin(t*math.pi)
            verts.append((point.x*rim,point.y*rim,z))
            if row:
                k,m = (row-1)*count+j, (row-1)*count+(j+1)%count
                faces.append((k,m,m+count,k+count))
    wrap = mesh("Forehead | woven storm band", verts, faces, cloth)
    solid=wrap.modifiers.new("Band edge", "SOLIDIFY")
    solid.thickness=.003

    # The badge follows the local forehead rather than facing the portrait camera.
    def surface(u,v,offset):
        a=.515+u
        z=.810+v+.016*math.sin(a-.515)
        p=scalp_point(z,a)
        normal=Vector((math.sin(a),-math.cos(a),.085)).normalized()
        return p+normal*offset
    def inlay(name, outline, offset, mat):
        v=[surface(0,0,offset)]+[surface(u,z,offset) for u,z in outline]
        f=[(0,j+1,(j+1)%len(outline)+1) for j in range(len(outline))]
        obj=mesh(name,v,f,mat)
        solid=obj.modifiers.new("Cast thickness","SOLIDIFY")
        solid.thickness=.003
        return obj
    plate=[(-.183,-.012),(-.135,-.029),(.146,-.029),(.18,-.013),(.18,.014),(.14,.028),(-.14,.028),(-.183,.012)]
    inlay("Band clasp | brass frame",plate,.018,metal)
    inlay("Band clasp | inlaid face",[(x*.90,z*.82) for x,z in plate],.022,enamel)
    # Two swept, tapering strokes echo the hair silhouette.
    for idx,(u,v) in enumerate([(-.046,-.002),(.041,.003)]):
        points=[(u-.046,v-.012),(u-.018,v+.008),(u+.052,v+.016),(u+.014,v-.001)]
        # Triangulate the convex motif locally, keeping the centre inside each shape.
        verts=[surface(a,b,.026) for a,b in points]
        mesh("Band clasp | swift "+str(idx+1),verts,[(0,1,2),(0,2,3)],metal)


def studio(scene):
    def aim(obj,point):
        obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
    def light(name, xyz, watts, size, color):
        data=bpy.data.lights.new(name, 'AREA')
        obj=bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj)
        obj.location=xyz
        data.energy, data.shape, data.size, data.color=watts,'DISK',size,color
        aim(obj,(0,0,.64))
    light("Softbox | key",(-2.4,-3.4,3.8), 295,2.7,(1,.91,.84))
    light("Softbox | fill",(2.7,-2.1,1.9),175,2.4,(.80,.92,1))
    light("Softbox | rim",(.6,2.1,2.9),360,1.85,(.65,.84,1))
    scene.world=bpy.data.worlds.new("Indigo portrait world")
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.50,.54,.64,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.27
    ground_mat=material("Studio | mist blue","#ACC2C7",.94)
    mesh("Studio | seamless floor",[(-100,-100,-.006),(100,-100,-.006),(100,100,-.006),(-100,100,-.006)],[(0,1,2,3)],ground_mat)
    data=bpy.data.cameras.new("Portrait lens")
    cam=bpy.data.objects.new("Camera | Hero",data)
    scene.collection.objects.link(cam)
    scene.camera=cam
    th=math.radians(23)
    cam.location=(3.1*math.sin(th),-3.1*math.cos(th),1.03)
    aim(cam,(0,.01,.65))
    data.type='ORTHO'
    data.ortho_scale=1.49
    scene.render.engine='CYCLES'
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_percentage=100
    scene.render.resolution_x=scene.render.resolution_y=760
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.22
    scene.render.image_settings.file_format='PNG'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active
                space.region_3d.view_perspective='CAMERA'
                space.region_3d.view_distance=1.8
                space.shading.color_type='MATERIAL'
                space.overlay.show_overlays=False


def build():
    if not bpy.app.background:
        raise RuntimeError("Use an isolated background Blender process to build this portrait.")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.name="Indigo | portrait"
    face_group=collection(scene,"01 | face and scarf")
    hair_group=collection(scene,"02 | indigo hair")
    band_group=collection(scene,"03 | embossed headband")
    build_face()
    regroup(list(scene.collection.objects), face_group)
    build_hair()
    regroup(list(scene.collection.objects), hair_group)
    for guide in bpy.data.collections["Indigo | editable hair spines"].objects:
        guide["destination"]=hair_group.name
    headband()
    regroup(list(scene.collection.objects),band_group)
    assets=list(face_group.objects)+list(hair_group.objects)+list(band_group.objects)
    studio(scene)
    studio_group=collection(scene,"Studio | camera and lighting")
    regroup(list(scene.collection.objects),studio_group)

    # Pack the exact source for interactive guide editing on a machine without this repo.
    for file in ("forms.py","hair.py"):
        block=bpy.data.texts.new("Indigo_"+file)
        block.write((HERE/file).read_text())
    editor=bpy.data.texts.new("INSTRUCTIONS - Refresh hair guides.py")
    editor.write('''"""Enable the editable hair spines collection, edit a Bezier guide, then Run Script here.
The visible subdivided lock cages can also be edited directly. Refresh rebuilds the selected
guide(s) only. Export the edited source without regenerating to preserve manual changes."""
import bpy, sys
from unittest.mock import patch
guides = [o for o in bpy.context.selected_objects if o.type == 'CURVE' and o.name.startswith('Guide ')]
if not guides:
    raise ValueError("Select one or more Indigo guide curves in Object Mode")
with patch.dict(sys.modules, {"forms": bpy.data.texts["Indigo_forms.py"].as_module()}):
    editor = bpy.data.texts["Indigo_hair.py"].as_module()
    for guide in guides:
        editor.rebuild_lock(guide)
''')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in assets:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=face_group.objects[0]
    bpy.context.preferences.filepaths.save_version=0
    out=Path(os.environ.get("INDIGO_OUTPUT",str(HERE)))
    for folder in ("sources","exports","previews"):
        (out/folder).mkdir(parents=True,exist_ok=True)
    scene.render.filepath="//../previews/hero.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"sources/indigo-ninja-head.blend"))
    export_portrait(out/"exports/indigo-ninja-head.glb")
    if os.environ.get("INDIGO_SKIP_RENDER") != "1":
        scene.render.filepath=str(out/"previews/hero.png")
        bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    build()
