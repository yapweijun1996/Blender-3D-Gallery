"""Blender background script. Pass input walk GLB and output GLB after --."""
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

source, destination = map(Path, sys.argv[sys.argv.index("--") + 1:])
raw = source.read_bytes()
size = struct.unpack_from("<I", raw, 12)[0]
doc = json.loads(raw[20:20 + size])
binary = bytearray(raw[28 + size:][:doc["buffers"][0]["byteLength"]])
nodes = doc["nodes"]
ids = {node["name"]: i for i, node in enumerate(nodes)}
parents = {child: i for i, node in enumerate(nodes) for child in node.get("children", [])}


def accessor(rows, kind):
    while len(binary) % 4:
        binary.append(0)
    offset = len(binary)
    for row in rows:
        binary.extend(struct.pack("<" + "f" * len(row), *row))
    view = len(doc["bufferViews"])
    doc["bufferViews"].append(dict(buffer=0, byteOffset=offset, byteLength=len(binary)-offset))
    item = dict(bufferView=view, componentType=5126, count=len(rows), type=kind)
    if kind == "SCALAR":
        item.update(min=[rows[0][0]], max=[rows[-1][0]])
    doc["accessors"].append(item)
    return len(doc["accessors"]) - 1


def track(clip, node, path, times, values, kind):
    sampler = len(clip["samplers"])
    clip["samplers"].append(dict(input=accessor([(t,) for t in times], "SCALAR"),
                                 output=accessor(values, kind), interpolation="LINEAR"))
    clip["channels"].append(dict(sampler=sampler, target=dict(node=node, path=path)))


def rotation(i):
    x, y, z, w = nodes[i].get("rotation", [0, 0, 0, 1])
    return Quaternion((w, x, y, z))


def gesture(name, times, poses):
    clip = dict(name=name, samplers=[], channels=[])
    for bone, axis, angles in poses:
        i = ids[bone]
        world = rotation(i)
        ancestor = i
        while ancestor in parents:
            ancestor = parents[ancestor]
            world = rotation(ancestor) @ world
        local_axis = world.inverted() @ Vector(axis)
        values = []
        for angle in angles:
            q = rotation(i) @ Quaternion(local_axis, math.radians(angle))
            values.append((q.x, q.y, q.z, q.w))
        track(clip, i, "rotation", times, values, "VEC4")
    doc["animations"].append(clip)


# Derive vertical root compensation from the evaluated soles at the walk samples.
walk = doc["animations"][0]
walk["name"] = "Walk"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
scene = bpy.context.scene
mesh = next(o for o in scene.objects if o.type == "MESH" and o.vertex_groups)
feet = {g.index for g in mesh.vertex_groups if "Foot" in g.name or "Toe" in g.name}
indices = [v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if g.group in feet) > .5]
channels = walk["channels"]
root = ids["Armature"]
assert not any(c["target"] == dict(node=root, path="translation") for c in channels)
duration = max(doc["accessors"][s["input"]]["max"][0] for s in walk["samplers"])
count = math.ceil(duration * 60)
times = [duration * i / count for i in range(count + 1)]
values = []
for time in times:
    frame = time * scene.render.fps / scene.render.fps_base
    scene.frame_set(math.floor(frame), subframe=frame % 1)
    obj = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    sole = min((obj.matrix_world @ obj.data.vertices[i].co).z for i in indices)
    x, y, z = nodes[root].get("translation", (0, 0, 0))
    values.append((x, y - sole, z))
track(walk, root, "translation", times, values, "VEC3")

gesture("Idle", [0, 1.3, 2.6, 4], [
    ("Spine02", (0, 0, 1), [0, 2, -1, 0]), ("Head", (0, 1, 0), [0, 5, -3, 0])])
gesture("Wave", [0, .45, .7, .95, 1.2, 1.45, 2.05, 2.35], [
    ("L_Upperarm", (1, 0, 0), [0, 72, 72, 72, 72, 72, 0, 0]),
    ("L_Forearm", (1, 0, 0), [0, 32, 54, 29, 54, 32, 0, 0])])
gesture("Nod", [0, .35, .65, .95, 1.3, 1.8], [
    ("Head", (0, 0, 1), [0, -13, 2, -10, 1, 0])])
# glTF skins are transformed by their joints. Keep the mesh as a scene root.
mesh_node = next(i for i, node in enumerate(nodes) if "skin" in node)
nodes[parents[mesh_node]]["children"].remove(mesh_node)
doc["scenes"][doc.get("scene", 0)]["nodes"].append(mesh_node)
doc["buffers"][0]["byteLength"] = len(binary)
header = json.dumps(doc, separators=(",", ":")).encode()
header += b" " * (-len(header) % 4)
binary += bytes(-len(binary) % 4)
destination.write_bytes(struct.pack("<4sIIII", b"glTF", 2, 28+len(header)+len(binary), len(header), 0x4E4F534A)
                        + header + struct.pack("<II", len(binary), 0x004E4942) + binary)
