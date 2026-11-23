"""Rebuild Persimmon Scout in a fresh background Blender process."""
import math
import os
from pathlib import Path
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("NINJA_OUT", str(HERE)))
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from body import build_body
from head import build_head
from kit import mat


def select(objects, active):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active


def add_rig(parts):
    skeleton = bpy.data.armatures.new("Scout skeleton")
    rig = bpy.data.objects.new("Persimmon Scout", skeleton)
    bpy.context.collection.objects.link(rig)
    select([rig], rig)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, start, end, parent=None):
        b = skeleton.edit_bones.new(name)
        b.head, b.tail = start, end
        if parent:
            b.parent = skeleton.edit_bones[parent]

    bone("Pelvis", (0, 0, .21), (0, 0, .31))
    bone("Torso", (0, 0, .31), (0, 0, .52), "Pelvis")
    bone("Head", (0, 0, .52), (0, 0, .93), "Torso")
    for s, sign in [("L", 1), ("R", -1)]:
        loc = lambda x,y,z: (x*sign,y,z)
        left = sign == 1
        shoulder = loc(.101,0,.445)
        elbow = loc(.150,-.005,.372) if left else loc(.151,0,.371)
        hand = loc(.181,-.036,.318) if left else loc(.190,-.054,.362)
        knee = loc(.082,-.020 if left else .012,.15)
        ankle = loc(.093,-.025 if left else .016,.070)
        bone("UpperArm."+s, shoulder, elbow, "Torso")
        bone("Forearm."+s, elbow, hand, "UpperArm."+s)
        bone("Thigh."+s, loc(.067,0,.25), knee, "Pelvis")
        bone("Shin."+s, knee, ankle, "Thigh."+s)
        bone("Foot."+s, ankle, loc(.093,ankle[1]-.065,.033), "Shin."+s)
    bpy.ops.object.mode_set(mode="OBJECT")
    skeleton.display_type = "STICK"
    for obj in parts:
        tag = obj.get("bone", "Head")
        if tag not in skeleton.bones:
            raise ValueError(f"{obj.name} refers to missing bone {tag}")
        group = obj.vertex_groups.new(name=tag)
        group.add(list(range(len(obj.data.vertices))), 1, "REPLACE")
        mod = obj.modifiers.new("Scout puppet rig", "ARMATURE")
        mod.object = rig
    # Individual parts are rigid, like pieces of a poseable vinyl figure.
    for frame, phase in [(1,0), (16,1), (31,0), (46,-.65), (61,0)]:
        for name, angles in {"Head":(1.2*phase,-2.2*phase,2.1*phase),
                             "Torso":(-.6*phase,.5*phase,.32*phase),
                             "Forearm.R":(-2.8*phase,0,1.1*phase)}.items():
            b = rig.pose.bones[name]
            b.rotation_mode = "XYZ"
            b.rotation_euler = [math.radians(v) for v in angles]
            b.keyframe_insert(data_path="rotation_euler", frame=frame, group=name)
    rig.animation_data.action.name = "Lookout Idle"
    return rig


def track(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def studio(scene):
    def disk(name, radius, depth, z, material):
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=depth, location=(0,0,z))
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(material)
        bevel = obj.modifiers.new("Edge radius", "BEVEL")
        bevel.width, bevel.segments = min(.009, depth*.34), 4
        obj.modifiers.new("Edge shading", "WEIGHTED_NORMAL")
    disk("Display plinth • lacquer", .382, .034, -.025, mat("Lacquer","#225653",.34))
    disk("Display plinth • brass seam", .378, .004, -.010, mat("Antique brass","#C89C67",.33,.30))
    disk("Display plinth • inset", .372, .008, -.005, mat("Sage enamel","#86ADA5",.52))
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.0421))
    bpy.context.object.name = "Warm studio floor"
    bpy.context.object.data.materials.append(mat("Studio parchment","#E5CEB2",.85))
    def area(name, loc, watts, size, color):
        d = bpy.data.lights.new(name, "AREA")
        d.energy, d.shape, d.size, d.color = watts, "DISK", size, color
        obj = bpy.data.objects.new(name,d)
        scene.collection.objects.link(obj)
        obj.location = loc
        track(obj,(0,0,.60))
    area("Large warm softbox",(-2.1,-2.9,3.6),210,2.6,(1,.91,.81))
    area("Skylight",(2.5,-1.4,2.0),135,2.2,(.78,.9,1))
    area("Hair rim",(.3,1.7,2.7),185,1.5,(1,.85,.67))
    world = bpy.data.worlds.new("Soft ambient")
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs[0].default_value=(.55,.6,.7,1)
    world.node_tree.nodes["Background"].inputs[1].default_value=.35
    scene.world=world
    cam = bpy.data.objects.new("Portrait camera", bpy.data.cameras.new("Portrait lens"))
    scene.collection.objects.link(cam)
    scene.camera=cam
    cam.data.type="ORTHO"
    return cam


def camera(cam, angle, target=(0,0,.53), scale=1.34):
    phi=math.radians(angle)
    cam.location=Vector(target)+Vector((2.8*math.sin(phi),-2.8*math.cos(phi),.32))
    track(cam,target)
    cam.data.ortho_scale=scale


def main():
    if not bpy.app.background:
        raise RuntimeError("Run in a fresh background Blender process.")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    for folder in ["sources","exports","previews"]:
        (OUT/folder).mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene
    scene.name="Persimmon Scout"
    build_body()
    build_head()
    parts=[o for o in scene.objects if o.type=="MESH"]
    expressions=[o for o in parts if o.data.shape_keys]
    if expressions:
        select(expressions,expressions[0])
        bpy.ops.object.join()
        face=bpy.context.object
        face.name="Face expressions"
        face["bone"]="Head"
    parts=[o for o in scene.objects if o.type=="MESH"]
    rig=add_rig(parts)
    scene.frame_start,scene.frame_end=1,61
    scene.render.fps=24
    scene.frame_set(1)
    cam=studio(scene)
    camera(cam,12)
    scene.render.engine="CYCLES"
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x,scene.render.resolution_y=760,820
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.view_settings.view_transform="AgX"
    scene.render.filepath="//../previews/portrait.png"
    select([],None)
    for ar in bpy.context.screen.areas:
        if ar.type=="VIEW_3D":
            ar.spaces.active.region_3d.view_perspective="CAMERA"
            ar.spaces.active.overlay.show_overlays=False
            ar.spaces.active.shading.color_type="MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"sources/persimmon-ninja.blend"))
    # Join only the export copy in this background process; the saved source keeps named parts.
    active=face if expressions else parts[0]
    select(parts,active)
    bpy.ops.object.join()
    merged=bpy.context.object
    merged.name="Scout • skinned figure"
    select([merged,rig],merged)
    bpy.ops.export_scene.gltf(filepath=str(OUT/"exports/persimmon-ninja.glb"),export_format="GLB",
                              use_selection=True,export_animations=True,export_animation_mode="ACTIONS",
                              export_morph_normal=False,export_texcoords=False,export_yup=True,
                              export_cameras=False,export_lights=False)
    scene.render.filepath=str(OUT/"previews/portrait.png")
    bpy.ops.render.render(write_still=True)


if __name__=="__main__":
    main()
