"""Render the exported GLBs as fixed-view Cycles CPU contact sheets."""
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parent
VIEWS = {
    "bay": (0, -1, 0),
    "aerial": (-.59, -.87, .57),
    "north": (-1, 0, 0),
    "rear": (0, 1, 0),
    "plan": (0, 0, 1),
    "south": (1, 0, 0),
}


def vector_bounds(points):
    return (Vector(tuple(min(p[i] for p in points) for i in range(3))),
            Vector(tuple(max(p[i] for p in points) for i in range(3))))


def area(name, position, target, energy, color, size):
    light = bpy.data.lights.new(name, "AREA")
    light.energy, light.color, light.size = energy, color, size
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (target-obj.location).to_track_quat("-Z", "Y").to_euler()


def render(stem, temp):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f"{stem}.glb"))
    points=[obj.matrix_world @ v.co for obj in bpy.context.scene.objects if obj.type=="MESH"
            for v in obj.data.vertices]
    lo,hi=vector_bounds(points)
    mid=(lo+hi)*.5
    span=max(hi-lo)
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=12
    scene.cycles.use_denoising=True
    scene.render.threads_mode="FIXED"
    scene.render.threads=2
    scene.render.resolution_x=720
    scene.render.resolution_y=480
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.view_settings.view_transform="AgX"
    scene.view_settings.look="AgX - Medium High Contrast"

    world=bpy.data.worlds.new("Daylight")
    scene.world=world
    world.use_nodes=True
    world.node_tree.nodes.get("Background").inputs[0].default_value=(.53,.64,.78,1)
    world.node_tree.nodes.get("Background").inputs[1].default_value=.48

    bpy.ops.mesh.primitive_plane_add(size=span*30,location=(mid.x,mid.y,-.045))
    stage=bpy.context.object
    mat=bpy.data.materials.new("Review backdrop")
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(.095,.127,.153,1)
    bsdf.inputs["Roughness"].default_value=.85
    stage.data.materials.append(mat)
    data=bpy.data.lights.new("Sun","SUN")
    data.energy=2.0
    data.angle=.15
    sun=bpy.data.objects.new("Sun",data)
    scene.collection.objects.link(sun)
    sun.rotation_euler=Vector((.60,.67,-1.26)).to_track_quat("-Z","Y").to_euler()
    area("Rear fill",(mid.x+span*.8,mid.y+span*.7,span*.8),mid,span**2*6,(.73,.85,1),span*.75)

    cam_data=bpy.data.cameras.new("QA camera")
    cam_data.type="ORTHO"
    cam_data.clip_end=span*40
    cam=bpy.data.objects.new("QA camera",cam_data)
    scene.collection.objects.link(cam)
    scene.camera=cam
    renders=[]
    for label, position in VIEWS.items():
        direction=Vector(position).normalized()
        rotation=direction.to_track_quat("Z","Y") if label!="plan" else Quaternion()
        local=[rotation.inverted() @ v for v in points]
        near,far=vector_bounds(local)
        center=rotation @ ((near+far)*.5)
        cam.rotation_euler=rotation.to_euler()
        cam.location=center+direction*span*2.5
        aspect=scene.render.resolution_x/scene.render.resolution_y
        cam_data.ortho_scale=max(far.x-near.x,(far.y-near.y)*aspect)*1.12
        file=temp/f"{stem}_{label}.png"
        scene.render.filepath=str(file)
        bpy.ops.render.render(write_still=True)
        renders.append(file)
    args=["ffmpeg","-v","error","-y","-filter_complex_threads","1"]
    for file in renders:
        args+=["-i",str(file)]
    layout="0_0|w0+4_0|w0+w1+8_0|0_h0+4|w0+4_h0+4|w0+w1+8_h0+4"
    args+=["-filter_complex",f"xstack=inputs=6:layout={layout}:fill=0x28313A",
           "-frames:v","1","-threads","1",str(ROOT/f"{stem}_contact.png")]
    subprocess.run(args,check=True)


if __name__=="__main__":
    assert bpy.app.version==(5,1,2)
    stems = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ("mbs_towers","mbs_podium")
    assert set(stems) <= {"mbs_towers","mbs_podium"}, stems
    with tempfile.TemporaryDirectory(prefix=".review-",dir=ROOT) as directory:
        for stem in stems:
            render(stem,Path(directory))
