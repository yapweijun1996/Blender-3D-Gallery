"""Verify joint bends and seven local motion clips on a reimported body GLB.

Blender 5.1: --python motion_review.py -- [body.glb] [--probe].
--probe writes only to .motion-runtime and skips image rendering.
"""
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
from collections import defaultdict

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
MOTION = HERE.parents[4] / "models/tripo-chibi-motion/motion.glb"
CLIPS = ("walk", "run", "wave", "jump", "idle", "nod", "dance")
# A side-leaning camera shows leg travel; a frontal camera shows the waving arm.
SHOTS = {"walk": (15, (.70, -1.00, .10)), "run": (8, (.85, -1.00, .12)),
         "wave": (19, (.18, -1.00, .06)), "jump": (9, (.73, -1.00, .12))}
STRESS = {"LeftArm": ((0, 1, 0), 75), "LeftForeArm": ((0, 0, 1), -95),
          "RightUpLeg": ((1, 0, 0), -65), "RightLeg": ((1, 0, 0), 100)}
PREFIX = "mixamorig:"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    old = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=False)
    created = set(bpy.context.scene.objects)-old
    arm, = (o for o in created if o.type == "ARMATURE")
    body, = (o for o in created if o.type == "MESH" and o.find_armature() == arm)
    for obj in created:
        if obj.type == "MESH" and obj != body:
            obj.hide_render = True
    return arm, body


def binding(arm):
    return {bone.name: arm.matrix_world @ bone.matrix_local for bone in arm.data.bones}


def prepare_arm(arm):
    animation = arm.animation_data_create()
    for track in animation.nla_tracks:
        track.mute = True
    animation.action = None
    for bone in arm.pose.bones:
        assert bone.rotation_mode == "QUATERNION", (bone.name, bone.rotation_mode)
        bone.matrix_basis = Matrix.Identity(4)
    return animation


def activate(animation, act):
    animation.action = act
    animation.action_slot = act.slots[0]
    assert animation.action_slot == act.slots[0]


def positions(body):
    obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = obj.data
    raw = np.empty(len(mesh.vertices)*3, dtype=np.float32)
    mesh.vertices.foreach_get("co", raw)
    m = np.array(obj.matrix_world)
    return raw.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]


def max_angle(q):
    return math.degrees(2*math.acos(min(1., abs(q.normalized().w))))


class MeshCheck:
    def __init__(self, body):
        self.body = body
        self.rest = positions(body)
        self.edges = np.array([tuple(edge.vertices) for edge in body.data.edges])
        a,b = self.edges.T
        length = np.linalg.norm(self.rest[a]-self.rest[b], axis=1)
        self.valid = length > .001
        self.edges = self.edges[self.valid]
        self.length = length[self.valid]
        self.edge_groups = defaultdict(list)
        for edge_index, (a,b) in enumerate(self.edges):
            groups = [{body.vertex_groups[w.group].name.removeprefix(PREFIX)
                       for w in body.data.vertices[i].groups if w.weight > .05} for i in (a,b)]
            for label, pair in (("shoulder", ("Shoulder","Arm")), ("elbow", ("Arm","ForeArm")),
                                ("hip", ("Hips","UpLeg")), ("knee", ("UpLeg","Leg"))):
                for side in ("Left","Right"):
                    names={side+name if name!="Hips" else name for name in pair}
                    if names <= set.union(*groups):
                        self.edge_groups[label].append(edge_index)
                        break
        self.edge_groups = {k: np.array(v) for k,v in self.edge_groups.items()}
        duplicates = defaultdict(list)
        for index,row in enumerate(self.rest):
            duplicates[tuple(np.round(row, 6))].append(index)
        pairs = [p for ids in duplicates.values() for p in itertools.combinations(ids,2)]
        self.seams = np.array(pairs, dtype=int).reshape((-1,2))

    def sample(self):
        xyz = positions(self.body)
        assert np.isfinite(xyz).all() and xyz.shape == self.rest.shape
        a,b = self.edges.T
        r = np.linalg.norm(xyz[a]-xyz[b],axis=1)/self.length
        crack = 0.
        if self.seams.size:
            a,b = self.seams.T
            crack = float(np.linalg.norm(xyz[a]-xyz[b],axis=1).max()*1000)
        worst=int(np.argmax(r))
        lo,hi=self.edges[worst]
        worst_edge=dict(vertex_indices=[int(lo),int(hi)],rest_endpoints_m=self.rest[[lo,hi]].tolist(),
                        rest_length_mm=float(1000*self.length[worst]),
                        posed_length_mm=float(1000*self.length[worst]*r[worst]),
                        groups=[[self.body.vertex_groups[w.group].name for w in self.body.data.vertices[i].groups if w.weight>.01] for i in (lo,hi)])
        return dict(max_paired_seam_separation_mm=crack, max_edge_stretch_ratio=float(r.max()),
                    max_edge_details=worst_edge,p99_edge_ratio=float(np.percentile(r,99)),
                    p999_edge_ratio=float(np.percentile(r,99.9)),
                    max_joint_edge_stretch_ratio={k:float(r[v].max()) for k,v in self.edge_groups.items()},
                    min_joint_edge_length_ratio={k:float(r[v].min()) for k,v in self.edge_groups.items()},
                    max_vertex_displacement_mm=float(np.linalg.norm(xyz-self.rest, axis=1).max()*1000),
                    lowest_vertex_mm=float(xyz[:,2].min()*1000))

    def summary(self, samples):
        worst_frame=max(samples,key=lambda f:samples[f]["max_edge_stretch_ratio"])
        return dict(frames=len(samples), first_frame=min(samples), last_frame=max(samples),
                    max_edge_details=dict(frame=worst_frame,**samples[worst_frame]["max_edge_details"]),
                    worst_frame_p99_edge_ratio=max(s["p99_edge_ratio"] for s in samples.values()),
                    worst_frame_p999_edge_ratio=max(s["p999_edge_ratio"] for s in samples.values()),
                    finite_unchanged_vertex_count=True,
                    max_paired_seam_separation_mm=max(v["max_paired_seam_separation_mm"] for v in samples.values()),
                    max_edge_stretch_ratio=max(v["max_edge_stretch_ratio"] for v in samples.values()),
                    max_joint_edge_stretch_ratio={k:max(s["max_joint_edge_stretch_ratio"][k] for s in samples.values())
                                                  for k in self.edge_groups},
                    min_joint_edge_length_ratio={k:min(s["min_joint_edge_length_ratio"][k] for s in samples.values())
                                                 for k in self.edge_groups},
                    max_vertex_displacement_mm=max(v["max_vertex_displacement_mm"] for v in samples.values()),
                    floor_z_range_mm=[min(v["lowest_vertex_mm"] for v in samples.values()),
                                      max(v["lowest_vertex_mm"] for v in samples.values())])


def render_setup():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.threads_mode="FIXED"
    scene.render.threads=4
    scene.render.resolution_x = scene.render.resolution_y = 576
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    world = bpy.data.worlds.new("Motion review world")
    scene.world = world
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs[0].default_value=(.17,.20,.25,1)
    world.node_tree.nodes["Background"].inputs[1].default_value=.65
    scene.view_settings.view_transform="AgX"
    for name, location, energy, size in [
            ("Softbox",(-1.5,-2.4,2.4),150,1.8),
            ("Fill",(1.5,-1.4,1.0),75,1.5),("Rim",(-.5,1.5,1.7),105,1.0)]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy,"DISK",size
        obj=bpy.data.objects.new(name,data)
        scene.collection.objects.link(obj)
        obj.location=location
        obj.rotation_euler=(Vector((0,0,.5))-obj.location).to_track_quat("-Z","Y").to_euler()
    cam=bpy.data.cameras.new("Motion orthographic")
    camera=bpy.data.objects.new(cam.name,cam)
    scene.collection.objects.link(camera)
    cam.type="ORTHO"
    scene.camera=camera
    return camera


def capture(body, camera, angle, path):
    xyz=positions(body)
    center=Vector((xyz.min(axis=0)+xyz.max(axis=0))/2)
    view=Vector(angle).normalized()
    q=(-view).to_track_quat("-Z","Y")
    camera.location=center+view*3.1
    camera.rotation_euler=q.to_euler()
    rotation=np.array(q.to_matrix())
    projected=xyz @ rotation[:,:2]
    camera.data.ortho_scale=float(max(np.ptp(projected,axis=0))*1.13)
    scene=bpy.context.scene
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    return dict(file=path.name, sha256=sha(path), camera_direction=angle,
                ortho_scale=camera.data.ortho_scale, center_m=tuple(center))


def main():
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    probe = "--probe" in args or "--probe-render" in args
    body_path=Path(next((a for a in args if a not in ("--probe","--probe-render")), str(HERE/"body_female_v1.glb"))).resolve()
    out=HERE/".motion-runtime" if probe else HERE
    out.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    target, body=load(body_path)
    source, source_mesh=load(MOTION)
    source_mesh.hide_render=True
    source_mesh.hide_viewport=True
    sa,ta=prepare_arm(source),prepare_arm(target)
    scene=bpy.context.scene
    scene.frame_set(0)
    src,dst=binding(source),binding(target)
    assert src.keys()==dst.keys()
    assert all((b.parent.name if b.parent else None)==(target.data.bones[b.name].parent.name if target.data.bones[b.name].parent else None)
               for b in source.data.bones)
    basis={name:dst[name].to_quaternion().inverted() @ m.to_quaternion() for name,m in src.items()}
    offsets={name:dst[name].to_3x3().inverted() @ m.to_3x3() for name,m in src.items()}
    bindings=[(source.pose.bones[n],target.pose.bones[n],basis[n],basis[n].inverted(),offsets[n]) for n in src]
    check=MeshCheck(body)
    stat={"source_sha256":sha(MOTION),"body_sha256":sha(body_path),"blender":bpy.app.version_string,
          "mesh_vertices":len(check.rest),"coincident_pairs":len(check.seams),"edge_probe_min_rest_length_mm":1,
          "rest_seam_quantization_m":.000001,"joint_edge_count":{k:len(v) for k,v in check.edge_groups.items()},
          "rest_axis_change_degrees":{n:max_angle(q) for n,q in basis.items()},
          "rotation_mode":"unchanged QUATERNION on all source and target bones",
          "sample_method":"Every integer Blender frame, inclusive at 24 fps. Direct playback assigns the source action and slot to the target. Rest-adjusted playback conjugates the source local quaternion delta through source/target world bind axes, maps local translation into the target bind axes and preserves scale. Both use the original clip's selected action slot.",
          "direct":{},"rest_adjusted":{},"frames":{}}
    shots_enabled=not probe or "--probe-render" in args
    camera=render_setup() if shots_enabled else None
    for mode in ("direct","rest_adjusted"):
        for name in CLIPS:
            act=bpy.data.actions[name]
            activate(sa,act)
            if mode=="direct":
                activate(ta,act)
            else:
                ta.action=None
            samples={}
            for f in range(math.ceil(act.frame_range[0]),math.floor(act.frame_range[1])+1):
                scene.frame_set(f)
                if mode=="rest_adjusted":
                    for a,b,q,inv,offset in bindings:
                        b.rotation_quaternion=(q @ a.rotation_quaternion @ inv).normalized()
                        b.location=offset @ a.location
                        b.scale=a.scale
                    bpy.context.view_layer.update()
                samples[f]=check.sample()
                if shots_enabled and mode=="rest_adjusted" and name in SHOTS and f==SHOTS[name][0]:
                    shot=capture(body,camera,SHOTS[name][1],out/f"motion_{name}_{f:03d}.png")
                    stat["frames"][name]=dict(frame=f,mode=mode,measurement=samples[f],**shot)
            stat[mode][name]=check.summary(samples)
    for b in target.pose.bones:
        b.matrix_basis=Matrix.Identity(4)
    for name,(axis,angle) in STRESS.items():
        bone=target.pose.bones[PREFIX+name]
        basis_rot=dst[bone.name].to_quaternion()
        bone.rotation_quaternion=basis_rot.inverted() @ Quaternion(Vector(axis),math.radians(angle)) @ basis_rot
    bpy.context.view_layer.update()
    stat["combined_stress"]={"world_rest_axis_degrees":STRESS,**check.sample()}
    if shots_enabled:
        shot=capture(body,camera,(.65,-1,.09),out/"motion_joint_stress.png")
        stat["combined_stress"]["render"]=shot
    stat["review_limits"]="Vertex coincidence and edge length detect UV splits, detached seams and stretching at sampled frames. They do not classify every smooth fold, interpart contact or subframe event."
    (out/"motion_review.json").write_text(json.dumps(stat,indent=2,allow_nan=False)+"\n")
    print("MOTION_REPORT",out/"motion_review.json",flush=True)


if __name__=="__main__":
    main()
